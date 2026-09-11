"""Recompute the v22 installation record: the music-trigger shim's three measured modes, including
the one that identified a song, and the UDFPS icon that is built but not yet drawable."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/v22-install-validation-20260911.json"
CONTRACT = ROOT / "config/nezha-now-playing-trigger.json"


class V22InstallRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.trigger = cls.record["now_playing_trigger"]
        cls.modes = cls.trigger["modes"]

    def test_identity_is_revision_22_over_the_v21_predecessor(self):
        self.assertEqual(self.record["build_number"], "nezha.b68e83ef070c648895e3881e")
        self.assertEqual(self.record["predecessor"], "nezha.34aee22f376f606d9ed52909")
        self.assertEqual(self.record["source_revision"], 22)

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

    def test_every_mode_left_the_audio_hal_alone(self):
        # The v21 regression: each refused load rebooted the HAL and restarted audioserver.
        self.assertEqual(set(self.modes), {"off", "periodic", "acd"})
        for mode, row in self.modes.items():
            self.assertEqual(row["hal_reboots"], 0, mode)
            self.assertTrue(row["audio_hal_stable"], mode)
            self.assertEqual(row["mode_property"], mode)
            self.assertEqual(row["now_playing_enabled"], "1", mode)

    def test_off_mode_refuses_recoverably(self):
        off = self.modes["off"]
        self.assertEqual(off["verdict"], "refused_without_hal_reboot")
        self.assertTrue(off["intercepted"] and off["refused_recoverably"])
        self.assertFalse(off["trigger_raised"])

    def test_periodic_mode_drove_asi_all_the_way_to_a_match(self):
        periodic = self.modes["periodic"]
        self.assertEqual(periodic["verdict"], "song_recognized")
        self.assertTrue(periodic["trigger_raised"])
        self.assertTrue(periodic["asi_received_trigger"])
        self.assertTrue(periodic["asi_ran_recognition"])
        self.assertTrue(periodic["history_has_song"])

    def test_acd_mode_loaded_and_armed_the_qualcomm_context_detector(self):
        acd = self.modes["acd"]
        self.assertTrue(acd["acd_loaded"] and acd["acd_started"])
        # Silent room: no context event is expected, and none is claimed.
        self.assertFalse(acd["acd_reported_music"])
        self.assertEqual(acd["verdict"], "acd_armed_no_music_event_yet")

    def test_the_shim_log_shows_each_mode_taking_the_model(self):
        tails = self.trigger["shim_log_tails"]
        self.assertTrue(any("mode=off" in l for l in tails["off"]))
        self.assertTrue(any("periodic trigger" in l for l in tails["periodic"]))
        self.assertTrue(any("QC ACD music context loaded" in l for l in tails["acd"]))
        contract = json.loads(CONTRACT.read_text())
        self.assertEqual(self.trigger["selector"], contract["selector"])
        self.assertTrue((ROOT / self.trigger["patch"]).exists())

    def test_model_files_and_leica_survive_and_userdata_is_retained(self):
        self.assertTrue(self.trigger["model_files_still_present"])
        self.assertTrue(self.record["leica_essential"]["props_from_build_prop_after_reboot"])
        self.assertFalse(self.record["retained_userdata"]["userdata_or_metadata_partition_written"])

    def test_udfps_icon_is_built_but_not_claimed_as_seen(self):
        icon = self.record["udfps_icon"]
        self.assertEqual(icon["built_resource_um"], 8000)
        self.assertEqual(icon["previous_build_resource_um"], 6000)
        self.assertIn("8000", icon["built_resource_line"])
        self.assertEqual(icon["expected_icon_px"], 132)
        # No template is enrolled, so no affordance is drawn and nothing is measured.
        self.assertFalse(icon["drawn_on_lock_screen"])
        self.assertEqual(icon["fingerprint_templates_enrolled"], 0)

    def test_status_page_and_index_name_the_installed_build(self):
        status = (ROOT / "docs/workspace-status.md").read_text()
        self.assertIn(self.record["build_number"], status)
        self.assertIn("v22-install-validation-20260911.md", (ROOT / "docs/README.md").read_text())
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn("song_recognized", page)
        self.assertIn("persist.sys.nezha.nowplaying.mode", page)


if __name__ == "__main__":
    unittest.main()
