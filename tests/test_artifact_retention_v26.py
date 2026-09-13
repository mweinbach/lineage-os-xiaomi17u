"""Recompute the September 13 artifact retention record from its own rows.

The pass deleted the v23, v24 and v25 delivery-set bytes, so their payload
hashes in this record are the only remaining identification of those builds.
These checks recompute every total the record and its documentation page state,
and hold the removal to the same path rules the deletion script enforced.
"""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/artifact-retention-20260913.json"
PAGE = ROOT / "docs/artifact-retention-20260913.md"

SHA256 = re.compile(r"^[0-9a-f]{64}$")
PAYLOADS = (
    "boot.img",
    "dtbo.img",
    "init_boot.img",
    "recovery.img",
    "super.img",
    "vbmeta.img",
    "vbmeta_system.img",
    "vendor_boot.img",
)


class ArtifactRetentionV26Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.page = PAGE.read_text()

    def test_removed_total_and_threshold_recompute_from_rows(self):
        rows = self.record["removed"]
        self.assertEqual(len(rows), 9)
        self.assertEqual(
            sum(row["kib"] for row in rows), self.record["removed_total_kib"]
        )
        threshold = self.record["removal_threshold_kib"]
        self.assertTrue(all(row["kib"] >= threshold for row in rows))
        self.assertTrue(
            all(
                row["kib"] < threshold
                for row in self.record["kept_small_receipt_directories"]
            )
        )

    def test_page_group_subtotals_recompute_from_the_rows(self):
        # The page breaks the removal into three groups; each subtotal must be
        # the sum of the rows under that parent, not a separately typed number.
        groups = {"artifacts/avb/nezha": 0, "artifacts/flash/nezha": 0, "transfer": 0}
        for row in self.record["removed"]:
            path = row["path"]
            if path.startswith("artifacts/avb/nezha"):
                groups["artifacts/avb/nezha"] += row["kib"]
            elif path.startswith("artifacts/flash/nezha"):
                groups["artifacts/flash/nezha"] += row["kib"]
            else:
                groups["transfer"] += row["kib"]
        self.assertEqual(sum(groups.values()), self.record["removed_total_kib"])
        for subtotal in groups.values():
            self.assertIn(f"{subtotal:,} KiB", self.page)
        self.assertIn(f"{self.record['removed_total_kib']:,} KiB", self.page)

    def test_freed_space_is_consistent_with_the_removed_bytes(self):
        freed = self.record["host_free_kib_after"] - self.record["host_free_kib_before"]
        removed = self.record["removed_total_kib"]
        self.assertGreater(freed, removed * 0.95)
        self.assertLess(freed, removed * 1.05)

    def test_every_removed_path_is_a_superseded_set_under_an_allowed_parent(self):
        kept = self.record["kept_delivery_set"]["artifact_set"]
        superseded = {row["artifact_set"] for row in self.record["removed_sets"]}
        parents = tuple(parent + "/" for parent in self.record["allowed_parents"])
        for row in self.record["removed"]:
            path = row["path"]
            with self.subTest(path=path):
                self.assertTrue(path.startswith(parents))
                expected = 2 if path.startswith("artifacts/build-validation/") else 3
                self.assertEqual(path.count("/"), expected)
                self.assertNotIn(kept, path)
                self.assertTrue(any(name in path for name in superseded))

    def test_the_kept_set_still_exists_with_its_recorded_directories(self):
        kept = self.record["kept_delivery_set"]
        self.assertEqual(kept["build_number"], "nezha.a22a7b1e3294c491ae5d03db")
        for relative in kept["directories"]:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_dir())
        for key in ("bundle_manifest_sha256", "reconciled_target_files_sha256"):
            self.assertRegex(kept[key], SHA256)
            self.assertIn(kept[key][:8], self.page)

    def test_removed_set_bytes_are_gone_but_their_receipts_remain(self):
        for row in self.record["removed"]:
            with self.subTest(path=row["path"]):
                self.assertFalse((ROOT / row["path"]).exists())
        # The admission receipts are pinned by hash elsewhere, so they had to survive.
        for row in self.record["kept_small_receipt_directories"]:
            with self.subTest(path=row["path"]):
                self.assertTrue((ROOT / row["path"] / "admission.json").is_file())

    def test_each_removed_set_is_identified_by_hash_for_a_later_replay(self):
        sets = self.record["removed_sets"]
        self.assertEqual(len(sets), 3)
        for entry in sets:
            with self.subTest(artifact_set=entry["artifact_set"]):
                self.assertRegex(entry["build_number"], r"^nezha\.[0-9a-f]{24}$")
                for key in (
                    "bundle_manifest_sha256",
                    "reconciled_target_files_sha256",
                ):
                    self.assertRegex(entry[key], SHA256)
                    self.assertIn(entry[key][:8], self.page)
                self.assertIn(entry["build_number"], self.page)
                self.assertEqual(tuple(sorted(entry["payload_sha256"])), PAYLOADS)
                for digest in entry["payload_sha256"].values():
                    self.assertRegex(digest, SHA256)
        # Distinct builds must not collapse onto one identity or one Super image.
        self.assertEqual(len({entry["build_number"] for entry in sets}), 3)
        supers = {entry["payload_sha256"]["super.img"] for entry in sets}
        self.assertEqual(len(supers), 3)


if __name__ == "__main__":
    unittest.main()
