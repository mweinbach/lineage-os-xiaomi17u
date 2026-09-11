"""Recompute the v21 installation record: the model files landed, the app-level gate opened, and the
Qualcomm DSP refused the model. The refusal is the measured result this set exists to establish."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/v21-install-validation-20260911.json"
CONTRACT = ROOT / "config/nezha-now-playing-dsp-model.json"


class V21InstallRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.np = cls.record["now_playing_dsp_model"]

    def test_identity_is_revision_20_over_the_v20_predecessor(self):
        self.assertEqual(self.record["build_number"], "nezha.34aee22f376f606d9ed52909")
        self.assertEqual(self.record["predecessor"], "nezha.d5894f355e27f7d2f503f519")
        self.assertEqual(self.record["source_revision"], 20)

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

    def test_both_model_files_landed_at_the_contract_hashes(self):
        contract = json.loads(CONTRACT.read_text())
        pinned = {f["name"]: (f["size_bytes"], f["sha256"]) for f in contract["files"]}
        recorded = {f["name"]: (f["size_bytes"], f["sha256"]) for f in self.np["files_pinned"]}
        self.assertEqual(recorded, pinned)
        self.assertEqual(set(pinned), {"music_detector.sound_model", "music_detector.descriptor"})
        self.assertTrue(self.np["files_present_on_device_with_pinned_hashes"])

    def test_the_app_gate_opened_but_the_dsp_refused_the_model(self):
        # The switch condition ASI evaluates is l() && r(); r() is the file check this set satisfies.
        self.assertTrue(self.np["switch_enabled_after_model_present"])
        self.assertEqual(self.np["now_playing_enabled_setting_after"], "1")
        self.assertEqual(self.np["verdict"], "dsp_model_load_failed")
        self.assertTrue(self.np["dsp_load_attempted"] and self.np["dsp_load_failed"])
        self.assertEqual(self.np["asi_loaded_models"], [])

    def test_the_refusal_names_the_vendor_uuid_and_the_hal_reboot(self):
        refusal = self.np["refusal"]
        uuid = "9f6ad62a-1f0b-11e7-87c5-40a8f03d3f15"
        self.assertTrue(any(uuid in line for line in refusal["pal_vendor_uuid_lookup"]))
        self.assertTrue(all("Failed to get sound model platform info" in line
                            for line in refusal["pal_refusal"]))
        self.assertTrue(refusal["pal_refusal"])
        self.assertTrue(all("rebooting HAL" in line for line in refusal["framework_reboot"]))
        self.assertIn("config/nezha-now-playing-trigger.json", refusal["contract"])
        self.assertTrue((ROOT / refusal["contract"]).exists())

    def test_leica_and_userdata_survive_the_set(self):
        self.assertTrue(self.record["leica_essential"]["props_from_build_prop_after_reboot"])
        self.assertFalse(self.record["retained_userdata"]["userdata_or_metadata_partition_written"])
        self.assertFalse(self.record["retained_userdata"]["wipe_requested"])

    def test_status_page_and_index_name_the_installed_build(self):
        status = (ROOT / "docs/workspace-status.md").read_text()
        self.assertIn(self.record["build_number"], status)
        self.assertIn("v21-install-validation-20260911.md", (ROOT / "docs/README.md").read_text())
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn("Failed to get sound model platform info", page)
        self.assertIn("now-playing-trigger-20260911.md", page)


if __name__ == "__main__":
    unittest.main()
