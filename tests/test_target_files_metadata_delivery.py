"""Offline maintained delivery tests; inert fixtures are not native ROM evidence."""

import ast
import copy
import hashlib
import importlib.util
import inspect
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PATH = Path(__file__).resolve().parents[1] / "scripts/target_files_metadata_delivery.py"
a = load("maintained_metadata_delivery_v2", PATH)
v1tests = load("maintained_metadata_v1_fixtures", a.ROOT / "tests/test_target_files_metadata_policy_images.py")
V1 = a._v1


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


class AssemblyTests(unittest.TestCase):
    def test_maintained_control_closure_uses_only_public_sources(self):
        self.assertEqual(("scripts/target_files_metadata.py",
                          "scripts/target_files_metadata_combined.py",
                          "scripts/target_files_metadata_policy_images.py",
                          "scripts/target_files_metadata_delivery.py"), a.CONTROL_TOOLS)
        reader = a.Reader()
        with mock.patch.object(reader, "read", wraps=reader.read) as read:
            profile, composition, controls = a._controls(a.ROOT, reader,
                source_contract=a._v1._factory.COMBINED_SOURCE_CONTRACT,
                image_contract=a.IMAGE_CONTRACT)
            reader.recheck()
        self.assertEqual(22, len(controls))
        self.assertEqual(10, len(composition["final_source_files"]))
        self.assertIs(a._files, a._v1._factory._files)
        for call in read.call_args_list:
            selected = Path(call.args[0]).relative_to(a.ROOT)
            with self.subTest(path=selected):
                self.assertIn(selected.parts[0], ("scripts", "patches", "config"))
        for name in controls:
            with self.subTest(control=name):
                self.assertNotIn("reports/", name)
                self.assertFalse(Path(name).is_absolute())

    def test_public_selector_keeps_the_exact_reviewed_image_basis(self):
        basis = (a.ROOT / a.V1_CONTRACT).read_bytes()
        delivery = (a.ROOT / a.IMAGE_CONTRACT).read_bytes()
        self.assertEqual({"sha256": "3900acae006d7df191fa81a1c7cc28a92402dc5098510809c9d41b3d239cae34",
                          "size_bytes": 92641}, a.identity(basis))
        self.assertEqual({"sha256": "a6883fd115c75336fc9152b0f38549d5e40706d45e7a2d88da1dfe8b246dbc02",
                          "size_bytes": 92893}, a.identity(delivery))
        self.assertEqual(basis, a.encoded(a._v1_view(json.loads(delivery))))
        self.assertEqual(a.CURRENT_REPORT_ID, json.loads(delivery)["current_policy_build_evidence"])
        for raw in (basis, delivery):
            self.assertNotIn(b"/Users/", raw)
            self.assertNotIn(b"-----BEGIN ", raw)

    def test_maintained_mode_requires_both_explicit_selectors(self):
        for kwargs in ({}, {"source_contract": a._v1._factory.COMBINED_SOURCE_CONTRACT},
                       {"image_contract": a.IMAGE_CONTRACT}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                a._controls(a.ROOT, a.Reader(), **kwargs)

    def test_v1_source_runtime_and_namespace_stay_frozen(self):
        self.assertEqual(a.V1_SOURCE_ID, a.identity((a.ROOT / a.V1_ADAPTER).read_bytes()))
        self.assertEqual(a.V1_RUNTIME_ID, a.identity(a._runtime_v1))
        self.assertNotIn("current_policy_evidence", inspect.signature(V1.stage_from_original).parameters)
        self.assertIn("current_policy_evidence", inspect.signature(a.stage_from_original).parameters)
        self.assertNotIn("selected_delivery_evidence", V1.ADMISSION_KEYS)
        self.assertIsNot(a._impl, V1.__dict__)
        self.assertIsNot(a._install_namespace, V1._install_namespace)

    def test_counted_transform_rejects_changed_predecessor_before_ast(self):
        with self.assertRaisesRegex(ValueError, "identity differs"):
            a._function_definitions(a._runtime_v1 + b"\n")
        with mock.patch.dict(a.TRANSFORMS, {"selection": [("not in frozen source", "replacement")]}):
            with self.assertRaisesRegex(a.TargetFilesMetadataError, "preimage differs"):
                a._function_definitions(a._runtime_v1)

    def test_install_preserves_atomic_body_and_passes_held_reader_to_report(self):
        old = V1._installation_source(V1._predecessor_raw)
        self.assertEqual(old.replace(a._report_call, a._report_call[:-1] + ", reader)"), a._install_source)
        self.assertIn("check_destination()", a._install_source)
        self.assertIn("reader.recheck()", a._install_source)
        self.assertIn("reversed(published)", a._install_source)

    def test_generated_native_checker_has_no_adjacent_code_dependency(self):
        controls = {name: (a.ROOT / name).read_bytes() for name in a.CONTROL_TOOLS}
        raw = a.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]
        self.assertEqual(raw, a.runtime_tool_payloads(controls)["tools/target_files_metadata.py"])
        namespace = {"__name__": "v2_native_probe", "__file__": "/nonexistent/delivery/tools/target_files_metadata.py"}
        with mock.patch("os.open", side_effect=AssertionError("no native bootstrap filesystem reads")):
            exec(compile(raw, "<v2-native>", "exec"), namespace)
        self.assertTrue(namespace["NATIVE"])
        self.assertEqual(a.V1_RUNTIME_ID, namespace["identity"](namespace["_runtime_v1"]))
        self.assertEqual(a.V1_SOURCE_ID, namespace["_v1"]._self_identity)


