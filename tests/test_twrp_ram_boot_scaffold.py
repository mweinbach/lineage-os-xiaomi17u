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


def _archive(entries):
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
    data += bytes((-len(data)) % 1024)
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


if __name__ == "__main__":
    unittest.main()
