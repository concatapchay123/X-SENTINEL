"""Synthetic Portable Executable (PE) test fixtures for X-SENTINEL V3.

SAFE SYNTHETIC PE GENERATION ONLY.
NEVER contains real malware or malicious payloads.
Strictly used for static parsing verification, malformed resilience,
and feature equivalence testing.
"""

from __future__ import annotations

import struct


def build_minimal_valid_pe(
    machine: int = 0x8664,  # AMD64
    timestamp: int = 0x5E000000,
    section_name: bytes = b".text\x00\x00\x00",
    code_bytes: bytes = b"\x90" * 0x1FF + b"\xC3",  # 512 bytes: NOPs + RET
    subsystem: int = 3,  # CUI (Console)
    dll_characteristics: int = 0x8160,
    include_dummy_import: bool = False,
    include_dummy_export: bool = False,
) -> bytes:
    """Construct a structurally valid 64-bit PE32+ binary in memory.

    All headers, alignments, offsets, and data directories are syntactically
    correct according to the Microsoft PE/COFF specification.
    """
    # 1. DOS Header (64 bytes)
    dos_header = bytearray(64)
    dos_header[0:2] = b"MZ"
    pe_offset = 0x80  # 128 bytes
    struct.pack_into("<I", dos_header, 0x3C, pe_offset)

    # 2. DOS Stub (64 bytes)
    dos_stub = b"\x00" * 64

    # 3. PE Signature (4 bytes)
    pe_sig = b"PE\x00\x00"

    # 4. COFF Header (20 bytes)
    num_sections = 1
    size_of_opt_header = 240  # PE32+ (112 optional header + 128 data directories)
    characteristics = 0x0022  # EXECUTABLE_IMAGE | LARGE_ADDRESS_AWARE

    coff_header = struct.pack(
        "<HHIIIHH",
        machine,
        num_sections,
        timestamp,
        0,  # pointer to symbol table
        0,  # number of symbols
        size_of_opt_header,
        characteristics,
    )

    # 5. Optional Header (PE32+, 112 bytes)
    magic = 0x020B  # PE32+
    major_linker = 14
    minor_linker = 0
    size_of_code = len(code_bytes)
    size_of_init_data = 0
    size_of_uninit_data = 0
    entry_point = 0x1000
    base_of_code = 0x1000
    image_base = 0x140000000
    section_alignment = 0x1000
    file_alignment = 0x200
    major_os = 6
    minor_os = 0
    major_img = 0
    minor_img = 0
    major_sub = 6
    minor_sub = 0
    win32_ver = 0
    size_of_image = 0x2000
    size_of_headers = 0x400
    checksum = 0
    size_of_stack_reserve = 0x100000
    size_of_stack_commit = 0x1000
    size_of_heap_reserve = 0x100000
    size_of_heap_commit = 0x1000
    loader_flags = 0
    num_rva_and_sizes = 16

    opt_header = struct.pack(
        "<HBBIIIIIQIIHHHHHHIIIIHHQQQQII",
        magic,
        major_linker,
        minor_linker,
        size_of_code,
        size_of_init_data,
        size_of_uninit_data,
        entry_point,
        base_of_code,
        image_base,
        section_alignment,
        file_alignment,
        major_os,
        minor_os,
        major_img,
        minor_img,
        major_sub,
        minor_sub,
        win32_ver,
        size_of_image,
        size_of_headers,
        checksum,
        subsystem,
        dll_characteristics,
        size_of_stack_reserve,
        size_of_stack_commit,
        size_of_heap_reserve,
        size_of_heap_commit,
        loader_flags,
        num_rva_and_sizes,
    )

    # 6. Data Directories (16 entries * 8 bytes = 128 bytes)
    data_dirs = bytearray(16 * 8)

    # 7. Section Header (.text, 40 bytes)
    virtual_size = len(code_bytes)
    virtual_address = 0x1000
    size_of_raw_data = ((len(code_bytes) + 0x1FF) // 0x200) * 0x200
    pointer_to_raw_data = 0x400
    sec_characteristics = 0x60000020  # CNT_CODE | MEM_EXECUTE | MEM_READ

    sec_header = struct.pack(
        "<8sIIIIIIHHI",
        section_name[:8],
        virtual_size,
        virtual_address,
        size_of_raw_data,
        pointer_to_raw_data,
        0,
        0,  # relocations
        0,
        0,  # line numbers
        sec_characteristics,
    )

    header_block = (
        dos_header + dos_stub + pe_sig + coff_header + opt_header + bytes(data_dirs) + sec_header
    )

    # Pad header block to file_alignment (0x400)
    padding = b"\x00" * (0x400 - len(header_block))
    aligned_code = code_bytes + b"\x00" * (size_of_raw_data - len(code_bytes))

    return bytes(header_block + padding + aligned_code)


def build_malformed_pe_variants() -> dict[str, bytes]:
    """Generate a dictionary of synthetic malformed binary fixtures for robustness testing."""
    valid_pe = build_minimal_valid_pe()

    # 1. Empty buffer
    empty = b""

    # 2. Too short for DOS header
    short_16 = b"MZ\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"

    # 3. Invalid DOS magic (ELF)
    elf_magic = b"\x7fELF" + b"\x00" * 60

    # 4. Invalid DOS magic (ZIP)
    zip_magic = b"PK\x03\x04" + b"\x00" * 60

    # 5. Invalid e_lfanew: points to 0
    bad_lfanew_zero = bytearray(valid_pe[:128])
    struct.pack_into("<I", bad_lfanew_zero, 0x3C, 0)

    # 6. Invalid e_lfanew: out of file bounds
    bad_lfanew_huge = bytearray(valid_pe[:128])
    struct.pack_into("<I", bad_lfanew_huge, 0x3C, 0x100000)

    # 7. Invalid PE signature: 'NE\x00\x00'
    bad_pe_sig = bytearray(valid_pe)
    bad_pe_sig[0x80:0x84] = b"NE\x00\x00"

    # 8. Truncated at PE signature
    truncated_pe_sig = valid_pe[: 0x80 + 4]

    # 9. Truncated COFF header (only 10 bytes of COFF)
    truncated_coff = valid_pe[: 0x80 + 4 + 10]

    # 10. Truncated Optional header
    truncated_opt = valid_pe[: 0x80 + 4 + 20 + 30]

    # 11. Corrupted section count (65,535 sections declared, file ends)
    bad_sec_count = bytearray(valid_pe)
    struct.pack_into("<H", bad_sec_count, 0x80 + 4 + 2, 0xFFFF)

    # 12. Corrupted section raw offset outside file
    bad_sec_offset = bytearray(valid_pe)
    # Section header is at 0x80 + 4 + 20 + 240 = 0x188
    # PointerToRawData is at offset 20 in section header
    struct.pack_into("<I", bad_sec_offset, 0x188 + 20, 0x1000000)

    # 13. Random non-PE bytes
    random_bytes = bytes((i * 37 + 13) % 256 for i in range(2048))

    return {
        "empty": empty,
        "short_16": short_16,
        "elf_magic": elf_magic,
        "zip_magic": zip_magic,
        "bad_lfanew_zero": bytes(bad_lfanew_zero),
        "bad_lfanew_huge": bytes(bad_lfanew_huge),
        "bad_pe_sig": bytes(bad_pe_sig),
        "truncated_pe_sig": truncated_pe_sig,
        "truncated_coff": truncated_coff,
        "truncated_opt": truncated_opt,
        "bad_sec_count": bytes(bad_sec_count),
        "bad_sec_offset": bytes(bad_sec_offset),
        "random_bytes": random_bytes,
    }
