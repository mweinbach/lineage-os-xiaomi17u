"""Offline checks for a recovery plan, not evidence that recovery works."""

import hashlib
import json
from pathlib import Path
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
FACTORY = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
PINS = {
    "missmytime": "17525a886e43c26c350fb3db9b260c55e4360dc8",
    "antocorvo": "4a35185d43782b4dd460a7f456d674c0976c0859",
    "teamwin": "5c3d206a5eeb3d446bcda8248a405a4b278bab5c",
    "twrp_test_manifest": "d2188a9345857fb078c391e8cb3e259a21e941e5",
    "official_manifest": "6dc117d9cbd08430daa16db2013560e1c4017fa8",
}


class RecoveryPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/recovery-plan.json").read_text())
        cls.doc = (ROOT / "docs/recovery-plan.md").read_text()

    def test_recovery_is_not_bootloader_protection(self):
        scope = self.record["scope"]
        self.assertFalse(scope["recovery_is_bootloader_corruption_protection"])
        self.assertTrue(scope["working_boot_chain_required"])
        self.assertIn("cannot prevent bootloader corruption", self.doc)

    def test_review_authorizes_no_phone_or_guest_change(self):
        scope = self.record["scope"]
        for key in ["new_recovery_target_registered", "recovery_source_synced",
                    "recovery_image_built", "device_changes_authorized", "phone_accessed",
                    "guest_accessed", "downloaded_code_executed", "other_device_settings_adopted",
                    "review_is_comprehensive_security_audit"]:
            self.assertFalse(scope[key], key)

    def test_factory_provenance_is_not_upgraded_to_oem_authentication(self):
        stock = self.record["stock"]
        self.assertEqual(stock["package_sha256"], FACTORY)
        self.assertIsNone(stock["origin_url"])
        self.assertFalse(stock["origin_verified"])
        self.assertFalse(stock["trusted_oem_key_supplied"])
        self.assertTrue(stock["selected_root_chain_and_qtvm_checks_passed"])
        self.assertFalse(stock["verification_bypass_flags_used"])
        self.assertFalse(stock["device_rollback_counters_checked"])

    def test_stock_receipts_are_explicit_and_distinct(self):
        stock = self.record["stock"]
        self.assertEqual(stock["archive_receipt_sha256"], "c0686eab1092809faad2c865662a8616e9eea5492c7afd0e7bfcae8447a74567")
        self.assertEqual(stock["boot_receipt_sha256"], "19a0cf859e91b283684c03ab1691f8469e3c87c5a01b8fc6a1eae1d5e65b1f37")
        self.assertEqual(stock["avb_receipt_sha256"], "5f22d51a23ba989f71bf6a37844bbade71b5c02b17e36c3ca77290ab9a795c58")
        self.assertEqual(len({stock[k] for k in ["archive_receipt_sha256", "boot_receipt_sha256", "avb_receipt_sha256"]}), 3)

    def test_recovery_header_and_payload_are_bound(self):
        recovery = self.record["stock"]["headers"]["recovery"]
        self.assertEqual(recovery["image_sha256"], "a6f2c77608026fcfe6221e5191c501b0ac880658f76c55231879ed198ce8a0f9")
        self.assertEqual(recovery["header_version"], 4)
        self.assertEqual(recovery["kernel_size_bytes"], 0)
        self.assertEqual(recovery["ramdisk_size_bytes"], 30407261)
        self.assertEqual(recovery["image_size_bytes"], 100 * 1024 * 1024)
        self.assertIn(recovery["image_sha256"], self.doc)

    def test_boot_kernel_and_ramdisks_stay_separate(self):
        stock = self.record["stock"]
        headers = stock["headers"]
        self.assertEqual(stock["recovery_kernel_source_partition"], "boot")
        self.assertEqual(stock["generic_ramdisk_source_partition"], "init_boot")
        self.assertEqual(headers["boot"]["kernel_size_bytes"], 39963136)
        self.assertEqual(headers["boot"]["ramdisk_size_bytes"], 0)
        self.assertEqual(headers["init_boot"]["kernel_size_bytes"], 0)
        self.assertEqual(headers["init_boot"]["ramdisk_size_bytes"], 2916992)
        self.assertEqual(headers["vendor_boot"]["page_size_bytes"], 4096)
        self.assertEqual(headers["vendor_boot"]["dtb_size_bytes"], 4496880)
        self.assertTrue(stock["dedicated_ab_recovery_names_observed"])
        for item in headers.values():
            self.assertEqual(item["header_version"], 4)
            self.assertRegex(item["unpack_log_sha256"], r"^[0-9a-f]{64}$")

    def test_image_lengths_do_not_become_live_capacity_proof(self):
        stock = self.record["stock"]
        self.assertTrue(stock["recovery_image_size_is_not_live_partition_measurement"])
        self.assertFalse(stock["live_physical_partition_sizes_verified"])
        self.assertIn("not a live partition measurement", self.doc)

    def test_recovery_and_system_rollback_locations_are_distinct(self):
        stock = self.record["stock"]
        recovery = stock["recovery_chain"]
        self.assertEqual(recovery["rollback_index"], 1)
        self.assertEqual(recovery["rollback_index_location"], 1)
        self.assertEqual(recovery["flags"], 0)
        self.assertTrue(recovery["embedded_signature_valid"])
        self.assertEqual(stock["vbmeta_system_chain"]["rollback_index_location"], 2)
        self.assertEqual(stock["vbmeta_system_chain"]["rollback_index"], 1769904000)

    def test_recovery_module_followup_matches_the_independent_stage_record(self):
        proof = self.record["followup_module_stage_audit"]
        raw = (ROOT / proof["record"]).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), proof["sha256"])
        audit = json.loads(raw)
        self.assertEqual(proof["stage"], "recovery_first_stage")
        stage = audit["stages"][proof["stage"]]
        mapping = {
            "request_rows": "requests", "unique_requested_modules": "unique_requests",
            "hard_dependency_closure_modules": "hard_closure_modules",
            "crc_expectations": "expectations", "kernel_crc_matches": "kernel_crc_matches",
            "local_predecessor_crc_matches": "local_hard_predecessor_crc_matches",
            "missing_hard_paths": "missing_hard_paths", "hard_or_pre_cycles": "hard_or_pre_cycles",
            "local_matching_provider_ambiguities": "local_crc_matching_provider_ambiguities",
        }
        for target, source in mapping.items():
            self.assertEqual(proof[target], stage[source], target)
        self.assertEqual(proof["hard_added_names"], audit["selection"][proof["stage"]]["hard_added_names"])
        self.assertEqual(proof["hard_dependency_closure_modules"],
                         proof["unique_requested_modules"] + len(proof["hard_added_names"]))
        self.assertEqual(proof["crc_expectations"],
                         proof["kernel_crc_matches"] + proof["local_predecessor_crc_matches"])
        self.assertEqual((proof["request_rows"], proof["unique_requested_modules"],
                          proof["hard_dependency_closure_modules"]), (435, 424, 426))
        self.assertIn("module-stage-closure.md", self.doc)

    def test_static_recovery_closure_keeps_soft_dependency_and_runtime_limits(self):
        proof = self.record["followup_module_stage_audit"]
        audit = json.loads((ROOT / proof["record"]).read_text())
        soft = audit["missing_soft_dependencies"]
        self.assertEqual(proof["missing_soft_edges"], soft["recovery_first_stage_edges"])
        self.assertEqual(proof["missing_soft_target"], soft["recovery_target"])
        self.assertEqual((proof["missing_soft_edges"], proof["missing_soft_target"]), (1, "phy-msm-snps-hs"))
        for key in ("missing_soft_target_proves_required_import_failure", "substitute_modules_added",
                    "stock_loader_source_identity_verified", "actual_module_loading_verified",
                    "signature_trust_verified", "recovery_image_built_or_booted"):
            self.assertIs(proof[key], False, key)
        self.assertFalse(audit["limits"]["actual_module_load_verified"])
        self.assertFalse(audit["limits"]["recovery_or_twrp_verified"])

    def test_package_gpt_bounds_are_not_live_geometry_or_flash_admission(self):
        gpt = self.record["stock"]["package_gpt_contract"]
        self.assertEqual(gpt["analysis_receipt_sha256"], "18c98f119761417a0ff11a7a107a713fce6fd7a99b9bb1288b300387fa7fcf3d")
        self.assertEqual(gpt["independent_receipt_sha256"], "94b3525a182a1576e0ec0d8910318f37a80693714c9bcf2beac41bff0d100cd1")
        self.assertEqual(gpt["sector_size_bytes"], 4096)
        self.assertEqual(gpt["package_lun"], 4)
        self.assertTrue(gpt["slot_sizes_equal"])
        self.assertTrue(gpt["package_partition_extents_verified"])
        self.assertEqual(gpt["partition_size_bytes_per_slot"], {
            "boot": 100663296, "init_boot": 8388608, "vendor_boot": 100663296,
            "recovery": 104857600, "dtbo": 33554432})
        for first, last in gpt["recovery_lba_extents"].values():
            self.assertEqual((last - first + 1) * gpt["sector_size_bytes"], 104857600)
        for key in ["physical_phone_capacity_verified", "flashable_gpt_admitted",
                    "growth_placeholders_resolved"]:
            self.assertFalse(gpt[key], key)

    def test_all_reviewed_repository_refs_are_pinned_but_unadopted(self):
        refs = self.record["source_references"]
        self.assertEqual({x["id"]: x["commit"] for x in refs}, PINS)
        self.assertEqual(len(refs), len(PINS))
        for item in refs:
            self.assertTrue(item["branch"])
            self.assertFalse(item["adopted"])
            self.assertRegex(item["tree_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(urlparse(item["repository"]).hostname, "github.com")
            self.assertIn(item["commit"], self.doc)

    def test_selected_file_evidence_has_hashes_and_source_identity(self):
        files = self.record["reviewed_config_files"]
        self.assertEqual(len(files), 13)
        self.assertEqual(len({(x["source"], x["path"]) for x in files}), len(files))
        for item in files:
            self.assertIn(item["source"], PINS)
            self.assertNotIn("..", Path(item["path"]).parts)
            self.assertFalse(Path(item["path"]).is_absolute())
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(item["git_blob_sha1"], r"^[0-9a-f]{40}$")
            self.assertGreater(item["size_bytes"], 0)

    def test_primary_references_are_teamwin_or_aosp(self):
        refs = self.record["primary_references"]
        self.assertEqual(len(refs), 10)
        for item in refs:
            url = urlparse(item["url"])
            self.assertEqual(url.scheme, "https")
            self.assertIn(url.hostname, {"twrp.me", "source.android.com"})
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
            self.assertTrue(item["observed_at"].startswith("2026-08-27T"))

    def test_missmytime_layout_is_not_whole_tree_approval(self):
        ref = self.record["community_findings"]["missmytime"]
        self.assertEqual(ref["header_version"], 4)
        self.assertTrue(ref["excludes_kernel_from_recovery"])
        self.assertTrue(ref["manual_decryption"])
        self.assertFalse(ref["full_tree_admitted"])
        self.assertFalse(ref["device_decryption_verified_here"])
        flags = ref["security_settings_not_adopted"]
        for key in ["ALLOW_MISSING_DEPENDENCIES", "BUILD_BROKEN_DUP_RULES",
                    "BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES"]:
            self.assertTrue(flags[key], key)
        self.assertEqual(flags["permissive_domains"], ["recovery", "hal_vibrator_default"])
        self.assertEqual(flags["PLATFORM_VERSION"], "99.87.36")
        for key in ["PLATFORM_SECURITY_PATCH", "VENDOR_SECURITY_PATCH", "BOOT_SECURITY_PATCH"]:
            self.assertEqual(flags[key], "2099-12-31")

    def test_older_tree_does_not_define_our_recovery_layout_or_security_route(self):
        ref = self.record["community_findings"]["antocorvo"]
        flags = ref["incompatible_active_settings"]
        self.assertEqual(flags["TARGET_BOARD_PLATFORM"], "xiaomi_sm8750")
        for key in ["TARGET_NO_RECOVERY", "BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT",
                    "BOARD_INCLUDE_RECOVERY_RAMDISK_IN_VENDOR_BOOT"]:
            self.assertTrue(flags[key], key)
        self.assertEqual(flags["BOARD_AVB_VBMETA_SYSTEM_ROLLBACK_INDEX_LOCATION"], 1)
        self.assertTrue(ref["strongbox_removed_by_reference"])
        self.assertFalse(ref["full_tree_admitted"])
        self.assertFalse(ref["device_decryption_verified_here"])
        self.assertIn("not confirmed", ref["decryption_status_reported"])

    def test_source_and_volume_separation_are_required(self):
        source = self.record["source_selection"]
        for key in ["preferred_reference_is_not_approved_full_tree",
                    "base_rom_checkout_must_not_be_repurposed", "separate_source_and_output_required",
                    "same_ext4_volume_concurrent_writer_forbidden"]:
            self.assertTrue(source[key], key)
        for key in ["full_transitive_manifest_resolved", "source_or_patch_scripts_executed",
                    "official_teamwin_xiaomi_index_contains_nezha"]:
            self.assertFalse(source[key], key)

    def test_phases_require_new_authorization_before_device_changes(self):
        phases = self.record["phases"]
        self.assertEqual([x["id"] for x in phases], ["research", "local_recovery",
                         "authorized_boot_smoke", "authorized_fbe_validation", "authorized_restore_validation"])
        for phase in phases[:2]:
            self.assertFalse(phase["phone_changes"])
        self.assertEqual(phases[1]["status"], "pending_after_core_rom_bringup")
        for phase in phases[2:]:
            self.assertTrue(phase["phone_changes"])
            self.assertEqual(phase["status"], "requires_specific_user_authorization")

    def test_backup_and_crypto_gates_do_not_claim_restorability(self):
        requirements = self.record["requirements"]
        self.assertTrue(self.record["stock"]["factory_fstab_reconciliation_required"])
        self.assertIn("/data/media", " ".join(requirements["backups"]))
        self.assertIn("off-device", " ".join(requirements["backups"]))
        self.assertIn("wrong credentials fail", " ".join(requirements["storage_and_encryption"]))
        self.assertIn("key-blob write-back", " ".join(requirements["storage_and_encryption"]))
        self.assertIn("not present Virtual A/B as two independent", " ".join(requirements["virtual_ab"]))
        self.assertIn("SELinux enforcing", " ".join(requirements["safety_controls"]))

    def test_bounded_receipt_does_not_claim_recovery_validation(self):
        evidence = self.record["evidence"]
        self.assertEqual(evidence["private_receipt"]["sha256"], "f07607300c58473b9cb698e26c40859e23a785623f1f5ebdeb89a397defa33d9")
        self.assertEqual(evidence["private_receipt"]["artifact_count"], 65)
        self.assertEqual(evidence["source_files"], 45)
        self.assertEqual(evidence["source_bytes"], 757838)
        self.assertEqual(evidence["primary_web_pages"], 10)
        self.assertIn(evidence["private_receipt"]["sha256"], self.doc)
        for key, value in self.record["validation"].items():
            self.assertFalse(value, key)
        serialized = json.dumps(self.record)
        self.assertNotIn("/Users/", serialized)
        self.assertNotIn("PRIVATE KEY-----", serialized)


if __name__ == "__main__":
    unittest.main()
