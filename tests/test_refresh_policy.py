"""Offline refresh source selection and deliberately bounded snapshot claims."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from scripts import refresh_policy as refresh

ROOT = Path(__file__).resolve().parents[1]
DUMP = b"""DisplayDeviceInfo{ fps=120.00001, fps=60.000004, fps=30.000002, fps=24.000002 }
mDefaultPeakRefreshRate: 240.0
mDefaultRefreshRate: 120.0
mDisplayModeSpecs={primary=physical: (60.0 240.0) render: (60.0 120.0) idleScreenRefreshRateConfig=null}
PRIORITY_USER_SETTING_MIN_RENDER_FRAME_RATE -> RenderVote{ mMinRefreshRate=60.0 }
PRIORITY_LOW_POWER_MODE -> RenderVote{ mMaxRefreshRate=60.0 }
renderFrameRate 60.000004
"""


class SourceTests(unittest.TestCase):
    def test_reviewed_resources_and_no_hardware_claim(self):
        report = refresh.verify_source(ROOT)
        self.assertEqual(report["resources"], refresh.RESOURCES)
        self.assertFalse(report["hardware_behavior_verified"])
        self.assertFalse(report["native_overlay_precedence_verified"])

    def test_modified_missing_and_duplicate_resources_rejected(self):
        raw = (ROOT / refresh.OVERLAY).read_text()
        for change in (raw.replace(">120<", ">24<", 1), raw.replace("</resources>",
                '<integer name="config_defaultPeakRefreshRate">120</integer></resources>'),
                "<resources/>"):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / refresh.OVERLAY).parent.mkdir(parents=True)
                (root / refresh.OVERLAY).write_text(change)
                (root / "config").mkdir()
                shutil.copyfile(ROOT / "config/nezha-refresh-policy.json", root / "config/nezha-refresh-policy.json")
                with self.assertRaises(ValueError):
                    refresh.verify_source(root)

    def test_make_selector_and_required_overlay(self):
        for flag, expected in (("", True), ("false", True), ("true", True),
                               ("yes", False), ("true false", False), ("true true", False)):
            with self.subTest(flag=flag):
                makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                            f"NEZHA_REFRESH_POLICY := {flag}\n"
                            f"include {ROOT}/device/xiaomi/nezha/refresh-policy.mk\n"
                            "all:\n\t@echo $(DEVICE_PACKAGE_OVERLAYS)\n")
                run = subprocess.run(["make", "--no-print-directory", "-f", "-"],
                                     input=makefile, capture_output=True, text=True)
                self.assertEqual(run.returncode == 0, expected, run.stderr)
                if expected:
                    self.assertEqual("refresh-overlay" in run.stdout, flag == "true")
        missing = ("NEZHA_DEVICE_PATH := /missing-nezha-fixture\nNEZHA_REFRESH_POLICY := true\n"
                   f"include {ROOT}/device/xiaomi/nezha/refresh-policy.mk\nall:\n\t@true\n")
        run = subprocess.run(["make", "--no-print-directory", "-f", "-"],
                             input=missing, capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("requires its framework resource overlay", run.stderr)

    def test_no_settings_writes_or_unqualified_policy(self):
        make = (ROOT / "device/xiaomi/nezha/refresh-policy.mk").read_text()
        for forbidden in ("PRODUCT_VENDOR_PROPERTIES", "PRODUCT_SYSTEM_PROPERTIES", "settings put", "setprop", "thermal"):
            self.assertNotIn(forbidden, make)
        resources = (ROOT / refresh.OVERLAY).read_text()
        for forbidden in ("config_defaultMinRefreshRate", "integer-array", "config_defaultRefreshRateInZone"):
            self.assertNotIn(forbidden, resources)


class SnapshotTests(unittest.TestCase):
    def test_reports_mode_advertisements_and_preserves_vote_origin_uncertainty(self):
        report = refresh.analyze_display(DUMP)
        self.assertEqual(report["advertised_physical_hz"], [24, 30, 60, 120])
        self.assertEqual(report["minimum_render_votes_hz"], [60])
        self.assertIn("fallback", report["minimum_vote_origin"])
        self.assertTrue(report["default_peak_exceeds_advertised_maximum"])
        self.assertTrue(report["idle_config_null_observed"])
        self.assertFalse(report["candidate_defaults_observed"])
        self.assertFalse(report["physical_transitions_verified"])
        self.assertFalse(report["battery_improvement_measured"])
        self.assertEqual(len(report["rate_votes"]), 2)

    def test_matching_defaults_not_a_behavior_pass(self):
        report = refresh.analyze_display(DUMP.replace(b"mDefaultPeakRefreshRate: 240", b"mDefaultPeakRefreshRate: 120"))
        self.assertTrue(report["candidate_defaults_observed"])
        self.assertFalse(report["surfaceflinger_timer_state_verified"])

    def test_missing_or_ambiguous_snapshot_rejected(self):
        for raw in (b"", DUMP.replace(b"fps=", b"rate="),
                    DUMP + b"\nmDefaultPeakRefreshRate: 120\n"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                refresh.analyze_display(raw)

    def test_bounded_regular_file_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dump").write_bytes(DUMP)
            (root / "link").symlink_to(root / "dump")
            with self.assertRaises(ValueError):
                refresh.read(root / "link")


if __name__ == "__main__":
    unittest.main()
