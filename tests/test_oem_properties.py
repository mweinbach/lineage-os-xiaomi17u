"""Fail-closed property source and native-output contracts, using synthetic CIL."""

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
from tests.test_oem_policy import native_fixture


ROOT = Path(__file__).resolve().parents[1]
PARSER = "vendor_mm_parser_prop"
VIDEO = "vendor_sys_video_prop"
DPM = "vendor_persist_dpm_prop"
PERF = "vendor_wlc_public_prop"
NAMES = {PARSER, VIDEO, DPM, PERF}


def property_fixture():
    corpus, vendor, contract, capability = native_fixture()
    properties = copy.deepcopy(op.load_property_contract(ROOT / op.PROPERTY_CONTRACT_PATH))
    platform = op.INPUT_FLAGS["platform_cil"]
    ext = op.INPUT_FLAGS["system_ext_cil"]
    mapping = op.INPUT_FLAGS["system_ext_mapping"]
    public = op.INPUT_FLAGS["factory_pub"]
    corpus[platform] += (
        b"(type mediaextractor)(type mediaserver)(type vendor_init)(type vendor_dpmd_vndr)(type vendor_hal_perf_default)\n"
        b"(typeattributeset domain (mediaextractor mediaserver vendor_init vendor_dpmd_vndr vendor_hal_perf_default))\n"
        b"(typeattributeset coredomain (mediaextractor mediaserver))\n"
        b"(roletype object_r mediaextractor)(roletype object_r mediaserver)\n"
        b"(typeattribute property_type)(typeattribute system_property_type)(typeattribute system_public_property_type)\n"
    )
    corpus[public] += b"(type mediaextractor)(type mediaserver)\n"
    named_members = {}
    for name, spec in properties["types"].items():
        corpus[ext] += f"(type {name})(roletype object_r {name})\n".encode()
        for attr in spec["attributes"]:
            named_members.setdefault(attr, []).append(name)
        corpus[mapping] += f"(typeattribute {name}_202504)(typeattributeset {name}_202504 ({name}))\n".encode()
        corpus[public] += f"(type {name})(typeattribute {name}_202504)(roletype object_r {name}_202504)\n".encode()
    for attr, members in named_members.items():
        corpus[ext] += f"(typeattributeset {attr} ({' '.join(members)}))\n".encode()
    for row in properties["read_clauses"]:
        corpus[ext] += (f"(allow {row['source_type']} {row['target_type']} ({row['class']} "
                        f"({' '.join(row['permissions'])})))\n").encode()
    for row in contract["unchanged_factory_inputs"]:
        if row["runtime_path"] == public:
            row.update(sha256=vp.sha(corpus[public]), size_bytes=len(corpus[public]))
    contexts = "".join(f"{row['property_pattern']} {row['context']}\n" for row in properties["property_contexts"]).encode()
    # This synthetic policy has only the two source read clauses. Production
    # uses the separate, pinned 105-edge budget from the complete private audit.
    properties["native_effective_ordinary_allow_edges"] = {}
    for name in properties["types"]:
        source = {PARSER: "mediaextractor", VIDEO: "mediaserver"}.get(name)
        rows = [(source, name, "file", permission) for permission in ("getattr", "map", "open", "read")] if source else []
        raw = b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in rows)
        properties["native_effective_ordinary_allow_edges"][name] = {
            "count": len(rows), "sha256_sorted_compact_json_rows": vp.sha(raw)}
    return corpus, vendor, contract, capability, properties, contexts


def source_fixture():
    contract = copy.deepcopy(op.load_property_contract(ROOT / op.PROPERTY_CONTRACT_PATH))
    contents = {row["path"]: (ROOT / row["path"]).read_bytes() for row in contract["source_files"]}
    return contents, contract


def replace_source(contents, contract, kind, change):
    row = next(row for row in contract["source_files"] if row["kind"] == kind)
    raw = change(contents[row["path"]])
    contents[row["path"]] = raw
    row.update(sha256=vp.sha(raw), size_bytes=len(raw))


