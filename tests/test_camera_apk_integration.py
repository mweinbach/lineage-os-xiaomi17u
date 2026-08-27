"""Check sanitized APK prerequisite evidence without private files or tools."""

import json
from pathlib import Path, PurePosixPath
import unittest
import xml.etree.ElementTree as ET

from scripts import vendor_inputs


ROOT = Path(__file__).resolve().parents[1]
RUNTIME_LIBRARIES = ["miui-cameraopt", "androidx.window.extensions", "androidx.window.sidecar"]


class CameraApkIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = (ROOT / "research/camera-apk-integration.json").read_text()
        cls.record = json.loads(cls.raw)
        cls.camera = json.loads((ROOT / "research/camera-dependencies.json").read_text())
        cls.selection = json.loads((ROOT / "vendor/xiaomi/nezha/camera-selection.json").read_text())
        cls.checks = {check["name"]: check for check in cls.record["standalone_checks"]}
        cls.document = " ".join((ROOT / "docs/camera-apk-integration.md").read_text().replace("**", "").split())

    def test_apk_identity_matches_the_existing_captured_dependency_record(self):
        record = self.record
        self.assertEqual(record["schema_version"], 1)
        self.assertEqual((record["device"], record["hardware_region"]), ("nezha", "CN"))
        self.assertEqual(record["apk"]["package"], "com.android.camera")
        self.assertEqual(record["apk"]["runtime_path"], "/product/priv-app/MiuiCamera/MiuiCamera.apk")
        for key in ("sha256", "size_bytes"):
            self.assertEqual(record["apk"][key], self.camera["camera_apk"][key])
        self.assertEqual(record["provenance"]["package_sha256"], self.camera["provenance"]["package_sha256"])
        self.assertIs(record["apk"]["unchanged_after_checks"], True)
        self.assertEqual(record["apk"]["zip_crc_verified_entries"], 9477)
        self.assertIs(record["provenance"]["origin_verified"], False)
        self.assertIs(record["provenance"]["package_avb_consistent"], False)

    def test_manifest_does_not_invent_shared_uid_or_required_libraries(self):
        manifest = self.record["manifest"]
        self.assertIs(manifest["shared_user_id_declared"], False)
        self.assertIs(manifest["shared_user_max_sdk_declared"], False)
        self.assertEqual(manifest["fresh_aapt2_shared_user_tokens"], 0)
        self.assertEqual((manifest["min_sdk"], manifest["target_sdk"]), (29, 35))
        self.assertIs(manifest["extract_native_libs"], False)
        self.assertEqual(manifest["optional_uses_libraries_in_order"], RUNTIME_LIBRARIES)
        self.assertEqual(self.record["uses_library_contract"]["required_uses_libraries"], [])

    def test_valid_signature_is_not_promoted_to_origin_or_platform_affinity(self):
        signing = self.record["signature"]
        self.assertIs(signing["apksigner_verifies"], True)
        self.assertEqual(signing["verified_schemes"], ["v3"])
        self.assertEqual((signing["signers"], signing["key_algorithm"], signing["key_size_bits"]), (1, "RSA", 2048))
        self.assertRegex(signing["certificate_sha256"], r"^[a-f0-9]{64}$")
        self.assertEqual({PurePosixPath(item["path"]).name for item in signing["compared_public_certificates"]},
                         {"platform.x509.pem", "testkey.x509.pem"})
        for item in signing["compared_public_certificates"]:
            self.assertNotEqual(item["certificate_der_sha256"], signing["certificate_sha256"])
            self.assertRegex(item["certificate_der_sha256"], r"^[a-f0-9]{64}$")
        for field in ("matches_pinned_default_platform_or_testkey", "origin_authenticated", "permission_grants_verified",
                      "actual_installed_platform_signature_or_future_release_key_verified"):
            self.assertIs(signing[field], False)

    def test_only_exact_signature_protection_permissions_are_classified_as_pure(self):
        self.assertEqual(self.record["signature"]["pure_platform_signature_permissions_requested"], [
            "android.permission.CONTROL_DEVICE_STATE",
            "android.permission.CONTROL_DISPLAY_BRIGHTNESS",
            "android.permission.INJECT_EVENTS",
        ])
        self.assertNotIn("android.permission.SYSTEM_CAMERA",
                         self.record["signature"]["pure_platform_signature_permissions_requested"])

    def test_zip_alignment_and_elf_page_layout_remain_distinct(self):
        alignment = self.record["alignment"]
        self.assertEqual(alignment["observed_nezha_kernel_page_size_bytes"], 4096)
        self.assertEqual(alignment["native_libraries"], 40)
        self.assertEqual(alignment["native_stored_and_zip_aligned_16k"], 40)
        self.assertEqual(alignment["elf_pt_load_alignment_and_congruence_4k_pass"], 40)
        self.assertEqual(alignment["elf_pt_load_alignment_and_congruence_16k_pass"], 37)
        exceptions = alignment["four_kib_only_elf_details"]
        self.assertEqual({PurePosixPath(item["path"]).name for item in exceptions},
                         {"libHawk.so", "libavif_android.so", "libpendant.so"})
        self.assertEqual(len(exceptions) + alignment["elf_pt_load_alignment_and_congruence_16k_pass"], 40)
        self.assertEqual({item["path"] for item in exceptions}, set(alignment["elf_4k_only_paths"]))
        for item in exceptions:
            self.assertEqual(item["pt_load_alignments"], [4096])
            self.assertRegex(item["sha256"], r"^[a-f0-9]{64}$")
            self.assertGreater(item["size_bytes"], 0)
        self.assertEqual(alignment["independent_readelf_crosschecked_exception_libraries"], 3)
        self.assertIs(alignment["all_zip_aligned_16k_does_not_prove_all_elf_aligned_16k"], True)
        self.assertIs(alignment["runtime_linking_or_execution_verified"], False)

    def test_packaging_failures_are_preserved_and_do_not_suggest_skipping_checks(self):
        packaging = self.record["dex_packaging"]
        self.assertEqual((packaging["dex_entries"], packaging["compressed_dex_entries"]), (8, 8))
        self.assertEqual(packaging["compressed_jni_entries"], 0)
        self.assertIs(packaging["preprocessed_required_for_retained_signature_at_target_sdk_35"], True)
        self.assertIs(packaging["unprivileged_check_pass_does_not_approve_privilege_removal"], True)
        expected = {"presigned-without-preprocessed": 1, "preprocessed-normal": 0,
                    "preprocessed-privileged-uncompress": 1}
        for name, code in expected.items():
            self.assertEqual(self.checks[name]["exit_code"], code)
        self.assertEqual(self.checks["preprocessed-privileged-uncompress"]["arguments"],
                         ["--preprocessed", "--privileged", "--uncompress-priv-app-dex"])
        self.assertIs(self.record["observed_product_policy"]["UncompressPrivAppDex"], True)

    def test_manifest_name_checks_preserve_exact_order_and_current_name_failure(self):
        contract = self.record["uses_library_contract"]
        self.assertEqual(self.checks["manifest-exact"]["optional_uses_libraries"], RUNTIME_LIBRARIES)
        self.assertEqual(self.checks["manifest-exact"]["exit_code"], 0)
        self.assertEqual(self.checks["manifest-current-module"]["exit_code"], 255)
        self.assertEqual(self.checks["manifest-current-module"]["optional_uses_libraries"][0],
                         contract["current_cameraopt_module"])
        qualified = self.checks["manifest-qualified-runtime"]
        self.assertEqual(qualified["exit_code"], 0)
        self.assertEqual(qualified["optional_uses_libraries"][0], "//vendor/xiaomi/nezha:miui-cameraopt")
        self.assertIs(contract["declared_library_order_matters"], True)
        self.assertIs(contract["renaming_dex_import_alone_sufficient"], False)

    def test_current_dex_selection_is_not_misrepresented_as_a_class_loader_provider(self):
        contract = self.record["uses_library_contract"]
        modules, _ = vendor_inputs._selection(ROOT / "vendor/xiaomi/nezha/camera-selection.json",
                                             self.selection["package_sha256"], [])
        cameraopt = next(module for module in modules if module["runtime_path"] == "/system_ext/framework/miui-cameraopt.jar")
        self.assertEqual(cameraopt["module_name"], contract["current_cameraopt_module"])
        self.assertEqual(cameraopt["type"], "dex_jar")
        self.assertIn("dex_import {", vendor_inputs._module_text(cameraopt))
        self.assertNotIn("provides_uses_lib", vendor_inputs._module_text(cameraopt))
        for key in ("current_dex_import_has_uses_library_dependency_provider", "current_dex_import_exposes_provides_uses_lib",
                    "dependency_graph_with_apk_verified", "provider_extension_implemented"):
            self.assertIs(contract[key], False)
        self.assertIn("Static inspection", contract["provider_conclusion"])
        self.assertEqual(contract["platform_window_modules"], RUNTIME_LIBRARIES[1:])
        self.assertEqual(contract["platform_window_module_type"], "java_library")

    def test_observed_relaxation_is_separate_from_the_uninstalled_authored_fix(self):
        observed = self.record["observed_product_policy"]
        fix = self.record["authored_strict_fix"]
        self.assertIs(observed["RelaxUsesLibraryCheck"], True)
        self.assertIs(observed["DisablePreopt"], False)
        self.assertIs(observed["OnlyPreoptArtBootImage"], False)
        self.assertIs(observed["WithDexpreopt"], True)
        self.assertEqual(observed["relaxation_source"]["assignment"], "RELAX_USES_LIBRARY_CHECK=true")
        self.assertEqual(observed["relaxation_source"]["path"], "bcr/bcr.mk")
        self.assertEqual(observed["relaxation_source"]["line"], 6)
        self.assertIs(observed["product_broken_flag_alone_overrides_relaxation"], False)
        self.assertEqual(fix["commit"], "91832e011a2703e73fd093afc7b0ee0f0ad5704d")
        self.assertEqual(fix["assignment"], "RELAX_USES_LIBRARY_CHECK := false")
        self.assertIs(fix["installed_at_this_snapshot"], False)
        self.assertIs(fix["generated_configuration_readback_verified"], False)
        self.assertIn("framework-v5/admission.json", fix["admission"]["path"])
        self.assertEqual(fix["required_next_configuration"], {
            "RelaxUsesLibraryCheck": False, "DisablePreopt": False,
            "OnlyPreoptArtBootImage": False, "WithDexpreopt": True,
        })
        self.assertEqual(fix["actual_uses_library_commands_must_omit"], "--enforce-uses-libraries-relax")

    def test_documented_board_override_matches_the_authored_late_guard(self):
        board = (ROOT / self.record["authored_strict_fix"]["path"]).read_text()
        strict = "RELAX_USES_LIBRARY_CHECK := false"
        self.assertIn(strict, board)
        self.assertLess(board.index("include vendor/lineage/config/BoardConfigLineage.mk"), board.index(strict))
        self.assertIn("ifneq ($(RELAX_USES_LIBRARY_CHECK),false)", board)
        self.assertIn("Nezha requires strict APK uses-library validation", board)
        self.assertIn("At this snapshot, v5 was not installed", self.document)
        self.assertIn("The earlier running build used v4", self.document)

    def test_primary_source_revisions_match_the_resolved_manifest(self):
        manifest = ET.parse(ROOT / "research/source-snapshots/evolution-bka-20260827.xml").getroot()
        projects = {p.get("path"): p for p in manifest.findall("project")}
        pins = self.record["source_pins"]
        for path, revision in pins.items():
            self.assertEqual(projects[path].get("revision"), revision)
        seen = set()
        for source in self.record["source_files"]:
            with self.subTest(source=source["path"]):
                self.assertEqual(source["revision"], pins[source["project"]])
                expected = ("https://github.com/Evolution-X/" + projects[source["project"]].get("name")
                            + "/blob/" + source["revision"] + "/" + source["path"])
                self.assertEqual(source["url"], expected)
                self.assertNotIn((source["project"], source["path"]), seen)
                seen.add((source["project"], source["path"]))
                if "sha256" in source:
                    self.assertRegex(source["sha256"], r"^[a-f0-9]{64}$")
        self.assertIn(("vendor/extras", "bcr/bcr.mk"), seen)
        self.assertIn(("build/soong", "java/java.go"), seen)
        self.assertIn(("frameworks/base", "core/res/AndroidManifest.xml"), seen)

    def test_evidence_links_are_hashes_and_metadata_not_private_contents(self):
        provenance = self.record["provenance"]
        receipt = provenance["private_review_receipt"]
        self.assertEqual(receipt["path"], "reports/camera-apk-import-review-20260827/receipt.json")
        self.assertEqual(receipt["sha256"], "2b0732ea80574aecd436a9e2e2177fc4fdef750599dc802519368c90bbf767a2")
        self.assertEqual(len(provenance["private_evidence_files"]), 8)
        for name, digest in provenance["private_evidence_files"].items():
            self.assertEqual(PurePosixPath(name).name, name)
            self.assertRegex(digest, r"^[a-f0-9]{64}$")
        for forbidden in ("/Users/", "-----BEGIN", "<manifest", '"serial"', '"password"', '"certificate_pem"'):
            self.assertNotIn(forbidden, self.raw)
        tools = self.record["tool_versions"]
        self.assertEqual(tools["sdk_build_tools"], "36.0.0")
        for digest in tools["sdk_files_sha256"].values():
            self.assertRegex(digest, r"^[a-f0-9]{64}$")

    def test_host_checks_are_not_promoted_to_apk_or_device_validation(self):
        boundaries = self.record["verification_boundaries"]
        self.assertIs(boundaries["standalone_host_validators_exercised"], True)
        for key, value in boundaries.items():
            if key == "standalone_host_validators_exercised":
                continue
            if key in ("checks_disabled", "checks_to_bypass"):
                self.assertEqual(value, [])
            else:
                self.assertIs(value, False, key)
        for check in self.checks.values():
            args = check.get("arguments", [])
            self.assertNotIn("--skip-preprocessed-apk-checks", args)
            self.assertNotIn("--enforce-uses-libraries-relax", args)
            self.assertNotIn("sign", args)
            self.assertNotIn("-f", args)
        self.assertIn("No permission, signature, compression, uses-library or ELF bypass is proposed", self.document)
        self.assertIn("No APK was imported, rewritten, signed, installed or executed", self.document)


if __name__ == "__main__":
    unittest.main()
