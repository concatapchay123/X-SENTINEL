"""X-SENTINEL V3 - Raw PE/LIEF Phase 2 Adapter.

Static binary parsing and EMBER2018-compatible feature extraction.
STRICT INVARIANT: NEVER executes, loads, or detonates input binaries.
Fail-closed feature gating: Raw PE ingestion remains disabled in baseline
until the TC-03 / Extractor Equivalence Gate is formally approved.
"""

from __future__ import annotations

import math
import os
from pathlib import Path
import re
import struct
from typing import Any

import numpy as np
from sklearn.feature_extraction import FeatureHasher

from .schema import FEATURE_COUNT, validate_vector


# ---------------------------------------------------------------------------
# Typed Exceptions
# ---------------------------------------------------------------------------


class RawPEError(Exception):
    """Base exception for all Raw PE ingestion and extraction errors."""


class FeatureGatedError(NotImplementedError, RawPEError):
    """Raised when Raw PE extraction is invoked while feature-gated."""


class MalformedPEError(RawPEError, ValueError):
    """Raised when an input file is corrupted, truncated, or structurally invalid."""


class PathTraversalError(RawPEError, PermissionError):
    """Raised when an input path violates filesystem isolation or directory bounds."""


class FileTooLargeError(RawPEError, ValueError):
    """Raised when an input file exceeds the maximum allowed upload byte limit."""


class PEParseError(RawPEError, RuntimeError):
    """Raised when the static parser fails to parse binary structures."""


# ---------------------------------------------------------------------------
# Constants & Defaults
# ---------------------------------------------------------------------------

DEFAULT_MAX_BYTES: int = 52_428_800  # 50 MB (aligned with config.max_upload_bytes)

DATA_DIRECTORY_NAMES: list[str] = [
    "EXPORT_TABLE",
    "IMPORT_TABLE",
    "RESOURCE_TABLE",
    "EXCEPTION_TABLE",
    "CERTIFICATE_TABLE",
    "BASE_RELOCATION_TABLE",
    "DEBUG",
    "ARCHITECTURE",
    "GLOBAL_PTR",
    "TLS_TABLE",
    "LOAD_CONFIG_TABLE",
    "BOUND_IMPORT",
    "IAT",
    "DELAY_IMPORT_DESCRIPTOR",
    "CLR_RUNTIME_HEADER",
]


# ---------------------------------------------------------------------------
# Input Security & Path Validation
# ---------------------------------------------------------------------------


