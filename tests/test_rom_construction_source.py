"""Offline source derivation boundaries; no private artifacts or native builds."""
import copy
from contextlib import ExitStack
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import generate_device_tree as generator
from scripts import rom_construction as inspection
from scripts import rom_construction_source as source


class RomConstructionSourceTests(unittest.TestCase):
    def setUp(self):
        self.contract, self.contract_id = source.load_contract()
        self.board = generator._policy_image_delivery_board((source.ROOT / source.BOARD).read_bytes())

    def fixture(self):
        # Only the base receipt is synthetic. The Board and guard are maintained
        # public bytes; no real source/native evidence is manufactured here.
        files = {source.BOARD: self.board, "device/xiaomi/nezha/device.mk": b"# synthetic unrelated source\n"}
        plan = {"schema_version": 1, "profile": "synthetic-offline-fixture", "files": source.file_entries(files),
                "admission": {"complete_target_files_allowed": False, "flash_allowed": False}}
        return plan, files

    def synthetic_binding(self, plan):
        stack = ExitStack()
        pin = source.metadata.identity(source.metadata.encoded(plan))
        contract = {**self.contract, "base_admission": pin}
        stack.enter_context(mock.patch.object(source, "BASE_ADMISSION", pin))
        stack.enter_context(mock.patch.object(source, "load_contract", return_value=(contract, self.contract_id)))
        return stack

    def test_contract_retains_separate_native_artifact_and_device_gates(self):
        scope = self.contract["scope"]
        self.assertTrue(scope["source_derivation_only"])
        for field in ("native_dispatch_allowed", "native_preflight_verified_by_generator",
                      "default_rom_super_ota_allowed", "complete_target_files_allowed",
                      "complete_input_compatibility_verified", "complete_rom_ready", "flash_allowed", "hardware_tested"):
            self.assertIs(scope[field], False)
        self.assertEqual(scope["phone_operations"], [])
        self.assertEqual(self.contract["recorded_source_installation"]["source_files"], 478)
        self.assertIn("plat_sepolicy_and_mapping.sha256", self.contract["required_native_preflight"])
        self.assertIn("one-uncovered-unlevelled-framework-matrix-definition-skip", self.contract["coverage_limits_retained"])
        self.assertEqual(inspection.inspect()["status"], "blocked")

    def test_changed_selector_and_resealed_readiness_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "contract.json"
            for field in ("complete_rom_ready", "native_dispatch_allowed", "default_rom_super_ota_allowed"):
                changed = copy.deepcopy(self.contract)
                changed["scope"][field] = True
                path.write_bytes(source.metadata.encoded(changed))
                with self.subTest(field=field), self.assertRaisesRegex(source.ConstructionSourceError, "selector differs"):
                    source.load_contract(path)

    def test_exact_board_transform_roundtrip_preserves_all_other_bytes(self):
        derived = source.derive_board(self.board)
        self.assertEqual(source.metadata.identity(derived), source.BOARD_AFTER)
        self.assertEqual(source.restore_board(derived), self.board)
        self.assertEqual(derived, self.board.replace(source.BLOCK, source.INCLUDE, 1))
        for changed in (self.board + b"\n", self.board.replace(source.BLOCK, b""), derived):
            with self.subTest(size=len(changed)), self.assertRaises(source.ConstructionSourceError):
                source.derive_board(changed)

    def test_guard_uses_post_release_flags_and_retains_other_restrictions(self):
        guard = source.render_guard()
        self.assertEqual(source.metadata.identity(guard), source.GUARD_ID)
        self.assertNotIn(b"TARGET_RELEASE", guard)
        for name, value in (("RELEASE_PLATFORM_VERSION", "BP4A"), ("RELEASE_PLATFORM_VERSION_CODENAME", "REL"),
                            ("RELEASE_PLATFORM_VERSION_LAST_STABLE", "16"), ("RELEASE_PLATFORM_SDK_VERSION", "36")):
            self.assertIn(f"ifneq ($({name}),{value})\n".encode(), guard)
        for marker in (b"$(origin NEZHA_FIRST_TARGET_FILES_CAPABILITY)", b"BOARD_AVB_ENABLE",
                       b"PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE", b"NEZHA_USE_PINNED_BUILD_DATETIME",
                       b"requires the sole target-files-package goal", b"superimage-nodeps", b"otapackage"):
            self.assertIn(marker, guard)
        with mock.patch.object(source, "GUARD_TEXT", source.GUARD_TEXT.replace("BOARD_AVB_ENABLE", "IGNORED")):
            with self.assertRaisesRegex(source.ConstructionSourceError, "guard changed"):
                source.render_guard()

    def test_unknown_base_cannot_use_a_valid_contract(self):
        plan, files = self.fixture()
        with self.assertRaisesRegex(source.ConstructionSourceError, "complete exact selected base"):
            source.apply(plan, files, source.ROOT / source.CONTRACT)

    def test_synthetic_base_derives_once_and_roundtrips_without_mutation(self):
        plan, files = self.fixture()
        before = copy.deepcopy(plan), dict(files)
        with self.synthetic_binding(plan), mock.patch("subprocess.run", side_effect=AssertionError("process dispatched")):
            selected, payloads = source.apply(plan, files, source.ROOT / source.CONTRACT)
            self.assertEqual(source.validate(selected, payloads), plan)
            self.assertEqual(selected["admission"], plan["admission"])
            self.assertEqual(payloads.keys() - files.keys(), {source.GUARD})
            with self.assertRaisesRegex(source.ConstructionSourceError, "selected twice"):
                source.apply(selected, payloads, source.ROOT / source.CONTRACT)
        self.assertEqual((plan, files), before)

    def test_resealing_any_unrelated_input_does_not_change_base_admission(self):
        plan, files = self.fixture()
        with self.synthetic_binding(plan):
            selected, payloads = source.apply(plan, files, source.ROOT / source.CONTRACT)
            for name in payloads:
                changed = {**payloads, name: payloads[name] + b"# changed\n"}
                resealed = {**selected, "files": source.file_entries(changed)}
                with self.subTest(name=name), self.assertRaises(source.ConstructionSourceError):
                    source.validate(resealed, changed)
            changed_plan = {**selected, "unreviewed_input_success": True}
            with self.assertRaisesRegex(source.ConstructionSourceError, "complete exact selected base"):
                source.validate(changed_plan, payloads)

    def test_removed_added_or_relabelled_guard_and_scope_are_rejected(self):
        plan, files = self.fixture()
        with self.synthetic_binding(plan):
            selected, payloads = source.apply(plan, files, source.ROOT / source.CONTRACT)
            for names in ({key: value for key, value in payloads.items() if key != source.GUARD},
                          {**payloads, "device/xiaomi/nezha/extra.mk": b"# extra\n"}):
                with self.assertRaises(source.ConstructionSourceError):
                    source.validate({**selected, "files": source.file_entries(names)}, names)
            for value in (True, 1, "true"):
                resealed = copy.deepcopy(selected)
                resealed[source.BINDING]["scope"]["complete_rom_ready"] = value
                with self.assertRaisesRegex(source.ConstructionSourceError, "admission differs"):
                    source.validate(resealed, payloads)

    def test_page_size_exception_is_exact_and_requires_explicit_selection(self):
        raw = source.render_guard()
        with self.assertRaises(generator.CandidateError):
            generator._page_size_source_guards({}, {source.GUARD: raw})
        selected = {source.BINDING: {"synthetic": True}, "page_size_profile": {}}
        generator._page_size_source_guards(selected, {source.GUARD: raw})
        for name, changed in ((source.GUARD, raw + b"# changed\n"),
                              ("device/xiaomi/nezha/another.mk", raw)):
            with self.subTest(name=name), self.assertRaises(generator.CandidateError):
                generator._page_size_source_guards(selected, {name: changed})

    def test_invalid_selection_stops_before_private_input_reads(self):
        with mock.patch.object(generator, "_load_records", side_effect=AssertionError("private inputs read")):
            with self.assertRaisesRegex(generator.CandidateError, "exact user, delivery"):
                generator.generate(Path("unused"), record_paths={}, kernel_receipt=Path("unused"),
                    vendor_receipt=Path("unused"), rom_construction_source_contract=source.ROOT / source.CONTRACT)

    def test_omission_does_not_read_or_apply_new_source_contract(self):
        with mock.patch.object(source, "load_contract", side_effect=AssertionError("implicit source selection")), \
             mock.patch.object(generator, "_load_records", side_effect=RuntimeError("normal base input route reached")):
            with self.assertRaisesRegex(RuntimeError, "normal base input route"):
                generator.generate(Path("unused"), record_paths={}, kernel_receipt=Path("unused"), vendor_receipt=Path("unused"))


