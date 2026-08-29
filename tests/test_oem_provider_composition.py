"""Compose explicit profiles without hiding forms from either native guard."""

from collections import Counter
import builtins
import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import framework_provider_policy as fp
from scripts import oem_policy as op
from scripts import vendor_policy as vp
from tests.test_framework_provider_policy import native_fixture as provider_fixture
from tests.test_oem_policy import native_fixture as oem_fixture
from tests.test_oem_properties import property_fixture


ROOT = Path(__file__).resolve().parents[1]
SIGMA = "vendor_sigmahal_qti"
SIGMA_SERVICE = "vendor_hal_sigma_miracast_service"
ATFWD = "vendor_hal_atfwd_hwservice"


def fixture(properties=False):
    if properties:
        corpus, vendor, base, capability, property_contract, property_contexts = property_fixture()
    else:
        corpus, vendor, base, capability = oem_fixture()
        property_contract, property_contexts = None, None
    provider_corpus, provider = provider_fixture()
    platform = op.INPUT_FLAGS["platform_cil"]
    existing = {form.expr for form in vp.parse(corpus[platform], platform)}
    inherited = [form.expr for form in vp.parse(provider_corpus[platform], platform) if form.expr not in existing]
    corpus[platform] += ("\n".join(vp.render(expr) for expr in inherited) + "\n").encode()
    corpus[platform] += b"(type inherited_platform_file)(roletype object_r inherited_platform_file)\n"
    corpus[platform] += b"(typeattributeset file_type (inherited_platform_file))\n"
    all_types = dict(base["types"])
    if property_contract is not None:
        all_types.update(property_contract["types"])
    all_types.update(provider["types"])
    members = {}
    for name, spec in all_types.items():
        for attr in spec["attributes"]:
            members.setdefault(attr, set()).add(name)
    ext = op.INPUT_FLAGS["system_ext_cil"]
    all_source = vp.parse(corpus[ext], ext) + vp.parse(provider_corpus[ext], ext)
    expressions = [form.expr for form in all_source
                   if not (form.expr[0] == "typeattributeset" and form.expr[1] in members)]
    platform_policy = vp.Policy(vp.parse(corpus[platform], platform))
    expressions.extend(("typeattributeset", attr, tuple(sorted(platform_policy.resolve(attr) | names)))
                       for attr, names in members.items())
    corpus[ext] = ("\n".join(vp.render(expr) for expr in expressions) + "\n").encode()
    contexts = ["".join(" ".join(row) + "\n" for row in provider["context_entries"][key]).encode()
                for key in ("file_contexts", "service_contexts")]
    return [corpus, vendor, base, capability, property_contract, property_contexts, provider, *contexts]


