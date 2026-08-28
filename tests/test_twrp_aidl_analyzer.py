"""Offline contract for the reviewed analyzer helper availability addition.

This checks pinned source edits, not dependency variants or a successful build.
"""

import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from test_twrp_patches import hunks, SOURCE_SNAPSHOT_SHA256

ROOT = Path(__file__).resolve().parents[1]
PROJECT = "system/tools/aidl"
REVISION = "5bde6fcffe8e3ac6feca449f7bc3502eed5fc0f5"
REPOSITORY = "https://android.googlesource.com/platform/system/tools/aidl"
OLD_SEVENTEEN = "d4bef57c9210ef97783a7919bf1560677bacd09850b57a83b923459dac4113cd"
OLD_METADATA = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
ENTRY_SHA256 = "a31fab90fb5c118c1e92876ecb67f41a1e6c7bad9aeabb75838c7b505a45df51"
FILE = {
    "path": "Android.bp", "mode": "100644",
    "before_sha256": "cafd0a962883328dbddf607bc3b7a287f48accfc5cf520a49d7ac125228ad40a",
    "after_sha256": "0e0c0bcd6120d8f54d04600006c086549b3954e59275820c44829406b8b2b1f2",
    "before_git_blob": "abffd0c2624fb324092945bda43708bb7249f0bd",
    "after_git_blob": "56f9a993fb3a9a000c6f65d9849c35c20852c93d",
    "before_size_bytes": 30149, "after_size_bytes": 30179,
}
ADDITION = "    recovery_available: true,\n"
ANCHOR = 'cc_library_static {\n    name: "aidl-analyzer-main",\n'
BEFORE = '''        "libbinder_tokio_rs",
        "libsimple_parcelable_rust",
        "libtokio",
    ],
    proc_macros: ["libasync_trait"],
    prefer_rlib: true,
    compile_multilib: "both",
    multilib: {
        lib32: {
            suffix: "32",
        },
        lib64: {
            suffix: "64",
        },
    },
    test_suites: ["general-tests"],
}

cc_library_static {
    name: "aidl-analyzer-main",
    host_supported: true,
    vendor_available: true,
    shared_libs: [
        "libbase",
        "libbinder",
    ],
    srcs: [
        "analyzer/analyzerMain.cpp",
        "analyzer/Analyzer.cpp",
    ],
    export_include_dirs: ["analyzer/include"],
}

cc_binary {
    name: "record_binder",
    whole_static_libs: ["aidl-analyzer-main"],
    shared_libs: [
        "libbase",
        "libbinder",
        "libutils",
'''
AFTER = BEFORE.replace(ANCHOR, ANCHOR + ADDITION, 1)
HEADER = ("diff --git a/Android.bp b/Android.bp\n"
          f"index {FILE['before_git_blob']}..{FILE['after_git_blob']} 100644\n"
          "--- a/Android.bp\n+++ b/Android.bp\n@@ -1102,40 +1102,41 @@\n")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def fixture():
    return (HEADER + "".join(("+" if line == ADDITION else " ") + line
                            for line in AFTER.splitlines(keepends=True))).encode()


def validate_patch(raw):
    """Require this exact single hunk; use the existing shared hunk reader."""
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected complete LF-terminated patch bytes")
    text = raw.decode("utf-8")
    parsed = list(hunks(text))
    if not text.startswith(HEADER) or len(parsed) != 1 or parsed[0][:4] != (1102, 40, 1102, 41):
        raise ValueError("Unreviewed path, full Git blobs, mode, or hunk coordinates")
    body = parsed[0][4]
    if len(body) != 41 or any(line[:1] not in (" ", "+") for line in body):
        raise ValueError("No removals, extra records, or malformed hunk bodies are allowed")
    if [line[1:] for line in body if line.startswith("+")] != [ADDITION]:
        raise ValueError("Only the single recovery_available true addition is allowed")
    before = "".join(line[1:] for line in body if line.startswith(" "))
    after = "".join(line[1:] for line in body)
    if before != BEFORE or after != AFTER or body[20] != "+" + ADDITION:
        raise ValueError("Addition moved or the original module/context changed")
    return before, after


class AidlAnalyzerTrackedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        cls.rows = cls.series["patches"]
        cls.row = cls.rows[17]

    def test_previous_seventeen_entries_and_metadata_unchanged(self):
        self.assertGreaterEqual(len(self.rows), 18)
        self.assertEqual(canonical(self.rows[:17]), OLD_SEVENTEEN)
        self.assertEqual(canonical({k: v for k, v in self.series.items() if k != "patches"}), OLD_METADATA)

    def test_previous_payloads_and_exact_new_record(self):
        self.assertEqual(canonical(self.row), ENTRY_SHA256)
        for row in self.rows:
            with self.subTest(patch=row["id"]):
                path = ROOT / row["patch"]
                self.assertFalse(path.is_symlink())
                self.assertEqual(digest(path.read_bytes()), row["patch_sha256"])

    def test_frozen_owner_revision(self):
        raw = (ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml").read_bytes()
        self.assertEqual(digest(raw), SOURCE_SNAPSHOT_SHA256)
        owners = [p for p in ET.fromstring(raw).iter("project") if p.get("path", p.get("name")) == PROJECT]
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0].get("revision"), REVISION)
        self.assertEqual((self.row["project"], self.row["base_commit"], self.row["repository"]),
                         (PROJECT, REVISION, REPOSITORY))

    def test_fresh_file_and_full_source_identities(self):
        self.assertEqual(len(self.row["files"]), 1)
        self.assertEqual({k: self.row["files"][0][k] for k in FILE}, FILE)
        self.assertEqual(FILE["after_size_bytes"] - FILE["before_size_bytes"], len(ADDITION.encode()))
        self.assertNotIn((PROJECT, "Android.bp"), {(r["project"], f["path"])
                         for r in self.rows[:17] for f in r["files"]})

    def test_exact_patch_and_preserved_helper_fields(self):
        raw = (ROOT / self.row["patch"]).read_bytes()
        self.assertEqual(raw, fixture())
        before, after = validate_patch(raw)
        module = self.row["files"][0]["recovery_available_modules"][0]
        # Module metadata ends at the closing brace, excluding its following LF.
        self.assertEqual(digest("".join(before.splitlines(keepends=True)[18:32]).removesuffix("\n").encode()), module["before_module_sha256"])
        self.assertEqual(digest("".join(after.splitlines(keepends=True)[18:33]).removesuffix("\n").encode()), module["after_module_sha256"])
        self.assertEqual(after.replace(ADDITION, "", 1), before)
        self.assertNotIn("recovery_available", before)
        self.assertIn(ANCHOR + ADDITION, after)
        for field in ('host_supported: true', 'vendor_available: true', '"libbase"', '"libbinder"',
                      '"analyzer/analyzerMain.cpp"', '"analyzer/Analyzer.cpp"',
                      'export_include_dirs: ["analyzer/include"]'):
            self.assertIn(field, before)
            self.assertIn(field, after)


class AidlAnalyzerMutationTests(unittest.TestCase):
    def test_reviewed_fixture_accepted(self):
        self.assertEqual(digest(fixture()), "1ecd3993ea99e4dd30bce5d3fa1545df6d047ad92cc91632eebabba401bad24f")
        self.assertEqual(validate_patch(fixture()), (BEFORE, AFTER))

    def test_unreviewed_mutations_rejected_without_checksum_gate(self):
        raw = fixture()
        changes = {
            "wrong_name": (b'name: "aidl-analyzer-main"', b'name: "other"'),
            "wrong_type": (b' cc_library_static {', b' cc_library {'),
            "moved": (("+" + ADDITION + "     host_supported: true,\n").encode(),
                      ("     host_supported: true,\n+" + ADDITION).encode()),
            "duplicate": (("+" + ADDITION).encode(), ("+" + ADDITION + "+" + ADDITION).encode()),
            "removal": (b'     vendor_available: true,', b'-    vendor_available: true,'),
            "false": (b'+    recovery_available: true,', b'+    recovery_available: false,'),
            "source": (b'"analyzer/Analyzer.cpp"', b'"other.cpp"'),
            "dependency": (b'"libbinder"', b'"other"'),
            "exports": (b'export_include_dirs:', b'local_include_dirs:'),
            "path": (b'--- a/Android.bp', b'--- a/other.bp'),
            "mode": (b' 100644\n', b' 100755\n'),
            "abbreviated_blob": (FILE['before_git_blob'].encode(), FILE['before_git_blob'][:12].encode()),
            "wrong_blob": (FILE['after_git_blob'].encode(), b'0' * 40),
            "hunk_count": (b'-1102,40', b'-1102,39'),
            "trailer": (b'         "libutils",\n', b'         "libutils",\nGIT binary patch\n'),
        }
        for name, (old, new) in changes.items():
            with self.subTest(mutation=name):
                self.assertIn(old, raw)
                changed = raw.replace(old, new, 1)
                self.assertNotEqual(changed, raw)
                with self.assertRaises(ValueError):
                    validate_patch(changed)


if __name__ == "__main__":
    unittest.main()
