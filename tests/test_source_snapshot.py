"""Offline consistency checks for the completed, inactive platform snapshot."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class SourceSnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/source-sync.json").read_text())
        cls.config = json.loads((ROOT / "config/sources.json").read_text())
        cls.snapshot = ROOT / cls.record["resolved_manifest"]["path"]
        cls.data = cls.snapshot.read_bytes()
        cls.manifest = ET.fromstring(cls.data)
        cls.projects = cls.manifest.findall("project")

    def test_snapshot_is_exact_and_outside_active_device_manifests(self):
        recorded = self.record["resolved_manifest"]
        self.assertTrue(self.snapshot.is_relative_to(ROOT / "research/source-snapshots"))
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), recorded["sha256"])
        self.assertEqual(len(self.data), recorded["bytes"])
        self.assertEqual(len(self.projects), recorded["project_count"])
        self.assertFalse((ROOT / "manifests/local_manifest.xml").exists())

    def test_all_project_revisions_are_full_commits_with_unique_safe_paths(self):
        paths = []
        for project in self.projects:
            self.assertRegex(project.get("revision"), r"^[0-9a-f]{40}$")
            path = PurePosixPath(project.get("path", project.get("name")))
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            paths.append(str(path))
        self.assertEqual(len(paths), len(set(paths)))
        self.assertNotIn("device/xiaomi/nezha", paths)
        self.assertNotIn("vendor/xiaomi/nezha", paths)

    def test_every_used_remote_is_public_https_without_credentials(self):
        remotes = {node.get("name"): node.attrib for node in self.manifest.findall("remote")}
        default = self.manifest.find("default").get("remote")
        origin = next(ref["url"] for ref in self.config["references"] if ref["name"] == "evolution-manifest")
        for project in self.projects:
            remote_name = project.get("remote", default)
            self.assertNotEqual(remote_name, "private")
            base = urljoin(origin, remotes[remote_name]["fetch"].rstrip("/") + "/")
            uri = urlparse(base + project.get("name"))
            self.assertEqual(uri.scheme, "https")
            self.assertIn(uri.netloc, {"github.com", "android.googlesource.com"})
            self.assertFalse(uri.username or uri.password or uri.query or uri.fragment)

    def test_manifest_repo_and_vendor_pins_match_configuration(self):
        refs = {ref["name"]: ref for ref in self.config["references"]}
        self.assertEqual(self.record["platform"]["manifest_commit"], refs["evolution-manifest"]["commit"])
        self.assertEqual(self.record["platform"]["repo_commit"], refs["repo-tool"]["commit"])
        vendor = next(project for project in self.projects if project.get("path") == "vendor/lineage")
        self.assertEqual(vendor.get("revision"), refs["evolution-vendor"]["commit"])
        self.assertEqual(vendor.get("revision"), self.record["evolution_vendor"]["head"])

    def test_completion_counts_and_claim_limits_are_consistent(self):
        self.assertEqual(self.record["sync"]["status"], "complete")
        self.assertEqual(self.record["sync"]["exit_code"], 0)
        self.assertFalse(self.record["sync"]["second_sync_started"])
        verified = self.record["checkout_verification"]
        for field in ("project_count", "head_match_count", "clean_project_count", "origin_match_count"):
            self.assertEqual(verified[field], len(self.projects))
        self.assertEqual(sum(self.record["remote_project_counts"].values()), len(self.projects))
        self.assertTrue(self.record["lfs_verification"]["all_content_hashes_match_lfs_oids"])
        self.assertFalse(self.record["device_target_registered"])
        self.assertFalse(self.record["full_android_build_verified"])
        self.assertFalse(self.record["hardware_features_tested_on_evolution"])
        for receipt in self.record["private_receipts"].values():
            self.assertTrue(receipt["host_path"].startswith("reports/"))
            self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}", receipt["sha256"]))


if __name__ == "__main__":
    unittest.main()
