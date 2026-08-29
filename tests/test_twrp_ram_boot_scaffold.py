"""Independent synthetic byte checks; no devices, images, native LZ4, or keys."""

from contextlib import ExitStack
import hashlib
from pathlib import Path
import struct
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import twrp_ram_boot_scaffold as scaffold


NAMES = ("debug_ramdisk", "dev", "metadata", "mnt", "proc", "second_stage_resources", "sys")


def _literal_prefix(archive):
    # Independent test encoder, including noncanonical archives for rejection.
    remaining = len(archive) - 15
    extension = bytearray()
    while remaining >= 255:
        extension.append(255)
        remaining -= 255
    extension.append(remaining)
    block = b"\xf0" + bytes(extension) + archive
    return bytes.fromhex("02214c18") + struct.pack("<I", len(block)) + block


def _parse_newc(archive):
    rows, offset = [], 0
    while True:
        if archive[offset:offset + 6] != b"070701" or offset % 4:
            raise AssertionError("invalid synthetic newc framing")
        fields = tuple(int(archive[offset + 6 + 8 * i:offset + 14 + 8 * i], 16) for i in range(13))
        name_start = offset + 110
        name_end = name_start + fields[11]
        if archive[name_end - 1] != 0:
            raise AssertionError("missing filename terminator")
        name = archive[name_start:name_end - 1].decode("ascii")
        data_start = (name_end + 3) // 4 * 4
        if any(archive[name_end:data_start]):
            raise AssertionError("nonzero filename padding")
        data_end = data_start + fields[6]
        next_offset = (data_end + 3) // 4 * 4
        if any(archive[data_end:next_offset]):
            raise AssertionError("nonzero data padding")
        row = {"name": name, "fields": fields, "data": archive[data_start:data_end], "offset": offset}
        offset = next_offset
        if name == "TRAILER!!!":
            return rows, row, archive[offset:]
        rows.append(row)


def _archive(entries, archive_size=None):
    """Independent negative fixture builder; every tuple is (name, mode, data)."""
    data = bytearray()
    rows = [(i, name, mode, body, 2 if mode & 0o170000 == 0o40000 else 1)
            for i, (name, mode, body) in enumerate(entries, 1)]
    rows.append((0, "TRAILER!!!", 0, b"", 1))
    for inode, name, mode, body, nlink in rows:
        fields = (inode, mode, 0, 0, nlink, 0, len(body), 0, 0, 0, 0, len(name) + 1, 0)
        data += b"070701" + b"".join(format(value, "08x").encode() for value in fields) + name.encode() + b"\0"
        data += bytes((-len(data)) % 4)
        data += body
        data += bytes((-len(data)) % 4)
    if archive_size is None:
        data += bytes((-len(data)) % 1024)
    else:
        if len(data) > archive_size:
            raise AssertionError("synthetic archive exceeds selected size")
        data += bytes(archive_size - len(data))
    return bytes(data)


