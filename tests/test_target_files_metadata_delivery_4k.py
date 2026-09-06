"""Offline 4 KiB delivery tests; inert fixtures are not native ROM evidence."""

import copy
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import target_files_metadata_delivery_4k as m
from support import write_file as write
from tests import test_target_files_metadata_delivery as historical_tests


class DescriptorTests(unittest.TestCase):
    def setUp(self):
        self.admission = json.loads((m.ROOT / m.IMAGE_CONTRACT).read_bytes())
        self.basis = json.loads((m.ROOT / m.BASIS_CONTRACT).read_bytes())
        self.historical = json.loads((m.ROOT / m.V2_CONTRACT).read_bytes())
        self.composition = self.admission["source_composition"]

    def test_new_selectors_are_explicit_and_historical_views_are_exact(self):
        self.assertEqual("config/nezha-policy-image-delivery-v2.json", m.IMAGE_CONTRACT)
        self.assertEqual("config/nezha-policy-image-delivery-basis-v2.json", m.BASIS_CONTRACT)
        self.assertEqual(3, self.admission["schema_version"])
        self.assertEqual(2, self.basis["schema_version"])
        before = copy.deepcopy(self.admission)
        self.assertEqual((m.ROOT / m.BASIS_CONTRACT).read_bytes(), m.encoded(m._basis_view(self.admission)))
        self.assertEqual((m.ROOT / m.V2_CONTRACT).read_bytes(), m.encoded(m._historical_view(self.admission)))
        self.assertEqual(before, self.admission)
        self.assertEqual(m.BASIS_ID, m.identity(m.encoded(self.basis)))
        self.assertEqual(m.V2_CONTRACT_ID, m.identity(m.encoded(self.historical)))

    def test_original_images_metadata_policy_source_and_copy_keep_their_meanings(self):
        for field in ("original_images", "packaged_images", "metadata_members", "source_composition",
                      "expected_root_descriptors", "policy_inputs", "delivery_proof", "selected_delivery_evidence", "scope"):
            with self.subTest(field=field):
                self.assertEqual(self.historical[field], self.admission[field])
        self.assertEqual(205, len(self.admission["metadata_members"]))
        self.assertEqual(6460780, sum(row["payload"]["size_bytes"] for row in self.admission["metadata_members"]))
        self.assertEqual(10, len(self.composition["final_source_files"]))
        self.assertEqual("dd11cdbee4b5d9193dfeb875ff2bfbfd5410cc4e2de14213577b386545b4c4ab",
                         self.admission["selected_delivery_evidence"]["sha256"])
        self.assertTrue(all(value is False for value in self.admission["scope"].values()))

    def test_new_and_historical_descriptors_are_not_interchangeable(self):
        for value in (self.historical, self.basis):
            with self.subTest(contract=value["contract_id"]), self.assertRaisesRegex(ValueError, "unknown explicit 4 KiB"):
                m._basis_view(value)
        with self.assertRaisesRegex(ValueError, "unknown explicit v2"):
            m._v2._validate_admission(self.admission, self.composition)
        with self.assertRaisesRegex(ValueError, "unknown image admission"):
            m._v2._v1._validate_admission(self.basis, self.composition)

    def test_unknown_fields_schema_aliases_and_missing_context_fail(self):
        for change in (lambda d: d.update(schema_version=True), lambda d: d.update(schema_version=3.0),
                       lambda d: d.update(contract_id="unselected"), lambda d: d.update(extra=True),
                       lambda d: d.pop("page_size_context"), lambda d: d.pop("historical_delivery_admission")):
            altered = copy.deepcopy(self.admission)
            change(altered)
            with self.subTest(change=change), self.assertRaises(ValueError):
                m._basis_view(altered)

    def test_inverse_basis_rejects_changed_immutable_inputs(self):
        changes = (
            lambda d: d["original_images"]["vendor"].update(sha256="0" * 64),
            lambda d: d["packaged_images"]["odm"].update(size_bytes=1),
            lambda d: d["metadata_members"][0]["payload"].update(sha256="0" * 64),
            lambda d: d["metadata_members"].pop(),
            lambda d: d["metadata_members"].reverse(),
            lambda d: d["source_composition"]["final_source_files"][0].update(sha256="0" * 64),
            lambda d: d["policy_inputs"]["actual_compiler_inputs"][0].update(resolved_path="/work/other/policy.cil"),
            lambda d: d["policy_inputs"]["exact_five_replacement_identities"]["odm"]["/etc/selinux/precompiled_sepolicy"].update(size_bytes=1),
            lambda d: d["expected_root_descriptors"]["vendor"].update(partition="odm"),
            lambda d: d["delivery_proof"].update(sha256="0" * 64),
            lambda d: d["scope"].update(complete_rom_ready=True),
            lambda d: d["historical_delivery_admission"].update(path="config/another.json"),
        )
        for index, change in enumerate(changes):
            altered = copy.deepcopy(self.admission)
            change(altered)
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "reviewed page/image basis"):
                m._basis_view(altered)

    def test_selected_copy_still_must_reconstruct_the_exact_historical_delivery(self):
        altered = copy.deepcopy(self.admission)
        altered["selected_delivery_evidence"]["sha256"] = "0" * 64
        # The page/image basis excludes copy selection; the historical view binds it.
        self.assertEqual(self.basis, m._basis_view(altered))
        with self.assertRaisesRegex(ValueError, "historical images, metadata, source or copy"):
            m._historical_view(altered)

    def test_historical_current_evidence_cannot_be_relabelled(self):
        altered = copy.deepcopy(self.admission)
        altered["historical_current_policy_evidence"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "historical current-policy identity differs"):
            m._validate_admission(altered, self.composition)

    def test_page_context_matches_the_public_authorized_profile(self):
        context = self.admission["page_size_context"]
        self.assertEqual(m.PAGE_CONTEXT, context)
        profile_raw = (m.ROOT / context["profile"]["path"]).read_bytes()
        self.assertEqual(m.expected(context["profile"]), m.identity(profile_raw))
        profile = json.loads(profile_raw)
        self.assertEqual("nezha-stock-4k-bringup-v2", context["profile_id"])
        self.assertEqual(profile["profile_id"], context["profile_id"])
        self.assertEqual(profile["product_settings"], context["product_settings"])
        self.assertEqual({"PRODUCT_MAX_PAGE_SIZE_SUPPORTED": 4096, "PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE": True,
                          "PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO": True}, context["product_settings"])
        self.assertEqual("device/xiaomi/nezha/generated/device-candidate.mk", context["source_product"]["path"])
        self.assertEqual("d336169a8f683bd798bb63360fbc62ee9ebdc03343e2f7ab91906052cde568a9", context["source_product"]["sha256"])
        self.assertEqual("392485b8ef5005f6d8079487c7a8ee7931597bacaab593478277f8201c4d03a2", context["source_candidate"]["sha256"])

    def test_page_profile_product_candidate_and_boolean_alias_changes_fail(self):
        changes = (
            lambda d: d["profile"].update(path="config/nezha-page-size-profile.json"),
            lambda d: d["profile"].update(sha256="0" * 64),
            lambda d: d.update(profile_id="another-profile"),
            lambda d: d["source_candidate"].update(sha256="0" * 64),
            lambda d: d["source_product"].update(path="device/xiaomi/nezha/device.mk"),
            lambda d: d["source_product"].update(sha256="0" * 64),
            lambda d: d["product_settings"].update(PRODUCT_MAX_PAGE_SIZE_SUPPORTED=16384),
            lambda d: d["product_settings"].update(PRODUCT_MAX_PAGE_SIZE_SUPPORTED=4096.0),
            lambda d: d["product_settings"].update(PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE=1),
            lambda d: d["product_settings"].update(PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO=False),
            lambda d: d.update(runtime_verified=True),
        )
        for index, change in enumerate(changes):
            altered = copy.deepcopy(self.admission)
            change(altered["page_size_context"])
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "reviewed page/image basis"):
                m._validate_admission(altered, self.composition)

    def test_missing_current_evidence_has_no_boolean_or_historical_override(self):
        # Selecting the missing-pin state exercises refusal only. No successful
        # 4 KiB evidence or permissive validator is supplied by this fixture.
        with mock.patch.object(m, "CURRENT_REPORT_ID", None):
            for value in (None, True, {}, {"passed": True}, m.HISTORICAL_CURRENT_ID):
                altered = copy.deepcopy(self.admission)
                altered["current_policy_build_evidence"] = value
                with self.subTest(value=value), self.assertRaisesRegex(ValueError, "not yet bound"):
                    m._validate_admission(altered, self.composition)
            for raw in (b"", b"{}\n", b'{"passed":true,"requested_goal_count":37}\n'):
                with self.subTest(raw=raw), self.assertRaisesRegex(ValueError, "not yet bound"):
                    m._validate_current(raw, self.admission, {}, {})

    def test_pending_policy_gate_reads_no_target_files(self):
        reader = mock.Mock(spec=m.Reader)
        reader.read.side_effect = AssertionError("pending current proof cannot read packaging inputs")
        with mock.patch.object(m, "CURRENT_REPORT_ID", None), self.assertRaisesRegex(ValueError, "not yet bound"):
            m._policy_gate(self.admission, Path("/nonexistent/target-files"), reader, {})
        reader.read.assert_not_called()

    def test_missing_delivery_evidence_cannot_reach_current_validation(self):
        with mock.patch.object(m, "_validate_current", side_effect=AssertionError("missing proof must fail first")):
            with self.assertRaisesRegex(ValueError, "delivery proof differs"):
                m._validate_evidence(b"", b"", self.admission, b"", b"")

    def test_old_or_incomplete_packaged_result_cannot_publish_a_report(self):
        for result in (None, {}, {"operation": "verify-actual-packaged-v13i-policy-v2",
                                 "seven_actual_framework_inputs_verified": True,
                                 "three_actual_framework_sidecars_recomputed": True},
                       {"operation": "verify-actual-packaged-4k-policy-v3",
                        "seven_actual_framework_inputs_verified": True}):
            reader = mock.Mock(current_policy_result=result)
            with self.subTest(result=result), self.assertRaisesRegex(ValueError, "before metadata publication"):
                m._installation_report({}, "0" * 64, reader)


