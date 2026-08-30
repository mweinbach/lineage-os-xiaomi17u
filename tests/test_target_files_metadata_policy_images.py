"""Offline public delivery-basis tests; inert metadata is not a delivery proof."""

import ast
import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import target_files_metadata_policy_images as a
from tests import test_target_files_metadata_combined as existing

PATH = a.ROOT / a.ADAPTER
REAL_FACTORY = a._factory


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


class BootstrapTests(unittest.TestCase):
    def test_public_basis_identity_paths_and_controls_are_explicit(self):
        self.assertEqual(Path(__file__).resolve().parents[1], a.ROOT)
        self.assertEqual("scripts/target_files_metadata_policy_images.py", a.ADAPTER)
        self.assertEqual("config/nezha-policy-image-delivery-basis.json", a.IMAGE_CONTRACT)
        self.assertTrue(all(path.startswith("scripts/") for path in a.CONTROL_TOOLS))
        self.assertIs(a._files, REAL_FACTORY._files)
        reader = a.Reader()
        _, composition, controls = a._controls(a.ROOT, reader,
            source_contract=REAL_FACTORY.COMBINED_SOURCE_CONTRACT, image_contract=a.IMAGE_CONTRACT)
        reader.recheck()
        wanted = {"sha256": "3900acae006d7df191fa81a1c7cc28a92402dc5098510809c9d41b3d239cae34", "size_bytes": 92641}
        self.assertEqual(wanted, a.identity(controls[a.IMAGE_CONTRACT]))
        admission = json.loads(controls[a.IMAGE_CONTRACT])
        self.assertIsNone(admission["current_policy_build_evidence"])
        self.assertEqual(205, len(admission["metadata_members"]))
        self.assertEqual(10, len(composition["final_source_files"]))
        self.assertTrue(all(value is False for value in admission["scope"].values()))

    def controls(self):
        return {a.BASE: (a.ROOT / a.BASE).read_bytes(), a.COMBINED: (a.ROOT / a.COMBINED).read_bytes(),
                a.ADAPTER: PATH.read_bytes()}

    def test_frozen_bodies_and_private_namespace_remain_unchanged(self):
        for path, wanted in a.FROZEN.items():
            self.assertEqual(wanted, a.identity((a.ROOT / path).read_bytes()))
        self.assertEqual((a.BASE, a.COMBINED), REAL_FACTORY.CONTROL_TOOLS)
        self.assertIsNot(REAL_FACTORY.verify_bundle.__globals__, a.verify_bundle.__globals__)
        self.assertIsNot(a._install_namespace, REAL_FACTORY.__dict__)
        self.assertIs(a._install_namespace["verify_bundle"], a._install_verify)
        self.assertIsNot(REAL_FACTORY.verify_bundle, a._install_verify)

    def test_native_assembly_is_deterministic_and_self_contained(self):
        controls = self.controls()
        raw = a.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]
        self.assertEqual(raw, a.runtime_tool_payloads(controls)["tools/target_files_metadata.py"])
        namespace = {"__name__": "native_probe", "__file__": "/nonexistent/bundle/tools/target_files_metadata.py"}
        with mock.patch("os.open", side_effect=AssertionError("native bootstrap must not load adjacent files")):
            exec(compile(raw, "<native-delivery-probe>", "exec"), namespace)
        self.assertTrue(namespace["NATIVE"])
        self.assertEqual(a.PREDECESSOR_ID, namespace["identity"](namespace["_predecessor_raw"]))
        self.assertIsNot(namespace["_factory"].verify_bundle.__globals__, namespace)
        self.assertEqual(REAL_FACTORY.EXPECTED_IMAGES, namespace["_factory"].EXPECTED_IMAGES)

    def test_bootstrap_rejects_modified_predecessors_before_execution(self):
        for name in (a.BASE, a.COMBINED):
            controls = self.controls()
            controls[name] += b"\n"
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "frozen source"):
                a.runtime_tool_payloads(controls)
        with self.assertRaisesRegex(ValueError, "runtime identity"):
            a._predecessor_body(a._predecessor_raw[:-1])

    def test_terminal_main_is_checked_after_runtime_hash(self):
        changed = a._predecessor_raw + b"\n"
        with mock.patch.object(a, "PREDECESSOR_ID", a.identity(changed)):
            with self.assertRaisesRegex(ValueError, "terminal main"):
                a._predecessor_body(changed)

    def test_atomic_install_source_changes_only_the_report_expression(self):
        original = a._function_source(a._predecessor_source, "install")
        derived = a._installation_source(a._predecessor_raw)
        self.assertEqual(original.replace(a.INSTALL_REPORT_PREIMAGE,
            "    report = _delivery_installation_report(receipt, expected_receipt)"), derived)
        original_tree, derived_tree = ast.parse(original), ast.parse(derived)
        def reports(tree):
            return [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                    and any(isinstance(target, ast.Name) and target.id == "report" for target in node.targets)]
        self.assertEqual(1, len(reports(original_tree)))
        self.assertEqual(1, len(reports(derived_tree)))
        reports(derived_tree)[0].value = reports(original_tree)[0].value
        self.assertEqual(ast.dump(original_tree), ast.dump(derived_tree))

    def test_source_reader_refuses_symlinks_hardlinks_and_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            original, alias = root / "source", root / "alias"
            original.write_bytes(b"bounded")
            wanted = a.identity(b"bounded")
            self.assertEqual(b"bounded", a._bootstrap_read(original, wanted))
            alias.symlink_to(original)
            with self.assertRaisesRegex(ValueError, "regular"):
                a._bootstrap_read(alias, wanted)
            alias.unlink()
            os.link(original, alias)
            with self.assertRaisesRegex(ValueError, "single-link"):
                a._bootstrap_read(original, wanted)
            alias.unlink()
            original.write_bytes(b"changed")
            with self.assertRaisesRegex(ValueError, "identity"):
                a._bootstrap_read(original, wanted)


