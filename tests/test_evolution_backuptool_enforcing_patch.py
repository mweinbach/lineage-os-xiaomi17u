"""Offline source contract; no private inputs, M4, subprocesses or phone.

Finite projections model only the pinned recovery_only selector. Actual host
M4 expansion is separately recorded and is not an Android policy compilation.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest


ROOT = Path(__file__).resolve().parents[1]
BEFORE_SHA = "cff90d8a5c7c7dcd3332cf74c1200ebbd0e7feeb8a43dba4bb41f64fe5775ba2"
AFTER_SHA = "3a1cb8110f792bc8669e8604c86208f9b8e948486ef2617a64a2a1ef67827e54"
BEFORE_BLOB = "b670fb07fe36d08edf645583ea15332e2a626dff"
AFTER_BLOB = "22ff6d81a4ceb0c8c4d450263d22c8500dfde7f6"
MACRO = "define(`recovery_only', ifelse(target_recovery, `true', $1, ))\n"
HEADER = (
    "diff --git a/common/private/backuptool.te b/common/private/backuptool.te\n"
    f"index {BEFORE_BLOB}..{AFTER_BLOB} 100644\n"
    "--- a/common/private/backuptool.te\n+++ b/common/private/backuptool.te\n"
    "@@ -1,9 +1,11 @@\n"
)
STATEMENT = b"permissive backuptool;\n"
WRAPPED = b"recovery_only(`\npermissive backuptool;\n')\n"


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def source_pair(raw):
    """Reconstruct the two exact complete files from the one full-file hunk."""
    if type(raw) is not bytes or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Complete LF patch bytes required")
    text = raw.decode("utf-8")
    if not text.startswith(HEADER):
        raise ValueError("Unreviewed source path, mode, blobs or hunk bounds")
    lines = text[len(HEADER):].splitlines(keepends=True)
    if any(line[:1] not in (" ", "+", "-") for line in lines):
        raise ValueError("Unexpected patch syntax")
    before = "".join(line[1:] for line in lines if line.startswith((" ", "-"))).encode()
    after = "".join(line[1:] for line in lines if line.startswith((" ", "+"))).encode()
    if (len(before.splitlines()), len(before), sha(before)) != (9, 152, BEFORE_SHA):
        raise ValueError("Original complete source differs")
    if (len(after.splitlines()), len(after), sha(after)) != (11, 171, AFTER_SHA):
        raise ValueError("Revised complete source differs")
    if before.count(STATEMENT) != 1 or after != before.replace(STATEMENT, WRAPPED):
        raise ValueError("Only the original permissive statement may be guarded")
    return before, after


def projected_tokens(source, *, target_recovery, variant):
    """Finite model of these two source bodies, not an M4 interpreter."""
    if type(source) is not bytes or sha(source) not in (BEFORE_SHA, AFTER_SHA):
        raise ValueError("Use only the two reviewed source bodies")
    if target_recovery is not None and type(target_recovery) is not str:
        raise ValueError("Recovery selector must be a literal string or absent")
    if variant not in ("user", "userdebug", "eng"):
        raise ValueError("Unreviewed build variant")
    if sha(source) == AFTER_SHA:
        source = source.replace(WRAPPED, STATEMENT if target_recovery == "true" else b"")
    return tuple(source.split())


class EvolutionBackuptoolEnforcingPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "patches/evolution/backuptool-enforcing.json").read_bytes())
        cls.patch = (ROOT / cls.record["patch"]).read_bytes()
        cls.before, cls.after = source_pair(cls.patch)

    def test_exact_project_revision_patch_and_complete_source_identities(self):
        r = self.record
        self.assertEqual(r["project"], "device/lineage/sepolicy")
        self.assertEqual(r["branch"], "bka")
        self.assertEqual(r["base_commit"], "37c13c9b74344c17eddd6067541e9fcba116a34e")
        self.assertEqual(r["patch"], "patches/evolution/0015-backuptool-permissive-only-recovery.patch")
        self.assertEqual((sha(self.patch), len(self.patch)), (r["patch_sha256"], r["patch_size_bytes"]))
        self.assertEqual(r["patch_sha256"], "70ac3adb7166f32b52c70eb16962f7b4ca6ad3c47630ecf4672dc47384a32a50")
        self.assertEqual(len(r["files"]), 1)
        item = r["files"][0]
        self.assertEqual((item["path"], item["mode"]), ("common/private/backuptool.te", "100644"))
        for label, body in (("before", self.before), ("after", self.after)):
            self.assertEqual((item[label + "_sha256"], item[label + "_size_bytes"]), (sha(body), len(body)))
            blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
            self.assertEqual(item[label + "_git_blob"], blob)

    def test_only_two_wrapper_lines_are_added_and_no_source_bytes_removed(self):
        lines = self.patch.decode()[len(HEADER):].splitlines()
        self.assertEqual([line[1:] for line in lines if line.startswith("+")], ["recovery_only(`", "')"])
        self.assertEqual([line for line in lines if line.startswith("-")], [])
        self.assertEqual(self.after.replace(WRAPPED, STATEMENT), self.before)
        self.assertEqual(self.patch.count(b"diff --git "), 1)

    def test_type_and_complete_neverallow_block_remain_outside_the_guard(self):
        self.assertEqual(self.after.split(WRAPPED), self.before.split(STATEMENT))
        self.assertEqual(self.after.split(WRAPPED)[0], b"type backuptool, domain, coredomain;\n\n")
        self.assertEqual(self.after.split(WRAPPED)[1],
                         b"\nneverallow {\n    domain\n    -recovery\n    -update_engine\n} backuptool:process transition;\n")

    def test_all_normal_variants_project_no_permissive_statement(self):
        expected = tuple(self.before.replace(STATEMENT, b"").split())
        for variant in ("user", "userdebug", "eng"):
            for selector in ("false", None):
                with self.subTest(variant=variant, selector=selector):
                    old = projected_tokens(self.before, target_recovery=selector, variant=variant)
                    new = projected_tokens(self.after, target_recovery=selector, variant=variant)
                    self.assertIn(b"permissive", old)
                    self.assertEqual(new, expected)
                    self.assertNotIn(b"permissive", new)

    def test_recovery_preserves_every_original_statement_in_all_three_variants(self):
        for variant in ("user", "userdebug", "eng"):
            with self.subTest(variant=variant):
                self.assertEqual(projected_tokens(self.after, target_recovery="true", variant=variant),
                                 projected_tokens(self.before, target_recovery="true", variant=variant))

    def test_only_literal_true_selects_the_existing_recovery_exception(self):
        for selector in ("", "TRUE", "1", " true", "true ", "other"):
            with self.subTest(selector=selector):
                tokens = projected_tokens(self.after, target_recovery=selector, variant="user")
                self.assertEqual(tokens, tuple(self.before.replace(STATEMENT, b"").split()))

    def test_projection_refuses_unknown_source_and_ambiguous_selector_types(self):
        for source in (self.after + STATEMENT, self.after.replace(b"neverallow", b"allow"), self.after.decode()):
            with self.assertRaises(ValueError):
                projected_tokens(source, target_recovery="false", variant="user")
        for selector in (True, False, 1, [], {}):
            with self.assertRaises(ValueError):
                projected_tokens(self.after, target_recovery=selector, variant="user")
        with self.assertRaises(ValueError):
            projected_tokens(self.after, target_recovery="true", variant="unknown")

    def test_patch_drift_and_permission_changes_are_rejected(self):
        substitutions = ((b"+recovery_only(`", b"+userdebug_or_eng(`"),
                         (b" neverallow {", b" allow {"),
                         (b"     -update_engine", b"     -init"),
                         (b" type backuptool, domain, coredomain;", b" type backuptool, domain;"),
                         (b"100644\n", b"100755\n"),
                         (b"@@ -1,9 +1,11 @@", b"@@ -2,9 +2,11 @@"),
                         (b"--- a/common/private/backuptool.te", b"--- a/common/private/recovery.te"))
        for old, new in substitutions:
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                source_pair(self.patch.replace(old, new, 1))
        for raw in (self.patch[:-1], self.patch + self.patch, self.patch.replace(b"\n", b"\r\n")):
            with self.assertRaises(ValueError):
                source_pair(raw)

    def test_existing_macro_is_pinned_without_redefinition_or_new_capabilities(self):
        macro = self.record["macro_source"]
        self.assertEqual((macro["project"], macro["path"]), ("system/sepolicy", "public/te_macros"))
        self.assertEqual(macro["commit"], "e631d35d7bd7b7993e84f3d49eeb34ec87dd1a27")
        self.assertEqual(macro["sha256"], "b749c90e4ad0b7873eaa03192309846fddc7a33b06284e1925ad849c2d5111cd")
        self.assertEqual((macro["line"], macro["definition"]), (544, MACRO))
        self.assertNotIn(b"define(", self.after)
        for key, value in self.record["source_effect"].items():
            if key.endswith("_changed") or key.endswith("_exemptions_added"):
                self.assertIs(value, False)

    def test_recorded_host_evidence_is_separate_from_offline_and_android_builds(self):
        proof = self.record["host_validation"]
        self.assertEqual((proof["patch_copies_reproduced"], proof["patch_max_fuzz"]), (2, 0))
        count = len(proof["source_versions"]) * len(proof["variants"]) * len(proof["recovery_selectors"])
        count += len(proof["additional_after_user_nontrue_selectors"])
        self.assertEqual((count, proof["m4_cases"]), (24, 24))
        self.assertEqual(proof["m4_tool"]["version"], "GNU M4 1.4.6")
        self.assertIs(proof["m4_tool"]["is_android_build_m4"], False)
        self.assertIs(proof["only_recovery_only_definition_expanded"], True)
        for key in ("all_expansions_exact", "all_m4_stderr_empty", "type_and_neverallow_tokens_unchanged",
                    "original_inputs_preserved"):
            self.assertIs(proof[key], True)
        for row in (proof["receipt"], self.record["source_capture_receipt"]):
            self.assertFalse(PurePosixPath(row["path"]).is_absolute())
            self.assertNotIn("..", PurePosixPath(row["path"]).parts)
            self.assertRegex(row["sha256"], r"^[a-f0-9]{64}$")
        independent = self.record["independent_full_macro_host_validation"]
        self.assertEqual((independent["variant_selector_pairs"], independent["host_m4_commands"]), (9, 27))
        self.assertEqual(len(independent["inputs_per_pair"]), 3)
        self.assertIs(independent["same_pinned_macro_source_and_host_tool"], True)
        self.assertIs(independent["android_build_executed"], False)
        self.assertIs(independent["full_policy_compiler_executed"], False)

    def test_native_adoption_requires_assertions_unfiltered_analysis_and_ota_validation(self):
        requirements = " ".join(self.record["adoption_requirements"])
        for text in ("all neverallow assertions retained", "unfiltered sepolicy-analyze permissive",
                     "require empty output", "context and Treble", "backup, addon.d, restore and OTA",
                     "normal update_engine transition to backuptool remains present"):
            self.assertIn(text, requirements)

    def test_patch_does_not_admit_source_images_boot_or_functional_backup(self):
        self.assertEqual(self.record["status"], "tested_source_patch_not_installed")
        self.assertTrue(self.record["limits"])
        self.assertTrue(all(value is False for value in self.record["limits"].values()))


if __name__ == "__main__":
    unittest.main()
