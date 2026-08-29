"""Offline byte-contract tests; no real images, native tools, or init execution."""

from contextlib import ExitStack
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import twrp_ram_boot_diagnostic as diagnostic
import twrp_ram_boot_scaffold as scaffold


NAMES = ("apex", "config", "debug_ramdisk", "dev", "metadata", "mnt", "proc", "second_stage_resources", "sys")
EXPECTED_RC = (
    b'on early-init\n'
    b'    write /dev/kmsg "NEZHA_TWRP_DIAG73_EARLY_INIT"\n'
    b'    start nezha_diag73\n\n'
    b'service nezha_diag73 /system/bin/sh -c "exec /system/bin/sleep 120"\n'
    b'    user shell\n'
    b'    group shell\n'
    b'    seclabel u:r:shell:s0\n'
    b'    disabled\n'
    b'    oneshot\n'
    b'    timeout_period 45\n'
    b'    reboot_on_failure reboot,bootloader\n'
)


def _entries(archive):
    """Independent test decoder retaining all newc fields and exact offsets."""
    result = []
    position = 0
    while position < len(archive):
        start = position
        if archive[start:start + 6] != b"070701" or start + 110 > len(archive):
            raise AssertionError("invalid test archive header")
        fields = tuple(int(archive[start + 6 + 8 * i:start + 14 + 8 * i], 16) for i in range(13))
        name_end = start + 110 + fields[11]
        name = archive[start + 110:name_end]
        if not name.endswith(b"\0") or b"\0" in name[:-1]:
            raise AssertionError("invalid test archive name")
        data_start = (name_end + 3) & ~3
        data_end = data_start + fields[6]
        position = (data_end + 3) & ~3
        if position > len(archive) or any(archive[name_end:data_start]) or any(archive[data_end:position]):
            raise AssertionError("invalid test archive bounds/padding")
        result.append({"name": name[:-1].decode("ascii"), "fields": fields,
                       "content": archive[data_start:data_end], "offset": start, "data_offset": data_start})
        if name == b"TRAILER!!!\0":
            return result, position
    raise AssertionError("missing test archive trailer")


def _literal_prefix(archive):
    """Encode test mutations without using the producer's golden guards."""
    remaining = len(archive) - 15
    extension = bytearray()
    while remaining >= 255:
        extension.append(255)
        remaining -= 255
    extension.append(remaining)
    block = b"\xf0" + bytes(extension) + archive
    return b"\x02\x21\x4c\x18" + struct.pack("<I", len(block)) + block


def _change(data, offset, replacement):
    return data[:offset] + replacement + data[offset + len(replacement):]


