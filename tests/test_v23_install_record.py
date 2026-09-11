"""Recompute the v23 installation record: the AICore feature declaration opened Play and delivered a
working runtime, and the model download stops at an attestation-gated server call."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/v23-install-validation-20260911.json"
CONTRACT = ROOT / "config/nezha-aicore.json"


class V23InstallRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.aicore = cls.record["aicore"]
        cls.contract = json.loads(CONTRACT.read_text())

    def test_identity_is_revision_25_over_the_v22_predecessor(self):
        self.assertEqual(self.record["build_number"], "nezha.2fa2ea3549a2fc869a4c79df")
        self.assertEqual(self.record["predecessor"], "nezha.b68e83ef070c648895e3881e")
        self.assertEqual(self.record["source_revision"], 25)

    def test_eight_writes_in_order_all_acknowledged_without_wipe_or_slot_change(self):
        writes = self.record["writes"]
        self.assertEqual([w["role"] for w in writes],
                         ["super", "dtbo", "init_boot", "vendor_boot", "recovery", "boot",
                          "vbmeta_system", "vbmeta"])
        self.assertTrue(all(w["status"] == "acknowledged" and w["exit_code"] == 0
                            and w["rehashed_identical"] for w in writes))
        self.assertFalse(self.record["authorization"]["wipe"]
                         or self.record["authorization"]["slot_change"])
        self.assertEqual(self.record["preflight"]["bootloader_values"]["current-slot"], "a")

    def test_boot_is_enforcing_rooted_userdebug(self):
        boot = self.record["boot"]
        self.assertEqual(boot["build_type"], "userdebug")
        self.assertEqual(boot["selinux"], "Enforcing")
        self.assertTrue(boot["root_adb"])
        self.assertLess(boot["seconds_to_boot_completed"], 60)
        self.assertEqual(boot["crash_fatal"], 0)

    def test_the_declaration_is_what_changed_and_the_phone_now_carries_both_features(self):
        self.assertEqual(self.aicore["features_declared_before"], 0)
        self.assertEqual(sorted(self.aicore["features_declared_on_device"]),
                         ["com.google.android.feature.AICORE_QC",
                          "com.google.android.feature.AICORE_QC_SM8850"])
        # the contract calls the same feature the gate
        self.assertIn("AICORE_QC_SM8850", self.contract["gate_analysis"]["cause"])
        self.assertEqual(self.aicore["selector"], self.contract["selector"])

    def test_play_changed_its_answer_and_delivered_the_qualcomm_build(self):
        self.assertIn("isn't compatible", self.aicore["play_verdict_before"])
        self.assertEqual(self.aicore["play_verdict_after"], "Update")
        installed = self.aicore["installed"]
        self.assertIn(".qc.", installed["version_name"])
        self.assertGreater(installed["version_code"], installed["stub_it_replaced"]["version_code"])
        self.assertGreater(installed["megabytes"], 100)
        # the stub the fragment ships is the one Play replaced
        self.assertIn("stub", installed["stub_it_replaced"]["version_name"])

    def test_the_runtime_carries_the_skeleton_for_this_npu(self):
        runtime = self.aicore["runtime_present"]
        self.assertEqual(runtime["this_npu"], "libQnnHtpV81Skel.so")
        self.assertIn(runtime["this_npu"], runtime["qnn_skels"])
        self.assertTrue(any("LiteRt" in lib for lib in runtime["other"]))

    def test_the_model_download_is_refused_by_the_server_not_by_the_build(self):
        download = self.aicore["model_download"]
        self.assertIn("INVALID_ARGUMENT", download["server_answer"])
        self.assertIn("GetManifestConfig", download["server_call"])
        self.assertIn("keymint", download["immediately_before"])
        self.assertEqual(download["device_state"]["ro.boot.verifiedbootstate"], "orange")
        self.assertEqual(download["device_state"]["vbmeta.device_state"], "unlocked")
        # the flag experiment changed nothing and was undone
        self.assertIn("identical", download["flag_experiment"]["result"])
        self.assertTrue(download["flag_experiment"]["restored"])
        self.assertGreaterEqual(download["attempts"], 2)

    def test_nothing_downstream_of_the_runtime_is_claimed(self):
        self.assertIn("no model", self.record["not_established"].lower())
        page = ROOT / self.record["document"]
        self.assertTrue(page.is_file())
        self.assertIn(page.name, (ROOT / "docs/README.md").read_text())
        body = page.read_text()
        self.assertIn("verifiedbootstate", body)
        self.assertIn("What this does not prove", body)

    def test_userdata_survived_and_the_earlier_features_were_re_observed(self):
        retained = self.record["retained_userdata"]
        self.assertFalse(retained["userdata_or_metadata_partition_written"])
        self.assertFalse(retained["wipe_requested"])
        self.assertGreater(int(retained["third_party_packages"]), 0)
        carried = self.record["carried_forward"]
        self.assertTrue(carried["now_playing"]["model_files_present"])
        self.assertTrue(carried["leica_essential"]["props_from_build_prop_after_reboot"])
        self.assertEqual(carried["dim"]["config_float"], "0.05")

    def test_every_phone_change_during_validation_is_listed(self):
        changes = self.record["device_changes_during_validation"]
        self.assertTrue(any("device_config" in c and "restored" in c for c in changes))
        self.assertTrue(any("audioserver" in c for c in changes))


if __name__ == "__main__":
    unittest.main()