class DeliveryTests(unittest.TestCase):
    def setUp(self):
        self.fixture = v1tests.DeliveryFixtureTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        f, old = self.fixture, v1tests.a
        self.root, self.controls, self.original = f.root, f.controls, f.original
        self.bundle = self.root / "v2-delivery"
        self.enterContext(mock.patch.object(a, "_v1", old))
        self.enterContext(mock.patch.dict(a._impl, {"_factory": old._factory, "ORIGINAL_ID": old.ORIGINAL_ID}))
        self.policy_bytes = {row["runtime_path"]: ("inert-policy-" + str(index)).encode()
                             for index, row in enumerate(f.admission["policy_inputs"]["actual_compiler_inputs"])}
        for index, name in enumerate(("plat", "system_ext", "product")):
            rows = f.admission["policy_inputs"]["actual_compiler_inputs"]
            first, second = rows[index * 2:index * 2 + 2]
            raw = (hashlib.sha256(self.policy_bytes[first["runtime_path"]] + self.policy_bytes[second["runtime_path"]]).hexdigest() + "\n").encode()
            f.admission["policy_inputs"]["exact_five_replacement_identities"]["odm"][
                "/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256"] = a.identity(raw)
        f.proof["policy_inputs"] = copy.deepcopy(f.admission["policy_inputs"])
        refs = {name: {"path": "fixture/" + name + ".json", **a.identity(name.encode())}
                for name in ("production_receipt", "production_independent_review", "raw_metadata_proof")}
        f.proof.update(refs)
        f.proof["leaf_derivations"] = {role + "-1": {"image": {
            "path": "/work/inert-production/pass-1-" + role + "/" + role + ".img", **old.PACKAGED_IMAGES[role]}}
            for role in ("vendor", "odm")}
        f.save_admission()
        v1_identity = a.identity(a.encoded(f.admission))
        self.enterContext(mock.patch.object(a, "V1_CONTRACT_ID", v1_identity))
        self.enterContext(mock.patch.dict(a._impl, {"V1_CONTRACT_ID": v1_identity}))
        framework, sidecars = a._policy_layout(f.admission)
        self.current = {"schema_version": 1, "operation": a.CURRENT_OPERATION,
            "status": "captured-current-wrapper-policy-identity-equality-verified",
            "captured_current_wrapper_policy_identity_equality_verified": True,
            "bound_evidence_rehashed_after_verification": True, "requested_goal_count": 37,
            "scope": {"runtime_verified": False, "complete_rom_ready": False, "zero_skips_claimed_for_build": False},
            "raw_policy_proof": refs["raw_metadata_proof"],
            "policy_equality": {"actual_compiler_inputs": copy.deepcopy(f.admission["policy_inputs"]["actual_compiler_inputs"]),
                "selected_factory_combined_binary": {"path": "/work/factory-combined", **f.admission["policy_inputs"]["exact_five_replacement_identities"]["odm"]["/etc/selinux/precompiled_sepolicy"]},
                "installed_odm_binary_still_distinct": {"path": "/work/source-only", **a.identity(b"inert source-only binary")},
                "protected_policy_outputs": [{"path": "/work/policy/" + str(i), **a.identity(str(i).encode())} for i in range(13)],
                "protected_runtime_outputs": [{"path": "/work/runtime/" + str(i), **a.identity(str(i).encode())} for i in range(11)]},
            "current_source_binding": {"source_inventory": [{"path": "/work/source/" + str(i), **a.identity(str(i).encode())} for i in range(204)]},
            "future_packaging_checks": {"framework_inputs": framework, "sidecars": [dict(row,
                odm_sidecar_tree_projection_required=False, recomputed_from_actual_packaged_files=False) for row in sidecars],
                "opaque_odm_target_files_image": "IMAGES/odm.img", "artifacts_fabricated": False,
                "odm_selinux_tree_is_not_part_of_the_original_205_member_metadata_projection": True}}
        self.current_path, self.selected_path = self.root / "current.json", self.root / "selected.json"
        current_raw = a.encoded(self.current)
        write(self.current_path, current_raw)
        self.enterContext(mock.patch.object(a, "CURRENT_REPORT_ID", a.identity(current_raw)))
        self.admission = copy.deepcopy(f.admission)
        self.admission.update(schema_version=2, contract_id=a.IMAGE_CONTRACT_ID,
                              current_policy_build_evidence=a.identity(current_raw), selected_delivery_evidence={})
        copy_bytes = sum(row["size_bytes"] for row in old.PACKAGED_IMAGES.values())
        self.selected = {"schema_version": 1, "operation": a.COPY_OPERATION, "status": "prepared-private-validation-bundle",
            "passed": True, "skipped": 0, "input_contract": a.COPY_INPUT_ID,
            "controls": {"current_policy": {"path": "current-policy.json", **a.CURRENT_REPORT_ID},
                         "delivery_proof": {"path": "delivery-proof.json", **f.admission["delivery_proof"]}},
            "output_directory": a.COPY_DIRECTORY,
            "selected_copies": {role: {"source": f.proof["leaf_derivations"][role + "-1"]["image"],
                "destination": {"path": a.COPY_DIRECTORY + "/images/" + role + ".img", **old.PACKAGED_IMAGES[role]},
                "independent_inode": True, "source_rehashed_before_and_after": True, "destination_rehashed_after_copy": True}
                for role in ("vendor", "odm")},
            "originals": {role: {"path": "/work/evolution/vendor/xiaomi/nezha/proprietary/images/" + role + ".img", **old._factory.EXPECTED_IMAGES[role],
                "rehashed_before_and_after": True} for role in ("vendor", "odm")},
            "verified_inputs": {role: {"count": count, "identities": rows, "rehashed_before_and_after": True}
                for role, count, rows in (("policy", 13, self.current["policy_equality"]["protected_policy_outputs"]),
                    ("runtime", 11, self.current["policy_equality"]["protected_runtime_outputs"]),
                    ("source", 204, self.current["current_source_binding"]["source_inventory"]))},
            "provenance": {**refs, "source_composition": a.identity(a.encoded(self.admission["source_composition"])),
                "metadata_members": {**a.identity(a.encoded(self.admission["metadata_members"])),
                    "count": len(self.admission["metadata_members"]), "payload_bytes": old.MEMBER_BYTES}},
            "disk": {"copy_bytes": copy_bytes, "reserve_bytes": 1 << 30,
                     "available_before_bytes": (1 << 30) + copy_bytes + 1, "available_after_bytes": (1 << 30) + 1},
            "scope": dict(a.COPY_SCOPE)}
        self.save_selected()
        write(self.controls / a.ADAPTER, PATH.read_bytes())

    def save_selected(self):
        raw = a.encoded(self.selected)
        write(self.selected_path, raw)
        self.admission["selected_delivery_evidence"] = a.identity(raw)
        write(self.controls / a.IMAGE_CONTRACT, a.encoded(self.admission))

    def stage(self, output=None):
        f = self.fixture
        return a.stage_from_original(self.original, output or self.bundle,
            expected_original_receipt=v1tests.a.ORIGINAL_ID["sha256"],
            source_contract=v1tests.existing.m.COMBINED_SOURCE_CONTRACT, image_contract=self.controls / a.IMAGE_CONTRACT,
            delivery_proof=f.proof_path, current_policy_evidence=self.current_path,
            selected_delivery_evidence=self.selected_path, controls_root=self.controls)

    def digest(self):
        return a.identity((self.bundle / a.RECEIPT).read_bytes())["sha256"]

    def verify(self, **kwargs):
        return a.verify_bundle(self.bundle, expected_receipt=self.digest(),
            source_contract=v1tests.existing.m.COMBINED_SOURCE_CONTRACT, image_contract=a.IMAGE_CONTRACT, **kwargs)

    def target(self):
        target = self.fixture.target()
        framework, sidecars = a._policy_layout(self.admission)
        for row in framework:
            top, suffix = row["target_files_path"].split("/", 1)
            write(target / row["target_files_path"], self.policy_bytes["/" + top.lower() + "/" + suffix])
        for row in sidecars:
            first, second = row["ordered_target_files_inputs"]
            raw = (hashlib.sha256((target / first).read_bytes() + (target / second).read_bytes()).hexdigest() + "\n").encode()
            write(target / row["framework_sidecar_path"], raw)
        return target

    def install(self, target):
        return a.install(self.bundle, target, expected_receipt=self.digest(), source_tree=self.fixture.fixture.source)

    def test_stage_requires_evidence_but_not_images_or_target_files(self):
        for path in self.fixture.final_images.values():
            path.unlink()
        result = self.stage()
        self.assertEqual(self.fixture.original_receipt["files"], result["files"])
        self.assertEqual(3, result["schema_version"])
        self.assertEqual(a.CURRENT_REPORT_ID, a.expected(result["current_policy_evidence"]))
        checked, _, _ = self.verify()
        self.assertEqual(result, checked)

    def test_stage_twice_is_identical_and_v1_consumer_rejects_v2(self):
        self.stage()
        second = self.root / "v2-second"
        self.stage(second)
        for path in v1tests.existing.m._files(self.bundle):
            self.assertEqual((self.bundle / path).read_bytes(), (second / path).read_bytes())
        with self.assertRaises(ValueError):
            v1tests.a.verify_bundle(self.bundle, expected_receipt=self.digest(),
                source_contract=v1tests.existing.m.COMBINED_SOURCE_CONTRACT, image_contract=a.IMAGE_CONTRACT)

    def test_actual_framework_and_sidecars_allow_inert_atomic_install(self):
        self.stage()
        target = self.target()
        result = self.install(target)
        self.assertEqual("project-policy-image-target-files-metadata-v2", result["operation"])
        self.assertTrue(result["packaged_policy_checks"]["seven_actual_framework_inputs_verified"])
        self.assertTrue(result["packaged_policy_checks"]["three_actual_framework_sidecars_recomputed"])
        self.assertFalse(result["complete_rom_ready"])
        self.assertFalse((target / "ODM/etc/selinux").exists())
        self.assertEqual(result, json.loads((target / "META/nezha_target_files_metadata.json").read_bytes()))

    def test_each_framework_file_and_sidecar_is_required(self):
        self.stage()
        target = self.target()
        framework, sidecars = a._policy_layout(self.admission)
        for relative in [row["target_files_path"] for row in framework] + [row["framework_sidecar_path"] for row in sidecars]:
            path = target / relative
            raw = path.read_bytes()
            path.unlink()
            with self.subTest(path=relative), self.assertRaises((ValueError, OSError)):
                self.install(target)
            self.assertFalse((target / "VENDOR").exists())
            path.write_bytes(raw)

    def test_sidecar_newline_and_order_are_not_normalized(self):
        self.stage()
        target = self.target()
        _, sidecars = a._policy_layout(self.admission)
        for row in sidecars:
            path = target / row["framework_sidecar_path"]
            original = path.read_bytes()
            first, second = row["ordered_target_files_inputs"]
            for raw in (original[:-1], (hashlib.sha256((target / second).read_bytes() + (target / first).read_bytes()).hexdigest() + "\n").encode()):
                path.write_bytes(raw)
                with self.subTest(path=str(path), raw=raw), self.assertRaises(ValueError):
                    self.install(target)
                self.assertFalse((target / "VENDOR").exists())
            path.write_bytes(original)

    def test_genfs_and_final_images_cannot_use_old_or_changed_bytes(self):
        self.stage()
        target = self.target()
        for relative in ("SYSTEM/etc/selinux/plat_sepolicy_genfs_202504.cil", "IMAGES/vendor.img", "IMAGES/odm.img"):
            path = target / relative
            raw = path.read_bytes()
            path.write_bytes(raw + b"changed")
            with self.subTest(path=relative), self.assertRaises(ValueError):
                self.install(target)
            self.assertFalse((target / "ODM").exists())
            path.write_bytes(raw)

    def test_framework_policy_symlinks_and_hardlinks_cannot_substitute_for_files(self):
        self.stage()
        target = self.target()
        for relative in ("SYSTEM/etc/selinux/plat_sepolicy.cil",
                         "SYSTEM_EXT/etc/selinux/system_ext_sepolicy_and_mapping.sha256"):
            path = target / relative
            raw = path.read_bytes()
            backing = self.root / "aliased-policy"
            for alias in ("symlink", "hardlink"):
                path.unlink()
                backing.write_bytes(raw)
                if alias == "symlink":
                    path.symlink_to(backing)
                else:
                    os.link(backing, path)
                with self.subTest(path=relative, alias=alias), self.assertRaises(ValueError):
                    self.install(target)
                self.assertFalse((target / "VENDOR").exists())
                path.unlink()
                backing.unlink()
                path.write_bytes(raw)

    def test_actual_combined_source_guard_still_required_before_install(self):
        self.stage()
        target = self.target()
        composition = self.admission["source_composition"]
        for row in composition["final_source_files"]:
            path = self.fixture.fixture.source / row["path"]
            raw = path.read_bytes()
            path.write_bytes(raw + b"changed source")
            with self.subTest(path=row["path"]), self.assertRaises(ValueError):
                self.install(target)
            self.assertFalse((target / "ODM").exists())
            path.write_bytes(raw)

    def test_copied_policy_and_delivery_evidence_are_receipt_bound(self):
        self.stage()
        for relative in (a.CURRENT_COPY, a.SELECTED_COPY):
            path = self.bundle / relative
            raw = path.read_bytes()
            path.write_bytes(raw + b"\n")
            with self.subTest(path=relative), self.assertRaises(ValueError):
                self.verify()
            path.write_bytes(raw)

    def test_policy_mutation_during_publication_rolls_back_owned_metadata(self):
        self.stage()
        target = self.target()
        original_publish = a._install_namespace["_publish_at"]
        def publish(source_fd, source, destination_fd, destination):
            result = original_publish(source_fd, source, destination_fd, destination)
            if destination == "VENDOR":
                (target / "SYSTEM/etc/selinux/plat_sepolicy.cil").write_bytes(b"changed during publish")
            return result
        with mock.patch.dict(a._install_namespace, {"_publish_at": publish}):
            with self.assertRaises(ValueError):
                self.install(target)
        for name in ("VENDOR", "ODM", "META/nezha_target_files_metadata.json"):
            self.assertFalse((target / name).exists())

    def test_current_and_selected_receipts_require_exact_external_identities(self):
        original = self.current_path.read_bytes()
        self.current_path.write_bytes(original + b"\n")
        with self.assertRaises(ValueError):
            self.stage()
        self.current_path.write_bytes(original)
        self.selected_path.write_bytes(self.selected_path.read_bytes() + b"\n")
        with self.assertRaises(ValueError):
            self.stage()
        self.assertFalse(self.bundle.exists())

    def test_v2_cannot_rewrite_frozen_v1_proof_or_original_images(self):
        for name in ("original_images", "packaged_images", "delivery_proof", "source_composition"):
            changed = copy.deepcopy(self.admission)
            changed[name] = {}
            with self.subTest(field=name), self.assertRaisesRegex(ValueError, "frozen v1"):
                a._validate_admission(changed, self.fixture.fixture.composition)

    def test_copy_receipt_rejects_aliases_nonindependent_files_and_stale_inputs(self):
        mutations = (
            lambda r: r.update(skipped=False), lambda r: r.update(passed=1),
            lambda r: r["scope"].update(delivery_images_adopted=True),
            lambda r: r["selected_copies"]["vendor"].update(independent_inode=False),
            lambda r: r["selected_copies"]["odm"]["destination"].update(path="/work/elsewhere/odm.img"),
            lambda r: r["verified_inputs"]["policy"]["identities"][0].update(sha256="0" * 64),
            lambda r: r["verified_inputs"]["runtime"].update(count=10),
            lambda r: r["verified_inputs"]["source"].update(rehashed_before_and_after=False),
            lambda r: r["originals"]["vendor"].update(path="/work/another-canonical-original/vendor.img"),
            lambda r: r["input_contract"].update(sha256="0" * 64),
            lambda r: r["disk"].update(reserve_bytes=0),
            lambda r: r.update(unreviewed=True),
        )
        for index, mutation in enumerate(mutations):
            changed = copy.deepcopy(self.selected)
            mutation(changed)
            raw = a.encoded(changed)
            admission = copy.deepcopy(self.admission)
            admission["selected_delivery_evidence"] = a.identity(raw)
            with self.subTest(index=index), self.assertRaises(ValueError):
                a._validate_selected(raw, admission, self.current, self.fixture.proof)

    def test_current_policy_flags_and_target_map_cannot_promote_or_redirect(self):
        mutations = (
            lambda r: r.update(requested_goal_count=True),
            lambda r: r["scope"].update(runtime_verified=True),
            lambda r: r["future_packaging_checks"]["framework_inputs"][0].update(target_files_path="OTHER/policy"),
            lambda r: r["future_packaging_checks"]["sidecars"][0].update(odm_sidecar_tree_projection_required=True),
            lambda r: r["policy_equality"].update(selected_factory_combined_binary=r["policy_equality"]["installed_odm_binary_still_distinct"]),
        )
        for index, mutation in enumerate(mutations):
            changed = copy.deepcopy(self.current)
            mutation(changed)
            raw = a.encoded(changed)
            admission = copy.deepcopy(self.admission)
            admission["current_policy_build_evidence"] = a.identity(raw)
            with self.subTest(index=index), mock.patch.object(a, "CURRENT_REPORT_ID", a.identity(raw)):
                with self.assertRaises(ValueError):
                    a._validate_current(raw, admission, self.fixture.proof)

    def test_external_evidence_verify_cannot_select_different_copies(self):
        self.stage()
        self.verify(current_policy_evidence=self.current_path, selected_delivery_evidence=self.selected_path)
        self.selected_path.write_bytes(b"{}\n")
        with self.assertRaises(ValueError):
            self.verify(selected_delivery_evidence=self.selected_path)

    def test_install_collision_does_not_remove_an_existing_tree(self):
        self.stage()
        target = self.target()
        write(target / "VENDOR/existing", b"keep other work")
        with self.assertRaises(ValueError):
            self.install(target)
        self.assertEqual(b"keep other work", (target / "VENDOR/existing").read_bytes())

    def test_selection_uses_unchanged_hook_variables_without_readiness(self):
        self.stage()
        text = a.selection(self.bundle, expected_receipt=self.digest(),
            source_contract=v1tests.existing.m.COMBINED_SOURCE_CONTRACT, image_contract=a.IMAGE_CONTRACT)
        self.assertEqual(3, text.count(" := "))
        self.assertIn("required at install", text)
        self.assertNotIn("ready := true", text)


if __name__ == "__main__":
    unittest.main()
