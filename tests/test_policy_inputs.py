"""Offline private policy-bundle tests using small, synthetic captured files.

No CIL compiler, native Android build, firmware executable, network, or device is
used. Native compilation and context-check results require separate evidence.
"""

import copy
import io
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest import mock

from scripts import policy_inputs as policy


WORKSPACE = Path(__file__).resolve().parents[1]
CORPUS_PATHS = [
    "/system/etc/selinux/plat_sepolicy.cil", "/system/etc/selinux/mapping/202504.cil",
    "/system_ext/etc/selinux/system_ext_sepolicy.cil", "/system_ext/etc/selinux/mapping/202504.cil",
    "/product/etc/selinux/product_sepolicy.cil", "/product/etc/selinux/mapping/202504.cil",
    "/vendor/etc/selinux/plat_pub_versioned.cil", "/vendor/etc/selinux/vendor_sepolicy.cil",
    "/odm/etc/selinux/odm_sepolicy.cil", "/system/etc/selinux/plat_sepolicy_genfs_202504.cil",
]


class PolicyInputsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.corpus = self.root / "corpus"
        self.corpus.mkdir()
        self.capture = self.root / "capture"
        self.capture.mkdir()
        self.output = self.root / "private-bundle"
        self.package = "a" * 64
        self.originals = {}
        self.enterContext(mock.patch.object(policy, "ROOT", self.workspace))
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("no native processes")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("no shell execution")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("no network")))
        correction = {"schema_version": 1, "device": "nezha", "inputs": [],
                      "factory_package_sha256": self.package,
                      "output": {"path": "vendor_sepolicy.cil", **policy.identity(b"not built\n")}}
        for index, runtime in enumerate(CORPUS_PATHS):
            data = ("Synthetic capture " + str(index) + "\n").encode()
            correction["inputs"].append({"runtime_path": runtime, **policy.identity(data)})
            path = self.corpus / runtime[1:]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            self.originals[path] = data
        self.correction = correction
        receipt_rows, contexts = [], []
        for part in ("vendor", "odm"):
            kinds = ["file", "hwservice", "property", "seapp", "service"]
            if part == "vendor":
                kinds += ["keystore2_key", "tee_service", "vndservice"]
            for index, kind in enumerate(kinds):
                name = "vndservice_contexts" if kind == "vndservice" else part + "_" + kind + "_contexts"
                runtime = "/" + part + "/etc/selinux/" + name
                relative = "policy/" + part + "/files/" + str(index).zfill(4)
                data = b"" if part == "odm" and kind != "property" else (name + " synthetic-entry\n").encode()
                path = self.capture / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
                self.originals[path] = data
                expected = {"runtime_path": runtime, "path": "factory/" + part + "/" + name,
                            "capture_path": relative, **policy.identity(data)}
                contexts.append(expected)
                receipt_rows.append({"runtime_path": runtime, "path": "artifacts/capture/" + relative,
                                     "partition": part, "image_path": "/etc/selinux/" + name,
                                     **policy.identity(data)})
        capture_receipt = {"schema_version": 1, "operation": "factory-policy-capture-and-comparison",
                           "parent_package_sha256": self.package, "files": receipt_rows}
        self.capture_receipt = capture_receipt
        raw = policy.encoded(capture_receipt)
        self.receipt_path = self.capture / "policy-receipt.json"
        self.receipt_path.write_bytes(raw)
        self.originals[self.receipt_path] = raw
        self.config = {"schema_version": 1, "device": "nezha", "bundle": policy.BUNDLE_PATH,
                       "platform": {"branch": "bka", "release": "bp4a", "board_api": "202504"},
                       "package_sha256": self.package, "contexts": contexts,
                       "factory_policy_capture": {"path": "artifacts/capture/policy-receipt.json",
                                                  **policy.identity(raw)},
                       "native_targets": ["nezha_factory_precompiled_sepolicy"]}
        self.factory = {"schema_version": 1, "device": {"codename": "nezha", "hardware_region": "CN"},
                        "provenance": {"factory": {"sha256": self.package}},
                        "receipts": {"policy_capture": self.config["factory_policy_capture"]}}
        for source in policy.CONTROL_FILES.values():
            path = self.workspace / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(("Synthetic control " + source + "\n").encode())
        # Exercise the actual native template while all proprietary data stays
        # synthetic. This also catches renderer/template schema disagreement.
        (self.workspace / "policy/nezha/Android.bp").write_bytes((WORKSPACE / "policy/nezha/Android.bp").read_bytes())
        tool = self.workspace / "scripts/policy_inputs.py"
        tool.write_bytes(b"Synthetic trusted staging source; never executed\n")
        self.write_contracts()

    def write_contracts(self):
        (self.workspace / policy.CONTRACT_PATH).write_bytes(policy.encoded(self.config))
        (self.workspace / policy.FACTORY_RECORD_PATH).write_bytes(policy.encoded(self.factory))
        raw = policy.encoded(self.correction)
        (self.workspace / "config/vendor-policy-correction.json").write_bytes(raw)
        self.enterContext(mock.patch.object(policy.vendor_policy, "CONTRACT_SHA256", policy.identity(raw)["sha256"]))

    def stage(self, output=None):
        return policy.stage_inputs(self.corpus, output or self.output, factory_policy_receipt=self.receipt_path)

    def assert_rejected(self, callback):
        with self.assertRaises((ValueError, OSError)):
            callback()

    def test_stage_and_verify_preserve_originals_and_all_exact_files(self):
        result = self.stage()
        verified = policy.verify_bundle(self.output)
        self.assertEqual(result["files"], verified["files"])
        self.assertEqual(verified["factory_package_sha256"], self.package)
        self.assertEqual(verified["receipt"], {"path": policy.RECEIPT_NAME,
                                              **policy.identity((self.output / policy.RECEIPT_NAME).read_bytes())})
        self.assertEqual(len(result["classification_inputs"]), 10)
        self.assertEqual(len(result["contexts"]), 13)
        self.assertEqual(len(result["files"]), 31)
        self.assertNotIn("oem_policy_contract", result)
        self.assertIsNone(verified["oem_policy_contract"])
        self.assertTrue(result["readback_verified"])
        self.assertFalse(result["scope"]["policy_compiled"])
        self.assertFalse(result["scope"]["contexts_validated"])
        self.assertFalse(result["scope"]["complete_rom_admitted"])
        self.assertEqual(result["scope"]["device_operations"], [])
        for path, data in self.originals.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        for member in result["files"]:
            path = self.output / member["path"]
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertNotIn(str(self.root), json.dumps(result))

    def test_second_private_bundle_is_byte_identical(self):
        first = self.stage()
        second_path = self.root / "second-private-bundle"
        second = self.stage(second_path)
        self.assertEqual(first, second)
        self.assertEqual((self.output / policy.RECEIPT_NAME).read_bytes(),
                         (second_path / policy.RECEIPT_NAME).read_bytes())

    def test_capture_root_argument_and_relocated_capture_preserve_provenance(self):
        relocated = self.root / "relocated-capture"
        shutil.copytree(self.capture, relocated)
        result = policy.stage_inputs(self.corpus, self.output, factory_capture_root=relocated)
        self.assertEqual(result["factory_policy_capture"], self.config["factory_policy_capture"])
        self.assertEqual(policy.verify_bundle(self.output)["status"], "verified")

    def test_authentic_zero_byte_captures_are_preserved_not_fabricated(self):
        result = self.stage()
        empty = [row for row in result["contexts"] if row["size_bytes"] == 0]
        self.assertEqual(len(empty), 4)
        for row in empty:
            self.assertEqual((self.output / row["path"]).read_bytes(), b"")
            self.assertEqual(row["sha256"], policy.identity(b"")["sha256"])
        (self.capture / empty[0]["capture_path"]).unlink()
        self.assert_rejected(lambda: self.stage(self.root / "missing-empty-context"))

    def test_changed_corpus_file_fails_before_publication(self):
        path = self.corpus / CORPUS_PATHS[0][1:]
        path.write_bytes(path.read_bytes() + b"unreviewed\n")
        self.assert_rejected(self.stage)
        self.assertFalse(self.output.exists())

    def test_changed_context_file_fails_before_publication(self):
        path = self.capture / self.config["contexts"][0]["capture_path"]
        path.write_bytes(b"unreviewed context")
        self.assert_rejected(self.stage)
        self.assertFalse(self.output.exists())

    def test_wrong_factory_receipt_fails_before_publication(self):
        self.receipt_path.write_bytes(policy.encoded({**self.capture_receipt, "unreviewed": True}))
        self.assert_rejected(self.stage)
        self.assertFalse(self.output.exists())

    def test_changed_derivation_contract_cannot_select_alternate_corpus(self):
        path = self.workspace / "config/vendor-policy-correction.json"
        path.write_bytes(path.read_bytes() + b" ")
        self.assert_rejected(self.stage)
        self.assertFalse(self.output.exists())

    def test_factory_config_cannot_diverge_from_public_capture_binding(self):
        self.config["factory_policy_capture"] = copy.deepcopy(self.config["factory_policy_capture"])
        self.config["factory_policy_capture"]["sha256"] = "b" * 64
        self.write_contracts()
        self.assert_rejected(self.stage)
        self.assertFalse(self.output.exists())

    def test_context_metadata_must_match_the_sealed_capture(self):
        changes = [lambda row: row.update(sha256="b" * 64),
                   lambda row: row.update(capture_path="policy/vendor/files/9999"),
                   lambda row: row.update(runtime_path="/vendor/etc/selinux/other_contexts"),
                   lambda row: row.update(path="factory/vendor/changed_contexts")]
        original = copy.deepcopy(self.config["contexts"][0])
        for change in changes:
            self.config["contexts"][0] = copy.deepcopy(original)
            change(self.config["contexts"][0])
            self.write_contracts()
            self.assert_rejected(self.stage)
            self.assertFalse(self.output.exists())

    def test_duplicate_selection_or_json_keys_are_rejected(self):
        self.config["contexts"].append(copy.deepcopy(self.config["contexts"][0]))
        self.write_contracts()
        self.assert_rejected(self.stage)
        self.config["contexts"].pop()
        self.write_contracts()
        path = self.workspace / policy.CONTRACT_PATH
        raw = path.read_bytes()
        path.write_bytes(raw.replace(b'{', b'{"device":"nezha",', 1))
        self.assert_rejected(self.stage)

    def test_private_output_refuses_existing_directory_or_symlink(self):
        self.output.mkdir()
        sentinel = self.output / "preserved"
        sentinel.write_bytes(b"other task")
        self.assert_rejected(self.stage)
        self.assertEqual(sentinel.read_bytes(), b"other task")
        alternate = self.root / "output-symlink"
        alternate.symlink_to(self.output, target_is_directory=True)
        self.assert_rejected(lambda: self.stage(alternate))

    def test_tracked_workspace_output_is_refused(self):
        path = self.workspace / "unignored-policy-candidate"
        self.assert_rejected(lambda: self.stage(path))
        self.assertFalse(path.exists())

    def test_ignored_workspace_output_is_allowed(self):
        parent = self.workspace / "artifacts"
        parent.mkdir()
        result = self.stage(parent / "candidate")
        self.assertEqual(result["status"], "staged")

    def test_output_cannot_add_descendants_to_preserved_input_directories(self):
        for root in (self.corpus, self.capture):
            output = root / "new-policy-bundle"
            self.assert_rejected(lambda: self.stage(output))
            self.assertFalse(output.exists())

    def test_factory_context_package_cannot_differ_from_vendor_corpus_package(self):
        self.correction["factory_package_sha256"] = "b" * 64
        self.write_contracts()
        self.assert_rejected(self.stage)
        self.assertFalse(self.output.exists())

    def test_symlink_input_or_ancestor_is_refused(self):
        source = self.corpus / CORPUS_PATHS[0][1:]
        original = source.read_bytes()
        source.unlink()
        other = self.root / "outside-corpus"
        other.write_bytes(original)
        source.symlink_to(other)
        self.assert_rejected(self.stage)
        source.unlink()
        source.write_bytes(original)
        alias = self.root / "corpus-alias"
        alias.symlink_to(self.corpus, target_is_directory=True)
        self.assert_rejected(lambda: policy.stage_inputs(alias, self.output, factory_capture_root=self.capture))

    def test_source_replacement_after_readback_fails_and_cleans_scratch(self):
        original_verify = policy.verify_bundle

        def changed_source(*args):
            result = original_verify(*args)
            path = self.corpus / CORPUS_PATHS[0][1:]
            path.write_bytes(b"changed after copy")
            return result

        with mock.patch.object(policy, "verify_bundle", side_effect=changed_source):
            self.assert_rejected(self.stage)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".nezha-policy-inputs-*")), [])

    def test_publication_race_preserves_the_other_destination(self):
        publish = policy.publish_new_directory

        def race(staging, destination):
            destination.mkdir()
            (destination / "other-task").write_bytes(b"preserve")
            return publish(staging, destination)

        with mock.patch.object(policy, "publish_new_directory", side_effect=race):
            self.assert_rejected(self.stage)
        self.assertEqual((self.output / "other-task").read_bytes(), b"preserve")
        self.assertEqual(list(self.root.glob(".nezha-policy-inputs-*")), [])

    def test_verify_rejects_corruption_even_if_receipt_is_updated(self):
        self.stage()
        member = "corpus/" + CORPUS_PATHS[0][1:]
        (self.output / member).write_bytes(b"replacement")
        receipt = json.loads((self.output / policy.RECEIPT_NAME).read_bytes())
        for row in receipt["files"]:
            if row["path"] == member:
                row.update(policy.identity(b"replacement"))
        (self.output / policy.RECEIPT_NAME).write_bytes(policy.encoded(receipt))
        self.assert_rejected(lambda: policy.verify_bundle(self.output))

    def test_verify_rejects_modified_source_template_or_control_tool(self):
        self.stage()
        for member in ("Android.bp", "tools/vendor_policy.py", "tools/artifact_files.py"):
            path = self.output / member
            original = path.read_bytes()
            path.write_bytes(original + b"unreviewed")
            self.assert_rejected(lambda: policy.verify_bundle(self.output))
            path.write_bytes(original)

    def test_verify_rejects_unexpected_files_missing_files_and_symlinks(self):
        self.stage()
        path = self.output / "unreviewed.py"
        path.write_bytes(b"no")
        self.assert_rejected(lambda: policy.verify_bundle(self.output))
        path.unlink()
        member = self.output / "factory/vendor/vendor_file_contexts"
        data = member.read_bytes()
        member.unlink()
        self.assert_rejected(lambda: policy.verify_bundle(self.output))
        member.symlink_to(self.capture / self.config["contexts"][0]["capture_path"])
        self.assert_rejected(lambda: policy.verify_bundle(self.output))
        member.unlink()
        member.write_bytes(data)
        self.assertEqual(policy.verify_bundle(self.output)["status"], "verified")

    def test_verify_rejects_claims_of_compilation_or_hardware_success(self):
        self.stage()
        path = self.output / policy.RECEIPT_NAME
        original = json.loads(path.read_bytes())
        for key in ("policy_compiled", "contexts_validated", "hardware_tested", "complete_rom_admitted"):
            receipt = copy.deepcopy(original)
            receipt["scope"][key] = True
            path.write_bytes(policy.encoded(receipt))
            self.assert_rejected(lambda: policy.verify_bundle(self.output))

    def test_short_free_space_fails_without_private_output(self):
        with mock.patch.object(policy.shutil, "disk_usage", return_value=shutil._ntuple_diskusage(100, 99, 1)):
            self.assert_rejected(self.stage)
        self.assertFalse(self.output.exists())

    def test_cli_stage_and_verify_report_separate_scope_without_processes(self):
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            code = policy.main(["stage", "--corpus-root", str(self.corpus), "--factory-capture-root",
                                str(self.capture), "--output", str(self.output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "staged")
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            code = policy.main(["verify", "--bundle", str(self.output)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["status"], "verified")
        self.assertFalse(json.loads(stdout.getvalue())["scope"]["policy_compiled"])

    def test_cli_failure_is_nonzero_and_does_not_publish(self):
        with mock.patch("sys.stderr", io.StringIO()) as stderr:
            code = policy.main(["verify", "--bundle", str(self.output)])
        self.assertEqual(code, 2)
        self.assertEqual(json.loads(stderr.getvalue())["status"], "failed")
        self.assertFalse(self.output.exists())

    def install_oem_fixture(self):
        from scripts import oem_policy
        self.oem = copy.deepcopy(json.loads((WORKSPACE / policy.OEM_CONTRACT_PATH).read_bytes()))
        self.oem["factory_package_sha256"] = self.package
        selected = {"/vendor/etc/selinux/plat_pub_versioned.cil", "/vendor/etc/selinux/vendor_sepolicy.cil",
                    "/odm/etc/selinux/odm_sepolicy.cil"}
        self.oem["unchanged_factory_inputs"] = [copy.deepcopy(row) for row in self.correction["inputs"]
                                                  if row["runtime_path"] in selected]
        self.oem["existing_vendor_derivation"].update(
            contract_sha256=policy.identity(policy.encoded(self.correction))["sha256"],
            **policy.identity(b"not built\n"))
        self.capability = json.loads((WORKSPACE / policy.OEM_CAPABILITY_PATH).read_bytes())
        self.capability["factory_package_sha256"] = self.package
        cap_raw = policy.encoded(self.capability)
        (self.workspace / policy.OEM_CAPABILITY_PATH).write_bytes(cap_raw)
        self.oem["required_capability_contract"]["sha256"] = policy.identity(cap_raw)["sha256"]
        self.config["oem_policy"] = {"contract_path": policy.OEM_CONTRACT_PATH,
                                     "native_target": policy.OEM_CHECK_TARGET,
                                     "contract_id": self.oem["contract_id"],
                                     "default_enabled": False, "factory_inputs_rewritten": False}
        for row in self.oem["source_files"]:
            path = self.workspace / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((WORKSPACE / row["path"]).read_bytes())
        (self.workspace / "scripts/oem_policy.py").write_bytes(b"synthetic unused native checker source\n")
        self.oem_path = self.workspace / policy.OEM_CONTRACT_PATH
        self.write_oem_contract()
        return oem_policy

    def write_oem_contract(self):
        from scripts import oem_policy
        self.write_contracts()
        raw = policy.encoded(self.oem)
        self.oem_path.write_bytes(raw)
        self.enterContext(mock.patch.object(oem_policy, "CONTRACT_SHA256", policy.identity(raw)["sha256"]))

    def stage_oem(self, output=None):
        return policy.stage_inputs(self.corpus, output or self.output, factory_policy_receipt=self.receipt_path,
                                   oem_policy_contract=self.oem_path)

    def test_oem_bundle_requires_explicit_opt_in_and_keeps_original_input_bytes(self):
        self.install_oem_fixture()
        legacy_path = self.root / "legacy-private-bundle"
        legacy = self.stage(legacy_path)
        self.assertNotIn("oem_policy_contract", legacy)
        self.assertNotIn(policy.OEM_CHECK_TARGET, (legacy_path / "Android.bp").read_text())
        self.assertFalse((legacy_path / "tools/oem_policy.py").exists())
        result = self.stage_oem()
        verified = policy.verify_bundle(self.output)
        binding = {"path": policy.OEM_CONTRACT_PATH, **policy.identity(self.oem_path.read_bytes())}
        self.assertEqual(result["oem_policy_contract"], binding)
        self.assertEqual(verified["oem_policy_contract"], binding)
        self.assertEqual(len(result["files"]), 36)
        self.assertIn(policy.OEM_CHECK_TARGET, result["native_targets"])
        self.assertIn('required: ["sepolicy_neverallows", "' + policy.OEM_CHECK_TARGET + '"]',
                      (self.output / "Android.bp").read_text())
        for runtime in CORPUS_PATHS:
            self.assertEqual((self.output / "corpus" / runtime[1:]).read_bytes(),
                             (legacy_path / "corpus" / runtime[1:]).read_bytes())
        for row in self.oem["source_files"]:
            self.assertEqual((self.output / "provenance/source" / row["path"]).read_bytes(),
                             (self.workspace / row["path"]).read_bytes())
        self.assertEqual(result["scope"], policy.SCOPE)
        self.assertFalse(result["scope"]["policy_compiled"])

    def test_both_profiles_keep_the_exact_original_blueprint_template(self):
        self.install_oem_fixture()
        paths = [self.root / "legacy-private-bundle", self.output]
        self.stage(paths[0])
        self.stage_oem(paths[1])
        for path in paths:
            original = (path / "provenance/Android.bp.template").read_bytes()
            self.assertEqual(original, (self.workspace / "policy/nezha/Android.bp").read_bytes())
            self.assertNotEqual(original, (path / "Android.bp").read_bytes())
            self.assertNotIn(policy.OEM_BEGIN, (path / "Android.bp").read_text())

    def test_oem_contract_and_source_hash_or_capability_tampering_fail_closed(self):
        self.install_oem_fixture()
        for path in [self.oem_path, self.workspace / policy.OEM_CAPABILITY_PATH,
                     *[self.workspace / row["path"] for row in self.oem["source_files"]]]:
            original = path.read_bytes()
            with self.subTest(path=path.name):
                path.write_bytes(original + b"unreviewed\n")
                self.assert_rejected(self.stage_oem)
                self.assertFalse(self.output.exists())
                path.write_bytes(original)

    def test_oem_source_directory_rejects_extra_declarations_or_other_files(self):
        self.install_oem_fixture()
        extra = (self.workspace / self.oem["source_files"][0]["path"]).with_name("unreviewed.te")
        extra.write_bytes(b"type unreviewed_type;\n")
        self.assert_rejected(self.stage_oem)
        self.assertFalse(self.output.exists())

    def test_oem_contract_cannot_retarget_platform_factory_or_vendor_derivation(self):
        self.install_oem_fixture()
        original = copy.deepcopy(self.oem)
        mutations = [lambda c: c.update(factory_package_sha256="b" * 64),
                     lambda c: c["platform"].update(board_api="202604"),
                     lambda c: c["unchanged_factory_inputs"][0].update(sha256="b" * 64),
                     lambda c: c["existing_vendor_derivation"].update(sha256="b" * 64),
                     lambda c: c["existing_vendor_derivation"].update(contract_sha256="b" * 64)]
        for mutate in mutations:
            self.oem = copy.deepcopy(original)
            mutate(self.oem)
            self.write_oem_contract()
            self.assert_rejected(self.stage_oem)
            self.assertFalse(self.output.exists())

    def test_oem_helper_capability_cannot_enable_property_writes(self):
        self.install_oem_fixture()
        self.capability["capability"]["value"] = "true"
        raw = policy.encoded(self.capability)
        (self.workspace / policy.OEM_CAPABILITY_PATH).write_bytes(raw)
        self.oem["required_capability_contract"]["sha256"] = policy.identity(raw)["sha256"]
        self.write_oem_contract()
        self.assert_rejected(self.stage_oem)
        self.assertFalse(self.output.exists())

    def test_oem_receipt_cannot_remove_or_forge_its_source_contract(self):
        self.install_oem_fixture()
        self.stage_oem()
        path = self.output / policy.RECEIPT_NAME
        original = json.loads(path.read_bytes())
        for binding in (None, {**original["oem_policy_contract"], "sha256": "b" * 64}):
            receipt = copy.deepcopy(original)
            receipt["oem_policy_contract"] = binding
            path.write_bytes(policy.encoded(receipt))
            self.assert_rejected(lambda: policy.verify_bundle(self.output))
        receipt = copy.deepcopy(original)
        del receipt["oem_policy_contract"]
        path.write_bytes(policy.encoded(receipt))
        self.assert_rejected(lambda: policy.verify_bundle(self.output))

    def test_transferred_oem_sources_tool_and_helper_contract_are_rehashed(self):
        self.install_oem_fixture()
        self.stage_oem()
        for member in ["tools/oem_policy.py", "tools/nezha-init-helper-capability.json",
                       "tools/nezha-oem-policy.json", "provenance/Android.bp.template",
                       *["provenance/source/" + row["path"] for row in self.oem["source_files"]]]:
            path = self.output / member
            original = path.read_bytes()
            with self.subTest(member=member):
                path.write_bytes(original + b"changed")
                self.assert_rejected(lambda: policy.verify_bundle(self.output))
                path.write_bytes(original)

    def test_blueprint_renderer_rejects_duplicate_or_removed_profile_markers(self):
        path = self.workspace / "policy/nezha/Android.bp"
        original = path.read_bytes()
        for raw in [original.replace(policy.OEM_BEGIN.encode(), b""),
                    original + policy.OEM_BEGIN.encode(),
                    original.replace(b'required: ["sepolicy_neverallows"]', b'required: []')]:
            path.write_bytes(raw)
            self.assert_rejected(self.stage)
            self.assertFalse(self.output.exists())

    def test_oem_cli_flag_records_separate_admission_without_native_execution(self):
        self.install_oem_fixture()
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            code = policy.main(["stage", "--corpus-root", str(self.corpus), "--factory-capture-root",
                                str(self.capture), "--output", str(self.output),
                                "--oem-policy-contract", str(self.oem_path)])
        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["oem_policy_contract"]["path"], policy.OEM_CONTRACT_PATH)
        self.assertFalse(result["scope"]["contexts_validated"])


class NativePolicyTemplateTests(unittest.TestCase):
    def test_current_public_controls_load_without_private_inputs(self):
        reader = policy.vendor_policy.Reader()
        contract, correction, controls = policy._contracts(reader)
        self.assertEqual(contract["device"], "nezha")
        self.assertEqual(contract["package_sha256"], correction["factory_package_sha256"])
        self.assertEqual(len(correction["inputs"]), 10)
        self.assertEqual(len(contract["contexts"]), 13)
        self.assertEqual(set(controls), set(policy.CONTROL_FILES))
        self.assertTrue(all(path.is_relative_to(WORKSPACE) for path in reader.bindings))
        self.assertFalse(any(path.relative_to(WORKSPACE).parts[0] in {"artifacts", "evidence", "reports"}
                             for path in reader.bindings))
        reader.recheck()

    def test_current_public_oem_controls_load_without_private_inputs(self):
        reader = policy.vendor_policy.Reader()
        contract, correction, controls = policy._contracts(reader)
        binding = policy._oem_controls(reader, WORKSPACE / policy.OEM_CONTRACT_PATH, contract, correction, controls)
        self.assertEqual(binding, {"path": policy.OEM_CONTRACT_PATH,
                                   **policy.identity((WORKSPACE / policy.OEM_CONTRACT_PATH).read_bytes())})
        self.assertIn("tools/oem_policy.py", controls)
        self.assertIn("tools/nezha-init-helper-capability.json", controls)
        self.assertIn(policy.OEM_CHECK_TARGET, controls["Android.bp"].decode())
        self.assertFalse(any(path.relative_to(WORKSPACE).parts[0] in {"artifacts", "evidence", "reports"}
                             for path in reader.bindings))
        reader.recheck()

    def test_optional_native_guard_uses_all_current_inputs_without_binary_dependency_cycle(self):
        from scripts import oem_policy
        bp = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        rendered = policy._render_blueprint(bp, True).decode()
        block = rendered.split('name: "' + policy.OEM_CHECK_TARGET + '"', 1)[1].split("\n}", 1)[0]
        for name in [*oem_policy.INPUT_FLAGS, "factory_vendor", "capability_contract", "tool_source", "output"]:
            self.assertIn("--" + name.replace("_", "-"), block)
        for module in ("plat_sepolicy.cil", "plat_mapping_file", "system_ext_sepolicy.cil",
                       "system_ext_mapping_file", "product_sepolicy.cil", "product_mapping_file",
                       "nezha_factory_genfs_policy", "nezha_factory_vendor_policy{derived/vendor_sepolicy.cil}"):
            self.assertIn('":' + module + '"', block)
        self.assertNotIn(":nezha_factory_precompiled_sepolicy", block)
        self.assertIn('java_genrule {\n    name: "' + policy.OEM_CHECK_TARGET + '"', rendered)
        self.assertIn('required: ["sepolicy_neverallows", "' + policy.OEM_CHECK_TARGET + '"]', rendered)
        self.assertNotIn('"corpus/system/', block)
        self.assertNotIn('"corpus/system_ext/', block)
        self.assertNotIn('"corpus/product/', block)
        self.assertIn('out: ["oem-policy-native-check.json"]', block)

    def test_combined_binary_uses_current_framework_outputs_and_strict_guards(self):
        text = (WORKSPACE / "policy/nezha/Android.bp").read_text()
        block = text.split("se_policy_binary {", 1)[1].split("\n}", 1)[0]
        for module in ("plat_sepolicy.cil", "plat_mapping_file", "system_ext_sepolicy.cil",
                       "system_ext_mapping_file", "product_sepolicy.cil", "product_mapping_file"):
            self.assertIn('":' + module + '"', block)
        self.assertNotIn('"corpus/system/', block)
        self.assertNotIn('"corpus/system_ext/', block)
        self.assertNotIn('"corpus/product/', block)
        self.assertIn('":nezha_factory_vendor_policy{derived/vendor_sepolicy.cil}"', block)
        self.assertIn('":nezha_factory_genfs_policy"', block)
        self.assertIn("ignore_neverallow: false", block)
        self.assertIn("installable: false", block)
        self.assertNotIn("permissive_domains_on_user_builds", block)
        self.assertIn('required: ["sepolicy_neverallows"]', block)

    def test_genfs_uses_current_device_arch_output_through_upstream_filegroup_pattern(self):
        bp = (WORKSPACE / "policy/nezha/Android.bp").read_text()
        group = bp.split('name: "nezha_factory_genfs_policy"', 1)[1].split("\n}", 1)[0]
        self.assertIn('filegroup {\n    name: "nezha_factory_genfs_policy"', bp)
        self.assertIn('device_first_srcs: [":plat_sepolicy_genfs_202504.cil"]', group)
        self.assertNotIn('"corpus/', group)
        binary = bp.split("se_policy_binary {", 1)[1].split("\n}", 1)[0]
        self.assertNotIn('":plat_sepolicy_genfs_202504.cil"', binary)
        sources = binary.split("srcs: [", 1)[1].split("]", 1)[0]
        self.assertTrue(sources.strip().endswith('\":nezha_factory_genfs_policy\",'))
        self.assertEqual(sources.count('\"'), 20)

    def test_native_derivation_has_both_outputs_and_the_original_complete_corpus(self):
        text = (WORKSPACE / "policy/nezha/Android.bp").read_text()
        block = text.split("genrule {", 1)[1].split("\n}", 1)[0]
        for runtime in CORPUS_PATHS:
            self.assertIn('"corpus' + runtime + '"', block)
        self.assertIn('"derived/vendor_sepolicy.cil", "derived/receipt.json"', block)
        for flag in ("--corpus-root", "--contract", "--tool-source", "--private-output-root", "--output"):
            self.assertIn(flag, block)
        self.assertIn("$(location nezha_vendor_policy_derivation_tool) derive", block)
        self.assertIn("readlink -f $(genDir)", block)
        self.assertIn("--output $$(readlink -f $(genDir))/candidate", block)
        self.assertNotIn("--output $$(readlink -f $(genDir))/derived", block)
        self.assertNotIn(" -N ", text)

    def test_context_aggregators_preserve_android_common_variant_dependencies(self):
        bp = (WORKSPACE / "policy/nezha/Android.bp").read_text()
        # Generated Android contexts have os:android,arch:common variants.
        # Match the pinned upstream sepolicy_test module type; a plain genrule
        # requests an empty dependency variant and fails graph construction.
        for kind in ("file", "hwservice", "service"):
            declaration = 'java_genrule {\n    name: "nezha_factory_all_' + kind + '_contexts",'
            self.assertIn(declaration, bp)
        # The derivation takes regular files and a host tool; it has no device
        # context dependency and must retain its existing generic genrule.
        self.assertIn('genrule {\n    name: "nezha_factory_vendor_policy",', bp)
        self.assertNotIn('java_genrule {\n    name: "nezha_factory_vendor_policy",', bp)

    def test_context_targets_use_real_factory_captures_and_no_full_labeling_claim(self):
        config = json.loads((WORKSPACE / policy.CONTRACT_PATH).read_text())
        bp = (WORKSPACE / "policy/nezha/Android.bp").read_text()
        self.assertEqual(len(config["contexts"]), 13)
        self.assertEqual(len([row for row in config["contexts"] if row["size_bytes"] == 0]), 4)
        self.assertFalse(config["full_treble_labeling_provided"])
        self.assertFalse(config["image_integration_provided"])
        for target in config["native_targets"]:
            self.assertIn('name: "' + target + '"', bp)
        for row in config["contexts"]:
            basename = Path(row["path"]).name
            if basename not in config["unvalidated_context_kinds"]:
                self.assertIn('"' + row["path"] + '"', bp)
        self.assertIn("-t TestDevTypeViolations", bp)
        self.assertIn("&& touch $(out)", bp)
        self.assertNotIn("treble_sepolicy_tests_202504", bp)

    def test_seapp_checks_separate_platform_and_vendor_coredomain_rules(self):
        bp = (WORKSPACE / "policy/nezha/Android.bp").read_text()
        vendor = bp.split('name: "nezha_factory_seapp_contexts_checked"', 1)[1].split("\n}", 1)[0]
        platform = bp.split('name: "nezha_factory_platform_seapp_contexts_checked"', 1)[1].split("\n}", 1)[0]
        self.assertIn(" -c ", vendor)
        self.assertNotIn(" -c ", platform)
        for prefix in ("plat", "system_ext", "product"):
            self.assertIn('":' + prefix + '_seapp_contexts"', platform)
        self.assertIn('":plat_seapp_neverallows"', platform)


if __name__ == "__main__":
    unittest.main()
