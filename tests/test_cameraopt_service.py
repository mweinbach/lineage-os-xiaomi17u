"""Exercise the opt-in and reject invalid built CameraOpt ownership artifacts."""
from pathlib import Path
import hashlib
import importlib.util
import json
import shutil
import struct
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/cameraopt-service.mk"
SPEC = importlib.util.spec_from_file_location(
    "cameraopt_artifacts", ROOT / "device/xiaomi/nezha/cameraopt-service/verify_artifacts.py")
ARTIFACTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ARTIFACTS)


def synthetic_dex(classes):
    """Minimal class-definition fixture; no compiler or phone is involved."""
    count = len(classes)
    strings_offset = 112
    types_offset = strings_offset + count * 4
    classes_offset = types_offset + count * 4
    data_offset = classes_offset + count * 32
    data = bytearray(data_offset)
    data[:8] = b"dex\n039\0"
    struct.pack_into("<II", data, 36, 112, 0x12345678)
    for offset, size, table_offset in ((56, count, strings_offset), (64, count, types_offset),
                                     (96, count, classes_offset)):
        struct.pack_into("<II", data, offset, size, table_offset)
    for index, name in enumerate(classes):
        encoded = name.encode("ascii")
        if len(encoded) >= 128:
            raise ValueError("Fixture descriptor is too long")
        struct.pack_into("<I", data, strings_offset + index * 4, len(data))
        struct.pack_into("<I", data, types_offset + index * 4, index)
        struct.pack_into("<III", data, classes_offset + index * 32, index, 1, 0xffffffff)
        data.extend(bytes([len(encoded)]) + encoded + b"\0")
    struct.pack_into("<I", data, 32, len(data))
    return bytes(data)


def jar(path, classes, *, compression=zipfile.ZIP_STORED, extra=None):
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        archive.writestr("classes.dex", synthetic_dex(classes))
        for name, value in (extra or {}).items():
            archive.writestr(name, value)


