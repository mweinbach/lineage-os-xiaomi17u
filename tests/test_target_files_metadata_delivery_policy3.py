"""Offline released-selector tests; synthetic mutations stay in temporary roots."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

CONTROL_ROOT = Path(__file__).resolve().parents[1]
from scripts import target_files_metadata_delivery_policy3 as m
from support import write_file as write
TEMPLATE = json.loads((CONTROL_ROOT / m.IMAGE_CONTRACT).read_bytes())


def synthetic_admission():
    d = copy.deepcopy(TEMPLATE)
    # These bindings are inert test values, never native success records.
    inert = m.identity(b"synthetic evidence only\n")
    for part, size in (("vendor", 959709184), ("odm", 4767621120)):
        d["packaged_images"][part] = {"sha256": inert["sha256"], "size_bytes": size}
        d["expected_root_descriptors"][part] = {"kind": "hashtree", "partition": part}
    d["delivery_proof"] = d["selected_delivery_evidence"] = inert
    d["page_size_context"]["source_product"] = copy.deepcopy(d["page_size_context"]["production_source_product"])
    for role in ("raw_metadata_proof", "production_receipt", "production_review", "copy_contract"):
        d["policy3_basis"][role] = inert
    d["policy3_basis"]["copy_directory"] = "/work/validation/synthetic-policy3-copy"
    return d


class ClosedSelectionTests(unittest.TestCase):
    def test_all_five_historical_sources_are_byte_identical(self):
        self.assertEqual(len(m.CONTROL_TOOLS), 6)
        expected = {'scripts/target_files_metadata.py': {'sha256': '60e54729e5e9b3e261af45898752717eb7213b98aafb51beac8b96b848ee6184', 'size_bytes': 39730}, 'scripts/target_files_metadata_combined.py': {'sha256': '239a136605f858efe4de4ad310aa16a1d8b3a1739e17fa815029fa8de8f9d23c', 'size_bytes': 24503}, 'scripts/target_files_metadata_delivery.py': {'sha256': '2d9d4a51eda659523fd64d39de914fa8294d9480f20c46688736295467508144', 'size_bytes': 27341}, 'scripts/target_files_metadata_delivery_4k.py': {'sha256': '735732de59ac095832528fc5e99562527246cfaf1bc478d3ddc1f0a3ae996c56', 'size_bytes': 26635}, 'scripts/target_files_metadata_policy_images.py': {'sha256': 'a94c652998dc9b1d16b07c0da5e26e3bcca292b2941ca2adeaf4df907a8b457d', 'size_bytes': 32074}}
        self.assertEqual(set(m._old.CONTROL_TOOLS), set(expected))
        for name, ref in expected.items():
            self.assertEqual(m.identity((CONTROL_ROOT / name).read_bytes()), ref)

    def test_pending_selection_fails_before_private_paths_are_opened(self):
        with mock.patch.object(m, "IMAGE_CONTRACT_IDENTITY", None), mock.patch.object(m._factory, "real_directory", side_effect=AssertionError("private path touched")):
            for action in (
                lambda: m._controls(Path("/missing"), m.Reader(), image_contract=m.IMAGE_CONTRACT),
                lambda: m.stage_from_original("/missing", "/uncreated", expected_original_receipt=m._v1.ORIGINAL_ID["sha256"],
                    source_contract=m._factory.COMBINED_SOURCE_CONTRACT, image_contract=m.IMAGE_CONTRACT,
                    delivery_proof="/missing", current_policy_evidence="/missing", selected_delivery_evidence="/missing"),
                lambda: m.verify_bundle("/missing", expected_receipt="0" * 64),
            ):
                with self.subTest(action=action), self.assertRaisesRegex(m.TargetFilesMetadataError, "blocked"):
                    action()

    def test_unknown_or_incomplete_descriptor_never_reseals_itself(self):
        m._validate_admission(TEMPLATE, TEMPLATE["source_composition"])
        incomplete = copy.deepcopy(TEMPLATE)
        incomplete["selected_delivery_evidence"] = None
        with mock.patch.object(m, "IMAGE_CONTRACT_IDENTITY", m.identity(m.encoded(incomplete))):
            with self.assertRaises(m.TargetFilesMetadataError):
                m._validate_admission(incomplete, incomplete["source_composition"])
        d = synthetic_admission()
        with mock.patch.object(m, "IMAGE_CONTRACT_IDENTITY", m.identity(m.encoded(d))):
            altered = copy.deepcopy(d)
            altered["contract_id"] = "nezha-4k-final-leaf-metadata-delivery-v3"
            with self.assertRaisesRegex(m.TargetFilesMetadataError, "reviewed release"):
                m._validate_admission(altered, d["source_composition"])

    def test_structural_refusals_remain_after_explicit_synthetic_pin(self):
        mutations = {
            "16k setting": lambda d: d["page_size_context"]["product_settings"].update(PRODUCT_MAX_PAGE_SIZE_SUPPORTED=16384),
            "disabled check": lambda d: d["page_size_context"]["product_settings"].update(PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE=False),
            "Boolean size": lambda d: d["policy3_basis"].update(source_count=True),
            "old private policy": lambda d: d["policy3_basis"]["required_policy_inputs"].update(sha256="0" * 64),
            "metadata missing": lambda d: d["metadata_members"].pop(),
            "metadata duplicate": lambda d: d["metadata_members"].__setitem__(1, d["metadata_members"][0]),
            "source missing": lambda d: d["policy3_basis"]["copy_verified_inputs"]["source"].pop(),
            "runtime missing": lambda d: d["policy3_basis"]["copy_verified_inputs"]["runtime"].pop(),
            "source duplicate": lambda d: d["policy3_basis"]["copy_verified_inputs"]["source"].__setitem__(1, d["policy3_basis"]["copy_verified_inputs"]["source"][0]),
            "source traversal": lambda d: d["page_size_context"]["source_product"].update(path="device/../product.mk"),
            "readiness": lambda d: d["scope"].update(complete_rom_ready=True),
        }
        for name, mutate in mutations.items():
            d = synthetic_admission()
            mutate(d)
            with self.subTest(name=name), mock.patch.object(m, "IMAGE_CONTRACT_IDENTITY", m.identity(m.encoded(d))):
                with self.assertRaises(m.TargetFilesMetadataError):
                    m._validate_admission(d, d["source_composition"])

    def test_real_controls_and_ten_source_composition_with_inert_release(self):
        d = synthetic_admission()
        source_reader = m.Reader()
        _, _, required_controls = m._controls(
            CONTROL_ROOT, source_reader,
            source_contract=m._factory.COMBINED_SOURCE_CONTRACT,
            image_contract=m.IMAGE_CONTRACT,
        )
        source_reader.recheck()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp).resolve() / "controls"
            # Materialize only the declared controls, never the private workspace.
            for name, raw in required_controls.items():
                write(root / name, raw)
            write(root / m.IMAGE_CONTRACT, m.encoded(d))
            with mock.patch.object(m, "IMAGE_CONTRACT_IDENTITY", m.identity(m.encoded(d))):
                reader = m.Reader()
                _, composition, controls = m._controls(root, reader, source_contract=m._factory.COMBINED_SOURCE_CONTRACT, image_contract=m.IMAGE_CONTRACT)
                reader.recheck()
                self.assertEqual(composition, TEMPLATE["source_composition"])
                self.assertEqual(len(composition["final_source_files"]), 10)
                self.assertTrue(set(m.CONTROL_TOOLS).issubset(controls))
                self.assertEqual(controls, {**required_controls, m.IMAGE_CONTRACT: m.encoded(d)})
                bad = copy.deepcopy(d)
                bad["policy_inputs"]["actual_compiler_inputs"][2]["sha256"] = "0" * 64
                write(root / m.IMAGE_CONTRACT, m.encoded(bad))
                with mock.patch.object(m, "IMAGE_CONTRACT_IDENTITY", m.identity(m.encoded(bad))):
                    with self.assertRaisesRegex(m.TargetFilesMetadataError, "compiler input identity"):
                        m._controls(root, m.Reader(), source_contract=m._factory.COMBINED_SOURCE_CONTRACT, image_contract=m.IMAGE_CONTRACT)

    def test_six_source_runtime_is_standalone_and_refuses_missing_bundle(self):
        controls = {name: (CONTROL_ROOT / name).read_bytes() for name in m.CONTROL_TOOLS}
        first = m.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]
        self.assertEqual(first, m.runtime_tool_payloads(controls)["tools/target_files_metadata.py"])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "tools/target_files_metadata.py"
            write(path, first)
            run = subprocess.run([sys.executable, "-I", "-S", "-B", str(path), "verify", "--bundle", str(Path(temp) / "missing"),
                "--expected-receipt", "0" * 64, "--source-contract", m._factory.COMBINED_SOURCE_CONTRACT,
                "--image-contract", m.IMAGE_CONTRACT], capture_output=True, timeout=20)
            self.assertNotEqual(run.returncode, 0)
            self.assertTrue(run.stderr)
            self.assertEqual(run.stdout, b"")
            self.assertFalse((Path(temp) / "controls").exists())

    def test_modified_historical_runtime_code_is_rejected(self):
        controls = {name: (CONTROL_ROOT / name).read_bytes() for name in m.CONTROL_TOOLS}
        for name in m._old.CONTROL_TOOLS:
            changed = dict(controls)
            changed[name] += b"\n# not the preserved source\n"
            with self.subTest(name=name), self.assertRaises((ValueError, m.TargetFilesMetadataError)):
                m.runtime_tool_payloads(changed)


class EvidenceShapeTests(unittest.TestCase):
    def setUp(self):
        self.d = synthetic_admission()
        basis = self.d["policy3_basis"]
        self.proof = {"schema_version": 1, "operation": m.PROOF_OPERATION,
            "derivation_verified": True, "bound_evidence_rehashed": True,
            **{key: self.d[key] for key in ("factory_package_sha256", "original_images", "packaged_images",
                "source_composition", "metadata_members", "expected_root_descriptors", "policy_inputs", "current_policy_build_evidence", "scope")},
            "metadata_count": 205, "metadata_bytes": 6460780, "original_metadata_receipt": m._v1.ORIGINAL_ID,
            "raw_metadata_proof": basis["raw_metadata_proof"], "production_receipt": basis["production_receipt"],
            "production_independent_review": basis["production_review"],
            "leaf_derivations": {part + "-" + str(n): {"image": {"path": "/work/validation/synthetic-footer/" + part + "-" + str(n) + ".img",
                **self.d["packaged_images"][part]}} for part in ("vendor", "odm") for n in (1, 2)}}
        self.d["delivery_proof"] = m.identity(m.encoded(self.proof))
        total = sum(row["size_bytes"] for row in self.d["packaged_images"].values())
        self.selected = {"schema_version": 1, "operation": m.COPY_OPERATION,
            "status": "prepared-private-validation-bundle", "passed": True, "skipped": 0,
            "input_contract": basis["copy_contract"], "scope": m._v2.COPY_SCOPE,
            "controls": {"current_policy": {"path": "current-policy.json", **m.CURRENT_REPORT_ID},
                         "delivery_proof": {"path": "delivery-proof.json", **self.d["delivery_proof"]}},
            "output_directory": basis["copy_directory"],
            "selected_copies": {part: {"source": self.proof["leaf_derivations"][part + "-1"]["image"],
                "destination": {"path": basis["copy_directory"] + "/images/" + part + ".img", **self.d["packaged_images"][part]},
                "independent_inode": True, "source_rehashed_before_and_after": True, "destination_rehashed_after_copy": True} for part in ("vendor", "odm")},
            "originals": {part: {"path": "/work/evolution/vendor/xiaomi/nezha/proprietary/images/" + part + ".img",
                **self.d["original_images"][part], "rehashed_before_and_after": True} for part in ("vendor", "odm")},
            "verified_inputs": {name: {"count": len(rows), "identities": rows, "rehashed_before_and_after": True}
                for name, rows in basis["copy_verified_inputs"].items()},
            "provenance": {"production_receipt": self.proof["production_receipt"],
                "production_independent_review": self.proof["production_independent_review"], "raw_metadata_proof": self.proof["raw_metadata_proof"],
                "source_composition": m.identity(m.encoded(self.d["source_composition"])),
                "metadata_members": {**m.identity(m.encoded(self.d["metadata_members"])), "count": 205, "payload_bytes": 6460780}},
            "disk": {"copy_bytes": total, "reserve_bytes": 1 << 30,
                     "available_before_bytes": total + (2 << 30), "available_after_bytes": 2 << 30}}
        self.d["selected_delivery_evidence"] = m.identity(m.encoded(self.selected))

    def test_two_complete_footer_passes_and_fresh_independent_copy_shape(self):
        self.assertEqual(m._validate_proof(m.encoded(self.proof), self.d), self.proof)
        self.assertEqual(m._validate_selected(m.encoded(self.selected), self.d, {}, self.proof), self.selected)

    def test_missing_or_divergent_second_footer_pass_is_rejected(self):
        for mode in ("missing", "different"):
            proof = copy.deepcopy(self.proof)
            if mode == "missing":
                del proof["leaf_derivations"]["odm-2"]
            else:
                proof["leaf_derivations"]["odm-2"]["image"]["sha256"] = "0" * 64
            admission = copy.deepcopy(self.d)
            admission["delivery_proof"] = m.identity(m.encoded(proof))
            with self.subTest(mode=mode), self.assertRaises(m.TargetFilesMetadataError):
                m._validate_proof(m.encoded(proof), admission)

    def test_copy_cannot_omit_protection_or_reuse_original_inode(self):
        mutations = (
            lambda x: x["verified_inputs"]["source"].update(count=204),
            lambda x: x["verified_inputs"]["policy"]["identities"].pop(),
            lambda x: x["verified_inputs"]["runtime"].update(rehashed_before_and_after=False),
            lambda x: x["selected_copies"]["odm"].update(independent_inode=False),
            lambda x: x.update(operation=m._v2.COPY_OPERATION),
        )
        for mutate in mutations:
            selected = copy.deepcopy(self.selected)
            mutate(selected)
            admission = copy.deepcopy(self.d)
            admission["selected_delivery_evidence"] = m.identity(m.encoded(selected))
            with self.subTest(mutate=mutate), self.assertRaises(m.TargetFilesMetadataError):
                m._validate_selected(m.encoded(selected), admission, {}, self.proof)


class ActualPackagedGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.target = Path(self.temp.name).resolve()
        self.admission = synthetic_admission()
        self.current = {"test": "synthetic packaged input test, no native claim"}
        self.current_pin = m.identity(m.encoded(self.current))
        self.rows = self.admission["policy_inputs"]["actual_compiler_inputs"]
        self.bodies = {}
        for index in (0, 1, 2, 3, 4, 5, 9):
            raw = ("(synthetic_input_%d)\n" % index).encode()
            self.rows[index].update(m.identity(raw))
            part, suffix = self.rows[index]["runtime_path"].lstrip("/").split("/", 1)
            path = part.upper() + "/" + suffix
            self.bodies[path] = raw
            write(self.target / path, raw)
        framework, sidecars = m._v2._policy_layout(self.admission)
        for sidecar, name in zip(sidecars, ("plat", "system_ext", "product")):
            first, second = sidecar["ordered_target_files_inputs"]
            raw = (hashlib.sha256(self.bodies[first] + self.bodies[second]).hexdigest() + "\n").encode()
            self.admission["policy_inputs"]["exact_five_replacement_identities"]["odm"]["/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256"] = m.identity(raw)
            write(self.target / sidecar["framework_sidecar_path"], raw)

    def gate(self, product=True):
        reader = m.Reader()
        reader.policy3_product_verified = product
        with mock.patch.object(m, "CURRENT_REPORT_ID", self.current_pin):
            result = m._policy_gate(self.admission, self.target, reader, self.current)
        reader.recheck()
        return result

    def test_all_seven_inputs_and_three_actual_sidecars_are_required(self):
        result = self.gate()
        self.assertEqual(len(result["framework_inputs"]), 7)
        self.assertEqual(len(result["sidecars"]), 3)
        self.assertTrue(result["actual_policy3_product_source_verified"])
        self.assertFalse(result["complete_rom_ready"])
        self.assertFalse(result["odm_selinux_tree_projected"])
        (self.target / "SYSTEM_EXT/etc/selinux/system_ext_sepolicy_and_mapping.sha256").unlink()
        with self.assertRaises((OSError, m.TargetFilesMetadataError)):
            self.gate()

    def test_wrong_product_and_wrong_digest_are_rejected(self):
        with self.assertRaisesRegex(m.TargetFilesMetadataError, "product source"):
            self.gate(False)
        path = self.target / "SYSTEM/etc/selinux/plat_sepolicy_and_mapping.sha256"
        path.write_bytes(b"0" * 64 + b"\n")
        with self.assertRaises(m.TargetFilesMetadataError):
            self.gate()

    def test_missing_genfs_and_swapped_input_order_are_rejected(self):
        path = self.target / "SYSTEM/etc/selinux/plat_sepolicy_genfs_202504.cil"
        raw = path.read_bytes()
        path.unlink()
        with self.assertRaises((OSError, m.TargetFilesMetadataError)):
            self.gate()
        path.write_bytes(raw)
        self.rows[0], self.rows[1] = self.rows[1], self.rows[0]
        with self.assertRaises(m.TargetFilesMetadataError):
            self.gate()

    def test_install_report_cannot_promote_an_incomplete_gate(self):
        reader = m.Reader()
        for result in (None, {}, {"operation": "verify-actual-packaged-policy3-policy-v1", "seven_actual_framework_inputs_verified": True}):
            reader.current_policy_result = result
            with self.assertRaisesRegex(m.TargetFilesMetadataError, "before metadata publication"):
                m._installation_report({}, "0" * 64, reader)


class ChecksumSuccessorTests(unittest.TestCase):
    """Public controls and inert fixtures only; no native execution or evidence."""

    def setUp(self):
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native process forbidden")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("shell execution forbidden")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network forbidden")))
        from scripts import target_files_metadata_checksum
        self.c = target_files_metadata_checksum
        self.base = copy.deepcopy(TEMPLATE["source_composition"])
        self.current = self.c._derive_composition(self.base)

    def controls(self):
        reader = self.c.Reader()
        result = self.c._controls(CONTROL_ROOT, reader,
            source_contract=self.c.SOURCE_CONTRACT, image_contract=self.c.IMAGE_CONTRACT)
        reader.recheck()
        return result

    def temporary_root(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        return Path(temporary.name).resolve()

    def selector_bundle(self, composition, *, descriptor=None, mutate=None):
        bundle = self.temporary_root()
        reference = composition["contracts"][-1]
        raw = (CONTROL_ROOT / reference["path"]).read_bytes() if descriptor is None else descriptor
        receipt = {"source_composition": copy.deepcopy(composition), "bundle_files": [
            {"path": "controls/" + reference["path"], **self.c.identity(raw)}]}
        if mutate is not None:
            mutate(receipt)
        write(bundle / "controls" / reference["path"], raw)
        write(bundle / self.c.RECEIPT, self.c.encoded(receipt))
        return bundle, self.c.identity(self.c.encoded(receipt))["sha256"]

    def original_fixture(self):
        admission = synthetic_admission()
        files = {}
        for index, member in enumerate(admission["metadata_members"]):
            # Keep the public 205-path/byte-count shape, never use private payloads.
            raw = bytes([97 + index % 26]) * member["payload"]["size_bytes"]
            member["payload"] = self.c.identity(raw)
            row = {key: member[key] for key in ("target_path", "partition", "path", "kind")}
            row.update(self.c.identity(raw))
            files[member["target_path"]] = (row, raw)
        original = {"schema_version": 1, "operation": "stage-factory-target-files-metadata",
            "profile": {"fixture": "synthetic original receipt only"},
            "images": copy.deepcopy(admission["original_images"]), "source_composition": self.base,
            "files": [files[path][0] for path in sorted(files)],
            "property_closure": {"fixture": "synthetic property closure"}, "scope": {"metadata_only": True}}
        raw = self.c.encoded(original)
        receipt = copy.deepcopy(original)
        receipt["source_composition"] = copy.deepcopy(self.current)
        original_check = self.c._old._impl["_check_original"]
        self.enterContext(mock.patch.dict(original_check.__globals__, ORIGINAL_ID=self.c.identity(raw)))
        self.enterContext(mock.patch.object(self.c._old, "IMAGE_CONTRACT_IDENTITY",
            self.c.identity(self.c.encoded(admission))))
        return raw, receipt, files, admission

    def test_public_composition_adds_only_the_pinned_checksum_transition(self):
        result = self.c.compose_sources(CONTROL_ROOT, source_contract=self.c.SOURCE_CONTRACT)
        wanted = copy.deepcopy(self.base)
        descriptor = json.loads((CONTROL_ROOT / self.c.SOURCE_CONTRACT).read_bytes())
        wanted["contracts"].append({"path": self.c.SOURCE_CONTRACT, **self.c.SOURCE_CONTRACT_IDENTITY})
        wanted["ordered_patches"].append(descriptor["patch"])
        wanted["source_transitions"].append({"patch": descriptor["patch"], **descriptor["source_file"]})
        for row in wanted["final_source_files"]:
            if row["path"] == self.c.CORE:
                row.update(descriptor["source_file"]["after"])
        self.assertEqual(result, wanted)
        self.assertEqual(self.base, TEMPLATE["source_composition"])
        self.assertEqual(self.c._old.compose_sources(CONTROL_ROOT,
            source_contract=self.c.BASE_SOURCE_CONTRACT), self.base)

    def test_public_composition_rejects_missing_old_and_unknown_selectors(self):
        for selector in (None, self.c.BASE_SOURCE_CONTRACT, "patches/evolution/unknown-checksum.json"):
            with self.subTest(selector=selector), self.assertRaises((OSError, self.c.TargetFilesMetadataError)):
                self.c.compose_sources(CONTROL_ROOT, source_contract=selector)

    def test_derive_composition_rejects_changed_base_core_and_unrelated_sources(self):
        mutations = (
            lambda d: next(row for row in d["final_source_files"] if row["path"] == self.c.CORE).update(sha256="0" * 64),
            lambda d: next(row for row in d["final_source_files"] if row["path"] != self.c.CORE).update(size_bytes=1),
            lambda d: d["ordered_patches"].reverse(),
            lambda d: d["contracts"].pop(),
            lambda d: d.update(whole_source_tree_verified=True),
        )
        for mutate in mutations:
            changed = copy.deepcopy(self.base)
            mutate(changed)
            with self.subTest(mutate=mutate), self.assertRaisesRegex(self.c.TargetFilesMetadataError, "predecessor composition"):
                self.c._derive_composition(changed)

    def test_controls_preserve_original_bytes_and_add_exactly_three_members(self):
        reader = m.Reader()
        old_profile, old_composition, old_controls = m._controls(CONTROL_ROOT, reader,
            source_contract=self.c.BASE_SOURCE_CONTRACT, image_contract=m.IMAGE_CONTRACT)
        reader.recheck()
        profile, composition, controls = self.controls()
        self.assertEqual(profile, old_profile)
        self.assertEqual(old_composition, self.base)
        self.assertEqual(composition, self.current)
        self.assertEqual(set(controls) - set(old_controls),
            {self.c.ADAPTER, self.c.SOURCE_CONTRACT, self.c.PATCH["path"]})
        self.assertEqual({name: controls[name] for name in old_controls}, old_controls)
        for path, pin in ((self.c.SOURCE_CONTRACT, self.c.SOURCE_CONTRACT_IDENTITY),
                          (self.c.PATCH["path"], self.c.PATCH), (self.c.ADAPTER, self.c._self_identity)):
            self.assertEqual(self.c.identity(controls[path]), self.c.expected(pin))

    def test_each_added_control_is_hash_bound(self):
        controls = self.controls()[2]
        root = self.temporary_root()
        for name, raw in controls.items():
            write(root / name, raw)
        for name in (self.c.ADAPTER, self.c.SOURCE_CONTRACT, self.c.PATCH["path"]):
            write(root / name, controls[name] + b"\n")
            with self.subTest(name=name), self.assertRaises(self.c.TargetFilesMetadataError):
                self.c._controls(root, self.c.Reader(), source_contract=self.c.SOURCE_CONTRACT,
                    image_contract=self.c.IMAGE_CONTRACT)
            write(root / name, controls[name])

    def test_successor_runtime_freezes_all_six_original_sources(self):
        controls = self.controls()[2]
        self.assertEqual(self.c.identity(m.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]),
            self.c.PREDECESSOR_RUNTIME_ID)
        self.assertEqual(tuple(self.c.CONTROL_TOOLS[:-1]), m.CONTROL_TOOLS)
        for name in m.CONTROL_TOOLS:
            self.assertEqual(controls[name], (CONTROL_ROOT / name).read_bytes())
            changed = dict(controls)
            changed[name] += b"\n# changed historical code\n"
            with self.subTest(name=name), self.assertRaises((ValueError, self.c.TargetFilesMetadataError)):
                self.c.runtime_tool_payloads(changed)

    def test_runtime_refuses_modified_extension_and_missing_sources(self):
        controls = self.controls()[2]
        changed = dict(controls)
        changed[self.c.ADAPTER] += b"\n"
        with self.assertRaisesRegex(self.c.TargetFilesMetadataError, "adapter differs"):
            self.c.runtime_tool_payloads(changed)
        for name in self.c.CONTROL_TOOLS:
            changed = dict(controls)
            del changed[name]
            with self.subTest(name=name), self.assertRaisesRegex(self.c.TargetFilesMetadataError, "source missing"):
                self.c.runtime_tool_payloads(changed)

    def test_standalone_runtime_is_deterministic_without_code_file_reads(self):
        controls = self.controls()[2]
        payloads = self.c.runtime_tool_payloads(controls)
        self.assertEqual(payloads, self.c.runtime_tool_payloads(controls))
        self.assertEqual(list(payloads), ["tools/target_files_metadata.py"])
        namespace = {"__name__": "isolated_checksum_test", "__file__": str(self.temporary_root() / "tools/checker.py")}
        with mock.patch("os.open", side_effect=AssertionError("external code read forbidden")):
            exec(compile(payloads["tools/target_files_metadata.py"], namespace["__file__"], "exec"), namespace)
        self.assertTrue(namespace["NATIVE"])
        self.assertEqual(namespace["compose_sources"](CONTROL_ROOT, source_contract=self.c.SOURCE_CONTRACT), self.current)
        self.assertEqual(namespace["runtime_tool_payloads"](controls), payloads)

    def test_actual_install_namespace_selects_the_new_receipt_contract(self):
        selector = self.c._install_namespace["_selected_receipt_source_contract"]
        self.assertIs(selector, self.c._selected_receipt_source_contract)
        self.assertIs(selector.__code__, self.c._selector_original.__code__)
        before = self.c._selector_original.__globals__
        self.assertEqual({key for key in before if before[key] is not self.c._selector_globals[key]},
            {"COMBINED_CONTRACTS", "COMBINED_SOURCE_CONTRACT", "COMBINED_SOURCE_ID"})
        bundle, digest = self.selector_bundle(self.current)
        self.assertEqual(selector(bundle, digest), self.c.SOURCE_CONTRACT)
        target = self.temporary_root()
        (target / "META").mkdir()
        stop = mock.Mock(side_effect=RuntimeError("stop after authenticated source selection"))
        with mock.patch.dict(self.c._install_namespace, verify_bundle=stop):
            with self.assertRaisesRegex(RuntimeError, "authenticated source selection"):
                self.c.install(bundle, target, expected_receipt=digest, source_tree=target / "unused-source")
        self.assertEqual(stop.call_args.kwargs["source_contract"], self.c.SOURCE_CONTRACT)

    def test_install_selector_rejects_old_contract_hash_inventory_and_id(self):
        selector = self.c._install_namespace["_selected_receipt_source_contract"]
        bundle, digest = self.selector_bundle(self.base)
        with self.assertRaises(self.c.TargetFilesMetadataError):
            selector(bundle, digest)
        for mutate in (
            lambda d: d["source_composition"]["contracts"][-1].update(sha256="0" * 64),
            lambda d: d["bundle_files"].clear(),
            lambda d: d["bundle_files"].append(copy.deepcopy(d["bundle_files"][0])),
        ):
            bundle, digest = self.selector_bundle(self.current, mutate=mutate)
            with self.subTest(mutate=mutate), self.assertRaises(self.c.TargetFilesMetadataError):
                selector(bundle, digest)
        descriptor = json.loads((CONTROL_ROOT / self.c.SOURCE_CONTRACT).read_bytes())
        descriptor["contract_id"] = "unrecognized-checksum-contract"
        raw = self.c.encoded(descriptor)
        composition = copy.deepcopy(self.current)
        composition["contracts"][-1].update(self.c.identity(raw))
        bundle, digest = self.selector_bundle(composition, descriptor=raw)
        with self.assertRaisesRegex(self.c.TargetFilesMetadataError, "copied source contract"):
            selector(bundle, digest)

    def test_original_check_uses_only_a_historical_source_comparison_view(self):
        raw, receipt, files, admission = self.original_fixture()
        snapshot = copy.deepcopy(receipt)
        checked = mock.Mock(wraps=self.c._old._impl["_check_original"])
        with mock.patch.dict(self.c._old._impl, _check_original=checked):
            self.c._check_original(raw, receipt, files, admission)
        checked.assert_called_once()
        self.assertEqual(checked.call_args.args[1], dict(receipt, source_composition=self.base))
        self.assertIs(checked.call_args.args[2], files)
        self.assertIs(checked.call_args.args[3], admission)
        self.assertEqual(receipt, snapshot)

    def test_original_check_preserves_every_other_semantic_field(self):
        raw, receipt, files, admission = self.original_fixture()
        for key in ("profile", "images", "files", "property_closure", "scope"):
            changed = copy.deepcopy(receipt)
            changed[key] = {"fixture": "tampered " + key}
            with self.subTest(key=key), self.assertRaisesRegex(self.c.TargetFilesMetadataError, "semantics differ: " + key):
                self.c._check_original(raw, changed, files, admission)

    def test_original_check_refuses_current_source_receipt_and_payload_tampering(self):
        raw, receipt, files, admission = self.original_fixture()
        for role in ("core", "unrelated"):
            changed = copy.deepcopy(receipt)
            row = next(row for row in changed["source_composition"]["final_source_files"]
                if (row["path"] == self.c.CORE) == (role == "core"))
            row["sha256"] = "0" * 64
            with self.subTest(role=role), self.assertRaisesRegex(self.c.TargetFilesMetadataError, "exact checksum successor"):
                self.c._check_original(raw, changed, files, admission)
        with self.assertRaisesRegex(self.c.TargetFilesMetadataError, "original metadata receipt"):
            self.c._check_original(raw + b"\n", receipt, files, admission)
        changed_files = dict(files)
        name = next(iter(changed_files))
        row, body = changed_files[name]
        changed_files[name] = (row, b"!" + body[1:])
        with self.assertRaisesRegex(self.c.TargetFilesMetadataError, "original metadata bytes"):
            self.c._check_original(raw, receipt, changed_files, admission)

    def test_inherited_packaged_policy_gate_remains_identical_and_fail_closed(self):
        fixture = ActualPackagedGateTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        expected_result = fixture.gate()
        with mock.patch.object(self.c._old, "CURRENT_REPORT_ID", fixture.current_pin):
            reader = self.c.Reader()
            reader.policy3_product_verified = True
            gate = self.c._impl["_current_policy_gate"]
            self.assertEqual(gate(fixture.admission, fixture.target, reader, fixture.current), expected_result)
            reader.recheck()
            with self.assertRaisesRegex(self.c.TargetFilesMetadataError, "product source"):
                gate(fixture.admission, fixture.target, self.c.Reader(), fixture.current)
            (fixture.target / "SYSTEM/etc/selinux/plat_sepolicy_and_mapping.sha256").write_bytes(b"0" * 64 + b"\n")
            with self.assertRaises(self.c.TargetFilesMetadataError):
                gate(fixture.admission, fixture.target, reader, fixture.current)

    def test_frozen_function_changes_are_only_two_counted_stage_selectors(self):
        import ast
        old_source, new_source = self.c._old._definitions(), self.c._definitions()
        def definitions(source):
            return {node.name: ast.dump(node) for node in ast.parse(source).body if isinstance(node, ast.FunctionDef)}
        before, after = definitions(old_source), definitions(new_source)
        self.assertEqual(set(before), set(after))
        self.assertEqual({name for name in before if before[name] != after[name]}, {"stage_from_original"})
        wanted = old_source
        self.assertEqual(len(self.c.STAGE_TRANSFORMS), 2)
        for old, new in self.c.STAGE_TRANSFORMS:
            self.assertEqual(wanted.count(old), 1)
            wanted = wanted.replace(old, new)
            for changed in (old_source.replace(old, old.replace("source_contract=", "unrecognized_selector=")),
                            old_source + "\n" + old_source):
                with self.subTest(boundary=old), mock.patch.object(self.c._old, "_definitions", return_value=changed):
                    with self.assertRaises(self.c.TargetFilesMetadataError):
                        self.c._definitions()
        self.assertEqual(new_source, wanted)


if __name__ == "__main__":
    unittest.main()
