"""Offline admission tests for the explicit stock-kernel 4 KiB capability."""

import copy
import hashlib
import importlib.util
import io
import json
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import unittest
from unittest import mock

from scripts import generate_device_tree as generator


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("page_size_candidate_fixtures", ROOT / "tests/test_generate_device_tree.py")
fixtures = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixtures)
CONFIG = b"CONFIG_PAGE_SHIFT=12\nCONFIG_ARM64_4K_PAGES=y\n# CONFIG_ARM64_16K_PAGES is not set\n# CONFIG_ARM64_64K_PAGES is not set\n"


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


class PageSizeProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.GenerateDeviceTreeTests.setUpClass()

    def setUp(self):
        # Reuse the established small input fixture without collecting its tests
        # a second time. Only its external proprietary verification is mocked.
        self.fixture = fixtures.GenerateDeviceTreeTests("runTest")
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        self.output = self.root / "artifacts/page-size-candidate"

    def inputs(self, config=CONFIG):
        inputs, verification, policy = self.fixture.provider_inputs(properties=True)
        receipt_path = inputs["kernel_receipt"]
        receipt = json.loads(receipt_path.read_text())
        config_path = receipt_path.parent / "reference/kernel.config"
        config_path.parent.mkdir(exist_ok=True)
        config_path.write_bytes(config)
        receipt["files"] = [row for row in receipt["files"] if row["path"] != "reference/kernel.config"]
        receipt["files"].append({"path": "reference/kernel.config", **identity(config), "readback_verified": True})
        receipt_path.write_text(json.dumps(receipt))
        profile = json.loads((ROOT / generator.PAGE_SIZE_PROFILE_RECORD).read_text())
        image_row = next(row for row in receipt["files"] if row["path"] == "kernel/Image")
        profile["kernel"]["image"] = {key: image_row[key] for key in ("path", "sha256", "size_bytes")}
        profile["kernel"]["config"].update(identity(config))
        profile["kernel"]["receipt"] = identity(receipt_path.read_bytes())
        profile["providers"]["contract"].update(verification["contract"])
        profile["providers"]["receipt"] = {key: verification["receipt"][key] for key in ("sha256", "size_bytes")}
        path = self.root / generator.PAGE_SIZE_PROFILE_RECORD
        path.write_text(json.dumps(profile, indent=2, sort_keys=True) + "\n")
        self.enterContext(mock.patch.object(generator, "PAGE_SIZE_PROFILE_SHA256", identity(path.read_bytes())["sha256"]))
        inputs["page_size_profile"] = path
        return inputs, verification, policy

    def rewrite_profile(self, inputs, mutate):
        path = inputs["page_size_profile"]
        value = json.loads(path.read_text())
        mutate(value)
        path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
        # Like the existing candidate tests, advance the public trust anchor only
        # to exercise semantic rejection beneath its production digest check.
        generator.PAGE_SIZE_PROFILE_SHA256 = identity(path.read_bytes())["sha256"]

    def generate(self, values, output=None):
        return self.fixture.generate_provider(output or self.output, *values)

    def reseal_candidate(self, plan, name, raw):
        (self.output / name).write_bytes(raw)
        next(row for row in plan["files"] if row["path"] == name).update(identity(raw))
        (self.output / "admission.json").write_text(json.dumps(plan))

    def test_reviewed_profile_pins_exact_kernel_and_all_provider_gaps(self):
        profile, bound = generator._page_size_profile_contract(ROOT / generator.PAGE_SIZE_PROFILE_RECORD)
        self.assertEqual(bound["sha256"], generator.PAGE_SIZE_PROFILE_SHA256)
        self.assertEqual(profile["kernel"]["image"]["sha256"], "4441e484563158ae961f0938462fa9a6ba54024a800329c4339f39a5ac8e35c8")
        self.assertEqual(profile["kernel"]["runtime_page_size_bytes"], 4096)
        self.assertEqual(len(profile["providers"]["files"]), 26)
        self.assertEqual(sum(not row["compatible_with_16k_alignment"] for row in profile["providers"]["files"]), 22)
        provider_profile = json.loads((ROOT / generator.FRAMEWORK_PROVIDER_INPUT_RECORD).read_text())
        selected = {row["runtime_path"]: {key: row[key] for key in ("module", "sha256", "size_bytes")}
                    for row in provider_profile["files"] if row["kind"] in ("binary", "shared_library")}
        self.assertEqual(selected, {row["runtime_path"]: {key: row[key] for key in ("module", "sha256", "size_bytes")}
                                    for row in profile["providers"]["files"]})

    def test_explicit_profile_adds_only_product_and_contract_payloads(self):
        values = self.inputs()
        ordinary = dict(values[0])
        del ordinary["page_size_profile"]
        baseline = self.generate((ordinary, *values[1:]), self.root / "artifacts/baseline")
        plan = self.generate(values)
        old_files = {row["path"]: row for row in baseline["files"]}
        new_files = {row["path"]: row for row in plan["files"]}
        self.assertEqual(set(new_files) - set(old_files), {generator.PAGE_SIZE_PROFILE_RECORD.as_posix()})
        self.assertEqual([name for name in old_files if old_files[name] != new_files[name]],
                         [(generator.DEVICE_PATH / "generated/device-candidate.mk").as_posix()])
        stripped = copy.deepcopy(plan)
        del stripped["page_size_profile"]
        stripped["files"] = baseline["files"]
        self.assertEqual(stripped, baseline)
        product = (self.output / generator.DEVICE_PATH / "generated/device-candidate.mk").read_text()
        for name, value in generator.PAGE_SIZE_PRODUCT_SETTINGS.items():
            self.assertEqual(product.count(f"{name} := {str(value).lower()}\n"), 1)
        self.assertEqual(generator.validate(self.output), plan)
        self.assertFalse(plan["page_size_profile"]["scope"]["compatibility_16k_verified"])
        self.assertFalse(plan["page_size_profile"]["scope"]["vsr_compatibility_verified"])

    def test_omitted_profile_is_not_read_or_inferred(self):
        values = list(self.inputs())
        values[0].pop("page_size_profile")
        with mock.patch.object(generator, "_page_size_profile_contract", side_effect=AssertionError("unselected profile read")):
            plan = self.generate(values)
            self.assertEqual(generator.validate(self.output), plan)
        self.assertNotIn("page_size_profile", plan)
        self.assertNotIn("PRODUCT_MAX_PAGE_SIZE_SUPPORTED", generator._render_product(plan))

    def test_page_profile_requires_explicit_provider_capability_before_input_reads(self):
        with mock.patch.object(generator, "_load_records", side_effect=AssertionError("input read")):
            with self.assertRaisesRegex(generator.CandidateError, "explicit factory and paired framework provider"):
                generator.generate(self.output, record_paths={}, kernel_receipt=None, vendor_receipt=None,
                                   page_size_profile=ROOT / generator.PAGE_SIZE_PROFILE_RECORD)

    def test_cli_selects_profile_explicitly(self):
        expected = self.root / "profile.json"
        with mock.patch.object(generator, "generate", return_value={}) as run, redirect_stdout(io.StringIO()):
            self.assertEqual(generator.main(["generate", "--kernel-receipt", "kernel.json", "--vendor-receipt", "vendor.json",
                                             "--page-size-profile", str(expected), "--output", str(self.output)]), 0)
        self.assertEqual(run.call_args.kwargs["page_size_profile"], expected)

    def test_profile_digest_change_is_rejected(self):
        values = self.inputs()
        with values[0]["page_size_profile"].open("a") as stream:
            stream.write(" ")
        with self.assertRaisesRegex(generator.CandidateError, "reviewed contract"):
            self.generate(values)
        self.assertFalse(self.output.exists())

    def test_different_kernel_receipt_is_rejected(self):
        values = self.inputs()
        values[0]["kernel_receipt"].write_text(values[0]["kernel_receipt"].read_text() + " ")
        with self.assertRaisesRegex(generator.CandidateError, "kernel receipt changed"):
            self.generate(values)
        self.assertFalse(self.output.exists())

    def test_profile_with_different_kernel_image_is_rejected(self):
        values = self.inputs()
        self.rewrite_profile(values[0], lambda record: record["kernel"]["image"].update(sha256="0" * 64))
        with self.assertRaisesRegex(generator.CandidateError, "kernel image/config"):
            self.generate(values)

    def test_changed_actual_kernel_image_is_rejected(self):
        values = self.inputs()
        (values[0]["kernel_receipt"].parent / "kernel/Image").write_bytes(b"different kernel")
        with self.assertRaisesRegex(generator.CandidateError, "hash/size mismatch"):
            self.generate(values)

    def test_changed_actual_kernel_config_is_rejected(self):
        values = self.inputs()
        (values[0]["kernel_receipt"].parent / "reference/kernel.config").write_bytes(CONFIG + b"CONFIG_PAGE_SHIFT=14\n")
        with self.assertRaisesRegex(generator.CandidateError, "hash/size mismatch"):
            self.generate(values)

    def test_duplicate_kernel_config_is_rejected_even_when_resealed(self):
        values = self.inputs(CONFIG + b"CONFIG_ARM64_4K_PAGES=y\n")
        with self.assertRaisesRegex(generator.CandidateError, "duplicated or contradictory: CONFIG_ARM64_4K_PAGES"):
            self.generate(values)

    def test_contradictory_kernel_config_is_rejected_even_when_resealed(self):
        values = self.inputs(CONFIG.replace(b"CONFIG_PAGE_SHIFT=12", b"CONFIG_PAGE_SHIFT=14"))
        with self.assertRaisesRegex(generator.CandidateError, "duplicated or contradictory: CONFIG_PAGE_SHIFT"):
            self.generate(values)

    def test_missing_kernel_config_symbol_is_rejected(self):
        values = self.inputs(CONFIG.replace(b"# CONFIG_ARM64_16K_PAGES is not set\n", b""))
        with self.assertRaisesRegex(generator.CandidateError, "absent.*CONFIG_ARM64_16K_PAGES"):
            self.generate(values)

    def test_provider_receipt_mismatch_is_rejected(self):
        values = self.inputs()
        self.rewrite_profile(values[0], lambda record: record["providers"]["receipt"].update(sha256="0" * 64))
        with self.assertRaisesRegex(generator.CandidateError, "provider receipt or contract"):
            self.generate(values)

    def test_provider_payload_mismatch_is_rejected(self):
        values = self.inputs()
        self.rewrite_profile(values[0], lambda record: record["providers"]["files"][0].update(sha256="0" * 64))
        with self.assertRaisesRegex(generator.CandidateError, "provider bytes differ"):
            self.generate(values)

    def test_semantic_profile_changes_are_rejected_beneath_digest(self):
        values = self.inputs()
        original = values[0]["page_size_profile"].read_bytes()
        changes = {
            "maximum": lambda p: p["product_settings"].update(PRODUCT_MAX_PAGE_SIZE_SUPPORTED=16384),
            "checker": lambda p: p["product_settings"].update(PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE=False),
            "bionic": lambda p: p["product_settings"].update(PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO=False),
            "bool_alias": lambda p: p["product_settings"].update(PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE=1),
            "scope": lambda p: p["scope"].update(complete_rom_admitted=True),
            "compatibility": lambda p: p["scope"].update(compatibility_16k_verified=True),
            "missing_gap": lambda p: p["providers"].update(not_16k_aligned_file_count=21),
            "duplicate": lambda p: p["providers"]["files"].__setitem__(1, copy.deepcopy(p["providers"]["files"][0])),
            "alignment": lambda p: p["providers"]["files"][0].update(load_alignments=[8193]),
        }
        for label, change in changes.items():
            with self.subTest(case=label):
                values[0]["page_size_profile"].write_bytes(original)
                self.rewrite_profile(values[0], change)
                with self.assertRaises(generator.CandidateError):
                    generator._page_size_profile_contract(values[0]["page_size_profile"])

    def test_resealed_profile_admission_cannot_claim_16k_or_rom_support(self):
        plan = self.generate(self.inputs())
        for field in ("compatibility_16k_verified", "vsr_compatibility_verified", "complete_rom_admitted", "hardware_tested"):
            changed = copy.deepcopy(plan)
            changed["page_size_profile"]["scope"][field] = True
            (self.output / "admission.json").write_text(json.dumps(changed))
            with self.subTest(field=field), self.assertRaisesRegex(generator.CandidateError, "page-size profile admission differs"):
                generator.validate(self.output)

    def test_resealed_duplicate_product_setting_is_rejected(self):
        plan = self.generate(self.inputs())
        name = (generator.DEVICE_PATH / "generated/device-candidate.mk").as_posix()
        raw = (self.output / name).read_bytes() + b"PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 16384\n"
        self.reseal_candidate(plan, name, raw)
        with self.assertRaisesRegex(generator.CandidateError, "namespace export changed"):
            generator.validate(self.output)

    def test_source_selectors_cannot_be_added_outside_explicit_product(self):
        plan = self.generate(self.inputs())
        name = (generator.DEVICE_PATH / "lineage_nezha.mk").as_posix()
        original = (self.output / name).read_bytes()
        for line in (b"PRODUCT_MAX_PAGE_SIZE_SUPPORTED := 4096", b"TARGET_BOOTS_16K := true",
                     b"LOCAL_IGNORE_MAX_PAGE_SIZE := true", b"PRODUCT_16K_DEVELOPER_OPTION := true",
                     b"PRODUCT_SYSTEM_PROPERTIES += ro.config.low_ram=true"):
            with self.subTest(line=line):
                self.reseal_candidate(plan, name, original + b"\n" + line + b"\n")
                with self.assertRaisesRegex(generator.CandidateError, "page-size"):
                    generator.validate(self.output)

    def test_unselected_profile_cannot_be_smuggled_into_source(self):
        values = list(self.inputs())
        values[0].pop("page_size_profile")
        path = values[0]["template_root"] / "lineage_nezha.mk"
        path.write_text(path.read_text() + "\nPRODUCT_MAX_PAGE_SIZE_SUPPORTED := 4096\n")
        with self.assertRaisesRegex(generator.CandidateError, "explicit generated profile"):
            self.generate(values)

    def test_late_kernel_change_prevents_publication(self):
        values = self.inputs()
        validate = generator.validate
        def mutate_after_validation(*args, **kwargs):
            result = validate(*args, **kwargs)
            (values[0]["kernel_receipt"].parent / "kernel/Image").write_bytes(b"late kernel change")
            return result
        with mock.patch.object(generator, "validate", side_effect=mutate_after_validation):
            with self.assertRaisesRegex(generator.CandidateError, "kernel image/config"):
                self.generate(values)
        self.assertFalse(self.output.exists())

    def test_late_profile_change_prevents_publication(self):
        values = self.inputs()
        validate = generator.validate
        def mutate_after_validation(*args, **kwargs):
            result = validate(*args, **kwargs)
            values[0]["page_size_profile"].write_text(values[0]["page_size_profile"].read_text() + " ")
            return result
        with mock.patch.object(generator, "validate", side_effect=mutate_after_validation):
            with self.assertRaisesRegex(generator.CandidateError, "reviewed contract"):
                self.generate(values)
        self.assertFalse(self.output.exists())

    def test_portable_validation_uses_bound_records_not_private_paths(self):
        plan = self.generate(self.inputs())
        with mock.patch.object(generator, "_verify_page_size_kernel", side_effect=AssertionError("private kernel read")), \
                mock.patch.object(generator, "_verify_framework_provider_bundle", side_effect=AssertionError("private provider read")):
            self.assertEqual(generator.validate(self.output), plan)

    def test_profile_does_not_admit_target_files_or_flash(self):
        self.generate(self.inputs())
        for purpose in ("target-files", "flash"):
            with self.subTest(purpose=purpose), self.assertRaisesRegex(generator.CandidateError, "admission refused"):
                generator.validate(self.output, purpose=purpose)


if __name__ == "__main__":
    unittest.main()
