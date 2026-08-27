"""Offline invariants for actual VINTF results, provenance and limited scope."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class VintfValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/vintf-validation.json").read_text())
        cls.contract = json.loads((ROOT / "research/vintf-contract.json").read_text())
        cls.apex = json.loads((ROOT / "research/apex-dependencies.json").read_text())
        cls.layout = json.loads((ROOT / "research/firmware-layout.json").read_text())

    def test_record_retains_exact_device_and_untrusted_modified_input(self):
        record = self.record
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["device"], {"codename": "nezha", "hardware_region": "CN"})
        source = record["provenance"]
        self.assertEqual(source["package_sha256"], self.layout["package"]["sha256"])
        self.assertEqual(source["package_sha256"], self.apex["provenance"]["package_sha256"])
        self.assertIn("modified Xiaomi.eu", source["source_kind"])
        self.assertEqual(source["input_avb_status"], "failed")
        self.assertIsNone(source["source_url"])
        for key in ("origin_verified", "oem_signature_authenticated", "signed_image_set_valid",
                    "proprietary_payloads_committed"):
            self.assertIs(source[key], False, key)

    def test_validator_source_matches_resolved_platform_project(self):
        tool = self.record["tool"]
        snapshot = tool["source_snapshot"]
        data = (ROOT / snapshot["path"]).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), snapshot["sha256"])
        self.assertEqual(len(data), snapshot["size_bytes"])
        project = next(p for p in ET.fromstring(data).findall("project")
                       if p.get("path") == "system/libvintf")
        self.assertEqual(tool["libvintf_commit"], project.get("revision"))
        self.assertEqual(tool["libvintf_project"], project.get("name"))
        for url in self.record["primary_sources"]:
            self.assertIn(tool["libvintf_commit"], url)
            self.assertTrue(url.startswith("https://android.googlesource.com/platform/system/libvintf/+"))
        self.assertEqual(tool["binary_sha256"],
                         "672c43b9208a2bb24d192d9fcbe12644712996c7e79a0d38ac2f36d6d65b40b0")

    def test_original_staging_counts_include_unconsumed_kernel_config(self):
        inputs = self.record["original_inputs"]
        self.assertEqual(inputs["xml_files"], self.contract["scope"]["vintf_xml_files"])
        self.assertEqual(inputs["xml_files"], 209)
        self.assertEqual(sum(inputs["xml_files_by_partition"].values()), inputs["xml_files"])
        self.assertEqual(inputs["xml_files_by_partition"],
                         {"vendor": 141, "odm": 37, "system": 19, "system_ext": 9, "product": 3})
        self.assertEqual(inputs["total_staged_files"], inputs["xml_files"] + 1)
        self.assertEqual(inputs["total_staged_bytes"], inputs["xml_bytes"] + inputs["kernel_config"]["size_bytes"])
        self.assertIs(inputs["kernel_config"]["consumed_by_check_one"], False)
        for key in ("all_files_rehashed_before_and_after", "all_files_unchanged"):
            self.assertIs(inputs[key], True)
        for key in ("nested_directories_flattened", "matrix_fragments_removed"):
            self.assertIs(inputs[key], False)

    def test_observed_info_list_is_whole_and_vendor_odm_coverage_is_exact(self):
        inputs = self.record["active_apex_inputs"]
        observed = self.apex["stock_observations"]
        self.assertEqual(inputs["apex_info_entries"], observed["active_total_entries"])
        self.assertEqual(inputs["apex_info_entries"], 39)
        self.assertEqual(inputs["active_vendor_count"], 3)
        self.assertEqual(inputs["active_odm_count"], 0)
        self.assertEqual(inputs["active_vendor_modules"],
                         [e["moduleName"] for e in observed["selected_active_modules"]])
        self.assertEqual(inputs["active_odm_modules"], [])
        self.assertEqual(inputs["live_active_metadata_receipt"], observed["active_metadata"])
        self.assertEqual(inputs["live_content_comparison"], observed["content_comparison"])
        self.assertTrue(inputs["observed_list_copied_unchanged"])
        for key in ("list_filtered_or_fabricated", "apex_ready_property_overridden",
                    "system_apex_content_staged", "full_runtime_apex_set_validated"):
            self.assertIs(inputs[key], False, key)

    def test_only_three_exact_xml_inputs_are_staged_with_module_names(self):
        inputs = self.record["active_apex_inputs"]
        files = {f["path"]: f for f in inputs["files"]}
        expected = {"apex-info-list.xml",
                    "com.android.hardware.cas/etc/vintf/android.hardware.cas-service.xml",
                    "com.google.android.widevine/etc/vintf/com.google.android.widevine.xml"}
        self.assertEqual(set(files), expected)
        self.assertEqual(inputs["staged_file_count"], len(files))
        self.assertEqual(inputs["staged_bytes"], sum(f["size_bytes"] for f in files.values()))
        self.assertEqual(inputs["staged_bytes"], 13940)
        self.assertEqual(files["apex-info-list.xml"]["sha256"], self.apex["stock_observations"]["active_xml_sha256"])
        for module in self.apex["modules"]:
            for fragment in module["vintf"]:
                row = files[fragment["runtime_path"].removeprefix("/apex/")]
                self.assertEqual(row["sha256"], fragment["sha256"])
        self.assertTrue(all(f["readback_verified"] for f in files.values()))
        self.assertFalse(any("nonupdatable" in name for name in files))

    def test_live_package_and_fragment_match_does_not_include_denied_protobufs(self):
        inputs = self.record["active_apex_inputs"]
        self.assertEqual(inputs["package_count_matched_to_live"], len(self.apex["modules"]))
        self.assertEqual(inputs["package_bytes_matched_to_live"], sum(m["package_bytes"] for m in self.apex["modules"]))
        self.assertEqual(inputs["package_bytes_matched_to_live"], 6348800)
        self.assertEqual(inputs["vintf_fragments_matched_to_live"], 2)
        denied = inputs["mounted_manifest_read_denials"]
        self.assertEqual(len(denied), 3)
        unavailable = {r["path"]: r for r in self.apex["stock_observations"]["unavailable"]}
        self.assertEqual({r["path"] for r in denied}, set(unavailable))
        for row in denied:
            self.assertEqual(row["status"], "permission-denied-not-metadata")
            self.assertFalse(row["staged"])
            self.assertEqual(row["observed_sha256"], unavailable[row["path"]]["diagnostic_sha256"])
            self.assertEqual(row["observed_size_bytes"], unavailable[row["path"]]["diagnostic_bytes"])
        self.assertIs(inputs["denied_error_content_staged"], False)

    def test_wifi_absence_is_bound_to_a_complete_matching_payload_inventory(self):
        inputs = self.record["active_apex_inputs"]
        wifi = inputs["wifi"]
        self.assertEqual(wifi["regular_files"], ["/apex_manifest.pb", "/etc/wifi_compat.json"])
        self.assertEqual(wifi["complete_inventory_entries"], 4)
        self.assertFalse(wifi["vintf_directory_present"])
        self.assertTrue(wifi["absence_justified_by_complete_matching_payload_inventory"])
        self.assertEqual(wifi["validator_lookup_result"], "NAME_NOT_FOUND")
        inventories = {r["module_name"]: r for r in inputs["payload_inventories"]}
        self.assertEqual(set(inventories), set(inputs["active_vendor_modules"]))
        for module in self.apex["modules"]:
            row = inventories[module["module_name"]]
            self.assertEqual(row["receipt_sha256"], module["static_inspection_receipt"]["sha256"])
            self.assertEqual(row["regular_files"], module["regular_files"])
            self.assertEqual(row["inventory_entries"], module["inventory_entries_excluding_root"])
            self.assertEqual(row["vintf_paths"], [f["payload_path"] for f in module["vintf"]])

    def test_actual_commands_keep_separate_modes_and_failure(self):
        checks = self.record["checks"]
        self.assertEqual(len(checks), 4)
        self.assertEqual([c["exit_code"] for c in checks], [0, 0, 70, 0])
        self.assertEqual([c["passed"] for c in checks], [True, True, False, True])
        self.assertIn("--dump-file-list", checks[0]["argv"])
        for check in checks[1:]:
            argv = check["argv"]
            self.assertEqual(argv[0], self.record["tool"]["binary_path"])
            self.assertIn("--check-one", argv)
            self.assertNotIn("--check-compat", argv)
            self.assertNotIn("--kernel", argv)
            dirmaps = [argv[i + 1] for i, a in enumerate(argv) if a == "--dirmap"]
            self.assertEqual(sum(p.startswith(("/vendor:", "/system:")) for p in dirmaps), 1)
            self.assertEqual(any(p.startswith("/apex:") for p in dirmaps), check["active_vendor_apex_included"])
            self.assertFalse(any("apex.all.ready=" in a for a in argv))
        self.assertEqual(checks[-1]["started_at"], "2026-08-27T19:30:27.620416+00:00")
        self.assertEqual(checks[-1]["completed_at"], "2026-08-27T19:30:27.699571+00:00")

    def test_fetch_counts_distinguish_staging_from_selection(self):
        checks = self.record["checks"]
        self.assertEqual([c["unique_successful_input_fetches"] for c in checks], [0, 175, 31, 178])
        counts = checks[-1]["fetched_partition_xml_by_partition"]
        self.assertEqual(counts, {"vendor": 138, "odm": 37, "system": 0, "system_ext": 0, "product": 0})
        self.assertEqual(checks[-1]["fetched_apex_info_lists"], 1)
        self.assertEqual(checks[-1]["fetched_apex_vintf_xml"], 2)
        self.assertEqual(sum(counts.values()) + 1 + 2, checks[-1]["unique_successful_input_fetches"])
        self.assertEqual(len(self.record["original_inputs"]["vendor_xml_not_selected_for_observed_skus"]), 141 - counts["vendor"])
        self.assertIn("/vendor/etc/vintf/manifest_alor.xml",
                      self.record["original_inputs"]["vendor_xml_not_selected_for_observed_skus"])

    def test_properties_are_observed_values_not_apex_readiness_bypass(self):
        props = self.record["properties"]["values"]
        observed = self.contract["runtime_property_observations"]["properties"]
        for name, observation in observed.items():
            self.assertEqual(props[name], observation["value"])
        self.assertEqual(props["ro.product.first_api_level"],
                         self.contract["properties_by_source"]["/odm/etc/build.prop"]["ro.product.first_api_level"])
        self.assertFalse(self.record["properties"]["overrides_modify_phone"])
        for check in self.record["checks"][1:]:
            argv = check["argv"]
            supplied = dict(argv[i + 1].split("=", 1) for i, a in enumerate(argv) if a == "--property")
            self.assertEqual(supplied, props)

    def test_framework_failure_retains_all_legacy_references(self):
        failure = self.record["stock_framework_failure"]
        self.assertEqual(failure["exit_code"], 70)
        self.assertEqual(failure["matrix_levels"], [5, 6, 7, 8])
        self.assertEqual(failure["unique_interface_definitions"], len(failure["interfaces"]))
        self.assertEqual(failure["unique_interface_definitions"], 5)
        self.assertEqual(failure["matrix_references"], sum(len(row["matrix_paths"]) for row in failure["interfaces"]))
        self.assertEqual(failure["matrix_references"], 11)
        names = {row["interface"] for row in failure["interfaces"]}
        self.assertIn("android.hardware.automotive.audiocontrol@1.0::IAudioControl", names)
        self.assertIn("android.hardware.automotive.audiocontrol@2.0::IAudioControl", names)
        self.assertIn("android.hardware.vr@1.0::IVr", names)
        self.assertIn("vendor.dolby.hardware.dms@2.0::IDms", names)
        self.assertIn("vendor.dolby_3_12.hardware.dms@2.0::IDms", names)
        self.assertEqual(failure["checks_disabled"], [])
        for key in ("stock_matrix_files_changed", "proves_nezha_runtime_incompatibility",
                    "is_evolution_framework_vendor_compatibility_result"):
            self.assertIs(failure[key], False)

    def test_sandbox_preserves_read_only_source_and_reports_actual_exceptions(self):
        sandbox = self.record["sandbox"]
        args = sandbox["argv_prefix"]
        self.assertEqual(args[0], self.record["tool"]["nsjail_path"])
        self.assertEqual(args[args.index("-R") + 1], "/")
        self.assertEqual(args[args.index("-B") + 1], "/tmp")
        self.assertEqual(sandbox["read_write_bind_paths"], ["/tmp"])
        self.assertTrue(sandbox["source_and_inputs_read_only_to_validator"])
        self.assertTrue(sandbox["root_bind_read_only"])
        self.assertTrue(sandbox["configuration_matches_previous_partition_checks"])
        self.assertTrue(sandbox["global_uid_gid_zero_warning_retained"])
        self.assertTrue(sandbox["proc_read_write"])
        self.assertFalse(sandbox["cgroup_namespace_enabled"])
        self.assertIn("--disable_clone_newcgroup", args)
        self.assertEqual(sandbox["validator_timeout_seconds"], 60)
        self.assertEqual(sandbox["supervisor_timeout_seconds"], 75)

    def test_validation_limits_do_not_promote_load_success_to_compatibility(self):
        verified = {"supplied_xml_hashes_verified", "observed_active_info_xml_preserved",
                    "all_active_vendor_odm_apex_vintf_paths_accounted_for",
                    "host_vendor_manifest_load_merge_passed", "host_device_matrix_parse_passed"}
        for field, value in self.record["verification_boundaries"].items():
            self.assertIs(value, field in verified, field)
        self.assertGreaterEqual(len(self.record["mode_limits"]), 5)
        self.assertGreaterEqual(len(self.record["remaining_checks"]), 4)
        preflight = self.record["failed_preflight"]
        self.assertFalse(preflight["validator_executed"])
        self.assertFalse(preflight["guest_directory_created"])
        self.assertFalse(preflight["original_inputs_changed"])

    def test_receipts_and_public_record_do_not_need_private_inputs(self):
        def walk(value):
            if isinstance(value, dict):
                forbidden = {"serial", "serialno", "imei", "imsi", "meid", "account", "email",
                             "phone_number", "stdout", "stderr", "data", "base64", "content"}
                self.assertFalse(forbidden.intersection(value))
                for key, child in value.items():
                    if key.endswith("sha256"):
                        self.assertRegex(child, r"^[a-f0-9]{64}$", key)
                    walk(child)
            elif isinstance(value, list):
                for child in value:
                    walk(child)
            elif isinstance(value, str):
                self.assertNotIn("/Users/", value)
                self.assertNotIn("/home/", value)
                self.assertNotIn("-----BEGIN", value)
        walk(self.record)
        for receipt in self.record["receipts"].values():
            path = PurePosixPath(receipt["path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertEqual(path.parts[0], "reports")
            self.assertGreater(receipt["size_bytes"], 0)
        self.assertEqual(self.record["receipts"]["vendor_apex_check"]["sha256"],
                         "d11f8d0e0f5c8934b47741b1dd48481c5d438c4bee860eaacb64bffd0f4faece")


if __name__ == "__main__":
    unittest.main()