class DiagnosticPrefixTests(unittest.TestCase):
    def setUp(self):
        self.archive = diagnostic.build_diagnostic_cpio()
        self.prefix = diagnostic.build_diagnostic_prefix()
        self.entries, self.archive_end = _entries(self.archive)

    def reject_archive(self, archive):
        with self.assertRaises(diagnostic.DiagnosticError):
            diagnostic.inspect_diagnostic_prefix(_literal_prefix(archive))

    def test_exact_rc_and_golden_archive_and_prefix_identities(self):
        self.assertEqual(diagnostic.SPEC_SHA256, "f15d164cc6d35c4d6ebfa607fa241eca9917f9049e3c4d1bdd3df2b4cf11e5ba")
        self.assertEqual(diagnostic.RC_BYTES, EXPECTED_RC)
        for value, size, digest in (
            (diagnostic.RC_BYTES, 301, "3839d84e593441f85b20db92eef38b61cfb603bb0b2c2fbd5a4ba2b34ad6fbf9"),
            (self.archive, 2048, "415cb2caf6ffa6cce47aea242b1c6978a38c80a9c385b98cd65ea0f644e28d64"),
            (self.prefix, 2065, "03bbe3bd0c2bd843e61377868b4c0946534f2fbaf545dca97a252dc6ecf47852"),
        ):
            with self.subTest(size=size):
                self.assertEqual(len(value), size)
                self.assertEqual(hashlib.sha256(value).hexdigest(), digest)

    def test_all_nine_directory_fields_and_only_one_rc_file_are_exact(self):
        self.assertEqual([e["name"] for e in self.entries], [*NAMES, "init.recovery.usb.rc", "TRAILER!!!"])
        for inode, entry in enumerate(self.entries[:9], 1):
            self.assertEqual(entry["fields"], (inode, 0o40755, 0, 0, 2, 0, 0, 0, 0, 0, 0, len(entry["name"]) + 1, 0))
            self.assertEqual(entry["content"], b"")
        rc = self.entries[9]
        self.assertEqual(rc["offset"], 1080)
        self.assertEqual(rc["data_offset"], 1212)
        self.assertEqual(rc["fields"], (10, 0o100750, 0, 0, 1, 0, 301, 0, 0, 0, 0, 21, 0))
        self.assertEqual(rc["content"], EXPECTED_RC)
        self.assertEqual(self.entries[-1]["offset"], 1516)
        self.assertEqual(self.entries[-1]["fields"], (0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 11, 0))
        self.assertEqual(self.archive_end, 1640)
        self.assertEqual(self.archive[self.archive_end:], bytes(408))

    def test_single_literal_block_has_exact_extension_and_no_extra_stream(self):
        self.assertEqual(self.prefix[:4], b"\x02\x21\x4c\x18")
        self.assertEqual(struct.unpack_from("<I", self.prefix, 4)[0], 2057)
        self.assertEqual(self.prefix[8:17], b"\xf0" + b"\xff" * 7 + b"\xf8")
        self.assertEqual(self.prefix[17:], self.archive)
        self.assertEqual(self.prefix, _literal_prefix(self.archive))
        for prefix in (self.prefix[:-1], self.prefix + b"\0", self.prefix + self.prefix,
                       _change(self.prefix, 0, b"BAD!"), _change(self.prefix, 4, struct.pack("<I", 2056)),
                       _change(self.prefix, 8, b"\xf1"), _change(self.prefix, 16, b"\xf7")):
            with self.subTest(size=len(prefix)), self.assertRaises(diagnostic.DiagnosticError):
                diagnostic.inspect_diagnostic_prefix(prefix)

    def test_every_directory_metadata_field_and_name_remains_pinned(self):
        for entry in self.entries[:9]:
            for field in range(13):
                changed = f"{entry['fields'][field] ^ 1:08x}".encode("ascii")
                with self.subTest(name=entry["name"], field=field):
                    self.reject_archive(_change(self.archive, entry["offset"] + 6 + 8 * field, changed))
            self.reject_archive(_change(self.archive, entry["offset"] + 110, b"X"))

    def test_rc_inode_type_mode_ownership_links_time_size_devices_and_name_are_pinned(self):
        rc = self.entries[9]
        for field in range(13):
            with self.subTest(field=field):
                changed = f"{rc['fields'][field] ^ 1:08x}".encode("ascii")
                self.reject_archive(_change(self.archive, rc["offset"] + 6 + 8 * field, changed))
        for mode in (0o100644, 0o100755, 0o104750, 0o120750, 0o40750):
            self.reject_archive(_change(self.archive, rc["offset"] + 14, f"{mode:08x}".encode("ascii")))
        self.reject_archive(_change(self.archive, rc["offset"] + 110, b"X"))

    def test_each_rc_byte_including_service_parameters_and_ending_is_exact(self):
        start = self.entries[9]["data_offset"]
        for offset, value in enumerate(EXPECTED_RC):
            with self.subTest(rc_byte=offset):
                self.reject_archive(_change(self.archive, start + offset, bytes([value ^ 1])))

    def test_missing_extra_key_executable_policy_and_property_entries_are_rejected(self):
        for before, after in (("apex", "nope"), ("config", "keysxx"), ("dev", "bin")):
            self.reject_archive(self.archive.replace(before.encode() + b"\0", after.encode() + b"\0", 1))
        trailer_start = self.entries[-1]["offset"]
        # Insert independently encoded entries before the trailer, including a
        # second RC. Exact rejection must not rely only on LZ4 magic or size.
        for name, mode, data in (("adb_keys", 0o100600, b"synthetic-key"),
                                 ("system/bin/extra", 0o100755, b"synthetic-program"),
                                 ("sepolicy", 0o100644, b"synthetic-policy"),
                                 ("default.prop", 0o100644, b"ro.adb.secure=0\n"),
                                 ("init.recovery.usb.rc", 0o100750, EXPECTED_RC)):
            encoded_name = name.encode() + b"\0"
            fields = (11, mode, 0, 0, 1, 0, len(data), 0, 0, 0, 0, len(encoded_name), 0)
            entry = b"070701" + b"".join(f"{v:08x}".encode() for v in fields) + encoded_name
            entry += bytes((-len(entry)) % 4)
            entry += data + bytes((-len(data)) % 4)
            changed = self.archive[:trailer_start] + entry + self.archive[trailer_start:self.archive_end]
            changed += bytes((-len(changed)) % 2048)
            with self.subTest(name=name): self.reject_archive(changed)

    def test_trailer_alignment_and_archive_padding_cannot_carry_hidden_bytes(self):
        trailer = self.entries[-1]
        for field in range(13):
            changed = f"{trailer['fields'][field] ^ 1:08x}".encode("ascii")
            self.reject_archive(_change(self.archive, trailer["offset"] + 6 + 8 * field, changed))
        for position in (1211, 1513, 1514, 1515, 1639, 1640, 2047):
            with self.subTest(position=position):
                self.assertEqual(self.archive[position], 0)
                self.reject_archive(_change(self.archive, position, b"X"))

    def test_old_directory_only_variants_are_unchanged_and_not_accepted_as_diagnostic(self):
        for options, expected_sha in (
            ({}, "b06e73b4444e3d31f6ea48e9a65c2a673cf3a58ee70a72f23a3665249d29f40d"),
            ({"include_apex": True}, "001605f7ab8e588eece60c6fa715e63ad6e9caf4a2da33cd6c90cbfeb9b10d66"),
            ({"include_apex": True, "include_config": True}, "602e50e43fc8b77e5550d7e01c4461339d5b02541065407a013a39d054324d9f"),
        ):
            prefix = scaffold.build_scaffold_prefix(**options)
            self.assertEqual(hashlib.sha256(prefix).hexdigest(), expected_sha)
            self.assertFalse(scaffold.inspect_scaffold_prefix(prefix, **options)["file_payloads_added"])
            for candidate in (prefix, prefix.ljust(2065, b"\0")):
                with self.assertRaises(diagnostic.DiagnosticError): diagnostic.inspect_diagnostic_prefix(candidate)
            with self.assertRaises(scaffold.ScaffoldError): scaffold.inspect_scaffold_prefix(self.prefix, **options)

    def test_metadata_distinguishes_exact_declarations_from_runtime_and_write_free_claims(self):
        report = diagnostic.inspect_diagnostic_prefix(self.prefix)
        self.assertFalse(report["directory_only"])
        self.assertTrue(report["file_payloads_added"])
        self.assertEqual(len(report["directories"]), 9)
        self.assertEqual(report["files"], [{"name": "init.recovery.usb.rc", "inode": 10, "mode": "100750",
                                          "uid": 0, "gid": 0, "nlink": 1, "mtime": 0, "size_bytes": 301,
                                          "sha256": hashlib.sha256(EXPECTED_RC).hexdigest()}])
        self.assertEqual(report["service_declaration"], {
            "name": "nezha_diag73", "argv": ["/system/bin/sh", "-c", "exec /system/bin/sleep 120"],
            "user": "shell", "group": "shell", "uid": 2000, "gid": 2000, "seclabel": "u:r:shell:s0",
            "disabled": True, "oneshot": True, "timeout_period_seconds": 45, "sleep_seconds": 120,
            "reboot_on_failure": "reboot,bootloader",
        })
        for field in ("runtime_rc_parsing_verified", "runtime_service_started_verified", "runtime_timer_armed_verified",
                      "runtime_logging_verified", "runtime_reboot_verified", "runtime_ui_verified", "security_grants_verified",
                      "global_write_free_verified", "full_kernel_decompression_verified", "runtime_mounts_verified",
                      "apex_packages_verified", "apex_runtime_verified", "configfs_mount_verified", "usb_runtime_verified"):
            self.assertIs(report[field], False, field)
        self.assertTrue(report["standard_reboot_may_update_bcb_and_reason"])

    def test_public_api_is_pure_fixed_and_rejects_mutable_inputs(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "os.system", "subprocess.run", "subprocess.Popen", "socket.socket", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("side effect")))
            self.assertEqual(diagnostic.build_diagnostic_cpio(), self.archive)
            self.assertEqual(diagnostic.build_diagnostic_prefix(), self.prefix)
            self.assertEqual(diagnostic.inspect_diagnostic_prefix(self.prefix), diagnostic.inspect_diagnostic_prefix(self.prefix))
        for value in (None, "prefix", bytearray(self.prefix), memoryview(self.prefix)):
            with self.assertRaises(diagnostic.DiagnosticError): diagnostic.inspect_diagnostic_prefix(value)
        for function in (diagnostic.build_diagnostic_cpio, diagnostic.build_diagnostic_prefix):
            with self.assertRaises(TypeError): function(include_apex=True)
            with self.assertRaises(TypeError): function(b"suffix")


if __name__ == "__main__":
    unittest.main()
