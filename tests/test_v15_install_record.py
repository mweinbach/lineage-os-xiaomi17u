"""Recompute the v15 installation record from its rows and tie it to the tier 1 record."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/v15-install-validation-20260909.json"
TIER1 = ROOT / "research/tier1-ims-dim-20260909.json"


class V15InstallRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.tier1 = json.loads(TIER1.read_text())

    def test_installed_identity_matches_the_prepared_delivery_set(self):
        delivery = self.tier1["delivery_set"]
        self.assertEqual(self.record["build_number"], delivery["build_number"])
        self.assertEqual(self.record["bundle_manifest_sha256"], delivery["bundle_manifest_sha256"])
        self.assertEqual(self.record["predecessor"], self.tier1["predecessor_installed_build"])

    def test_eight_writes_in_order_all_acknowledged_without_wipe_or_slot_change(self):
        writes = self.record["writes"]
        self.assertEqual([w["role"] for w in writes], ["super", "dtbo", "init_boot", "vendor_boot", "recovery", "boot", "vbmeta_system", "vbmeta"])
        self.assertTrue(all(w["status"] == "acknowledged" and w["exit_code"] == 0 for w in writes))
        self.assertTrue(all(w["target"] == ("super" if w["role"] == "super" else w["role"] + "_a") for w in writes))
        self.assertFalse(self.record["authorization"]["wipe"] or self.record["authorization"]["slot_change"])
        self.assertEqual(self.record["preflight"]["bootloader_values"]["current-slot"], "a")

    def test_ims_and_dim_results_are_internally_consistent(self):
        ims = self.record["ims"]
        self.assertEqual(ims["apk_sha256"], "56f103215b1aa301e65b6ecde29bb67318cba07f3f3d91d2196372fd14d44172")
        self.assertEqual(sorted(l.split(":")[1] for l in ims["libraries"]), ["ims-ext-common", "qti-telephony-hidl-wrapper", "qti-telephony-utils"])
        self.assertEqual(ims["avc_denials_for_domain"], 0)
        self.assertFalse(ims["registration_attempted"])
        dim = self.record["dim"]
        self.assertEqual(dim["config_float"], "0.05")
        self.assertGreater(dim["keyguard_dim_panel_value"], 100)
        self.assertLess(dim["keyguard_dim_panel_value"], dim["panel_max"] * 0.05)
        self.assertLess(dim["v14_dim_panel_value"], dim["keyguard_dim_panel_value"])

    def test_retention_and_userdata_recompute(self):
        retention = self.record["retention"]
        self.assertEqual(sum(r["kib"] for r in retention["removed"]), retention["removed_total_kib"])
        self.assertTrue(all("v14" in r["path"] for r in retention["removed"]))
        self.assertIn("v15", retention["kept"])
        ledger = json.loads((ROOT / "research/hardware-ledger-v14-20260909.json").read_text())["measurements"]["retained_userdata"]
        userdata = self.record["retained_userdata"]
        self.assertEqual(userdata["accounts"], ledger["accounts"])
        self.assertEqual(userdata["third_party_packages"], ledger["third_party_packages"])
        self.assertGreaterEqual(userdata["media_files"], ledger["media_files"])

    def test_status_page_and_index_name_the_installed_build(self):
        status = (ROOT / "docs/workspace-status.md").read_text()
        self.assertIn(self.record["build_number"], status)
        self.assertIn("v15-install-validation-20260909.md", status)
        self.assertIn("v15-install-validation-20260909.md", (ROOT / "docs/README.md").read_text())


if __name__ == "__main__":
    unittest.main()
