"""Keep the pinned MiCode research separate from a verified Nezha build."""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class MiCodePopsicleReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/micode-popsicle-review.json").read_text())
        cls.boot = json.loads((ROOT / "research/boot-contract.json").read_text())
        cls.document = (ROOT / "docs/micode-popsicle-review.md").read_text()

    def test_sources_have_exact_verified_pins_and_bounded_search_scope(self):
        self.assertEqual(self.record["schema_version"], 1)
        for source in self.record["sources"].values():
            self.assertEqual(source["branch"], "popsicle-w-oss")
            self.assertRegex(source["commit"], r"^[a-f0-9]{40}$")
            self.assertRegex(source["tree_sha1"], r"^[a-f0-9]{40}$")
            self.assertIn(source["commit"], source["commit_url"])
            self.assertIn(source["commit"], self.document)
            self.assertTrue(source["remote_head_verified"])
            self.assertTrue(source["origin_verified"])
            self.assertTrue(source["worktree_clean"])
            self.assertTrue(source["all_reachable_objects_present"])
            self.assertEqual(source["git_fsck_exit_code"], 0)
            self.assertGreater(source["tracked_file_count"], 0)
            self.assertEqual(source["case_insensitive_nezha_path_matches"], [])
            self.assertEqual(source["case_insensitive_nezha_text_matches"], [])
            self.assertEqual(source["text_search_exit_code"], 1)
            self.assertTrue(source["text_search_skips_binary_files"])

    def test_ack_family_agrees_without_claiming_exact_source_equivalence(self):
        ack = self.record["ack_reference"]
        baseline = self.record["captured_baseline"]
        self.assertTrue(ack["tag_peels_to_declared_commit"])
        self.assertRegex(ack["commit"], r"^[a-f0-9]{40}$")
        self.assertRegex(ack["tag_object_sha1"], r"^[a-f0-9]{40}$")
        self.assertEqual(ack["kernel_version"], [6, 12, 23])
        self.assertEqual(ack["kmi_generation"], 5)
        self.assertEqual(ack["clang_version"], baseline["clang_family"])
        self.assertEqual(baseline["kmi_family_from_release"], "6.12-android16-5")
        self.assertFalse(ack["exact_supplied_kernel_source_verified"])
        self.assertFalse(ack["live_suffix_lookup"]["absence_from_all_public_sources_established"])

    def test_external_gki_and_debug_settings_are_not_promoted(self):
        build = self.record["build_composition"]
        self.assertEqual(build["kernel_directory"], "common")
        self.assertEqual(build["soc_directory"], "soc-repo")
        self.assertEqual(build["default_perf_base_kernel_label"], "//common:kernel_aarch64")
        self.assertEqual(build["dt_makefile_label"], "//common:Makefile")
        self.assertFalse(build["local_makefile_version_is_effective_gki_version"])
        self.assertFalse(build["image_packing_page_size_proves_kernel_page_size"])
        self.assertFalse(build["addresses_approved_for_nezha"])
        self.assertFalse(build["nezha_config_target_present"])
        self.assertFalse(build["complete_external_dependency_manifest_verified"])
        self.assertFalse(build["consolidate_settings"]["adopted_by_workspace"])
        self.assertFalse(build["kernel_abi_target_executed"])
        self.assertIn("Module.symvers", build["absent_local_inputs"])

    def test_generic_dt_matches_do_not_replace_xiaomi_board_identity(self):
        comparison = self.record["dt_comparison"]
        self.assertEqual(comparison["supplied_nezha_xiaomi_miboard_id_u32"], [5, 0])
        self.assertEqual(comparison["supplied_nezha_qcom_board_id_u32"], [8, 0])
        expected = {"popsicle": [1, 0], "pudding": [2, 0], "pandora": [3, 0]}
        self.assertEqual(len(comparison["public_overlays"]), len(expected))
        for overlay in comparison["public_overlays"]:
            self.assertEqual(overlay["xiaomi_miboard_id_u32"], expected[overlay["target"]])
            self.assertEqual(overlay["qcom_board_id_u32"], comparison["supplied_nezha_qcom_board_id_u32"])
            self.assertTrue(overlay["compatible_matches_supplied_nezha"])
            self.assertTrue(overlay["qcom_msm_id_pairs_match_supplied_nezha_set"])
            self.assertFalse(overlay["variant_match_verified"])
        self.assertFalse(comparison["shared_qualcomm_ids_prove_exact_variant"])
        self.assertFalse(comparison["live_overlay_selection_verified"])
        stock = next(tree for tree in self.boot["device_trees"]["trees"] if tree["source"] == "dtbo")
        self.assertEqual(comparison["supplied_nezha_dtbo_sha256"], stock["sha256"])
        self.assertEqual(comparison["supplied_nezha_compatible"], stock["compatible"])

    def test_module_evidence_keeps_crc_signature_and_loading_gaps(self):
        baseline = self.record["captured_baseline"]
        self.assertEqual(baseline["kernel_release"], self.boot["kernel"]["release"])
        self.assertEqual(baseline["kernel_sha256"], self.boot["kernel"]["sha256"])
        self.assertEqual(baseline["ikconfig_sha256"], self.boot["kernel"]["ikconfig_sha256"])
        self.assertEqual(baseline["module_instances"], sum(baseline["module_sets"].values()))
        self.assertEqual(baseline["module_instances"], self.boot["dlkm_followup"]["total_module_instances"])
        self.assertLess(baseline["distinct_module_payloads"], baseline["module_instances"])
        self.assertNotEqual(*baseline["zs_malloc_expected_crcs"].values())
        self.assertEqual(baseline["supplied_system_blocklist"], ["zram", "zsmalloc"])
        self.assertTrue(baseline["public_sibling_system_blocklists_empty"])
        for key in ("kernel_export_crcs_verified", "module_provider_export_crcs_verified",
                    "module_signatures_verified", "module_loading_tested",
                    "vendor_zram_zsmalloc_binary_equivalence_verified"):
            self.assertFalse(baseline[key])

    def test_source_file_receipts_are_bound_to_their_repository_pin(self):
        seen = set()
        for item in self.record["selected_source_files"]:
            identity = (item["repository"], item["path"])
            self.assertNotIn(identity, seen)
            seen.add(identity)
            source = self.record["sources"][item["repository"]]
            self.assertEqual(item["url"], source["url"].removesuffix(".git") +
                             "/blob/" + source["commit"] + "/" + item["path"])
            self.assertRegex(item["sha256"], r"^[a-f0-9]{64}$")
            self.assertRegex(item["git_blob_sha1"], r"^[a-f0-9]{40}$")
            self.assertGreaterEqual(item["size_bytes"], 0)
            self.assertGreaterEqual(item["line_count"], 0)
        self.assertIn(("kernel", "android/ACK_SHA"), seen)
        self.assertIn(("devicetree", "qcom/popsicle-sm8850-overlay.dtso"), seen)
        self.assertIn(self.record["evidence"]["receipt_sha256"], self.document)

    def test_community_link_and_licenses_do_not_imply_build_or_redistribution_proof(self):
        citation = self.record["community_citation"]
        self.assertFalse(citation["public_reproducible_rom_sources_supplied_by_link"])
        self.assertFalse(citation["author_claims_are_workspace_device_tests"])
        self.assertTrue((ROOT / citation["source_record"]).is_file())
        licenses = self.record["licenses"]
        self.assertTrue(licenses["preserve_source_notices"])
        self.assertTrue(licenses["corresponding_source_review_required_before_binary_distribution"])
        self.assertFalse(licenses["proprietary_userspace_redistribution_rights_established"])
        self.assertFalse(licenses["third_party_license_compliance_determined"])

    def test_research_does_not_activate_or_validate_a_product(self):
        limits = self.record["verification_boundaries"]
        self.assertTrue(limits["common_soc_and_kmi_family_relevance_verified"])
        self.assertIsNone(limits["lunch_target"])
        for key, value in limits.items():
            if key not in {"common_soc_and_kmi_family_relevance_verified", "lunch_target"}:
                with self.subTest(key=key):
                    self.assertIs(value, False)
        self.assertFalse(self.record["evidence"]["raw_firmware_and_modules_committed"])

    def test_sanitized_record_has_no_private_identifiers_keys_or_host_paths(self):
        forbidden = {"serial", "serialno", "imei", "imsi", "meid", "account", "email",
                     "phone_number", "private_key", "public_key", "key_blob", "raw_blob"}

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
                self.assertNotIn("/home/", value)
                self.assertNotIn("-----BEGIN", value)
                self.assertNotIn("..", Path(value).parts)

        check(self.record)
        self.assertTrue(self.record["evidence"]["ignored_report_directory"].startswith("reports/"))


if __name__ == "__main__":
    unittest.main()
