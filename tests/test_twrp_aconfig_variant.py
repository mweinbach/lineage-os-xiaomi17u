"""Offline contract for one exact aconfig image-availability restoration.

The approved hunk contains the complete C++ module and surrounding release
selection. Full-file identities bind the unseen source to the reviewed TWRP
preimage and exact Android 16 r1 postimage. These tests do not execute Soong or
infer recovery consumers, image variants, compilation, or device behavior.
"""

import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0017-restore-aconfig-storage-core-images"
PATCH_PATH = "patches/twrp/" + PATCH_ID + ".patch"
SOURCE_PATH = "tools/aconfig/aconfig_storage_read_api/Android.bp"
PROJECT = "build/make"
BASE_COMMIT = "3b5b2b43b8e2200ef92b7b814a84c8dde8b74121"
REPOSITORY = "https://github.com/TWRP-Test/android_build"
SNAPSHOT_PATH = "research/source-snapshots/twrp-16.0-linux-20260828.xml"
SNAPSHOT_SHA256 = "e967ec0392a3438f4706278e9e77b0810c4401a36f0e64c211a1e5c6e5bfb051"
PREVIOUS_SIXTEEN_SHA256 = "64da3e3374ea8fd69523ccd990057b7c4587228572aab006cb018a86e60b2ec2"
PREVIOUS_METADATA_SHA256 = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
ENTRY_CANONICAL_SHA256 = "9335747921d619ae39df313165ddb9f25f9fe35bde79268aa71fcc4b94eaacc6"
PATCH_SHA256 = "6ad92da04f41474793921fed371a958043bef605fa3857367438e939db510523"
PATCH_SIZE = 1502
FILE_IDENTITIES = {
    "path": SOURCE_PATH,
    "mode": "100644",
    "before_sha256": "3319305b8b1b5f70e045b3d6e81f4dbd1195a067906695ad6b2bdab3fe22c66a",
    "before_size_bytes": 4371,
    "before_git_blob": "27300b66b1af8c44882d9e6c19dd16048edf4a0d",
    "after_sha256": "9de30e8e3732b4855b4cedb16531c570291e14bff15b72f7a7420ed2314c6299",
    "after_size_bytes": 4341,
    "after_git_blob": "16341b92735823ef624892dbfa6c94864f9bcfef",
}
MODULE_IDENTITIES = {
    "name": "libaconfig_storage_read_api_cc",
    "type": "cc_library",
    "constructor_line": 80,
    "name_line": 81,
    "removed_property_line": 95,
    "before_module_sha256": "86575f1f61a88bc8e2a6228df598a64766dc4115885604678e3c30fc7bcb33a1",
    "after_module_sha256": "12c2109b7c9b901c7a9d0a85ead3ebf360db026b03be08ce1a249d1c97be34b4",
    "recovery_available_property_before": True,
    "recovery_available_property_after": False,
}
REMOVED = '    recovery_available: true,\n'
MODULE_BEFORE = '''cc_library {
    name: "libaconfig_storage_read_api_cc",
    srcs: ["aconfig_storage_read_api.cpp"],
    generated_headers: [
        "cxx-bridge-header",
        "libcxx_aconfig_storage_read_api_bridge_header",
    ],
    generated_sources: ["libcxx_aconfig_storage_read_api_bridge_code"],
    whole_static_libs: ["libaconfig_storage_read_api_cxx_bridge"],
    export_include_dirs: ["include"],
    static_libs: [
        "libbase",
    ],
    host_supported: true,
    vendor_available: true,
    recovery_available: true,
    product_available: true,
    apex_available: [
        "//apex_available:platform",
        "//apex_available:anyapex",
    ],
    min_sdk_version: "29",
    target: {
        linux: {
            version_script: "libaconfig_storage_read_api_cc.map",
        },
    },
    double_loadable: true,
    afdo: true,
}
'''
MODULE_AFTER = MODULE_BEFORE.replace(REMOVED, "", 1)
CONTEXT_PREFIX = '    ],\n    min_sdk_version: "29",\n}\n\n// flag read api cc interface\n'
CONTEXT_SUFFIX = '''
cc_defaults {
    name: "aconfig_lib_cc_shared_link.defaults",
    shared_libs: select(release_flag("RELEASE_READ_FROM_NEW_STORAGE"), {
        true: ["libaconfig_storage_read_api_cc"],
        default: [],
'''
BEFORE_HUNK = CONTEXT_PREFIX + MODULE_BEFORE + CONTEXT_SUFFIX
AFTER_HUNK = CONTEXT_PREFIX + MODULE_AFTER + CONTEXT_SUFFIX
HEADER = (
    f"diff --git a/{SOURCE_PATH} b/{SOURCE_PATH}\n"
    "index 27300b66b1af8c44882d9e6c19dd16048edf4a0d..16341b92735823ef624892dbfa6c94864f9bcfef 100644\n"
    f"--- a/{SOURCE_PATH}\n"
    f"+++ b/{SOURCE_PATH}\n"
)
HUNK_HEADER = "@@ -75,41 +75,40 @@\n"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def reviewed_fixture():
    """Construct the reviewed fragment in memory without reading source files."""
    body = "".join(("-" if line == REMOVED else " ") + line
                   for line in BEFORE_HUNK.splitlines(keepends=True))
    return (HEADER + HUNK_HEADER + body).encode()