class ExplicitCompositionTests(unittest.TestCase):
    def check(self, value=None, *, properties=False):
        return op.check_native_contents(*(value or fixture(properties)))

    def test_provider_profile_and_property_profile_remain_independently_optional(self):
        for properties in (False, True):
            with self.subTest(properties=properties):
                result = self.check(properties=properties)
                provider = result["provider_policy_verification"]
                self.assertEqual(result["status"], "verified")
                self.assertEqual(len(result["type_ownership"]), 7 if properties else 3)
                self.assertEqual(len(provider["type_ownership"]), 8)
                self.assertEqual(provider["source_allow_clauses"], 26)
                self.assertEqual(provider["source_dontaudit_clauses"], 2)
                self.assertEqual(provider["source_type_transitions"], 2)
                self.assertEqual(len(provider["registration_assertions"]), 4)
                self.assertEqual(result["provider_context_verification"]["provider_context_rows"],
                                 {"file_contexts": 4, "service_contexts": 2})
                self.assertEqual("property_effective_ordinary_allow_edges" in result, properties)
                self.assertTrue(all(value is False for value in provider["scope"].values()))

    def test_default_profiles_never_import_optional_provider_checker(self):
        with patch.object(op, "_provider_module", side_effect=AssertionError("unexpected optional import")):
            self.assertEqual(op.check_native_contents(*oem_fixture())["status"], "verified")
            self.assertEqual(op.check_native_contents(*property_fixture())["status"], "verified")
            self.assertNotIn("provider_contract_id", op.verify_sources(ROOT))
            self.assertNotIn("provider_contract_id", op.verify_sources(ROOT, property_contract_path=ROOT / op.PROPERTY_CONTRACT_PATH))

    def test_fresh_legacy_module_load_does_not_require_provider_checker_to_exist(self):
        original_import = builtins.__import__

        def reject_optional_module(name, globals=None, locals=None, fromlist=(), level=0):
            if "framework_provider_policy" in name or "framework_provider_policy" in (fromlist or ()):
                raise AssertionError("legacy bundles do not contain the provider checker")
            return original_import(name, globals, locals, fromlist, level)

        path = ROOT / "scripts/oem_policy.py"
        namespace = {"__file__": str(path), "__name__": "scripts.oem_policy_import_probe", "__package__": "scripts"}
        with patch.object(builtins, "__import__", side_effect=reject_optional_module):
            exec(compile(path.read_bytes(), str(path), "exec"), namespace)
            self.assertEqual(namespace["check_native_contents"](*oem_fixture())["status"], "verified")
            self.assertEqual(namespace["check_native_contents"](*property_fixture())["status"], "verified")

    def test_provider_forms_are_not_accepted_by_default_even_if_properties_are_selected(self):
        for properties in (False, True):
            value = fixture(properties)
            with self.subTest(properties=properties), self.assertRaises(op.OemPolicyError):
                op.check_native_contents(*value[:6])

    def test_both_current_context_outputs_and_explicit_contract_are_required(self):
        for missing in (6, 7, 8):
            value = fixture()
            value[missing] = None
            with self.subTest(missing=missing), self.assertRaisesRegex(op.OemPolicyError, "context"):
                self.check(value)

    def test_contract_device_platform_factory_and_prerequisite_bindings_fail_closed(self):
        for field in ("device", "platform", "factory_package_sha256", "oem_policy", "init_helper"):
            value = fixture()
            if field in {"oem_policy", "init_helper"}:
                value[6]["required_contracts"][field]["sha256"] = "0" * 64
            else:
                value[6][field] = "different"
            with self.subTest(field=field), self.assertRaisesRegex(op.OemPolicyError, "provider profile"):
                self.check(value)

    def test_provider_and_oem_source_names_cannot_overlap(self):
        value = fixture(True)
        value[6]["types"][ATFWD] = copy.deepcopy(value[6]["types"][SIGMA_SERVICE])
        with self.assertRaisesRegex(op.OemPolicyError, "duplicates an OEM"):
            self.check(value)

    def test_oem_mappings_roles_and_factory_derivation_are_still_required(self):
        for change in ("mapping", "role", "factory", "helper"):
            value = fixture(True)
            if change == "mapping":
                path = op.INPUT_FLAGS["system_ext_mapping"]
                value[0][path] = value[0][path].replace(f"(typeattributeset {ATFWD}_202504 ({ATFWD}))".encode(), b"")
            elif change == "role":
                path = op.INPUT_FLAGS["system_ext_cil"]
                value[0][path] = value[0][path].replace(f"(roletype object_r {ATFWD})".encode(), b"")
            elif change == "factory":
                value[1] += b"; changed original"
            else:
                value[0][op.INPUT_FLAGS["platform_cil"]] += b"(allow init_dev_config apexd_select_prop (property_service (set)))"
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                self.check(value)

    def test_property_read_context_and_effective_budget_cannot_be_relaxed_by_provider(self):
        for change in ("read", "context", "extra_indirect"):
            value = fixture(True)
            if change == "read":
                path = op.INPUT_FLAGS["system_ext_cil"]
                value[0][path] = value[0][path].replace(
                    b"(allow mediaextractor vendor_mm_parser_prop (file (getattr map open read)))", b"")
            elif change == "context":
                value[5] = value[5].replace(b"vendor.mm.enable.qcom_parser", b"vendor.mm.")
            else:
                value[0][op.INPUT_FLAGS["platform_cil"]] += b"(allow domain vendor_mm_parser_prop (file (read)))"
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                self.check(value)

    def test_unrelated_permissions_or_transitions_cannot_hide_behind_provider_opt_in(self):
        for addition in (
            b"(allow init_dev_config offlinelog_file (file (read)))",
            b"(dontaudit init_dev_config offlinelog_file (file (read)))",
            b"(auditallow init_dev_config offlinelog_file (file (read)))",
            b"(typetransition init_dev_config offlinelog_file file offlinelog_file)",
            b"(allowx init_dev_config offlinelog_file (ioctl file ((range 0x0 0xffff))))",
        ):
            value = fixture(True)
            value[0][op.INPUT_FLAGS["system_ext_cil"]] += addition
            with self.subTest(addition=addition), self.assertRaises(op.OemPolicyError):
                self.check(value)

    def test_exact_provider_allow_dontaudit_and_transition_counts_are_preserved(self):
        for change in ("missing", "duplicate", "set", "dontaudit", "transition"):
            value = fixture(True)
            path = op.INPUT_FLAGS["system_ext_cil"]
            grant = f"(allow {SIGMA} servicemanager (binder (call transfer)))".encode()
            if change == "missing":
                value[0][path] = value[0][path].replace(grant, b"")
            elif change == "duplicate":
                value[0][path] += grant
            elif change == "set":
                value[0][path] += f"(allow {SIGMA} vendor_mm_parser_prop (property_service (set)))".encode()
            elif change == "dontaudit":
                value[0][path] = value[0][path].replace(f"(dontaudit init {SIGMA} (process (noatsecure)))".encode(), b"")
            else:
                value[0][path] = value[0][path].replace(f"(typetransition init {SIGMA}_exec process {SIGMA})".encode(), b"")
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "source permissions"):
                self.check(value)

    def test_required_provider_assertions_cannot_be_removed_or_weakened(self):
        for change in ("missing", "duplicate", "weakened"):
            value = fixture()
            path = op.INPUT_FLAGS["system_ext_cil"]
            assertion = f"(neverallow base_typeattr_9000 {SIGMA_SERVICE} (service_manager (add)))".encode()
            if change == "missing":
                value[0][path] = value[0][path].replace(assertion, b"")
            elif change == "duplicate":
                value[0][path] += assertion
            else:
                value[0][path] = value[0][path].replace(f"(not ({SIGMA}))".encode(),
                                                     f"(not ({SIGMA} untrusted_app))".encode())
            with self.subTest(change=change), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "restriction"):
                self.check(value)

    def test_generated_attribute_cannot_activate_inherited_permissions_or_other_semantics(self):
        inherited_rules = (
            "(allow base_typeattr_987654 apexd_select_prop (file (write)))",
            "(dontaudit base_typeattr_987654 apexd_select_prop (file (write)))",
            "(typetransition base_typeattr_987654 offlinelog_file file offlinelog_file)",
            "(neverallow base_typeattr_987654 apexd_select_prop (file (write)))",
        )
        for properties in (False, True):
            for rule in inherited_rules:
                value = fixture(properties)
                value[0][op.INPUT_FLAGS["platform_cil"]] += (
                    "(typeattribute base_typeattr_987654)" + rule).encode()
                value[0][op.INPUT_FLAGS["system_ext_cil"]] += (
                    f"(typeattributeset base_typeattr_987654 ({SIGMA}))").encode()
                with self.subTest(properties=properties, rule=rule), self.assertRaisesRegex(op.OemPolicyError, "inherited anonymous"):
                    self.check(value)

    def test_new_anonymous_name_cannot_supply_an_unresolved_foreign_reference(self):
        value = fixture()
        value[0][op.INPUT_FLAGS["platform_cil"]] += b"(allow base_typeattr_987654 apexd_select_prop (file (write)))"
        value[0][op.INPUT_FLAGS["system_ext_cil"]] += (
            f"(typeattribute base_typeattr_987654)(typeattributeset base_typeattr_987654 ({SIGMA}))").encode()
        with self.assertRaisesRegex(op.OemPolicyError, "inherited anonymous"):
            self.check(value)

    def test_identical_inherited_generated_assignment_is_not_a_new_permission(self):
        value = fixture(True)
        definition = b"(typeattribute base_typeattr_987654)(typeattributeset base_typeattr_987654 (init))"
        value[0][op.INPUT_FLAGS["platform_cil"]] += definition
        value[0][op.INPUT_FLAGS["system_ext_cil"]] += definition
        self.assertEqual(self.check(value)["status"], "verified")

    def test_inherited_domain_expression_may_grow_only_through_admitted_named_memberships(self):
        value = fixture(True)
        value[0][op.INPUT_FLAGS["platform_cil"]] += (
            b"(typeattribute base_typeattr_987654)(typeattributeset base_typeattr_987654 (domain))")
        value[0][op.INPUT_FLAGS["system_ext_cil"]] += (
            f"(typeattributeset base_typeattr_987654 ({SIGMA} vendor_qccsyshal_qti))").encode()
        self.assertEqual(self.check(value)["status"], "verified")
        # Object labels are not part of the independently admitted domain set.
        value[0][op.INPUT_FLAGS["system_ext_cil"]] += (
            f"(typeattributeset base_typeattr_987654 ({SIGMA_SERVICE}))").encode()
        with self.assertRaisesRegex(op.OemPolicyError, "inherited anonymous"):
            self.check(value)

    def test_source_cannot_override_inherited_anonymous_expansion(self):
        value = fixture()
        value[0][op.INPUT_FLAGS["platform_cil"]] += (
            b"(typeattribute base_typeattr_987654)(typeattributeset base_typeattr_987654 (init))"
            b"(expandtypeattribute (base_typeattr_987654) false)")
        value[0][op.INPUT_FLAGS["system_ext_cil"]] += b"(expandtypeattribute (base_typeattr_987654) true)"
        with self.assertRaisesRegex(op.OemPolicyError, "anonymous attribute expansion"):
            self.check(value)

    def test_provider_checker_receives_full_corpus_without_removed_forms(self):
        value = fixture(True)
        with patch.object(fp, "check_native_extension", wraps=fp.check_native_extension) as check:
            self.check(value)
        policy, parsed, supplied_contract = check.call_args.args
        self.assertEqual(list(parsed), list(op.INPUT_FLAGS.values()))
        expected = Counter(form.expr for runtime, raw in value[0].items() for form in vp.parse(raw, runtime))
        actual = Counter(form.expr for forms in parsed.values() for form in forms)
        self.assertEqual(actual, expected)
        self.assertEqual(Counter(form.expr for forms in policy.by_head.values() for form in forms), expected)
        self.assertIs(supplied_contract, value[6])

    def test_private_provider_types_cannot_leak_into_other_partitions_or_mappings(self):
        for runtime, form in (
            (op.INPUT_FLAGS["product_cil"], f"(allow {SIGMA} init (binder (call)))"),
            (op.INPUT_FLAGS["product_mapping"], f"(typeattribute {SIGMA}_202504)(typeattributeset {SIGMA}_202504 ({SIGMA}))"),
            (op.INPUT_FLAGS["system_ext_mapping"], f"(typeattribute {SIGMA}_202504)(typeattributeset {SIGMA}_202504 ({SIGMA}))"),
        ):
            value = fixture()
            value[0][runtime] += form.encode()
            with self.subTest(runtime=runtime), self.assertRaises((op.OemPolicyError, fp.FrameworkProviderPolicyError)):
                self.check(value)

    def test_named_membership_requires_exact_platform_baseline_plus_all_owned_deltas(self):
        for change in ("missing_inherited", "unrelated_member", "duplicate_assignment"):
            value = fixture(True)
            path = op.INPUT_FLAGS["system_ext_cil"]
            forms = vp.parse(value[0][path], path)
            form = next(form for form in forms if form.expr[:2] == ("typeattributeset", "file_type"))
            if change == "duplicate_assignment":
                value[0][path] += vp.render(form.expr).encode()
            else:
                members = list(form.expr[2])
                if change == "missing_inherited":
                    members.remove("inherited_platform_file")
                else:
                    members.append("apexd_select_prop")
                replacement = ("typeattributeset", "file_type", tuple(members))
                value[0][path] = value[0][path][:form.start] + vp.render(replacement).encode() + value[0][path][form.end:]
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "source-owned"):
                self.check(value)

    def test_native_contexts_reject_missing_duplicate_wrong_labels_and_extra_provider_paths(self):
        for index in (7, 8):
            for change in ("missing", "duplicate", "wrong_label", "extra_path"):
                value = fixture()
                rows = value[index].splitlines()
                if change == "missing":
                    value[index] = b"\n".join(rows[1:])
                elif change == "duplicate":
                    value[index] += rows[0] + b"\n"
                elif change == "wrong_label":
                    value[index] = value[index].replace(b"u:object_r:", b"u:object_r:wrong_", 1)
                else:
                    value[index] += b"unexpected " + rows[0].split()[-1] + b"\n"
                with self.subTest(index=index, change=change), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "contexts"):
                    self.check(value)


