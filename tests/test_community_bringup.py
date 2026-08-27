"""Offline checks keeping community reports separate from our hardware proof."""

import json
from pathlib import Path
import unittest
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]


class CommunityBringupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/community-bringup.json").read_text())

    def test_private_source_and_binary_release_are_not_an_active_product(self):
        source = self.record["source_availability"]
        for flag in ("device_tree_public", "kernel_link_proves_exact_nezha_build_inputs",
                     "complete_reproducible_source_manifest_obtained", "camera_port_source_obtained"):
            self.assertFalse(source[flag])
        release = self.record["successor_release"]
        for flag in ("archive_downloaded", "archive_hash_verified", "archive_inspected",
                     "tested_on_this_phone", "adopted_as_evolution_source"):
            self.assertFalse(release[flag])
        config = json.loads((ROOT / "config/sources.json").read_text())
        self.assertFalse(config["device"]["build_ready"])
        self.assertIsNone(config["device"]["lunch_target"])

    def test_firmware_and_reported_features_retain_their_boundaries(self):
        baselines = self.record["firmware_baselines"]
        self.assertNotEqual(baselines["release_requires"], baselines["this_workspace_observed_label"])
        self.assertFalse(baselines["equivalence_established"])
        self.assertFalse(baselines["extra_global_modem_attachment_applicable_to_cn_device"])
        self.assertFalse(baselines["firmware_change_authorized_or_performed"])
        for feature in self.record["reported_feature_leads"]:
            self.assertEqual(feature["status"], "maintainer_report_only")
            self.assertFalse(feature["evolution_device_tested"])
            uri = urlparse(feature["source"])
            self.assertEqual(uri.scheme, "https")
            self.assertEqual(uri.hostname, "xdaforums.com")
            self.assertTrue(uri.fragment.startswith("post-"))

    def test_no_device_actions_or_outreach_are_recorded(self):
        self.assertTrue(all(value is False for value in self.record["safety"].values()))
        receipt = self.record["private_receipt"]
        self.assertTrue(receipt["path"].startswith("reports/"))
        self.assertRegex(receipt["sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
