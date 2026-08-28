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
                    if "failed_command_exit_code" in entry:
                        self.assertNotEqual(entry["failed_command_exit_code"], 0)
                    else:
                        # An output/provenance check may fail after the build
                        # command returns zero. Do not invent a command error.
                        self.assertTrue(entry["validation_error"])
                else:
                    self.assertEqual(entry["command_exit_code"], 0)
                    self.assertIs(entry["sandbox_fallback_detected"], False)

    def test_first_complete_graph_has_real_ninja_outputs_and_keeps_prior_failures(self):
        completed = [entry for entry in self.record["attempts"]
                     if entry["action"] == "graph" and entry["status"] == "completed"]
        self.assertTrue(completed)
        first = completed[0]
        self.assertEqual(first["number"], 51)
        self.assertTrue(all(entry["status"] == "failed"
                            for entry in self.record["attempts"][:50]))
        observed = first["full_graph_generation_observed"]
        self.assertIs(observed["image_exists"], False)
        self.assertEqual({Path(item["path"]).name for item in observed["files"]}, {
            "combined-twrp_nezha.ninja", "build-twrp_nezha.ninja",
            "build-twrp_nezha-package.ninja", "build.twrp_nezha.ninja",
        })
        for item in observed["files"]:
            self.assertTrue(item["path"].startswith("/work/out/twrp-nezha/"))
            self.assertGreater(item["size_bytes"], 0)
            self.assertRegex(item["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(observed["completion_receipt"]["sha256"],
                         first["receipt"]["sha256"])
        cleanup = first["clean_state_validation"]
        self.assertTrue(cleanup["preflight_passed"])
        self.assertTrue(cleanup["postflight_passed"])
        self.assertEqual(cleanup["checks_each"], 325)
        self.assertIs(cleanup["existing_state_preserved"], True)

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
        self.assertGreaterEqual(config["attempt"], 12)
        self.assertEqual(config["VendorVars"]["nezha_twrp"]["native_recovery_only"], "true")
        self.assertEqual(config["VendorVarTypes"]["nezha_twrp"]["native_recovery_only"], "bool")
        self.assertRegex(config["source"]["sha256"], r"^[0-9a-f]{64}$")
        profile = self.record["attempts"][11]["native_recovery_profile_observed"]
        self.assertEqual(profile["selected_value"], "true")
        self.assertEqual(profile["variable_type"], "bool")
        self.assertIs(profile["omitted_robolectric_errors"], True)

    def test_build_evidence_does_not_admit_phone_actions_or_oem_trust(self):
        for flag in ("hardware_validation_performed", "flash_admitted",
                     "oem_key_trust_established", "phone_commands_run"):
            self.assertIs(self.record[flag], False)
        self.assertTrue(self.record["limitations"])
        artifact = self.record["compiled_recovery_image"]
        if artifact is not None:
            self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
            self.assertIs(artifact["flash_admitted"], False)

    def test_current_graph_exports_disabled_crypto_and_omapi_as_booleans(self):
        config = self.record["generated_configuration_observed"]
        self.assertGreaterEqual(config["attempt"], 38)
        self.assertLessEqual(config["attempt"], len(self.record["attempts"]))
        values = config["VendorVars"]["twrpGlobalVars"]
        types = config["VendorVarTypes"]["twrpGlobalVars"]
        for name in ("include_se_omapi", "include_crypto", "include_crypto_fbe"):
            with self.subTest(variable=name):
                # soong_config_set_bool serializes false as an empty value.
                self.assertEqual(values[name], "")
                self.assertEqual(types[name], "bool")

    def test_build_commands_distinguish_diagnostic_and_canonical_evidence(self):
        for entry in self.record["attempts"]:
            with self.subTest(attempt=entry["number"]):
                markers = ("diagnostic_only", "canonical_build_receipt_required")
                for marker in markers:
                    if marker in entry:
                        self.assertIs(type(entry[marker]), bool)
                if entry["action"] != "build":
                    # Older graph commands retain their recorded argument shape.
                    self.assertTrue(all(entry.get(marker, False) is False for marker in markers))
                    continue
                command = entry["command"]
                self.assertIsInstance(command, list)
                diagnostic = "-k0" in command or any(entry.get(marker, False) for marker in markers)
                self.assertEqual(len(command), 6 if diagnostic else 5)
                self.assertEqual(command[:3], ["bash", "build/soong/soong_ui.bash", "--make-mode"])
                self.assertRegex(command[3], r"^-j[1-9][0-9]*$")
                self.assertEqual(command[4:], ["-k0", "recoveryimage"] if diagnostic else ["recoveryimage"])
                if diagnostic:
                    for marker in markers:
                        self.assertIs(entry.get(marker), True)
                    if entry["status"] == "completed":
                        self.assertIsInstance(entry.get("artifact"), dict)
                        self.assertTrue({"path", "size_bytes", "sha256"}.issubset(entry["artifact"]))
                        self.assertIs(entry["artifact"].get("flash_admitted"), False)
                        self.assertIs(entry.get("canonical_artifact_admitted"), False)

    def test_build_failure_evidence_cannot_be_recorded_as_completed(self):
        for entry in self.record["attempts"]:
            if entry["action"] == "build":
                with self.subTest(attempt=entry["number"]):
                    if ("failed_command_exit_code" in entry or entry.get("validation_error")
                            or entry.get("command_exit_code", 0) != 0):
                        self.assertEqual(entry["status"], "failed")

    def test_top_level_compiled_image_requires_a_normal_completed_build(self):
        artifact = self.record["compiled_recovery_image"]
        if self.record["status"] == "recovery_image_compiled_artifact_and_hardware_validation_pending":
            self.assertIsNotNone(artifact)
        if artifact is None:
            return
        normal_builds = [entry for entry in self.record["attempts"]
                         if entry["action"] == "build" and entry["status"] == "completed"
                         and entry.get("diagnostic_only", False) is False
                         and entry.get("canonical_build_receipt_required", False) is False
                         and len(entry["command"]) == 5
                         and type(entry.get("command_exit_code")) is int
                         and entry.get("command_exit_code") == 0
                         and entry.get("sandbox_fallback_detected") is False
                         and "failed_command_exit_code" not in entry
                         and not entry.get("validation_error")
                         and isinstance(entry.get("artifact"), dict)]
        identity = {name: artifact[name] for name in ("path", "size_bytes", "sha256")}
        self.assertTrue(any(all(entry["artifact"].get(name) == value
                                for name, value in identity.items()) for entry in normal_builds),
                        "Top-level compiled image requires matching normal completed-build evidence")


if __name__ == "__main__":
    unittest.main()
