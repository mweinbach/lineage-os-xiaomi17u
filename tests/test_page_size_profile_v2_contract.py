"""Offline cross-contract checks for the current, explicitly selected 4 KiB profile.

These tests use only public records. Private ELF/header inspection and native
build outcomes are separate evidence; generator admission has its own tests.
"""

import copy
import hashlib
import json
from pathlib import Path
import unittest

from scripts.framework_provider_derivations import validate_rule


ROOT = Path(__file__).resolve().parents[1]
OLD = "config/nezha-page-size-profile.json"
CURRENT = "config/nezha-page-size-profile-v2.json"
PROVIDERS = "config/nezha-framework-providers.json"
OLD_IDENTITY = {
    "sha256": "9d180aeeb13e0c04a4f2726bf94ad6651e1052cb5f9162359c147814bc6607ca",
    "size_bytes": 13226,
}
CURRENT_IDENTITY = {
    "sha256": "bed228b0595ef2dc1dd814e98c0966ba9b9452b542de50354db522e2420bed1e",
    "size_bytes": 15567,
}


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


class PageSizeProfileV2ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old_raw = (ROOT / OLD).read_bytes()
        cls.current_raw = (ROOT / CURRENT).read_bytes()
        cls.provider_raw = (ROOT / PROVIDERS).read_bytes()
        cls.old = json.loads(cls.old_raw)
        cls.current = json.loads(cls.current_raw)
        cls.provider = json.loads(cls.provider_raw)

    def test_predecessor_is_preserved_and_successor_is_separately_pinned(self):
        self.assertEqual(identity(self.old_raw), OLD_IDENTITY)
        self.assertEqual(identity(self.current_raw), CURRENT_IDENTITY)
        self.assertEqual(self.current["predecessor"], {"path": OLD, **OLD_IDENTITY})
        self.assertEqual(self.current["profile_id"], "nezha-stock-4k-bringup-v2")
        self.assertEqual(self.current["schema_version"], 1)
        self.assertNotEqual(self.current["profile_id"], self.old["profile_id"])

    def test_kernel_identity_and_platform_selection_do_not_drift(self):
        for field in ("device", "release_config", "kernel"):
            with self.subTest(field=field):
                self.assertEqual(self.current[field], self.old[field])
        self.assertEqual(self.current["kernel"]["runtime_page_size_bytes"], 4096)
        self.assertEqual(self.current["kernel"]["settings"], {
            "CONFIG_ARM64_4K_PAGES": "y", "CONFIG_ARM64_16K_PAGES": "n",
            "CONFIG_ARM64_64K_PAGES": "n", "CONFIG_PAGE_SHIFT": "12",
        })

    def test_provider_contract_and_receipt_are_current_v7(self):
        self.assertEqual(self.current["providers"]["contract"], {
            "path": PROVIDERS, **identity(self.provider_raw),
        })
        self.assertEqual(self.current["providers"]["receipt"], {
            "sha256": "c8d2ec1822e45181f45af57fd2389a9939eb635e14866dce41b85736fe65513e",
            "size_bytes": 13737,
        })
        self.assertNotEqual(self.current["providers"]["receipt"], self.old["providers"]["receipt"])

    def test_all_original_payload_rows_remain_separate_from_derived_output(self):
        rows = self.current["providers"]["files"]
        self.assertEqual(rows, self.old["providers"]["files"])
        expected = {
            row["runtime_path"]: {key: row[key] for key in ("module", "sha256", "size_bytes")}
            for row in self.provider["files"] if row["kind"] in ("binary", "shared_library")
        }
        actual = {
            row["runtime_path"]: {key: row[key] for key in ("module", "sha256", "size_bytes")}
            for row in rows
        }
        self.assertEqual(len(rows), 26)
        self.assertEqual(len(actual), 26)
        self.assertEqual(actual, expected)

    def test_exact_existing_derivation_and_evidence_are_bound(self):
        derivations = self.current["providers"]["payload_derivations"]
        self.assertEqual(derivations, self.provider["payload_derivations"])
        self.assertEqual(len(derivations), 1)
        entry = derivations[0]
        validate_rule(entry["recipe"])
        evidence = entry["evidence"]
        self.assertEqual(identity((ROOT / evidence["path"]).read_bytes()),
                         {key: evidence[key] for key in ("sha256", "size_bytes")})
        self.assertEqual(entry["recipe"]["changed_byte_file_offset"], 17588)
        self.assertEqual(entry["recipe"]["old"], "android.media.audio.common.types-V2-cpp.so")
        self.assertEqual(entry["recipe"]["new"], "android.media.audio.common.types-V4-cpp.so")

    def test_effective_override_changes_only_the_reviewed_identity(self):
        providers = self.current["providers"]
        overrides = providers["effective_file_overrides"]
        self.assertEqual(len(overrides), 1)
        override = overrides[0]
        entry = providers["payload_derivations"][0]
        originals = {row["runtime_path"]: row for row in providers["files"]}
        original = originals[entry["runtime_path"]]
        self.assertEqual({key: original[key] for key in ("sha256", "size_bytes")}, entry["recipe"]["original"])
        expected = copy.deepcopy(original)
        expected.update(entry["recipe"]["derived"])
        self.assertEqual(override, expected)
        self.assertEqual(override["sha256"], "06ffed0abd8cd7258c44e672e7fde4377f39626dddbed59eef70f60426c08082")
        self.assertEqual(override["load_alignments"], [4096] * 4)
        self.assertFalse(override["compatible_with_16k_alignment"])

    def test_effective_inventory_retains_all_26_and_all_22_known_gaps(self):
        providers = self.current["providers"]
        effective = {row["runtime_path"]: row for row in providers["files"]}
        effective.update({row["runtime_path"]: row for row in providers["effective_file_overrides"]})
        self.assertEqual(len(effective), providers["native_file_count"])
        self.assertEqual(len(effective), 26)
        for row in effective.values():
            self.assertTrue(row["load_alignments"])
            for alignment in row["load_alignments"]:
                self.assertIs(type(alignment), int)
                self.assertGreaterEqual(alignment, 4096)
                self.assertEqual(alignment & (alignment - 1), 0)
            self.assertIs(row["compatible_with_16k_alignment"],
                          all(alignment % 16384 == 0 for alignment in row["load_alignments"]))
        gaps = sum(not row["compatible_with_16k_alignment"] for row in effective.values())
        self.assertEqual(gaps, providers["not_16k_aligned_file_count"])
        self.assertEqual(gaps, 22)

    def test_authorized_threshold_keeps_checks_and_unverified_scope(self):
        self.assertEqual(self.current["product_settings"], {
            "PRODUCT_MAX_PAGE_SIZE_SUPPORTED": 4096,
            "PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE": True,
            "PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO": True,
        })
        self.assertEqual(self.current["scope"], self.old["scope"])
        for key in ("compatibility_16k_verified", "vsr_compatibility_verified",
                    "native_component_build_verified", "hardware_tested", "complete_rom_admitted"):
            self.assertIs(self.current["scope"][key], False)
        self.assertIs(self.current["scope"]["strict_elf_checks_required"], True)
        self.assertEqual(self.current["scope"]["phone_operations"], [])


if __name__ == "__main__":
    unittest.main()
