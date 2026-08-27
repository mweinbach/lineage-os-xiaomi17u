"""Synthetic, offline tests of inert GPT/XML capture and package geometry."""

import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import sys
import tarfile
import tempfile
import unittest
from unittest import mock
import uuid
import xml.etree.ElementTree as ET
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import gpt_metadata as gpt


TYPE_GUID = uuid.UUID("11111111-2222-3333-4444-555555555555")
DISK_GUID = uuid.UUID("aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee")
ZERO_GUID = uuid.UUID(int=0)


def _entry(label, first, last, *, type_guid=TYPE_GUID, unique=1, flags=0):
    encoded = label.encode("utf-16-le")
    return (
        type_guid.bytes_le + uuid.UUID(int=unique).bytes_le
        + struct.pack("<QQQ", first, last, flags) + encoded + bytes(72 - len(encoded))
    )


def _header(array, *, backup=False, empty=False, count=32):
    current, alternate = (26, 1) if backup else (1, 26)
    first, last, entry_lba = 6, 21, 22 if backup else 2
    if empty:
        current, alternate, first, last, entry_lba, count = 1, 0, 34, 0, 2, 4
    raw = bytearray(gpt.GPT_HEADER.pack(
        b"EFI PART", 0x10000, 92, 0, 0, current, alternate, first, last,
        DISK_GUID.bytes_le, entry_lba, count, 128, zlib.crc32(array[:count * 128]),
    ))
    struct.pack_into("<I", raw, 16, zlib.crc32(raw))
    return bytes(raw) + bytes(4096 - len(raw))


def _fragments(lun=0):
    finite_label = "boot_a" if lun == 0 else f"part{lun}"
    growth_label = "userdata" if lun == 0 else "last_parti"
    growth_type = TYPE_GUID if lun == 0 else ZERO_GUID
    growth_flags = 0 if lun == 0 else 1 << 60
    array = _entry(finite_label, 6, 21) + _entry(
        growth_label, 22, 21, type_guid=growth_type, unique=2, flags=growth_flags
    )
    array += bytes(16384 - len(array))
    mbr = bytearray(4096)
    mbr[450] = 0xEE
    struct.pack_into("<II", mbr, 454, 1, 0xFFFFFFFF)
    mbr[510:512] = b"\x55\xaa"
    main = bytes(mbr) + _header(array) + array
    backup = array + _header(array, backup=True)
    unused = _entry("empty", 34, 545, type_guid=ZERO_GUID) + bytes(16384 - 128)
    empty = bytes(mbr) + _header(unused, empty=True) + unused
    return {"main": main, "backup": backup, "both": main + backup, "empty": empty}


def _program(label, filename, lun, first, count, *, sparse=False, combined=False):
    return ET.Element("program", {
        "SECTOR_SIZE_IN_BYTES": "4096", "file_sector_offset": "0", "filename": filename,
        "label": label, "num_partition_sectors": str(count),
        "partofsingleimage": str(combined).lower(), "physical_partition_number": str(lun),
        "readbackverify": "false", "size_in_KB": str(count * 4) + ".0",
        "sparse": str(sparse).lower(),
        "start_byte_hex": hex(first * 4096) if first is not None else "(4096*NUM_DISK_SECTORS)-20480.",
        "start_sector": str(first) if first is not None else "NUM_DISK_SECTORS-5.",
    })


def _fixture_blobs():
    blobs = {}
    layout = ET.Element("configuration")
    ET.SubElement(layout, "parser_instructions").text = (
        "\nWRITE_PROTECT_BOUNDARY_IN_KB=0\nSECTOR_SIZE_IN_BYTES=4096\n"
        "GROW_LAST_PARTITION_TO_FILL_DISK=true\n"
    )
    for lun in range(6):
        finite = "boot_a" if lun == 0 else f"part{lun}"
        growth = "userdata" if lun == 0 else "last_parti"
        physical = ET.SubElement(layout, "physical_partition")
        for label, kib, type_guid, readonly, filename, sparse in (
            (finite, 64, TYPE_GUID, False, "boot.img", False),
            (growth, 128 if lun == 0 else 0, TYPE_GUID if lun == 0 else ZERO_GUID,
             lun != 0, "userdata.img" if lun == 0 else "", lun == 0),
        ):
            ET.SubElement(physical, "partition", {
                "label": label, "size_in_kb": str(kib), "type": str(type_guid),
                "bootable": "false", "readonly": str(readonly).lower(),
                "filename": filename, "sparse": str(sparse).lower(),
            })
        raw = ET.Element("data")
        raw.extend([
            _program(finite, "boot.img", lun, 6, 16),
            _program(growth, "userdata.img" if lun == 0 else "", lun, 22, 0, sparse=lun == 0),
            _program("PrimaryGPT", f"gpt_main{lun}.bin", lun, 0, 6, combined=True),
            _program("BackupGPT", f"gpt_backup{lun}.bin", lun, None, 5, combined=True),
        ])
        patches = ET.Element("patches")
        ET.SubElement(patches, "patch", {
            "SECTOR_SIZE_IN_BYTES": "4096", "byte_offset": "16", "filename": "DISK",
            "physical_partition_number": str(lun), "size_in_bytes": "4",
            "start_sector": "NUM_DISK_SECTORS-1.", "value": "CRC32(NUM_DISK_SECTORS-1.,92)",
            "what": "Inert synthetic declaration",
        })
        blobs[f"rawprogram{lun}.xml"] = ET.tostring(raw)
        blobs[f"patch{lun}.xml"] = ET.tostring(patches)
        for kind, data in _fragments(lun).items():
            blobs[f"gpt_{kind}{lun}.bin"] = data
    blobs["partition_ext_p1.xml"] = ET.tostring(layout)
    return blobs


def _rewrite_header(data, offset=4096, *, values=None):
    changed = bytearray(data)
    fields = list(gpt.GPT_HEADER.unpack_from(changed, offset))
    for index, value in (values or {}).items():
        fields[index] = value
    fields[3] = 0
    raw = gpt.GPT_HEADER.pack(*fields)
    fields[3] = zlib.crc32(raw)
    changed[offset:offset + 92] = gpt.GPT_HEADER.pack(*fields)
    return bytes(changed)


