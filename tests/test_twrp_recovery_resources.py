"""Offline contract for restoring the original common MDPI resource module.

The hunk reconstructs the complete commented and restored module, not the
complete Android.bp file. Sealed full-file identities bind the surrounding
source. These tests require no ignored reports, checkout, network, or phone;
they do not run fsgen/Soong or establish resource installation in an image.
"""

import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from support import canonical_json_sha256 as canonical, sha256_bytes as digest
from test_twrp_patches import hunks, SOURCE_SNAPSHOT_SHA256


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0020-restore-common-mdpi-recovery-resources"
PROJECT = "bootable/recovery"
REVISION = "b70f8e998b302381ecefc6e7f46df1614bd61afc"
REPOSITORY = "https://github.com/TWRP-Test/android_bootable_recovery"
OLD_NINETEEN = "02408fc3f1947b720603463dcd4c6b268ed0aa1d68ac1259440c5f789359156e"
OLD_METADATA = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
ENTRY_SHA256 = "abb5ea6499406ca3c657055dd23f1903da48fe84a9247625d3ff12aa156f51d0"
PATCH_SHA256 = "115176b88854cbdf85b7d0770d7a5aae00ccc43b84606a18b0dc448eb55fa96b"
FILE = {
    "path": "Android.bp", "mode": "100644",
    "before_sha256": "194b733dd7e16246688d6b94f4d559e890a3110b2ce8ef77c9e30f3327ee55d4",
    "after_sha256": "1049726f463a715bd9e3d4714599de9e2be7185dbec1ceb19d1bbf99d8bd2cbf",
    "before_git_blob": "d7c56cc80e5aab8a5d9cd261bd82041d720a97a7",
    "after_git_blob": "87c1a57f513bdc1e1fcc7bca980886739c4ca047",
    "before_size_bytes": 20733, "after_size_bytes": 20703,
}
MODULE = {
    "type": "prebuilt_res", "name": "recovery-resources-common-mdpi",
    "constructor_line": 314, "name_line": 315, "end_line": 323,
    "before_comment_prefix": "// ", "uncommented_lines": 10,
    "source_glob": "res-mdpi/images/*.png",
    "before_module_sha256": "986f508fcf9d37773f28a99f9e0e69b92f9a6f83a1d0252091be20c55204e0d9",
    "after_module_sha256": "30fb4bfd79ddc99c5d3c6463730cb80e91a1b9bffff7f927605f0ecc552cc216",
    "upstream_repository": "https://android.googlesource.com/platform/bootable/recovery",
    "upstream_commit": "80fbea7e9af1dd883f2046e9b299d6fe45a0f693",
    "upstream_path": "Android.bp", "upstream_constructor_line": 314,
    "upstream_module_sha256": "30fb4bfd79ddc99c5d3c6463730cb80e91a1b9bffff7f927605f0ecc552cc216",
}
RESTORED_BLOCK = (
    'prebuilt_res {\n'
    '    name: "recovery-resources-common-mdpi",\n'
    '    recovery: true,\n'
    '    install_in_root: true,\n'
    '    relative_install_path: "images",\n'
    '    srcs: [\n'
    '        "res-mdpi/images/*.png",\n'
    '    ],\n'
    '    no_full_install: true,\n'
    '}\n'
)
COMMENTED_BLOCK = "".join("// " + line for line in RESTORED_BLOCK.splitlines(keepends=True))
HEADER = (f"diff --git a/{FILE['path']} b/{FILE['path']}\n"
          f"index {FILE['before_git_blob']}..{FILE['after_git_blob']} 100644\n"
          f"--- a/{FILE['path']}\n+++ b/{FILE['path']}\n@@ -294,50 +294,50 @@\n")
HUNK_SHA256 = {
    "before": "7018b76c137da6ef0244eb664508f56d2a5caca8177e5725be0c411bfa69c82a",
    "after": "aa2ec7a8eb796ddaa0e5337815015b29fae86da5be6130e3690c07efd5e30204",
}


