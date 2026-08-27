"""Offline checks for factory comparison metadata, not image or device tests."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
FACTORY = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
EU = "b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69"
BUNDLE_SHA = "811f7904adbec2fa99d933179b1247d0c2e30f80a2ba7e0b54c8a2e713917360"
SELECTION_SHA = "c82cf07f512342d7e20cc155a6425bf89d272c6c1fb3fc258e89e50473f7a8d2"
EVIDENCE = {
    "factory_property_comparison": "349783a63894190afcecef489707800a0e03c851b58cac64375774021c08a901",
    "factory_property_values": "d377ae5021b580a6e0aef25c5056c87cc820dbefd5cdebc6e7bbcf0961b5a697",
    "normalized_factory_layout": "8fa822ebe52e9ea1cfea2e6215af150623c6321d782291f9588ddb84636de1c0",
    "layout_normalization": "897830714ee38bc7193a003684e62e5b653b7d52b6bee7d1cbe23928109090c5",
    "camera_comparison": "0994eddaa3a718e2edfd42d1ec125c1647757f02293f2210bf29437c2e384f63",
    "dlkm_comparison": "70e4471ba25fcce901c37aface8f88e4d22b067fc963d1a3f8b12227fb23b018",
    "dlkm_file_comparison": "fc9872cde366b60fecdffd24344006613abf9775c31eca4b077c34e570eb9559",
    "independent_layout_review": "04aa9f32ed114b9dfe7c59b7b336b47e68e09cf8016fc6fb40c6487360a7b716",
    "independent_small_file_readback": "1c36c558a7f4b863921975f68b156576ce15258c24be882f75d20565af2a9684",
    "host_vendor_bundle": BUNDLE_SHA,
    "factory_camera_selection": SELECTION_SHA,
    "factory_selection_derivation": "0fb51972ba98e7e349509d836b9422a1bb17a2add1cc4fc557bbd23506b36c66",
    "canonical_inventory_adapter": "e691fa2bf39e8abed1aae44b36a39a068a34f4dc6aa40ba175ee2b5bde3dee8c",
}


class FactoryInputReuseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def read(path):
            return json.loads((ROOT / path).read_text())

        cls.record = read("research/factory-input-reuse.json")
        cls.doc = (ROOT / "docs/factory-input-reuse.md").read_text()
        cls.boot = read("research/factory-boot-contract.json")
        cls.factory = read("research/factory-firmware-validation.json")
        cls.eu_vintf = read("research/vintf-contract.json")
        cls.selection = read("vendor/xiaomi/nezha/camera-selection.json")

    def test_factory_origin_remains_unknown_and_eu_is_preserved(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["device"], {"codename": "nezha", "hardware_region": "CN"})
        factory = self.record["packages"]["factory"]
        self.assertEqual(factory, {"sha256": FACTORY, "source_kind": "user-provided",
                                   "source_url": None, "origin_verified": False})
        self.assertEqual(self.record["packages"]["xiaomi_eu"],
                         {"sha256": EU, "modified_package": True, "retained_separately": True})

    def test_evidence_hashes_are_explicit_without_private_file_dependencies(self):
        evidence = self.record["evidence"]
        for name, digest in EVIDENCE.items():
            with self.subTest(name=name):
                item = evidence[name]
                self.assertEqual(item["sha256"], digest)
                self.assertGreater(item["size_bytes"], 0)
                self.assertFalse(Path(item["path"]).is_absolute())
                self.assertNotIn("..", Path(item["path"]).parts)
        self.assertEqual(evidence["host_vendor_bundle"]["size_bytes"], 11837)
        self.assertEqual(evidence["dlkm_file_comparison"]["size_bytes"], 680752)

    def test_all_nine_property_files_differ_but_69_selected_values_agree(self):
        properties = self.record["properties"]
        self.assertEqual(properties["logical_image_count"], 8)
        self.assertEqual(properties["property_file_count"], 9)
        self.assertEqual(properties["whole_file_byte_match_count"], 0)
        self.assertEqual(properties["whole_file_byte_difference_count"], 9)
        self.assertEqual(properties["selected_critical_property_count"], 69)
        self.assertEqual(properties["selected_critical_value_difference_count"], 0)
        files = properties["files"]
        self.assertEqual(len(files), 9)
        self.assertEqual(len({item["runtime_path"] for item in files}), 9)
        self.assertEqual(sum(item["selected_critical_property_count"] for item in files), 69)
        for item in files:
            self.assertIs(item["whole_file_bytes_equal"], False)
            self.assertIs(item["selected_critical_values_equal"], True)
            self.assertNotEqual(item["factory_sha256"], item["eu_sha256"])
            baseline = self.eu_vintf["source_files"][item["runtime_path"]]
            self.assertEqual((item["eu_sha256"], item["eu_size_bytes"]),
                             (baseline["sha256"], baseline["size_bytes"]))
        self.assertEqual(sum(item["factory_size_bytes"] + item["eu_size_bytes"] for item in files), 136129)
        self.assertEqual(properties["factory_and_eu_property_bytes_rehashed"], 136129)
        self.assertEqual(properties["source_image_bytes_hashed_by_guarded_capture"], 12477939712)

    def test_selected_api_patch_and_debug_values_remain_exact(self):
        values = {(item["runtime_path"], item["key"]): item["factory_and_eu_value"]
                  for item in self.record["properties"]["selected_key_values"]}
        expected = {
            ("/odm/etc/build.prop", "ro.product.first_api_level"): "36",
            ("/vendor/build.prop", "ro.board.first_api_level"): "202504",
            ("/vendor/build.prop", "ro.board.api_level"): "202504",
            ("/vendor/build.prop", "ro.board.api_frozen"): "true",
            ("/vendor/build.prop", "ro.vendor.build.version.sdk"): "36",
            ("/vendor/build.prop", "ro.vendor.build.security_patch"): "2026-02-01",
            ("/vendor/build.prop", "ro.board.platform"): "canoe",
            ("/system/build.prop", "ro.build.version.sdk"): "36",
            ("/system/build.prop", "ro.build.version.security_patch"): "2026-07-01",
            ("/system/build.prop", "ro.llndk.api_level"): "202504",
            ("/system/build.prop", "ro.build.type"): "user",
            ("/system/build.prop", "ro.debuggable"): "0",
            ("/system/build.prop", "ro.secure"): "1",
            ("/system/build.prop", "ro.adb.secure"): "1",
        }
        self.assertEqual(values, expected)
        self.assertEqual(len(self.record["properties"]["selected_key_values"]), len(expected))
        for (path, key), value in values.items():
            known = self.eu_vintf["properties_by_source"][path]
            if key in known:
                self.assertEqual(value, known[key])

    def test_bare_property_line_stays_uninterpreted_in_both_packages(self):
        properties = self.record["properties"]
        lines = properties["uninterpreted_lines"]
        self.assertEqual(len(lines), 2)
        self.assertEqual({(item["source"], item["line"]) for item in lines},
                         {("factory", 480), ("xiaomi_eu", 479)})
        for item in lines:
            self.assertEqual(item["runtime_path"], "/odm/etc/build.prop")
            self.assertEqual(item["literal"], "ro.vendor.mitee_support")
            self.assertNotIn("=", item["literal"])
            self.assertIs(item["interpreted_as_empty_assignment"], False)
        self.assertIs(properties["uninterpreted_line_was_not_an_empty_assignment"], True)
        initial = properties["initial_analysis"]
        self.assertIs(initial["capture_completed"], True)
        self.assertIs(initial["analysis_completed"], False)
        self.assertIs(initial["original_capture_receipts_preserved"], True)
        self.assertIs(initial["firmware_corrupt_claimed"], False)
        self.assertIs(properties["runtime_precedence_or_imports_resolved"], False)
        self.assertIs(properties["effective_vintf_verified_by_this_comparison"], False)

    def test_normalized_layout_counts_and_geometry_bind_factory_metadata(self):
        layout = self.record["normalized_layout"]
        factory = self.factory["logical_partitions"]
        self.assertEqual(layout["logical_partition_count"], len(factory["partitions"]))
        self.assertEqual(layout["logical_partition_count"], 16)
        self.assertEqual(layout["populated_partition_count"], 8)
        self.assertEqual(layout["empty_b_partition_count"], 8)
        self.assertEqual(layout["allocated_logical_bytes"], sum(item["size_bytes"] for item in factory["partitions"]))
        self.assertEqual(layout["allocated_logical_bytes"], 12477939712)
        group = next(item for item in factory["groups"] if item["name"] == layout["group_name"])
        self.assertEqual(layout["group_name"], "qti_dynamic_partitions_a")
        self.assertEqual(layout["group_allocated_bytes"], group["allocated_size"])
        self.assertEqual(layout["group_allocated_bytes"], layout["allocated_logical_bytes"])
        self.assertEqual(layout["group_maximum_bytes"], group["maximum_size"])
        self.assertEqual(layout["group_maximum_bytes"], 15290335232)
        self.assertEqual(layout["super_declared_bytes"], 15300820992)
        self.assertLess(layout["group_allocated_bytes"], layout["group_maximum_bytes"])
        self.assertLess(layout["group_maximum_bytes"], layout["super_declared_bytes"])
        self.assertEqual(layout["raw_super_sha256"], factory["source_image"]["sha256"])
        self.assertIs(layout["geometry_is_package_metadata_not_live_capacity"], True)
        self.assertEqual(layout["logical_extraction_receipt"], factory["receipt"])

    def test_avb_label_mapping_reuses_exact_external_proof_without_authentication(self):
        layout = self.record["normalized_layout"]
        self.assertEqual(layout["external_avb_receipt"], self.factory["avb"]["receipt"])
        self.assertEqual(layout["filesystem_receipt"], self.factory["filesystems"]["receipt"])
        self.assertEqual(layout["recorded_avb_status"], "passed")
        self.assertEqual(layout["vendor_tool_mapped_avb_status"], "verified")
        self.assertIs(layout["mapping_is_not_new_authentication"], True)
        self.assertIs(self.record["host_vendor_bundle"]["source"]["source_trust_is_from_record_not_reauthenticated"], True)
        self.assertIs(self.record["host_vendor_bundle"]["verification"]["avb_checked_by_this_tool"], False)

    def test_schema_plan_success_does_not_become_device_generation_or_activation(self):
        layout = self.record["normalized_layout"]
        self.assertIs(layout["vendor_base_plan_accepted"], True)
        self.assertIs(layout["base_plan_exercised_camera_extra_guards"], False)
        self.assertEqual(layout["device_derive_variants_accepted"], ["user", "userdebug"])
        self.assertIs(layout["schema_plans_used_historical_eu_boot_reference"], True)
        self.assertIs(layout["schema_plans_were_mixed_package_references"], True)
        self.assertIs(layout["device_target_generated_by_normalization"], False)
        self.assertIs(layout["historical_eu_layout_unchanged"], True)

    def test_dlkm_aggregates_count_files_modules_metadata_and_bytes_separately(self):
        dlkm = self.record["module_payloads"]["dlkm"]
        self.assertEqual((dlkm["file_count"], dlkm["module_file_instances"], dlkm["metadata_file_count"]),
                         (504, 484, 20))
        self.assertEqual(dlkm["file_bytes"], 143279456)
        parts = {item["partition"]: item for item in dlkm["partitions"]}
        expected = {"vendor_dlkm": (387, 381, 6, 129052231), "system_dlkm": (117, 103, 14, 14227225)}
        self.assertEqual(set(parts), set(expected))
        for name, totals in expected.items():
            item = parts[name]
            self.assertEqual((item["file_count"], item["module_file_instances"],
                              item["metadata_file_count"], item["file_bytes"]), totals)
            self.assertEqual(item["module_file_instances"] + item["metadata_file_count"], item["file_count"])
            self.assertEqual((item["files_added"], item["files_removed"], item["files_changed"]), (0, 0, 0))
            self.assertIs(item["all_file_bytes_equal_eu_source_and_existing_bundle"], True)
        for key in ["file_count", "module_file_instances", "metadata_file_count", "file_bytes"]:
            self.assertEqual(sum(item[key] for item in parts.values()), dlkm[key])
        self.assertIs(dlkm["all_bytes_equal_eu_source_and_existing_bundle"], True)

    def test_914_counts_module_file_instances_not_unique_or_loaded_modules(self):
        modules = self.record["module_payloads"]
        self.assertEqual(modules["vendor_ramdisk_module_file_instances"],
                         self.boot["vendor_ramdisk_modules"]["factory_module_count"])
        self.assertEqual(modules["vendor_ramdisk_module_file_instances"], 430)
        self.assertEqual(modules["combined_module_file_instances"],
                         modules["dlkm"]["module_file_instances"] + modules["vendor_ramdisk_module_file_instances"])
        self.assertEqual(modules["combined_module_file_instances"], 914)
        self.assertIsNone(modules["unique_module_count"])
        self.assertIn("not 914 unique modules or loaded modules", modules["count_basis"])
        self.assertEqual(modules["vendor_ramdisk_comparison_receipt"], self.boot["ramdisk_comparison"]["receipt"])
        self.assertIs(modules["vendor_ramdisk_all_module_bytes_equal_eu"], True)
        self.assertIs(modules["appended_signature_bytes_included_when_present"], True)
        for key in ["stripping_or_resigning_performed_by_comparison", "abi_or_provider_selection_verified_by_equality",
                    "module_signature_trust_verified_by_equality", "modules_loaded_by_comparison"]:
            self.assertIs(modules[key], False)

    def test_camera_originals_and_selected_outputs_have_distinct_totals(self):
        camera = self.record["camera"]
        files = camera["files"]
        self.assertEqual(len(files), camera["original_source_file_count"])
        self.assertEqual(camera["original_source_file_count"], 9)
        self.assertEqual(len({item["source_runtime_path"] for item in files}), 9)
        self.assertEqual(len({item["selected_runtime_path"] for item in files}), 9)
        self.assertEqual(sum(item["source_size_bytes"] for item in files), 544623)
        self.assertEqual(camera["original_source_total_bytes"], 544623)
        self.assertEqual(sum(item["selected_size_bytes"] for item in files), 542236)
        self.assertEqual(camera["selected_output_total_bytes"], 542236)
        self.assertEqual(camera["selected_output_count"], 9)
        self.assertEqual(Counter(item["type"] for item in files), camera["type_counts"])
        self.assertEqual(camera["type_counts"], {"dex_jar": 4, "shared_library": 1, "xml": 4})
        self.assertEqual(sum(item["selected_output_is_original_factory_file"] for item in files), 7)
        self.assertEqual(camera["direct_output_count"], 7)
        self.assertEqual(camera["derived_xml_output_count"], 2)
        self.assertIs(camera["all_original_source_bytes_equal_eu"], True)
        self.assertIs(camera["all_selected_outputs_reproduced_from_factory_sources"], True)

    def test_camera_selection_payloads_match_the_preserved_public_selection(self):
        original = {item["runtime_path"]: item for item in self.selection["modules"]}
        for item in self.record["camera"]["files"]:
            selected = original[item["selected_runtime_path"]]
            self.assertEqual((item["selected_sha256"], item["selected_size_bytes"], item["type"]),
                             (selected["sha256"], selected["size_bytes"], selected["type"]))
            source = selected.get("derivation", {}).get("source", selected)
            self.assertEqual((item["source_runtime_path"], item["source_sha256"], item["source_size_bytes"]),
                             (source["runtime_path"], source["sha256"], source["size_bytes"]))
            self.assertIs(item["source_bytes_equal_eu"], True)
            self.assertIs(item["selected_output_reproduced_from_factory"], True)

    def test_derived_xml_outputs_are_not_labeled_original_factory_files(self):
        modules = {item["runtime_path"]: item for item in self.selection["modules"]}
        derived = [item for item in self.record["camera"]["files"] if "derivation" in item]
        self.assertEqual(len(derived), 2)
        for item in derived:
            self.assertEqual(item["type"], "xml")
            self.assertIs(item["selected_output_is_original_factory_file"], False)
            self.assertNotEqual(item["source_sha256"], item["selected_sha256"])
            original_recipe = modules[item["selected_runtime_path"]]["derivation"]
            digest = hashlib.sha256(json.dumps(original_recipe, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            self.assertEqual(item["derivation"]["recipe_sha256"], digest)
            for key in ["kind", "library_name", "source_library_file", "library_file"]:
                self.assertEqual(item["derivation"][key], original_recipe[key])
        postproc = next(item for item in derived if "postprocservice" in item["selected_runtime_path"])
        self.assertTrue(postproc["derivation"]["source_library_file"].startswith("/system/framework/"))
        self.assertTrue(postproc["derivation"]["library_file"].startswith("/system_ext/framework/"))

    def test_new_selection_changes_only_package_binding_and_does_not_include_apk(self):
        camera = self.record["camera"]
        self.assertIs(camera["factory_selection_changes_only_package_sha256"], True)
        self.assertIs(camera["historical_selection_preserved"], True)
        self.assertEqual(self.selection["package_sha256"], EU)
        original = ROOT / "vendor/xiaomi/nezha/camera-selection.json"
        self.assertEqual(hashlib.sha256(original.read_bytes()).hexdigest(), camera["historical_selection_sha256"])
        self.assertEqual(self.record["host_vendor_bundle"]["source"]["selection_sha256"], SELECTION_SHA)
        for key in ["apk_included", "apk_executed", "runtime_class_loader_or_camera_feature_compatibility_verified"]:
            self.assertIs(camera[key], False)

    def test_canonical_inventory_adapter_copies_only_two_metadata_files(self):
        adapter = self.record["canonical_inventory_adapter"]
        self.assertEqual(adapter["file_count"], 2)
        self.assertEqual(len(adapter["files"]), 2)
        expected = {
            "inventory.json": (429688, "bc53750daaf9b7747aaf5b7d5ea54ddfce439c796da8658c35eec45b37bf63e3"),
            "receipt.json": (991, "83547126d6de4fb414bad6508f5b845060d2cf89c12bfe23b394057c80799f56"),
        }
        for item in adapter["files"]:
            name = Path(item["source"]).name
            self.assertEqual((item["size_bytes"], item["sha256"]), expected[name])
            self.assertEqual(Path(item["destination"]).name, name)
            self.assertIn("/erofs-contract-v1/inventory/system_ext/", item["source"])
            self.assertIn("/erofs/system_ext_a-inventory/", item["destination"])
            self.assertIs(item["source_unchanged"], True)
            self.assertIs(item["destination_readback_verified"], True)
        self.assertIs(adapter["metadata_copies_byte_identical"], True)
        self.assertIs(adapter["originals_preserved"], True)
        for key in ["receipt_contents_changed", "images_rescanned", "guards_disabled", "links_used"]:
            self.assertIs(adapter[key], False)

    def test_initial_staging_failure_remains_separate_from_success(self):
        adapter = self.record["canonical_inventory_adapter"]
        initial = adapter["initial_stage"]
        self.assertIs(initial["bundle_publication_reached"], False)
        self.assertIs(initial["success_json_emitted"], False)
        self.assertEqual(initial["stdout"]["size_bytes"], 0)
        self.assertEqual(initial["stderr"]["size_bytes"], 200)
        self.assertEqual(initial["stderr"]["sha256"],
                         "e4c5906f9eb6cf2d2b0abb6c4679ff178d39b8588b8e0d42b016915b578bd950")
        successful = adapter["successful_stage"]
        self.assertEqual(successful["stdout"]["sha256"], BUNDLE_SHA)
        self.assertEqual(successful["stdout"]["size_bytes"], 11837)
        self.assertEqual(successful["stderr"]["size_bytes"], 0)
        self.assertEqual(successful["stderr"]["sha256"], hashlib.sha256(b"").hexdigest())

    def test_host_bundle_counts_images_extras_and_generated_files_separately(self):
        bundle = self.record["host_vendor_bundle"]
        self.assertEqual(bundle["operation"], "vendor-inputs-stage")
        self.assertIs(bundle["host_staging_complete"], True)
        self.assertEqual((bundle["image_count"], bundle["extra_count"], bundle["generated_file_count"]), (2, 9, 5))
        self.assertEqual(bundle["image_bytes"], 5727330304)
        self.assertEqual(bundle["extra_bytes"], self.record["camera"]["selected_output_total_bytes"])
        self.assertEqual(bundle["image_bytes"] + bundle["extra_bytes"], bundle["total_blob_bytes"])
        self.assertEqual(bundle["total_blob_bytes"], 5727872540)
        self.assertEqual(len(bundle["generated_files"]), 5)
        self.assertEqual(sum(item["size_bytes"] for item in bundle["generated_files"]), 5354)
        self.assertEqual(bundle["generated_file_bytes_not_in_blob_total"], 5354)
        for item in bundle["generated_files"]:
            self.assertIs(item["readback_verified"], True)

    def test_host_images_and_source_bind_the_exact_factory_extraction(self):
        bundle = self.record["host_vendor_bundle"]
        outputs = {item["partition"]: item for item in self.factory["logical_partitions"]["outputs"]}
        self.assertEqual(set(bundle["images"]), {"vendor", "odm"})
        for name, item in bundle["images"].items():
            source = outputs[item["source_partition"]]
            self.assertEqual(item["source_partition"], name + "_a")
            self.assertEqual((item["sha256"], item["size_bytes"]), (source["sha256"], source["size_bytes"]))
            self.assertIs(item["readback_verified"], True)
        source = bundle["source"]
        self.assertEqual(source["package_sha256"], FACTORY)
        self.assertEqual(source["source_record_sha256"], EVIDENCE["normalized_factory_layout"])
        self.assertEqual(source["logical_receipt_sha256"], self.factory["logical_partitions"]["receipt"]["sha256"])
        self.assertEqual(source["raw_super_sha256"], self.record["normalized_layout"]["raw_super_sha256"])
        self.assertEqual(source["source_kind"], "user-provided")
        self.assertIs(source["origin_verified"], False)
        self.assertIsNone(bundle["origin_url_retained_in_bound_normalized_source_record"])

    def test_host_staging_does_not_claim_guest_build_or_device_compatibility(self):
        bundle = self.record["host_vendor_bundle"]
        self.assertIs(bundle["verification"]["input_blob_hashes_checked"], True)
        for key, value in bundle["verification"].items():
            if key != "input_blob_hashes_checked":
                self.assertIs(value, False, key)
        self.assertIs(bundle["guest_adoption_proven_by_this_receipt"], False)
        self.assertIs(bundle["build_or_device_compatibility_proven_by_this_receipt"], False)
        normalized_doc = " ".join(self.doc.split())
        self.assertIn("staged on the host", normalized_doc)
        self.assertIn("does not establish installation in the builder", normalized_doc)

    def test_independent_review_and_readback_counts_are_evidence_not_hardware_tests(self):
        validation = self.record["independent_validation"]
        self.assertIs(validation["layout_review_passed"], True)
        self.assertEqual(validation["layout_review_material_findings"], 0)
        self.assertEqual(validation["critical_factory_values_independently_parsed"], 69)
        self.assertEqual(validation["small_file_readback_count"], 88)
        self.assertEqual(validation["small_file_readback_bytes"], 3360249)
        self.assertIs(validation["small_file_hashes_and_lengths_match"], True)
        self.assertEqual(validation["prior_full_offline_test_count"], 968)
        self.assertEqual(validation["prior_full_offline_test_log"]["test_count"], 968)
        self.assertIs(validation["tests_are_not_android_build_or_phone_tests"], True)

    def test_publication_boundaries_do_not_change_phone_guest_or_old_records(self):
        for key, value in self.record["publication_boundaries"].items():
            self.assertIs(value, False, key)
        self.assertEqual(set(self.record["publication_boundaries"]), {
            "fresh_image_access", "firmware_executed", "guest_accessed", "phone_accessed",
            "proprietary_payloads_or_signing_keys_published", "historical_records_rewritten",
            "build_inputs_activated_by_this_publication", "oem_origin_or_trust_root_authenticated",
            "phone_partition_fit_or_rollback_verified", "rom_boot_or_native_features_verified",
        })

    def test_record_is_compact_metadata_without_payloads_and_links_resolve(self):
        def check(value):
            if isinstance(value, dict):
                for key, item in value.items():
                    if (key.endswith("sha256") and item is not None
                            and key != "factory_selection_changes_only_package_sha256"):
                        for digest in item if isinstance(item, list) else [item]:
                            self.assertRegex(digest, r"^[0-9a-f]{64}$")
                    self.assertNotIn(key, {"raw_contents", "base64_payload", "signing_key", "private_key",
                                           "serial", "serial_number", "imei", "ordered_entries"})
                    check(item)
            elif isinstance(value, list):
                self.assertLess(len(value), 40, "do not publish full raw inventories")
                for item in value:
                    check(item)

        check(self.record)
        raw = (ROOT / "research/factory-input-reuse.json").read_bytes()
        self.assertLess(len(raw), 50 * 1024)
        serialized = raw.decode()
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("PRIVATE KEY-----", serialized)
        for related in self.record["related_records"]:
            self.assertTrue((ROOT / related).is_file(), related)
        for target in re.findall(r"\]\(([^)]+)\)", self.doc):
            self.assertFalse(Path(target).is_absolute())
            self.assertTrue((ROOT / "docs" / target).is_file(), target)
        for key in ["normalized_factory_layout", "factory_property_comparison", "dlkm_comparison",
                    "camera_comparison", "factory_camera_selection", "host_vendor_bundle",
                    "independent_layout_review"]:
            self.assertIn(self.record["evidence"][key]["sha256"], self.doc)


if __name__ == "__main__":
    unittest.main()