def _replace_main_array(data, array):
    changed = bytearray(data)
    changed[8192:8192 + len(array)] = array
    count = struct.unpack_from("<I", changed, 4176)[0]
    return _rewrite_header(changed, values={13: zlib.crc32(changed[8192:8192 + count * 128])})


def _xml_change(data, transform):
    root = ET.fromstring(data)
    transform(root)
    return ET.tostring(root)


class MetadataFixture:
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.output = self.root / "new-capture"

    def package(self, *, extra=(), omit=(), transform=lambda value: value, replacements=None):
        replacements = replacements or {}
        raw = io.BytesIO()
        with tarfile.open(fileobj=raw, mode="w", format=tarfile.USTAR_FORMAT) as archive:
            rows = [("nezha/images/" + name, replacements.get(name, b"inert metadata"))
                    for name in sorted(gpt.ALLOWED_NAMES) if name not in omit]
            rows.extend(extra)
            for name, payload in rows:
                entry = name if isinstance(name, tarfile.TarInfo) else tarfile.TarInfo(name)
                entry.size = len(payload)
                archive.addfile(entry, io.BytesIO(payload))
        encoded = transform(gzip.compress(raw.getvalue()))
        self.sha = hashlib.sha256(encoded).hexdigest()
        self.intake = self.root / self.sha
        self.intake.mkdir()
        self.package_path = self.intake / "firmware.tgz"
        self.package_path.write_bytes(encoded)
        metadata = {"schema_version": 2, "filename": "firmware.tgz", "sha256": self.sha,
                    "size_bytes": len(encoded), "device": "nezha", "build": "declared",
                    "region": "CN", "source_kind": "user-provided", "source_url": None,
                    "origin_verified": False, "collected_at_utc": "2026-08-27T00:00:00+00:00"}
        (self.intake / "metadata.json").write_text(json.dumps(metadata))

    def capture(self):
        return gpt.capture_metadata(self.intake, self.output, expected_sha256=self.sha)


