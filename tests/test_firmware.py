"""Offline firmware evidence tests; no network, phones, or third-party modules."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest import mock
import zipfile


from scripts import firmware


class FirmwareIntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "stock package.tgz"
        self.contents = b"firmware fixture\x00" * 11
        self.source.write_bytes(self.contents)
        self.artifacts = self.root / "artifacts" / "firmware"
        self.options = {
            "device": "verified-test-product",
            "build": "verified-test-build",
            "region": "verified-test-region",
            "source_url": "https://example.com/stock-package.tgz",
            "artifacts_dir": self.artifacts,
        }

    def intake(self, **options):
        return firmware.intake_firmware(self.source, **{**self.options, **options})

    def test_preserves_input_and_records_provenance(self):
        before = self.source.stat()
        digest = hashlib.sha256(self.contents).hexdigest()
        result = self.intake(expected_sha256=digest.upper())
        self.assertFalse(result["reused"])
        destination = self.artifacts / digest / self.source.name
        self.assertEqual(result["firmware_path"], str(destination))
        self.assertEqual(destination.read_bytes(), self.contents)
        self.assertEqual(self.source.read_bytes(), self.contents)
        self.assertEqual(self.source.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual(self.source.stat().st_ino, before.st_ino)
        metadata = json.loads((destination.parent / "metadata.json").read_text())
        self.assertEqual(metadata, result["metadata"])
        self.assertEqual(metadata["sha256"], digest)
        self.assertEqual(metadata["size_bytes"], len(self.contents))
        for field in ("device", "build", "region", "source_url"):
            self.assertEqual(metadata[field], self.options[field])
        self.assertEqual(list(self.artifacts.iterdir()), [destination.parent])

    def test_repeat_verifies_without_recopying_or_changing_metadata(self):
        first = self.intake()
        destination = Path(first["firmware_path"])
        inode = destination.stat().st_ino
        metadata_bytes = Path(first["metadata_path"]).read_bytes()
        with mock.patch.object(firmware.tempfile, "mkdtemp", side_effect=AssertionError("copied twice")):
            second = self.intake()
        self.assertTrue(second["reused"])
        self.assertEqual(second["metadata"], first["metadata"])
        self.assertEqual(Path(second["metadata_path"]).read_bytes(), metadata_bytes)
        self.assertEqual(destination.stat().st_ino, inode)

    def test_publication_race_does_not_replace_an_existing_empty_directory(self):
        publish = firmware.publish_new_directory
        created = []

        def race(staging, destination):
            destination.mkdir()
            created.append((destination, destination.stat().st_ino))
            publish(staging, destination)

        with mock.patch.object(firmware, "publish_new_directory", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.intake()
        destination, inode = created[0]
        self.assertEqual(destination.stat().st_ino, inode)
        self.assertEqual(list(destination.iterdir()), [])

    def test_checksum_mismatch_does_not_create_artifacts(self):
        with self.assertRaisesRegex(firmware.IntakeError, "SHA256 mismatch"):
            self.intake(expected_sha256="0" * 64)
        self.assertFalse(self.artifacts.exists())
        self.assertEqual(self.source.read_bytes(), self.contents)

    def test_invalid_checksum_rejected(self):
        for digest in ("", "0" * 63, "g" * 64, "0" * 65, " " + "0" * 64):
            with self.subTest(digest=digest), self.assertRaises(firmware.IntakeError):
                self.intake(expected_sha256=digest)
        self.assertFalse(self.artifacts.exists())

    def test_corrupt_existing_copy_is_not_silently_repaired(self):
        first = self.intake()
        destination = Path(first["firmware_path"])
        metadata = Path(first["metadata_path"]).read_bytes()
        destination.write_bytes(b"X" * len(self.contents))
        with self.assertRaisesRegex(firmware.IntakeError, "integrity"):
            self.intake()
        self.assertEqual(destination.read_bytes(), b"X" * len(self.contents))
        self.assertEqual(Path(first["metadata_path"]).read_bytes(), metadata)
        self.assertEqual(self.source.read_bytes(), self.contents)

    def test_conflicting_provenance_is_not_overwritten(self):
        first = self.intake()
        metadata = Path(first["metadata_path"]).read_bytes()
        for field, value in (
            ("device", "different-device"),
            ("build", "different-build"),
            ("region", "different-region"),
            ("source_url", "https://example.com/different-package.tgz"),
        ):
            with self.subTest(field=field), self.assertRaisesRegex(firmware.IntakeError, "conflicts"):
                self.intake(**{field: value})
        self.assertEqual(Path(first["metadata_path"]).read_bytes(), metadata)

    def test_same_contents_with_different_name_do_not_create_a_second_copy(self):
        first = self.intake()
        alternate = self.root / "renamed.tgz"
        alternate.write_bytes(self.contents)
        with self.assertRaisesRegex(firmware.IntakeError, "filename"):
            firmware.intake_firmware(alternate, **self.options)
        self.assertEqual(len(list(Path(first["firmware_path"]).parent.iterdir())), 2)

    def test_invalid_existing_metadata_is_preserved(self):
        result = self.intake()
        path = Path(result["metadata_path"])
        for content in ("not json", "[]", "{}", "x" * (firmware.MAX_METADATA_BYTES + 1)):
            path.write_text(content)
            with self.subTest(content=content[:20]), self.assertRaises(firmware.IntakeError):
                self.intake()
            self.assertEqual(path.read_text(), content)

    def test_existing_metadata_requires_exact_types_and_utc_timestamp(self):
        result = self.intake()
        path = Path(result["metadata_path"])
        for field, value in (
            ("schema_version", True),
            ("size_bytes", float(len(self.contents))),
            ("collected_at_utc", "2026-01-01T00:00:00"),
            ("collected_at_utc", "2026-01-01T00:00:00+01:00"),
            ("collected_at_utc", 7),
        ):
            path.write_text(json.dumps({**result["metadata"], field: value}))
            with self.subTest(field=field, value=value), self.assertRaises(firmware.IntakeError):
                self.intake()

    def test_metadata_validation_happens_before_copy(self):
        for field in ("device", "build", "region"):
            for value in ("", " ", " value", "value ", "a\nb", "a\x00b"):
                with self.subTest(field=field, value=value), self.assertRaises(firmware.IntakeError):
                    self.intake(**{field: value})
        self.assertFalse(self.artifacts.exists())

    def test_source_url_validation(self):
        for url in (
            "http://example.com/file.tgz",
            "file:///tmp/stock.tgz",
            "https:///file.tgz",
            "https://user:password@example.com/file.tgz",
            "https://example.com/file.tgz#secret",
            "https://example.com:999999/file.tgz",
            "https://example.com:0/file.tgz",
            "https://example.com/a b.tgz",
            "https://example.com\\evil/file.tgz",
        ):
            with self.subTest(url=url), self.assertRaises(firmware.IntakeError):
                self.intake(source_url=url)
        self.assertFalse(self.artifacts.exists())

    def test_unsafe_filenames_are_rejected(self):
        for filename in ("metadata.json", "Metadata.JSON", "bad\\name.tgz", "line\nbreak.tgz", "name."):
            source = self.root / filename
            source.write_bytes(self.contents)
            with self.subTest(filename=filename), self.assertRaises(firmware.IntakeError):
                firmware.intake_firmware(source, **self.options)
        self.assertFalse(self.artifacts.exists())

    def test_empty_package_and_directory_are_rejected(self):
        self.source.write_bytes(b"")
        with self.assertRaisesRegex(firmware.IntakeError, "empty"):
            self.intake()
        with self.assertRaisesRegex(firmware.IntakeError, "regular"):
            firmware.intake_firmware(self.root, **self.options)

    def test_input_symlink_is_rejected(self):
        source = self.root / "link.tgz"
        source.symlink_to(self.source)
        with self.assertRaisesRegex(firmware.IntakeError, "regular"):
            firmware.intake_firmware(source, **self.options)
        self.assertEqual(self.source.read_bytes(), self.contents)

    def test_output_symlink_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.artifacts.parent.mkdir()
        self.artifacts.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(firmware.IntakeError, "symlink"):
            self.intake()
        self.assertEqual(list(outside.iterdir()), [])

    def test_output_ancestor_symlink_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.artifacts.parent.symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(firmware.IntakeError, "symlink"):
            self.intake()
        self.assertEqual(list(outside.iterdir()), [])

    def test_checksum_directory_symlink_is_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        self.artifacts.mkdir(parents=True)
        digest = hashlib.sha256(self.contents).hexdigest()
        (self.artifacts / digest).symlink_to(outside, target_is_directory=True)
        with self.assertRaisesRegex(firmware.IntakeError, "symlink"):
            self.intake()
        self.assertEqual(list(outside.iterdir()), [])

    def test_stored_file_and_metadata_symlinks_are_rejected(self):
        result = self.intake()
        for key in ("firmware_path", "metadata_path"):
            path = Path(result[key])
            original = path.read_bytes()
            path.unlink()
            path.symlink_to(self.source)
            with self.subTest(key=key), self.assertRaisesRegex(firmware.IntakeError, "regular"):
                self.intake()
            path.unlink()
            path.write_bytes(original)
        self.assertEqual(self.source.read_bytes(), self.contents)

    def test_streaming_checksum_and_copy(self):
        self.source.write_bytes(b"A" * (firmware.CHUNK_SIZE * 2 + 17))
        result = self.intake()
        self.assertEqual(result["metadata"]["sha256"], hashlib.sha256(self.source.read_bytes()).hexdigest())
        self.assertEqual(Path(result["firmware_path"]).read_bytes(), self.source.read_bytes())

    def test_source_change_between_hash_and_copy_is_rejected(self):
        original = firmware._hash_file

        def changing_hash(path, output=None):
            if output is not None:
                self.source.write_bytes(b"changed contents")
            return original(path, output)

        with mock.patch.object(firmware, "_hash_file", side_effect=changing_hash):
            with self.assertRaisesRegex(firmware.IntakeError, "changed between"):
                self.intake()
        self.assertEqual(list(self.artifacts.iterdir()), [])

    def test_failed_copy_does_not_leave_partial_package(self):
        original = firmware._hash_file

        def fail_copy(path, output=None):
            if output is not None:
                output.write(b"partial")
                raise OSError("simulated full disk")
            return original(path, output)

        with mock.patch.object(firmware, "_hash_file", side_effect=fail_copy):
            with self.assertRaisesRegex(OSError, "full disk"):
                self.intake()
        self.assertEqual(list(self.artifacts.iterdir()), [])
        self.assertEqual(self.source.read_bytes(), self.contents)

    def test_existing_lock_is_preserved(self):
        self.artifacts.mkdir(parents=True)
        digest = hashlib.sha256(self.contents).hexdigest()
        lock = self.artifacts / f".{digest}.lock"
        lock.write_text("pid=12345\n")
        with self.assertRaisesRegex(firmware.IntakeError, "lock already exists"):
            self.intake()
        self.assertEqual(lock.read_text(), "pid=12345\n")
        self.assertEqual(list(self.artifacts.iterdir()), [lock])

    def test_corrupted_temporary_copy_is_not_published(self):
        original = firmware._hash_file

        def corrupt_copy(path, output=None):
            result = original(path, output)
            if output is not None:
                output.seek(0)
                output.write(b"corruption")
            return result

        with mock.patch.object(firmware, "_hash_file", side_effect=corrupt_copy):
            with self.assertRaisesRegex(firmware.IntakeError, "temporary firmware copy failed integrity"):
                self.intake()
        self.assertEqual(list(self.artifacts.iterdir()), [])
        self.assertEqual(self.source.read_bytes(), self.contents)

    def test_zip_inventory_never_extracts_or_executes(self):
        with zipfile.ZipFile(self.source, "w") as archive:
            archive.writestr("images/boot.img", b"boot image")
            archive.writestr("flash_all.sh", b"touch SHOULD_NOT_EXIST")
            archive.writestr("../escaped.txt", b"unsafe")
            archive.writestr("/absolute.txt", b"unsafe")
            archive.writestr("C:\\escape.txt", b"unsafe")
            symlink = zipfile.ZipInfo("images/link")
            symlink.create_system = 3
            symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(symlink, "../../outside")
        result = self.intake(inspect=True)
        inventory = result["archive"]
        self.assertEqual(inventory["format"], "zip")
        self.assertEqual(inventory["member_count"], 6)
        self.assertEqual([entry["unsafe_path"] for entry in inventory["members"]], [False, False, True, True, True, False])
        self.assertEqual(inventory["members"][-1]["kind"], "symlink")
        self.assertFalse((self.root / "escaped.txt").exists())
        self.assertFalse((self.root / "SHOULD_NOT_EXIST").exists())
        self.assertEqual(len(list(Path(result["firmware_path"]).parent.iterdir())), 2)

    def test_tar_gzip_inventory_never_extracts(self):
        with tarfile.open(self.source, "w:gz") as archive:
            entry = tarfile.TarInfo("images/vendor.img")
            entry.size = 6
            archive.addfile(entry, io.BytesIO(b"vendor"))
            entry = tarfile.TarInfo("../escape")
            entry.size = 1
            archive.addfile(entry, io.BytesIO(b"x"))
            entry = tarfile.TarInfo("images/link")
            entry.type = tarfile.SYMTYPE
            entry.linkname = "../../outside"
            archive.addfile(entry)
        result = self.intake(inspect=True)
        inventory = result["archive"]
        self.assertEqual(inventory["format"], "tar")
        self.assertEqual(inventory["member_count"], 3)
        self.assertTrue(inventory["members"][1]["unsafe_path"])
        self.assertTrue(inventory["members"][2]["unsafe_link_target"])
        self.assertFalse((self.root / "escape").exists())
        self.assertFalse((self.root / "images").exists())

    def test_inventory_limit_is_enforced(self):
        with zipfile.ZipFile(self.source, "w") as archive:
            archive.writestr("one", b"1")
            archive.writestr("two", b"2")
        with mock.patch.object(firmware, "MAX_ARCHIVE_MEMBERS", 1):
            with self.assertRaisesRegex(firmware.IntakeError, "exceeds"):
                self.intake(inspect=True)

    def test_inspection_can_be_requested_on_a_later_repeat(self):
        with zipfile.ZipFile(self.source, "w") as archive:
            archive.writestr("payload.bin", b"fixture")
        first = self.intake()
        second = self.intake(inspect=True)
        self.assertTrue(second["reused"])
        self.assertEqual(second["archive"]["members"][0]["name"], "payload.bin")
        self.assertEqual(first["metadata"], second["metadata"])

    def test_unsupported_inspection_returns_error(self):
        with self.assertRaisesRegex(firmware.IntakeError, "ZIP or TAR"):
            self.intake(inspect=True)

    def test_cli_success_prints_json(self):
        intake = firmware.intake_firmware

        def with_temp_output(*args, **kwargs):
            return intake(*args, **kwargs, artifacts_dir=self.artifacts)

        output = io.StringIO()
        with mock.patch.object(firmware, "intake_firmware", side_effect=with_temp_output):
            with contextlib.redirect_stdout(output):
                code = firmware.main([
                    str(self.source), "--device", "test-product", "--build", "test-build",
                    "--region", "test-region", "--source-url", "https://example.com/package.tgz",
                ])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(output.getvalue())["metadata"]["device"], "test-product")

    def test_cli_checksum_error_is_nonzero(self):
        stderr = io.StringIO()
        stdout = io.StringIO()
        with contextlib.redirect_stderr(stderr), contextlib.redirect_stdout(stdout):
            code = firmware.main([
                str(self.source), "--device", "test-product", "--build", "test-build",
                "--region", "test-region", "--source-url", "https://example.com/package.tgz",
                "--expected-sha256", "0" * 64,
            ])
        self.assertEqual(code, 1)
        self.assertIn("SHA256 mismatch", stderr.getvalue())
        self.assertEqual(stdout.getvalue(), "")
        self.assertFalse(self.artifacts.exists())

    def test_default_url_mode_preserves_legacy_metadata_schema(self):
        first = self.intake()
        self.assertEqual(first["metadata"]["schema_version"], 1)
        self.assertNotIn("source_kind", first["metadata"])
        self.assertNotIn("origin_verified", first["metadata"])
        self.assertEqual(set(first["metadata"]), {
            "schema_version", "filename", "device", "build", "region", "source_url",
            "sha256", "size_bytes", "collected_at_utc",
        })
        second = self.intake(source_kind="url")
        self.assertTrue(second["reused"])
        self.assertEqual(second["metadata"], first["metadata"])

    def test_unknown_origin_requires_explicit_user_provided_mode(self):
        for source_kind in ("url",):
            with self.subTest(source_kind=source_kind), self.assertRaisesRegex(firmware.IntakeError, "explicitly user-provided"):
                self.intake(source_url=None, source_kind=source_kind)
        self.assertFalse(self.artifacts.exists())

    def test_user_provided_package_records_unknown_origin_truthfully(self):
        first = self.intake(source_kind="user-provided", source_url=None)
        metadata = first["metadata"]
        self.assertEqual(metadata["schema_version"], 2)
        self.assertEqual(metadata["source_kind"], "user-provided")
        self.assertIsNone(metadata["source_url"])
        self.assertIs(metadata["origin_verified"], False)
        self.assertEqual(Path(first["firmware_path"]).read_bytes(), self.contents)
        second = self.intake(source_kind="user-provided", source_url=None)
        self.assertTrue(second["reused"])
        self.assertEqual(second["metadata"], metadata)

    def test_user_provided_mode_does_not_verify_optional_url(self):
        result = self.intake(source_kind="user-provided")
        self.assertEqual(result["metadata"]["source_url"], self.options["source_url"])
        self.assertIs(result["metadata"]["origin_verified"], False)

    def test_user_provided_optional_url_still_requires_safe_https(self):
        for url in ("", "file:///tmp/firmware.zip", "http://example.com/firmware.zip", "https://user:secret@example.com/file.zip"):
            with self.subTest(url=url), self.assertRaises(firmware.IntakeError):
                self.intake(source_kind="user-provided", source_url=url)
        self.assertFalse(self.artifacts.exists())

    def test_provenance_mode_cannot_relabel_an_existing_package(self):
        first = self.intake(source_kind="user-provided", source_url=None)
        path = Path(first["metadata_path"])
        before = path.read_bytes()
        with self.assertRaises(firmware.IntakeError):
            self.intake()
        self.assertEqual(path.read_bytes(), before)

    def test_later_url_cannot_silently_replace_unknown_origin(self):
        first = self.intake(source_kind="user-provided", source_url=None)
        before = Path(first["metadata_path"]).read_bytes()
        with self.assertRaisesRegex(firmware.IntakeError, "source_url"):
            self.intake(source_kind="user-provided")
        self.assertEqual(Path(first["metadata_path"]).read_bytes(), before)

    def test_origin_verification_cannot_be_falsely_set_in_existing_metadata(self):
        result = self.intake(source_kind="user-provided", source_url=None)
        path = Path(result["metadata_path"])
        metadata = {**result["metadata"], "origin_verified": True}
        path.write_text(json.dumps(metadata))
        with self.assertRaisesRegex(firmware.IntakeError, "origin_verified"):
            self.intake(source_kind="user-provided", source_url=None)
        self.assertEqual(json.loads(path.read_text()), metadata)

    def test_unsupported_provenance_kinds_are_rejected(self):
        for source_kind in ("", "official", "downloaded", None):
            with self.subTest(source_kind=source_kind), self.assertRaisesRegex(firmware.IntakeError, "source kind"):
                self.intake(source_kind=source_kind)
        self.assertFalse(self.artifacts.exists())

    def test_cli_still_requires_source_url_by_default(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit) as result:
            firmware.main([
                str(self.source), "--device", "test-product", "--build", "test-build", "--region", "test-region",
            ])
        self.assertEqual(result.exception.code, 2)
        self.assertIn("--source-url is required", stderr.getvalue())
        self.assertFalse(self.artifacts.exists())

    def test_cli_user_provided_does_not_need_or_invent_a_url(self):
        intake = firmware.intake_firmware

        def with_temp_output(*args, **kwargs):
            return intake(*args, **kwargs, artifacts_dir=self.artifacts)

        stdout = io.StringIO()
        with mock.patch.object(firmware, "intake_firmware", side_effect=with_temp_output):
            with contextlib.redirect_stdout(stdout):
                code = firmware.main([
                    str(self.source), "--device", "test-product", "--build", "test-build",
                    "--region", "test-region", "--source-kind", "user-provided",
                ])
        self.assertEqual(code, 0)
        metadata = json.loads(stdout.getvalue())["metadata"]
        self.assertEqual(metadata["source_kind"], "user-provided")
        self.assertIsNone(metadata["source_url"])
        self.assertIs(metadata["origin_verified"], False)


if __name__ == "__main__":
    unittest.main()
