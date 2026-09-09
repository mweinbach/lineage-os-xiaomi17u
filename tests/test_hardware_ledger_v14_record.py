"""Recompute the tier 0 ledger record from its rows and check it carries no private identifiers."""

import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "research/hardware-ledger-v14-20260909.json"
CONTRACT = ROOT / "config/nezha-hardware-qualification.json"
PRIVATE = (
    re.compile(r"\b(?=[0-9a-f]{8}\b)(?=[0-9]*[a-f])[0-9a-f]{8}\b"),  # short hex device serials, not dates
    re.compile(r"\b\d{15}\b"),                             # IMEI
    re.compile(r"(?:[0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}"),   # MAC or BSSID
    re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"),  # IPv4
    re.compile(r"\b4[01]\.\d{5,}\b"),                     # the session's latitude family
    re.compile(r"The WiFi Network|iccid|imsi", re.I),
)


class HardwareLedgerRecordTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(RECORD.read_text())
        cls.contract = json.loads(CONTRACT.read_text())

    def test_counts_recompute_and_ids_match_the_contract(self):
        checks = self.record["ledger"]["checks"]
        counts = {state: sum(row["status"] == state for row in checks) for state in ("pass", "fail", "not-run")}
        self.assertEqual(counts, self.record["ledger"]["counts"])
        self.assertEqual([row["id"] for row in checks], [item["id"] for item in self.contract["checks"]])
        self.assertEqual(sum(counts.values()), len(self.contract["checks"]))
        for row in checks:
            with self.subTest(check=row["id"]):
                self.assertEqual(row["evidence_files"] > 0, row["status"] != "not-run")

    def test_hands_on_list_covers_every_unrun_check(self):
        unrun = {row["id"] for row in self.record["ledger"]["checks"] if row["status"] == "not-run"}
        listed = set()
        for group in self.record["hands_on_remaining"].values():
            for item in group:
                listed.add(item.split(" ")[0])
        self.assertEqual(unrun, listed)

    def test_measurements_are_internally_consistent(self):
        display = self.record["measurements"]["display"]
        clone = display["brightness_clone"]
        self.assertEqual(len(clone), len(display["sweep_settings"]))
        self.assertEqual(all(a < b for a, b in zip(clone, clone[1:])), display["strictly_monotonic"])
        self.assertLessEqual(max(clone) / display["clone_max"], display["normal_range_backlight_fraction"] + 0.001)
        thermal = self.record["measurements"]["thermal_load"]
        self.assertLess(thermal["baseline_max_cpu_zone_c"], thermal["peak_max_cpu_zone_c"])
        self.assertLess(thermal["recovery_45s_max_cpu_zone_c"], thermal["peak_max_cpu_zone_c"])
        self.assertEqual(thermal["thermal_status_max"], 0)
        changes = self.record["device_state_changes"]
        self.assertTrue(changes["restored_equals_baseline"])
        self.assertFalse(any(changes[key] for key in ("reboot", "flash", "install", "wipe")))

    def test_record_and_page_carry_no_private_identifiers(self):
        texts = {"record": RECORD.read_text(), "page": (ROOT / "docs/hardware-ledger-v14-20260909.md").read_text()}
        for name, text in texts.items():
            for pattern in PRIVATE:
                with self.subTest(source=name, pattern=pattern.pattern):
                    self.assertIsNone(pattern.search(text))

    def test_status_page_and_index_name_the_record(self):
        self.assertIn("hardware-ledger-v14-20260909.md", (ROOT / "docs/workspace-status.md").read_text())
        self.assertIn("hardware-ledger-v14-20260909.md", (ROOT / "docs/README.md").read_text())


if __name__ == "__main__":
    unittest.main()
