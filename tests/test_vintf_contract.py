"""Check the sanitized VINTF record without private images, tools or a phone.

These tests protect provenance and distinctions in the published record; they
do not revalidate private XML, run libvintf or establish hardware compatibility.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]


class VintfContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "research/vintf-contract.json").read_text())
        cls.layout = json.loads((ROOT / "research/firmware-layout.json").read_text())

    def test_static_evidence_does_not_claim_compatibility_or_authentication(self):
        record = self.record
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual(record["device"]["codename"], "nezha")
        self.assertEqual(record["device"]["hardware_region"], "CN")
        self.assertFalse(record["device"]["build_ready"])
        self.assertIsNone(record["device"]["lunch_target"])
        provenance = record["provenance"]
        self.assertEqual(provenance["package_sha256"], self.layout["package"]["sha256"])
        self.assertEqual(provenance["raw_super_sha256"], self.layout["raw_image"]["sha256"])
        self.assertIn("modified Xiaomi.eu", provenance["package_kind"])
        self.assertIsNone(provenance["source_url"])
        self.assertTrue(provenance["phone_accessed_by_this_analysis"])
        for field in ("origin_verified", "initial_offline_file_analysis_accessed_phone", "phone_modified",
                      "firmware_executed", "image_mounted", "symlinks_followed",
                      "analysis_v1_properties_usable"):
            self.assertIs(provenance[field], False, field)
        self.assertTrue(provenance["private_artifacts_git_ignored"])
        self.assertTrue(provenance["analysis"].endswith("/vintf-analysis-v2.json"))
        verified = {"xml_well_formedness_and_recorded_hashes_verified", "requested_runtime_properties_read"}
        for field, value in record["verification_boundaries"].items():
            self.assertIs(value, field in verified, field)

    def test_capture_totals_and_parent_image_hashes_agree(self):
        partitions = self.record["partitions"]
        scope = self.record["scope"]
        layout = {p["name"]: p for p in self.layout["partitions"] if p["size_bytes"]}
        self.assertEqual({p["name"] for p in partitions}, set(layout))
        self.assertEqual(len(partitions), scope["logical_images"])
        self.assertEqual(scope["logical_images"], 8)
        for field, total in (("inventory_entries", "inventory_entries"),
                             ("capture_files", "contract_capture_files"),
                             ("capture_bytes", "contract_capture_bytes")):
            self.assertEqual(sum(p[field] for p in partitions), scope[total])
        self.assertEqual(scope["inventory_entries"], 16038)
        self.assertEqual(scope["contract_capture_files"], 1306)
        self.assertEqual(scope["contract_capture_bytes"], 343023223)
        self.assertEqual(scope["separate_vendor_camera_capture_files"], 7)
        self.assertEqual(scope["separate_manual_native_seed_files"], 13)
        for partition in partitions:
            with self.subTest(partition=partition["name"]):
                parent = layout[partition["name"]]
                self.assertEqual(partition["image_sha256"], parent["extraction"]["sha256"])
                self.assertEqual(partition["image_size_bytes"], parent["size_bytes"])
                path = PurePosixPath(partition["capture_receipt"])
                self.assertFalse(path.is_absolute())
                self.assertNotIn("..", path.parts)
                self.assertEqual(path.parts[0], "artifacts")
                self.assertEqual(path.name, "receipt.json")
                for field in ("image_sha256", "inventory_sha256", "inventory_receipt_sha256",
                              "capture_receipt_sha256"):
                    self.assertRegex(partition[field], r"^[a-f0-9]{64}$")

    def test_xml_counts_keep_manifest_roles_and_empty_overrides_distinct(self):
        scope = self.record["scope"]
        roles = {(d["xml_kind"], d["xml_type"]): d for d in scope["document_counts"]}
        expected = {("manifest", "device"): (177, 221),
                    ("manifest", "framework"): (22, 37),
                    ("compatibility-matrix", "framework"): (9, 859),
                    ("compatibility-matrix", "device"): (1, 3)}
        self.assertEqual(set(roles), set(expected))
        for key, (documents, hals) in expected.items():
            self.assertEqual(roles[key]["documents"], documents)
            self.assertEqual(roles[key]["hal_elements"], hals)
            self.assertEqual(sum(roles[key]["hal_formats"].values()), hals)
        self.assertEqual(sum(d["documents"] for d in roles.values()), scope["vintf_xml_files"])
        self.assertEqual(scope["vintf_xml_files"], 209)
        self.assertEqual(sum(d["hal_elements"] for d in roles.values()), scope["hal_elements"])
        self.assertEqual(scope["hal_elements"], 1120)
        self.assertEqual(roles[("manifest", "device")]["hal_formats"], {"aidl": 220, "native": 1})
        self.assertEqual(scope["device_manifest_empty_override_elements"], 22)
        self.assertEqual(scope["matrix_hal_elements_with_optional_attribute"], 0)
        self.assertTrue(scope["counts_are_unmerged_xml_elements_not_running_services"])
        self.assertFalse(scope["active_apex_manifests_included"])

    def test_live_xml_match_has_a_narrow_scope(self):
        comparison = self.record["live_comparison"]
        self.assertEqual(comparison["vintf_xml"], 209)
        self.assertEqual(comparison["permission_xml"], 223)
        self.assertEqual(comparison["vintf_xml"] + comparison["permission_xml"],
                         comparison["xml_paths_and_sha256_equal"])
        self.assertEqual(comparison["xml_paths_and_sha256_equal"], 432)
        self.assertTrue(comparison["all_compared_xml_paths_and_sha256_match"])
        self.assertFalse(comparison["proves_complete_os_identity"])
        self.assertFalse(comparison["proves_effective_vintf"])
        self.assertRegex(comparison["baseline_manifest_sha256"], r"^[a-f0-9]{64}$")

    def test_source_paths_retain_partition_and_flat_capture_mapping(self):
        partitions = {p["name"]: p for p in self.record["partitions"]}
        for path, source in self.record["source_files"].items():
            with self.subTest(path=path):
                parsed = PurePosixPath(path)
                self.assertEqual(str(parsed), path)
                self.assertTrue(parsed.is_absolute())
                self.assertNotIn("..", parsed.parts)
                self.assertEqual(source["logical_partition"], parsed.parts[1] + "_a")
                self.assertIn(source["logical_partition"], partitions)
                self.assertRegex(source["sha256"], r"^[a-f0-9]{64}$")
                self.assertGreater(source["size_bytes"], 0)
                self.assertGreaterEqual(source["nid"], 0)
                self.assertRegex(source["captured_file"], r"^files/[0-9]{4}$")

    def test_properties_are_keyed_by_complete_path_not_mount_name(self):
        props = self.record["properties_by_source"]
        self.assertEqual(len(props), 9)
        vendor = props["/vendor/build.prop"]
        self.assertEqual(vendor["ro.board.platform"], "canoe")
        self.assertEqual(vendor["ro.board.api_level"], "202504")
        self.assertEqual(vendor["ro.board.first_api_level"], "202504")
        self.assertEqual(vendor["ro.board.api_frozen"], "true")
        self.assertEqual(vendor["ro.vendor.build.version.sdk"], "36")
        self.assertEqual(vendor["ro.vendor.build.security_patch"], "2026-02-01")
        self.assertEqual(props["/vendor/odm_dlkm/etc/build.prop"], {})
        self.assertEqual(props["/system/build.prop"]["ro.llndk.api_level"], "202504")
        self.assertEqual(props["/odm/etc/build.prop"]["ro.product.first_api_level"], "36")
        self.assertNotEqual(props["/system/build.prop"]["ro.build.version.incremental"],
                            vendor["ro.vendor.build.version.incremental"])
        for source, values in props.items():
            self.assertIn(source, self.record["source_files"])
            self.assertNotIn("ro.vendor.api_level", values)
        self.assertEqual(set(self.record["runtime_properties_missing_from_initial_baseline"]),
                         {"ro.boot.product.vendor.sku", "ro.boot.product.hardware.sku", "ro.vendor.api_level"})
        self.assertEqual(self.record["runtime_properties_not_verified"], [])

    def test_followup_reports_only_requested_properties_after_identity_checks(self):
        observation = self.record["runtime_property_observations"]
        expected = {"ro.boot.product.vendor.sku": "canoe",
                    "ro.boot.product.hardware.sku": "nezha", "ro.vendor.api_level": "202504"}
        self.assertEqual(observation["status"], "complete")
        self.assertEqual(observation["properties"],
                         {key: {"status": "ok", "value": value} for key, value in expected.items()})
        self.assertEqual(observation["command_count"], 2 + 3 + len(expected))
        self.assertEqual(observation["command_artifact_count"], 2 * observation["command_count"])
        self.assertTrue(observation["requested_properties_only_after_identity_preflight"])
        self.assertTrue(observation["command_artifact_readback_verified"])
        self.assertEqual(observation["device_identity"], {
            "manufacturer": "Xiaomi", "codename": "nezha", "non_emulator_preflight_passed": True,
            "same_explicit_private_serial_as_baseline": True,
        })
        for name, value in expected.items():
            self.assertEqual(observation["property_stdout_sha256"][name],
                             hashlib.sha256((value + "\n").encode()).hexdigest())
        for field in ("phone_modified", "origin_verified", "properties_are_immutable_hardware_proof",
                      "complete_effective_vintf_verified"):
            self.assertFalse(observation[field])

    def test_followup_is_a_new_private_receipt_not_a_rewritten_baseline(self):
        observation = self.record["runtime_property_observations"]
        path = PurePosixPath(observation["private_receipt"])
        self.assertFalse(path.is_absolute())
        self.assertNotIn("..", path.parts)
        self.assertEqual(path.parts[0], "evidence")
        self.assertTrue(path.parts[1].startswith("vintf-properties-"))
        self.assertEqual(path.name, "receipt.json")
        self.assertNotEqual(str(path.parent),
                            str(PurePosixPath(self.record["live_comparison"]["baseline_manifest"]).parent))
        self.assertTrue(observation["previous_manifest_unchanged"])
        self.assertEqual(observation["previous_manifest_sha256"],
                         self.record["live_comparison"]["baseline_manifest_sha256"])
        self.assertEqual(observation["collector"], "scripts/collect_stock.py")
        for field in ("private_receipt_sha256", "private_manifest_sha256", "collector_sha256"):
            self.assertRegex(observation[field], r"^[a-f0-9]{64}$")

    def test_lookup_inference_uses_pinned_rules_without_claiming_loader_success(self):
        lookup = self.record["manifest_lookup_inference"]
        reference = lookup["reference"]
        manifest = ET.parse(ROOT / "research/source-snapshots/evolution-bka-20260827.xml").getroot()
        project = next(p for p in manifest.findall("project") if p.get("path") == "system/libvintf")
        self.assertEqual(reference["commit"], project.get("revision"))
        self.assertEqual(reference["project"], project.get("name"))
        self.assertRegex(reference["sha256"], r"^[a-f0-9]{64}$")
        self.assertIn(reference["commit"], reference["url"])
        self.assertIn(reference["url"], self.record["primary_references"])
        self.assertEqual([entry["path"] for entry in lookup["vendor_lookup_order"]],
                         ["/vendor/etc/vintf/manifest_canoe.xml", "/vendor/etc/vintf/manifest.xml"])
        first = lookup["vendor_lookup_order"][0]
        self.assertEqual(first["path"], lookup["first_existing_vendor_lookup_path"])
        self.assertTrue(first["entry_observed_in_image_inventory"])
        self.assertEqual(first["type"], "regular")
        self.assertIn(first["path"], self.record["source_files"])
        self.assertFalse(lookup["alor_manifest_in_observed_sku_lookup_order"])
        self.assertEqual([entry["path"] for entry in lookup["odm_lookup_order"]], [
            "/odm/etc/vintf/manifest_nezha.xml", "/odm/etc/vintf/manifest.xml",
            "/odm/etc/manifest_nezha.xml", "/odm/etc/manifest.xml",
        ])
        self.assertTrue(all(not e["entry_observed_in_image_inventory"] and e["type"] is None
                            for e in lookup["odm_lookup_order"]))
        self.assertFalse(lookup["odm_base_manifest_observed_in_image"])
        self.assertTrue(lookup["odm_fragments_observed_in_image"])
        self.assertTrue(lookup["lookup_fallback_requires_name_not_found"])
        for field in ("live_xiaomi_eu_libvintf_binary_verified_against_reference",
                      "complete_fragment_and_apex_merge_verified", "loader_schema_validation_performed"):
            self.assertFalse(lookup[field])

    def test_target_candidates_do_not_claim_runtime_sku_selection(self):
        candidates = self.record["vendor_manifest_candidates"]
        self.assertEqual({PurePosixPath(c["source"]).name for c in candidates},
                         {"manifest_canoe.xml", "manifest_alor.xml"})
        for candidate in candidates:
            self.assertEqual(candidate["attributes"],
                             {"version": "9.0", "type": "device", "target-level": "202504"})
            self.assertEqual(candidate["sepolicy_version"], "202504")
            self.assertFalse(candidate["explicit_kernel_element"])
            self.assertFalse(candidate["runtime_selection_verified"])

    def test_selected_device_hals_are_manifest_declarations_not_matrix_entries(self):
        declarations = self.record["selected_device_hal_declarations"]
        self.assertEqual(len(declarations), 63)
        for declaration in declarations:
            source = self.record["source_files"][declaration["source"]]
            self.assertEqual((source["xml_kind"], source["xml_type"]), ("manifest", "device"))
            self.assertNotIn("/qspa/", declaration["source"])
            self.assertIn(declaration["format"], {"aidl", "native"})
            self.assertTrue(declaration.get("fqnames") or declaration.get("interfaces"))
            for version in declaration["declared_versions"]:
                self.assertRegex(version, r"^[1-9][0-9]*$")
        by_name = {}
        for declaration in declarations:
            by_name.setdefault(declaration["name"], []).append(declaration)
        for name, version in (("android.hardware.biometrics.fingerprint", "4"),
                              ("android.hardware.biometrics.face", "4"),
                              ("android.hardware.radio.config", "4"),
                              ("vendor.qti.hardware.radio.ims", "20"),
                              ("android.hardware.power", "6")):
            self.assertEqual(by_name[name][0]["declared_versions"], [version])
        camera = {d["fqnames"][0]: d for d in by_name["android.hardware.camera.provider"]}
        self.assertEqual(camera["ICameraProvider/vendor_qti/0"]["declared_versions"], ["3"])
        self.assertEqual(camera["ICameraProvider/external/0"]["declared_versions"], [])
        self.assertEqual(by_name["vendor.xiaomi.hardware.postprocservice"][0]["declared_versions"], [])
        self.assertEqual(by_name["android.hardware.vibrator"][0]["override"], "true")
        self.assertEqual(by_name["mapper"][0]["fqnames"], ["@5.0/qti"])

    def test_empty_overrides_remain_separate_and_activation_unverified(self):
        profiles = self.record["nested_profile_empty_overrides"]
        counts = {PurePosixPath(p["source"]).name: len(p["empty_overrides"]) for p in profiles}
        self.assertEqual(counts, {"qspa-modem.xml": 21, "qspa-nav.xml": 1})
        self.assertEqual(sum(counts.values()), self.record["scope"]["device_manifest_empty_override_elements"])
        for profile in profiles:
            self.assertFalse(profile["activation_verified"])
            self.assertIn(profile["source"], self.record["source_files"])
            for declaration in profile["empty_overrides"]:
                self.assertEqual(declaration["override"], "true")
                self.assertEqual(declaration["format"], "aidl")
                self.assertNotIn("fqnames", declaration)
                self.assertNotIn("interfaces", declaration)
                self.assertNotIn("declared_versions", declaration)

    def test_framework_requirements_and_legacy_camera_are_not_provider_proof(self):
        matrix = self.record["device_to_framework_matrix"]
        self.assertEqual(matrix["system_sdk_versions"], ["36"])
        self.assertFalse(matrix["merged_compatibility_verified"])
        requirements = matrix["requirements"]
        self.assertEqual(len(requirements), 3)
        for requirement in requirements:
            self.assertEqual(requirement["source"], matrix["source"])
            self.assertEqual(requirement["format"], "aidl")
            self.assertEqual(requirement["declared_versions"], [])
        matches = matrix["matching_static_framework_manifest_declarations"]
        self.assertEqual({m["name"] for m in matches if m["format"] == "aidl"},
                         {r["name"] for r in requirements})
        hidl = [m for m in matches if m["format"] == "hidl"]
        self.assertEqual(len(hidl), 1)
        self.assertEqual(hidl[0]["max-level"], "8")
        legacy = self.record["legacy_matrix_only_camera_name"]
        source = self.record["source_files"][legacy["declaration"]["source"]]
        self.assertEqual(source["xml_kind"], "compatibility-matrix")
        self.assertEqual(legacy["declaration"]["name"], "vendor.xiaomi.hardware.campostproc")
        self.assertEqual(legacy["declaration"]["declared_versions"], ["1.0"])
        self.assertEqual(legacy["matching_device_manifest_declarations"], 0)
        self.assertFalse(legacy["optional_attribute_present"])
        self.assertFalse(legacy["runtime_service_verified"])

    def test_kernel_conditional_sets_are_not_all_unconditional_requirements(self):
        kernel = self.record["kernel_matrix"]
        self.assertEqual(kernel["framework_level"], "202504")
        self.assertEqual(kernel["kernel_level"], "202504")
        self.assertEqual(kernel["minimum_version"], "6.12.0")
        self.assertEqual(kernel["unconditional_config_count"], 260)
        conditional = kernel["conditional_fragments"]
        self.assertEqual(len(conditional), 10)
        self.assertEqual(kernel["kernel_fragment_count"], 1 + len(conditional))
        self.assertTrue(all(c["conditions_all"] for c in conditional))
        self.assertEqual(sum(c["config_count"] for c in conditional), 32)
        self.assertEqual(kernel["config_elements_across_all_fragments"], 292)
        arm64 = [c for c in conditional if c["conditions_all"] ==
                 [{"name": "CONFIG_ARM64", "type": "tristate", "value": "y"}]]
        self.assertEqual(arm64[0]["config_count"], 14)
        self.assertEqual(len([c for c in conditional if len(c["conditions_all"]) == 2]), 1)
        boot = json.loads((ROOT / "research/boot-contract.json").read_text())
        self.assertEqual(kernel["observed_kernel_release"], boot["kernel"]["release"])
        numeric = tuple(map(int, kernel["observed_kernel_release"].split("-", 1)[0].split(".")))
        self.assertGreaterEqual(numeric, (6, 12, 0))
        self.assertTrue(kernel["numeric_minimum_met"])
        for key in ("numeric_comparison_is_complete_compatibility", "effective_kernel_fcm_verified",
                    "all_applicable_configs_matched"):
            self.assertFalse(kernel[key])
        policy = self.record["framework_policy_matrix"]
        self.assertEqual(policy["kernel_sepolicy_version"], "30")
        self.assertIn("202504", policy["sepolicy_versions"])
        self.assertFalse(policy["vbmeta_field_proves_package_authenticity"])

    def test_postproc_permission_path_discrepancy_stays_unresolved(self):
        path = self.record["postproc_library_path"]
        jar = path["observed_regular_file"]
        self.assertEqual(path["declared_path"], "/system/framework/" + path["library_name"] + ".jar")
        self.assertEqual(jar["runtime_path"], "/system_ext/framework/" + path["library_name"] + ".jar")
        camera = json.loads((ROOT / path["native_seed_receipt_record"]).read_text())
        self.assertIn(jar, camera["artifacts"])
        for key in ("declared_path_entry_observed_in_system_inventory", "matching_alias_observed",
                    "runtime_path_resolution_verified"):
            self.assertFalse(path[key])
        self.assertIn(path["permission_source"], self.record["source_files"])

    def test_inspection_contract_and_document_keep_safety_limits(self):
        inspection = self.record["inspection"]
        self.assertEqual(inspection["script"], "scripts/erofs_inventory.py")
        self.assertEqual(inspection["tool"]["version"], "dump.erofs (erofs-utils) 1.9.4")
        self.assertRegex(inspection["tool"]["sha256"], r"^[a-f0-9]{64}$")
        for key, value in inspection.items():
            if isinstance(value, bool):
                self.assertTrue(value, key)
        document = (ROOT / "docs/vintf-contract.md").read_text()
        for text in (self.record["provenance"]["package_sha256"], "1,306", "16,038", "432",
                     "vintf-analysis-v2.json", "symlinks", "checkvintf", "unverified",
                     "erofs_inventory.py", "manifest_canoe.xml"):
            self.assertIn(text.lower(), document.lower())

    def test_record_contains_no_private_host_or_device_identifier_fields(self):
        forbidden = {"serial", "serialno", "imei", "imsi", "meid", "account", "email", "phone_number"}

        def check(value):
            if isinstance(value, dict):
                self.assertFalse(forbidden.intersection(value))
                for key, child in value.items():
                    check(key)
                    check(child)
            elif isinstance(value, list):
                for child in value:
                    check(child)
            elif isinstance(value, str):
                self.assertNotIn("/Users/", value)
                self.assertNotIn("/home/", value)

        check(self.record)


if __name__ == "__main__":
    unittest.main()
