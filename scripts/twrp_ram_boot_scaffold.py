"""Pure, deterministic directory-only prefix for the explicit Nezha v3 trial.

The canonical build66 ramdisk is not an input to this producer and is never
modified here. The default seven-directory archive is 1024 bytes; explicit
include_apex adds only an empty /apex and uses 1536 bytes. Each is encoded as a
single literal-only legacy LZ4 block. No decompressor or kernel is executed.
"""

from __future__ import annotations

import hashlib
import struct


DIRECTORIES = ("debug_ramdisk", "dev", "metadata", "mnt", "proc", "second_stage_resources", "sys")
APEX_DIRECTORIES = ("apex",) + DIRECTORIES
CPIO_SIZE = 1024
PREFIX_SIZE = 1037
APEX_CPIO_SIZE = 1536
APEX_PREFIX_SIZE = 1551
CPIO_SHA256 = "027b1045269d9d61baa63b204818977cef7ecdc953ef9265d5d8a9520404cd2e"
PREFIX_SHA256 = "b06e73b4444e3d31f6ea48e9a65c2a673cf3a58ee70a72f23a3665249d29f40d"
APEX_CPIO_SHA256 = "4ea8b5645cc9d2bc0533df35431f45c604b0a76e1dc48efd7ac6f56fe4d18c14"
APEX_PREFIX_SHA256 = "001605f7ab8e588eece60c6fa715e63ad6e9caf4a2da33cd6c90cbfeb9b10d66"
LEGACY_MAGIC = b"\x02\x21\x4c\x18"


class ScaffoldError(ValueError):
    """The directory scaffold does not match its exact reviewed bytes."""


def _variant(include_apex):
    if type(include_apex) is not bool:
        raise ScaffoldError("include_apex must be an explicit boolean")
    if include_apex:
        return APEX_DIRECTORIES, APEX_CPIO_SIZE, APEX_PREFIX_SIZE, APEX_CPIO_SHA256, APEX_PREFIX_SHA256
    return DIRECTORIES, CPIO_SIZE, PREFIX_SIZE, CPIO_SHA256, PREFIX_SHA256


def _newc_entry(name, inode, mode, nlink):
    encoded_name = name.encode("ascii") + b"\0"
    fields = (inode, mode, 0, 0, nlink, 0, 0, 0, 0, 0, 0, len(encoded_name), 0)
    entry = b"070701" + b"".join(f"{field:08x}".encode("ascii") for field in fields) + encoded_name
    return entry + bytes((-len(entry)) % 4)


def build_scaffold_cpio(*, include_apex=False):
    """Return the selected fixed root-owned 0755 directory set and newc trailer."""
    names, archive_size, _, archive_sha, _ = _variant(include_apex)
    archive = b"".join(_newc_entry(name, inode, 0o40755, 2)
                       for inode, name in enumerate(names, 1))
    archive += _newc_entry("TRAILER!!!", 0, 0, 1)
    if len(archive) > archive_size:
        raise ScaffoldError("directory archive exceeds its fixed size")
    archive += bytes(archive_size - len(archive))
    if hashlib.sha256(archive).hexdigest() != archive_sha:
        raise ScaffoldError("directory archive differs from the independent byte contract")
    return archive


def build_scaffold_prefix(*, include_apex=False):
    """Return the selected fixed legacy-LZ4 prefix without consulting files/tools."""
    _, archive_size, prefix_size, _, prefix_sha = _variant(include_apex)
    # Token carries 15 literals; extension bytes carry the remaining length.
    remaining = archive_size - 15
    extension = b"\xff" * (remaining // 255) + bytes([remaining % 255])
    block = b"\xf0" + extension + build_scaffold_cpio(include_apex=include_apex)
    prefix = LEGACY_MAGIC + struct.pack("<I", len(block)) + block
    if len(prefix) != prefix_size or hashlib.sha256(prefix).hexdigest() != prefix_sha:
        raise ScaffoldError("legacy-LZ4 prefix differs from the independent byte contract")
    return prefix


def inspect_scaffold_prefix(prefix, *, include_apex=False):
    """Require byte-for-byte identity, including directory metadata and padding."""
    names, archive_size, prefix_size, archive_sha, prefix_sha = _variant(include_apex)
    if type(prefix) is not bytes or prefix != build_scaffold_prefix(include_apex=include_apex):
        raise ScaffoldError("scaffold prefix differs from the exact directory-only contract")
    return {
        "schema_version": 1, "operation": "inspect-twrp-ram-boot-scaffold",
        "include_apex": include_apex,
        "prefix_size_bytes": prefix_size, "prefix_sha256": prefix_sha,
        "cpio_size_bytes": archive_size, "cpio_sha256": archive_sha,
        "compression": {"format": "lz4-legacy", "block_count": 1,
                        "compressed_block_size_bytes": prefix_size - 8, "literal_size_bytes": archive_size,
                        "literal_only": True, "exact_encoding_verified": True},
        "directories": [{"name": name, "inode": inode, "mode": "040755", "uid": 0, "gid": 0,
                         "nlink": 2, "mtime": 0, "size_bytes": 0}
                        for inode, name in enumerate(names, 1)],
        "directory_metadata_verified": True, "trailer_and_padding_verified": True,
        "empty_apex_directory_verified": include_apex, "apex_packages_verified": False, "apex_runtime_verified": False,
        "file_payloads_added": False, "symlinks_added": False,
        "full_kernel_decompression_verified": False, "runtime_mounts_verified": False,
    }
