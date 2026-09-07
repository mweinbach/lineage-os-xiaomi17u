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


class ChecksumConstructionSourceTests(unittest.TestCase):
    def setUp(self):
        from scripts import policy_inputs, target_files_metadata_checksum as checksum
        self.public_root = source.ROOT
        self.policy3, self.policy3_id = source.load_contract(source.ROOT / source.POLICY3_CONTRACT)
        self.original = source.load_contract()
        board = generator._policy_image_delivery_board((source.ROOT / source.BOARD).read_bytes())
        self.board = policy_inputs.factory_property_contexts_board(policy_inputs.camera_property_board(board))
        self.composition = checksum.compose_sources(source.ROOT, source_contract=checksum.SOURCE_CONTRACT)
        self.composition_id = source.metadata.identity(source.metadata.encoded(self.composition))
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        (self.root / "config").mkdir()
        for name in (source.CONTRACT, source.POLICY3_CONTRACT):
            (self.root / name).write_bytes((source.ROOT / name).read_bytes())
        self.path = self.root / source.CHECKSUM_CONTRACT
        self.contract = {**copy.deepcopy(self.policy3), "schema_version": 3,
                         "contract_id": source.CHECKSUM_CONTRACT_ID, "base_admission": None,
                         "selected_source_contract": copy.deepcopy(source.CHECKSUM_SOURCE_CONTRACT)}
        self.path.write_bytes(source.metadata.encoded(self.contract))
        for patch in (mock.patch.object(source, "ROOT", self.root),
                      # The maintained composer is independently tested. Freeze
                      # its real public output for these synthetic base fixtures.
                      mock.patch.object(checksum, "compose_sources", return_value=self.composition)):
            patch.start(); self.addCleanup(patch.stop)

    def fixture(self):
        files = {source.BOARD: self.board, "device/xiaomi/nezha/device.mk": b"# synthetic unrelated input\n"}
        native = {"project_commit": self.composition["project"]["commit"],
                  "files": self.composition["final_source_files"], "composition": self.composition,
                  "composition_identity": self.composition_id}
        plan = {"schema_version": 1, "profile": "synthetic-offline-fixture", "files": source.file_entries(files),
                "target_files_metadata": {"source_contract": copy.deepcopy(source.CHECKSUM_SOURCE_CONTRACT),
                    "native_source": copy.deepcopy(self.composition), "composition_identity": self.composition_id,
                    "policy_image_delivery": {"contract": copy.deepcopy(self.policy3["selected_policy_image_contract"])}},
                "mi_ext_inputs": {"native_source": copy.deepcopy(native)},
                "admission": {"complete_target_files_allowed": False, "flash_allowed": False}}
        contract = {**copy.deepcopy(self.contract), "base_admission": source.metadata.identity(source.metadata.encoded(plan))}
        return plan, files, contract

    def synthetic_binding(self, contract):
        raw = source.metadata.encoded(contract)
        self.path.write_bytes(raw)
        return mock.patch.object(source, "CHECKSUM_CONTRACT_SHA256", source.metadata.identity(raw)["sha256"])

    def test_checksum_public_binding_preserves_both_predecessors(self):
        with mock.patch.object(source, "ROOT", self.public_root):
            actual, _ = source.load_contract(self.public_root / source.CHECKSUM_CONTRACT)
            self.assertEqual(source.load_contract(), self.original)
            self.assertEqual(source.load_contract(self.public_root / source.POLICY3_CONTRACT), (self.policy3, self.policy3_id))
            self.assertNotEqual(actual["base_admission"], self.policy3["base_admission"])
            for name in set(self.policy3) - {"schema_version", "contract_id", "base_admission"}:
                self.assertEqual(actual[name], self.policy3[name], name)
            after = source.derive_board(self.board, self.public_root / source.CHECKSUM_CONTRACT)
            self.assertEqual(source.restore_board(after, self.public_root / source.CHECKSUM_CONTRACT), self.board)
            self.assertEqual(source.metadata.identity(source.render_guard()), self.policy3["guard"])

    def test_checksum_missing_actual_binding_stops_before_payload_or_process(self):
        class Unreadable(dict):
            def get(self, *args): raise AssertionError("pending plan inspected")
            def __getitem__(self, key): raise AssertionError("pending payload inspected")
        with mock.patch.object(source, "CHECKSUM_CONTRACT_SHA256", None), \
             mock.patch("subprocess.run", side_effect=AssertionError("native dispatch")):
            with self.assertRaisesRegex(source.ConstructionSourceError, "unbound"):
                source.apply(Unreadable(), Unreadable(), self.path)
        with self.synthetic_binding(self.contract):
            with self.assertRaisesRegex(source.ConstructionSourceError, "missing actual bindings"):
                source.apply(Unreadable(), Unreadable(), self.path)

    def test_checksum_synthetic_base_roundtrip_only_changes_board_and_guard(self):
        plan, files, contract = self.fixture()
        before = copy.deepcopy(plan), dict(files)
        with self.synthetic_binding(contract), mock.patch("subprocess.run", side_effect=AssertionError("native dispatch")):
            selected, payloads = source.apply(plan, files, self.path)
            self.assertEqual(source.validate(selected, payloads), plan)
            self.assertEqual(set(payloads) - set(files), {source.GUARD})
            self.assertEqual([name for name in files if files[name] != payloads[name]], [source.BOARD])
            self.assertEqual(selected["admission"], plan["admission"])
            self.assertEqual(payloads[source.GUARD], source.render_guard())
            with self.assertRaisesRegex(source.ConstructionSourceError, "selected twice"):
                source.apply(selected, payloads, self.path)
        self.assertEqual((plan, files), before)

    def test_checksum_descriptor_and_resealed_preserved_fields_are_closed(self):
        _, _, original = self.fixture()
        mutations = (
            lambda d: d.update(extra=True), lambda d: d.update(schema_version=True),
            lambda d: d["scope"].update(native_dispatch_allowed=True),
            lambda d: d["recorded_policy_basis"].update(source_files=545),
            lambda d: d["board_before"].update(size_bytes=4097),
            lambda d: d["selected_policy_image_contract"].update(sha256="0" * 64),
            lambda d: d["selected_source_contract"].update(path="patches/evolution/target-files-source-composition.json"),
            lambda d: d["base_admission"].update(size_bytes=True),
            lambda d: d.update(base_admission=copy.deepcopy(self.policy3["base_admission"])),
        )
        for mutate in mutations:
            contract = copy.deepcopy(original); mutate(contract)
            with self.subTest(mutate=mutate), self.synthetic_binding(contract):
                with self.assertRaises(source.ConstructionSourceError):
                    source.load_contract(self.path)
        with self.synthetic_binding(original):
            forged = self.root / "forged.json"
            forged.write_bytes(self.path.read_bytes() + b"\n")
            with self.assertRaisesRegex(source.ConstructionSourceError, "selector differs"):
                source.load_contract(forged)

    def test_checksum_resealed_source_selection_and_full_compositions_are_required(self):
        for kind in ("selector", "metadata", "metadata_identity", "mi_ext"):
            plan, files, contract = self.fixture()
            if kind == "selector":
                plan["target_files_metadata"]["source_contract"]["path"] = "patches/evolution/target-files-source-composition.json"
            elif kind == "metadata":
                plan["target_files_metadata"]["native_source"]["final_source_files"][0]["sha256"] = "0" * 64
            elif kind == "metadata_identity":
                plan["target_files_metadata"]["composition_identity"] = {"sha256": "0" * 64, "size_bytes": 1}
            else:
                plan["mi_ext_inputs"]["native_source"]["files"][0]["sha256"] = "0" * 64
            contract["base_admission"] = source.metadata.identity(source.metadata.encoded(plan))
            with self.subTest(kind=kind), self.synthetic_binding(contract):
                with self.assertRaisesRegex(source.ConstructionSourceError, "checksum complete base"):
                    source.apply(plan, files, self.path)

    def test_checksum_board_payload_and_plan_mutations_cannot_be_resealed(self):
        plan, files, contract = self.fixture()
        with self.synthetic_binding(contract):
            selected, payloads = source.apply(plan, files, self.path)
            for name in payloads:
                changed = {**payloads, name: payloads[name] + b"# mutation\n"}
                with self.subTest(name=name), self.assertRaises(source.ConstructionSourceError):
                    source.validate({**selected, "files": source.file_entries(changed)}, changed)
            with self.assertRaisesRegex(source.ConstructionSourceError, "complete exact selected base"):
                source.validate({**selected, "invented_native_success": True}, payloads)
            for board in (self.board + b"\n", self.board.replace(source.BLOCK, b""), self.board + source.BLOCK):
                with self.subTest(size=len(board)), self.assertRaises(source.ConstructionSourceError):
                    source.derive_board(board, self.path)
            with self.assertRaises(source.ConstructionSourceError):
                source.restore_board(payloads[source.BOARD] + b"\n", self.path)

    def test_checksum_selection_cannot_be_relabelled_as_a_predecessor(self):
        plan, files, contract = self.fixture()
        with self.synthetic_binding(contract):
            selected, payloads = source.apply(plan, files, self.path)
            for contract_id in (source.CONTRACT_ID, source.POLICY3_CONTRACT_ID, "unknown-successor"):
                changed = copy.deepcopy(selected)
                changed[source.BINDING]["contract_id"] = contract_id
                with self.subTest(contract_id=contract_id), self.assertRaises(source.ConstructionSourceError):
                    source.validate(changed, payloads)
            for path in (source.CONTRACT, source.POLICY3_CONTRACT):
                with self.subTest(path=path), self.assertRaises(source.ConstructionSourceError):
                    source.apply(plan, files, self.root / path)


