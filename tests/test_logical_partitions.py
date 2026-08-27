"""Offline LP format fixtures; no checkout, phone, mount, or executable required."""

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "logical_partitions", Path(__file__).resolve().parents[1] / "scripts" / "logical_partitions.py"
)
lp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lp)

IMAGE_SIZE = 256 * 1024
METADATA_SIZE = 4096
SLOTS = 3
DATA_OFFSET = 40960
VENDOR_DATA = bytes(range(256)) * 16
ODM_DATA = b"odm-data" * 512


def padded(name: str) -> bytes:
    return name.encode("ascii").ljust(36, b"\0")


def geometry(*, maximum=METADATA_SIZE, slots=SLOTS, block_size=4096) -> bytes:
    value = bytearray(struct.pack("<II32sIII", 0x616C4467, 52, bytes(32), maximum, slots, block_size))
    value[8:40] = hashlib.sha256(value).digest()
    return bytes(value)


def metadata(*, partitions=None, extents=None, groups=None, devices=None, minor=2,
             flags=1, table_order=("partitions", "extents", "groups", "block_devices")) -> bytes:
    # Group 2 owns _a in metadata slot 0, deliberately not slot + 1.
    if partitions is None:
        partitions = [(padded("vendor_a"), 1, 0, 2, 2),
                      (padded("odm_a"), 1, 2, 1, 2),
                      (padded("vendor_b"), 1, 3, 0, 1)]
    if extents is None:
        extents = [(8, 0, 80, 0), (8, 1, 0, 0), (8, 0, 88, 0)]
    if groups is None:
        groups = [(padded("default"), 0, 0), (padded("qti_b"), 0, 65536), (padded("qti_a"), 0, 65536)]
    if devices is None:
        devices = [(80, 4096, 0, IMAGE_SIZE, padded("super"), 0)]
    formats = {"partitions": ("<36sIIII", partitions), "extents": ("<QIQI", extents),
               "groups": ("<36sIQ", groups), "block_devices": ("<QIIQ36sI", devices)}
    tables = bytearray()
    descriptors = {}
    for name in table_order:
        fmt, rows = formats[name]
        descriptors[name] = struct.pack("<III", len(tables), len(rows), struct.calcsize(fmt))
        for row in rows:
            tables.extend(struct.pack(fmt, *row))
    header_size = 256 if minor >= 2 else 128
    header = bytearray(struct.pack("<IHHI32sI32s", 0x414C5030, 10, minor, header_size,
                                   bytes(32), len(tables), hashlib.sha256(tables).digest()))
    for name in formats:
        header.extend(descriptors[name])
    if minor >= 2:
        header.extend(struct.pack("<I", flags) + bytes(124))
    header[12:44] = hashlib.sha256(header).digest()
    return bytes(header + tables)


def rewrite_header(blob: bytes, offset: int, fmt: str, value: int, *, checksum=True) -> bytes:
    result = bytearray(blob)
    header_size = struct.unpack_from("<I", result, 8)[0]
    struct.pack_into(fmt, result, offset, value)
    if checksum:
        result[12:44] = bytes(32)
        result[12:44] = hashlib.sha256(result[:header_size]).digest()
    return bytes(result)


def rewrite_geometry(blob: bytes, offset: int, value: int, *, checksum=True) -> bytes:
    result = bytearray(blob)
    struct.pack_into("<I", result, offset, value)
    if checksum:
        result[8:40] = bytes(32)
        result[8:40] = hashlib.sha256(result).digest()
    return bytes(result)


class LogicalPartitionsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        # macOS /var and /tmp can be symlinks; tests use their actual location.
        self.root = Path(self.temporary.name).resolve()
        self.root_patch = mock.patch.object(lp, "WORKSPACE_ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.path = self.root / "super.raw.img"
        self.output = self.root / "artifacts" / "extracted"

    def write_image(self, *, data=None, geometries=None, copies=None):
        image = bytearray(IMAGE_SIZE)
        for index, value in enumerate(geometries or (geometry(), geometry())):
            image[4096 + index * 4096:4096 + index * 4096 + len(value)] = value
        data = metadata() if data is None else data
        for copy in range(2):
            for slot in range(SLOTS):
                value = (copies or {}).get((copy, slot), data)
                offset = 12288 + (copy * SLOTS + slot) * METADATA_SIZE
                image[offset:offset + len(value)] = value
        image[DATA_OFFSET:DATA_OFFSET + 4096] = VENDOR_DATA
        image[DATA_OFFSET + 4096:DATA_OFFSET + 8192] = ODM_DATA
        self.path.write_bytes(image)
        return hashlib.sha256(image).hexdigest()

    def inspect(self):
        return lp.inspect_image(self.path)

    def extract(self, names=None, *, slot=0, output=None, expected=None):
        return lp.extract_image(self.path, expected or hashlib.sha256(self.path.read_bytes()).hexdigest(),
                                slot, names or ["vendor_a"], output or self.output)

    def assert_invalid(self, text):
        report = self.inspect()
        self.assertFalse(report["valid"], report)
        self.assertFalse(report["extraction_supported"])
        self.assertIn(text, "\n".join(report["errors"]))
        with self.assertRaises(lp.LogicalPartitionError):
            self.extract()
        self.assertFalse(self.output.exists())
        return report

    def test_inspects_all_geometry_and_metadata_copies(self):
        digest = self.write_image()
        before = self.path.stat()
        report = self.inspect()
        after = self.path.stat()
        self.assertTrue(report["valid"])
        self.assertTrue(report["extraction_supported"])
        self.assertTrue(report["geometry_copies_match"])
        self.assertEqual(report["image"]["sha256"], digest)
        self.assertEqual(len(report["slots"]), 3)
        self.assertTrue(report["all_slots_identical"])
        self.assertEqual(before.st_ino, after.st_ino)
        self.assertEqual(before.st_mtime_ns, after.st_mtime_ns)
        self.assertEqual(before.st_ctime_ns, after.st_ctime_ns)
        for index, entry in enumerate(report["slots"]):
            self.assertEqual(entry["slot"], index)
            self.assertTrue(entry["copies_match"])
            self.assertEqual(entry["primary"]["offset"], 12288 + index * 4096)
            self.assertEqual(entry["backup"]["offset"], 12288 + (index + 3) * 4096)
            for copy in (entry["primary"], entry["backup"]):
                self.assertTrue(copy["valid"])
                self.assertTrue(copy["header"]["checksum"]["valid"])
                self.assertTrue(copy["header"]["tables_checksum"]["valid"])
                self.assertTrue(copy["header"]["virtual_ab_device"])
                self.assertEqual(copy["groups"][2]["maximum_size"], 65536)
                self.assertEqual(copy["groups"][2]["allocated_size"], 12288)
                self.assertEqual(copy["block_devices"][0]["partition_name"], "super")
                self.assertEqual(copy["extents"][1]["target_type_name"], "ZERO")
                self.assertEqual(copy["partitions"][0]["group_index"], 2)
        json.dumps(report)

    def test_extracts_linear_zero_and_empty_partitions_with_hashes(self):
        digest = self.write_image()
        receipt = self.extract(["vendor_a", "odm_a", "vendor_b"])
        self.assertEqual(receipt["status"], "complete")
        self.assertEqual((self.output / "vendor_a.img").read_bytes(), VENDOR_DATA + bytes(4096))
        self.assertEqual((self.output / "odm_a.img").read_bytes(), ODM_DATA)
        self.assertEqual((self.output / "vendor_b.img").read_bytes(), b"")
        self.assertEqual(receipt, json.loads((self.output / "receipt.json").read_text()))
        self.assertFalse(receipt["authentication_verified"])
        self.assertEqual(self.path.read_bytes()[DATA_OFFSET:DATA_OFFSET + 4096], VENDOR_DATA)
        for output in receipt["outputs"]:
            content = (self.output / output["filename"]).read_bytes()
            self.assertEqual(output["parent_image_sha256"], digest)
            self.assertEqual(output["sha256"], hashlib.sha256(content).hexdigest())
            self.assertEqual(output["size_bytes"], len(content))
            self.assertTrue(output["readback_verified"])
            self.assertEqual((self.output / output["filename"]).stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.output.stat().st_mode & 0o777, 0o700)

    def test_versions_10_0_and_10_1_have_short_headers(self):
        for minor in (0, 1):
            with self.subTest(minor=minor):
                self.write_image(data=metadata(minor=minor))
                report = self.inspect()
                self.assertTrue(report["valid"], report["errors"])
                self.assertEqual(report["slots"][0]["primary"]["header"]["header_size"], 128)
                self.assertEqual(report["slots"][0]["primary"]["header"]["flags"], 0)

    def test_tables_can_be_serialized_in_another_order(self):
        self.write_image(data=metadata(table_order=("block_devices", "extents", "groups", "partitions")))
        self.assertTrue(self.inspect()["valid"])
        self.extract()
        self.assertEqual((self.output / "vendor_a.img").read_bytes(), VENDOR_DATA + bytes(4096))

    def test_slot_selection_does_not_assume_partition_group_index(self):
        changed = metadata(partitions=[(padded("only_here"), 1, 0, 3, 0)])
        self.write_image(copies={(0, 2): changed, (1, 2): changed})
        report = self.inspect()
        self.assertTrue(report["valid"])
        self.assertFalse(report["all_slots_identical"])
        receipt = self.extract(["only_here"], slot=2)
        self.assertEqual(receipt["metadata_slot"], 2)
        self.assertEqual((self.output / "only_here.img").read_bytes(), VENDOR_DATA + bytes(4096) + ODM_DATA)

    def test_slot_suffix_flags_are_reported_without_renaming(self):
        self.write_image(data=metadata(partitions=[(padded("vendor"), 3, 0, 3, 0)]))
        report = self.inspect()
        self.assertTrue(report["names_are_on_disk"])
        self.assertTrue(report["slots"][0]["primary"]["partitions"][0]["slot_suffixed"])
        with self.assertRaisesRegex(lp.LogicalPartitionError, "absent"):
            self.extract(["vendor_a"])
        self.extract(["vendor"])
        self.assertTrue((self.output / "vendor.img").is_file())

    def test_unknown_header_flags_are_reported_but_block_extraction(self):
        self.write_image(data=metadata(flags=0x83))
        report = self.inspect()
        self.assertTrue(report["valid"])
        header = report["slots"][0]["primary"]["header"]
        self.assertTrue(header["overlays_active"])
        self.assertEqual(header["unknown_flags"], 0x80)
        self.assertFalse(report["extraction_supported"])
        with self.assertRaisesRegex(lp.LogicalPartitionError, "unknown header flags"):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_active_overlays_block_extraction_without_hiding_metadata(self):
        self.write_image(data=metadata(flags=3))
        report = self.inspect()
        self.assertTrue(report["valid"])
        self.assertFalse(report["extraction_supported"])
        with self.assertRaisesRegex(lp.LogicalPartitionError, "active overlays"):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_padding_outside_checksummed_structs_does_not_create_disagreement(self):
        self.write_image()
        with self.path.open("r+b") as stream:
            stream.seek(8192 + 52)
            stream.write(b"geometry-padding")
            stream.seek(12288 + 3 * 4096 + len(metadata()))
            stream.write(b"slot-padding")
        self.assertTrue(self.inspect()["valid"])

    def test_geometry_magic_and_struct_size(self):
        for offset, value, expected in ((0, 0, "geometry magic"), (4, 4096, "struct size"), (4, 0, "struct size")):
            with self.subTest(offset=offset, value=value):
                bad = rewrite_geometry(geometry(), offset, value)
                self.write_image(geometries=(bad, bad))
                self.assert_invalid(expected)

    def test_geometry_checksum_failure_is_reported_and_backup_does_not_enable_extraction(self):
        bad = bytearray(geometry())
        bad[8] ^= 1
        self.write_image(geometries=(bytes(bad), geometry()))
        report = self.assert_invalid("geometry SHA256 checksum")
        self.assertFalse(report["geometry_copies"]["primary"]["checksum"]["valid"])
        self.assertEqual(report["selected_geometry_copy"], "backup")
        self.assertEqual(len(report["slots"]), 3)

    def test_geometry_disagreement_blocks_extraction(self):
        self.write_image(geometries=(geometry(), geometry(block_size=512)))
        self.assert_invalid("geometry disagree")

    def test_geometry_resource_and_alignment_limits(self):
        cases = [("maximum", 0), ("maximum", 513), ("maximum", lp.MAX_METADATA_BYTES + 512),
                 ("slots", 0), ("slots", lp.MAX_METADATA_SLOTS + 1),
                 ("block_size", 0), ("block_size", 513), ("block_size", lp.MAX_LOGICAL_BLOCK_SIZE + 512)]
        for name, value in cases:
            with self.subTest(name=name, value=value):
                bad = geometry(**{name: value})
                self.write_image(geometries=(bad, bad))
                self.assertFalse(self.inspect()["valid"])

    def test_geometry_metadata_region_cannot_exceed_raw_image(self):
        self.write_image(geometries=(geometry(maximum=65536),) * 2)
        self.assert_invalid("metadata slots extend outside")

    def test_geometry_metadata_region_resource_limit(self):
        self.write_image()
        with mock.patch.object(lp, "MAX_METADATA_REGION_BYTES", 32768):
            self.assert_invalid("metadata resource limit")

    def test_metadata_magic_versions_and_header_sizes(self):
        for offset, fmt, value, error in ((0, "<I", 0, "metadata magic"),
                                         (4, "<H", 9, "unsupported metadata version"),
                                         (4, "<H", 11, "unsupported metadata version"),
                                         (6, "<H", 3, "unsupported metadata version"),
                                         (8, "<I", 128, "header size")):
            with self.subTest(offset=offset, value=value):
                self.write_image(data=rewrite_header(metadata(), offset, fmt, value))
                self.assert_invalid(error)

    def test_header_checksum_failure_is_recorded(self):
        self.write_image(data=rewrite_header(metadata(), 128, "<I", 0, checksum=False))
        report = self.assert_invalid("header SHA256 checksum")
        self.assertFalse(report["slots"][0]["primary"]["header"]["checksum"]["valid"])

    def test_tables_checksum_failure_is_recorded(self):
        bad = bytearray(metadata())
        bad[-1] ^= 1
        self.write_image(data=bytes(bad))
        report = self.assert_invalid("tables SHA256 checksum")
        self.assertFalse(report["slots"][0]["primary"]["header"]["tables_checksum"]["valid"])

    def test_primary_backup_metadata_disagreement_in_any_slot_blocks_extraction(self):
        self.write_image(copies={(1, 2): metadata(flags=3)})
        report = self.assert_invalid("slot 2 primary and backup metadata disagree")
        self.assertFalse(report["slots"][2]["copies_match"])

    def test_corrupt_unselected_backup_is_not_ignored(self):
        self.write_image(copies={(1, 1): bytes(len(metadata()))})
        self.assert_invalid("slot 1 backup: invalid metadata magic")

    def test_header_plus_tables_must_fit_inside_one_slot(self):
        # AOSP table size alone is insufficient: the header consumes slot bytes too.
        self.write_image(data=rewrite_header(metadata(), 44, "<I", METADATA_SIZE))
        self.assert_invalid("extend past this metadata slot")

    def test_expanded_header_reserved_bytes_must_be_zero(self):
        self.write_image(data=rewrite_header(metadata(), 132, "<I", 1))
        self.assert_invalid("reserved bytes")

    def test_all_table_entry_sizes_are_checked(self):
        for offset in (88, 100, 112, 124):
            with self.subTest(offset=offset):
                self.write_image(data=rewrite_header(metadata(), offset, "<I", 1))
                self.assert_invalid("entry size")

    def test_table_count_and_bounds_are_checked(self):
        for offset, value, error in ((84, lp.MAX_TABLE_ENTRIES + 1, "entry count"),
                                     (80, 0xFFFFFFFF, "table region"),
                                     (96, 1000, "table region")):
            with self.subTest(offset=offset):
                self.write_image(data=rewrite_header(metadata(), offset, "<I", value))
                self.assert_invalid(error)

    def test_overlapping_or_gapped_tables_are_rejected(self):
        for value in (0, 1):
            with self.subTest(value=value):
                self.write_image(data=rewrite_header(metadata(), 92, "<I", value))
                self.assert_invalid("overlaps another table or leaves a gap")

    def test_unsafe_partition_names_and_padding_are_rejected(self):
        for name in (padded("../vendor"), padded("vendor_a.img"), padded(""), b"v\0x" + bytes(33),
                     bytes([255]) + bytes(35), padded("vendor\\a"), padded("a/b")):
            with self.subTest(name=name):
                self.write_image(data=metadata(partitions=[(name, 1, 0, 3, 0)]))
                self.assert_invalid("name")

    def test_full_36_character_name_is_supported(self):
        name = "x" * 36
        self.write_image(data=metadata(partitions=[(name.encode(), 1, 0, 3, 0)]))
        self.extract([name])
        self.assertTrue((self.output / (name + ".img")).is_file())

    def test_duplicate_and_case_colliding_names_are_rejected(self):
        for name in ("vendor_a", "VENDOR_A"):
            with self.subTest(name=name):
                self.write_image(data=metadata(partitions=[(padded("vendor_a"), 1, 0, 2, 2),
                                                          (padded(name), 1, 2, 1, 1)]))
                self.assert_invalid("case-colliding")

    def test_partition_indices_attributes_and_extent_ownership(self):
        cases = [([(padded("vendor_a"), 16, 0, 3, 0)], "attributes"),
                 ([(padded("vendor_a"), 1, 4, 0, 0)], "extent range"),
                 ([(padded("vendor_a"), 1, 0, 4, 0)], "extent range"),
                 ([(padded("vendor_a"), 1, 0, 3, 3)], "group index"),
                 ([(padded("vendor_a"), 1, 0, 2, 0)], "without a partition owner"),
                 ([(padded("vendor_a"), 1, 0, 3, 0), (padded("odm_a"), 1, 0, 1, 0)], "shares extent")]
        for partitions, error in cases:
            with self.subTest(error=error):
                self.write_image(data=metadata(partitions=partitions))
                self.assert_invalid(error)

    def test_updated_attribute_requires_version_10_1(self):
        self.write_image(data=metadata(minor=0, partitions=[(padded("vendor_a"), 5, 0, 3, 0)]))
        self.assert_invalid("attributes unsupported")
        self.write_image(data=metadata(minor=1, partitions=[(padded("vendor_a"), 5, 0, 3, 0)]))
        self.assertTrue(self.inspect()["valid"])

    def test_disabled_partitions_are_reported_but_cannot_be_extracted(self):
        self.write_image(data=metadata(partitions=[(padded("vendor_a"), 9, 0, 3, 0)]))
        self.assertTrue(self.inspect()["valid"])
        with self.assertRaisesRegex(lp.LogicalPartitionError, "marked disabled"):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_linear_extents_must_fit_matching_physical_device(self):
        cases = [((8, 0, 80, 1), "block device index"),
                 ((8, 0, 0, 0), "before its block device"),
                 ((8, 0, IMAGE_SIZE // 512 - 4, 0), "past its block device"),
                 ((2**63, 0, 80, 0), "excessive length"),
                 ((0, 0, 80, 0), "empty or excessive length"),
                 ((1, 0, 80, 0), "logical block size"),
                 ((8, 2, 80, 0), "unsupported target type")]
        for value, error in cases:
            with self.subTest(error=error):
                self.write_image(data=metadata(extents=[value, (8, 1, 0, 0), (8, 0, 88, 0)]))
                self.assert_invalid(error)

    def test_zero_extents_require_zero_source_and_data(self):
        for value in ((8, 1, 1, 0), (8, 1, 0, 1)):
            with self.subTest(value=value):
                self.write_image(data=metadata(extents=[(8, 0, 80, 0), value, (8, 0, 88, 0)]))
                self.assert_invalid("ZERO extent 1 has nonzero target fields")

    def test_physical_extent_overlap_is_rejected(self):
        self.write_image(data=metadata(extents=[(8, 0, 80, 0), (8, 1, 0, 0), (8, 0, 84, 0)]))
        self.assert_invalid("overlaps another extent")

    def test_group_size_limits_flags_names_and_presence(self):
        cases = [([(padded("default"), 0, 0), (padded("qti_b"), 0, 65536), (padded("qti_a"), 0, 4096)], "exceeds its maximum"),
                 ([(padded("default"), 2, 0)], "unsupported flags"),
                 ([(padded("../../unsafe"), 0, 0)], "unsafe name"),
                 ([(padded("default"), 0, 0), (padded("DEFAULT"), 0, 0)], "case-colliding"),
                 ([], "no partition groups")]
        for groups, error in cases:
            with self.subTest(error=error):
                self.write_image(data=metadata(groups=groups))
                self.assert_invalid(error)

    def test_zero_group_maximum_means_unlimited(self):
        self.write_image(data=metadata(groups=[(padded("default"), 0, 0)],
                                       partitions=[(padded("vendor_a"), 1, 0, 3, 0)]))
        self.assertTrue(self.inspect()["valid"])

    def test_physical_devices_metadata_overlap_size_and_alignment(self):
        cases = [((1, 4096, 0, IMAGE_SIZE, padded("super"), 0), "overlaps reserved"),
                 ((80, 4096, 0, IMAGE_SIZE - 512, padded("super"), 0), "does not match"),
                 ((80, 4096, 0, IMAGE_SIZE + 512, padded("super"), 0), "does not match"),
                 ((80, 4096, 0, IMAGE_SIZE + 1, padded("super"), 0), "invalid size"),
                 ((IMAGE_SIZE // 512 + 1, 4096, 0, IMAGE_SIZE, padded("super"), 0), "starts past"),
                 ((80, 4097, 0, IMAGE_SIZE, padded("super"), 0), "unaligned alignment"),
                 ((80, 4096, 1, IMAGE_SIZE, padded("super"), 0), "unaligned alignment"),
                 ((80, 4096, 4096, IMAGE_SIZE, padded("super"), 0), "alignment offset"),
                 ((80, 0, 512, IMAGE_SIZE, padded("super"), 0), "alignment offset"),
                 ((80, 4096, 0, IMAGE_SIZE, padded("../super"), 0), "unsafe name"),
                 ((80, 4096, 0, IMAGE_SIZE, padded("super"), 2), "unsupported flags")]
        for value, error in cases:
            with self.subTest(error=error):
                self.write_image(data=metadata(devices=[value]))
                self.assert_invalid(error)
        self.write_image(data=metadata(devices=[]))
        self.assert_invalid("does not declare a super block device")

    def test_multidevice_metadata_is_inspected_but_extraction_is_unsupported(self):
        devices = [(80, 4096, 0, IMAGE_SIZE, padded("super"), 0),
                   (0, 4096, 0, 8192, padded("other"), 0)]
        self.write_image(data=metadata(devices=devices, extents=[(8, 0, 0, 1), (8, 1, 0, 0), (8, 0, 88, 0)]))
        report = self.inspect()
        self.assertTrue(report["valid"])
        self.assertFalse(report["extraction_supported"])
        self.assertIn("one physical super device", report["extraction_constraints"][0])
        with self.assertRaisesRegex(lp.LogicalPartitionError, "one physical super device"):
            self.extract()
        self.assertFalse(self.output.exists())

    def test_other_device_extent_is_checked_against_its_own_size(self):
        devices = [(80, 4096, 0, IMAGE_SIZE, padded("super"), 0),
                   (0, 4096, 0, 4096, padded("other"), 0)]
        self.write_image(data=metadata(devices=devices, extents=[(16, 0, 0, 1), (8, 1, 0, 0), (8, 0, 88, 0)]))
        self.assert_invalid("past its block device")

    def test_duplicate_block_devices_are_rejected(self):
        devices = [(80, 4096, 0, IMAGE_SIZE, padded("super"), 0),
                   (0, 4096, 0, 4096, padded("SUPER"), 0)]
        self.write_image(data=metadata(devices=devices))
        self.assert_invalid("case-colliding")

    def test_expected_source_hash_is_required_for_extraction_and_never_trusted(self):
        self.write_image()
        for expected in (None, "", "not-a-hash", "a" * 64):
            with self.subTest(expected=expected):
                with self.assertRaises(lp.LogicalPartitionError):
                    lp.extract_image(self.path, expected, 0, ["vendor_a"], self.output)
                self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(lp.LogicalPartitionError, "does not match"):
            lp.inspect_image(self.path, "0" * 64)

    def test_uppercase_expected_hash_is_accepted(self):
        digest = self.write_image()
        self.assertTrue(lp.inspect_image(self.path, digest.upper())["valid"])

    def test_missing_duplicate_and_unsafe_selections_do_not_create_output(self):
        self.write_image()
        for names in ([], ["missing"], ["vendor_a", "missing"], ["vendor_a", "vendor_a"],
                      ["vendor_a", "VENDOR_A"], ["../vendor_a"], ["vendor_a.img"]):
            with self.subTest(names=names):
                with self.assertRaises(lp.LogicalPartitionError):
                    lp.extract_image(self.path, hashlib.sha256(self.path.read_bytes()).hexdigest(),
                                     0, names, self.output)
                self.assertFalse(self.output.exists())

    def test_invalid_slot_does_not_create_output(self):
        self.write_image()
        for slot in (-1, 3, True, "0"):
            with self.subTest(slot=slot):
                with self.assertRaises(lp.LogicalPartitionError):
                    self.extract(slot=slot)
                self.assertFalse(self.output.exists())

    def test_output_must_be_inside_a_private_root(self):
        self.write_image()
        for path in (self.root / "tracked", self.root / "artifacts", self.root.parent / "outside-lp-test",
                     self.root / "artifacts" / ".." / "escaped"):
            with self.subTest(path=path):
                with self.assertRaises(lp.LogicalPartitionError):
                    self.extract(output=path)
        self.assertFalse((self.root / "tracked").exists())
        self.assertFalse((self.root / "escaped").exists())

    def test_evidence_output_root_is_allowed(self):
        self.write_image()
        output = self.root / "evidence" / "logical" / "new"
        self.extract(output=output)
        self.assertTrue((output / "receipt.json").is_file())

    def test_existing_output_directory_and_file_are_never_overwritten(self):
        self.write_image()
        self.output.mkdir(parents=True)
        sentinel = self.output / "vendor_a.img"
        sentinel.write_bytes(b"keep existing evidence")
        with self.assertRaises(FileExistsError):
            self.extract()
        self.assertEqual(sentinel.read_bytes(), b"keep existing evidence")
        other = self.root / "artifacts" / "a-file"
        other.write_bytes(b"unchanged")
        with self.assertRaises(FileExistsError):
            self.extract(output=other)
        self.assertEqual(other.read_bytes(), b"unchanged")

    def test_input_symlink_and_symlink_ancestor_are_rejected(self):
        self.write_image()
        linked = self.root / "linked.img"
        linked.symlink_to(self.path)
        with self.assertRaises(OSError):
            lp.inspect_image(linked)
        directory = self.root / "linked-directory"
        directory.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(OSError):
            lp.inspect_image(directory / self.path.name)

    def test_output_symlink_and_symlink_ancestor_are_rejected(self):
        self.write_image()
        actual = self.root / "actual"
        actual.mkdir()
        self.output.parent.mkdir()
        self.output.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(OSError):
            self.extract()
        self.assertEqual(list(actual.iterdir()), [])
        ancestor = self.output.parent / "linked"
        ancestor.symlink_to(actual, target_is_directory=True)
        with self.assertRaises(OSError):
            self.extract(output=ancestor / "new")
        self.assertFalse((actual / "new").exists())

    def test_nonregular_inputs_do_not_block_or_read_devices(self):
        fifo = self.root / "a-pipe"
        os.mkfifo(fifo)
        with self.assertRaisesRegex(lp.LogicalPartitionError, "regular file"):
            lp.inspect_image(fifo)
        with self.assertRaises(lp.LogicalPartitionError):
            lp.inspect_image(self.root)

    def test_source_size_limits_and_sparse_input(self):
        self.path.write_bytes(bytes(512))
        with self.assertRaisesRegex(lp.LogicalPartitionError, "raw image size"):
            self.inspect()
        self.write_image()
        with mock.patch.object(lp, "MAX_IMAGE_BYTES", IMAGE_SIZE - 512):
            with self.assertRaisesRegex(lp.LogicalPartitionError, "raw image size"):
                self.inspect()
        with self.path.open("ab") as stream:
            stream.write(b"x")
        with self.assertRaisesRegex(lp.LogicalPartitionError, "sector-aligned"):
            self.inspect()
        self.write_image()
        with self.path.open("r+b") as stream:
            stream.write(struct.pack("<I", 0xED26FF3A))
        with self.assertRaisesRegex(lp.LogicalPartitionError, "Android sparse"):
            self.inspect()

    def test_source_mutation_is_detected(self):
        self.write_image()
        original_read = lp.RawImage.read
        changed = False

        def mutate(image, offset, size):
            nonlocal changed
            data = original_read(image, offset, size)
            if not changed and size > 4:
                changed = True
                with self.path.open("r+b") as stream:
                    stream.seek(DATA_OFFSET)
                    stream.write(b"changed")
            return data

        with mock.patch.object(lp.RawImage, "read", mutate):
            with self.assertRaisesRegex(lp.LogicalPartitionError, "source image changed"):
                self.extract()
        self.assertFalse(self.output.exists())

    def test_source_path_replacement_is_detected(self):
        self.write_image()
        with lp.RawImage(self.path) as image:
            replacement = self.root / "replacement.img"
            replacement.write_bytes(self.path.read_bytes())
            replacement.replace(self.path)
            with self.assertRaisesRegex(lp.LogicalPartitionError, "changed|replaced"):
                image.unchanged()

    def test_failure_during_extraction_has_no_success_receipt(self):
        self.write_image()
        with mock.patch.object(lp, "_verify_output", side_effect=lp.LogicalPartitionError("readback failed")):
            with self.assertRaisesRegex(lp.LogicalPartitionError, "readback failed"):
                self.extract()
        self.assertTrue(self.output.is_dir())
        self.assertFalse((self.output / "receipt.json").exists())
        self.assertEqual((self.output / "vendor_a.img").read_bytes(), VENDOR_DATA + bytes(4096))

    def test_source_mutation_during_extraction_has_no_success_receipt(self):
        self.write_image()
        original = lp._write_partition

        def mutate(*args):
            result = original(*args)
            with self.path.open("r+b") as stream:
                stream.seek(DATA_OFFSET)
                stream.write(b"modified")
            return result

        with mock.patch.object(lp, "_write_partition", mutate):
            with self.assertRaisesRegex(lp.LogicalPartitionError, "source image changed"):
                self.extract()
        self.assertFalse((self.output / "receipt.json").exists())

    def test_insufficient_disk_space_stops_before_partition_writes(self):
        self.write_image()
        space = mock.Mock(f_bavail=0, f_frsize=4096)
        with mock.patch.object(lp.os, "fstatvfs", return_value=space):
            with self.assertRaisesRegex(lp.LogicalPartitionError, "insufficient free disk"):
                self.extract()
        self.assertEqual(list(self.output.iterdir()), [])

    def test_file_creation_never_follows_symlink_or_truncates(self):
        self.output.mkdir(parents=True)
        sentinel = self.root / "sentinel"
        sentinel.write_bytes(b"private existing content")
        link = self.output / "vendor_a.img"
        link.symlink_to(sentinel)
        directory_fd = lp._directory_fd(self.output)
        try:
            with self.assertRaises(FileExistsError):
                lp._new_file(directory_fd, "vendor_a.img")
        finally:
            os.close(directory_fd)
        self.assertEqual(sentinel.read_bytes(), b"private existing content")

    def test_read_bounds_and_readback_verification(self):
        self.write_image()
        with lp.RawImage(self.path) as image:
            for offset, size in ((-1, 1), (0, -1), (IMAGE_SIZE, 1), (IMAGE_SIZE + 1, 0)):
                with self.subTest(offset=offset, size=size):
                    with self.assertRaises(lp.LogicalPartitionError):
                        image.read(offset, size)
            with mock.patch.object(lp, "MAX_METADATA_BYTES", 512):
                with self.assertRaisesRegex(lp.LogicalPartitionError, "bounded buffer"):
                    image.read(0, 1024)
        self.output.mkdir(parents=True)
        (self.output / "bad.img").write_bytes(b"wrong")
        directory_fd = lp._directory_fd(self.output)
        try:
            with self.assertRaisesRegex(lp.LogicalPartitionError, "SHA256 verification failed"):
                lp._verify_output(directory_fd, "bad.img", 5, "0" * 64)
        finally:
            os.close(directory_fd)

    def test_io_uses_bounded_reads_and_zero_writes(self):
        self.write_image()
        original = lp.RawImage.read
        sizes = []

        def measured(image, offset, size):
            sizes.append(size)
            return original(image, offset, size)

        with mock.patch.object(lp, "CHUNK_SIZE", 1024), mock.patch.object(lp.RawImage, "read", measured):
            self.extract()
        self.assertLessEqual(max(sizes), 4096)  # Geometry is fixed at one 4 KiB block.
        self.assertGreater(sizes.count(1024), 200)
        self.assertEqual((self.output / "vendor_a.img").read_bytes(), VENDOR_DATA + bytes(4096))

    def test_cli_inspection_and_extraction(self):
        digest = self.write_image()
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(lp.main(["inspect", "--image", str(self.path)]), 0)
        self.assertEqual(json.loads(out.getvalue())["image"]["sha256"], digest)
        out = io.StringIO()
        with redirect_stdout(out):
            code = lp.main(["extract", "--image", str(self.path), "--expected-sha256", digest,
                            "--slot", "0", "--partition", "vendor_a", "--partition", "odm_a",
                            "--output", str(self.output)])
        self.assertEqual(code, 0)
        self.assertEqual(len(json.loads(out.getvalue())["outputs"]), 2)

    def test_cli_invalid_metadata_returns_json_and_failure_exit_status(self):
        self.write_image(copies={(1, 0): bytes(len(metadata()))})
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(lp.main(["inspect", "--image", str(self.path)]), 2)
        self.assertFalse(json.loads(out.getvalue())["valid"])

    def test_cli_invalid_hash_is_clear_without_traceback(self):
        self.write_image()
        errors = io.StringIO()
        with redirect_stderr(errors):
            self.assertEqual(lp.main(["inspect", "--image", str(self.path), "--expected-sha256", "bad"]), 2)
        self.assertIn("expected SHA256", errors.getvalue())
        self.assertNotIn("Traceback", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
