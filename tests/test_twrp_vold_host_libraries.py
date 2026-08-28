"""Offline contract for libkeystoreinfo's Bionic system library scope.

The complete patch reconstructs both source files without a checkout or network.
Target assertions record the reviewed Soong semantics; they do not run Soong,
compile a host/recovery variant, enable FBE, or establish working decryption.
"""

import hashlib
import json
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET

from test_twrp_patches import hunks, SOURCE_SNAPSHOT_SHA256


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0025-vold-bionic-system-libraries"
PROJECT = "system/vold"
REVISION = "4c83041ec61f9b482085685f1e6aed5a62f103aa"
REPOSITORY = "https://github.com/TWRP-Test/android_system_vold"
SOONG_REVISION = "91bdc79cffb29d35b2d46a33204c061c3e7ed4f7"
OLD_SERIES_SHA256 = "a109dcd496134874ba3165bea817d1ce056062a33bf48131f75dfd4957b033de"
OLD_TWENTY_FOUR = "292c3b569261f0c06e92a53619e7fa89cf9da1ebeb155bc317ce0ed57cf09b59"
OLD_SERIALIZED_RECORDS = "edf252dca5e31991b279deaaad742ba4f6c52b70117bf6f8a7cc4f366d341f4b"
OLD_METADATA = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
ENTRY_SHA256 = "cfe2eecdda8475d7f27bce536f1cd59413aa27f0e377e36c5efc7d0e4ce94d47"
PATCH_SHA256 = "39669d2658f4f7b079acb4ba367cd70ed9747d53757b63ac1555f460eb60473a"
FILE = {
    "path": "Android.bp", "mode": "100644",
    "before_sha256": "bb073d5ee838770abbf2f6a4af96012b5580d77bfc552c4d7995ef935725bcb2",
    "after_sha256": "ab54aef2e2179b038947299a8ff22a0fdaeb992c5f6492e47c979c32d742a4b8",
    "before_git_blob": "c06743bf3ea3ce163c3f4dac7a46c78b6ec93def",
    "after_git_blob": "62a10ec5d86663aa5f879adf3860113092af2d27",
    "before_size_bytes": 8544, "after_size_bytes": 8594,
}
OLD_LIBRARIES = (
    '    system_shared_libs: [\n'
    '        "libc", \n'
    '        "libdl",\n'
    '        ],\n'
)
OPEN_SCOPE = '    target: {\n        bionic: {\n'
CLOSE_SCOPE = '        },\n    },\n'
NEW_LIBRARIES = OPEN_SCOPE + OLD_LIBRARIES + CLOSE_SCOPE
ADDITIONS = (OPEN_SCOPE + CLOSE_SCOPE).splitlines(keepends=True)
EOF_MARKER = "\\ No newline at end of file\n"
HEADER = ("diff --git a/Android.bp b/Android.bp\n"
          f"index {FILE['before_git_blob']}..{FILE['after_git_blob']} 100644\n"
          "--- a/Android.bp\n+++ b/Android.bp\n@@ -1,391 +1,395 @@\n")
MODULE_NAMES = [
    "vold_default_flags", "vold_default_libs", "libvold_binder", "libvold_headers",
    "android.system.vold-service.xml", "libvold", "vold", "vdc", "secdiscard",
    "vold_prepare_subdirs", "vold_aidl", "libkeystoreinfo", "fscryptpolicyget",
    "soong-vold_defaults", "vold_defaults", "vold_flags", "vold_flags_c_lib",
]


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def serialized_records(text):
    """Locate patch objects without normalizing their serialized bytes."""
    decoder = json.JSONDecoder()
    position = text.index("[", text.index('"patches":')) + 1
    records = []
    while True:
        while text[position].isspace() or text[position] == ",":
            position += 1
        if text[position] == "]":
            return records
        value, end = decoder.raw_decode(text, position)
        if not isinstance(value, dict):
            raise ValueError("Expected a patch record")
        records.append((position, end, text[position:end]))
        position = end


def module(text):
    matches = re.findall(r'^cc_library \{\n    name: "libkeystoreinfo",.*?^\}',
                         text, re.M | re.S)
    if len(matches) != 1:
        raise ValueError("Expected exactly the original libkeystoreinfo module")
    return matches[0]


