"""Offline invariants for captured policy inputs and the retained strict failure."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class SelinuxContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/selinux-contract.json").read_text())
        cls.layout = json.loads((ROOT / "research/firmware-layout.json").read_text())
        cls.vintf = json.loads((ROOT / "research/vintf-contract.json").read_text())
        cls.files = {row["runtime_path"]: row for part in cls.record["capture"]["partitions"]
                     for row in part["files"]}

    def test_device_and_modified_package_origin_remain_explicit(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["device"], {"codename": "nezha", "hardware_region": "CN"})
        provenance = self.record["provenance"]
        self.assertEqual(provenance["package_sha256"], self.layout["package"]["sha256"])
        self.assertIn("modified Xiaomi.eu", provenance["source_kind"])
        self.assertEqual(provenance["input_avb_status"], "failed")
        self.assertIsNone(provenance["source_url"])
        for key in ("origin_verified", "oem_signature_authenticated", "raw_policy_or_proprietary_files_committed"):
            self.assertIs(provenance[key], False)

    def test_capture_totals_and_image_hashes_match_the_existing_layout(self):
        capture = self.record["capture"]
        expected_counts = {"vendor": 14, "odm": 11, "system": 13, "system_ext": 11, "product": 11}
        layout = {row["name"]: row for row in self.layout["partitions"]}
        inventories = {p["name"]: p for p in self.vintf["partitions"]}
        self.assertEqual(len(self.files), 60)
        self.assertEqual(capture["total_files"], 60)
        self.assertEqual(capture["total_bytes"], 7721996)
        self.assertEqual(sum(p["capture_bytes"] for p in capture["partitions"]), capture["total_bytes"])
        self.assertEqual({p["partition"]: p["capture_files"] for p in capture["partitions"]}, expected_counts)
        for partition in capture["partitions"]:
            name = partition["partition"] + "_a"
            self.assertEqual(partition["image_sha256"], layout[name]["extraction"]["sha256"])
            self.assertEqual(partition["image_size_bytes"], layout[name]["size_bytes"])
            self.assertEqual(partition["inventory_sha256"], inventories[name]["inventory_sha256"])
            self.assertEqual(partition["capture_files"], len(partition["files"]))
            self.assertEqual(partition["capture_bytes"], sum(r["size_bytes"] for r in partition["files"]))
        self.assertTrue(capture["all_captured_files_rehashed"])
        for key in ("image_mounted", "firmware_executed", "phone_accessed"):
            self.assertIs(capture[key], False)

    def test_image_paths_and_flat_capture_files_are_not_confused(self):
        for partition in self.record["capture"]["partitions"]:
            for row in partition["files"]:
                runtime = row["image_path"] if partition["partition"] == "system" else "/" + partition["partition"] + row["image_path"]
                self.assertEqual(row["runtime_path"], runtime)
                self.assertTrue(row["readback_verified"])
                self.assertRegex(row["captured_file"], r"^files/[0-9]{4}$")
                self.assertGreaterEqual(row["size_bytes"], 0)
                self.assertGreaterEqual(row["nid"], 0)
                self.assertNotIn("..", PurePosixPath(runtime).parts)
        for partition in ["vendor", "odm"]:
            for name in ["file_contexts", "property_contexts", "service_contexts", "hwservice_contexts", "seapp_contexts"]:
                self.assertIn(f"/{partition}/etc/selinux/{partition}_{name}", self.files)

    def test_policy_api_genfs_and_binary_versions_keep_distinct_roles(self):
        versions = self.record["versions"]
        self.assertEqual(versions["vendor_policy_version_text"], "202504\n")
        self.assertEqual(versions["vendor_genfs_version_text"], "202504\n")
        for filename, field in [("plat_sepolicy_vers.txt", "vendor_policy_version_text"),
                                ("genfs_labels_version.txt", "vendor_genfs_version_text")]:
            data = versions[field].encode()
            row = self.files["/vendor/etc/selinux/" + filename]
            self.assertEqual(row["sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual(row["size_bytes"], len(data))
        self.assertEqual(versions["binary_policy_format_version"], 30)
        self.assertEqual(versions["platform_build_policy_version"], 30)
        self.assertEqual(versions["vintf_declared_kernel_policy_version"], "30")
        self.assertTrue(versions["same_version_does_not_prove_policy_or_kernel_compatibility"])

    def test_precompiled_policy_is_only_a_header_and_hash_reference(self):
        binary = self.record["precompiled_reference"]
        source = self.files[binary["runtime_path"]]
        self.assertEqual(binary["sha256"], source["sha256"])
        self.assertEqual(binary["size_bytes"], source["size_bytes"])
        self.assertEqual(binary["size_bytes"], 1735127)
        self.assertEqual(binary["magic_hex"], "0xf97cff8c")
        self.assertEqual(binary["identifier"], "SE Linux")
        self.assertEqual(binary["policy_version"], 30)
        self.assertEqual(binary["config_flags_hex"], "0xc0000001")
        self.assertEqual(binary["unknown_handling_bits"], 0)
        self.assertTrue(binary["mls_flag_set"])
        for key in ("used_as_compiler_input", "installed_or_loaded", "binary_semantics_or_permissive_domains_verified"):
            self.assertIs(binary[key], False)

    def test_stored_hash_agreement_does_not_hide_recomputed_disagreement(self):
        comparison = self.record["precompiled_metadata_comparison"]
        self.assertEqual({r["partition"] for r in comparison["pairs"]}, {"system", "system_ext", "product"})
        self.assertTrue(comparison["all_stored_pairs_equal"])
        self.assertFalse(comparison["all_recomputed_pairs_match"])
        for row in comparison["pairs"]:
            self.assertEqual(row["retained_digest"], row["odm_digest"])
            self.assertNotEqual(row["retained_digest"], row["computed_cil_then_mapping_digest"])
            expected = hashlib.sha256((row["retained_digest"] + "\n").encode()).hexdigest()
            self.assertEqual(self.files[row["framework_metadata_path"]]["sha256"], expected)
            self.assertEqual(self.files[row["odm_metadata_path"]]["sha256"], expected)
            self.assertIn(row["cil_path"], self.files)
            self.assertTrue(row["mapping_path"].endswith("/mapping/202504.cil"))
            self.assertTrue(row["stored_metadata_pair_equal"])
            self.assertFalse(row["recomputed_cil_mapping_matches_metadata"])
        self.assertTrue(comparison["init_compares_stored_metadata_not_actual_cil_bytes"])
        self.assertFalse(comparison["cause_of_discrepancy_verified"])
        self.assertFalse(comparison["policy_bytes_or_metadata_repaired"])
        self.assertFalse(comparison["genfs_cil_included_in_pinned_hash_recipes"])
        self.assertTrue(comparison["recipe_applied_is_pinned_bka_not_authenticated_xiaomi_build"])
        self.assertFalse(comparison["xiaomi_original_hash_recipe_and_input_order_verified"])
        rules = comparison["ordered_genrule_inputs"]
        self.assertEqual(len(rules), 3)
        for rule, pair in zip(rules, comparison["pairs"]):
            self.assertEqual(rule["runtime_input_paths"], [pair["cil_path"], pair["mapping_path"]])
            self.assertEqual(len(rule["input_modules"]), 2)
            self.assertTrue(rule["input_modules"][0].endswith("_sepolicy.cil"))
            self.assertTrue(rule["input_modules"][1].endswith("_mapping_file"))
            self.assertFalse(any("genfs" in path for path in rule["runtime_input_paths"]))

    def test_cil_form_inventory_is_not_a_permissive_analysis_pass(self):
        inventory = self.record["cil_inventory"]
        self.assertEqual(inventory["total_files"], 11)
        self.assertEqual(len(inventory["files"]), inventory["total_files"])
        self.assertEqual(inventory["total_neverallow_forms"], 6081)
        self.assertEqual(inventory["total_neverallow_forms"], sum(r["top_level_form_counts"]["neverallow"] for r in inventory["files"]))
        self.assertEqual(inventory["total_typepermissive_forms"], 0)
        for row in inventory["files"]:
            self.assertEqual(row["sha256"], self.files[row["runtime_path"]]["sha256"])
            self.assertEqual(row["size_bytes"], self.files[row["runtime_path"]]["size_bytes"])
        self.assertIn("not compiler or runtime", inventory["parse_scope"])
        self.assertTrue(inventory["stock_platform_mls"])
        self.assertEqual(inventory["stock_platform_handleunknown"], "deny")

    def test_native_tool_sources_match_pinned_platform_projects(self):
        tools = self.record["native_tools"]
        snapshot = ET.parse(ROOT / tools["source_snapshot"]).getroot()
        projects = {p.get("path"): p.get("revision") for p in snapshot.findall("project")}
        for name, source in tools["public_source_projects"].items():
            self.assertEqual(source["head"], projects[name])
            self.assertTrue(source["clean"])
        self.assertEqual(tools["source_file_count"], 183)
        self.assertEqual(tools["source_bytes"], 2228086)
        self.assertTrue(tools["all_original_and_copied_source_bytes_unchanged"])
        self.assertTrue(tools["source_projects_clean_after"])
        self.assertTrue(tools["different_from_soong_x86_64_host_tools"])
        for name in ["secilc", "sepolicy-analyze"]:
            self.assertEqual(tools["outputs"][name]["elf_machine"], 183)
            self.assertEqual(tools["outputs"][name]["elf_class_bits"], 64)

    def test_failed_tool_attempts_remain_separate_from_policy_failure(self):
        attempts = self.record["native_tools"]["attempts"]
        self.assertEqual([a["attempt"] for a in attempts], [1, 2, 3])
        self.assertEqual([a["strict_compilation_attempted"] for a in attempts], [False, False, True])
        self.assertFalse(any(a["strict_stock_cil_compilation_passed"] for a in attempts))
        first = {s["name"]: s for s in attempts[0]["steps"]}
        second = {s["name"]: s for s in attempts[1]["steps"]}
        final = {s["name"]: s for s in attempts[2]["steps"]}
        self.assertEqual(first["build-libsepol"]["exit_code"], 2)
        self.assertEqual(second["build-libsepol"]["exit_code"], 0)
        self.assertEqual(second["build-secilc"]["exit_code"], 1)
        self.assertEqual(final["compile-stock-strict"]["exit_code"], 255)
        self.assertTrue(all(s["passed"] for name, s in final.items() if name.startswith("build-")))

    def test_compiler_adjustments_do_not_relax_policy_checks(self):
        tools = self.record["native_tools"]
        warning = tools["warning_adjustment"]
        self.assertEqual(warning["flag"], "-Wno-error=unused-function")
        self.assertTrue(warning["all_other_default_makefile_flags_retained"])
        self.assertTrue(warning["warning_remains_visible"])
        self.assertFalse(warning["policy_rules_or_neverallow_checks_changed"])
        self.assertEqual(tools["android_define"]["flag"], "-DANDROID")
        self.assertFalse(tools["android_define"]["source_or_policy_bytes_changed"])
        for command in tools["build_commands"]:
            argv = command["argv"]
            if command["name"] == "build-libsepol":
                flags = next(a.removeprefix("CFLAGS=") for a in argv if a.startswith("CFLAGS=")).split()
                for flag in ["-Werror", "-Wall", "-W", "-Wundef", "-Wshadow", "-Wmissing-format-attribute",
                             "-O2", "-fno-semantic-interposition", "-Wno-error=unused-function", "-DANDROID"]:
                    self.assertIn(flag, flags)
                self.assertIn("-j2", argv)
            else:
                self.assertIn("-DANDROID", argv)
                self.assertIn("-Werror", argv)
        self.assertNotIn("-N", self.record["strict_stock_compile"]["argv"])
        self.assertNotIn("--disable-neverallow", self.record["strict_stock_compile"]["argv"])

    def test_compile_order_keeps_all_mapping_and_vendor_roles(self):
        check = self.record["strict_stock_compile"]
        expected = [
            "/system/etc/selinux/plat_sepolicy.cil", "/system/etc/selinux/mapping/202504.cil",
            "/system_ext/etc/selinux/system_ext_sepolicy.cil", "/system_ext/etc/selinux/mapping/202504.cil",
            "/product/etc/selinux/product_sepolicy.cil", "/product/etc/selinux/mapping/202504.cil",
            "/vendor/etc/selinux/plat_pub_versioned.cil", "/vendor/etc/selinux/vendor_sepolicy.cil",
            "/odm/etc/selinux/odm_sepolicy.cil", "/system/etc/selinux/plat_sepolicy_genfs_202504.cil",
        ]
        self.assertEqual([r["runtime_path"] for r in check["input_order"]], expected)
        self.assertEqual(check["input_files"], 10)
        self.assertEqual(check["input_bytes"], 5403225)
        for row in check["input_order"]:
            self.assertEqual(row["sha256"], self.files[row["runtime_path"]]["sha256"])
            self.assertEqual(row["size_bytes"], self.files[row["runtime_path"]]["size_bytes"])
        self.assertEqual(check["argv"][1:7], ["-m", "-M", "true", "-G", "-c", "30"])
        self.assertEqual(check["argv"][11:], ["/work/validation/nezha-selinux-stock-v3/inputs" + path for path in expected])
        self.assertFalse(any("precompiled_sepolicy" in a for a in check["argv"]))
        self.assertEqual(self.files[expected[-1]]["sha256"], self.files["/system/etc/selinux/plat_sepolicy_genfs_202604.cil"]["sha256"])
        self.assertFalse(any("202604" in a for a in check["argv"]))

    def test_seven_assertions_and_ten_allow_references_preserve_failure(self):
        check = self.record["strict_stock_compile"]
        self.assertEqual(check["exit_code"], 255)
        self.assertFalse(check["passed"])
        self.assertEqual(check["neverallow_assertions_failed"], len(check["diagnostics"]))
        self.assertEqual(check["neverallow_assertions_failed"], 7)
        self.assertEqual(check["conflicting_allow_references"], sum(len(d["conflicting_allow_locations"]) for d in check["diagnostics"]))
        self.assertEqual(check["conflicting_allow_references"], 10)
        for diagnostic in check["diagnostics"]:
            for location in [diagnostic["assertion"], *diagnostic["conflicting_allow_locations"]]:
                self.assertIn(location["runtime_path"], self.files)
                self.assertGreater(location["line"], 0)
        self.assertEqual(check["stderr_sha256"], "078c40850c0cd8f979efd70b0436de0a665c5cbb12b0e062fefe223d513f345a")
        for key in ("neverallow_checks_disabled", "source_or_policy_rules_changed", "policy_binary_created",
                    "file_contexts_output_created", "stock_precompiled_binary_used", "evolution_framework_compatibility_check",
                    "proves_phone_is_permissive", "proves_feature_is_broken"):
            self.assertIs(check[key], False)

    def test_permissive_analysis_cannot_pass_without_a_policy_binary(self):
        analysis = self.record["strict_stock_compile"]["permissive_analysis"]
        self.assertEqual(analysis["status"], "not-run-no-generated-policy")
        self.assertFalse(analysis["passed"])
        self.assertIsNone(analysis["permissive_domain_count"])
        self.assertEqual(analysis["planned_argv"][-1], "permissive")
        self.assertTrue(analysis["nonempty_output_would_not_be_filtered"])

    def test_product_source_targets_do_not_falsely_cover_captured_vendor_policy(self):
        observation = self.record["current_product_observation"]
        values = observation["selected_values"]
        self.assertEqual(values["BoardSepolicyVers"], "202504")
        self.assertEqual(values["PlatformSepolicyVersion"], "202504")
        self.assertEqual(values["VendorVars.ANDROID"]["BOARD_GENFS_LABELS_VERSION"], "202504")
        self.assertFalse(values["SelinuxIgnoreNeverallows"])
        for key in ["BoardVendorSepolicyDirs", "BoardOdmSepolicyDirs", "SystemExtPublicSepolicyDirs", "SystemExtPrivateSepolicyDirs"]:
            self.assertEqual(values[key], [])
        self.assertTrue(observation["normal_source_product_policy_targets_do_not_cover_captured_vendor_odm_cil"])
        next_checks = self.record["next_checks"]
        self.assertEqual(next_checks["soong_x86_64_corroboration"]["status"], "not-run-in-this-record")
        self.assertEqual(next_checks["soong_x86_64_corroboration"]["targets"], ["secilc", "sepolicy-analyze"])
        self.assertEqual(len(next_checks["framework_policy_targets"]), 7)
        self.assertIn("sepolicy_neverallows", next_checks["source_policy_test_targets"])
        self.assertIn("sepolicy_dev_type_test", next_checks["source_policy_test_targets"])
        self.assertTrue(next_checks["permissive_check_required_even_for_userdebug"])

    def test_sandbox_bounds_source_and_inputs_without_hiding_exceptions(self):
        isolation = self.record["isolation"]
        args = self.record["strict_stock_compile"]["sandbox_argv"]
        self.assertTrue(isolation["source_and_android_out_read_only_to_tools"])
        self.assertTrue(isolation["stock_inputs_read_only_bind"])
        self.assertEqual(isolation["read_write_bind_paths"], [isolation["guest_directory"], "/tmp"])
        self.assertEqual([args[i + 1] for i, arg in enumerate(args) if arg == "-B"], isolation["read_write_bind_paths"])
        self.assertEqual([args[i + 1] for i, arg in enumerate(args) if arg == "-R"], ["/", isolation["guest_directory"] + "/inputs"])
        self.assertEqual(isolation["native_make_jobs"], 2)
        self.assertEqual(self.record["strict_stock_compile"]["timeout_seconds"], 90)
        self.assertTrue(isolation["proc_read_write"])
        self.assertFalse(isolation["cgroup_namespace_enabled"])
        self.assertTrue(isolation["outer_uid_gid_zero_warning_retained"])
        for key in ["no_soong_or_ninja_run", "no_network_or_package_install", "no_phone_access"]:
            self.assertIs(isolation[key], True)

    def test_public_record_contains_hashes_and_observations_not_private_content(self):
        def check(value):
            if isinstance(value, dict):
                forbidden = {"serial", "serialno", "imei", "imsi", "meid", "account", "email", "phone_number",
                             "stdout", "stderr", "base64", "raw_cil", "content"}
                self.assertFalse(forbidden.intersection(value))
                for key, child in value.items():
                    if key.endswith("sha256"):
                        self.assertRegex(child, r"^[a-f0-9]{64}$")
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
            elif isinstance(value, str):
                self.assertNotIn("/Users/", value)
                self.assertNotIn("/home/", value)
                self.assertNotIn("-----BEGIN", value)
        check(self.record)
        verified = {"capture_integrity_verified", "source_pins_and_native_tool_build_verified",
                    "strict_stock_compile_executed_with_neverallows"}
        for key, value in self.record["verification_boundaries"].items():
            self.assertIs(value, key in verified, key)


if __name__ == "__main__":
    unittest.main()
