"""Offline integrity checks for the ARM64 cluster research evidence.

These tests validate the record, not an Android build or a remote worker.
"""

import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "research" / "arm64-cluster"


class Arm64ClusterResearchTests(unittest.TestCase):
    def setUp(self):
        self.pins = json.loads((RESEARCH / "source-pins.json").read_text())

    def test_source_pins_have_immutable_provenance(self):
        self.assertEqual(self.pins["schema_version"], 1)
        seen = set()
        for source in self.pins["sources"]:
            key = (source["repository"], source["requested_ref"])
            with self.subTest(key=key):
                self.assertNotIn(key, seen)
                seen.add(key)
                self.assertIn(source["status"], {"resolved", "unavailable_ref"})
                if source["status"] == "resolved":
                    self.assertRegex(source["commit"], r"^[0-9a-f]{40}$")
                    self.assertRegex(source["metadata_response_sha256"], r"^[0-9a-f]{64}$")
                    self.assertTrue(source["immutable_url"].endswith(source["commit"]))
                    self.assertTrue(source["author_time"])
                    self.assertTrue(source["committer_time"])
                    self.assertIsInstance(source["tree_entries"], list)
                else:
                    self.assertIn("error", source)
                    self.assertNotIn("commit", source)

    def test_inventory_does_not_claim_a_full_build(self):
        self.assertIs(self.pins["full_platform_build_verified"], False)
        self.assertIn("not proof", self.pins["scope"])

    def test_public_arm64_go_and_clang_roots_are_recorded_as_empty(self):
        by_key = {(s["repository"], s["requested_ref"]): s for s in self.pins["sources"]}
        for repository in ("platform/prebuilts/go/linux-arm64",
                           "platform/prebuilts/clang/host/linux-arm64"):
            with self.subTest(repository=repository):
                self.assertEqual(by_key[repository, "main"]["tree_entries"], [])
                self.assertEqual(by_key[repository, "android-16.0.0_r4"]["status"],
                                 "unavailable_ref")

    def test_release_and_main_are_separate_baselines(self):
        refs = {s["requested_ref"] for s in self.pins["sources"]}
        self.assertTrue({"main", "android-16.0.0_r1", "android-16.0.0_r4",
                         "android-17.0.0_r1"}.issubset(refs))


if __name__ == "__main__":
    unittest.main()
