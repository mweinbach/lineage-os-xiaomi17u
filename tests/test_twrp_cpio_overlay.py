"""Synthetic newc replacement tests; no extraction, native tools, or devices."""

from contextlib import ExitStack
from pathlib import Path
import stat
import sys
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import twrp_cpio_overlay as overlay


def _entry(name, data=b"", *, mode=stat.S_IFREG | 0o750, nlink=1, uid=0, gid=0):
    raw = name.encode() + b"\0"
    fields = (17, mode, uid, gid, nlink, 1234, len(data), 2, 3, 0, 0, len(raw), 0)
    header = b"070701" + b"".join(f"{v:08x}".encode() for v in fields) + raw
    return header + bytes((-len(header)) % 4) + data + bytes((-len(data)) % 4)


OLD_ONE, OLD_TWO = b"first=old\n", b"second=longer old contents\n"
KEEP = _entry("untouched", b"\x00\xffopaque\x00", mode=stat.S_IFREG | 0o640)
KEEP = KEEP[:110].upper() + KEEP[110:]
TRAILER = _entry("TRAILER!!!", mode=0o755) + bytes(44)


def _archive(one=OLD_ONE, two=OLD_TWO, *, extra=b""):
    return (_entry(".", mode=stat.S_IFDIR | 0o755, nlink=2)
            + _entry("etc", mode=stat.S_IFDIR | 0o755, nlink=2)
            + _entry("./one", one, uid=12, gid=34) + KEEP
            + _entry("etc/two", two, mode=stat.S_IFREG | 0o640)
            + _entry("link", b"one", mode=stat.S_IFLNK | 0o777) + extra + TRAILER)


class CpioOverlayTests(unittest.TestCase):
    def test_two_replacements_preserve_order_metadata_other_frames_and_trailer(self):
        data = _archive()
        changes = {"one": (OLD_ONE, b"first=longer replacement\n"), "./etc/two": (OLD_TWO, b"x\n")}
        result = overlay.replace_files(data, changes)
        self.assertEqual(result, _archive(changes["one"][1], changes["./etc/two"][1]))
        before, _ = overlay._archive(data)
        after, _ = overlay._archive(result)
        self.assertEqual(list(before), list(after))
        for name in before:
            for key in before[name].keys() - {"offset_bytes", "size_bytes"}:
                self.assertEqual(before[name][key], after[name][key], (name, key))
        self.assertIn(KEEP, result)
        self.assertTrue(result.endswith(TRAILER))
        self.assertEqual(data, _archive())

    def test_growth_shrink_empty_and_all_alignment_residues(self):
        for size in (0, 1, 2, 3, 4, 5, 15, 1025):
            with self.subTest(size=size):
                new = b"x" * size
                self.assertEqual(overlay.replace_files(_archive(), {"./one": (OLD_ONE, new)}), _archive(new))

    def test_noop_preserves_even_uppercase_filesize_and_raw_name_bytes(self):
        frame = _entry("./one", OLD_ONE)
        data = frame[:110].upper() + frame[110:] + TRAILER
        self.assertEqual(overlay.replace_files(data, {"one": (OLD_ONE, OLD_ONE)}), data)
        self.assertEqual(overlay.replace_files(data, {}), data)

    def test_wrong_preimage_missing_path_or_normalized_collision_is_rejected(self):
        for changes in ({"one": (b"wrong", b"new")}, {"missing": (OLD_ONE, b"new")},
                        {"one": (OLD_ONE, b"new"), "etc/two": (b"wrong", b"new")},
                        {"one": (OLD_ONE, b"a"), "./one": (OLD_ONE, b"b")},
                        {"TRAILER!!!": (b"old", b"new")}):
            with self.subTest(changes=changes), self.assertRaises(overlay.CpioOverlayError):
                overlay.replace_files(_archive(), changes)

    def test_directory_symlink_and_hardlink_are_not_replacement_files(self):
        cases = ((_archive(), "etc", b"old"), (_archive(), "link", b"one"),
                 (_entry("hard", OLD_ONE, nlink=2) + TRAILER, "hard", OLD_ONE))
        for data, path, old in cases:
            with self.subTest(path=path), self.assertRaisesRegex(overlay.CpioOverlayError, "regular file with nlink=1"):
                overlay.replace_files(data, {path: (old, b"new")})

    def test_types_empty_preimages_and_unsafe_names_are_rejected(self):
        for data in (None, "archive", bytearray(_archive()), memoryview(_archive())):
            with self.assertRaises(overlay.CpioOverlayError): overlay.replace_files(data, {})
        for changes in (None, [], {1: (OLD_ONE, b"new")}, {"one": [OLD_ONE, b"new"]},
                        {"one": (OLD_ONE,)}, {"one": (b"", b"new")}, {"one": ("old", b"new")},
                        {"one": (OLD_ONE, bytearray(b"new"))}):
            with self.assertRaises(overlay.CpioOverlayError): overlay.replace_files(_archive(), changes)
        for path in ("/one", "../one", "././one", "etc//two", "etc/../one", "one\0", "C:one", "\ud800"):
            with self.subTest(path=repr(path)), self.assertRaises(overlay.CpioOverlayError):
                overlay.replace_files(_archive(), {path: (OLD_ONE, b"new")})

    def test_invalid_or_concatenated_archives_are_rejected_before_replacement(self):
        data = _archive()
        for invalid in (b"", b"BADBAD" + data[6:], data[:-1], data + data,
                        _archive(extra=_entry("one", OLD_ONE)), data[:-1] + b"X",
                        _entry("link", b"elsewhere", mode=stat.S_IFLNK | 0o777)
                        + _entry("link/child", b"old") + TRAILER):
            with self.subTest(size=len(invalid)), self.assertRaises(overlay.CpioOverlayError):
                overlay.replace_files(invalid, {"one": (OLD_ONE, b"new")})

    def test_output_size_is_bounded_before_join(self):
        data = _archive()
        with mock.patch.object(overlay, "MAX_ARCHIVE_BYTES", len(data)), self.assertRaisesRegex(overlay.CpioOverlayError, "size bound"):
            overlay.replace_files(data, {"one": (OLD_ONE, OLD_ONE * 10)})

    def test_pure_function_uses_existing_validator_before_and_after(self):
        data, changes = _archive(), {"one": (OLD_ONE, b"changed")}
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "os.system", "subprocess.run", "subprocess.Popen", "socket.socket", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("side effect")))
            validator = stack.enter_context(mock.patch.object(overlay, "_archive", wraps=overlay._archive))
            result = overlay.replace_files(data, changes)
        self.assertEqual(validator.call_args_list, [mock.call(data), mock.call(result)])
        self.assertEqual(result, _archive(b"changed"))
        self.assertEqual(changes, {"one": (OLD_ONE, b"changed")})


if __name__ == "__main__":
    unittest.main()
