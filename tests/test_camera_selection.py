"""Validate the explicit Camera input profile without private files or a phone."""

from collections import Counter
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

from scripts import vendor_inputs


ROOT = Path(__file__).resolve().parents[1]
SELECTION = ROOT / "vendor/xiaomi/nezha/camera-selection.json"
JNI = "/system_ext/lib64/libcamera_algoup_jni.xiaomi.so"
JARS = {
    "/system_ext/framework/camerax-vendor-extensions.jar",
    "/system_ext/framework/com.xiaomi.hardware.camera.companion-V1.jar",
    "/system_ext/framework/miui-cameraopt.jar",
    "/system_ext/framework/vendor.xiaomi.hardware.postprocservice-V1-java.jar",
}
XML = {
    "/system_ext/etc/permissions/com.xiaomi.hardware.camera.companion.xml":
        ("7f8be37f7a76c1a2311c26362716612fefe4a2ebac41a2b13fe410f4a2044ca1", 335),
    "/system_ext/etc/permissions/miui-cameraopt.xml":
        ("5088b9b19d251e3a2c24ce435c02a3c4f0fd6ce3d81a68d1a6c1c435598c2371", 797),
    "/system_ext/etc/permissions/vendor.xiaomi.hardware.postprocservice-V1-java-permission.xml":
        ("3a22f4bfe89ad6388a67bf7d2f985ae285b602270f7b95cc116b9d46e8236bd7", 188),
}


class CameraSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selection = json.loads(SELECTION.read_text())
        cls.camera = json.loads((ROOT / "research/camera-dependencies.json").read_text())
        cls.vintf = json.loads((ROOT / "research/vintf-contract.json").read_text())
        cls.modules = {module["runtime_path"]: module for module in cls.selection["modules"]}

    def test_exact_bounded_scope_and_package_binding(self):
        self.assertEqual(self.selection["schema_version"], 1)
        self.assertEqual(self.selection["device"], "nezha")
        self.assertEqual(self.selection["package_sha256"], self.camera["provenance"]["package_sha256"])
        self.assertFalse(self.camera["provenance"]["origin_verified"])
        self.assertFalse(self.camera["provenance"]["package_avb_consistent"])
        self.assertEqual(set(self.modules), {JNI, *JARS, *XML})
        self.assertEqual(len(self.selection["modules"]), 8)
        self.assertEqual(Counter(m["type"] for m in self.modules.values()),
                         {"shared_library": 1, "dex_jar": 4, "xml": 3})
        self.assertEqual(sum(m["size_bytes"] for m in self.modules.values()), 542026)

    def test_jni_and_jar_hashes_match_captured_seed_record(self):
        seeds = {artifact["runtime_path"]: artifact for artifact in self.camera["artifacts"]}
        for path in {JNI, *JARS}:
            with self.subTest(path=path):
                self.assertEqual(self.modules[path]["sha256"], seeds[path]["sha256"])
                self.assertEqual(self.modules[path]["size_bytes"], seeds[path]["size_bytes"])
                self.assertEqual(seeds[path]["image_sha256"],
                                 "b2937ccb0dd38290af629c19064d1bacf4d9167d5074fb86e972f4d30b4c54ef")

    def test_permission_xml_hashes_are_original_not_rewritten(self):
        for path, (digest, size) in XML.items():
            with self.subTest(path=path):
                self.assertEqual(self.modules[path]["sha256"], digest)
                self.assertEqual(self.modules[path]["size_bytes"], size)
                self.assertEqual(self.modules[path]["type"], "xml")

    def test_twenty_dt_needed_names_have_explicit_soong_mapping(self):
        seed = next(item for item in self.camera["artifacts"] if item["runtime_path"] == JNI)
        self.assertEqual((seed["elf_bits"], seed["elf_machine"]), (64, 183))
        self.assertTrue(seed["readelf_crosscheck"])
        self.assertEqual(len(seed["needed"]), 20)
        self.assertTrue(all(name.endswith(".so") for name in seed["needed"]))
        self.assertEqual(self.modules[JNI]["shared_libs"], sorted(name[:-3] for name in seed["needed"]))
        self.assertIn("libandroid_runtime", self.modules[JNI]["shared_libs"])
        self.assertIn("libcamera_client", self.modules[JNI]["shared_libs"])
        self.assertIn("android.hidl.token@1.0-utils", self.modules[JNI]["shared_libs"])

    def test_generator_accepts_profile_and_preserves_native_validation(self):
        modules, digest = vendor_inputs._selection(SELECTION, self.selection["package_sha256"], [])
        self.assertRegex(digest, r"^[a-f0-9]{64}$")
        self.assertEqual(len(modules), 8)
        self.assertEqual(len({m["module_name"] for m in modules}), 8)
        for module in modules:
            if module["type"] == "shared_library":
                module["elf_bits"] = 64
                module["elf_machine"] = 183
        blueprint = "\n".join(vendor_inputs._module_text(module) for module in modules)
        self.assertEqual(blueprint.count("cc_prebuilt_library_shared {"), 1)
        self.assertEqual(blueprint.count("dex_import {"), 4)
        self.assertEqual(blueprint.count("prebuilt_etc_xml {"), 3)
        self.assertIn("android_arm64: {", blueprint)
        self.assertIn('stem: "libcamera_algoup_jni.xiaomi"', blueprint)
        self.assertIn("check_elf_files: true", blueprint)
        self.assertIn("strip: { none: true }", blueprint)
        for forbidden in ("check_elf_files: false", "enforce_uses_libs", "provides_uses_lib",
                          "skip_preprocessed_apk_checks", "android_app_import", "system_shared_libs"):
            self.assertNotIn(forbidden, blueprint)

    def test_unrelated_frameworks_vendor_files_and_apk_are_not_selected(self):
        for path in self.modules:
            self.assertTrue(path.startswith("/system_ext/"))
            self.assertFalse(path.endswith(".apk"))
            self.assertNotIn("..", Path(path).parts)
            self.assertNotIn(Path(path).name,
                             {"framework.jar", "services.jar", "platform-miui.xml", "privapp-permissions-product.xml"})
        self.assertNotIn("/vendor/framework/androidx.camera.extensions.impl.jar", self.modules)
        self.assertNotIn("/system_ext/etc/permissions/platform-miui.xml", self.modules)

    def test_postproc_discrepancy_is_not_hidden_by_selecting_the_jar(self):
        mismatch = self.vintf["postproc_library_path"]
        self.assertIn(mismatch["permission_source"], self.modules)
        self.assertIn(mismatch["observed_regular_file"]["runtime_path"], self.modules)
        self.assertNotEqual(mismatch["declared_path"], mismatch["observed_regular_file"]["runtime_path"])
        self.assertFalse(mismatch["matching_alias_observed"])
        self.assertFalse(mismatch["runtime_path_resolution_verified"])
        self.assertEqual(self.modules[mismatch["permission_source"]]["sha256"],
                         self.vintf["source_files"][mismatch["permission_source"]]["sha256"])

    def test_profile_cannot_be_silently_reused_with_another_firmware_package(self):
        with self.assertRaises(vendor_inputs.VendorInputError):
            vendor_inputs._selection(SELECTION, "f" * 64, [])

    def test_documented_module_sources_use_the_resolved_platform_pins(self):
        document = (ROOT / "docs/camera-inputs.md").read_text()
        manifest = ET.parse(ROOT / "research/source-snapshots/evolution-bka-20260827.xml").getroot()
        revisions = {project.get("revision") for project in manifest.findall("project")}
        links = re.findall(
            r"\[([^\]]+)\]\((https://(?:github\.com|android\.googlesource\.com)/[^)]+)\)", document)
        dependency_links = {name: url for name, url in links if name in self.modules[JNI]["shared_libs"]}
        self.assertEqual(set(dependency_links), set(self.modules[JNI]["shared_libs"]))
        for name, url in dependency_links.items():
            with self.subTest(name=name):
                revision = re.search(r"/[a-f0-9]{40}/", url)
                self.assertIsNotNone(revision)
                self.assertIn(revision.group()[1:-1], revisions)
        self.assertIn("/core/jni/Android.bp#L588", dependency_links["libmedia_jni_utils"])

    def test_document_keeps_registration_and_runtime_limits_explicit(self):
        document = " ".join((ROOT / "docs/camera-inputs.md").read_text().split())
        for text in ("CameraX shared-library registration remains pending", "platform-miui.xml",
                     "postproc XML still points to", "The Camera APK and full MIUI framework are not included",
                     "No uses-library, signature or preprocessed-APK check was disabled"):
            self.assertIn(text, document)


if __name__ == "__main__":
    unittest.main()
