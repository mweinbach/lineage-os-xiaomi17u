"""Recompute the v17 installation record and tie it to the always-on Leica Essential selection."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/v17-install-validation-20260910.json"
LEICA = ROOT / "research/leica-essential-20260910.json"


class V17InstallRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())

    def test_identity_is_revision_16_over_the_v16_predecessor(self):
        self.assertEqual(self.record["build_number"], "nezha.11b0a26475073bca18f34c39")
        self.assertEqual(self.record["predecessor"], "nezha.434625bd9b5cd7a8a7eabd84")
        self.assertEqual(self.record["source_revision"], 16)

    def test_eight_writes_in_order_all_acknowledged_without_wipe_or_slot_change(self):
        writes = self.record["writes"]
        self.assertEqual([w["role"] for w in writes], ["super", "dtbo", "init_boot", "vendor_boot", "recovery", "boot", "vbmeta_system", "vbmeta"])
        self.assertTrue(all(w["status"] == "acknowledged" and w["exit_code"] == 0 and w["rehashed_identical"] for w in writes))
        self.assertTrue(all(w["target"] == ("super" if w["role"] == "super" else w["role"] + "_a") for w in writes))
        self.assertFalse(self.record["authorization"]["wipe"] or self.record["authorization"]["slot_change"])
        self.assertEqual(self.record["preflight"]["bootloader_values"]["current-slot"], "a")

    def test_boot_is_enforcing_rooted_userdebug(self):
        boot = self.record["boot"]
        self.assertEqual(boot["build_type"], "userdebug")
        self.assertEqual(boot["selinux"], "Enforcing")
        self.assertTrue(boot["root_adb"])
        self.assertLess(boot["seconds_to_boot_completed"], 60)
        self.assertEqual(boot["crash_fatal"], 0)

    def test_leica_essential_is_baked_into_build_prop_not_runtime(self):
        leica = self.record["leica_essential"]
        self.assertEqual(leica["system_build_prop_props"]["ro.theme_customize"], "LCC")
        self.assertEqual(leica["system_build_prop_props"]["camera.debug.safe.check.disable"], "true")
        # present after a clean reboot => from the image, not resetprop
        self.assertTrue(leica["present_after_clean_reboot_from_build_prop"])
        self.assertTrue(leica["mode_list_evidence_present"])
        self.assertTrue(leica["app_stayed_open_no_apk_version_error"])
        self.assertIn("no longer used", leica["note"])
        self.assertIn("Magisk", leica["note"])
        self.assertIn("resetprop", leica["note"])
        # cross-check the Leica research record agrees it is built and installed as v17
        built = json.loads(LEICA.read_text())["built_and_installed"]
        self.assertEqual(built["delivery_set"], "v17")
        self.assertEqual(built["build_identity"], self.record["build_number"])
        self.assertFalse(built["runtime_resetprop_or_magisk_used"])

    def test_userdata_retained_and_v16_retired(self):
        ud = self.record["retained_userdata"]
        self.assertFalse(ud["userdata_or_metadata_partition_written"])
        self.assertEqual(ud["accounts"], "1")
        ret = self.record["retention"]
        self.assertEqual(sum(r["kib"] for r in ret["removed"]), ret["removed_total_kib"])
        self.assertTrue(all("v16" in r["path"] for r in ret["removed"]))
        self.assertIn("v17", ret["kept"])
        self.assertGreater(ret["host_free_kib_after"], ret["host_free_kib_before"])

    def test_status_page_and_index_name_the_installed_build(self):
        status = (ROOT / "docs/workspace-status.md").read_text()
        self.assertIn(self.record["build_number"], status)
        self.assertIn("v17-install-validation-20260910.md", (ROOT / "docs/README.md").read_text())
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn("25.5 seconds", page)
        self.assertIn("Leica Essential", page)


if __name__ == "__main__":
    unittest.main()