class CameraOptServiceSelectionTests(unittest.TestCase):
    def run_fragment(self, selector=None, *, target="nezha", product="lineage_nezha", prerequisites=None,
                     existing_classpath=""):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        values = {"TARGET_DEVICE": target, "TARGET_PRODUCT": product,
                  "NEZHA_DEVICE_PATH": "device/xiaomi/nezha",
                  "NEZHA_CAMERA_FRAMEWORK": "true", "NEZHA_CAMERAOPT_NATIVE_COMPAT": "true",
                  "NEZHA_CAMERA_PLATFORM_SIGNED": "true", "NEZHA_CAMERA_AUX_PACKAGES": "true",
                  "PRODUCT_SYSTEM_SERVER_JARS": existing_classpath}
        values.update(prerequisites or {})
        if selector is not None:
            values["NEZHA_CAMERAOPT_SERVICE"] = selector
        assignments = "".join(f"{key} := {value}\n" for key, value in values.items()
                              if value is not None)
        variables = ("PRODUCT_PACKAGES", "PRODUCT_SYSTEM_SERVER_JARS", "PRODUCT_SYSTEM_PROPERTIES",
                     "PRODUCT_PACKAGE_OVERLAYS", "SYSTEM_EXT_PUBLIC_SEPOLICY_DIRS",
                     "SYSTEM_EXT_PRIVATE_SEPOLICY_DIRS")
        recipe = "\t@printf '%s\\n' " + " ".join(f"'$({value})'" for value in variables) + "\n"
        return subprocess.run([make, "--no-print-directory", "-f", "-"],
                              input=assignments + f"include {FRAGMENT}\nall:\n" + recipe,
                              text=True, capture_output=True, timeout=10,
                              env={"PATH": "/usr/bin:/bin"})

    def test_unselected_service_does_not_change_product_configuration(self):
        for selector in (None, "", " ", "false", " false "):
            with self.subTest(selector=selector):
                result = self.run_fragment(selector, prerequisites={
                    "NEZHA_CAMERA_FRAMEWORK": "false", "NEZHA_CAMERA_PLATFORM_SIGNED": "false"})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), "")

    def test_enabled_service_orders_the_runtime_and_selects_dedicated_policy(self):
        result = self.run_fragment(" true ", existing_classpath="services org.lineageos.platform")
        self.assertEqual(result.returncode, 0, result.stderr)
        values = result.stdout.splitlines()
        self.assertEqual(values[0].split(), ["miui-cameraopt", "nezha-cameraopt-service"])
        self.assertEqual(values[1].split(), ["services", "org.lineageos.platform", "miui-cameraopt",
                                           "nezha-cameraopt-service"])
        self.assertEqual(values[2].split(), ["ro.nezha.cameraopt.service=true"])
        self.assertEqual(values[3].split(), ["device/xiaomi/nezha/cameraopt-service/overlay"])
        self.assertEqual(values[4].split(), ["device/xiaomi/nezha/cameraopt-service/sepolicy/public"])
        self.assertEqual(values[5].split(), ["device/xiaomi/nezha/cameraopt-service/sepolicy/private"])
        contract = json.loads((ROOT / "config/nezha-cameraopt-service.json").read_text())
        predecessor = contract["effective_predecessor_service_array"]
        # The compiled v8 array is a measured build decision: changing this pin
        # requires rebasing the overlay to retain every existing system service.
        self.assertEqual(predecessor["entries"], [])
        self.assertEqual(predecessor["apk_sha256"],
                         "24147e85038e3a3a97b04091d132d9f1886c29edcb4f739ab3802fc451df5005")
        overlay = ET.parse(ROOT / "device/xiaomi/nezha/cameraopt-service/overlay/frameworks/base/"
                           "core/res/res/values/config.xml")
        entries = [item.text for item in overlay.findall(
            "./string-array[@name='config_deviceSpecificSystemServices']/item")]
        self.assertEqual(entries, predecessor["entries"] + [
            "com.android.server.cameraopt.NezhaCameraOptService"])

    def test_malformed_selector_fails_before_selecting_anything(self):
        for selector in ("yes", "1", "TRUE", "False", "true true", "true false", "false false"):
            with self.subTest(selector=selector):
                result = self.run_fragment(selector)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("NEZHA_CAMERAOPT_SERVICE", result.stderr)
                self.assertEqual(result.stdout, "")

    def test_service_rejects_missing_or_malformed_prerequisites(self):
        for name in ("NEZHA_CAMERA_FRAMEWORK", "NEZHA_CAMERAOPT_NATIVE_COMPAT",
                     "NEZHA_CAMERA_PLATFORM_SIGNED", "NEZHA_CAMERA_AUX_PACKAGES"):
            for value in (None, "", "false", "yes", "true true"):
                with self.subTest(name=name, value=value):
                    result = self.run_fragment("true", prerequisites={name: value})
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(name + "=true", result.stderr)
                    self.assertEqual(result.stdout, "")

    def test_foreign_product_or_duplicate_classpath_is_rejected(self):
        for product in (None, "", "other_product", "lineage_nezha other_product"):
            with self.subTest(product=product):
                result = self.run_fragment("true", product=product)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("TARGET_PRODUCT=lineage_nezha", result.stderr)
        result = self.run_fragment("true", target="other_device")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("TARGET_DEVICE=nezha", result.stderr)
        for entry in ("miui-cameraopt", "nezha-cameraopt-service", "platform:miui-cameraopt",
                      "platform:nezha-cameraopt-service"):
            with self.subTest(entry=entry):
                result = self.run_fragment("true", existing_classpath="services " + entry)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("exclusive ownership", result.stderr)

    def test_early_product_inheritance_accepts_unassigned_target_device(self):
        # Soong queries product release configuration before TARGET_DEVICE is
        # assigned. The selected TARGET_PRODUCT must still be checked here.
        late = self.run_fragment("true")
        for target in (None, "", " "):
            with self.subTest(target=target):
                early = self.run_fragment("true", target=target)
                self.assertEqual(early.returncode, 0, early.stderr)
                self.assertEqual(early.stdout, late.stdout)


class CameraOptArtifactOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.original = self.directory / "original.jar"
        self.runtime = self.directory / "runtime.jar"
        self.adapter = self.directory / "adapter.jar"
        self.services = self.directory / "services.jar"
        self.factory_classes = ["Lcom/miui/cameraopt/ICameraOptManager;",
                                "Lcom/miui/cameraopt/verify/Verifier;"]
        self.adapter_classes = ["Lcom/android/server/cameraopt/NezhaCameraOptService;",
                                "Lcom/android/server/cameraopt/CameraStatusSampler;"]
        self.helper = "Lcom/android/server/am/NezhaCameraProcessPolicy;"
        jar(self.original, self.factory_classes)
        jar(self.runtime, self.factory_classes, compression=zipfile.ZIP_DEFLATED)
        jar(self.adapter, self.adapter_classes)
        jar(self.services, [self.helper])
        self.classpath = ["/system/framework/services.jar", "/system_ext/framework/miui-cameraopt.jar",
                          "/system_ext/framework/nezha-cameraopt-service.jar"]
        self.contract = {"factory_jar_sha256": hashlib.sha256(self.original.read_bytes()).hexdigest(),
                         "factory_required_classes": self.factory_classes,
                         "adapter_required_classes": self.adapter_classes,
                         "process_helper_class": self.helper,
                         "runtime_classpath_order": self.classpath.copy()}

    def validate(self):
        return ARTIFACTS.validate(self.contract, self.original, self.runtime, self.adapter,
                                  self.services, self.classpath)

    def test_zip_repacking_preserves_factory_code_ownership(self):
        result = self.validate()
        self.assertEqual(result["status"], "artifact_ownership_verified")
        self.assertNotEqual(result["factory_input_sha256"], result["original_runtime_sha256"])
        self.assertEqual(result["original_class_count"], 2)

    def test_modified_factory_input_or_runtime_is_rejected(self):
        jar(self.runtime, self.factory_classes + ["Lcom/miui/cameraopt/Replacement;"])
        with self.assertRaisesRegex(ARTIFACTS.ValidationError, "changed member"):
            self.validate()
        jar(self.original, self.factory_classes + ["Lcom/miui/cameraopt/Replacement;"])
        with self.assertRaisesRegex(ARTIFACTS.ValidationError, "differs from the selected original"):
            self.validate()

    def test_factory_declarations_cannot_be_installed_with_adapter(self):
        for leaked in (self.factory_classes[0], "Lcom/miui/cameraopt/CompileOnlyUnexpected;"):
            with self.subTest(leaked=leaked):
                jar(self.adapter, self.adapter_classes + [leaked])
                with self.assertRaises(ARTIFACTS.ValidationError):
                    self.validate()

    def test_helper_is_required_in_services_and_not_in_adapter(self):
        jar(self.services, ["Lcom/android/server/SystemServer;"])
        with self.assertRaisesRegex(ARTIFACTS.ValidationError, "process-policy helper"):
            self.validate()
        jar(self.services, [self.helper])
        jar(self.adapter, self.adapter_classes + [self.helper])
        with self.assertRaisesRegex(ARTIFACTS.ValidationError, "unexpected runtime class"):
            self.validate()

    def test_only_measured_platform_duplicates_are_accepted(self):
        duplicate = "Landroid/hidl/base/V1_0/IBase;"
        jar(self.original, self.factory_classes + [duplicate])
        jar(self.runtime, self.factory_classes + [duplicate])
        self.contract["factory_jar_sha256"] = hashlib.sha256(self.original.read_bytes()).hexdigest()
        jar(self.services, [self.helper, duplicate])
        with self.assertRaisesRegex(ARTIFACTS.ValidationError, "unreviewed duplicate"):
            self.validate()
        self.contract["allowed_platform_duplicates"] = [duplicate]
        self.assertEqual(self.validate()["baseline_platform_duplicates"], [duplicate])

    def test_runtime_dependency_order_and_unique_entries_are_required(self):
        correct = self.classpath.copy()
        for entries in (list(reversed(correct)), correct + [correct[1]], correct[:-1],
                        correct + ["/system/framework/nezha-cameraopt-compile-stubs.jar"]):
            with self.subTest(entries=entries):
                self.classpath = entries
                with self.assertRaises(ARTIFACTS.ValidationError):
                    self.validate()

    def test_malformed_dex_bounds_are_rejected(self):
        data = bytearray(synthetic_dex(["Lcom/example/Fixture;"]))
        struct.pack_into("<I", data, 100, len(data) + 4)
        with self.assertRaisesRegex(ARTIFACTS.ValidationError, "out of bounds"):
            ARTIFACTS.dex_classes(bytes(data))


if __name__ == "__main__":
    unittest.main()
