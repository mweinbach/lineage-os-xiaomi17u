"""The Leica Essential enablement fragment: selector rules, the two properties, and the contract/doc it records."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/leica-essential.mk"
CONTRACT = ROOT / "config/nezha-leica-essential.json"
DEVICE = ROOT / "device/xiaomi/nezha/device.mk"
RECORD = ROOT / "research/leica-essential-20260910.json"


class FragmentTests(unittest.TestCase):
    def test_contract_names_the_fragment_selector_and_two_properties(self):
        contract = json.loads(CONTRACT.read_text())
        make = FRAGMENT.read_text()
        self.assertEqual(contract["fragment"], str(FRAGMENT.relative_to(ROOT)))
        self.assertIn(contract["selector"], make)
        names = {p["name"]: p["value"] for p in contract["properties"]}
        self.assertEqual(names, {"ro.theme_customize": "LCC", "camera.debug.safe.check.disable": "true"})
        for name, value in names.items():
            self.assertIn(f"{name}={value}", make)
            self.assertEqual([p for p in contract["properties"] if p["name"] == name][0]["product_variable"], "PRODUCT_SYSTEM_PROPERTIES")
        # runtime-only mechanisms must not leak into the build fragment
        for forbidden in ("setprop", "resetprop", "PRODUCT_PROPERTY_OVERRIDES", "PRODUCT_VENDOR_PROPERTIES", "PRODUCT_ODM_PROPERTIES"):
            self.assertNotIn(forbidden, make)
        self.assertIn("include $(NEZHA_DEVICE_PATH)/leica-essential.mk", DEVICE.read_text())

    def test_contract_records_the_gate_and_local_models(self):
        contract = json.loads(CONTRACT.read_text())
        gate = contract["gate_mechanism"]
        self.assertIn("RitIeKoenwCSqcPf", gate["security_check"])
        self.assertIn("camera.debug.safe.check.disable", gate["security_check"])
        self.assertIn("ro.theme_customize==LCC", gate["support_check"])
        self.assertTrue(any("styletrans" in f for f in contract["device_files_present"]))
        self.assertFalse(contract["measured_on_v16"]["after_minimal"].startswith("With no"))
        self.assertIn("2512BPNDAC", contract["measured_on_v16"]["after_minimal"])

    def test_generator_lists_the_fragment(self):
        sys.path.insert(0, str(ROOT))
        from scripts import generate_device_tree as generator
        self.assertEqual(generator.TEMPLATE_FILES.count("leica-essential.mk"), 1)

    def test_record_and_index_name_the_document(self):
        record = json.loads(RECORD.read_text())
        self.assertEqual(record["module_id"], 256)
        self.assertFalse(record["measured"]["identity_spoof_needed"])
        self.assertEqual(sorted(record["properties"]), ["camera.debug.safe.check.disable=true", "ro.theme_customize=LCC"])
        page = (ROOT / record["document"]).read_text()
        self.assertIn("camera.debug.safe.check.disable", page)
        self.assertIn(Path(record["document"]).name, (ROOT / "docs/README.md").read_text())

    def test_make_selector_emits_both_properties_only_when_true(self):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        for flag, expected_ok, expected_property in (("", True, False), ("false", True, False), ("true", True, True),
                                                     ("yes", False, False), ("true false", False, False)):
            with self.subTest(flag=flag):
                makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                            f"NEZHA_LEICA_ESSENTIAL := {flag}\n"
                            f"include {FRAGMENT}\n"
                            "all:\n\t@echo [$(PRODUCT_SYSTEM_PROPERTIES)]\n")
                run = subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile, capture_output=True, text=True,
                                     env={"PATH": "/usr/bin:/bin"})
                self.assertEqual(run.returncode == 0, expected_ok, run.stderr)
                if expected_ok:
                    self.assertEqual("ro.theme_customize=LCC" in run.stdout, expected_property, run.stdout)
                    self.assertEqual("camera.debug.safe.check.disable=true" in run.stdout, expected_property, run.stdout)

    def test_selector_refuses_to_double_own_the_properties(self):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                    "PRODUCT_SYSTEM_PROPERTIES := ro.theme_customize=LCC\n"
                    "NEZHA_LEICA_ESSENTIAL := true\n"
                    f"include {FRAGMENT}\n"
                    "all:\n\t@echo ok\n")
        run = subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile, capture_output=True, text=True,
                             env={"PATH": "/usr/bin:/bin"})
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("exclusive ownership", run.stderr)


if __name__ == "__main__":
    unittest.main()
