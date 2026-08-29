"""Offline adversarial tests of the explicit private provider policy guard."""

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import framework_provider_policy as fp
from scripts import vendor_policy as vp


ROOT = Path(__file__).resolve().parents[1]
SIGMA = "vendor_sigmahal_qti"
QCC = "vendor_qccsyshal_qti"
SERVICE = "vendor_hal_sigma_miracast_service"


def native_fixture():
    contract = copy.deepcopy(fp.load_contract())
    base_domains = ["init", "servicemanager", "audioserver", "surfaceflinger", "atrace",
                    "shell", "system_app", "traceur_app", "untrusted_app", "su"]
    base_objects = ["audioserver_service", "surfaceflinger_service"]
    attrs = sorted({attr for spec in contract["types"].values() for attr in spec["attributes"]})
    platform = "(role r)(role object_r)\n"
    platform += "".join(f"(type {name})(roletype object_r {name})\n" for name in base_domains + base_objects)
    platform += "".join(f"(typeattribute {name})\n" for name in attrs)
    platform += "(typeattributeset domain (" + " ".join(base_domains) + "))\n"
    platform += "(typeattributeset coredomain (init servicemanager audioserver surfaceflinger))\n"
    platform += "(roletype r domain)\n"
    source = ""
    for name, spec in contract["types"].items():
        source += f"(type {name})(roletype object_r {name})\n"
        source += "".join(f"(typeattributeset {attr} ({name}))\n" for attr in spec["attributes"])
    source += "\n".join(vp.render(expr) for expr, count in fp.expected_native_forms(contract).items()
                          for _ in range(count)) + "\n"
    for index, row in enumerate(contract["native_policy_budget"]["registration_assertions"]):
        attr = "base_typeattr_" + str(9000 + index)
        source += f"(typeattribute {attr})(typeattributeset {attr} (and (domain) (not ({' '.join(row['exclude_domains'])}))))\n"
        source += f"(neverallow {attr} {row['service']} (service_manager ({row['permission']})))\n"
    corpus = {
        "/system/etc/selinux/plat_sepolicy.cil": platform.encode(),
        fp.EXT_RUNTIME: source.encode(), fp.EXT_MAPPING: b"\n",
        "/vendor/etc/selinux/vendor_sepolicy.cil": b"\n",
        "/product/etc/selinux/mapping/202504.cil": b"\n",
    }
    return corpus, contract


def native_check(corpus, contract):
    parsed = {runtime: vp.parse(raw, runtime) for runtime, raw in corpus.items()}
    policy = vp.Policy([form for forms in parsed.values() for form in forms])
    return fp.check_native_extension(policy, parsed, contract)


