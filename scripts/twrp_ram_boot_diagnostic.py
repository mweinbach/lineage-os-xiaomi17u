"""Produce the exact candidate73 diagnostic prefix without files or native tools.

This is not a directory-only scaffold: it contains nine empty directories and
one init RC file. It never reads or changes the canonical compressed ramdisk.
Byte identity does not establish that init parses the RC, starts its service,
arms its timeout, writes a marker, or reboots. Standard reboot handling can
update the bootloader control block and persisted reboot reason.
"""

from __future__ import annotations

import hashlib
import struct

if __package__:
    from .twrp_ram_boot_scaffold import CONFIG_DIRECTORIES, LEGACY_MAGIC
else:
    from twrp_ram_boot_scaffold import CONFIG_DIRECTORIES, LEGACY_MAGIC


SPEC_SHA256 = "f15d164cc6d35c4d6ebfa607fa241eca9917f9049e3c4d1bdd3df2b4cf11e5ba"
RC_NAME = "init.recovery.usb.rc"
RC_TEXT = (
    'on early-init\n'
    '    write /dev/kmsg "NEZHA_TWRP_DIAG73_EARLY_INIT"\n'
    '    start nezha_diag73\n'
    '\n'
    'service nezha_diag73 /system/bin/sh -c "exec /system/bin/sleep 120"\n'
    '    user shell\n'
    '    group shell\n'
    '    seclabel u:r:shell:s0\n'
    '    disabled\n'
    '    oneshot\n'
    '    timeout_period 45\n'
    '    reboot_on_failure reboot,bootloader\n'
)
RC_BYTES = RC_TEXT.encode("ascii")
RC_SIZE = 301
RC_SHA256 = "3839d84e593441f85b20db92eef38b61cfb603bb0b2c2fbd5a4ba2b34ad6fbf9"
CPIO_SIZE = 2048
PREFIX_SIZE = 2065
CPIO_SHA256 = "415cb2caf6ffa6cce47aea242b1c6978a38c80a9c385b98cd65ea0f644e28d64"
PREFIX_SHA256 = "03bbe3bd0c2bd843e61377868b4c0946534f2fbaf545dca97a252dc6ecf47852"


class DiagnosticError(ValueError):
    """The diagnostic prefix does not match its exact reviewed bytes."""


def _newc_entry(name, inode, mode, nlink, content=b""):
    encoded_name = name.encode("ascii") + b"\0"
    fields = (inode, mode, 0, 0, nlink, 0, len(content), 0, 0, 0, 0, len(encoded_name), 0)
    entry = b"070701" + b"".join(f"{field:08x}".encode("ascii") for field in fields) + encoded_name
    entry += bytes((-len(entry)) % 4)
    return entry + content + bytes((-len(content)) % 4)


def build_diagnostic_cpio():
    """Return nine fixed directories, the exact 301-byte RC, and a newc trailer."""
    if len(RC_BYTES) != RC_SIZE or hashlib.sha256(RC_BYTES).hexdigest() != RC_SHA256:
        raise DiagnosticError("diagnostic RC differs from the reviewed byte contract")
    archive = b"".join(_newc_entry(name, inode, 0o40755, 2)
                       for inode, name in enumerate(CONFIG_DIRECTORIES, 1))
    archive += _newc_entry(RC_NAME, 10, 0o100750, 1, RC_BYTES)
    archive += _newc_entry("TRAILER!!!", 0, 0, 1)
    if len(archive) > CPIO_SIZE:
        raise DiagnosticError("diagnostic archive exceeds its fixed size")
    archive += bytes(CPIO_SIZE - len(archive))
    if hashlib.sha256(archive).hexdigest() != CPIO_SHA256:
        raise DiagnosticError("diagnostic archive differs from the exact byte contract")
    return archive


def build_diagnostic_prefix():
    """Return one fixed literal-only legacy-LZ4 block; no suffix is accepted."""
    remaining = CPIO_SIZE - 15
    extension = b"\xff" * (remaining // 255) + bytes([remaining % 255])
    block = b"\xf0" + extension + build_diagnostic_cpio()
    prefix = LEGACY_MAGIC + struct.pack("<I", len(block)) + block
    if len(prefix) != PREFIX_SIZE or hashlib.sha256(prefix).hexdigest() != PREFIX_SHA256:
        raise DiagnosticError("diagnostic LZ4 prefix differs from the exact byte contract")
    return prefix


def inspect_diagnostic_prefix(prefix):
    """Require every byte, including RC text, metadata, trailer, and padding."""
    if type(prefix) is not bytes or prefix != build_diagnostic_prefix():
        raise DiagnosticError("diagnostic prefix differs from the exact directories-plus-RC contract")
    return {
        "schema_version": 1, "operation": "inspect-twrp-ram-boot-diagnostic",
        "spec_sha256": SPEC_SHA256, "directory_only": False,
        "prefix_size_bytes": PREFIX_SIZE, "prefix_sha256": PREFIX_SHA256,
        "cpio_size_bytes": CPIO_SIZE, "cpio_sha256": CPIO_SHA256,
        "compression": {"format": "lz4-legacy", "block_count": 1,
                        "compressed_block_size_bytes": PREFIX_SIZE - 8,
                        "literal_size_bytes": CPIO_SIZE, "literal_only": True,
                        "exact_encoding_verified": True},
        "directories": [{"name": name, "inode": inode, "mode": "040755", "uid": 0, "gid": 0,
                         "nlink": 2, "mtime": 0, "size_bytes": 0}
                        for inode, name in enumerate(CONFIG_DIRECTORIES, 1)],
        "files": [{"name": RC_NAME, "inode": 10, "mode": "100750", "uid": 0, "gid": 0,
                   "nlink": 1, "mtime": 0, "size_bytes": RC_SIZE, "sha256": RC_SHA256}],
        "service_declaration": {
            "name": "nezha_diag73", "argv": ["/system/bin/sh", "-c", "exec /system/bin/sleep 120"],
            "user": "shell", "group": "shell", "uid": 2000, "gid": 2000,
            "seclabel": "u:r:shell:s0", "disabled": True, "oneshot": True,
            "timeout_period_seconds": 45, "sleep_seconds": 120,
            "reboot_on_failure": "reboot,bootloader",
        },
        "directory_metadata_verified": True, "rc_bytes_and_metadata_verified": True,
        "trailer_and_padding_verified": True, "file_payloads_added": True, "symlinks_added": False,
        "empty_apex_directory_verified": True, "empty_config_directory_verified": True,
        "apex_packages_verified": False, "apex_runtime_verified": False,
        "configfs_mount_verified": False, "usb_runtime_verified": False,
        "runtime_rc_parsing_verified": False, "runtime_service_started_verified": False,
        "runtime_timer_armed_verified": False, "runtime_logging_verified": False,
        "runtime_reboot_verified": False, "runtime_ui_verified": False,
        "security_grants_verified": False, "global_write_free_verified": False,
        "standard_reboot_may_update_bcb_and_reason": True,
        "full_kernel_decompression_verified": False, "runtime_mounts_verified": False,
    }
