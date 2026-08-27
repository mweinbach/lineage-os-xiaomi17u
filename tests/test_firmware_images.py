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

    def package(self, members=None, *, compression=zipfile.ZIP_DEFLATED):
        data = io.BytesIO()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(data, "w", compression) as archive:
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

    def intake_snapshot(self):
        return {name: ((self.intake / name).read_bytes(),
                       images._signature((self.intake / name).stat()))
                for name in ("firmware.zip", "metadata.json")}

    def assert_failed_extraction_preserves(self, expected_intake):
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.iterdir()), [])
        self.assertEqual({path.name for path in self.intake.iterdir()}, set(expected_intake))
        self.assertEqual(self.intake_snapshot(), expected_intake)

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

    def test_publication_race_preserves_an_existing_empty_directory(self):
        self.package()
        publish = images.publish_new_directory
        inode = []

        def race(staging, destination):
            destination.mkdir()
            inode.append(destination.stat().st_ino)
            publish(staging, destination)

        with mock.patch.object(images, "publish_new_directory", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.extract()
        self.assertEqual(self.output.stat().st_ino, inode[0])
        self.assertEqual(list(self.output.iterdir()), [])

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

    def test_rejects_case_alias_of_intake_on_case_insensitive_filesystem(self):
        self.package()
        alias = self.root / self.sha.upper()
        if not alias.exists() or not alias.samefile(self.intake):
            self.skipTest("filesystem has distinct case-sensitive path identities")
        self.output = alias / "new-parent" / "extracted"
        with self.assertRaisesRegex(images.IntakeError, "outside immutable"):
            self.extract()
        self.assertFalse((self.intake / "new-parent").exists())

    def test_rejects_archive_without_images(self):
        self.package([("install.sh", b"not an image")])
        with self.assertRaisesRegex(images.IntakeError, "no supported image"):
            self.extract()

    def test_rejects_corrupt_zip_crc(self):
        self.package(compression=zipfile.ZIP_STORED)
        package = self.intake / "firmware.zip"
        raw = bytearray(package.read_bytes())
        # Corrupt the second image's stored bytes, leaving its ZIP CRC intact.
        raw[raw.index(b"sparse fixture")] ^= 1
        package.write_bytes(raw)
        # The intake hash describes the corrupted package so extraction reaches
        # actual ZIP reading instead of failing at the outer SHA256 check.
        self.sha = hashlib.sha256(raw).hexdigest()
        renamed = self.root / self.sha
        self.intake.rename(renamed)
        self.intake = renamed
        self.metadata["sha256"] = self.sha
        (self.intake / "metadata.json").write_text(json.dumps(self.metadata))
        before = self.intake_snapshot()
        with self.assertRaisesRegex(zipfile.BadZipFile, "Bad CRC-32.*super.img.0"):
            self.extract()
        self.assert_failed_extraction_preserves(before)

    def test_rejects_metadata_mutation_and_preserves_changed_input(self):
        self.package()
        expected_intake = self.intake_snapshot()
        metadata_path = self.intake / "metadata.json"
        changed_metadata = json.dumps({**self.metadata, "build": "changed-during-extraction"}).encode()
        fsync = images.os.fsync
        mutations = []

        def mutate_after_first_image_write(descriptor):
            fsync(descriptor)
            if not mutations:
                metadata_path.write_bytes(changed_metadata)
                mutations.append(images._signature(metadata_path.stat()))

        with mock.patch.object(images.os, "fsync", side_effect=mutate_after_first_image_write):
            with self.assertRaisesRegex(images.IntakeError, "intake metadata changed during extraction"):
                self.extract()
        self.assertEqual(len(mutations), 1)
        expected_intake["metadata.json"] = (changed_metadata, mutations[0])
        self.assert_failed_extraction_preserves(expected_intake)

    def test_rejects_package_mutation_after_hash_and_preserves_changed_input(self):
        self.package()
        expected_intake = self.intake_snapshot()
        package = self.intake / "firmware.zip"
        image_entries = images._image_entries
        mutations = []

        def mutate_after_package_hash(*args):
            entries = image_entries(*args)
            with package.open("ab") as stream:
                stream.write(b"changed-during-extraction")
            mutations.append(images._signature(package.stat()))
            return entries

        with mock.patch.object(images, "_image_entries", side_effect=mutate_after_package_hash):
            with self.assertRaisesRegex(images.IntakeError, "package changed during extraction"):
                self.extract()
        self.assertEqual(len(mutations), 1)
        expected_intake["firmware.zip"] = (
            expected_intake["firmware.zip"][0] + b"changed-during-extraction", mutations[0],
        )
        self.assert_failed_extraction_preserves(expected_intake)

    def test_rejects_staged_readback_corruption_and_preserves_intake(self):
        self.package()
        before = self.intake_snapshot()
        open_regular = images._open_regular
        corruptions = []

        def corrupt_second_image_before_readback(path):
            if path.name == "super.img.0":
                self.assertEqual(path.parent.parent, self.output.parent)
                self.assertTrue((path.parent / "boot.img").is_file())
                path.write_bytes(b"corrupted staged image")
                corruptions.append(path)
            return open_regular(path)

        with mock.patch.object(images, "_open_regular", side_effect=corrupt_second_image_before_readback):
            with self.assertRaisesRegex(images.IntakeError, "extracted output failed SHA256 readback"):
                self.extract()
        self.assertEqual(len(corruptions), 1)
        self.assertFalse(corruptions[0].exists())
        self.assert_failed_extraction_preserves(before)


if __name__ == "__main__":
    unittest.main()