class ScaffoldTests(unittest.TestCase):
    def test_independent_cpio_and_prefix_golden_identities(self):
        cpio = scaffold.build_scaffold_cpio()
        prefix = scaffold.build_scaffold_prefix()
        self.assertEqual(len(cpio), 1024)
        self.assertEqual(hashlib.sha256(cpio).hexdigest(), "027b1045269d9d61baa63b204818977cef7ecdc953ef9265d5d8a9520404cd2e")
        self.assertEqual(len(prefix), 1037)
        self.assertEqual(hashlib.sha256(prefix).hexdigest(), "b06e73b4444e3d31f6ea48e9a65c2a673cf3a58ee70a72f23a3665249d29f40d")
        self.assertEqual(cpio, _archive([(name, 0o40755, b"") for name in NAMES]))
        self.assertEqual(prefix, _literal_prefix(cpio))

    def test_all_thirteen_newc_fields_directory_order_and_trailer_are_exact(self):
        rows, trailer, padding = _parse_newc(scaffold.build_scaffold_cpio())
        self.assertEqual([row["name"] for row in rows], list(NAMES))
        self.assertEqual(list(NAMES), sorted(NAMES))
        for inode, row in enumerate(rows, 1):
            self.assertEqual(row["fields"], (inode, 0o40755, 0, 0, 2, 0, 0, 0, 0, 0, 0, len(row["name"]) + 1, 0))
            self.assertEqual(row["data"], b"")
        self.assertEqual(trailer["fields"], (0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 11, 0))
        self.assertEqual(trailer["data"], b"")
        self.assertEqual(padding, bytes(56))

    def test_literal_block_length_and_consumption_are_exact_without_native_lz4(self):
        prefix = scaffold.build_scaffold_prefix()
        self.assertEqual(prefix[:4], bytes.fromhex("02214c18"))
        self.assertEqual(struct.unpack_from("<I", prefix, 4)[0], 1029)
        self.assertEqual(prefix[8], 0xf0)
        position, length = 9, 15
        while True:
            extension = prefix[position]
            position += 1
            length += extension
            if extension < 255:
                break
        self.assertEqual(prefix[9:position], bytes.fromhex("fffffff4"))
        self.assertEqual(length, 1024)
        self.assertEqual(position + length, len(prefix))
        self.assertEqual(prefix[position:], scaffold.build_scaffold_cpio())

    def test_producer_and_prefix_inspector_are_pure(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "os.system", "subprocess.run", "subprocess.Popen", "socket.socket", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("side effect")))
            first = scaffold.build_scaffold_prefix()
            self.assertEqual(first, scaffold.build_scaffold_prefix())
            report = scaffold.inspect_scaffold_prefix(first)
        self.assertTrue(report["directory_metadata_verified"])
        self.assertEqual([row["name"] for row in report["directories"]], list(NAMES))
        for field in ("file_payloads_added", "symlinks_added", "full_kernel_decompression_verified", "runtime_mounts_verified"):
            self.assertIs(report[field], False)

    def test_invalid_prefix_encoding_lengths_and_mutable_inputs_are_rejected(self):
        prefix = scaffold.build_scaffold_prefix()
        for value in (prefix[:-1], prefix + b"\0", b"", bytearray(prefix), memoryview(prefix)):
            with self.subTest(value_type=type(value)), self.assertRaises(scaffold.ScaffoldError):
                scaffold.inspect_scaffold_prefix(value)
        for offset in (0, 4, 8, 9, 12):
            changed = bytearray(prefix); changed[offset] ^= 1
            with self.subTest(offset=offset), self.assertRaises(scaffold.ScaffoldError):
                scaffold.inspect_scaffold_prefix(bytes(changed))

    def test_changed_directory_metadata_and_padding_are_rejected(self):
        cpio = scaffold.build_scaffold_cpio()
        for field, value in ((0, 0), (1, 0o40777), (1, 0o44755), (2, 1000), (3, 1000), (4, 1),
                             (5, 1), (6, 1), (7, 1), (8, 1), (9, 1), (10, 1), (12, 1)):
            changed = bytearray(cpio)
            changed[6 + field * 8:14 + field * 8] = f"{value:08x}".encode()
            with self.subTest(field=field, value=value), self.assertRaises(scaffold.ScaffoldError):
                scaffold.inspect_scaffold_prefix(_literal_prefix(bytes(changed)))
        changed = cpio[:-1] + b"x"
        with self.assertRaises(scaffold.ScaffoldError): scaffold.inspect_scaffold_prefix(_literal_prefix(changed))

    def test_extra_renamed_reordered_key_executable_or_symlink_members_are_rejected(self):
        original = [(name, 0o40755, b"") for name in NAMES]
        cases = (original + [("extra", 0o40755, b"")], list(reversed(original)),
                 [("changed", 0o40755, b"")] + original[1:],
                 [("adb_keys", 0o100600, b"synthetic-not-a-key")] + original[1:],
                 [("init", 0o100755, b"synthetic-not-executable")] + original[1:],
                 [("debug_ramdisk", 0o120777, b"elsewhere")] + original[1:])
        for entries in cases:
            with self.subTest(first=entries[0]), self.assertRaises(scaffold.ScaffoldError):
                scaffold.inspect_scaffold_prefix(_literal_prefix(_archive(entries)))


