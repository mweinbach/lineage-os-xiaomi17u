"""Offline full-source contract tests; no APK, Soong, process or device needed."""

import hashlib
import json
from pathlib import Path
import re
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from scripts import partition_build_props
from scripts import twrp_patch_state


ROOT = Path(__file__).resolve().parents[1]
PATCH = "patches/evolution/0022-systemui-clocks-optional-window-libraries.patch"
CONTRACT = "patches/evolution/systemui-clocks-optional-window-libraries.json"
RELATIVE = "themes/SystemUIClocks/Android.bp"
PATCH_SHA = "ebae241f30864a722daba678822c03b05014c6e01c15dfac71d2032733b5faf0"
BEFORE_SHA = "361ee46333c9d7898b0a032b10944a3fa8ad32932174af4513a530e3c8eb1574"
AFTER_SHA = "60a4e55feec15932b0bb732742e0528dcbefcdc224363247afabcfff7b3fb58e"
BEFORE_BLOB = "f8a352ab85bbcbc25f03036cbf3e82a29575d4f7"
AFTER_BLOB = "26a114a748f81af9cfe851a5ca3bae6d486b6373"
NAMES = tuple("SystemUIClocks-" + name for name in (
    "BigNum", "Calligraphy", "Flex", "Growth", "Inflate", "NumOverlap", "Metro", "Weather"))
FLEX = "SystemUIClocks-Flex"
LIBRARIES = ["androidx.window.extensions", "androidx.window.sidecar"]
ADDITION = (b'\toptional_uses_libs: [\r\n'
            b'\t\t"androidx.window.extensions",\r\n'
            b'\t\t"androidx.window.sidecar",\r\n'
            b'\t],\r\n')
HEADER = (
    f"diff --git a/{RELATIVE} b/{RELATIVE}\n"
    f"index {BEFORE_BLOB}..{AFTER_BLOB} 100755\n"
    f"--- a/{RELATIVE}\n+++ b/{RELATIVE}\n"
    "@@ -1,95 +1,123 @@\n"
).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def source_pair(raw):
    """Recover only the pinned complete CRLF files from the full-file hunk."""
    if type(raw) is not bytes or not raw.startswith(HEADER) or b"\0" in raw:
        raise ValueError("unexpected file, index, mode or hunk header")
    lines = raw[len(HEADER):].splitlines(keepends=True)
    if not lines or any(line[:1] not in (b" ", b"+", b"-") or not line.endswith(b"\r\n")
                        or b"\r" in line[:-2] or b"\n" in line[:-2] for line in lines):
        raise ValueError("complete CRLF source lines required")
    before = b"".join(line[1:] for line in lines if line.startswith((b" ", b"-")))
    after = b"".join(line[1:] for line in lines if line.startswith((b" ", b"+")))
    for data, count, size, digest, blob in (
            (before, 95, 2046, BEFORE_SHA, BEFORE_BLOB),
            (after, 123, 2690, AFTER_SHA, AFTER_BLOB)):
        if (len(data.splitlines()), len(data), sha(data), git_blob(data)) != (count, size, digest, blob):
            raise ValueError("complete source identity differs")
    return before, after


def module_blocks(raw):
    """Parse only this file's eight literal import blocks, not general Blueprint."""
    matches = list(re.finditer(rb'android_app_import \{\r\n\tname: "([^"]+)",\r\n.*?^\}\r\n', raw, re.M | re.S))
    if tuple(match[1].decode() for match in matches) != NAMES or b"\r\n".join(match[0] for match in matches) != raw:
        raise ValueError("unexpected module closure, order or interstitial text")
    return {match[1].decode(): match[0] for match in matches}


def optional_libraries(block):
    matches = list(re.finditer(rb'\toptional_uses_libs: \[\r\n((?:\t\t"[^"\r\n]+",\r\n)+)\t\],\r\n', block))
    if len(matches) != block.count(b"optional_uses_libs:") or len(matches) > 1:
        raise ValueError("ambiguous optional library list")
    return re.findall(r'"([^"]+)"', matches[0][1].decode()) if matches else []


def reversed_patch(raw):
    source_pair(raw)
    header = HEADER.replace(f"{BEFORE_BLOB}..{AFTER_BLOB}".encode(),
                            f"{AFTER_BLOB}..{BEFORE_BLOB}".encode())
    header = header.replace(b"@@ -1,95 +1,123 @@", b"@@ -1,123 +1,95 @@")
    return header + b"".join((b"-" if line.startswith(b"+") else b"+") + line[1:]
                             if line.startswith((b"+", b"-")) else line
                             for line in raw[len(HEADER):].splitlines(keepends=True))


def replay(source, raw, reverse=False):
    before, after = source_pair(raw)
    expected_before, expected_after = (after, before) if reverse else (before, after)
    if source != expected_before:
        raise ValueError("complete source preimage differs")
    result = partition_build_props._apply_patch(source, reversed_patch(raw) if reverse else raw)
    if result != expected_after:
        raise ValueError("complete source postimage differs")
    return result


class SystemUIClocksOptionalWindowLibrariesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / CONTRACT).read_bytes())
        cls.patch = (ROOT / PATCH).read_bytes()
        cls.before, cls.after = source_pair(cls.patch)
        cls.old = module_blocks(cls.before)
        cls.new = module_blocks(cls.after)

    def setUp(self):
        for target in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(target, side_effect=AssertionError("offline test: " + target)))

    def test_complete_crlf_source_pair_and_executable_mode_are_pinned(self):
        r = self.record
        self.assertEqual((r["schema_version"], r["id"], r["project"], r["branch"]),
                         (1, "systemui-clocks-optional-window-libraries-v1", "vendor/extras", "bka"))
        self.assertEqual((r["patch"], r["patch_sha256"], r["patch_size_bytes"]), (PATCH, PATCH_SHA, 3087))
        self.assertEqual((sha(self.patch), len(self.patch)), (PATCH_SHA, 3087))
        self.assertEqual(len(r["files"]), 1)
        row = r["files"][0]
        self.assertEqual((row["path"], row["mode"], row["line_endings"]), (RELATIVE, "100755", "CRLF"))
        for phase, raw, lines in (("before", self.before, 95), ("after", self.after, 123)):
            self.assertEqual((row[phase + "_sha256"], row[phase + "_size_bytes"], row[phase + "_git_blob"]),
                             (sha(raw), len(raw), git_blob(raw)))
            self.assertEqual(raw.count(b"\r\n"), lines)
            self.assertNotIn(b"\n", raw.replace(b"\r\n", b""))
        twrp_patch_state.chain_patch_index(self.patch, RELATIVE, row, mode=0o755)

    def test_pinned_manifest_revision_and_origin_match(self):
        r = self.record
        pin = r["source_snapshot"]
        raw = (ROOT / pin["path"]).read_bytes()
        self.assertEqual((sha(raw), len(raw)), (pin["sha256"], pin["size_bytes"]))
        manifest = ET.fromstring(raw)
        projects = [p for p in manifest.findall("project") if p.get("path") == r["project"]]
        self.assertEqual(len(projects), 1)
        p = projects[0]
        self.assertEqual(p.get("revision"), "c401d732c0475b7010c205a2e9bfb0fd6888d0be")
        self.assertEqual(p.get("revision"), r["base_commit"])
        self.assertEqual((p.get("remote"), p.get("upstream")), (r["remote_name"], "refs/heads/bka"))
        remotes = [x for x in manifest.findall("remote") if x.get("name") == r["remote_name"]]
        self.assertEqual(len(remotes), 1)
        self.assertEqual(remotes[0].get("fetch").rstrip("/") + "/" + p.get("name"), r["origin"])

    def test_only_seven_literal_lists_change_with_flex_fully_unchanged(self):
        self.assertEqual(tuple(self.old), NAMES)
        self.assertEqual(tuple(self.new), NAMES)
        self.assertEqual(self.old[FLEX], self.new[FLEX])
        self.assertEqual(optional_libraries(self.new[FLEX]), [])
        for name in NAMES:
            with self.subTest(module=name):
                self.assertEqual(optional_libraries(self.old[name]), [])
                self.assertEqual(optional_libraries(self.new[name]), [] if name == FLEX else LIBRARIES)
                expected = self.old[name] if name == FLEX else self.old[name].replace(
                    b'\tcertificate: "platform",\r\n', b'\tcertificate: "platform",\r\n' + ADDITION, 1)
                self.assertEqual(self.new[name], expected)
        self.assertEqual(self.after.count(ADDITION), 7)
        self.assertEqual(self.after.replace(ADDITION, b""), self.before)
        self.assertNotIn(b"defaults:", self.after)
        self.assertNotIn(b"\tuses_libs:", self.after)

    def test_all_original_apks_signing_and_dexpreopt_settings_remain(self):
        for name in NAMES:
            with self.subTest(module=name):
                for row in (f'\tapk: "{name}/{name}.apk",\r\n'.encode(), b'\towner: "google",\r\n',
                            b'\tcertificate: "platform",\r\n', b'\tdex_preopt: {\r\n\t\tenabled: false,\r\n\t},\r\n',
                            b'\tprivileged: true,\r\n', b'\tsystem_ext_specific: true,\r\n'):
                    self.assertEqual((self.old[name].count(row), self.new[name].count(row)), (1, 1))
        body = self.patch[len(HEADER):].splitlines(keepends=True)
        self.assertFalse(any(line.startswith(b"-") for line in body))
        self.assertEqual(b"".join(line[1:] for line in body if line.startswith(b"+")), ADDITION * 7)

    def test_exact_forward_reverse_and_duplicate_guards(self):
        self.assertEqual(replay(self.before, self.patch), self.after)
        self.assertEqual(replay(self.after, self.patch, reverse=True), self.before)
        self.assertEqual(partition_build_props._apply_patch(self.before, self.patch), self.after)
        self.assertEqual(partition_build_props._apply_patch(self.after, reversed_patch(self.patch)), self.before)
        for raw, reverse in ((self.after, False), (self.before, True)):
            with self.subTest(reverse=reverse), self.assertRaises(ValueError):
                replay(raw, self.patch, reverse=reverse)

    def test_source_drift_line_endings_and_extra_bytes_are_rejected(self):
        for raw in (self.before.replace(b"\r\n", b"\n"), self.before.replace(b'"platform"', b'"testkey"', 1),
                    self.before.replace(b"enabled: false", b"enabled: true", 1), self.before[:-1],
                    b"// shifted\r\n" + self.before, self.before + b"// tail\r\n"):
            with self.subTest(identity=sha(raw)), self.assertRaises(ValueError):
                replay(raw, self.patch)

    def test_wrong_path_mode_blob_and_hunk_counts_are_rejected(self):
        for old, new in ((RELATIVE.encode(), b"themes/Android.bp"), (b"100755\n", b"100644\n"),
                         (BEFORE_BLOB.encode(), b"0" * 40), (AFTER_BLOB.encode(), b"0" * 40),
                         (b"@@ -1,95 +1,123 @@", b"@@ -2,95 +2,123 @@"),
                         (b"@@ -1,95 +1,123 @@", b"@@ -1,94 +1,123 @@"),
                         (b"@@ -1,95 +1,123 @@", b"@@ -1,95 +1,124 @@")):
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                source_pair(self.patch.replace(old, new, 1))

    def test_partial_duplicate_normalized_or_broadened_patch_is_rejected(self):
        wrong_flex = self.patch.replace(b' \tname: "SystemUIClocks-Flex",\r\n',
                                       b' \tname: "SystemUIClocks-Flex",\r\n' + b"".join(b"+" + row for row in ADDITION.splitlines(keepends=True)))
        for raw in (self.patch[:-1], self.patch + self.patch, self.patch.replace(b"\r\n", b"\n"),
                    self.patch.replace(b"\n", b"\r\n"), self.patch + b" trailer\r\n", wrong_flex):
            with self.subTest(identity=sha(raw)), self.assertRaises(ValueError):
                source_pair(raw)

    def test_all_eight_actual_apk_bindings_and_original_results_are_distinct(self):
        rows = self.record["module_records"]
        self.assertEqual(tuple(row["module"] for row in rows), NAMES)
        self.assertEqual(sum(row["original_apk"]["size_bytes"] for row in rows), 18703915)
        self.assertEqual(len({row["original_apk"]["sha256"] for row in rows}), 8)
        for row in rows:
            name = row["module"]
            with self.subTest(module=name):
                self.assertEqual(row["original_apk"]["source_path"], f"vendor/extras/themes/SystemUIClocks/{name}/{name}.apk")
                self.assertRegex(row["original_apk"]["sha256"], r"^[a-f0-9]{64}$")
                self.assertEqual(row["original_apk"]["mode"], "0644")
                self.assertEqual(row["native_exit_code"], 0 if name == FLEX else 255)
                self.assertEqual(row["native_status"], "passed" if name == FLEX else "manifest_mismatch")
                self.assertEqual(row["manifest_optional_libraries"], optional_libraries(self.new[name]))
                self.assertEqual(row["required_uses_libraries_after"], [])
                self.assertEqual(row["optional_uses_libraries_after"], optional_libraries(self.new[name]))
                self.assertIs(row["source_changed"], name != FLEX)
                self.assertIs(row["ordinary_status_producer_verified"], False)

    def test_audit_and_host_fixtures_do_not_claim_native_adoption_or_package(self):
        r = self.record
        self.assertEqual(r["status"], "tested_source_patch_not_installed")
        audit = r["original_native_audit"]
        self.assertEqual((audit["exit_code"], audit["passed"], audit["manifest_mismatches"]), (1, 2, 7))
        self.assertEqual(audit["unchanged_passed_modules"], ["bcr", FLEX])
        self.assertIs(audit["original_failed_result_preserved"], True)
        self.assertIs(audit["ordinary_status_output_verified"], False)
        self.assertTrue(all(value is False for value in r["preparation_limits"].values()))
        for field in ("original_apks_changed", "Flex_module_changed", "signing_changed", "dexpreopt_settings_changed",
                      "enforcement_changed", "shared_defaults_added", "required_library_settings_changed",
                      "normal_android_selinux_changed", "page_size_changed", "recovery_changed"):
            self.assertIs(r["source_effect"][field], False)
        requirements = " ".join(r["adoption_requirements"])
        for phrase in ("all eight", "Flex", "CRLF", "100755", "actual union", "no relaxation", "fresh",
                       "target-files", "4 KiB", "working76"):
            self.assertIn(phrase, requirements)


if __name__ == "__main__":
    unittest.main()
