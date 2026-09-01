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
REPO = CONTROL_ROOT
from scripts import target_files_metadata_delivery_policy3 as m
TEMPLATE = json.loads((CONTROL_ROOT / m.IMAGE_CONTRACT).read_bytes())


def write(path, raw):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)


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


if __name__ == "__main__":
    unittest.main()
