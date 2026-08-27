"""Offline consistency for the bounded real boot/DLKM build evidence."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class BootDlkmBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/boot-dlkm-build.json").read_text())

    def test_build_is_bound_to_historical_v6_not_the_latest_source(self):
        record = self.record
        progress = json.loads((ROOT / "research/build-progress.json").read_text())
        v6 = next(row for row in progress["installation"]["device_source_updates"] if row["version"] == 6)
        self.assertEqual(record["inputs"]["device_admission_sha256"], v6["admission_sha256"])
        self.assertEqual(record["variant"], "userdebug")
        self.assertEqual(record["profile"], "framework-checks")
        build = record["build"]
        self.assertEqual(build["previous_camera_attempt_sha256"], progress["camera_build"]["attempts"][-1]["sha256"])
        self.assertTrue(build["passed"])
        self.assertEqual(build["exit_code"], 0)
        self.assertFalse(build["timed_out"])
        self.assertFalse(build["sandbox_fallback_observed"])
        self.assertEqual(build["checks_disabled_by_this_probe"], [])
        self.assertEqual(build["ninja_actions_completed"], 2656)
        self.assertTrue(build["incremental_output_preserved"])
        self.assertEqual(build["physical_out_dir"], progress["module_build"]["physical_out_dir"])

    def test_actual_sandbox_observation_keeps_source_read_only(self):
        sandbox = self.record["sandbox"]
        self.assertEqual(sandbox["ninja_parent"], "nsjail")
        self.assertEqual(set(sandbox["namespace_separation"]), {"mnt", "net", "pid", "user"})
        self.assertTrue(all(sandbox["namespace_separation"].values()))
        self.assertTrue(sandbox["source_read_only"])
        self.assertTrue(sandbox["output_read_write"])
        self.assertTrue(sandbox["observation_did_not_enter_namespace"])

    def test_output_set_is_four_images_not_a_complete_rom(self):
        snapshot = self.record["output_snapshot"]
        self.assertTrue(snapshot["host_copies_readback_verified"])
        self.assertEqual({Path(row["path"]).name for row in snapshot["images"]},
                         {"boot.img", "dtbo.img", "vendor_dlkm.img", "system_dlkm.img"})
        sizes = {Path(row["path"]).name: row["size_bytes"] for row in snapshot["images"]}
        self.assertEqual(sizes, {"boot.img": 100663296, "dtbo.img": 23068672,
                                 "vendor_dlkm.img": 54124544, "system_dlkm.img": 8417280})
        self.assertTrue(all(row["identity_stable"] for row in snapshot["images"]))
        self.assertFalse(self.record["inputs"]["factory_images_substituted"])
        self.assertFalse(self.record["inputs"]["origin_verified"])
        self.assertFalse(self.record["inputs"]["source_image_set_avb_passed"])

    def test_kernel_and_overlay_payloads_match_without_claiming_source_compilation(self):
        kernel = self.record["kernel"]
        self.assertTrue(kernel["matches_exact_admitted_prebuilt"])
        self.assertEqual(kernel["size_bytes"], 39963136)
        self.assertEqual(kernel["sha256"], "4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8")
        self.assertEqual(kernel["boot_header_version"], 4)
        self.assertEqual(kernel["ramdisk_size"], 0)
        dtbo = self.record["dtbo"]
        self.assertEqual(dtbo["entry_count"], 1)
        self.assertTrue(dtbo["all_entry_bytes_match_stock"])
        self.assertFalse(dtbo["container_bytes_match_stock"])
        self.assertEqual(dtbo["overlay_sha256"], "4bb4b31bca5de3e354a565304d1ea277ac6d9b70e2760a40147d9f151a691f99")

    def test_boot_signature_is_distinct_from_unsigned_child_descriptors(self):
        proof = self.record["image_inspection"]
        rows = {row["image"]: row for row in proof["avb"]}
        self.assertEqual(set(rows), {"boot", "dtbo", "vendor_dlkm", "system_dlkm"})
        self.assertEqual(rows["boot"]["algorithm"], "SHA256_RSA4096")
        self.assertTrue(rows["boot"]["embedded_signature_present"])
        self.assertTrue(rows["boot"]["embedded_signature_verified"])
        self.assertTrue(rows["boot"]["matches_engineering_test_key"])
        self.assertEqual(rows["boot"]["embedded_key_sha256"], proof["engineering_public_key_sha256"])
        self.assertEqual(rows["boot"]["rollback_index"], 1769904000)
        for name in ("dtbo", "vendor_dlkm", "system_dlkm"):
            self.assertEqual(rows[name]["algorithm"], "NONE")
            self.assertFalse(rows[name]["embedded_signature_present"])
            self.assertFalse(rows[name]["embedded_signature_verified"])
            self.assertIsNone(rows[name]["embedded_key_sha256"])
        for row in rows.values():
            self.assertEqual(row["flags"], 0)
            self.assertEqual(len(row["descriptors"]), 1)
            self.assertTrue(row["descriptors"][0]["bounds_verified"])
        self.assertTrue(proof["all_four_internal_avb_checks_passed"])
        self.assertTrue(proof["both_erofs_data_checks_passed"])
        self.assertTrue(all(row["exit_code"] == 0 for row in proof["commands"]))
        self.assertFalse(proof["complete_new_vbmeta_chain_built"])
        self.assertFalse(proof["signed_by_authenticated_xiaomi_key"])
        self.assertFalse(proof["device_acceptance_verified"])
        self.assertEqual(proof["checks_disabled"], [])

    def test_module_bytes_and_order_survive_both_staging_and_image_creation(self):
        dlkm = self.record["dlkm_contents"]
        self.assertTrue(dlkm["all_484_module_bytes_preserved_inside_images"])
        self.assertEqual(dlkm["source_snapshot_sha256"], self.record["output_snapshot"]["receipt"]["sha256"])
        self.assertEqual(dlkm["kernel_receipt_sha256"], self.record["inputs"]["kernel_receipt_sha256"])
        stages = {row["stage"]: row for row in dlkm["stages"]}
        self.assertEqual({name: row["module_count"] for name, row in stages.items()},
                         {"vendor_dlkm": 381, "system_dlkm": 103})
        self.assertEqual(stages["vendor_dlkm"]["ordered_load_count"], 576)
        self.assertEqual(stages["vendor_dlkm"]["unique_load_count"], 381)
        self.assertEqual(stages["system_dlkm"]["ordered_load_count"], 82)
        self.assertEqual(stages["system_dlkm"]["unique_load_count"], 82)
        for stage in stages.values():
            for key in ("all_captured_files_rehashed", "all_module_and_metadata_bytes_match_staged_output",
                        "module_set_exactly_matches_staged_output", "load_order_preserved", "blocklist_directives_preserved"):
                self.assertTrue(stage[key])
            self.assertEqual(len(stage["metadata_files"]), 5)
        self.assertFalse(dlkm["module_abi_compatibility_verified"])
        self.assertFalse(dlkm["module_loading_tested"])

    def test_vendor_selector_stays_separate_from_vendor_module_blocklist(self):
        dlkm = self.record["dlkm_contents"]
        selector = dlkm["vendor_side_system_selector"]
        self.assertEqual(selector["sha256"], "370cb88e7e8915f34e94bd6b93616f263be8a3523adc15fb554a712dc016a03f")
        self.assertEqual(selector["size_bytes"], 151)
        self.assertTrue(selector["bytes_match"])
        self.assertTrue(selector["path"].endswith("vendor_dlkm/lib/modules/system_dlkm.modules.blocklist"))
        stages = {row["stage"]: row for row in dlkm["stages"]}
        self.assertTrue(stages["vendor_dlkm"]["vendor_side_system_selector_captured"])
        self.assertEqual(stages["vendor_dlkm"]["captured_files"], 387)
        self.assertEqual(stages["system_dlkm"]["captured_files"], 108)
        self.assertNotEqual(stages["vendor_dlkm"]["blocklist"]["sha256"], selector["sha256"])

    def test_source_policy_success_does_not_claim_vendor_compatibility(self):
        policy = self.record["policy_scope"]
        self.assertEqual(policy["framework_input_count"], 7)
        self.assertTrue(policy["platform_neverallow_target_passed"])
        self.assertEqual(policy["source_policy_test_targets_passed"], ["sepolicy_test", "sepolicy_dev_type_test"])
        self.assertFalse(policy["stock_vendor_odm_cil_included_in_these_targets"])
        self.assertFalse(policy["combined_vendor_policy_compatibility_verified"])
        self.assertFalse(policy["permissive_domain_absence_verified"])
        outputs = self.record["output_snapshot"]["framework_policy_outputs"]
        self.assertEqual(len(outputs), 7)
        empty = [row for row in outputs if "/system_ext/" in row["path"] or "/product/etc/" in row["path"]]
        self.assertEqual(len(empty), 4)
        self.assertTrue(all(row["size_bytes"] == 1 for row in empty))

    def test_effective_configuration_keeps_java_and_selinux_checks_enabled(self):
        configs = {Path(row["path"]).name: row["values"] for row in self.record["output_snapshot"]["effective_configurations"]}
        self.assertEqual(configs["dexpreopt-lineage_nezha.config"],
                         {"RelaxUsesLibraryCheck": False, "DisablePreopt": False,
                          "DisablePreoptBootImages": False, "DisablePreoptModules": []})
        soong = configs["soong.lineage_nezha.variables"]
        self.assertTrue(soong["WithDexpreopt"])
        self.assertFalse(soong["SelinuxIgnoreNeverallows"])
        self.assertTrue(soong["DeviceCheckPrebuiltMaxPageSize"])
        self.assertEqual(soong["DeviceMaxPageSizeSupported"], "16384")

    def test_boundaries_keep_phone_and_full_rom_claims_false(self):
        for key, value in self.record["boundaries"].items():
            if key == "checks_disabled":
                self.assertEqual(value, [])
            else:
                self.assertIs(value, False, key)


if __name__ == "__main__":
    unittest.main()