class PropertySourceTests(unittest.TestCase):
    def test_actual_opt_in_has_four_public_types_eight_prefixes_and_two_readers(self):
        result = op.verify_sources(ROOT, property_contract_path=ROOT / op.PROPERTY_CONTRACT_PATH)
        properties = result["property_source_verification"]
        self.assertEqual(set(properties["declarations"]), NAMES)
        self.assertEqual(len(properties["property_contexts"]), 8)
        self.assertEqual({(row["source_type"], row["target_type"]) for row in properties["read_clauses"]},
                         {("mediaextractor", PARSER), ("mediaserver", VIDEO)})
        self.assertEqual(result["property_contract_sha256"], op.PROPERTY_CONTRACT_SHA256)
        self.assertTrue(result["all_inputs_rehashed_unchanged"])
        self.assertTrue(all(value is False for value in result["scope"].values()))

    def test_default_source_profile_and_frozen_v1_bytes_are_unchanged(self):
        raw = (ROOT / op.CONTRACT_PATH).read_bytes()
        self.assertEqual(vp.sha(raw), "3de325f5ff8ba52dc8e43e20556fe876cc44905b04d40ed3b0ff038eaff10cc7")
        self.assertEqual(len(raw), 12375)
        base = op.load_contract()
        for row in base["source_files"]:
            self.assertEqual(vp.sha((ROOT / row["path"]).read_bytes()), row["sha256"])
        result = op.verify_sources(ROOT)
        self.assertEqual(len(result["declarations"]), 3)
        self.assertNotIn("property_contract_sha256", result)
        self.assertNotIn("property_source_verification", result)

    def test_property_contract_requires_explicit_identical_bytes(self):
        with self.assertRaisesRegex(op.OemPolicyError, "explicitly"):
            op.load_property_contract(None)
        with tempfile.TemporaryDirectory() as directory:
            copy_path = Path(directory).resolve() / "contract.json"
            raw = (ROOT / op.PROPERTY_CONTRACT_PATH).read_bytes()
            copy_path.write_bytes(raw)
            self.assertEqual(op.load_property_contract(copy_path), op.load_property_contract(ROOT / op.PROPERTY_CONTRACT_PATH))
            copy_path.write_bytes(raw + b" ")
            with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256"):
                op.load_property_contract(copy_path)

    def test_unreviewed_source_bytes_fail_before_grammar(self):
        contents, contract = source_fixture()
        contents[next(iter(contents))] += b"\n# another source revision\n"
        with self.assertRaisesRegex(op.OemPolicyError, "source hash"):
            op.verify_property_source_contents(contents, contract)

    def test_repinned_source_cannot_use_other_macros_or_add_set_rules(self):
        for change in (
            lambda raw: raw.replace(b"system_public_prop", b"vendor_public_prop"),
            lambda raw: raw.replace(b"system_public_prop", b"system_vendor_config_prop"),
            lambda raw: raw + b"set_prop(vendor_init, vendor_mm_parser_prop)\n",
            lambda raw: raw + b"allow mediaextractor vendor_mm_parser_prop:file write;\n",
        ):
            contents, contract = source_fixture()
            replace_source(contents, contract, "system_public_prop", change)
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "only reviewed"):
                op.verify_property_source_contents(contents, contract)

    def test_missing_extra_duplicate_or_other_property_is_not_admitted(self):
        for change in (
            lambda raw: raw.replace(b"system_public_prop(vendor_mm_parser_prop)\n", b""),
            lambda raw: raw + b"system_public_prop(vendor_wlc_prop)\n",
            lambda raw: raw + b"system_public_prop(vendor_wlc_public_prop)\n",
        ):
            contents, contract = source_fixture()
            replace_source(contents, contract, "system_public_prop", change)
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "declarations"):
                op.verify_property_source_contents(contents, contract)

    def test_readers_are_exact_and_cannot_be_duplicated_or_replaced(self):
        for change in (
            lambda raw: raw.replace(b"mediaextractor", b"system_app"),
            lambda raw: raw + b"get_prop(mediaextractor, vendor_mm_parser_prop)\n",
            lambda raw: raw.replace(b"get_prop(mediaextractor, vendor_mm_parser_prop)", b""),
        ):
            contents, contract = source_fixture()
            replace_source(contents, contract, "get_prop", change)
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "reads"):
                op.verify_property_source_contents(contents, contract)

    def test_source_contexts_preserve_implicit_prefix_and_no_value_type(self):
        for change in (
            lambda raw: raw.replace(b"vendor.mm.enable.qcom_parser ", b"vendor.mm. "),
            lambda raw: raw.replace(b":s0\n", b":s0 exact\n", 1),
            lambda raw: raw.replace(b":s0\n", b":s0 prefix bool\n", 1),
            lambda raw: raw.replace(b":s0\n", b":s0 prefix\n", 1),
            lambda raw: raw.replace(b":s0\n", b":s0 # inline comment\n", 1),
            lambda raw: raw + b"vendor.mpctl.init.complete u:object_r:vendor_wlc_public_prop:s0\n",
        ):
            contents, contract = source_fixture()
            replace_source(contents, contract, "property_contexts", change)
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                op.verify_property_source_contents(contents, contract)

    def test_extra_file_in_property_owner_directory_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            source_root = Path(directory).resolve()
            for contract in (op.load_contract(), op.load_property_contract(ROOT / op.PROPERTY_CONTRACT_PATH)):
                for row in contract["source_files"]:
                    target = source_root / row["path"]
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes((ROOT / row["path"]).read_bytes())
            target.with_name("unreviewed.te").write_text("allow init default_prop:property_service set;\n")
            with self.assertRaisesRegex(op.OemPolicyError, "unreviewed file"):
                op.verify_sources(source_root, capability_path=ROOT / "config/nezha-init-helper-capability.json",
                                  property_contract_path=ROOT / op.PROPERTY_CONTRACT_PATH)

    def test_public_contract_keeps_factory_payloads_private_and_scope_limited(self):
        raw = (ROOT / op.PROPERTY_CONTRACT_PATH).read_bytes()
        contract = op.load_property_contract(ROOT / op.PROPERTY_CONTRACT_PATH)
        self.assertEqual(contract["base_oem_contract"]["sha256"], op.CONTRACT_SHA256)
        self.assertTrue(all(value is False for value in contract["limits"].values()))
        self.assertEqual(len(contract["source_files"]), 4)
        self.assertEqual(len(contract["property_contexts"]), 8)
        for forbidden in (b"(allow ", b"BEGIN PRIVATE KEY", b"/Users/", b"(neverallow "):
            self.assertNotIn(forbidden, raw)


