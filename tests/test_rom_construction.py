"""Offline construction admission boundaries; no native or hardware success fixtures."""

import copy
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import generate_device_tree as generator
from scripts import rom_construction as construction


class RomConstructionTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.identity = construction.load_contract()
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()

    def write(self, value):
        path = self.root / "construction.json"
        path.write_bytes(construction.metadata.encoded(value))
        return path

    def test_plan_keeps_actual_missing_roles_distinct_from_existing_component_basis(self):
        result = construction.inspect()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["missing_selected_input_roles"], list(construction.ROLES))
        self.assertIn("full_vintf_native_result", result["missing_selected_input_roles"])
        self.assertIn("necessary_vintf_coverage", result["missing_selected_input_roles"])
        self.assertEqual(set(result["available_basis"]), construction.BASIS)
        self.assertFalse(result["available_basis_is_selected_input_admission"])
        self.assertEqual(result["basis_identities_verified"], {})
        self.assertFalse(result["scope"]["native_goal_dispatch_allowed"])

    def test_default_plan_does_not_open_private_evidence_or_dispatch_processes(self):
        original = construction.metadata.Reader.read
        opened = []
        def read(reader, path, *args, **kwargs):
            opened.append(Path(path))
            return original(reader, path, *args, **kwargs)
        with mock.patch.object(construction.metadata.Reader, "read", read), \
                mock.patch("subprocess.run", side_effect=AssertionError("process dispatched")):
            construction.inspect("ota")
        # Reader's terminal recheck reads the same public control again.
        self.assertEqual(opened, [construction.ROOT / construction.CONTRACT] * 2)

    def test_signed_final_artifacts_are_not_target_files_input_prerequisites(self):
        target = construction.inspect("target-files")
        self.assertFalse(any("signed" in role or "boot" in role or "physical" in role
                             for role in target["missing_selected_input_roles"]))
        self.assertIn("final-image-avb-signing-and-complete-descriptor-chain", target["downstream_only"])
        self.assertIn("final-installed-apk-inventory-and-strict-treble-labeling", target["required_artifact_checks"])

    def test_super_and_ota_add_their_own_real_input_roles_without_admitting_dispatch(self):
        for phase, (goal, additional) in construction.PHASES.items():
            with self.subTest(phase=phase):
                result = construction.inspect(phase)
                self.assertEqual(result["ordinary_goal"], goal)
                self.assertEqual(result["missing_selected_input_roles"], [*construction.ROLES, *additional])
                self.assertFalse(result["scope"]["native_goal_dispatch_allowed"])

    def test_ordinary_goal_cannot_be_replaced_by_nodeps_raw_path_or_other_alias(self):
        for goal in ("superimage-nodeps", "bacon", "droid", "out/target/product/nezha/system.img", ""):
            changed = copy.deepcopy(self.contract)
            changed["phases"]["super"]["ordinary_goal"] = goal
            with self.subTest(goal=goal), self.assertRaisesRegex(construction.ConstructionError, "ordinary phase target"):
                construction._schema(changed)

    def test_coverage_limits_cannot_be_removed_or_flipped(self):
        for name in construction.COVERAGE:
            for value in (False, 1, None):
                changed = copy.deepcopy(self.contract)
                changed["vintf_coverage_requirements"][name] = value
                with self.subTest(name=name, value=value), self.assertRaisesRegex(construction.ConstructionError, "coverage limits"):
                    construction._schema(changed)

    def test_outer_pass_or_user_supplied_receipt_cannot_bind_an_unreviewed_role(self):
        for role in construction.ROLES:
            for claimed in ({"passed": True}, {"complete_input_compatibility_verified": True},
                            {"sha256": "a" * 64, "size_bytes": 10}, True, "passed"):
                changed = copy.deepcopy(self.contract)
                changed["required_selected_input_roles"][role] = claimed
                with self.subTest(role=role, claimed=claimed), self.assertRaisesRegex(construction.ConstructionError, "no reviewed selected-input"):
                    construction._schema(changed)

    def test_readiness_and_phone_scope_cannot_be_promoted(self):
        for flag in ("native_goal_dispatch_allowed", "framework_target_guards_changed",
                     "complete_target_files_allowed", "complete_rom_ready", "flash_allowed", "hardware_tested"):
            for value in (True, 0):
                changed = copy.deepcopy(self.contract)
                changed["scope"][flag] = value
                with self.subTest(flag=flag, value=value), self.assertRaisesRegex(construction.ConstructionError, "promote dispatch"):
                    construction._schema(changed)
        changed = copy.deepcopy(self.contract)
        changed["scope"]["phone_operations"] = ["flash"]
        with self.assertRaisesRegex(construction.ConstructionError, "promote dispatch"):
            construction._schema(changed)

    def test_product_release_and_page_size_are_not_inferred(self):
        for field, value in (("product", "lineage_other"), ("variant", "userdebug"), ("branch", "cage"),
                             ("release_config", "bp4b"), ("shipping_api_level", "36"), ("maximum_page_size_bytes", 16384)):
            changed = copy.deepcopy(self.contract)
            changed["context"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(construction.ConstructionError, "exact Nezha"):
                construction._schema(changed)

    def test_reproducibility_does_not_invent_an_epoch_or_select_0012(self):
        result = construction.inspect()
        self.assertEqual(result["reproducibility"], construction.REPRODUCIBILITY)
        for field, value in (("selected", True), ("manifest_epoch_evidence", {"epoch": 0}),
                             ("changes_current_packaging_composition", True)):
            changed = copy.deepcopy(self.contract)
            changed["reproducibility"][field] = value
            with self.subTest(field=field), self.assertRaisesRegex(construction.ConstructionError, "separately qualified 0012"):
                construction._schema(changed)

    def test_changed_canonical_contract_is_not_trusted_even_when_selected_by_default(self):
        path = self.root / construction.CONTRACT
        path.parent.mkdir(parents=True)
        path.write_bytes(construction.metadata.encoded(self.contract) + b"\n")
        with mock.patch.object(construction, "ROOT", self.root), self.assertRaisesRegex(construction.ConstructionError, "maintained construction contract changed"):
            construction.load_contract()

    def test_resealed_external_contract_does_not_replace_public_controls(self):
        changed = copy.deepcopy(self.contract)
        changed["status"] = "admitted"
        with self.assertRaisesRegex(construction.ConstructionError, "differs from the maintained"):
            construction.load_contract(self.write(changed))

    def test_exact_external_copy_is_accepted_only_as_an_unbound_plan(self):
        path = self.root / "copy.json"
        path.write_bytes((construction.ROOT / construction.CONTRACT).read_bytes())
        result = construction.inspect(contract_path=path)
        self.assertEqual(result["status"], "blocked")
        with self.assertRaisesRegex(construction.ConstructionError, "unbound selected-input roles"):
            construction.require_admission(path)

    def test_linked_contract_is_refused(self):
        path = self.root / "linked.json"
        path.symlink_to(construction.ROOT / construction.CONTRACT)
        with self.assertRaises(construction.metadata.TargetFilesMetadataError):
            construction.load_contract(path)

    def test_missing_available_evidence_is_not_a_success_or_skip(self):
        with self.assertRaises(FileNotFoundError):
            construction.inspect(evidence_root=self.root)

    def test_plan_and_check_exit_codes_distinguish_inspection_from_admission(self):
        for command, expected in (("plan", 0), ("check", 2)):
            with self.subTest(command=command), redirect_stdout(io.StringIO()) as stream:
                code = construction.main([command, "--phase", "ota"])
                self.assertEqual(code, expected)
                self.assertEqual(json.loads(stream.getvalue())["status"], "blocked")

    def test_generator_rejects_explicit_construction_before_reading_private_inputs(self):
        output = self.root / "must-not-exist"
        with mock.patch.object(generator, "_load_records", side_effect=AssertionError("records opened")), \
                mock.patch.object(generator, "_bind_bundles", side_effect=AssertionError("private inputs opened")), \
                self.assertRaisesRegex(generator.CandidateError, "full_vintf_native_result.*necessary_vintf_coverage"):
            generator.generate(output, record_paths={}, kernel_receipt=None, vendor_receipt=None,
                               rom_construction_contract=construction.ROOT / construction.CONTRACT)
        self.assertFalse(output.exists())

    def test_generator_cli_does_not_implicitly_select_construction(self):
        for selected in (False, True):
            args = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json", "--output", "candidate"]
            if selected:
                args += ["--rom-construction-contract", "construction.json"]
            with self.subTest(selected=selected), mock.patch.object(generator, "generate", return_value={}) as generate, \
                    redirect_stdout(io.StringIO()):
                self.assertEqual(generator.main(args), 0)
                self.assertEqual(generate.call_args.kwargs["rom_construction_contract"],
                                 Path("construction.json") if selected else None)

    def test_generator_cli_reports_blocked_without_publishing_candidate(self):
        output = self.root / "candidate"
        with redirect_stderr(io.StringIO()) as errors, redirect_stdout(io.StringIO()) as stream:
            result = generator.main(["generate", "--kernel-receipt", "absent-kernel.json", "--vendor-receipt", "absent-vendor.json",
                                     "--rom-construction-contract", str(construction.ROOT / construction.CONTRACT), "--output", str(output)])
        self.assertEqual(result, 1)
        self.assertIn("construction admission blocked", errors.getvalue())
        self.assertEqual(stream.getvalue(), "")
        self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
