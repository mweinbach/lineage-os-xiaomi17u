"""The QTI value-add framework flag fragment: selector rules and the single system property."""
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import rom_construction_source as source  # noqa: E402

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


CANDIDATES = (b"# Explicit September 6 successor candidates; native/device qualification remains pending.\n"
              b"NEZHA_CALIBRATED_DISPLAY := true\nNEZHA_DOLBY_CONTROLLER := true\nNEZHA_HAPTICS_CONTROLS := true\n"
              b"NEZHA_CAMERA_TASK_PROFILES := true\nNEZHA_REFRESH_POLICY := true\nNEZHA_WORKLOAD_CLASSIFIER := false\n\n")


class SelectionTests(unittest.TestCase):
    """The guest source transaction: fragment install, device.mk include and product selector, each pinned."""

    def test_device_derivation_adds_only_the_include(self):
        raw = (ROOT / source.CAMERA_FRAMEWORK_DEVICE_SNAPSHOT).read_bytes()
        self.assertEqual(source.metadata.identity(raw), source.CAMERA_FRAMEWORK_DEVICE_BEFORE)
        derived = source.derive_camera_framework_device(raw)
        self.assertEqual(source.metadata.identity(derived), source.CAMERA_FRAMEWORK_DEVICE_AFTER)
        # Later independent fragments do not change the historical QTI derivation.
        _camera_include = (b"# Ported HyperOS camera framework (native libs, configs, app, properties).\n"
                           b"include $(NEZHA_DEVICE_PATH)/camera-framework.mk\n\n")
        _session_include = (b"# Native camera session tags for the retained HyperOS HAL; explicit opt-in.\n"
                            b"include $(NEZHA_DEVICE_PATH)/camera-session-inject.mk\n\n")
        current = (ROOT / source.CAMERA_FRAMEWORK_DEVICE).read_bytes()
        self.assertEqual(derived, current.replace(_camera_include, b"", 1).replace(_session_include, b"", 1))
        anchor = source.CAMERA_FRAMEWORK_DEVICE_ANCHOR.encode("ascii")
        self.assertEqual(derived, raw.replace(anchor, anchor + source.CAMERA_FRAMEWORK_DEVICE_INCLUDE.encode("ascii"), 1))
        for changed in (raw + b"\n", derived, raw.replace(anchor, anchor * 2, 1)):
            with self.subTest(size=len(changed)), self.assertRaises(source.ConstructionSourceError):
                source.derive_camera_framework_device(changed)

    def test_product_derivation_enables_only_the_selector(self):
        tracked = (ROOT / source.CAMERA_FRAMEWORK_PRODUCT).read_bytes()
        anchor = source.PRODUCT_SELECTION_ANCHOR.encode("ascii")
        self.assertEqual(tracked.count(anchor), 1)
        restored = tracked.replace(anchor, CANDIDATES + anchor, 1)
        self.assertEqual(source.metadata.identity(restored), source.CAMERA_FRAMEWORK_PRODUCT_BEFORE)
        derived = source.derive_camera_framework_product(restored)
        self.assertEqual(source.metadata.identity(derived), source.CAMERA_FRAMEWORK_PRODUCT_AFTER)
        product_anchor = source.CAMERA_FRAMEWORK_PRODUCT_ANCHOR.encode("ascii")
        self.assertEqual(derived, restored.replace(product_anchor, product_anchor + source.CAMERA_FRAMEWORK_PRODUCT_ASSIGNMENT.encode("ascii"), 1))
        self.assertEqual(derived.count(b"NEZHA_QTI_VALUE_ADD_FRAMEWORK"), 1)
        self.assertLess(derived.index(b"NEZHA_QTI_VALUE_ADD_FRAMEWORK := true"), derived.index(anchor))
        for changed in (restored + b"\n", derived, tracked, restored.replace(product_anchor, product_anchor * 2, 1)):
            with self.subTest(size=len(changed)), self.assertRaises(source.ConstructionSourceError):
                source.derive_camera_framework_product(changed)

    def test_contract_pins_the_fragment_and_both_derivations(self):
        contract, identity = source.load_camera_framework_contract()
        self.assertEqual(identity, source.CAMERA_FRAMEWORK_CONTRACT_ID)
        self.assertEqual(source.render_camera_framework_fragment(), FRAGMENT.read_bytes())
        self.assertEqual(contract["source_selection"]["fragment"]["path"], source.CAMERA_FRAMEWORK_FRAGMENT)
        self.assertEqual(contract["runtime_evidence_20260907"]["control"]["selected_xml"], "kaanapali_gsi.xml")
        self.assertEqual(contract["runtime_evidence_20260907"]["with_flag"]["selected_xml"], "nezha.xml")
        with self.assertRaises(source.ConstructionSourceError):
            source.load_camera_framework_contract(ROOT / "config/nezha-rom-construction-variant-opt-in-v1.json")

    def test_derived_product_selects_the_property_under_host_make(self):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        tracked = (ROOT / source.CAMERA_FRAMEWORK_PRODUCT).read_bytes()
        anchor = source.PRODUCT_SELECTION_ANCHOR.encode("ascii")
        derived = source.derive_camera_framework_product(tracked.replace(anchor, CANDIDATES + anchor, 1))
        # only the candidate block matters here; the inherit-product calls need the full tree
        block = derived[derived.index(b"# Explicit September 6"):derived.index(anchor)].decode("ascii")
        makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n{block}"
                    f"include {ROOT}/device/xiaomi/nezha/qti-value-add-framework.mk\n"
                    "all:\n\t@echo [$(PRODUCT_SYSTEM_PROPERTIES)]\n")
        run = subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile, capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.strip(), "[ro.vendor.qti.va_aosp.support=1]")


if __name__ == "__main__":
    unittest.main()
