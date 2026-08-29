"""Offline combined metadata admission tests; inert payloads are not ROM images."""

import ast
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from scripts import target_files_metadata as legacy
from scripts import target_files_metadata_combined as m


WORKSPACE = m.ROOT


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


class CombinedSourceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.reader = m.Reader()
        _, self.composition, self.controls = m._controls(
            WORKSPACE, self.reader, source_contract=m.COMBINED_SOURCE_CONTRACT)
        self.reader.recheck()
        for path, raw in self.controls.items():
            write(self.root / path, raw)
        self.descriptor = json.loads(self.controls[m.COMBINED_SOURCE_CONTRACT])
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native process forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))

    def compose(self, **kwargs):
        return m.compose_sources(self.root, source_contract=self.root / m.COMBINED_SOURCE_CONTRACT, **kwargs)

    def save(self, value=None):
        write(self.root / m.COMBINED_SOURCE_CONTRACT, m.encoded(value or self.descriptor))

    def test_legacy_bytes_and_serialized_composition_are_unchanged(self):
        self.assertEqual(m.FROZEN_BASE_IDENTITY, m.identity((WORKSPACE / m.FROZEN_BASE).read_bytes()))
        expected = {"sha256": "6cc3a2bc48603a8eb8b15082252350dc550c0dfc669af24d96e6b4e1a317ad0f", "size_bytes": 3971}
        before = legacy.encoded(legacy.compose_sources(WORKSPACE))
        self.assertEqual(expected, legacy.identity(before))
        self.compose()
        self.assertEqual(before, legacy.encoded(legacy.compose_sources(WORKSPACE)))
        self.assertEqual((m.FROZEN_BASE,), legacy.CONTROL_TOOLS)
        self.assertNotEqual(m.compose_sources.__globals__, legacy.compose_sources.__globals__)

    def test_all_seven_transitions_and_ten_final_guards_bound(self):
        result = self.compose()
        self.assertEqual(7, len(result["ordered_patches"]))
        self.assertEqual(8, len(result["contracts"]))
        self.assertEqual(10, len(result["initial_source_files"]))
        self.assertEqual(10, len(result["final_source_files"]))
        self.assertEqual(self.descriptor["source_transitions"], result["source_transitions"])
        self.assertEqual(self.descriptor["final_source_files"], result["final_source_files"])
        self.assertFalse(result["patches_applied_by_this_tool"])
        self.assertFalse(result["whole_source_tree_verified"])

    def test_no_implicit_selection(self):
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "explicit"):
            m.compose_sources(self.root)

    def test_explicit_selector_must_match_copied_contract(self):
        wrong = self.root / "wrong.json"
        wrong.write_bytes(b'{}\n')
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "selected"):
            m.compose_sources(self.root, source_contract=wrong)

    def test_relative_selector_uses_control_root_and_absolute_selector_compares_public_bytes(self):
        relative = m.compose_sources(self.root, source_contract=m.COMBINED_SOURCE_CONTRACT)
        absolute = m.compose_sources(self.root, source_contract=WORKSPACE / m.COMBINED_SOURCE_CONTRACT)
        self.assertEqual(relative, absolute)
        changed = copy.deepcopy(self.descriptor)
        changed["limitations"].append("Inert copied-control mutation.")
        self.save(changed)
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "selected"):
            m.compose_sources(self.root, source_contract=WORKSPACE / m.COMBINED_SOURCE_CONTRACT)

    def test_descriptor_unknown_fields_and_unbounded_nontext_limitations_rejected(self):
        for mutation in (lambda d: d.update(extra=True), lambda d: d.update(limitations=[]),
                         lambda d: d.update(limitations=[False]), lambda d: d.update(limitations=["x" * 2049])):
            changed = copy.deepcopy(self.descriptor)
            mutation(changed)
            self.save(changed)
            with self.subTest(mutation=mutation), self.assertRaises(m.TargetFilesMetadataError):
                self.compose()

    def test_descriptor_rejects_reordered_duplicate_missing_and_extra_source_rows(self):
        mutations = (
            lambda d: d["source_transitions"].reverse(),
            lambda d: d["source_transitions"].append(copy.deepcopy(d["source_transitions"][0])),
            lambda d: d["final_source_files"].pop(),
            lambda d: d["initial_source_files"][0].update(sha256="0" * 64),
            lambda d: d["final_source_files"][0].update(size_bytes=True),
            lambda d: d["final_source_files"][0].update(extra="unreviewed"),
            lambda d: d["required_contracts"].reverse(),
            lambda d: d["required_contracts"][0].update(path="elsewhere.json"),
        )
        for mutation in mutations:
            changed = copy.deepcopy(self.descriptor)
            mutation(changed)
            self.save(changed)
            with self.subTest(mutation=mutations.index(mutation)), self.assertRaises(m.TargetFilesMetadataError):
                self.compose()

    def test_descriptor_rejects_rebased_or_historical_transition_substitution(self):
        for path in ("before", "after", "historical_transition"):
            changed = copy.deepcopy(self.descriptor)
            changed["rebased_readonly_transition"][path] = {}
            self.save(changed)
            with self.subTest(path=path), self.assertRaisesRegex(m.TargetFilesMetadataError, "readonly transition"):
                self.compose()

    def test_descriptor_rejects_scope_semantic_boolean_aliases_and_profile_change(self):
        mutations = (
            lambda d: d["scope"].update(native_vintf_verified=True),
            lambda d: d["scope"].update(source_modified=0),
            lambda d: d["semantics"].update(source_hash_fallback_allowed=True),
            lambda d: d["semantics"].update(native_entrypoint_self_contained=1),
            lambda d: d["metadata_profile"].update(sha256="0" * 64),
            lambda d: d.update(schema_version=True),
            lambda d: d["project"].update(branch="cnb"),
            lambda d: d["readonly_macro"].update(body_sha256="0" * 64),
        )
        for index, mutation in enumerate(mutations):
            changed = copy.deepcopy(self.descriptor)
            mutation(changed)
            self.save(changed)
            with self.subTest(mutation=index), self.assertRaises(m.TargetFilesMetadataError):
                self.compose()

    def test_every_readonly_upgrade_field_is_validated(self):
        for name in self.descriptor["readonly_upgrade"]:
            changed = copy.deepcopy(self.descriptor)
            changed["readonly_upgrade"][name] = None
            self.save(changed)
            with self.subTest(name=name), self.assertRaisesRegex(m.TargetFilesMetadataError, "readonly source upgrade"):
                self.compose()

    def test_both_predecessor_identities_are_required(self):
        for name in ("metadata_predecessor_composition", "readonly_legacy_predecessor_composition"):
            changed = copy.deepcopy(self.descriptor)
            changed[name]["sha256"] = "0" * 64
            self.save(changed)
            with self.subTest(name=name), self.assertRaises(m.TargetFilesMetadataError):
                self.compose()

    def test_each_original_contract_remains_frozen(self):
        for path in m.COMBINED_CONTRACTS:
            original = (self.root / path).read_bytes()
            write(self.root / path, original + b"\n")
            with self.subTest(path=path), self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
                self.compose()
            write(self.root / path, original)

    def test_each_original_patch_remains_frozen(self):
        for path in m.COMBINED_PATCHES:
            original = (self.root / path).read_bytes()
            write(self.root / path, original + b"\n")
            with self.subTest(path=path), self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
                self.compose()
            write(self.root / path, original)

    def test_duplicate_descriptor_key_refused(self):
        raw = (self.root / m.COMBINED_SOURCE_CONTRACT).read_bytes()
        write(self.root / m.COMBINED_SOURCE_CONTRACT, raw.replace(b'{\n', b'{\n  "schema_version": 1,\n', 1))
        with self.assertRaises(m.TargetFilesMetadataError):
            self.compose()

    def test_source_contract_symlink_and_hardlink_refused(self):
        path = self.root / m.COMBINED_SOURCE_CONTRACT
        original = path.read_bytes()
        alternate = self.root / "alternate.json"
        alternate.write_bytes(original)
        path.unlink()
        path.symlink_to(alternate)
        with self.assertRaises(m.TargetFilesMetadataError):
            self.compose()
        path.unlink()
        os.link(alternate, path)
        with self.assertRaises(m.TargetFilesMetadataError):
            self.compose()

    def test_native_checker_is_deterministic_self_contained_and_does_not_load_private_code(self):
        first = m.runtime_tool_payloads(self.controls)
        self.assertEqual(first, m.runtime_tool_payloads(self.controls))
        self.assertEqual(["tools/target_files_metadata.py"], list(first))
        raw = first["tools/target_files_metadata.py"]
        modules = {node.module for node in ast.walk(ast.parse(raw)) if isinstance(node, ast.ImportFrom)}
        self.assertEqual({"__future__", "pathlib"}, modules)
        namespace = {"__name__": "isolated_combined_checker", "__file__": str(self.root / "tools/checker.py")}
        with mock.patch.object(os, "open", side_effect=AssertionError("private code file read forbidden")):
            exec(compile(raw, namespace["__file__"], "exec"), namespace)
        self.assertEqual(self.composition, namespace["compose_sources"](
            self.root, source_contract=m.COMBINED_SOURCE_CONTRACT))
        self.assertEqual(first, namespace["runtime_tool_payloads"](self.controls))

    def test_native_generation_rejects_changed_frozen_base(self):
        changed = dict(self.controls)
        changed[m.FROZEN_BASE] += b"\n"
        with self.assertRaisesRegex(ValueError, "base identity"):
            m.runtime_tool_payloads(changed)

    def test_frozen_source_transforms_leave_readers_and_publication_helpers_unchanged(self):
        original = ast.parse(self.controls[m.FROZEN_BASE])
        derived = ast.parse(m._base_body(self.controls[m.FROZEN_BASE]))
        def definitions(tree):
            return {node.name: ast.dump(node) for node in tree.body
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
        before, after = definitions(original), definitions(derived)
        self.assertEqual(set(before), set(after))
        self.assertEqual({"stage", "verify_bundle", "install", "selection"},
                         {name for name in before if before[name] != after[name]})

    def test_main_boundary_and_hook_are_counted_after_base_identity(self):
        original = self.controls[m.FROZEN_BASE]
        for changed, message in ((original + b"\n", "main boundary"),
                (original.replace(b"def stage(", b"def unexpected_stage("), "base hook")):
            with self.subTest(message=message), mock.patch.object(m, "FROZEN_BASE_IDENTITY", m.identity(changed)):
                with self.assertRaisesRegex(ValueError, message):
                    m._base_body(changed)

    def test_bootstrap_reader_rejects_symlink_hardlink_and_changed_bytes_before_execution(self):
        path = self.root / "base.py"
        original = self.controls[m.FROZEN_BASE]
        path.write_bytes(original)
        self.assertEqual(original, m._read_bootstrap_base(path))
        alias = self.root / "alias.py"
        alias.symlink_to(path)
        with self.assertRaisesRegex(ValueError, "regular"):
            m._read_bootstrap_base(alias)
        alias.unlink()
        os.link(path, alias)
        with self.assertRaisesRegex(ValueError, "single-link"):
            m._read_bootstrap_base(path)
        alias.unlink()
        path.write_bytes(b"X" + original[1:])
        with self.assertRaisesRegex(ValueError, "identity"):
            m._read_bootstrap_base(path)


class CombinedBundleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.controls, self.inputs, self.source = [self.root / name for name in ("controls", "inputs", "source")]
        for directory in (self.controls, self.inputs, self.source):
            directory.mkdir()
        self.bundle = self.root / "bundle"
        reader = m.Reader()
        _, self.composition, controls = m._controls(WORKSPACE, reader, source_contract=m.COMBINED_SOURCE_CONTRACT)
        reader.recheck()
        for path, data in controls.items():
            write(self.controls / path, data)
        for row in self.composition["final_source_files"]:
            raw = ("Inert source fixture: " + row["path"]).encode()
            write(self.source / row["path"], raw)
            row.update(m.identity(raw))
        self.enterContext(mock.patch.object(m, "compose_sources", side_effect=self.fixture_composition))
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native process forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))
        self.images = {name: self.root / (name + ".img") for name in ("vendor", "odm")}
        self.identities = {}
        for name, path in self.images.items():
            path.write_bytes(("Inert " + name + " fixture, not an EROFS image.\n").encode())
            self.identities[name] = m.identity(path.read_bytes())
        self.enterContext(mock.patch.object(m, "EXPECTED_IMAGES", self.identities))
        self.counts = {"vendor": {"properties": 1, "apex": 1}, "odm": {"properties": 1, "apex": 0}}
        self.enterContext(mock.patch.object(m, "EXPECTED_COUNTS", self.counts))
        self.payloads = {"vendor": {"/build.prop": b"ro.vendor.fixture=original\n",
                                    "/etc/vintf/manifest.xml": b"<manifest/>\n",
                                    "/apex/inert.apex": b"Not a real APEX.\n"},
                         "odm": {"/etc/build.prop": b"ro.product.first_api_level=36\n",
                                 "/etc/vintf/manifest.xml": b"<manifest/>\n"}}
        profile = {"schema_version": 1, "contract_id": "nezha-factory-target-files-metadata-v1",
                   "device": "nezha", "branch": "bka", "release": "bp4a", "bundle": m.BUNDLE,
                   "factory_package_sha256": m.EXPECTED_PACKAGE, "partitions": {}, "scope": copy.deepcopy(m.SCOPE)}
        for partition, payloads in self.payloads.items():
            directories = {"/"}
            for name in payloads:
                parent = Path(name).parent
                while parent.as_posix() != "/":
                    directories.add(parent.as_posix())
                    parent = parent.parent
            rows = [{"path": name, "type": "directory", "nid": i + 1} for i, name in enumerate(sorted(directories))]
            rows += [{"path": name, "type": "regular", "nid": len(rows) + i + 1} for i, name in enumerate(sorted(payloads))]
            inventory = {"schema_version": 1, "image": self.identities[partition], "entries": rows}
            raw = m.encoded(inventory)
            inventory_ref = {"path": partition + "/inventory.json", **m.identity(raw)}
            write(self.inputs / inventory_ref["path"], raw)
            tool = m.identity(b"inert inventory exporter")
            evidence = {"schema_version": 1, "operation": "erofs-scan", "entry_count": len(rows),
                        "image": self.identities[partition], "inventory": m.identity(raw), "image_mounted": False,
                        "origin_verified": False, "symlinks_followed": False, "tool": tool}
            raw = m.encoded(evidence)
            evidence_ref = {"path": partition + "/inventory-receipt.json", **m.identity(raw)}
            write(self.inputs / evidence_ref["path"], raw)
            files = []
            for index, (name, data) in enumerate(sorted(payloads.items())):
                row = next(row for row in rows if row["path"] == name)
                member = f"files/{index:04}"
                write(self.inputs / partition / "capture" / member, data)
                files.append({**row, "output_path": member, "readback_verified": True, **m.identity(data)})
            capture = {"schema_version": 1, "operation": "erofs-capture", "image": self.identities[partition],
                       "image_mounted": False, "origin_verified": False, "symlinks_followed": False,
                       "firmware_executed": False, "tool": tool, "files": files,
                       "inventory_sha256": inventory_ref["sha256"], "inventory_receipt_sha256": evidence_ref["sha256"]}
            raw = m.encoded(capture)
            capture_ref = {"path": partition + "/capture/receipt.json", **m.identity(raw)}
            write(self.inputs / capture_ref["path"], raw)
            profile["partitions"][partition] = {"image": self.identities[partition], "entry_count": len(rows),
                "counts": {**self.counts[partition], "vintf": 1}, "inventory": inventory_ref,
                "inventory_receipt": evidence_ref, "captures": [capture_ref]}
        raw = m.encoded(profile)
        write(self.controls / m.PROFILE, raw)
        self.profile_ref = {"path": m.PROFILE, **m.identity(raw)}
        self.enterContext(mock.patch.object(m, "FROZEN_PROFILE", self.profile_ref))

    def fixture_composition(self, root, *, source_contract=None):
        m.require(source_contract is not None, "explicit combined source contract required")
        return copy.deepcopy(self.composition)

    def stage(self, destination=None):
        return m.stage(self.inputs, destination or self.bundle, vendor_image=self.images["vendor"],
                       odm_image=self.images["odm"], controls_root=self.controls,
                       source_contract=m.COMBINED_SOURCE_CONTRACT)

    def digest(self):
        return m.identity((self.bundle / m.RECEIPT).read_bytes())["sha256"]

    def verify(self, **kwargs):
        return m.verify_bundle(self.bundle, expected_receipt=self.digest(),
                               source_contract=m.COMBINED_SOURCE_CONTRACT, **kwargs)

    def target(self):
        target = self.root / "target-files"
        (target / "META").mkdir(parents=True)
        (target / "IMAGES").mkdir()
        for partition, path in self.images.items():
            shutil.copyfile(path, target / "IMAGES" / (partition + ".img"))
        write(target / "META/misc_info.txt", b"building_vendor_image=\nbuilding_odm_image=\nab_update=true\nvintf_enforce=true\n")
        write(target / "META/kernel_version.txt", b"inert-kernel\n")
        write(target / "META/kernel_configs.txt", b"CONFIG_INERT=y\n")
        return target

    def test_stage_verify_install_keep_images_and_payloads_unchanged(self):
        receipt = self.stage()
        verified, _, _ = self.verify(source_tree=self.source, vendor_image=self.images["vendor"], odm_image=self.images["odm"])
        self.assertEqual(receipt, verified)
        target = self.target()
        report = m.install(self.bundle, target, expected_receipt=self.digest(), source_tree=self.source)
        for partition, payloads in self.payloads.items():
            self.assertEqual(self.images[partition].read_bytes(), (target / "IMAGES" / (partition + ".img")).read_bytes())
            for path, raw in payloads.items():
                self.assertEqual(raw, (target / (partition.upper() + path)).read_bytes())
        self.assertEqual(m.SCOPE, report["scope"])
        self.assertFalse(report["scope"]["vintf_verified"])
        self.assertFalse(report["scope"]["complete_rom_admitted"])

    def test_repeated_staging_is_byte_identical_with_one_generated_native_tool(self):
        self.stage()
        second = self.root / "second"
        self.stage(second)
        for path in m._files(self.bundle):
            self.assertEqual((self.bundle / path).read_bytes(), (second / path).read_bytes(), path)
        self.assertEqual({"target_files_metadata.py"}, m._files(self.bundle / "tools"))
        self.assertEqual(m.FROZEN_BASE_IDENTITY,
                         m.identity((self.bundle / "controls" / m.FROZEN_BASE).read_bytes()))

    def test_explicit_stage_and_verify_selection_required(self):
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "explicit"):
            m.stage(self.inputs, self.bundle, vendor_image=self.images["vendor"],
                    odm_image=self.images["odm"], controls_root=self.controls)
        self.stage()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "explicit"):
            m.verify_bundle(self.bundle, expected_receipt=self.digest())

    def test_install_rejects_unadmitted_receipt_before_inference(self):
        self.stage()
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "receipt differs"):
            m._selected_receipt_source_contract(self.bundle, "0" * 64)
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "external"):
            m._selected_receipt_source_contract(self.bundle, "")

    def test_install_requires_exact_copied_descriptor_and_inventory_reference(self):
        self.stage()
        original = json.loads((self.bundle / m.RECEIPT).read_bytes())
        mutations = (
            lambda r: r["source_composition"]["contracts"].pop(),
            lambda r: r["source_composition"]["contracts"][-1].update(path=m.SOURCE_CONTRACT),
            lambda r: r["source_composition"]["contracts"][-1].update(sha256="0" * 64),
            lambda r: r.update(bundle_files=[row for row in r["bundle_files"]
                if row["path"] != "controls/" + m.COMBINED_SOURCE_CONTRACT]),
        )
        for index, mutation in enumerate(mutations):
            changed = copy.deepcopy(original)
            mutation(changed)
            write(self.bundle / m.RECEIPT, m.encoded(changed))
            with self.subTest(mutation=index), self.assertRaises(m.TargetFilesMetadataError):
                m._selected_receipt_source_contract(self.bundle, self.digest())

    def test_every_final_source_guard_is_checked(self):
        self.stage()
        for row in self.composition["final_source_files"]:
            path = self.source / row["path"]
            original = path.read_bytes()
            path.write_bytes(b"changed source")
            with self.subTest(path=row["path"]), self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
                self.verify(source_tree=self.source)
            path.write_bytes(original)

    def test_modified_generated_checker_rejected(self):
        self.stage()
        path = self.bundle / "tools/target_files_metadata.py"
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
            self.verify()

    def test_modified_copied_base_rejected_even_if_inventory_rehashed(self):
        self.stage()
        path = self.bundle / "controls" / m.FROZEN_BASE
        path.write_bytes(path.read_bytes() + b"\n")
        receipt = json.loads((self.bundle / m.RECEIPT).read_bytes())
        next(row for row in receipt["bundle_files"] if row["path"] == "controls/" + m.FROZEN_BASE).update(m.identity(path.read_bytes()))
        write(self.bundle / m.RECEIPT, m.encoded(receipt))
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "identity"):
            self.verify()

    def test_receipt_rejects_boolean_schema_and_numeric_scope_aliases(self):
        self.stage()
        original = json.loads((self.bundle / m.RECEIPT).read_bytes())
        for mutation in (lambda r: r.update(schema_version=True),
                         lambda r: r["scope"].update(complete_rom_admitted=0),
                         lambda r: r["scope"].update(metadata_only=1),
                         lambda r: r["source_composition"].update(patches_applied_by_this_tool=0)):
            changed = copy.deepcopy(original)
            mutation(changed)
            write(self.bundle / m.RECEIPT, m.encoded(changed))
            with self.subTest(mutation=mutation), self.assertRaisesRegex(m.TargetFilesMetadataError, "scope"):
                self.verify()

    def test_modified_adapter_control_cannot_match_unchanged_generated_tool(self):
        self.stage()
        path = self.bundle / "controls" / m.ADAPTER
        path.write_bytes(path.read_bytes() + b"\n")
        receipt = json.loads((self.bundle / m.RECEIPT).read_bytes())
        next(row for row in receipt["bundle_files"] if row["path"] == "controls/" + m.ADAPTER).update(m.identity(path.read_bytes()))
        write(self.bundle / m.RECEIPT, m.encoded(receipt))
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "derivation"):
            self.verify()

    def test_selection_uses_generated_tool_hash_and_keeps_readiness_closed(self):
        receipt = self.stage()
        text = m.selection(self.bundle, expected_receipt=self.digest(), source_contract=m.COMBINED_SOURCE_CONTRACT)
        tool = next(row for row in receipt["bundle_files"] if row["path"] == "tools/target_files_metadata.py")
        self.assertIn(tool["sha256"], text)
        self.assertIn(self.digest(), text)
        self.assertNotIn("NEZHA_COMPLETE_ROM", text)

    def test_generated_checker_runs_bundle_verification_in_its_own_namespace(self):
        receipt = self.stage()
        tool = self.bundle / "tools/target_files_metadata.py"
        namespace = {"__name__": "isolated_checker", "__file__": str(tool)}
        exec(compile(tool.read_bytes(), str(tool), "exec"), namespace)
        namespace.update(EXPECTED_IMAGES=self.identities, EXPECTED_COUNTS=self.counts,
                         FROZEN_PROFILE=self.profile_ref, compose_sources=self.fixture_composition)
        actual, _, _ = namespace["verify_bundle"](
            self.bundle, expected_receipt=self.digest(), source_contract=m.COMBINED_SOURCE_CONTRACT,
            source_tree=self.source, vendor_image=self.images["vendor"], odm_image=self.images["odm"])
        self.assertEqual(receipt, actual)

    def test_cli_requires_explicit_source_contract_for_host_operations(self):
        for argv in (["plan"], ["verify", "--bundle", str(self.bundle), "--expected-receipt", "0" * 64],
                     ["selection", "--bundle", str(self.bundle), "--expected-receipt", "0" * 64]):
            with self.subTest(command=argv[0]), mock.patch("sys.stderr", new=io.StringIO()):
                with self.assertRaisesRegex(SystemExit, "2"):
                    m.main(argv)


if __name__ == "__main__":
    unittest.main()