class CompositionSourceAndFilesystemTests(unittest.TestCase):
    def test_actual_source_profiles_verify_without_claiming_provider_artifact_admission(self):
        for properties in (False, True):
            result = op.verify_sources(ROOT, provider_contract_path=ROOT / fp.CONTRACT_PATH,
                property_contract_path=ROOT / op.PROPERTY_CONTRACT_PATH if properties else None)
            self.assertEqual(len(result["provider_source_verification"]), 8)
            self.assertEqual(len(result["provider_source_files"]), 4)
            self.assertEqual(result["provider_contract_sha256"], fp.CONTRACT_SHA256)
            self.assertFalse(result["provider_artifact_bundle_verified"])
            self.assertEqual("property_contract_id" in result, properties)

    def test_native_optional_contract_and_context_paths_are_bound_and_hashed(self):
        value = fixture(True)
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            paths = {}
            for flag, runtime in op.INPUT_FLAGS.items():
                target = root / (flag + ".cil")
                target.write_bytes(value[0][runtime])
                paths[flag] = target
            for name, raw in (("vendor.cil", value[1]), ("cap.json", value[3]),
                              ("property_contexts", value[5]), ("file_contexts", value[7]),
                              ("service_contexts", value[8])):
                (root / name).write_bytes(raw)
            with patch.object(op, "load_contract", return_value=value[2]), \
                    patch.object(op, "load_property_contract", return_value=value[4]):
                result = op.check_native(paths, root / "vendor.cil", root / "cap.json",
                    property_contract_path=ROOT / op.PROPERTY_CONTRACT_PATH,
                    property_contexts_path=root / "property_contexts", provider_contract_path=ROOT / fp.CONTRACT_PATH,
                    provider_file_contexts_path=root / "file_contexts", provider_service_contexts_path=root / "service_contexts")
            self.assertEqual(result["status"], "verified")
            self.assertIn("framework_provider_policy.py", result["tool_sources_sha256"])
            bound = {row["path"] for row in result["input_bindings"]}
            self.assertTrue({str(root / "file_contexts"), str(root / "service_contexts")} <= bound)
            self.assertTrue(result["all_inputs_rehashed_unchanged"])

    def test_cli_source_provider_profile_requires_explicit_flag_and_fresh_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).resolve() / "receipt.json"
            args = ["verify-sources", "--source-root", str(ROOT), "--provider-contract", str(ROOT / fp.CONTRACT_PATH),
                    "--property-contract", str(ROOT / op.PROPERTY_CONTRACT_PATH), "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(op.main(args), 0)
            original = output.read_bytes()
            self.assertEqual(json.loads(original)["provider_contract_sha256"], fp.CONTRACT_SHA256)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(op.main(args), 1)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
