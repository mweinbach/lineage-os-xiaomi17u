"""Recompute the September 9 artifact retention record from its own rows."""

import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/artifact-retention-20260909.json"


class ArtifactRetentionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())

    def test_removed_total_and_threshold_recompute_from_rows(self):
        rows = self.record["removed"]
        self.assertEqual(sum(row["kib"] for row in rows), self.record["removed_total_kib"])
        self.assertTrue(all(row["kib"] >= self.record["removal_threshold_kib"] for row in rows))
        self.assertTrue(all(row["kib"] < self.record["removal_threshold_kib"]
                            for row in self.record["kept_small_receipt_directories"]))
        self.assertEqual(len(rows), 46)

    def test_every_removed_path_is_a_superseded_set_under_an_allowed_parent(self):
        kept = self.record["kept_delivery_set"]["artifact_set"]
        parents = tuple(parent + "/" for parent in self.record["allowed_parents"])
        for row in self.record["removed"]:
            with self.subTest(path=row["path"]):
                self.assertTrue(row["path"].startswith(parents))
                self.assertEqual(row["path"].count("/"), row["path"].startswith("artifacts/build-validation/") and 2 or 3)
                self.assertNotIn(kept, row["path"])
        self.assertTrue(all(kept in path for path in self.record["kept_delivery_set"]["directories"]))

    def test_freed_space_is_consistent_with_the_removed_bytes(self):
        freed = self.record["host_free_kib_after"] - self.record["host_free_kib_before"]
        removed = self.record["removed_total_kib"]
        self.assertGreater(freed, removed * 0.95)
        self.assertLess(freed, removed * 1.05)

    def test_kept_set_is_recorded_with_its_hashes(self):
        # The pass kept the set installed at the time (v14); later installs retire it in turn,
        # so the status page need only still name that build as a recorded predecessor.
        kept = self.record["kept_delivery_set"]
        status = (ROOT / "docs/workspace-status.md").read_text()
        page = (ROOT / "docs/artifact-retention-20260909.md").read_text()
        self.assertIn(kept["build_number"], status)
        self.assertIn(kept["build_number"], page)
        for key in ("bundle_manifest_sha256", "reconciled_target_files_sha256"):
            self.assertRegex(kept[key], r"^[0-9a-f]{64}$")
            self.assertIn(kept[key][:8], page)
        self.assertIn(kept["artifact_set"], page)


if __name__ == "__main__":
    unittest.main()
