"""TC-03 / PLAN-BE-19: Automated Malformed PE Robustness Test Suite.

Acceptance Criterion 2: Malformed PE test.
Verifies that the static parser fails closed on all malformed, truncated,
corrupted, non-PE, oversized, and adversarial inputs without crashing,
without leaking file handles, and without fabricating feature vectors.
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest
from x_sentinel.data.raw_pe import (
    FeatureGatedError,
    FileTooLargeError,
    MalformedPEError,
    PathTraversalError,
    PEParseError,
    RawPEFeatureExtractor,
    extract_static_pe,
    read_bounded_bytes,
    validate_input_path,
    validate_pe_structure,
)

from tests.fixtures.synthetic_pe import (
    build_malformed_pe_variants,
    build_minimal_valid_pe,
)


@pytest.fixture
def enabled_extractor(tmp_path: Path) -> RawPEFeatureExtractor:
    return RawPEFeatureExtractor(enabled=True, base_dir=tmp_path)


# ---------------------------------------------------------------------------
# 1. Structural Header Malformation Tests
# ---------------------------------------------------------------------------


def test_empty_file_rejected(tmp_path: Path, enabled_extractor: RawPEFeatureExtractor) -> None:
    empty_file = tmp_path / "empty.exe"
    empty_file.write_bytes(b"")
    with pytest.raises(MalformedPEError, match="File too small"):
        enabled_extractor.extract(empty_file)


def test_empty_bytes_rejected() -> None:
    with pytest.raises(MalformedPEError, match="File too small"):
        extract_static_pe(b"")


def test_truncated_dos_header_rejected(tmp_path: Path, enabled_extractor: RawPEFeatureExtractor) -> None:
    short_file = tmp_path / "short_dos.exe"
    short_file.write_bytes(b"MZ" + b"\x00" * 30)
    with pytest.raises(MalformedPEError, match="File too small"):
        enabled_extractor.extract(short_file)


@pytest.mark.parametrize(
    "magic_bytes,label",
    [
        (b"PK\x03\x04", "ZIP"),
        (b"\x7fELF", "ELF"),
        (b"\xca\xfe\xba\xbe", "Mach-O"),
        (b"%PDF", "PDF"),
        (b"ABCD", "Arbitrary text"),
        (b"\x00\x00\x00\x00", "Zero bytes"),
    ],
)
def test_invalid_dos_magic_rejected(magic_bytes: bytes, label: str) -> None:
    corrupt_data = magic_bytes + b"\x00" * 60
    with pytest.raises(MalformedPEError, match="Invalid DOS signature"):
        validate_pe_structure(corrupt_data)


def test_invalid_lfanew_offset_zero() -> None:
    pe = bytearray(build_minimal_valid_pe()[:128])
    pe[0x3C:0x40] = b"\x00\x00\x00\x00"
    with pytest.raises(MalformedPEError, match="Invalid PE header offset"):
        validate_pe_structure(bytes(pe))


def test_invalid_lfanew_offset_out_of_bounds() -> None:
    pe = bytearray(build_minimal_valid_pe()[:128])
    pe[0x3C:0x40] = b"\x00\x00\x10\x00"  # offset 0x100000 > file len
    with pytest.raises(MalformedPEError, match="Invalid PE header offset"):
        validate_pe_structure(bytes(pe))


def test_missing_pe_signature() -> None:
    pe = bytearray(build_minimal_valid_pe())
    pe[0x80:0x84] = b"NE\x00\x00"  # OS/2 NE signature
    with pytest.raises(MalformedPEError, match="Invalid PE signature"):
        validate_pe_structure(bytes(pe))


def test_truncated_coff_header() -> None:
    pe = build_minimal_valid_pe()[: 0x80 + 4 + 10]
    with pytest.raises(MalformedPEError, match="Invalid PE header offset|Truncated COFF"):
        validate_pe_structure(pe)


def test_zero_sections_rejected() -> None:
    pe = bytearray(build_minimal_valid_pe())
    # In COFF header, num_sections is at offset 2
    pe[0x80 + 4 + 2 : 0x80 + 4 + 4] = b"\x00\x00"
    with pytest.raises(MalformedPEError, match="zero sections"):
        validate_pe_structure(bytes(pe))


def test_corrupted_section_count_out_of_bounds() -> None:
    pe = bytearray(build_minimal_valid_pe())
    # Set section count to 0xFFFF
    pe[0x80 + 4 + 2 : 0x80 + 4 + 4] = b"\xff\xff"
    with pytest.raises(MalformedPEError, match="Section headers out of bounds"):
        validate_pe_structure(bytes(pe))


def test_corrupted_section_raw_offset_out_of_bounds() -> None:
    pe = bytearray(build_minimal_valid_pe())
    # Section header starts at 0x80 + 4 + 20 + 240 = 0x188
    # PointerToRawData is at offset 20 in section header
    pe[0x188 + 20 : 0x188 + 24] = b"\x00\x00\x00\x10"  # 0x10000000
    with pytest.raises(MalformedPEError, match="Section 0 data out of bounds"):
        validate_pe_structure(bytes(pe))


def test_random_bytes_rejected() -> None:
    random_data = bytes((i * 43 + 7) % 256 for i in range(4096))
    with pytest.raises(MalformedPEError):
        extract_static_pe(random_data)


# ---------------------------------------------------------------------------
# 2. Input Security & Resource Boundary Tests
# ---------------------------------------------------------------------------


def test_file_exceeding_max_bytes_rejected(tmp_path: Path) -> None:
    oversized = tmp_path / "oversized.exe"
    # Create file with 100 bytes when max_bytes is 50
    oversized.write_bytes(b"A" * 100)
    extractor = RawPEFeatureExtractor(enabled=True, base_dir=tmp_path, max_bytes=50)

    with pytest.raises(FileTooLargeError, match="exceeds maximum allowed limit"):
        extractor.extract(oversized)


def test_byte_buffer_exceeding_max_bytes_rejected() -> None:
    with pytest.raises(FileTooLargeError, match="exceeds maximum allowed limit"):
        read_bounded_bytes(b"A" * 100, max_bytes=50)


def test_path_traversal_parent_directory_rejected(tmp_path: Path) -> None:
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    outside_file = tmp_path / "target.exe"
    outside_file.write_bytes(build_minimal_valid_pe())

    extractor = RawPEFeatureExtractor(enabled=True, base_dir=sub_dir)
    with pytest.raises(PathTraversalError, match="Path traversal detected"):
        extractor.extract(sub_dir / ".." / "target.exe")


def test_path_traversal_without_base_dir_rejected() -> None:
    """Verify that path traversal sequences ('..') are rejected even when base_dir is None."""
    with pytest.raises(PathTraversalError, match="Path traversal detected"):
        validate_input_path("../secret.exe", base_dir=None)

    with pytest.raises(PathTraversalError, match="Path traversal detected"):
        validate_input_path("subdir/../../secret.exe", base_dir=None)


def test_null_byte_in_path_rejected(tmp_path: Path) -> None:
    extractor = RawPEFeatureExtractor(enabled=True, base_dir=tmp_path)
    with pytest.raises(PathTraversalError, match="Null byte detected"):
        extractor.extract("sample.exe\x00.evil")


def test_empty_path_rejected() -> None:
    with pytest.raises(MalformedPEError, match="Input path cannot be empty"):
        validate_input_path("")


def test_nonexistent_file_rejected(tmp_path: Path, enabled_extractor: RawPEFeatureExtractor) -> None:
    with pytest.raises(FileNotFoundError, match="Input file not found"):
        enabled_extractor.extract(tmp_path / "nonexistent.exe")


def test_directory_path_rejected(tmp_path: Path, enabled_extractor: RawPEFeatureExtractor) -> None:
    sub_dir = tmp_path / "a_directory"
    sub_dir.mkdir()
    with pytest.raises(MalformedPEError, match="is not a regular file"):
        enabled_extractor.extract(sub_dir)


# ---------------------------------------------------------------------------
# 3. Fail-Closed Feature Gating Invariants
# ---------------------------------------------------------------------------


def test_disabled_by_default_raises_feature_gated_error() -> None:
    extractor = RawPEFeatureExtractor()
    assert not extractor.enabled
    with pytest.raises(FeatureGatedError, match="Raw PE/LIEF extraction is feature-gated"):
        extractor.extract("valid.exe")


def test_disabled_extract_bytes_raises_feature_gated_error() -> None:
    extractor = RawPEFeatureExtractor(enabled=False)
    with pytest.raises(FeatureGatedError, match="Raw PE/LIEF extraction is feature-gated"):
        extractor.extract_bytes(b"MZ" + b"\x00" * 100)


def test_feature_gated_error_inherits_not_implemented_error() -> None:
    """Ensures backwards compatibility with existing baseline security tests."""
    extractor = RawPEFeatureExtractor()
    with pytest.raises(NotImplementedError):
        extractor.extract("untrusted.exe")


# ---------------------------------------------------------------------------
# 4. Comprehensive Synthetic Malformed Corpus Test (All Variants)
# ---------------------------------------------------------------------------


def test_all_synthetic_malformed_variants(tmp_path: Path, enabled_extractor: RawPEFeatureExtractor) -> None:
    variants = build_malformed_pe_variants()
    assert len(variants) >= 12, "Must test at least 12 distinct malformed variants"

    for name, data in variants.items():
        sample = tmp_path / f"variant_{name}.bin"
        sample.write_bytes(data)

        with pytest.raises(MalformedPEError):
            enabled_extractor.extract(sample)


# ---------------------------------------------------------------------------
# 5. Adversarial Bit-Flip Fuzzing Resilience (Never Crashes Process)
# ---------------------------------------------------------------------------


def test_adversarial_bit_flip_fuzzing_resilience() -> None:
    """Corrupt random bytes of valid PE to verify process never terminates abruptly."""
    base_pe = bytearray(build_minimal_valid_pe())

    # Create 20 corrupt permutations
    for seed in range(20):
        corrupt = bytearray(base_pe)
        offset = (seed * 73 + 19) % len(corrupt)
        corrupt[offset] = (corrupt[offset] ^ 0xFF)

        try:
            vec = extract_static_pe(bytes(corrupt))
            # If it succeeded (e.g. non-critical padding modified), vector must be valid 2,381 floats
            assert len(vec) == 2381
            assert all(isinstance(v, float) and not math.isnan(v) and not math.isinf(v) for v in vec)
        except (MalformedPEError, PEParseError):
            # Safe handled failure
            pass