class Policy3ConstructionSourceTests(unittest.TestCase):
    def setUp(self):
        from scripts import policy_inputs
        self.public_root = source.ROOT
        self.actual, self.actual_id = source.load_contract(source.ROOT / source.POLICY3_CONTRACT)
        self.old, self.old_id = source.load_contract()
        board = generator._policy_image_delivery_board((source.ROOT / source.BOARD).read_bytes())
        self.board = policy_inputs.factory_property_contexts_board(policy_inputs.camera_property_board(board))
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "config").mkdir()
        for name in (source.CONTRACT, source.POLICY3_CONTRACT):
            (self.root / name).write_bytes((source.ROOT / name).read_bytes())
        patch = mock.patch.object(source, "ROOT", self.root)
        patch.start(); self.addCleanup(patch.stop)
        self.path = self.root / source.POLICY3_CONTRACT

    def fixture(self, board=None):
        board = self.board if board is None else board
        image = copy.deepcopy(self.actual["selected_policy_image_contract"])
        files = {source.BOARD: board, "device/xiaomi/nezha/device.mk": b"# unrelated synthetic source\n"}
        plan = {"schema_version": 1, "profile": "synthetic-offline-fixture", "files": source.file_entries(files),
                "target_files_metadata": {"policy_image_delivery": {"contract": image}},
                "admission": {"complete_target_files_allowed": False, "flash_allowed": False}}
        contract = copy.deepcopy(self.actual)
        contract.update(base_admission=source.metadata.identity(source.metadata.encoded(plan)),
                        board_before=source.metadata.identity(board),
                        board_after=source.metadata.identity(board.replace(source.BLOCK, source.INCLUDE, 1)))
        return plan, files, contract

    def synthetic_binding(self, contract):
        raw = source.metadata.encoded(contract)
        self.path.write_bytes(raw)
        return mock.patch.object(source, "POLICY3_CONTRACT_SHA256", source.metadata.identity(raw)["sha256"])

    def test_policy3_actual_public_board_and_guard_preserve_default_scope(self):
        self.assertEqual(source.metadata.identity(self.board), self.actual["board_before"])
        after = source.derive_board(self.board, self.path)
        self.assertEqual(source.metadata.identity(after), self.actual["board_after"])
        self.assertEqual(source.restore_board(after, self.path), self.board)
        self.assertEqual(source.load_contract(), (self.old, self.old_id))
        self.assertEqual(source.metadata.identity(source.render_guard()), self.old["guard"])
        for key in ("scope", "context", "required_native_preflight", "coverage_limits_retained"):
            self.assertEqual(self.actual[key], self.old[key])

    def test_policy3_missing_bindings_fail_before_payload_or_process(self):
        class Unreadable(dict):
            def get(self, *args): raise AssertionError("pending plan inspected")
            def __getitem__(self, key): raise AssertionError("pending payload inspected")
        contract = copy.deepcopy(self.actual)
        for name in source.POLICY3_BINDINGS:
            contract[name] = None
        contract["selected_policy_image_contract"].update(sha256=None, size_bytes=None)
        with self.synthetic_binding(contract), mock.patch("subprocess.run", side_effect=AssertionError("native dispatch")):
            for action in (lambda: source.load_contract(self.path),
                           lambda: source.apply(Unreadable(), Unreadable(), self.path),
                           lambda: source.derive_board(b"unused", self.path)):
                with self.assertRaisesRegex(source.ConstructionSourceError, "missing actual bindings"):
                    action()

    def test_policy3_synthetic_complete_base_changes_only_board_and_guard(self):
        plan, files, contract = self.fixture()
        before = copy.deepcopy(plan), dict(files)
        with self.synthetic_binding(contract), mock.patch("subprocess.run", side_effect=AssertionError("native dispatch")):
            selected, payloads = source.apply(plan, files, self.path)
            self.assertEqual(source.validate(selected, payloads), plan)
            self.assertEqual(set(payloads) - set(files), {source.GUARD})
            self.assertEqual([name for name in files if files[name] != payloads[name]], [source.BOARD])
            self.assertEqual(selected["admission"], plan["admission"])
            with self.assertRaisesRegex(source.ConstructionSourceError, "selected twice"):
                source.apply(selected, payloads, self.path)
        self.assertEqual((plan, files), before)

    def test_policy3_resealed_context_scope_basis_or_identity_cannot_expand_selection(self):
        _, _, original = self.fixture()
        for mutate in (lambda d: d.update(extra=True), lambda d: d.update(schema_version=True),
                       lambda d: d["scope"].update(native_dispatch_allowed=True),
                       lambda d: d["context"].update(with_gms=1),
                       lambda d: d["recorded_policy_basis"].update(source_files=204),
                       lambda d: d["base_admission"].update(size_bytes=True),
                       lambda d: d["selected_policy_image_contract"].update(path="config/nezha-policy-image-delivery-v2.json")):
            contract = copy.deepcopy(original); mutate(contract)
            with self.subTest(mutate=mutate), self.synthetic_binding(contract):
                with self.assertRaises(source.ConstructionSourceError):
                    source.load_contract(self.path)

    def test_policy3_resealed_payload_or_plan_does_not_change_the_bound_base(self):
        plan, files, contract = self.fixture()
        with self.synthetic_binding(contract):
            selected, payloads = source.apply(plan, files, self.path)
            for name in payloads:
                changed = {**payloads, name: payloads[name] + b"# mutation\n"}
                with self.subTest(path=name), self.assertRaises(source.ConstructionSourceError):
                    source.validate({**selected, "files": source.file_entries(changed)}, changed)
            with self.assertRaisesRegex(source.ConstructionSourceError, "complete exact selected base"):
                source.validate({**selected, "invented_native_success": True}, payloads)

    def test_policy3_old_image_contract_cannot_be_relabelled_as_the_new_base(self):
        plan, files, contract = self.fixture()
        plan["target_files_metadata"]["policy_image_delivery"]["contract"]["contract_id"] = generator.POLICY_IMAGE_DELIVERY_4K_CONTRACT_ID
        contract["base_admission"] = source.metadata.identity(source.metadata.encoded(plan))
        with self.synthetic_binding(contract), self.assertRaisesRegex(source.ConstructionSourceError, "different image delivery contract"):
            source.apply(plan, files, self.path)

    def test_policy3_exact_board_block_and_default_selector_remain_closed(self):
        for board in (self.board + source.BLOCK, self.board.replace(source.BLOCK, b""), self.board + source.INCLUDE):
            plan, files, contract = self.fixture(board)
            with self.subTest(size=len(board)), self.synthetic_binding(contract):
                with self.assertRaisesRegex(source.ConstructionSourceError, "exact future delivery Board"):
                    source.apply(plan, files, self.path)
        with self.assertRaises(source.ConstructionSourceError):
            source.derive_board(self.board)


if __name__ == "__main__":
    unittest.main()
