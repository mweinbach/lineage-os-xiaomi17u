"""The QTI value-add framework flag fragment: selector rules and the single system property."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/qti-value-add-framework.mk"
CONTRACT = ROOT / "config/nezha-qti-value-add-framework.json"


class FragmentTests(unittest.TestCase):
    def test_contract_names_the_fragment_property_and_selector(self):
        contract = json.loads(CONTRACT.read_text())
        make = FRAGMENT.read_text()
        self.assertEqual(contract["fragment"], str(FRAGMENT.relative_to(ROOT)))
        self.assertIn(contract["selector"], make)
        self.assertIn(f'{contract["property"]["name"]}={contract["property"]["value"]}', make)
        self.assertEqual(contract["property"]["product_variable"], "PRODUCT_SYSTEM_PROPERTIES")
        # The flag belongs to the system image, as in the factory build; never to the retained vendor or ODM images.
        for forbidden in ("PRODUCT_VENDOR_PROPERTIES", "PRODUCT_ODM_PROPERTIES", "PRODUCT_PROPERTY_OVERRIDES", "setprop"):
            self.assertNotIn(forbidden, make)
        self.assertIn("include $(NEZHA_DEVICE_PATH)/qti-value-add-framework.mk", (ROOT / "device/xiaomi/nezha/device.mk").read_text())

    def test_make_selector_emits_the_property_only_when_true(self):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        for flag, expected_ok, expected_property in (("", True, False), ("false", True, False), ("true", True, True),
                                                     ("yes", False, False), ("true false", False, False), ("true true", False, False)):
            with self.subTest(flag=flag):
                makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                            f"NEZHA_QTI_VALUE_ADD_FRAMEWORK := {flag}\n"
                            f"include {ROOT}/device/xiaomi/nezha/qti-value-add-framework.mk\n"
                            "all:\n\t@echo [$(PRODUCT_SYSTEM_PROPERTIES)]\n")
                run = subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile, capture_output=True, text=True,
                                     env={"PATH": "/usr/bin:/bin"})
                self.assertEqual(run.returncode == 0, expected_ok, run.stderr)
                if expected_ok:
                    self.assertEqual("ro.vendor.qti.va_aosp.support=1" in run.stdout, expected_property, run.stdout)
                    if not expected_property:
                        self.assertEqual(run.stdout.strip(), "[]")


if __name__ == "__main__":
    unittest.main()
