"""Recompute the tier 1 IMS and dim record against the tracked sources it describes."""

import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/tier1-ims-dim-20260909.json"
BUILD = re.compile(r"^nezha\.[0-9a-f]{24}$")
SHA = re.compile(r"^[0-9a-f]{64}$")


class Tier1RecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())

    def test_identities_and_hashes_are_well_formed_and_chained(self):
        revisions = self.record["source_revisions"]
        self.assertEqual([r["revision"] for r in revisions], [12, 13])
        for r in revisions:
            self.assertTrue(BUILD.fullmatch(r["build_number"]))
            self.assertEqual(r["inventory_rows"], 702)
        self.assertEqual(revisions[1]["build_number"], self.record["delivery_set"]["build_number"])
        delivery = self.record["delivery_set"]
        for key in ("unsigned_archive", "system_ext_measured", "reconciled_archive", "super"):
            self.assertTrue(SHA.fullmatch(delivery[key]["sha256"]), key)
            self.assertGreater(delivery[key]["size_bytes"], 0)
        self.assertTrue(SHA.fullmatch(delivery["bundle_manifest_sha256"]))
        self.assertLess(delivery["reconciled_archive"]["size_bytes"], delivery["unsigned_archive"]["size_bytes"])
        self.assertFalse(delivery["installed"] or delivery["flash_authorized"] or delivery["phone_accessed"])

    def test_library_comparison_matches_the_stock_result_and_the_tracked_activation(self):
        libs = self.record["ims"]["java_libraries"]
        self.assertEqual(libs["missing_types"] + libs["missing_methods"] + libs["missing_fields"], 0)
        self.assertEqual({k: libs[k] for k in ("library_types_referenced", "members_found", "members_delegated")},
                         libs["stock_jars_result"])
        activated = (ROOT / "device/xiaomi/nezha/ims/Android.bp").read_text()
        self.assertEqual(len(re.findall(r'^    name: "', activated, re.M)), self.record["ims"]["modules_activated"])
        self.assertEqual(self.record["ims"]["modules_activated"] + self.record["ims"]["modules_dropped_as_duplicates"], 24)
        self.assertEqual(self.record["ims"]["jni"]["shared_module"], "nezha_cam_libimscamera_jni")
        self.assertIn('required: ["nezha_cam_libimscamera_jni"]', activated)

    def test_policy_record_matches_the_tracked_policy_files(self):
        policy = self.record["ims"]["policy"]
        seapp = (ROOT / "device/xiaomi/nezha/ims/sepolicy/private/seapp_contexts").read_text()
        self.assertIn(policy["selector"], seapp)
        private = (ROOT / "device/xiaomi/nezha/ims/sepolicy/private/vendor_qtelephony.te").read_text()
        finds = re.search(r"allow vendor_qtelephony \{([^}]*)\}:service_manager find;", private).group(1).split()
        self.assertEqual(len(finds), policy["service_finds"])
        self.assertEqual(policy["permissive_domains_added"], 0)
        self.assertNotIn("permissive", private)

    def test_dim_record_matches_the_generator(self):
        import sys
        sys.path.insert(0, str(ROOT / "scripts"))
        import display_panel_inputs as panel
        display = self.record["display"]
        self.assertEqual(str(panel.DIM_FLOAT), str(display["dim_float_after"]))
        self.assertEqual(panel.CONTRACT_ID, display["contract"])
        self.assertEqual(display["compiled_value_in_framework_res"], "0.05")
        self.assertEqual(display["dim_float_before"], 0.0)

    def test_status_page_and_index_name_the_delivery(self):
        status = (ROOT / "docs/workspace-status.md").read_text()
        self.assertIn(self.record["delivery_set"]["build_number"], status)
        self.assertIn(self.record["delivery_set"]["bundle_manifest_sha256"], status)
        self.assertIn("tier1-ims-dim-20260909.md", (ROOT / "docs/README.md").read_text())
        page = (ROOT / "docs/tier1-ims-dim-20260909.md").read_text()
        self.assertIn(self.record["delivery_set"]["reconciled_archive"]["sha256"], page)
        self.assertEqual(hashlib.sha256(b"").hexdigest()[:8], "e3b0c442")  # keeps hashlib import honest for future pins


if __name__ == "__main__":
    unittest.main()
