"""Build-only Camera packet integrity using synthetic bytes, never private APKs."""

import copy
import contextlib
import errno
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import camera_apk_inputs as camera


ROOT = Path(__file__).resolve().parents[1]


class CameraApkInputsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "artifacts").mkdir()
        self.output = self.root / "artifacts/camera-packet"
        self.contract = json.loads((ROOT / camera.CONFIG).read_text())
        self.review = json.loads((ROOT / "research/factory-camera-apk.json").read_text())
        self.apk = b"synthetic unsigned fixture; tests exercise content integrity only\x00" * 8
        self.contract["apk"].update(camera.identity(self.apk))
        self.capture_dir = self.root / Path(self.contract["capture"]["path"]).parent
        self.write(str(self.capture_dir.relative_to(self.root) / "files/0001"), self.apk)
        capture = {"schema_version": 1, "operation": "erofs-capture",
                   "image": self.contract["factory_image"], "firmware_executed": False,
                   "image_mounted": False, "symlinks_followed": False,
                   "files": [{**camera.identity(self.apk), "path": self.contract["apk"]["image_relative_path"],
                              "nid": self.contract["apk"]["nid"], "output_path": "files/0001",
                              "type": "regular", "readback_verified": True}]}
        self.contract["capture"] = self.write(self.contract["capture"]["path"], camera.encoded(capture))
        self.runtime_payloads = {f"proprietary/system_ext/fixture/{i}": f"runtime {i}".encode() for i in range(9)}
        self.runtime_bp = b"soong_namespace {}\n// synthetic runtime fixture\n"
        self.runtime = {"extras": [{"path": name, **camera.identity(data)} for name, data in self.runtime_payloads.items()],
                        "generated_files": [{"path": "Android.bp", **camera.identity(self.runtime_bp)}]}
        for name in camera.REFERENCES:
            if name in {"capture", "review"}:
                continue
            data = camera.encoded(self.runtime) if name == "runtime_bundle" else camera.encoded({"fixture": name})
            self.contract[name] = self.write(self.contract[name]["path"], data)
        self.review["factory_input"].update(camera.identity(self.apk))
        self.review["factory_input"]["capture"] = self.contract["capture"]
        self.review["runtime_dependencies"]["contract"] = self.contract["runtime_contract"]
        self.review["runtime_dependencies"]["bundle_receipt"] = self.contract["runtime_bundle"]
        self.contract["review"] = self.write(self.contract["review"]["path"], camera.encoded(self.review))
        self.source_payloads = {name: ("pinned fixture " + name).encode() for name in self.contract["source_requirements"]["files"]}
        self.contract["source_requirements"]["files"] = {name: camera.identity(data)["sha256"] for name, data in self.source_payloads.items()}
        self.save_contract()
        self.root_patch = patch.object(camera, "ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.root_patch.stop)
        self.hash_patch = patch.object(camera, "CONTRACT_SHA256", camera.identity(camera.encoded(self.contract))["sha256"])
        self.hash_patch.start()
        self.addCleanup(self.hash_patch.stop)

    def write(self, name, data):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return {"path": name, **camera.identity(data)}

    def save_contract(self):
        self.write(camera.CONFIG, camera.encoded(self.contract))

    def stage(self):
        return camera.stage_inputs(self.root, self.output)

    def native_arguments(self, output=None):
        receipt = json.loads((self.output / camera.RECEIPT).read_text())
        paths = [str(self.output / row["path"]) for row in receipt["files"]
                 if row["path"].startswith("source/") and "/tools/" not in row["path"]]
        return ["--output-dir", str(output or self.root / "native-output"), *paths]

    def native(self, arguments=None):
        script = str(self.output / "source/tools/verify_camera_apk.py")
        argv = [script, *(arguments or self.native_arguments())]
        stdout, stderr, code = io.StringIO(), io.StringIO(), 0
        with patch.object(sys, "argv", argv), contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            try:
                runpy.run_path(script, run_name="__main__")
            except SystemExit as error:
                code = error.code
        return subprocess.CompletedProcess(argv, code, stdout.getvalue(), stderr.getvalue())

    def installed_source(self):
        root = self.root / "android"
        shutil.copytree(self.output / "source", root / camera.NAMESPACE)
        for name, data in self.source_payloads.items():
            path = root / "build/soong" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        for name, data in {**self.runtime_payloads, "Android.bp": self.runtime_bp}.items():
            path = root / "vendor/xiaomi/nezha" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        return root

    def test_real_contract_is_pinned_and_does_not_admit_images(self):
        raw = (ROOT / camera.CONFIG).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), "0db6561f34300f7c7aea527ed5a60513f3f12bb241e8d448820a8467e23870ac")
        value = json.loads(raw)
        self.assertEqual(value["apk"]["sha256"], "7bce1fb140802511bb3d6527f6fcc25ef7558f278d24229755413d3a9b42199e")
        self.assertEqual(value["apk"]["size_bytes"], 204365218)
        self.assertEqual(value["scope"], camera.SCOPE)

    def test_same_input_with_tighter_read_bound_retains_original_identity(self):
        path = self.root / camera.CONFIG
        reader = camera.Reader()
        data = reader.read(path, maximum=camera.MAX_APK)
        self.assertEqual(reader.read(path, maximum=camera.MAX_METADATA), data)
        reader.recheck()
        path.write_bytes(data + b" ")
        with self.assertRaises(camera.CameraApkError):
            reader.recheck()

    def test_stage_is_reproducible_and_producer_copies_verified_bytes(self):
        first = self.stage()
        second = self.root / "artifacts/repeated"
        self.assertEqual(first, camera.stage_inputs(self.root, second))
        verified = camera.verify_bundle(self.output)
        self.assertTrue(verified["readback_verified"])
        result = self.native()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.root / "native-output/verified/MiuiCamera.apk").read_bytes(), self.apk)
        success = json.loads((self.root / "native-output/camera-apk-checked.json").read_text())
        self.assertEqual(success["apk"], camera.identity(self.apk))
        self.assertFalse(success["image_adoption_allowed"])
        self.assertEqual((self.capture_dir / "files/0001").read_bytes(), self.apk)

    def test_source_contract_is_only_one_namespace_without_product_wiring(self):
        self.stage()
        install = json.loads((self.output / camera.INSTALL).read_text())
        self.assertTrue(all(row["destination"].startswith(camera.NAMESPACE + "/") for row in install["files"]))
        self.assertFalse(any(row["destination"].endswith((".mk", ".te", "mac_permissions.xml")) for row in install["files"]))
        self.assertEqual(install["scope"]["product_packages"], [])
        self.assertEqual(install["scope"]["make_namespace_exports"], [])
        bp = (self.output / "source/Android.bp").read_text()
        self.assertIn('apk: ":nezha_factory_camera_verified_apk"', bp)
        self.assertIn(':nezha_factory_camera_inputs_check{verified/MiuiCamera.apk}', bp)
        for forbidden in ("installable:", "required:", "overrides:", "source_module_name:", "dex_preopt:", "skip_preprocessed", "certificate:", "missing_optional", "PRODUCT_PACKAGES"):
            self.assertNotIn(forbidden, bp)
        plan = install["build_requirements"]
        self.assertFalse(plan["execution_runner_admitted"])
        self.assertTrue(plan["reject_install_writes_in_dependency_closure"])
        self.assertTrue(plan["protect_install_trees_and_images_readonly_through_all_aliases"])
        self.assertEqual(set(plan["required_output_roles"]), {"apk", "packaging_stamp", "strict_library_status", "dexpreopt_config", "odex", "vdex"})

    def test_old_or_modified_apk_fails_before_publication(self):
        (self.capture_dir / "files/0001").write_bytes(b"a different old APK")
        with self.assertRaises(camera.CameraApkError):
            self.stage()
        self.assertFalse(self.output.exists())

    def test_unpinned_control_or_contract_cannot_change_admission(self):
        for path in (self.root / camera.CONFIG, self.root / self.contract["review"]["path"],
                     self.root / self.contract["capture"]["path"]):
            before = path.read_bytes()
            with self.subTest(path=path.name):
                path.write_bytes(before + b" ")
                with self.assertRaises(camera.CameraApkError):
                    self.stage()
                path.write_bytes(before)
                self.assertFalse(self.output.exists())

    def test_duplicate_json_and_weakened_reviewed_scope_fail(self):
        raw = camera.encoded(self.contract).replace(b'"device": "nezha",', b'"device": "nezha", "device": "nezha",')
        (self.root / camera.CONFIG).write_bytes(raw)
        with patch.object(camera, "CONTRACT_SHA256", camera.identity(raw)["sha256"]), self.assertRaises(camera.CameraApkError):
            self.stage()
        value = copy.deepcopy(self.contract)
        value["scope"]["image_adoption_allowed"] = True
        raw = camera.encoded(value)
        (self.root / camera.CONFIG).write_bytes(raw)
        with patch.object(camera, "CONTRACT_SHA256", camera.identity(raw)["sha256"]), self.assertRaises(camera.CameraApkError):
            self.stage()

    def test_existing_public_nested_and_symlinked_outputs_fail(self):
        paths = [self.root / "public-output", self.capture_dir / "nested",
                 (self.root / self.contract["runtime_bundle"]["path"]).parent / "nested"]
        self.output.mkdir()
        paths.append(self.output)
        link = self.root / "artifacts/link"
        link.symlink_to(self.root / "artifacts", target_is_directory=True)
        paths.append(link / "child")
        for output in paths:
            with self.subTest(output=output), self.assertRaises((camera.CameraApkError, OSError)):
                camera.stage_inputs(self.root, output)

    def test_symlinked_input_rejected(self):
        path = self.capture_dir / "files/0001"
        other = self.root / "actual-apk"
        path.rename(other)
        path.symlink_to(other)
        with self.assertRaises(camera.CameraApkError):
            self.stage()

    def test_resealed_blueprint_receipt_and_extra_files_do_not_pass(self):
        self.stage()
        bp = self.output / "source/Android.bp"
        before = bp.read_bytes()
        bp.write_bytes(before.replace(b'enforce_uses_libs: true', b'enforce_uses_libs: false'))
        receipt_path = self.output / camera.RECEIPT
        receipt = json.loads(receipt_path.read_text())
        row = next(row for row in receipt["files"] if row["path"] == "source/Android.bp")
        row.update(camera.identity(bp.read_bytes()))
        receipt_path.write_bytes(camera.encoded(receipt))
        with self.assertRaises(camera.CameraApkError):
            camera.verify_bundle(self.output)
        self.assertNotEqual(self.native().returncode, 0)
        self.assertFalse((self.root / "native-output/camera-apk-checked.json").exists())

    def test_extra_empty_directory_is_rejected(self):
        self.stage()
        (self.output / "source/extra").mkdir()
        with self.assertRaises(camera.CameraApkError):
            camera.verify_bundle(self.output)

    def test_late_extra_file_is_rejected_after_input_recheck(self):
        self.stage()
        original = camera.Reader.recheck
        def changed(reader):
            original(reader)
            (self.output / "source/Android.mk").write_text("unexpected product wiring")
        with patch.object(camera.Reader, "recheck", changed), self.assertRaises(camera.CameraApkError):
            camera.verify_bundle(self.output)

    def test_native_missing_duplicate_extra_and_modified_controls_fail(self):
        self.stage()
        args = self.native_arguments()
        for changed in (args[:-1], [*args, args[-1]], [*args[:-1], args[-2]]):
            with self.subTest(arguments=changed[-2:]):
                self.assertNotEqual(self.native(changed).returncode, 0)
                self.assertFalse((self.root / "native-output/camera-apk-checked.json").exists())
        control = self.output / "source/provenance/review.json"
        control.write_bytes(control.read_bytes() + b" ")
        self.assertNotEqual(self.native().returncode, 0)
        self.assertFalse((self.root / "native-output/verified/MiuiCamera.apk").exists())

    def test_native_output_reuse_overlap_and_symlink_fail(self):
        self.stage()
        self.assertNotEqual(self.native(self.native_arguments(self.output / "source/new" )).returncode, 0)
        link = self.root / "linked-output"
        link.symlink_to(self.root, target_is_directory=True)
        self.assertNotEqual(self.native(self.native_arguments(link / "new")).returncode, 0)
        self.assertEqual(self.native().returncode, 0)
        self.assertNotEqual(self.native().returncode, 0)

    def test_native_rollback_removes_only_its_published_output(self):
        self.stage()
        spec = importlib.util.spec_from_file_location("camera_native_fixture", self.output / "source/tools/verify_camera_apk.py")
        native = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(native)
        link = native.os.link
        def fail_receipt(source, target, **kwargs):
            if Path(target).name == "camera-apk-checked.json":
                raise OSError(errno.EIO, "injected publication failure")
            return link(source, target, **kwargs)
        with patch.object(native.os, "link", fail_receipt), self.assertRaises(OSError):
            native.main(self.native_arguments())
        self.assertFalse((self.root / "native-output/verified/MiuiCamera.apk").exists())
        self.assertFalse((self.root / "native-output/camera-apk-checked.json").exists())

    def test_installed_readback_requires_exact_source_and_runtime_inputs(self):
        self.stage()
        root = self.installed_source()
        result = subprocess.CompletedProcess([], 0, str(root / "build/soong") + "\n" + self.contract["source_requirements"]["revision"] + "\n", "")
        with patch.object(camera.subprocess, "run", return_value=result):
            checked = camera.verify_installed(self.output, root)
            self.assertTrue(checked["nine_runtime_inputs_and_blueprint_verified"])
            self.assertFalse(checked["native_execution_admitted"])
            self.assertFalse(checked["product_membership_verified"])
            (root / "vendor/xiaomi/nezha/Android.bp").write_text("changed provider")
            with self.assertRaises(camera.CameraApkError):
                camera.verify_installed(self.output, root)

    def test_installed_extra_file_and_wrong_source_revision_fail(self):
        self.stage()
        root = self.installed_source()
        result = subprocess.CompletedProcess([], 0, str(root / "build/soong") + "\n" + "0" * 40 + "\n", "")
        with patch.object(camera.subprocess, "run", return_value=result), self.assertRaises(camera.CameraApkError):
            camera.verify_installed(self.output, root)
        (root / camera.NAMESPACE / "Android.mk").write_text("unexpected")
        with self.assertRaises(camera.CameraApkError):
            camera.verify_installed(self.output, root)


if __name__ == "__main__":
    unittest.main()
