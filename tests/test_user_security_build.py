"""Offline invariants for the public v8 build record; no private inputs or phone."""

from datetime import datetime
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class UserSecurityBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/user-security-build.json").read_text())
        cls.prior = json.loads((ROOT / "research/selinux-user-integration.json").read_text())

    def test_scope_keeps_provenance_and_runtime_unverified(self):
        r = self.record
        self.assertEqual(r["schema_version"], 1)
        self.assertEqual(r["device"], {"codename": "nezha", "hardware_region": "CN"})
        self.assertEqual(r["snapshot"], "hardened-user-v8-source-build")
        self.assertEqual(r["provenance"]["factory_package_sha256"],
                         self.prior["provenance"]["factory_package_sha256"])
        self.assertIsNone(r["provenance"]["factory_source_url"])
        self.assertIs(r["provenance"]["factory_origin_authenticated"], False)
        self.assertIs(r["provenance"]["historical_receipts_rewritten"], False)
        for key, value in r["limits"].items():
            self.assertEqual(value, [] if key == "checks_disabled" else False, key)

    def test_receipts_identify_distinct_build_analysis_transfer_and_audit(self):
        receipts = self.record["receipts"]
        self.assertEqual(set(receipts), {"build", "build_sandbox", "policy_check", "cil_delta",
                                         "policy_transfer", "source_audit"})
        self.assertEqual(receipts["build"]["sha256"],
                         "869ea7bd4fbb1dd914d5d159ba591efc0a392a44ab63e9a6954281f5755986d6")
        self.assertEqual(receipts["policy_check"]["sha256"],
                         "860ba46668d8dc9f83434a0f3ca6bf7ac1a75e91d07777610f90a744fbf05077")
        self.assertEqual(len({v["sha256"] for v in receipts.values()}), len(receipts))
        for row in receipts.values():
            path = PurePosixPath(row["path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertIn(path.parts[0], {"reports", "artifacts"})
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(row["size_bytes"], 0)

    def test_build_is_successful_user_incremental_component_scope(self):
        b = self.record["build"]
        self.assertEqual((b["target_product"], b["target_release"], b["target_variant"]),
                         ("lineage_nezha", "bp4a", "user"))
        self.assertEqual((b["exit_code"], b["ninja_actions_completed"]), (0, 6551))
        self.assertIs(b["passed"], True)
        self.assertLess(datetime.fromisoformat(b["started_at"]),
                        datetime.fromisoformat(b["completed_at"]))
        self.assertEqual(b["input_admission_sha256"],
                         "d5f390860ad90f35351502887efd43b140c9c5771173ec17ba4e276e2b9afd1a")
        self.assertEqual(b["physical_out_dir"], self.prior["framework_build"]["out"])
        self.assertIs(b["incremental_user_output_reused"], True)
        for key in ("timed_out", "old_output_reset_or_installclean_requested", "source_sync_repeated",
                    "full_rom_build_verified", "policy_targets_include_captured_factory_vendor_cil",
                    "second_stage_init_packaged_into_system_image_verified"):
            self.assertIs(b[key], False, key)
        self.assertEqual(b["checks_disabled_by_this_probe"], [])
        self.assertTrue({"initbootimage", "vendorbootimage", "dtboimage", "init", "precompiled_sepolicy",
                         "sepolicy_neverallows", "sepolicy_test", "sepolicy_dev_type_test"} <= set(b["targets"]))
        self.assertFalse({"droid", "otapackage", "target-files-package"} & set(b["targets"]))

    def test_previous_outputs_are_preserved_and_not_reclassified(self):
        b = self.record["build"]
        for key in ("source_inputs_unchanged_after_build", "all_eleven_old_userdebug_artifacts_unchanged",
                    "prior_user_policy_tools_and_config_preserved"):
            self.assertIs(b[key], True)
        self.assertEqual(b["preserved_user_files"], 17)
        self.assertEqual(b["preservation_manifest_sha256"],
                         "43a54f9e488ccd909589cd8069b7604e555016d5ab0f973f0720c9699adf4406")
        self.assertIs(self.prior["observed_configuration"]["values"]["EnforceSELinuxTrebleLabeling"], False)

    def test_source_audit_matches_snapshot_and_only_three_patches(self):
        r = self.record
        p = ROOT / r["provenance"]["source_snapshot"]
        self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),
                         r["provenance"]["source_snapshot_sha256"])
        revisions = {e.get("path", e.get("name")): e.get("revision")
                     for e in ET.parse(p).findall("project")}
        a = r["source_audit"]
        summary = a["summary"]
        self.assertEqual(summary, {"project_count": 1179, "head_match_count": 1179,
                         "remote_match_count": 1179, "clean_project_count": 1176,
                         "intentional_modified_project_count": 3, "accepted_worktree_count": 1179,
                         "unexpected_projects": []})
        self.assertEqual(len(revisions), summary["project_count"])
        self.assertEqual(a["local_manifest_files"], [])
        self.assertIs(a["project_list_matches"], True)
        for key in ("source_writes_performed", "lfs_payloads_independently_rehashed",
                    "ignored_files_audited", "authored_non_repo_directories_audited"):
            self.assertIs(a[key], False)
        patches = r["source_patches"]
        self.assertEqual({p["project"] for p in patches}, {"vendor/lineage", "system/sepolicy", "system/core"})
        for patch in patches:
            self.assertEqual(patch["base_commit"], revisions[patch["project"]])
            self.assertEqual(hashlib.sha256((ROOT / patch["patch"]).read_bytes()).hexdigest(),
                             patch["patch_sha256"])
        self.assertEqual(sum(len(p["files"]) for p in patches), 4)

    def test_effective_configuration_enforces_checks_without_claiming_test_execution(self):
        c = self.record["observed_configuration"]
        values = c["values"]
        for key in ("Debuggable", "Eng", "SelinuxIgnoreNeverallows"):
            self.assertIs(values[key], False)
        self.assertIs(values["EnforceSELinuxTrebleLabeling"], True)
        self.assertEqual(values["SELinuxTrebleLabelingTrackingListFile"], "")
        self.assertEqual((values["Platform_sdk_version"], values["BoardSepolicyVers"],
                          values["PlatformSepolicyVersion"]), (36, "202504", "202504"))
        self.assertEqual((values["DeviceName"], values["DeviceProduct"]), ("nezha", "lineage_nezha"))
        self.assertIs(c["actual_treble_labeling_test_pass_verified"], False)

    def test_both_binary_checks_are_unfiltered_and_empty(self):
        analysis = self.record["source_policy_analysis"]
        self.assertIs(analysis["unfiltered"], True)
        self.assertIs(analysis["permissive_allowlists_applied"], False)
        self.assertIs(analysis["all_inputs_and_sources_unchanged"], True)
        self.assertIs(analysis["factory_odm_prebuilt_policy_replaced"], False)
        self.assertIs(analysis["runtime_enforcement_verified"], False)
        binaries = analysis["binaries"]
        self.assertEqual([b["name"] for b in binaries], ["source-precompiled", "source-neverallows"])
        self.assertEqual([b["input"]["size_bytes"] for b in binaries], [721536, 775106])
        self.assertEqual([b["input"]["sha256"] for b in binaries], [
            "8ba4d0fa829bf2f4fe8a759953b2afcf886a0ac76933bda6c2e2a28771c8563a",
            "06dd74fe21f27629cd6275cbe88244fa6c0221eecaf147ae34f5a1278b0f09b6"])
        for binary in binaries:
            self.assertEqual(binary["exit_code"], 0)
            self.assertEqual(binary["reported_domains"], [])
            self.assertIs(binary["zero_permissive_domains"], True)
            self.assertEqual(binary["analysis_argv_tail"][-1], "permissive")
            self.assertEqual(len(binary["analysis_argv_tail"]), 3)
            self.assertEqual(binary["stdout"]["size_bytes"], 0)
            self.assertEqual(binary["stdout"]["sha256"], hashlib.sha256(b"").hexdigest())
            self.assertEqual(binary["stderr"]["size_bytes"], 315)
        self.assertIn("/odm/etc/selinux/", binaries[0]["input"]["path"])

    def test_strict_combination_keeps_all_ten_inputs_and_factory_hashes(self):
        strict = self.record["strict_factory_check"]
        prior = self.prior["strict_check"]
        rows = strict["input_order"]
        self.assertEqual([r["runtime_path"] for r in rows],
                         [r["runtime_path"] for r in prior["input_order"]])
        self.assertEqual(strict["input_count"], len(rows))
        self.assertEqual(strict["input_count"], 10)
        self.assertEqual((strict["framework_input_count"], strict["unchanged_factory_input_count"]), (7, 3))
        self.assertEqual(strict["input_bytes"], sum(r["size_bytes"] for r in rows))
        self.assertEqual(strict["input_bytes"], prior["input_bytes"] - 20)
        for old, new in zip(prior["input_order"], rows):
            if new["runtime_path"] != "/system/etc/selinux/plat_sepolicy.cil":
                self.assertEqual((new["sha256"], new["size_bytes"]), (old["sha256"], old["size_bytes"]))

    def test_combined_failure_has_no_binary_or_permissive_pass(self):
        s = self.record["strict_factory_check"]
        self.assertEqual(s["compiler_flags"], ["-m", "-M", "true", "-G", "-c", "30"])
        self.assertNotIn("-N", s["compiler_flags"])
        self.assertEqual((s["exit_code"], s["neverallow_assertion_sites"], s["displayed_allow_locations"]),
                         (255, 5, 11))
        for key in ("passed", "policy_binary_produced", "file_contexts_produced",
                    "assertions_or_diagnostics_filtered", "permissive_analysis_possible_for_failed_combined_binary"):
            self.assertIs(s[key], False)
        self.assertEqual([g["lines"] for g in s["remaining_groups"]], [[6044], [5931, 5746], [24641, 24636]])
        self.assertEqual(sum(len(g["lines"]) for g in s["remaining_groups"]), s["neverallow_assertion_sites"])

    def test_platform_delta_removes_only_permissive_su(self):
        d = self.record["platform_cil_delta"]
        self.assertEqual(d["removed_statement"], "(typepermissive su)")
        self.assertEqual(d["old_bytes"] - d["new_bytes"], len((d["removed_statement"] + "\n").encode()))
        self.assertEqual(d["old_sha256"], self.prior["strict_check"]["input_order"][0]["sha256"])
        self.assertEqual(d["new_sha256"], self.record["strict_factory_check"]["input_order"][0]["sha256"])
        self.assertIs(d["exact_single_statement_difference"], True)
        self.assertIs(d["all_other_cil_bytes_unchanged"], True)
        self.assertIs(d["input_files_modified"], False)
        self.assertIs(d["runtime_enforcement_verified"], False)

    def test_build_and_analysis_sandbox_observations_have_distinct_scope(self):
        s = self.record["sandbox"]
        self.assertEqual(s["build_namespace_separation"], dict.fromkeys(("mnt", "net", "pid", "user"), True))
        for key in ("build_source_read_only", "build_out_read_write",
                    "policy_checks_source_and_both_outs_read_only", "policy_checks_inputs_tools_and_provenance_read_only",
                    "namespace_tmp_backed_inside_validation", "all_policy_inputs_and_sources_unchanged"):
            self.assertIs(s[key], True)
        self.assertIs(s["build_sandbox_fallback_observed"], False)
        self.assertEqual(s["policy_check_count"], 3)
        self.assertEqual(s["policy_check_input_tool_and_provenance_count"], 22)
        self.assertEqual(s["policy_checks_writable_backing_directory"], "/work/validation/nezha-factory-policy-v8-1")

    def test_progress_links_later_proof_without_rewriting_installation_receipts(self):
        progress = json.loads((ROOT / "research/build-progress.json").read_text())
        later = progress["factory_user_security_build"]
        self.assertEqual(later["record"], "research/user-security-build.json")
        self.assertEqual(later["build_receipt_sha256"], self.record["receipts"]["build"]["sha256"])
        self.assertIs(later["build_passed"], True)
        self.assertIs(later["source_policy_zero_permissive_domains"], True)
        self.assertIs(later["combined_factory_policy_passed"], False)
        self.assertIs(later["full_rom_verified"], False)
        self.assertIs(later["phone_accessed"], False)
        source = {p["project"]: p for p in progress["source_adjustments"]}
        self.assertIs(source["system/sepolicy"]["installation"]["built_policy_verified"], False)
        self.assertIs(source["system/core"]["installation"]["android_compilation_verified"], False)


if __name__ == "__main__":
    unittest.main()