class ApexScaffoldTests(unittest.TestCase):
    def test_independent_eight_directory_goldens_preserve_seven_directory_defaults(self):
        old_cpio, old_prefix = scaffold.build_scaffold_cpio(), scaffold.build_scaffold_prefix()
        cpio = scaffold.build_scaffold_cpio(include_apex=True)
        prefix = scaffold.build_scaffold_prefix(include_apex=True)
        self.assertEqual(len(cpio), 1536)
        self.assertEqual(hashlib.sha256(cpio).hexdigest(), "4ea8b5645cc9d2bc0533df35431f45c604b0a76e1dc48efd7ac6f56fe4d18c14")
        self.assertEqual(len(prefix), 1551)
        self.assertEqual(hashlib.sha256(prefix).hexdigest(), "001605f7ab8e588eece60c6fa715e63ad6e9caf4a2da33cd6c90cbfeb9b10d66")
        self.assertEqual(cpio, _archive([(name, 0o40755, b"") for name in ("apex",) + NAMES], 1536))
        self.assertEqual(prefix, _literal_prefix(cpio))
        self.assertEqual(struct.unpack_from("<I", prefix, 4)[0], 1543)
        self.assertEqual(prefix[8:15], b"\xf0" + b"\xff" * 5 + b"\xf6")
        self.assertEqual(prefix[15:], cpio)
        self.assertEqual(old_cpio, scaffold.build_scaffold_cpio())
        self.assertEqual(old_prefix, scaffold.build_scaffold_prefix())
        self.assertEqual(hashlib.sha256(old_prefix).hexdigest(), "b06e73b4444e3d31f6ea48e9a65c2a673cf3a58ee70a72f23a3665249d29f40d")

    def test_all_eight_directory_fields_and_1536_padding_are_exact(self):
        rows, trailer, padding = _parse_newc(scaffold.build_scaffold_cpio(include_apex=True))
        self.assertEqual([row["name"] for row in rows], ["apex", *NAMES])
        for inode, row in enumerate(rows, 1):
            self.assertEqual(row["fields"], (inode, 0o40755, 0, 0, 2, 0, 0, 0, 0, 0, 0, len(row["name"]) + 1, 0))
            self.assertEqual(row["data"], b"")
        self.assertEqual(trailer["offset"], 960)
        self.assertEqual(trailer["fields"], (0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 11, 0))
        self.assertEqual(padding, bytes(452))

    def test_exact_variant_is_explicit_and_reports_no_apex_package_or_runtime_claim(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "os.system", "subprocess.run", "subprocess.Popen", "socket.socket", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("side effect")))
            prefix = scaffold.build_scaffold_prefix(include_apex=True)
            report = scaffold.inspect_scaffold_prefix(prefix, include_apex=True)
        self.assertTrue(report["include_apex"])
        self.assertTrue(report["empty_apex_directory_verified"])
        self.assertFalse(report["apex_packages_verified"])
        self.assertFalse(report["apex_runtime_verified"])
        self.assertFalse(report["runtime_mounts_verified"])
        self.assertFalse(report["full_kernel_decompression_verified"])
        with self.assertRaises(scaffold.ScaffoldError): scaffold.inspect_scaffold_prefix(prefix)
        with self.assertRaises(scaffold.ScaffoldError):
            scaffold.inspect_scaffold_prefix(scaffold.build_scaffold_prefix(), include_apex=True)
        for value in (1, None, "true"):
            with self.subTest(value=value), self.assertRaises(scaffold.ScaffoldError):
                scaffold.build_scaffold_prefix(include_apex=value)

    def test_missing_extra_content_file_or_symlink_apex_is_rejected(self):
        original = [(name, 0o40755, b"") for name in ("apex",) + NAMES]
        for entries in (original[1:], original + [("extra", 0o40755, b"")],
                        [("apex", 0o100755, b"inert contents")] + original[1:],
                        [("apex", 0o120777, b"elsewhere")] + original[1:],
                        [("apex", 0o40777, b"")] + original[1:]):
            prefix = _literal_prefix(_archive(entries, 1536))
            with self.subTest(entries=entries[:1]), self.assertRaises(scaffold.ScaffoldError):
                scaffold.inspect_scaffold_prefix(prefix, include_apex=True)

    def test_apex_owner_mode_and_tail_padding_mutations_are_rejected(self):
        cpio = scaffold.build_scaffold_cpio(include_apex=True)
        for field, value in ((1, 0o44755), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1)):
            changed = bytearray(cpio)
            changed[6 + field * 8:14 + field * 8] = f"{value:08x}".encode()
            with self.subTest(field=field), self.assertRaises(scaffold.ScaffoldError):
                scaffold.inspect_scaffold_prefix(_literal_prefix(bytes(changed)), include_apex=True)
        with self.assertRaises(scaffold.ScaffoldError):
            scaffold.inspect_scaffold_prefix(_literal_prefix(cpio[:-1] + b"x"), include_apex=True)


