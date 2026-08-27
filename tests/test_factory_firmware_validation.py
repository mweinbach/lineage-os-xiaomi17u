"""Offline consistency for separately verified factory image operations."""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"


class FactoryFirmwareValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/factory-firmware-validation.json").read_text())
        cls.intake = json.loads((ROOT / "research/factory-firmware-intake.json").read_text())

    def test_package_is_bound_without_inventing_an_origin(self):
        r = self.record
        self.assertEqual(r["package"]["sha256"], PACKAGE)
        self.assertEqual(r["package"]["size_bytes"], 12778943953)
        self.assertEqual(r["package"]["source_kind"], "user-provided")
        self.assertIsNone(r["package"]["source_url"])
        self.assertIsNone(r["package"]["independently_published_sha256"])
        self.assertFalse(r["package"]["origin_verified"])
        self.assertFalse(r["package"]["oem_key_authenticated"])
        ref = r["intake_record"]
        self.assertEqual(hashlib.sha256((ROOT / ref["path"]).read_bytes()).hexdigest(), ref["sha256"])
        self.assertEqual(r["archive_extraction_receipt"], self.intake["extraction"]["receipt"])

    def test_single_sparse_image_linkage_and_chunk_arithmetic(self):
        sparse = self.record["sparse_super"]
        source = sparse["input"]
        self.assertEqual(sparse["piece_count"], 1)
        self.assertEqual(source["name"], "super.img")
        self.assertTrue(sparse["not_byte_concatenated"])
        self.assertTrue(sparse["parent_extraction_linkage_verified"])
        image = next(row for row in self.intake["images"] if row["path"] == "super.img")
        self.assertEqual(source["sha256"], image["sha256"])
        self.assertEqual(source["size_bytes"], image["size_bytes"])
        self.assertEqual(sparse["input_archive_member"], image["archive_member"])
        self.assertEqual(source["chunk_counts"], {"raw": 198, "fill": 13, "dont_care": 9})
        self.assertEqual(sum(source["chunk_counts"].values()), source["total_chunks"])
        expanded = source["block_size"] * source["total_blocks"]
        self.assertEqual(expanded, 15300820992)
        self.assertEqual(sum(source["bytes_by_type"].values()), expanded)
        self.assertEqual(sparse["output"]["size_bytes"], expanded)
        self.assertEqual(source["sparse_header_checksum"], 0)
        self.assertIn("reject", sparse["checksum_policy"])

    def test_strict_tar_followup_rechecks_the_original_complete_archive(self):
        check = self.record["strict_archive_corroboration"]
        self.assertEqual(check["package_sha256"], PACKAGE)
        self.assertEqual(check["package_size_bytes"], self.record["package"]["size_bytes"])
        self.assertEqual(check["original_image_receipt_sha256"], self.record["archive_extraction_receipt"]["sha256"])
        for key in ("package_sha256_reverified", "package_identity_unchanged", "original_receipts_unchanged",
                    "runtime_strict_header_policy_verified", "invalid_empty_truncated_headers_rejected",
                    "all_zero_eof_header_retained", "tar_header_checksums_verified", "gzip_stream_crc_verified",
                    "catalog_matches_both_original_receipts", "second_end_marker_and_zero_padding_verified",
                    "all_56_streamed_hashes_match_originals"):
            self.assertTrue(check[key])
        self.assertEqual(check["member_count"], 127)
        self.assertEqual(check["decompressed_archive_bytes"], 15325941760)
        self.assertEqual(check["metadata_files_hashed"], 37)
        self.assertEqual(check["image_files_hashed"], 19)
        self.assertEqual(check["reader_source_commit"], "7d1598150a166f738f83025f27ab7a370eb72397")
        for key in ("new_image_or_metadata_copies_created", "phone_accessed", "guest_accessed", "firmware_executed",
                    "xml_instructions_applied", "images_mounted", "physical_phone_geometry_verified", "origin_verified"):
            self.assertFalse(check[key])

    def test_user_extracted_directory_images_match_separate_verified_copies(self):
        check = self.record["user_extracted_images"]
        self.assertEqual(check["package_sha256"], PACKAGE)
        self.assertEqual(check["archive_extraction_receipt_sha256"], self.record["archive_extraction_receipt"]["sha256"])
        self.assertTrue(check["all_images_match"])
        self.assertEqual(check["image_count"], 19)
        images = {row["path"]: row for row in self.intake["images"]}
        self.assertEqual({row["path"] for row in check["images"]}, set(images))
        self.assertEqual(sum(row["size_bytes"] for row in check["images"]), check["total_image_bytes_per_directory"])
        for row in check["images"]:
            self.assertEqual(row["sha256"], images[row["path"]]["sha256"])
            self.assertEqual(row["size_bytes"], images[row["path"]]["size_bytes"])
            for key in ("both_match_verified_archive", "both_regular_nonsymlink", "both_identity_stable"):
                self.assertTrue(row[key])
        for key in ("phone_accessed", "guest_accessed", "firmware_executed", "inputs_modified", "images_mounted", "origin_verified"):
            self.assertFalse(check[key])

    def test_independent_sparse_output_is_not_claimed_as_independent_lp_extraction(self):
        sparse = self.record["sparse_super"]
        check = sparse["independent_crosscheck"]
        self.assertTrue(check["matches_guarded_reconstruction"])
        self.assertTrue(check["input_and_tool_sources_unchanged"])
        self.assertEqual(check["checks_disabled"], [])
        self.assertEqual(check["source_revision"], "19a1e68e47bbe9ba446e167b2d402953bd7e0c87")
        self.assertEqual(self.record["logical_partitions"]["source_image"]["sha256"], sparse["output"]["sha256"])
        self.assertFalse(self.record["logical_partitions"]["independent_logical_extractor_run"])

    def test_lp_redundancy_and_virtual_ab_are_separate_from_live_capacity(self):
        lp = self.record["logical_partitions"]
        for key in ("all_geometry_and_metadata_copies_valid", "all_primary_backup_pairs_match",
                    "all_slots_identical", "virtual_ab_device"):
            self.assertTrue(lp[key])
        self.assertEqual(lp["geometry_copies"], 2)
        self.assertEqual(lp["metadata_copies"], 6)
        self.assertEqual(lp["metadata_slots"], 3)
        self.assertEqual(lp["metadata_version"], [10, 2])
        self.assertEqual(lp["header_flags"], 1)
        self.assertEqual(lp["logical_block_size"], 4096)
        self.assertEqual(lp["metadata_max_size"], 65536)
        self.assertEqual(len(lp["block_devices"]), 1)
        self.assertEqual(lp["block_devices"][0]["size_bytes"], 15300820992)
        self.assertFalse(lp["live_physical_geometry_verified"])

    def test_all_logical_outputs_fit_their_group_and_keep_parent_hashes(self):
        lp = self.record["logical_partitions"]
        parts = lp["partitions"]
        self.assertEqual(len(parts), 16)
        active = {row["name"]: row for row in parts if row["size_bytes"]}
        self.assertEqual(len(active), 8)
        self.assertTrue(all(name.endswith("_a") for name in active))
        empty = [row for row in parts if not row["size_bytes"]]
        self.assertEqual(len(empty), 8)
        self.assertTrue(all(row["name"].endswith("_b") for row in empty))
        group = next(row for row in lp["groups"] if row["name"] == "qti_dynamic_partitions_a")
        self.assertEqual(sum(row["size_bytes"] for row in active.values()), group["allocated_size"])
        self.assertEqual(group["allocated_size"], 12477939712)
        self.assertEqual(group["maximum_size"], 15290335232)
        self.assertLess(group["allocated_size"], group["maximum_size"])
        self.assertEqual({row["partition"] for row in lp["outputs"]}, set(active))
        for row in lp["outputs"]:
            self.assertEqual(row["parent_image_sha256"], lp["source_image"]["sha256"])
            self.assertEqual(row["size_bytes"], active[row["partition"]]["size_bytes"])
            self.assertTrue(row["readback_verified"])

    def test_boot_headers_preserve_the_dedicated_ramdisk_only_recovery(self):
        boot = self.record["boot_inspection"]
        self.assertTrue(boot["all_selected_inputs_unchanged"])
        self.assertEqual(len(boot["unpack_commands"]), 5)
        self.assertTrue(all(row["exit_code"] == 0 for row in boot["unpack_commands"]))
        self.assertEqual(len(boot["dtbo_commands"]), 2)
        self.assertTrue(all(row["exit_code"] == 0 for row in boot["dtbo_commands"]))
        headers = boot["headers"]
        self.assertTrue(all(row["header_version"] == 4 for row in headers.values()))
        self.assertEqual(headers["boot"]["kernel_size"], 39963136)
        self.assertEqual(headers["boot"]["ramdisk_size"], 0)
        self.assertEqual(headers["init_boot"]["kernel_size"], 0)
        self.assertEqual(headers["recovery"]["kernel_size"], 0)
        self.assertEqual(headers["recovery"]["ramdisk_size"], 30407261)
        self.assertEqual(headers["vendor_boot"]["page_size"], 4096)
        self.assertEqual(headers["vendor_boot"]["vendor_ramdisk_size"], 18107362)
        images = {row["path"]: row for row in self.intake["images"]}
        for name, row in headers.items():
            self.assertEqual(row["image_sha256"], images[name + ".img"]["sha256"])
            self.assertEqual(row["image_size_bytes"], images[name + ".img"]["size_bytes"])

    def test_passed_avb_keeps_embedded_keys_distinct_from_oem_trust(self):
        avb = self.record["avb"]
        self.assertTrue(avb["selected_root_chain_and_qtvm_checks_passed"])
        self.assertTrue(avb["all_inputs_unchanged"])
        self.assertEqual({row["label"] for row in avb["commands"]}, {"root-follow-chain", "qtvm-dtbo"})
        self.assertTrue(all(row["exit_code"] == 0 for row in avb["commands"]))
        self.assertEqual(set(avb["embedded_signatures"]), {"vbmeta", "vbmeta_system", "boot", "recovery", "qtvm_dtbo"})
        for sig in avb["embedded_signatures"].values():
            self.assertTrue(sig["embedded_signature_valid"])
            self.assertEqual(sig["algorithm"], "SHA256_RSA4096")
            self.assertEqual(sig["flags"], 0)
            self.assertFalse(sig["trusted_oem_key"])
        for flag in ("verification_bypass_flags_used", "images_padded_or_patched", "trusted_oem_key_supplied",
                     "origin_verified", "device_rollback_counters_checked", "fec_cryptographic_verification_performed"):
            self.assertFalse(avb[flag])
        self.assertEqual(avb["descriptor_name_mapping"], {"qtvm-dtbo.img": "qtvm_dtbo.img"})
        self.assertFalse(avb["descriptor_name_mapping_changes_bytes"])

    def test_chain_locations_are_not_inferred_from_child_header_locations(self):
        avb = self.record["avb"]
        chains = {row["partition"]: row for row in avb["chain_key_checks"]}
        self.assertEqual({name: row["rollback_index_location"] for name, row in chains.items()},
                         {"boot": 3, "recovery": 1, "vbmeta_system": 2})
        for name, row in chains.items():
            sig = avb["embedded_signatures"][name]
            self.assertTrue(row["parent_and_child_keys_match"])
            self.assertEqual(row["public_key_sha256"], sig["embedded_key_sha256"])
            self.assertEqual(sig["rollback_index_location_in_header"], 0)
        self.assertEqual(avb["embedded_signatures"]["recovery"]["rollback_index"], 1)

    def test_all_hashtrees_are_bounded_without_claiming_fec_correction(self):
        avb = self.record["avb"]
        outputs = {row["partition"].removesuffix("_a"): row for row in self.record["logical_partitions"]["outputs"]}
        self.assertEqual({row["partition"] for row in avb["hashtree_preflight"]}, set(outputs))
        self.assertEqual(len(avb["hash_preflight"]), 8)
        for row in avb["hashtree_preflight"]:
            self.assertEqual(row["file_size_bytes"], outputs[row["partition"]]["size_bytes"])
            self.assertTrue(all(row["bounds"].values()))
            self.assertLessEqual(row["data_size_bytes"], row["file_size_bytes"])
            self.assertLessEqual(row["tree_offset"] + row["tree_size"], row["file_size_bytes"])
            self.assertLessEqual(row["fec_offset"] + row["fec_size"], row["file_size_bytes"])
            self.assertFalse(row["fec_cryptographic_verification_performed"])
        self.assertTrue(all(row["bounds_verified"] for row in avb["hash_preflight"]))

    def test_filesystem_data_checks_cover_all_outputs_without_mounting(self):
        fs = self.record["filesystems"]
        self.assertEqual(fs["tool_version"], "1.9.4")
        self.assertEqual(fs["arguments"], ["--extract", "IMAGE"])
        self.assertTrue(fs["all_passed"])
        self.assertTrue(fs["superblock_checksum_check_enabled"])
        self.assertFalse(fs["extract_destination_supplied"])
        self.assertFalse(fs["image_mounted"])
        self.assertFalse(fs["avb_checked_by_this_operation"])
        self.assertEqual(fs["checks_disabled"], [])
        outputs = {row["partition"]: row for row in self.record["logical_partitions"]["outputs"]}
        self.assertEqual({row["partition"] for row in fs["partitions"]}, set(outputs))
        for row in fs["partitions"]:
            self.assertEqual(row["exit_code"], 0)
            self.assertTrue(row["passed"])
            self.assertTrue(row["image_unchanged"])
            self.assertEqual(row["sha256"], outputs[row["partition"]]["sha256"])
            self.assertEqual(row["size_bytes"], outputs[row["partition"]]["size_bytes"])

    def test_input_lineages_remain_separate(self):
        rows = {row["path"]: row for row in self.record["image_comparison_with_xiaomi_eu"]}
        identical = {"boot.img", "init_boot.img", "recovery.img", "dtbo.img", "vbmeta.img", "vbmeta_system.img"}
        for name in identical:
            self.assertTrue(rows[name]["xiaomi_eu_same_basename"]["sha256_matches"])
        self.assertFalse(rows["vendor_boot.img"]["xiaomi_eu_same_basename"]["sha256_matches"])
        limits = self.record["boundaries"]
        self.assertTrue(limits["embedded_signature_consistency_verified"])
        self.assertTrue(all(value is False for key, value in limits.items()
                            if key != "embedded_signature_consistency_verified"))

    def test_record_contains_no_private_payload_or_identifiers(self):
        forbidden = {"raw_cil", "raw_key", "base64", "content", "stdout", "stderr", "serial", "imei", "imsi"}
        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for key, child in value.items():
                    if key.endswith("sha256") and child is not None:
                        self.assertRegex(child, r"^[a-f0-9]{64}$")
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
        check(self.record)


if __name__ == "__main__":
    unittest.main()
