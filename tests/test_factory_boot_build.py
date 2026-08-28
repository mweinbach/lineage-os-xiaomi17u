"""Offline consistency checks for published v8 evidence, not device boot tests."""

import json
from pathlib import Path, PurePosixPath
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASE = "artifacts/build-validation/nezha-factory-boot-v8-1"
FACTORY = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
IMAGES = {
    "init_boot": (8388608, "eae81b09a6b6f5ee7c1901fef654e407b8d3776a5ec7682a3291f86c76475e0f"),
    "vendor_boot": (100663296, "b10bdb2e9f4e12b126982924e2b754717e37da739da2ad4d6f4192742471db86"),
    "dtbo": (33554432, "b166ce78ee67b970feb71e10b6123204c30f225b6b867023b75582eedf82fa35"),
}
INIT = {
    "first_stage": (2713472, "e1f34b1dc3473646ac55e56a9731b505a75e6d35fa2366d4c7cf54f016dedd54"),
    "second_stage": (2708392, "3a0001d2b6383a5a97861c288eb82241ae5b88d18b3811f16d7960230abf8ca7"),
}
RECEIPTS = {
    "build": "869ea7bd4fbb1dd914d5d159ba591efc0a392a44ab63e9a6954281f5755986d6",
    "guest_manifest": "af85322b5462cd5f9bbc21f82a7fe5a38ef73b185ecb919933102c9d0690e5a7",
    "collection": "9b86aeb8b08552c917caab318d2b2489bf5fd5858174cbc4f3490363e6e04c60",
    "sealed_snapshot": "a3873195eb76155a502208af5bc037cdaf740acc5df574eab43ef47312ef21e6",
    "validation": "cff12cd8e5fc60290758c3c6c2e2a70ebce4f1f22982d345feec4e4a83d9a8e3",
    "remaining_schema_preflight": "b37558ec4cb530724c831cdfef99915d3613c29af51c5d7715b5891b56a68e69",
    "factory_vendor_inventory": "81ea2df0c4927f4a58d9587bb09a2809dccd5f75a62542669926fd1d9a5bdec6",
    "cpio_source_review": "fea40acea1e5d12d987be354de87dcf9e5bd4347e2d10ea6add40bc71d057058",
    "avb_control_flow_review": "c4d51847d0e133ff20c6516a58004eb444cda89aa18ec6025835baec36c8f99d",
}


class FactoryBootBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = (ROOT / "research/factory-boot-build.json").read_text()
        cls.record = json.loads(cls.text)
        cls.doc = (ROOT / "docs/factory-boot-build.md").read_text()
        cls.policy = json.loads((ROOT / "research/user-security-build.json").read_text())
        cls.factory = json.loads((ROOT / "research/factory-boot-contract.json").read_text())

    def test_snapshot_is_three_user_components_not_a_rom(self):
        r = self.record
        self.assertEqual(r["schema_version"], 1)
        self.assertEqual(r["device"], {"codename": "nezha", "hardware_region": "CN"})
        self.assertEqual(r["snapshot"], "factory-user-v8-boot-components")
        self.assertEqual(r["status"], "three_generated_boot_components_validated_not_a_complete_rom")
        build = r["build"]
        for key in ("name", "target_product", "target_release", "target_variant", "started_at", "completed_at"):
            self.assertEqual(build[key], self.policy["build"][key])
        self.assertEqual((build["target_product"], build["target_release"], build["target_variant"]),
                         ("lineage_nezha", "bp4a", "user"))
        self.assertEqual(build["ninja_actions_completed"], 6551)
        self.assertEqual(build["exit_code"], 0)
        self.assertIs(build["passed"], True)
        self.assertIs(build["full_rom_build_verified"], False)
        self.assertEqual(build["component_goals"], ["initbootimage", "vendorbootimage", "dtboimage", "init"])

    def test_receipt_bindings_are_exact_and_do_not_require_private_files(self):
        self.assertEqual(set(self.record["receipts"]), set(RECEIPTS))
        for name, checksum in RECEIPTS.items():
            row = self.record["receipts"][name]
            self.assertEqual(row["sha256"], checksum)
            self.assertGreater(row["size_bytes"], 0)
            self.assertTrue(row["path"].startswith(("reports/", "artifacts/")))
            self.assertNotIn("..", PurePosixPath(row["path"]).parts)
        self.assertEqual(self.record["receipts"]["validation"]["size_bytes"], 427291)
        self.assertEqual(self.record["receipts"]["validation"]["path"], BASE + "/host-boot-validation-v3/receipt.json")
        self.assertEqual(self.record["receipts"]["factory_vendor_inventory"]["size_bytes"], 454747)

    def test_factory_origin_and_historical_kernel_result_are_not_upgraded(self):
        p = self.record["provenance"]
        self.assertEqual(p["factory_package_sha256"], FACTORY)
        self.assertEqual(p["factory_package_sha256"], self.factory["packages"]["factory"]["sha256"])
        self.assertEqual(p["factory_source_kind"], "user-provided")
        self.assertIsNone(p["factory_source_url"])
        self.assertIs(p["factory_origin_verified"], False)
        self.assertEqual(p["kernel_bundle_input_avb_status_not_relabelled"], "failed")
        self.assertIs(p["module_equality_is_not_signature_authentication"], True)
        self.assertIs(p["generated_images_are_new_build_artifacts_not_factory_images"], True)
        self.assertEqual(p["device_admission_sha256"], self.policy["build"]["input_admission_sha256"])
        self.assertEqual(p["kernel_receipt_sha256"], "4ce149410ba2ab5f24653ebd8c4020a7401ba5172e2648c19f3c8bf726a7e9bb")
        self.assertEqual(p["vendor_receipt_sha256"], "811f7904adbec2fa99d933179b1247d0c2e30f80a2ba7e0b54c8a2e713917360")

    def test_one_sealed_snapshot_is_reused_without_mutating_out(self):
        c = self.record["collection"]
        self.assertEqual((c["guest_file_count"], c["host_symbol_reports_added"], c["host_snapshot_file_count"]), (29, 2, 31))
        self.assertEqual(c["host_snapshot_file_bytes"], 152380776)
        self.assertEqual(c["guest_seal_path"], "/work/validation/nezha-factory-boot-v8-1/sealed-snapshot-v1")
        for key in ("all_stream_hashes_verified", "all_snapshot_files_rechecked", "no_android_build_active_during_sealing",
                    "same_sealed_snapshot_used_for_all_inspections", "guest_accessed_for_sealing"):
            self.assertIs(c[key], True, key)
        for key in ("source_and_out_modified", "existing_files_replaced", "phone_accessed"):
            self.assertIs(c[key], False, key)
        self.assertEqual(c["host_collector_sha256"], "de9c3660bc3397b65459abffcdbaa8f431ec96da864992ec7e03b1f75e336d90")
        self.assertEqual(c["guest_collector_sha256"], "04f6c2e89a69ef772b41a79b19401e54040b1299322d001fd7bc639098d49353")

    def test_image_hashes_and_package_budgets_are_exact(self):
        self.assertEqual(set(self.record["images"]), set(IMAGES))
        for name, expected in IMAGES.items():
            row = self.record["images"][name]
            self.assertEqual((row["size_bytes"], row["sha256"]), expected)
            self.assertEqual(row["path"], BASE + "/images/" + name + ".img")
            self.assertEqual(row["size_bytes"], row["package_derived_partition_budget_bytes"])
            self.assertIs(row["fits_package_budget"], True)
            self.assertIs(row["live_partition_fit_verified"], False)
            self.assertIn(expected[1], self.doc)

    def test_all_avb_blocks_are_unsigned_despite_successful_hash_checks(self):
        for name, image in self.record["images"].items():
            with self.subTest(image=name):
                avb = image["avb"]
                self.assertEqual(avb["algorithm"], "NONE")
                self.assertEqual((avb["flags"], avb["hash_descriptor_flags"], avb["rollback_index"]), (0, 0, 0))
                self.assertEqual(avb["hash_algorithm"], "sha256")
                for key in ("direct_sealed_byte_hash_verified", "hash_descriptor_digest_verified",
                            "declared_descriptor_array_exactly_exhausted"):
                    self.assertIs(avb[key], True, key)
                for key in ("embedded_signature_present", "embedded_signature_verified", "matches_engineering_test_key",
                            "oem_authenticated", "complete_new_chain_verified", "phone_bootloader_libavb_version_verified"):
                    self.assertIs(avb[key], False, key)
                self.assertIsNone(avb["embedded_key_sha256"])

    def test_avb_extents_and_host_version_checks_have_bounded_scope(self):
        expected = {"init_boot": (3735552, 3735552, 832, 4), "vendor_boot": (22618112, 22618112, 704, 2),
                    "dtbo": (1495111, 1499136, 704, 2)}
        for name, values in expected.items():
            image = self.record["images"][name]
            avb = image["avb"]
            self.assertEqual(tuple(avb[key] for key in ("original_image_size", "vbmeta_offset", "vbmeta_size", "descriptor_count")), values)
            self.assertLessEqual(avb["original_image_size"], avb["vbmeta_offset"])
            self.assertLess(avb["vbmeta_offset"] + avb["vbmeta_size"], image["size_bytes"])
            self.assertEqual(avb["required_libavb_version"], [1, 0])
            self.assertEqual(avb["checked_against_host_libavb_version"], [1, 3])

    def test_generated_properties_are_not_stock_identity_or_signatures(self):
        init = self.record["images"]["init_boot"]["properties"]
        self.assertEqual(init["os_version"], "16")
        self.assertEqual(init["security_patch"], "2026-02-01")
        for image in self.record["images"].values():
            properties = image["properties"]
            self.assertEqual(properties["fingerprint_sha256"], "bb80d7139b86811fc26fe82aa2e5f0e71aad001caf60a0711d3b562d5771e3f4")
            self.assertEqual(properties["fingerprint_variant"], "user")
            self.assertEqual(properties["fingerprint_signing_tags"], "test-keys")
            self.assertIs(image["avb"]["embedded_signature_present"], False)

    def test_init_boot_header_has_no_kernel_and_matches_compressed_stream(self):
        header = self.record["headers"]["init_boot"]
        self.assertEqual((header["header_version"], header["header_size"], header["page_size"]), (4, 1584, 4096))
        self.assertEqual((header["kernel_size"], header["signature_size"], header["ramdisk_offset"]), (0, 0, 4096))
        self.assertEqual(header["ramdisk_size"], 3727924)
        self.assertEqual(header["ramdisk_size"], self.record["ramdisks"]["init_boot"]["compressed"]["size_bytes"])
        self.assertEqual(header["cmdline"], "")

    def test_vendor_header_retains_nezha_fragment_geometry(self):
        header = self.record["headers"]["vendor_boot"]
        self.assertEqual((header["header_version"], header["header_size"], header["page_size"]), (4, 2128, 4096))
        self.assertEqual((header["table_size"], header["entry_count"], header["entry_size"]), (108, 1, 108))
        self.assertEqual(header["load_addresses"], {"kernel": 32768, "ramdisk": 16777216, "tags": 256, "dtb": 32505856})
        fragment = header["fragment"]
        self.assertEqual((fragment["offset"], fragment["type"], fragment["name"], fragment["board_id"]), (0, 1, "", [0] * 16))
        self.assertEqual(fragment["size_bytes"], header["ramdisk_size"])
        self.assertEqual(header["ramdisk_size"], 18106953)
        self.assertEqual(header["dtb_size"], 4496880)
        self.assertEqual(header["bootconfig_size"], 270)
        self.assertEqual(header["cmdline"].split().count("bootconfig"), 2)
        self.assertIn("contains `bootconfig` twice", self.doc)

    def test_dtb_matches_the_existing_factory_component(self):
        dtb = self.record["dtb"]
        self.assertEqual((dtb["size_bytes"], dtb["tree_count"]), (4496880, 8))
        self.assertEqual(dtb["sha256"], "1a5c30b75e816f33dd36caa114faa7bc656605e4ac9ffe786726538b37ada22d")
        self.assertIs(dtb["bytes_match_admitted"], True)
        factory = next(row for row in self.factory["header_component_readback"]["components"]
                       if row["path"] == "unpacked/vendor_boot/dtb")
        self.assertEqual(dtb["sha256"], factory["factory_sha256"])

    def test_dtbo_payload_matches_without_claiming_whole_image_equality(self):
        dtbo = self.record["dtbo"]
        self.assertEqual(dtbo["header_words"], [3619138334, 1495111, 32, 32, 1, 32, 4096, 0])
        self.assertEqual(len(dtbo["entries"]), 1)
        entry = dtbo["entries"][0]
        self.assertEqual((entry["size_bytes"], entry["offset"]), (1495047, 64))
        self.assertEqual(entry["sha256"], "4bb4b31bca5de3e354a565304d1ea277ac6d9b70e2760a40147d9f151a691f99")
        self.assertEqual(entry["all_entry_words"], [1495047, 64, 0, 0, 0, 0, 0, 0])
        self.assertIs(dtbo["all_overlay_bytes_match_admitted"], True)
        self.assertIs(dtbo["whole_image_bytes_match_admitted"], False)

    def test_bootconfig_preserves_values_without_claiming_stock_byte_order(self):
        config = self.record["bootconfig"]
        self.assertEqual(config["values"], self.factory["vendor_bootconfig"]["declarations"])
        self.assertEqual(len(config["values"]), 8)
        self.assertEqual(config["size_bytes"], 270)
        self.assertEqual(config["sha256"], "597ae0930da0636ed6099bf5a892004f34885bfbe9f424135d5af6cb46b8fd67")
        self.assertIs(config["all_eight_admitted_values_retained"], True)
        self.assertIs(config["bytes_match_sealed_generated_bootconfig"], True)
        self.assertIs(config["bytes_match_stock_reference"], False)
        self.assertEqual(config["additional_keys"], [])

    def test_ramdisk_counts_and_hashes_distinguish_occurrences_from_paths(self):
        expected = {
            "init_boot": (7159296, 42, 41, "5546b97deb9b6b81b4c6c526c2a41d1d3a025205b7597c8efba0a1d8e860754e"),
            "vendor_boot": (48229632, 440, 440, "3e0a0b297ff1e95a01229b521e723f5dee9f9e1efb1f2b2e8b380e7a33064f2e"),
        }
        for name, values in expected.items():
            r = self.record["ramdisks"][name]
            self.assertEqual(tuple(r[key] for key in ("size_bytes", "entry_count", "unique_path_count", "sha256")), values)
            self.assertEqual(r["archive_count"], 1)
            self.assertEqual(sum(group["entry_count"] for group in r["metadata_groups"]), r["entry_count"])
            self.assertTrue(all(group["uid"] == group["gid"] == 0 for group in r["metadata_groups"]))
            self.assertIs(r["paths_materialized"], False)
            self.assertIs(r["symlinks_followed"], False)
        self.assertEqual(sum(r["entry_count"] for r in self.record["ramdisks"].values()), 482)

    def test_duplicate_directory_preserves_both_identical_metadata_occurrences(self):
        d = self.record["repeated_directory"]
        self.assertEqual((d["cpio"], d["canonical_path"], d["archive"]), ("init_boot", "dev", 0))
        self.assertEqual(len(d["occurrences"]), 2)
        first, second = d["occurrences"]
        self.assertEqual((first["header_offset"], second["header_offset"]), (0, 728))
        self.assertEqual((first["content_offset"], second["content_offset"]), (116, 844))
        self.assertEqual((first["inode"], second["inode"]), (300000, 300006))
        differing = {key for key in first if first[key] != second[key]}
        self.assertEqual(differing, {"occurrence_index", "header_offset", "content_offset", "inode"})
        for item in (first, second):
            self.assertEqual(item["mode"], "0o40755")
            self.assertEqual(item["nlink"], 1)
            for key in ("uid", "gid", "mtime", "size_bytes", "device_major", "device_minor", "rdev_major", "rdev_minor", "checksum"):
                self.assertEqual(item[key], 0)
        for key in ("all_occurrences_preserved", "same_archive_same_spelling_required", "directory_metadata_must_match",
                    "file_symlink_alias_and_ancestor_conflicts_rejected", "generation_explanation_is_source_supported_inference"):
            self.assertIs(d[key], True, key)

    def test_all_modules_match_without_loadability_or_signature_claims(self):
        m = self.record["vendor_ramdisk_modules"]
        self.assertEqual(m["count"], self.factory["vendor_ramdisk_modules"]["factory_module_count"])
        self.assertEqual((m["count"], m["total_module_payload_bytes"]), (430, 47961360))
        self.assertEqual(m["factory_inventory_matching_payload_count"], 430)
        self.assertEqual(m["factory_matching_mode_uid_gid_count"], 430)
        self.assertEqual(m["module_metadata"], {"mode": "0o100644", "uid": 0, "gid": 0})
        self.assertIs(m["all_bytes_match_admitted"], True)
        self.assertIs(m["no_modules_loaded"], True)
        self.assertIs(m["module_abi_and_signature_trust_verified"], False)
        self.assertNotIn("modules", m, "Do not publish the full private module inventory here")

    def test_all_six_module_metadata_files_match_admitted_and_sealed_stage(self):
        m = self.record["vendor_ramdisk_modules"]
        self.assertEqual(m["metadata_file_count"], 6)
        self.assertEqual({Path(row["cpio_path"]).name for row in m["metadata"]},
                         {"modules.alias", "modules.blocklist", "modules.dep", "modules.load", "modules.load.recovery", "modules.softdep"})
        self.assertEqual(sum(row["size_bytes"] for row in m["metadata"]), 200483)
        for row in m["metadata"]:
            self.assertEqual(row["sha256"], row["admitted_sha256"])
            for key in ("bytes_match_admitted", "ordered_noncomment_lines_match_admitted",
                        "sealed_stage_bytes_compared", "sealed_stage_bytes_match"):
                self.assertIs(row[key], True, key)
            self.assertEqual((row["mode"], row["uid"], row["gid"]), ("0o100644", 0, 0))
            if Path(row["cpio_path"]).name in ("modules.blocklist", "modules.load", "modules.load.recovery"):
                self.assertIs(row["required_load_or_blocklist_semantics_match"], True)

    def test_module_load_order_and_duplicates_remain_explicit(self):
        m = self.record["vendor_ramdisk_modules"]
        self.assertEqual((m["normal_load_entries"], m["normal_load_unique_names"]), (157, 154))
        self.assertEqual((m["recovery_load_entries"], m["recovery_load_unique_names"]), (435, 424))
        self.assertIs(m["load_order_and_duplicates_preserved"], True)
        self.assertIs(m["all_load_names_present"], True)

    def test_fstab_is_the_exact_generated_factory_selection(self):
        f = self.record["fstab"]
        self.assertEqual((f["size_bytes"], f["row_count"], f["avb_row_count"]), (5850, 29, 13))
        self.assertEqual(f["sha256"], "f1406e41b969daed6156892e2abafea20293a9e3cd532b7e42de6bf7ca7a987e")
        self.assertIs(f["exact_generated_bytes_match"], True)
        self.assertIs(f["selected_factory_verification_and_encryption_flags_preserved"], True)
        self.assertIs(f["raw_factory_fstab_bytes_adopted_wholesale"], False)
        self.assertIs(f["mounts_or_formatting_performed"], False)
        self.assertEqual(f["cpio_metadata"], {"mode": "0o100644", "uid": 0, "gid": 0, "nlink": 1})

    def test_all_thirteen_selected_avb_rows_retain_chain_names(self):
        rows = self.record["fstab"]["verification_rows"]
        self.assertEqual(len(rows), 13)
        sources = {row["source"].split("/")[-1]: row for row in rows}
        self.assertEqual(set(sources), {"system", "system_ext", "product", "mi_ext", "vendor", "odm",
                                       "vendor_dlkm", "system_dlkm", "boot", "init_boot", "vendor_boot", "dtbo", "recovery"})
        for name, row in sources.items():
            self.assertEqual(row["verification_flags"], ["avb=vbmeta_system" if name in ("system", "system_ext", "product") else "avb=vbmeta"])

    def test_userdata_encryption_declarations_are_retained_without_formatting(self):
        rows = self.record["fstab"]["encryption_rows"]
        data = next(row for row in rows if row["mount_point"] == "/data")
        self.assertEqual(data["filesystem"], "f2fs")
        self.assertIn("inlinecrypt", data["mount_options"])
        self.assertEqual(data["encryption_flags"], [
            "fileencryption=aes-256-xts:aes-256-cts:v2+inlinecrypt_optimized+wrappedkey_v0",
            "keydirectory=/metadata/vold/metadata_encryption", "metadata_encryption=aes-256-xts:wrappedkey_v0",
        ])
        self.assertIs(self.record["fstab"]["mounts_or_formatting_performed"], False)

    def test_missing_gsi_key_paths_do_not_become_a_boot_failure_claim(self):
        k = self.record["referenced_avb_keys"]
        self.assertEqual(k["count"], 7)
        self.assertEqual(k["paths"], ["/avb/" + letter + "-gsi.avbpubkey" for letter in "qrstuvw"])
        self.assertEqual((k["literal_paths_present_in_either_cpio"], k["first_stage_alternatives_present"]), (0, 0))
        self.assertIs(k["absence_is_not_a_boot_failure_conclusion"], True)
        self.assertIs(k["normal_chained_avb_and_alternative_dsu_key_paths_are_distinct"], True)
        for key in ("key_bytes_exported", "runtime_key_availability_verified", "device_unlock_state_verified"):
            self.assertIs(k[key], False, key)
        self.assertEqual(k["pinned_fs_mgr_source_commit"], "241488ea392c01079941d86ddc458b8a0c9ae6e1")

    def test_both_init_elf_files_have_exact_hashes_and_no_execution_claim(self):
        self.assertEqual(set(self.record["init"]), set(INIT))
        for stage, expected in INIT.items():
            item = self.record["init"][stage]
            self.assertEqual((item["binary"]["size_bytes"], item["binary"]["sha256"]), expected)
            self.assertEqual((item["elf"]["elf_class"], item["elf"]["endianness"], item["elf"]["machine"]), (64, "little", 183))
            self.assertIs(item["elf"]["program_file_bounds_verified"], True)
            self.assertIs(item["elf"]["executed"], False)
            self.assertIs(item["runtime_behavior_verified"], False)
            self.assertIn(expected[1], self.doc)

    def test_only_first_stage_init_packaging_is_verified(self):
        first, second = self.record["init"]["first_stage"], self.record["init"]["second_stage"]
        self.assertIs(first["packaging_verified"], True)
        self.assertIs(first["bytes_match_sealed_built_init"], True)
        self.assertEqual(first["cpio_path"], "init")
        self.assertEqual(first["cpio_metadata"], {"mode": "0o100750", "uid": 0, "gid": 0, "nlink": 1})
        self.assertIs(second["packaging_verified"], False)
        self.assertIs(second["packaging_into_system_image_verified"], False)

    def test_both_init_compiler_records_bind_macro_zero_and_correct_sources(self):
        expected = {
            "first_stage": ("system/core/init/first_stage_init.cpp", "dd69639b649c49aaa8513f05f2cf0dc7bf2695d564018ae1f31ec31ea2d769a1",
                            932836, "4e110803aa2a534e680993082ddbc76b2caea0e921c5d0b43904e1e21b7b3dff", 445),
            "second_stage": ("system/core/init/property_service.cpp", "d82faacbbeb80256a416ca81cb9c877def16c3140aa57f4126db41889a67a887",
                             1413488, "1fb65948a27927345a2bdfe0f3cbd287e075bfa80c35d24f57b493298ebb91a3", 457),
        }
        for stage, (path, source_sha, size, object_sha, argc) in expected.items():
            item = self.record["init"][stage]
            self.assertEqual(item["source"], {"path": path, "sha256": source_sha})
            compile_record = item["compile_evidence"]
            self.assertEqual(compile_record["effective_spoof_safetynet_macro"], "0")
            self.assertEqual(compile_record["argv_source"], "ninja-command")
            self.assertEqual((compile_record["object"]["size_bytes"], compile_record["object"]["sha256"]), (size, object_sha))
            self.assertEqual((compile_record["argument_count"], compile_record["response_file_count"]), (argc, 0))

    def test_cumulative_ninja_rows_do_not_prove_invocation_or_binary_linkage(self):
        for item in self.record["init"].values():
            evidence = item["compile_evidence"]
            self.assertIs(evidence["object_mtime_in_build_window"], True)
            self.assertIs(evidence["latest_matching_cumulative_ninja_row_mtime_matches_object"], True)
            self.assertEqual(evidence["cumulative_ninja_log_sha256"], "68794776055ddb4c686debe47ef9536fcc84d52028fdba1e359ec6e90c74cbb5")
            for key in ("current_invocation_proven", "object_linkage_into_binary_independently_proven",
                        "compiler_reexecuted_by_inspection", "reproducible_build_proven"):
                self.assertIs(evidence[key], False, key)

    def test_pinned_host_symbol_reports_do_not_prove_runtime_behavior(self):
        for stage, item in self.record["init"].items():
            symbols = item["symbols"]
            self.assertEqual(symbols["stage"], stage)
            self.assertEqual(symbols["input_binary_sha256"], item["binary"]["sha256"])
            self.assertEqual(symbols["tool_sha256"], "37e565359be0c9f2868348dd314416a420d137ee84c891ec8474cf7d29cfd995")
            self.assertEqual(symbols["exit_code"], 0)
            self.assertEqual(symbols["evidence_sha256"], symbols["receipt"]["sha256"])
            self.assertIs(symbols["symbols_or_their_absence_do_not_prove_runtime_behaviour"], True)
            self.assertGreater(symbols["stdout_size_bytes"], 0)

    def test_effective_security_configuration_has_no_test_or_runtime_shortcut(self):
        config = self.record["effective_configuration"]
        self.assertEqual(config["soong"], {"Debuggable": False, "Eng": False, "SelinuxIgnoreNeverallows": False,
                                          "EnforceSELinuxTrebleLabeling": True, "SELinuxTrebleLabelingTrackingListFile": ""})
        for key, value in config["soong"].items():
            self.assertEqual(value, self.policy["observed_configuration"]["values"][key])
        self.assertEqual(config["dexpreopt"], {"RelaxUsesLibraryCheck": False, "DisablePreopt": False})
        self.assertIs(config["enabled_treble_flag_is_not_proof_of_test_scheduling_or_runtime_compatibility"], True)

    def test_source_policy_success_is_not_full_factory_composition_success(self):
        p = self.record["source_policy_scope"]
        self.assertEqual(p["record"], "research/user-security-build.json")
        binaries = self.policy["source_policy_analysis"]["binaries"]
        self.assertEqual(p["source_policy_binaries_with_zero_permissive_domains"], sum(row["zero_permissive_domains"] for row in binaries))
        self.assertEqual(p["source_policy_binaries_with_zero_permissive_domains"], 2)
        self.assertEqual(p["remaining_neverallow_assertion_sites"], self.policy["strict_factory_check"]["neverallow_assertion_sites"])
        self.assertEqual(p["remaining_neverallow_assertion_sites"], 5)
        for key in ("full_factory_composition_passed", "full_factory_policy_binary_produced", "image_validation_compiled_or_replaced_policy"):
            self.assertIs(p[key], False, key)

    def test_failed_inspector_attempts_are_retained_without_corruption_claims(self):
        h = self.record["inspector_history"]
        self.assertEqual(h["successful_revision"], 3)
        self.assertEqual([item["revision"] for item in h["attempts"]], [1, 2])
        self.assertEqual([item["failure"]["sha256"] for item in h["attempts"]], [
            "8124248f9303bb5234c4f6771e5e25195c5276b30d036632abb5a4a5a4f59437",
            "47f7c7ea0116a426bbaca101077ef938a7a85d8121325c71384ccc8ae3160d6a",
        ])
        self.assertEqual(h["attempts"][0]["reason"], "Duplicate path in CPIO archive: dev")
        self.assertEqual(h["attempts"][1]["reason"], "'entries'")
        for attempt in h["attempts"]:
            self.assertIs(attempt["preserved"], True)
            self.assertIs(attempt["image_or_firmware_corruption_established"], False)
            self.assertIs(attempt["successful_validation_receipt_published"], False)
        self.assertIs(h["cpio_parser_unchanged_between_v2_and_v3"], True)
        self.assertIs(h["standalone_factory_inventory_summary_and_hash_checked"], True)
        self.assertEqual(h["remaining_schema_preflight_input_count"], 47)
        self.assertEqual(h["focused_test_counts"]["validator_v3"], 86)

    def test_successful_readback_counts_and_tool_pins_are_explicit(self):
        v = self.record["validation"]
        self.assertEqual(v["revision"], 3)
        self.assertEqual(v["driver"]["sha256"], "bccbe8e1498610feac0db3cadde61eb36d3c6fdaf8f0157216b8f6d4debf0ee0")
        self.assertEqual((v["input_readback_count"], v["generated_output_files_rehashed"]), (498, 30))
        self.assertEqual(v["generated_output_bytes_rehashed_excluding_receipt"], 83599532)
        self.assertEqual(v["pinned_tool_command_count"], 11)
        self.assertIs(v["all_inputs_rechecked"], True)
        self.assertIs(v["passed"], True)
        self.assertEqual(self.record["tools"]["unpack_bootimg"]["commit"], "954bc3ead5e679005fddf3484d247f2557b3c2c9")
        self.assertEqual(self.record["tools"]["avbtool"]["commit"], "c92ce4cb9a1b6d20a1bc11b7e5864af9f78615bb")
        self.assertEqual(self.record["tools"]["mkdtboimg"]["commit"], "10c6b5f81069d6d78c7ef3833458f4d51d02e2a6")

    def test_unverified_runtime_release_and_recovery_limits_remain_false(self):
        limits = self.record["limits"]
        self.assertIs(limits["all_three_generated_avb_blocks_are_unsigned"], True)
        self.assertIs(limits["hash_integrity_is_not_signature_authentication"], True)
        for key in ("full_vbmeta_chain_verified", "signed_by_authenticated_xiaomi_key", "live_partition_fit_verified",
                    "live_bootloader_state_verified", "full_rom_verified", "device_boot_verified", "native_features_verified",
                    "second_stage_init_packaged_into_system_image_verified", "init_runtime_behavior_verified",
                    "module_loadability_verified", "custom_recovery_built_or_tested", "phone_accessed"):
            self.assertIs(limits[key], False, key)
        self.assertEqual(limits["checks_disabled"], [])
        for key in ("guest_accessed", "live_out_accessed", "images_mounted", "firmware_executed", "phone_accessed"):
            self.assertIs(self.record["validation"][key], False, key)
        self.assertEqual(self.record["validation"]["checks_disabled"], [])

    def test_public_record_remains_metadata_without_private_payloads(self):
        self.assertLess(len(self.text), 50000)
        for forbidden in ("/Users/", "BEGIN PRIVATE KEY", "BEGIN RSA PRIVATE KEY", '"raw_command"',
                          '"expanded_argv"', '"source_identity"', '"serial_number"', '"stdout":'):
            self.assertNotIn(forbidden, self.text)
        for name, source in self.record["tools"].items():
            self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$", name)
        for group in self.record["source_references"].values():
            for source in group:
                self.assertRegex(source["sha256"], r"^[0-9a-f]{64}$")
                self.assertGreater(source["size_bytes"], 0)

    def test_document_links_public_evidence_and_states_unsigned_scope(self):
        for literal in ("All three generated AVB blocks are unsigned", "6,551", "430", "5,850", "86 offline tests",
                        "five neverallow", "not a complete ROM", "Neither inspector failure established firmware corruption"):
            self.assertIn(literal, self.doc)
        for name in ("collection", "sealed_snapshot", "validation"):
            self.assertIn(RECEIPTS[name], self.doc)
        targets = re.findall(r"\]\(([^)]+)\)", self.doc)
        for target in targets:
            if not target.startswith("https://"):
                self.assertTrue((ROOT / "docs" / target).is_file(), target)
        self.assertIn("../research/user-security-build.json", targets)
        self.assertIn("../research/factory-boot-build.json", targets)


if __name__ == "__main__":
    unittest.main()