class BootstrapAndControlTests(unittest.TestCase):
    def controls(self):
        return {name: (m.ROOT / name).read_bytes() for name in m.CONTROL_TOOLS}

    def test_maintained_source_closure_and_predecessor_namespaces_are_separate(self):
        self.assertEqual((*m._v2.CONTROL_TOOLS, "scripts/target_files_metadata_delivery_4k.py"), m.CONTROL_TOOLS)
        self.assertEqual(5, len(m.CONTROL_TOOLS))
        self.assertTrue(all(path.startswith("scripts/") for path in m.CONTROL_TOOLS))
        self.assertEqual(m.V2_SOURCE_ID, m.identity((m.ROOT / m.V2_ADAPTER).read_bytes()))
        self.assertEqual(m.V2_RUNTIME_ID, m.identity(m._runtime_v2))
        self.assertIsNot(m._impl, m._v2._impl)
        self.assertIsNot(m._install_namespace, m._v2._install_namespace)
        self.assertEqual(m._v2._install_namespace["install"].__code__.co_code,
                         m._install_namespace["install"].__code__.co_code)

    def test_native_assembly_is_deterministic_self_contained_and_refuses_missing_pin(self):
        raw = m.runtime_tool_payloads(self.controls())["tools/target_files_metadata.py"]
        self.assertEqual(raw, m.runtime_tool_payloads(self.controls())["tools/target_files_metadata.py"])
        namespace = {"__name__": "fourk_native_probe", "__file__": "/nonexistent/bundle/tools/target_files_metadata.py"}
        with mock.patch("os.open", side_effect=AssertionError("native bootstrap cannot read adjacent code")):
            exec(compile(raw, "<native-4k-delivery>", "exec"), namespace)
        self.assertTrue(namespace["NATIVE"])
        self.assertEqual(m.CURRENT_REPORT_ID, namespace["CURRENT_REPORT_ID"])
        self.assertEqual(m.V2_RUNTIME_ID, m.identity(namespace["_runtime_v2"]))
        admission = json.loads((m.ROOT / m.IMAGE_CONTRACT).read_bytes())
        self.assertEqual(m._basis_view(admission), namespace["_basis_view"](admission))
        self.assertEqual(m._historical_view(admission), namespace["_historical_view"](admission))
        with self.assertRaisesRegex(ValueError, "actual current 4 KiB policy report differs"):
            namespace["_validate_current"](b"{}\n", admission, {}, {})
        with mock.patch.dict(namespace, {"CURRENT_REPORT_ID": None}), self.assertRaisesRegex(ValueError, "not yet bound"):
            namespace["_validate_current"](b"", {}, {}, {})

    def test_each_missing_or_changed_predecessor_control_fails_assembly(self):
        for name in m.CONTROL_TOOLS:
            controls = self.controls()
            del controls[name]
            with self.subTest(missing=name), self.assertRaisesRegex(ValueError, "controls missing"):
                m.runtime_tool_payloads(controls)
        for name in m._v2.CONTROL_TOOLS:
            controls = self.controls()
            controls[name] += b"\n# unreviewed predecessor\n"
            with self.subTest(changed=name), self.assertRaises(ValueError):
                m.runtime_tool_payloads(controls)

    def test_current_extension_requires_bounded_bytes(self):
        for raw in (b"", "not bytes", b"x" * ((2 << 20) + 1)):
            controls = self.controls()
            controls[m.ADAPTER] = raw
            with self.subTest(kind=type(raw).__name__, size=len(raw)), self.assertRaisesRegex(ValueError, "bounded maintained"):
                m.runtime_tool_payloads(controls)

    def test_hash_and_single_terminal_main_are_checked_before_body_use(self):
        with self.assertRaisesRegex(ValueError, "identity differs"):
            m._strip_main(m._runtime_v2 + b"\n", m.V2_RUNTIME_ID)
        for altered in (m._runtime_v2[:-len(m.MAIN)], m._runtime_v2 + m.MAIN):
            with self.subTest(size=len(altered)), self.assertRaisesRegex(ValueError, "terminal main"):
                m._strip_main(altered, m.identity(altered))
        with mock.patch.dict(m.TRANSFORMS, {"_receipt": [("absent source preimage", "replacement")]}):
            with self.assertRaisesRegex(ValueError, "preimage differs"):
                m._function_definitions()

    def test_bootstrap_refuses_symlink_hardlink_and_changed_source(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            original, alias = root / "source.py", root / "alias.py"
            original.write_bytes(b"bounded source")
            wanted = m.identity(original.read_bytes())
            alias.symlink_to(original)
            with self.assertRaisesRegex(ValueError, "single-link regular"):
                m._read_bootstrap(alias, wanted)
            alias.unlink()
            os.link(original, alias)
            with self.assertRaisesRegex(ValueError, "single-link regular"):
                m._read_bootstrap(original, wanted)
            alias.unlink()
            original.write_bytes(b"changed source")
            with self.assertRaisesRegex(ValueError, "identity differs"):
                m._read_bootstrap(original, wanted)

    def test_explicit_selectors_and_valid_controls_do_not_open_pending_gate(self):
        source = m._v2._v1._factory.COMBINED_SOURCE_CONTRACT
        for kwargs in ({}, {"source_contract": source}, {"image_contract": m.IMAGE_CONTRACT}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                m._controls(m.ROOT, m.Reader(), **kwargs)
        with self.assertRaisesRegex(ValueError, "selected image contract differs"):
            m._controls(m.ROOT, m.Reader(), source_contract=source, image_contract=m.V2_CONTRACT)
        with mock.patch.object(m, "CURRENT_REPORT_ID", None), self.assertRaisesRegex(ValueError, "not yet bound"):
            m._controls(m.ROOT, m.Reader(), source_contract=source, image_contract=m.IMAGE_CONTRACT)

    def test_changed_current_adapter_control_is_refused_before_pending_gate(self):
        source = m._v2._v1._factory.COMBINED_SOURCE_CONTRACT
        _, _, old_controls = m._v2._controls(m.ROOT, m.Reader(), source_contract=source, image_contract=m.V2_CONTRACT)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve()
            for name, raw in old_controls.items():
                write(root / name, raw)
            write(root / m.ADAPTER, (m.ROOT / m.ADAPTER).read_bytes() + b"\n# changed copied adapter\n")
            write(root / m.IMAGE_CONTRACT, (m.ROOT / m.IMAGE_CONTRACT).read_bytes())
            with self.assertRaisesRegex(ValueError, "identity differs"):
                m._controls(root, m.Reader(), source_contract=source, image_contract=m.IMAGE_CONTRACT)


class HistoricalBundleRejectionTests(unittest.TestCase):
    def setUp(self):
        # This creates only the established inert historical-v2 fixture. The
        # 4 KiB adapter's current-proof constant and validators are untouched.
        self.fixture = historical_tests.DeliveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.fixture.stage()
        self.bundle = self.fixture.bundle
        self.source = historical_tests.v1tests.existing.m.COMBINED_SOURCE_CONTRACT

    def digest(self):
        return m.identity((self.bundle / m.RECEIPT).read_bytes())["sha256"]

    def test_historical_receipt_is_rejected_before_new_contract_selection(self):
        with self.assertRaisesRegex(ValueError, "unknown delivery bundle schema"):
            m.verify_bundle(self.bundle, expected_receipt=self.digest(), source_contract=self.source,
                            image_contract=m.IMAGE_CONTRACT)
        with self.assertRaisesRegex(ValueError, "unknown image selector receipt"):
            m._impl["_selected_image_contract"](self.bundle, self.digest())

    def test_changing_only_schema_and_operation_cannot_relabel_old_bundle(self):
        path = self.bundle / m.RECEIPT
        receipt = json.loads(path.read_bytes())
        receipt.update(schema_version=4, operation=m.STAGE_OPERATION,
                       historical_current_policy_evidence={}, page_size_context={})
        path.write_bytes(m.encoded(receipt))
        with self.assertRaisesRegex(ValueError, "unknown image contract path"):
            m._impl["_selected_image_contract"](self.bundle, self.digest())

    def test_install_and_cli_refuse_old_receipt_without_publication(self):
        original_pin = copy.deepcopy(m.CURRENT_REPORT_ID)
        target = self.fixture.target()
        source = self.fixture.fixture.fixture.source
        with self.assertRaisesRegex(ValueError, "unknown image selector receipt"):
            m.install(self.bundle, target, expected_receipt=self.digest(), source_tree=source)
        with mock.patch("sys.stderr", new_callable=io.StringIO) as stderr:
            status = m.main(["install", "--bundle", str(self.bundle), "--expected-receipt", self.digest(),
                             "--source-tree", str(source), "--target-files", str(target)])
        self.assertEqual(2, status)
        self.assertIn("unknown image selector receipt", stderr.getvalue())
        for name in ("VENDOR", "ODM", "META/nezha_target_files_metadata.json"):
            self.assertFalse((target / name).exists())
        self.assertEqual(original_pin, m.CURRENT_REPORT_ID)


class InertCurrentDeliveryTests(unittest.TestCase):
    """The complete validator runs on inert fixtures, never captured ROM proof."""

    def setUp(self):
        self.old = historical_tests.DeliveryTests()
        self.old.setUp()
        self.addCleanup(self.old.doCleanups)
        old, previous = self.old, historical_tests.a
        self.root, self.controls = old.root, old.controls
        self.bundle = self.root / "fourk-metadata"
        self.source = old.fixture.fixture.source
        self.product_bytes = b"Inert selected 4 KiB product; not an Android makefile.\n"
        context = copy.deepcopy(m.PAGE_CONTEXT)
        context["source_candidate"] = m.identity(b"inert selected candidate")
        context["source_product"].update(m.identity(self.product_bytes))
        self.context = context
        product_path = "/work/evolution/" + context["source_product"]["path"]
        old.current["goals"] = ["inert-component-" + str(index) for index in range(37)]
        old.current["current_source_binding"]["source_inventory"][0] = {
            "path": product_path, **m.identity(b"inert historical product")}
        historical_raw = m.encoded(old.current)
        historical_id = m.identity(historical_raw)
        write(old.current_path, historical_raw)
        self.enterContext(mock.patch.object(previous, "CURRENT_REPORT_ID", historical_id))
        old.admission["current_policy_build_evidence"] = historical_id
        old.selected["controls"]["current_policy"] = {"path": "current-policy.json", **historical_id}
        old.selected["verified_inputs"]["source"]["identities"] = old.current["current_source_binding"]["source_inventory"]
        old.save_selected()
        historical_admission_id = m.identity(m.encoded(old.admission))
        installation_ids = {name: m.identity(("inert-installation-" + name).encode())
                            for name in ("profile", "manifest", "installation", "journal", "commit")}
        settings_ids = {name: m.identity(("inert-settings-" + name).encode()) for name in ("before", "after")}
        self.enterContext(mock.patch.object(m, "_v2", previous))
        self.enterContext(mock.patch.object(m, "HISTORICAL_CURRENT_ID", historical_id))
        self.enterContext(mock.patch.object(m, "V2_CONTRACT_ID", historical_admission_id))
        self.enterContext(mock.patch.object(m, "PAGE_CONTEXT", context))
        self.enterContext(mock.patch.object(m, "INSTALLATION_IDS", installation_ids))
        self.enterContext(mock.patch.object(m, "SETTINGS_IDS", settings_ids))
        current_rows = copy.deepcopy(old.current["current_source_binding"]["source_inventory"])
        current_rows[0] = {"path": product_path, **m.expected(context["source_product"])}
        inventory_id = m.identity(m.encoded(current_rows))
        history = {
            "verified": True, "operation": "verify-v13j-pagesize-sources-after-build",
            "base": "/work/candidates/nezha-stock-4k-v13ja", "source_files_checked": 204,
            "max_page_size_supported": 4096, "normal_android_enforcing_required": True,
            "profile_identity": installation_ids["profile"], "manifest_identity": installation_ids["manifest"],
            "actual_commit_canonical_identity": installation_ids["commit"],
            "actual_commit": {"verified": True, "installation": installation_ids["installation"],
                              "journal": installation_ids["journal"]},
            "records": {name: {"path": "/inert/" + name + ".json", **installation_ids[name]}
                        for name in ("installation", "journal")},
            "source_inventory": current_rows, "source_inventory_identity": inventory_id,
            "source_projects": {"inert": "unchanged"},
            "predecessor_history": {"source_projects": {"inert": "unchanged"}},
        }
        self.current = {
            "schema_version": 1, "operation": "build-post-v13j-4k-framework-components", "phase": "pagesize-v13j-1",
            "target_product": "lineage_nezha", "target_release": "bp4a", "variant": "user",
            "goals": copy.deepcopy(old.current["goals"]), "exit_code": 0, "build_passed": True,
            "native_component_build_passed": True, "build_passed_scope": "native-37-goal-component-build-only",
            "timed_out": False, "forced_kill_after_timeout": False, "remaining_build_processes": [],
            "post_build_error": None, "sandbox_fallback": False, "ninja_argv_verified": True, "ninja_argv_error": None,
            "sandbox": {"namespace_and_mount_checks_passed": True, "source_readonly_output_writable": True},
            "native_settings_transition_verified": True, "page_size_profile_selected": True, "selected_max_page_size": 4096,
            "page_size_transition": {"verified": True, "before_max_page_size": 16384, "after_max_page_size": 4096,
                "prebuilt_max_page_size_check": True, "no_bionic_page_size_macro_unchanged": True,
                "strict_soong_elf_checks_selected": True, "checker_actions_verified": False,
                "vsr_16k_compatibility_verified": False},
            "source_history_proof": history,
            "bindings": {"profile_identity": installation_ids["profile"], "manifest_identity": installation_ids["manifest"]},
            "source_manifest": {"path": "/inert/current-source.json", **inventory_id},
            "protected_policy_outputs": copy.deepcopy(old.current["policy_equality"]["protected_policy_outputs"]),
            "protected_runtime_outputs": copy.deepcopy(old.current["policy_equality"]["protected_runtime_outputs"]),
            "prior_policy_analysis_reused": True,
        }
        for role, maximum in (("before", "16384"), ("after", "4096")):
            self.current["strict_settings_" + role] = {
                "settings": {"path": "/work/out/nezha-user-policy-20260827T2220Z/soong/soong.lineage_nezha.variables",
                             **settings_ids[role]}, "max_page_size": maximum,
                "strict_soong_elf_checks_selected": True, "prebuilt_max_page_size_check": True,
                "no_bionic_page_size_macro": True, "checker_actions_verified": False}
        for field in ("fresh_policy_compiler_actions_verified", "policy_outputs_invalidated_or_moved", "metadata_source_selected",
                      "vsr_16k_compatibility_verified", "full_vendor_kernel_apex_compatibility_executed", "compatibility_verified",
                      "allocator_runtime_registration_verified", "apex_cryptographic_validation_performed",
                      "provider_elf_compatibility_verified", "provider_runtime_requested", "strict_provider_elf_actions_verified",
                      "images_requested", "complete_rom_ready", "phone_accessed"):
            self.current[field] = False
        self.current_path = self.root / "inert-current-fourk.json"
        write(self.current_path, m.encoded(self.current))
        current_id = m.identity(self.current_path.read_bytes())
        self.enterContext(mock.patch.object(m, "CURRENT_REPORT_ID", current_id))
        self.admission = copy.deepcopy(old.admission)
        self.admission.update(schema_version=3, contract_id=m.IMAGE_CONTRACT_ID,
            historical_current_policy_evidence=historical_id,
            historical_delivery_admission={"path": m.V2_CONTRACT, **historical_admission_id},
            page_size_context=context, current_policy_build_evidence=current_id)
        basis = copy.deepcopy(self.admission)
        basis.update(schema_version=2, contract_id=m.BASIS_CONTRACT_ID, current_policy_build_evidence=None)
        del basis["historical_current_policy_evidence"], basis["selected_delivery_evidence"]
        basis_id = m.identity(m.encoded(basis))
        self.enterContext(mock.patch.object(m, "BASIS_ID", basis_id))
        self.enterContext(mock.patch.dict(m._impl, {
            "_factory": previous._v1._factory, "ORIGINAL_ID": previous._v1.ORIGINAL_ID,
            "V1_CONTRACT_ID": previous.V1_CONTRACT_ID, "V2_CONTRACT_ID": historical_admission_id,
            "BASIS_ID": basis_id, "PAGE_CONTEXT": context,
        }))
        write(self.controls / m.BASIS_CONTRACT, m.encoded(basis))
        write(self.controls / m.IMAGE_CONTRACT, m.encoded(self.admission))
        write(self.controls / m.ADAPTER, (m.ROOT / m.ADAPTER).read_bytes())
        write(self.controls / context["profile"]["path"], (m.ROOT / context["profile"]["path"]).read_bytes())

    def stage(self, output=None):
        return m.stage_from_original(self.old.original, output or self.bundle,
            expected_original_receipt=historical_tests.v1tests.a.ORIGINAL_ID["sha256"],
            source_contract=historical_tests.v1tests.existing.m.COMBINED_SOURCE_CONTRACT,
            image_contract=self.controls / m.IMAGE_CONTRACT, delivery_proof=self.old.fixture.proof_path,
            current_policy_evidence=self.current_path, selected_delivery_evidence=self.old.selected_path,
            historical_policy_evidence=self.old.current_path, controls_root=self.controls)

    def digest(self):
        return m.identity((self.bundle / m.RECEIPT).read_bytes())["sha256"]

    def verify(self, **kwargs):
        return m.verify_bundle(self.bundle, expected_receipt=self.digest(),
            source_contract=historical_tests.v1tests.existing.m.COMBINED_SOURCE_CONTRACT,
            image_contract=m.IMAGE_CONTRACT, **kwargs)

    def target(self):
        target = self.old.target()
        write(self.source / self.context["source_product"]["path"], self.product_bytes)
        return target

    def install(self, target):
        return m.install(self.bundle, target, expected_receipt=self.digest(), source_tree=self.source)

    def test_inert_stage_verify_and_repeat_preserve_metadata_and_historical_evidence(self):
        receipt = self.stage()
        self.assertEqual(4, receipt["schema_version"])
        self.assertEqual(self.old.fixture.original_receipt["files"], receipt["files"])
        self.assertEqual(self.old.current_path.read_bytes(), (self.bundle / m.HISTORICAL_COPY).read_bytes())
        verified, _, _ = self.verify(current_policy_evidence=self.current_path,
                                    historical_policy_evidence=self.old.current_path,
                                    selected_delivery_evidence=self.old.selected_path)
        self.assertEqual(receipt, verified)
        second = self.root / "fourk-repeat"
        self.stage(second)
        for path in m._files(self.bundle):
            self.assertEqual((self.bundle / path).read_bytes(), (second / path).read_bytes())

    def test_inert_install_checks_product_images_framework_and_sidecars(self):
        self.stage()
        target = self.target()
        report = self.install(target)
        self.assertEqual("project-policy-image-target-files-metadata-4k-v3", report["operation"])
        for field in ("actual_fourk_product_source_verified", "seven_actual_framework_inputs_verified",
                      "three_actual_framework_sidecars_recomputed"):
            self.assertTrue(report["packaged_policy_checks"][field])
        self.assertFalse(report["complete_rom_ready"])
        self.assertFalse((target / "ODM/etc/selinux").exists())
        self.assertEqual(report, json.loads((target / "META/nezha_target_files_metadata.json").read_bytes()))

    def test_each_actual_framework_file_and_sidecar_must_match(self):
        self.stage()
        target = self.target()
        inputs, sidecars = m._v2._policy_layout(self.admission)
        paths = [row["target_files_path"] for row in inputs] + [row["framework_sidecar_path"] for row in sidecars]
        for relative in paths:
            path = target / relative
            raw = path.read_bytes()
            for changed in (None, raw + b"changed"):
                if changed is None:
                    path.unlink()
                else:
                    path.write_bytes(changed)
                with self.subTest(path=relative, missing=changed is None), self.assertRaises((ValueError, OSError)):
                    self.install(target)
                self.assertFalse((target / "VENDOR").exists())
                path.write_bytes(raw)

    def test_source_product_missing_old_or_aliased_bytes_fail(self):
        self.stage()
        target = self.target()
        path = self.source / self.context["source_product"]["path"]
        path.unlink()
        with self.assertRaises((ValueError, OSError)):
            self.install(target)
        path.write_bytes(b"inert historical product")
        with self.assertRaises(ValueError):
            self.install(target)
        outside = self.root / "same-product-bytes"
        outside.write_bytes(self.product_bytes)
        for kind in ("symlink", "hardlink"):
            path.unlink()
            if kind == "symlink":
                path.symlink_to(outside)
            else:
                os.link(outside, path)
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                self.install(target)
        self.assertFalse((target / "ODM").exists())

    def test_all_ten_packaging_sources_and_both_images_remain_guarded(self):
        self.stage()
        target = self.target()
        paths = [self.source / row["path"] for row in self.admission["source_composition"]["final_source_files"]]
        paths += [target / "IMAGES/vendor.img", target / "IMAGES/odm.img"]
        for path in paths:
            raw = path.read_bytes()
            path.write_bytes(raw + b"changed")
            with self.subTest(path=str(path)), self.assertRaises(ValueError):
                self.install(target)
            self.assertFalse((target / "VENDOR").exists())
            path.write_bytes(raw)

    def test_policy_gate_requires_source_product_and_canonical_image_paths(self):
        self.stage()
        target = self.target()
        with self.assertRaisesRegex(ValueError, "actual 4 KiB product source"):
            m._policy_gate(self.admission, target, m.Reader(), self.current)
        with self.assertRaisesRegex(ValueError, "canonical selected final images"):
            self.verify(source_tree=self.source, vendor_image=self.old.fixture.final_images["vendor"],
                        odm_image=self.old.fixture.final_images["odm"], target_files=target)

    def test_product_change_during_publication_rolls_back_only_owned_metadata(self):
        self.stage()
        target = self.target()
        original_publish = m._install_namespace["_publish_at"]
        def publish(source_fd, source, destination_fd, destination):
            result = original_publish(source_fd, source, destination_fd, destination)
            if destination == "VENDOR":
                (self.source / self.context["source_product"]["path"]).write_bytes(b"changed during publication")
            return result
        with mock.patch.dict(m._install_namespace, {"_publish_at": publish}):
            with self.assertRaises(ValueError):
                self.install(target)
        for path in ("VENDOR", "ODM", "META/nezha_target_files_metadata.json"):
            self.assertFalse((target / path).exists())
        self.assertTrue((target / "IMAGES/vendor.img").is_file())

    def test_missing_or_changed_evidence_and_page_controls_abort_staging(self):
        paths = [self.current_path, self.old.current_path, self.old.selected_path,
                 self.controls / m.BASIS_CONTRACT, self.controls / self.context["profile"]["path"]]
        for path in paths:
            raw = path.read_bytes()
            path.unlink()
            with self.subTest(path=str(path)), self.assertRaises((ValueError, OSError)):
                self.stage()
            self.assertFalse(self.bundle.exists())
            path.write_bytes(raw)
        self.stage()
        for relative in (m.HISTORICAL_COPY, m._v2.CURRENT_COPY, m._v2.SELECTED_COPY):
            path = self.bundle / relative
            raw = path.read_bytes()
            path.write_bytes(raw + b"\n")
            with self.subTest(copied=relative), self.assertRaises(ValueError):
                self.verify()
            path.write_bytes(raw)

    def test_current_result_rejects_changed_source_policy_runtime_settings_or_scope(self):
        changes = (
            lambda d: d.update(exit_code=False), lambda d: d.update(build_passed=1),
            lambda d: d.update(timed_out=True), lambda d: d.update(remaining_build_processes=["inert-process"]),
            lambda d: d.update(selected_max_page_size=16384),
            lambda d: d["strict_settings_after"].update(max_page_size="16384"),
            lambda d: d["strict_settings_after"].update(checker_actions_verified=True),
            lambda d: d["page_size_transition"].update(vsr_16k_compatibility_verified=True),
            lambda d: d["source_history_proof"]["source_inventory"][0].update(sha256="0" * 64),
            lambda d: d["source_history_proof"]["source_inventory"].pop(),
            lambda d: d["source_history_proof"]["actual_commit"].update(verified=False),
            lambda d: d["source_history_proof"]["actual_commit"]["journal"].update(sha256="0" * 64),
            lambda d: d["bindings"]["profile_identity"].update(sha256="0" * 64),
            lambda d: d["protected_policy_outputs"][0].update(sha256="0" * 64),
            lambda d: d["protected_runtime_outputs"][0].update(size_bytes=0),
            lambda d: d["goals"].reverse(), lambda d: d.update(fresh_policy_compiler_actions_verified=True),
            lambda d: d.update(metadata_source_selected=True), lambda d: d.update(complete_rom_ready=True),
        )
        for index, change in enumerate(changes):
            altered = copy.deepcopy(self.current)
            change(altered)
            with self.subTest(index=index), self.assertRaises(ValueError):
                m._validate_current_fields(altered, self.admission, self.old.current)


if __name__ == "__main__":
    unittest.main()
