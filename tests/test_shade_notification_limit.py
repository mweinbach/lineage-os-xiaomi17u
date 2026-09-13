"""Protect the measured shade failure and the reviewed source/evidence hashes."""
import hashlib
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
METADATA = ROOT / "patches/evolution/nezha-shade-notification-limit.json"


class ShadeNotificationLimitTests(unittest.TestCase):
    def test_patch_integrity(self):
        record = json.loads(METADATA.read_text())
        patch = (ROOT / record["patch"]).read_bytes()
        self.assertEqual(hashlib.sha256(patch).hexdigest(), record["patch_sha256"])

    def test_measured_stale_limit_requires_unlocked_shade_repair(self):
        # These measured values select the source branch being repaired. A locked
        # shade, a blocked notification or a normal count would be a different bug.
        observed = json.loads(METADATA.read_text())["runtime_observation"]
        self.assertEqual(observed["shade_expanded_fraction"], 1.0)
        self.assertTrue(observed["shade_expanded"])
        self.assertFalse(observed["is_on_lockscreen"])
        self.assertTrue(observed["show_unlimited_notifications"])
        self.assertTrue(observed["is_user_interacting"])
        self.assertFalse(observed["panel_tracking"])
        self.assertFalse(observed["qs_tracking"])
        self.assertEqual(observed["max_displayed_notifications"], 1)
        self.assertEqual(observed["stack_end_height_px"], 342)

    def test_private_evidence_hashes_when_available(self):
        record = json.loads(METADATA.read_text())
        evidence = record.get("validation", {}).get("evidence", [])
        if not evidence or not all((ROOT / item["path"]).is_file() for item in evidence):
            self.skipTest("private device and coroutine evidence is not included in checkout")
        for item in evidence:
            with self.subTest(path=item["path"]):
                actual = hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest()
                self.assertEqual(actual, item["sha256"])


if __name__ == "__main__":
    unittest.main()
