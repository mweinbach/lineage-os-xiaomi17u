"""Exercise the bounded camera-ID allowlist override through real Make."""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/camera-aux-packages.mk"
FACTORY = ("vendor.camera.aux.packagelist=com.xiaomi.runin,com.xiaomi.cameratest,"
           "com.xiaomi.factory.mmi,org.codeaurora.snapcam")
SELECTED = "vendor.camera.aux.packagelist=com.android.camera,org.lineageos.aperture"


class CameraAuxPackageTests(unittest.TestCase):
    def run_make(self, selector, framework="true", properties=FACTORY):
        make = shutil.which("make")
        if not make:
            self.skipTest("GNU Make unavailable")
        script = (f"NEZHA_CAMERA_AUX_PACKAGES := {selector}\n"
                  f"NEZHA_CAMERA_FRAMEWORK := {framework}\n"
                  f"PRODUCT_SYSTEM_PROPERTIES := keep.before=1 {properties} keep.after=2\n"
                  "PRODUCT_VENDOR_PROPERTIES := untouched.vendor=1\n"
                  f"include {FRAGMENT}\n"
                  "all:\n\t@printf '%s\\n' '$(PRODUCT_SYSTEM_PROPERTIES)' '$(PRODUCT_VENDOR_PROPERTIES)'\n")
        return subprocess.run([make, "--no-print-directory", "-f", "-"], input=script,
                              capture_output=True, text=True, timeout=10,
                              env={"PATH": "/usr/bin:/bin"})

    def test_selected_replaces_one_property_and_preserves_the_rest(self):
        run = self.run_make("true")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout.splitlines(),
                         [f"keep.before=1 keep.after=2 {SELECTED}", "untouched.vendor=1"])
        # Android's property value bound is 91 payload bytes plus its terminator.
        self.assertLessEqual(len(SELECTED.split("=", 1)[1].encode()), 91)

    def test_unselected_preserves_even_an_unrelated_property_value(self):
        for selector in ("", "false", " false "):
            for properties in (FACTORY, "vendor.camera.aux.packagelist=another.app", ""):
                with self.subTest(selector=selector, properties=properties):
                    run = self.run_make(selector, "false", properties)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout.splitlines()[0].split(),
                                     ["keep.before=1", *properties.split(), "keep.after=2"])

    def test_bad_selectors_or_missing_framework_fail(self):
        for selector, framework in (("yes", "true"), ("TRUE", "true"),
                                    ("true true", "true"), ("false false", "true"),
                                    ("true false", "true"), ("true", "false"),
                                    ("true", ""), ("true", "true true")):
            with self.subTest(selector=selector, framework=framework):
                run = self.run_make(selector, framework)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("NEZHA_CAMERA_AUX_PACKAGES", run.stderr)
                self.assertEqual(run.stdout, "")

    def test_unreviewed_missing_or_duplicate_predecessors_fail(self):
        for properties in ("", "vendor.camera.aux.packagelist=another.app",
                           FACTORY + " " + FACTORY,
                           FACTORY + " vendor.camera.aux.packagelist=another.app"):
            with self.subTest(properties=properties):
                run = self.run_make("true", properties=properties)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("single reviewed factory camera allowlist", run.stderr)

    def test_contract_hashes_recompute_from_source(self):
        contract = json.loads((ROOT / "config/nezha-camera-aux-packages.json").read_text())
        self.assertEqual(hashlib.sha256(FRAGMENT.read_bytes()).hexdigest(),
                         contract["fragment_sha256"])
        self.assertEqual(hashlib.sha256((ROOT / contract["predecessor_fragment"]).read_bytes()).hexdigest(),
                         contract["predecessor_fragment_sha256"])


if __name__ == "__main__":
    unittest.main()
