"""Offline tests for exclusive publication, including the real local syscall."""

import ctypes
import errno
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "artifact_files", Path(__file__).resolve().parents[1] / "scripts" / "artifact_files.py"
)
artifacts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifacts)


class ArtifactPublicationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.staging = self.root / "staging"
        self.staging.mkdir()
        (self.staging / "receipt.json").write_text("{}\n")
        self.destination = self.root / "published"

    def test_real_publication_moves_whole_directory(self):
        inode = self.staging.stat().st_ino
        artifacts.publish_new_directory(self.staging, self.destination)
        self.assertFalse(self.staging.exists())
        self.assertEqual(self.destination.stat().st_ino, inode)
        self.assertEqual((self.destination / "receipt.json").read_text(), "{}\n")

    def test_real_empty_destination_is_not_replaced(self):
        self.destination.mkdir()
        inode = self.destination.stat().st_ino
        with self.assertRaises(FileExistsError):
            artifacts.publish_new_directory(self.staging, self.destination)
        self.assertEqual(self.destination.stat().st_ino, inode)
        self.assertEqual(list(self.destination.iterdir()), [])
        self.assertTrue(self.staging.is_dir())

    def test_real_file_and_dangling_symlink_are_not_replaced(self):
        self.destination.write_text("preserve")
        with self.assertRaises(OSError):
            artifacts.publish_new_directory(self.staging, self.destination)
        self.assertEqual(self.destination.read_text(), "preserve")
        self.destination.unlink()
        self.destination.symlink_to(self.root / "missing")
        with self.assertRaises(OSError):
            artifacts.publish_new_directory(self.staging, self.destination)
        self.assertTrue(self.destination.is_symlink())
        self.assertTrue(self.staging.is_dir())

    def test_macos_uses_rename_excl(self):
        library = mock.Mock()
        library.renamex_np.return_value = 0
        with mock.patch.object(artifacts.sys, "platform", "darwin"), \
                mock.patch.object(artifacts.ctypes, "CDLL", return_value=library) as loader:
            artifacts.publish_new_directory(self.staging, self.destination)
        loader.assert_called_once_with(None, use_errno=True)
        library.renamex_np.assert_called_once_with(os.fsencode(self.staging), os.fsencode(self.destination), 4)
        self.assertEqual(library.renamex_np.argtypes, [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint])
        self.assertIs(library.renamex_np.restype, ctypes.c_int)
        library.renameat2.assert_not_called()

    def test_linux_uses_rename_noreplace(self):
        library = mock.Mock()
        library.renameat2.return_value = 0
        with mock.patch.object(artifacts.sys, "platform", "linux"), \
                mock.patch.object(artifacts.ctypes, "CDLL", return_value=library):
            artifacts.publish_new_directory(self.staging, self.destination)
        library.renameat2.assert_called_once_with(-100, os.fsencode(self.staging),
                                                 -100, os.fsencode(self.destination), 1)
        self.assertEqual(library.renameat2.argtypes, [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                                                     ctypes.c_char_p, ctypes.c_uint])
        self.assertIs(library.renameat2.restype, ctypes.c_int)
        library.renamex_np.assert_not_called()

    def test_unsupported_os_and_missing_syscalls_fail_closed(self):
        with mock.patch.object(artifacts.sys, "platform", "unsupported"), \
                mock.patch.object(artifacts.ctypes, "CDLL") as loader:
            with self.assertRaises(OSError) as error:
                artifacts.publish_new_directory(self.staging, self.destination)
        self.assertEqual(error.exception.errno, errno.ENOTSUP)
        loader.assert_not_called()
        for platform in ("darwin", "linux"):
            with self.subTest(platform=platform), mock.patch.object(artifacts.sys, "platform", platform), \
                    mock.patch.object(artifacts.ctypes, "CDLL", return_value=object()):
                with self.assertRaises(OSError) as error:
                    artifacts.publish_new_directory(self.staging, self.destination)
                self.assertEqual(error.exception.errno, errno.ENOSYS)
        self.assertTrue(self.staging.is_dir())
        self.assertFalse(self.destination.exists())

    def test_filesystem_errors_propagate_without_fallback(self):
        for platform, symbol in (("darwin", "renamex_np"), ("linux", "renameat2")):
            for code in (errno.EEXIST, errno.ENOTSUP, errno.ENOSPC, errno.EXDEV):
                library = mock.Mock()
                getattr(library, symbol).return_value = -1
                with self.subTest(platform=platform, code=code), \
                        mock.patch.object(artifacts.sys, "platform", platform), \
                        mock.patch.object(artifacts.ctypes, "CDLL", return_value=library), \
                        mock.patch.object(artifacts.ctypes, "get_errno", return_value=code), \
                        mock.patch.object(artifacts.os, "rename") as fallback:
                    with self.assertRaises(OSError) as error:
                        artifacts.publish_new_directory(self.staging, self.destination)
                    self.assertEqual(error.exception.errno, code)
                    fallback.assert_not_called()
        self.assertTrue(self.staging.is_dir())
        self.assertFalse(self.destination.exists())


if __name__ == "__main__":
    unittest.main()