def validate_input_path(
    path: str | Path,
    base_dir: Path | None = None,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> Path:
    """Validate untrusted path input for filesystem traversal and file constraints.

    Guarantees:
    1. Rejects path traversal sequences (e.g. '../').
    2. Enforces directory isolation if base_dir is supplied.
    3. Verifies file existence.
    4. Verifies file is a regular file (rejects directories, devices, named pipes).
    5. Verifies file size does not exceed max_bytes.
    """
    raw_str = str(path)
    if not raw_str or not raw_str.strip():
        raise MalformedPEError("Input path cannot be empty")

    # Reject null bytes in path
    if "\x00" in raw_str:
        raise PathTraversalError("Null byte detected in input path")

    # Reject directory traversal sequences ('..') in path components
    normalized_str = raw_str.replace("\\", "/")
    path_parts = [part for part in normalized_str.split("/") if part]
    if ".." in path_parts or ".." in Path(path).parts:
        raise PathTraversalError(f"Path traversal detected: traversal sequence in '{raw_str}'")

    try:
        resolved_path = Path(path).resolve()
    except Exception as exc:
        raise PathTraversalError(f"Cannot resolve input path '{path}': {exc}") from exc

    if base_dir is not None:
        try:
            resolved_base = base_dir.resolve()
            resolved_path.relative_to(resolved_base)
        except ValueError as exc:
            raise PathTraversalError(
                f"Path traversal detected: '{resolved_path}' is outside '{base_dir}'"
            ) from exc

    if not resolved_path.exists():
        raise FileNotFoundError(f"Input file not found: '{resolved_path}'")

    if not resolved_path.is_file():
        raise MalformedPEError(f"Input path is not a regular file: '{resolved_path}'")

    try:
        file_size = resolved_path.stat().st_size
    except OSError as exc:
        raise PEParseError(f"Cannot determine file size for '{resolved_path}': {exc}") from exc

    if file_size > max_bytes:
        raise FileTooLargeError(
            f"File size {file_size} bytes exceeds maximum allowed limit {max_bytes} bytes"
        )

    return resolved_path


def read_bounded_bytes(
    source: str | Path | bytes | bytearray,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> bytes:
    """Safely read binary content up to max_bytes with strict upper bounds."""
    if isinstance(source, (bytes, bytearray)):
        b = bytes(source)
        if len(b) > max_bytes:
            raise FileTooLargeError(
                f"Byte buffer size {len(b)} exceeds maximum allowed limit {max_bytes} bytes"
            )
        return b

    validated_path = validate_input_path(source, max_bytes=max_bytes)
    try:
        with open(validated_path, "rb") as f:
            data = f.read(max_bytes + 1)
            if len(data) > max_bytes:
                raise FileTooLargeError(
                    f"File '{validated_path}' exceeds maximum allowed limit {max_bytes} bytes"
                )
            return data
    except (FileTooLargeError, PathTraversalError, MalformedPEError):
        raise
    except Exception as exc:
        raise PEParseError(f"Failed to read file '{validated_path}': {exc}") from exc


# ---------------------------------------------------------------------------
# PE Structural Validation (Static Analysis Only)
# ---------------------------------------------------------------------------


def validate_pe_structure(data: bytes) -> tuple[int, int]:
    """Perform pre-parsing structural validation of Windows Portable Executable headers.

    Validates:
    - Minimum length for DOS header (64 bytes).
    - DOS header magic signature (b"MZ" / 0x5A4D).
    - e_lfanew offset bounds and alignment.
    - PE signature (b"PE\\x00\\x00" / 0x00004550).
    - Basic COFF header presence.

    Returns:
    - (pe_offset, machine_type)
    """
    if len(data) < 64:
        raise MalformedPEError(
            f"File too small ({len(data)} bytes) to contain a valid DOS header (minimum 64 bytes)"
        )

    if data[:2] != b"MZ":
        raise MalformedPEError(
            f"Invalid DOS signature: expected b'MZ', got {data[:2]!r}"
        )

    (e_lfanew,) = struct.unpack_from("<I", data, 0x3C)
    if e_lfanew < 64 or e_lfanew + 24 > len(data):
        raise MalformedPEError(
            f"Invalid PE header offset (e_lfanew = {e_lfanew}, file length = {len(data)})"
        )

    pe_signature = data[e_lfanew : e_lfanew + 4]
    if pe_signature != b"PE\x00\x00":
        raise MalformedPEError(
            f"Invalid PE signature at offset {e_lfanew}: expected b'PE\\x00\\x00', got {pe_signature!r}"
        )

    coff_offset = e_lfanew + 4
    if coff_offset + 20 > len(data):
        raise MalformedPEError("Truncated COFF header: file ends before COFF header completes")

    mach, num_sections, _, _, _, size_of_opt_header, _ = struct.unpack_from(
        "<HHIIIHH", data, coff_offset
    )

    if num_sections == 0:
        raise MalformedPEError("Invalid PE: COFF header declares zero sections")

    sections_start = coff_offset + 20 + size_of_opt_header
    sections_end = sections_start + num_sections * 40
    if sections_end > len(data):
        raise MalformedPEError(
            f"Section headers out of bounds: required offset {sections_end} exceeds file length {len(data)}"
        )

    # Validate section raw data bounds
    for sec_idx in range(num_sections):
        s_offset = sections_start + sec_idx * 40
        raw_size, raw_ptr = struct.unpack_from("<II", data, s_offset + 16)
        if raw_size > 0 and raw_ptr + raw_size > len(data):
            raise MalformedPEError(
                f"Section {sec_idx} data out of bounds: offset {raw_ptr} + {raw_size} exceeds file length {len(data)}"
            )

    return e_lfanew, mach



# ---------------------------------------------------------------------------
# EMBER2018 Static Feature Extractors (2,381 Features)
# ---------------------------------------------------------------------------


def extract_byte_histogram(data: bytes) -> list[float]:
    """Extract normalized byte histogram (256 features)."""
    if not data:
        return [0.0] * 256
    counts = np.bincount(np.frombuffer(data, dtype=np.uint8), minlength=256).astype(np.float32)
    total = float(counts.sum())
    if total > 0.0:
        counts = counts / total
    return counts.tolist()


def _entropy_bin_counts(block: np.ndarray, window: int = 2048) -> tuple[int, np.ndarray]:
    c = np.bincount(block >> 4, minlength=16)
    p = c.astype(np.float32) / window
    wh = np.where(c)[0]
    h = float(np.sum(-p[wh] * np.log2(p[wh])) * 2)
    hbin = min(int(h * 2), 15)
    return hbin, c


def extract_byte_entropy(data: bytes, step: int = 1024, window: int = 2048) -> list[float]:
    """Extract joint 2d byte/entropy histogram (256 features).

    Conforms exactly to EMBER2018 ByteEntropyHistogram definition:
    16 entropy bins x 16 coarse byte value bins over 2048-byte sliding window (step 1024).
    Compatible with NumPy 2.x.
    """
    if not data:
        return [0.0] * 256

    output = np.zeros((16, 16), dtype=np.int64)
    a = np.frombuffer(data, dtype=np.uint8)

    if a.shape[0] < window:
        hbin, c = _entropy_bin_counts(a, window)
        output[hbin, :] += c
    else:
        shape = a.shape[:-1] + (a.shape[-1] - window + 1, window)
        strides = a.strides + (a.strides[-1],)
        blocks = np.lib.stride_tricks.as_strided(a, shape=shape, strides=strides)[::step, :]
        for block in blocks:
            hbin, c = _entropy_bin_counts(block, window)
            output[hbin, :] += c

    counts = output.flatten().astype(np.float32)
    total = float(counts.sum())
    if total > 0.0:
        counts = counts / total
    return counts.tolist()


_RE_ALLSTRINGS = re.compile(b"[\x20-\x7f]{5,}")
_RE_PATHS = re.compile(b"c:\\\\", re.IGNORECASE)
_RE_URLS = re.compile(b"https?://", re.IGNORECASE)
_RE_REGISTRY = re.compile(b"HKEY_")
_RE_MZ = re.compile(b"MZ")


def extract_strings(data: bytes) -> list[float]:
    """Extract string statistics and character distribution (104 features).

    Conforms exactly to EMBER2018 StringExtractor definition:
    numstrings (1), avlength (1), printables (1), printabledist (96),
    entropy (1), paths (1), urls (1), registry (1), MZ (1) = 104 features.
    """
    allstrings = _RE_ALLSTRINGS.findall(data)
    if allstrings:
        lengths = [len(s) for s in allstrings]
        avlength = float(sum(lengths)) / len(lengths)
        as_shifted_string = [b - 0x20 for b in b"".join(allstrings)]
        c = np.bincount(as_shifted_string, minlength=96)
        csum = c.sum()
        p = c.astype(np.float32) / csum
        wh = np.where(c)[0]
        h = float(np.sum(-p[wh] * np.log2(p[wh])))
    else:
        avlength = 0.0
        c = np.zeros(96, dtype=np.int64)
        csum = 0
        h = 0.0

    hist_divisor = float(csum) if csum > 0 else 1.0
    vec = np.hstack([
        float(len(allstrings)),
        float(avlength),
        float(csum),
        c / hist_divisor,
        float(h),
        float(len(_RE_PATHS.findall(data))),
        float(len(_RE_URLS.findall(data))),
        float(len(_RE_REGISTRY.findall(data))),
        float(len(_RE_MZ.findall(data))),
    ]).astype(np.float32)

    return vec.tolist()


def extract_general_file_info(data: bytes, binary: Any | None) -> list[float]:
    """Extract general PE file metadata (10 features)."""
    if binary is None:
        return [
            float(len(data)),
            0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        ]

    has_sig = getattr(binary, "has_signatures", getattr(binary, "has_signature", False))

    return [
        float(len(data)),
        float(getattr(binary, "virtual_size", 0)),
        float(int(getattr(binary, "has_debug", False))),
        float(len(getattr(binary, "exported_functions", []))),
        float(len(getattr(binary, "imported_functions", []))),
        float(int(getattr(binary, "has_relocations", False))),
        float(int(getattr(binary, "has_resources", False))),
        float(int(bool(has_sig))),
        float(int(getattr(binary, "has_tls", False))),
        float(len(getattr(binary, "symbols", []))),
    ]


def extract_header_info(data: bytes, binary: Any | None) -> list[float]:
    """Extract COFF and Optional Header metadata (62 features)."""
    hasher_10 = FeatureHasher(10, input_type="string")
    if binary is None:
        h_machine = hasher_10.transform([[""]]).toarray()[0].tolist()
        h_char = hasher_10.transform([[]]).toarray()[0].tolist()
        h_subsystem = hasher_10.transform([[""]]).toarray()[0].tolist()
        h_dll_char = hasher_10.transform([[]]).toarray()[0].tolist()
        h_magic = hasher_10.transform([[""]]).toarray()[0].tolist()
        return [0.0] + h_machine + h_char + h_subsystem + h_dll_char + h_magic + ([0.0] * 11)

    header = getattr(binary, "header", None)
    opt = getattr(binary, "optional_header", None)

    timestamp = float(getattr(header, "time_date_stamps", 0))
    machine_str = str(getattr(header, "machine", "")).split(".")[-1]
    char_list = [str(c).split(".")[-1] for c in getattr(header, "characteristics_list", [])]

    subsystem_str = str(getattr(opt, "subsystem", "")).split(".")[-1]
    dll_char_list = [str(c).split(".")[-1] for c in getattr(opt, "dll_characteristics_lists", [])]
    magic_str = str(getattr(opt, "magic", "")).split(".")[-1]

    h_machine = hasher_10.transform([[machine_str]]).toarray()[0].tolist()
    h_char = hasher_10.transform([char_list]).toarray()[0].tolist()
    h_subsystem = hasher_10.transform([[subsystem_str]]).toarray()[0].tolist()
    h_dll_char = hasher_10.transform([dll_char_list]).toarray()[0].tolist()
    h_magic = hasher_10.transform([[magic_str]]).toarray()[0].tolist()

    numeric_fields = [
        float(getattr(opt, "major_image_version", 0)),
        float(getattr(opt, "minor_image_version", 0)),
        float(getattr(opt, "major_linker_version", 0)),
        float(getattr(opt, "minor_linker_version", 0)),
        float(getattr(opt, "major_operating_system_version", 0)),
        float(getattr(opt, "minor_operating_system_version", 0)),
        float(getattr(opt, "major_subsystem_version", 0)),
        float(getattr(opt, "minor_subsystem_version", 0)),
        float(getattr(opt, "sizeof_code", 0)),
        float(getattr(opt, "sizeof_headers", 0)),
        float(getattr(opt, "sizeof_heap_commit", 0)),
    ]

    return [timestamp] + h_machine + h_char + h_subsystem + h_dll_char + h_magic + numeric_fields


def extract_section_info(data: bytes, binary: Any | None) -> list[float]:
    """Extract section characteristics and statistics (255 features)."""
    hasher_50_str = FeatureHasher(50, input_type="string")
    hasher_50_pair = FeatureHasher(50, input_type="pair")

    if binary is None:
        h_empty_pair = hasher_50_pair.transform([[]]).toarray()[0].tolist()
        h_entry_name = hasher_50_str.transform([[""]]).toarray()[0].tolist()
        h_characteristics = hasher_50_str.transform([[]]).toarray()[0].tolist()
        return [0.0] * 5 + (h_empty_pair * 3) + h_entry_name + h_characteristics

    sections = getattr(binary, "sections", [])
    sec_dicts: list[dict[str, Any]] = []

    for s in sections:
        props = [str(c).split(".")[-1] for c in getattr(s, "characteristics_lists", [])]
        sec_dicts.append({
            "name": getattr(s, "name", ""),
            "size": float(getattr(s, "size", 0)),
            "entropy": float(getattr(s, "entropy", 0.0)),
            "vsize": float(getattr(s, "virtual_size", 0)),
            "props": props,
        })

    entry_name = ""
    try:
        rva = getattr(binary.optional_header, "addressof_entrypoint", 0)
        sec_entry = binary.section_from_rva(rva)
        if sec_entry is not None:
            entry_name = getattr(sec_entry, "name", "")
        else:
            for s in sections:
                props = [str(c).split(".")[-1] for c in getattr(s, "characteristics_lists", [])]
                if "MEM_EXECUTE" in props:
                    entry_name = getattr(s, "name", "")
                    break
    except Exception:
        entry_name = ""

    general_features = [
        float(len(sec_dicts)),
        float(sum(1 for s in sec_dicts if s["size"] == 0)),
        float(sum(1 for s in sec_dicts if not s["name"])),
        float(sum(1 for s in sec_dicts if "MEM_READ" in s["props"] and "MEM_EXECUTE" in s["props"])),
        float(sum(1 for s in sec_dicts if "MEM_WRITE" in s["props"])),
    ]

    sizes = [(s["name"], s["size"]) for s in sec_dicts]
    h_sizes = hasher_50_pair.transform([sizes]).toarray()[0].tolist()

    entropies = [(s["name"], s["entropy"]) for s in sec_dicts]
    h_entropies = hasher_50_pair.transform([entropies]).toarray()[0].tolist()

    vsizes = [(s["name"], s["vsize"]) for s in sec_dicts]
    h_vsizes = hasher_50_pair.transform([vsizes]).toarray()[0].tolist()

    h_entry_name = hasher_50_str.transform([[entry_name]]).toarray()[0].tolist()

    entry_chars = [p for s in sec_dicts for p in s["props"] if s["name"] == entry_name]
    h_entry_chars = hasher_50_str.transform([entry_chars]).toarray()[0].tolist()

    return general_features + h_sizes + h_entropies + h_vsizes + h_entry_name + h_entry_chars


def extract_imports_info(data: bytes, binary: Any | None) -> list[float]:
    """Extract imported libraries and functions (1,280 features)."""
    hasher_256 = FeatureHasher(256, input_type="string")
    hasher_1024 = FeatureHasher(1024, input_type="string")

    if binary is None:
        h_libs = hasher_256.transform([[]]).toarray()[0].tolist()
        h_funcs = hasher_1024.transform([[]]).toarray()[0].tolist()
        return h_libs + h_funcs

    raw_imports: dict[str, list[str]] = {}
    for lib in getattr(binary, "imports", []):
        lib_name = getattr(lib, "name", "").lower()
        if not lib_name:
            continue
        if lib_name not in raw_imports:
            raw_imports[lib_name] = []
        for entry in getattr(lib, "entries", []):
            if getattr(entry, "is_ordinal", False):
                raw_imports[lib_name].append(f"ordinal{entry.ordinal}")
            else:
                entry_name = getattr(entry, "name", "")[:10000]
                if entry_name:
                    raw_imports[lib_name].append(entry_name)

    libraries = list(set(raw_imports.keys()))
    h_libraries = hasher_256.transform([libraries]).toarray()[0].tolist()

    full_imports = [
        f"{lib}:{func}" for lib, funcs in raw_imports.items() for func in funcs
    ]
    h_imports = hasher_1024.transform([full_imports]).toarray()[0].tolist()

    return h_libraries + h_imports


def extract_exports_info(data: bytes, binary: Any | None) -> list[float]:
    """Extract exported functions (128 features)."""
    hasher_128 = FeatureHasher(128, input_type="string")
    if binary is None:
        return hasher_128.transform([[]]).toarray()[0].tolist()

    exports: list[str] = []
    for exp in getattr(binary, "exported_functions", []):
        if hasattr(exp, "name"):
            exports.append(str(exp.name)[:10000])
        else:
            exports.append(str(exp)[:10000])

    return hasher_128.transform([exports]).toarray()[0].tolist()


def extract_data_directories(data: bytes, binary: Any | None) -> list[float]:
    """Extract PE Data Directories sizes and RVAs (30 features).

    Conforms to EMBER2018 directory order (15 directories x (size, virtual_address)).
    """
    out = [0.0] * 30
    if binary is None:
        return out

    dirs = list(getattr(binary, "data_directories", []))
    for i in range(15):
        if i < len(dirs):
            d = dirs[i]
            out[2 * i] = float(getattr(d, "size", 0))
            out[2 * i + 1] = float(getattr(d, "rva", 0))

    return out


# ---------------------------------------------------------------------------
# Core Static Parsing & Extraction Pipeline
# ---------------------------------------------------------------------------


def extract_static_pe(
    source: str | Path | bytes,
    max_bytes: int = DEFAULT_MAX_BYTES,
) -> list[float]:
    """Statically parse a PE binary and extract the canonical 2,381 EMBER2018 feature vector.

    NEVER executes the binary.
    Fails closed with typed exceptions on malformed, corrupted, or invalid inputs.
    Validates output vector against canonical schema.
    """
    data = read_bounded_bytes(source, max_bytes=max_bytes)

    # 1. Structural Pre-Validation
    validate_pe_structure(data)

    # 2. Static Binary Parsing (LIEF)
    binary = None
    try:
        import lief

        # Parse static binary structure from byte sequence
        binary = lief.PE.parse(list(data))
    except (MalformedPEError, FileTooLargeError, PathTraversalError):
        raise
    except Exception as exc:
        raise PEParseError(f"Native static parser failed on binary: {exc}") from exc

    if binary is None:
        raise MalformedPEError("Static parser returned null: binary headers or sections corrupted")

    # 3. Extract Feature Groups
    v_hist = extract_byte_histogram(data)
    v_ent = extract_byte_entropy(data)
    v_str = extract_strings(data)
    v_gen = extract_general_file_info(data, binary)
    v_hdr = extract_header_info(data, binary)
    v_sec = extract_section_info(data, binary)
    v_imp = extract_imports_info(data, binary)
    v_exp = extract_exports_info(data, binary)
    v_dirs = extract_data_directories(data, binary)

    raw_vector = (
        v_hist + v_ent + v_str + v_gen + v_hdr + v_sec + v_imp + v_exp + v_dirs
    )

    if len(raw_vector) != FEATURE_COUNT:
        raise PEParseError(
            f"Extraction produced {len(raw_vector)} features, expected canonical {FEATURE_COUNT}"
        )

    # 4. Canonical Vector Validation
    return validate_vector(raw_vector)


# ---------------------------------------------------------------------------
# Phase 2 Adapter Class
# ---------------------------------------------------------------------------


class RawPEFeatureExtractor:
    """Phase-2 adapter. Static parsing only; never execute input binaries.

    By default, enabled is False (feature-gated fail-closed).
    When enabled is True, executes static-only EMBER2018-compatible extraction.
    """

    def __init__(
        self,
        enabled: bool = False,
        max_bytes: int = DEFAULT_MAX_BYTES,
        base_dir: Path | None = None,
    ) -> None:
        self.enabled = enabled
        self.max_bytes = max_bytes
        self.base_dir = base_dir

    def extract(self, path: str | Path) -> list[float]:
        """Extract canonical 2,381 feature vector from a PE file path.

        Raises:
            FeatureGatedError: If raw PE extraction is disabled (baseline default).
            PathTraversalError: If path contains directory traversal sequences.
            FileNotFoundError: If input file does not exist.
            FileTooLargeError: If input exceeds max_bytes limit.
            MalformedPEError: If file is not a valid PE or is corrupted.
            PEParseError: If parsing or vector validation fails.
        """
        if not self.enabled:
            raise FeatureGatedError(
                "Raw PE/LIEF extraction is feature-gated until TC-03/schema equivalence is approved"
            )

        validated_path = validate_input_path(
            path, base_dir=self.base_dir, max_bytes=self.max_bytes
        )
        return extract_static_pe(validated_path, max_bytes=self.max_bytes)

    def extract_bytes(self, data: bytes) -> list[float]:
        """Extract canonical 2,381 feature vector from in-memory binary bytes.

        Raises:
            FeatureGatedError: If raw PE extraction is disabled (baseline default).
            FileTooLargeError: If bytes exceed max_bytes limit.
            MalformedPEError: If bytes do not form a valid PE binary.
            PEParseError: If parsing or vector validation fails.
        """
        if not self.enabled:
            raise FeatureGatedError(
                "Raw PE/LIEF extraction is feature-gated until TC-03/schema equivalence is approved"
            )

        return extract_static_pe(data, max_bytes=self.max_bytes)
