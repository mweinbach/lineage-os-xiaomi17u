"""Offline contract checks; no private inputs, M4, subprocesses or device.

Actual host M4 evidence and future Android policy verification are separate.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest


ROOT = Path(__file__).resolve().parents[1]
SYMBOL = "target_vendor_persist_camera_prop_vendor_init_writes"
CAMERA = "vendor_persist_camera_prop"
BEFORE_SHA = "e0448d64ba284410fb5281ee3390d53aee0b3730cf6ab0f44926009d5b50d6f7"
AFTER_SHA = "f61da3a36e2cbea8c74284270da46dc0ba8459483eea740e5aa2818440f9e3c4"
BEFORE_BLOB = "17c5cd0e38d7dea6cc9bc4e448db24349ff8415b"
AFTER_BLOB = "a86de112ec1df669198fd74a9bbe40e3a00e8ddc"
ASSERTION = "neverallow { domain -init -vendor_init } vendor_persist_camera_prop:property_service set;"
HEADER = (
    "diff --git a/common/public/property.te b/common/public/property.te\n"
    f"index {BEFORE_BLOB}..{AFTER_BLOB} 100644\n"
    "--- a/common/public/property.te\n+++ b/common/public/property.te\n"
    "@@ -1,11 +1,19 @@\n"
)
VALIDATOR = (
    f"ifdef(`{SYMBOL}', `ifelse(defn(`{SYMBOL}'), `true', `',\n"
    f"       defn(`{SYMBOL}'), `false', `',\n"
    f"       `errprint(`{SYMBOL} must be true or false\n"
    "')m4exit(1)')')dnl\n"
)
SELECTION = (
    f"ifelse(defn(`{SYMBOL}'), `false', `system_public_prop({CAMERA})\n"
    "unix_socket_connect(vendor_init, property, init)\n"
    f"get_prop(vendor_init, {CAMERA})\n"
    f"{ASSERTION}',\n"
    f"`system_vendor_config_prop({CAMERA})')\n"
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_pair(raw):
    """Reconstruct only the pinned complete source pair from the full hunk."""
    if type(raw) is not bytes or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Complete LF patch bytes required")
    text = raw.decode("utf-8")
    if not text.startswith(HEADER):
        raise ValueError("Unreviewed path, mode, blobs or hunk positions")
    lines = text[len(HEADER):].splitlines(keepends=True)
    if any(line[:1] not in (" ", "+", "-") for line in lines):
        raise ValueError("Unexpected patch syntax")
    before = "".join(line[1:] for line in lines if line.startswith((" ", "-"))).encode()
    after = "".join(line[1:] for line in lines if line.startswith((" ", "+"))).encode()
    if (len(before.splitlines()), len(before), sha(before)) != (11, 267, BEFORE_SHA):
        raise ValueError("Original complete source differs")
    if (len(after.splitlines()), len(after), sha(after)) != (19, 925, AFTER_SHA):
        raise ValueError("Guarded complete source differs")
    return before, after


class CameraPropertyVendorInitWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "patches/evolution/camera-property-vendor-init-write.json").read_bytes())
        cls.patch = (ROOT / cls.record["patch"]).read_bytes()
        cls.before, cls.after = source_pair(cls.patch)

    def test_exact_project_patch_and_source_pair_are_pinned(self):
        r = self.record
        self.assertEqual(r["schema_version"], 1)
        self.assertEqual(r["contract_id"], "nezha-camera-property-vendor-init-no-write-v1")
        self.assertEqual((r["project"], r["branch"]), ("device/lineage/sepolicy", "bka"))
        self.assertEqual(r["base_commit"], "37c13c9b74344c17eddd6067541e9fcba116a34e")
        self.assertEqual(r["patch_sha256"], "ed58352acd05991a22d48efd829dca9af8060baa071a664ef7aed0d2e963a1b3")
        self.assertEqual((sha(self.patch), len(self.patch)), (r["patch_sha256"], r["patch_size_bytes"]))
        self.assertEqual(len(r["files"]), 1)
        item = r["files"][0]
        self.assertEqual((item["path"], item["mode"]), ("common/public/property.te", "100644"))
        for label, raw in (("before", self.before), ("after", self.after)):
            self.assertEqual((item[label + "_sha256"], item[label + "_size_bytes"]), (sha(raw), len(raw)))
            self.assertEqual(item[label + "_git_blob"],
                             hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest())

    def test_only_the_camera_macro_invocation_is_replaced(self):
        original = f"system_vendor_config_prop({CAMERA})\n".encode()
        replacement = (VALIDATOR + SELECTION).encode()
        self.assertEqual(self.before.count(original), 1)
        self.assertEqual(self.after, self.before.replace(original, replacement))
        self.assertEqual(self.after.replace(replacement, original), self.before)
        lines = self.patch.decode()[len(HEADER):].splitlines()
        self.assertEqual([line[1:] for line in lines if line.startswith("-")], [original.decode().rstrip("\n")])
        self.assertEqual(self.patch.count(b"diff --git "), 1)

    def test_value_validation_precedes_every_camera_grant(self):
        source = self.after.decode()
        self.assertEqual(source.splitlines()[0], "# Aux camera allow/excludelist prop")
        self.assertTrue(source.startswith("# Aux camera allow/excludelist prop\n" + VALIDATOR))
        self.assertLess(source.index(VALIDATOR), source.index(SELECTION))
        self.assertIn("m4exit(1)", VALIDATOR)
        self.assertNotIn("m4exit(0)", source)
        self.assertEqual(source.count("defn(`" + SYMBOL + "')"), 3)
        self.assertNotIn("define(`" + SYMBOL, source)

    def test_disabled_branch_preserves_type_socket_read_and_original_assertion(self):
        disabled = SELECTION.split("`false', `", 1)[1].split("',\n", 1)[0]
        self.assertEqual(disabled.splitlines(), [
            f"system_public_prop({CAMERA})",
            "unix_socket_connect(vendor_init, property, init)",
            f"get_prop(vendor_init, {CAMERA})",
            ASSERTION,
        ])
        self.assertNotIn("set_prop(", disabled)
        self.assertEqual(self.record["source_effect"]["assertion_retained"], ASSERTION)
        self.assertEqual(self.record["source_effect"]["removed_occurrences_when_false"], 1)
        self.assertEqual(self.record["source_effect"]["grants_added"], 0)

    def test_default_branch_is_the_exact_original_macro_call(self):
        self.assertTrue(SELECTION.endswith(f"`system_vendor_config_prop({CAMERA})')\n"))
        capability = self.record["capability"]
        self.assertEqual(capability["allowed_explicit_values"], ["true", "false"])
        for key in ("undefined_preserves_upstream_grants", "true_preserves_upstream_grants",
                    "default_and_true_macro_expansions_byte_identical", "invalid_value_causes_fatal_m4_error"):
            self.assertIs(capability[key], True)
        self.assertIs(capability["api_or_device_name_inference_used"], False)

    def test_other_properties_and_global_macros_stay_unchanged(self):
        suffix = self.before.split(b"\n# NFC\n", 1)[1]
        self.assertEqual(self.after.split(b"\n# NFC\n", 1)[1], suffix)
        self.assertIn(b"system_vendor_config_prop(vendor_persist_nfc_prop)", suffix)
        self.assertIn(b"system_vendor_config_prop(usb_uvc_config_prop)", suffix)
        self.assertIn(b"system_restricted_prop(xtra_control_prop)", suffix)
        macro = self.record["macro_source"]
        self.assertEqual(macro["sha256"], "b749c90e4ad0b7873eaa03192309846fddc7a33b06284e1925ad849c2d5111cd")
        self.assertEqual(macro["size_bytes"], 42239)
        self.assertIn("  neverallow { domain -init -vendor_init } $1:property_service set;\n",
                      macro["system_vendor_config_prop_definition"])
        for key in ("type_attributes_changed", "property_contexts_changed", "shared_macros_changed",
                    "assertions_removed_or_weakened", "factory_inputs_changed", "nfc_usb_xtra_declarations_changed"):
            self.assertIs(self.record["source_effect"][key], False)

    def test_factory_assertion_still_prohibits_all_noncore_writers(self):
        factory = self.record["factory_assertion"]
        self.assertEqual((factory["sha256"], factory["size_bytes"]),
                         ("4258020807f41ab856992db8f44027bf8a3fd80cbc40f506129595aa5fa17dd8", 396303))
        self.assertEqual(factory["expression"],
                         "(neverallow base_typeattr_232_202504 vendor_persist_camera_prop_202504 (property_service (set)))")
        self.assertEqual(factory["source_attribute_definition"],
                         "(typeattributeset base_typeattr_232_202504 (and (domain) (not (coredomain))))")
        self.assertEqual(factory["versioned_property_scope_attribute"], "system_restricted_property_type")
        self.assertIs(factory["original_bytes_preserved"], True)

    def test_existing_two_type_owners_and_singleton_mapping_are_retained(self):
        owners = self.record["duplicate_type_ownership"]
        self.assertEqual(owners["property_type"], CAMERA)
        self.assertEqual(owners["declarations_per_runtime"], 1)
        self.assertEqual(owners["role"], "object_r")
        self.assertEqual(owners["mapping_attribute"], CAMERA + "_202504")
        self.assertEqual(owners["mapping_members"], [CAMERA])
        self.assertEqual({owners["factory_runtime"], owners["source_runtime"]},
                         {"/vendor/etc/selinux/plat_pub_versioned.cil", "/system_ext/etc/selinux/system_ext_sepolicy.cil"})
        self.assertIs(owners["existing_contract_ownership_unchanged"], True)

    def test_duplicate_make_definition_guard_is_an_explicit_adoption_requirement(self):
        capability = self.record["capability"]
        self.assertEqual(capability["symbol"], SYMBOL)
        self.assertEqual(capability["board_variable"], "BOARD_SEPOLICY_M4DEFS")
        self.assertEqual(capability["proposed_definition"], SYMBOL + "=false")
        self.assertIs(capability["duplicate_definitions_rejected_by_admission"], True)
        self.assertIs(capability["duplicate_definition_guard_is_separate_from_m4_value_validation"], True)
        requirements = " ".join(self.record["adoption_requirements"])
        for text in ("exactly one", "missing, duplicate, conflicting, injected or overridden",
                     "without sorting or deduplicating", "same false definition", "no default profile selects false"):
            self.assertIn(text, requirements)
        self.assertIs(self.record["limits"]["duplicate_make_definition_guard_tested_by_this_fixture"], False)

    def test_recorded_real_host_m4_cases_are_not_offline_or_android_compile_passes(self):
        proof = self.record["host_validation"]
        self.assertEqual(proof["valid_cases"], len(proof["variants"]) * len(proof["recovery_values"]) *
                         len(proof["source_capability_cases"]))
        self.assertEqual(proof["valid_cases"], 24)
        self.assertEqual(proof["invalid_cases"], len(set(proof["invalid_values"])))
        self.assertEqual((proof["invalid_cases"], proof["invalid_exit_code"], proof["invalid_policy_statements_emitted"]),
                         (11, 1, 0))
        self.assertEqual((proof["original_type_declarations"], proof["original_neverallows"],
                          proof["original_allow_statements"], proof["disabled_allow_statements"]), (4, 4, 12, 11))
        for key in ("default_and_true_expansions_byte_identical", "only_one_camera_set_statement_removed_when_false",
                    "all_other_ordered_statements_unchanged", "all_valid_stderr_empty",
                    "complete_captured_platform_macros_used", "original_source_and_factory_inputs_preserved"):
            self.assertIs(proof[key], True)
        self.assertIs(proof["m4_tool"]["is_android_build_m4"], False)
        self.assertEqual((proof["patch_copies_reproduced"], proof["patch_max_fuzz"]), (2, 0))

    def test_permission_assertion_capability_and_patch_drift_are_rejected(self):
        substitutions = ((b"+get_prop(vendor_init,", b"+set_prop(vendor_init,"),
                         (b"+neverallow {", b"+allow {"),
                         (b"-init -vendor_init", b"-init -vendor_init -shell"),
                         (b"m4exit(1)", b"m4exit(0)"),
                         (b"`false', `system_public_prop", b"`true', `system_public_prop"),
                         (b"100644\n", b"100755\n"),
                         (b"@@ -1,11 +1,19 @@", b"@@ -2,11 +2,19 @@"),
                         (b"--- a/common/public/property.te", b"--- a/common/private/property.te"))
        for old, new in substitutions:
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                source_pair(self.patch.replace(old, new, 1))
        for raw in (self.patch[:-1], self.patch + self.patch, self.patch.replace(b"\n", b"\r\n")):
            with self.assertRaises(ValueError):
                source_pair(raw)

    def test_actual_failure_is_preserved_and_no_runtime_or_image_claim_is_made(self):
        self.assertEqual(self.record["selected_profile"],
                         {"device": "nezha", "hardware_region": "CN", "branch": "bka", "release": "bp4a",
                          "board_api": "202504", "build_variant": "user", "capability_value": "false"})
        failure = self.record["native_failure_receipt"]
        self.assertEqual(failure["failed_target"], "nezha_factory_precompiled_sepolicy")
        self.assertIs(failure["original_failed_result_preserved"], True)
        for row in (failure, self.record["source_capture_receipt"], self.record["host_validation"]["receipt"]):
            path = PurePosixPath(row["path"])
            self.assertFalse(path.is_absolute())
            self.assertNotIn("..", path.parts)
            self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")
        self.assertEqual(self.record["status"], "tested_optional_source_patch_not_installed")
        self.assertTrue(all(value is False for value in self.record["limits"].values()))
        requirements = " ".join(self.record["adoption_requirements"])
        for text in ("strict combined policy compilation", "contexts and Treble", "unfiltered normal-policy permissive",
                     "no assertion or check may be disabled", "camera property labels, assignments and readers"):
            self.assertIn(text, requirements)


if __name__ == "__main__":
    unittest.main()
