"""Recompute the tier 2 v15 measurement record from its private analysis when present, and check its shape."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/tier2-camera-v15-measurements-20260909.json"
CASE = ROOT / "evidence/tier2-camera-v15-20260909/sustained-1080p30-dv-v15"


class MeasurementRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())

    def test_record_is_internally_consistent(self):
        r = self.record["sustained_recording"]
        self.assertLess(abs(r["duration_seconds"] - r["frames_decoded"] / r["fps_every_30s"]), 2.0)
        self.assertEqual(r["gaps_over_100ms"], 0)
        self.assertGreaterEqual(r["board_c"]["end"], r["board_c"]["start"])
        self.assertEqual(r["board_c"]["max"], r["board_c"]["end"])
        self.assertEqual(r["thermal_status_max"], 0)
        z = self.record["per_zoom_photos"]
        self.assertEqual(len(z["steps"]), len(z["focal_mm"]), len(z["focal_35mm"]))
        self.assertEqual(z["focal_mm"][1:], [8.71] * 5)
        self.assertEqual(self.record["build_identity"], "nezha.81c1b93277a1fa371a3efbb3")

    def test_record_matches_the_private_analysis_when_present(self):
        if not (CASE / "analysis.json").exists():
            self.skipTest("private measurement evidence not present")
        a = json.loads((CASE / "analysis.json").read_text())
        r = self.record["sustained_recording"]
        self.assertEqual(a["decoded_frames"], r["frames_decoded"])
        self.assertEqual(a["gap_count_over_100ms"], r["gaps_over_100ms"])
        self.assertEqual(set(a["fps_per_30s"].values()), {r["fps_every_30s"]})
        self.assertEqual(a["board_c_first_last_max"], [r["board_c"]["start"], r["board_c"]["end"], r["board_c"]["max"]])
        self.assertEqual(a["battery_c_first_last"], [r["battery_c"]["start"], r["battery_c"]["end"]])
        self.assertEqual(round(a["duration_s"], 3), r["duration_seconds"])
        self.assertEqual(a["media"][0]["size_bytes"], r["size_bytes"])
        self.assertEqual(int(a["video_stream"]["width"]), r["video"]["width"])
        self.assertEqual(max(int(s["thermal_status"].split()[-1]) for s in a["samples"] if s["thermal_status"]), r["thermal_status_max"])

    def test_document_and_index_name_the_record(self):
        page = (ROOT / self.record["document"]).read_text()
        self.assertIn("24.01 fps", page)
        self.assertIn("What this does not prove", page)
        self.assertIn(Path(self.record["document"]).name, (ROOT / "docs/README.md").read_text())


if __name__ == "__main__":
    unittest.main()