class SourceTests(unittest.TestCase):
    def test_actual_private_profile_does_not_claim_provider_or_hardware_admission(self):
        result = fp.verify_sources(ROOT)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(len(result["types"]), 8)
        self.assertFalse(result["provider_bundle_verified"])
        self.assertFalse(result["pinned_android_macro_sources_verified"])
        self.assertTrue(result["all_inputs_rehashed_unchanged"])
        self.assertTrue(all(value is False for value in result["scope"].values()))

    def test_contract_is_exact_even_from_another_location(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "contract.json"
            raw = (ROOT / fp.CONTRACT_PATH).read_bytes()
            path.write_bytes(raw)
            self.assertEqual(fp.load_contract(path), fp.load_contract())
            path.write_bytes(raw + b" ")
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                fp.load_contract(path)

    def test_unreviewed_source_statement_fails_even_if_file_hash_is_rebound(self):
        contract = copy.deepcopy(fp.load_contract())
        contents = {row["path"]: (ROOT / row["path"]).read_bytes() for row in contract["source_files"]}
        row = next(row for row in contract["source_files"] if row["path"].endswith(SIGMA + ".te"))
        contents[row["path"]] += b"allow vendor_sigmahal_qti self:capability sys_admin;\n"
        row.update(sha256=vp.sha(contents[row["path"]]), size_bytes=len(contents[row["path"]]))
        with self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "statement budget"):
            fp.verify_source_contents(contents, contract)

    def test_extra_file_or_symlink_in_private_source_directory_fails(self):
        contract = fp.load_contract()
        for symlink in (False, True):
            with self.subTest(symlink=symlink), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve()
                for row in contract["source_files"]:
                    dest = root / row["path"]
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes((ROOT / row["path"]).read_bytes())
                extra = dest.with_name("unreviewed.te")
                extra.symlink_to(dest.name) if symlink else extra.write_text("type injected, domain;\n")
                with self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "unreviewed file"):
                    fp.verify_sources(root)

    def test_source_and_context_bytes_must_match_the_contract(self):
        contract = fp.load_contract()
        original = {row["path"]: (ROOT / row["path"]).read_bytes() for row in contract["source_files"]}
        for name in original:
            with self.subTest(name=name):
                contents = dict(original)
                contents[name] += b"# drift\n"
                with self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "source hash"):
                    fp.verify_source_contents(contents, contract)

    def test_provider_bundle_is_explicit_and_validated_by_its_own_guard(self):
        with patch("scripts.framework_provider_inputs.verify_bundle", return_value={"status": "verified"}) as verify:
            result = fp.verify_sources(ROOT, provider_bundle=Path("selected-private-bundle"))
        self.assertTrue(result["provider_bundle_verified"])
        verify.assert_called_once_with(Path("selected-private-bundle"),
                                       contract_path=ROOT / "config/nezha-framework-providers.json")
        with patch("scripts.framework_provider_inputs.verify_bundle", return_value={"status": "failed"}):
            with self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "not verified"):
                fp.verify_sources(ROOT, provider_bundle=Path("selected-private-bundle"))

    def test_android_macro_capture_must_have_exact_pinned_bytes(self):
        contract = copy.deepcopy(fp.load_contract())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            contract["pinned_android_sources"] = [{"path": "system/sepolicy/public/te_macros",
                                                   "size_bytes": 7, "sha256": vp.sha(b"pinned\n")}]
            path = root / contract["pinned_android_sources"][0]["path"]
            path.parent.mkdir(parents=True)
            path.write_bytes(b"pinned\n")
            self.assertEqual(len(fp.verify_macro_sources(root, contract)), 1)
            path.write_bytes(b"edited\n")
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                fp.verify_macro_sources(root, contract)

    def test_contract_records_lifecycle_limits_and_no_private_public_maps(self):
        contract = fp.load_contract()
        self.assertTrue(all(spec["versioned_attribute"] is None for spec in contract["types"].values()))
        self.assertTrue(all(spec["scope"] == "system_ext_private" for spec in contract["types"].values()))
        self.assertTrue(any("disabled" in line for line in contract["runtime_limits"]))
        self.assertTrue(any("hwservicemanager.ready" in line for line in contract["runtime_limits"]))
        self.assertFalse(contract["evidence_scope"]["original_oem_te_recovered"])
        raw = (ROOT / fp.CONTRACT_PATH).read_text()
        for forbidden in ("/Users/", "BEGIN PRIVATE KEY", "(allow ", "(neverallow "):
            self.assertNotIn(forbidden, raw)


