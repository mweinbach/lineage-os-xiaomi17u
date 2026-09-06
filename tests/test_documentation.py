"""Check local documentation links and sanitized baseline invariants."""

import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit

from support import walk_objects


ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_relative_documentation_links_exist(self):
        documents = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
        for document in documents:
            for target in re.findall(r"\]\(([^\s)]+)\)", document.read_text()):
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                with self.subTest(document=document.name, target=target):
                    self.assertTrue((document.parent / unquote(parsed.path)).exists())

    def test_sanitized_baseline_retains_provenance_and_known_gaps(self):
        baseline = json.loads((ROOT / "research/device-baseline.json").read_text())
        self.assertEqual(baseline["device"]["codename"], "nezha")
        self.assertEqual(baseline["device"]["reported_hwc"], "CN")
        self.assertEqual(baseline["firmware"]["page_size_bytes"], 4096)
        self.assertEqual(baseline["collection"]["status"], "partial")
        self.assertEqual(len(baseline["collection"]["unavailable_reads"]), 3)
        self.assertEqual(baseline["evolution_x_hardware_testing"], "not performed")
        self.assertIn("unverified", baseline["boot_state"]["actual_bootloader_state"])
        self.assertRegex(baseline["collection"]["camera_apk_sha256"], r"^[a-f0-9]{64}$")

    def test_sanitized_baseline_does_not_contain_personal_identifier_fields(self):
        baseline = json.loads((ROOT / "research/device-baseline.json").read_text())
        forbidden = {"serial", "serialno", "imei", "imsi", "meid", "account", "email", "phone_number"}

        for item in walk_objects(baseline):
            self.assertFalse(forbidden.intersection(item))

    def test_firmware_layout_retains_modified_origin_and_build_gates(self):
        layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        self.assertEqual(layout["schema_version"], 1)
        self.assertEqual(layout["device"], {"codename": "nezha", "hardware_region": "CN"})
        package = layout["package"]
        self.assertEqual(package["source_kind"], "user-provided")
        self.assertIsNone(package["source_url"])
        self.assertFalse(package["origin_verified"])
        self.assertIn("modified", package["distribution"])
        self.assertTrue(package["original_retained"])
        self.assertTrue(package["original_and_intake_copy_hashes_verified"])
        self.assertEqual(package["archive_crc_entries_verified"], package["archive_entry_count"])
        self.assertEqual(package["image_member_crcs_verified"], package["image_members_extracted"])
        self.assertFalse(package["installers_extracted_or_executed"])
        self.assertNotEqual(package["declared_build"], package["embedded_incremental"])
        gates = layout["verification_boundaries"]
        self.assertEqual(gates["publisher_authenticity"], "unverified")
        for key in ("signed_flashable_partition_set", "approved_for_boardconfig",
                    "full_evolution_x_build_tested", "evolution_x_hardware_tested",
                    "phone_modifications_performed", "missing_bytes_may_be_synthesized"):
            self.assertIs(gates[key], False)
        self.assertIsNone(gates["lunch_target"])

    def test_firmware_layout_sparse_geometry_and_provenance_are_consistent(self):
        layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        sparse, raw = layout["sparse_representation"], layout["raw_image"]
        self.assertEqual(sparse["version"], "1.0")
        self.assertEqual(sparse["piece_count"], len(sparse["pieces"]))
        self.assertEqual([piece["name"] for piece in sparse["pieces"]],
                         [f"super.img.{index}" for index in range(15)])
        self.assertEqual(sparse["block_size_bytes"] * sparse["total_blocks_per_piece"], raw["size_bytes"])
        self.assertEqual(sparse["expanded_size_bytes"], raw["size_bytes"])
        self.assertEqual(sparse["written_bytes"] + sparse["unwritten_zero_bytes"], raw["size_bytes"])
        self.assertEqual(sum(sparse["chunk_counts"].values()),
                         sum(piece["total_chunks"] for piece in sparse["pieces"]))
        self.assertEqual(sparse["write_range_count"], sparse["chunk_counts"]["raw"] + sparse["chunk_counts"]["fill"])
        self.assertTrue(sparse["all_header_checksums_zero"])
        self.assertEqual(sparse["crc32_chunk_count"], 0)
        self.assertTrue(sparse["independent_implementations_match"])
        self.assertTrue(sparse["inputs_match_archive_extraction_receipt"])
        self.assertEqual(raw["parent_package_sha256"], layout["package"]["sha256"])
        for record in (layout["package"], raw, *sparse["pieces"]):
            self.assertRegex(record["sha256"], r"^[a-f0-9]{64}$")
            self.assertGreater(record["size_bytes"], 0)

    def test_firmware_layout_metadata_copies_and_table_boundaries(self):
        layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        metadata = layout["logical_metadata"]
        geometry, header = metadata["geometry"], metadata["header"]
        self.assertEqual(metadata["version"], "10.2")
        self.assertTrue(metadata["all_geometry_checksums_valid"])
        self.assertTrue(metadata["geometry_copies_identical"])
        self.assertEqual(metadata["geometry_copy_offsets_bytes"], [4096, 8192])
        self.assertEqual(geometry["struct_size"], 52)
        self.assertEqual(geometry["metadata_region_end"],
                         12288 + 2 * geometry["metadata_max_size"] * geometry["metadata_slot_count"])
        self.assertEqual(len(metadata["slots"]), geometry["metadata_slot_count"])
        self.assertTrue(metadata["all_slots_identical"])
        self.assertEqual(header["flags"], 1)
        self.assertTrue(header["virtual_ab_device"])
        self.assertFalse(header["overlays_active"])
        self.assertEqual(header["unknown_flags"], 0)
        self.assertLessEqual(header["header_size"] + header["tables_size"], geometry["metadata_max_size"])
        self.assertRegex(metadata["geometry_checksum_sha256"], r"^[a-f0-9]{64}$")
        self.assertRegex(header["header_checksum_sha256"], r"^[a-f0-9]{64}$")
        self.assertRegex(header["tables_checksum_sha256"], r"^[a-f0-9]{64}$")
        for index, slot in enumerate(metadata["slots"]):
            self.assertEqual(slot["slot"], index)
            self.assertEqual(slot["primary_offset"], 12288 + index * geometry["metadata_max_size"])
            self.assertEqual(slot["backup_offset"],
                             slot["primary_offset"] + geometry["metadata_slot_count"] * geometry["metadata_max_size"])
            for key in ("primary_checksum_valid", "backup_checksum_valid", "copies_identical"):
                self.assertTrue(slot[key])
            self.assertRegex(slot["metadata_sha256"], r"^[a-f0-9]{64}$")
        cursor = 0
        for table in sorted(metadata["tables"].values(), key=lambda item: item["offset"]):
            self.assertEqual(table["offset"], cursor)
            cursor += table["num_entries"] * table["entry_size"]
        self.assertEqual(cursor, header["tables_size"])

    def test_firmware_layout_partition_extents_and_hashes(self):
        layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        metadata = layout["logical_metadata"]
        partitions = layout["partitions"]
        self.assertEqual(len(partitions), metadata["tables"]["partitions"]["num_entries"])
        self.assertEqual(len({partition["name"] for partition in partitions}), 16)
        self.assertEqual(len(metadata["physical_devices"]), 1)
        device = metadata["physical_devices"][0]
        self.assertEqual(device["size_bytes"], layout["raw_image"]["size_bytes"])
        self.assertGreaterEqual(device["first_logical_sector"] * 512, metadata["geometry"]["metadata_region_end"])
        groups = {group["index"]: group for group in metadata["groups"]}
        group_totals = {index: 0 for index in groups}
        physical_ranges = []
        for partition in partitions:
            with self.subTest(partition=partition["name"]):
                self.assertRegex(partition["name"], r"^[a-z_]+_[ab]$")
                self.assertEqual(partition["attributes"], 1)
                self.assertEqual(partition["group_name"], groups[partition["group_index"]]["name"])
                group_totals[partition["group_index"]] += partition["size_bytes"]
                total = 0
                for extent in partition["extents"]:
                    self.assertEqual(extent["target_type_name"], "LINEAR")
                    self.assertEqual(extent["target_source"], 0)
                    self.assertEqual(extent["physical_offset_bytes"], extent["target_data"] * 512)
                    start = extent["physical_offset_bytes"]
                    end = start + extent["num_sectors"] * 512
                    self.assertGreaterEqual(start, device["first_logical_sector"] * 512)
                    self.assertLessEqual(end, device["size_bytes"])
                    physical_ranges.append((start, end))
                    total += extent["num_sectors"] * 512
                self.assertEqual(total, partition["size_bytes"])
                extraction = partition["extraction"]
                if partition["name"].endswith("_a"):
                    self.assertGreater(total, 0)
                    self.assertEqual(extraction["status"], "extracted")
                    self.assertRegex(extraction["sha256"], r"^[a-f0-9]{64}$")
                    self.assertEqual(extraction["parent_image_sha256"], layout["raw_image"]["sha256"])
                    self.assertTrue(extraction["readback_verified"])
                    self.assertTrue(extraction["independent_extractor_matches"])
                    self.assertEqual(partition["filesystem"]["format"], "EROFS")
                    self.assertEqual(partition["filesystem"]["read_only_integrity_exit_code"], 0)
                else:
                    self.assertEqual(total, 0)
                    self.assertEqual(partition["extents"], [])
                    self.assertEqual(extraction["status"], "not_extracted_empty")
                    self.assertIsNone(extraction["sha256"])
                    self.assertIsNone(partition["filesystem"])
        previous_end = 0
        for start, end in sorted(physical_ranges):
            self.assertGreaterEqual(start, previous_end)
            previous_end = end
        self.assertEqual(len(physical_ranges), metadata["tables"]["extents"]["num_entries"])
        for index, group in groups.items():
            self.assertEqual(group["allocated_size"], group_totals[index])
            if group["maximum_size"]:
                self.assertLessEqual(group_totals[index], group["maximum_size"])
        self.assertTrue(metadata["on_disk_names_retained"])
        self.assertFalse(metadata["empty_b_extents_imply_physical_partition_absence"])

    def test_firmware_layout_integrity_success_does_not_hide_avb_failures(self):
        layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        filesystem = layout["filesystem_validation"]
        self.assertEqual(filesystem["command_flags"], ["--extract"])
        self.assertFalse(filesystem["destination_argument_provided"])
        self.assertFalse(filesystem["file_extraction_requested"])
        self.assertTrue(filesystem["superblock_checksum_checks_enabled"])
        self.assertTrue(filesystem["all_exit_codes_zero"])
        self.assertEqual(filesystem["verified_image_count"], 8)
        self.assertFalse(filesystem["publisher_authenticity_verified"])
        self.assertRegex(filesystem["tool_sha256"], r"^[a-f0-9]{64}$")
        gates = layout["verification_boundaries"]
        self.assertEqual(gates["avb_partition_set_status"], "failed")
        self.assertFalse(gates["vendor_boot_content_digest_matches"])
        self.assertFalse(gates["first_stage_fstab_avb_or_verify_flags_present"])
        partitions = {partition["name"]: partition for partition in layout["partitions"]}
        descriptors = gates["logical_avb_descriptor_ranges"]
        self.assertEqual(len(descriptors), 8)
        for descriptor in descriptors:
            self.assertEqual(descriptor["actual_size_bytes"], partitions[descriptor["partition"]]["size_bytes"])
            self.assertFalse(descriptor["complete_declared_hashtree_present"])
            self.assertFalse(descriptor["complete_declared_fec_present"])
        product = next(item for item in descriptors if item["partition"] == "product_a")
        self.assertLess(product["actual_size_bytes"], product["descriptor_data_size_bytes"])

    def test_firmware_layout_keeps_physical_geometry_unresolved(self):
        layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        physical = layout["physical_partition_geometry"]
        self.assertEqual(physical["status"], "unresolved")
        self.assertFalse(physical["package_image_lengths_are_physical_partition_sizes"])
        self.assertTrue(layout["logical_metadata"]["physical_device_sizes_are_metadata_declarations"])
        attempt = physical["read_only_attempt"]
        self.assertEqual(attempt["command_count"], attempt["partition_count"] * len(attempt["requested_fields"]))
        self.assertEqual(attempt["successful_reads"], 0)
        self.assertEqual(attempt["failure"], "Permission denied")
        self.assertFalse(attempt["privilege_escalation_performed"])

    def test_firmware_layout_documented_hashes_and_tool_pins(self):
        layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        document = (ROOT / "docs/firmware-analysis.md").read_text()
        self.assertIn(layout["package"]["sha256"], document)
        self.assertIn(layout["raw_image"]["sha256"], document)
        for partition in layout["partitions"]:
            if partition["extraction"]["status"] == "extracted":
                self.assertIn(partition["extraction"]["sha256"], document)
        for reference in layout["tool_references"].values():
            self.assertRegex(reference.get("workspace_commit", reference.get("commit")), r"^[a-f0-9]{40}$")
            if "script" in reference:
                self.assertTrue((ROOT / reference["script"]).is_file())
        config = json.loads((ROOT / "config/sources.json").read_text())
        extract_utils = next(reference for reference in config["references"] if reference["name"] == "extract-utils")
        self.assertEqual(layout["tool_references"]["independent_extract_utils"]["commit"], extract_utils["commit"])

    def test_firmware_layout_contains_no_private_identifiers_or_absolute_paths(self):
        layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        forbidden = {"serial", "serialno", "device_serial", "imei", "imsi", "meid", "account",
                     "email", "phone_number", "private_key", "public_key", "key_blob", "raw_blob",
                     "inode", "mtime_ns", "ctime_ns"}

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
            elif isinstance(value, str):
                self.assertFalse(value.startswith("/"))
                self.assertNotIn("/Users/", value)
                self.assertNotIn("/home/", value)
                self.assertNotIn("-----BEGIN", value)
                self.assertNotIn("..", Path(value).parts)
                self.assertLessEqual(len(value), 512)

        check(layout)
        self.assertTrue(layout["evidence"]["private_analysis_root"].startswith("artifacts/"))
        self.assertTrue(layout["evidence"]["physical_geometry_receipt"].startswith("evidence/"))


if __name__ == "__main__":
    unittest.main()
