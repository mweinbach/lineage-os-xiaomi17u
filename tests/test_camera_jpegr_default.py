"""Exercise the opt-in JPEG_R property default without private inputs or a phone."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/camera-jpegr-default.mk"
PROPERTY = "persist.vendor.camera.sdk.third.jpegr.enable=1"
OUTPUT_VARIABLES = (
    "PRODUCT_SYSTEM_PROPERTIES",
    "PRODUCT_VENDOR_PROPERTIES",
    "PRODUCT_ODM_PROPERTIES",
    "PRODUCT_COPY_FILES",
    "PRODUCT_PACKAGES",
    "LOCAL_INIT_RC",
)
PRESERVED_OUTPUTS = {
    "PRODUCT_SYSTEM_PROPERTIES": ["ro.nezha.test=kept", "persist.nezha.test=kept"],
    "PRODUCT_VENDOR_PROPERTIES": ["vendor.nezha.test=kept"],
    "PRODUCT_ODM_PROPERTIES": ["odm.nezha.test=kept"],
    "PRODUCT_COPY_FILES": ["preserved/source:preserved/destination"],
    "PRODUCT_PACKAGES": ["PreservedPackage"],
    "LOCAL_INIT_RC": ["preserved-init.rc"],
}


class CameraJpegRDefaultTests(unittest.TestCase):
    def test_contract_hash_recomputes_from_fragment(self):
        contract = json.loads((ROOT / "config/nezha-camera-jpegr-default.json").read_text())
        self.assertEqual(ROOT / contract["fragment"], FRAGMENT)
        self.assertEqual(hashlib.sha256(FRAGMENT.read_bytes()).hexdigest(),
                         contract["fragment_sha256"])
        # Pin the measured vendor switch and its placement: this must not turn
        # into a different camera capability, vendor-image change, or init hook.
        self.assertEqual(contract["property_variable"], "PRODUCT_SYSTEM_PROPERTIES")
        self.assertEqual(contract["properties"], [PROPERTY])

    def run_fragment(self, selector, framework, existing=None):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        assignments = []
        for name, value in (("NEZHA_CAMERA_JPEGR_DEFAULT", selector),
                            ("NEZHA_CAMERA_FRAMEWORK", framework)):
            if value is not None:
                assignments.append(f"{name} := {value}\n")
        for name, values in (existing or {}).items():
            assignments.append(f"{name} := {' '.join(values)}\n")
        script = "".join(assignments) + f"include {FRAGMENT}\nall:\n"
        for name in OUTPUT_VARIABLES:
            script += f"\t@printf '%s\\n' '{name}=$({name})'\n"
        return subprocess.run([make, "--no-print-directory", "-f", "-"],
                              input=script, text=True, capture_output=True,
                              timeout=10, env={"PATH": "/usr/bin:/bin"})

    def assert_outputs(self, result, expected):
        self.assertEqual(result.returncode, 0, result.stderr)
        outputs = {}
        for line in result.stdout.splitlines():
            name, separator, value = line.partition("=")
            self.assertEqual(separator, "=", result.stdout)
            self.assertNotIn(name, outputs, result.stdout)
            outputs[name] = value.split()
        self.assertEqual(outputs, {name: expected.get(name, [])
                                   for name in OUTPUT_VARIABLES})

    def test_unselected_default_emits_no_output(self):
        for selector in (None, "", " ", "false", " false "):
            for framework in (None, "", "false", "true"):
                with self.subTest(selector=selector, framework=framework):
                    self.assert_outputs(self.run_fragment(selector, framework), {})

    def test_unselected_default_preserves_existing_outputs(self):
        for selector in (None, "false"):
            with self.subTest(selector=selector):
                result = self.run_fragment(selector, "true", PRESERVED_OUTPUTS)
                self.assert_outputs(result, PRESERVED_OUTPUTS)

    def test_enabled_default_adds_only_the_exact_system_property(self):
        for selector, framework in (("true", "true"), (" true ", " true ")):
            with self.subTest(selector=selector, framework=framework):
                result = self.run_fragment(selector, framework)
                self.assert_outputs(result, {"PRODUCT_SYSTEM_PROPERTIES": [PROPERTY]})

    def test_enabled_default_appends_and_preserves_other_outputs(self):
        result = self.run_fragment("true", "true", PRESERVED_OUTPUTS)
        expected = {name: list(values) for name, values in PRESERVED_OUTPUTS.items()}
        expected["PRODUCT_SYSTEM_PROPERTIES"].append(PROPERTY)
        self.assert_outputs(result, expected)

    def test_malformed_or_multiple_selector_values_fail(self):
        for selector in ("yes", "1", "0", "TRUE", "False", "true true",
                         "true false", "false false", "true\ttrue"):
            with self.subTest(selector=selector):
                result = self.run_fragment(selector, "true")
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NEZHA_CAMERA_JPEGR_DEFAULT", result.stderr)
                self.assertEqual(result.stdout.strip(), "")

    def test_enabled_default_requires_framework_true(self):
        for framework in (None, "", " ", "false", "yes", "TRUE",
                          "true true", "true false"):
            with self.subTest(framework=framework):
                result = self.run_fragment("true", framework)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NEZHA_CAMERA_FRAMEWORK=true", result.stderr)
                self.assertEqual(result.stdout.strip(), "")


if __name__ == "__main__":
    unittest.main()
