"""Validate the portable TWRP source lock, without accessing a guest or network."""

import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class TwrpSourceSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/twrp-source-sync.json").read_text())
        cls.config = json.loads((ROOT / "config/twrp.json").read_text())
        cls.raw = (ROOT / cls.record["snapshot"]["path"]).read_bytes()
        cls.tree = ET.fromstring(cls.raw)
        cls.projects = {node.get("path", node.get("name")): node for node in cls.tree.findall("project")}

    def test_snapshot_hash_matches_the_successful_freeze_record(self):
        snapshot = self.record["snapshot"]
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), snapshot["sha256"])
        self.assertEqual(len(self.raw), snapshot["size_bytes"])
        self.assertEqual(self.record["manifest"], self.config["manifest"])
        self.assertEqual(self.record["project_selection"], self.config["project_selection"])

    def test_every_selected_project_has_one_full_commit(self):
        self.assertEqual(len(self.projects), 391)
        self.assertEqual(len(self.tree.findall("project")), len(self.projects))
        self.assertNotIn("prebuilts/bazel/darwin-x86_64", self.projects)
        for name, project in self.projects.items():
            with self.subTest(project=name):
                self.assertRegex(project.get("revision"), r"^[0-9a-f]{40}$")
                self.assertFalse(Path(name).is_absolute())
                self.assertNotIn("..", Path(name).parts)

    def test_all_reviewed_fork_commits_survive_the_full_sync(self):
        upstream = json.loads((ROOT / "research/twrp-upstream.json").read_text())
        for project in upstream["pinned_projects"]:
            self.assertEqual(self.projects[project["path"]].get("revision"), project["commit"])
        self.assertEqual(self.record["verification"]["reviewed_github_heads"], 36)
        self.assertEqual(self.record["verification"]["aosp_tag_commits_verified"], 355)

    def test_frozen_tree_is_complete_but_not_a_build_or_phone_result(self):
        verified = self.record["verification"]
        self.assertEqual(verified["selected_projects"], 391)
        self.assertTrue(verified["all_present"])
        self.assertTrue(verified["all_heads_origins_and_clean_worktrees_verified"])
        self.assertEqual(verified["failures"], [])
        for key in ("repo_signature_checks_disabled", "source_build_proven_by_sync",
                    "hardware_validation_performed"):
            self.assertFalse(verified[key])

    def test_environment_and_tool_probes_are_explicitly_limited(self):
        host = self.record["host_preflight"]
        self.assertEqual(host["host_mode"], "apple-rosetta")
        self.assertEqual(host["os"], "Linux")
        self.assertTrue(host["supported_build_host"])
        self.assertEqual(set(host["filesystems"].values()), {"ext4"})
        self.assertTrue(all(row["exit_code"] == 0 for row in self.record["host_tool_version_smoke"]["checks"]))
        execution = self.record["execution"]
        for key in ("new_writer_vm_attached", "evolution_source_mutation_commands_run",
                    "host_phone_evidence_or_credentials_mounted"):
            self.assertFalse(execution[key])
        self.assertEqual(execution["source_dir"], "/work/twrp-nezha")


if __name__ == "__main__":
    unittest.main()
