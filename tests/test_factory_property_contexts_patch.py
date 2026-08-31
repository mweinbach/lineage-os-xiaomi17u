"""Offline source/context contract; no private inputs, M4, processes or device."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest


ROOT = Path(__file__).resolve().parents[1]
SYMBOL = "target_nezha_preserve_factory_property_labels"
BEFORE_SHA = "a29095adf4349ac75c516e75ebe60efd2e419c09aaaa6c8bd6409e9208c4b3ff"
AFTER_SHA = "33884485f126d7941542f92f2a09d5f6aec1aba1bff63af52b4d1c721d2769be"
BEFORE_BLOB = "2e97da55bf208d3954f035a18ee2c408dc362c49"
AFTER_BLOB = "5aa968e62bcc5e23a700d50d88b402e96dafa5a2"
SELECTORS = (
    "vendor.camera.aux.packageexcludelist", "vendor.camera.aux.packagelist",
    "vendor.camera.skip_unconfigure.packagelist", "ro.vendor.audio.dolby.dax.support",
    "ro.vendor.audio.dolby.dax.version", "ro.vendor.audio.dolby.surround.enable",
    "vendor.usb.uvc.payload_transfer_size",
)
HEADER = (
    "diff --git a/common/private/property_contexts b/common/private/property_contexts\n"
    f"index {BEFORE_BLOB}..{AFTER_BLOB} 100644\n"
    "--- a/common/private/property_contexts\n+++ b/common/private/property_contexts\n"
    "@@ -1,72 +1,79 @@\n"
)
VALIDATOR = (
    f"ifdef(`{SYMBOL}', `ifelse(defn(`{SYMBOL}'), `true', `',\n"
    f"       defn(`{SYMBOL}'), `false', `',\n"
    f"       `errprint(`{SYMBOL} must be true or false\n"
    "')m4exit(1)')')dnl\n"
).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_pair(raw):
    """Reconstruct only the two pinned complete files from the full-file hunk."""
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
    if (len(before.splitlines()), len(before), sha(before)) != (72, 2870, BEFORE_SHA):
        raise ValueError("Original complete source differs")
    if (len(after.splitlines()), len(after), sha(after)) != (79, 3423, AFTER_SHA):
        raise ValueError("Guarded complete source differs")
    return before, after


def semantic_rows(raw):
    return [line for line in raw.splitlines(keepends=True) if line.strip() and not line.lstrip().startswith(b"#")]


def guarded(rows):
    return f"ifelse(defn(`{SYMBOL}'), `true', `', `".encode() + b"".join(rows) + b"')dnl\n"


class FactoryPropertyContextsPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "patches/evolution/factory-property-contexts.json").read_bytes())
        cls.patch = (ROOT / cls.record["patch"]).read_bytes()
        cls.before, cls.after = source_pair(cls.patch)
        cls.suppressed = [row["raw_line"].encode() for row in cls.record["suppressed_rows"]]
        cls.selected = cls.before
        for row in cls.suppressed:
            cls.selected = cls.selected.replace(row, b"")

    def test_exact_project_patch_and_complete_source_pair(self):
        r = self.record
        self.assertEqual(r["contract_id"], "nezha-preserve-factory-property-contexts-v1")
        self.assertEqual((r["project"], r["branch"]), ("device/lineage/sepolicy", "bka"))
        self.assertEqual(r["base_commit"], "37c13c9b74344c17eddd6067541e9fcba116a34e")
        self.assertEqual(r["patch_sha256"], "1c467b55273f153dd569838ce6f58f89b334c4aa40911bcc99436b48e0c6e819")
        self.assertEqual((sha(self.patch), len(self.patch)), (r["patch_sha256"], r["patch_size_bytes"]))
        self.assertEqual(len(r["files"]), 1)
        item = r["files"][0]
        self.assertEqual((item["path"], item["mode"]), ("common/private/property_contexts", "100644"))
        for label, raw in (("before", self.before), ("after", self.after)):
            self.assertEqual((item[label + "_sha256"], item[label + "_size_bytes"]), (sha(raw), len(raw)))
            self.assertEqual(item[label + "_git_blob"],
                             hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest())

    def test_exact_seven_original_untyped_prefix_rows_are_selected(self):
        rows = self.record["suppressed_rows"]
        self.assertEqual(tuple(row["selector"] for row in rows), SELECTORS)
        self.assertEqual([row["source_line"] for row in rows], [6, 7, 8, 35, 36, 37, 72])
        source_lines = self.before.splitlines(keepends=True)
        for row in rows:
            with self.subTest(selector=row["selector"]):
                raw = row["raw_line"].encode()
                self.assertEqual(source_lines[row["source_line"] - 1], raw)
                self.assertEqual(self.before.count(raw), 1)
                self.assertEqual(raw.decode().split(), [row["selector"], row["context"]])
                self.assertEqual(row["match_kind"], "prefix")
                self.assertEqual(row["explicit_value_type_fields"], [])
        self.assertEqual(sum(map(len, self.suppressed)), 540)

    def test_only_three_selected_blocks_and_one_early_validator_are_added(self):
        expected = VALIDATOR + self.before
        for group in (self.suppressed[:3], self.suppressed[3:6], self.suppressed[6:]):
            expected = expected.replace(b"".join(group), guarded(group))
        self.assertEqual(self.after, expected)
        self.assertEqual(self.after.count(VALIDATOR), 1)
        self.assertEqual(self.after.count(f"ifelse(defn(`{SYMBOL}'), `true', `', `".encode()), 3)
        self.assertEqual(self.patch.count(b"diff --git "), 1)
        self.assertTrue(self.after.startswith(VALIDATOR + b"# ATV\n"))

    def test_special_dolby_and_nonvendor_usb_rows_remain_outside_guards(self):
        retained = self.record["retained_special_rows"]
        self.assertEqual([row.split()[0] for row in retained],
                         ["ro.vendor.dolby.dax.version", "ro.usb.uvc.disable_video_encode_flag"])
        for row in retained:
            raw = row.encode()
            self.assertEqual(self.selected.count(raw), 1)
            self.assertEqual(self.after.count(raw), 1)
            for group in (self.suppressed[:3], self.suppressed[3:6], self.suppressed[6:]):
                self.assertNotIn(raw, guarded(group))

    def test_selected_bytes_and_all_twenty_five_remaining_rows_match(self):
        self.assertEqual((sha(self.selected), len(self.selected)),
                         ("e9482be864095e35b62486f9ac0b5f9e7886cc88ee3038848c900434e289f438", 2330))
        self.assertEqual((len(semantic_rows(self.before)), len(semantic_rows(self.selected))), (32, 25))
        self.assertEqual([row.decode().split() for row in semantic_rows(self.selected)],
                         self.record["selected_base_semantic_rows"])
        self.assertEqual(semantic_rows(self.selected), [row for row in semantic_rows(self.before) if row not in self.suppressed])
        effect = self.record["context_effect"]
        self.assertEqual((effect["original_full_system_ext_rows"], effect["expected_selected_full_system_ext_rows"],
                          effect["unchanged_owned_rows"]), (40, 33, 8))

    def test_literal_capability_values_and_duplicate_guard_requirements_are_explicit(self):
        cap = self.record["capability"]
        self.assertEqual(cap["symbol"], SYMBOL)
        self.assertEqual(cap["allowed_explicit_values"], ["true", "false"])
        self.assertEqual(cap["proposed_definition"], SYMBOL + "=true")
        for key in ("undefined_preserves_upstream_contexts", "false_preserves_upstream_contexts",
                    "true_suppresses_only_selected_rows", "invalid_value_causes_fatal_m4_error",
                    "duplicate_definitions_rejected_by_admission", "duplicate_definition_guard_is_separate_from_m4_value_validation"):
            self.assertIs(cap[key], True)
        self.assertIs(cap["api_or_device_name_inference_used"], False)
        self.assertIn(b"m4exit(1)", VALIDATOR)
        self.assertNotIn(b"m4exit(0)", self.after)
        self.assertNotIn(b"define(`" + SYMBOL.encode(), self.after)

    def test_default_plain_bytes_and_synchronized_provenance_have_distinct_claims(self):
        proof = self.record["host_validation"]
        self.assertIs(proof["default_without_sync_byte_identical"], True)
        self.assertIs(proof["default_with_sync_non_marker_bytes_and_order_identical"], True)
        self.assertIs(proof["raw_synchronized_markers_retained_and_different"], True)
        self.assertIs(self.record["context_effect"]["raw_line_markers_rewritten"], False)
        builder = self.record["native_builder_source"]
        self.assertEqual(builder["m4_flags"], ["--fatal-warnings", "-s"])
        self.assertIs(builder["appends_generated_newline_after_each_source"], True)
        self.assertIs(builder["preserves_property_context_comments_and_line_markers"], True)
        self.assertIs(builder["exact_native_command_captured"], False)
        self.assertIs(proof["exact_native_command_replayed"], False)
        self.assertIs(proof["native_generated_newline_inputs_appended"], False)

    def test_all_three_factory_fallbacks_and_five_preimage_inputs_are_bound(self):
        rows = self.record["suppressed_rows"]
        self.assertEqual([row["factory_fallback"]["selector"] for row in rows],
                         ["vendor.camera."] * 3 + ["ro.vendor.audio."] * 3 + ["vendor.usb."])
        self.assertEqual([row["factory_fallback"]["context"] for row in rows],
                         ["u:object_r:vendor_camera_prop:s0"] * 3 + ["u:object_r:vendor_audio_prop:s0"] * 3 +
                         ["u:object_r:vendor_usb_prop:s0"])
        for row in rows:
            fallback = row["factory_fallback"]
            self.assertTrue(row["selector"].startswith(fallback["selector"]))
            self.assertEqual((fallback["match_kind"], fallback["effective_value_type"]), ("prefix", "string"))
        closure = self.record["preimage_context_closure"]
        self.assertEqual(len(closure["five_complete_context_inputs"]), 5)
        self.assertEqual(len({r["runtime_path"] for r in closure["five_complete_context_inputs"]}), 5)
        self.assertEqual(closure["unexpected_exact_or_deeper_overrides"], 0)
        self.assertIs(closure["entire_seven_prefix_languages_analyzed"], True)
        self.assertIs(closure["selected_native_context_outputs_produced"], False)
        factory = {row["runtime_path"]: row for row in self.record["factory_context_sources"]}
        self.assertEqual(factory["/vendor/etc/selinux/vendor_property_contexts"]["sha256"],
                         "1ea657519b3869186b340700beffa8e7669aec87a7f542a708db7e2e9c0fa692")

    def test_recorded_host_fixtures_are_not_native_or_offline_m4_execution(self):
        proof = self.record["host_validation"]
        count = len(proof["variants"]) * len(proof["recovery_values"]) * len(proof["sync_lines_values"]) * len(proof["source_capability_cases"])
        self.assertEqual((proof["valid_cases"], count), (48, 48))
        self.assertEqual(proof["invalid_cases"], len(proof["sync_lines_values"]) * len(set(proof["invalid_values"])))
        self.assertEqual((proof["invalid_cases"], proof["invalid_exit_code"], proof["invalid_context_rows_emitted"]), (22, 1, 0))
        self.assertEqual((proof["patch_copies_reproduced"], proof["patch_max_fuzz"]), (2, 0))
        self.assertIs(proof["m4_tool"]["is_android_build_m4"], False)
        self.assertIs(proof["all_valid_stderr_empty"], True)

    def test_context_patch_changes_no_declarations_grants_assertions_or_values(self):
        effect = self.record["context_effect"]
        for key in ("type_declarations_changed", "permissions_changed", "assertions_changed",
                    "factory_contexts_changed", "property_values_copied_or_changed"):
            self.assertIs(effect[key], False)
        companion = self.record["related_camera_write_contract"]
        self.assertEqual(companion["path"], "patches/evolution/camera-property-vendor-init-write.json")
        self.assertEqual(companion["sha256"], "70d90fc8431b0edc0c67e3e0d8610a72763924bb985aead45439d9c033194c3d")
        self.assertIs(companion["separate_permission_effect_unchanged"], True)

    def test_wrong_row_guard_path_mode_or_fatal_behavior_is_rejected(self):
        substitutions = ((b"`ro.vendor.audio.dolby.dax.support", b"`ro.vendor.dolby.dax.version"),
                         (b"m4exit(1)", b"m4exit(0)"),
                         (b"`true', `', `vendor.camera", b"`false', `', `vendor.camera"),
                         (b" vendor.camera.aux.packagelist          u:object_r:vendor_persist_camera_prop:s0",
                          b" vendor.camera.aux.packagelist          u:object_r:vendor_camera_prop:s0"),
                         (b"100644\n", b"100755\n"),
                         (b"@@ -1,72 +1,79 @@", b"@@ -2,72 +2,79 @@"),
                         (b"--- a/common/private/property_contexts", b"--- a/common/private/file_contexts"))
        for old, new in substitutions:
            self.assertIn(old, self.patch)
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                source_pair(self.patch.replace(old, new, 1))
        for raw in (self.patch[:-1], self.patch + self.patch, self.patch.replace(b"\n", b"\r\n")):
            with self.assertRaises(ValueError):
                source_pair(raw)

    def test_native_selected_context_and_runtime_gates_remain_required(self):
        requirements = " ".join(self.record["adoption_requirements"])
        for text in ("no default profile selects true", "exactly one", "without sorting or deduplicating",
                     "same true definition", "complete five-context corpus", "entire selected prefix language",
                     "including names extending", "Keep patch 0016", "strict combined policy compilation",
                     "unfiltered normal-policy permissive", "Do not copy factory system property defaults"):
            self.assertIn(text, requirements)
        self.assertEqual(self.record["status"], "tested_optional_source_patch_not_installed")
        self.assertTrue(all(value is False for value in self.record["limits"].values()))
        for row in (self.record["source_capture_receipt"], self.record["host_validation"]["receipt"],
                    self.record["preimage_context_closure"]["receipt"]):
            self.assertFalse(PurePosixPath(row["path"]).is_absolute())
            self.assertNotIn("..", PurePosixPath(row["path"]).parts)
            self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")


if __name__ == "__main__":
    unittest.main()
