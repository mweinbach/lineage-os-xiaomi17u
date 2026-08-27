"""Offline consistency checks for the admitted development product."""

import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BuildProgressTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads((ROOT / "research/build-progress.json").read_text())

    def installed_version(self, version):
        return next(row for row in self.record["installation"]["device_source_updates"]
                    if row["version"] == version)

    def test_development_target_is_separate_from_complete_rom_admission(self):
        device = json.loads((ROOT / "config/sources.json").read_text())["device"]
        self.assertFalse(device["build_ready"])
        self.assertIsNone(device["lunch_target"])
        target = device["development_target"]
        self.assertEqual(target["lunch_target"], self.record["lunch_target"])
        self.assertEqual(target["profile"], "framework-checks")
        self.assertTrue(target["configuration_verified"])
        self.assertFalse(self.record["full_rom_verified"])
        self.assertFalse(self.record["device_boot_verified"])
        self.assertFalse(self.record["phone_modifications_performed"])
        products = (ROOT / "device/xiaomi/nezha/AndroidProducts.mk").read_text()
        self.assertIn(target["lunch_target"], products)

    def test_configuration_result_binds_nezha_and_enabled_avb(self):
        result = self.record["product_configuration"]
        self.assertEqual(result["exit_code"], 0)
        expected = {"TARGET_PRODUCT": "lineage_nezha", "TARGET_DEVICE": "nezha",
                    "TARGET_ARCH": "arm64", "TARGET_BOARD_PLATFORM": "canoe",
                    "BOARD_KERNEL_PAGESIZE": "4096", "BOARD_AVB_ENABLE": "true",
                    "PRODUCT_SHIPPING_API_LEVEL": "36", "BOARD_SHIPPING_API_LEVEL": "202504"}
        for key, value in expected.items():
            self.assertEqual(result["values"][key], value)
        self.assertEqual(result["disabled_checks"], [])
        self.assertRegex(result["sha256"], r"^[a-f0-9]{64}$")

    def test_base_snapshot_and_property_adjustment_are_bound(self):
        record = self.record
        snapshot = ROOT / record["base_source_snapshot"]
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(), record["base_source_snapshot_sha256"])
        adjustment = record["source_adjustments"][0]
        self.assertEqual(hashlib.sha256((ROOT / adjustment["patch"]).read_bytes()).hexdigest(), adjustment["patch_sha256"])
        self.assertEqual(adjustment["project"], "vendor/lineage")
        self.assertEqual(record["kernel_bundle"]["module_instances"], 914)
        self.assertGreaterEqual(record["kernel_bundle"]["file_count"], record["kernel_bundle"]["module_instances"])

    def test_current_admission_is_bound_to_installed_source_updates(self):
        record = self.record
        updates = record["installation"]["device_source_updates"]
        versions = [item["version"] for item in updates]
        self.assertEqual(versions, list(range(2, versions[-1] + 1)))
        self.assertEqual(updates[-1]["admission_sha256"], record["device_admission"]["sha256"])
        for update in updates:
            self.assertRegex(update["sha256"], r"^[a-f0-9]{64}$")
            self.assertTrue(update["changes"])
            for change in update["changes"]:
                self.assertTrue(change["path"].startswith("device/xiaomi/nezha/"))
                self.assertNotEqual(change["before_sha256"], change["after_sha256"])

    def test_relative_output_alias_preserves_physical_output_and_checks(self):
        module = self.record["module_build"]
        alias = module["output_alias"]
        self.assertEqual(module["out_dir"], alias["lexical_out_dir"])
        self.assertEqual(module["physical_out_dir"], alias["physical_out_dir"])
        self.assertTrue(module["out_dir"].startswith("out-"))
        self.assertNotIn("/", module["out_dir"])
        self.assertTrue(alias["same_inode"])
        self.assertTrue(alias["output_markers_preserved"])
        self.assertFalse(alias["source_modified"])
        self.assertEqual(alias["disabled_checks"], [])
        docs = (ROOT / "docs/build-progress.md").read_text()
        self.assertIn("OUT_DIR=" + module["out_dir"] + " \\", docs)
        for attempt in module["attempts"]:
            if attempt["result"] == "running":
                continue
            self.assertRegex(attempt["sha256"], r"^[a-f0-9]{64}$")
            self.assertIn("exit_code", attempt)
            self.assertIn("completed_at", attempt)

    def test_android_output_is_distinct_from_host_tool_and_rom(self):
        record = self.record
        self.assertTrue(record["android_modules_verified"])
        self.assertEqual(record["module_build"]["state"], "passed")
        successful = record["module_build"]["attempts"][-1]
        self.assertEqual(successful["exit_code"], 0)
        self.assertTrue(successful["passed"])
        self.assertFalse(successful["sandbox_fallback_observed"])
        proof = record["module_build"]["output_verification"]
        outputs = {row["path"]: row for row in proof["outputs"]}
        self.assertEqual(outputs["target/product/nezha/system/lib64/libbase.so"]["elf_machine"], 183)
        self.assertEqual(outputs["host/linux-x86/bin/checkvintf"]["elf_machine"], 62)
        for output in outputs.values():
            self.assertEqual(output["elf_class"], 64)
            self.assertRegex(output["sha256"], r"^[a-f0-9]{64}$")
        self.assertFalse(proof["android_binary_executed"])
        self.assertFalse(record["full_rom_verified"])
        self.assertFalse(record["device_boot_verified"])

    def test_product_sandbox_observation_is_not_the_standalone_readonly_claim(self):
        sandbox = self.record["module_build"]["sandbox_observation"]
        self.assertTrue(sandbox["ninja_ran_under_nsjail"])
        self.assertTrue(all(sandbox["namespace_separation"].values()))
        self.assertFalse(sandbox["source_read_only"])
        self.assertTrue(sandbox["output_read_write"])
        self.assertEqual(sandbox["checks_disabled_by_this_probe"], [])
        camera = self.record["camera_build"]
        self.assertTrue(camera["ninja_read_only_source_required"])
        self.assertTrue(camera["strict_elf_checks_required"])
        self.assertFalse(camera["camera_function_verified"])
        self.assertEqual(camera["input_admission_sha256"], self.installed_version(5)["admission_sha256"])
        self.assertEqual(len(camera["targets"]), 9)

    def test_camera_source_mount_is_observed_not_just_requested(self):
        sandbox = self.record["camera_build"]["sandbox_observation"]
        self.assertRegex(sandbox["sha256"], r"^[a-f0-9]{64}$")
        self.assertTrue(sandbox["ninja_ran_under_nsjail"])
        self.assertEqual(set(sandbox["namespace_separation"]), {"mnt", "net", "pid", "user"})
        self.assertTrue(all(sandbox["namespace_separation"].values()))
        self.assertTrue(sandbox["source_read_only"])
        self.assertTrue(sandbox["output_read_write"])
        self.assertEqual(sandbox["checks_disabled_by_this_probe"], [])
        self.assertFalse(self.record["camera_build"]["camera_function_verified"])

    def test_camera_timeout_keeps_incremental_outputs_and_attempt_history(self):
        camera = self.record["camera_build"]
        first, second = camera["attempts"][:2]
        self.assertEqual(first["result"], "timed_out")
        self.assertTrue(first["timed_out"])
        self.assertFalse(first["passed"])
        self.assertEqual(first["deadline_seconds"], 3600)
        self.assertEqual(first["checks_disabled_by_this_probe"], [])
        self.assertEqual(second["deadline_seconds"], 7200)
        self.assertTrue(second["incremental_output_preserved"])
        self.assertEqual(second["previous_attempt_sha256"], first["sha256"])
        self.assertNotEqual(first["input_admission_sha256"], second["input_admission_sha256"])
        self.assertEqual(second["input_admission_sha256"], self.installed_version(5)["admission_sha256"])
        self.assertEqual(camera["additional_validation_tool_targets"], ["secilc", "sepolicy-analyze"])

    def test_effective_java_configuration_is_strict_without_disabling_dexpreopt(self):
        proof = self.record["strict_java_configuration"]
        self.assertTrue(proof["strict_uses_library_check_effective"])
        self.assertTrue(proof["dexpreopt_enabled"])
        self.assertFalse(proof["apk_imported_or_validated"])
        self.assertEqual(proof["checks_disabled"], [])
        self.assertEqual(proof["device_admission_sha256"], self.installed_version(5)["admission_sha256"])
        configs = {Path(row["path"]).name: row for row in proof["configurations"]}
        dexpreopt = configs["dexpreopt-lineage_nezha.config"]["values"]
        self.assertFalse(dexpreopt["RelaxUsesLibraryCheck"])
        self.assertFalse(dexpreopt["DisablePreopt"])
        self.assertFalse(dexpreopt["DisablePreoptBootImages"])
        self.assertEqual(dexpreopt["DisablePreoptModules"], [])
        self.assertFalse(dexpreopt["OnlyPreoptArtBootImage"])
        soong = configs["soong.lineage_nezha.variables"]["values"]
        self.assertTrue(soong["WithDexpreopt"])
        self.assertFalse(soong["SelinuxIgnoreNeverallows"])
        update = self.installed_version(5)
        self.assertTrue(update["atomic_directory_exchange"])
        self.assertTrue(update["kernel_vendor_receipts_unchanged"])
        self.assertGreater(configs["dexpreopt-lineage_nezha.config"]["mtime"], update["completed_at"])

    def test_camera_continuation_completed_without_weakening_checks(self):
        camera = self.record["camera_build"]
        attempt = camera["attempts"][-1]
        self.assertEqual(camera["state"], "passed")
        self.assertEqual(attempt["number"], 2)
        self.assertEqual(attempt["result"], "passed")
        self.assertTrue(attempt["passed"])
        self.assertEqual(attempt["exit_code"], 0)
        self.assertFalse(attempt["timed_out"])
        self.assertFalse(attempt["sandbox_fallback_observed"])
        self.assertEqual(attempt["checks_disabled_by_this_probe"], [])
        self.assertEqual(attempt["ninja_actions_completed"], 4206)
        self.assertGreater(attempt["completed_at"], attempt["started_at"])
        self.assertEqual(attempt["sandbox_observation"], camera["sandbox_observation"])
        proof = camera["output_verification"]
        self.assertEqual(proof["build_receipt_sha256"], attempt["sha256"])
        self.assertEqual(proof["device_admission_sha256"], attempt["input_admission_sha256"])
        self.assertEqual(proof["vendor_receipt_sha256"], camera["input_vendor_receipt_sha256"])

    def test_camera_outputs_preserve_inputs_and_include_real_preoptimization(self):
        camera = self.record["camera_build"]
        proof = camera["output_verification"]
        self.assertTrue(proof["all_nine_outputs_verified"])
        self.assertTrue(proof["source_files_unchanged"])
        self.assertEqual({row["module"] for row in proof["outputs"]}, set(camera["targets"]))
        self.assertEqual(len(proof["outputs"]), 9)
        jars = [row for row in proof["outputs"] if row["type"] == "dex_jar"]
        self.assertEqual(len(jars), 4)
        for output in proof["outputs"]:
            self.assertRegex(output["sha256"], r"^[a-f0-9]{64}$")
            self.assertEqual(output["sha256"], output["source_sha256"])
            if output["type"] == "dex_jar":
                self.assertTrue(output["all_zip_member_contents_match"])
                self.assertTrue(output["zip_crc_verified"])
                self.assertTrue(output["container_bytes_match"])
            else:
                self.assertTrue(output["bytes_match"])
        self.assertTrue(proof["all_four_jars_preoptimized"])
        self.assertEqual(len(proof["dexpreopt_outputs"]), 8)
        for jar in jars:
            outputs = [row for row in proof["dexpreopt_outputs"] if row["module"] == jar["module"]]
            self.assertEqual({Path(row["path"]).suffix for row in outputs}, {".odex", ".vdex"})
            for row in outputs:
                self.assertGreater(row["size_bytes"], 0)
                self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")
                if row["path"].endswith(".odex"):
                    self.assertEqual(row["elf_machine"], 183)
        for flag in ("android_binaries_executed", "camera_apk_included", "camera_function_verified",
                     "phone_accessed", "full_rom_verified"):
            self.assertFalse(proof[flag])

    def test_jni_validation_ran_and_host_policy_tools_are_distinct(self):
        proof = self.record["camera_build"]["output_verification"]
        jni = proof["jni_elf_validation"]
        self.assertTrue(jni["ninja_action_recorded"])
        self.assertEqual(jni["rule"], "g.cc.checkElfFile")
        self.assertEqual(jni["max_page_size"], 16384)
        self.assertEqual(jni["shared_library_inputs"], 20)
        self.assertFalse(jni["allow_undefined_symbols"])
        self.assertTrue(jni["stamp"]["path"].endswith(".check_elf_file"))
        self.assertEqual({Path(row["path"]).name for row in proof["host_tools"]},
                         {"secilc", "sepolicy-analyze", "checkvintf"})
        self.assertTrue(all(row["elf_machine"] == 62 for row in proof["host_tools"]))

    def test_v6_selector_install_does_not_relabel_historical_camera_proof(self):
        update = self.installed_version(6)
        previous = self.installed_version(5)
        self.assertEqual(update["previous_admission_sha256"], previous["admission_sha256"])
        self.assertTrue(update["readback_verified"])
        self.assertTrue(update["atomic_directory_exchange"])
        self.assertTrue(update["old_source_directories_preserved"])
        self.assertTrue(update["kernel_vendor_receipts_unchanged"])
        self.assertTrue(update["system_dlkm_vendor_selector_copy_required"])
        self.assertEqual([row["path"] for row in update["changes"]], ["device/xiaomi/nezha/device.mk"])
        self.assertNotEqual(update["admission_sha256"], self.record["camera_build"]["input_admission_sha256"])

    def test_user_variant_has_a_fresh_output_and_its_own_source_admission(self):
        update = self.installed_version(7)
        previous = self.installed_version(6)
        self.assertEqual(update["variant"], "user")
        self.assertEqual(update["previous_variant"], "userdebug")
        self.assertEqual(update["previous_admission_sha256"], previous["admission_sha256"])
        self.assertTrue(update["old_source_directories_preserved"])
        self.assertTrue(update["atomic_directory_exchange"])
        self.assertTrue(update["kernel_vendor_receipts_unchanged"])
        self.assertEqual({row["path"] for row in update["changes"]},
                         {"device/xiaomi/nezha/AndroidProducts.mk", "device/xiaomi/nezha/BoardConfig.mk",
                          "device/xiaomi/nezha/README.md"})
        user = self.record["user_policy_build"]
        self.assertEqual(user["input_admission_sha256"], update["admission_sha256"])
        self.assertEqual(user["target_variant"], "user")
        self.assertTrue(user["fresh_output"])
        self.assertNotEqual(user["physical_out_dir"], user["old_output_directory"])
        self.assertEqual(user["old_output_directory"], self.record["module_build"]["physical_out_dir"])
        self.assertFalse(user["old_output_reset_or_installclean_requested"])
        self.assertEqual(user["old_artifact_hashes_before_verified"], 11)
        self.assertFalse(user["full_rom_verified"])
        self.assertFalse(user["phone_accessed"])

    def test_user_framework_targets_pass_without_relabeling_factory_policy(self):
        user = self.record["user_policy_build"]
        self.assertEqual(user["state"], "passed")
        self.assertTrue(user["passed"])
        self.assertEqual(user["exit_code"], 0)
        self.assertFalse(user["timed_out"])
        self.assertFalse(user["sandbox_fallback_observed"])
        self.assertFalse(user["live_ninja_namespace_snapshot_captured"])
        self.assertEqual(user["checks_disabled_by_this_probe"], [])
        self.assertEqual(user["ninja_actions_completed"], 2788)
        self.assertGreater(user["completed_at"], user["started_at"])
        self.assertEqual(user["sha256"],
                         "5dff46fcbbbe5ffd0d8a8a046ac93c070b61ebf2c63dc70c2ae3dd573df25fc8")
        self.assertFalse(user["source_policy_targets_include_captured_vendor_cil"])
        self.assertFalse(user["combined_factory_vendor_policy_passed"])
        self.assertTrue({"sepolicy_neverallows", "sepolicy_test", "sepolicy_dev_type_test"}
                        <= set(user["targets"]))
        self.assertNotIn("bootimage", user["targets"])
        old = user["old_output_artifacts"]
        self.assertEqual(len(old), 11)
        self.assertEqual(len({row["path"] for row in old}), 11)
        self.assertTrue(user["all_eleven_old_artifacts_unchanged"])
        self.assertTrue(all(row["matches_previous"] for row in old))

    def test_factory_adoption_preserves_prior_inputs_and_does_not_promote_trust(self):
        update = self.installed_version(8)
        self.assertEqual(update["previous_admission_sha256"], self.installed_version(7)["admission_sha256"])
        self.assertTrue(update["atomic_directory_exchange"])
        self.assertTrue(update["old_source_directories_preserved"])
        self.assertTrue(update["kernel_bundle_bytes_unchanged"])
        self.assertTrue(update["camera_extra_bytes_unchanged"])
        self.assertTrue(update["vendor_images_changed_to_factory"])
        self.assertTrue(update["all_eighteen_historical_outputs_unchanged"])
        self.assertFalse(update["output_directories_reset"])
        self.assertFalse(update["effective_configuration_verified"])
        vendor = self.record["vendor_bundle"]
        self.assertEqual(vendor["sha256"], "811f7904adbec2fa99d933179b1247d0c2e30f80a2ba7e0b54c8a2e713917360")
        self.assertEqual(vendor["input_avb_status"], "verified")
        self.assertFalse(vendor["origin_verified"])
        self.assertNotEqual(vendor["sha256"], self.record["camera_build"]["input_vendor_receipt_sha256"])
        prior = self.record["previous_vendor_bundles"][0]
        self.assertEqual(prior["sha256"], self.record["camera_build"]["input_vendor_receipt_sha256"])
        factory = self.record["factory_candidate"]
        self.assertEqual(factory["dtbo_package_extent_bytes"], 33554432)
        self.assertEqual(factory["dtbo_stored_image_bytes"], 23068672)
        self.assertFalse(factory["kernel_provenance_relabelled"])
        self.assertFalse(factory["full_rom_verified"])
        self.assertFalse(factory["treble_labeling_check_passed"])
        self.assertTrue(factory["factory_logical_flags_preserved"])
        self.assertEqual(factory["factory_boot_verification_rows"], 5)

    def test_permissive_su_source_patch_is_not_yet_a_policy_binary_proof(self):
        source = next(row for row in self.record["source_adjustments"] if row["project"] == "system/sepolicy")
        self.assertEqual(hashlib.sha256((ROOT / source["patch"]).read_bytes()).hexdigest(), source["patch_sha256"])
        self.assertEqual(source["removed_policy_statements"], ["permissive su;"])
        applied = source["installation"]
        self.assertEqual(applied["sha256"], "f776922d1e1167fa53998d0bbf8983fea0f11a9a756b160f75b4e4405918542b")
        self.assertTrue(applied["other_policy_statements_unchanged"])
        self.assertTrue(applied["only_expected_worktree_change"])
        self.assertFalse(applied["built_policy_verified"])

    def test_init_hardening_is_bound_without_a_runtime_or_bootloader_claim(self):
        source = next(row for row in self.record["source_adjustments"] if row["project"] == "system/core")
        metadata = json.loads((ROOT / "patches/evolution/init-boot-properties.json").read_text())
        self.assertEqual({key: value for key, value in source.items() if key != "installation"}, metadata)
        self.assertEqual(hashlib.sha256((ROOT / source["patch"]).read_bytes()).hexdigest(), source["patch_sha256"])
        applied = source["installation"]
        self.assertEqual(applied["sha256"], "e8893a3c2e26cd19ba5ad0b6c521d19a214de6f5ae295c3316701dd2736f02c3")
        self.assertTrue(applied["only_expected_worktree_changes"])
        self.assertTrue(applied["all_eighteen_historical_outputs_unchanged"])
        self.assertTrue(applied["known_spoofing_helpers_disabled_by_default"])
        self.assertTrue(applied["existing_ro_boot_properties_write_once"])
        for key in ("libinit_hooks_and_initial_property_sources_verified", "android_compilation_verified",
                    "runtime_property_values_verified", "bootloader_unlock_state_verified", "phone_accessed",
                    "android_output_modified"):
            self.assertFalse(applied[key])

    def test_independent_factory_readback_does_not_relabel_source_checks_as_a_build(self):
        audit = self.record["factory_candidate"]["independent_source_audit"]
        self.assertEqual(audit["sha256"], "a3fab1746edcb26b9ec1e954451d524cfebaf2cc75c20691f700ac9b94d8d676")
        self.assertEqual(audit["device_file_count"], 10)
        self.assertEqual(audit["vendor_file_count"], 17)
        self.assertEqual(audit["source_file_bytes_hashed"], 5727913542)
        self.assertEqual(audit["additional_receipt_bytes_hashed"], 470020)
        self.assertEqual(audit["guest_vendor_images_hashed"], 2)
        for key in ("all_expected_paths_present_no_extra_files", "all_file_identities_unchanged",
                    "all_hashes_and_sizes_match"):
            self.assertTrue(audit[key])
        for key in ("kernel_payload_files_rehashed_by_this_audit", "other_source_projects_audited",
                    "out_accessed", "effective_build_configuration_verified", "source_or_out_written",
                    "factory_origin_verified"):
            self.assertFalse(audit[key])


if __name__ == "__main__":
    unittest.main()