def validate_restoration_patch(raw):
    """Constrain this one hunk, independently of its published payload checksum.

    Exact context is intentional: this is a test of one reviewed change, not a
    general patch parser. It rejects metadata, paths, line movement, extra edits,
    fake anchors, and all changes to the complete module or release context.
    """
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected complete LF-terminated patch bytes")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("Patch must be UTF-8 text") from error
    lines = [line + "\n" for line in text[:-1].split("\n")]
    if "".join(lines[:4]) != HEADER:
        raise ValueError("Only the reviewed path, full Git blob IDs and regular mode are allowed")
    if len(lines) < 5 or lines[4] != HUNK_HEADER:
        raise ValueError("Only the reviewed explicit hunk coordinates are allowed")
    body = lines[5:]
    if any(line[:1] not in (" ", "-") for line in body):
        raise ValueError("No additions, extra hunks, headers, trailers or EOF markers are allowed")
    if len(body) != 41 or sum(line.startswith(" ") for line in body) != 40:
        raise ValueError("Unified hunk counts differ from the complete body")
    if [line[1:] for line in body if line.startswith("-")] != [REMOVED]:
        raise ValueError("Only the exact recovery_available property may be removed")
    if body[20] != "-" + REMOVED:
        raise ValueError("The property removal moved from original source line 95")
    before = "".join(line[1:] for line in body)
    after = "".join(line[1:] for line in body if line.startswith(" "))
    if before != BEFORE_HUNK or after != AFTER_HUNK:
        raise ValueError("The approved module/type/name or surrounding source context changed")
    return before, after


class AconfigVariantTrackedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / "patches/twrp/series.json").read_text())
        cls.patches = cls.record["patches"]
        cls.patch = (ROOT / PATCH_PATH).read_bytes()

    def test_previous_sixteen_entries_and_historical_metadata_unchanged(self):
        self.assertGreaterEqual(len(self.patches), 17)
        self.assertEqual(canonical_sha256(self.patches[:16]), PREVIOUS_SIXTEEN_SHA256)
        self.assertEqual(canonical_sha256({key: value for key, value in self.record.items()
                                          if key != "patches"}), PREVIOUS_METADATA_SHA256)

    def test_previous_sixteen_payloads_match_their_unchanged_records(self):
        for row in self.patches[:16]:
            with self.subTest(patch=row["id"]):
                path = ROOT / row["patch"]
                self.assertFalse(path.is_symlink())
                self.assertEqual(sha256(path.read_bytes()), row["patch_sha256"])

    def test_exact_single_new_entry(self):
        self.assertEqual(self.patches[16]["id"], PATCH_ID)
        self.assertEqual(canonical_sha256(self.patches[16]), ENTRY_CANONICAL_SHA256)
        self.assertEqual(self.patches[16]["project"], PROJECT)
        self.assertEqual(self.patches[16]["repository"], REPOSITORY)

    def test_pinned_frozen_build_make_owner(self):
        raw = (ROOT / SNAPSHOT_PATH).read_bytes()
        self.assertEqual(sha256(raw), SNAPSHOT_SHA256)
        project = [item for item in ET.fromstring(raw).iter("project")
                   if item.get("path", item.get("name")) == PROJECT]
        self.assertEqual(len(project), 1)
        self.assertEqual(project[0].get("revision"), BASE_COMMIT)
        self.assertEqual(self.patches[16]["base_commit"], BASE_COMMIT)

    def test_fresh_file_and_full_preimage_postimage_metadata(self):
        self.assertEqual(len(self.patches[16]["files"]), 1)
        item = self.patches[16]["files"][0]
        self.assertEqual({key: item[key] for key in FILE_IDENTITIES}, FILE_IDENTITIES)
        self.assertEqual(item["restored_modules"], [MODULE_IDENTITIES])
        self.assertEqual(item["before_size_bytes"] - item["after_size_bytes"], len(REMOVED.encode()))
        old_files = {(row["project"], file["path"])
                     for row in self.patches[:16] for file in row["files"]}
        self.assertNotIn((PROJECT, SOURCE_PATH), old_files)

    def test_exact_sealed_patch_payload_and_shape(self):
        self.assertFalse((ROOT / PATCH_PATH).is_symlink())
        self.assertEqual(len(self.patch), PATCH_SIZE)
        self.assertEqual(sha256(self.patch), PATCH_SHA256)
        self.assertEqual(self.patches[16]["patch_sha256"], PATCH_SHA256)
        self.assertEqual(self.patch, reviewed_fixture())
        self.assertEqual(validate_restoration_patch(self.patch), (BEFORE_HUNK, AFTER_HUNK))

    def test_complete_module_deps_flags_and_release_context_preserved(self):
        self.assertEqual(sha256(MODULE_BEFORE.encode()), MODULE_IDENTITIES["before_module_sha256"])
        self.assertEqual(sha256(MODULE_AFTER.encode()), MODULE_IDENTITIES["after_module_sha256"])
        before, after = validate_restoration_patch(self.patch)
        self.assertEqual(after, before.replace(REMOVED, "", 1))
        for line in ('    host_supported: true,\n', '    vendor_available: true,\n',
                     '    product_available: true,\n', '    double_loadable: true,\n',
                     '    afdo: true,\n', '    min_sdk_version: "29",\n',
                     '    whole_static_libs: ["libaconfig_storage_read_api_cxx_bridge"],\n'):
            self.assertIn(line, before)
            self.assertIn(line, after)
        self.assertTrue(before.endswith(CONTEXT_SUFFIX))
        self.assertTrue(after.endswith(CONTEXT_SUFFIX))
        self.assertIn('release_flag("RELEASE_READ_FROM_NEW_STORAGE")', after)
        self.assertNotIn("recovery_available", MODULE_AFTER)


if __name__ == "__main__":
    unittest.main()
