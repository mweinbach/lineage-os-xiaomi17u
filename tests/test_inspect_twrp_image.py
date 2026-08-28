"""Offline synthetic tests; no proprietary images, phone, or external tools."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import inspect_twrp_image as inspector


def _pad(data, alignment=4096):
    return data + bytes((-len(data)) % alignment)


def _legacy():
    # One real LZ4 literal sequence, not a recovery CPIO or executable.
    block = b"\x50hello"
    return b"\x02\x21\x4c\x18" + struct.pack("<I", len(block)) + block


def _frame():
    # Standard 64 KiB independent frame containing one uncompressed block.
    return b"\x04\x22\x4d\x18\x60\x40\x82" + struct.pack("<I", 0x80000005) + b"hello" + bytes(4)


def _image(ramdisk=None, signature=b""):
    ramdisk = _legacy() if ramdisk is None else ramdisk
    header = bytearray(4096)
    struct.pack_into("<8s9I", header, 0, b"ANDROID!", 0, len(ramdisk), 0, 1584, 0, 0, 0, 0, 4)
    struct.pack_into("<I", header, 1580, len(signature))
    return bytes(header) + _pad(ramdisk) + _pad(signature)


def _u32(data, offset, value):
    result = bytearray(data)
    struct.pack_into("<I", result, offset, value)
    return bytes(result)


def _be64(data, offset, value):
    result = bytearray(data)
    struct.pack_into(">Q", result, offset, value)
    return bytes(result)


def _vbmeta(descriptors=None, *, flags=0):
    # Deliberately synthetic key/signature bytes; only their ranges are valid.
    if descriptors is None:
        descriptors = struct.pack(">QQ", 99, 8) + b"inert123"
    authentication = _pad(b"h" * 32 + b"s" * 64, 64)
    auxiliary = _pad(descriptors + b"fake-key" + b"metadata", 64)
    header = bytearray(256)
    struct.pack_into(">4sIIQQI", header, 0, b"AVB0", 1, 0, len(authentication), len(auxiliary), 1)
    struct.pack_into(">10Q", header, 32, 0, 32, 32, 64, len(descriptors), 8,
                     len(descriptors) + 8, 8, 0, len(descriptors))
    struct.pack_into(">QII", header, 112, 1, flags, 1)
    header[128:138] = b"synthetic\0"
    return bytes(header) + authentication + auxiliary


def _with_avb(image=None, vbmeta=None):
    image = _image() if image is None else image
    vbmeta = _vbmeta() if vbmeta is None else vbmeta
    size = (len(image) + len(vbmeta) + 64 + 4095) // 4096 * 4096
    footer = struct.pack(">4sIIQQQ28s", b"AVBf", 1, 0, len(image), len(image), len(vbmeta), bytes(28))
    return image + vbmeta + bytes(size - len(image) - len(vbmeta) - len(footer)) + footer


class ImageFixture(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.image = self.root / "recovery.img"

    def inspect(self, data):
        self.image.write_bytes(data)
        return inspector.inspect_image(self.image)

    def reject(self, data, message):
        with self.assertRaisesRegex(inspector.ImageInspectionError, message):
            self.inspect(data)


class RecoveryEnvelopeTests(ImageFixture):
    def test_legacy_image_hashes_and_boundaries_are_explicit(self):
        data = _image()
        report = self.inspect(data)
        self.assertEqual(report["image"]["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(report["image"]["size_bytes"], 8192)
        self.assertEqual(report["image"]["name"], "recovery.img")
        self.assertEqual(report["ramdisk"]["sha256"], hashlib.sha256(_legacy()).hexdigest())
        self.assertEqual(report["ramdisk"]["offset_bytes"], 4096)
        self.assertEqual(report["ramdisk"]["compression"]["format"], "lz4-legacy")
        self.assertEqual(report["header"]["version"], 4)
        self.assertEqual(report["header"]["size_bytes"], 1584)
        self.assertEqual(report["header"]["page_size_bytes"], 4096)
        self.assertEqual(report["header"]["kernel_size_bytes"], 0)
        self.assertTrue(report["validation"]["structurally_valid"])
        for name in ("boot_tested", "avb_trusted", "flash_admitted", "phone_accessed",
                     "image_mutated", "ramdisk_decompressed", "twrp_contents_verified",
                     "compiled_selinux_policy_verified", "device_compatibility_verified",
                     "rollback_compatibility_verified"):
            self.assertIs(report["validation"][name], False, name)
        self.assertFalse(report["avb"]["footer_present"])
        self.assertFalse(report["avb"]["vbmeta_parsed"])
        self.assertEqual(self.image.read_bytes(), data)

    def test_capacity_bound_matches_factory_record_not_live_measurement(self):
        record = json.loads((ROOT / "research/recovery-plan.json").read_text())
        package_gpt = record["stock"]["package_gpt_contract"]
        report = self.inspect(_image())
        self.assertEqual(inspector.MAX_IMAGE_BYTES, 104857600)
        self.assertEqual(inspector.MAX_IMAGE_BYTES, package_gpt["partition_size_bytes_per_slot"]["recovery"])
        self.assertFalse(report["contract"]["physical_phone_capacity_verified"])
        boot_record = json.loads((ROOT / "research/factory-boot-contract.json").read_text())
        stock_header = boot_record["header_component_readback"]["headers"]["recovery"]
        self.assertEqual(report["header"]["version"], stock_header["header_version"])
        self.assertEqual(report["header"]["kernel_size_bytes"], stock_header["kernel_size_bytes"])

    def test_framed_lz4_and_optional_signature_ranges(self):
        report = self.inspect(_image(_frame(), signature=b"synthetic-signature"))
        self.assertEqual(report["ramdisk"]["compression"]["format"], "lz4-frame")
        self.assertEqual(report["header"]["boot_signature_offset_bytes"], 8192)
        self.assertEqual(report["header"]["boot_signature_size_bytes"], 19)
        self.assertFalse(report["header"]["boot_signature_verified"])
        self.assertFalse(report["ramdisk"]["compression"]["checksums_verified"])
        self.assertFalse(report["ramdisk"]["compression"]["compressed_blocks_decoded"])

    def test_rejects_wrong_magic_and_vendor_boot(self):
        self.reject(b"VNDRBOOT" + _image()[8:], "vendor_boot")
        self.reject(b"NOTBOOT!" + _image()[8:], "magic")

    def test_rejects_kernel_containing_boot_image(self):
        self.reject(_u32(_image(), 8, 64), "must not contain a kernel")

    def test_rejects_wrong_header_version_and_size(self):
        for offset, values in ((40, (0, 1, 2, 3, 5, 0xFFFFFFFF)),
                               (20, (0, 44, 1580, 4096, 0xFFFFFFFF))):
            for value in values:
                with self.subTest(offset=offset, value=value):
                    self.reject(_u32(_image(), offset, value), "header v4")

    def test_rejects_truncation_and_declared_ranges_outside_image(self):
        for data in (_image()[:1500], _image()[:4096], _image()[:-1],
                     _u32(_image(), 12, 0xFFFFFFFF), _u32(_image(), 1580, 4096),
                     _u32(_image(), 1580, 0xFFFFFFFF)):
            with self.subTest(size=len(data)):
                self.reject(data, "bounds|truncated|page-aligned")
        self.reject(_u32(_image(), 12, 0), "ramdisk is empty")

    def test_rejects_nonzero_reserved_padding_and_trailer_bytes(self):
        for offset in (24, 28, 32, 36, 1584, 8191):
            changed = bytearray(_image())
            changed[offset] = 1
            with self.subTest(offset=offset):
                self.reject(bytes(changed), "nonzero")
        self.reject(_image() + b"undeclared" + bytes(4096 - 10), "unrecognized image trailer")

    def test_rejects_unterminated_command_line(self):
        changed = bytearray(_image())
        changed[44:1580] = b"x" * 1536
        self.reject(bytes(changed), "unterminated Android command line")

    def test_rejects_truncated_or_wrong_compression_envelope(self):
        for data in (b"\x1f\x8b" + b"gzip" * 5, b"070701" + b"cpio" * 5,
                     _legacy()[:4], _legacy()[:-1], _legacy() + b"\0",
                     _legacy()[:4] + bytes(4),
                     _legacy()[:4] + struct.pack("<I", 0xFFFFFFFF),
                     _frame()[:-1], _frame()[:7] + bytes(4),
                     _frame() + _frame()):
            with self.subTest(ramdisk=data):
                self.reject(_image(data), "LZ4|compression")

    def test_rejects_unsupported_lz4_flags_sizes_or_dictionary(self):
        for index, value in ((4, 0), (4, 0x62), (4, 0x61), (5, 0x30), (5, 0xC0), (5, 0x41)):
            changed = bytearray(_frame())
            changed[index] = value
            with self.subTest(index=index, value=value):
                self.reject(_image(bytes(changed)), "LZ4")
        self.reject(_image(_u32(_frame(), 7, 0x80010001)), "exceeds declared maximum")

    def test_optional_lz4_size_and_checksum_fields_are_bounded_not_verified(self):
        # Same payload, with content size, block checksum and content checksum.
        frame = (b"\x04\x22\x4d\x18\x7c\x40" + struct.pack("<Q", 5) + b"\0"
                 + struct.pack("<I", 0x80000005) + b"hello" + bytes(12))
        report = self.inspect(_image(frame))
        self.assertFalse(report["ramdisk"]["compression"]["checksums_verified"])
        for data in (frame[:13], frame[:-1], frame[:-8]):
            self.reject(_image(data), "LZ4")

    def test_rejects_excess_lz4_blocks(self):
        ramdisk = _legacy()[:4] + _legacy()[4:] * (inspector.MAX_LZ4_BLOCKS + 1)
        self.reject(_image(ramdisk), "too many LZ4 blocks")

    def test_image_size_bound_checked_before_reading(self):
        self.image.write_bytes(_image())
        with self.image.open("ab") as stream:
            stream.truncate(inspector.MAX_IMAGE_BYTES + 4096)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "size exceeds"):
            inspector.inspect_image(self.image)

    def test_accepts_zero_padding_at_exact_factory_limit(self):
        self.image.write_bytes(_image())
        with self.image.open("ab") as stream:
            stream.truncate(inspector.MAX_IMAGE_BYTES)
        report = inspector.inspect_image(self.image)
        self.assertEqual(report["image"]["size_bytes"], inspector.MAX_IMAGE_BYTES)
        self.assertFalse(report["validation"]["flash_admitted"])


class AvbEnvelopeTests(ImageFixture):
    def test_parsed_footer_and_descriptor_headers_do_not_establish_trust(self):
        report = self.inspect(_with_avb())
        avb = report["avb"]
        self.assertTrue(avb["footer_present"])
        self.assertTrue(avb["vbmeta_parsed"])
        self.assertEqual(avb["original_image_size_bytes"], 8192)
        self.assertEqual(avb["vbmeta_sha256"], hashlib.sha256(_vbmeta()).hexdigest())
        self.assertEqual(avb["vbmeta"]["rollback_index"], 1)
        descriptor = avb["vbmeta"]["descriptor_headers"][0]
        self.assertEqual(descriptor["tag"], 99)
        self.assertEqual(descriptor["size_bytes"], 24)
        self.assertFalse(descriptor["payload_semantics_parsed"])
        for obj in (avb, avb["vbmeta"]):
            self.assertFalse(obj["signature_verified"])
            self.assertFalse(obj["trusted_key_verified"])
        self.assertFalse(report["validation"]["avb_trusted"])
        self.assertFalse(report["validation"]["flash_admitted"])

    def test_absent_descriptor_is_not_invented_from_footer(self):
        report = self.inspect(_with_avb(vbmeta=_vbmeta(b"")))
        self.assertEqual(report["avb"]["vbmeta"]["descriptor_headers"], [])

    def test_flags_are_reported_as_untrusted_data_not_a_verification_bypass(self):
        report = self.inspect(_with_avb(vbmeta=_vbmeta(flags=3)))
        self.assertEqual(report["avb"]["vbmeta"]["flags"], 3)
        self.assertFalse(report["validation"]["avb_trusted"])
        self.assertFalse(report["validation"]["flash_admitted"])

    def test_rejects_footer_overlaps_and_out_of_range_sizes(self):
        data = _with_avb()
        footer = len(data) - 64
        for field, value in ((12, 4096), (12, 100000), (20, 4096),
                             (20, 8193), (20, 0xFFFFFFFFFFFFFFFF),
                             (28, 0), (28, 0xFFFFFFFFFFFFFFFF)):
            with self.subTest(field=field, value=value):
                self.reject(_be64(data, footer + field, value), "AVB")

    def test_rejects_invalid_footer_reserved_bytes_and_version(self):
        for offset in (-1, -60, -56):
            changed = bytearray(_with_avb())
            changed[offset] = 2
            self.reject(bytes(changed), "AVB footer")

    def test_rejects_vbmeta_magic_sizes_and_reserved_fields(self):
        for offset in (0, 4, 19, 27, 176):
            changed = bytearray(_vbmeta())
            changed[offset] = 0xFF
            with self.subTest(offset=offset):
                self.reject(_with_avb(vbmeta=bytes(changed)), "AVB")
        self.reject(_with_avb(vbmeta=b"AVB0"), "AVB")

    def test_rejects_overlapping_and_out_of_range_avb_fields(self):
        for offset, value in ((48, 16), (40, 0xFFFFFFFFFFFFFFFF), (64, 0),
                               (80, 24), (96, 0xFFFFFFFFFFFFFFFF), (104, 0xFFFFFFFFFFFFFFFF)):
            with self.subTest(offset=offset, value=value):
                self.reject(_with_avb(vbmeta=_be64(_vbmeta(), offset, value)), "AVB")

    def test_rejects_truncated_or_excessive_descriptor_headers(self):
        for descriptors in (bytes(8), struct.pack(">QQ", 2, 7),
                            struct.pack(">QQ", 2, 0xFFFFFFFFFFFFFFF8),
                            struct.pack(">QQ", 99, 0) * (inspector.MAX_AVB_DESCRIPTORS + 1)):
            with self.subTest(length=len(descriptors)):
                self.reject(_with_avb(vbmeta=_vbmeta(descriptors)), "AVB")

    def test_rejects_undeclared_nonzero_bytes_between_vbmeta_and_footer(self):
        changed = bytearray(_with_avb())
        changed[-65] = 1
        self.reject(bytes(changed), "padding after AVB metadata")


class FileSafetyAndCliTests(ImageFixture):
    def test_rejects_symlink_nonregular_or_missing_input(self):
        target = self.root / "target.img"
        target.write_bytes(_image())
        self.image.symlink_to(target)
        with self.assertRaises(inspector.IntakeError):
            inspector.inspect_image(self.image)
        self.image.unlink()
        os.mkfifo(self.image)
        with self.assertRaises(inspector.IntakeError):
            inspector.inspect_image(self.image)
        self.image.unlink()
        with self.assertRaises(FileNotFoundError):
            inspector.inspect_image(self.image)
        with self.assertRaises(inspector.IntakeError):
            inspector.inspect_image(self.root)
        self.assertEqual(target.read_bytes(), _image())

    def test_rejects_symlink_input_ancestor(self):
        directory = self.root / "actual"
        directory.mkdir()
        (directory / "recovery.img").write_bytes(_image())
        link = self.root / "link"
        link.symlink_to(directory, target_is_directory=True)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "ancestors"):
            inspector.inspect_image(link / "recovery.img")

    def test_rejects_image_change_during_inspection(self):
        self.image.write_bytes(_image())
        before = (1, 2, len(_image()), 3, 4)
        after = (1, 2, len(_image()), 3, 5)
        with mock.patch.object(inspector, "_signature", side_effect=[before, before, after]):
            with self.assertRaisesRegex(inspector.ImageInspectionError, "changed while inspected"):
                inspector.inspect_image(self.image)

    def test_cli_prints_json_and_writes_new_private_report(self):
        self.image.write_bytes(_image())
        output = self.root / "inspection.json"
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = inspector.main([str(self.image), "--output", str(output)])
        self.assertEqual(result, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(json.loads(stdout.getvalue()), json.loads(output.read_text()))
        self.assertLess(output.stat().st_size, inspector.MAX_REPORT_BYTES)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode) & 0o077, 0)
        self.assertEqual(self.image.read_bytes(), _image())

    def test_cli_invalid_image_never_creates_report(self):
        self.image.write_bytes(bytes(4096))
        output = self.root / "invalid.json"
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = inspector.main([str(self.image), "--output", str(output)])
        self.assertEqual(result, 2)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("inspection failed", stderr.getvalue())
        self.assertFalse(output.exists())

    def test_never_overwrites_regular_symlink_directory_or_input_output(self):
        report = self.inspect(_image())
        existing = self.root / "existing.json"
        existing.write_text("preserve")
        link = self.root / "link.json"
        link.symlink_to(existing)
        broken = self.root / "broken.json"
        broken.symlink_to(self.root / "absent.json")
        directory = self.root / "directory.json"
        directory.mkdir()
        for output in (existing, link, broken, directory):
            with self.subTest(output=output.name), self.assertRaises(FileExistsError):
                inspector.write_report(output, report)
        with self.assertRaises(inspector.ImageInspectionError):
            inspector.write_report(self.image, report)
        self.assertEqual(existing.read_text(), "preserve")
        self.assertTrue(link.is_symlink())
        self.assertTrue(broken.is_symlink())
        self.assertEqual(self.image.read_bytes(), _image())

    def test_output_parent_suffix_path_and_report_bounds(self):
        report = self.inspect(_image())
        link = self.root / "link"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "ancestors"):
            inspector.write_report(link / "unsafe.json", report)
        with self.assertRaises(FileNotFoundError):
            inspector.write_report(self.root / "absent" / "report.json", report)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "suffix"):
            inspector.write_report(self.root / "report.img", report)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "path"):
            inspector.write_report("x" * 4097, report)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "output bound"):
            inspector.write_report(self.root / "large.json", {"data": "x" * inspector.MAX_REPORT_BYTES})
        self.assertFalse((self.root / "large.json").exists())
        self.assertFalse((self.root / "absent").exists())

    def test_failed_report_write_retains_partial_artifact_without_retry_overwrite(self):
        report = self.inspect(_image())
        output = self.root / "new.json"
        with mock.patch.object(inspector.os, "fsync", side_effect=OSError("synthetic write error")):
            with self.assertRaisesRegex(inspector.ImageInspectionError, "partial artifact is preserved"):
                inspector.write_report(output, report)
        self.assertTrue(output.is_file())
        with self.assertRaises(FileExistsError):
            inspector.write_report(output, report)
        self.assertEqual(self.image.read_bytes(), _image())

    def test_replacing_input_ancestor_cannot_redirect_open(self):
        directory = self.root / "input"
        directory.mkdir()
        image = directory / "recovery.img"
        image.write_bytes(_image())
        other = self.root / "other-input"
        other.mkdir()
        (other / image.name).write_bytes(_u32(_image(), 8, 1))
        moved = self.root / "moved-input"
        real_open = os.open

        def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
            if path == image.name:
                directory.rename(moved)
                directory.symlink_to(other, target_is_directory=True)
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(inspector.os, "open", side_effect=swapping_open):
            report = inspector.inspect_image(image)
        self.assertEqual(report["image"]["sha256"], hashlib.sha256(_image()).hexdigest())
        self.assertEqual((moved / image.name).read_bytes(), _image())

    def test_replacing_output_ancestor_cannot_redirect_write(self):
        report = self.inspect(_image())
        directory = self.root / "output"
        directory.mkdir()
        output = directory / "new.json"
        other = self.root / "other-output"
        other.mkdir()
        moved = self.root / "moved-output"
        real_open = os.open

        def swapping_open(path, flags, mode=0o777, *, dir_fd=None):
            if path == output.name:
                directory.rename(moved)
                directory.symlink_to(other, target_is_directory=True)
            return real_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(inspector.os, "open", side_effect=swapping_open):
            inspector.write_report(output, report)
        self.assertEqual(json.loads((moved / output.name).read_text()), report)
        self.assertFalse((other / output.name).exists())

    def test_failed_write_never_unlinks_an_unrelated_replacement(self):
        report = self.inspect(_image())
        output = self.root / "new.json"
        moved = self.root / "moved-partial.json"

        def replacing_fsync(_descriptor):
            output.rename(moved)
            output.write_bytes(b"unrelated replacement must survive")
            raise OSError("synthetic write error")

        with mock.patch.object(inspector.os, "fsync", side_effect=replacing_fsync):
            with self.assertRaisesRegex(inspector.ImageInspectionError, "partial artifact is preserved"):
                inspector.write_report(output, report)
        self.assertEqual(output.read_bytes(), b"unrelated replacement must survive")
        self.assertTrue(moved.is_file())
        self.assertEqual(self.image.read_bytes(), _image())


if __name__ == "__main__":
    unittest.main()
