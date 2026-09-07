"""The ported camera-framework selection fragment: guard rules and properties, pinned by the contract."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/camera-framework.mk"
CONTRACT = ROOT / "config/nezha-camera-framework.json"


class CameraFrameworkFragmentTests(unittest.TestCase):
    def test_contract_matches_fragment_and_selector(self):
        contract = json.loads(CONTRACT.read_text())
        make = FRAGMENT.read_text()
        self.assertEqual(contract["fragment"], str(FRAGMENT.relative_to(ROOT)))
        self.assertIn(contract["selector"], make)
        self.assertEqual(contract["property_variable"], "PRODUCT_SYSTEM_PROPERTIES")
        for prop in contract["properties"]:
            self.assertIn(prop, make)
        # never place these Xiaomi camera properties on the vendor/odm images or via setprop
        for forbidden in ("PRODUCT_VENDOR_PROPERTIES", "PRODUCT_ODM_PROPERTIES", "setprop"):
            self.assertNotIn(forbidden, make)
        self.assertIn("include $(NEZHA_DEVICE_PATH)/camera-framework.mk",
                      (ROOT / "device/xiaomi/nezha/device.mk").read_text())

    def test_make_selector_emits_properties_only_when_true(self):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        for flag, ok, has in (("", True, False), ("false", True, False), ("true", True, True),
                              ("yes", False, False), ("true false", False, False)):
            with self.subTest(flag=flag):
                makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                            f"NEZHA_CAMERA_FRAMEWORK := {flag}\n"
                            "inherit-product-if-exists = \n"
                            f"include {ROOT}/device/xiaomi/nezha/camera-framework.mk\n"
                            "all:\n\t@echo [$(PRODUCT_SYSTEM_PROPERTIES)]\n")
                run = subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile,
                                     capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
                self.assertEqual(run.returncode == 0, ok, run.stderr)
                if ok:
                    self.assertEqual("vendor.camera.support.mivi=true" in run.stdout, has, run.stdout)


if __name__ == "__main__":
    unittest.main()
