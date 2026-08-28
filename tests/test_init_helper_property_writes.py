"""Offline source/metadata checks; no private inputs, M4, processes or phone."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InitHelperPropertyWritesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "patches/evolution/init-helper-property-writes.json").read_text())
        cls.raw = (ROOT / cls.record["patch"]).read_bytes()
        cls.patch = cls.raw.decode()

    def test_source_patch_is_bound_to_the_exact_pinned_single_file(self):
        r = self.record
        self.assertEqual(r["schema_version"], 1)
        self.assertEqual(r["project"], "system/sepolicy")
        self.assertEqual(r["base_commit"], "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27")
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), r["patch_sha256"])
        self.assertEqual(r["patch_sha256"], "5017f88c6e4af56f931bccc488a8120487c938d55ecbf5ce38118a6c6b4b0c1a")
        self.assertEqual(len(r["files"]), 1)
        source = r["files"][0]
        self.assertEqual(source["path"], "private/init_dev_config.te")
        self.assertEqual(source["before_sha256"], "48ccb169eb04e90e87ce9ee68ed037ee9aecadf82fb8600f64cec110d68e114f")
        self.assertEqual(source["after_sha256"], "1ff8ff9a44a9607724409dfc3eb29e49547a0a98400a4442b17ae33bc4ea7da2")
        self.assertEqual((source["before_size_bytes"], source["after_size_bytes"]), (299, 1001))
        for key in ("before_git_blob", "after_git_blob"):
            self.assertRegex(source[key], r"^[a-f0-9]{40}$")
        self.assertTrue(self.patch.startswith("--- a/private/init_dev_config.te\n+++ b/private/init_dev_config.te\n"))

    def test_patch_hunk_and_size_delta_are_consistent(self):
        self.assertEqual(re.findall(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@", self.patch, re.M),
                         [("6", "5", "6", "20")])
        lines = self.patch.split("@@ -6,5 +6,20 @@\n")[1].splitlines(keepends=True)
        self.assertEqual(sum(line.startswith((" ", "-")) for line in lines), 5)
        self.assertEqual(sum(line.startswith((" ", "+")) for line in lines), 20)
        self.assertTrue(all(line[:1] in (" ", "+", "-") for line in lines))
        delta = sum(len(line[1:].encode()) for line in lines if line.startswith("+"))
        delta -= sum(len(line[1:].encode()) for line in lines if line.startswith("-"))
        self.assertEqual(delta, 702)
        self.assertTrue(self.raw.endswith(b"\n"))

    def test_git_application_proof_is_bound_and_separate_from_source_adoption(self):
        proof = self.record["source_application_validation"]
        self.assertEqual(proof["git_apply_check_exit_code"], 0)
        self.assertEqual(proof["git_apply_exit_code"], 0)
        self.assertIs(proof["expected_result_bytes_matched"], True)
        self.assertIs(proof["isolated_source_fixture"], True)
        self.assertIs(proof["android_checkout_modified"], False)
        self.assertIs(proof["policy_compiler_executed"], False)
        self.assertEqual(proof["receipt"], {
            "path": "artifacts/source-contracts/nezha-init-helper-capability-v1/git-application-v1/receipt.json",
            "size_bytes": 1851,
            "sha256": "214a9b27694ad3cdeb87315fe0036e0ce98046a19dc1bfaa97e800bfed86b262",
        })

    def test_default_branch_retains_both_original_set_prop_calls(self):
        c = self.record["capability"]
        self.assertEqual(c["symbol"], "target_init_dev_config_property_writes")
        self.assertEqual(c["allowed_explicit_values"], ["true", "false"])
        self.assertIs(c["undefined_preserves_upstream_grants"], True)
        self.assertIs(c["true_preserves_upstream_grants"], True)
        self.assertIn("+ifelse(defn(`target_init_dev_config_property_writes'), `false', `\n", self.patch)
        self.assertIn("+', `\n set_prop(init_dev_config, apexd_select_prop)\n"
                      " set_prop(init_dev_config, media_variant_prop)\n+')\n", self.patch)

    def test_disabled_branch_preserves_two_socket_and_two_read_macro_calls(self):
        part = self.patch.split("+ifelse(defn(`target_init_dev_config_property_writes'), `false', `\n", 1)[1]
        part = part.split("+', `\n", 1)[0]
        self.assertEqual(part.splitlines(), [
            "+unix_socket_connect(init_dev_config, property, init)",
            "+get_prop(init_dev_config, apexd_select_prop)",
            "+unix_socket_connect(init_dev_config, property, init)",
            "+get_prop(init_dev_config, media_variant_prop)",
        ])
        self.assertNotIn("set_prop", part)

    def test_invalid_values_fail_before_property_grants_without_api_inference(self):
        self.assertIn("+ifdef(`target_init_dev_config_property_writes', `\n", self.patch)
        self.assertIn("+       `errprint(`target_init_dev_config_property_writes must be true or false\n", self.patch)
        self.assertIn("+')m4exit(1)')\n", self.patch)
        added = "\n".join(line[1:] for line in self.patch.splitlines() if line.startswith("+") and not line.startswith("+++"))
        self.assertNotIn("board_api", added)
        self.assertNotIn("202504", added)
        self.assertNotIn("202604", added)
        self.assertIs(self.record["capability"]["api_version_inference_used"], False)
        self.assertIs(self.record["capability"]["invalid_value_causes_fatal_m4_error"], True)

    def test_macro_evidence_preserves_ordered_grants_and_duplicates(self):
        proof = self.record["macro_validation"]
        self.assertEqual([case["name"] for case in proof["cases"]], ["original", "undefined", "enabled", "disabled"])
        self.assertEqual([case["explicit_value"] for case in proof["cases"]], [None, None, "true", "false"])
        self.assertEqual([case["grant_occurrences"] for case in proof["cases"]], [8, 8, 8, 6])
        self.assertEqual([case["property_service_set_occurrences"] for case in proof["cases"]], [2, 2, 2, 0])
        for case in proof["cases"]:
            self.assertEqual(case["exit_code"], 0)
            for key in ("property_file_read_occurrences", "socket_write_occurrences", "socket_connect_occurrences"):
                self.assertEqual(case[key], 2)
            self.assertRegex(case["expanded_text_sha256"], r"^[a-f0-9]{64}$")
            self.assertGreater(case["expanded_text_size_bytes"], 0)
        self.assertIs(proof["ordered_grants_and_duplicate_counts_checked"], True)
        self.assertIs(proof["independent_permission_tuple_model_checked"], True)

    def test_invalid_macro_cases_are_recorded_without_a_synthetic_pass_claim(self):
        invalid = self.record["macro_validation"]["invalid_values"]
        self.assertEqual(len(invalid), 11)
        self.assertEqual(len({row["value"] for row in invalid}), 11)
        for row in invalid:
            self.assertNotIn(row["value"], ("true", "false"))
            self.assertEqual(row["exit_code"], 1)
            self.assertIs(row["permission_grants_emitted"], False)

    def test_host_macro_proof_is_not_android_m4_or_full_source_compilation(self):
        proof = self.record["macro_validation"]
        self.assertEqual(proof["host_tool"]["version"], "GNU M4 1.4.6")
        self.assertEqual(proof["host_tool"]["path"], "/usr/bin/m4")
        self.assertEqual(proof["host_tool"]["sha256"], "1685f2c90307faa05ef5ae8f707d3a18a519c9dad75882768f66abb475f1b3d7")
        self.assertIs(proof["host_tool"]["is_android_build_m4"], False)
        for key in ("android_build_m4_executed", "full_policy_compiler_executed", "unchanged_prefix_expanded_in_macro_fixture"):
            self.assertIs(proof[key], False)
        self.assertEqual(proof["synthetic_tests_passed"], 35)
        self.assertIs(proof["synthetic_process_calls_mocked"], True)

    def test_narrow_conditional_effect_leaves_assertions_and_other_domains_unchanged(self):
        effect = self.record["conditional_effect"]
        self.assertEqual(effect["source_domain"], "init_dev_config")
        self.assertEqual(effect["property_types"], ["apexd_select_prop", "media_variant_prop"])
        self.assertEqual((effect["class"], effect["permission"]), ("property_service", "set"))
        self.assertEqual((effect["set_grants_removed_when_false"], effect["grants_added"]), (2, 0))
        self.assertEqual(effect["other_source_prefix_bytes"], 208)
        for key in ("source_domain_types_transitions_prefix_unchanged", "property_reads_and_socket_grants_unchanged",
                    "existing_init_and_vendor_init_permissions_unchanged"):
            self.assertIs(effect[key], True)
        for key in ("assertions_modified", "platform_api_mappings_modified", "service_invocation_modified"):
            self.assertIs(effect[key], False)

    def test_static_source_wiring_does_not_claim_the_definition_was_installed(self):
        source = self.record["source_wiring"]
        self.assertIs(source["statically_verified"], True)
        self.assertEqual([row["line"] for row in source["steps"]], [217, 397, 2036, 256])
        self.assertIs(source["new_value_observed_in_actual_build"], False)
        capability = self.record["capability"]
        self.assertEqual(capability["board_variable"], "BOARD_SEPOLICY_M4DEFS")
        self.assertIs(capability["new_board_definition_installed"], False)
        self.assertIs(capability["duplicate_admission_guard_implemented"], False)
        self.assertIs(capability["duplicate_definitions_rejected_by_future_admission"], True)

    def test_static_media_path_is_observed_without_claiming_runtime_nonuse(self):
        evidence = self.record["static_vendor_evidence"]
        self.assertIsNone(evidence["source_url"])
        self.assertIs(evidence["origin_authenticated"], False)
        capture = evidence["capture"]
        self.assertEqual((capture["vendor_files"], capture["odm_files"], capture["total_files"]), (178, 75, 253))
        self.assertEqual(capture["vendor_files"] + capture["odm_files"], capture["total_files"])
        self.assertEqual((capture["total_bytes"], capture["helper_literal_hits"], capture["media_setter_source_statements"]), (716487, 0, 4))
        self.assertEqual((capture["vendor_selected_symlinks_not_followed"], capture["odm_selected_symlinks_not_followed"]), (2, 0))
        self.assertEqual(evidence["existing_action_triggers"], ["property:vendor.media.target_variant=*", "post-fs-data"])
        self.assertIs(evidence["existing_vendor_init_media_set_grant_observed"], True)
        for key in ("selector_value_or_producer_verified", "runtime_imports_or_triggers_evaluated",
                    "complete_provider_or_import_closure_verified", "runtime_helper_absence_proven"):
            self.assertIs(evidence[key], False)

    def test_private_bindings_are_metadata_and_not_read_by_workspace_tests(self):
        self.assertEqual(len(self.record["source_capture_bindings"]), 9)
        for row in [*self.record["source_capture_bindings"], *self.record["receipts"].values()]:
            path = PurePosixPath(row["path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertEqual(path.parts[0], "artifacts")
            self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")
            self.assertGreater(row["size_bytes"], 0)

    def test_patch_remains_unadmitted_and_cannot_claim_a_feature_or_policy_pass(self):
        self.assertEqual(self.record["status"], "tested_optional_source_patch_not_admitted")
        for key, value in self.record["limits"].items():
            self.assertEqual(value, [] if key == "checks_disabled" else False, key)
        requirements = " ".join(self.record["adoption_requirements"])
        for phrase in ("duplicate definitions", "unresolved selectors", "final link evidence", "unfiltered",
                       "cannot waive vendor assertions", "separately authorized device tests"):
            self.assertIn(phrase, requirements)


if __name__ == "__main__":
    unittest.main()
