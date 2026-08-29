"""Offline, synthetic source/native policy guards; no guest or firmware needed."""

import copy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import oem_policy as op
from scripts import vendor_policy as vp


ROOT = Path(__file__).resolve().parents[1]
SERVICE = "vendor_hal_atfwd_hwservice"
AIDL = "vendor_hal_systemhelper_aidl_service"
DATA = "offlinelog_file"


def native_fixture():
    contract = copy.deepcopy(op.load_contract())
    capability = (ROOT / "config/nezha-init-helper-capability.json").read_bytes()
    public = [name for name, spec in contract["types"].items() if spec["scope"] == "system_ext_public"]
    attrs = sorted({attr for spec in contract["types"].values() for attr in spec["attributes"]})
    platform = (
        "(role r)(role object_r)\n"
        "(type init_dev_config)(type apexd_select_prop)(type media_variant_prop)\n"
        "(typeattribute domain)(typeattributeset domain (init_dev_config))\n"
        "(typeattribute coredomain)(roletype r domain)\n"
        + "\n".join(f"(typeattribute {name})" for name in attrs)
        + "\n(allow init_dev_config apexd_select_prop (file (read)))\n"
    ).encode()
    source = ""
    for name, spec in contract["types"].items():
        source += f"(type {name})(roletype object_r {name})\n"
        source += "".join(f"(typeattributeset {attr} ({name}))\n" for attr in spec["attributes"])
    mapping = "".join(f"(typeattribute {name}_202504)(typeattributeset {name}_202504 ({name}))\n" for name in public)
    factory_pub = "".join(f"(type {name})(typeattribute {name}_202504)(roletype object_r {name}_202504)\n" for name in public)
    vendor = f"(type {DATA})(roletype object_r {DATA})\n".encode()
    corpus = {runtime: b"\n" for runtime in op.INPUT_FLAGS.values()}
    corpus[op.INPUT_FLAGS["platform_cil"]] = platform
    corpus[op.INPUT_FLAGS["system_ext_cil"]] = source.encode()
    corpus[op.INPUT_FLAGS["system_ext_mapping"]] = mapping.encode()
    corpus[op.INPUT_FLAGS["factory_pub"]] = factory_pub.encode()
    corpus[op.INPUT_FLAGS["derived_vendor"]] = vendor
    for row in contract["unchanged_factory_inputs"]:
        raw = corpus[row["runtime_path"]]
        row.update(sha256=vp.sha(raw), size_bytes=len(raw))
    contract["existing_vendor_derivation"].update(sha256=vp.sha(vendor), size_bytes=len(vendor))
    return corpus, vendor, contract, capability


