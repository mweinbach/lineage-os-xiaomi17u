"""The camcorder profile selection fragment: selector rules and the single factory system property."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/camera-video-profiles.mk"
CONTRACT = ROOT / "config/nezha-camera-video-profiles.json"
DEVICE = ROOT / "device/xiaomi/nezha/device.mk"


class FragmentTests(unittest.TestCase):
    def test_contract_names_the_fragment_property_and_selector(self):
        contract = json.loads(CONTRACT.read_text())
        make = FRAGMENT.read_text()
        self.assertEqual(contract["fragment"], str(FRAGMENT.relative_to(ROOT)))
        self.assertIn(contract["selector"], make)
        self.assertIn(f'{contract["property"]["name"]}={contract["property"]["value"]}', make)
        self.assertEqual(contract["property"]["product_variable"], "PRODUCT_SYSTEM_PROPERTIES")
        # The stock key lives in the system image; it is never pushed into the retained vendor or ODM images.
        for forbidden in ("PRODUCT_VENDOR_PROPERTIES", "PRODUCT_ODM_PROPERTIES", "PRODUCT_PROPERTY_OVERRIDES", "setprop"):
            self.assertNotIn(forbidden, make)
        assignments = [line for line in make.splitlines()
                       if line.strip() == "media.settings.xml=/vendor/etc/media_profiles_vendor.xml"]
        self.assertEqual(len(assignments), 1)
        self.assertIn("include $(NEZHA_DEVICE_PATH)/camera-video-profiles.mk", DEVICE.read_text())
        stock = contract["stock_evidence"]["factory_system_build_prop"]
        self.assertEqual(stock["text"], f'{contract["property"]["name"]}={contract["property"]["value"]}')
        self.assertEqual(contract["measured_on_v15"]["loaded_table_camera0_highest"], "1920x1080@30")
        self.assertEqual(contract["measured_on_v15"]["media_settings_xml"], "unset")
        for digest in (contract["measured_on_v15"]["loaded_table_sha256"], contract["measured_on_v15"]["factory_table_sha256"]):
            self.assertRegex(digest, r"^[0-9a-f]{64}$")
        self.assertNotEqual(contract["measured_on_v15"]["loaded_table_sha256"], contract["measured_on_v15"]["factory_table_sha256"])

    def test_generator_lists_the_fragment(self):
        sys.path.insert(0, str(ROOT))
        from scripts import generate_device_tree as generator
        self.assertEqual(generator.TEMPLATE_FILES.count("camera-video-profiles.mk"), 1)

    def test_make_selector_emits_the_property_only_when_true(self):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        for flag, expected_ok, expected_property in (("", True, False), ("false", True, False), ("true", True, True),
                                                     ("yes", False, False), ("true false", False, False), ("true true", False, False)):
            with self.subTest(flag=flag):
                makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                            f"NEZHA_CAMERA_VIDEO_PROFILES := {flag}\n"
                            f"include {FRAGMENT}\n"
                            "all:\n\t@echo [$(PRODUCT_SYSTEM_PROPERTIES)]\n")
                run = subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile, capture_output=True, text=True,
                                     env={"PATH": "/usr/bin:/bin"})
                self.assertEqual(run.returncode == 0, expected_ok, run.stderr)
                if expected_ok:
                    self.assertEqual("media.settings.xml=/vendor/etc/media_profiles_vendor.xml" in run.stdout,
                                     expected_property, run.stdout)
                    if not expected_property:
                        self.assertEqual(run.stdout.strip(), "[]")

    def test_selector_refuses_a_second_owner_of_the_key(self):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                    "PRODUCT_SYSTEM_PROPERTIES := media.settings.xml=/system/etc/other.xml\n"
                    "NEZHA_CAMERA_VIDEO_PROFILES := true\n"
                    f"include {FRAGMENT}\nall:\n\t@true\n")
        run = subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile, capture_output=True, text=True,
                             env={"PATH": "/usr/bin:/bin"})
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("exclusive ownership", run.stderr)

    def test_stock_build_prop_pin_matches_the_retained_copy_when_present(self):
        contract = json.loads(CONTRACT.read_text())
        stock = contract["stock_evidence"]["factory_system_build_prop"]
        path = ROOT / stock["path"]
        if not path.exists():
            self.skipTest("factory extract not present on this host")
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), stock["sha256"])
        self.assertEqual(raw.decode().splitlines()[stock["line"] - 1], stock["text"])


if __name__ == "__main__":
    unittest.main()
