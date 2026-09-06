"""Offline checks of the authored DSP extension and public evidence contract."""

from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest
import xml.etree.ElementTree as ET

from support import assert_no_private_material


ROOT = Path(__file__).resolve().parents[1]
RECORD = "research/dsp-policy-integration.json"
FACTORY = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
POLICY_PIN = "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27"
SOURCE_PATHS = (
    "device/xiaomi/nezha/sepolicy/system_ext/public/attributes",
    "device/xiaomi/nezha/sepolicy/product/private/isolated_compute_app.te",
)
RECEIPT_HASHES = {
    "source_ownership_receipt": "40c54145c834ceaf8257f3252705e2b6524529b56a6ef455739bd7e4716089f4",
    "policy_capture_receipt": "e9b44133f73254493736496d1fb50b7402b96f3c3b395bbd042b0b35b35fedb3",
    "fixture_receipt": "3b60d9a6a45da4bfb843af4bce4c565c5818469eeaf2b934f8eb58a0e4082f6d",
    "readback_receipt": "95ae454136a17ed46b2e5a8292a3a0678faca5264681dad1ece3fdd3c27a154d",
}


class DspPolicyIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / RECORD).read_bytes()
        cls.record = json.loads(cls.raw)
        cls.contract = cls.record["generator_contract"]
        cls.fixture = cls.record["compiler_fixture"]
        cls.result = cls.record["strict_result"]
        cls.user = json.loads((ROOT / "research/selinux-user-integration.json").read_text())
        cls.factory = json.loads((ROOT / "research/factory-framework-contract.json").read_text())
        cls.validation = json.loads((ROOT / "research/factory-firmware-validation.json").read_text())
        cls.baseline = cls.user["strict_check"]["input_order"]

    def test_contract_has_exact_nezha_identity_profile_and_unverified_factory_origin(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["device"], {"codename": "nezha", "hardware_region": "CN"})
        self.assertEqual(self.contract["contract_id"], "nezha-dsp-membership-v1")
        self.assertEqual(self.contract["profile"], "framework-checks")
        self.assertEqual(self.contract["factory_package_sha256"], FACTORY)
        self.assertEqual(FACTORY, self.validation["package"]["sha256"])
        self.assertIs(self.contract["factory_origin_verified"], False)
        provenance = self.record["provenance"]
        self.assertIsNone(provenance["source_url"])
        self.assertIn("user-provided", provenance["factory_source_kind"])
        for key in ("origin_verified", "oem_trust_root_authenticated", "proprietary_cil_images_or_logs_published"):
            self.assertIs(provenance[key], False)
        self.assertLessEqual(len(self.raw), 20000)

    def test_required_revisions_match_the_resolved_public_snapshot(self):
        path = "research/source-snapshots/evolution-bka-20260827.xml"
        self.assertEqual(self.record["provenance"]["source_snapshot"], path)
        revisions = {row.get("path", row.get("name")): row.get("revision")
                     for row in ET.parse(ROOT / path).findall("project")}
        pins = self.contract["required_source_revisions"]
        self.assertEqual(pins, {
            "system/sepolicy": POLICY_PIN,
            "external/selinux": "085c131ad1b984bfa8ffdafee7a976e9d89f403c",
        })
        for project, revision in pins.items():
            self.assertEqual(revision, revisions[project])
            self.assertEqual(revision, self.user["source_projects"][project]["commit"])

    def test_vendor_and_odm_image_identities_match_factory_logical_outputs(self):
        images = self.contract["vendor_images"]
        self.assertEqual(set(images), {"vendor", "odm"})
        logical = {row["partition"].removesuffix("_a"): row
                   for row in self.validation["logical_partitions"]["outputs"]}
        for partition, row in images.items():
            self.assertEqual(row, {key: logical[partition][key] for key in ("sha256", "size_bytes")})
            self.assertGreater(row["size_bytes"], 0)
        self.assertEqual(images["vendor"]["size_bytes"], 959709184)
        self.assertEqual(images["odm"]["size_bytes"], 4767621120)

    def test_three_factory_cil_references_match_the_unchanged_baseline_inputs(self):
        rows = self.contract["policy_inputs"]
        self.assertEqual(len(rows), 3)
        self.assertEqual([row["runtime_path"] for row in rows],
                         [row["runtime_path"] for row in self.baseline[6:9]])
        factory = {row["runtime_path"]: row for row
                   in self.factory["strict_policy_checks"]["checks"]["factory"]["input_order"]}
        for row, baseline in zip(rows, self.baseline[6:9]):
            self.assertEqual(set(row), {"runtime_path", "path", "sha256", "size_bytes"})
            for key in ("sha256", "size_bytes"):
                self.assertEqual(row[key], baseline[key])
                self.assertEqual(row[key], factory[row["runtime_path"]][key])
            path = PurePosixPath(row["path"])
            self.assertTrue(row["path"].startswith("artifacts/firmware-analysis/" + FACTORY + "/erofs-contract-v1/policy/"))
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
        self.assertEqual(self.contract["policy_capture_receipt"], self.factory["receipts"]["policy_capture"])

    def test_authored_files_match_the_reviewed_source_hashes(self):
        rows = self.contract["source_files"]
        self.assertEqual([row["path"] for row in rows], list(SOURCE_PATHS))
        expected = [
            ("66658bc9fe936e88b469c4a57d3e884d8d194e7e1a5a37fe82ef620908d92803", 169),
            ("d0f258575f1f3147d221d808468d5ae23e04be795a7dddeb9abd792f22b7ca98", 215),
        ]
        for row, identity in zip(rows, expected):
            data = (ROOT / row["path"]).read_bytes()
            self.assertEqual((row["sha256"], row["size_bytes"]), identity)
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
            self.assertEqual(len(data), row["size_bytes"])
        self.assertIs(self.record["provenance"]["authored_source_bytes_match_reviewed_fixture"], True)

    def test_sources_declare_only_one_attribute_and_one_exact_membership(self):
        statements = []
        for path in SOURCE_PATHS:
            text = (ROOT / path).read_text()
            statements.append(re.sub(r"\s+", " ", re.sub(r"#[^\n]*", "", text)).strip())
        self.assertEqual(statements, [
            "attribute vendor_hal_dspmanager_client;",
            "typeattribute isolated_compute_app vendor_hal_dspmanager_client;",
        ])
        for text in statements:
            for forbidden in ("expandattribute", "typealias", "permissive", "allow ", "neverallow ", "dontaudit "):
                self.assertNotIn(forbidden, text)

    def test_wiring_keeps_public_declaration_and_product_private_assignment_separate(self):
        wiring = self.contract["wiring"]
        self.assertEqual(wiring, {
            "SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/system_ext/public",
            "PRODUCT_PRIVATE_SEPOLICY_DIRS": "device/xiaomi/nezha/sepolicy/product/private",
        })
        self.assertEqual(str(PurePosixPath(SOURCE_PATHS[0]).parent), wiring["SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS"])
        self.assertEqual(str(PurePosixPath(SOURCE_PATHS[1]).parent), wiring["PRODUCT_PRIVATE_SEPOLICY_DIRS"])
        ownership = self.record["source_ownership"]
        self.assertEqual((ownership["declaration_layer"], ownership["membership_layer"]), ("system_ext public", "product private"))
        self.assertEqual((ownership["client_attribute"], ownership["member"]),
                         ("vendor_hal_dspmanager_client", "isolated_compute_app"))
        self.assertIs(ownership["original_xiaomi_source_filename_known"], False)

    def test_receipts_bind_ownership_capture_plan_attempt_and_readback_without_opening_them(self):
        for name, digest in RECEIPT_HASHES.items():
            row = self.contract[name]
            self.assertEqual(set(row), {"path", "sha256", "size_bytes"})
            self.assertEqual(row["sha256"], digest)
            self.assertTrue(row["path"].startswith("artifacts/"))
            self.assertNotIn("..", PurePosixPath(row["path"]).parts)
            self.assertGreater(row["size_bytes"], 0)
        plan = self.fixture["derivation_plan"]
        self.assertEqual(plan["sha256"], "707802baf20229f97e6696e4727b5c1902f6d7b4144e00e8103916dce1872f50")
        self.assertTrue(plan["path"].endswith("/prepared-v1/plan.json"))
        self.assertEqual(self.fixture["attempt"], 2)
        self.assertIs(self.fixture["prior_outputs_overwritten"], False)
        self.assertRegex(self.fixture["prior_loader_failure_receipt_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(self.fixture["runtime_bundle_receipt_sha256"], r"^[0-9a-f]{64}$")
        self.assertLess(datetime.fromisoformat(self.fixture["started_at"]), datetime.fromisoformat(self.fixture["completed_at"]))

    def test_old_preprocessed_fixture_is_not_a_fresh_soong_or_m4_build(self):
        self.assertEqual(self.fixture["preprocessed_source_variant"], "userdebug")
        self.assertEqual(self.fixture["final_platform_assembly_variant"], "user")
        self.assertEqual(self.fixture["final_platform_snapshot"], "user-v7")
        self.assertIn("old userdebug preprocessed source", self.fixture["fixture_scope"])
        self.assertIn("No new Soong or m4 evaluation", self.fixture["fixture_scope"])
        self.assertIs(self.fixture["fresh_soong_or_m4_build_performed"], False)
        self.assertIs(self.fixture["plain_source_contains_no_conditional_or_m4_macro_invocations"], True)
        self.assertEqual(self.fixture["source_insertions_at_pinned_file_order_boundaries"], 4)
        self.assertEqual(self.fixture["original_source_bytes_removed"], 0)

    def test_trusted_derivation_tools_and_strict_flags_are_preserved(self):
        tools = {row["name"]: row for row in self.fixture["tools"]}
        self.assertEqual(set(tools), {"checkpolicy", "version_policy", "secilc", "sepolicy-analyze"})
        for row in tools.values():
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(row["size_bytes"], 0)
        self.assertEqual(tools["checkpolicy"]["sha256"], "26eba65919fb50c8c20a0e66a2ca7cf88b1965b4bb32928b9bf7f346170de4e7")
        self.assertEqual(tools["version_policy"]["sha256"], "be55494a98945767502c67213956114b70aace5ed38fc2ea9a54cbf161dc1418")
        self.assertEqual(tools["secilc"]["sha256"], self.factory["strict_policy_checks"]["tools"]["secilc"]["sha256"])
        self.assertEqual(self.fixture["strict_flags"], ["-m", "-M", "true", "-G", "-c", "30"])
        self.assertNotIn("-N", self.fixture["strict_flags"])
        self.assertIs(self.fixture["neverallow_checks_disabled"], False)
        self.assertIs(self.fixture["build_cil_wrapper_disabled_merge_used_as_proof"], False)

    def test_two_generated_fragments_account_for_the_entire_byte_delta(self):
        self.assertEqual((self.fixture["original_input_count"], self.fixture["framework_input_count"],
                          self.fixture["factory_input_count"]), (10, 7, 3))
        self.assertEqual(self.fixture["unchanged_input_count"], 8)
        changed = self.fixture["changed_inputs"]
        self.assertEqual([row["runtime_path"] for row in changed], [self.baseline[2]["runtime_path"], self.baseline[4]["runtime_path"]])
        self.assertEqual([(row["sha256"], row["size_bytes"]) for row in changed], [
            ("7bee774aff706c539a1617c5c2c8f47100fd8987eedeb00e31ab40e1281068ec", 46),
            ("238af2a9cee8a300b574de03a0d26620fb23c6af0a7814e8ff0b6b84da7d2f5d", 73),
        ])
        by_path = {row["runtime_path"]: row for row in self.baseline}
        total = sum(row["size_bytes"] for row in self.baseline)
        delta = sum(row["size_bytes"] - by_path[row["runtime_path"]]["size_bytes"] for row in changed)
        self.assertEqual((total, delta), (5361195, 117))
        self.assertEqual(self.fixture["baseline_input_bytes"], total)
        self.assertEqual(self.fixture["candidate_input_bytes"], total + delta)
        self.assertEqual(self.fixture["candidate_input_bytes"], 5361312)

    def test_empty_controls_and_version_mapping_bytes_remain_exact(self):
        checks = self.fixture["derivation_checks"]
        for key in ("empty_controls_exact_newline", "system_ext_exact_declaration", "product_exact_membership",
                    "public_and_export_diff_exact_unversioned_declaration", "mapping_bytes_identical",
                    "inserted_plain_te_source_only", "no_new_allow_or_assertion_statements"):
            self.assertIs(checks[key], True)
        self.assertEqual(checks["mapping_sha256"], self.baseline[1]["sha256"])
        self.assertEqual(self.fixture["mapping_fragment_bytes"], 1)
        self.assertEqual(self.fixture["mapping_fragment_sha256"], hashlib.sha256(b"\n").hexdigest())
        for index in (3, 5):
            self.assertEqual(self.baseline[index]["sha256"], self.fixture["mapping_fragment_sha256"])
            self.assertEqual(self.baseline[index]["size_bytes"], self.fixture["mapping_fragment_bytes"])

    def test_five_to_four_result_preserves_the_complete_assertion_multiset(self):
        self.assertEqual(self.result["baseline"]["assertion_sites"], 5)
        self.assertEqual(self.result["candidate"]["assertion_sites"], 4)
        self.assertEqual(self.result["baseline"]["displayed_allow_locations"], 11)
        self.assertEqual(self.result["candidate"]["displayed_allow_locations"], 10)
        self.assertEqual(self.result["complete_assertion_count"], 6366)
        self.assertIs(self.result["complete_assertion_multiset_equal"], True)
        self.assertIs(self.result["original_assertions_removed"], False)
        self.assertIs(self.result["only_dsp_failure_removed"], True)
        self.assertIs(self.result["all_four_other_diagnostics_preserved"], True)
        for result in (self.result["baseline"], self.result["candidate"]):
            self.assertEqual(result["exit_code"], 255)
            self.assertGreater(result["stderr"]["size_bytes"], 0)
            self.assertRegex(result["stderr"]["sha256"], r"^[0-9a-f]{64}$")

    def test_remaining_diagnostics_match_the_previous_user_snapshot(self):
        previous = self.user["strict_check"]["diagnostics"]
        self.assertEqual(self.result["removed_assertion"], previous[0]["assertion"])
        self.assertEqual(self.result["removed_assertion"],
                         {"runtime_path": "/vendor/etc/selinux/vendor_sepolicy.cil", "line": 6044})
        expected = [{**row["assertion"], "displayed_allow_count": len(row["displayed_allow_locations"]),
                     "abbreviated_matching_rules": row["abbreviated_matching_rules"]} for row in previous[1:]]
        self.assertEqual(self.result["remaining_assertions"], expected)
        self.assertEqual(self.result["remaining_group_counts"], {"init_properties": 2, "binder_non_domain_objects": 2})
        self.assertEqual(sum(self.result["remaining_group_counts"].values()), len(expected))
        self.assertEqual(sum(row["displayed_allow_count"] for row in expected), self.result["candidate"]["displayed_allow_locations"])
        shortened = [row["abbreviated_matching_rules"] for row in expected if row["abbreviated_matching_rules"]]
        self.assertEqual(shortened, [{"displayed": 4, "total": 35}, {"displayed": 4, "total": 32}])
        self.assertIs(self.result["diagnostic_display_is_complete_inventory"], False)

    def test_existing_vendor_rules_provide_six_new_directed_permissions_not_new_allows(self):
        permissions = self.record["inherited_permissions"]
        self.assertEqual(permissions["existing_vendor_rule_lines"], list(range(6035, 6042)))
        self.assertEqual(permissions["newly_applicable_existing_rules"], len(permissions["existing_vendor_rule_lines"]))
        self.assertEqual(permissions["changed_attribute_sets"], 2)
        self.assertEqual(permissions["edges"], self.user["remaining_group_analysis"]["isolated_compute"]["edges"])
        added = Counter()
        for edge in permissions["edges"]:
            self.assertEqual(set(edge["added"]), set(edge["after_hypothetical"]) - set(edge["before"]))
            self.assertEqual(edge["after_hypothetical"], edge["factory"])
            added[edge["class"]] += len(edge["added"])
        self.assertEqual(added, {"binder": 4, "fd": 2, "service_manager": 0})
        self.assertEqual(permissions["new_directed_binder_permissions"], added["binder"])
        self.assertEqual(permissions["new_directed_fd_permissions"], added["fd"])
        self.assertEqual(permissions["new_service_find_permissions"], added["service_manager"])
        self.assertIs(permissions["all_five_edges_match_factory_static_allow_sets"], True)
        self.assertEqual(self.record["source_ownership"]["new_source_allow_rules"], 0)
        self.assertEqual(self.record["source_ownership"]["new_source_assertions"], 0)

    def test_source_ownership_does_not_add_types_roles_expansion_or_api_mapping(self):
        ownership = self.record["source_ownership"]
        self.assertEqual(ownership["api_version"], self.user["observed_configuration"]["values"]["PlatformSepolicyVersion"])
        self.assertEqual(ownership["new_types_or_roles"], 0)
        self.assertEqual(ownership["factory_declaration"], {"runtime_path": "/system_ext/etc/selinux/system_ext_sepolicy.cil", "line": 198})
        self.assertEqual(ownership["factory_public_export"], {"runtime_path": "/vendor/etc/selinux/plat_pub_versioned.cil", "line": 4987})
        self.assertEqual(ownership["factory_membership"], {"runtime_path": "/product/etc/selinux/product_sepolicy.cil", "line": 15})
        for key in ("core_platform_public_source_modified", "attribute_expansion_directive_added", "new_attribute_mapping_required"):
            self.assertIs(ownership[key], False)
        self.assertEqual(ownership["client_expansion_directives_in_factory_ten_inputs"], 0)
        self.assertEqual(ownership["client_expansion_directives_in_user_ten_inputs"], 0)
        self.assertIs(ownership["named_public_attributes_are_not_versioned"], True)

    def test_guard_and_readback_claims_keep_private_inventory_and_device_access_separate(self):
        guards = self.record["guards"]
        self.assertEqual(guards["copied_inputs_before_after"], 51)
        self.assertEqual(guards["original_sources_and_trusted_tools_before_after"], 26)
        self.assertEqual((guards["readback_file_count"], guards["readback_total_bytes"]), (77, 21042592))
        for key in ("all_input_tool_and_snapshot_identities_unchanged", "mount_observations_before_and_after_matched",
                    "source_old_out_tools_confs_provenance_inputs_read_only", "writable_validation_only_with_private_tmp",
                    "readback_all_hashes_reverified_before_publication"):
            self.assertIs(guards[key], True)
        for key in ("android_source_or_out_written", "user_out_accessed", "phone_accessed",
                    "firmware_executed", "full_private_readback_inventory_published"):
            self.assertIs(guards[key], False)
        self.assertEqual(guards["errors"], [])
        self.assertEqual(guards["guard_errors"], [])

    def test_generator_option_is_explicit_factory_only_and_keeps_legacy_payload(self):
        behavior = self.record["generator_behavior"]
        self.assertEqual(behavior["option"], "--dsp-policy-contract")
        self.assertIs(behavior["optional"], True)
        self.assertIs(behavior["factory_profile_required"], True)
        self.assertIs(behavior["approved_record_hash_pinned_in_generator"], True)
        self.assertIs(behavior["exact_vendor_odm_images_and_three_cil_inputs_required"], True)
        self.assertIs(behavior["exact_source_revisions_and_two_authored_source_hashes_required"], True)
        self.assertEqual(behavior["payload_additions"], [*SOURCE_PATHS, RECORD])
        self.assertEqual(behavior["legacy_payload_file_count"], 12)
        self.assertIs(behavior["default_generation_enables_dsp_extension"], False)
        self.assertIs(behavior["private_policy_inputs_copied_into_generated_payload"], False)
        self.assertIs(behavior["standalone_validation_uses_copied_approved_public_record"], True)
        self.assertIs(behavior["option_is_not_a_flash_or_full_rom_admission"], True)

    def test_generator_pins_this_exact_public_record_sources_and_wiring(self):
        from scripts import generate_device_tree as generator

        self.assertEqual(generator.DSP_POLICY_CONTRACT_SHA256, hashlib.sha256(self.raw).hexdigest())
        self.assertEqual(generator.DSP_POLICY_CONTRACT_ID, self.contract["contract_id"])
        self.assertEqual(str(generator.DSP_POLICY_RECORD), RECORD)
        self.assertEqual({str(generator.DEVICE_PATH / path) for path in generator.DSP_POLICY_FILES}, set(SOURCE_PATHS))
        self.assertEqual(generator.DSP_POLICY_WIRING, self.contract["wiring"])

    def test_partial_compiler_result_is_not_a_binary_treble_or_native_feature_pass(self):
        self.assertEqual(self.fixture["compiled_binary_outputs"], [])
        self.assertIsNone(self.fixture["permissive_analysis"])
        self.assertIs(self.fixture["strict_compilation_passed"], False)
        for value in self.record["limits"].values():
            self.assertIs(value, False)
        for key in ("native_dsp_access_verified_on_evolution", "camera_voice_or_isolated_compute_privacy_verified"):
            self.assertIs(self.record["inherited_permissions"][key], False)
        next_checks = " ".join(self.record["next_validation"])
        for phrase in ("fresh framework/source build", "without removing assertions", "unfiltered permissive-domain analysis",
                       "no skipped inputs", "separately authorized device tests"):
            self.assertIn(phrase, next_checks)

    def test_documentation_links_public_sources_and_keeps_fixture_limits(self):
        path = ROOT / "docs/dsp-policy-integration.md"
        text = path.read_text()
        for phrase in ("6,366 assertions", "exit 255", "no policy binary", "older userdebug preprocessed source",
                       "fresh Soong or m4", "user-v7", "five audited edges", "--dsp-policy-contract",
                       "does not authorize complete"):
            self.assertIn(phrase, text)
        for _, target in re.findall(r"\[([^]]+)\]\(([^)]+)\)", text):
            if target.startswith("https://"):
                self.assertIn("/" + POLICY_PIN + "/", target)
            else:
                self.assertTrue((path.parent / target).is_file(), target)
        self.assertIn(RECEIPT_HASHES["fixture_receipt"], text)
        self.assertIn(self.fixture["derivation_plan"]["sha256"], text)

    def test_public_record_contains_metadata_without_private_payloads(self):
        forbidden = {"raw_cil", "raw_xml", "raw_log", "raw_rule", "private_key", "base64", "data_base64",
                     "serial", "imei", "imsi", "content", "identity", "guest_identity", "guest_receipt_identity"}
        assert_no_private_material(self, self.record, forbidden)


if __name__ == "__main__":
    unittest.main()
