"""Synthetic offline tests; proprietary CIL and a Linux guest are not required."""

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import vendor_policy as vp


ROOT = Path(__file__).resolve().parents[1]
VENDOR = "/vendor/etc/selinux/vendor_sepolicy.cil"
TARGET_ASSERTION = b"(neverallow all_types not_domain (binder (impersonate call set_context_mgr transfer)))"
SOURCE_ASSERTION = b"(neverallow not_domain all_types (binder (impersonate call set_context_mgr transfer)))"
PLATFORM = (
    b"(type proc)(type server)(type obj)\n"
    b"(typeattribute domain)(typeattributeset domain (proc server))\n"
    b"(typeattribute all_types)(typeattributeset all_types (all))\n"
    b"(typeattribute not_domain)(typeattributeset not_domain (not (domain)))\n"
    b"(typeattribute obj_202504)(typeattributeset obj_202504 (obj))\n"
    b"(typealias obj_alias)(typealiasactual obj_alias obj)\n"
    b"(role r)(role object_r)(roletype r domain)(roletype object_r obj)\n"
    b"(class binder (impersonate call set_context_mgr transfer))\n"
    + TARGET_ASSERTION + b"\n" + SOURCE_ASSERTION + b"\n"
)
BAD_TARGET = b"(allow proc obj_202504 (binder (call transfer)))"
BAD_SOURCE = b"(allow obj_alias server (binder (transfer)))"
VENDOR_DATA = (
    b"; private-style synthetic fixture\r\n" + BAD_TARGET + b"\r\n" + BAD_SOURCE + b"\r\n"
    + BAD_TARGET + b"\r\n"
    b"(allow proc server (binder (call transfer)))\r\n"
    b"(allow proc self (binder (call)))\r\n"
    b"(allow proc obj (fd (use)))\r\n"
    b"(allow proc obj (service_manager (find)))\r\n"
    b"(neverallow proc server (process (transition)))\r\n"
    b"(neverallowx proc server (ioctl chr_file (0x1234)))\r\n"
    b"(allowx proc server (ioctl chr_file (0x1234)))\r\n"
)
EXPECTED_VENDOR = VENDOR_DATA.replace(BAD_TARGET, b" " * len(BAD_TARGET)).replace(BAD_SOURCE, b" " * len(BAD_SOURCE))


def fixture(platform=PLATFORM, vendor=VENDOR_DATA):
    corpus = {vp.PLATFORM_RUNTIME: platform, VENDOR: vendor}
    contract = {
        "inputs": [{"runtime_path": path, "sha256": vp.sha(data), "size_bytes": len(data)}
                   for path, data in corpus.items()],
        "vendor_runtime_path": VENDOR,
        "binder_assertions": {"target_non_domain": vp.sha(TARGET_ASSERTION),
                              "source_non_domain": vp.sha(SOURCE_ASSERTION)},
        "service_object_types": ["obj"],
        "output": {"path": "vendor_sepolicy.cil", "sha256": vp.sha(EXPECTED_VENDOR),
                   "size_bytes": len(EXPECTED_VENDOR)},
        "expected": {"domain_types": 2, "role_r_types": 2, "removed_occurrences": 3,
                     "removed_distinct_normalized_statements": 2,
                     "bad_binder_groups_before": {"target_non_domain": 2, "source_non_domain": 1},
                     "neverallow_statements": 3, "neverallowx_statements": 1,
                     "vendor_neverallow_statements": 1, "related_fd_occurrences": 1,
                     "related_fd_distinct_statements": 1},
        "factory_package_sha256": "a" * 64,
        "classification_corpus": "synthetic-test-only",
    }
    return corpus, contract


class ParserTests(unittest.TestCase):
    def test_comments_strings_crlf_and_same_line_forms_preserve_exact_offsets(self):
        data = b';(type fake)\r\n(type a)(filecon "a(;x)" file (u object_r a (s0 s0)))\r\n'
        forms = vp.parse(data)
        self.assertEqual(len(forms), 2)
        self.assertEqual([form.line for form in forms], [2, 2])
        self.assertEqual(data[forms[0].start:forms[0].end], b"(type a)")
        self.assertEqual(forms[1].expr[1], '"a(;x)"')

    def test_unbalanced_nul_outside_atom_and_unterminated_quote_fail(self):
        for data in (b"(type a", b"(type a))", b"atom(type a)", b"(type \0)", b'("bad)', b"(type \xff)"):
            with self.subTest(data=data), self.assertRaises(vp.VendorPolicyError):
                vp.parse(data)

    def test_size_depth_and_token_bounds_fail(self):
        for name, bound in (("MAX_BYTES", 2), ("MAX_DEPTH", 1), ("MAX_TOKENS", 2)):
            with self.subTest(name=name), patch.object(vp, name, bound), self.assertRaises(vp.VendorPolicyError):
                vp.parse(b"(allow proc obj (binder (call)))")


