"""Offline tests for fastboot TAR extraction; no firmware bytes are committed."""

import gzip
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import firmware_tar as images


class FirmwareTarTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / "artifacts" / "images"

    def package(self, members=None, *, transform=lambda raw: raw, format=tarfile.USTAR_FORMAT):
        data = io.BytesIO()
        with tarfile.open(fileobj=data, mode="w", format=format) as archive:
            for name, content in members or [("nezha/images/boot.img", b"ANDROID!test"),
                                             ("nezha/images/super.img", b"sparse test"),
                                             ("nezha/flash_all.sh", b"do not run"),
                                             ("nezha/images/firmware.elf", b"not extracted")]:
                entry = name if isinstance(name, tarfile.TarInfo) else tarfile.TarInfo(name)
                entry.size = len(content)
                archive.addfile(entry, io.BytesIO(content))
        raw = transform(gzip.compress(data.getvalue()))
        self.sha = hashlib.sha256(raw).hexdigest()
        self.intake = self.root / self.sha
        self.intake.mkdir()
        (self.intake / "firmware.tgz").write_bytes(raw)
        self.metadata = {"schema_version": 2, "filename": "firmware.tgz", "sha256": self.sha,
                         "size_bytes": len(raw), "device": "nezha", "region": "CN",
                         "build": "fixture", "source_kind": "user-provided", "source_url": None,
                         "origin_verified": False}
        (self.intake / "metadata.json").write_text(json.dumps(self.metadata))

    def extract(self, **kwargs):
        return images.extract_images(self.intake, self.output, expected_sha256=self.sha, **kwargs)

    def package_with_tail(self, tail):
        """Put an exact TAR suffix after one complete, extractable member."""
        def replace_tail(encoded):
            raw = gzip.decompress(encoded)
            # One 512-byte USTAR header and one padded four-byte body.
            self.assertEqual(raw[1024:1536], bytes(512))
            return gzip.compress(raw[:1024] + tail)
        self.package([("images/boot.img", b"boot")], transform=replace_tail)

    def assert_bad_header_is_not_published(self):
        before = (self.intake / "firmware.tgz").read_bytes()
        # The wrapper checksum is valid; the error must be in the TAR headers.
        gzip.decompress(before)
        self.assertEqual(hashlib.sha256(before).hexdigest(), self.sha)
        with mock.patch.object(images, "publish_new_directory", wraps=images.publish_new_directory) as publish:
            with self.assertRaisesRegex(images.IntakeError, "invalid or incomplete TAR member header"):
                self.extract()
            publish.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.iterdir()), [])
        self.assertEqual((self.intake / "firmware.tgz").read_bytes(), before)

    def test_extracts_only_images_and_records_gzip_integrity_and_readback(self):
        self.package()
        before = (self.intake / "firmware.tgz").read_bytes()
        receipt = self.extract()
        self.assertEqual(receipt["image_count"], 2)
        self.assertEqual(receipt["member_count"], 4)
        self.assertTrue(receipt["gzip_stream_crc_verified"])
        self.assertTrue(receipt["tar_header_checksums_verified"])
        self.assertFalse(receipt["installers_extracted_or_executed"])
        self.assertFalse(receipt["phone_accessed"])
        self.assertEqual(receipt["intake_provenance"], self.metadata)
        self.assertEqual({p.name for p in self.output.iterdir()}, {"boot.img", "super.img", "receipt.json"})
        self.assertEqual(before, (self.intake / "firmware.tgz").read_bytes())
        for row in receipt["images"]:
            path = self.output / row["path"]
            self.assertEqual(row["sha256"], hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse(path.stat().st_mode & 0o111)
            self.assertTrue(row["readback_verified"])

    def test_supports_direct_images_and_one_leading_dot(self):
        self.package([("./images/boot.img", b"boot")])
        self.assertEqual(self.extract()["images"][0]["archive_member"], "images/boot.img")

    def test_pax_metadata_is_supported_with_bounds(self):
        entry = tarfile.TarInfo("nezha/images/boot.img")
        entry.pax_headers = {"comment": "bounded metadata"}
        self.package([(entry, b"boot")], format=tarfile.PAX_FORMAT)
        self.assertEqual(self.extract()["image_count"], 1)

    def test_gnu_longname_metadata_retains_bounded_header_handling(self):
        name = "n" * 128 + "/images/boot.img"
        self.package([(name, b"boot")], format=tarfile.GNU_FORMAT)
        receipt = self.extract()
        self.assertEqual(receipt["image_count"], 1)
        self.assertEqual(receipt["images"][0]["archive_member"], name)
        self.assertTrue(receipt["tar_header_checksums_verified"])

    def test_rejects_large_pax_header_before_body_parse(self):
        entry = tarfile.TarInfo("nezha/images/boot.img")
        entry.pax_headers = {"comment": "a" * (images.MAX_METADATA_BYTES + 1)}
        self.package([(entry, b"boot")], format=tarfile.PAX_FORMAT)
        with self.assertRaisesRegex(images.IntakeError, "metadata exceeds"):
            self.extract()

    def test_rejects_existing_output_and_retains_lock(self):
        self.package()
        self.output.parent.mkdir()
        lock = self.output.parent / ".images.lock"
        lock.write_text("keep")
        with self.assertRaisesRegex(images.IntakeError, "lock exists"):
            self.extract()
        self.assertEqual(lock.read_text(), "keep")
        self.output.mkdir()
        with self.assertRaisesRegex(images.IntakeError, "already exists"):
            self.extract()

    def test_rejects_hash_mismatch_before_output(self):
        self.package()
        with (self.intake / "firmware.tgz").open("ab") as f:
            f.write(b"modified")
        with self.assertRaisesRegex(images.IntakeError, "SHA256 mismatch"):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_rejects_bad_gzip_crc_even_when_outer_hash_matches(self):
        def corrupt(raw):
            value = bytearray(raw)
            value[-8] ^= 1
            return bytes(value)
        self.package(transform=corrupt)
        with self.assertRaises(gzip.BadGzipFile):
            self.extract()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.iterdir()), [])

    def test_rejects_truncated_gzip(self):
        self.package(transform=lambda raw: raw[:-5])
        with self.assertRaises(EOFError):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_rejects_nonzero_trailer_in_prefetched_tar_buffer(self):
        self.package(transform=lambda raw: gzip.compress(gzip.decompress(raw) + b"unreviewed second archive"))
        with self.assertRaisesRegex(images.IntakeError, "after TAR end marker"):
            self.extract()

    def test_rejects_missing_second_end_block(self):
        self.package([("images/boot.img", b"boot")],
                     transform=lambda raw: gzip.compress(gzip.decompress(raw)[:1536]))
        with self.assertRaisesRegex(images.IntakeError, "second TAR end marker"):
            self.extract()

    def test_rejects_invalid_tar_header_checksum(self):
        def corrupt(raw):
            value = bytearray(gzip.decompress(raw))
            value[0] ^= 1
            return gzip.compress(value)
        self.package(transform=corrupt)
        self.assert_bad_header_is_not_published()

    def test_rejects_late_invalid_header_before_valid_zero_padding(self):
        invalid = bytearray(tarfile.TarInfo("unselected-member").tobuf())
        invalid[148:156] = b"0000000\0"
        self.package_with_tail(bytes(invalid) + bytes(1024))
        self.assert_bad_header_is_not_published()

    def test_rejects_late_numeric_header_error_with_valid_checksum(self):
        invalid = bytearray(tarfile.TarInfo("unselected-member").tobuf())
        invalid[124:136] = b"bad-size!!!!"
        invalid[148:156] = b" " * 8
        checksum = sum(invalid)
        invalid[148:156] = f"{checksum:06o}\0 ".encode()
        self.assertEqual(tarfile.calc_chksums(invalid)[0], checksum)
        self.package_with_tail(bytes(invalid) + bytes(1024))
        self.assert_bad_header_is_not_published()

    def test_rejects_late_truncated_headers_in_valid_gzip(self):
        header = tarfile.TarInfo("truncated-member").tobuf()
        for length in (1, 255, 511):
            with self.subTest(length=length):
                self.package_with_tail(header[:length])
                self.assert_bad_header_is_not_published()

    def test_rejects_eof_without_any_tar_end_marker(self):
        self.package_with_tail(b"")
        self.assert_bad_header_is_not_published()

    def test_accepts_two_zero_end_markers_with_optional_zero_record_padding(self):
        for padding in (0, 8192):
            with self.subTest(padding=padding):
                self.package_with_tail(bytes(1024 + padding))
                output = self.output.parent / ("valid-padding-" + str(padding))
                result = images.extract_images(self.intake, output, expected_sha256=self.sha)
                self.assertEqual((output / "boot.img").read_bytes(), b"boot")
                self.assertEqual(result["decompressed_archive_bytes"], 2048 + padding)
                self.assertTrue(result["gzip_stream_crc_verified"])
                self.assertTrue(result["tar_header_checksums_verified"])

    def test_zero_header_still_has_distinct_end_marker_semantics(self):
        with self.assertRaises(tarfile.EOFHeaderError):
            images.BoundedTarInfo.frombuf(bytes(512), "utf-8", "strict")
        entry = images.BoundedTarInfo.frombuf(tarfile.TarInfo("valid").tobuf(), "utf-8", "strict")
        self.assertIsInstance(entry, images.BoundedTarInfo)
        self.assertEqual(entry.name, "valid")

    def test_cli_cannot_report_success_for_late_invalid_header(self):
        invalid = bytearray(tarfile.TarInfo("unselected-member").tobuf())
        invalid[148:156] = b"0000000\0"
        self.package_with_tail(bytes(invalid) + bytes(1024))
        with mock.patch.object(sys, "stdout", new=io.StringIO()) as stdout:
            with mock.patch.object(sys, "stderr", new=io.StringIO()) as stderr:
                code = images.main(["--intake", str(self.intake), "--output", str(self.output),
                                    "--expected-sha256", self.sha])
        self.assertEqual(code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("invalid or incomplete TAR member header", stderr.getvalue())
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.iterdir()), [])

    def test_rejects_duplicate_case_alias_unsafe_and_multiple_image_roots(self):
        sets = [
            [("images/boot.img", b"a"), ("images/boot.img", b"b")],
            [("images/boot.img", b"a"), ("images/BOOT.img", b"b")],
            [("../installer.sh", b"bad"), ("images/boot.img", b"boot")],
            [("/images/boot.img", b"boot")],
            [("a//images/boot.img", b"boot")],
            [("a/images/boot.img", b"a"), ("b/images/vendor.img", b"b")],
        ]
        for members in sets:
            with self.subTest(members=members):
                self.package(members)
                with self.assertRaises(images.IntakeError):
                    self.extract()
                self.assertFalse(self.output.exists())

    def test_rejects_links_and_special_members_even_if_unselected(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE, tarfile.CHRTYPE, tarfile.BLKTYPE):
            with self.subTest(kind=kind):
                entry = tarfile.TarInfo("unselected")
                entry.type = kind
                entry.linkname = "images/boot.img"
                self.package([(entry, b""), ("images/boot.img", b"boot")])
                with self.assertRaisesRegex(images.IntakeError, "links.*special"):
                    self.extract()

    def test_rejects_empty_image_no_images_limits_and_low_disk(self):
        self.package([("images/boot.img", b"")])
        with self.assertRaisesRegex(images.IntakeError, "empty"):
            self.extract()
        self.package([("flash.sh", b"not extracted")])
        with self.assertRaisesRegex(images.IntakeError, "no supported image"):
            self.extract()
        self.package()
        with self.assertRaisesRegex(images.IntakeError, "extracted image size"):
            self.extract(max_image_bytes=1)
        with self.assertRaisesRegex(images.IntakeError, "archive exceeds"):
            self.extract(max_archive_bytes=100)
        with mock.patch.object(images.shutil, "disk_usage", return_value=mock.Mock(free=0)):
            with self.assertRaisesRegex(images.IntakeError, "insufficient free"):
                self.extract()

    def test_rejects_input_symlink_output_symlink_and_intake_alias(self):
        self.package()
        self.output = self.intake / "new" / "images"
        with self.assertRaisesRegex(images.IntakeError, "outside immutable"):
            self.extract()
        alias = self.root / self.sha.upper()
        if alias.exists() and alias.samefile(self.intake):
            self.output = alias / "new" / "images"
            with self.assertRaisesRegex(images.IntakeError, "outside immutable"):
                self.extract()
        self.output = self.root / "linked" / "images"
        self.output.parent.symlink_to(self.intake, target_is_directory=True)
        with self.assertRaises(images.IntakeError):
            self.extract()
        self.output = self.root / "artifacts" / "images"
        source = self.intake / "firmware.tgz"
        source.rename(self.root / "real.tgz")
        source.symlink_to(self.root / "real.tgz")
        with self.assertRaises(images.IntakeError):
            self.extract()

    def test_publication_race_does_not_replace_existing_directory(self):
        self.package()
        publish = images.publish_new_directory
        def race(staging, target):
            target.mkdir()
            (target / "keep").write_text("keep")
            return publish(staging, target)
        with mock.patch.object(images, "publish_new_directory", side_effect=race):
            with self.assertRaises(FileExistsError):
                self.extract()
        self.assertEqual((self.output / "keep").read_text(), "keep")

    def test_metadata_mutation_rejects_publication(self):
        self.package()
        fsync = images.os.fsync
        def mutate(fd):
            fsync(fd)
            (self.intake / "metadata.json").write_text("{}")
        with mock.patch.object(images.os, "fsync", side_effect=mutate):
            with self.assertRaisesRegex(images.IntakeError, "metadata changed"):
                self.extract()
        self.assertFalse(self.output.exists())

    def test_failure_cleans_staging_without_changing_input(self):
        self.package()
        before = (self.intake / "firmware.tgz").read_bytes()
        with mock.patch.object(images.os, "fsync", side_effect=OSError("disk error")):
            with self.assertRaises(OSError):
                self.extract()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.output.parent.iterdir()), [])
        self.assertEqual((self.intake / "firmware.tgz").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