class SourceGuardTests(unittest.TestCase):
    def test_actual_source_contract_contains_only_three_reviewed_declarations(self):
        result = op.verify_sources(ROOT)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(set(result["declarations"]), {SERVICE, AIDL, DATA})
        self.assertIn("coredomain_hwservice", result["declarations"][SERVICE])
        self.assertNotIn("coredomain", result["declarations"][SERVICE])
        self.assertTrue(result["all_inputs_rehashed_unchanged"])
        self.assertTrue(all(value is False for value in result["scope"].values()))

    def test_allow_m4_permissive_typeattributes_and_extra_statements_fail(self):
        for text in (
            "allow a b:file read;", "permissive a;", "typeattribute a domain;",
            "ifelse(x,y,`type a, file_type;')", "type a, file_type; allow a a:file read;",
            "type a, file_type; garbage", "type a, file_type; type a, file_type;",
            "type a, file_type, file_type;",
        ):
            with self.subTest(text=text), self.assertRaises(op.OemPolicyError):
                op.source_declarations(text.encode())

    def test_source_hash_rejects_unreviewed_extra_allow_even_if_type_names_match(self):
        contract = op.load_contract()
        contents = {row["path"]: (ROOT / row["path"]).read_bytes() for row in contract["source_files"]}
        contents[next(iter(contents))] += b"allow a b:file read;\n"
        with self.assertRaisesRegex(op.OemPolicyError, "source hash"):
            op.verify_source_contents(contents, contract)

    def test_hash_matching_wrong_scope_or_attribute_still_fails(self):
        contract = copy.deepcopy(op.load_contract())
        contents = {row["path"]: (ROOT / row["path"]).read_bytes() for row in contract["source_files"]}
        row = contract["source_files"][0]
        contents[row["path"]] = contents[row["path"]].replace(b"coredomain_hwservice", b"coredomain")
        row.update(sha256=vp.sha(contents[row["path"]]), size_bytes=len(contents[row["path"]]))
        with self.assertRaisesRegex(op.OemPolicyError, "exact attributes"):
            op.verify_source_contents(contents, contract)

    def test_copied_contract_bytes_are_pinned(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "copied.json"
            raw = (ROOT / op.CONTRACT_PATH).read_bytes()
            path.write_bytes(raw)
            self.assertEqual(op.load_contract(path), op.load_contract())
            path.write_bytes(raw + b" ")
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                op.load_contract(path)

    def test_unreviewed_file_in_ownership_directory_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            contract = op.load_contract()
            for row in contract["source_files"]:
                target = root / row["path"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes((ROOT / row["path"]).read_bytes())
            target.with_name("surprise.te").write_bytes(b"type surprise, domain;\n")
            with self.assertRaisesRegex(op.OemPolicyError, "unreviewed file"):
                op.verify_sources(root, capability_path=ROOT / "config/nezha-init-helper-capability.json")

    def test_contract_documents_exact_factory_evidence_without_payloads(self):
        contract = op.load_contract()
        self.assertEqual(contract["platform"], {"branch": "bka", "release": "bp4a", "board_api": "202504"})
        self.assertFalse(contract["duplicate_declarations"]["factory_files_rewritten"])
        self.assertEqual(contract["duplicate_declarations"]["compiler_multiple_declarations_flag"], "-m")
        self.assertEqual(len(contract["unchanged_factory_inputs"]), 3)
        self.assertEqual(len(contract["source_files"]), 2)
        for forbidden in ("(allow ", "BEGIN PRIVATE KEY", "/Users/", "(neverallow "):
            self.assertNotIn(forbidden, (ROOT / op.CONTRACT_PATH).read_text())


class NativeGuardTests(unittest.TestCase):
    def check(self, fixture=None):
        return op.check_native_contents(*(fixture or native_fixture()))

    def test_exact_public_mappings_roles_and_private_type_pass(self):
        result = self.check()
        self.assertEqual(result["status"], "verified")
        self.assertEqual(result["helper_effective_property_set_grants"], 0)
        self.assertEqual(result["type_ownership"][SERVICE]["versioned_mapping"], [SERVICE])
        self.assertIsNone(result["type_ownership"][DATA]["versioned_mapping"])
        for row in result["type_ownership"].values():
            self.assertEqual(row["roles"], ["object_r"])
            self.assertFalse(row["domain"])
            self.assertFalse(row["coredomain"])
        self.assertTrue(all(value is False for value in result["scope"].values()))

    def test_original_factory_and_derived_inputs_are_independently_pinned(self):
        for change in ("original_vendor", "factory_pub", "derived_vendor", "factory_odm"):
            corpus, vendor, contract, capability = native_fixture()
            if change == "original_vendor":
                vendor += b"; changed"
            else:
                corpus[op.INPUT_FLAGS[change]] += b"; changed"
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                self.check((corpus, vendor, contract, capability))

    def test_missing_duplicate_wrong_singleton_and_wrong_owner_mapping_fail(self):
        for change in ("missing", "duplicate", "wrong_member", "wrong_owner"):
            fixture = list(native_fixture())
            corpus = fixture[0]
            path = op.INPUT_FLAGS["system_ext_mapping"]
            row = f"(typeattributeset {SERVICE}_202504 ({SERVICE}))".encode()
            if change == "missing":
                corpus[path] = corpus[path].replace(row, b"")
            elif change == "duplicate":
                corpus[path] += row
            elif change == "wrong_member":
                corpus[path] = corpus[path].replace(row, f"(typeattributeset {SERVICE}_202504 ({AIDL}))".encode())
            else:
                corpus[path] = corpus[path].replace(row, b"")
                corpus[op.INPUT_FLAGS["product_mapping"]] += row
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                self.check(fixture)

    def test_private_data_type_must_not_gain_a_public_mapping(self):
        fixture = list(native_fixture())
        fixture[0][op.INPUT_FLAGS["system_ext_mapping"]] += (
            f"(typeattribute {DATA}_202504)(typeattributeset {DATA}_202504 ({DATA}))".encode())
        with self.assertRaisesRegex(op.OemPolicyError, "public mapping"):
            self.check(fixture)

    def test_source_must_generate_each_object_role_itself(self):
        fixture = list(native_fixture())
        key = op.INPUT_FLAGS["system_ext_cil"]
        role = f"(roletype object_r {SERVICE})".encode()
        fixture[0][key] = fixture[0][key].replace(role, b"")
        # Factory mapping still makes the combined object_r membership true.
        with self.assertRaisesRegex(op.OemPolicyError, "source did not generate"):
            self.check(fixture)

    def test_source_permission_or_transition_is_not_hidden_by_correct_oem_types(self):
        changes = (
            "(allow init_dev_config offlinelog_file (file (read)))",
            "(auditallow init_dev_config offlinelog_file (file (read)))",
            "(dontaudit init_dev_config offlinelog_file (file (write)))",
            "(typetransition init_dev_config offlinelog_file file offlinelog_file)",
        )
        for change in changes:
            fixture = list(native_fixture())
            fixture[0][op.INPUT_FLAGS["system_ext_cil"]] += change.encode()
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "declaration-only"):
                self.check(fixture)

    def test_named_source_memberships_cannot_widen_unrelated_types_or_dsp_clients(self):
        changes = (
            "(typeattributeset domain (apexd_select_prop))",
            "(typeattributeset core_data_file_type (apexd_select_prop))",
            "(typeattribute vendor_hal_dspmanager_client)(typeattributeset vendor_hal_dspmanager_client (init_dev_config))",
        )
        for change in changes:
            fixture = list(native_fixture())
            fixture[0][op.INPUT_FLAGS["system_ext_cil"]] += change.encode()
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "unreviewed source-owned"):
                self.check(fixture)

    def test_mapping_cannot_add_unrelated_named_membership_or_permission(self):
        for change in ("(typeattributeset domain (apexd_select_prop))",
                       "(allow init_dev_config offlinelog_file (file (read)))"):
            fixture = list(native_fixture())
            fixture[0][op.INPUT_FLAGS["system_ext_mapping"]] += change.encode()
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                self.check(fixture)

    def test_service_object_cannot_be_promoted_into_domain_coredomain_or_role_r(self):
        changes = (
            f"(typeattributeset domain ({SERVICE}))",
            f"(typeattributeset coredomain ({SERVICE}))",
            f"(roletype r {SERVICE})",
        )
        for change in changes:
            fixture = list(native_fixture())
            fixture[0][op.INPUT_FLAGS["platform_cil"]] += change.encode()
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "promoted"):
                self.check(fixture)

    def test_missing_source_membership_not_hidden_by_versioned_factory_assignment(self):
        fixture = list(native_fixture())
        key = op.INPUT_FLAGS["system_ext_cil"]
        row = f"(typeattributeset protected_hwservice ({SERVICE}))".encode()
        fixture[0][key] = fixture[0][key].replace(row, b"")
        fixture[0][op.INPUT_FLAGS["platform_cil"]] += row
        with self.assertRaisesRegex(op.OemPolicyError, "source-owned"):
            self.check(fixture)

    def test_broadened_named_membership_fails(self):
        fixture = list(native_fixture())
        fixture[0][op.INPUT_FLAGS["platform_cil"]] += (
            f"(typeattribute broadened)(typeattributeset broadened ({SERVICE}))".encode())
        with self.assertRaisesRegex(op.OemPolicyError, "broadened"):
            self.check(fixture)

    def test_platform_redeclaration_and_unreviewed_system_ext_type_fail(self):
        for flag, text in (("platform_cil", f"(type {SERVICE})"),
                           ("system_ext_cil", "(type extra_oem_type)")):
            fixture = list(native_fixture())
            fixture[0][op.INPUT_FLAGS[flag]] += text.encode()
            with self.subTest(flag=flag), self.assertRaises(op.OemPolicyError):
                self.check(fixture)

    def test_helper_direct_and_attribute_mediated_set_permissions_fail(self):
        for grant in (
            "(allow init_dev_config apexd_select_prop (property_service (set)))",
            "(allow domain media_variant_prop (property_service (set)))",
        ):
            fixture = list(native_fixture())
            fixture[0][op.INPUT_FLAGS["platform_cil"]] += grant.encode()
            with self.subTest(grant=grant), self.assertRaisesRegex(op.OemPolicyError, "property-write"):
                self.check(fixture)

    def test_wrong_helper_capability_contract_and_permissive_fail(self):
        fixture = list(native_fixture())
        fixture[3] += b" "
        with self.assertRaisesRegex(op.OemPolicyError, "capability contract hash"):
            self.check(fixture)
        fixture = list(native_fixture())
        fixture[0][op.INPUT_FLAGS["platform_cil"]] += b"(typepermissive init_dev_config)"
        with self.assertRaisesRegex(op.OemPolicyError, "permissive domain"):
            self.check(fixture)

    def test_native_input_reordering_or_missing_file_fails(self):
        fixture = list(native_fixture())
        fixture[0] = dict(reversed(list(fixture[0].items())))
        with self.assertRaisesRegex(op.OemPolicyError, "input order"):
            self.check(fixture)
        fixture = list(native_fixture())
        del fixture[0][op.INPUT_FLAGS["platform_genfs"]]
        with self.assertRaisesRegex(op.OemPolicyError, "input order"):
            self.check(fixture)