class ModeFlagsConstructionSourceTests(ChecksumConstructionSourceTests):
    """Reuse the checksum source checks for the runtime-only BASE successor."""

    def setUp(self):
        super().setUp()
        # The new selector must validate the real bound checksum predecessor;
        # only its own descriptor digest is replaced for synthetic fixtures.
        self.path.write_bytes((self.public_root / source.CHECKSUM_CONTRACT).read_bytes())
        self.checksum, self.checksum_id = source.load_contract(self.path)
        self.path = self.root / source.MODE_FLAGS_CONTRACT
        self.contract = {**copy.deepcopy(self.checksum),
                         "contract_id": source.MODE_FLAGS_CONTRACT_ID, "base_admission": None}
        self.path.write_bytes(source.metadata.encoded(self.contract))

    def synthetic_binding(self, contract):
        raw = source.metadata.encoded(contract)
        self.path.write_bytes(raw)
        return mock.patch.object(source, "MODE_FLAGS_CONTRACT_SHA256", source.metadata.identity(raw)["sha256"])

    def test_checksum_public_binding_preserves_both_predecessors(self):
        with mock.patch.object(source, "ROOT", self.public_root):
            actual, _ = source.load_contract(self.public_root / source.MODE_FLAGS_CONTRACT)
            self.assertEqual(source.load_contract(), self.original)
            self.assertEqual(source.load_contract(self.public_root / source.POLICY3_CONTRACT), (self.policy3, self.policy3_id))
            self.assertEqual(source.load_contract(self.public_root / source.CHECKSUM_CONTRACT), (self.checksum, self.checksum_id))
            self.assertNotEqual(actual["base_admission"], self.checksum["base_admission"])
            self.assertEqual(set(actual), set(self.checksum))
            for name in set(self.checksum) - {"contract_id", "base_admission"}:
                self.assertEqual(actual[name], self.checksum[name], name)
            after = source.derive_board(self.board, self.public_root / source.MODE_FLAGS_CONTRACT)
            self.assertEqual(source.restore_board(after, self.public_root / source.MODE_FLAGS_CONTRACT), self.board)
            self.assertEqual(source.metadata.identity(source.render_guard()), self.checksum["guard"])

    def test_checksum_missing_actual_binding_stops_before_payload_or_process(self):
        class Unreadable(dict):
            def get(self, *args): raise AssertionError("pending plan inspected")
            def __getitem__(self, key): raise AssertionError("pending payload inspected")
        with mock.patch.object(source, "MODE_FLAGS_CONTRACT_SHA256", None), \
             mock.patch("subprocess.run", side_effect=AssertionError("native dispatch")):
            with self.assertRaisesRegex(source.ConstructionSourceError, "unbound"):
                source.apply(Unreadable(), Unreadable(), self.path)
        with self.synthetic_binding(self.contract):
            with self.assertRaisesRegex(source.ConstructionSourceError, "missing actual bindings"):
                source.apply(Unreadable(), Unreadable(), self.path)

    def test_mode_flags_checksum_base_and_selection_cannot_be_relabelled(self):
        plan, files, contract = self.fixture()
        reused = {**contract, "base_admission": copy.deepcopy(self.checksum["base_admission"])}
        with self.synthetic_binding(reused):
            with self.assertRaisesRegex(source.ConstructionSourceError, "separately measured complete base"):
                source.load_contract(self.path)
        with self.synthetic_binding(contract):
            selected, payloads = source.apply(plan, files, self.path)
            changed = copy.deepcopy(selected)
            changed[source.BINDING]["contract_id"] = source.CHECKSUM_CONTRACT_ID
            with self.assertRaises(source.ConstructionSourceError):
                source.validate(changed, payloads)
            with self.assertRaisesRegex(source.ConstructionSourceError, "complete exact selected base"):
                source.apply(plan, files, self.root / source.CHECKSUM_CONTRACT)


