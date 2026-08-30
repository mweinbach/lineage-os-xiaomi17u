"""Offline consumer tests for the explicit provider-v7 4 KiB successor."""

import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
from unittest import mock

from scripts import generate_device_tree as generator


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("current_page_candidate_fixtures", ROOT / "tests/test_generate_device_tree.py")
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)
CONFIG = b"CONFIG_PAGE_SHIFT=12\nCONFIG_ARM64_4K_PAGES=y\n# CONFIG_ARM64_16K_PAGES is not set\n# CONFIG_ARM64_64K_PAGES is not set\n"


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


class CurrentPageSizeProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.GenerateDeviceTreeTests.setUpClass()

    def setUp(self):
        self.fixture = fixtures.GenerateDeviceTreeTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.output = self.root / "artifacts/current-page-candidate"

    def inputs(self):
        values, verification, policy = self.fixture.provider_inputs(properties=True)
        receipt_path = values["kernel_receipt"]
        receipt = json.loads(receipt_path.read_text())
        config_path = receipt_path.parent / "reference/kernel.config"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_bytes(CONFIG)
        receipt["files"].append({"path": "reference/kernel.config", **identity(CONFIG), "readback_verified": True})
        receipt_path.write_text(json.dumps(receipt))
        profile = json.loads((ROOT / generator.PAGE_SIZE_PROFILE_V2_RECORD).read_text())
        image = next(row for row in receipt["files"] if row["path"] == "kernel/Image")
        profile["kernel"]["image"] = {key: image[key] for key in ("path", "sha256", "size_bytes")}
        profile["kernel"]["config"].update(identity(CONFIG))
        profile["kernel"]["receipt"] = identity(receipt_path.read_bytes())
        profile["providers"]["contract"].update(verification["contract"])
        profile["providers"]["receipt"] = {key: verification["receipt"][key] for key in ("sha256", "size_bytes")}
        path = self.root / generator.PAGE_SIZE_PROFILE_V2_RECORD
        path.write_text(json.dumps(profile, sort_keys=True, indent=2) + "\n")
        self.enterContext(mock.patch.object(generator, "PAGE_SIZE_PROFILE_V2_SHA256", identity(path.read_bytes())["sha256"]))
        values["page_size_profile"] = path
        return values, verification, policy

    def generate(self, values, output=None):
        return self.fixture.generate_provider(output or self.output, *values)

    def rewrite_profile(self, inputs, change):
        path = inputs["page_size_profile"]
        profile = json.loads(path.read_text())
        change(profile)
        path.write_text(json.dumps(profile, sort_keys=True, indent=2) + "\n")
        # Exercise semantic rejection below the fixed production trust anchor.
        generator.PAGE_SIZE_PROFILE_V2_SHA256 = identity(path.read_bytes())["sha256"]

    def test_both_public_profiles_keep_separate_closed_identities(self):
        for name, expected in ((generator.PAGE_SIZE_PROFILE_RECORD, generator.PAGE_SIZE_PROFILE_ID),
                               (generator.PAGE_SIZE_PROFILE_V2_RECORD, generator.PAGE_SIZE_PROFILE_V2_ID)):
            profile, _ = generator._page_size_profile_contract(ROOT / name)
            self.assertEqual(profile["profile_id"], expected)
        self.assertEqual(identity((ROOT / generator.PAGE_SIZE_PROFILE_RECORD).read_bytes()),
                         {"sha256": "9d180aeeb13e0c04a4f2726bf94ad6651e1052cb5f9162359c147814bc6607ca", "size_bytes": 13226})

    def test_successor_changes_only_product_and_its_new_descriptor(self):
        values = self.inputs()
        plain = dict(values[0])
        del plain["page_size_profile"]
        baseline = self.generate((plain, *values[1:]), self.root / "artifacts/default")
        plan = self.generate(values)
        before = {row["path"]: row for row in baseline["files"]}
        after = {row["path"]: row for row in plan["files"]}
        self.assertEqual(after.keys() - before.keys(), {generator.PAGE_SIZE_PROFILE_V2_RECORD.as_posix()})
        self.assertEqual([name for name in before if before[name] != after[name]],
                         [(generator.DEVICE_PATH / "generated/device-candidate.mk").as_posix()])
        stripped = copy.deepcopy(plan)
        del stripped["page_size_profile"]
        stripped["files"] = baseline["files"]
        self.assertEqual(stripped, baseline)
        self.assertEqual(generator.validate(self.output), plan)
        self.assertEqual(plan["page_size_profile"]["provider_payload_derivations"], values[1]["payload_derivations"])
        self.assertEqual(len(plan["page_size_profile"]["known_16k_incompatible_files"]), 22)
        self.assertEqual(plan["page_size_profile"]["product_settings"], generator.PAGE_SIZE_PRODUCT_SETTINGS)
        for purpose in ("target-files", "flash"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(self.output, purpose=purpose)

    def test_omitted_profile_does_not_read_or_select_either_record(self):
        values = self.inputs()
        values[0].pop("page_size_profile")
        with mock.patch.object(generator, "_page_size_profile_contract", side_effect=AssertionError("unselected profile read")):
            plan = self.generate(values)
            self.assertEqual(generator.validate(self.output), plan)
        self.assertNotIn("page_size_profile", plan)
        self.assertNotIn("PRODUCT_MAX_PAGE_SIZE_SUPPORTED", generator._render_product(plan))

    def test_unknown_or_crossed_portable_id_path_is_rejected_before_profile_read(self):
        plan = self.generate(self.inputs())
        for field, value in (("profile_id", "unknown"), ("profile_id", generator.PAGE_SIZE_PROFILE_ID),
                             ("path", generator.PAGE_SIZE_PROFILE_RECORD.as_posix()),
                             ("path", "../../outside.json"), ("path", "/outside.json")):
            changed = copy.deepcopy(plan)
            target = changed["page_size_profile"] if field == "profile_id" else changed["page_size_profile"]["contract"]
            target[field] = value
            (self.output / "admission.json").write_text(json.dumps(changed))
            with self.subTest(field=field, value=value), \
                    mock.patch.object(generator, "_page_size_profile_contract", side_effect=AssertionError("unexpected profile read")), \
                    self.assertRaises(generator.CandidateError):
                generator.validate(self.output)

    def test_unknown_descriptor_digest_and_crossed_id_are_rejected(self):
        values = self.inputs()
        path = values[0]["page_size_profile"]
        raw = path.read_bytes()
        for change in (lambda p: p.update(profile_id=generator.PAGE_SIZE_PROFILE_ID),
                       lambda p: p.update(profile_id="unreviewed")):
            path.write_bytes(raw)
            self.rewrite_profile(values[0], change)
            with self.assertRaises(generator.CandidateError):
                generator._page_size_profile_contract(path)
        path.write_bytes(raw + b" ")
        with self.assertRaisesRegex(generator.CandidateError, "reviewed contract"):
            generator._page_size_profile_contract(path)

    def test_old_provider_receipt_cannot_select_current_profile(self):
        values = self.inputs()
        old = json.loads((ROOT / generator.PAGE_SIZE_PROFILE_RECORD).read_bytes())
        self.rewrite_profile(values[0], lambda p: p["providers"].update(receipt=old["providers"]["receipt"]))
        with self.assertRaisesRegex(generator.CandidateError, "provider receipt or contract"):
            self.generate(values)

    def test_derivation_and_override_must_match_verified_current_provider(self):
        values = self.inputs()
        raw = values[0]["page_size_profile"].read_bytes()
        changes = {
            "missing_derivation": lambda p: p["providers"].update(payload_derivations=[]),
            "duplicate_derivation": lambda p: p["providers"]["payload_derivations"].append(copy.deepcopy(p["providers"]["payload_derivations"][0])),
            "stale_evidence": lambda p: p["providers"]["payload_derivations"][0]["evidence"].update(sha256="0" * 64),
            "different_recipe": lambda p: p["providers"]["payload_derivations"][0]["recipe"].update(changed_byte_file_offset=1),
            "missing_override": lambda p: p["providers"].update(effective_file_overrides=[]),
            "different_override": lambda p: p["providers"]["effective_file_overrides"][0].update(sha256="0" * 64),
            "different_layout": lambda p: p["providers"]["effective_file_overrides"][0].update(load_alignments=[16384] * 4),
            "different_module": lambda p: p["providers"]["effective_file_overrides"][0].update(module="nezha_framework_other"),
            "different_predecessor": lambda p: p["predecessor"].update(sha256="0" * 64),
        }
        for label, change in changes.items():
            values[0]["page_size_profile"].write_bytes(raw)
            self.rewrite_profile(values[0], change)
            with self.subTest(case=label), self.assertRaisesRegex(generator.CandidateError, "page-size"):
                self.generate(values)
            self.assertFalse(self.output.exists())

    def test_derived_payload_cannot_replace_original_inventory(self):
        values = self.inputs()
        def replace(profile):
            override = profile["providers"]["effective_file_overrides"][0]
            index = next(i for i, row in enumerate(profile["providers"]["files"]) if row["runtime_path"] == override["runtime_path"])
            profile["providers"]["files"][index] = copy.deepcopy(override)
        self.rewrite_profile(values[0], replace)
        with self.assertRaisesRegex(generator.CandidateError, "provider bytes differ"):
            self.generate(values)

    def test_current_profile_cannot_reuse_delivery_evidence(self):
        required = {name: "explicit" for name in (
            "target_files_source_contract", "target_files_metadata_receipt", "target_files_metadata_receipt_sha256",
            "policy_inputs_receipt", "framework_provider_policy_contract", "framework_provider_inputs_receipt",
            "framework_allocator_contract", "factory_boot_contract", "partition_metadata", "fstab_source",
            "dsp_policy_contract", "init_helper_capability_contract")}
        with mock.patch.object(generator, "_load_records", side_effect=AssertionError("input read")), \
                self.assertRaisesRegex(generator.CandidateError, "policy-image delivery requires"):
            generator.generate(self.output, record_paths={}, kernel_receipt=None, vendor_receipt=None,
                               variant="user", page_size_profile=ROOT / generator.PAGE_SIZE_PROFILE_V2_RECORD,
                               policy_image_delivery_contract=ROOT / generator.POLICY_IMAGE_DELIVERY_CONTRACT, **required)


if __name__ == "__main__":
    unittest.main()