class ClassificationTests(unittest.TestCase):
    def test_exact_removal_keeps_assertions_fd_service_and_valid_process_grants(self):
        corpus, contract = fixture()
        result, receipt = vp.derive_corpus(corpus, contract)
        self.assertEqual(result, EXPECTED_VENDOR)
        self.assertEqual(receipt["measured"]["removed_occurrences"], 3)
        self.assertEqual(receipt["measured"]["removed_distinct_normalized_statements"], 2)
        self.assertEqual(receipt["measured"]["combined_binder_allow_count_after"], 2)
        before = vp.parse(VENDOR_DATA)
        after = vp.parse(result)
        for head in ("neverallow", "neverallowx", "allowx"):
            self.assertEqual([form for form in before if form.expr[0] == head],
                             [form for form in after if form.expr[0] == head])
        self.assertIn(b"(allow proc obj (fd (use)))", result)
        self.assertIn(b"(allow proc obj (service_manager (find)))", result)
        self.assertIn(b"(allow proc server (binder (call transfer)))", result)
        self.assertIn(b"(allow proc self (binder (call)))", result)
        self.assertEqual([i for i, byte in enumerate(VENDOR_DATA) if byte in (10, 13)],
                         [i for i, byte in enumerate(result) if byte in (10, 13)])

    def test_duplicate_rules_are_removed_as_separate_occurrences_even_on_same_line(self):
        vendor = VENDOR_DATA.replace(BAD_TARGET + b"\r\n" + BAD_SOURCE, BAD_TARGET + BAD_SOURCE)
        corpus, contract = fixture(vendor=vendor)
        expected = vendor.replace(BAD_TARGET, b" " * len(BAD_TARGET)).replace(BAD_SOURCE, b" " * len(BAD_SOURCE))
        contract["output"] = {"path": "vendor_sepolicy.cil", "sha256": vp.sha(expected), "size_bytes": len(expected)}
        result, receipt = vp.derive_corpus(corpus, contract)
        self.assertEqual(result, expected)
        self.assertEqual(len({row["start_byte"] for row in receipt["removals"]}), 3)

    def test_attribute_alias_role_attribute_and_boolean_closure_resolve(self):
        data = (
            b"(type a)(type b)(type c)(typeattribute x)(typeattribute y)"
            b"(typeattributeset x (or (a) (b)))(typeattributeset y (and (not (c)) (all)))"
            b"(typealias z)(typealiasactual z a)"
            b"(role r)(role object_r)(roleattribute rr)(roleattributeset rr (r))"
            b"(roletype rr x)"
        )
        p = vp.Policy(vp.parse(data))
        self.assertEqual(p.resolve("x"), {"a", "b"})
        self.assertEqual(p.resolve("x"), p.resolve("y"))
        self.assertEqual(p.resolve("z"), {"a"})
        self.assertEqual(p.role_bindings()["a"], {"r"})
        self.assertEqual(p.evaluate(("xor", ("a", "b"), ("b", "c")), p.resolve, p.types), {"a", "c"})

    def test_promotion_into_domain_or_role_r_fails(self):
        variants = (
            PLATFORM.replace(b"domain (proc server)", b"domain (proc server obj)"),
            PLATFORM + b"(roletype r obj)",
            PLATFORM.replace(b"(roletype object_r obj)", b""),
        )
        for platform in variants:
            with self.subTest(platform=platform[-40:]), self.assertRaises(vp.VendorPolicyError):
                vp.derive_corpus(*fixture(platform=platform))

    def test_mixed_empty_two_object_and_self_object_endpoints_fail(self):
        for replacement, extra in ((b"domain obj_202504", b""), (b"empty obj_202504", b"(typeattribute empty)"),
                                   (b"obj obj_202504", b""), (b"obj self", b"")):
            vendor = VENDOR_DATA.replace(b"proc obj_202504", replacement)
            with self.subTest(replacement=replacement), self.assertRaises(vp.VendorPolicyError):
                vp.derive_corpus(*fixture(platform=PLATFORM + extra, vendor=vendor))

    def test_unreviewed_non_domain_object_cannot_be_removed(self):
        platform = PLATFORM + b"(type other)(roletype object_r other)"
        vendor = VENDOR_DATA + b"(allow proc other (binder (call)))"
        with self.assertRaisesRegex(vp.VendorPolicyError, "singleton service"):
            vp.derive_corpus(*fixture(platform=platform, vendor=vendor))

    def test_rule_in_platform_cannot_be_removed(self):
        with self.assertRaisesRegex(vp.VendorPolicyError, "in vendor CIL"):
            vp.derive_corpus(*fixture(platform=PLATFORM + BAD_TARGET))

    def test_missing_duplicate_or_redefined_binder_assertion_fails(self):
        for platform in (PLATFORM.replace(TARGET_ASSERTION, b""), PLATFORM + TARGET_ASSERTION,
                         PLATFORM.replace(b"not_domain (not (domain))", b"not_domain (obj server)")):
            with self.subTest(platform=platform[-40:]), self.assertRaises(vp.VendorPolicyError):
                vp.derive_corpus(*fixture(platform=platform))

    def test_unknown_permission_extended_binder_and_conditional_fail(self):
        vendors = (
            VENDOR_DATA.replace(b"binder (call transfer)", b"binder (execute)"),
            VENDOR_DATA + b"(allowx proc obj (ioctl binder (0x1234)))",
            VENDOR_DATA + b"(booleanif flag (true (allow proc obj (binder (call)))))",
            VENDOR_DATA + b"(block hidden (allow proc obj (binder (call))))",
        )
        for vendor in vendors:
            with self.subTest(vendor=vendor[-80:]), self.assertRaises(vp.VendorPolicyError):
                vp.derive_corpus(*fixture(vendor=vendor))

    def test_cycle_unknown_type_and_conflicting_alias_fail(self):
        extras = (
            b"(typeattribute loop)(typeattributeset loop (loop))",
            b"(typeattribute loop)(typeattributeset loop (missing))",
            b"(typealiasactual obj_alias server)",
        )
        for extra in extras:
            with self.subTest(extra=extra), self.assertRaises(vp.VendorPolicyError):
                vp.derive_corpus(*fixture(platform=PLATFORM + extra))

    def test_input_bytes_and_order_are_bound_before_classification(self):
        corpus, contract = fixture()
        corpus[VENDOR] += b"; drift"
        with self.assertRaisesRegex(vp.VendorPolicyError, "input hash"):
            vp.derive_corpus(corpus, contract)
        corpus, contract = fixture()
        with self.assertRaisesRegex(vp.VendorPolicyError, "input order"):
            vp.derive_corpus(dict(reversed(list(corpus.items()))), contract)

    def test_aggregate_and_final_output_hash_mismatch_fail(self):
        corpus, contract = fixture()
        contract["expected"]["removed_occurrences"] = 2
        with self.assertRaisesRegex(vp.VendorPolicyError, "aggregate differs"):
            vp.derive_corpus(corpus, contract)
        corpus, contract = fixture()
        contract["output"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(vp.VendorPolicyError, "validated prototype"):
            vp.derive_corpus(corpus, contract)


class FilesystemTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.corpus_dir = self.root / "corpus"
        self.corpus_dir.mkdir()
        self.private = self.root / "artifacts"
        self.private.mkdir()
        self.corpus, self.contract = fixture()
        for runtime, data in self.corpus.items():
            path = self.corpus_dir / runtime.lstrip("/")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self.contract_file = self.root / "contract.json"
        self.contract_file.write_bytes(vp.encoded(self.contract))
        self.output = self.private / "derived"

    def stage(self, **options):
        with patch.object(vp, "WORKSPACE_ROOT", self.root), \
                patch.object(vp, "CONTRACT_SHA256", vp.sha(self.contract_file.read_bytes())):
            return vp.derive(self.corpus_dir, self.output, contract_path=self.contract_file, **options)

    def test_new_private_publication_rehashes_input_and_outputs(self):
        receipt = self.stage()
        self.assertEqual((self.output / "vendor_sepolicy.cil").read_bytes(), EXPECTED_VENDOR)
        self.assertEqual(json.loads((self.output / "receipt.json").read_bytes()), receipt)
        self.assertTrue(receipt["all_inputs_rehashed_unchanged"])
        self.assertTrue(receipt["output_readback_verified"])
        self.assertEqual((self.output / "vendor_sepolicy.cil").stat().st_mode & 0o777, 0o444)
        self.assertEqual((self.corpus_dir / VENDOR.lstrip("/")).read_bytes(), VENDOR_DATA)
        with self.assertRaisesRegex(vp.VendorPolicyError, "already exists"):
            self.stage()

    def test_symlink_input_and_parent_are_rejected(self):
        original = self.corpus_dir / VENDOR.lstrip("/")
        target = original.with_suffix(".original")
        original.rename(target)
        original.symlink_to(target)
        with self.assertRaisesRegex(vp.VendorPolicyError, "regular file"):
            self.stage()
        alias = self.root / "alias"
        alias.symlink_to(self.corpus_dir, target_is_directory=True)
        with self.assertRaisesRegex(vp.VendorPolicyError, "ancestor"):
            vp.real_directory(alias)
        self.assertFalse(self.output.exists())

    def test_unapproved_output_and_corpus_nesting_are_rejected(self):
        with patch.object(vp, "WORKSPACE_ROOT", self.root):
            for target in (self.root / "tracked", self.corpus_dir / "derived"):
                with self.subTest(target=target), self.assertRaises(vp.VendorPolicyError):
                    vp._destination(target, self.corpus_dir)
        with patch.object(vp, "WORKSPACE_ROOT", self.root / "virtual-package"), \
                self.assertRaisesRegex(vp.VendorPolicyError, "separate"):
            vp._destination(self.corpus_dir / "derived", self.corpus_dir,
                            private_output_root=self.corpus_dir)

    def test_external_sbox_root_and_explicit_tool_source_are_supported(self):
        external = self.root / "sbox"
        external.mkdir()
        self.output = external / "derived"
        # Simulate a packaged tool with a virtual source location outside sbox.
        with patch.object(vp, "WORKSPACE_ROOT", self.root / "virtual-package"), \
                patch.object(vp, "CONTRACT_SHA256", vp.sha(self.contract_file.read_bytes())):
            receipt = vp.derive(self.corpus_dir, self.output, contract_path=self.contract_file,
                                private_output_root=external, tool_source=ROOT / "scripts/vendor_policy.py")
        self.assertEqual(receipt["tool_sha256"], vp.sha((ROOT / "scripts/vendor_policy.py").read_bytes()))

    def test_explicit_private_root_cannot_turn_tracked_workspace_into_output(self):
        tracked = self.root / "tracked"
        tracked.mkdir()
        with patch.object(vp, "WORKSPACE_ROOT", self.root):
            for private in (self.root, tracked, Path("/")):
                with self.subTest(private=private), self.assertRaises(vp.VendorPolicyError):
                    vp._destination(tracked / "new", self.corpus_dir, private)

    def test_changed_source_and_existing_publication_race_leave_no_derived_output(self):
        path = self.corpus_dir / VENDOR.lstrip("/")
        original_recheck = vp.Reader.recheck

        def mutate(reader):
            path.write_bytes(path.read_bytes() + b"; changed")
            original_recheck(reader)

        with patch.object(vp.Reader, "recheck", mutate), self.assertRaises(vp.VendorPolicyError):
            self.stage()
        self.assertFalse(self.output.exists())
        self.assertEqual(list(self.private.iterdir()), [])

    def test_atomic_publication_refusal_preserves_other_task_output(self):
        def compete(staging, destination):
            destination.mkdir()
            (destination / "owner").write_bytes(b"other task")
            raise FileExistsError(destination)

        with patch.object(vp, "publish_new_directory", compete), self.assertRaises(FileExistsError):
            self.stage()
        self.assertEqual((self.output / "owner").read_bytes(), b"other task")
        self.assertEqual(list(self.private.iterdir()), [self.output])

    def test_copied_contract_must_match_immutable_reviewed_hash(self):
        self.contract_file.write_text('{"schema_version": 1}')
        with self.assertRaisesRegex(vp.VendorPolicyError, "SHA256 mismatch"):
            vp.load_contract(self.contract_file)


class PublicContractTests(unittest.TestCase):
    def test_public_contract_binds_prior_review_without_publishing_proprietary_rules(self):
        contract = vp.load_contract()
        review = json.loads((ROOT / "research/binder-policy-correction.json").read_text())
        self.assertEqual(len(contract["inputs"]), 10)
        self.assertEqual(contract["inputs"], [{key: row[key] for key in ("runtime_path", "sha256", "size_bytes")}
                                               for row in review["comparison"]["input_order"]])
        self.assertEqual(contract["output"]["sha256"], review["correction"]["derived_vendor_sha256"])
        self.assertEqual(contract["expected"]["removed_occurrences"], 67)
        self.assertEqual(contract["expected"]["removed_distinct_normalized_statements"], 65)
        self.assertEqual(contract["expected"]["neverallow_statements"]
                         + contract["expected"]["neverallowx_statements"], 6366)
        raw = (ROOT / "config/vendor-policy-correction.json").read_text()
        for forbidden in ("(allow ", "(neverallow ", "/Users/", "BEGIN PRIVATE KEY"):
            self.assertNotIn(forbidden, raw)
        self.assertLess(len(raw), 9000)


if __name__ == "__main__":
    unittest.main()