class NativeFilesystemTests(unittest.TestCase):
    def test_explicit_native_files_and_fresh_receipt_support_packaged_tool(self):
        corpus, vendor, contract, capability = native_fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            inputs = {}
            for flag, runtime in op.INPUT_FLAGS.items():
                path = root / (flag + ".cil")
                path.write_bytes(corpus[runtime])
                inputs[flag] = path
            original = root / "original-vendor.cil"
            original.write_bytes(vendor)
            cap = root / "capability.json"
            cap.write_bytes(capability)
            config = root / "contract.json"
            config.write_bytes(vp.encoded(contract))
            with patch.object(op, "CONTRACT_SHA256", vp.sha(config.read_bytes())):
                result = op.check_native(inputs, original, cap, contract_path=config,
                                         tool_source=ROOT / "scripts/oem_policy.py")
            self.assertTrue(result["all_inputs_rehashed_unchanged"])
            self.assertEqual(len(result["input_bindings"]), 16)
            output = root / "receipt.json"
            with contextlib.redirect_stdout(io.StringIO()):
                op._write_result(result, output)
            self.assertEqual(json.loads(output.read_bytes()), result)
            with self.assertRaises(FileExistsError):
                op._write_result(result, output)

    def test_symlink_receipt_target_is_never_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            victim = root / "original"
            victim.write_bytes(b"preserve")
            output = root / "receipt.json"
            output.symlink_to(victim)
            with self.assertRaises(FileExistsError):
                op._write_result({}, output)
            self.assertEqual(victim.read_bytes(), b"preserve")


if __name__ == "__main__":
    unittest.main()
