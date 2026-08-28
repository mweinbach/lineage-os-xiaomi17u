"""Check public TWRP source/stock records without a phone, network or blobs."""

import json
from pathlib import Path
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


class TwrpRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.upstream = json.loads((ROOT / "research/twrp-upstream.json").read_text())
        cls.stock = json.loads((ROOT / "research/twrp-stock-contract.json").read_text())
        cls.previous = json.loads((ROOT / "research/recovery-plan.json").read_text())

    def test_minimal_manifest_selection_and_counts(self):
        manifest = self.upstream["manifest"]
        self.assertEqual(manifest["branch"], "twrp-16.0")
        self.assertEqual(manifest["commit"], "d2188a9345857fb078c391e8cb3e259a21e941e5")
        self.assertEqual(manifest["default_revision"], "refs/tags/android-16.0.0_r1")
        counts = manifest["project_counts"]
        self.assertEqual(counts["baseline"] - counts["baseline_replaced"]
                         + counts["overlay_added"] - counts["minimal_removals"], counts["final"])
        self.assertEqual(counts["aosp"] + counts["github"], counts["final"])
        self.assertEqual(counts["final"], 392)
        followup = manifest["linux_selection_followup"]
        self.assertEqual(counts["selected_linux"], 391)
        self.assertEqual(followup["selected_linux_count"], counts["final"] - 1)
        self.assertEqual(followup["excluded_project"]["path"], "prebuilts/bazel/darwin-x86_64")
        self.assertTrue(followup["all_other_expanded_project_paths_present"])
        self.assertFalse(followup["count_difference_is_incomplete_download"])

    def test_moving_project_references_are_explicit_full_pins(self):
        projects = self.upstream["pinned_projects"]
        self.assertEqual(len(projects), 36)
        self.assertEqual(len({row["path"] for row in projects}), len(projects))
        for row in projects:
            with self.subTest(project=row["path"]):
                self.assertRegex(row["commit"], r"^[0-9a-f]{40}$")
                self.assertTrue(row["branch"])
                self.assertEqual(urlparse(row["repository"]).hostname, "github.com")
                self.assertFalse(Path(row["path"]).is_absolute())
                self.assertNotIn("..", Path(row["path"]).parts)

    def test_patch_bases_match_the_reviewed_source_projects(self):
        pins = {row["path"]: row["commit"] for row in self.upstream["pinned_projects"]}
        for row in self.upstream["aosp_project_pins"]:
            pins[row["path"]] = row["commit"]
        series = json.loads((ROOT / "patches/twrp/series.json").read_text())
        self.assertEqual(series["manifest"]["commit"], self.upstream["manifest"]["commit"])
        for patch in series["patches"]:
            self.assertEqual(patch["base_commit"], pins[patch["project"]])

    def test_source_review_does_not_claim_device_or_build_success(self):
        self.assertTrue(all(value is False for value in self.upstream["scope"].values()))
        self.assertFalse(self.upstream["encryption_constraints"]["runtime_decryption_verified"])
        self.assertFalse(self.upstream["first_stage_module_contract"]["actual_module_loading_verified"])
        self.assertFalse(self.upstream["validation"]["android_build_or_device_test_claimed"])

    def test_recovery_header_matches_prior_independent_factory_evidence(self):
        layout = self.stock["layout"]
        fresh = layout["fresh_header"]
        previous = self.previous["stock"]["headers"]["recovery"]
        for key in ("header_version", "kernel_size_bytes", "ramdisk_size_bytes"):
            self.assertEqual(fresh[key], previous[key])
        self.assertEqual((fresh["header_version"], fresh["header_size_bytes"],
                          fresh["page_size_bytes"], fresh["kernel_size_bytes"]), (4, 1584, 4096, 0))
        self.assertEqual(fresh["cmdline"], "")
        self.assertEqual(layout["stock_image"]["sha256"], previous["image_sha256"])
        self.assertEqual(layout["stock_image"]["size_bytes"], 104857600)
        self.assertFalse(layout["physical_phone_capacity_verified"])
        self.assertFalse(layout["kernel_embedded"])

    def test_stock_and_compile_only_contract_do_not_replace_vendor_boot(self):
        contract = self.stock["initial_target_contract"]
        self.assertEqual(contract["kernel_source_partition"], "boot")
        self.assertEqual(contract["dtb_bootconfig_modules_source_partition"], "vendor_boot")
        self.assertEqual(contract["max_package_image_bytes"], 104857600)
        for key in ("replace_vendor_boot", "copy_stock_init_adbd_recovery_or_monolithic_policy",
                    "duplicate_vendor_ramdisk_module_payloads",
                    "automatically_decrypt_mount_format_or_upgrade_userdata_keys"):
            self.assertFalse(contract[key])
        self.assertTrue(contract["authenticated_adb"])
        self.assertTrue(contract["enforcing_selinux"])

    def test_module_stage_and_touch_are_separate_runtime_dependencies(self):
        loading = self.stock["module_loading"]
        self.assertEqual(loading["recovery_ramdisk_module_count"], 0)
        self.assertEqual(loading["vendor_ramdisk_module_count"], 430)
        self.assertTrue(loading["do_not_reload_entire_vendor_ramdisk_list_from_recovery_rc"])
        self.assertFalse(loading["hard_closure_and_crc_matches_prove_runtime_admission"])
        touch = self.stock["display_and_input"]["touch"]
        self.assertTrue(touch["both_drivers_absent_from_vendor_boot"])
        self.assertEqual({row["filename"] for row in touch["driver_modules"]},
                         {"synaptics_tcm2.ko", "xiaomi_touch.ko"})
        self.assertEqual({row["source"] for row in touch["driver_modules"]}, {"vendor_dlkm"})
        for row in touch["crc_provider_coverage"].values():
            self.assertEqual(row["versioned_import_count"],
                             row["kernel_crc_match"] + row["module_crc_match_unique_payload"])
            self.assertEqual(row["unmatched_versioned_imports"], 0)
            self.assertFalse(row["module_loaded"])

    def test_display_requires_drm_and_has_no_runtime_proof(self):
        display = self.stock["display_and_input"]
        facts = display["kernel_config"]["facts"]
        self.assertEqual(facts["CONFIG_DRM"], "y")
        self.assertEqual(facts["CONFIG_DRM_KMS_HELPER"], "y")
        self.assertEqual(facts["CONFIG_FB"], "n")
        self.assertEqual(facts["CONFIG_DRM_FBDEV_EMULATION"], "n")
        self.assertTrue(all(value is False for value in display["runtime_claims"].values()))

    def test_crypto_policy_and_signing_checks_are_not_waived(self):
        self.assertFalse(self.stock["fstab"]["decryption_test_passed"])
        self.assertIn("wrappedkey_v0", self.stock["fstab"]["normal_fileencryption"])
        self.assertTrue(self.stock["policy_and_services"]["target_neverallow_checks_must_remain_enabled"])
        self.assertTrue(self.stock["policy_and_services"]["target_requires_enforcing_without_permissive_domains"])
        for key in ("oem_signing_keys_available", "custom_image_is_stock_signed",
                    "verification_disable_flags_allowed", "phone_stored_rollback_counters_verified"):
            self.assertFalse(self.stock["avb"][key])

    def test_public_records_contain_no_personal_identifiers_or_private_payloads(self):
        forbidden = {"serial", "serialno", "imei", "imsi", "meid", "email", "phone_number"}

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
            elif isinstance(value, str):
                self.assertNotIn("/Users/", value)
                self.assertNotRegex(value, r"-----BEGIN .*PRIVATE KEY-----")
        check(self.upstream)
        check(self.stock)


if __name__ == "__main__":
    unittest.main()
