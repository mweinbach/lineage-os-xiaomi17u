"""Pure, deterministic directory-only prefix for the explicit Nezha v3 trial.

The canonical build66 ramdisk is not an input to this producer and is never
modified here. This constructs one 1024-byte newc archive encoded as a single
literal-only legacy LZ4 block. It does not execute a decompressor or kernel.
"""

from __future__ import annotations

import hashlib
import struct


DIRECTORIES = ("debug_ramdisk", "dev", "metadata", "mnt", "proc", "second_stage_resources", "sys")
CPIO_SIZE = 1024
PREFIX_SIZE = 1037
CPIO_SHA256 = "027b1045269d9d61baa63b204818977cef7ecdc953ef9265d5d8a9520404cd2e"
PREFIX_SHA256 = "b06e73b4444e3d31f6ea48e9a65c2a673cf3a58ee70a72f23a3665249d29f40d"
LEGACY_MAGIC = b"\x02\x21\x4c\x18"


class ScaffoldError(ValueError):
    """The directory scaffold does not match its exact reviewed bytes."""


def _newc_entry(name, inode, mode, nlink):
    encoded_name = name.encode("ascii") + b"\0"
    fields = (inode, mode, 0, 0, nlink, 0, 0, 0, 0, 0, 0, len(encoded_name), 0)
    entry = b"070701" + b"".join(f"{field:08x}".encode("ascii") for field in fields) + encoded_name
    return entry + bytes((-len(entry)) % 4)


def build_scaffold_cpio():
    """Return exactly seven root-owned 0755 directories and the newc trailer."""
    archive = b"".join(_newc_entry(name, inode, 0o40755, 2)
                       for inode, name in enumerate(DIRECTORIES, 1))
    archive += _newc_entry("TRAILER!!!", 0, 0, 1)
    if len(archive) > CPIO_SIZE:
        raise ScaffoldError("directory archive exceeds its fixed size")
    archive += bytes(CPIO_SIZE - len(archive))
    if hashlib.sha256(archive).hexdigest() != CPIO_SHA256:
        raise ScaffoldError("directory archive differs from the independent byte contract")
    return archive


def build_scaffold_prefix():
    """Return the 1037-byte legacy-LZ4 prefix; no files or tools are consulted."""
    # Literal length 1024: token 15 + extension 255 + 255 + 255 + 244.
    block = b"\xf0\xff\xff\xff\xf4" + build_scaffold_cpio()
    prefix = LEGACY_MAGIC + struct.pack("<I", len(block)) + block
    if len(prefix) != PREFIX_SIZE or hashlib.sha256(prefix).hexdigest() != PREFIX_SHA256:
        raise ScaffoldError("legacy-LZ4 prefix differs from the independent byte contract")
    return prefix


def inspect_scaffold_prefix(prefix):
    """Require byte-for-byte identity, including directory metadata and padding."""
    if type(prefix) is not bytes or prefix != build_scaffold_prefix():
        raise ScaffoldError("scaffold prefix differs from the exact directory-only contract")
    return {
        "schema_version": 1, "operation": "inspect-twrp-ram-boot-scaffold",
        "prefix_size_bytes": PREFIX_SIZE, "prefix_sha256": PREFIX_SHA256,
        "cpio_size_bytes": CPIO_SIZE, "cpio_sha256": CPIO_SHA256,
        "compression": {"format": "lz4-legacy", "block_count": 1,
                        "compressed_block_size_bytes": 1029, "literal_size_bytes": CPIO_SIZE,
                        "literal_only": True, "exact_encoding_verified": True},
        "directories": [{"name": name, "inode": inode, "mode": "040755", "uid": 0, "gid": 0,
                         "nlink": 2, "mtime": 0, "size_bytes": 0}
                        for inode, name in enumerate(DIRECTORIES, 1)],
        "directory_metadata_verified": True, "trailer_and_padding_verified": True,
        "file_payloads_added": False, "symlinks_added": False,
        "full_kernel_decompression_verified": False, "runtime_mounts_verified": False,
    }
