"""Check local documentation links and sanitized baseline invariants."""

import json
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]


class DocumentationTests(unittest.TestCase):
    def test_relative_documentation_links_exist(self):
        documents = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
        for document in documents:
            for target in re.findall(r"\]\(([^\s)]+)\)", document.read_text()):
                parsed = urlsplit(target)
                if parsed.scheme or parsed.netloc or not parsed.path:
                    continue
                with self.subTest(document=document.name, target=target):
                    self.assertTrue((document.parent / unquote(parsed.path)).exists())

    def test_sanitized_baseline_retains_provenance_and_known_gaps(self):
        baseline = json.loads((ROOT / "research/device-baseline.json").read_text())
        self.assertEqual(baseline["device"]["codename"], "nezha")
        self.assertEqual(baseline["device"]["reported_hwc"], "CN")
        self.assertEqual(baseline["firmware"]["page_size_bytes"], 4096)
        self.assertEqual(baseline["collection"]["status"], "partial")
        self.assertEqual(len(baseline["collection"]["unavailable_reads"]), 3)
        self.assertEqual(baseline["evolution_x_hardware_testing"], "not performed")
        self.assertIn("unverified", baseline["boot_state"]["actual_bootloader_state"])
        self.assertRegex(baseline["collection"]["camera_apk_sha256"], r"^[a-f0-9]{64}$")

    def test_sanitized_baseline_does_not_contain_personal_identifier_fields(self):
        baseline = json.loads((ROOT / "research/device-baseline.json").read_text())
        forbidden = {"serial", "serialno", "imei", "imsi", "meid", "account", "email", "phone_number"}

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for child in value.values():
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)

        check(baseline)


if __name__ == "__main__":
    unittest.main()
