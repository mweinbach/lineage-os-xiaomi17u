"""Check the tier 2 v16 camera record: video matrix, microphone, CameraOpt runtime, and the Leica gate."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/tier2-camera-v16-20260910.json"


class Tier2CameraV16Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())

    def test_camcorder_probe_grows_from_v15_to_v16(self):
        p = self.record["camcorder_profiles"]["probe"]
        self.assertEqual(p["v15_total"], 29)
        self.assertEqual(p["v16_total"], 118)
        self.assertTrue(p["v16_cam0_has_2160p"] and p["v16_cam0_has_8k"])
        self.assertEqual(p["v15_cam0_max"], "1920x1080@30")
        self.assertEqual(p["v16_cam0_max"], "7680x4320@30")

    def test_video_matrix_playable_flags_match_the_notes(self):
        by = {c["case"]: c for c in self.record["video_matrix"]}
        self.assertTrue(by["v16-4k60-short"]["playable"])
        self.assertEqual(by["v16-4k60-short"]["width"], 3840)
        self.assertEqual(by["v16-4k60-short"]["gaps_over_100ms"], 0)
        self.assertTrue(by["v16-1080p30-hevc-short"]["playable"])
        for case in ("v16-8k-short", "v16-4k120-short", "v16-sustained-4k60"):
            self.assertFalse(by[case]["playable"], case)

    def test_microphone_tracks_the_tone(self):
        mic = self.record["microphone"]
        self.assertLess(mic["dolby_vision_on"]["window_0_4s_peak_dbfs"], -60)
        self.assertGreater(mic["dolby_vision_on"]["window_5_9s_peak_dbfs"], -10)
        self.assertGreater(mic["dolby_vision_off"]["window_5_9s_peak_dbfs"], -10)

    def test_cameraopt_ran_the_ported_methods_within_the_adj_floor(self):
        rt = self.record["cameraopt_runtime"]
        self.assertGreaterEqual(rt["implemented_counts_after_use"]["reclaimMemoryForCamera"], 1)
        self.assertGreaterEqual(rt["implemented_counts_after_use"]["boostCameraByThreshold"], 1)
        self.assertEqual(rt["adj_floor"], 800)
        self.assertEqual(rt["reclaim_kills"], len(rt["victims"]))
        # every recorded victim sits above the service-B adjustment floor
        for v in rt["victims"]:
            adj = int(v.split("adj ")[1].split(")")[0])
            self.assertGreater(adj, rt["adj_floor"])

    def test_leica_filters_enabled_and_m3_m9_finding_corrected(self):
        leica = self.record["leica"]
        self.assertEqual(leica["cloud_color_filters"]["state"], "enabled and cloud-delivered")
        m = leica["m3_m9_leica_essential"]
        self.assertIn("enabled", m["state"])
        self.assertIn("camera.debug.safe.check.disable", m["correction"])
        self.assertIn("RitIeKoenwCSqcPf", m["correction"])
        self.assertEqual(m["record"], "research/leica-essential-20260910.json")

    def test_document_and_index_name_the_record(self):
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn("Leica Essential", page)
        self.assertIn("leica-essential-20260910.md", page)
        self.assertIn(Path(self.record["document"]).name, (ROOT / "docs/README.md").read_text())


if __name__ == "__main__":
    unittest.main()