class NativeGuardTests(unittest.TestCase):
    def test_exact_private_source_budget_roles_and_assertions_pass(self):
        result = native_check(*native_fixture())
        self.assertEqual(result["source_allow_clauses"], 26)
        self.assertEqual(result["source_dontaudit_clauses"], 2)
        self.assertEqual(result["source_type_transitions"], 2)
        self.assertEqual(len(result["registration_assertions"]), 4)
        self.assertEqual(result["type_ownership"][SIGMA]["roles"], ["object_r", "r"])
        self.assertEqual(result["type_ownership"][SERVICE]["roles"], ["object_r"])
        self.assertTrue(all(row["public_mapping"] is None for row in result["type_ownership"].values()))

    def test_missing_or_duplicate_source_type_owner_fails(self):
        for change in ("missing", "duplicate_source", "factory_owner"):
            corpus, contract = native_fixture()
            declaration = f"(type {SIGMA})".encode()
            if change == "missing":
                corpus[fp.EXT_RUNTIME] = corpus[fp.EXT_RUNTIME].replace(declaration, b"")
            elif change == "duplicate_source":
                corpus[fp.EXT_RUNTIME] += declaration
            else:
                corpus["/vendor/etc/selinux/vendor_sepolicy.cil"] += declaration
            with self.subTest(change=change), self.assertRaises((fp.FrameworkProviderPolicyError, vp.VendorPolicyError)):
                native_check(corpus, contract)

    def test_missing_process_role_and_extra_object_role_fail(self):
        for change in ("process", "object"):
            corpus, contract = native_fixture()
            if change == "process":
                key = "/system/etc/selinux/plat_sepolicy.cil"
                corpus[key] = corpus[key].replace(b"(roletype r domain)", b"")
            else:
                corpus[fp.EXT_RUNTIME] += f"(roletype r {SERVICE})".encode()
            with self.subTest(change=change), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "role"):
                native_check(corpus, contract)

    def test_mls_exceptions_or_service_domain_promotion_fail(self):
        for text in (f"(typeattribute mlstrustedsubject)(typeattributeset mlstrustedsubject ({QCC}))",
                     f"(typeattributeset domain ({SERVICE}))",
                     "(typeattribute mlstrustedobject)(typeattributeset mlstrustedobject (vendor_qcc_data_file))"):
            corpus, contract = native_fixture()
            corpus[fp.EXT_RUNTIME] += text.encode()
            with self.subTest(text=text), self.assertRaises(fp.FrameworkProviderPolicyError):
                native_check(corpus, contract)

    def test_private_type_cannot_gain_a_public_mapping_from_any_partition(self):
        for runtime in (fp.EXT_MAPPING, "/product/etc/selinux/mapping/202504.cil"):
            corpus, contract = native_fixture()
            corpus[runtime] += f"(typeattribute {SIGMA}_202504)(typeattributeset {SIGMA}_202504 ({SIGMA}))".encode()
            with self.subTest(runtime=runtime), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "attributes|mapping|outside"):
                native_check(corpus, contract)

    def test_private_provider_rules_or_aliases_cannot_be_hidden_in_other_partitions(self):
        for runtime in ("/system/etc/selinux/plat_sepolicy.cil", "/product/etc/selinux/product_sepolicy.cil"):
            for text in (f"(allow {SIGMA} su (binder (call)))",
                         f"(typeattribute base_typeattr_9980)(typeattributeset base_typeattr_9980 ({SIGMA}))(allow base_typeattr_9980 su (binder (call)))",
                         f"(typealias provider_alias)(typealiasactual provider_alias {SIGMA})"):
                corpus, contract = native_fixture()
                corpus[runtime] = corpus.get(runtime, b"") + text.encode()
                with self.subTest(runtime=runtime, text=text), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "outside"):
                    native_check(corpus, contract)

    def test_source_owned_type_cannot_gain_an_unreviewed_alias(self):
        corpus, contract = native_fixture()
        corpus[fp.EXT_RUNTIME] += f"(typealias provider_alias)(typealiasactual provider_alias {SIGMA})".encode()
        with self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "alias"):
            native_check(corpus, contract)

    def test_exact_permission_budget_rejects_extra_missing_or_duplicate_grants(self):
        for change in ("extra", "missing", "duplicate", "indirect", "debug_tcp", "audit", "xperm"):
            corpus, contract = native_fixture()
            grant = f"(allow {SIGMA} servicemanager (binder (call transfer)))".encode()
            if change == "missing":
                corpus[fp.EXT_RUNTIME] = corpus[fp.EXT_RUNTIME].replace(grant, b"")
            elif change == "duplicate":
                corpus[fp.EXT_RUNTIME] += grant
            elif change == "indirect":
                corpus[fp.EXT_RUNTIME] += f"(typeattribute base_typeattr_9999)(typeattributeset base_typeattr_9999 ({SIGMA}))(allow base_typeattr_9999 su (binder (call)))".encode()
            else:
                rows = {"extra": f"(allow {SIGMA} su (binder (call)))",
                        "debug_tcp": f"(allow {SIGMA} su (tcp_socket (accept getopt read write)))",
                        "audit": f"(auditallow {SIGMA} su (binder (call)))",
                        "xperm": f"(allowx {SIGMA} {SIGMA} (ioctl file ((range 0x0 0xffff))))"}
                corpus[fp.EXT_RUNTIME] += rows[change].encode()
            with self.subTest(change=change), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "budget"):
                native_check(corpus, contract)

    def test_changed_transition_or_dontaudit_is_rejected(self):
        for old, new in ((f"(typetransition init {SIGMA}_exec process {SIGMA})", f"(typetransition init {SIGMA}_exec process {QCC})"),
                         (f"(dontaudit init {SIGMA} (process (noatsecure)))", f"(dontaudit init {SIGMA} (process (transition)))")):
            corpus, contract = native_fixture()
            corpus[fp.EXT_RUNTIME] = corpus[fp.EXT_RUNTIME].replace(old.encode(), new.encode())
            with self.subTest(old=old), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "budget"):
                native_check(corpus, contract)

    def test_registration_assertions_cannot_be_removed_weakened_or_duplicated(self):
        for change in ("missing", "weakened", "duplicate"):
            corpus, contract = native_fixture()
            needle = f"(neverallow base_typeattr_9000 {SERVICE} (service_manager (add)))".encode()
            if change == "missing":
                corpus[fp.EXT_RUNTIME] = corpus[fp.EXT_RUNTIME].replace(needle, b"")
            elif change == "duplicate":
                corpus[fp.EXT_RUNTIME] += needle
            else:
                corpus[fp.EXT_RUNTIME] = corpus[fp.EXT_RUNTIME].replace(
                    f"(not ({SIGMA}))".encode(), f"(not ({SIGMA} untrusted_app))".encode())
            with self.subTest(change=change), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "restriction"):
                native_check(corpus, contract)

    def test_permissive_declaration_is_never_an_extension(self):
        corpus, contract = native_fixture()
        corpus[fp.EXT_RUNTIME] += f"(typepermissive {SIGMA})".encode()
        with self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "permissive"):
            native_check(corpus, contract)

    def test_permission_order_is_irrelevant_but_duplicate_permissions_are_invalid(self):
        corpus, contract = native_fixture()
        corpus[fp.EXT_RUNTIME] = corpus[fp.EXT_RUNTIME].replace(b"(binder (call transfer))", b"(binder (transfer call))")
        self.assertEqual(native_check(corpus, contract)["status"], "verified")
        corpus[fp.EXT_RUNTIME] = corpus[fp.EXT_RUNTIME].replace(b"(binder (transfer call))", b"(binder (call call transfer))", 1)
        with self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "unique literals"):
            native_check(corpus, contract)

    def test_form_hook_is_exact_and_not_a_provider_endpoint_wildcard(self):
        contract = fp.load_contract()
        forms = vp.parse(f"(allow {SIGMA} servicemanager (binder (call transfer)))".encode())
        self.assertTrue(fp.native_form_allowed(forms[0], contract))
        self.assertFalse(fp.native_form_allowed(vp.parse(f"(allow {SIGMA} su (binder (call)))".encode())[0], contract))


