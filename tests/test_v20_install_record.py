"""Recompute the v20 installation record and tie it to the HEVC recorder fix (8K/4K120/long-4K60 decodable)."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/v20-install-validation-20260910.json"


class V20InstallRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())

    def test_identity_is_revision_19_over_the_v19_predecessor(self):
        self.assertEqual(self.record["build_number"], "nezha.d5894f355e27f7d2f503f519")
        self.assertEqual(self.record["predecessor"], "nezha.613930978f6706c35296cd90")
        self.assertEqual(self.record["source_revision"], 19)

    def test_eight_writes_in_order_all_acknowledged_without_wipe_or_slot_change(self):
        writes = self.record["writes"]
        self.assertEqual([w["role"] for w in writes], ["super", "dtbo", "init_boot", "vendor_boot", "recovery", "boot", "vbmeta_system", "vbmeta"])
        self.assertTrue(all(w["status"] == "acknowledged" and w["exit_code"] == 0 and w["rehashed_identical"] for w in writes))
        self.assertFalse(self.record["authorization"]["wipe"] or self.record["authorization"]["slot_change"])
        self.assertEqual(self.record["preflight"]["bootloader_values"]["current-slot"], "a")

    def test_boot_is_enforcing_rooted_userdebug(self):
        boot = self.record["boot"]
        self.assertEqual(boot["build_type"], "userdebug")
        self.assertEqual(boot["selinux"], "Enforcing")
        self.assertTrue(boot["root_adb"])
        self.assertLess(boot["seconds_to_boot_completed"], 60)
        self.assertEqual(boot["crash_fatal"], 0)

    def test_all_three_modes_record_a_decodable_hevc_track(self):
        fix = self.record["hevc_recorder_fix"]
        self.assertTrue(fix["all_three_decodable"])
        self.assertEqual(len(fix["patches"]), 3)
        for p in fix["patches"]:
            self.assertTrue((ROOT / p).exists(), p)
        v = fix["video_matrix_measured_on_device"]
        for mode in ("8k30", "4k120", "4k60_long"):
            self.assertTrue(v[mode]["decodable"], mode)
            self.assertEqual(v[mode]["codec"], "hevc", mode)
            self.assertGreater(v[mode]["frames_decoded"], 1, mode)
        self.assertEqual(v["8k30"]["resolution"], "7680x4320")
        self.assertEqual(v["4k120"]["resolution"], "3840x2160")
        self.assertGreater(v["4k120"]["container_fps"], 100)  # a true 120 fps track

    def test_leica_still_baked_and_userdata_retained_and_v19_retired(self):
        self.assertTrue(self.record["leica_essential"]["props_from_build_prop_after_reboot"])
        ud = self.record["retained_userdata"]
        self.assertFalse(ud["userdata_or_metadata_partition_written"])
        ret = self.record["retention"]
        self.assertEqual(sum(r["kib"] for r in ret["removed"]), ret["removed_total_kib"])
        self.assertTrue(all("v19" in r["path"] for r in ret["removed"]))
        self.assertIn("v20", ret["kept"])
        self.assertGreater(ret["host_free_kib_after"], ret["host_free_kib_before"])

    def test_status_page_and_index_name_the_installed_build(self):
        status = (ROOT / "docs/workspace-status.md").read_text()
        self.assertIn(self.record["build_number"], status)
        self.assertIn("v20-install-validation-20260910.md", (ROOT / "docs/README.md").read_text())
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn("7680", page)
        self.assertIn("120", page)


if __name__ == "__main__":
    unittest.main()
