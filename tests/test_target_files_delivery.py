"""Offline consumer tests; synthetic bundles are not Android install evidence."""

from contextlib import redirect_stdout
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from scripts import generate_device_tree as g
from scripts import target_files_metadata as original
from scripts import target_files_metadata_combined as combined
from scripts import target_files_metadata_delivery as delivery
from scripts import target_files_metadata_delivery_policy3 as metadata
from scripts import rom_construction_source as construction
from scripts import policy_inputs
from tests import test_generate_device_tree as fixtures


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / g.TARGET_FILES_SOURCE_CONTRACT
CONTRACT = ROOT / g.POLICY_IMAGE_DELIVERY_CONTRACT


class TargetFilesDeliveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.GenerateDeviceTreeTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.GenerateDeviceTreeTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root

    def public(self):
        return g._metadata_public_binding(source_contract=SOURCE, image_contract=CONTRACT)

    def binding_plan(self):
        binding = self.public()
        vendor = {"sha256": "1" * 64, "size_bytes": 100}
        binding.update(receipt={"path": g.TARGET_FILES_METADATA_RECEIPT, "sha256": "2" * 64, "size_bytes": 200},
                       vendor_bundle=vendor)
        plan = {"profile": "framework-checks", "release_config": "bp4a", "variant": "user",
                "product": "lineage_nezha", "device": {"codename": "nezha"}, "shipping_api_level": 36,
                "admission": {"configuration_allowed": True, "flash_allowed": False,
                              "complete_target_files_allowed": False},
                "source_packages": {"vendor": binding["factory_package_sha256"]},
                "factory_profile": {"package_sha256": binding["factory_package_sha256"], "origin_verified": False},
                "bundles": {"vendor": vendor}, "target_files_metadata": binding,
                "policy_inputs": {"receipt": copy.deepcopy(g.POLICY_IMAGE_DELIVERY_POLICY)},
                "framework_providers": {"inputs": {"receipt": copy.deepcopy(g.POLICY_IMAGE_DELIVERY_PROVIDERS)}},
                "framework_allocator": {"contract_record": {"sha256": g.FRAMEWORK_ALLOCATOR_CONTRACT_SHA256}},
                "mi_ext_inputs": {"native_source": {
                    "project_commit": binding["native_source"]["project"]["commit"],
                    "files": binding["native_source"]["final_source_files"],
                    "composition": binding["native_source"], "composition_identity": binding["composition_identity"]}}}
        return binding, plan

    def generation_inputs(self):
        """Reuse existing tiny provider fixtures, mocking only private verifiers."""
        inputs, provider, policy = self.fixture.provider_inputs(properties=True)
        self.enterContext(mock.patch.object(g, "_verify_framework_provider_bundle", return_value=provider))
        self.enterContext(mock.patch.object(g, "_verify_policy_input_bundle", return_value=policy))
        real_public = self.public()
        inputs, factory_public, receipt, _ = self.fixture.metadata_inputs(source_contract=SOURCE, inputs=inputs)
        real_public.update({key: copy.deepcopy(factory_public[key]) for key in ("factory_package_sha256", "images")})
        real_public["policy_image_delivery"]["required_policy_inputs"] = copy.deepcopy(policy["receipt"])
        real_public["policy_image_delivery"]["required_framework_providers"] = copy.deepcopy(provider["receipt"])
        self.enterContext(mock.patch.object(g, "_metadata_public_binding", side_effect=lambda **kw:
            copy.deepcopy(real_public if "image_contract" in kw else factory_public)))
        receipt.update(schema_version=3, operation="stage-policy-image-target-files-metadata-v2",
                       bundle_files=copy.deepcopy(real_public["control_files"]),
                       packaged_images=copy.deepcopy(real_public["policy_image_delivery"]["packaged_images"]),
                       current_policy_evidence={"path": "provenance/current-policy-evidence.json",
                           **real_public["policy_image_delivery"]["current_policy_evidence"]},
                       selected_delivery_evidence={"path": "provenance/selected-delivery-evidence.json",
                           **real_public["policy_image_delivery"]["selected_delivery_evidence"]})
        bundle = inputs["target_files_metadata_receipt"].parent
        _, _, controls = delivery._controls(ROOT, delivery.Reader(), source_contract=SOURCE, image_contract=CONTRACT)
        runtime = delivery.runtime_tool_payloads(controls)
        for row in receipt["bundle_files"]:
            name = row["path"]
            target = bundle / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / name.removeprefix("controls/")).read_bytes()
                               if name.startswith("controls/") else runtime[name])
        raw = delivery.encoded(receipt)
        inputs["target_files_metadata_receipt"].write_bytes(raw)
        inputs["target_files_metadata_receipt_sha256"] = hashlib.sha256(raw).hexdigest()
        files = {str(index): ({}, b"synthetic metadata") for index in range(real_public["metadata_file_count"])}
        verifier = self.enterContext(mock.patch.object(delivery, "verify_bundle", return_value=(receipt, files, mock.Mock())))
        allocator = json.loads((ROOT / g.FRAMEWORK_ALLOCATOR_RECORD).read_bytes())
        for row in (allocator["source_lock"], allocator["source_snapshot"]):
            target = self.root / row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((ROOT / row["path"]).read_bytes())
        inputs["framework_allocator_contract"] = ROOT / g.FRAMEWORK_ALLOCATOR_RECORD
        inputs["policy_image_delivery_contract"] = CONTRACT
        inputs["variant"] = "user"
        (inputs["template_root"] / "BoardConfig.mk").write_bytes((ROOT / g.DEVICE_PATH / "BoardConfig.mk").read_bytes())
        return inputs, receipt, verifier

    def paired_4k_binding_plan(self):
        """Exercise the consumer boundary without inventing native proof data."""
        binding, plan = self.binding_plan()
        profile, profile_identity = g._page_size_profile_contract(ROOT / g.PAGE_SIZE_PROFILE_V2_RECORD)
        plan["kernel"] = {"sha256": profile["kernel"]["image"]["sha256"], "page_size_bytes": 4096}
        plan["bundles"]["kernel"] = copy.deepcopy(profile["kernel"]["receipt"])
        plan["framework_providers"]["inputs"].update(
            contract={key: profile["providers"]["contract"][key] for key in ("sha256", "size_bytes")},
            files=[{"path": "proprietary" + row["runtime_path"],
                    **{key: row[key] for key in ("sha256", "size_bytes")}} for row in profile["providers"]["files"]],
            payload_derivations=copy.deepcopy(profile["providers"]["payload_derivations"]))
        plan["page_size_profile"] = g._page_size_profile_binding(plan, profile, profile_identity)
        partitions = [*g.FRAMEWORK_PARTITIONS, "mi_ext"]
        plan.update(packaged_logical_partitions=partitions, required_unpacked_partitions=[],
                    logical_filesystems={name: "erofs" for name in partitions})
        selected = binding["policy_image_delivery"]
        selected["contract"] = {"path": g.POLICY_IMAGE_DELIVERY_4K_CONTRACT,
                                "contract_id": g.POLICY_IMAGE_DELIVERY_4K_CONTRACT_ID,
                                "sha256": "4" * 64, "size_bytes": 400}
        selected["page_size_context"] = copy.deepcopy(g.POLICY_IMAGE_DELIVERY_4K_CONTEXT)
        selected["historical_current_policy_evidence"] = copy.deepcopy(selected["current_policy_evidence"])
        public = {key: copy.deepcopy(value) for key, value in binding.items() if key not in {"receipt", "vendor_bundle"}}
        # The independent maintained adapter owns native evidence validation.
        # These mocks isolate the generator's page/product pairing checks.
        self.enterContext(mock.patch.object(g, "_metadata_options", return_value={}))
        self.enterContext(mock.patch.object(g, "_metadata_module", return_value=delivery))
        self.enterContext(mock.patch.object(g, "_metadata_public_binding", return_value=public))
        return binding, plan

    def test_factory_routing_does_not_inspect_delivery(self):
        with mock.patch.object(g, "_policy_image_delivery_reference", side_effect=AssertionError("implicit delivery")):
            self.assertIs(g._metadata_module(), original)
            self.assertIs(g._metadata_module(source_contract=SOURCE), combined)
            self.assertNotIn("policy_image_delivery", g._metadata_public_binding(source_contract=SOURCE))

    def test_default_generation_and_explicit_none_have_identical_bytes(self):
        inputs = self.fixture.generation_inputs()
        with mock.patch.object(g, "_policy_image_delivery_reference", side_effect=AssertionError("implicit delivery")):
            first = g.generate(self.root / "artifacts/default", **inputs)
            second = g.generate(self.root / "artifacts/none", policy_image_delivery_contract=None, **inputs)
        self.assertEqual(first, second)
        for row in first["files"]:
            self.assertEqual((self.root / "artifacts/default" / row["path"]).read_bytes(),
                             (self.root / "artifacts/none" / row["path"]).read_bytes())

    def test_public_closure_is_four_maintained_sources_and_one_runtime(self):
        public = self.public()
        self.assertEqual(delivery.CONTROL_TOOLS, ("scripts/target_files_metadata.py",
            "scripts/target_files_metadata_combined.py", "scripts/target_files_metadata_policy_images.py",
            "scripts/target_files_metadata_delivery.py"))
        self.assertEqual(len(public["control_files"]), 23)
        self.assertFalse(any(row["path"].startswith("controls/reports/") for row in public["control_files"]))
        self.assertEqual([row["path"] for row in public["control_files"] if row["path"].startswith("tools/")],
                         ["tools/target_files_metadata.py"])
        self.assertEqual(len(public["native_source"]["final_source_files"]), 10)
        self.assertEqual(public["metadata_file_count"], 205)
        for name in ("vendor", "odm"):
            self.assertNotEqual(public["images"][name], public["policy_image_delivery"]["packaged_images"][name])

    def test_cli_only_selects_the_explicit_flag(self):
        base = ["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json", "--output", "artifacts/out"]
        for extra, expected in (([], None), (["--policy-image-delivery-contract", "selected.json"], Path("selected.json"))):
            with mock.patch.object(g, "generate", return_value={}) as generate, redirect_stdout(io.StringIO()):
                self.assertEqual(g.main(base + extra), 0)
            self.assertEqual(generate.call_args.kwargs["policy_image_delivery_contract"], expected)

    def test_incomplete_capabilities_and_held_page_profile_fail_before_input_reads(self):
        required = dict(target_files_source_contract="source", target_files_metadata_receipt="receipt",
                        target_files_metadata_receipt_sha256="1" * 64, policy_inputs_receipt="policy",
                        framework_provider_policy_contract="provider-policy", framework_provider_inputs_receipt="providers",
                        framework_allocator_contract="allocator")
        for missing in required:
            options = {k: v for k, v in required.items() if k != missing}
            with self.subTest(missing=missing), mock.patch.object(g, "_load_records") as load, self.assertRaises(g.CandidateError):
                g.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none", vendor_receipt="none",
                           variant="user", policy_image_delivery_contract=CONTRACT, **options)
            load.assert_not_called()
        with mock.patch.object(g, "_load_records") as load, self.assertRaises(g.CandidateError):
            g.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none", vendor_receipt="none",
                       variant="user", policy_image_delivery_contract=CONTRACT, page_size_profile="held", **required)
        load.assert_not_called()

    def test_delivery_rejects_userdebug_before_input_reads(self):
        with mock.patch.object(g, "_load_records") as load, self.assertRaisesRegex(g.CandidateError, "explicit user variant"):
            g.generate(self.root / "artifacts/refused", record_paths={}, kernel_receipt="none", vendor_receipt="none",
                       variant="userdebug", policy_image_delivery_contract=CONTRACT)
        load.assert_not_called()

    def test_changed_linked_and_special_contracts_are_rejected(self):
        for kind in ("changed", "symlink", "hardlink", "directory", "fifo"):
            path = self.root / kind
            if kind == "changed": path.write_bytes(CONTRACT.read_bytes() + b"\n")
            elif kind == "symlink": path.symlink_to(CONTRACT)
            elif kind == "hardlink":
                original_path = self.root / "contract-copy"
                original_path.write_bytes(CONTRACT.read_bytes())
                path.hardlink_to(original_path)
            elif kind == "directory": path.mkdir()
            else: os.mkfifo(path)
            with self.subTest(kind=kind), self.assertRaises((g.CandidateError, OSError)):
                g._policy_image_delivery_reference(path)

    def test_wrong_current_inputs_and_forged_scope_are_rejected(self):
        binding, plan = self.binding_plan()
        self.assertIn("BOARD_NEZHA_PREBUILT_METADATA := true", g._target_files_metadata_binding(plan, binding))
        mutations = [lambda p: p.update(variant="userdebug"), lambda p: p.update(release_config="other"),
                     lambda p: p.update(product="other"), lambda p: p["device"].update(codename="other"),
                     lambda p: p.update(shipping_api_level=35),
                     lambda p: p["policy_inputs"]["receipt"].update(sha256="0" * 64),
                     lambda p: p["framework_providers"]["inputs"]["receipt"].update(sha256="0" * 64),
                     lambda p: p["framework_allocator"]["contract_record"].update(sha256="0" * 64),
                     lambda p: p.pop("framework_allocator"), lambda p: p.update(page_size_profile={}),
                     lambda p: p["target_files_metadata"]["policy_image_delivery"]["scope"].update(native_image_bytes_verified=True),
                     lambda p: p["target_files_metadata"]["policy_image_delivery"]["packaged_images"]["vendor"].update(sha256="0" * 64),
                     lambda p: p["target_files_metadata"]["images"].update(vendor=binding["policy_image_delivery"]["packaged_images"]["vendor"])]
        for mutation in mutations:
            changed = copy.deepcopy(plan)
            mutation(changed)
            with self.subTest(mutation=mutation), self.assertRaises(g.CandidateError):
                g._target_files_metadata_binding(changed, changed["target_files_metadata"])

    def test_source_overlay_keeps_complete_board_guard_and_original_paths(self):
        binding, plan = self.binding_plan()
        board = (g.DEVICE_PATH / "BoardConfig.mk").as_posix()
        before = (ROOT / board).read_bytes()
        after = g._policy_image_delivery_board(before)
        addition = b"include $(NEZHA_DEVICE_PATH)/generated/policy-image-delivery.mk\n"
        self.assertEqual(after.replace(addition, b"", 1), before)
        payloads = {board: after, g.POLICY_IMAGE_DELIVERY_INCLUDE.as_posix(): g._render_policy_image_delivery(binding).encode()}
        g._policy_image_delivery_source_guards(plan, payloads)
        guard = payloads[g.POLICY_IMAGE_DELIVERY_INCLUDE.as_posix()]
        for name in ("vendor", "odm"):
            self.assertIn(f"ifneq ($(origin BOARD_PREBUILT_{name.upper()}IMAGE),file)".encode(), guard)
            self.assertIn(f"vendor/xiaomi/nezha/proprietary/images/{name}.img".encode(), guard)
            self.assertIn(f"BOARD_PREBUILT_{name.upper()}IMAGE := {g.POLICY_IMAGE_DELIVERY_PATH}/images/{name}.img".encode(), guard)
        self.assertNotIn(b"override ", guard)
        self.assertNotIn(b".KATI_READONLY", guard)

    def test_source_gate_rejects_missing_capability_extra_selectors_and_mutated_board(self):
        binding, plan = self.binding_plan()
        board = (g.DEVICE_PATH / "BoardConfig.mk").as_posix()
        payloads = {board: g._policy_image_delivery_board((ROOT / board).read_bytes()),
                    g.POLICY_IMAGE_DELIVERY_INCLUDE.as_posix(): g._render_policy_image_delivery(binding).encode()}
        with self.assertRaises(g.CandidateError): g._policy_image_delivery_source_guards({}, payloads)
        for name, extra in ((board, b"# changed\n"),
                            ((g.DEVICE_PATH / "device.mk").as_posix(), b"BOARD_PREBUILT_VENDORIMAGE := other\n"),
                            (g.POLICY_IMAGE_DELIVERY_INCLUDE.as_posix(), b"BOARD_AVB_ENABLE := false\n")):
            mutated = dict(payloads)
            mutated[name] = mutated.get(name, b"") + extra
            with self.subTest(name=name), self.assertRaises(g.CandidateError):
                g._policy_image_delivery_source_guards(plan, mutated)

    def test_full_generation_is_repeatable_and_preserves_readiness(self):
        inputs, _, verifier = self.generation_inputs()
        first, second = self.root / "artifacts/delivery-one", self.root / "artifacts/delivery-two"
        plan = g.generate(first, **inputs)
        self.assertEqual(g.generate(second, **inputs), plan)
        self.assertEqual(g.validate(first), plan)
        self.assertEqual(verifier.call_count, 4)
        self.assertTrue(all(call.kwargs == {"expected_receipt": inputs["target_files_metadata_receipt_sha256"],
            "source_contract": SOURCE, "image_contract": CONTRACT} for call in verifier.call_args_list))
        for purpose in ("target-files", "flash"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(g.CandidateError, "not a complete signed partition set"):
                g.validate(first, purpose=purpose)
        self.assertFalse(plan["admission"]["complete_target_files_allowed"])
        self.assertNotIn("page_size_profile", plan)
        self.assertFalse(any(row["path"].startswith("vendor/") for row in plan["files"]))

    def test_new_receipt_cannot_select_delivery_through_the_old_mode(self):
        inputs, _, _ = self.generation_inputs()
        with self.assertRaises(g.CandidateError):
            g._verify_target_files_metadata(inputs["target_files_metadata_receipt"],
                expected_receipt_sha256=inputs["target_files_metadata_receipt_sha256"], source_contract=SOURCE)

    def test_schema_current_copy_and_runtime_mutations_fail(self):
        inputs, receipt, _ = self.generation_inputs()
        baseline = copy.deepcopy(receipt)
        mutations = [lambda r: r.update(schema_version=True), lambda r: r.update(schema_version=2),
                     lambda r: r.update(operation="stage-policy-image-target-files-metadata"),
                     lambda r: r["current_policy_evidence"].update(sha256="0" * 64),
                     lambda r: r["selected_delivery_evidence"].update(size_bytes=True),
                     lambda r: r["packaged_images"].update(vendor=r["images"]["vendor"]),
                     lambda r: r["bundle_files"].pop()]
        for mutate in mutations:
            receipt.clear(); receipt.update(copy.deepcopy(baseline)); mutate(receipt)
            with self.subTest(mutate=mutate), self.assertRaises(g.CandidateError):
                g._verify_target_files_metadata(inputs["target_files_metadata_receipt"],
                    expected_receipt_sha256=inputs["target_files_metadata_receipt_sha256"],
                    source_contract=SOURCE, image_contract=CONTRACT)

    def test_validation_rejects_resealed_delivery_guard_and_weakened_board(self):
        inputs, _, _ = self.generation_inputs()
        output = self.root / "artifacts/guarded"
        plan = g.generate(output, **inputs)
        for name in ((g.DEVICE_PATH / "BoardConfig.mk").as_posix(), g.POLICY_IMAGE_DELIVERY_INCLUDE.as_posix()):
            raw = (output / name).read_bytes()
            self.fixture.reseal_candidate_file(output, plan, name, raw + b"BOARD_AVB_ENABLE := false\n")
            with self.subTest(name=name), self.assertRaises(g.CandidateError): g.validate(output)
            self.fixture.reseal_candidate_file(output, plan, name, raw)
        self.assertEqual(g.validate(output), plan)

    def test_portable_validation_does_not_read_private_images_or_bundle(self):
        inputs, _, _ = self.generation_inputs()
        output = self.root / "artifacts/portable"
        plan = g.generate(output, **inputs)
        inputs["target_files_metadata_receipt"].unlink()
        with mock.patch.object(g, "_verify_target_files_metadata", side_effect=AssertionError("private bundle reopened")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("native command executed")):
            self.assertEqual(g.validate(output), plan)

    def test_4k_selector_has_closed_id_schema_and_canonical_path(self):
        path = self.root / g.POLICY_IMAGE_DELIVERY_4K_CONTRACT
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = {"schema_version": 3, "contract_id": g.POLICY_IMAGE_DELIVERY_4K_CONTRACT_ID}
        path.write_text(json.dumps(descriptor))
        # This is only the descriptor-selection boundary, not image admission.
        with mock.patch.object(g, "ROOT", self.root):
            selected = g._policy_image_delivery_reference(path)
            self.assertEqual(selected["path"], g.POLICY_IMAGE_DELIVERY_4K_CONTRACT)
            self.assertEqual(selected["contract_id"], g.POLICY_IMAGE_DELIVERY_4K_CONTRACT_ID)
            for mutation in ({"schema_version": 2}, {"schema_version": True}, {"contract_id": "unknown"},
                             {"contract_id": g.POLICY_IMAGE_DELIVERY_CONTRACT_ID}):
                path.write_text(json.dumps({**descriptor, **mutation}))
                with self.subTest(mutation=mutation), self.assertRaises((g.CandidateError, OSError)):
                    g._policy_image_delivery_reference(path)

    def test_4k_selector_never_opens_an_admission_supplied_path(self):
        binding, _ = self.binding_plan()
        binding["policy_image_delivery"]["contract"].update(
            contract_id=g.POLICY_IMAGE_DELIVERY_4K_CONTRACT_ID, path="../../unreviewed.json")
        with mock.patch.object(g, "_policy_image_delivery_reference", side_effect=AssertionError("untrusted path read")), \
                self.assertRaisesRegex(g.CandidateError, "selector differs"):
            g._metadata_image_selection(binding)

    def test_4k_pairing_requires_full_admission_and_exact_product_bytes(self):
        binding, plan = self.paired_4k_binding_plan()
        product = g._render_product(plan).encode()
        self.assertEqual({"sha256": hashlib.sha256(product).hexdigest(), "size_bytes": len(product)},
                         {key: g.POLICY_IMAGE_DELIVERY_4K_CONTEXT["source_product"][key] for key in ("sha256", "size_bytes")})
        self.assertIn("BOARD_NEZHA_PREBUILT_METADATA := true", g._target_files_metadata_binding(plan, binding))
        for mutate in (lambda p: p.pop("page_size_profile"),
                       lambda p: p["page_size_profile"].update(profile_id=g.PAGE_SIZE_PROFILE_ID),
                       lambda p: p["page_size_profile"]["contract"].update(sha256="0" * 64),
                       lambda p: p["page_size_profile"]["product_settings"].update(PRODUCT_MAX_PAGE_SIZE_SUPPORTED=16384),
                       lambda p: p["page_size_profile"]["product_settings"].update(PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE=1),
                       lambda p: p["page_size_profile"]["scope"].update(complete_rom_admitted=True),
                       lambda p: p["kernel"].update(sha256="0" * 64),
                       lambda p: p["framework_providers"]["inputs"]["receipt"].update(sha256="0" * 64)):
            changed = copy.deepcopy(plan)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(g.CandidateError):
                g._target_files_metadata_binding(changed, changed["target_files_metadata"])
        with mock.patch.object(g, "_render_product", return_value=product.decode() + "# changed\n"), \
                self.assertRaisesRegex(g.CandidateError, "unchanged current product"):
            g._target_files_metadata_binding(plan, binding)

    def test_4k_pairing_does_not_promote_scope_or_accept_a_resealed_context(self):
        binding, plan = self.paired_4k_binding_plan()
        mutations = (lambda p: p.update(variant="userdebug"),
                     lambda p: p.update(release_config="other"),
                     lambda p: p["admission"].update(complete_target_files_allowed=True),
                     lambda p: p["target_files_metadata"]["policy_image_delivery"]["page_size_context"]["source_candidate"].update(sha256="0" * 64),
                     lambda p: p["target_files_metadata"]["policy_image_delivery"]["historical_current_policy_evidence"].update(sha256="0" * 64))
        for mutate in mutations:
            changed = copy.deepcopy(plan)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaises(g.CandidateError):
                g._target_files_metadata_binding(changed, changed["target_files_metadata"])

    def test_actual_4k_public_route_preserves_historical_controls_and_metadata(self):
        from scripts import target_files_metadata_delivery_4k as paired
        selected_contract = ROOT / g.POLICY_IMAGE_DELIVERY_4K_CONTRACT
        public = g._metadata_public_binding(source_contract=SOURCE, image_contract=selected_contract)
        old = self.public()
        self.assertIs(g._metadata_module(source_contract=SOURCE, image_contract=selected_contract), paired)
        self.assertEqual(paired.CONTROL_TOOLS, (*delivery.CONTROL_TOOLS, "scripts/target_files_metadata_delivery_4k.py"))
        selected = public["policy_image_delivery"]
        self.assertEqual(selected["page_size_context"], g.POLICY_IMAGE_DELIVERY_4K_CONTEXT)
        self.assertEqual(selected["historical_current_policy_evidence"], old["policy_image_delivery"]["current_policy_evidence"])
        self.assertEqual(selected["selected_delivery_evidence"], old["policy_image_delivery"]["selected_delivery_evidence"])
        self.assertNotEqual(selected["current_policy_evidence"], selected["historical_current_policy_evidence"])
        self.assertEqual(selected["packaged_images"], old["policy_image_delivery"]["packaged_images"])
        for key in ("images", "scope", "metadata_file_count", "native_source", "composition_identity"):
            self.assertEqual(public[key], old[key])
        before = {row["path"]: row for row in old["control_files"] if row["path"].startswith("controls/")}
        after = {row["path"]: row for row in public["control_files"] if row["path"].startswith("controls/")}
        self.assertTrue(all(after.get(name) == row for name, row in before.items()))
        self.assertEqual([row["path"] for row in public["control_files"] if row["path"].startswith("tools/")],
                         ["tools/target_files_metadata.py"])

    def test_4k_consumer_rejects_resealed_legacy_receipts_and_context_changes(self):
        from scripts import target_files_metadata_delivery_4k as paired
        selected_contract = ROOT / g.POLICY_IMAGE_DELIVERY_4K_CONTRACT
        public = g._metadata_public_binding(source_contract=SOURCE, image_contract=selected_contract)
        selected = public["policy_image_delivery"]
        receipt = {key: copy.deepcopy(public[key]) for key in ("profile", "images", "scope")}
        receipt.update(schema_version=4, operation="stage-policy-image-target-files-metadata-4k-v3",
                       source_composition=copy.deepcopy(public["native_source"]),
                       files=[{} for _ in range(public["metadata_file_count"])],
                       bundle_files=copy.deepcopy(public["control_files"]),
                       packaged_images=copy.deepcopy(selected["packaged_images"]),
                       page_size_context=copy.deepcopy(selected["page_size_context"]))
        for key, name in (("current_policy_evidence", "current-policy-evidence.json"),
                          ("selected_delivery_evidence", "selected-delivery-evidence.json"),
                          ("historical_current_policy_evidence", "historical-v13i-policy-evidence.json")):
            receipt[key] = {"path": "provenance/" + name, **selected[key]}
        _, _, controls = paired._controls(ROOT, paired.Reader(), source_contract=SOURCE, image_contract=selected_contract)
        payloads = {"controls/" + name: raw for name, raw in controls.items()}
        payloads.update(paired.runtime_tool_payloads(controls))
        bundle = self.root / "synthetic-consumer-boundary"
        for name, raw in payloads.items():
            target = bundle / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        path = bundle / g.TARGET_FILES_METADATA_RECEIPT
        baseline = copy.deepcopy(receipt)
        # The adapter owns metadata/native proof verification. Isolate that
        # boundary here, including a resealed external receipt for every case.
        projected = {str(index): ({}, b"synthetic metadata") for index in range(public["metadata_file_count"])}
        with mock.patch.object(paired, "verify_bundle", return_value=(receipt, projected, mock.Mock())) as verifier:
            def verify():
                raw = paired.encoded(receipt)
                path.write_bytes(raw)
                return g._verify_target_files_metadata(path, expected_receipt_sha256=hashlib.sha256(raw).hexdigest(),
                                                       source_contract=SOURCE, image_contract=selected_contract)
            self.assertEqual(verify()["policy_image_delivery"], selected)
            self.assertEqual(verifier.call_args.kwargs["image_contract"], selected_contract)
            mutations = (lambda r: r.update(schema_version=3), lambda r: r.update(schema_version=True),
                         lambda r: r.update(operation="stage-policy-image-target-files-metadata-v2"),
                         lambda r: r.pop("page_size_context"),
                         lambda r: r["page_size_context"]["product_settings"].update(PRODUCT_MAX_PAGE_SIZE_SUPPORTED=16384),
                         lambda r: r["page_size_context"]["product_settings"].update(PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE=1),
                         lambda r: r["page_size_context"]["source_product"].update(sha256="0" * 64),
                         lambda r: r["current_policy_evidence"].update(selected["historical_current_policy_evidence"]),
                         lambda r: r.pop("historical_current_policy_evidence"),
                         lambda r: r["historical_current_policy_evidence"].update(path="provenance/current-policy-evidence.json"),
                         lambda r: r["selected_delivery_evidence"].update(sha256="0" * 64),
                         lambda r: r["packaged_images"].update(vendor=r["images"]["vendor"]),
                         lambda r: r["bundle_files"].pop())
            for mutate in mutations:
                receipt.clear()
                receipt.update(copy.deepcopy(baseline))
                mutate(receipt)
                with self.subTest(mutate=mutate), self.assertRaises(g.CandidateError):
                    verify()

    def test_4k_delivery_requires_explicit_current_profile_before_private_inputs(self):
        required = {name: "explicit" for name in (
            "target_files_source_contract", "target_files_metadata_receipt", "target_files_metadata_receipt_sha256",
            "policy_inputs_receipt", "framework_provider_policy_contract", "framework_provider_inputs_receipt",
            "framework_allocator_contract", "factory_boot_contract", "partition_metadata", "fstab_source",
            "dsp_policy_contract", "init_helper_capability_contract")}
        for page in (None, ROOT / g.PAGE_SIZE_PROFILE_RECORD):
            with self.subTest(page=page), mock.patch.object(g, "_load_records", side_effect=AssertionError("private input read")), \
                    self.assertRaisesRegex(g.CandidateError, "4 KiB policy-image delivery requires"):
                g.generate(self.root / "artifacts/refused-4k", record_paths={}, kernel_receipt=None, vendor_receipt=None,
                           variant="user", policy_image_delivery_contract=ROOT / g.POLICY_IMAGE_DELIVERY_4K_CONTRACT,
                           page_size_profile=page, **required)


    def test_policy3_public_required_receipts_preserve_canonical_filenames(self):
        with mock.patch.object(g, "ROOT", metadata.ROOT):
            binding = g._metadata_public_binding(
                source_contract=metadata.ROOT / "patches/evolution/target-files-source-composition.json",
                image_contract=metadata.ROOT / metadata.IMAGE_CONTRACT)
        selected = binding["policy_image_delivery"]
        self.assertEqual(selected["required_policy_inputs"],
                         {"path": "policy-inputs.json", **metadata.REQUIRED_POLICY})
        self.assertEqual(selected["required_framework_providers"],
                         {"path": "framework-provider-inputs.json", **metadata.REQUIRED_PROVIDERS})

    def test_policy3_closed_selector_and_pending_release_refusal(self):
        self.assertEqual(g._policy_image_delivery_spec(g.POLICY_IMAGE_DELIVERY_POLICY3_CONTRACT_ID),
                         ("config/nezha-policy-image-delivery-policy3.json", 4))
        with mock.patch.object(metadata, "IMAGE_CONTRACT_IDENTITY", None), \
                mock.patch.object(g, "ROOT", metadata.ROOT), \
                mock.patch.object(g, "_bind_bundles", side_effect=AssertionError("private bundle opened")):
            with self.assertRaisesRegex(g.CandidateError, "policy3 delivery is blocked"):
                g._policy_image_delivery_reference(metadata.ROOT / metadata.IMAGE_CONTRACT)

    def test_policy3_exact_current_policy_and_final_product_required(self):
        binding, plan = self.paired_4k_binding_plan()
        selected = binding["policy_image_delivery"]
        selected["contract"].update(path=g.POLICY_IMAGE_DELIVERY_POLICY3_CONTRACT,
                                    contract_id=g.POLICY_IMAGE_DELIVERY_POLICY3_CONTRACT_ID)
        selected.pop("historical_current_policy_evidence")
        selected["page_size_context"].pop("source_candidate")
        selected["page_size_context"]["production_source_product"] = copy.deepcopy(selected["page_size_context"]["source_product"])
        selected["required_policy_inputs"] = copy.deepcopy(metadata.REQUIRED_POLICY)
        selected["policy3_basis"] = {"required_policy_inputs": copy.deepcopy(metadata.REQUIRED_POLICY)}
        plan["policy_inputs"]["receipt"] = copy.deepcopy(metadata.REQUIRED_POLICY)
        final_product = g._render_product(plan).encode() + b"# synthetic final namespace selection\n"
        selected["page_size_context"]["source_product"].update(metadata.identity(final_product))
        g._metadata_public_binding.return_value = {key: copy.deepcopy(value) for key, value in binding.items()
                                                  if key not in {"receipt", "vendor_bundle"}}
        with mock.patch.object(g, "_render_product", return_value=final_product.decode()):
            self.assertIn("BOARD_NEZHA_PREBUILT_METADATA := true", g._target_files_metadata_binding(plan, binding))
            stale = copy.deepcopy(plan)
            stale["policy_inputs"]["receipt"] = copy.deepcopy(g.POLICY_IMAGE_DELIVERY_POLICY)
            with self.assertRaisesRegex(g.CandidateError, "exact current policy"):
                g._target_files_metadata_binding(stale, stale["target_files_metadata"])
            for mutation in (lambda p: p.update(variant="userdebug"), lambda p: p.update(release_config="other"),
                             lambda p: p["admission"].update(complete_target_files_allowed=True)):
                changed = copy.deepcopy(plan)
                mutation(changed)
                with self.assertRaises(g.CandidateError):
                    g._target_files_metadata_binding(changed, changed["target_files_metadata"])
        with self.assertRaisesRegex(g.CandidateError, "unchanged current product"):
            g._target_files_metadata_binding(plan, binding)

    def test_policy3_construction_derives_after_camera_and_factory_includes(self):
        board_path = (g.DEVICE_PATH / "BoardConfig.mk").as_posix()
        before = g._policy_image_delivery_board((ROOT / board_path).read_bytes())
        before = policy_inputs.factory_property_contexts_board(policy_inputs.camera_property_board(before))
        after = before + b"# synthetic constructor result\n"
        payloads = {board_path: after, g.POLICY_IMAGE_DELIVERY_INCLUDE.as_posix(): b"# synthetic delivery guard\n"}
        for contract_id, record in ((construction.POLICY3_CONTRACT_ID, construction.POLICY3_CONTRACT),
                                    (construction.CHECKSUM_CONTRACT_ID, construction.CHECKSUM_CONTRACT),
                                    (construction.MODE_FLAGS_CONTRACT_ID, construction.MODE_FLAGS_CONTRACT)):
            plan = {"target_files_metadata": {"policy_image_delivery": {}}, "camera_property_capability": {},
                    "factory_property_contexts_capability": {}, construction.BINDING: {"contract_id": contract_id}}
            def derive(raw, contract_path=None):
                self.assertEqual(raw, before)
                self.assertEqual(contract_path, g.ROOT / record)
                return after
            with self.subTest(contract_id=contract_id), \
                    mock.patch.object(construction, "derive_board", side_effect=derive) as called, \
                    mock.patch.object(g, "_render_policy_image_delivery", return_value="# synthetic delivery guard\n"):
                g._policy_image_delivery_source_guards(plan, payloads)
                called.assert_called_once()

    def test_policy3_audit_sources_are_exact_and_opt_in(self):
        selected = {"target_files_metadata": {"policy_image_delivery": {
            "contract": {"contract_id": g.POLICY_IMAGE_DELIVERY_POLICY3_CONTRACT_ID}}}}
        unrelated = {"device/xiaomi/nezha/unrelated.txt": b"preserved sentinel"}
        default = dict(unrelated)
        g._bind_policy3_audit_sources({}, default)
        self.assertEqual(default, unrelated)
        g._policy3_audit_source_guards({}, default)
        payloads = dict(unrelated)
        g._bind_policy3_audit_sources(selected, payloads)
        self.assertEqual(set(payloads) - set(unrelated), {row["path"] for row in g.POLICY3_AUDIT_SOURCE_FILES})
        self.assertEqual(payloads["device/xiaomi/nezha/unrelated.txt"], b"preserved sentinel")
        g._policy3_audit_source_guards(selected, payloads)
        with self.assertRaises(g.CandidateError):
            g._policy3_audit_source_guards({}, payloads)
        with self.assertRaises(g.CandidateError):
            g._bind_policy3_audit_sources(selected, payloads)
        for row in g.POLICY3_AUDIT_SOURCE_FILES:
            missing = dict(payloads)
            del missing[row["path"]]
            with self.assertRaises(g.CandidateError):
                g._policy3_audit_source_guards(selected, missing)
            changed = dict(payloads)
            changed[row["path"]] += b"\n// mutation\n"
            with self.assertRaises(g.CandidateError):
                g._policy3_audit_source_guards(selected, changed)

    def test_policy3_missing_or_mutated_maintained_audit_source_fails(self):
        selected = {"target_files_metadata": {"policy_image_delivery": {
            "contract": {"contract_id": g.POLICY_IMAGE_DELIVERY_POLICY3_CONTRACT_ID}}}}
        with mock.patch.object(g, "ROOT", self.root):
            with self.assertRaises(g.CandidateError):
                g._bind_policy3_audit_sources(selected, {})
            for row in g.POLICY3_AUDIT_SOURCE_FILES:
                path = self.root / row["source"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes((ROOT / row["source"]).read_bytes())
            path.write_bytes(path.read_bytes() + b"\n// changed producer\n")
            with self.assertRaises(g.CandidateError):
                g._bind_policy3_audit_sources(selected, {})

if __name__ == "__main__":
    unittest.main()
