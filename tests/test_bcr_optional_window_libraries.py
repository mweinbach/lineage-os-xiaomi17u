"""Offline full-source patch checks, not APK, Android graph or device tests.

The tiny complete Makefile is recoverable from the public patch. Keep its CRLF
bytes intact; no ignored reports, source checkout, external tools or phone are
needed. Separate host checker fixtures use synthetic XML, not the actual APK.
"""

import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from scripts import partition_build_props
from scripts import twrp_patch_state


ROOT = Path(__file__).resolve().parents[1]
PATCH = "patches/evolution/0021-bcr-optional-window-libraries.patch"
CONTRACT = "patches/evolution/bcr-optional-window-libraries.json"
RELATIVE = "bcr/prebuilts/product/priv-app/com.chiller3.bcr/Android.mk"
PATCH_SHA = "3e21e7033877d47f6dbaec1c4c501fb970fa1d4a15cd5471ccaea0dd10091856"
BEFORE_SHA = "b1cd6bb0cfe700cab6501d47f3b5f68f7cc945366d3e0c3da1412693d22af254"
AFTER_SHA = "30d9b220f1c5103ad2326351cdafedde96fed4ebbac6e48ed9701a65d025b296"
BEFORE_BLOB = "ff4bc1b27793fe5d7d28123124ca2d8bd9a009a6"
AFTER_BLOB = "5fe450509ec5281310c5009e0020bc0aab1c07fc"
LIBRARIES = ["androidx.window.extensions", "androidx.window.sidecar"]
ADDITION = ("LOCAL_OPTIONAL_USES_LIBRARIES := " + " ".join(LIBRARIES) + "\r\n").encode()
HEADER = (
    f"diff --git a/{RELATIVE} b/{RELATIVE}\n"
    f"index {BEFORE_BLOB}..{AFTER_BLOB} 100644\n"
    f"--- a/{RELATIVE}\n+++ b/{RELATIVE}\n"
    "@@ -1,11 +1,12 @@\n"
).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def source_pair(raw):
    """Admit only the complete reviewed file pair, with LF headers/CRLF hunks."""
    if type(raw) is not bytes or not raw.startswith(HEADER) or b"\0" in raw:
        raise ValueError("unexpected path, mode, index or hunk header")
    lines = raw[len(HEADER):].splitlines(keepends=True)
    if not lines or any(line[:1] not in (b" ", b"+", b"-")
                        or not line.endswith(b"\r\n")
                        or b"\r" in line[:-2] or b"\n" in line[:-2] for line in lines):
        raise ValueError("complete CRLF source lines required")
    before = b"".join(line[1:] for line in lines if line.startswith((b" ", b"-")))
    after = b"".join(line[1:] for line in lines if line.startswith((b" ", b"+")))
    for data, count, size, digest, blob in (
            (before, 11, 310, BEFORE_SHA, BEFORE_BLOB),
            (after, 12, 395, AFTER_SHA, AFTER_BLOB)):
        if (len(data.splitlines()), len(data), sha(data), git_blob(data)) != (count, size, digest, blob):
            raise ValueError("complete source identity differs")
    return before, after


def reversed_patch(raw):
    """Reverse the already authenticated single full-file hunk, without Git."""
    source_pair(raw)
    header = HEADER.replace(f"{BEFORE_BLOB}..{AFTER_BLOB}".encode(),
                            f"{AFTER_BLOB}..{BEFORE_BLOB}".encode())
    header = header.replace(b"@@ -1,11 +1,12 @@", b"@@ -1,12 +1,11 @@")
    lines = raw[len(HEADER):].splitlines(keepends=True)
    return header + b"".join((b"-" if line.startswith(b"+") else b"+") + line[1:]
                             if line.startswith((b"+", b"-")) else line for line in lines)


def replay(source, raw, reverse=False):
    """Full identity guards around the existing pure, exact-hunk replayer."""
    before, after = source_pair(raw)
    expected_before, expected_after = (after, before) if reverse else (before, after)
    if source != expected_before:
        raise ValueError("source is not the complete expected preimage")
    result = partition_build_props._apply_patch(source, reversed_patch(raw) if reverse else raw)
    if result != expected_after:
        raise ValueError("result is not the complete expected postimage")
    return result


class BcrOptionalWindowLibrariesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / CONTRACT).read_bytes())
        cls.patch = (ROOT / PATCH).read_bytes()
        cls.before, cls.after = source_pair(cls.patch)

    def setUp(self):
        for target in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(target, side_effect=AssertionError("offline test: " + target)))

    def test_exact_patch_and_complete_crlf_source_contract(self):
        r = self.record
        self.assertEqual((r["schema_version"], r["id"], r["project"], r["branch"]),
                         (1, "bcr-optional-window-libraries-v1", "vendor/extras", "bka"))
        self.assertEqual((r["patch"], r["patch_sha256"], r["patch_size_bytes"]), (PATCH, PATCH_SHA, 784))
        self.assertEqual((sha(self.patch), len(self.patch)), (PATCH_SHA, 784))
        self.assertEqual(len(r["files"]), 1)
        row = r["files"][0]
        self.assertEqual((row["path"], row["mode"], row["line_endings"]), (RELATIVE, "100644", "CRLF"))
        for phase, data, count in (("before", self.before, 11), ("after", self.after, 12)):
            self.assertEqual((row[phase + "_sha256"], row[phase + "_size_bytes"], row[phase + "_git_blob"]),
                             (sha(data), len(data), git_blob(data)))
            self.assertEqual(data.count(b"\r\n"), count)
            self.assertNotIn(b"\n", data.replace(b"\r\n", b""))
        twrp_patch_state.chain_patch_index(self.patch, RELATIVE, row, mode=0o644)

    def test_project_origin_and_revision_match_the_pinned_manifest(self):
        r = self.record
        snapshot = r["source_snapshot"]
        raw = (ROOT / snapshot["path"]).read_bytes()
        self.assertEqual((sha(raw), len(raw)), (snapshot["sha256"], snapshot["size_bytes"]))
        manifest = ET.fromstring(raw)
        projects = [p for p in manifest.findall("project") if p.get("path") == r["project"]]
        self.assertEqual(len(projects), 1)
        project = projects[0]
        self.assertEqual(project.get("revision"), "c401d732c0475b7010c205a2e9bfb0fd6888d0be")
        self.assertEqual(project.get("revision"), r["base_commit"])
        self.assertEqual((project.get("remote"), project.get("upstream")), (r["remote_name"], "refs/heads/bka"))
        remotes = [p for p in manifest.findall("remote") if p.get("name") == r["remote_name"]]
        self.assertEqual(len(remotes), 1)
        self.assertEqual(remotes[0].get("fetch").rstrip("/") + "/" + project.get("name"), r["origin"])

    def test_only_one_ordered_optional_assignment_is_added(self):
        body = self.patch[len(HEADER):].splitlines(keepends=True)
        self.assertFalse(any(line.startswith(b"-") for line in body))
        self.assertEqual([line[1:] for line in body if line.startswith(b"+")], [ADDITION])
        self.assertEqual(self.after.replace(ADDITION, b"", 1), self.before)
        self.assertEqual(self.after.count(ADDITION), 1)
        self.assertTrue(self.after.endswith(ADDITION + b"include $(BUILD_PREBUILT)\r\n"))
        self.assertNotIn(b"LOCAL_USES_LIBRARIES", self.before + self.after)
        row = self.record["files"][0]
        self.assertEqual((row["required_uses_libraries_before"], row["required_uses_libraries_after"]), ([], []))
        self.assertEqual((row["optional_uses_libraries_before"], row["optional_uses_libraries_after"]), ([], LIBRARIES))
        self.assertEqual(self.record["observed_failure"]["manifest_optional_libraries"], LIBRARIES)

    def test_original_module_signing_placement_and_privileges_are_preserved(self):
        expected = {
            "LOCAL_MODULE": "bcr", "LOCAL_SRC_FILES": "bcr.apk", "LOCAL_PRODUCT_MODULE": "true",
            "LOCAL_MODULE_CLASS": "APPS", "LOCAL_CERTIFICATE": "PRESIGNED",
            "LOCAL_PRIVILEGED_MODULE": "true", "LOCAL_MODULE_SUFFIX": "$(COMMON_ANDROID_PACKAGE_SUFFIX)",
        }
        for variable, value in expected.items():
            line = f"{variable} := {value}\r\n".encode()
            with self.subTest(variable=variable):
                self.assertEqual((self.before.count(line), self.after.count(line)), (1, 1))
        self.assertEqual(self.record["retained_module_settings"], expected)

    def test_exact_forward_and_reverse_preserve_every_original_byte(self):
        self.assertEqual(replay(self.before, self.patch), self.after)
        self.assertEqual(replay(self.after, self.patch, reverse=True), self.before)
        self.assertEqual(partition_build_props._apply_patch(self.before, self.patch), self.after)
        self.assertEqual(partition_build_props._apply_patch(self.after, reversed_patch(self.patch)), self.before)

    def test_duplicate_application_and_reverse_of_original_fail(self):
        for source, reverse in ((self.after, False), (self.before, True)):
            with self.subTest(reverse=reverse), self.assertRaises(ValueError):
                replay(source, self.patch, reverse=reverse)
        with self.assertRaises(ValueError):
            partition_build_props._apply_patch(self.after, self.patch)

    def test_normalized_endings_shifted_context_and_extra_bytes_fail(self):
        changes = (
            self.before.replace(b"\r\n", b"\n"),
            self.before.replace(b"LOCAL_MODULE := bcr", b"LOCAL_MODULE := other", 1),
            b"# shifted\r\n" + self.before,
            self.before + b"# extra\r\n",
            self.before[:-1],
        )
        for source in changes:
            with self.subTest(identity=sha(source)), self.assertRaises(ValueError):
                replay(source, self.patch)

    def test_wrong_file_mode_index_and_hunk_positions_fail(self):
        changes = (
            (RELATIVE.encode(), b"bcr/Android.mk"),
            (b"100644\n", b"100755\n"),
            (BEFORE_BLOB.encode(), b"0" * 40),
            (AFTER_BLOB.encode(), b"0" * 40),
            (b"@@ -1,11 +1,12 @@", b"@@ -2,11 +2,12 @@"),
            (b"@@ -1,11 +1,12 @@", b"@@ -1,12 +1,12 @@"),
            (b"@@ -1,11 +1,12 @@", b"@@ -1,11 +1,13 @@"),
        )
        for old, new in changes:
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                source_pair(self.patch.replace(old, new, 1))

    def test_partial_extra_duplicate_or_normalized_patch_is_rejected(self):
        for raw in (self.patch[:-1], self.patch + self.patch, self.patch + b" trailer\r\n",
                    self.patch.replace(b"\r\n", b"\n"), self.patch.replace(b"\n", b"\r\n"),
                    self.patch + b"+" + ADDITION):
            with self.subTest(identity=sha(raw)), self.assertRaises(ValueError):
                source_pair(raw)

    def test_library_reordering_missing_entries_and_reclassification_fail(self):
        mutations = (
            ADDITION.replace(b"androidx.window.extensions androidx.window.sidecar",
                             b"androidx.window.sidecar androidx.window.extensions"),
            ADDITION.replace(b" androidx.window.sidecar", b""),
            ADDITION.replace(b"LOCAL_OPTIONAL_USES_LIBRARIES", b"LOCAL_USES_LIBRARIES"),
        )
        for addition in mutations:
            with self.subTest(addition=addition), self.assertRaises(ValueError):
                source_pair(self.patch.replace(ADDITION, addition, 1))

    def test_failed_native_package_and_fresh_adoption_requirements_remain_explicit(self):
        r = self.record
        self.assertEqual(r["status"], "tested_source_patch_not_installed")
        failure = r["observed_failure"]
        self.assertEqual((failure["module"], failure["native_build_exit_code"]), ("bcr", 1))
        for key in ("build_required_libraries", "build_optional_libraries", "build_missing_optional_libraries",
                    "manifest_required_libraries", "dexpreopt_config_operands"):
            self.assertEqual(failure[key], [])
        self.assertIs(failure["strict_enforcement_retained"], True)
        self.assertIs(failure["original_result_preserved"], True)
        self.assertTrue(all(value is False for value in r["preparation_limits"].values()))
        for key in ("required_library_settings_changed", "apk_bytes_or_manifests_changed",
                    "signing_settings_changed", "privilege_or_partition_changed", "enforcement_settings_changed",
                    "global_or_other_module_settings_changed", "providers_or_library_registration_added",
                    "source_lock_changed", "normal_android_selinux_changed", "page_size_changed", "recovery_changed"):
            self.assertIs(r["source_effect"][key], False)
        requirements = " ".join(r["adoption_requirements"])
        for phrase in ("full combined intake", "original APK", "CRLF", "fresh", "no relaxation",
                       "class-loader contexts", "target-files", "4 KiB", "working76"):
            self.assertIn(phrase, requirements)
        self.assertFalse(any(token in ADDITION for token in (b"RELAX", b"BROKEN", b"ENFORCE", b"DEX_PREOPT")))


if __name__ == "__main__":
    unittest.main()