def validate_patch(raw):
    """Allow only the sealed ten-line uncomment, without a payload hash gate."""
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected complete LF-terminated patch bytes")
    text = raw.decode("utf-8")
    parsed = list(hunks(text))
    if not text.startswith(HEADER) or len(parsed) != 1 or parsed[0][:4] != (294, 50, 294, 50):
        raise ValueError("Unreviewed path, full Git blobs, mode, or hunk coordinates")
    body = parsed[0][4]
    if len(body) != 60 or any(line[:1] not in (" ", "+", "-") for line in body):
        raise ValueError("Unexpected hunk body, extra section, or trailer")
    before_lines = [line[1:] for line in body if line.startswith((" ", "-"))]
    after_lines = [line[1:] for line in body if line.startswith((" ", "+"))]
    removed = "".join(line[1:] for line in body if line.startswith("-"))
    added = "".join(line[1:] for line in body if line.startswith("+"))
    if len(before_lines) != 50 or len(after_lines) != 50:
        raise ValueError("Both hunk counts must match the complete body")
    if removed != COMMENTED_BLOCK or added != RESTORED_BLOCK:
        raise ValueError("Only the ten original comment prefixes may be removed")
    if "".join(before_lines[20:30]) != COMMENTED_BLOCK or "".join(after_lines[20:30]) != RESTORED_BLOCK:
        raise ValueError("The complete module must remain at original lines 314 through 323")
    before, after = "".join(before_lines), "".join(after_lines)
    if before.count(COMMENTED_BLOCK) != 1 or after != before.replace(COMMENTED_BLOCK, RESTORED_BLOCK, 1):
        raise ValueError("A neighboring module, density, or property changed")
    expected_body = ([" " + line for line in before_lines[:20]]
                     + ["-" + line for line in COMMENTED_BLOCK.splitlines(keepends=True)]
                     + ["+" + line for line in RESTORED_BLOCK.splitlines(keepends=True)]
                     + [" " + line for line in before_lines[30:]])
    if body != expected_body:
        raise ValueError("Unexpected removal/addition ordering or changed context")
    for stage, value in [("before", before), ("after", after)]:
        if digest(value.encode()) != HUNK_SHA256[stage]:
            raise ValueError("The reviewed neighboring source context changed")
    return before, after


class RecoveryResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        cls.rows = cls.series["patches"]
        cls.row = cls.rows[19]
        cls.path = ROOT / "patches/twrp" / (PATCH_ID + ".patch")
        cls.patch = cls.path.read_bytes()

    def test_historical_prefix_and_metadata_survive_future_appends(self):
        self.assertGreaterEqual(len(self.rows), 20)
        self.assertEqual(canonical(self.rows[:19]), OLD_NINETEEN)
        self.assertEqual(canonical({k: v for k, v in self.series.items() if k != "patches"}), OLD_METADATA)

    def test_exact_new_record_and_all_twenty_payloads(self):
        self.assertEqual(self.row["id"], PATCH_ID)
        self.assertEqual(canonical(self.row), ENTRY_SHA256)
        self.assertEqual(self.row["patch"], "patches/twrp/" + PATCH_ID + ".patch")
        for row in self.rows[:20]:
            with self.subTest(patch=row["id"]):
                path = ROOT / row["patch"]
                self.assertFalse(path.is_symlink())
                self.assertTrue(path.is_file())
                self.assertEqual(digest(path.read_bytes()), row["patch_sha256"])

    def test_frozen_recovery_owner_and_source_url(self):
        raw = (ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml").read_bytes()
        self.assertEqual(digest(raw), SOURCE_SNAPSHOT_SHA256)
        owners = [p for p in ET.fromstring(raw).iter("project") if p.get("path", p.get("name")) == PROJECT]
        self.assertEqual(len(owners), 1)
        self.assertEqual(owners[0].get("revision"), REVISION)
        self.assertEqual((self.row["project"], self.row["base_commit"], self.row["repository"]),
                         (PROJECT, REVISION, REPOSITORY))
        self.assertEqual(self.row["files"][0]["source_url"],
                         f"https://raw.githubusercontent.com/TWRP-Test/android_bootable_recovery/{REVISION}/Android.bp")

    def test_fresh_file_full_identities_and_thirty_byte_reduction(self):
        self.assertEqual(len(self.row["files"]), 1)
        self.assertEqual({k: self.row["files"][0][k] for k in FILE}, FILE)
        self.assertNotIn((PROJECT, FILE["path"]), {(r["project"], f["path"])
                         for r in self.rows[:19] for f in r["files"]})
        for stage in ["before", "after"]:
            self.assertRegex(FILE[stage + "_git_blob"], r"^[0-9a-f]{40}$")
            self.assertRegex(FILE[stage + "_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(FILE["before_size_bytes"] - FILE["after_size_bytes"], 30)
        before, after = validate_patch(self.patch)
        self.assertEqual(len(before.encode()) - len(after.encode()), 30)

    def test_sealed_payload_and_exact_single_hunk(self):
        self.assertEqual(len(self.patch), 1944)
        self.assertEqual(digest(self.patch), PATCH_SHA256)
        self.assertEqual(self.row["patch_sha256"], PATCH_SHA256)
        self.assertEqual(self.patch.count(b"diff --git "), 1)
        before, after = validate_patch(self.patch)
        self.assertEqual((len(before.splitlines()), len(after.splitlines())), (50, 50))
        self.assertEqual(self.patch.splitlines()[1].decode(),
                         f"index {FILE['before_git_blob']}..{FILE['after_git_blob']} 100644")

    def test_complete_original_module_provenance_and_properties(self):
        self.assertEqual(self.row["files"][0]["uncommented_modules"], [MODULE])
        self.assertEqual(digest(COMMENTED_BLOCK.encode()), MODULE["before_module_sha256"])
        self.assertEqual(digest(RESTORED_BLOCK.encode()), MODULE["after_module_sha256"])
        self.assertEqual(MODULE["after_module_sha256"], MODULE["upstream_module_sha256"])
        self.assertEqual(len(RESTORED_BLOCK.splitlines()), MODULE["uncommented_lines"])
        self.assertEqual(MODULE["end_line"] - MODULE["constructor_line"] + 1, 10)
        self.assertEqual(MODULE["name_line"], MODULE["constructor_line"] + 1)
        self.assertEqual("".join(line[3:] for line in COMMENTED_BLOCK.splitlines(keepends=True)), RESTORED_BLOCK)

    def test_neighboring_densities_and_nonresource_code_stay_unchanged(self):
        before, after = validate_patch(self.patch)
        self.assertEqual(after.replace(RESTORED_BLOCK, COMMENTED_BLOCK, 1), before)
        self.assertEqual(before.splitlines()[:20], after.splitlines()[:20])
        self.assertEqual(before.splitlines()[30:], after.splitlines()[30:])
        for density in ["hdpi", "xhdpi"]:
            field = f'//     name: "recovery-resources-common-{density}",'
            self.assertIn(field, before)
            self.assertIn(field, after)
            self.assertNotIn(f'\n    name: "recovery-resources-common-{density}",', after)
        self.assertEqual(after.count("\nprebuilt_res {\n"), 1)
        # The sole-file envelope forbids fsgen, density and product-setting edits.
        self.assertEqual([f["path"] for f in self.row["files"]], ["Android.bp"])

    def test_unreviewed_source_mutations_rejected_without_payload_hash_gate(self):
        raw = self.patch
        removals = "".join("-" + line for line in COMMENTED_BLOCK.splitlines(keepends=True)).encode()
        additions = "".join("+" + line for line in RESTORED_BLOCK.splitlines(keepends=True)).encode()
        mutations = {
            "constructor": raw.replace(b"+prebuilt_res {", b"+genrule {", 1),
            "density_alias": raw.replace(b'+    name: "recovery-resources-common-mdpi",', b'+    name: "recovery-resources-common-hdpi",', 1),
            "source_glob": raw.replace(b'+        "res-mdpi/images/*.png",', b'+        "res-hdpi/images/*.png",', 1),
            "destination": raw.replace(b'+    relative_install_path: "images",', b'+    relative_install_path: "twres",', 1),
            "not_recovery": raw.replace(b"+    recovery: true,", b"+    recovery: false,", 1),
            "not_root": raw.replace(b"+    install_in_root: true,", b"+    install_in_root: false,", 1),
            "full_install": raw.replace(b"+    no_full_install: true,", b"+    no_full_install: false,", 1),
            "partial_uncomment": raw.replace(b"+    srcs: [", b"+//     srcs: [", 1),
            "changed_original": raw.replace(b"-//     recovery: true,", b"-//     recovery: false,", 1),
            "extra_property": raw.replace(b"+    recovery: true,\n", b"+    recovery: true,\n+    enabled: true,\n", 1),
            "neighbor_density_context": raw.replace(b' //     name: "recovery-resources-common-hdpi",', b' //     name: "recovery-resources-common-xxxhdpi",', 1),
            "moved_module": raw.replace(b" \n" + removals + additions, removals + additions + b" \n", 1),
        }
        for name, changed in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(changed, raw)
                with self.assertRaises(ValueError):
                    validate_patch(changed)

    def test_malformed_envelopes_and_extra_file_edits_are_rejected(self):
        raw = self.patch
        mutations = {
            "old_path": raw.replace(b"--- a/Android.bp", b"--- a/other.bp", 1),
            "new_path": raw.replace(b"+++ b/Android.bp", b"+++ b/other.bp", 1),
            "mode": raw.replace(b" 100644\n", b" 100755\n", 1),
            "short_old_blob": raw.replace(FILE["before_git_blob"].encode(), FILE["before_git_blob"][:12].encode(), 1),
            "short_new_blob": raw.replace(FILE["after_git_blob"].encode(), FILE["after_git_blob"][:12].encode(), 1),
            "old_start": raw.replace(b"@@ -294,50", b"@@ -293,50", 1),
            "new_count": raw.replace(b"+294,50 @@", b"+294,49 @@", 1),
            "preamble": b"unreviewed preamble\n" + raw,
            "trailer": raw + b"GIT binary patch\n",
            "extra_fsgen_file": raw + b"diff --git a/build/soong/fsgen.go b/build/soong/fsgen.go\n",
            "extra_product_file": raw + b"diff --git a/device.mk b/device.mk\n",
            "no_final_lf": raw[:-1],
            "crlf": raw.replace(b"\n", b"\r\n"),
            "nul": raw.replace(b"+prebuilt_res", b"+prebuilt\0_res", 1),
            "invalid_utf8": raw.replace(b"+prebuilt_res", b"+prebuilt\xff_res", 1),
            "not_bytes": raw.decode(),
        }
        for name, changed in mutations.items():
            with self.subTest(mutation=name), self.assertRaises(ValueError):
                validate_patch(changed)


if __name__ == "__main__":
    unittest.main()