class ContextGuardTests(unittest.TestCase):
    def contexts(self):
        contract = fp.load_contract()
        return {key: ("\n".join(" ".join(row) for row in rows) + "\n").encode()
                for key, rows in contract["context_entries"].items()}, contract

    def test_exact_rows_pass_in_larger_native_context_files(self):
        contents, contract = self.contexts()
        contents["file_contexts"] += b"/unrelated u:object_r:unrelated_file:s0\n"
        result = fp.verify_native_contexts(contents["file_contexts"], contents["service_contexts"], contract)
        self.assertEqual(result["provider_context_rows"], {"file_contexts": 4, "service_contexts": 2})

    def test_missing_duplicate_or_broader_qdma_context_fails(self):
        for change in ("missing", "duplicate", "qdma", "wrong_label"):
            contents, contract = self.contexts()
            row = contents["file_contexts"].splitlines(keepends=True)[0]
            if change == "missing":
                contents["file_contexts"] = contents["file_contexts"].replace(row, b"")
            elif change == "duplicate":
                contents["file_contexts"] += row
            elif change == "wrong_label":
                contents["file_contexts"] = contents["file_contexts"].replace(b"vendor_sigmahal_qti_exec", b"vendor_qccsyshal_qti_exec")
            else:
                contents["file_contexts"] = contents["file_contexts"].replace(b"/data/misc/qcc", b"/data/misc/(qcc|qdma)")
            with self.subTest(change=change), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "contexts"):
                fp.verify_native_contexts(contents["file_contexts"], contents["service_contexts"], contract)

    def test_same_path_or_service_with_a_foreign_label_cannot_hide_from_the_guard(self):
        for key in ("file_contexts", "service_contexts"):
            contents, contract = self.contexts()
            expected_key = contract["context_entries"][key][0][0]
            contents[key] += f"{expected_key} u:object_r:system_file:s0\n".encode()
            with self.subTest(key=key), self.assertRaisesRegex(fp.FrameworkProviderPolicyError, "contexts"):
                fp.verify_native_contexts(contents["file_contexts"], contents["service_contexts"], contract)


if __name__ == "__main__":
    unittest.main()
