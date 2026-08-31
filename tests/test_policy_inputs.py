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
import struct
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


def provider_elf(needed="libc.so", *, soname=None):
    """A small synthetic ARM64 ELF with one DT_NEEDED entry; never executed."""
    raw = bytearray(0x800)
    raw[:16] = b"\x7fELF\x02\x01\x01" + b"\0" * 9
    strings = b"\0" + needed.encode() + b"\0"
    dynamic = [(1, 1)]
    if soname is not None:
        dynamic.append((14, len(strings)))
        strings += soname.encode() + b"\0"
    dynamic += [(5, 0x500), (10, len(strings)), (0, 0)]
    interpreter = b"/system/bin/linker64\0"
    struct.pack_into("<HHIQQQIHHHHHH", raw, 16, 3, 183, 1, 0x400, 64, 0, 0, 64, 56,
                     3 if soname is None else 2, 0, 0, 0)
    struct.pack_into("<IIQQQQQQ", raw, 64, 1, 5 if soname is None else 4, 0, 0, 0, len(raw), len(raw), 4096)
    struct.pack_into("<IIQQQQQQ", raw, 120, 2, 6, 0x200, 0x200, 0, len(dynamic) * 16, len(dynamic) * 16, 8)
    if soname is None:
        struct.pack_into("<IIQQQQQQ", raw, 176, 3, 4, 0x400, 0x400, 0, len(interpreter), len(interpreter), 1)
    for index, pair in enumerate(dynamic):
        struct.pack_into("<qQ", raw, 0x200 + index * 16, *pair)
    raw[0x400:0x400 + len(interpreter)] = interpreter
    raw[0x500:0x500 + len(strings)] = strings
    return bytes(raw)


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
        self.assertNotIn("oem_property_contract", result)
        self.assertIsNone(verified["oem_property_contract"])
        self.assertIsNone(verified["framework_provider_policy_contract"])
        self.assertIsNone(verified["framework_provider_inputs"])
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
        invalid = [original.replace(policy.OEM_BEGIN.encode(), b""),
                   original + policy.OEM_BEGIN.encode(),
                   original.replace(b'required: ["sepolicy_neverallows"]', b'required: []')]
        for pair in (*policy.OEM_PROPERTY_BLOCKS, *policy.PROVIDER_BLOCKS):
            for marker in pair:
                invalid.extend([original.replace(marker.encode(), b""), original + marker.encode()])
        for raw in invalid:
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

    def install_property_fixture(self):
        self.install_oem_fixture()
        self.properties = copy.deepcopy(json.loads((WORKSPACE / policy.OEM_PROPERTY_CONTRACT_PATH).read_bytes()))
        self.properties["base_oem_contract"] = {
            "path": policy.OEM_CONTRACT_PATH, **policy.identity(self.oem_path.read_bytes())}
        for key in ("factory_package_sha256", "required_capability_contract", "device", "platform", "profile"):
            self.properties[key] = copy.deepcopy(self.oem[key])
        self.config["oem_properties"] = {
            "contract_path": policy.OEM_PROPERTY_CONTRACT_PATH,
            "native_target": policy.OEM_CHECK_TARGET,
            "contract_id": self.properties["contract_id"],
            "default_enabled": False, "factory_inputs_rewritten": False}
        for row in self.properties["source_files"]:
            path = self.workspace / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((WORKSPACE / row["path"]).read_bytes())
        self.property_path = self.workspace / policy.OEM_PROPERTY_CONTRACT_PATH
        self.write_property_contract()

    def write_property_contract(self):
        from scripts import oem_policy
        self.write_contracts()
        raw = policy.encoded(self.properties)
        self.property_path.write_bytes(raw)
        self.enterContext(mock.patch.object(oem_policy, "PROPERTY_CONTRACT_SHA256", policy.identity(raw)["sha256"]))

    def stage_properties(self, output=None):
        return policy.stage_inputs(self.corpus, output or self.output, factory_policy_receipt=self.receipt_path,
                                   oem_policy_contract=self.oem_path, oem_property_contract=self.property_path)

    def test_property_profile_requires_the_separately_explicit_oem_base(self):
        self.install_property_fixture()
        self.assert_rejected(lambda: policy.stage_inputs(
            self.corpus, self.output, factory_policy_receipt=self.receipt_path,
            oem_property_contract=self.property_path))
        self.assertFalse(self.output.exists())
        for stage, name in ((self.stage, "legacy"), (self.stage_oem, "oem-v1")):
            output = self.root / name
            result = stage(output)
            self.assertNotIn("oem_property_contract", result)
            self.assertIsNone(policy.verify_bundle(output)["oem_property_contract"])
            self.assertNotIn("--property-contract", (output / "Android.bp").read_text())
            self.assertFalse((output / "tools/nezha-oem-properties.json").exists())

    def test_property_bundle_binds_both_profiles_and_preserves_original_factory_inputs(self):
        self.install_property_fixture()
        result = self.stage_properties()
        verified = policy.verify_bundle(self.output)
        base = {"path": policy.OEM_CONTRACT_PATH, **policy.identity(self.oem_path.read_bytes())}
        properties = {"path": policy.OEM_PROPERTY_CONTRACT_PATH, **policy.identity(self.property_path.read_bytes())}
        self.assertEqual(result["oem_policy_contract"], base)
        self.assertEqual(verified["oem_policy_contract"], base)
        self.assertEqual(result["oem_property_contract"], properties)
        self.assertEqual(verified["oem_property_contract"], properties)
        self.assertEqual(len(result["files"]), 41)
        self.assertEqual(result["native_targets"].count(policy.OEM_CHECK_TARGET), 1)
        self.assertEqual(result["scope"], policy.SCOPE)
        self.assertEqual(verified["scope"], policy.SCOPE)
        for runtime in CORPUS_PATHS:
            self.assertEqual((self.output / "corpus" / runtime[1:]).read_bytes(),
                             self.originals[self.corpus / runtime[1:]])
        for path, original in self.originals.items():
            self.assertEqual(path.read_bytes(), original)
        for row in self.properties["source_files"]:
            self.assertEqual((self.output / "provenance/source" / row["path"]).read_bytes(),
                             (self.workspace / row["path"]).read_bytes())
        self.assertIn("--property-contract", (self.output / "Android.bp").read_text())
        self.assertIn("--system-ext-property-contexts", (self.output / "Android.bp").read_text())

    def test_property_contract_cannot_change_base_factory_helper_device_or_platform(self):
        self.install_property_fixture()
        original = copy.deepcopy(self.properties)
        mutations = [lambda c: c["base_oem_contract"].update(sha256="b" * 64),
                     lambda c: c["base_oem_contract"].update(size_bytes=1),
                     lambda c: c.update(factory_package_sha256="b" * 64),
                     lambda c: c["required_capability_contract"].update(value="true"),
                     lambda c: c["device"].update(codename="other"),
                     lambda c: c["platform"].update(branch="newer"),
                     lambda c: c.update(profile="complete-rom")]
        for mutate in mutations:
            self.properties = copy.deepcopy(original)
            mutate(self.properties)
            self.write_property_contract()
            self.assert_rejected(self.stage_properties)
            self.assertFalse(self.output.exists())

    def test_property_admission_must_select_the_required_native_guard_without_image_rewrites(self):
        self.install_property_fixture()
        original = copy.deepcopy(self.config["oem_properties"])
        for key, value in (("contract_path", policy.OEM_CONTRACT_PATH), ("native_target", "other"),
                           ("contract_id", "other"), ("default_enabled", True),
                           ("factory_inputs_rewritten", True)):
            self.config["oem_properties"] = {**original, key: value}
            self.write_property_contract()
            self.assert_rejected(self.stage_properties)
            self.assertFalse(self.output.exists())

    def test_property_source_hashes_contract_and_directory_inventory_are_checked(self):
        self.install_property_fixture()
        for path in [self.property_path, *[self.workspace / row["path"] for row in self.properties["source_files"]]]:
            original = path.read_bytes()
            with self.subTest(path=path.name):
                path.write_bytes(original + b"unreviewed\n")
                self.assert_rejected(self.stage_properties)
                self.assertFalse(self.output.exists())
                path.write_bytes(original)
        extra = (self.workspace / self.properties["source_files"][0]["path"]).with_name("unreviewed.te")
        extra.write_bytes(b"allow unreviewed unreviewed:file write;\n")
        self.assert_rejected(self.stage_properties)
        self.assertFalse(self.output.exists())

    def test_property_source_parser_rejects_permission_broadening_even_after_identity_updates(self):
        self.install_property_fixture()
        row = next(row for row in self.properties["source_files"] if row["path"].endswith("/mediaextractor.te"))
        source = self.workspace / row["path"]
        original = source.read_bytes()
        for appended in (b"set_prop(mediaextractor, vendor_mm_parser_prop)\n",
                         b"get_prop(shell, vendor_mm_parser_prop)\n",
                         b"allow mediaextractor vendor_mm_parser_prop:file write;\n"):
            source.write_bytes(original + appended)
            row.update(policy.identity(source.read_bytes()))
            self.write_property_contract()
            self.assert_rejected(self.stage_properties)
            self.assertFalse(self.output.exists())

    def test_property_receipt_cannot_drop_base_or_remove_or_forge_the_extra_profile(self):
        self.install_property_fixture()
        self.stage_properties()
        path = self.output / policy.RECEIPT_NAME
        original = json.loads(path.read_bytes())
        for field in ("oem_policy_contract", "oem_property_contract"):
            for value in (None, {**original[field], "sha256": "b" * 64}):
                receipt = copy.deepcopy(original)
                receipt[field] = value
                path.write_bytes(policy.encoded(receipt))
                self.assert_rejected(lambda: policy.verify_bundle(self.output))
            receipt = copy.deepcopy(original)
            del receipt[field]
            path.write_bytes(policy.encoded(receipt))
            self.assert_rejected(lambda: policy.verify_bundle(self.output))

    def test_transferred_property_contract_sources_and_generated_blueprint_are_rehashed(self):
        self.install_property_fixture()
        self.stage_properties()
        for member in ["Android.bp", "tools/nezha-oem-properties.json",
                       *["provenance/source/" + row["path"] for row in self.properties["source_files"]]]:
            path = self.output / member
            original = path.read_bytes()
            with self.subTest(member=member):
                path.write_bytes(original + b"changed")
                self.assert_rejected(lambda: policy.verify_bundle(self.output))
                path.write_bytes(original)

    def test_property_cli_reports_admission_separately_from_native_or_hardware_results(self):
        self.install_property_fixture()
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            code = policy.main(["stage", "--corpus-root", str(self.corpus), "--factory-capture-root",
                                str(self.capture), "--output", str(self.output),
                                "--oem-policy-contract", str(self.oem_path),
                                "--oem-property-contract", str(self.property_path)])
        self.assertEqual(code, 0)
        result = json.loads(stdout.getvalue())
        self.assertEqual(result["oem_property_contract"]["path"], policy.OEM_PROPERTY_CONTRACT_PATH)
        self.assertEqual(result["scope"], policy.SCOPE)

    def install_provider_fixture(self, *, properties=False, derivation=False):
        from scripts import framework_provider_inputs as inputs
        from scripts import framework_provider_policy as source
        self.install_property_fixture() if properties else self.install_oem_fixture()
        self.with_provider_properties = properties
        self.provider_source = copy.deepcopy(json.loads((WORKSPACE / policy.PROVIDER_POLICY_CONTRACT_PATH).read_bytes()))
        actual_profile = json.loads((WORKSPACE / policy.PROVIDER_INPUTS_CONTRACT_PATH).read_bytes())
        self.provider_profile = {
            "schema_version": 1, "device": "nezha", "bundle": inputs.BUNDLE,
            "module_package": inputs.MODULE_PACKAGE, "platform": copy.deepcopy(self.config["platform"]),
            "factory_package_sha256": self.package,
            "factory_image": {"partition": "system_ext", "sha256": "b" * 64, "size_bytes": 1234567},
            "source_lock": {"path": "config/provider-source-lock.json", **policy.identity(b"provider fixture lock\n")},
            "captures": {}, "files": [], "providers": copy.deepcopy(actual_profile["providers"]),
            "source_dependencies": {"libc.so": "libc"}, "source_replacements": [],
            "required_source_patches": [], "runtime_requirements": ["Synthetic inputs; runtime not tested."],
            "native_output_recipe": copy.deepcopy(inputs.NATIVE_OUTPUT_RECIPE), "scope": copy.deepcopy(inputs.SCOPE),
            "payload_derivations": [],
        }
        (self.workspace / "config/provider-source-lock.json").write_bytes(b"provider fixture lock\n")
        capture = self.root / "provider-capture"
        capture.mkdir()
        receipt = {"schema_version": 1, "operation": "erofs-capture",
                   "image": {"sha256": "b" * 64, "size_bytes": 1234567},
                   "image_mounted": False, "firmware_executed": False, "symlinks_followed": False, "files": []}
        self.provider_source["selected_provider_artifacts"] = []
        for index, provider in enumerate(self.provider_profile["providers"]):
            payloads = {
                "binary": provider_elf(),
                "init_rc": ("service " + provider["init_service"] + " " + provider["binary"]
                            + "\n    class hal\n    user system\n").encode(),
                "vintf_fragment": ('<manifest version="9.0" type="framework"><hal format="aidl"><name>'
                                   + provider["hal"] + '</name><fqname>' + provider["interface"] + '/'
                                   + provider["instance"] + '</fqname></hal></manifest>\n').encode(),
            }
            for kind, data in payloads.items():
                runtime = provider[kind]
                relative = str(index) + "-" + kind
                (capture / relative).write_bytes(data)
                mode = "0755" if kind == "binary" else "0644"
                row = {"runtime_path": runtime, "kind": kind, "capture": "fixture", "capture_path": relative,
                       "mode": mode, **policy.identity(data)}
                if kind == "binary":
                    row.update(module="nezha_framework_fixture_" + str(index), needed=["libc.so"], soname=None)
                self.provider_profile["files"].append(row)
                receipt["files"].append({"path": runtime.removeprefix("/system_ext"), "output_path": relative,
                                          "type": "regular", "mode": mode, "readback_verified": True,
                                          **policy.identity(data)})
                self.provider_source["selected_provider_artifacts"].append({
                    "path": runtime.removeprefix("/system_ext"), **policy.identity(data)})
        if derivation:
            old, new = "libfixture-V2.so", "libfixture-V4.so"
            runtime = "/system_ext/lib64/libfixture.so"
            original = provider_elf(old, soname="libfixture.so")
            offset = 0x501 + old.index("2")
            derived = original[:offset] + b"4" + original[offset + 1:]
            (capture / "fixture-library").write_bytes(original)
            self.provider_profile["files"].append({
                "runtime_path": runtime, "kind": "shared_library", "capture": "fixture",
                "capture_path": "fixture-library", "mode": "0644", **policy.identity(original),
                "module": "nezha_framework_fixture_library", "needed": [old], "soname": "libfixture.so"})
            receipt["files"].append({"path": runtime.removeprefix("/system_ext"), "output_path": "fixture-library",
                                     "type": "regular", "mode": "0644", "readback_verified": True,
                                     **policy.identity(original)})
            evidence = b'{"scope":"synthetic dependency evidence, no runtime proof"}\n'
            evidence_path = "research/fixture-provider-compatibility.json"
            (self.workspace / evidence_path).write_bytes(evidence)
            self.provider_profile["payload_derivations"] = [{"runtime_path": runtime,
                "recipe": {"kind": "exact-equal-length-dt-needed-string-replacement",
                           "original": policy.identity(original), "derived": policy.identity(derived),
                           "old": old, "new": new, "dt_needed_string_file_offset": 0x501,
                           "changed_byte_file_offset": offset, "original_byte_hex": "32", "derived_byte_hex": "34"},
                "evidence": {"path": evidence_path, **policy.identity(evidence)}}]
            self.provider_profile["source_dependencies"][new] = "libfixture-V4"
            self.provider_derivation_bytes = (original, derived)
        capture_raw = policy.encoded(receipt)
        (capture / "capture.json").write_bytes(capture_raw)
        self.provider_profile["captures"]["fixture"] = {"path": "capture.json", **policy.identity(capture_raw)}
        self.provider_source["factory_package_sha256"] = self.package
        self.provider_source["required_contracts"]["oem_policy"]["sha256"] = policy.identity(self.oem_path.read_bytes())["sha256"]
        self.provider_source["required_contracts"]["init_helper"]["sha256"] = policy.identity(
            (self.workspace / policy.OEM_CAPABILITY_PATH).read_bytes())["sha256"]
        self.config["framework_provider_policy"] = {
            "contract_id": self.provider_source["contract_id"], "contract_path": policy.PROVIDER_POLICY_CONTRACT_PATH,
            "provider_inputs_contract_path": policy.PROVIDER_INPUTS_CONTRACT_PATH,
            "provider_inputs_check": policy.PROVIDER_INPUTS_CHECK, "native_target": policy.OEM_CHECK_TARGET,
            "default_enabled": False, "factory_inputs_rewritten": False,
        }
        for row in self.provider_source["source_files"]:
            path = self.workspace / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((WORKSPACE / row["path"]).read_bytes())
        for name in ("framework_provider_policy", "framework_provider_inputs", "framework_provider_derivations"):
            (self.workspace / ("scripts/" + name + ".py")).write_bytes(b"synthetic provider control source\n")
        self.provider_source_path = self.workspace / policy.PROVIDER_POLICY_CONTRACT_PATH
        self.write_provider_contracts()
        self.enterContext(mock.patch.object(inputs, "ROOT", self.workspace))
        self.provider_bundle = self.workspace / "artifacts/provider-bundle"
        self.provider_bundle.parent.mkdir(exist_ok=True)
        # Use the real external stager/verifier over synthetic ELF, XML and
        # capture files. No mocked admission result or firmware process is used.
        inputs.stage_inputs(capture, self.provider_bundle)
        self.provider_receipt = self.provider_bundle / inputs.RECEIPT
        self.original_provider_files = {path.relative_to(self.provider_bundle): path.read_bytes()
                                       for path in self.provider_bundle.rglob("*") if path.is_file()}
        return inputs, source

    def write_provider_contracts(self):
        from scripts import framework_provider_policy as source
        self.write_contracts()
        profile_raw = policy.encoded(self.provider_profile)
        (self.workspace / policy.PROVIDER_INPUTS_CONTRACT_PATH).write_bytes(profile_raw)
        self.provider_source["required_contracts"]["provider_inputs"]["sha256"] = policy.identity(profile_raw)["sha256"]
        source_raw = policy.encoded(self.provider_source)
        self.provider_source_path.write_bytes(source_raw)
        self.enterContext(mock.patch.object(source, "CONTRACT_SHA256", policy.identity(source_raw)["sha256"]))

    def stage_providers(self, output=None):
        return policy.stage_inputs(
            self.corpus, output or self.output, factory_policy_receipt=self.receipt_path,
            oem_policy_contract=self.oem_path,
            oem_property_contract=self.property_path if self.with_provider_properties else None,
            framework_provider_policy_contract=self.provider_source_path,
            framework_provider_inputs_receipt=self.provider_receipt)

    def verify_providers(self, output=None, receipt=None):
        return policy.verify_bundle(output or self.output,
                                    framework_provider_inputs_receipt=receipt or self.provider_receipt)

    def test_provider_profile_reverifies_real_synthetic_bundle_and_preserves_both_input_sets(self):
        inputs, _ = self.install_provider_fixture()
        result = self.stage_providers()
        verified = self.verify_providers()
        provider = inputs.verify_bundle(self.provider_bundle)
        self.assertEqual(result["framework_provider_inputs"], provider)
        self.assertEqual(verified["framework_provider_inputs"], provider)
        self.assertEqual(result["framework_provider_policy_contract"], {
            "path": policy.PROVIDER_POLICY_CONTRACT_PATH, **policy.identity(self.provider_source_path.read_bytes())})
        self.assertEqual(len(result["files"]), 46)
        self.assertEqual(result["native_targets"].count(inputs.CHECK), 1)
        self.assertNotIn("oem_property_contract", result)
        self.assertEqual(verified["scope"], policy.SCOPE)
        for relative, data in self.original_provider_files.items():
            self.assertEqual((self.provider_bundle / relative).read_bytes(), data)
        for path, data in self.originals.items():
            self.assertEqual(path.read_bytes(), data)
        self.assertFalse(any(row["path"].startswith("proprietary/") for row in result["files"]))

    def test_provider_profile_composes_with_explicit_properties_without_enabling_them_implicitly(self):
        self.install_provider_fixture(properties=True)
        result = self.stage_providers()
        verified = self.verify_providers()
        self.assertEqual(len(result["files"]), 51)
        self.assertEqual(verified["oem_property_contract"]["path"], policy.OEM_PROPERTY_CONTRACT_PATH)
        self.assertEqual(verified["framework_provider_policy_contract"]["path"], policy.PROVIDER_POLICY_CONTRACT_PATH)
        text = (self.output / "Android.bp").read_text()
        self.assertIn("--property-contract", text)
        self.assertIn("--provider-contract", text)
        self.assertEqual(result["scope"], policy.SCOPE)

    def test_provider_derivation_composes_with_properties_without_replacing_originals(self):
        inputs, _ = self.install_provider_fixture(properties=True, derivation=True)
        result = self.stage_providers()
        verified = self.verify_providers()
        self.assertEqual(verified["framework_provider_inputs"]["payload_derivations"],
                         self.provider_profile["payload_derivations"])
        self.assertEqual(len(result["files"]), 52)
        evidence = self.provider_profile["payload_derivations"][0]["evidence"]
        for original, member in ((self.workspace / evidence["path"], "provenance/evidence/" + evidence["path"]),
                                 (self.workspace / "scripts/framework_provider_derivations.py",
                                  "provenance/tools/framework_provider_derivations.py")):
            self.assertEqual((self.output / member).read_bytes(), original.read_bytes())
        namespace = {"__name__": "offline_test"}
        script = self.provider_bundle / "tools/verify_framework_provider_inputs.py"
        exec(compile(script.read_bytes(), str(script), "exec"), namespace)
        native_output = self.root / "native-output"
        with mock.patch("sys.stdout", new=io.StringIO()) as stdout:
            namespace["main"](["--output-dir", str(native_output),
                               *(str(self.provider_bundle / name) for name in namespace["EXPECTED"])])
        self.assertIs(json.loads(stdout.getvalue())["verified"], True)
        original, derived = self.provider_derivation_bytes
        self.assertEqual((self.provider_bundle / "proprietary/system_ext/lib64/libfixture.so").read_bytes(), original)
        self.assertEqual((native_output / "verified/system_ext/lib64/libfixture.so").read_bytes(), derived)
        self.assertEqual(sum(a != b for a, b in zip(original, derived)), 1)
        self.assertEqual(inputs.verify_bundle(self.provider_bundle), verified["framework_provider_inputs"])
        self.assertFalse(verified["scope"]["complete_rom_admitted"])

    def install_evolution_fixture(self):
        from scripts import evolution_policy_base
        self.install_provider_fixture(properties=True, derivation=True)
        self.evolution = copy.deepcopy(json.loads((WORKSPACE / policy.EVOLUTION_BASE_CONTRACT_PATH).read_bytes()))
        self.evolution["required_contracts"] = {
            "oem_policy": {"path": policy.OEM_CONTRACT_PATH, **policy.identity(self.oem_path.read_bytes())},
            "oem_properties": {"path": policy.OEM_PROPERTY_CONTRACT_PATH, **policy.identity(self.property_path.read_bytes())},
            "framework_provider_policy": {"path": policy.PROVIDER_POLICY_CONTRACT_PATH,
                                           **policy.identity(self.provider_source_path.read_bytes())},
        }
        for paths in policy.EVOLUTION_BASE_OWNED_GROUPS.values():
            for name in paths:
                target = self.workspace / name
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.exists():
                    target.write_bytes((WORKSPACE / name).read_bytes())
        (self.workspace / "scripts/evolution_policy_base.py").write_bytes(b"synthetic native comparison helper, never executed\n")
        self.evolution_path = self.workspace / policy.EVOLUTION_BASE_CONTRACT_PATH
        self.write_evolution_contract()
        return evolution_policy_base

    def write_evolution_contract(self):
        from scripts import evolution_policy_base
        raw = policy.encoded(self.evolution)
        self.evolution_path.write_bytes(raw)
        self.enterContext(mock.patch.object(evolution_policy_base, "CONTRACT_SHA256", policy.identity(raw)["sha256"]))

    def evolution_options(self):
        return {"factory_policy_receipt": self.receipt_path, "oem_policy_contract": self.oem_path,
                "oem_property_contract": self.property_path,
                "framework_provider_policy_contract": self.provider_source_path,
                "framework_provider_inputs_receipt": self.provider_receipt,
                "evolution_policy_base_contract": self.evolution_path}

    def stage_evolution(self, output=None):
        return policy.stage_inputs(self.corpus, output or self.output, **self.evolution_options())

    def test_evolution_bundle_is_explicit_repeatable_and_adds_no_copied_upstream_sources(self):
        self.install_evolution_fixture()
        baseline = self.stage_providers(self.root / "legacy-provider-bundle")
        result = self.stage_evolution()
        repeat = self.stage_evolution(self.root / "evolution-repeat")
        self.assertEqual(result, repeat)
        verified = self.verify_providers()
        self.assertEqual(verified["evolution_policy_base_contract"], {
            "path": policy.EVOLUTION_BASE_CONTRACT_PATH, **policy.identity(self.evolution_path.read_bytes())})
        self.assertNotIn("evolution_policy_base_contract", baseline)
        before = {row["path"]: row for row in baseline["files"]}
        after = {row["path"]: row for row in result["files"]}
        self.assertEqual(set(after) - set(before), {
            "tools/evolution_policy_base.py", "tools/evolution-policy-base.json",
            "provenance/nezha-owned-policy.Android.bp",
            "provenance/source/device/xiaomi/nezha/sepolicy/system_ext/public/attributes"})
        for path, row in before.items():
            if path != "Android.bp":
                self.assertEqual(after[path], row)
        self.assertFalse(any("device/lineage/" in row["path"] for row in result["files"]))
        self.assertEqual(result["classification_inputs"], baseline["classification_inputs"])
        self.assertEqual(result["native_targets"], baseline["native_targets"])
        self.assertEqual(result["scope"], policy.SCOPE)
        for path, raw in self.originals.items():
            self.assertEqual(path.read_bytes(), raw)

    def test_evolution_bundle_requires_all_explicit_source_profiles_before_reading(self):
        self.install_evolution_fixture()
        for name in ("oem_policy_contract", "oem_property_contract", "framework_provider_policy_contract",
                     "framework_provider_inputs_receipt"):
            options = {**self.evolution_options(), name: None}
            with self.subTest(name=name), mock.patch.object(policy, "_contracts") as load:
                self.assert_rejected(lambda: policy.stage_inputs(self.corpus, self.output, **options))
                load.assert_not_called()
            self.assertFalse(self.output.exists())

    def test_evolution_bundle_rejects_wrong_contract_coupling_and_broadened_exclusions(self):
        self.install_evolution_fixture()
        original = copy.deepcopy(self.evolution)
        mutations = [lambda value: value["required_contracts"]["oem_properties"].update(sha256="f" * 64),
                     lambda value: value.update(build_variant="userdebug"),
                     lambda value: value["platform"].update(release="future"),
                     lambda value: value["owned_source_groups"]["nezha_owned_system_ext_public_policy"].pop(),
                     lambda value: value["owned_source_groups"]["nezha_owned_system_ext_private_policy"][0].update(
                         path="device/xiaomi/nezha/sepolicy/system_ext/oem/private/*.te")]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.evolution = copy.deepcopy(original)
                mutate(self.evolution)
                self.write_evolution_contract()
                self.assert_rejected(self.stage_evolution)
                self.assertFalse(self.output.exists())

    def test_evolution_profile_cannot_be_removed_or_forged_in_a_transferred_receipt(self):
        self.install_evolution_fixture()
        self.stage_evolution()
        path = self.output / policy.RECEIPT_NAME
        original = json.loads(path.read_bytes())
        for mutation in (lambda value: value.pop("evolution_policy_base_contract"),
                         lambda value: value["evolution_policy_base_contract"].update(sha256="f" * 64)):
            changed = copy.deepcopy(original)
            mutation(changed)
            path.write_bytes(policy.encoded(changed))
            self.assert_rejected(self.verify_providers)
        path.write_bytes(policy.encoded(original))
        self.assertEqual(self.verify_providers()["status"], "verified")

    def test_evolution_transferred_tool_descriptor_groups_and_dsp_source_are_rehashed(self):
        self.install_evolution_fixture()
        self.stage_evolution()
        for name in ("tools/evolution_policy_base.py", "tools/evolution-policy-base.json",
                     "provenance/nezha-owned-policy.Android.bp",
                     "provenance/source/device/xiaomi/nezha/sepolicy/system_ext/public/attributes"):
            path = self.output / name
            original = path.read_bytes()
            with self.subTest(name=name):
                path.write_bytes(original + b"unreviewed\n")
                self.assert_rejected(self.verify_providers)
                path.write_bytes(original)
        self.assertEqual(self.verify_providers()["status"], "verified")

    def test_evolution_cli_flag_does_not_implicitly_enable_other_capabilities(self):
        base = ["stage", "--corpus-root", "corpus", "--factory-capture-root", "factory", "--output", "out"]
        for arguments, expected in (([], None), (["--evolution-policy-base-contract", "base.json"], Path("base.json"))):
            with mock.patch.object(policy, "stage_inputs", return_value={}) as stage, mock.patch("sys.stdout", io.StringIO()):
                self.assertEqual(policy.main([*base, *arguments]), 0)
            self.assertEqual(stage.call_args.kwargs["evolution_policy_base_contract"], expected)
            for name in ("oem_policy_contract", "oem_property_contract", "framework_provider_policy_contract"):
                self.assertIsNone(stage.call_args.kwargs[name])

    def install_camera_fixture(self):
        self.install_evolution_fixture()
        self.camera_path = self.workspace / policy.CAMERA_PROPERTY_CONTRACT_PATH
        self.camera_path.parent.mkdir(parents=True, exist_ok=True)
        self.camera_path.write_bytes((WORKSPACE / policy.CAMERA_PROPERTY_CONTRACT_PATH).read_bytes())
        camera = json.loads(self.camera_path.read_bytes())
        patch = self.workspace / camera["patch"]
        patch.write_bytes((WORKSPACE / camera["patch"]).read_bytes())
        return camera

    def stage_camera(self, output=None):
        return policy.stage_inputs(self.corpus, output or self.output, **self.evolution_options(),
                                   camera_property_capability_contract=self.camera_path)

    def test_camera_bundle_is_explicit_paired_and_does_not_replace_any_cil(self):
        camera = self.install_camera_fixture()
        baseline = self.stage_evolution(self.root / "camera-absent")
        result = self.stage_camera()
        self.assertEqual(result, self.stage_camera(self.root / "camera-repeat"))
        verified = self.verify_providers()
        self.assertEqual(verified["camera_property_capability_contract"], {
            "path": policy.CAMERA_PROPERTY_CONTRACT_PATH, **policy.identity(self.camera_path.read_bytes())})
        self.assertNotIn("camera_property_capability_contract", baseline)
        before = {row["path"]: row for row in baseline["files"]}
        after = {row["path"]: row for row in result["files"]}
        self.assertEqual(set(after) - set(before), {
            "tools/camera-property-vendor-init-write.json", "provenance/" + camera["patch"],
            "provenance/camera-property-capability.mk"})
        self.assertEqual([name for name in before if before[name] != after[name]], ["Android.bp"])
        self.assertEqual(result["classification_inputs"], baseline["classification_inputs"])
        self.assertEqual(result["native_targets"], baseline["native_targets"])
        self.assertEqual(result["scope"], baseline["scope"])
        rendered = (self.output / "Android.bp").read_text()
        original = (self.root / "camera-absent/Android.bp").read_text()
        additions = [line for line in rendered.splitlines() if line not in original.splitlines()]
        self.assertEqual(len(additions), 2)
        self.assertIn('        "tools/camera-property-vendor-init-write.json",', additions)

    def test_camera_bundle_requires_base_before_reading_inputs(self):
        with mock.patch.object(policy, "_contracts") as load:
            self.assert_rejected(lambda: policy.stage_inputs(self.corpus, self.output,
                factory_policy_receipt=self.receipt_path, camera_property_capability_contract="unused"))
            load.assert_not_called()

    def test_camera_bundle_cannot_demote_profile_or_change_guard_patch_or_contract(self):
        camera = self.install_camera_fixture()
        self.stage_camera()
        path = self.output / policy.RECEIPT_NAME
        original = json.loads(path.read_bytes())
        for mutate in (lambda item: item.pop("camera_property_capability_contract"),
                       lambda item: item.pop("evolution_policy_base_contract"),
                       lambda item: item["camera_property_capability_contract"].update(sha256="f" * 64)):
            changed = copy.deepcopy(original)
            mutate(changed)
            path.write_bytes(policy.encoded(changed))
            self.assert_rejected(self.verify_providers)
        path.write_bytes(policy.encoded(original))
        for name in ("tools/camera-property-vendor-init-write.json", "provenance/" + camera["patch"],
                     "provenance/camera-property-capability.mk"):
            target = self.output / name
            data = target.read_bytes()
            target.write_bytes(data + b"unreviewed\n")
            self.assert_rejected(self.verify_providers)
            target.write_bytes(data)
        self.assertEqual(self.verify_providers()["status"], "verified")

    def test_camera_native_render_requires_explicit_base_and_is_exactly_additive(self):
        template = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        for args in ((False, False, False, False), (True, True, True, False)):
            with self.assertRaisesRegex(policy.PolicyInputsError, "explicit Evolution"):
                policy._render_blueprint(template, *args, camera_property_enabled=True)
        before = policy._render_blueprint(template, True, True, True, True)
        after = policy._render_blueprint(template, True, True, True, True, True)
        self.assertEqual(before, after.replace(b'        "tools/camera-property-vendor-init-write.json",\n', b"").replace(
            b'         "--camera-property-capability-contract $$(readlink -f $(location tools/camera-property-vendor-init-write.json)) " +\n', b""))

    def test_camera_cli_flag_does_not_select_the_base_implicitly(self):
        args = ["stage", "--corpus-root", "corpus", "--factory-capture-root", "factory", "--output", "out"]
        for extra, expected in (([], None), (["--camera-property-capability-contract", "camera.json"], Path("camera.json"))):
            with mock.patch.object(policy, "stage_inputs", return_value={}) as stage, mock.patch("sys.stdout", io.StringIO()):
                self.assertEqual(policy.main([*args, *extra]), 0)
            self.assertEqual(stage.call_args.kwargs["camera_property_capability_contract"], expected)
            self.assertIsNone(stage.call_args.kwargs["evolution_policy_base_contract"])

    def install_factory_contexts_fixture(self):
        self.install_camera_fixture()
        self.factory_contexts_path = self.workspace / policy.FACTORY_CONTEXTS_CONTRACT_PATH
        self.factory_contexts_path.write_bytes((WORKSPACE / policy.FACTORY_CONTEXTS_CONTRACT_PATH).read_bytes())
        contract = json.loads(self.factory_contexts_path.read_bytes())
        (self.workspace / contract["patch"]).write_bytes((WORKSPACE / contract["patch"]).read_bytes())
        return contract

    def stage_factory_contexts(self, output=None):
        return policy.stage_inputs(self.corpus, output or self.output, **self.evolution_options(),
            camera_property_capability_contract=self.camera_path,
            factory_property_contexts_capability_contract=self.factory_contexts_path)

    def test_factory_contexts_bundle_is_paired_repeatable_and_preserves_original_contexts(self):
        contexts = self.install_factory_contexts_fixture()
        baseline = self.stage_camera(self.root / "contexts-absent")
        result = self.stage_factory_contexts()
        self.assertEqual(result, self.stage_factory_contexts(self.root / "contexts-repeat"))
        verified = self.verify_providers()
        self.assertEqual(verified["factory_property_contexts_capability_contract"], {
            "path": policy.FACTORY_CONTEXTS_CONTRACT_PATH, **policy.identity(self.factory_contexts_path.read_bytes())})
        self.assertNotIn("factory_property_contexts_capability_contract", baseline)
        before = {row["path"]: row for row in baseline["files"]}
        after = {row["path"]: row for row in result["files"]}
        self.assertEqual(set(after) - set(before), {"tools/factory-property-contexts.json",
            "provenance/" + contexts["patch"], "provenance/factory-property-contexts-capability.mk"})
        self.assertEqual([name for name in before if before[name] != after[name]], ["Android.bp"])
        self.assertEqual(result["contexts"], baseline["contexts"])
        self.assertEqual(result["classification_inputs"], baseline["classification_inputs"])
        self.assertEqual(result["native_targets"], baseline["native_targets"])
        self.assertEqual(result["scope"], baseline["scope"])
        new = (self.output / "Android.bp").read_text()
        old = (self.root / "contexts-absent/Android.bp").read_text()
        self.assertEqual(len(new.splitlines()) - len(old.splitlines()), 10)

    def test_factory_contexts_bundle_requires_camera_profile_before_reading(self):
        with mock.patch.object(policy, "_contracts") as load:
            self.assert_rejected(lambda: policy.stage_inputs(self.corpus, self.output,
                factory_policy_receipt=self.receipt_path, factory_property_contexts_capability_contract="unused"))
            load.assert_not_called()
        with self.assertRaisesRegex(policy.PolicyInputsError, "camera property"):
            policy._render_blueprint((WORKSPACE / "policy/nezha/Android.bp").read_bytes(),
                                      True, True, True, True, False, True)

    def test_factory_contexts_transferred_profile_guard_patch_and_original_inputs_are_bound(self):
        contexts = self.install_factory_contexts_fixture()
        self.stage_factory_contexts()
        receipt = self.output / policy.RECEIPT_NAME
        raw = receipt.read_bytes()
        for key in ("factory_property_contexts_capability_contract", "camera_property_capability_contract"):
            changed = json.loads(raw)
            del changed[key]
            receipt.write_bytes(policy.encoded(changed))
            self.assert_rejected(self.verify_providers)
        receipt.write_bytes(raw)
        for name in ("tools/factory-property-contexts.json", "provenance/" + contexts["patch"],
                     "provenance/factory-property-contexts-capability.mk", "factory/vendor/vendor_property_contexts",
                     "factory/odm/odm_property_contexts"):
            path = self.output / name
            before = path.read_bytes()
            path.write_bytes(before + b"changed\n")
            self.assert_rejected(self.verify_providers)
            path.write_bytes(before)
        self.assertEqual(self.verify_providers()["status"], "verified")

    def test_factory_contexts_cli_flag_does_not_implicitly_select_camera(self):
        args = ["stage", "--corpus-root", "corpus", "--factory-capture-root", "factory", "--output", "out"]
        for extra, expected in (([], None), (["--factory-property-contexts-capability-contract", "contexts.json"], Path("contexts.json"))):
            with mock.patch.object(policy, "stage_inputs", return_value={}) as stage, mock.patch("sys.stdout", io.StringIO()):
                self.assertEqual(policy.main([*args, *extra]), 0)
            self.assertEqual(stage.call_args.kwargs["factory_property_contexts_capability_contract"], expected)
            self.assertIsNone(stage.call_args.kwargs["camera_property_capability_contract"])

    def test_provider_verification_cannot_drop_or_reseal_derivation_metadata(self):
        inputs, _ = self.install_provider_fixture(derivation=True)
        original = inputs.verify_bundle(self.provider_bundle)
        mutations = (
            lambda value: value.pop("payload_derivations"),
            lambda value: value.update(payload_derivations=[]),
            lambda value: value["payload_derivations"].append(copy.deepcopy(value["payload_derivations"][0])),
            lambda value: value["payload_derivations"][0]["recipe"].update(changed_byte_file_offset=1),
            lambda value: value["payload_derivations"][0]["recipe"]["derived"].update(sha256="f" * 64),
            lambda value: value["payload_derivations"][0]["evidence"].update(sha256="f" * 64),
        )
        for number, mutate in enumerate(mutations):
            changed = copy.deepcopy(original)
            mutate(changed)
            output = self.root / ("refused-provider-" + str(number))
            with self.subTest(number=number), mock.patch.object(inputs, "verify_bundle", return_value=changed), \
                    self.assertRaisesRegex(policy.PolicyInputsError, "external provider verification differs"):
                self.stage_providers(output)
            self.assertFalse(output.exists())
        self.stage_providers()
        receipt_path = self.output / policy.RECEIPT_NAME
        receipt = json.loads(receipt_path.read_bytes())
        receipt["framework_provider_inputs"]["payload_derivations"] = []
        receipt_path.write_bytes(policy.encoded(receipt))
        self.assert_rejected(self.verify_providers)

    def test_provider_derivation_evidence_and_helper_are_rechecked_after_transfer(self):
        self.install_provider_fixture(derivation=True)
        self.stage_providers()
        reference = self.provider_profile["payload_derivations"][0]["evidence"]
        evidence = self.workspace / reference["path"]
        for path in (evidence, self.output / ("provenance/evidence/" + reference["path"]),
                     self.workspace / "scripts/framework_provider_derivations.py",
                     self.output / "provenance/tools/framework_provider_derivations.py"):
            raw = path.read_bytes()
            with self.subTest(path=path):
                path.write_bytes(raw + b"unreviewed")
                self.assert_rejected(self.verify_providers)
                path.write_bytes(raw)
        original = evidence.read_bytes()
        evidence.unlink()
        self.assert_rejected(lambda: self.stage_providers(self.root / "missing-evidence"))
        evidence.symlink_to(self.provider_source_path)
        self.assert_rejected(lambda: self.stage_providers(self.root / "symlink-evidence"))
        evidence.unlink()
        evidence.write_bytes(original)
        self.assertEqual(self.verify_providers()["status"], "verified")

    def test_provider_opt_in_requires_base_source_and_external_receipt_together(self):
        self.install_provider_fixture()
        options = {"factory_policy_receipt": self.receipt_path, "oem_policy_contract": self.oem_path,
                   "framework_provider_policy_contract": self.provider_source_path,
                   "framework_provider_inputs_receipt": self.provider_receipt}
        for key in ("oem_policy_contract", "framework_provider_policy_contract", "framework_provider_inputs_receipt"):
            selected = {**options, key: None}
            self.assert_rejected(lambda: policy.stage_inputs(self.corpus, self.output, **selected))
            self.assertFalse(self.output.exists())

    def test_legacy_oem_and_property_profiles_never_admit_or_read_provider_inputs(self):
        inputs, _ = self.install_provider_fixture(properties=True)
        with mock.patch.object(inputs, "verify_bundle", side_effect=AssertionError("unexpected provider admission")):
            for name, stage, count in (("legacy", self.stage, 31), ("oem", self.stage_oem, 36),
                                       ("properties", self.stage_properties, 41)):
                output = self.root / name
                result = stage(output)
                verified = policy.verify_bundle(output)
                self.assertEqual(len(result["files"]), count)
                self.assertNotIn("framework_provider_policy_contract", result)
                self.assertNotIn("framework_provider_inputs", result)
                self.assertIsNone(verified["framework_provider_policy_contract"])
                self.assertIsNone(verified["framework_provider_inputs"])
                self.assertFalse((output / "tools/framework_provider_policy.py").exists())
                self.assertNotIn("--provider-contract", (output / "Android.bp").read_text())

    def test_provider_verification_requires_the_actual_external_bundle_every_time(self):
        self.install_provider_fixture()
        self.stage_providers()
        self.assert_rejected(lambda: policy.verify_bundle(self.output))
        self.assert_rejected(lambda: self.verify_providers(receipt=self.root / policy.PROVIDER_INPUTS_RECEIPT_NAME))
        self.assert_rejected(lambda: self.verify_providers(receipt=self.provider_bundle / "wrong-name.json"))
        self.assertEqual(self.verify_providers()["status"], "verified")
        legacy = self.root / "legacy"
        self.stage(legacy)
        self.assert_rejected(lambda: policy.verify_bundle(legacy, framework_provider_inputs_receipt=self.provider_receipt))

    def test_old_or_loose_provider_output_recipe_is_not_an_admitted_image_dependency(self):
        self.install_provider_fixture()
        original = copy.deepcopy(self.provider_profile["native_output_recipe"])
        for recipe in (None, {**original, "consumer_inputs": "raw_filegroups"},
                       {key: value for key, value in original.items() if key != "payload_transformations"},
                       {**original, "payload_transformations": "arbitrary_elf_rewrite"},
                       {**original, "unreviewed_option": True},
                       {**original, "all_inputs_checked_before_outputs": False},
                       {**original, "all_inputs_checked_before_outputs": 1},
                       {**original, "producer": "unreviewed"}):
            if recipe is None:
                self.provider_profile.pop("native_output_recipe")
            else:
                self.provider_profile["native_output_recipe"] = recipe
            self.write_provider_contracts()
            self.assert_rejected(self.stage_providers)
            self.assertFalse(self.output.exists())

    def test_provider_source_contract_cannot_change_factory_platform_base_helper_or_scope(self):
        self.install_provider_fixture()
        original = copy.deepcopy(self.provider_source)
        mutations = [lambda c: c.update(factory_package_sha256="b" * 64),
                     lambda c: c.update(device="other"),
                     lambda c: c["platform"].update(branch="newer"),
                     lambda c: c["required_contracts"]["oem_policy"].update(sha256="b" * 64),
                     lambda c: c["required_contracts"]["init_helper"].update(sha256="b" * 64),
                     lambda c: c["scope"].update(complete_rom_admitted=True)]
        for mutate in mutations:
            self.provider_source = copy.deepcopy(original)
            mutate(self.provider_source)
            self.write_provider_contracts()
            self.assert_rejected(self.stage_providers)
            self.assertFalse(self.output.exists())

    def test_provider_source_artifacts_must_match_actual_selected_inputs(self):
        self.install_provider_fixture()
        original = copy.deepcopy(self.provider_source["selected_provider_artifacts"])
        for selected in (original[:-1], [*original, original[0]],
                         [{**original[0], "sha256": "b" * 64}, *original[1:]]):
            self.provider_source["selected_provider_artifacts"] = selected
            self.write_provider_contracts()
            self.assert_rejected(self.stage_providers)
            self.assertFalse(self.output.exists())

    def test_provider_source_statement_budget_survives_repinned_bytes_and_extra_files(self):
        self.install_provider_fixture()
        row = next(row for row in self.provider_source["source_files"] if row["path"].endswith("vendor_sigmahal_qti.te"))
        source = self.workspace / row["path"]
        original = source.read_bytes()
        source.write_bytes(original + b"allow vendor_sigmahal_qti self:capability sys_admin;\n")
        row.update(policy.identity(source.read_bytes()))
        self.write_provider_contracts()
        self.assert_rejected(self.stage_providers)
        self.assertFalse(self.output.exists())
        source.write_bytes(original)
        row.update(policy.identity(original))
        self.write_provider_contracts()
        source.with_name("unreviewed.te").write_bytes(b"type unreviewed_provider, domain;\n")
        self.assert_rejected(self.stage_providers)
        self.assertFalse(self.output.exists())

    def test_provider_native_selection_cannot_drop_the_tagged_byte_guard(self):
        self.install_provider_fixture()
        selection = self.config["framework_provider_policy"]
        selection["provider_inputs_check"] = policy.PROVIDER_INPUTS_CHECK.split("{", 1)[0]
        self.write_provider_contracts()
        self.assert_rejected(self.stage_providers)
        self.assertFalse(self.output.exists())

    def test_provider_receipt_binding_cannot_be_removed_or_forged(self):
        self.install_provider_fixture()
        self.stage_providers()
        path = self.output / policy.RECEIPT_NAME
        original = json.loads(path.read_bytes())
        for field in ("framework_provider_policy_contract", "framework_provider_inputs"):
            receipt = copy.deepcopy(original)
            del receipt[field]
            path.write_bytes(policy.encoded(receipt))
            self.assert_rejected(self.verify_providers)
        receipt = copy.deepcopy(original)
        receipt["framework_provider_inputs"]["receipt"]["sha256"] = "b" * 64
        path.write_bytes(policy.encoded(receipt))
        self.assert_rejected(self.verify_providers)
        receipt = copy.deepcopy(original)
        receipt["framework_provider_policy_contract"]["sha256"] = "b" * 64
        path.write_bytes(policy.encoded(receipt))
        self.assert_rejected(self.verify_providers)
        receipt = copy.deepcopy(original)
        del receipt["framework_provider_policy_contract"]
        del receipt["framework_provider_inputs"]
        path.write_bytes(policy.encoded(receipt))
        self.assert_rejected(lambda: policy.verify_bundle(self.output))

    def test_provider_payload_mutation_is_not_hidden_by_its_copied_receipt(self):
        self.install_provider_fixture()
        self.stage_providers()
        row = self.provider_profile["files"][0]
        path = self.provider_bundle / ("proprietary" + row["runtime_path"])
        path.write_bytes(path.read_bytes() + b"unreviewed")
        self.assert_rejected(self.verify_providers)

    def test_provider_inputs_changed_after_readback_prevent_policy_publication(self):
        self.install_provider_fixture()
        verify = policy.verify_bundle

        def change_after_readback(*args, **kwargs):
            result = verify(*args, **kwargs)
            path = self.provider_bundle / ("proprietary" + self.provider_profile["files"][0]["runtime_path"])
            path.write_bytes(b"changed after provider and policy readback")
            return result

        with mock.patch.object(policy, "verify_bundle", side_effect=change_after_readback):
            self.assert_rejected(self.stage_providers)
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.root.glob(".nezha-policy-inputs-*")), [])

    def test_late_provider_file_or_empty_directory_prevents_policy_publication(self):
        self.install_provider_fixture()
        verify = policy.verify_bundle
        extra = self.provider_bundle / "unreviewed"
        for directory in (False, True):
            with self.subTest(directory=directory):
                def change_after_readback(*args, **kwargs):
                    result = verify(*args, **kwargs)
                    if directory:
                        extra.mkdir()
                    else:
                        extra.write_bytes(b"unreviewed provider bundle member\n")
                    return result

                with mock.patch.object(policy, "verify_bundle", side_effect=change_after_readback):
                    self.assert_rejected(self.stage_providers)
                self.assertFalse(self.output.exists())
                self.assertEqual(list(self.root.glob(".nezha-policy-inputs-*")), [])
                extra.rmdir() if directory else extra.unlink()
                for relative, original in self.original_provider_files.items():
                    self.assertEqual((self.provider_bundle / relative).read_bytes(), original)

    def test_late_provider_inventory_change_is_rejected_by_standalone_verification(self):
        self.install_provider_fixture()
        self.stage_providers()
        members = policy._members

        def add_after_policy_inventory(*args):
            result = members(*args)
            (self.provider_bundle / "unreviewed").mkdir()
            return result

        with mock.patch.object(policy, "_members", side_effect=add_after_policy_inventory):
            self.assert_rejected(self.verify_providers)

    def test_policy_output_cannot_change_the_provider_bundle_inventory(self):
        self.install_provider_fixture()
        destination = self.provider_bundle / "nested-policy"
        self.assert_rejected(lambda: self.stage_providers(destination))
        self.assertFalse(destination.exists())

    def test_both_bundles_can_move_and_still_verify_without_host_paths(self):
        self.install_provider_fixture()
        self.stage_providers()
        original = self.verify_providers()
        relocated_policy, relocated_inputs = self.root / "relocated-policy", self.root / "relocated-inputs"
        shutil.copytree(self.output, relocated_policy)
        shutil.copytree(self.provider_bundle, relocated_inputs)
        relocated = self.verify_providers(relocated_policy, relocated_inputs / policy.PROVIDER_INPUTS_RECEIPT_NAME)
        self.assertEqual(original, relocated)
        self.assertNotIn(str(self.root), json.dumps(relocated))

    def test_transferred_provider_sources_controls_and_receipt_are_rehashed(self):
        self.install_provider_fixture()
        self.stage_providers()
        members = ["tools/framework_provider_policy.py", "tools/nezha-framework-provider-policy.json",
                   "provenance/nezha-framework-providers.json", "provenance/tools/framework_provider_inputs.py",
                   policy.PROVIDER_INPUTS_RECEIPT_MEMBER,
                   *["provenance/source/" + row["path"] for row in self.provider_source["source_files"]]]
        for member in members:
            path = self.output / member
            original = path.read_bytes()
            with self.subTest(member=member):
                path.write_bytes(original + b"changed")
                self.assert_rejected(self.verify_providers)
                path.write_bytes(original)

    def test_provider_cli_requires_external_reverification_and_keeps_build_claims_false(self):
        self.install_provider_fixture()
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            code = policy.main(["stage", "--corpus-root", str(self.corpus), "--factory-policy-receipt",
                                str(self.receipt_path), "--output", str(self.output),
                                "--oem-policy-contract", str(self.oem_path),
                                "--framework-provider-policy-contract", str(self.provider_source_path),
                                "--framework-provider-inputs-receipt", str(self.provider_receipt)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["scope"], policy.SCOPE)
        stdout = io.StringIO()
        with mock.patch("sys.stdout", stdout):
            code = policy.main(["verify", "--bundle", str(self.output),
                                "--framework-provider-inputs-receipt", str(self.provider_receipt)])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["scope"], policy.SCOPE)
        with mock.patch("sys.stderr", io.StringIO()):
            self.assertEqual(policy.main(["verify", "--bundle", str(self.output)]), 2)


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

    def test_current_public_property_controls_load_without_private_inputs(self):
        reader = policy.vendor_policy.Reader()
        contract, correction, controls = policy._contracts(reader)
        base = policy._oem_controls(reader, WORKSPACE / policy.OEM_CONTRACT_PATH, contract, correction, controls)
        binding = policy._oem_property_controls(reader, WORKSPACE / policy.OEM_PROPERTY_CONTRACT_PATH,
                                                contract, controls, base)
        self.assertEqual(binding, {"path": policy.OEM_PROPERTY_CONTRACT_PATH,
                                   **policy.identity((WORKSPACE / policy.OEM_PROPERTY_CONTRACT_PATH).read_bytes())})
        self.assertIn("tools/nezha-oem-properties.json", controls)
        self.assertIn("--system-ext-property-contexts", controls["Android.bp"].decode())
        self.assertFalse(any(path.relative_to(WORKSPACE).parts[0] in {"artifacts", "evidence", "reports"}
                             for path in reader.bindings))
        reader.recheck()

    def test_current_public_provider_controls_bind_source_and_verified_output_recipe_without_private_inputs(self):
        reader = policy.vendor_policy.Reader()
        contract, correction, controls = policy._contracts(reader)
        base = policy._oem_controls(reader, WORKSPACE / policy.OEM_CONTRACT_PATH, contract, correction, controls)
        binding = policy._provider_controls(reader, WORKSPACE / policy.PROVIDER_POLICY_CONTRACT_PATH,
                                             contract, controls, base)
        self.assertEqual(binding, {"path": policy.PROVIDER_POLICY_CONTRACT_PATH,
                                   **policy.identity((WORKSPACE / policy.PROVIDER_POLICY_CONTRACT_PATH).read_bytes())})
        self.assertIn("tools/framework_provider_policy.py", controls)
        self.assertIn(policy.PROVIDER_INPUTS_CHECK, controls["Android.bp"].decode())
        profile = json.loads(controls["provenance/nezha-framework-providers.json"])
        self.assertEqual(profile["native_output_recipe"], policy.PROVIDER_NATIVE_OUTPUT_RECIPE)
        self.assertFalse(any(path.relative_to(WORKSPACE).parts[0] in {"artifacts", "evidence", "reports"}
                             for path in reader.bindings))
        reader.recheck()

    def test_current_evolution_public_controls_load_without_private_or_upstream_source_reads(self):
        reader = policy.vendor_policy.Reader()
        contract, correction, controls = policy._contracts(reader)
        oem = policy._oem_controls(reader, WORKSPACE / policy.OEM_CONTRACT_PATH, contract, correction, controls)
        properties = policy._oem_property_controls(reader, WORKSPACE / policy.OEM_PROPERTY_CONTRACT_PATH,
                                                    contract, controls, oem)
        providers = policy._provider_controls(reader, WORKSPACE / policy.PROVIDER_POLICY_CONTRACT_PATH,
                                              contract, controls, oem, True)
        binding = policy._evolution_base_controls(reader, WORKSPACE / policy.EVOLUTION_BASE_CONTRACT_PATH,
                                                  contract, controls, oem, properties, providers)
        self.assertEqual(binding, {"path": policy.EVOLUTION_BASE_CONTRACT_PATH,
                                   **policy.identity((WORKSPACE / policy.EVOLUTION_BASE_CONTRACT_PATH).read_bytes())})
        self.assertIn("--evolution-policy-base-contract", controls["Android.bp"].decode())
        self.assertEqual(controls["provenance/nezha-owned-policy.Android.bp"], policy.render_evolution_owned_groups())
        self.assertFalse(any(path.relative_to(WORKSPACE).parts[0] in {"artifacts", "evidence", "reports"}
                             or path.relative_to(WORKSPACE).as_posix().startswith("device/lineage/")
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

    def test_property_profile_only_changes_the_explicit_guard_inputs_and_arguments(self):
        bp = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        legacy = policy._render_blueprint(bp, False).decode()
        original_oem = policy._render_blueprint(bp, True).decode()
        properties = policy._render_blueprint(bp, True, True).decode()
        for original in (legacy, original_oem):
            self.assertNotIn("--property-contract", original)
            self.assertNotIn("tools/nezha-oem-properties.json", original)
        self.assertIn('":system_ext_property_contexts"', properties)
        self.assertIn("--property-contract", properties)
        self.assertIn("--system-ext-property-contexts", properties)
        for rendered in (original_oem, properties):
            binary = rendered.split("se_policy_binary {", 1)[1].split("\n}", 1)[0]
            inputs = binary.split("srcs: [", 1)[1].split("]", 1)[0]
            self.assertEqual(inputs.count('"'), 20)
            self.assertNotIn("properties", inputs)
            self.assertIn('required: ["sepolicy_neverallows", "' + policy.OEM_CHECK_TARGET + '"]', binary)
        with self.assertRaises(ValueError):
            policy._render_blueprint(bp, False, True)

    def test_provider_profile_uses_tagged_byte_producer_and_both_native_contexts(self):
        raw = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        # Pinned Soong recognizes qualified //namespace:name references.
        # A leading colon is for unqualified names and rejects a slash.
        self.assertTrue(policy.PROVIDER_INPUTS_CHECK.startswith("//"))
        base = policy._render_blueprint(raw, True).decode()
        base_inputs = base.split("se_policy_binary {", 1)[1].split("srcs: [", 1)[1].split("]", 1)[0]
        for properties in (False, True):
            rendered = policy._render_blueprint(raw, True, properties, True).decode()
            binary = rendered.split("se_policy_binary {", 1)[1].split("\n}", 1)[0]
            self.assertEqual(binary.split("srcs: [", 1)[1].split("]", 1)[0], base_inputs)
            block = rendered.split('name: "' + policy.OEM_CHECK_TARGET + '"', 1)[1].split("\n}", 1)[0]
            for module in ("system_ext_file_contexts", "system_ext_service_contexts"):
                self.assertIn('\":' + module + '\"', block)
                self.assertIn("$(location :" + module + ")", block)
            for flag in ("--provider-contract", "--system-ext-file-contexts", "--system-ext-service-contexts"):
                self.assertIn(flag, block)
            self.assertIn('"' + policy.PROVIDER_INPUTS_CHECK + '"', block)
            self.assertNotIn('\"://', block)
            self.assertNotIn('"' + policy.PROVIDER_INPUTS_CHECK.split("{", 1)[0] + '"', block)
            self.assertNotIn(":nezha_factory_precompiled_sepolicy", block)
            tool = rendered.split('name: "nezha_oem_policy_check_tool"', 1)[1].split("\n}", 1)[0]
            self.assertIn('"tools/framework_provider_policy.py"', tool)
            self.assertIn('"tools/framework_provider_policy.py"', block)
            self.assertIn('"tools/nezha-framework-provider-policy.json"', block)
        self.assertNotIn("framework_provider_policy.py", base)
        with self.assertRaises(ValueError):
            policy._render_blueprint(raw, False, False, True)

    def test_provider_opt_in_preserves_all_previous_rendered_profiles_exactly(self):
        raw = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        expected = [((False,), "4b2121879fde74d5d27961f49fe5609bb2441317d9695400b6f30ce332f38072", 8599),
                    ((True,), "1a873a7da7d07177b08635d5fd67785111538c60ce83ea0797027f6e4fe9243b", 11205),
                    ((True, True), "c22e6889c11d09911b9748fae2f914765f2d10b07ba2020a6a2849e92869136c", 11486)]
        for flags, digest, size in expected:
            with self.subTest(flags=flags):
                self.assertEqual(policy.identity(policy._render_blueprint(raw, *flags)),
                                 {"sha256": digest, "size_bytes": size})

    def test_evolution_base_opt_in_preserves_both_provider_profiles_exactly(self):
        raw = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        for flags, digest, size in (
            ((True, False, True), "55faa9d1f214ad21dc13099f49188c00ab8aa83290b1d283bfe308dca3875740", 11852),
            ((True, True, True), "5cd20287b966d752f1ed62ce6c9b17011f8b6162ce1b90077f29ee5db8eafc4c", 12133),
        ):
            with self.subTest(flags=flags):
                before = policy._render_blueprint(raw, *flags)
                self.assertEqual(policy.identity(before), {"sha256": digest, "size_bytes": size})
                self.assertEqual(before, policy._render_blueprint(raw, *flags, evolution_base_enabled=False))
                self.assertNotIn(b"evolution_base", before)

    def test_evolution_base_requires_all_three_source_profiles(self):
        raw = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        for flags in ((False, False, False), (True, False, False), (True, True, False), (True, False, True)):
            with self.subTest(flags=flags), self.assertRaises(ValueError):
                policy._render_blueprint(raw, *flags, evolution_base_enabled=True)

    def test_evolution_comparison_never_joins_or_changes_strict_compiler_inputs(self):
        raw = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        before = policy._render_blueprint(raw, True, True, True).decode()
        after = policy._render_blueprint(raw, True, True, True, True).decode()
        binary = lambda text: text.split("se_policy_binary {", 1)[1].split("\n}", 1)[0]
        self.assertEqual(binary(before), binary(after))
        guard = after.split('name: "' + policy.OEM_CHECK_TARGET + '"', 1)[1].split("\n}", 1)[0]
        for name in ("nezha_evolution_base_system_ext_sepolicy.cil", "nezha_evolution_base_system_ext_mapping_file",
                     "nezha_evolution_base_system_ext_pub_policy.cil", "system_ext_pub_policy.cil"):
            self.assertIn('":' + name + '"', guard)
            self.assertIn("$(location :" + name + ")", guard)
        self.assertNotIn(":nezha_factory_precompiled_sepolicy", guard)
        self.assertIn("--evolution-base-source-files $(locations :nezha_evolution_base_source_files)", guard)
        tool = after.split('name: "nezha_oem_policy_check_tool"', 1)[1].split("\n}", 1)[0]
        self.assertIn('"tools/evolution_policy_base.py"', tool)
        self.assertIn('"tools/evolution_policy_base.py"', guard)

    def test_evolution_comparison_uses_native_source_subtraction_and_strict_private_cil(self):
        raw = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        text = policy._render_blueprint(raw, True, True, True, True).decode()
        for scope in ("public", "private"):
            group = text.split('name: "nezha_evolution_base_' + scope + '_policy"', 1)[1].split("\n}", 1)[0]
            self.assertIn('srcs: [":se_build_files{.system_ext_' + scope + '}"]', group)
            self.assertIn('exclude_srcs: ["//device/xiaomi/nezha:nezha_owned_system_ext_' + scope + '_policy"]', group)
            self.assertNotIn("*", group)
        private = text.split('name: "nezha_evolution_base_system_ext_sepolicy.cil"', 1)[1].split("\n}", 1)[0]
        self.assertIn('filter_out: [":plat_sepolicy.cil"]', private)
        self.assertIn("secilc_check: true", private)
        self.assertIn("ignore_neverallow: false", private)
        self.assertIn("installable: false", private)
        mapping = text.split('name: "nezha_evolution_base_system_ext_mapping_file"', 1)[1].split("\n}", 1)[0]
        self.assertIn('version: "current"', mapping)
        self.assertIn('filter_out: [":plat_mapping_file"]', mapping)
        self.assertIn("installable: false", mapping)
        self.assertNotIn("dependent_cils", mapping)

    def test_evolution_context_comparisons_use_native_types_without_install_claims(self):
        raw = (WORKSPACE / "policy/nezha/Android.bp").read_bytes()
        text = policy._render_blueprint(raw, True, True, True, True).decode()
        for kind in ("property", "file", "service"):
            name = "nezha_evolution_base_" + kind + "_contexts"
            self.assertIn(kind + '_contexts {\n    name: "' + name + '"', text)
            block = text.split('name: "' + name + '"', 1)[1].split("\n}", 1)[0]
            self.assertIn('defaults: ["contexts_flags_defaults"]', block)
            self.assertIn("system_ext_specific: true", block)
            self.assertNotIn("installable", block)
        self.assertNotIn("PRODUCT_PACKAGES +=", text)
        self.assertNotIn("nezha_evolution_base_seapp", text)

    def test_evolution_owned_groups_are_exact_local_source_selectors(self):
        raw = policy.render_evolution_owned_groups().decode()
        self.assertEqual(raw.count("filegroup {"), 5)
        self.assertNotIn("soong_namespace", raw)
        self.assertNotIn("../", raw)
        self.assertNotIn("*", raw)
        self.assertNotIn("PRODUCT_PACKAGES", raw)
        base = "device/xiaomi/nezha/sepolicy/"
        for name, paths in policy.EVOLUTION_BASE_OWNED_GROUPS.items():
            block = raw.split('name: "' + name + '"', 1)[1].split("\n}", 1)[0]
            selected = block.split("srcs: [", 1)[1].split("]", 1)[0]
            self.assertEqual(selected.count('"'), len(paths) * 2)
            for path in paths:
                self.assertIn('"' + path.removeprefix(base) + '"', selected)
            # Soong visibility.go rejects individual vendor packages when the
            # declaring source package is outside vendor/.
            self.assertIn('visibility: ["//vendor:__subpackages__"]', block)
            self.assertNotIn("//vendor/xiaomi/nezha-policy", block)

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
