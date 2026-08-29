"""Validate community-reference metadata offline, without ignored captures or a phone."""

import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
PINS = {
    "anto": (
        "antocorvo3000/twrp-xiaomi-17-series",
        "4a35185d43782b4dd460a7f456d674c0976c0859",
        "2dc0d043e2c3e19946f6974c192b05337c48c8e0",
        "cb570a1fe74c49f0698890bafa27df1b264e4785",
    ),
    "ekin": (
        "EkinStrop/twrp_device_xiaomi_nezha",
        "7ad14e492e3ca25a63dfdb39b2fa50e0074a0910",
        "5448dc3b495ce15c6794b3862acb4abb7f5bf935",
        "5448dc3b495ce15c6794b3862acb4abb7f5bf935",
    ),
}
RECEIPTS = {
    "reports/twrp-community-reference-pins-20260828T173600Z.json":
        "ee0d0677a971edfba8c9367c91c6efff84966d6ef79fe818ac5f42f5599ee5b6",
    "reports/twrp-reference-anto/review.json":
        "1ff3131d871f4e72cec0b7244bd83eecaf8a221b9b119f8515f6cbd4eb7b5770",
    "reports/twrp-reference-ekin/audit.json":
        "3c71420a737c105878a242027fb9f6339af82c9ac45d8af523ada14c48e37839",
    "reports/twrp-reference-security/audit.json":
        "0254824d713f5899ff7ec49d8cef20b839da8252f355b08418c12920bc71e789",
    "reports/twrp-reference-ekin/patch-applicability.json":
        "99c1ebff0df999b4aac1d8b90aeb6d1ef4507c6b42248306ddb8f12b6f43efd8",
}


class TwrpCommunityReferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/twrp-community-references.json").read_text())
        cls.stock = json.loads((ROOT / "research/twrp-stock-contract.json").read_text())
        cls.factory = json.loads((ROOT / "research/factory-boot-contract.json").read_text())
        cls.config = json.loads((ROOT / "config/twrp.json").read_text())
        cls.docs = (ROOT / "docs/twrp-community-references.md").read_text()
        cls.refs = {r["id"]: r for r in cls.record["references"]}

    def test_observation_time_comes_from_the_live_metadata_receipt(self):
        self.assertEqual(self.record["schema_version"], 1)
        timestamp = self.record["observed_at_utc"]
        self.assertEqual(timestamp, "2026-08-28T17:36:10.812Z")
        self.assertEqual(datetime.datetime.fromisoformat(timestamp.replace("Z", "+00:00")).utcoffset(),
                         datetime.timedelta(0))
        self.assertIn("Read-only GitHub MCP", self.record["method"])

    def test_both_repositories_have_exact_commit_and_tree_pins(self):
        self.assertEqual(len(self.record["references"]), 2)
        self.assertEqual(set(self.refs), set(PINS))
        for name, (repo, commit, tree, device_tree) in PINS.items():
            with self.subTest(reference=name):
                ref = self.refs[name]
                self.assertEqual((ref["repository"], ref["commit"], ref["tree"], ref["device_tree"]),
                                 (repo, commit, tree, device_tree))
                self.assertEqual(ref["branch_at_observation"], "main")
                self.assertEqual(ref["url"], f"https://github.com/{repo}/tree/{commit}")
                self.assertEqual(ref["source_base_url"], f"https://github.com/{repo}/blob/{commit}/")
                self.assertRegex(commit, r"^[a-f0-9]{40}$")
        self.assertEqual(self.refs["anto"]["device_directory"], "twrp_device_xiaomi_nezha")
        self.assertEqual(self.refs["ekin"]["device_directory"], ".")

    def test_source_paths_cannot_escape_the_pinned_repository(self):
        for ref in self.refs.values():
            for section in ("status", "layout", "security"):
                for path in ref[section]["source_paths"]:
                    with self.subTest(reference=ref["id"], path=path):
                        pure = PurePosixPath(path)
                        self.assertFalse(pure.is_absolute())
                        self.assertNotIn("..", pure.parts)
                        self.assertNotIn("\\", path)
                        url = urlparse(ref["source_base_url"] + path)
                        self.assertEqual(url.scheme, "https")
                        self.assertEqual(url.hostname, "github.com")
                        self.assertIn("/blob/" + ref["commit"] + "/", url.path)

    def test_stock_baseline_is_the_unchanged_tracked_package_contract(self):
        baseline = self.record["stock_baseline"]
        self.assertEqual(baseline["record"], "research/twrp-stock-contract.json")
        self.assertEqual(baseline["factory_record"], "research/factory-boot-contract.json")
        self.assertEqual(baseline["sha256"], "4f42ecd281359e2e7dd7745088af9026ad583b4c7e8002390ad04f608915fa44")
        self.assertEqual(baseline["factory_record_sha256"], "b3ab3adc8458d4cac38506d800016f2d6f2ab0256e46261684f3441b4e2419b0")
        for path_key, hash_key in (("record", "sha256"), ("factory_record", "factory_record_sha256")):
            self.assertEqual(hashlib.sha256((ROOT / baseline[path_key]).read_bytes()).hexdigest(), baseline[hash_key])
        self.assertEqual(baseline["factory_version"], self.stock["provenance"]["factory_version"])
        self.assertEqual(baseline["factory_version"], "OS3.0.309.0.WPACNXM_16.0")
        self.assertIs(baseline["authoritative_over_community_geometry"], True)
        self.assertIs(baseline["physical_phone_capacity_verified"], False)

    def test_ekin_layout_correlates_with_stock_not_a_downloaded_image(self):
        baseline = self.record["stock_baseline"]["recovery"]
        header = self.stock["layout"]["fresh_header"]
        for key in ("header_version", "kernel_size_bytes", "page_size_bytes"):
            self.assertEqual(baseline[key], header[key])
        self.assertEqual((baseline["header_version"], baseline["kernel_size_bytes"],
                          baseline["page_size_bytes"], baseline["image_size_bytes"]),
                         (4, 0, 4096, 104857600))
        self.assertEqual(baseline["image_size_bytes"], self.stock["layout"]["stock_image"]["size_bytes"])
        self.assertEqual(baseline["ramdisk_compression"], self.stock["initial_target_contract"]["ramdisk_compression"])
        ekin = self.refs["ekin"]["layout"]
        self.assertEqual(ekin["boot_header_version"], 4)
        self.assertEqual(ekin["recovery_partition_size_bytes"], baseline["image_size_bytes"])
        for key in ("exclude_kernel_from_recovery", "ramdisk_lz4", "corroborates_stock_image_layout"):
            self.assertIs(ekin[key], True)
        self.assertIs(ekin["generated_image_verified"], False)

    def test_anto_donor_identity_and_dtb_conflicts_remain_explicit(self):
        anto = self.refs["anto"]["layout"]
        self.assertEqual((anto["platform"], anto["bootloader_board"], anto["product"]),
                         ("xiaomi_sm8750", "sun", "sm8750_thales"))
        self.assertIs(anto["target_no_recovery"], True)
        self.assertIs(anto["recovery_in_vendor_boot"], True)
        self.assertEqual(anto["prebuilt_donor_named"], "Popsicle")
        self.assertIs(anto["compatible_with_stock_recovery_layout"], False)
        self.assertIs(anto["prebuilt_payload_identity_verified"], False)
        stock_dtb = self.factory["header_component_readback"]["headers"]["vendor_boot"]["dtb_size_bytes"]
        self.assertEqual(self.record["stock_baseline"]["vendor_boot_dtb_size_bytes"], stock_dtb)
        self.assertEqual((anto["prebuilt_dtb_size_bytes"], stock_dtb), (4511274, 4496880))
        self.assertNotEqual(anto["prebuilt_dtb_size_bytes"], stock_dtb)

    def test_brightness_values_are_compared_without_runtime_claims(self):
        baseline = self.record["stock_baseline"]["brightness"]
        display = self.stock["display_and_input"]["display"]
        self.assertEqual(baseline["path"], display["backlight_path_from_stock_recovery_init"])
        self.assertEqual(baseline["panel_maximum"], display["stock_panel_brightness_max_level"])
        self.assertEqual(baseline["recovery_initial"], display["stock_recovery_initial_brightness"])
        self.assertEqual((baseline["panel_maximum"], baseline["recovery_initial"]), (16383, 200))
        for name, values in (("anto", (1024, 820)), ("ekin", (8191, 4096))):
            with self.subTest(reference=name):
                ref = self.refs[name]["brightness"]
                self.assertEqual((ref["maximum"], ref["default"]), values)
                self.assertNotEqual(values, (baseline["panel_maximum"], baseline["recovery_initial"]))
                self.assertIs(ref["values_stock_verified"], False)
        self.assertIs(baseline["runtime_panel_selection_verified"], False)

    def test_usb_path_facts_match_stock_while_sequence_is_unverified(self):
        lead = self.record["useful_leads"]["usb"]
        stock = self.stock["usb_and_adb"]
        for a, b in (("controller", "usb_controller_from_vendor_bootconfig"),
                     ("mode_path_template", "peripheral_mode_path_template"),
                     ("udc_path_template", "udc_path_template"), ("gadget_root", "configfs_gadget_root")):
            self.assertEqual(lead[a], stock[b])
        self.assertEqual(lead["controller"], "a600000.dwc3")
        self.assertIn("a600000.ssusb", lead["mode_path_template"])
        self.assertIs(lead["stock_paths_correlated"], True)
        self.assertIs(lead["community_sequence_equal"], True)
        self.assertIs(lead["runtime_sequence_verified"], False)

    def test_touch_leads_preserve_stock_closure_and_unverified_blacklist(self):
        lead = self.record["useful_leads"]["touch"]
        touch = self.stock["display_and_input"]["touch"]
        self.assertEqual(set(lead["stock_driver_names"]), {r["filename"] for r in touch["driver_modules"]})
        self.assertEqual(lead["stock_declared_dependency_closure_count"], touch["declared_dependency_closure_count"])
        self.assertEqual(lead["stock_declared_dependency_closure_count"], 13)
        self.assertEqual(lead["community_blacklist"], "hbtp_vm")
        for key in ("blacklist_input_name_verified", "community_modules_or_firmware_verified", "runtime_verified"):
            self.assertIs(lead[key], False)

    def test_maintainer_reports_do_not_become_stock_309_verification(self):
        ekin = self.refs["ekin"]["status"]
        self.assertEqual(ekin["maintainer_test_environment"], "LineageOS")
        self.assertEqual(ekin["user_report_environment"], "Xiaomi.eu build 308")
        self.assertIs(ekin["maintainer_hyperos_test_claimed"], False)
        self.assertEqual(self.refs["anto"]["status"]["decryption"], "Explicitly unconfirmed on Nezha hardware")
        for ref in self.refs.values():
            self.assertIs(ref["stock_309_runtime_verified"], False)
            self.assertIs(ref["nezha_release_asset_observed"], False)
            self.assertIs(ref["adopted"], False)

    def test_neither_tree_claims_a_reproducible_pinned_source_base(self):
        for ref in self.refs.values():
            self.assertIs(ref["pinned_platform_manifest_found"], False)
            self.assertIs(ref["pinned_recovery_source_base_found"], False)
        self.assertIn("fully pinned Android platform manifest", self.docs)

    def test_community_build_waivers_are_recorded_not_adopted(self):
        ekin = self.refs["ekin"]["security"]
        self.assertEqual(ekin["build_variant"], "eng")
        self.assertEqual(set(ekin["build_waivers"]), {
            "ALLOW_MISSING_DEPENDENCIES", "SKIP_ABI_CHECKS", "BUILD_BROKEN_DUP_RULES",
            "BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES", "BUILD_BROKEN_PLUGIN_VALIDATION",
        })
        self.assertIs(self.refs["anto"]["security"]["missing_dependencies_allowed"], True)
        self.assertIs(self.record["security_disposition"]["retain_signature_elf_artifact_and_dependency_checks"], True)

    def test_insecure_adb_and_persistent_mount_settings_are_not_inherited(self):
        for ref in self.refs.values():
            self.assertEqual(ref["security"]["ro_adb_secure"], "0")
            self.assertIs(ref["security"]["persistent_mount_read_only"], False)
        self.assertEqual(self.refs["ekin"]["security"]["adb_tcp_port"], 5555)
        self.assertIs(self.record["security_disposition"]["import_community_access_settings"], False)
        self.assertIs(self.record["security_disposition"]["retain_authenticated_usb_adb"], True)

    def test_selinux_and_avb_declarations_are_not_runtime_or_oem_proof(self):
        security = self.refs["ekin"]["security"]
        self.assertIs(security["permissive_kernel_argument_declared"], True)
        self.assertIs(security["effective_selinux_mode_verified"], False)
        self.assertEqual(security["generic_vbmeta_flags"], 3)
        self.assertIs(security["recovery_footer_flags_verified"], False)
        self.assertEqual(security["avb_key_kind"], "public AOSP test key")
        self.assertEqual(security["platform_version"], "99.87.36")
        self.assertEqual(security["platform_security_patch"], "2099-12-31")
        self.assertEqual(security["vendor_security_patch"], "2099-12-31")
        disposition = self.record["security_disposition"]
        self.assertIs(disposition["retain_enforcing_selinux"], True)
        self.assertIs(disposition["retain_stock_rollback_constraints"], True)
        self.assertIs(disposition["oem_key_trust_verified"], False)

    def test_patch_checks_name_the_real_source_pins_and_scope(self):
        review = self.record["source_patch_review"]
        self.assertEqual(review["recovery_base"], self.config["pinned_projects"]["bootable/recovery"]["commit"])
        self.assertEqual(review["vold_base"], self.config["pinned_projects"]["system/vold"]["commit"])
        self.assertEqual((review["independent_pristine_checks"], review["unchanged_applicable_count"]), (9, 1))
        self.assertIs(review["full_historical_chain_tested"], False)
        self.assertIs(review["current_graph_fix"], False)
        self.assertEqual(len(review["candidates"]), 2)

    def test_super_size_fix_is_applicable_but_not_admitted(self):
        patch = next(p for p in self.record["source_patch_review"]["candidates"] if p["id"].startswith("0002-"))
        self.assertEqual(patch["sha256"], "89ada4a4370e69edc1d836bd6528f08aa5f846955f7bc0c1a53792fda380976b")
        self.assertIs(patch["applies_to_pinned_source"], True)
        self.assertIs(patch["forward_reverse_identity_verified"], True)
        self.assertIs(patch["admitted"], False)
        self.assertIs(patch["runtime_verified"], False)

    def test_gcm_lead_requires_rebase_and_cryptographic_tests(self):
        patch = next(p for p in self.record["source_patch_review"]["candidates"] if p["id"].startswith("0001-"))
        self.assertEqual(patch["sha256"], "d6f8df93691b43233f4c8bee953a687788b10f9599f31575f86882522b0da973")
        self.assertIs(patch["bug_patterns_present_in_pinned_source"], True)
        self.assertIs(patch["applies_to_pinned_source"], False)
        self.assertIs(patch["rebase_required"], True)
        for key in ("cryptographic_vectors_tested", "admitted", "runtime_verified"):
            self.assertIs(patch[key], False)

    def test_logging_correlation_is_not_a_new_nonroot_access_fix(self):
        logging = self.record["useful_leads"]["logging"]
        self.assertIs(logging["anto_logd_matches_pinned_upstream"], True)
        self.assertEqual(logging["logd_source_bytes"], 307)
        self.assertEqual(logging["logd_source_sha256"], "e0444a7b6470b51ab32ba52803ed8d9dba328c6d778a85cb89ba4cb1f24ed476")
        self.assertIs(logging["new_nonroot_log_access_proven"], False)

    def test_review_does_not_authorize_or_perform_mutating_actions(self):
        actions = self.record["review_actions"]
        self.assertEqual(set(actions), {
            "community_artifact_downloaded", "binary_or_key_payload_read", "upstream_script_executed",
            "community_source_adopted", "build_target_changed", "guest_written", "phone_commands_run",
        })
        for key, value in actions.items():
            with self.subTest(action=key):
                self.assertIs(value, False)

    def test_receipt_identities_are_retained_without_reading_ignored_files(self):
        receipts = self.record["evidence_receipts"]
        self.assertEqual(len(receipts), len(RECEIPTS))
        self.assertEqual({r["path"]: r["sha256"] for r in receipts}, RECEIPTS)
        for receipt in receipts:
            self.assertTrue(receipt["path"].startswith("reports/"))
            self.assertNotIn("..", PurePosixPath(receipt["path"]).parts)
            self.assertRegex(receipt["sha256"], r"^[a-f0-9]{64}$")
        self.assertIn("ignored reports", self.record["validation_scope"])

    def test_documentation_preserves_pins_credit_and_validation_limits(self):
        for ref in self.refs.values():
            self.assertIn(ref["url"], self.docs)
            for credit in ref["credit"]:
                self.assertIn(credit, self.record["attribution_and_payloads"])
                self.assertIn(credit, self.docs)
        self.assertIn("2099", self.docs)
        self.assertIn("no raw community sources, binaries, keys or", self.docs)
        self.assertIn("not ignored reports, network access or a phone", self.docs)

    def test_public_record_contains_metadata_not_raw_payloads_or_local_private_paths(self):
        forbidden_keys = {"private_key", "raw_source", "script_body", "blob_data", "base64",
                          "artifact_base64", "device_serial", "serial", "credentials"}

        def visit(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden_keys.intersection(value))
                for child in value.values():
                    visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)
            elif isinstance(value, str):
                self.assertNotIn("-----BEGIN ", value)
                self.assertNotIn("/Users/", value)
                self.assertNotIn("/home/", value)
                self.assertLess(len(value), 2048)

        visit(self.record)


if __name__ == "__main__":
    unittest.main()
