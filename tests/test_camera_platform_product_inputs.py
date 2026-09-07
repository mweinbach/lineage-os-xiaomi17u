import copy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import camera_apk_inputs as base
from scripts import camera_platform_product_inputs as platform
from scripts import camera_product_inputs as original


class CameraPlatformProductTests(unittest.TestCase):
    """Exercise source staging and Make selection without APK tools or a phone."""

    MAKE_CASES = 0

    def source(self):
        files = {
            path: base.encoded({"synthetic_reference": name})
            for name, path in base.PROVENANCE.items()
        }
        files["provenance/review.json"] = (
            base.ROOT / "research/factory-camera-apk.json").read_bytes()
        files["provenance/contract.json"] = b'{"synthetic_contract": true}\n'
        files[base.PAYLOAD] = b"synthetic original APK\x00\xff\n"
        files["Android.bp"] = b"original generated Blueprint\n"
        files["tools/verify_camera_apk.py"] = b"original generated producer\n"
        return files

    def write_files(self, root, files):
        for name, raw in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    def verified_input(self, root):
        files = {"source/" + name: raw for name, raw in self.source().items()}
        self.write_files(root, files)
        return {
            "files": [{"path": name, **base.identity(raw)}
                      for name, raw in sorted(files.items())],
            "receipt": {"synthetic_verified_packet": True},
        }

    def import_properties(self, blueprint):
        blocks = re.findall(r"^android_app_import \{\n(.*?)^\}",
                            blueprint.decode(), re.MULTILINE | re.DOTALL)
        self.assertEqual(len(blocks), 1)
        result = {}
        for line in blocks[0].splitlines():
            match = re.fullmatch(r"    (\w+): (.*),", line)
            self.assertIsNotNone(match, line)
            key, value = match.groups()
            self.assertNotIn(key, result)
            result[key] = json.loads(value)
        return result

    def producer(self, root, rendered, inputs=None):
        source = root / "source"
        self.write_files(source, rendered)
        if inputs is None:
            inputs = [str(source / name) for name in rendered
                      if name != "tools/verify_camera_apk.py"]
        result = subprocess.run(
            [sys.executable, "-B", str(source / "tools/verify_camera_apk.py"),
             "--output-dir", str(root / "out"), *inputs],
            capture_output=True, text=True, timeout=15)
        return result

    def run_make(self, root, selector=None, camera=None, framework=None,
                 real_include=False):
        fragment = base.ROOT / "device/xiaomi/nezha/camera-platform-signed.mk"
        assignments = []
        for name, value in [("NEZHA_CAMERA_PLATFORM_SIGNED", selector),
                            ("NEZHA_XIAOMI_CAMERA", camera),
                            ("NEZHA_CAMERA_FRAMEWORK", framework)]:
            if value is not None:
                assignments.append(f"{name} := {value}")
        inherit = "$(eval INCLUDES += $(strip $(1)))"
        if real_include:
            inherit += "$(eval include $(strip $(1)))"
        makefile = root / "test.mk"
        makefile.write_text("\n".join([
            *assignments,
            "PRODUCT_SOONG_NAMESPACES := sentinel.namespace",
            "PRODUCT_PACKAGES := SentinelPackage",
            "define inherit-product", inherit, "endef",
            f"include {fragment}",
            "$(info INCLUDES=$(strip $(INCLUDES)))",
            "$(info NAMESPACES=$(strip $(PRODUCT_SOONG_NAMESPACES)))",
            "$(info PACKAGES=$(strip $(PRODUCT_PACKAGES)))",
            ".PHONY: all", "all: ; @:", "",
        ]))
        type(self).MAKE_CASES += 1
        result = subprocess.run(
            ["make", "-rR", "-s", "-f", str(makefile), "all"],
            cwd=root, env={"PATH": os.defpath}, capture_output=True,
            text=True, timeout=10)
        values = dict(line.split("=", 1) for line in result.stdout.splitlines()
                      if line.startswith(("INCLUDES=", "NAMESPACES=", "PACKAGES=")))
        return result, values

    def test_preserves_original_payload_provenance_and_baseline_render(self):
        source = self.source()
        untouched = copy.deepcopy(source)
        baseline = original.render(source)
        rendered = platform.render(source)
        regenerated = {"Android.bp", "tools/verify_camera_apk.py"}
        for name, raw in source.items():
            if name not in regenerated:
                with self.subTest(preserved=name):
                    self.assertEqual(rendered[name], raw)
        self.assertEqual(source, untouched)
        self.assertEqual(original.render(source), baseline)
        self.assertEqual(set(rendered), (set(source) | {
            platform.PERMISSION_FILE, platform.POLICY_FILE, platform.PRODUCT_FILE}))
        self.assertEqual(rendered[platform.PERMISSION_FILE],
                         baseline[original.PERMISSION_FILE])
        self.assertEqual(rendered[platform.PERMISSION_FILE].count(b"<permission name="), 11)

    def test_changes_only_normal_signing_properties_in_app_import(self):
        source = self.source()
        before = self.import_properties(original.render(source)["Android.bp"])
        after = self.import_properties(platform.render(source)["Android.bp"])
        self.assertTrue(before.pop("presigned"))
        self.assertTrue(before.pop("preprocessed"))
        before.update(certificate="platform", name=platform.MODULE,
                      required=[platform.PERMISSION_MODULE],
                      apk=":nezha_platform_camera_verified_apk")
        self.assertEqual(after, before)
        self.assertTrue(after["enforce_uses_libs"])
        self.assertTrue(after["system_ext_specific"])
        self.assertTrue(after["privileged"])
        self.assertEqual(after["uses_libs"], [])
        self.assertEqual(after["optional_uses_libs"], [
            "miui-cameraopt", "androidx.window.extensions", "androidx.window.sidecar"])
        for name in ["relax_uses_library_check", "dex_preopt", "overrides",
                     "skip_preprocessed_apk_checks", "product_specific"]:
            self.assertNotIn(name, after)

    def test_rejects_changed_base_signing_contract(self):
        blueprint = base._blueprint([*self.source(), "Android.bp"])
        for changed in [blueprint.replace(b"    presigned: true,\n", b""),
                        blueprint.replace(b"    preprocessed: true,\n", b""),
                        blueprint.replace(b"    presigned: true,\n",
                                          b"    presigned: true,\n" * 2)]:
            with self.subTest(blueprint=changed), mock.patch.object(
                    base, "_blueprint", return_value=changed):
                with self.assertRaisesRegex(base.CameraApkError, "contract changed"):
                    platform.render(self.source())

    def test_packet_uses_original_verification_and_records_recomputed_identities(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            verified = self.verified_input(root)
            with mock.patch.object(base, "verify_bundle", return_value=verified) as check:
                files, receipt = platform.expected_packet(root)
            check.assert_called_once_with(root)
            self.assertEqual(receipt["original_packet"], verified["receipt"])
            self.assertEqual(receipt["original_apk"], base.identity(self.source()[base.PAYLOAD]))
            self.assertEqual(receipt["partition"], "system_ext")
            self.assertEqual(receipt["include"], platform.NAMESPACE + "/" + platform.PRODUCT_FILE)
            self.assertEqual(receipt["module"], platform.MODULE)
            for name in ["apk_transformed_or_signed", "key_accessed", "phone_accessed",
                         "native_build_verified", "runtime_verified"]:
                self.assertFalse(receipt[name])
            self.assertEqual(receipt["signing_policy"],
                             json.loads(files["source/" + platform.POLICY_FILE]))
            self.assertEqual(json.loads(files[platform.RECEIPT]), receipt)
            self.assertEqual({row["path"] for row in receipt["files"]},
                             set(files) - {platform.RECEIPT})
            for row in receipt["files"]:
                with self.subTest(path=row["path"]):
                    self.assertEqual(row["sha256"], hashlib.sha256(files[row["path"]]).hexdigest())
                    self.assertEqual(row["size_bytes"], len(files[row["path"]]))
                    self.assertEqual(row["destination"], platform.NAMESPACE + "/" +
                                     row["path"].removeprefix("source/"))

    def test_original_verification_failure_prevents_rendering(self):
        input_packet = Path("synthetic-unverified-packet")
        with mock.patch.object(base, "verify_bundle", side_effect=base.CameraApkError(
                "original packet rejected")) as check, mock.patch.object(platform, "render") as render:
            with self.assertRaisesRegex(base.CameraApkError, "original packet rejected"):
                platform.expected_packet(input_packet)
        check.assert_called_once_with(input_packet)
        render.assert_not_called()

    def test_rechecks_input_bytes_after_original_packet_verification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            verified = self.verified_input(root)
            payload = root / "source" / base.PAYLOAD
            raw = payload.read_bytes()
            payload.write_bytes(bytes([raw[0] ^ 1]) + raw[1:])
            with mock.patch.object(base, "verify_bundle", return_value=verified):
                with self.assertRaises(base.CameraApkError):
                    platform.expected_packet(root)

    def test_native_producer_hashes_every_declared_input_before_publication(self):
        original_files = platform.render(self.source())
        inputs = set(original_files) - {"tools/verify_camera_apk.py"}
        for tamper in [None, *sorted(inputs)]:
            with self.subTest(tamper=tamper), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                rendered = dict(original_files)
                if tamper:
                    raw = rendered[tamper]
                    rendered[tamper] = bytes([raw[0] ^ 1]) + raw[1:]
                result = self.producer(root, rendered)
                self.assertEqual(result.returncode, 2 if tamper else 0, result.stderr)
                if tamper:
                    self.assertIn("input hash mismatch", result.stderr)
                    self.assertFalse((root / "out").exists())
                else:
                    self.assertEqual(result.stderr, "")
                    self.assertEqual((root / "out" / base.VERIFIED).read_bytes(),
                                     self.source()[base.PAYLOAD])
                    receipt = json.loads((root / "out/camera-apk-checked.json").read_text())
                    self.assertEqual(receipt["input_count"], len(inputs))
                    self.assertEqual(receipt["apk"], base.identity(self.source()[base.PAYLOAD]))
                    self.assertTrue(receipt["verified"])
                    self.assertFalse(receipt["apk_executed_or_signed"])
                    self.assertFalse(receipt["image_adoption_allowed"])
        blueprint = original_files["Android.bp"].decode()
        genrule = re.search(r"^genrule \{\n(.*?)^\}", blueprint, re.MULTILINE | re.DOTALL).group(1)
        declared = re.search(r"    srcs: \[\n(.*?)    \],", genrule, re.DOTALL).group(1)
        self.assertEqual(set(re.findall(r'"([^"]+)"', declared)), inputs)

    def test_native_producer_rejects_missing_duplicate_and_unknown_inputs(self):
        rendered = platform.render(self.source())
        names = [name for name in rendered if name != "tools/verify_camera_apk.py"]
        for variation in ["missing", "duplicate", "unknown", "extra"]:
            with self.subTest(variation=variation), tempfile.TemporaryDirectory() as temp:
                root = Path(temp).resolve()
                inputs = [str(root / "source" / name) for name in names]
                if variation == "missing":
                    inputs.pop()
                elif variation == "duplicate":
                    inputs[-1] = inputs[0]
                elif variation == "unknown":
                    inputs[-1] = str(root / "unknown.input")
                else:
                    inputs.append(str(root / "unknown.input"))
                result = self.producer(root, rendered, inputs)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse((root / "out").exists())

    def test_make_selector_off_invalid_and_dependency_gates(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            for selector in [None, "", "false", " false "]:
                for dependency in [None, "false", "true"]:
                    with self.subTest(selector=selector, dependencies=dependency):
                        result, values = self.run_make(root, selector, dependency, dependency)
                        self.assertEqual(result.returncode, 0, result.stderr)
                        self.assertEqual(values, {"INCLUDES": "", "NAMESPACES": "sentinel.namespace",
                                                  "PACKAGES": "SentinelPackage"})
            for selector in ["0", "1", "TRUE", "yes", "true false", "true true"]:
                with self.subTest(invalid=selector):
                    result, _ = self.run_make(root, selector, "true", "true")
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn("NEZHA_CAMERA_PLATFORM_SIGNED must", result.stderr)
            for dependency in [None, "false"]:
                for missing in ["camera", "framework"]:
                    with self.subTest(missing=missing, value=dependency):
                        camera = dependency if missing == "camera" else "true"
                        framework = dependency if missing == "framework" else "true"
                        result, _ = self.run_make(root, "true", camera, framework)
                        self.assertNotEqual(result.returncode, 0)
                        required = "NEZHA_XIAOMI_CAMERA" if missing == "camera" else "NEZHA_CAMERA_FRAMEWORK"
                        self.assertIn(f"requires {required}=true", result.stderr)
            for selector in ["true", " true "]:
                with self.subTest(enabled=selector):
                    result, values = self.run_make(root, selector, "true", "true")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(values["INCLUDES"], platform.NAMESPACE + "/" + platform.PRODUCT_FILE)

    def test_make_requires_packet_and_includes_generated_product(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            result, _ = self.run_make(root, "true", "true", "true", real_include=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(platform.PRODUCT_FILE, result.stderr)
            rendered = platform.render(self.source())
            self.write_files(root / platform.NAMESPACE,
                             {platform.PRODUCT_FILE: rendered[platform.PRODUCT_FILE]})
            result, values = self.run_make(root, "true", "true", "true", real_include=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(values["NAMESPACES"].split(), ["sentinel.namespace", platform.NAMESPACE])
            self.assertEqual(values["PACKAGES"].split(), ["SentinelPackage", platform.MODULE,
                             platform.PERMISSION_MODULE, "androidx.window.extensions", "androidx.window.sidecar"])
            self.assertNotIn(original.MODULE, values["PACKAGES"].split())

    def test_config_hashes_and_identifiers_match_real_inputs_and_rendered_graph(self):
        config = json.loads((base.ROOT / "config/nezha-camera-platform-signed.json").read_text())
        contract = json.loads((base.ROOT / config["preserved_input"]["contract"]).read_text())
        for name in ["fragment", "generator", "baseline_generator"]:
            with self.subTest(identity=name):
                self.assertEqual(config[name + "_sha256"],
                                 hashlib.sha256((base.ROOT / config[name]).read_bytes()).hexdigest())
        preserved = config["preserved_input"]
        self.assertEqual(preserved["apk_sha256"], contract["apk"]["sha256"])
        self.assertEqual(preserved["apk_size_bytes"], contract["apk"]["size_bytes"])
        self.assertEqual(preserved["factory_certificate_sha256"], contract["signer_certificate_sha256"])
        rendered = platform.render(self.source())
        properties = self.import_properties(rendered["Android.bp"])
        policy = json.loads(rendered[platform.POLICY_FILE])
        self.assertEqual(config["module"], properties["name"])
        self.assertEqual(config["certificate"], properties["certificate"])
        self.assertEqual(config["include"], config["namespace"] + "/" + platform.PRODUCT_FILE)
        self.assertIn("PRODUCT_SOONG_NAMESPACES += " + config["namespace"],
                      rendered[platform.PRODUCT_FILE].decode())
        for name in ["selector", "requires_selectors", "package", "certificate"]:
            self.assertEqual(config[name], policy[name])
        self.assertEqual(config["partition"], "system_ext")
        self.assertEqual(config["build_behavior"]["enforce_uses_libs"], properties["enforce_uses_libs"])
        self.assertEqual(config["build_behavior"]["optional_uses_libs_in_order"], properties["optional_uses_libs"])
        self.assertEqual(config["build_behavior"]["extra_privapp_permissions_added"],
                         policy["additional_privapp_permissions"])
        self.assertEqual(config["build_behavior"]["verifier_or_package_manager_changes"],
                         policy["apk_verifier_or_package_manager_modified"])


if __name__ == "__main__":
    unittest.main()
