"""Offline checks of the narrow source patch, not private policy or device tests."""

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


class SelinuxEnforcementPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "patches/evolution/selinux-enforcement.json").read_text())
        cls.raw = (ROOT / cls.record["patch"]).read_bytes()
        cls.patch = cls.raw.decode()

    def test_patch_and_both_source_versions_are_explicitly_bound(self):
        self.assertEqual(self.record["project"], "system/sepolicy")
        self.assertEqual(self.record["base_commit"], "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27")
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), self.record["patch_sha256"])
        self.assertEqual(len(self.record["files"]), 1)
        source = self.record["files"][0]
        self.assertEqual(source["path"], "private/su.te")
        self.assertEqual(source["before_sha256"], "aa90a463c2e7a98f749c474f08c864be65467bca8118481de0388e8ce85e924f")
        self.assertEqual(source["after_sha256"], "111c6d9384480ef07d0e47cabdc69cc990112831b783a6e14db619b26ca2dc01")
        self.assertEqual(source["before_size_bytes"] - source["after_size_bytes"], 62)
        self.assertIn(source["before_git_blob"] + ".." + source["after_git_blob"], self.patch)

    def test_only_the_unconditional_permissive_statement_and_its_comment_are_removed(self):
        removed = [line[1:] for line in self.patch.splitlines() if line.startswith("-") and not line.startswith("---")]
        added = [line[1:] for line in self.patch.splitlines() if line.startswith("+") and not line.startswith("+++")]
        self.assertEqual(removed, ["", "# su is also permissive to permit setenforce.", "permissive su;"])
        self.assertEqual(added, [])
        self.assertEqual(self.record["removed_policy_statements"], ["permissive su;"])
        self.assertIn(" ')\n", self.patch)
        self.assertNotIn("--disable-neverallow", self.patch)

    def test_single_file_hunk_counts_match_and_preserve_the_macro_closure(self):
        matches = re.findall(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@", self.patch, re.M)
        self.assertEqual(matches, [("132", "6", "132", "3")])
        body = self.patch.split("@@ -132,6 +132,3 @@\n", 1)[1].splitlines()
        self.assertEqual(sum(line.startswith((" ", "-")) for line in body), 6)
        self.assertEqual(sum(line.startswith((" ", "+")) for line in body), 3)
        self.assertEqual(self.patch.count("diff --git "), 1)
        self.assertTrue(self.raw.endswith(b"\n"))

    def test_patch_does_not_claim_a_complete_enforcing_or_compatible_policy(self):
        for flag in ("allow_rules_changed", "neverallow_rules_changed", "historical_api_snapshots_changed",
                     "upstream_permissive_allowlists_changed"):
            self.assertIs(self.record[flag], False)
        requirements = " ".join(self.record["verification_requirements"])
        self.assertIn("unfiltered sepolicy-analyze permissive", requirements)
        self.assertIn("require empty output", requirements)
        self.assertIn("factory vendor/ODM compatibility", requirements)
        self.assertNotIn("device_tested", self.record)


if __name__ == "__main__":
    unittest.main()