def validate_patch(raw):
    """Validate exact structure and source identities, not just payload SHA256."""
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected complete LF-terminated patch bytes")
    text = raw.decode("utf-8")
    parsed = list(hunks(text))
    if (not text.startswith(HEADER) or text.count(EOF_MARKER) != 1
            or not text.endswith(" }\n" + EOF_MARKER)
            or len(parsed) != 1 or parsed[0][:4] != (1, 391, 1, 395)):
        raise ValueError("Unreviewed path, blobs, mode, complete hunk or EOF marker")
    body = parsed[0][4]
    if len(body) != 395 or any(line[:1] not in (" ", "+") for line in body):
        raise ValueError("Only context and the four scope additions are allowed")
    if [line[1:] for line in body if line.startswith("+")] != ADDITIONS:
        raise ValueError("Only the exact target.bionic wrapper is allowed")
    before = "".join(line[1:] for line in body if line.startswith(" "))
    after = "".join(line[1:] for line in body)
    if (before.count(OLD_LIBRARIES) != 1
            or after != before.replace(OLD_LIBRARIES, NEW_LIBRARIES, 1)
            or OLD_LIBRARIES not in module(before)
            or NEW_LIBRARIES not in module(after)):
        raise ValueError("The original list must be scoped only inside libkeystoreinfo")
    for stage, data in [("before", before.encode()), ("after", after.encode())]:
        if (digest(data) != FILE[stage + "_sha256"]
                or len(data) != FILE[stage + "_size_bytes"] or data.endswith(b"\n")):
            raise ValueError("Complete source bytes or original EOF changed")
    return before, after


class VoldHostLibraryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series_text = (ROOT / "patches/twrp/series.json").read_text()
        cls.series = json.loads(cls.series_text)
        cls.rows = cls.series["patches"]
        cls.row = cls.rows[24]
        cls.patch = (ROOT / "patches/twrp" / (PATCH_ID + ".patch")).read_bytes()

    def test_previous_twenty_four_objects_and_serialized_bytes_are_unchanged(self):
        self.assertGreaterEqual(len(self.rows), 25)
        self.assertEqual(canonical(self.rows[:24]), OLD_TWENTY_FOUR)
        records = serialized_records(self.series_text)
        self.assertEqual(digest("\n".join(record[2] for record in records[:24]).encode()),
                         OLD_SERIALIZED_RECORDS)
        # Remove all append-only records to recover the complete original JSON,
        # including metadata and whitespace outside the patches array.
        previous = self.series_text[:records[23][1]] + self.series_text[records[-1][1]:]
        self.assertEqual(digest(previous.encode()), OLD_SERIES_SHA256)

    def test_non_patch_metadata_and_existing_payloads_are_unchanged(self):
        self.assertEqual(canonical({k: v for k, v in self.series.items() if k != "patches"}),
                         OLD_METADATA)
        for row in self.rows[:24]:
            with self.subTest(patch=row["id"]):
                path = ROOT / row["patch"]
                self.assertFalse(path.is_symlink())
                self.assertEqual(digest(path.read_bytes()), row["patch_sha256"])

    def test_exact_record_and_fresh_file_do_not_create_another_chain(self):
        self.assertEqual(canonical(self.row), ENTRY_SHA256)
        self.assertEqual(self.row["id"], PATCH_ID)
        self.assertEqual(len(self.row["files"]), 1)
        self.assertEqual({key: self.row["files"][0][key] for key in FILE}, FILE)
        self.assertNotIn("predecessor_patch_id", self.row["files"][0])
        self.assertNotIn((PROJECT, FILE["path"]), {(r["project"], f["path"])
                         for r in self.rows[:24] for f in r["files"]})
        chains = [(r["id"], f["path"], f["predecessor_patch_id"])
                  for r in self.rows[:25] for f in r["files"] if "predecessor_patch_id" in f]
        self.assertEqual(chains, [("0024-recovery-usb-only-adb", "daemon/main.cpp",
                                  "0004-require-recovery-adb-auth")])

    def test_frozen_vold_and_soong_source_owners(self):
        raw = (ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml").read_bytes()
        self.assertEqual(digest(raw), SOURCE_SNAPSHOT_SHA256)
        for project, revision in [(PROJECT, REVISION), ("build/soong", SOONG_REVISION)]:
            owners = [p for p in ET.fromstring(raw).iter("project")
                      if p.get("path", p.get("name")) == project]
            self.assertEqual(len(owners), 1)
            self.assertEqual(owners[0].get("revision"), revision)
        self.assertEqual((self.row["project"], self.row["base_commit"], self.row["repository"]),
                         (PROJECT, REVISION, REPOSITORY))
        self.assertEqual(self.row["source_snapshot_sha256"], SOURCE_SNAPSHOT_SHA256)
        self.assertEqual(self.row["files"][0]["source_url"],
                         REPOSITORY + "/blob/" + REVISION + "/Android.bp")

    def test_payload_reconstructs_complete_files_and_full_git_blobs(self):
        self.assertEqual(len(self.patch), 9205)
        self.assertEqual(digest(self.patch), PATCH_SHA256)
        self.assertEqual(self.row["patch_sha256"], PATCH_SHA256)
        before, after = validate_patch(self.patch)
        for stage, text in [("before", before), ("after", after)]:
            raw = text.encode()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual(blob, FILE[stage + "_git_blob"])

    def test_only_four_braces_are_added_and_original_whitespace_survives(self):
        before, after = validate_patch(self.patch)
        self.assertEqual(after.replace(NEW_LIBRARIES, OLD_LIBRARIES, 1), before)
        self.assertEqual(len(after.encode()) - len(before.encode()), 50)
        self.assertEqual((len(before.splitlines()), len(after.splitlines())), (391, 395))
        for text in (before, after):
            self.assertFalse(text.endswith("\n"))
            self.assertEqual(text.count('        "libc", \n'), 1)
            self.assertEqual(text.count(OLD_LIBRARIES), 1)

    def test_other_modules_package_license_and_metadata_are_byte_identical(self):
        before, after = validate_patch(self.patch)
        self.assertEqual(before.replace(module(before), "", 1),
                         after.replace(module(after), "", 1))
        for text in (before, after):
            names = re.findall(r'^ {2,4}name: "([^"]+)"', text, re.M)
            self.assertEqual(names, MODULE_NAMES)
            self.assertEqual(len(names), len(set(names)))
            self.assertTrue(text.startswith(
                'package {\n    default_applicable_licenses: ["Android-Apache-2.0"],\n}\n'))

    def test_original_module_fields_and_identities_survive(self):
        before, after = validate_patch(self.patch)
        metadata = self.row["files"][0]["system_library_modules"]
        self.assertEqual(len(metadata), 1)
        m = metadata[0]
        self.assertEqual((m["type"], m["name"], m["constructor_line"]),
                         ("cc_library", "libkeystoreinfo", 318))
        for stage, text in [("before", before), ("after", after)]:
            body = module(text)
            self.assertEqual(digest(body.encode()), m[stage + "_module_sha256"])
            self.assertIn("host_supported: true,", body)
            self.assertIn("recovery_available: true,", body)
            self.assertIn('"KeystoreInfo.cpp"', body)
            self.assertIn('shared_libs: [\n        "libsqlite"\n    ],', body)
            self.assertNotIn("defaults:", body)
            self.assertNotIn("enabled:", body)

    def test_bionic_pair_is_scoped_and_other_host_properties_stay_unset(self):
        _, after = validate_patch(self.patch)
        body = module(after)
        self.assertEqual(body.count("system_shared_libs:"), 1)
        self.assertEqual(body.count("target:"), 1)
        self.assertEqual(body.count("bionic:"), 1)
        self.assertIn(NEW_LIBRARIES, body)
        contract = self.row["target_contract"]
        self.assertEqual(contract["selector"], "target.bionic")
        self.assertEqual(contract["explicit_library_targets"], ["android", "linux_bionic"])
        self.assertEqual(contract["explicit_system_shared_libs"], ["libc", "libdl"])
        self.assertEqual(contract["inherited_default_targets"],
                         ["linux_glibc", "linux_musl", "darwin", "windows"])
        self.assertIs(contract["non_bionic_property_unset"], True)
        self.assertIs(contract["non_bionic_property_empty_list"], False)
        for key in ("host_supported_unchanged", "recovery_available_unchanged",
                    "static_and_shared_variants_preserved"):
            self.assertIs(contract[key], True)
        for target in contract["inherited_default_targets"]:
            self.assertNotIn(target + ":", body)
        self.assertNotIn('"libm"', body)

    def test_source_evidence_is_bound_without_loading_ignored_captures(self):
        evidence = self.row["source_evidence"]
        self.assertEqual((evidence["soong_project"], evidence["soong_revision"]),
                         ("build/soong", SOONG_REVISION))
        self.assertEqual([f["path"] for f in evidence["files"]],
                         ["android/arch.go", "cc/linker.go", "cc/library.go"])
        for file in evidence["files"]:
            self.assertRegex(file["sha256"], r"^[0-9a-f]{64}$")
            self.assertIn(SOONG_REVISION, file["source_url"])
        aosp = evidence["aosp_vold_comparison"]
        self.assertEqual(aosp["revision"], "11760521a2e86389c56620ec50e780e8b17e40ca")
        self.assertIs(aosp["libkeystoreinfo_present"], False)
        self.assertEqual(aosp["tag"], "android-16.0.0_r1")

    def test_no_crypto_enablement_or_validation_waiver_is_introduced(self):
        board = (ROOT / "recovery/twrp/device/xiaomi/nezha/BoardConfig.mk").read_text()
        for flag in ("TW_INCLUDE_CRYPTO", "TW_INCLUDE_CRYPTO_FBE"):
            self.assertIn(flag + " := false\n", board)
        changed = "".join(ADDITIONS)
        for forbidden in ("ALLOW_MISSING_DEPENDENCIES", "BUILD_BROKEN", "enabled:",
                          "host_supported:", "check_elf_files", "permissive", "Decrypt.cpp",
                          "apex_available", "visibility", "system_shared_libs: []"):
            self.assertNotIn(forbidden, changed)
        limits = " ".join(self.row["limits"])
        self.assertIn("do not execute Soong", limits)
        self.assertIn("No crypto source edit, FBE enablement", limits)
        self.assertIn("phone operation", limits)

    def test_unreviewed_source_scope_and_payload_mutations_are_rejected(self):
        raw = self.patch
        changes = {
            "path": (b"--- a/Android.bp", b"--- a/other.bp"),
            "mode": (b" 100644\n", b" 100755\n"),
            "short_blob": (FILE["before_git_blob"].encode(), FILE["before_git_blob"][:12].encode()),
            "host_disabled": (b"host_supported: true", b"host_supported: false"),
            "recovery_disabled": (b"recovery_available: true", b"recovery_available: false"),
            "android_only": (b"+        bionic:", b"+        android:"),
            "glibc_selector": (b"+        bionic:", b"+        linux_glibc:"),
            "empty_global": (b"+    target: {\n", b"+    system_shared_libs: [],\n+    target: {\n"),
            "provider_waiver": (b"+        bionic: {\n", b"+        bionic: {\n+            enabled: false,\n"),
            "libm_added": (b'         "libdl",\n', b'         "libdl",\n+        "libm",\n'),
            "wrong_order": (b'         "libc", \n         "libdl",\n',
                            b'         "libdl",\n         "libc", \n'),
            "missing_libc": (b'         "libc", \n', b""),
            "whitespace_cleanup": (b'         "libc", \n', b'         "libc",\n'),
            "other_source": (b'"KeystoreInfo.cpp"', b'"Other.cpp"'),
            "other_module": (b'name: "libvold"', b'name: "other_libvold"'),
            "license": (b'"Android-Apache-2.0"', b'"other-license"'),
            "hunk_count": (b"-1,391", b"-1,390"),
            "no_eof_marker": (EOF_MARKER.encode(), b""),
            "crlf": (b"\n", b"\r\n"),
            "trailer": (raw, raw + b"GIT binary patch\n"),
            "second_file": (raw, raw + raw),
        }
        for name, (old, new) in changes.items():
            with self.subTest(mutation=name):
                self.assertIn(old, raw)
                changed = raw.replace(old, new, 1)
                self.assertNotEqual(changed, raw)
                with self.assertRaises(ValueError):
                    validate_patch(changed)

    def test_eof_reader_accepts_context_and_separate_old_new_markers(self):
        cases = [
            ("@@ -1 +1 @@\n value\n" + EOF_MARKER, [" value"]),
            ("@@ -1 +1 @@\n-old\n" + EOF_MARKER + "+new\n" + EOF_MARKER,
             ["-old", "+new"]),
            ("@@ -1 +1 @@\n-old\n" + EOF_MARKER + "+new\n", ["-old", "+new\n"]),
            ("@@ -1 +1 @@\n-old\n+new\n" + EOF_MARKER, ["-old\n", "+new"]),
        ]
        for text, expected in cases:
            with self.subTest(text=text):
                self.assertEqual(list(hunks(text)), [(1, 1, 1, 1, expected)])

    def test_eof_reader_rejects_orphan_duplicate_malformed_and_continued_sides(self):
        hunk = "@@ -1 +1 @@\n"
        invalid = [
            EOF_MARKER,
            EOF_MARKER + hunk + " value\n",
            hunk + EOF_MARKER,
            hunk + " value\n" + EOF_MARKER * 2,
            hunk + " value\n\\ No newline at end of file",
            hunk + " value\n\\ No newline at EOF\n",
            hunk + " value\n" + EOF_MARKER + " more\n",
            hunk + "-old\n" + EOF_MARKER + "-more\n+new\n",
            hunk + "+new\n" + EOF_MARKER + "+more\n-old\n",
            hunk + "-old\n" + EOF_MARKER + "+new\n" + EOF_MARKER + " more\n",
            hunk + " value\n" + EOF_MARKER + "@@ -2 +2 @@\n more\n",
        ]
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(ValueError):
                list(hunks(text))

    def test_reader_preserves_all_marker_free_hunks_in_the_previous_queue(self):
        pattern = r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n"
        for row in self.rows[:24]:
            text = (ROOT / row["patch"]).read_text()
            for section in text.split("diff --git ")[1:]:
                with self.subTest(patch=row["id"], file=section.splitlines()[0]):
                    self.assertNotIn(EOF_MARKER, section)
                    matches = list(re.finditer(pattern, section, re.M))
                    expected = []
                    for index, match in enumerate(matches):
                        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
                        expected.append((int(match[1]), int(match[2] or 1), int(match[3]),
                                         int(match[4] or 1), section[match.end():end].splitlines(keepends=True)))
                    self.assertEqual(list(hunks(section)), expected)


if __name__ == "__main__":
    unittest.main()