class PropertyNativeTests(unittest.TestCase):
    def check(self, fixture=None):
        return op.check_native_contents(*(fixture or property_fixture()))

    def test_explicit_profile_checks_seven_objects_six_mappings_and_two_reads(self):
        result = self.check()
        self.assertEqual(len(result["type_ownership"]), 7)
        self.assertEqual(len(result["property_contexts_verified"]), 8)
        self.assertEqual(len(result["explicit_source_read_clauses"]), 2)
        for name in NAMES:
            row = result["type_ownership"][name]
            self.assertEqual(row["versioned_mapping"], [name])
            self.assertEqual(row["roles"], ["object_r"])
            self.assertFalse(row["domain"])
            self.assertFalse(row["coredomain"])
            self.assertNotIn("vendor_property_type", row["attributes"])
        self.assertEqual(result["helper_effective_property_set_grants"], 0)
        self.assertTrue(all(value is False for value in result["scope"].values()))

    def test_default_native_guard_rejects_property_additions(self):
        fixture = property_fixture()
        with self.assertRaises(op.OemPolicyError):
            op.check_native_contents(*fixture[:4])
        self.assertNotIn("property_contract_id", op.check_native_contents(*native_fixture()))

    def test_profile_and_native_contexts_must_both_be_selected(self):
        fixture = list(property_fixture())
        fixture[5] = None
        with self.assertRaisesRegex(op.OemPolicyError, "native context"):
            self.check(fixture)
        fixture = list(native_fixture()) + [None, b"\n"]
        with self.assertRaisesRegex(op.OemPolicyError, "silently enable"):
            self.check(fixture)

    def test_wrong_base_factory_platform_or_helper_binding_fails(self):
        for key in ("base_oem_contract", "factory_package_sha256", "platform", "required_capability_contract"):
            fixture = list(property_fixture())
            fixture[4][key] = {} if isinstance(fixture[4][key], dict) else "wrong"
            with self.subTest(key=key), self.assertRaises(op.OemPolicyError):
                self.check(fixture)

    def test_property_singletons_roles_and_source_owner_are_independent_requirements(self):
        for change in ("map_missing", "map_duplicate", "map_other_member", "role_missing", "owner_other"):
            fixture = list(property_fixture())
            corpus = fixture[0]
            ext, mapping = op.INPUT_FLAGS["system_ext_cil"], op.INPUT_FLAGS["system_ext_mapping"]
            assignment = f"(typeattributeset {PARSER}_202504 ({PARSER}))".encode()
            if change == "map_missing":
                corpus[mapping] = corpus[mapping].replace(assignment, b"")
            elif change == "map_duplicate":
                corpus[mapping] += assignment
            elif change == "map_other_member":
                corpus[mapping] = corpus[mapping].replace(assignment, f"(typeattributeset {PARSER}_202504 ({VIDEO}))".encode())
            elif change == "role_missing":
                corpus[ext] = corpus[ext].replace(f"(roletype object_r {PARSER})".encode(), b"")
            else:
                declaration = f"(type {PARSER})".encode()
                corpus[ext] = corpus[ext].replace(declaration, b"")
                corpus[op.INPUT_FLAGS["product_cil"]] += declaration
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                self.check(fixture)

    def test_vendor_ownership_or_domain_promotion_does_not_follow_name_prefix(self):
        for attr in ("vendor_property_type", "domain", "coredomain"):
            fixture = list(property_fixture())
            fixture[0][op.INPUT_FLAGS["platform_cil"]] += (
                ("(typeattribute vendor_property_type)" if attr == "vendor_property_type" else "")
                + f"(typeattributeset {attr} ({PARSER}))").encode()
            with self.subTest(attr=attr), self.assertRaises(op.OemPolicyError):
                self.check(fixture)

    def test_exact_source_reads_cannot_hide_write_set_other_reader_or_extra_grant(self):
        for change in ("write", "set", "other_reader", "extra", "duplicate", "missing"):
            fixture = list(property_fixture())
            corpus, ext = fixture[0], op.INPUT_FLAGS["system_ext_cil"]
            grant = f"(allow mediaextractor {PARSER} (file (getattr map open read)))".encode()
            if change == "write":
                corpus[ext] = corpus[ext].replace(grant, grant.replace(b"open read", b"open read write"))
            elif change == "set":
                corpus[ext] += f"(allow vendor_init {PARSER} (property_service (set)))".encode()
            elif change == "other_reader":
                corpus[ext] = corpus[ext].replace(grant, grant.replace(b"mediaextractor", b"mediaserver"))
            elif change == "extra":
                corpus[ext] += b"(allow init_dev_config offlinelog_file (file (read)))"
            elif change == "duplicate":
                corpus[ext] += grant
            else:
                corpus[ext] = corpus[ext].replace(grant, b"")
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "source permissions"):
                self.check(fixture)

    def test_read_source_cannot_be_replaced_by_alias_or_lose_process_classification(self):
        for change in ("alias", "not_core", "not_domain", "wrong_role", "wrong_owner"):
            fixture = list(property_fixture())
            corpus, platform, public = fixture[0], op.INPUT_FLAGS["platform_cil"], op.INPUT_FLAGS["factory_pub"]
            if change == "alias":
                corpus[platform] = corpus[platform].replace(b"(type mediaextractor)",
                    b"(typealias mediaextractor)(typealiasactual mediaextractor init_dev_config)")
                corpus[public] = corpus[public].replace(b"(type mediaextractor)", b"")
                for row in fixture[2]["unchanged_factory_inputs"]:
                    if row["runtime_path"] == public:
                        row.update(sha256=vp.sha(corpus[public]), size_bytes=len(corpus[public]))
            elif change == "not_core":
                corpus[platform] = corpus[platform].replace(b"(typeattributeset coredomain (mediaextractor mediaserver))",
                                                          b"(typeattributeset coredomain (mediaserver))")
            elif change == "not_domain":
                corpus[platform] = corpus[platform].replace(b"(typeattributeset domain (mediaextractor mediaserver",
                                                          b"(typeattributeset domain (mediaserver")
            elif change == "wrong_role":
                corpus[platform] = corpus[platform].replace(b"(roletype object_r mediaextractor)", b"")
            else:
                corpus[platform] = corpus[platform].replace(b"(type mediaextractor)", b"")
                corpus[op.INPUT_FLAGS["product_cil"]] += b"(type mediaextractor)"
            with self.subTest(change=change), self.assertRaisesRegex(op.OemPolicyError, "property reader"):
                self.check(fixture)

    def test_native_context_normalization_can_only_make_prefix_explicit(self):
        fixture = list(property_fixture())
        fixture[5] = fixture[5].replace(b":s0\n", b":s0 prefix\n")
        self.assertEqual(len(self.check(fixture)["property_contexts_verified"]), 8)
        for change in (
            lambda raw: raw.replace(b":s0\n", b":s0 exact\n", 1),
            lambda raw: raw.replace(b":s0\n", b":s0 prefix bool\n", 1),
            lambda raw: raw.replace(b":s0\n", b":s0 # inline comment\n", 1),
            lambda raw: b"\n".join(raw.splitlines()[1:]),
            lambda raw: raw + b"vendor. u:object_r:vendor_wlc_public_prop:s0\n",
            lambda raw: raw.replace(b"vendor.qcom_parser.", b"vendor.qcom_parser"),
        ):
            fixture = list(property_fixture())
            fixture[5] = change(fixture[5])
            with self.subTest(change=change), self.assertRaises(op.OemPolicyError):
                self.check(fixture)

    def test_property_profile_does_not_relax_existing_helper_or_permissive_guards(self):
        for addition in (
            b"(allow init_dev_config apexd_select_prop (property_service (set)))",
            b"(typepermissive vendor_init)",
        ):
            fixture = list(property_fixture())
            fixture[0][op.INPUT_FLAGS["platform_cil"]] += addition
            with self.subTest(addition=addition), self.assertRaises(op.OemPolicyError):
                self.check(fixture)

    def test_finite_budget_catches_indirect_platform_grants_and_property_outgoing_edges(self):
        for addition in (
            f"(allow domain {PARSER} (file (read)))".encode(),
            f"(allow vendor_init {DPM} (property_service (set)))".encode(),
            f"(allow property_type media_variant_prop (filesystem (associate)))".encode(),
            f"(allow property_type self (file (getattr)))".encode(),
        ):
            fixture = list(property_fixture())
            fixture[0][op.INPUT_FLAGS["platform_cil"]] += addition
            with self.subTest(addition=addition), self.assertRaisesRegex(op.OemPolicyError, "finite edge budget"):
                self.check(fixture)

    def test_cli_source_profile_is_explicit_and_receipt_cannot_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory).resolve() / "receipt.json"
            args = ["verify-sources", "--source-root", str(ROOT), "--property-contract",
                    str(ROOT / op.PROPERTY_CONTRACT_PATH), "--output", str(output)]
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(op.main(args), 0)
            result = json.loads(output.read_bytes())
            self.assertEqual(result["property_contract_sha256"], op.PROPERTY_CONTRACT_SHA256)
            original = output.read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(op.main(args), 1)
            self.assertEqual(output.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