class ConfigScaffoldTests(unittest.TestCase):
    def test_nine_directory_goldens_preserve_both_older_variants(self):
        older = {value: scaffold.build_scaffold_prefix(include_apex=value) for value in (False, True)}
        cpio = scaffold.build_scaffold_cpio(include_apex=True, include_config=True)
        prefix = scaffold.build_scaffold_prefix(include_apex=True, include_config=True)
        self.assertEqual(len(cpio), 1536)
        self.assertEqual(hashlib.sha256(cpio).hexdigest(), "21053c223bbd43731b7ba898bbe75eb5816e9b254a8a53913e145a78a6f6a5e4")
        self.assertEqual(len(prefix), 1551)
        self.assertEqual(hashlib.sha256(prefix).hexdigest(), "602e50e43fc8b77e5550d7e01c4461339d5b02541065407a013a39d054324d9f")
        self.assertEqual(cpio, _archive([(name, 0o40755, b"") for name in ("apex", "config") + NAMES], 1536))
        self.assertEqual(prefix, _literal_prefix(cpio))
        self.assertEqual(struct.unpack_from("<I", prefix, 4)[0], 1543)
        self.assertEqual(prefix[8:15], b"\xf0" + b"\xff" * 5 + b"\xf6")
        for value, expected in older.items():
            self.assertEqual(expected, scaffold.build_scaffold_prefix(include_apex=value))

    def test_all_nine_directory_fields_and_padding_are_exact(self):
        rows, trailer, padding = _parse_newc(scaffold.build_scaffold_cpio(include_apex=True, include_config=True))
        self.assertEqual([row["name"] for row in rows], ["apex", "config", *NAMES])
        for inode, row in enumerate(rows, 1):
            self.assertEqual(row["fields"], (inode, 0o40755, 0, 0, 2, 0, 0, 0, 0, 0, 0, len(row["name"]) + 1, 0))
            self.assertEqual(row["data"], b"")
        self.assertEqual(trailer["offset"], 1080)
        self.assertEqual(trailer["fields"], (0, 0, 0, 0, 1, 0, 0, 0, 0, 0, 0, 11, 0))
        self.assertEqual(padding, bytes(332))

    def test_config_requires_explicit_apex_and_reports_no_mount_or_usb_success(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "os.system", "subprocess.run", "subprocess.Popen", "socket.socket", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("side effect")))
            prefix = scaffold.build_scaffold_prefix(include_apex=True, include_config=True)
            report = scaffold.inspect_scaffold_prefix(prefix, include_apex=True, include_config=True)
        self.assertTrue(report["empty_config_directory_verified"])
        for key in ("configfs_mount_verified", "usb_runtime_verified", "runtime_mounts_verified", "full_kernel_decompression_verified"):
            self.assertIs(report[key], False)
        with self.assertRaises(scaffold.ScaffoldError): scaffold.build_scaffold_prefix(include_config=True)
        with self.assertRaises(scaffold.ScaffoldError): scaffold.inspect_scaffold_prefix(prefix, include_apex=True)
        with self.assertRaises(scaffold.ScaffoldError):
            scaffold.inspect_scaffold_prefix(scaffold.build_scaffold_prefix(include_apex=True), include_apex=True, include_config=True)
        for value in (1, None, "true"):
            with self.subTest(value=value), self.assertRaises(scaffold.ScaffoldError):
                scaffold.build_scaffold_prefix(include_apex=True, include_config=value)

    def test_missing_extra_file_content_or_symlink_config_is_rejected(self):
        original = [(name, 0o40755, b"") for name in ("apex", "config") + NAMES]
        for entries in (original[:1] + original[2:], original + [("config/usb_gadget", 0o40755, b"")],
                        original[:1] + [("config", 0o100755, b"inert contents")] + original[2:],
                        original[:1] + [("config", 0o120777, b"elsewhere")] + original[2:]):
            prefix = _literal_prefix(_archive(entries, 1536))
            with self.subTest(entries=entries[:2]), self.assertRaises(scaffold.ScaffoldError):
                scaffold.inspect_scaffold_prefix(prefix, include_apex=True, include_config=True)

    def test_config_owner_mode_and_padding_mutations_are_rejected(self):
        cpio = scaffold.build_scaffold_cpio(include_apex=True, include_config=True)
        config_offset = _parse_newc(cpio)[0][1]["offset"]
        for field, value in ((1, 0o40777), (2, 1), (3, 1), (4, 1), (5, 1), (6, 1)):
            changed = bytearray(cpio)
            start = config_offset + 6 + field * 8
            changed[start:start + 8] = f"{value:08x}".encode()
            with self.subTest(field=field), self.assertRaises(scaffold.ScaffoldError):
                scaffold.inspect_scaffold_prefix(_literal_prefix(bytes(changed)), include_apex=True, include_config=True)
        with self.assertRaises(scaffold.ScaffoldError):
            scaffold.inspect_scaffold_prefix(_literal_prefix(cpio[:-1] + b"x"), include_apex=True, include_config=True)


if __name__ == "__main__":
    unittest.main()