class DeliveryFixtureTests(unittest.TestCase):
    def setUp(self):
        # Reuse the existing inert factory-capture fixture, not private images.
        self.fixture = existing.CombinedBundleTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.stage()
        self.root = self.fixture.root
        self.controls = self.fixture.controls
        self.bundle = self.root / "delivery"
        self.original = self.fixture.bundle
        original_raw = (self.original / a.RECEIPT).read_bytes()
        self.original_receipt = json.loads(original_raw)
        self.enterContext(mock.patch.object(a, "_factory", existing.m))
        self.enterContext(mock.patch.object(a, "ORIGINAL_ID", a.identity(original_raw)))
        self.enterContext(mock.patch.object(a, "MEMBER_COUNT", len(self.original_receipt["files"])))
        total = sum(row["size_bytes"] for row in self.original_receipt["files"])
        self.enterContext(mock.patch.object(a, "MEMBER_BYTES", total))
        self.final_images = {name: self.root / ("final-" + name + ".img") for name in ("vendor", "odm")}
        identities = {}
        for name, path in self.final_images.items():
            path.write_bytes(("Inert FINAL " + name + "; not an Android image.\n").encode())
            identities[name] = a.identity(path.read_bytes())
        self.enterContext(mock.patch.object(a, "PACKAGED_IMAGES", identities))
        members = [{"target_path": row["target_path"], "partition": row["partition"], "path": row["path"],
                    "kind": row["kind"], "payload": {key: row[key] for key in ("sha256", "size_bytes")}}
                   for row in self.original_receipt["files"]]
        inputs = [{"compiler_input": "inert/input-" + str(index), "resolved_path": "/inert/input-" + str(index),
                   "runtime_path": path, **a.identity(("inert-policy-" + str(index)).encode())}
                  for index, path in enumerate(a.COMPILER_RUNTIME_PATHS)]
        replacement = a.identity(b"inert replacement")
        changes = {"vendor": {"/etc/selinux/vendor_sepolicy.cil": replacement},
                   "odm": {"/etc/selinux/precompiled_sepolicy": replacement, **{
                       "/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256": replacement
                       for name in ("plat", "system_ext", "product")}}}
        self.admission = {"schema_version": 1, "contract_id": a.IMAGE_CONTRACT_ID,
            "factory_package_sha256": existing.m.EXPECTED_PACKAGE,
            "original_images": copy.deepcopy(existing.m.EXPECTED_IMAGES), "packaged_images": identities,
            "source_composition": copy.deepcopy(self.fixture.composition), "metadata_members": members,
            "expected_root_descriptors": {name: {"kind": "hashtree", "partition": name} for name in ("vendor", "odm")},
            "policy_inputs": {"actual_compiler_inputs": inputs, "exact_five_replacement_identities": changes},
            "delivery_proof": {}, "current_policy_build_evidence": None, "scope": dict(a.PROOF_SCOPE)}
        self.proof = {key: copy.deepcopy(value) for key, value in self.admission.items() if key not in ("contract_id", "delivery_proof")}
        self.proof.update(operation=a.PROOF_OPERATION, derivation_verified=True, bound_evidence_rehashed=True,
                          metadata_count=a.MEMBER_COUNT, metadata_bytes=a.MEMBER_BYTES,
                          original_metadata_receipt={"path": "fixture/original.json", **a.ORIGINAL_ID})
        self.proof_path = self.root / "proof.json"
        self.save_admission()
        write(self.controls / a.ADAPTER, PATH.read_bytes())

    def save_admission(self):
        raw = a.encoded(self.proof)
        write(self.proof_path, raw)
        self.admission["delivery_proof"] = a.identity(raw)
        write(self.controls / a.IMAGE_CONTRACT, a.encoded(self.admission))

    def stage(self, output=None):
        return a.stage_from_original(self.original, output or self.bundle,
            expected_original_receipt=a.ORIGINAL_ID["sha256"], source_contract=existing.m.COMBINED_SOURCE_CONTRACT,
            image_contract=self.controls / a.IMAGE_CONTRACT, delivery_proof=self.proof_path, controls_root=self.controls)

    def digest(self):
        return a.identity((self.bundle / a.RECEIPT).read_bytes())["sha256"]

    def verify(self, **options):
        return a.verify_bundle(self.bundle, expected_receipt=self.digest(),
            source_contract=existing.m.COMBINED_SOURCE_CONTRACT, image_contract=a.IMAGE_CONTRACT, **options)

    def target(self):
        target = self.fixture.target()
        for name, path in self.final_images.items():
            (target / "IMAGES" / (name + ".img")).write_bytes(path.read_bytes())
        return target

    def rewrite_receipt(self, change):
        path = self.bundle / a.RECEIPT
        receipt = json.loads(path.read_bytes())
        change(receipt)
        path.write_bytes(a.encoded(receipt))

    def test_stage_from_original_never_opens_image_bodies(self):
        original_read = existing.m.Reader.read
        seen = []
        def read(reader, path, *args, **kwargs):
            seen.append(str(path))
            self.assertNotEqual(".img", Path(path).suffix)
            return original_read(reader, path, *args, **kwargs)
        with mock.patch.object(existing.m.Reader, "read", read):
            receipt = self.stage()
        self.assertTrue(seen)
        self.assertEqual(self.original_receipt["files"], receipt["files"])
        self.assertEqual(self.original_receipt["images"], receipt["images"])
        self.assertEqual(a.PACKAGED_IMAGES, receipt["packaged_images"])
        self.assertEqual(a.PROOF_SCOPE, receipt["delivery_scope"])
        self.assertEqual((self.original / a.RECEIPT).read_bytes(), (self.bundle / a.ORIGINAL_COPY).read_bytes())

    def test_repeated_stage_and_verification_preserve_exact_payloads(self):
        receipt = self.stage()
        second = self.root / "second-delivery"
        self.stage(second)
        for path in existing.m._files(self.bundle):
            self.assertEqual((self.bundle / path).read_bytes(), (second / path).read_bytes(), path)
        checked, files, _ = self.verify()
        self.assertEqual(receipt, checked)
        self.assertEqual(a.MEMBER_COUNT, len(files))
        self.assertEqual({"target_files_metadata.py"}, existing.m._files(self.bundle / "tools"))
        for row in self.original_receipt["bundle_files"]:
            if row["path"].startswith(("tree/", "provenance/")):
                self.assertEqual((self.original / row["path"]).read_bytes(), (self.bundle / row["path"]).read_bytes())

    def test_new_bundle_is_rejected_by_unchanged_combined_consumer(self):
        self.stage()
        with self.assertRaises(existing.m.TargetFilesMetadataError):
            existing.m.verify_bundle(self.bundle, expected_receipt=self.digest(), source_contract=existing.m.COMBINED_SOURCE_CONTRACT)

    def test_host_verify_requires_explicit_image_selector_and_external_digest(self):
        self.stage()
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "explicit image"):
            a.verify_bundle(self.bundle, expected_receipt=self.digest(), source_contract=existing.m.COMBINED_SOURCE_CONTRACT)
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "external"):
            a.verify_bundle(self.bundle, expected_receipt="", source_contract=existing.m.COMBINED_SOURCE_CONTRACT, image_contract=a.IMAGE_CONTRACT)
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "receipt differs"):
            a._selected_image_contract(self.bundle, "0" * 64)

    def test_both_final_images_and_every_source_guard_are_checked(self):
        self.stage()
        self.verify(source_tree=self.fixture.source, vendor_image=self.final_images["vendor"], odm_image=self.final_images["odm"])
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "both selected"):
            self.verify(vendor_image=self.final_images["vendor"])
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "identity differs"):
            self.verify(vendor_image=self.fixture.images["vendor"], odm_image=self.final_images["odm"])
        for row in self.fixture.composition["final_source_files"]:
            path = self.fixture.source / row["path"]
            before = path.read_bytes()
            path.write_bytes(before + b"changed")
            with self.subTest(path=row["path"]), self.assertRaises(a.TargetFilesMetadataError):
                self.verify(source_tree=self.fixture.source)
            path.write_bytes(before)

    def test_install_checks_final_images_then_blocks_before_publication(self):
        self.stage()
        target = self.target()
        seen = []
        original_read = a.Reader.read
        def read(reader, path, *args, **kwargs):
            seen.append((str(path), kwargs.get("data", True)))
            return original_read(reader, path, *args, **kwargs)
        with mock.patch.object(a.Reader, "read", read), mock.patch.dict(a._install_namespace,
                {"_publish_at": mock.Mock(side_effect=AssertionError("publication forbidden"))}):
            with self.assertRaisesRegex(a.CurrentPolicyEvidenceRequired, "37-goal"):
                a.install(self.bundle, target, expected_receipt=self.digest(), source_tree=self.fixture.source)
        for partition in ("vendor", "odm"):
            self.assertIn((str(target / "IMAGES" / (partition + ".img")), False), seen)
        for name in ("VENDOR", "ODM", "META/nezha_target_files_metadata.json"):
            self.assertFalse((target / name).exists())

    def test_no_current_policy_boolean_or_object_can_promote_admission(self):
        for value in (True, {}, {"passed": True}, {"normal_goals": 37}):
            changed = copy.deepcopy(self.admission)
            changed["current_policy_build_evidence"] = value
            with self.subTest(value=value), self.assertRaisesRegex(a.TargetFilesMetadataError, "no positive"):
                a._validate_admission(changed, self.fixture.composition)

    def test_contract_rejects_unknown_fields_aliases_pairs_and_members(self):
        mutations = (
            lambda d: d.update(extra=True), lambda d: d.update(schema_version=True),
            lambda d: d.update(contract_id="unknown"),
            lambda d: d["scope"].update(images_or_keys_read=0),
            lambda d: d["original_images"]["vendor"].update(sha256="0" * 64),
            lambda d: d["packaged_images"].pop("odm"),
            lambda d: d["metadata_members"].reverse(),
            lambda d: d["metadata_members"][0].update(path="/../escape"),
            lambda d: d["metadata_members"][0]["payload"].update(size_bytes=True),
            lambda d: d["metadata_members"][0].update(extra=True),
            lambda d: d["policy_inputs"]["actual_compiler_inputs"].reverse(),
            lambda d: d["expected_root_descriptors"]["vendor"].update(partition="odm"),
            lambda d: d["policy_inputs"]["exact_five_replacement_identities"]["odm"].update({"/sixth": a.identity(b"bad")}),
        )
        for index, mutate in enumerate(mutations):
            changed = copy.deepcopy(self.admission)
            mutate(changed)
            with self.subTest(index=index), self.assertRaises(a.TargetFilesMetadataError):
                a._validate_admission(changed, self.fixture.composition)

    def test_changed_proof_cannot_be_admitted_by_a_passed_boolean(self):
        self.proof["metadata_members"][0]["payload"]["sha256"] = "0" * 64
        self.save_admission()
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "proof linkage"):
            self.stage()
        self.assertFalse(self.bundle.exists())

    def test_duplicate_json_and_changed_executable_controls_are_refused(self):
        raw = (self.controls / a.IMAGE_CONTRACT).read_bytes()
        write(self.controls / a.IMAGE_CONTRACT, raw.replace(b'"schema_version": 1', b'"schema_version": 1, "schema_version": 1'))
        with self.assertRaisesRegex((a.TargetFilesMetadataError, existing.m.TargetFilesMetadataError), "JSON"):
            self.stage()
        self.save_admission()
        write(self.controls / a.ADAPTER, PATH.read_bytes() + b"\n")
        with self.assertRaisesRegex(existing.m.TargetFilesMetadataError, "identity differs"):
            self.stage()

    def test_changed_original_receipt_and_payload_are_refused(self):
        raw = (self.original / a.RECEIPT).read_bytes()
        (self.original / a.RECEIPT).write_bytes(raw + b"\n")
        with self.assertRaisesRegex(existing.m.TargetFilesMetadataError, "receipt differs"):
            self.stage()
        (self.original / a.RECEIPT).write_bytes(raw)
        row = self.original_receipt["files"][0]
        (self.original / "tree" / row["target_path"]).write_bytes(b"changed")
        with self.assertRaises(existing.m.TargetFilesMetadataError):
            self.stage()

    def test_unlisted_file_duplicate_inventory_and_schema_alias_are_refused(self):
        self.stage()
        extra = self.bundle / "unexpected"
        extra.write_bytes(b"bad")
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "unlisted"):
            self.verify()
        extra.unlink()
        raw = (self.bundle / a.RECEIPT).read_bytes()
        self.rewrite_receipt(lambda d: d["bundle_files"].append(d["bundle_files"][0]))
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "duplicate"):
            self.verify()
        (self.bundle / a.RECEIPT).write_bytes(raw)
        self.rewrite_receipt(lambda d: d.update(schema_version=True))
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "schema"):
            self.verify()

    def test_missing_image_selector_inventory_is_refused_after_external_hash(self):
        self.stage()
        self.rewrite_receipt(lambda d: d["bundle_files"].__setitem__(slice(None),
            [row for row in d["bundle_files"] if row["path"] != "controls/" + a.IMAGE_CONTRACT]))
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "uniquely inventoried"):
            a._selected_image_contract(self.bundle, self.digest())

    def test_selection_emits_only_existing_hook_variables_and_keeps_scope_false(self):
        self.stage()
        text = a.selection(self.bundle, expected_receipt=self.digest(),
            source_contract=existing.m.COMBINED_SOURCE_CONTRACT, image_contract=a.IMAGE_CONTRACT)
        self.assertIn("current policy adoption remains blocked", text)
        self.assertEqual(3, text.count(" := "))
        self.assertIn(self.digest(), text)

    def test_stage_rejects_existing_output_without_replacing_it(self):
        self.bundle.mkdir()
        sentinel = self.bundle / "keep"
        sentinel.write_bytes(b"unrelated work")
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "new bundle"):
            self.stage()
        self.assertEqual(b"unrelated work", sentinel.read_bytes())

    def test_original_input_mutation_before_publication_aborts_stage(self):
        original_recheck = a.Reader.recheck
        changed = False
        def recheck(reader):
            nonlocal changed
            if not changed and any(path.parent.name.startswith(".nezha-delivery-") for path in reader.bindings):
                (self.original / "tree" / self.original_receipt["files"][0]["target_path"]).write_bytes(b"mutated")
                changed = True
            return original_recheck(reader)
        with mock.patch.object(a.Reader, "recheck", recheck):
            with self.assertRaises((a.TargetFilesMetadataError, existing.m.TargetFilesMetadataError)):
                self.stage()
        self.assertTrue(changed)
        self.assertFalse(self.bundle.exists())

    def test_staged_payload_readback_rejects_changed_copy(self):
        original_write = existing.m._write
        def damaged_write(path, raw):
            if "/tree/" in str(path):
                raw += b"changed after copying"
            return original_write(path, raw)
        with mock.patch.object(existing.m, "_write", damaged_write):
            with self.assertRaises(a.TargetFilesMetadataError):
                self.stage()
        self.assertFalse(self.bundle.exists())

    def test_generated_tool_change_rejected_even_with_new_receipt_hash(self):
        self.stage()
        tool = self.bundle / "tools/target_files_metadata.py"
        tool.write_bytes(tool.read_bytes() + b"\n# unreviewed\n")
        self.rewrite_receipt(lambda d: next(row for row in d["bundle_files"]
            if row["path"] == "tools/target_files_metadata.py").update(a.identity(tool.read_bytes())))
        with self.assertRaisesRegex(a.TargetFilesMetadataError, "derivation differs|payload inventory"):
            self.verify()

    def test_symlink_and_hardlinked_bundle_payloads_refused(self):
        self.stage()
        member = self.bundle / "tree" / self.original_receipt["files"][0]["target_path"]
        raw = member.read_bytes()
        outside = self.root / "outside-payload"
        outside.write_bytes(raw)
        member.unlink()
        member.symlink_to(outside)
        with self.assertRaises(a.TargetFilesMetadataError):
            self.verify()
        member.unlink()
        os.link(outside, member)
        with self.assertRaises(a.TargetFilesMetadataError):
            self.verify()

    def test_wrong_final_image_blocks_before_pending_gate_and_publication(self):
        self.stage()
        target = self.target()
        (target / "IMAGES/vendor.img").write_bytes(b"not the selected final image")
        with mock.patch.object(a, "_current_policy_gate", side_effect=AssertionError("image check must run first")):
            with self.assertRaisesRegex(a.TargetFilesMetadataError, "identity differs"):
                a.install(self.bundle, target, expected_receipt=self.digest(), source_tree=self.fixture.source)
        self.assertFalse((target / "VENDOR").exists())

    def test_cli_returns_three_for_pending_install_without_publishing(self):
        self.stage()
        target = self.target()
        with mock.patch("sys.stdout", new_callable=io.StringIO) as out:
            status = a.main(["install", "--bundle", str(self.bundle), "--expected-receipt", self.digest(),
                             "--source-tree", str(self.fixture.source), "--target-files", str(target)])
        self.assertEqual(3, status)
        self.assertEqual("blocked", json.loads(out.getvalue())["status"])
        self.assertFalse((target / "VENDOR").exists())


if __name__ == "__main__":
    unittest.main()
