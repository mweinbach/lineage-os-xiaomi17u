"""Check the public static milestone against its committed build ledger.

These offline record tests do not inspect ignored images, run native tools,
contact a phone, or reproduce the recorded artifact verification.
"""
import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TwrpArtifactMilestoneTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/twrp-artifact-milestone.json").read_text())
        cls.ledger = json.loads((ROOT / "research/twrp-build-progress.json").read_text())

    def test_milestone_binds_a_normal_completed_build(self):
        record = self.record
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["status"], "bounded_static_artifact_sequence_passed")
        self.assertEqual(record["target_product"], "twrp_nezha")
        build = self.ledger["attempts"][record["build"]["attempt"] - 1]
        self.assertEqual(build["number"], 66)
        self.assertEqual(build["action"], "build")
        self.assertEqual(build["status"], "completed")
        self.assertEqual(build["command"], ["bash", "build/soong/soong_ui.bash",
                                           "--make-mode", "-j16", "recoveryimage"])
        self.assertEqual(build["command_exit_code"], 0)
        self.assertIs(build["sandbox_fallback_detected"], False)
        self.assertEqual(record["build"]["source_control_commit"], build["workspace_commit"])
        self.assertEqual(record["artifact"]["build_state_sha256"], build["build_state_sha256"])
        self.assertEqual(record["artifact"]["build_receipt_sha256"], build["receipt"]["sha256"])
        self.assertEqual(record["artifact"]["image_sha256"], build["artifact"]["sha256"])
        self.assertEqual(record["artifact"]["image_size_bytes"], build["artifact"]["size_bytes"])

    def test_evidence_identities_do_not_embed_raw_payloads(self):
        evidence = self.record["evidence"]
        self.assertEqual(set(evidence), {"run_report", "verification_report", "capture_report",
                                         "v2_binding", "build_receipt", "elf_inventory", "staging_receipt"})
        for row in evidence.values():
            self.assertEqual(set(row), {"sha256", "size_bytes"})
            self.assertRegex(row["sha256"], r"^[0-9a-f]{64}$")
            self.assertGreater(row["size_bytes"], 0)
        self.assertEqual(evidence["build_receipt"]["sha256"], self.record["artifact"]["build_receipt_sha256"])
        workflow = self.record["workflow"]
        self.assertEqual(workflow["source_manifest_sha256"], self.ledger["source_snapshot"]["sha256"])
        self.assertEqual((workflow["helper_count"], workflow["staged_file_count"]), (16, 18))
        self.assertIs(workflow["matching_staged_helper_identities"], True)
        self.assertIs(workflow["helper_execution_timing_attested"], False)

    def test_native_policy_result_preserves_empty_unfiltered_outputs(self):
        policy = self.record["native_policy"]
        self.assertEqual(policy["returncode"], 0)
        for stream in ("stdout", "stderr"):
            self.assertEqual(policy[stream + "_size_bytes"], 0)
            self.assertEqual(policy[stream + "_sha256"], hashlib.sha256(b"").hexdigest())
        self.assertIs(policy["unfiltered_permissive_query_passed"], True)
        self.assertRegex(policy["policy_sha256"], r"^[0-9a-f]{64}$")

    def test_elf_and_five_compile_roles_remain_static_evidence(self):
        inventory = self.record["elf_inventory"]
        self.assertEqual((inventory["elf_count"], inventory["dependency_count"],
                          inventory["interpreter_count"], inventory["finding_count"]), (160, 1074, 44, 0))
        rows = self.record["compile_evidence"]
        self.assertEqual(len(rows), 5)
        self.assertEqual({row["role"] for row in rows},
                         {"init", "libtwrpinstall", "minadbd", "adbd_main", "adbd_wifi"})
        for row in rows:
            self.assertRegex(row["source_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(row["object_sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(row["packaged_elf_sha256"], r"^[0-9a-f]{64}$")
            self.assertEqual(row["object_format"], "llvm-bitcode-thinlto")
            self.assertIn(row["llvm_module_count"], (1, 2))
            api = "30" if row["role"].startswith("adbd_") else "10000"
            self.assertEqual(row["target_triple"], "aarch64-linux-android" + api)

    def test_three_normalizations_keep_mode_equality_false(self):
        expected = {"twres/ui.xml": ("0755", "0644"),
                    "init.recovery.qcom.rc": ("0644", "0750"),
                    "system/bin/logd": ("0755", "0550")}
        rows = self.record["mode_normalizations"]
        self.assertEqual(len(rows), len(expected))
        self.assertEqual({row["member"] for row in rows}, set(expected))
        for row in rows:
            self.assertEqual((row["staging_mode"], row["packed_mode"]), expected[row["member"]])
            self.assertIs(row["hash_and_mode_match"], False)
            self.assertTrue(row["mode_policy"].startswith("fs_config_"))
        self.assertTrue(self.record["equality_flags"])
        self.assertTrue(all(flag is False for flag in self.record["equality_flags"].values()))

    def test_inventory_and_export_match_the_same_verified_archive(self):
        inventory = self.record["inventory_verification"]
        self.assertEqual(inventory["status"], "inventory_checks_passed")
        self.assertEqual(inventory["cpio_sha256"], self.record["artifact"]["cpio_sha256"])
        self.assertEqual(inventory["archive_entry_count"], 777)
        self.assertEqual(inventory["file_type_counts"], {"directory": 28, "regular": 541, "symlink": 208})
        self.assertEqual(sum(inventory["file_type_counts"].values()), inventory["archive_entry_count"])
        self.assertIs(inventory["archive_dot_present"], False)
        self.assertEqual(inventory["staging_census_count"], 778)
        self.assertEqual(inventory["name_inventory_entries"], 778)
        self.assertEqual(inventory["checksum_entries"], 537)
        self.assertEqual(inventory["etc_target"], "/system/etc")
        self.assertTrue(inventory["checks"])
        self.assertTrue(all(value is True for value in inventory["checks"].values()))
        exported = self.record["local_export"]
        self.assertEqual(exported["image_sha256"], self.record["artifact"]["image_sha256"])
        self.assertEqual(exported["cpio_sha256"], self.record["artifact"]["cpio_sha256"])
        self.assertEqual(exported["image_path"], "artifacts/twrp/nezha/build66/recovery.img")

    def test_prior_failures_and_pending_hardware_work_are_not_relabelled(self):
        self.assertEqual(self.record["capture_status"], "actual_artifact_captured_verification_pending")
        historical = self.record["historical_failures"]
        self.assertEqual([row["run"] for row in historical], ["run63", "run65"])
        for row in historical:
            self.assertEqual(row["status"], "verification_failed")
            self.assertRegex(row["verification_report_sha256"], r"^[0-9a-f]{64}$")
        required = {"boot_tested", "flash_admitted", "authenticated_adb_verified",
                    "runtime_selinux_enforcement_verified", "runtime_file_labels_verified",
                    "runtime_elf_dependency_closure_verified", "oem_authority_verified",
                    "compiler_execution_attested", "compiled_transport_behavior_verified"}
        self.assertTrue(required <= self.record["unverified"].keys())
        self.assertTrue(all(value is False for value in self.record["unverified"].values()))
        self.assertIs(self.record["personal_key_read_or_provisioned"], False)
        self.assertIs(self.record["recovery_log_access_verified"], False)
        self.assertIs(self.record["phone_changed"], False)


if __name__ == "__main__":
    unittest.main()
