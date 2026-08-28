"""Validate the public build-attempt ledger without logs, network or a phone."""

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TwrpBuildProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/twrp-build-progress.json").read_text())

    def test_ledger_binds_the_immutable_source_baseline(self):
        record = self.record
        source = json.loads((ROOT / "research/twrp-source-sync.json").read_text())
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["device"], "nezha")
        self.assertEqual(record["base_project_count"], 391)
        self.assertEqual(record["source_snapshot"], source["snapshot"])
        self.assertEqual(record["manifest_commit"], source["manifest"]["commit"])
        snapshot = ROOT / record["source_snapshot"]["path"]
        self.assertEqual(hashlib.sha256(snapshot.read_bytes()).hexdigest(),
                         record["source_snapshot"]["sha256"])

    def test_attempts_keep_ordered_provenance_and_real_outcomes(self):
        attempts = self.record["attempts"]
        self.assertGreaterEqual(len(attempts), 2)
        self.assertEqual([entry["number"] for entry in attempts],
                         list(range(1, len(attempts) + 1)))
        for entry in attempts:
            with self.subTest(attempt=entry["number"]):
                self.assertIn(entry["action"], ("graph", "build"))
                self.assertIn(entry["status"], ("failed", "completed"))
                self.assertRegex(entry["workspace_commit"], r"^[0-9a-f]{40}$")
                self.assertEqual(entry["target_product"], "twrp_nezha")
                self.assertEqual(entry["target_build_variant"], "user")
                self.assertIn(entry["command"][-1], ("nothing", "recoveryimage"))
                self.assertNotIn("recoveryimage-nodeps", entry["command"])
                for name in ("control_archive", "log", "receipt"):
                    identity = entry[name]
                    self.assertTrue(identity["path"].startswith("reports/"))
                    self.assertNotIn("..", Path(identity["path"]).parts)
                    self.assertRegex(identity["sha256"], r"^[0-9a-f]{64}$")
                    self.assertGreater(identity["size_bytes"], 0)
                if entry["status"] == "failed":
                    self.assertNotEqual(entry["failed_command_exit_code"], 0)

    def test_initial_failures_are_not_rewritten_as_successes(self):
        first, second = self.record["attempts"][:2]
        self.assertEqual(first["status"], "failed")
        self.assertEqual(second["status"], "failed")
        self.assertFalse(first["resource_generation_verified"])
        self.assertTrue(second["resource_generation_verified"])
        self.assertEqual(first["supplementary_projects"], [])
        self.assertEqual(second["supplementary_projects"][0]["path"], "system/bpf")
        self.assertEqual(second["supplementary_projects"][0]["commit"],
                         "4447acd742bf443f9088c300bd69f96ede8eaeb1")

    def test_resources_belong_to_the_actual_product_output(self):
        resources = self.record["resource_generation"]["resources"]
        self.assertEqual({Path(item["path"]).name for item in resources},
                         {"splash.xml", "ui.xml"})
        for item in resources:
            self.assertTrue(item["path"].startswith(
                "/work/out/twrp-nezha/target/product/nezha/recovery/root/twres/"))
            self.assertTrue(item["exists"])
            self.assertGreater(item["size_bytes"], 0)
            self.assertTrue(re.fullmatch(r"[0-9a-f]{64}", item["sha256"]))

    def test_observed_configuration_keeps_the_selected_validation(self):
        config = self.record["generated_configuration_observed"]
        for flag in ("Allow_missing_dependencies", "SelinuxIgnoreNeverallows", "Debuggable"):
            self.assertIs(config[flag], False)
        for flag in ("Enforce_vintf_manifest", "BoardAvbEnable"):
            self.assertIs(config[flag], True)

    def test_build_evidence_does_not_admit_phone_actions_or_oem_trust(self):
        for flag in ("hardware_validation_performed", "flash_admitted",
                     "oem_key_trust_established", "phone_commands_run"):
            self.assertIs(self.record[flag], False)
        self.assertTrue(self.record["limitations"])
        artifact = self.record["compiled_recovery_image"]
        if artifact is not None:
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
            self.assertIs(artifact["flash_admitted"], False)


if __name__ == "__main__":
    unittest.main()