class AvbSha256ConstructionSourceTests(unittest.TestCase):
    """A selected Board-only successor, not a change to historical renderers."""

    def setUp(self):
        self.public_root = source.ROOT
        self.previous = {path: source.load_contract(self.public_root / path) for path in
                         (source.CONTRACT, source.POLICY3_CONTRACT,
                          source.CHECKSUM_CONTRACT, source.MODE_FLAGS_CONTRACT)}
        self.legacy_board = generator._policy_image_delivery_board(
            (self.public_root / source.BOARD).read_bytes())
        # Reuse the existing complete source-composition fixture without
        # inheriting tests whose checksum-specific base rule differs here.
        self.base_case = ChecksumConstructionSourceTests()
        self.addCleanup(self.base_case.doCleanups)
        self.base_case.setUp()
        self.root, self.board = self.base_case.root, self.base_case.board
        for path in (source.CHECKSUM_CONTRACT, source.MODE_FLAGS_CONTRACT, source.AVB_SHA256_CONTRACT):
            (self.root / path).write_bytes((self.public_root / path).read_bytes())
        self.path = self.root / source.AVB_SHA256_CONTRACT
        self.mode, _ = self.previous[source.MODE_FLAGS_CONTRACT]
        self.actual, self.actual_id = source.load_contract(self.path)
        self.old_final = self.board.replace(source.BLOCK, source.INCLUDE, 1)
        self.arguments = [f"BOARD_AVB_{name}_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256".encode()
                          for name in ("SYSTEM", "SYSTEM_EXT", "PRODUCT", "SYSTEM_DLKM", "VENDOR_DLKM")]

    def fixture(self):
        plan, files, _ = self.base_case.fixture()
        # Both contracts bind this same synthetic complete base. The live
        # descriptors and all native artifacts remain outside this fixture.
        previous = {**copy.deepcopy(self.mode),
                    "base_admission": source.metadata.identity(source.metadata.encoded(plan))}
        contract = {**copy.deepcopy(self.actual), "base_admission": previous["base_admission"]}
        return plan, files, previous, contract

    def synthetic_binding(self, previous, contract):
        stack = ExitStack()
        for path, value, constant in ((source.MODE_FLAGS_CONTRACT, previous, "MODE_FLAGS_CONTRACT_SHA256"),
                                      (source.AVB_SHA256_CONTRACT, contract, "AVB_SHA256_CONTRACT_SHA256")):
            raw = source.metadata.encoded(value)
            (self.root / path).write_bytes(raw)
            stack.enter_context(mock.patch.object(source, constant, source.metadata.identity(raw)["sha256"]))
        return stack

    def test_public_selector_preserves_all_four_previous_contracts_and_board_derivations(self):
        self.assertEqual(set(self.actual), set(self.mode))
        self.assertEqual(self.actual["contract_id"], source.AVB_SHA256_CONTRACT_ID)
        self.assertNotEqual(self.actual["board_after"], self.mode["board_after"])
        for field in set(self.mode) - {"contract_id", "board_after"}:
            self.assertEqual(self.actual[field], self.mode[field], field)
        self.assertEqual(source.load_contract(), self.previous[source.CONTRACT])
        for path, expected in self.previous.items():
            with self.subTest(selector=path):
                self.assertEqual(source.load_contract(self.root / path), expected)
                board = self.legacy_board if path == source.CONTRACT else self.board
                derived = source.derive_board(board, self.root / path)
                self.assertEqual(source.metadata.identity(derived), expected[0]["board_after"])
                self.assertEqual(source.restore_board(derived, self.root / path), board)
                self.assertNotIn(b"--hash_algorithm sha256", derived)
        self.assertEqual(source.metadata.identity(source.render_guard()), self.mode["guard"])

    def test_exact_five_hashtree_arguments_follow_all_existing_hooks_without_other_board_changes(self):
        derived = source.derive_board(self.board, self.path)
        self.assertEqual(source.metadata.identity(derived), self.actual["board_after"])
        self.assertTrue(derived.startswith(self.old_final))
        suffix = derived[len(self.old_final):]
        argument_lines = [line for line in suffix.splitlines() if line and not line.startswith(b"#")]
        self.assertEqual(argument_lines, self.arguments)
        self.assertEqual(derived.count(b"--hash_algorithm sha256"), 5)
        for line in self.arguments:
            self.assertGreater(derived.index(line), derived.rfind(b"include "))
        self.assertNotIn(b"BOARD_AVB_MI_EXT_", suffix)
        self.assertNotIn(b"BOARD_AVB_VENDOR_ADD_HASHTREE", suffix)
        self.assertNotIn(b"BOARD_AVB_ODM_", suffix)
        for protected in (b"--flags", b"--fec", b"--salt", b"KEY_PATH", b"ROLLBACK", b"SELINUX"):
            self.assertNotIn(protected, suffix)
        self.assertEqual(source.restore_board(derived, self.path), self.board)

    def test_same_complete_base_roundtrips_with_only_board_changed_and_guard_added(self):
        plan, files, previous, contract = self.fixture()
        before = copy.deepcopy(plan), dict(files)
        with self.synthetic_binding(previous, contract), \
             mock.patch("subprocess.run", side_effect=AssertionError("native dispatch")):
            selected, payloads = source.apply(plan, files, self.path)
            self.assertEqual(source.validate(selected, payloads), plan)
            self.assertEqual(set(payloads) - set(files), {source.GUARD})
            self.assertEqual([name for name in files if files[name] != payloads[name]], [source.BOARD])
            self.assertEqual(payloads[source.GUARD], source.render_guard())
            self.assertEqual(selected["admission"], plan["admission"])
            self.assertEqual(selected[source.BINDING]["base_admission"], previous["base_admission"])
            with self.assertRaises(source.ConstructionSourceError):
                source.apply(selected, payloads, self.path)
        self.assertEqual((plan, files), before)

    def test_missing_duplicate_conflicting_or_extra_board_arguments_cannot_be_resealed(self):
        plan, files, previous, contract = self.fixture()
        with self.synthetic_binding(previous, contract):
            selected, payloads = source.apply(plan, files, self.path)
            good = payloads[source.BOARD]
            changes = [good.replace(line + b"\n", b"", 1) for line in self.arguments]
            changes += [good + self.arguments[0] + b"\n",
                        good.replace(b"--hash_algorithm sha256", b"--hash_algorithm sha1", 1),
                        good + b"BOARD_AVB_SYSTEM_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha1\n",
                        good + b"BOARD_AVB_MI_EXT_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha256\n",
                        good.replace(self.arguments[0], self.arguments[0].replace(b" += ", b" := "), 1)]
            for changed in changes:
                with self.subTest(size=len(changed)):
                    with self.assertRaises(source.ConstructionSourceError):
                        source.restore_board(changed, self.path)
                    altered = {**payloads, source.BOARD: changed}
                    with self.assertRaises(source.ConstructionSourceError):
                        source.validate({**selected, "files": source.file_entries(altered)}, altered)
            for changed in (self.board + b"\n", self.board.replace(source.BLOCK, b""),
                            self.board + source.BLOCK, good):
                with self.subTest(preimage_size=len(changed)), self.assertRaises(source.ConstructionSourceError):
                    source.derive_board(changed, self.path)

    def test_resealed_descriptor_cannot_change_preserved_base_scope_or_source_contract(self):
        _, _, previous, original = self.fixture()
        mutations = (
            lambda d: d.update(extra=True), lambda d: d.update(schema_version=True),
            lambda d: d["base_admission"].update(sha256="0" * 64),
            lambda d: d["board_before"].update(size_bytes=1),
            lambda d: d["guard"].update(sha256="0" * 64),
            lambda d: d["scope"].update(native_dispatch_allowed=True),
            lambda d: d["context"].update(with_gms=False),
            lambda d: d["selected_source_contract"].update(path="unreviewed.json"),
            lambda d: d["selected_policy_image_contract"].update(sha256="0" * 64),
        )
        for mutate in mutations:
            contract = copy.deepcopy(original); mutate(contract)
            with self.subTest(mutation=mutate), self.synthetic_binding(previous, contract):
                with self.assertRaises(source.ConstructionSourceError):
                    source.load_contract(self.path)
        with self.synthetic_binding(previous, original):
            forged = self.root / "forged.json"
            forged.write_bytes(self.path.read_bytes() + b"\n")
            with self.assertRaises(source.ConstructionSourceError):
                source.load_contract(forged)

    def test_resealing_new_descriptor_after_pin_cannot_authorize_arbitrary_board_bytes(self):
        plan, files, previous, contract = self.fixture()
        bad = self.old_final + b"BOARD_AVB_SYSTEM_ADD_HASHTREE_FOOTER_ARGS += --hash_algorithm sha1\n"
        contract["board_after"] = source.metadata.identity(bad)
        with self.synthetic_binding(previous, contract), self.assertRaises(source.ConstructionSourceError):
            source.apply(plan, files, self.path)

    def test_complete_metadata_and_mi_ext_composition_guards_still_apply_to_new_selector(self):
        for kind in ("selector", "metadata", "metadata_identity", "mi_ext"):
            plan, files, previous, contract = self.fixture()
            if kind == "selector":
                plan["target_files_metadata"]["source_contract"]["path"] = "unreviewed.json"
            elif kind == "metadata":
                plan["target_files_metadata"]["native_source"]["final_source_files"][0]["sha256"] = "0" * 64
            elif kind == "metadata_identity":
                plan["target_files_metadata"]["composition_identity"] = {"sha256": "0" * 64, "size_bytes": 1}
            else:
                plan["mi_ext_inputs"]["native_source"]["files"][0]["sha256"] = "0" * 64
            previous["base_admission"] = contract["base_admission"] = source.metadata.identity(source.metadata.encoded(plan))
            with self.subTest(kind=kind), self.synthetic_binding(previous, contract):
                with self.assertRaisesRegex(source.ConstructionSourceError, "checksum complete base"):
                    source.apply(plan, files, self.path)

    def test_selected_payloads_cannot_be_relabelled_as_any_previous_selector(self):
        plan, files, previous, contract = self.fixture()
        with self.synthetic_binding(previous, contract):
            selected, payloads = source.apply(plan, files, self.path)
            for path, (old, _) in self.previous.items():
                changed = copy.deepcopy(selected)
                changed[source.BINDING]["contract_id"] = old["contract_id"]
                with self.subTest(selector=path), self.assertRaises(source.ConstructionSourceError):
                    source.validate(changed, payloads)

    def test_unbound_selector_fails_before_payload_inspection_or_native_calls(self):
        class Unreadable(dict):
            def get(self, *args): raise AssertionError("pending plan inspected")
            def __getitem__(self, key): raise AssertionError("pending payload inspected")
        with mock.patch.object(source, "AVB_SHA256_CONTRACT_SHA256", None), \
             mock.patch("subprocess.run", side_effect=AssertionError("native dispatch")):
            with self.assertRaisesRegex(source.ConstructionSourceError, "unbound"):
                source.apply(Unreadable(), Unreadable(), self.path)


