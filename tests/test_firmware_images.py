"""Synthetic firmware ZIP tests; never need firmware, a phone or the network."""

import hashlib
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import firmware_images as images


class FirmwareImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / "artifacts" / "images"

    def package(self, members=None):
        data = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
                for name, content in members or [("images/boot.img", b"ANDROID!fixture"),
                                                 ("images/super.img.0", b"sparse fixture"),
                                                 ("install.sh", b"do not run")]:
                    archive.writestr(name, content)
        raw = data.getvalue()
        self.sha = hashlib.sha256(raw).hexdigest()
        self.intake = self.root / self.sha
        self.intake.mkdir()
        (self.intake / "firmware.zip").write_bytes(raw)
        self.metadata = {"schema_version": 2, "filename": "firmware.zip", "sha256": self.sha,
                         "size_bytes": len(raw), "source_kind": "user-provided", "source_url": None,
                         "origin_verified": False, "device": "fixture", "build": "fixture", "region": "CN"}
        (self.intake / "metadata.json").write_text(json.dumps(self.metadata))

    def extract(self, **kwargs):
        return images.extract_images(self.intake, self.output, expected_sha256=self.sha, **kwargs)

    def test_extracts_only_images_with_readback_hashes_and_original_provenance(self):
        self.package()
        before = (self.intake / "firmware.zip").stat()
        result = self.extract()
        self.assertEqual(result["image_count"], 2)
        self.assertEqual(result["intake_provenance"], self.metadata)
        self.assertEqual(result["parent_package_sha256"], self.sha)
        self.assertFalse(result["installers_extracted_or_executed"])
        self.assertFalse(result["phone_accessed"])
        self.assertEqual({p.name for p in self.output.iterdir()}, {"boot.img", "super.img.0", "receipt.json"})
        for record in result["images"]:
            output = self.output / record["path"]
            self.assertEqual(record["sha256"], hashlib.sha256(output.read_bytes()).hexdigest())
            self.assertTrue(record["crc_verified"])
            self.assertFalse(output.stat().st_mode & 0o111)
        self.assertEqual(before.st_mtime_ns, (self.intake / "firmware.zip").stat().st_mtime_ns)
        self.assertEqual(json.loads((self.output / "receipt.json").read_text()), result)

    def test_rejects_existing_output_without_changing_it(self):
        self.package()
        self.output.mkdir(parents=True)
        (self.output / "keep").write_text("keep")
        with self.assertRaisesRegex(images.IntakeError, "already exists"):
            self.extract()
        self.assertEqual((self.output / "keep").read_text(), "keep")

    def test_rejects_wrong_package_hash_before_creating_output(self):
        self.package()
        with (self.intake / "firmware.zip").open("ab") as stream:
            stream.write(b"changed")
        with self.assertRaisesRegex(images.IntakeError, "SHA256 mismatch"):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_rejects_duplicate_case_collision_traversal_and_nested_images(self):
        bad_sets = [
            [("images/boot.img", b"a"), ("images/boot.img", b"b")],
            [("images/boot.img", b"a"), ("images/BOOT.img", b"b")],
            [("images/../boot.img", b"a")],
            [("images/sub/boot.img", b"a")],
            [("images/install.sh", b"a")],
            [("images/boot.img", b"a"), ("../installer.sh", b"b")],
        ]
        for members in bad_sets:
            with self.subTest(members=members):
                self.package(members)
                with self.assertRaises(images.IntakeError):
                    self.extract()
                self.assertFalse(self.output.exists())

    def test_rejects_archive_symlinks_and_special_files(self):
        for mode in (stat.S_IFLNK, stat.S_IFIFO):
            with self.subTest(mode=mode):
                entry = zipfile.ZipInfo("images/boot.img")
                entry.create_system = 3
                entry.external_attr = (mode | 0o777) << 16
                self.package([(entry, b"/outside")])
                with self.assertRaisesRegex(images.IntakeError, "special file"):
                    self.extract()

    def test_rejects_symlink_input_and_output_ancestors(self):
        self.package()
        package = self.intake / "firmware.zip"
        moved = self.root / "real.zip"
        package.rename(moved)
        package.symlink_to(moved)
        with self.assertRaises(images.IntakeError):
            self.extract()
        package.unlink()
        moved.rename(package)
        self.output.parent.symlink_to(self.intake, target_is_directory=True)
        with self.assertRaises(images.IntakeError):
            self.extract()

    def test_rejects_size_limit_and_insufficient_disk(self):
        self.package()
        with self.assertRaisesRegex(images.IntakeError, "exceeds limit"):
            self.extract(max_bytes=1)
        with mock.patch.object(images.shutil, "disk_usage", return_value=mock.Mock(free=0)):
            with self.assertRaisesRegex(images.IntakeError, "insufficient free"):
                self.extract()
        self.assertFalse(self.output.exists())

    def test_failure_does_not_publish_partial_outputs_or_remove_existing_lock(self):
        self.package()
        with mock.patch.object(images.os, "fsync", side_effect=OSError("disk failure")):
            with self.assertRaises(OSError):
                self.extract()
        self.assertEqual(list(self.output.parent.iterdir()), [])
        lock = self.output.parent / ".images.lock"
        lock.write_text("keep")
        with self.assertRaisesRegex(images.IntakeError, "lock exists"):
            self.extract()
        self.assertEqual(lock.read_text(), "keep")

    def test_rejects_wrong_receipt_or_intake_directory_identity(self):
        self.package()
        self.metadata["sha256"] = "0" * 64
        (self.intake / "metadata.json").write_text(json.dumps(self.metadata))
        with self.assertRaisesRegex(images.IntakeError, "match expected SHA256"):
            self.extract()

    def test_rejects_output_inside_intake(self):
        self.package()
        self.output = self.intake / "extracted"
        with self.assertRaisesRegex(images.IntakeError, "outside immutable"):
            self.extract()

    def test_rejects_archive_without_images(self):
        self.package([("install.sh", b"not an image")])
        with self.assertRaisesRegex(images.IntakeError, "no supported image"):
            self.extract()

    def test_rejects_corrupt_zip_crc(self):
        self.package()
        # Force a CRC failure from the stdlib boundary, including cleanup after staging.
        with mock.patch.object(images.zipfile.ZipFile, "open", side_effect=zipfile.BadZipFile("Bad CRC")):
            with self.assertRaises(zipfile.BadZipFile):
                self.extract()
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
