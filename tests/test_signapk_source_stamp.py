"""Offline patch-contract checks, not Java or APK signature verification.

The public partial hunks are replayed against inert surrounding text using the
existing exact-patch reader. Full captured-source replay is separate evidence;
these tests need no ignored reports, Android checkout, signer, key or phone.
"""

import hashlib
import json
from pathlib import Path
import re
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from scripts import target_files_source_composition as composition
from scripts import twrp_patch_state as patch_state


ROOT = Path(__file__).resolve().parents[1]
PATCH = "patches/evolution/0020-signapk-remove-stale-source-stamp.patch"
CONTRACT = "patches/evolution/signapk-source-stamp.json"
RELATIVE = "tools/signapk/src/com/android/signapk/SignApk.java"
SOURCE = "build/make/" + RELATIVE
MAKE_RELATIVE = "core/app_prebuilt_internal.mk"
PATCH_SHA = "007e8cf5f714b48baa0a58694cd1e7846c62b127acc3ae59dff1ca647add3343"
MAKE_ADDITION = (
    "# Re-sign non-presigned APKs when the signing tool changes.\n"
    "ifneq ($(LOCAL_CERTIFICATE),PRESIGNED)\n"
    "$(built_module): $(SIGNAPK_JAR)\n"
    "endif\n\n"
).encode()
OLD_CALL = (
    "                    copyFiles(inputJar, null, apkSigner, outputJar,\n"
    "                              outputJarCounter, timestamp, alignment);\n"
).encode()
NEW_CALL = (
    "                    // The discarded signing block leaves its source-stamp digest obsolete.\n"
    "                    copyFiles(inputJar,\n"
    "                            Pattern.compile(Pattern.quote(\n"
    "                                    ApkUtils.SOURCE_STAMP_CERTIFICATE_HASH_ZIP_ENTRY_NAME)),\n"
    "                            apkSigner, outputJar, outputJarCounter, timestamp, alignment);\n"
).encode()


def patch_sections(raw):
    """Require exactly the two reviewed files, in their recorded order."""
    pieces = raw.split(b"diff --git ")
    paths = (MAKE_RELATIVE, RELATIVE)
    if pieces[0] or len(pieces) != 3:
        raise ValueError("expected exactly two source files")
    result = {}
    for path, body in zip(paths, pieces[1:]):
        if not body.startswith(f"a/{path} b/{path}\n".encode()):
            raise ValueError("unexpected file or order")
        result[path] = b"diff --git " + body
    return result


def reverse_patch(raw):
    """Invert the one reviewed text hunk for an in-memory reverse rehearsal."""
    lines = raw.splitlines(keepends=True)
    output = []
    in_hunk = False
    for line in lines:
        if line.startswith(b"index "):
            match = re.fullmatch(rb"index ([0-9a-f]{40})\.\.([0-9a-f]{40}) 100644\n", line)
            if match is None:
                raise ValueError("unexpected patch index")
            line = b"index " + match[2] + b".." + match[1] + b" 100644\n"
        elif line.startswith(b"@@ "):
            match = re.fullmatch(rb"@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", line)
            if match is None or in_hunk:
                raise ValueError("expected one explicit hunk")
            line = (b"@@ -" + match[3] + b"," + match[4]
                    + b" +" + match[1] + b"," + match[2] + b" @@\n")
            in_hunk = True
        elif in_hunk and line.startswith((b"+", b"-")):
            line = (b"-" if line.startswith(b"+") else b"+") + line[1:]
        output.append(line)
    if not in_hunk:
        raise ValueError("missing hunk")
    return b"".join(output)


def fixture_source(raw):
    """Exact hunk context surrounded by inert text, not a compilable Java file."""
    headers = list(re.finditer(rb"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", raw, re.M))
    if len(headers) != 1:
        raise ValueError("expected one hunk")
    match = headers[0]
    start = int(match[1])
    body = raw[match.end():].splitlines(keepends=True)
    before = b"".join(line[1:] for line in body if line.startswith((b" ", b"-")))
    prefix = b"".join(f"// untouched fixture line {number}\n".encode()
                       for number in range(1, start))
    return prefix + before + b"// untouched fixture tail\n"


class SignApkSourceStampPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / CONTRACT).read_bytes())
        cls.bundle = (ROOT / PATCH).read_bytes()
        cls.sections = patch_sections(cls.bundle)
        cls.patch = cls.sections[RELATIVE]
        cls.row = cls.record["files"][1]
        cls.fixture = fixture_source(cls.patch)

    def setUp(self):
        for target in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(target, side_effect=AssertionError("offline test: " + target)))

    def test_contract_binds_both_exact_source_transitions(self):
        r = self.record
        self.assertEqual((r["schema_version"], r["project"], r["branch"]), (1, "build/make", "bka"))
        self.assertEqual(r["base_commit"], "a438ca40c6ed779042f806142b1165ba1360a7b2")
        self.assertEqual((r["patch"], r["patch_sha256"], r["patch_size_bytes"]),
                         (PATCH, PATCH_SHA, 1900))
        self.assertEqual((hashlib.sha256(self.bundle).hexdigest(), len(self.bundle)), (PATCH_SHA, 1900))
        self.assertEqual(r["files"], [{
            "path": MAKE_RELATIVE, "mode": "100644",
            "before_sha256": "24567acfe9cf31468d3824b95523aa0957eb0c7b79153caab7ef5d9a11c14bbe",
            "before_size_bytes": 10510,
            "before_git_blob": "ca3814c33fa53089b551f2f79ac73de75c3ab0fe",
            "after_sha256": "1694fe9e005f4c94b639b16cefb905fb1fc8b960659d80b575f129d5b4f126da",
            "after_size_bytes": 10648,
            "after_git_blob": "a6e5a2ffd6ed05558a1fa96bf1c2678b3dac48df",
        }, {
            "path": RELATIVE, "mode": "100644",
            "before_sha256": "6aa7fa0c1a5aae0f0595e519023c6ee2f70d75ce5bc8aac8e9d9a87961eb2bd2",
            "before_size_bytes": 60936,
            "before_git_blob": "654e19675d7c836f4734dd986293ac7506096207",
            "after_sha256": "a1ef3eaac711108c867c1834c475a84a4425d0fb29d07364b3fd20ed71f260f9",
            "after_size_bytes": 61172,
            "after_git_blob": "196daba1088e143f9a6f0a32915bded7b5a93c56",
        }])
        for row in r["files"]:
            patch_state.chain_patch_index(self.sections[row["path"]], row["path"], row, mode=0o644)

    def test_make_and_apksig_revisions_match_the_pinned_manifest(self):
        manifest = ET.fromstring((ROOT / self.record["source_snapshot"]["path"]).read_bytes())
        for path, commit in (("build/make", self.record["base_commit"]),
                             ("tools/apksig", self.record["pinned_semantics"]["apksig_revision"])):
            rows = [row for row in manifest.findall("project") if row.get("path", row.get("name")) == path]
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0].get("revision"), commit)

    def test_only_the_apk_copy_argument_and_comment_change(self):
        body = self.patch.split(b"@@ -1280,8 +1280,11 @@\n", 1)[1]
        removed = b"".join(line[1:] for line in body.splitlines(keepends=True) if line.startswith(b"-"))
        added = b"".join(line[1:] for line in body.splitlines(keepends=True) if line.startswith(b"+"))
        self.assertEqual((removed, added), (OLD_CALL, NEW_CALL))
        self.assertEqual(self.patch.count(b"diff --git "), 1)
        self.assertEqual(self.patch.count(b"@@ "), 1)
        self.assertEqual(len(added) - len(removed), self.row["after_size_bytes"] - self.row["before_size_bytes"])
        effect = self.record["source_effect"]
        self.assertEqual(effect["excluded_zip_entry"], "stamp-cert-sha256")
        self.assertEqual(effect["filename_match"], "Pattern.quote literal with Matcher.matches whole-name matching")

    def test_forward_and_reverse_preserve_every_surrounding_fixture_byte(self):
        for relative, patch in self.sections.items():
            before = fixture_source(patch)
            after = composition._apply_exact_patch(before, patch, "build/make/" + relative)
            with self.subTest(relative=relative):
                if relative == RELATIVE:
                    self.assertEqual(after, before.replace(OLD_CALL, NEW_CALL, 1))
                else:
                    self.assertEqual(after.replace(MAKE_ADDITION, b"", 1), before)
                self.assertEqual(composition._apply_exact_patch(after, reverse_patch(patch),
                                                                "build/make/" + relative), before)
                self.assertEqual(reverse_patch(reverse_patch(patch)), patch)

    def test_normal_signer_dependency_precedes_the_unchanged_common_recipe(self):
        patch = self.sections[MAKE_RELATIVE]
        body = patch.split(b"@@ -214,6 +214,11 @@\n", 1)[1]
        self.assertFalse(any(line.startswith(b"-") for line in body.splitlines()))
        added = b"".join(line[1:] for line in body.splitlines(keepends=True) if line.startswith(b"+"))
        self.assertEqual(added, MAKE_ADDITION)
        before = fixture_source(patch)
        after = composition._apply_exact_patch(before, patch, "build/make/" + MAKE_RELATIVE)
        common = (b"$(built_module) : $(my_prebuilt_src_file) | $(ZIPALIGN) $(ZIP2ZIP) "
                  b"$(SIGNAPK_JAR) $(SIGNAPK_JNI_LIBRARY_PATH)\n"
                  b"\t$(transform-prebuilt-to-target)\n"
                  b"\t$(uncompress-prebuilt-embedded-jni-libs)\n")
        self.assertIn(MAKE_ADDITION + common, after)
        self.assertEqual(after.count(common), 1)

    def test_file_closure_rejects_duplicates_missing_files_and_wrong_order(self):
        for raw in (self.patch, self.bundle + self.patch,
                    self.patch + self.sections[MAKE_RELATIVE],
                    self.sections[MAKE_RELATIVE] + self.sections[MAKE_RELATIVE]):
            with self.subTest(raw=hashlib.sha256(raw).hexdigest()), self.assertRaises(ValueError):
                patch_sections(raw)

    def test_duplicate_application_and_reverse_of_original_are_rejected(self):
        after = composition._apply_exact_patch(self.fixture, self.patch, SOURCE)
        for source, patch in ((after, self.patch), (self.fixture, reverse_patch(self.patch))):
            with self.subTest(source=hashlib.sha256(source).hexdigest()), self.assertRaises(ValueError):
                composition._apply_exact_patch(source, patch, SOURCE)

    def test_changed_context_and_shifted_source_are_rejected(self):
        for source in (self.fixture.replace(b"outputJar.setLevel(9);", b"outputJar.setLevel(8);", 1),
                       b"// new line\n" + self.fixture):
            with self.subTest(source=hashlib.sha256(source).hexdigest()), self.assertRaises(ValueError):
                composition._apply_exact_patch(source, self.patch, SOURCE)

    def test_wrong_hunk_counts_positions_or_duplicate_hunk_are_rejected(self):
        marker = b"@@ -1280,8 +1280,11 @@"
        changes = [self.patch.replace(marker, changed, 1) for changed in (
            b"@@ -1280,9 +1280,11 @@", b"@@ -1280,8 +1280,12 @@",
            b"@@ -1281,8 +1281,11 @@", b"@@ -1280,8 +1281,11 @@",
        )]
        changes.append(self.patch + self.patch[self.patch.index(b"@@ "):])
        for patch in changes:
            with self.subTest(patch=hashlib.sha256(patch).hexdigest()), self.assertRaises(ValueError):
                composition._apply_exact_patch(self.fixture, patch, SOURCE)

    def test_wrong_file_extra_file_and_truncated_patch_are_rejected(self):
        for patch in (self.patch.replace(RELATIVE.encode(), b"tools/signapk/Android.bp"),
                      self.patch + self.patch, self.patch[:-1], self.patch + b"unexpected trailer\n"):
            with self.subTest(patch=hashlib.sha256(patch).hexdigest()), self.assertRaises(ValueError):
                composition._apply_exact_patch(self.fixture, patch, SOURCE)

    def test_changed_git_blob_or_mode_is_rejected(self):
        for old, new in ((b"100644\n", b"100755\n"),
                         (self.row["before_git_blob"].encode(), b"0" * 40),
                         (self.row["after_git_blob"].encode(), b"0" * 40)):
            with self.subTest(new=new), self.assertRaises(ValueError):
                patch_state.chain_patch_index(self.patch.replace(old, new, 1), RELATIVE, self.row, mode=0o644)

    def test_preparation_keeps_failed_verification_and_native_gates_explicit(self):
        failure = self.record["observed_failure"]
        self.assertEqual((failure["native_build_exit_code"], failure["installed_signature_exit_code"],
                          failure["wrapper_exit_code"]), (0, 1, 1))
        self.assertEqual(failure["installed_signature_stderr"], "WARNING: No SourceStamp signature\n")
        self.assertEqual(failure["warnings_as_errors_retained"], "-Werr")
        self.assertEqual(self.record["status"], "tested_source_patch_not_installed")
        self.assertTrue(all(value is False for value in self.record["preparation_limits"].values()))
        for field in ("whole_file_ota_signing_changed", "ordinary_presigned_recipe_changed",
                      "signing_algorithms_or_keys_changed", "original_apk_bytes_changed",
                      "verifier_flags_changed", "source_lock_changed"):
            self.assertIs(self.record["source_effect"][field], False)


if __name__ == "__main__":
    unittest.main()