if __name__ == "__main__":
    unittest.main()


class VariantOptInGuardTests(unittest.TestCase):
    """Tool behavior of the explicit build-variant opt-in successor."""

    def test_opt_in_guard_changes_only_the_variant_clause(self):
        base = source.render_guard().decode("ascii")
        derived = source.render_variant_opt_in_guard().decode("ascii")
        self.assertEqual(source.metadata.identity(derived.encode("ascii")), source.VARIANT_OPT_IN_GUARD_ID)
        self.assertEqual(derived, base.replace(source.USER_ONLY_CLAUSE, source.VARIANT_OPT_IN_CLAUSE, 1))
        self.assertNotIn(source.USER_ONLY_CLAUSE, derived)
        self.assertIn(source.VARIANT_OPT_IN_ENV, derived)
        self.assertNotIn("eng", source.VARIANT_OPT_IN_CLAUSE.split("$(error")[0])
        with mock.patch.object(source, "VARIANT_OPT_IN_CLAUSE", source.VARIANT_OPT_IN_CLAUSE.replace("userdebug/userdebug", "eng/eng")):
            with self.assertRaisesRegex(source.ConstructionSourceError, "guard changed"):
                source.render_variant_opt_in_guard()

    def test_contract_binds_predecessor_and_derived_guard(self):
        contract, identity = source.load_variant_opt_in_contract()
        self.assertEqual(identity["sha256"], source.VARIANT_OPT_IN_CONTRACT_SHA256)
        self.assertEqual(contract["predecessor"]["guard"], source.metadata.identity(source.render_guard()))
        self.assertEqual(contract["guard"], source.metadata.identity(source.render_variant_opt_in_guard()))
        self.assertEqual(contract["guard_path"], source.GUARD)
        self.assertFalse(contract["scope"]["flash_allowed"])
        with mock.patch.object(source, "VARIANT_OPT_IN_CONTRACT_SHA256", "0" * 64):
            with self.assertRaisesRegex(source.ConstructionSourceError, "contract changed"):
                source.load_variant_opt_in_contract()

    def test_environment_defaults_to_user_and_rejects_eng(self):
        self.assertEqual(source.variant_environment(), {"TARGET_BUILD_VARIANT": "user"})
        self.assertEqual(source.variant_environment("userdebug"),
                         {"TARGET_BUILD_VARIANT": "userdebug", source.VARIANT_OPT_IN_ENV: "userdebug"})
        for variant in ("eng", "", "USER", None):
            with self.subTest(variant=variant), self.assertRaisesRegex(source.ConstructionSourceError, "eng is not admitted"):
                source.variant_environment(variant)

    def test_host_make_admits_only_user_or_explicit_userdebug(self):
        import shutil
        import subprocess
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        with tempfile.TemporaryDirectory() as directory:
            makefile = Path(directory) / "guard.mk"
            makefile.write_bytes(source.VARIANT_OPT_IN_CLAUSE.encode("ascii") + b"all:\n\t@true\n")
            cases = ((["TARGET_BUILD_VARIANT=user"], 0), (["TARGET_BUILD_VARIANT=user", "NEZHA_BUILD_VARIANT_OPT_IN=userdebug"], 0),
                     (["TARGET_BUILD_VARIANT=userdebug", "NEZHA_BUILD_VARIANT_OPT_IN=userdebug"], 0),
                     (["TARGET_BUILD_VARIANT=userdebug"], 2), (["TARGET_BUILD_VARIANT=userdebug", "NEZHA_BUILD_VARIANT_OPT_IN=user"], 2),
                     (["TARGET_BUILD_VARIANT=eng", "NEZHA_BUILD_VARIANT_OPT_IN=eng"], 2), (["TARGET_BUILD_VARIANT=eng", "NEZHA_BUILD_VARIANT_OPT_IN=userdebug"], 2))
            for assignments, expected in cases:
                with self.subTest(assignments=assignments):
                    result = subprocess.run([make, "-s", "-f", str(makefile), *assignments], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
                    self.assertEqual(result.returncode, expected, result.stderr)
                    if expected:
                        self.assertIn("explicitly selects userdebug", result.stderr)


class VariantOptInMetadataSelectionTests(unittest.TestCase):
    """The userdebug opt-in also skips the prebuilt metadata delivery whose policy gate cannot pass."""

    PREDECESSOR = (source.METADATA_SELECTION_HEAD +
                   "BOARD_NEZHA_PREBUILT_METADATA := true\n"
                   "BOARD_NEZHA_PREBUILT_METADATA_RECEIPT_SHA256 := 79975bdb7d7cf41ea61181420fd1a17c97d72e574bc161edff272d5ef6ee0458\n"
                   "BOARD_NEZHA_PREBUILT_METADATA_TOOL_SHA256 := c4029700d44fc0273c5716aafd4bc0389aa236084baaddce8afbefedb8d2aff2\n").encode("ascii")

    def test_predecessor_pin_is_recomputed_from_the_delivered_selection(self):
        self.assertEqual(source.metadata.identity(self.PREDECESSOR), source.METADATA_SELECTION_BEFORE)

    def test_derivation_only_wraps_the_selection_in_the_opt_in_conditional(self):
        derived = source.derive_metadata_selection(self.PREDECESSOR)
        self.assertEqual(source.metadata.identity(derived), source.METADATA_SELECTION_AFTER)
        body = self.PREDECESSOR[len(source.METADATA_SELECTION_HEAD):]
        self.assertEqual(derived, (source.METADATA_SELECTION_HEAD + source.METADATA_SELECTION_EXCEPTION).encode("ascii") + body + b"endif\n")
        contract, _ = source.load_variant_opt_in_contract()
        self.assertEqual(contract["metadata_selection"]["after"], source.METADATA_SELECTION_AFTER)
        for changed in (self.PREDECESSOR + b"\n", self.PREDECESSOR.replace(b":= true", b":= false"), derived):
            with self.subTest(size=len(changed)), self.assertRaises(source.ConstructionSourceError):
                source.derive_metadata_selection(changed)

    def test_host_make_keeps_delivery_except_for_explicit_userdebug(self):
        import shutil
        import subprocess
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        with tempfile.TemporaryDirectory() as directory:
            makefile = Path(directory) / "selection.mk"
            makefile.write_bytes(source.derive_metadata_selection(self.PREDECESSOR) +
                                 b"all:\n\t@echo \"[$(BOARD_NEZHA_PREBUILT_METADATA)|$(BOARD_NEZHA_PREBUILT_METADATA_RECEIPT_SHA256)]\"\n")
            for assignments, expected in ((["TARGET_BUILD_VARIANT=user"], "[true|79975bdb"),
                                          (["TARGET_BUILD_VARIANT=userdebug"], "[true|79975bdb"),
                                          (["TARGET_BUILD_VARIANT=userdebug", "NEZHA_BUILD_VARIANT_OPT_IN=userdebug"], "[|]"),
                                          (["TARGET_BUILD_VARIANT=user", "NEZHA_BUILD_VARIANT_OPT_IN=userdebug"], "[true|79975bdb")):
                with self.subTest(assignments=assignments):
                    result = subprocess.run([make, "-s", "-f", str(makefile), *assignments], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertTrue(result.stdout.strip().startswith(expected), result.stdout)


class VariantOptInProductSelectionTests(unittest.TestCase):
    """The userdebug opt-in leaves PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG unset in Lineage's common config."""

    # The merged product predecessor is the tracked product makefile plus the September 6
    # merge's explicit candidate selection block inserted before the device inherit.
    MERGE_SELECTION = (b"# Explicit September 6 successor candidates; native/device qualification remains pending.\n"
                       b"NEZHA_CALIBRATED_DISPLAY := true\nNEZHA_DOLBY_CONTROLLER := true\nNEZHA_HAPTICS_CONTROLS := true\n"
                       b"NEZHA_CAMERA_TASK_PROFILES := true\nNEZHA_REFRESH_POLICY := true\nNEZHA_WORKLOAD_CLASSIFIER := false\n\n")

    def merged_product(self):
        tracked = (source.ROOT / source.PRODUCT_SELECTION).read_bytes()
        anchor = source.PRODUCT_SELECTION_ANCHOR.encode("ascii")
        self.assertEqual(tracked.count(anchor), 1)
        return tracked.replace(anchor, self.MERGE_SELECTION + anchor, 1)

    def test_product_restore_removes_only_the_ineffective_override(self):
        restored = self.merged_product()
        self.assertEqual(source.metadata.identity(restored), source.PRODUCT_SELECTION_RESTORED)
        anchor = source.PRODUCT_SELECTION_ANCHOR.encode("ascii")
        installed = restored.replace(anchor, source.PRODUCT_SELECTION_INEFFECTIVE_OVERRIDE.encode("ascii") + anchor, 1)
        self.assertEqual(source.metadata.identity(installed), source.PRODUCT_SELECTION_INEFFECTIVE)
        self.assertEqual(source.restore_product_selection(installed), restored)
        contract = source.load_variant_opt_in_contract()[0]
        self.assertEqual(contract["product_selection"]["installed"], source.PRODUCT_SELECTION_INEFFECTIVE)
        self.assertEqual(contract["product_selection"]["restored"], source.PRODUCT_SELECTION_RESTORED)
        for changed in (installed + b"\n", restored):
            with self.subTest(size=len(changed)), self.assertRaises(source.ConstructionSourceError):
                source.restore_product_selection(changed)

    def test_common_selection_wraps_only_the_assignment(self):
        raw = (source.ROOT / source.COMMON_SELECTION_SNAPSHOT).read_bytes()
        self.assertEqual(source.metadata.identity(raw), source.COMMON_SELECTION_BEFORE)
        derived = source.derive_common_selection(raw)
        self.assertEqual(source.metadata.identity(derived), source.COMMON_SELECTION_AFTER)
        assignment = source.COMMON_SELECTION_ASSIGNMENT.encode("ascii")
        self.assertEqual(derived, raw.replace(assignment, source.COMMON_SELECTION_EXCEPTION.encode("ascii"), 1))
        self.assertEqual(derived.count(b"PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG"), 1)
        self.assertEqual(source.load_variant_opt_in_contract()[0]["common_selection"]["after"], source.COMMON_SELECTION_AFTER)
        for changed in (raw + b"\n", derived, raw.replace(assignment, assignment * 2, 1)):
            with self.subTest(size=len(changed)), self.assertRaises(source.ConstructionSourceError):
                source.derive_common_selection(changed)

    def test_host_make_leaves_the_flag_unset_only_for_explicit_userdebug(self):
        import shutil
        import subprocess
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        # add_json_bool as defined in build/make/common/json.mk: any non-empty value is true,
        # which is why the earlier ":= false" override could not restore ro.debuggable=1.
        helper = b"json_bool = $(if $(strip $(1)),true,false)\n"
        with tempfile.TemporaryDirectory() as directory:
            makefile = Path(directory) / "common.mk"
            makefile.write_bytes(helper + source.COMMON_SELECTION_EXCEPTION.encode("ascii")
                                 + b"all:\n\t@echo \"[$(PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG)] $(call json_bool,$(PRODUCT_NOT_DEBUGGABLE_IN_USERDEBUG)) $(call json_bool,false)\"\n")
            for assignments, expected in ((["TARGET_BUILD_VARIANT=user"], "[true] true true"), (["TARGET_BUILD_VARIANT=userdebug"], "[true] true true"),
                                          (["TARGET_BUILD_VARIANT=userdebug", "NEZHA_BUILD_VARIANT_OPT_IN=userdebug"], "[] false true")):
                with self.subTest(assignments=assignments):
                    result = subprocess.run([make, "-s", "-f", str(makefile), *assignments], capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertEqual(result.stdout.strip(), expected)
