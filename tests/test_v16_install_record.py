"""Recompute the v16 installation record from its rows and tie it to the prepared delivery set."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/v16-install-validation-20260910.json"
CAMERAOPT = ROOT / "research/cameraopt-four-methods-20260909.json"


class V16InstallRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())

    def test_installed_identity_matches_the_prepared_delivery_set(self):
        delivery = json.loads(CAMERAOPT.read_text())["delivery_set"]
        self.assertEqual(self.record["build_number"], delivery["build_number"])
        self.assertEqual(self.record["bundle_manifest_sha256"], delivery["bundle_manifest_sha256"])
        self.assertEqual(self.record["predecessor"], "nezha.81c1b93277a1fa371a3efbb3")

    def test_eight_writes_in_order_all_acknowledged_without_wipe_or_slot_change(self):
        writes = self.record["writes"]
        self.assertEqual([w["role"] for w in writes], ["super", "dtbo", "init_boot", "vendor_boot", "recovery", "boot", "vbmeta_system", "vbmeta"])
        self.assertTrue(all(w["status"] == "acknowledged" and w["exit_code"] == 0 and w["rehashed_identical"] for w in writes))
        self.assertTrue(all(w["target"] == ("super" if w["role"] == "super" else w["role"] + "_a") for w in writes))
        self.assertFalse(self.record["authorization"]["wipe"] or self.record["authorization"]["slot_change"])
        self.assertEqual(self.record["preflight"]["bootloader_values"]["current-slot"], "a")

    def test_boot_and_camcorder_and_cameraopt_are_consistent(self):
        boot = self.record["boot"]
        self.assertEqual(boot["build_type"], "userdebug")
        self.assertEqual(boot["selinux"], "Enforcing")
        self.assertTrue(boot["root_adb"])
        self.assertLess(boot["seconds_to_boot_completed"], 60)
        prof = self.record["camcorder_profiles"]
        self.assertEqual(prof["media_settings_xml"], "/vendor/etc/media_profiles_vendor.xml")
        self.assertEqual(prof["codecs_variant"], "_canoe_v2")
        self.assertRegex(prof["canoe_v2_sha256"], r"^[0-9a-f]{64}$")
        opt = self.record["cameraopt"]
        self.assertIn("configuration_state=loaded", opt["configuration_state"])
        self.assertTrue(any("ro.nezha.cameraopt.service" in p for p in opt["service_property"]))

    def test_leica_edition_gate_is_empty_on_this_unit(self):
        leica = self.record["leica_edition_properties"]
        self.assertEqual(leica["ro_theme_customize"], "")
        self.assertFalse(leica["matching_odm_prop_file_present"])

    def test_userdata_retained_and_v15_retired(self):
        ud = self.record["retained_userdata"]
        self.assertFalse(ud["userdata_or_metadata_partition_written"])
        self.assertEqual(ud["accounts"], "1")
        ret = self.record["retention"]
        self.assertEqual(sum(r["kib"] for r in ret["removed"]), ret["removed_total_kib"])
        self.assertTrue(all("v15" in r["path"] for r in ret["removed"]))
        self.assertIn("v16", ret["kept"])
        self.assertGreater(ret["host_free_kib_after"], ret["host_free_kib_before"])

    def test_status_page_and_index_name_the_installed_build(self):
        status = (ROOT / "docs/workspace-status.md").read_text()
        self.assertIn(self.record["build_number"], status)
        self.assertIn("v16-install-validation-20260910.md", (ROOT / "docs/README.md").read_text())
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn("25.4 seconds", page)


if __name__ == "__main__":
    unittest.main()
