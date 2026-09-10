"""Recompute the tier 2 camera records (CameraOpt four methods, camcorder profiles) against their sources."""

import json
from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
CAMERAOPT = ROOT / "research/cameraopt-four-methods-20260909.json"
PROFILES = ROOT / "research/camera-video-profiles-20260909.json"
BUILD = re.compile(r"^nezha\.[0-9a-f]{24}$")


class CameraOptRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(CAMERAOPT.read_text())
        cls.contract = json.loads((ROOT / cls.record["contract"]).read_text())

    def test_record_matches_the_contract_and_the_planner_constants(self):
        r = self.record
        self.assertEqual(r["contract_id"], self.contract["contract_id"])
        self.assertEqual(r["patch"], self.contract["reclaim_patch"]["patch"])
        for method in r["ported_methods"]:
            self.assertIn(method, self.contract["ported_app_reachable_methods"])
        sys.path.insert(0, str(ROOT))
        from scripts import test_nezha_cameraopt_reclaim as harness
        planner = harness.PLANNER.read_text()
        engine = r["reclaim_engine"]
        self.assertIn(f'DEFAULT_CAPTURE_INTERVAL_MS = {r["ported_methods"]["reclaimMemoryForCamera"]["factory_interval_default_ms"]};', planner)
        self.assertIn(f'MAX_KILLS_PER_BATCH = {engine["max_kills_per_batch"]};', planner)
        self.assertIn(f'MAX_COMPACTIONS_PER_PASS = {engine["max_compactions_per_pass"]};', planner)
        self.assertEqual(engine["adj_floor"], 800)
        self.assertIn("ADJ_FLOOR = ProcessList.SERVICE_B_ADJ", planner)
        for level, scene in r["ported_methods"]["boostCameraByThreshold"]["factory_scenes"].items():
            self.assertIn(f'"{scene}"', planner, level)
        self.assertTrue(BUILD.fullmatch(r["evidence"]["source_revision"]["build_number"]))
        self.assertEqual(r["evidence"]["source_revision"]["inventory_rows"], 707)
        self.assertEqual(r["evidence"]["source_revision"]["changed_files"],
                         r["evidence"]["source_revision"]["added_files"] + r["evidence"]["source_revision"]["modified_files"])
        self.assertEqual(sorted(r["evidence"]["component_build"]["services_jar_defines"]), sorted(self.contract["reclaim_helper_classes"]))
        self.assertEqual(r["evidence"]["planner_harness_gap_kb"], 300000)

    def test_document_and_index_name_the_record(self):
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn(self.record["evidence"]["source_revision"]["build_number"], page)
        self.assertIn(str(self.record["evidence"]["planner_harness_checks"]), page)
        self.assertIn("What this does not prove", page)
        self.assertIn(Path(self.record["document"]).name, (ROOT / "docs/README.md").read_text())


class VideoProfilesRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(PROFILES.read_text())
        cls.contract = json.loads((ROOT / cls.record["contract"]).read_text())

    def test_record_matches_the_contract(self):
        r, c = self.record, self.contract
        self.assertEqual(r["cause"]["property"], c["property"]["name"])
        self.assertEqual(r["cause"]["stock_value"], c["property"]["value"])
        self.assertEqual(r["fix"]["fragment"], c["fragment"])
        self.assertEqual(r["fix"]["selector"], c["selector"])
        self.assertEqual(r["measured_build"], c["measured_on_v15"]["build_identity"])
        self.assertEqual(r["tables"]["media_profiles_V1_0.xml"]["camera0_highest"], c["measured_on_v15"]["loaded_table_camera0_highest"])
        self.assertEqual(r["tables"]["media_profiles_V1_0.xml"]["camera0_profiles"], c["measured_on_v15"]["loaded_table_camera0_profiles"])
        self.assertEqual(r["tables"]["media_profiles_canoe_v2.xml"]["camera0_profiles"], c["measured_on_v15"]["factory_table_camera0_profiles"])
        self.assertEqual(r["tables"]["media_profiles_canoe_v2.xml"]["high_speed"], c["measured_on_v15"]["factory_table_high_speed"])

    def test_tables_recompute_when_the_private_copies_are_present(self):
        import xml.etree.ElementTree as ET
        base = ROOT / "evidence/tier2-camera-v15-20260909/capabilities"
        if not (base / "media_profiles_canoe_v2.xml").exists():
            self.skipTest("private capability evidence not present")
        for name, expected in self.record["tables"].items():
            tree = ET.parse(base / name).getroot()
            cameras = {cam.get("cameraId"): cam for cam in tree.iter("CamcorderProfiles")}
            profiles = list(cameras["0"].iter("EncoderProfile"))
            self.assertEqual(len(profiles), expected["camera0_profiles"], name)
            best = max(profiles, key=lambda e: int(e.find("Video").get("width")))
            video = best.find("Video")
            self.assertEqual(f'{video.get("width")}x{video.get("height")}@{video.get("frameRate")}', expected["camera0_highest"])

    def test_document_and_index_name_the_record(self):
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn("media.settings.xml", page)
        self.assertIn("What this does not prove", page)
        self.assertIn(Path(self.record["document"]).name, (ROOT / "docs/README.md").read_text())


if __name__ == "__main__":
    unittest.main()


class PreparedDeliveryTests(unittest.TestCase):
    """The prepared v16 set: both records carry the same hashes, and nothing claims installation or approval."""

    def test_records_share_one_prepared_delivery_that_is_not_installed(self):
        first = json.loads(CAMERAOPT.read_text())["delivery_set"]
        second = json.loads(PROFILES.read_text())["delivery_set"]
        self.assertEqual(first, second)
        self.assertTrue(BUILD.fullmatch(first["build_number"]))
        for key in ("unsigned_archive", "reconciled_archive", "super", "system_ext_measured"):
            self.assertRegex(first[key]["sha256"], r"^[0-9a-f]{64}$", key)
            self.assertGreater(first[key]["size_bytes"], 0)
        self.assertRegex(first["bundle_manifest_sha256"], r"^[0-9a-f]{64}$")
        self.assertLess(first["reconciled_archive"]["size_bytes"], first["unsigned_archive"]["size_bytes"])
        self.assertFalse(first["installed"] or first["flash_authorized"] or first["phone_accessed"])
        self.assertEqual(first["bundle_payloads"], 8)
        status = (ROOT / "docs/workspace-status.md").read_text()
        self.assertIn(first["build_number"], status)
        self.assertIn(first["bundle_manifest_sha256"], status)
        # The installed identity on the status page is still v15.
        self.assertIn("| Installed build identity | `nezha.81c1b93277a1fa371a3efbb3`", status)
        page = (ROOT / "docs/cameraopt-four-methods-20260909.md").read_text()
        for value in (first["build_number"], first["reconciled_archive"]["sha256"], first["bundle_manifest_sha256"]):
            self.assertIn(value, page)