class MetadataCaptureTests(MetadataFixture, unittest.TestCase):
    def test_exact_allowlist_is_copied_with_complete_integrity_and_unknown_origin(self):
        self.package(extra=[("nezha/flash_all.sh", b"never run this"),
                            ("nezha/images/qsahara_device_programmer.xml", b"never apply this"),
                            ("nezha/images/xbl.elf", b"never run this")])
        before = self.package_path.read_bytes()
        result = self.capture()
        self.assertEqual({p.name for p in self.output.iterdir()}, gpt.ALLOWED_NAMES | {"receipt.json"})
        self.assertEqual(result["file_count"], 37)
        self.assertTrue(result["gzip_stream_crc_verified"])
        self.assertTrue(result["tar_header_checksums_verified"])
        self.assertEqual(result["parent_package_sha256"], self.sha)
        self.assertEqual(result["intake_provenance"]["source_kind"], "user-provided")
        self.assertFalse(result["intake_provenance"]["origin_verified"])
        for key in ("xml_instructions_applied", "firmware_executed", "device_programmer_extracted_or_executed",
                    "phone_accessed", "physical_phone_geometry_verified"):
            self.assertFalse(result[key])
        for row in result["files"]:
            copied = (self.output / row["path"]).read_bytes()
            self.assertEqual(hashlib.sha256(copied).hexdigest(), row["sha256"])
            self.assertEqual(len(copied), row["size_bytes"])
            self.assertTrue(row["readback_verified"])
        self.assertEqual(self.package_path.read_bytes(), before)

    def test_missing_required_metadata_refuses_publication(self):
        self.package(omit={"patch0.xml"})
        with self.assertRaisesRegex(gpt.IntakeError, "37-file"):
            self.capture()
        self.assertFalse(self.output.exists())

    def test_nonallowlisted_programmer_does_not_substitute_a_required_file(self):
        self.package(omit={"partition_ext_p1.xml"}, extra=[("nezha/images/partition.xml", b"not allowed")])
        with self.assertRaises(gpt.IntakeError):
            self.capture()
        self.assertFalse(self.output.exists())

    def test_bad_gzip_crc_and_truncation_refuse_all_outputs(self):
        for transform in [lambda raw: raw[:-8] + bytes([raw[-8] ^ 1]) + raw[-7:], lambda raw: raw[:-3]]:
            with self.subTest(transform=transform), tempfile.TemporaryDirectory() as directory:
                self.root = Path(directory).resolve()
                self.output = self.root / "new-capture"
                self.package(transform=transform)
                with self.assertRaises((gzip.BadGzipFile, EOFError)):
                    self.capture()
                self.assertFalse(self.output.exists())

    def test_invalid_tar_header_after_all_selected_members_is_not_treated_as_eof(self):
        def corrupt_late_header(encoded):
            raw = bytearray(gzip.decompress(encoded))
            with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
                entries = list(archive)
            last = entries[-1]
            end = last.offset_data + ((last.size + 511) // 512) * 512
            malformed = bytearray(tarfile.TarInfo("bad-checksum-member").tobuf())
            malformed[148:156] = b"0000000\0"
            # All 37 valid selected members precede this corrupt header.
            # Remaining zero padding used to let tarfile treat it as EOF.
            raw[end:end + 512] = malformed
            return gzip.compress(raw)

        self.package(transform=corrupt_late_header)
        with self.assertRaises(gpt.IntakeError):
            self.capture()
        self.assertFalse(self.output.exists())
        self.assertFalse((self.root / ".new-capture.lock").exists())

    def test_unsafe_duplicate_and_ambiguous_members_are_refused(self):
        for extra in [[("../outside", b"x")], [("nezha/images/GPT_MAIN0.BIN", b"x")],
                      [("other/images/gpt_main0.bin", b"x")]]:
            with self.subTest(extra=extra), tempfile.TemporaryDirectory() as directory:
                self.root = Path(directory).resolve()
                self.output = self.root / "new-capture"
                self.package(extra=extra)
                with self.assertRaises(gpt.IntakeError):
                    self.capture()
                self.assertFalse(self.output.exists())

    def test_links_are_rejected_even_outside_the_allowlist(self):
        for kind in (tarfile.SYMTYPE, tarfile.LNKTYPE, tarfile.FIFOTYPE):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                self.root = Path(directory).resolve()
                self.output = self.root / "new-capture"
                entry = tarfile.TarInfo("nezha/elsewhere")
                entry.type = kind
                entry.linkname = "target"
                self.package(extra=[(entry, b"")])
                with self.assertRaises(gpt.IntakeError):
                    self.capture()
                self.assertFalse(self.output.exists())

    def test_size_bounds_and_low_disk_are_enforced_before_publication(self):
        self.package()
        with mock.patch.object(gpt, "MAX_MEMBER_BYTES", 4), self.assertRaises(gpt.IntakeError):
            self.capture()
        with mock.patch.object(gpt, "MAX_CAPTURE_BYTES", 20), self.assertRaises(gpt.IntakeError):
            self.capture()
        with mock.patch.object(gpt.shutil, "disk_usage", return_value=mock.Mock(free=0)), self.assertRaises(gpt.IntakeError):
            self.capture()
        self.assertFalse(self.output.exists())

    def test_existing_output_and_input_alias_are_preserved(self):
        self.package()
        self.output.mkdir()
        (self.output / "keep").write_text("keep")
        with self.assertRaises(gpt.IntakeError):
            self.capture()
        self.assertEqual((self.output / "keep").read_text(), "keep")
        self.output = self.intake / "inside"
        with self.assertRaises(gpt.IntakeError):
            self.capture()

    def test_package_hash_and_metadata_mutation_are_not_accepted(self):
        self.package()
        with self.assertRaises(gpt.IntakeError):
            gpt.capture_metadata(self.intake, self.output, expected_sha256="0" * 64)
        old_publish = gpt._file_hash

        def mutate(path):
            result = old_publish(path)
            (self.intake / "metadata.json").write_text("{}")
            return result

        with mock.patch.object(gpt, "_file_hash", side_effect=mutate), self.assertRaises(gpt.IntakeError):
            self.capture()
        self.assertFalse(self.output.exists())

    def test_publication_race_never_replaces_existing_directory(self):
        self.package()
        publish = gpt.publish_new_directory

        def race(staging, target):
            target.mkdir()
            (target / "keep").write_text("keep")
            return publish(staging, target)

        with mock.patch.object(gpt, "publish_new_directory", side_effect=race), self.assertRaises(OSError):
            self.capture()
        self.assertEqual((self.output / "keep").read_text(), "keep")


class GPTParsingTests(unittest.TestCase):
    def test_main_backup_combined_and_empty_crcs_are_checked(self):
        for kind, data in _fragments().items():
            with self.subTest(kind=kind):
                result = gpt.parse_gpt_blob(data, kind)
                self.assertEqual(result["sector_size_bytes"], 4096)
                self.assertFalse(result["usable_physical_disk_geometry_verified"])
                for header in result["headers"]:
                    self.assertTrue(header["header_crc32_verified"])
                    self.assertTrue(header["entry_array_crc32_verified"])
                self.assertEqual(len(result["headers"]), 2 if kind == "both" else 1)
        result = gpt.parse_gpt_blob(_fragments()["main"], "main")
        self.assertEqual(result["headers"][0]["entry_array_offset_bytes"], 8192)
        self.assertEqual(result["protective_mbr"]["size_in_lba"], 0xFFFFFFFF)

    def test_header_and_array_corruption_are_separately_rejected(self):
        for offset, message in [(4140, "header CRC32"), (8200, "entry-array CRC32")]:
            with self.subTest(offset=offset):
                data = bytearray(_fragments()["main"])
                data[offset] ^= 1
                with self.assertRaisesRegex(gpt.IntakeError, message):
                    gpt.parse_gpt_blob(bytes(data), "main")

    def test_revision_size_reserved_and_array_dimensions_are_not_trusted(self):
        cases = [
            {0: b"EFI FAIL"}, {1: 0x20000}, {2: 0}, {2: 4097}, {4: 1},
            {11: 0}, {11: 129}, {11: 2**32 - 1}, {12: 0}, {12: 256},
        ]
        for fields in cases:
            with self.subTest(fields=fields), self.assertRaises(gpt.IntakeError):
                gpt.parse_gpt_blob(_rewrite_header(_fragments()["main"], values=fields), "main")

    def test_exact_lengths_and_sector_size_are_required(self):
        for data in (_fragments()["main"][:-1], _fragments()["main"] + b"\0"):
            with self.assertRaises(gpt.IntakeError):
                gpt.parse_gpt_blob(data, "main")
        for sector in (512, 8192, True):
            with self.assertRaises(gpt.IntakeError):
                gpt.parse_gpt_blob(_fragments()["main"], "main", sector_size=sector)
        with self.assertRaises(gpt.IntakeError):
            gpt.parse_gpt_blob(_fragments()["main"], "unknown")

    def test_array_lba_header_location_and_u64_extents_are_bounded(self):
        for fields in ({10: 0}, {10: 3}, {10: 2**64 - 1}, {5: 2}, {6: 0}, {8: 5},
                       {7: 34}, {8: 2**64 - 1}, {9: bytes(16)}):
            with self.subTest(fields=fields), self.assertRaises(gpt.IntakeError):
                gpt.parse_gpt_blob(_rewrite_header(_fragments()["main"], values=fields), "main")

    def test_padding_and_protective_mbr_structure_are_validated(self):
        for offset in (450, 454, 462, 510, 512, 4190, 13000):
            with self.subTest(offset=offset):
                data = bytearray(_fragments()["main"])
                data[offset] ^= 1
                with self.assertRaises(gpt.IntakeError):
                    gpt.parse_gpt_blob(bytes(data), "main")

    def test_utf16_names_zero_terminator_and_identifier_uniqueness(self):
        original = _fragments()["main"]
        for first in (
            _entry("../unsafe", 6, 21),
            _entry("boot_a", 6, 21, unique=0),
            _entry("boot_a", 6, 21)[:56] + b"\x00\xd8" + bytes(70),
            _entry("boot_a", 6, 21)[:56] + "ok\0bad".encode("utf-16-le") + bytes(60),
        ):
            with self.subTest(first=first[:8]), self.assertRaises(gpt.IntakeError):
                gpt.parse_gpt_blob(_replace_main_array(original, first), "main")
        for second in (_entry("boot_a", 22, 21, unique=2), _entry("userdata", 22, 21, unique=1)):
            with self.assertRaises(gpt.IntakeError):
                array = original[8192:8320] + second
                gpt.parse_gpt_blob(_replace_main_array(original, array), "main")

    def test_inverted_interval_and_byte_overflow_are_refused(self):
        for first, last in ((22, 20), (2**64 - 1, 2**64 - 1)):
            with self.subTest(first=first), self.assertRaises(gpt.IntakeError):
                data = _replace_main_array(_fragments()["main"], _entry("boot_a", first, last))
                gpt.parse_gpt_blob(data, "main")

    def test_combined_header_identity_mismatch_is_rejected(self):
        data = _rewrite_header(_fragments()["both"], 40960, values={9: uuid.UUID(int=99).bytes_le})
        with self.assertRaisesRegex(gpt.IntakeError, "combined"):
            gpt.parse_gpt_blob(data, "both")

    def test_empty_crc_success_never_establishes_usable_geometry(self):
        result = gpt.parse_gpt_blob(_fragments()["empty"], "empty")
        header = result["headers"][0]
        self.assertTrue(result["empty_template"])
        self.assertEqual(header["alternate_lba"], 0)
        self.assertGreater(header["first_usable_lba"], header["last_usable_lba"])
        self.assertTrue(header["entries"][0]["type_guid_zero"])
        self.assertFalse(result["usable_physical_disk_geometry_verified"])
        with self.assertRaises(gpt.IntakeError):
            gpt.parse_gpt_blob(_rewrite_header(_fragments()["empty"], values={7: 6}), "empty")


class XMLAndCrosscheckTests(unittest.TestCase):
    def setUp(self):
        self.blobs = _fixture_blobs()

    def test_six_luns_crosscheck_finite_extents_and_unresolved_growth(self):
        result = gpt.analyze_metadata(self.blobs)
        self.assertEqual(result["lun_count"], 6)
        self.assertEqual(result["header_entry_crc_pairs_verified"], 30)
        self.assertEqual(result["finite_partition_count"], 6)
        self.assertEqual(result["growth_placeholder_count"], 6)
        for lun in result["luns"]:
            self.assertTrue(lun["combined_fragment_bytes_match"])
            self.assertTrue(lun["primary_backup_entry_arrays_identical"])
            self.assertEqual(lun["finite_partition_count"], 1)
            self.assertEqual(lun["partitions"][0]["size_bytes"], 65536)
            self.assertFalse(lun["empty_template_has_valid_usable_lba_range"])
        growth = result["luns"][0]["partitions"][-1]
        self.assertEqual(growth["size_bytes"], 0)
        self.assertEqual(growth["xml_requested_size_bytes"], 128 * 1024)
        self.assertEqual(growth["role"], "unresolved-growth-placeholder")
        for key in ("physical_phone_geometry_verified", "flashable_gpt_admitted",
                    "xml_instructions_applied", "phone_accessed", "firmware_executed"):
            self.assertFalse(result[key])

    def test_dtd_entities_utf16_excessive_bytes_nodes_and_depth_are_rejected(self):
        bad = [
            b'<!DOCTYPE data [<!ENTITY bad "expand">]><data>&bad;</data>',
            b'<!ENTITY bad SYSTEM "file:///private"><data/>',
            "<data/>".encode("utf-16"), b"<data>\0</data>",
            b"<data><a><b><c><d/></c></b></a></data>",
            b"<data>" + b"<a/>" * 1024 + b"</data>",
        ]
        for data in bad:
            with self.subTest(size=len(data)), self.assertRaises(gpt.IntakeError):
                gpt._xml(data, "data")
        with mock.patch.object(gpt, "MAX_MEMBER_BYTES", 6), self.assertRaises(gpt.IntakeError):
            gpt._xml(b"<data/>", "data")

    def test_unknown_missing_duplicate_and_nonliteral_declarations_are_rejected(self):
        original = self.blobs["partition_ext_p1.xml"]
        for transform in (
            lambda root: root.find("parser_instructions").__setattr__("text", "exec=bad"),
            lambda root: root.find("parser_instructions").__setattr__(
                "text", root.find("parser_instructions").text + "SECTOR_SIZE_IN_BYTES=4096\n"),
            lambda root: root.find("parser_instructions").__setattr__(
                "text", root.find("parser_instructions").text.replace("4096", "512")),
            lambda root: root.remove(root[-1]),
            lambda root: root.set("unexpected", "yes"),
        ):
            with self.subTest(transform=transform), self.assertRaises(gpt.IntakeError):
                gpt.parse_partition_xml(_xml_change(original, transform))

    def test_partition_fields_are_bounded_and_whitespace_booleans_normalized(self):
        original = self.blobs["partition_ext_p1.xml"]
        for key, value in (
            ("label", "../escape"), ("size_in_kb", "3"), ("size_in_kb", "-1"),
            ("size_in_kb", "9" * 21), ("type", "bad-guid"), ("filename", "../boot.img"),
            ("filename", "$(touch marker)"), ("readonly", "False"), ("surprise", "true"),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(gpt.IntakeError):
                gpt.parse_partition_xml(_xml_change(original, lambda root: root[1][0].set(key, value)))
        changed = _xml_change(original, lambda root: root[1][0].set("readonly", " false"))
        self.assertEqual(gpt.parse_partition_xml(changed)["luns"][0]["partitions"][0]["attributes_hex"],
                         "0x0000000000000000")

    def test_rawprogram_sector_lun_byte_size_and_boolean_crosschecks(self):
        original = self.blobs["rawprogram0.xml"]
        for key, value in (
            ("SECTOR_SIZE_IN_BYTES", "512"), ("physical_partition_number", "1"),
            ("file_sector_offset", "1"), ("num_partition_sectors", "-1"),
            ("size_in_KB", "1.25"), ("size_in_KB", "65.0"), ("start_byte_hex", "0x1"),
            ("sparse", "True"), ("filename", "/tmp/out"), ("label", "BackupGPT"),
            ("start_sector", "NUM_DISK_SECTORS-1."), ("unexpected", "0"),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(gpt.IntakeError):
                gpt.parse_rawprogram_xml(_xml_change(original, lambda root: root[0].set(key, value)), 0)
        with self.assertRaises(gpt.IntakeError):
            gpt.parse_rawprogram_xml(original, True)

    def test_backup_symbolic_offset_is_not_evaluated_or_guessed(self):
        rows = gpt.parse_rawprogram_xml(self.blobs["rawprogram0.xml"], 0)
        self.assertIsNone(rows[-1]["first_lba"])
        self.assertEqual(rows[-1]["start_sector_expression"], "NUM_DISK_SECTORS-5.")
        for key, value in (
            ("start_sector", "NUM_DISK_SECTORS-4."),
            ("start_byte_hex", "(4096*NUM_DISK_SECTORS)-16384."),
        ):
            with self.assertRaises(gpt.IntakeError):
                data = _xml_change(self.blobs["rawprogram0.xml"], lambda root: root[-1].set(key, value))
                gpt.parse_rawprogram_xml(data, 0)

    def test_patch_expressions_are_counted_but_not_applied(self):
        result = gpt.parse_patch_xml(self.blobs["patch0.xml"], 0)
        self.assertEqual(result["symbolic_disk_sector_rows"], 1)
        self.assertEqual(result["crc_recalculation_requests"], 1)
        self.assertFalse(result["instructions_applied"])
        self.assertFalse(result["expressions_evaluated"])
        for key, value in (
            ("value", "__import__('os').system('touch marker')"),
            ("value", "CRC32(open(file),92)"), ("value", "CRC32(0,99999999999999999999)"),
            ("value", "NUM_DISK_SECTORS+1"), ("value", "NUM_DISK_SECTORS-0"),
            ("start_sector", "-1"), ("physical_partition_number", "5"),
            ("filename", "programmer.elf"), ("byte_offset", "4095"), ("size_in_bytes", "16"),
        ):
            with self.subTest(key=key, value=value), self.assertRaises(gpt.IntakeError):
                data = _xml_change(self.blobs["patch0.xml"], lambda root: root[0].set(key, value))
                gpt.parse_patch_xml(data, 0)

    def test_crosschecks_do_not_accept_wrong_partition_file_flags_size_or_order(self):
        for path, transform in (
            ("partition_ext_p1.xml", lambda root: root[1][0].set("size_in_kb", "68")),
            ("partition_ext_p1.xml", lambda root: root[1][0].set("type", str(ZERO_GUID))),
            ("partition_ext_p1.xml", lambda root: root[1][0].set("readonly", "true")),
            ("partition_ext_p1.xml", lambda root: root[1][0].set("filename", "different.img")),
            ("partition_ext_p1.xml", lambda root: root[1][0].set("sparse", "true")),
            ("rawprogram0.xml", lambda root: root[0].set("partofsingleimage", "true")),
            ("rawprogram0.xml", lambda root: root[0].set("label", "wrong")),
            ("rawprogram0.xml", lambda root: root[-2].set("filename", "gpt_main1.bin")),
        ):
            blobs = dict(self.blobs)
            blobs[path] = _xml_change(blobs[path], transform)
            with self.subTest(path=path, transform=transform), self.assertRaises(gpt.IntakeError):
                gpt.analyze_metadata(blobs)

    def test_growth_requires_declaration_and_zero_extent_must_be_terminal(self):
        blobs = dict(self.blobs)
        blobs["partition_ext_p1.xml"] = blobs["partition_ext_p1.xml"].replace(
            b"GROW_LAST_PARTITION_TO_FILL_DISK=true", b"GROW_LAST_PARTITION_TO_FILL_DISK=false")
        with self.assertRaisesRegex(gpt.IntakeError, "growth placeholder"):
            gpt.analyze_metadata(blobs)
        main = _replace_main_array(self.blobs["gpt_main0.bin"], _entry("boot_a", 6, 5))
        blobs = dict(self.blobs)
        blobs["gpt_main0.bin"] = main
        with self.assertRaises(gpt.IntakeError):
            gpt.analyze_metadata(blobs)

    def test_combined_fragment_and_backup_changes_are_not_hidden_by_valid_crcs(self):
        for changed_name in ("gpt_backup0.bin", "gpt_both0.bin"):
            blobs = dict(self.blobs)
            offset = 16384 if changed_name == "gpt_backup0.bin" else 40960
            blobs[changed_name] = _rewrite_header(blobs[changed_name], offset,
                                                  values={9: uuid.UUID(int=99).bytes_le})
            with self.subTest(name=changed_name), self.assertRaises(gpt.IntakeError):
                gpt.analyze_metadata(blobs)
        with self.assertRaises(gpt.IntakeError):
            gpt.analyze_metadata({key: value for key, value in self.blobs.items() if key != "patch0.xml"})

    def test_overlap_or_gap_cannot_become_a_partition_capacity(self):
        blobs = dict(self.blobs)
        main = _replace_main_array(blobs["gpt_main0.bin"], _entry("boot_a", 7, 22))
        backup = main[8192:] + _header(main[8192:], backup=True)
        blobs.update({"gpt_main0.bin": main, "gpt_backup0.bin": backup, "gpt_both0.bin": main + backup})
        with self.assertRaises(gpt.IntakeError):
            gpt.analyze_metadata(blobs)


class MetadataInspectionTests(MetadataFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.package(replacements=_fixture_blobs())
        self.capture_result = self.capture()
        self.capture_dir = self.output
        self.output = self.root / "new-inspection"
        self.capture_sha = hashlib.sha256((self.capture_dir / "receipt.json").read_bytes()).hexdigest()

    def inspect(self):
        return gpt.inspect_metadata(self.capture_dir, self.output, expected_sha256=self.sha,
                                    expected_capture_sha256=self.capture_sha)

    def rewrite_receipt(self, transform):
        path = self.capture_dir / "receipt.json"
        result = json.loads(path.read_bytes())
        transform(result)
        path.write_text(json.dumps(result))
        self.capture_sha = hashlib.sha256(path.read_bytes()).hexdigest()

    def test_inspection_is_bound_to_all_hashes_and_preserves_sources(self):
        before = {path.name: path.read_bytes() for path in self.capture_dir.iterdir()}
        result = self.inspect()
        self.assertEqual(result["input_count"], 37)
        self.assertEqual(result["capture_receipt_sha256"], self.capture_sha)
        self.assertEqual(result["parent_package_sha256"], self.sha)
        self.assertTrue(result["input_hashes_and_identity_rechecked"])
        self.assertTrue(result["output"]["readback_verified"])
        data = (self.output / "analysis.json").read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), result["output"]["sha256"])
        self.assertEqual({path.name: path.read_bytes() for path in self.capture_dir.iterdir()}, before)

    def test_wrong_package_receipt_and_file_hashes_refuse_publication(self):
        for kwargs in (
            {"expected_sha256": "0" * 64, "expected_capture_sha256": self.capture_sha},
            {"expected_sha256": self.sha, "expected_capture_sha256": "0" * 64},
        ):
            with self.assertRaises(gpt.IntakeError):
                gpt.inspect_metadata(self.capture_dir, self.output, **kwargs)
        path = self.capture_dir / "gpt_main0.bin"
        data = bytearray(path.read_bytes())
        data[-1] = 1
        path.write_bytes(data)
        with self.assertRaisesRegex(gpt.IntakeError, "SHA256"):
            self.inspect()
        self.assertFalse(self.output.exists())

    def test_receipt_rows_must_be_unique_allowlisted_and_consistent(self):
        original = (self.capture_dir / "receipt.json").read_bytes()
        transforms = [
            lambda r: r.__setitem__("file_count", True),
            lambda r: r.__setitem__("total_file_bytes", 0),
            lambda r: r.__setitem__("gzip_stream_crc_verified", False),
            lambda r: r.__setitem__("xml_instructions_applied", True),
            lambda r: r.__setitem__("physical_phone_geometry_verified", True),
            lambda r: r.__setitem__("intake_provenance", {}),
            lambda r: r["files"][0].__setitem__("path", "../outside"),
            lambda r: r["files"][0].__setitem__("path", r["files"][1]["path"]),
            lambda r: r["files"][0].__setitem__("archive_member", "../images/" + r["files"][0]["path"]),
            lambda r: r["files"][0].__setitem__("size_bytes", True),
            lambda r: r["files"][0].__setitem__("sha256", "bad"),
            lambda r: r["files"][0].__setitem__("readback_verified", False),
        ]
        for transform in transforms:
            with self.subTest(transform=transform):
                (self.capture_dir / "receipt.json").write_bytes(original)
                self.rewrite_receipt(transform)
                with self.assertRaises(gpt.IntakeError):
                    self.inspect()
                self.assertFalse(self.output.exists())

    def test_malformed_receipt_and_excessive_sizes_fail_cleanly(self):
        path = self.capture_dir / "receipt.json"
        original = path.read_bytes()
        for payload in (b"[]", b"{bad", b"null"):
            path.write_bytes(payload)
            self.capture_sha = hashlib.sha256(payload).hexdigest()
            with self.subTest(payload=payload), self.assertRaises(gpt.IntakeError):
                self.inspect()
        path.write_bytes(original)
        self.capture_sha = hashlib.sha256(original).hexdigest()
        with mock.patch.object(gpt, "MAX_MEMBER_BYTES", 10), self.assertRaises(gpt.IntakeError):
            self.inspect()
        with mock.patch.object(gpt, "MAX_CAPTURE_BYTES", 1), self.assertRaises(gpt.IntakeError):
            self.inspect()
        with mock.patch.object(gpt, "MAX_METADATA_BYTES", 10), self.assertRaises(gpt.IntakeError):
            self.inspect()

    def test_symlink_or_special_file_inputs_are_refused_without_following(self):
        for name in ("receipt.json", "gpt_main0.bin"):
            original = (self.capture_dir / name).read_bytes()
            target = self.root / ("private-" + name)
            target.write_bytes(original)
            (self.capture_dir / name).unlink()
            (self.capture_dir / name).symlink_to(target)
            with self.subTest(name=name), self.assertRaises(gpt.IntakeError):
                self.inspect()
            (self.capture_dir / name).unlink()
            (self.capture_dir / name).write_bytes(original)
        link = self.root / "capture-link"
        link.symlink_to(self.capture_dir, target_is_directory=True)
        with self.assertRaises(gpt.IntakeError):
            gpt.inspect_metadata(link, self.output, expected_sha256=self.sha,
                                 expected_capture_sha256=self.capture_sha)
        (self.capture_dir / "gpt_main0.bin").unlink()
        os.mkfifo(self.capture_dir / "gpt_main0.bin")
        with self.assertRaises(gpt.IntakeError):
            self.inspect()

    def test_inspection_rejects_source_or_receipt_mutation_after_parse(self):
        analyze = gpt.analyze_metadata
        for name in ("receipt.json", "gpt_main0.bin"):
            original = (self.capture_dir / name).read_bytes()

            def mutate(blobs):
                result = analyze(blobs)
                (self.capture_dir / name).write_bytes(original + b" ")
                return result

            with self.subTest(name=name), mock.patch.object(gpt, "analyze_metadata", side_effect=mutate):
                with self.assertRaises(gpt.IntakeError):
                    self.inspect()
            self.assertFalse(self.output.exists())
            (self.capture_dir / name).write_bytes(original)

    def test_inspection_rejects_replacement_with_identical_content(self):
        analyze = gpt.analyze_metadata

        def replace(blobs):
            result = analyze(blobs)
            path = self.capture_dir / "gpt_main0.bin"
            replacement = self.root / "identical"
            replacement.write_bytes(path.read_bytes())
            replacement.replace(path)
            return result

        with mock.patch.object(gpt, "analyze_metadata", side_effect=replace), self.assertRaises(gpt.IntakeError):
            self.inspect()
        self.assertFalse(self.output.exists())

    def test_inspection_publication_race_and_existing_output_preserve_other_files(self):
        publish = gpt.publish_new_directory

        def race(staging, target):
            target.mkdir()
            (target / "keep").write_text("keep")
            return publish(staging, target)

        with mock.patch.object(gpt, "publish_new_directory", side_effect=race), self.assertRaises(OSError):
            self.inspect()
        self.assertEqual((self.output / "keep").read_text(), "keep")
        with self.assertRaises(gpt.IntakeError):
            self.inspect()

    def test_inspection_input_alias_output_symlink_and_existing_lock_are_preserved(self):
        target = self.root / "elsewhere"
        target.mkdir()
        self.output.symlink_to(target, target_is_directory=True)
        with self.assertRaises(gpt.IntakeError):
            self.inspect()
        self.output.unlink()
        lock = self.root / ".new-inspection.lock"
        lock.write_text("keep")
        with self.assertRaisesRegex(gpt.IntakeError, "lock exists"):
            self.inspect()
        self.assertEqual(lock.read_text(), "keep")
        self.output = self.capture_dir / "inside"
        with self.assertRaises(gpt.IntakeError):
            self.inspect()


class PartitionMetadataRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/partition-metadata.json").read_text())
        cls.factory = json.loads((ROOT / "research/factory-firmware-intake.json").read_text())

    def test_package_and_complete_input_hash_inventory_are_bound_to_factory_intake(self):
        record = self.record
        self.assertEqual(record["package"]["sha256"], self.factory["package"]["sha256"])
        self.assertEqual(record["package"]["source_kind"], "user-provided")
        self.assertIsNone(record["package"]["source_url"])
        self.assertFalse(record["package"]["origin_verified"])
        capture = record["capture"]
        self.assertEqual(capture["file_count"], 37)
        self.assertEqual({row["path"] for row in capture["files"]}, gpt.ALLOWED_NAMES)
        self.assertEqual(capture["allowlist"], sorted(gpt.ALLOWED_NAMES))
        self.assertEqual(sum(row["size_bytes"] for row in capture["files"]), 805356)
        self.assertEqual(capture["total_file_bytes"], 805356)
        for row in capture["files"]:
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertLessEqual(row["size_bytes"], gpt.MAX_MEMBER_BYTES)

    def test_inventory_has_160_fixed_extents_and_six_terminal_growth_entries(self):
        luns = self.record["luns"]
        self.assertEqual([row["lun"] for row in luns], list(range(6)))
        self.assertEqual([row["finite_partition_count"] for row in luns], [33, 9, 9, 3, 98, 8])
        self.assertEqual(sum(len(row["partitions"]) for row in luns), 166)
        for lun in luns:
            self.assertEqual(lun["sector_size_bytes"], 4096)
            self.assertEqual(lun["growth_placeholder_count"], 1)
            first = 6
            for index, entry in enumerate(lun["partitions"]):
                self.assertEqual(entry["index"], index)
                self.assertEqual(entry["first_lba"], first)
                self.assertEqual(entry["sectors"], entry["last_lba"] - first + 1)
                self.assertEqual(entry["size_bytes"], entry["sectors"] * 4096)
                if entry["role"] == "finite-package-extent":
                    self.assertGreater(entry["size_bytes"], 0)
                    self.assertFalse(entry["type_guid_zero"])
                    self.assertEqual(entry["size_bytes"], entry["xml_requested_size_bytes"])
                    first = entry["last_lba"] + 1
                else:
                    self.assertEqual(entry["role"], "unresolved-growth-placeholder")
                    self.assertEqual(index, len(lun["partitions"]) - 1)
                    self.assertEqual(entry["size_bytes"], 0)
            self.assertEqual(first, lun["template_last_usable_lba"] + 1)
            self.assertEqual(lun["template_backup_header_lba"], first + 4)
            self.assertFalse(lun["template_disk_size_is_phone_capacity"])

    def test_image_budgets_use_package_extents_including_32_mib_dtbo(self):
        expected = {
            "boot": 96 * 1024**2, "init_boot": 8 * 1024**2,
            "vendor_boot": 96 * 1024**2, "recovery": 100 * 1024**2,
            "dtbo": 32 * 1024**2, "vbmeta": 128 * 1024,
            "vbmeta_system": 128 * 1024, "super": 15300820992,
        }
        sizes = {row["name"]: row for row in self.record["build_relevant_sizes"]}
        images = {row["path"]: row for row in self.factory["images"]}
        parts = {row["label"]: (lun["lun"], row) for lun in self.record["luns"]
                 for row in lun["partitions"]}
        self.assertEqual(set(sizes), set(expected))
        for name, size in expected.items():
            row = sizes[name]
            self.assertEqual(row["package_extent_bytes"], size)
            self.assertEqual(row["stored_image_bytes"], images[name + ".img"]["size_bytes"])
            self.assertEqual(row["stored_image_sha256"], images[name + ".img"]["sha256"])
            for label in row["labels"]:
                lun, entry = parts[label]
                self.assertEqual(lun, row["lun"])
                self.assertEqual(entry["size_bytes"], size)
                self.assertEqual(entry["role"], "finite-package-extent")
            self.assertFalse(row["physical_phone_capacity_verified"])
            self.assertFalse(row["use_as_flash_admission"])
        self.assertEqual(sizes["dtbo"]["stored_image_bytes"], 22 * 1024**2)
        self.assertEqual(sizes["super"]["sparse_header_expanded_bytes"], expected["super"])

    def test_empty_and_growth_templates_cannot_claim_disk_or_userdata_capacity(self):
        limits = self.record["template_limits"]
        self.assertTrue(limits["all_protective_mbr_sizes_are_ffffffff"])
        self.assertFalse(limits["protective_mbr_size_is_capacity_measurement"])
        self.assertEqual(limits["empty_template_first_usable_lba"], 34)
        self.assertEqual(limits["empty_template_last_usable_lba"], 0)
        self.assertEqual(limits["empty_template_alternate_lba"], 0)
        self.assertEqual(limits["empty_template_active_partition_count"], 0)
        self.assertEqual(limits["userdata_xml_requested_bytes"], 14 * 1024**3)
        self.assertEqual(limits["userdata_gpt_and_rawprogram_sectors"], 0)
        self.assertIsNone(limits["userdata_actual_size_bytes"])
        self.assertEqual(limits["last_parti_zero_type_guid_count"], 5)
        self.assertTrue(self.record["partition_xml_declarations"]["grow_last_partition_to_fill_disk"])
        self.assertFalse(self.record["partition_xml_declarations"]["declarations_executed"])
        for lun in self.record["luns"]:
            self.assertFalse(lun["empty_template_has_valid_usable_lba_range"])
            self.assertEqual(lun["empty_template_active_partition_count"], 0)

    def test_independent_crc_and_extent_results_agree_with_bounded_inspection(self):
        checked = self.record["inspection"]
        independent = self.record["independent_check"]
        for key, value in (
            ("header_entry_crc_pairs_verified", 30), ("finite_partition_count", 160),
            ("growth_placeholder_count", 6),
        ):
            self.assertEqual(checked[key], value)
            self.assertEqual(independent[key], value)
        self.assertEqual(checked["nonempty_header_entry_crc_pairs_verified"], 24)
        self.assertEqual(checked["empty_header_entry_crc_pairs_verified"], 6)
        self.assertEqual(checked["main_backup_entry_array_matches"], 6)
        self.assertEqual(checked["combined_equals_main_plus_backup_matches"], 6)
        self.assertFalse(independent["parser_module_imported"])
        self.assertTrue(checked["input_hashes_and_identity_rechecked"])

    def test_patch_and_source_directory_checks_do_not_execute_or_expand_their_scope(self):
        patches = self.record["patch_xml"]
        self.assertEqual((patches["file_count"], patches["row_count"]), (6, 156))
        self.assertEqual(patches["symbolic_disk_sector_rows"], 102)
        self.assertEqual(patches["crc_recalculation_requests"], 48)
        for key in ("expressions_evaluated", "instructions_applied", "disk_sector_count_supplied"):
            self.assertFalse(patches[key])
        compared = self.record["user_extracted_directory_comparison"]
        self.assertEqual(compared["metadata_files_compared"], 37)
        self.assertEqual(compared["total_metadata_bytes"], 805356)
        self.assertTrue(compared["all_metadata_files_match_capture"])
        self.assertIn("Only", compared["scope"])

    def test_receipts_are_hash_bound_and_point_to_private_artifacts(self):
        expected = {
            "capture": "3b97ce32e078481b80f4ff1c460193f70cf1a711549e85f937f71edfab489386",
            "inspection": "18c98f119761417a0ff11a7a107a713fce6fd7a99b9bb1288b300387fa7fcf3d",
            "independent_check": "94b3525a182a1576e0ec0d8910318f37a80693714c9bcf2beac41bff0d100cd1",
        }
        for key, sha in expected.items():
            receipt = self.record[key]["receipt"]
            self.assertEqual(receipt["sha256"], sha)
            self.assertTrue(receipt["path"].startswith("artifacts/firmware-analysis/"))
            self.assertGreater(receipt["size_bytes"], 0)
        self.assertEqual(self.record["inspection"]["analysis"]["sha256"],
                         "f979ef51db85fa97556d68bdd00140bf3a731024899441a0d5f2785caa5a84cb")
        self.assertTrue((ROOT / "docs/partition-metadata.md").is_file())

    def test_public_record_preserves_safety_and_contains_no_raw_guid_identifiers(self):
        for key, value in self.record["verification_boundaries"].items():
            with self.subTest(boundary=key):
                self.assertIs(value, False)
        encoded = json.dumps(self.record)
        self.assertNotRegex(encoded, r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}")
        self.assertNotIn("/Users/", encoded)
        self.assertNotIn("BEGIN PRIVATE KEY", encoded)
        self.assertEqual(self.record["references"][0]["url"],
                         "https://uefi.org/specs/UEFI/2.11/05_GUID_Partition_Table_Format.html")

    def test_strict_tar_corroboration_binds_the_unchanged_original_receipts(self):
        strict = self.record["strict_archive_corroboration"]
        self.assertEqual(strict["receipt"]["sha256"],
                         "362e50ef12a10ca2c648093e6049d170065bcad9490dbc1ac262fe1ba0016327")
        self.assertEqual(strict["original_metadata_receipt_sha256"],
                         self.record["capture"]["receipt"]["sha256"])
        self.assertEqual(strict["original_image_receipt_sha256"],
                         self.factory["extraction"]["receipt"]["sha256"])
        self.assertEqual(strict["member_count"], 127)
        self.assertEqual(strict["decompressed_archive_bytes"], 15325941760)
        self.assertEqual((strict["metadata_files_hashed"], strict["image_files_hashed"]), (37, 19))
        self.assertGreaterEqual(strict["trailing_zero_bytes_after_first_end_marker"], 512)
        self.assertEqual(strict["reader_fix_commit"], "7d1598150a166f738f83025f27ab7a370eb72397")
        for key in (
            "package_sha256_reverified", "package_identity_unchanged",
            "runtime_strict_header_policy_verified", "invalid_empty_truncated_headers_rejected",
            "all_zero_eof_header_retained", "tar_header_checksums_verified",
            "gzip_stream_crc_verified", "catalog_matches_both_original_receipts",
            "second_end_marker_and_zero_padding_verified", "original_receipts_unchanged",
        ):
            self.assertTrue(strict[key])
        for key in (
            "new_image_or_metadata_copies_created", "phone_accessed", "guest_accessed",
            "firmware_executed", "xml_instructions_applied", "images_mounted",
            "physical_phone_geometry_verified",
        ):
            self.assertFalse(strict[key])


if __name__ == "__main__":
    unittest.main()
