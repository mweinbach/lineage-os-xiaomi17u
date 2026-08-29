"""Strict Camera runtime selection checks using synthetic offline inputs."""

import copy
import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import camera_runtime_inputs as camera
from scripts import vendor_inputs as vendor
import test_vendor_inputs as fixtures


ROOT = Path(__file__).resolve().parents[1]


class RuntimeVendorTests(unittest.TestCase):
    setUp = fixtures.VendorInputTests.setUp
    save_metadata = fixtures.VendorInputTests.save_metadata
    add_extras = fixtures.VendorInputTests.add_extras
    stage = fixtures.VendorInputTests.stage
    assert_no_output = fixtures.VendorInputTests.assert_no_output

    def runtime_inputs(self, graph=None):
        graph = graph or {"runtime.parent": ["runtime.second", "runtime.leaf"],
                          "runtime.second": ["runtime.leaf"], "runtime.leaf": []}
        specs = []
        for name, dependencies in graph.items():
            jar = f"/system_ext/framework/original-{name}.jar"
            attributes = f' name="{name}" file="{jar}"'
            if dependencies:
                attributes += ' dependency="' + ":".join(dependencies) + '"'
            specs += [(jar, "dex_jar", fixtures.dex_jar()),
                      (f"/system_ext/etc/permissions/{name}.xml", "xml",
                       f"<permissions><library{attributes}/></permissions>".encode())]
        self.add_extras(specs)
        for module in self.selection["modules"]:
            if module["type"] == "dex_jar":
                name = Path(module["runtime_path"]).stem.removeprefix("original-")
                module["runtime_library"] = {"name": name,
                                             "registration": f"/system_ext/etc/permissions/{name}.xml",
                                             "uses_libs": graph[name]}
        self.save_selection()
        return self.selection_path

    def save_selection(self):
        self.selection_path.write_text(json.dumps(self.selection))

    def replace_xml(self, name, raw):
        runtime = f"/system_ext/etc/permissions/{name}.xml"
        row = next(row for row in self.selection["modules"] if row["runtime_path"] == runtime)
        captured = next(row for row in self.capture["files"] if "/system_ext" + row["path"] == runtime)
        for record in (row, captured):
            record.update(sha256=hashlib.sha256(raw).hexdigest(), size_bytes=len(raw))
        (self.capture_dir / captured["output_path"]).write_bytes(raw)
        self.capture_path.write_text(json.dumps(self.capture))
        self.save_selection()

    def test_runtime_graph_stages_exact_names_paths_and_ordered_required_subtrees(self):
        selection = self.runtime_inputs()
        receipt = self.stage(selection=selection)
        self.assertTrue(receipt["verification"]["runtime_registration_graph_checked"])
        self.assertFalse(receipt["verification"]["full_dependency_closure_verified"])
        self.assertFalse(receipt["verification"]["signature_or_elf_checks_disabled"])
        blueprint = (self.output / "Android.bp").read_text()
        self.assertIn('name: "runtime.parent"', blueprint)
        self.assertIn('stem: "original-runtime.parent"', blueprint)
        self.assertIn('uses_libs: ["runtime.second", "runtime.leaf"]', blueprint)
        self.assertIn('uses_libs: []', blueprint)
        self.assertIn('system_ext_specific: true', blueprint)
        self.assertNotIn('provides_uses_lib', blueprint)
        self.assertNotIn('dex_preopt', blueprint)
        for name in ("runtime.parent", "runtime.second", "runtime.leaf"):
            self.assertIn(name, (self.output / "nezha-vendor.mk").read_text())

    def test_unregistered_legacy_profile_does_not_gain_provider_fields_or_new_outputs(self):
        selection = self.add_extras([("/system_ext/framework/legacy.jar", "dex_jar", fixtures.dex_jar())])
        receipt = self.stage(selection=selection)
        self.assertNotIn("runtime_registration_graph_checked", receipt["verification"])
        self.assertNotIn("uses_libs", (self.output / "Android.bp").read_text())
        self.assertEqual(len(receipt["generated_files"]), 5)

    def test_xml_name_path_and_required_order_must_match_actual_captured_bytes(self):
        selection = self.runtime_inputs()
        wrong = [
            b'<permissions><library name="runtime.parent" file="/system/framework/original-runtime.parent.jar" dependency="runtime.second:runtime.leaf"/></permissions>',
            b'<permissions><library name="prefixed.runtime.parent" file="/system_ext/framework/original-runtime.parent.jar" dependency="runtime.second:runtime.leaf"/></permissions>',
            b'<permissions><library name="runtime.parent" file="/system_ext/framework/original-runtime.parent.jar" dependency="runtime.leaf:runtime.second"/></permissions>',
            b'<permissions><library name="runtime.parent" file="/system_ext/framework/original-runtime.parent.jar"/></permissions>',
        ]
        for raw in wrong:
            with self.subTest(raw=raw):
                self.replace_xml("runtime.parent", raw)
                with self.assertRaises(vendor.VendorInputError):
                    self.stage(selection=selection)
                self.assert_no_output()

    def test_hidden_dependency_or_registration_policy_is_not_ignored(self):
        selection = self.runtime_inputs({"runtime.leaf": []})
        start = '<permissions><library name="runtime.leaf" file="/system_ext/framework/original-runtime.leaf.jar"'
        for suffix in (' dependency="runtime.hidden"/></permissions>', ' dependency=""/></permissions>',
                       ' on-bootclasspath-since="35"/></permissions>',
                       '/><privapp-permissions package="example"/></permissions>',
                       '>unexpected</library></permissions>'):
            with self.subTest(suffix=suffix):
                self.replace_xml("runtime.leaf", (start + suffix).encode())
                with self.assertRaises(vendor.VendorInputError):
                    self.stage(selection=selection)
                self.assert_no_output()

    def test_duplicate_runtime_registration_cannot_hide_in_another_selected_xml(self):
        selection = self.runtime_inputs()
        self.replace_xml("runtime.second", b'<permissions><library name="runtime.parent" file="/system_ext/framework/original-runtime.parent.jar" dependency="runtime.second:runtime.leaf"/></permissions>')
        with self.assertRaises(vendor.VendorInputError):
            self.stage(selection=selection)
        self.assert_no_output()

    def test_registration_dtd_and_namespace_ambiguities_are_rejected(self):
        selection = self.runtime_inputs({"runtime.leaf": []})
        base = '<permissions><library name="runtime.leaf" file="/system_ext/framework/original-runtime.leaf.jar"/></permissions>'
        for raw in ('<!DOCTYPE permissions []>' + base,
                    base.replace('<library', '<library xmlns="urn:unexpected"'),
                    base.replace('<permissions>', '<permissions other="value">')):
            with self.subTest(raw=raw):
                self.replace_xml("runtime.leaf", raw.encode())
                with self.assertRaises(vendor.VendorInputError):
                    self.stage(selection=selection)
                self.assert_no_output()

    def test_missing_registration_and_unknown_dependency_fail_before_publication(self):
        selection = self.runtime_inputs()
        original = copy.deepcopy(self.selection)
        for kind in ("missing_xml", "unknown_dependency", "duplicate_xml"):
            self.selection = copy.deepcopy(original)
            jar = self.selection["modules"][0]["runtime_library"]
            if kind == "missing_xml":
                jar["registration"] = "/system_ext/etc/permissions/absent.xml"
            elif kind == "unknown_dependency":
                jar["uses_libs"] = ["not_installed"]
            else:
                self.selection["modules"][2]["runtime_library"]["registration"] = jar["registration"]
            self.save_selection()
            with self.subTest(kind=kind), self.assertRaises(vendor.VendorInputError):
                self.stage(selection=selection)
            self.assert_no_output()

    def test_cycles_and_duplicate_or_qualified_names_fail(self):
        selection = self.runtime_inputs()
        original = copy.deepcopy(self.selection)
        changes = [lambda m: m[0]["runtime_library"].update(uses_libs=["runtime.parent"]),
                   lambda m: m[4]["runtime_library"].update(uses_libs=["runtime.parent"]),
                   lambda m: m[0]["runtime_library"].update(uses_libs=["runtime.leaf", "runtime.leaf"]),
                   lambda m: m[0]["runtime_library"].update(name="//vendor/example:runtime.parent"),
                   lambda m: m[0]["runtime_library"].update(name="prebuilt_runtime.parent"),
                   lambda m: m[2]["runtime_library"].update(name="RUNTIME.PARENT")]
        for index, change in enumerate(changes):
            self.selection = copy.deepcopy(original)
            change(self.selection["modules"])
            self.save_selection()
            with self.subTest(index=index), self.assertRaises(vendor.VendorInputError):
                self.stage(selection=selection)
            self.assert_no_output()

    def test_provider_alias_and_checker_override_fields_remain_unsupported(self):
        selection = self.runtime_inputs()
        original = copy.deepcopy(self.selection)
        for field, value in (("provides_uses_lib", "runtime.parent"), ("optional_uses_libs", []),
                             ("enforce_uses_libs", False), ("dex_preopt", {"enabled": False})):
            self.selection = copy.deepcopy(original)
            self.selection["modules"][0][field] = value
            self.save_selection()
            with self.subTest(field=field), self.assertRaises(vendor.VendorInputError):
                self.stage(selection=selection)
            self.assert_no_output()


class CameraRuntimeContractTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.contract = json.loads((ROOT / "config/nezha-camera-runtime.json").read_text())
        self.contract_path = self.root / "contract.json"
        self.output = self.root / "artifacts/runtime-preparation"
        selection = json.loads((ROOT / "vendor/xiaomi/nezha/camera-selection.json").read_text())
        selection["package_sha256"] = self.contract["package_sha256"]
        self.base = self.write("base-selection.json", (json.dumps(selection) + "\n").encode())
        self.contract["base_selection"] = self.base
        factory = {"schema_version": 1, "packages": {"factory": {"sha256": selection["package_sha256"]}},
                   "evidence": {"factory_camera_selection": self.base}}
        self.contract["factory_record"] = self.write("factory-record.json", json.dumps(factory).encode())
        provider = json.loads((ROOT / "research/dex-import-uses-library.json").read_text())
        self.contract["provider_record"] = self.write("provider-record.json", json.dumps(provider).encode())
        self.contract["source_patch"] = self.write(provider["patch"]["path"],
                                                   (ROOT / provider["patch"]["path"]).read_bytes())
        self.save_contract()

    def write(self, relative, raw):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        return {"path": relative, "sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}

    def save_contract(self):
        self.contract_path.write_text(json.dumps(self.contract))

    def prepare(self):
        return camera.prepare(self.contract_path, self.output, workspace_root=self.root)

    def test_preparation_preserves_every_proprietary_hash_path_and_scope(self):
        receipt = self.prepare()
        result = json.loads((self.output / "camera-runtime-selection.json").read_text())
        base = json.loads((self.root / self.base["path"]).read_text())
        for old, new in zip(base["modules"], result["modules"]):
            self.assertEqual(old, {key: value for key, value in new.items() if key != "runtime_library"})
        self.assertEqual(receipt["runtime_modules"], ["camerax-vendor-extensions.jar",
                         "com.xiaomi.hardware.camera.companion-V1", "miui-cameraopt",
                         "vendor.xiaomi.hardware.postprocservice-V1-java"])
        self.assertFalse(receipt["actual_xml_and_blob_hashes_checked"])
        self.assertTrue(all(value is False for value in receipt["scope"].values()))
        with self.assertRaises(vendor.VendorInputError):
            self.prepare()

    def test_contract_rejects_changed_base_hash_package_patch_and_broader_scope(self):
        original = copy.deepcopy(self.contract)
        changes = [lambda c: c["base_selection"].update(sha256="0" * 64),
                   lambda c: c.update(package_sha256="0" * 64),
                   lambda c: c["source_patch"].update(sha256="0" * 64),
                   lambda c: c["scope"].update(permission_grants_added=True),
                   lambda c: c["source"].update(revision="0" * 40),
                   lambda c: c["libraries"].pop(),
                   lambda c: c["libraries"][0].update(registration="/system_ext/etc/permissions/absent.xml")]
        for index, change in enumerate(changes):
            self.contract = copy.deepcopy(original)
            change(self.contract)
            self.save_contract()
            with self.subTest(index=index), self.assertRaises(vendor.VendorInputError):
                self.prepare()
            self.assertFalse(self.output.exists())

    def test_preparation_rejects_duplicate_json_keys_and_reference_traversal(self):
        self.contract_path.write_text(self.contract_path.read_text().replace('"schema_version": 1',
                                                                            '"schema_version": 1, "schema_version": 1', 1))
        with self.assertRaises(vendor.VendorInputError):
            self.prepare()
        self.contract["source_patch"]["path"] = "../escape"
        self.save_contract()
        with self.assertRaises(vendor.VendorInputError):
            self.prepare()

    def test_preparation_rejects_symlinked_inputs_and_public_output(self):
        original = self.root / self.base["path"]
        saved = self.root / "saved.json"
        original.rename(saved)
        original.symlink_to(saved)
        with self.assertRaises(vendor.VendorInputError):
            self.prepare()
        original.unlink()
        saved.rename(original)
        with self.assertRaises(vendor.VendorInputError):
            camera.prepare(self.contract_path, self.root / "public-output", workspace_root=self.root)

    def test_cli_reports_symlinked_output_ancestor_as_an_admission_error(self):
        self.output.parent.mkdir()
        real = self.root / "real-output"
        real.mkdir()
        link = self.output.parent / "linked"
        link.symlink_to(real, target_is_directory=True)
        errors = io.StringIO()
        with contextlib.redirect_stderr(errors):
            result = camera.main(["--contract", str(self.contract_path), "--workspace-root", str(self.root),
                                  "prepare", "--output", str(link / "candidate")])
        self.assertEqual(result, 2)
        self.assertIn("camera runtime admission failed", errors.getvalue())
        self.assertFalse((real / "candidate").exists())

    def test_preparation_rechecks_output_before_publishing_a_bound_receipt(self):
        real_write = vendor._write_file

        def corrupt_previous(staging, name, content):
            result = real_write(staging, name, content)
            if name == "camera-runtime-admission.json":
                path = staging / "camera-runtime-selection.json"
                path.write_bytes(path.read_bytes() + b" ")
            return result

        with patch.object(vendor, "_write_file", side_effect=corrupt_previous), self.assertRaises(vendor.VendorInputError):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_source_verification_checks_pinned_revision_and_all_expected_bytes(self):
        source = self.root / "source/build/soong"
        source.mkdir(parents=True)
        records = self.contract["source"]["files"]
        for index, row in enumerate(records):
            raw = f"synthetic source {index}\n".encode()
            path = source / row["path"]
            path.parent.mkdir(exist_ok=True)
            path.write_bytes(raw)
            row["after_sha256"] = hashlib.sha256(raw).hexdigest()
        provider_path = self.root / self.contract["provider_record"]["path"]
        provider = json.loads(provider_path.read_text())
        provider["patch"]["files"] = records
        self.contract["provider_record"] = self.write(self.contract["provider_record"]["path"], json.dumps(provider).encode())
        self.save_contract()
        command = subprocess.CompletedProcess([], 0, str(source) + "\n" + self.contract["source"]["revision"] + "\n", "")
        with patch.object(camera.subprocess, "run", return_value=command) as run:
            checked = camera.verify_source(self.contract_path, source, workspace_root=self.root)
            self.assertEqual(len(checked["files"]), 3)
            self.assertFalse(checked["source_modified"])
            self.assertFalse(checked["native_build_executed"])
            self.assertEqual(run.call_args.args[0][-3:], ["rev-parse", "--show-toplevel", "HEAD"])
            (source / "java/java.go").write_text("unexpected local change")
            with self.assertRaises(vendor.VendorInputError):
                camera.verify_source(self.contract_path, source, workspace_root=self.root)
        wrong = subprocess.CompletedProcess([], 0, str(source) + "\n" + "0" * 40 + "\n", "")
        with patch.object(camera.subprocess, "run", return_value=wrong), self.assertRaises(vendor.VendorInputError):
            camera.verify_source(self.contract_path, source, workspace_root=self.root)

    def test_base_source_requires_absent_added_file_and_exact_preimages(self):
        source = self.root / "source/build/soong"
        (source / "java").mkdir(parents=True)
        records = self.contract["source"]["files"]
        for index, row in enumerate(records):
            if row["before_sha256"] is None:
                continue
            raw = f"synthetic preimage {index}\n".encode()
            (source / row["path"]).write_bytes(raw)
            row["before_sha256"] = hashlib.sha256(raw).hexdigest()
        provider_path = self.root / self.contract["provider_record"]["path"]
        provider = json.loads(provider_path.read_text())
        provider["patch"]["files"] = records
        self.contract["provider_record"] = self.write(self.contract["provider_record"]["path"], json.dumps(provider).encode())
        self.save_contract()
        command = subprocess.CompletedProcess([], 0, str(source) + "\n" + self.contract["source"]["revision"] + "\n", "")
        with patch.object(camera.subprocess, "run", return_value=command):
            checked = camera.verify_source(self.contract_path, source, workspace_root=self.root, state="base")
            self.assertEqual(checked["files"][-1], {"path": "java/dex_import_test.go", "absent": True})
            added = source / "java/dex_import_test.go"
            added.symlink_to(source / "absent-target")
            with self.assertRaises(vendor.VendorInputError):
                camera.verify_source(self.contract_path, source, workspace_root=self.root, state="base")
            added.unlink()
            (source / "java/Android.bp").write_text("unexpected original source change")
            with self.assertRaises(vendor.VendorInputError):
                camera.verify_source(self.contract_path, source, workspace_root=self.root, state="base")


if __name__ == "__main__":
    unittest.main()
