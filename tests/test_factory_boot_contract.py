"""Offline consistency checks for static factory boot evidence, not boot tests."""

import json
from pathlib import Path
import re
import unittest

from support import walk_objects


ROOT = Path(__file__).resolve().parents[1]
FACTORY = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
EU = "b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69"
RECEIPTS = {
    "image_readback": "2c5c406b9374f7e1a191d994c0f6c4de25516e74ff857a3e4bde3e63c4b4eddb",
    "header_component_readback": "534873e0b25e1ca48a9d1fc83c8a83c6d460146f7ac8070b0c5df4f3b3edf6f2",
    "ramdisk_comparison": "138df4eff3d7f916bb6c24f9a91bd7e4ec2fae5c7a42bc5526bda1bf7c76330f",
    "independent_output_readback": "fbdc7a9262b9fd6cf60f89d8e6a55fdeaf082109b3237e3d5ab72a55d37d990b",
}


class FactoryBootContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/factory-boot-contract.json").read_text())
        cls.doc = (ROOT / "docs/factory-boot-contract.md").read_text()
        cls.intake = json.loads((ROOT / "research/factory-firmware-intake.json").read_text())

    def test_package_integrity_does_not_upgrade_origin_or_replace_eu(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["device"], {"codename": "nezha", "hardware_region": "CN"})
        factory = self.record["packages"]["factory"]
        self.assertEqual(factory["sha256"], FACTORY)
        self.assertEqual(factory["sha256"], self.intake["package"]["sha256"])
        self.assertEqual(factory["source_kind"], "user-provided")
        self.assertIsNone(factory["source_url"])
        self.assertIs(factory["origin_verified"], False)
        eu = self.record["packages"]["xiaomi_eu"]
        self.assertEqual(eu["sha256"], EU)
        self.assertIs(eu["modified_package"], True)
        self.assertIs(eu["retained_separately"], True)

    def test_all_nineteen_images_bind_to_the_original_intake_inventory(self):
        readback = self.record["image_readback"]
        self.assertEqual(readback["source_directory"],
                         "sources/nezha_images_OS3.0.309.0.WPACNXM_16.0/images")
        self.assertEqual(readback["image_count"], 19)
        self.assertEqual(len(readback["images"]), 19)
        actual = {x["path"]: (x["size_bytes"], x["sha256"]) for x in readback["images"]}
        expected = {x["path"]: (x["size_bytes"], x["sha256"]) for x in self.intake["images"]}
        self.assertEqual(len(actual), 19)
        self.assertEqual(actual, expected)
        self.assertEqual(sum(size for size, _ in actual.values()), 14852407336)
        self.assertEqual(readback["total_image_bytes_per_directory"], 14852407336)
        self.assertIs(readback["both_directories_rehashed"], True)
        self.assertIs(readback["all_images_match"], True)
        for item in readback["images"]:
            self.assertIs(item["archive_and_user_copy_match"], True)
            self.assertEqual(Path(item["path"]).name, item["path"])

    def test_receipts_remain_explicit_without_requiring_private_files(self):
        for section, digest in RECEIPTS.items():
            with self.subTest(section=section):
                receipt = self.record[section]["receipt"]
                self.assertEqual(receipt["sha256"], digest)
                self.assertGreater(receipt["size_bytes"], 0)
                self.assertTrue(receipt["path"].startswith(
                    f"artifacts/firmware-analysis/{FACTORY}/boot-analysis/"))
                self.assertTrue(receipt["path"].endswith("/receipt.json"))
                self.assertNotIn("..", Path(receipt["path"]).parts)
                self.assertIn(digest, self.doc)
        self.assertEqual(len(set(RECEIPTS.values())), len(RECEIPTS))

    def test_boot_and_recovery_headers_match_pinned_unpacker_observations(self):
        header_readback = self.record["header_component_readback"]
        unpacker = header_readback["pinned_unpacker"]
        self.assertEqual(unpacker["commit"], "954bc3ead5e679005fddf3484d247f2557b3c2c9")
        self.assertEqual(unpacker["sha256"],
                         "06b54dd9a07c5281778e29e234e76f6e3faee8bf0c904a5ef88fdee30eeed12e")
        self.assertEqual(header_readback["factory_initial_receipt_sha256"],
                         "19a0cf859e91b283684c03ab1691f8469e3c87c5a01b8fc6a1eae1d5e65b1f37")
        self.assertEqual(header_readback["eu_component_receipt_sha256"],
                         "ecdc974e9e4d9b2df8b64331bd82c395bc47499e7b8db8e3cd5b7a2c60d6bb3b")
        headers = header_readback["headers"]
        self.assertEqual(set(headers), {"boot", "init_boot", "vendor_boot", "recovery"})
        for name, (kernel, ramdisk) in {
            "boot": (39963136, 0), "init_boot": (0, 2916992), "recovery": (0, 30407261),
        }.items():
            self.assertEqual(headers[name]["kernel_size_bytes"], kernel)
            self.assertEqual(headers[name]["ramdisk_size_bytes"], ramdisk)
            self.assertEqual(headers[name]["boot_signature_field_bytes"], 0)
        for header in headers.values():
            self.assertEqual(header["header_version"], 4)
            self.assertIs(header["header_matches_pinned_unpack_log"], True)
            self.assertRegex(header["image_first_4096_bytes_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(header["pinned_unpack_log_sha256"], r"^[0-9a-f]{64}$")
        self.assertIs(header_readback["zero_boot_signature_field_does_not_establish_avb_disabled"], True)

    def test_vendor_header_uses_the_observed_single_ramdisk_arrangement(self):
        vendor = self.record["header_component_readback"]["headers"]["vendor_boot"]
        expected = {
            "page_size_bytes": 4096, "header_size_bytes": 2128,
            "vendor_ramdisk_size_bytes": 18107362, "dtb_size_bytes": 4496880,
            "bootconfig_size_bytes": 270, "ramdisk_table_bytes": 108,
            "ramdisk_table_entry_count": 1, "ramdisk_table_entry_size_bytes": 108,
            "ramdisk_type": 1, "ramdisk_offset": 0,
        }
        for key, value in expected.items():
            self.assertEqual(vendor[key], value, key)
        self.assertIs(vendor["ramdisk_name_empty"], True)
        self.assertIs(vendor["ramdisk_board_id_words_all_zero"], True)

    def test_kernel_dtb_and_bootconfig_hashes_match_preserved_eu(self):
        components = self.record["header_component_readback"]["components"]
        self.assertEqual(len(components), 5)
        by_path = {item["path"]: item for item in components}
        expected = {
            "unpacked/boot/kernel": (39963136, "4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8"),
            "unpacked/vendor_boot/dtb": (4496880, "1a5c30b75e816f33dd36caa114faa7bc656605e4ac9ffe786726538b37ada22d"),
            "unpacked/vendor_boot/bootconfig": (270, "bad92331bd65be0207c84a855cb0b9580a504acd89684e3222007b20b683805f"),
            "unpacked/init_boot/kernel": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
            "unpacked/recovery/kernel": (0, "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"),
        }
        self.assertEqual(set(by_path), set(expected))
        for path, (size, digest) in expected.items():
            item = by_path[path]
            self.assertEqual((item["size_bytes"], item["factory_sha256"]), (size, digest))
            self.assertEqual(item["factory_sha256"], item["xiaomi_eu_sha256"])
            self.assertIs(item["bytes_match_eu"], True)

    def test_bootconfig_records_only_static_literals(self):
        bootconfig = self.record["vendor_bootconfig"]
        self.assertEqual(bootconfig["size_bytes"], 270)
        component = next(item for item in self.record["header_component_readback"]["components"]
                         if item["path"] == "unpacked/vendor_boot/bootconfig")
        self.assertEqual(bootconfig["sha256"], component["factory_sha256"])
        self.assertIs(bootconfig["bytes_match_eu"], True)
        self.assertIs(bootconfig["live_bootconfig_verified"], False)
        self.assertEqual(bootconfig["declarations"], {
            "androidboot.hardware": "qcom", "androidboot.memcg": "1",
            "androidboot.usbcontroller": "a600000.dwc3",
            "androidboot.load_modules_parallel": "true",
            "androidboot.hypervisor.protected_vm.supported": "true",
            "androidboot.hypervisor.version": "gunyah",
            "androidboot.vendor.qspa": "true", "androidboot.serialconsole": "0",
        })

    def test_ramdisk_sizes_and_entry_counts_reconcile_with_headers(self):
        ramdisks = self.record["ramdisk_comparison"]["ramdisks"]
        headers = self.record["header_component_readback"]["headers"]
        expected = {
            "init_boot": (5436160, 24, "37743dfaad677c44ad24b63973faa805d56f3ade644891a254e72ed17c171abc"),
            "vendor_boot": (48237312, 440, "26c5c433214b1abcbf2e2a8aae0afe73cb555839e17bda0a6b9ba76c1d7fc0af"),
            "recovery": (53929472, 1036, "13083e8177001c912c0078e03f59c79dccdbe0895a6b62ce2019bae47dfa7cd7"),
        }
        self.assertEqual(set(ramdisks), set(expected))
        for name, (size, count, digest) in expected.items():
            item = ramdisks[name]
            self.assertEqual((item["cpio_size_bytes"], item["entry_count"], item["cpio_sha256"]),
                             (size, count, digest))
            header_key = "vendor_ramdisk_size_bytes" if name == "vendor_boot" else "ramdisk_size_bytes"
            self.assertEqual(item["compressed_size_bytes"], headers[name][header_key])
            self.assertEqual(item["archive_count"], 1)
            self.assertEqual(item["compressed_sha256_matches_eu"], name != "vendor_boot")
            self.assertEqual(item["cpio_sha256_matches_eu"], name != "vendor_boot")
        self.assertEqual(sum(x["entry_count"] for x in ramdisks.values()), 1500)

    def test_only_vendor_fstab_changed_in_the_compared_entry_fields(self):
        fstab = self.record["normal_vendor_fstab"]
        for name, item in self.record["ramdisk_comparison"]["ramdisks"].items():
            comparison = item["comparison"]
            self.assertEqual(comparison["compared_fields"],
                             ["kind", "mode", "uid", "gid", "nlink", "size_bytes", "sha256", "link_target"])
            self.assertEqual(comparison["added_entries"], [])
            self.assertEqual(comparison["removed_entries"], [])
            self.assertIs(comparison["entry_order_equal"], True)
            self.assertIs(comparison["mtime_not_present_in_reused_parser_inventory"], True)
            self.assertIs(comparison["cpio_content_offsets_not_compared_as_file_metadata"], True)
            changed = comparison["changed_entries"]
            self.assertEqual(comparison["equal_entry_count"] + len(changed), item["entry_count"])
            if name != "vendor_boot":
                self.assertEqual(changed, [])
                continue
            self.assertEqual(len(changed), 1)
            self.assertEqual(changed[0]["path"], fstab["archive_path"])
            self.assertEqual(changed[0]["different_fields"], ["size_bytes", "sha256"])
            for side, prefix in [("factory", "factory"), ("xiaomi_eu", "eu")]:
                self.assertEqual(changed[0][side]["size_bytes"], fstab[f"{prefix}_size_bytes"])
                self.assertEqual(changed[0][side]["sha256"], fstab[f"{prefix}_sha256"])

    def test_all_430_vendor_ramdisk_modules_match_without_loadability_claim(self):
        modules = self.record["vendor_ramdisk_modules"]
        ramdisks = self.record["ramdisk_comparison"]["ramdisks"]
        self.assertEqual(modules["factory_module_count"], 430)
        self.assertEqual(modules["eu_module_count"], 430)
        self.assertEqual(modules["same_path_content_hash_matches"], 430)
        for name, item in ramdisks.items():
            expected = 430 if name == "vendor_boot" else 0
            for key in ["module_count", "eu_module_count", "module_hash_matches_with_eu"]:
                self.assertEqual(item[key], expected)
        self.assertIs(modules["loadability_verified"], False)
        self.assertIs(modules["kernel_export_crc_or_signature_trust_verified"], False)
        self.assertIn("only vendor_boot", modules["dlkm_scope"])

    def test_module_metadata_and_duplicate_load_entries_are_preserved(self):
        modules = self.record["vendor_ramdisk_modules"]
        metadata = {item["path"]: item for item in modules["module_metadata_files"]}
        self.assertEqual(set(metadata), {f"lib/modules/modules.{suffix}" for suffix in [
            "alias", "blocklist", "dep", "load", "load.recovery", "softdep"]})
        self.assertEqual(len(modules["module_metadata_files"]), 6)
        for item in metadata.values():
            self.assertIs(item["bytes_match_eu"], True)
            self.assertGreater(item["size_bytes"], 0)
        self.assertEqual(len(modules["ordered_load_lists"]), 2)
        for item, counts in zip(modules["ordered_load_lists"], [(157, 154), (435, 424)]):
            self.assertEqual((item["entry_count"], item["unique_entry_count"]), counts)
            self.assertEqual(item["entry_count"] - item["unique_entry_count"],
                             sum(count - 1 for count in item["duplicates"].values()))
            self.assertEqual(item["sha256"], metadata[item["path"]]["sha256"])
            self.assertEqual(item["entry_count"], metadata[item["path"]]["noncomment_line_count"])
            self.assertEqual(item["missing_module_filenames"], [])
            self.assertIs(item["ordered_entries_preserved"], True)
            self.assertIs(item["modules_loaded"], False)
        self.assertEqual(modules["ordered_load_lists"][0]["duplicates"],
                         {"bootinfo.ko": 2, "debug_ext.ko": 2, "smcinvoke_dlkm.ko": 2})

    def test_factory_fstab_restores_the_exact_21_verification_rows(self):
        fstab = self.record["normal_vendor_fstab"]
        self.assertEqual(fstab["rows_in_each"], 61)
        self.assertEqual((fstab["factory_size_bytes"], fstab["eu_size_bytes"]), (13661, 13076))
        self.assertIs(fstab["non_flag_columns_equal"], True)
        self.assertIs(fstab["existing_flag_order_preserved"], True)
        self.assertEqual(fstab["avb_added_row_count"], 21)
        self.assertEqual(len(fstab["flag_changes"]), 21)
        expected = {}
        for partition in ["system", "system_ext", "product"]:
            for filesystem in ["ext4", "erofs"]:
                expected[(partition, filesystem)] = "avb=vbmeta_system"
        for partition in ["mi_ext", "vendor", "vendor_dlkm", "system_dlkm", "odm"]:
            for filesystem in ["ext4", "erofs"]:
                expected[(partition, filesystem)] = "avb=vbmeta"
        for partition in ["boot", "init_boot", "vendor_boot", "dtbo", "recovery"]:
            expected[(f"/dev/block/by-name/{partition}", "emmc")] = "avb=vbmeta"
        actual = {}
        for row in fstab["flag_changes"]:
            self.assertEqual(row["removed_flags"], [])
            avb = [flag for flag in row["added_flags"] if flag.startswith("avb=")]
            self.assertEqual(len(avb), 1)
            self.assertTrue(all(flag.startswith(("avb=", "avb_keys=")) for flag in row["added_flags"]))
            actual[(row["source"], row["filesystem"])] = avb[0]
        self.assertEqual(actual, expected)
        self.assertIs(fstab["fstab_applied"], False)

    def test_two_system_key_lists_do_not_infer_keys_or_a_stock_boot_failure(self):
        keys = self.record["gsi_key_references"]
        expected_paths = [f"/avb/{letter}-gsi.avbpubkey" for letter in "qrstuvw"]
        self.assertEqual(keys["path_count"], 7)
        self.assertEqual([item["path"] for item in keys["paths"]], expected_paths)
        for item in keys["paths"]:
            self.assertEqual(item["matching_cpio_entries"], [])
        fstab = self.record["normal_vendor_fstab"]
        self.assertEqual(fstab["avb_keys_added_row_count"], 2)
        references = [(row, flag) for row in fstab["flag_changes"] for flag in row["added_flags"]
                      if flag.startswith("avb_keys=")]
        self.assertEqual(len(references), 2)
        self.assertEqual({row["filesystem"] for row, _ in references}, {"ext4", "erofs"})
        for row, flag in references:
            self.assertEqual(row["mount_point"], "/system")
            self.assertEqual(flag, "avb_keys=" + ":".join(expected_paths))
        for key in ["key_contents_published", "key_flags_removed", "stock_boot_failure_inferred"]:
            self.assertIs(keys[key], False)
        self.assertIn("Only these three CPIO inventories", keys["scope"])

    def test_normal_userdata_encryption_requirements_remain_unchanged(self):
        fstab = self.record["normal_vendor_fstab"]
        self.assertIs(fstab["encryption_flags_equal_to_eu"], True)
        rows = {row["mount_point"]: row for row in fstab["normal_data_rows"]}
        self.assertEqual(set(rows), {"/data", "/metadata"})
        self.assertEqual(rows["/data"]["filesystem"], "f2fs")
        self.assertIn("inlinecrypt", rows["/data"]["mount_options"])
        self.assertEqual(rows["/data"]["encryption_flags"], [
            "fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0",
            "keydirectory=/metadata/vold/metadata_encryption",
            "metadata_encryption=aes-256-xts:wrappedkey_v0",
        ])
        self.assertIn("checkpoint=fs", rows["/data"]["fs_mgr_flags"])
        self.assertEqual(rows["/metadata"]["filesystem"], "f2fs")
        self.assertIn("first_stage_mount", rows["/metadata"]["fs_mgr_flags"])

    def test_recovery_fstabs_are_preserved_evidence_not_a_twrp_configuration(self):
        fstabs = {item["archive_path"]: item for item in self.record["stock_recovery_fstabs"]}
        self.assertEqual(len(self.record["stock_recovery_fstabs"]), 2)
        expected = {
            "miui.factoryreset.fstab": (426, 2, "e5d88b7eabc695bc3ed0d4149afac495f0b266abbe2204ea4a7554e1f31fd4e8"),
            "system/etc/recovery.fstab": (3709, 11, "daccf8b606e5fbb90537ae9f023d8d9a05c5a8f0d8283026e7931a92a6ced9b1"),
        }
        self.assertEqual(set(fstabs), set(expected))
        for path, (size, rows, digest) in expected.items():
            item = fstabs[path]
            self.assertEqual((item["size_bytes"], item["row_count"], item["sha256"]), (size, rows, digest))
            self.assertIs(item["bytes_match_eu"], True)
            self.assertIs(item["applied_or_adopted_for_twrp"], False)
            data = next(row for row in item["data_and_metadata_rows"] if row["mount_point"] == "/data")
            self.assertIn("fileencryption=ice", data["encryption_flags"])
            self.assertIn("wrappedkey", data["encryption_flags"])
        logical = fstabs["system/etc/recovery.fstab"]["logical_rows"]
        self.assertEqual({row["filesystem"] for row in logical}, {"ext4"})
        self.assertEqual({row["source"] for row in logical},
                         {"system", "system_ext", "product", "vendor", "odm"})
        for row in logical:
            expected_flag = "avb" if row["source"] in {"vendor", "odm"} else "avb=vbmeta_system"
            self.assertEqual(row["verification_flags"], [expected_flag])
        self.assertIn("not a ready TWRP fstab", self.record["recovery_fstab_limit"])

    def test_literal_service_presence_is_not_service_execution(self):
        services = self.record["literal_boot_service_inventory"]
        self.assertEqual(len(services), 15)
        self.assertEqual(len({(item["ramdisk"], item["name"]) for item in services}), 15)
        for item in services:
            self.assertIs(item["executed"], False)
            if item["present_in_same_cpio"]:
                self.assertRegex(item["member_sha256"], r"^[0-9a-f]{64}$")
            else:
                self.assertIsNone(item["member_sha256"])
                self.assertIsNone(item["member_kind"])
        self.assertEqual({item["executable_path"] for item in services if not item["present_in_same_cpio"]},
                         {"/system/bin/charger", "/system/bin/auditctl"})
        unresolved = self.record["unresolved_literal_init_dependencies"]
        self.assertEqual(len(unresolved), 5)
        self.assertEqual(sum(item["contains_unresolved_property"] for item in unresolved), 1)
        for item in unresolved:
            self.assertIs(item["present_in_same_cpio"], False)
            self.assertIs(item["runtime_failure_inferred"], False)

    def test_bounded_decoder_pins_trusted_tools_without_running_old_workflow(self):
        comparison = self.record["ramdisk_comparison"]
        self.assertEqual(comparison["lz4"]["version"], "1.10.0")
        self.assertEqual(comparison["lz4"]["sha256"],
                         "b7dccdc84a76f0359c26c67393a6d50b4b073f8bf85078dca7ccf877502b00e5")
        self.assertEqual(comparison["decompression_timeout_seconds_per_ramdisk"], 120)
        self.assertEqual(comparison["decompression_limit_bytes_per_ramdisk"], 512 * 1024 * 1024)
        self.assertIs(comparison["all_three_lz4_commands_exited_zero"], True)
        self.assertIs(comparison["input_identity_and_hash_rechecked"], True)
        parser = comparison["reused_parser_source"]
        self.assertEqual(parser["reused_function_names"], ["hash_bytes", "parse_cpio"])
        self.assertIs(parser["old_top_level_workflow_executed"], False)
        self.assertIs(parser["additional_complete_archive_and_input_bounds_checked"], True)

    def test_independent_readback_covers_all_1500_member_contents(self):
        readback = self.record["independent_output_readback"]
        self.assertEqual(readback["artifact_count_rehashed"], 31)
        self.assertEqual(readback["artifacts_total_bytes_rehashed"], 108712012)
        self.assertEqual(readback["cpio_member_contents_rehashed"], 1500)
        self.assertEqual(readback["cpio_member_contents_rehashed"],
                         sum(item["entry_count"] for item in self.record["ramdisk_comparison"]["ramdisks"].values()))
        self.assertIs(readback["all_output_hashes_match"], True)
        self.assertIs(readback["cpio_parser_reused"], False)

    def test_failed_wrapper_attempt_is_not_rewritten_as_corrupt_firmware(self):
        history = self.record["wrapper_attempt_history"]
        self.assertEqual(history["trusted_lz4_exit_code"], 44)
        self.assertEqual(history["fd_offset_diagnostic"], {
            "python_logical_offset": 0, "inherited_os_descriptor_offset": 4096,
            "legacy_lz4_magic_correct": True,
        })
        self.assertIs(history["no_success_claimed_for_v1"], True)
        self.assertIs(history["firmware_corrupt_claimed"], False)
        self.assertEqual(history["fixed_attempt"], "ramdisk-comparison-v2")
        self.assertEqual(history["fixed_attempt_child_stdin_offset_bytes"], 0)
        self.assertEqual(history["fixed_attempt_receipt_sha256"], RECEIPTS["ramdisk_comparison"])
        self.assertTrue(history["failed_staging_preserved"].startswith(
            f"artifacts/firmware-analysis/{FACTORY}/boot-analysis/.ramdisk-comparison-"))
        validation = self.record["private_offline_validation"]
        self.assertEqual(validation["wrapper_test_count"], 10)
        self.assertEqual(validation["reused_parser_test_count"], 14)
        self.assertIs(validation["tests_require_phone"], False)
        self.assertIs(validation["tests_execute_firmware"], False)
        self.assertIn("this was not\nfirmware corruption", self.doc)

    def test_boundaries_keep_static_evidence_separate_from_boot_or_decryption(self):
        boundaries = self.record["verification_boundaries"]
        self.assertEqual(set(boundaries), {
            "phone_accessed", "guest_accessed", "images_mounted", "cpio_paths_or_links_materialized",
            "firmware_executed", "fstab_or_init_declarations_applied", "build_inputs_changed",
            "twrp_fstab_adopted", "custom_recovery_built", "recovery_decryption_verified",
            "rom_boot_or_feature_compatibility_verified", "physical_partition_sizes_verified",
            "oem_origin_or_trust_root_authenticated", "raw_firmware_or_key_contents_published",
        })
        for key, value in boundaries.items():
            self.assertIs(value, False, key)
        for phrase in ["recovery decryption remains unverified", "not a new live bootconfig read",
                       "cannot protect against boot-chain or bootloader damage"]:
            self.assertIn(phrase, " ".join(self.doc.split()))

    def test_public_record_has_hashes_and_links_without_private_payloads(self):
        for item in walk_objects(self.record):
            for key, value in item.items():
                if key.endswith("sha256") and value is not None:
                    self.assertRegex(value, r"^[0-9a-f]{64}$", key)
                self.assertNotIn(key, {"serial", "serial_number", "imei", "key_bytes",
                                       "private_key", "raw_contents", "base64_payload"})
        serialized = json.dumps(self.record)
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("PRIVATE KEY-----", serialized)
        self.assertNotRegex(serialized, r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")
        for related in self.record["related_records"]:
            self.assertFalse(Path(related).is_absolute())
            self.assertNotIn("..", Path(related).parts)
            self.assertTrue((ROOT / related).is_file(), related)
        for target in re.findall(r"\]\(([^)]+)\)", self.doc):
            self.assertFalse(Path(target).is_absolute())
            self.assertTrue((ROOT / "docs" / target).is_file(), target)


if __name__ == "__main__":
    unittest.main()
