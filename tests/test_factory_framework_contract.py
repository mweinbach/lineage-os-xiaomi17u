"""Offline consistency checks; no private artifacts or Android tools are required."""

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
FACTORY = "d2cf57fd753311b352fe39fd450155231a38c6f536f66bf782588c797820cd8b"
XIAOMI_EU = "b29afecc91f74f190e3d248f07b84b29f8b7d74e36b6ff079310e864bea22c69"
POLICY_COMMIT = "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27"
BUILD_RECEIPT_SHA = "f920c2adba3dace5aa4b7dc067b195d5bfdd40539dee1acf07b46fa2063fbc99"
OUT = "/work/out/nezha-framework-20260827T1835Z"
INPUT_ORDER = [
    "/system/etc/selinux/plat_sepolicy.cil",
    "/system/etc/selinux/mapping/202504.cil",
    "/system_ext/etc/selinux/system_ext_sepolicy.cil",
    "/system_ext/etc/selinux/mapping/202504.cil",
    "/product/etc/selinux/product_sepolicy.cil",
    "/product/etc/selinux/mapping/202504.cil",
    "/vendor/etc/selinux/plat_pub_versioned.cil",
    "/vendor/etc/selinux/vendor_sepolicy.cil",
    "/odm/etc/selinux/odm_sepolicy.cil",
    "/system/etc/selinux/plat_sepolicy_genfs_202504.cil",
]
CATEGORIES = {"vintf", "permissions", "sysconfig", "default-permissions", "vintf-legacy"}
COMPARISON_COUNTS = {
    "identical": 446,
    "changed": 5,
    "factory-only-path": 18,
    "xiaomi-eu-only-path": 19,
    "factory-nonregular-path": 0,
    "xiaomi-eu-nonregular-path": 0,
}


def diagnostic_rows(check):
    """Expand the public grouped representation without needing private logs."""
    if "diagnostics" in check:
        return check["diagnostics"]
    rows = []
    for group in check["diagnostic_groups"]:
        if "shared_displayed_allow_locations" in group:
            per_assertion = [{"assertion_line": line, "assertion_source_location": None,
                              "displayed_allow_locations": group["shared_displayed_allow_locations"],
                              "abbreviated_matching_rules": []}
                             for line in group["assertion_lines"]]
        else:
            per_assertion = group["per_assertion"]
        for row in per_assertion:
            rows.append({
                "assertion": {"runtime_path": group["assertion_runtime_path"], "line": row["assertion_line"],
                              "source_location": row["assertion_source_location"]},
                "displayed_allow_locations": row["displayed_allow_locations"],
                "abbreviated_matching_rules": row["abbreviated_matching_rules"],
            })
    return rows


class FactoryFrameworkContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def read(name):
            return json.loads((ROOT / "research" / name).read_text())

        cls.record = read("factory-framework-contract.json")
        cls.validation = read("factory-firmware-validation.json")
        cls.eu_policy = read("selinux-contract.json")
        cls.eu_vintf = read("vintf-contract.json")
        cls.policy = cls.record["factory_policy"]
        cls.xml = cls.record["factory_xml"]
        cls.strict = cls.record["strict_policy_checks"]
        cls.variant = cls.record["variant_source_analysis"]
        # Reconstruct the declared 60-file comparison from the committed EU
        # baseline and the 15 published differences. This checks consistency,
        # not the private capture bytes, which remain bound by receipt hashes.
        cls.policy_files = {
            row["runtime_path"]: {**row, "partition": part["partition"]}
            for part in cls.eu_policy["capture"]["partitions"] for row in part["files"]
        }
        for row in cls.policy["comparison"]["files"]:
            cls.policy_files[row["runtime_path"]].update(
                sha256=row["factory_sha256"], size_bytes=row["factory_size_bytes"])
        cls.xml_differences = {row["runtime_path"]: row for row in cls.xml["comparison"]["files"]}
        cls.images = {row["partition"].removesuffix("_a"): row
                      for row in cls.validation["logical_partitions"]["outputs"]}

    def test_device_and_both_package_origins_stay_explicit(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["device"], {"codename": "nezha", "hardware_region": "CN"})
        factory = self.record["provenance"]["factory"]
        for key, value in self.validation["package"].items():
            self.assertEqual(factory[key], value)
        self.assertEqual(factory["sha256"], FACTORY)
        self.assertEqual(factory["size_bytes"], 12778943953)
        self.assertEqual(factory["source_kind"], "user-provided")
        self.assertIsNone(factory["source_url"])
        self.assertIsNone(factory["independently_published_sha256"])
        for key in ("origin_verified", "oem_key_authenticated", "avb_pass_authenticates_download_origin"):
            self.assertIs(factory[key], False)
        eu = self.record["provenance"]["xiaomi_eu"]
        self.assertEqual(eu["package_sha256"], XIAOMI_EU)
        self.assertEqual(eu["package_sha256"], self.eu_policy["provenance"]["package_sha256"])
        self.assertIn("modified Xiaomi.eu", eu["source_kind"])
        self.assertIsNone(eu["source_url"])
        self.assertIs(eu["origin_verified"], False)

    def test_factory_capture_is_bound_to_the_validated_images_and_receipts(self):
        source = self.record["provenance"]["factory"]
        self.assertEqual(source["validation_record"], "research/factory-firmware-validation.json")
        for key, parent in (("logical_partition_receipt", "logical_partitions"),
                            ("filesystem_receipt", "filesystems"), ("avb_receipt", "avb")):
            self.assertEqual(source[key], self.validation[parent]["receipt"])
        self.assertIs(source["all_eight_filesystem_checks_passed"], True)
        self.assertIs(source["selected_internal_avb_chain_passed"], True)
        self.assertEqual(self.policy["source_image_and_inventory_metadata"],
                         "factory_xml.partitions entries matched by partition name")
        for part in self.xml["partitions"]:
            with self.subTest(partition=part["partition"]):
                image = self.images[part["partition"]]
                self.assertEqual(part["image_sha256"], image["sha256"])
                self.assertEqual(part["image_size_bytes"], image["size_bytes"])

    def test_private_receipt_references_keep_exact_check_identities(self):
        expected = {
            "policy_capture": "e9b44133f73254493736496d1fb50b7402b96f3c3b395bbd042b0b35b35fedb3",
            "xml_capture_original": "eeeb49835adba454f729fca48c203f7dbca9509abaacd5513ce13628ba04cef3",
            "xml_comparison_corrected": "6df160536e3c7df61445770a579854c2b8431ffa6fd501609394863b0c32b9fa",
            "strict_factory": "47f78e6dca9b424133339e4a5f62b67b2d40d843be41f6c36c5ce2ca148504ca",
            "strict_evolution_factory": "f03d74c6380c9dcba51b29247c06673f693a81d826bed95d3957decd7fbcef29",
            "combined_readback": "0f551e8a7eb46a6479cbcefe3b4aab3d73037735a383e2e0db379fb72d0f8ae4",
            "diagnostic_summary": "89d1bfb3914e924286fc6d95993f449d5af7359c25f215a58a116d4cd95b3323",
            "variant_source": "de232d89435f9f1bc263359ea32e53736259a9de1e8d3c814cd84a64e82e6cf4",
        }
        receipts = self.record["receipts"]
        self.assertEqual({key: row["sha256"] for key, row in receipts.items()}, expected)
        self.assertEqual(len({row["path"] for row in receipts.values()}), len(expected))
        for key, row in receipts.items():
            self.assertTrue(row["path"].startswith("artifacts/"))
            self.assertNotIn("..", PurePosixPath(row["path"]).parts)
            self.assertGreater(row["size_bytes"], 0)
            if key != "variant_source":
                self.assertIn("/" + FACTORY + "/", row["path"])

    def test_capture_tool_records_guarded_reads_without_executing_firmware(self):
        tool = self.record["capture_tool"]
        self.assertEqual(tool["script"], "scripts/erofs_inventory.py")
        self.assertEqual({row["path"] for row in tool["source_files_at_capture"]},
                         {"scripts/erofs_inventory.py", "scripts/firmware.py", "scripts/artifact_files.py"})
        for key in ("read_only_filesystem_inventory", "whole_source_image_hash_checked",
                    "held_source_identity_checked", "captured_files_rehashed"):
            self.assertIs(tool[key], True)
        for key in ("symlinks_followed", "images_mounted", "firmware_executed", "phone_accessed"):
            self.assertIs(tool[key], False)

    def test_sixty_policy_files_have_consistent_partition_counts_and_bytes(self):
        self.assertEqual(self.policy["total_files"], 60)
        self.assertEqual(len(self.policy_files), 60)
        self.assertEqual(self.policy["full_60_path_inventory_retained_in_receipt"], "policy_capture")
        self.assertEqual(self.policy["total_bytes"], 7561542)
        self.assertEqual(sum(row["size_bytes"] for row in self.policy_files.values()), 7561542)
        self.assertEqual({part["partition"]: part["capture_count"] for part in self.policy["partitions"]},
                         {"vendor": 14, "odm": 11, "system": 13, "system_ext": 11, "product": 11})
        for part in self.policy["partitions"]:
            rows = [row for row in self.policy_files.values() if row["partition"] == part["partition"]]
            self.assertEqual(len(rows), part["capture_count"])
            self.assertEqual(sum(row["size_bytes"] for row in rows), part["capture_bytes"])
            self.assertEqual(part["baseline_paths_missing_or_not_regular"], [])

    def test_selected_version_and_precompiled_metadata_keep_capture_receipts(self):
        parts = {part["partition"]: part for part in self.policy["partitions"]}
        rows = self.policy["selected_version_and_precompiled_files"]
        self.assertEqual(len(rows), 3)
        self.assertEqual({row["runtime_path"] for row in rows}, {
            "/vendor/etc/selinux/genfs_labels_version.txt", "/vendor/etc/selinux/plat_sepolicy_vers.txt",
            "/odm/etc/selinux/precompiled_sepolicy",
        })
        for row in rows:
            self.assertEqual(row["runtime_path"], "/" + row["partition"] + row["image_path"])
            self.assertEqual(row["capture_receipt_sha256"], parts[row["partition"]]["capture_receipt_sha256"])
            for key in ("sha256", "size_bytes"):
                self.assertEqual(row[key], self.policy_files[row["runtime_path"]][key])

    def test_policy_comparison_recomputes_45_identical_and_15_changed(self):
        eu_files = {row["runtime_path"]: row for part in self.eu_policy["capture"]["partitions"]
                    for row in part["files"]}
        comparison = self.policy["comparison"]
        rows = comparison["files"]
        self.assertEqual(len(rows), 15)
        self.assertEqual(len({row["runtime_path"] for row in rows}), 15)
        self.assertTrue({row["runtime_path"] for row in rows} <= set(self.policy_files))
        self.assertEqual(set(self.policy_files), set(eu_files))
        self.assertIs(comparison["all_selected_factory_paths_present"], True)
        for row in rows:
            for prefix, source in (("factory", self.policy_files), ("xiaomi_eu", eu_files)):
                captured = source[row["runtime_path"]]
                self.assertEqual(row[prefix + "_sha256"], captured["sha256"])
                self.assertEqual(row[prefix + "_size_bytes"], captured["size_bytes"])
            equal = (row["factory_sha256"], row["factory_size_bytes"]) == (row["xiaomi_eu_sha256"], row["xiaomi_eu_size_bytes"])
            self.assertIs(row["identical"], equal)
        self.assertEqual(sum(row["identical"] for row in rows), 0)
        self.assertEqual(len(rows), comparison["changed"])
        self.assertEqual(len(eu_files) - len(rows), comparison["identical"])
        self.assertEqual((comparison["identical"], comparison["changed"]), (45, 15))
        self.assertFalse(next(row for row in rows if row["runtime_path"] == INPUT_ORDER[7])["identical"])
        self.assertNotIn(INPUT_ORDER[8], {row["runtime_path"] for row in rows})
        self.assertIn("Only the 15 changed paths", comparison["public_files_scope"])

    def test_policy_selection_does_not_claim_every_selinux_path_was_captured(self):
        extras = {part["partition"]: part["other_regular_selinux_paths_not_captured_count"]
                  for part in self.policy["partitions"]}
        self.assertEqual(extras,
                         {"vendor": 0, "odm": 0, "system": 15, "system_ext": 16, "product": 7})
        self.assertIn("60-file", self.policy["selection"])
        self.assertIn("separately", self.policy["selection"])
        self.assertEqual(self.policy["unselected_paths_retained_in_receipt"], "policy_capture")

    def test_version_agreement_and_precompiled_bytes_are_not_runtime_proof(self):
        versions = self.policy["versions"]
        self.assertEqual(versions["vendor_policy_api"], 202504)
        self.assertEqual(versions["vendor_genfs_api"], 202504)
        self.assertEqual(versions["binary_policy_format_version"], 30)
        self.assertIs(versions["version_files_include_trailing_newline"], True)
        self.assertIs(versions["version_agreement_is_not_compatibility"], True)
        for path in ("/vendor/etc/selinux/plat_sepolicy_vers.txt", "/vendor/etc/selinux/genfs_labels_version.txt"):
            self.assertEqual(self.policy_files[path]["sha256"], hashlib.sha256(b"202504\n").hexdigest())
            self.assertEqual(self.policy_files[path]["size_bytes"], 7)
        precompiled = self.policy["precompiled_reference"]
        for key in ("sha256", "size_bytes"):
            self.assertEqual(precompiled[key], self.policy_files[precompiled["runtime_path"]][key])
        self.assertEqual(precompiled["policy_version"], 30)
        self.assertEqual(precompiled["config_flags_hex"], "0xc0000001")
        for key in ("used_as_compiler_input", "loaded_or_installed", "binary_semantics_or_permissive_domains_verified"):
            self.assertIs(precompiled[key], False)

    def test_precompiled_metadata_keeps_three_recomputed_matches_and_zero_stored_pairs(self):
        metadata = self.policy["precompiled_metadata"]
        self.assertEqual(len(metadata["pairs"]), 3)
        self.assertEqual({row["partition"] for row in metadata["pairs"]}, {"system", "system_ext", "product"})
        for row in metadata["pairs"]:
            self.assertEqual(row["retained_digest"], row["computed_cil_then_mapping_digest"])
            self.assertNotEqual(row["retained_digest"], row["odm_digest"])
            self.assertIs(row["stored_metadata_pair_equal"], False)
            self.assertIs(row["recomputed_cil_mapping_matches_metadata"], True)
            for digest_key, path_key in (("retained_digest", "framework_metadata_path"), ("odm_digest", "odm_metadata_path")):
                expected = hashlib.sha256((row[digest_key] + "\n").encode()).hexdigest()
                self.assertEqual(self.policy_files[row[path_key]]["sha256"], expected)
                self.assertEqual(self.policy_files[row[path_key]]["size_bytes"], 65)
            self.assertIn(row["cil_path"], self.policy_files)
            self.assertIn(row["mapping_path"], self.policy_files)
        self.assertIs(metadata["all_framework_metadata_matches_recomputed_cil_mapping"], True)
        self.assertIs(metadata["all_stored_framework_odm_pairs_equal"], False)
        self.assertEqual(metadata["stored_framework_odm_pairs_matching"], 0)
        for key in ("genfs_included_in_hash_recipe", "xiaomi_original_hash_recipe_verified",
                    "cause_of_discrepancy_verified", "metadata_or_cil_repaired"):
            self.assertIs(metadata[key], False)
        source = metadata["source"]
        self.assertEqual(source["commit"], POLICY_COMMIT)
        android_bp = next(row for row in self.variant["source_files"] if row["path"] == "Android.bp")
        self.assertEqual(source["sha256"], android_bp["sha256"])

    def test_xml_capture_covers_eight_inventories_and_469_files(self):
        parts = self.xml["partitions"]
        self.assertEqual(self.xml["inventoried_partitions"], 8)
        self.assertEqual({part["partition"] for part in parts}, set(self.images))
        self.assertEqual(len(parts), 8)
        self.assertEqual(self.xml["inventory_entries"], 18512)
        self.assertEqual(sum(part["inventory_entry_count"] for part in parts), 18512)
        self.assertEqual(self.xml["total_files"], 469)
        self.assertEqual(sum(part["selected_xml_count"] for part in parts), 469)
        self.assertEqual(self.xml["total_bytes"], 1199639)
        self.assertEqual(sum(part["capture_bytes"] for part in parts), 1199639)
        self.assertEqual({part["partition"]: part["selected_xml_count"] for part in parts},
                         {"vendor": 214, "odm": 53, "system": 61, "system_ext": 98,
                          "product": 37, "mi_ext": 6, "system_dlkm": 0, "vendor_dlkm": 0})
        self.assertEqual(self.xml["full_469_path_inventory_retained_in_receipt"], "xml_capture_original")
        self.assertIs(self.xml["per_partition_category_counts_retained_in_private_receipt"], True)
        for part in parts:
            self.assertEqual(part["nonregular_xml_not_followed"], [])

    def test_zero_dlkm_xml_is_inventory_evidence_not_an_empty_capture(self):
        parts = {part["partition"]: part for part in self.xml["partitions"]}
        for name in ("system_dlkm", "vendor_dlkm"):
            part = parts[name]
            self.assertGreater(part["inventory_entry_count"], 0)
            self.assertEqual(part["selected_xml_count"], 0)
            self.assertEqual(part["capture_bytes"], 0)
            self.assertIsNone(part["capture_receipt_sha256"])
        for part in self.policy["partitions"]:
            self.assertIn(part["partition"], parts)
            self.assertGreater(parts[part["partition"]]["inventory_entry_count"], part["capture_count"])

    def test_corrected_xml_union_preserves_42_differences_and_488_total_paths(self):
        comparison = self.xml["comparison"]
        rows = comparison["files"]
        self.assertEqual(len(rows), 42)
        self.assertEqual(len(self.xml_differences), 42)
        self.assertEqual(comparison["full_union_paths"], 488)
        self.assertEqual(comparison["comparison_counts"], COMPARISON_COUNTS)
        counts = Counter(row["status"] for row in rows)
        self.assertEqual({key: counts[key] for key in COMPARISON_COUNTS},
                         {key: 0 if key == "identical" else value for key, value in COMPARISON_COUNTS.items()})
        self.assertEqual(sum(row["factory_sha256"] is not None for row in rows) + 446, comparison["factory_xml_count"])
        self.assertEqual(sum(row["xiaomi_eu_sha256"] is not None for row in rows) + 446, comparison["xiaomi_eu_xml_count"])
        self.assertEqual((comparison["factory_xml_count"], comparison["xiaomi_eu_xml_count"]), (469, 470))
        self.assertEqual(sum(COMPARISON_COUNTS.values()), comparison["full_union_paths"])
        self.assertEqual(comparison["factory_xml_count"] + comparison["xiaomi_eu_xml_count"] - (446 + 5), 488)
        self.assertIs(comparison["full_file_sizes_retained_in_private_receipt"], True)
        self.assertIn("Only the 42", comparison["public_files_scope"])
        for row in rows:
            factory, eu = row["factory_sha256"], row["xiaomi_eu_sha256"]
            path = PurePosixPath(row["runtime_path"])
            self.assertTrue(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertEqual(str(path), row["runtime_path"])
            self.assertTrue(row["runtime_path"].endswith(".xml"))
            self.assertIn(row["category"], CATEGORIES)
            if factory is None:
                expected = "xiaomi-eu-only-path"
                self.assertIsNotNone(eu)
            elif eu is None:
                expected = "factory-only-path"
            else:
                self.assertNotEqual(factory, eu)
                expected = "changed"
            self.assertEqual(row["status"], expected)

    def test_xml_category_totals_keep_vintf_and_permission_scopes_separate(self):
        comparison = self.xml["comparison"]
        by_category = comparison["comparison_by_category"]
        self.assertEqual(set(by_category), CATEGORIES)
        for category, counts in by_category.items():
            rows = [row for row in comparison["files"] if row["category"] == category]
            actual = Counter(row["status"] for row in rows)
            for key in COMPARISON_COUNTS:
                if key != "identical":
                    self.assertEqual(actual[key], counts[key])
        for key, count in COMPARISON_COUNTS.items():
            self.assertEqual(sum(counts[key] for counts in by_category.values()), count)
        self.assertEqual(by_category["vintf"], {key: 209 if key == "identical" else 0 for key in COMPARISON_COUNTS})
        self.assertEqual(by_category["permissions"]["changed"], 1)
        self.assertEqual(by_category["sysconfig"]["changed"], 4)

    def test_xml_correction_keeps_eight_inventory_rechecks_and_38_additional_reads(self):
        comparison = self.xml["comparison"]
        eu_parts = {part["name"].removesuffix("_a"): part for part in self.eu_vintf["partitions"]}
        bindings = comparison["inventory_bindings"]
        self.assertEqual(bindings["complete_partitions_compared"], 8)
        self.assertEqual(bindings["complete_partitions_compared"], len(eu_parts))
        self.assertEqual(bindings["source_image_and_inventory_hashes_retained_in_receipt"], "xml_comparison_corrected")
        self.assertIs(bindings["all_inventory_inputs_rehashed"], True)
        extra = comparison["extra_xiaomieu_captures"]
        self.assertEqual({row["partition"]: row["files"] for row in extra},
                         {"product": 12, "system": 13, "system_ext": 10, "vendor": 3})
        self.assertEqual(sum(row["files"] for row in extra), 38)
        self.assertEqual(sum(row["size_bytes"] for row in extra), 92926)
        self.assertEqual(comparison["previously_captured_xiaomieu_xml_count"], 432)
        # The prior inventory also captured non-XML configuration files.
        self.assertGreaterEqual(sum(part["capture_files"] for part in eu_parts.values()), 432)
        self.assertEqual(comparison["additional_xiaomieu_xml_count"], 38)
        self.assertEqual(432 + 38, comparison["xiaomi_eu_xml_count"])
        for row in extra:
            self.assertEqual(row["source_package_sha256"], XIAOMI_EU)
        self.assertEqual({row["partition"]: row["receipt_sha256"] for row in extra}, {
            "product": "5430e48e571ce9d2c8d28b5ab0f191632c9bb4a613319d6fe54993ccf99843a6",
            "system": "f68eec64128eddc0604ab5681f35d2493fd5752f2f6747484731207212507c6f",
            "system_ext": "f83fe49a8cfe977119d32283fdb52930607bddf824018b4da39cef3d8dca77a0",
            "vendor": "7beb62d1a8f7fa5008adf349c9d52b846673ba5f2a68ee47bd7d2ad30dc637e0",
        })
        self.assertEqual(comparison["receipt_key"], "xml_comparison_corrected")
        for key in ("complete_regular_xml_inventory_coverage", "original_capture_set_absence_labels_corrected",
                    "original_receipt_and_captures_preserved"):
            self.assertIs(comparison[key], True)
        self.assertIn("prior captured set", comparison["original_comparison_scope"])

    def test_xml_hash_equality_does_not_claim_schema_apex_or_runtime_compatibility(self):
        expected_changed = {
            "/product/etc/permissions/split-permissions-google.xml",
            "/product/etc/sysconfig/google.xml",
            "/system/etc/sysconfig/hiddenapi-package-whitelist.xml",
            "/system_ext/etc/sysconfig/miui_whitelist.xml",
            "/system_ext/etc/sysconfig/power-save-conf.xml",
        }
        self.assertEqual({row["runtime_path"] for row in self.xml["comparison"]["files"] if row["status"] == "changed"}, expected_changed)
        self.assertTrue(any(path.startswith("/mi_ext/product/") for path in self.xml_differences))
        self.assertTrue(any(path.startswith("/product/pangu/") for path in self.xml_differences))
        for key in ("xml_well_formedness_parsed", "xml_schema_validated", "effective_vintf_or_permissions_verified",
                    "apex_payloads_included", "nested_product_or_mi_ext_paths_prove_active_overlays"):
            self.assertIs(self.xml[key], False)

    def test_compiler_source_projects_match_the_committed_resolved_manifest(self):
        self.assertEqual(self.strict["source_snapshot"], "research/source-snapshots/evolution-bka-20260827.xml")
        snapshot = ET.parse(ROOT / self.strict["source_snapshot"]).getroot()
        projects = {row.get("path"): row.get("revision") for row in snapshot.findall("project")}
        expected = {"external/selinux": "085c131ad1b984bfa8ffdafee7a976e9d89f403c", "system/sepolicy": POLICY_COMMIT}
        self.assertEqual({name: source["head"] for name, source in self.strict["source_projects"].items()}, expected)
        for name, source in self.strict["source_projects"].items():
            self.assertEqual(source["head"], projects[name])
            self.assertIs(source["tracked_worktree_clean"], True)

    def test_soong_tools_are_pinned_separately_from_factory_executables(self):
        expected = {
            "secilc": ("0e1f73449ac82302d88d721b2fa106aad9ae895d9cb92afd69b31aae2253dff7", 1368096),
            "sepolicy-analyze": ("a271e82042286276651db28a34928bd149c745ccb6ba7cacf18b51258b909669", 543160),
            "nsjail": ("3f97556c3cf8a83d3f5ae854e6dfc2f345355ead547dd661d07a369b6c2ba280", 284176),
        }
        self.assertEqual(set(self.strict["tools"]), set(expected))
        for name, pair in expected.items():
            tool = self.strict["tools"][name]
            self.assertEqual((tool["sha256"], tool["size_bytes"]), pair)
            if name != "nsjail":
                self.assertEqual(tool["path"], OUT + "/host/linux-x86/bin/" + name)
                self.assertEqual(tool["elf_machine"], 62)
        self.assertEqual(self.strict["tool_build_output_receipt"]["sha256"],
                         "517abf483adf40ec5dcb0386231667f03be93771a73e0d6746096f4f8ee8d399")

    def test_both_compilers_keep_all_ten_inputs_in_strict_order(self):
        flags = ["-m", "-M", "true", "-G", "-c", "30"]
        self.assertEqual(self.strict["compiler_flags"], flags)
        self.assertEqual(self.strict["input_runtime_order"], INPUT_ORDER)
        self.assertEqual(set(self.strict["checks"]), {"factory", "evolution_factory_userdebug"})
        for check in self.strict["checks"].values():
            self.assertEqual(check["input_count"], 10)
            self.assertEqual([row["runtime_path"] for row in check["input_order"]], INPUT_ORDER)
            self.assertEqual(sum(row["size_bytes"] for row in check["input_order"]), check["input_bytes"])
            self.assertEqual(len(check["commands"]), 1)
            command = check["commands"][0]
            self.assertEqual(command["compiler_executable_reference"], "strict_policy_checks.tools.secilc.path")
            self.assertEqual(command["compiler_flags_reference"], "strict_policy_checks.compiler_flags")
            self.assertEqual(command["input_base"], check["guest_destination"] + "/inputs")
            self.assertEqual(command["input_order_reference"], "input_order in this check, matching shared input_runtime_order")
            self.assertIs(command["exact_argv_in_bound_receipt"], True)
            for key in ("policy_output", "file_contexts_output"):
                path = PurePosixPath(command[key])
                self.assertEqual(path.parts[0], "results")
                self.assertEqual(len(path.parts), 2)
                self.assertNotIn("..", path.parts)
            self.assertTrue(command["policy_output"].endswith(".policy"))
            self.assertTrue(command["file_contexts_output"].endswith(".file_contexts"))
        self.assertNotIn("-N", self.strict["compiler_flags"])
        self.assertNotIn("--disable-neverallow", self.strict["compiler_flags"])
        self.assertFalse(any("precompiled_sepolicy" in path for path in INPUT_ORDER))

    def test_sandbox_writers_are_only_the_fresh_validation_directory_and_tmp(self):
        sandbox = self.strict["sandbox"]
        self.assertEqual(sandbox["engine"], "nsjail")
        for key in ("android_source_read_only", "android_out_read_only", "staged_inputs_read_only",
                    "outer_uid_gid_warning_recorded", "exact_argv_retained_in_each_receipt"):
            self.assertIs(sandbox[key], True)
        self.assertEqual(sandbox["writable_paths"], ["fresh check guest_destination", "/tmp"])
        self.assertEqual(sandbox["command_timeout_seconds"], 90)
        self.assertEqual((sandbox["identity_user"], sandbox["identity_group"]), ("nobody", "nogroup"))
        destinations = set()
        for check in self.strict["checks"].values():
            destination = check["guest_destination"]
            destinations.add(destination)
            command = check["commands"][0]
            self.assertTrue(destination.startswith("/work/validation/nezha-selinux-"))
            self.assertNotIn("..", PurePosixPath(destination).parts)
            self.assertEqual(command["timeout_seconds"], 110)
            self.assertIsNone(command["failure"])
        self.assertEqual(len(destinations), 2)

    def test_factory_failure_keeps_exact_stock_inputs_and_one_assertion(self):
        check = self.strict["checks"]["factory"]
        self.assertEqual(check["receipt_key"], "strict_factory")
        self.assertEqual(check["input_bytes"], 5408720)
        self.assertIs(check["evolution_framework_inputs_used"], False)
        for row in check["input_order"]:
            for key in ("sha256", "size_bytes"):
                self.assertEqual(row[key], self.policy_files[row["runtime_path"]][key])
        self.assertEqual(check["assertion_sites_reported"], 1)
        self.assertEqual(check["displayed_allow_locations"], 2)
        self.assertIs(check["diagnostic_allow_locations_are_exhaustive"], True)
        diagnostic, = check["diagnostics"]
        self.assertEqual((diagnostic["assertion"]["runtime_path"], diagnostic["assertion"]["line"]), (INPUT_ORDER[7], 9901))
        self.assertEqual([(row["runtime_path"], row["line"]) for row in diagnostic["displayed_allow_locations"]],
                         [(INPUT_ORDER[2], 4604), (INPUT_ORDER[2], 4702)])
        self.assertEqual(diagnostic["abbreviated_matching_rules"], [])

    def test_combined_check_binds_seven_framework_files_and_three_factory_files(self):
        check = self.strict["checks"]["evolution_factory_userdebug"]
        self.assertEqual(check["receipt_key"], "strict_evolution_factory")
        self.assertEqual((check["framework_input_count"], check["factory_input_count"]), (7, 3))
        self.assertEqual(check["input_bytes"], 5498245)
        self.assertEqual((check["target_product"], check["target_release"], check["target_variant"]),
                         ("lineage_nezha", "bp4a", "userdebug"))
        self.assertEqual(check["framework_build_receipt"]["sha256"], BUILD_RECEIPT_SHA)
        self.assertEqual(check["framework_build_receipt"]["path"], "reports/nezha-boot-policy-v6-1-receipt.json")
        self.assertEqual(check["framework_input_order_positions"], [1, 2, 3, 4, 5, 6, 10])
        self.assertEqual(check["factory_input_order_positions"], [7, 8, 9])
        positions = check["framework_input_order_positions"] + check["factory_input_order_positions"]
        self.assertEqual(sorted(positions), list(range(1, 11)))
        framework = {check["input_order"][index - 1]["runtime_path"]: check["input_order"][index - 1]
                     for index in check["framework_input_order_positions"]}
        self.assertEqual(set(framework), set(INPUT_ORDER[:6] + INPUT_ORDER[9:]))
        for row in check["input_order"][6:9]:
            for key in ("sha256", "size_bytes"):
                self.assertEqual(row[key], self.policy_files[row["runtime_path"]][key])
        self.assertEqual(check["framework_source_base"], OUT + "/target/product/nezha")
        self.assertEqual((framework[INPUT_ORDER[0]]["sha256"], framework[INPUT_ORDER[0]]["size_bytes"]),
                         ("87013669c357868bd3c4a0c32b64ed1328bcba7ed463db3a9fffb3b281bf9780", 3149674))
        self.assertEqual((framework[INPUT_ORDER[1]]["sha256"], framework[INPUT_ORDER[1]]["size_bytes"]),
                         ("a98f4b8479aa64e7d2b5a4146e6edc89fc50d62c80d37200258ff719dfced03b", 229237))
        self.assertEqual(framework[INPUT_ORDER[9]], self.strict["checks"]["factory"]["input_order"][9])
        self.assertIs(check["framework_source_hashes_unchanged_after"], True)
        self.assertIs(check["provenance_receipt_hashes_unchanged_after"], True)

    def test_four_newline_framework_inputs_remain_in_the_compiler_input_set(self):
        check = self.strict["checks"]["evolution_factory_userdebug"]
        self.assertEqual(check["one_newline_framework_inputs"], INPUT_ORDER[2:6])
        self.assertIs(check["one_newline_inputs_included_without_modification"], True)
        rows = {row["runtime_path"]: row for row in check["input_order"]}
        newline_sha = hashlib.sha256(b"\n").hexdigest()
        self.assertEqual({row["runtime_path"] for row in check["input_order"] if row["size_bytes"] == 1}, set(INPUT_ORDER[2:6]))
        for path in INPUT_ORDER[2:6]:
            self.assertEqual(rows[path]["size_bytes"], 1)
            self.assertEqual(rows[path]["sha256"], newline_sha)

    def test_combined_failure_counts_displayed_rules_without_hiding_truncation(self):
        check = self.strict["checks"]["evolution_factory_userdebug"]
        self.assertEqual(check["assertion_sites_reported"], 21)
        self.assertEqual(check["displayed_allow_locations"], 27)
        self.assertIs(check["diagnostic_allow_locations_are_exhaustive"], False)
        diagnostics = diagnostic_rows(check)
        abbreviated = [(row, item) for row in diagnostics for item in row["abbreviated_matching_rules"]]
        self.assertEqual(len(abbreviated), 2)
        self.assertEqual({(item["displayed"], item["total_matching_rules"]) for _, item in abbreviated}, {(4, 35), (4, 32)})
        self.assertEqual({row["assertion"]["source_location"] for row, _ in abbreviated},
                         {"system/sepolicy/private/domain.te:2223", "system/sepolicy/private/domain.te:2224"})
        for row, item in abbreviated:
            self.assertEqual(len(row["displayed_allow_locations"]), item["displayed"])
            self.assertLess(item["displayed"], item["total_matching_rules"])

    def test_diagnostic_locations_bind_to_the_exact_inputs_without_raw_rules(self):
        for check in self.strict["checks"].values():
            inputs = {row["runtime_path"]: row for row in check["input_order"]}
            diagnostics = diagnostic_rows(check)
            self.assertEqual(len(diagnostics), check["assertion_sites_reported"])
            self.assertEqual(len({(row["assertion"]["runtime_path"], row["assertion"]["line"]) for row in diagnostics}), len(diagnostics))
            self.assertEqual(sum(len(row["displayed_allow_locations"]) for row in diagnostics), check["displayed_allow_locations"])
            for diagnostic in diagnostics:
                assertion = diagnostic["assertion"]
                self.assertRegex(inputs[assertion["runtime_path"]]["sha256"], r"^[0-9a-f]{64}$")
                for row in [assertion, *diagnostic["displayed_allow_locations"]]:
                    self.assertIn(row["runtime_path"], inputs)
                    self.assertGreater(row["line"], 0)
                    self.assertLessEqual(set(row), {"runtime_path", "line", "sha256", "source_location"})
                    if row["source_location"] is not None:
                        self.assertRegex(row["source_location"], r"^system/sepolicy/[a-z0-9_/]+\.te:[1-9][0-9]*$")

    def test_failed_checks_do_not_invent_outputs_permissive_analysis_or_missing_types(self):
        for check in self.strict["checks"].values():
            self.assertEqual(check["exit_code"], 255)
            self.assertIs(check["passed"], False)
            self.assertEqual(check["generated_outputs"], [])
            self.assertIsNone(check["permissive_analysis"])
            self.assertEqual(check["inspection_guard_errors"], [])
            for key in ("input_hashes_unchanged_after", "tool_hashes_unchanged_after", "source_projects_unchanged_after"):
                self.assertIs(check[key], True)
            for key in ("missing_type_diagnostic_observed", "neverallow_checks_disabled", "source_or_policy_rules_changed",
                        "stock_precompiled_policy_used", "firmware_executed", "android_source_modified",
                        "android_out_modified", "phone_accessed"):
                self.assertIs(check[key], False)
            command, = check["commands"]
            self.assertEqual(command["exit_code"], 255)
            self.assertEqual(command["stdout_bytes"], 0)
            self.assertGreater(command["stderr_bytes"], 0)
            self.assertLessEqual(command["stderr_bytes"], 2 * 1024**2)
            self.assertEqual(command["stdout_sha256"], hashlib.sha256(b"").hexdigest())

    def test_variant_analysis_binds_seven_public_sources_to_the_same_commit(self):
        source = self.variant
        self.assertEqual(source["receipt_key"], "variant_source")
        self.assertEqual(source["source_project"], "system/sepolicy")
        self.assertEqual(source["source_commit"], POLICY_COMMIT)
        self.assertEqual(len(source["source_files"]), 7)
        self.assertEqual({row["path"] for row in source["source_files"]}, {
            "private/llkd.te", "private/hal_codec2.te", "private/init_dev_config.te",
            "private/isolated_compute_app.te", "private/domain.te", "public/te_macros", "Android.bp",
        })
        self.assertEqual(sum(row["size_bytes"] for row in source["source_files"]), source["source_total_bytes"])
        self.assertEqual(source["source_total_bytes"], 172389)
        self.assertIs(source["all_git_blobs_and_sha256_verified"], True)
        self.assertIs(source["source_worktree_or_out_modified"], False)
        for row in source["source_files"]:
            self.assertRegex(row["git_blob_sha1"], r"^[0-9a-f]{40}$")
            self.assertGreater(row["size_bytes"], 0)
        self.assertEqual(source["repository_url"], "https://github.com/Evolution-X/system_sepolicy")

    def test_variant_groups_account_for_16_debug_and_five_unguarded_sites(self):
        groups = {row["id"]: row for row in self.variant["groups"]}
        self.assertEqual({name: row["assertion_sites"] for name, row in groups.items()}, {
            "llkd_ptrace": 15, "codec2_tcp_to_su": 1, "init_dev_config_properties": 2,
            "isolated_compute_service_find": 1, "binder_nondomain_restrictions": 2,
        })
        debug = [row for row in groups.values() if row["variant_guarded"]]
        unguarded = [row for row in groups.values() if not row["variant_guarded"]]
        self.assertEqual(sum(row["assertion_sites"] for row in debug), self.variant["debug_guarded_assertion_sites"])
        self.assertEqual(self.variant["debug_guarded_assertion_sites"], 16)
        self.assertEqual(sum(row["assertion_sites"] for row in unguarded), self.variant["nondebug_assertion_sites"])
        self.assertEqual(self.variant["nondebug_assertion_sites"], 5)
        self.assertEqual(len(unguarded), self.variant["nondebug_restriction_groups"])
        self.assertEqual(self.variant["nondebug_restriction_groups"], 3)
        self.assertEqual(sum(row["assertion_sites"] for row in groups.values()), 21)
        for row in debug:
            self.assertEqual(row["guard"], "userdebug_or_eng")
        for row in unguarded:
            self.assertIsNone(row["guard"])
        check = self.strict["checks"]["evolution_factory_userdebug"]
        actual_groups = {row["id"]: row for row in check["diagnostic_groups"]}
        self.assertEqual(set(actual_groups), set(groups))
        for name, row in actual_groups.items():
            self.assertEqual(row["assertion_sites"], groups[name]["assertion_sites"])
            self.assertEqual(len(row["assertion_lines"]), row["assertion_sites"])
            self.assertEqual(len(set(row["assertion_lines"])), row["assertion_sites"])
            if "per_assertion" in row:
                self.assertEqual([item["assertion_line"] for item in row["per_assertion"]], row["assertion_lines"])
                self.assertEqual(sum(len(item["displayed_allow_locations"]) for item in row["per_assertion"]), row["displayed_allow_locations_count"])
            else:
                self.assertIs(row["shared_displayed_allow_locations_repeat_for_each_assertion"], True)
                self.assertEqual(len(row["shared_displayed_allow_locations"]) * row["assertion_sites"], row["displayed_allow_locations_count"])
            self.assertIs(row["all_matching_allow_locations_displayed"], name != "binder_nondomain_restrictions")
        self.assertEqual(sum(row["displayed_allow_locations_count"] for row in actual_groups.values()), 27)
        diagnostics = diagnostic_rows(check)
        grants = Counter(location["source_location"] for row in diagnostics for location in row["displayed_allow_locations"])
        self.assertEqual(grants["system/sepolicy/private/llkd.te:22"], groups["llkd_ptrace"]["assertion_sites"])
        self.assertEqual(grants["system/sepolicy/private/hal_codec2.te:10"], groups["codec2_tcp_to_su"]["assertion_sites"])

    def test_variant_prediction_is_not_an_unperformed_user_build_or_eng_advice(self):
        macro = self.variant["macro"]
        self.assertEqual(macro["name"], "userdebug_or_eng")
        self.assertEqual(macro["source"], "public/te_macros")
        self.assertEqual((macro["definition_start_line"], macro["definition_end_line"]), (607, 610))
        self.assertEqual(macro["expands_body_for"], ["userdebug", "eng"])
        self.assertEqual(macro["does_not_expand_body_for"], ["user"])
        self.assertIs(macro["eng_variant_recommended_or_enabled"], False)
        self.assertIs(self.variant["actual_user_policy_compile_performed"], False)
        self.assertIs(self.variant["user_policy_passed"], False)
        self.assertIs(self.variant["variant_prediction_is_not_a_compiler_result"], True)
        for group in self.variant["groups"]:
            self.assertIs(group["user_variant_result_verified"], False)

    def test_verification_boundaries_and_remaining_gates_remain_explicit(self):
        self.assertEqual(set(self.record["boundaries"]), {
            "phone_accessed", "phone_modified", "android_source_modified_by_checks", "android_out_modified_by_checks",
            "stock_precompiled_policy_used", "policy_or_checks_weakened", "raw_firmware_policy_xml_logs_or_signing_keys_committed",
            "rom_booted", "native_feature_verified",
        })
        self.assertTrue(all(value is False for value in self.record["boundaries"].values()))
        self.assertIs(self.strict["neverallow_checks_disabled"], False)
        self.assertIs(self.strict["policy_rules_modified_or_omitted"], False)
        self.assertEqual(len(self.record["next_validation"]), 5)
        gates = " ".join(self.record["next_validation"])
        for phrase in ("strict assertions", "sepolicy-analyze permissive", "complete VINTF", "explicitly authorized device tests"):
            self.assertIn(phrase, gates)

    def test_record_contains_hashes_and_locations_without_private_payloads(self):
        forbidden = {"raw_cil", "raw_xml", "raw_key", "private_key", "raw_log", "raw_rule", "rule_text",
                     "allow_rule", "neverallow_rule", "base64", "data_base64", "content", "serial", "imei", "imsi"}

        def inspect(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for key, child in value.items():
                    if key.endswith("sha256") and child is not None:
                        self.assertRegex(child, r"^[0-9a-f]{64}$")
                    if key in ("stdout", "stderr"):
                        self.assertRegex(child, r"^logs/[a-z0-9-]+\.(stdout|stderr)$")
                    inspect(child)
            elif isinstance(value, list):
                for child in value:
                    inspect(child)
            elif isinstance(value, str):
                self.assertNotIn("-----BEGIN PRIVATE KEY-----", value)
                self.assertNotIn("(allow ", value)
                self.assertNotIn("(neverallow ", value)
                self.assertNotIn("<manifest", value)

        inspect(self.record)
        self.assertIs(self.record["provenance"]["raw_policy_xml_or_proprietary_bytes_committed"], False)


if __name__ == "__main__":
    unittest.main()
