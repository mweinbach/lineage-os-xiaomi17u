"""Offline contract for the single generic-image native recovery selector.

The tracked hunk contains the complete image module, not its complete 37 KB
Blueprint file. Sealed source identities bind bytes outside the hunk. The
Boolean matrix is a controlled expectation from the pinned Android factory
and ModuleBase semantics, not a Soong evaluator or a graph/build result.
No ignored receipts, source checkout, network, subprocess, or phone is needed.
"""

import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from test_twrp_patches import hunks, SOURCE_SNAPSHOT_SHA256
from test_twrp_device import assignments, source_path_allowed


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0021-native-recovery-generic-system-image"
PROJECT = "build/make"
REVISION = "3b5b2b43b8e2200ef92b7b814a84c8dde8b74121"
REPOSITORY = "https://github.com/TWRP-Test/android_build"
SOONG_REVISION = "91bdc79cffb29d35b2d46a33204c061c3e7ed4f7"
OLD_TWENTY = "dd1a51718b5ebdb4899e05983b668e1b778d1200625907155076b8b7c340295b"
OLD_METADATA = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
HISTORICAL_SOURCE_RULE_COUNT = 169
HISTORICAL_SOURCE_RULES = "fbbdecd70ea8dc50ae86d8dc0e420d5b54f311293e3d22fea25f969a8fe31ee5"
ENTRY_SHA256 = "fad8b9b0efe64202800cc507f5c6a4f9a10e0b9cd6217ae204765585c31957b3"
PATCH_SHA256 = "1c793575de0629073c908431b01d9336fd4aa06016eaaec8bd9286e1424eae3d"
FILE = {
    "path": "target/product/generic/Android.bp", "mode": "100644",
    "before_sha256": "bcee7ae67c73aa8e0923766688589d0dc2eabd082b2b57d5acbdf661348a8f27",
    "after_sha256": "9a960fd5edd4fabe96fbc0a12bc5a27092f58db10ad854481bd1cf551118579c",
    "before_git_blob": "0a32a55b6be95915ad3c2011344e5f19a0ab6056",
    "after_git_blob": "11e195762e1b16bf718b827e74da14e99584bb15",
    "before_size_bytes": 37411, "after_size_bytes": 37546,
}
MODULE = {
    "type": "android_system_image", "name": "aosp_shared_system_image",
    "constructor_line": 1054, "name_line": 1055,
    "before_module_sha256": "0fba6db5af04cb9b1437ea91e407f458f02cf1c8337fdb50314c52c7d1dcda08",
    "after_module_sha256": "db1a0d27db76cec32842cdabee46a9796519f21b84835369dbdd6abe84bff04b",
    "enabled_property_present_before": False,
    "enabled_when_true": False, "enabled_otherwise": True,
    "selector_namespace": "nezha_twrp", "selector_variable": "native_recovery_only",
    "selector_type": "bool",
}
ANCHOR = 'android_system_image {\n    name: "aosp_shared_system_image",\n'
INSERTION = (
    '    enabled: select(soong_config_variable("nezha_twrp", "native_recovery_only"), {\n'
    '        true: false,\n'
    '        default: true,\n'
    '    }),\n'
)
BEFORE_MODULE = (
    ANCHOR
    + '    defaults: ["system_image_defaults"],\n'
    '    dirs: android_rootdirs,\n'
    '    symlinks: android_symlinks,\n'
    '    type: "erofs",\n'
    '    erofs: {\n'
    '        compressor: "lz4hc,9",\n'
    '        compress_hints: "erofs_compress_hints.txt",\n'
    '    },\n'
    '    deps: [\n'
    '        // DO NOT update this list. Instead, update the system_image_defaults to\n'
    '        // sync with the base_system.mk\n'
    '        "logpersist.start", // cf only\n'
    '    ],\n'
    '}\n'
)
AFTER_MODULE = BEFORE_MODULE.replace(ANCHOR, ANCHOR + INSERTION, 1)
HEADER = (f"diff --git a/{FILE['path']} b/{FILE['path']}\n"
          f"index {FILE['before_git_blob']}..{FILE['after_git_blob']} 100644\n"
          f"--- a/{FILE['path']}\n+++ b/{FILE['path']}\n"
          "@@ -1036,34 +1036,38 @@ system_image_defaults {\n")
HUNK_SHA256 = {
    "before": "481e957a2a1407cbf32fdfd6793dfe2eec390a9347197038cc5b8907f74b528c",
    "after": "37b1a293d1b9275c3e8af72587821de53bf86c7158f23afe5a269c9e2063c00e",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def validate_patch(raw):
    """Constrain the exact image-only addition without a payload checksum gate."""
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected complete LF-terminated patch bytes")
    text = raw.decode("utf-8")
    parsed = list(hunks(text))
    if not text.startswith(HEADER) or len(parsed) != 1 or parsed[0][:4] != (1036, 34, 1036, 38):
        raise ValueError("Unreviewed path, full Git blobs, mode, or hunk coordinates")
    body = parsed[0][4]
    if len(body) != 38 or any(line[:1] not in (" ", "+") for line in body):
        raise ValueError("No source removal, extra file, or malformed hunk is allowed")
    added = "".join(line[1:] for line in body if line.startswith("+"))
    before_lines = [line[1:] for line in body if line.startswith(" ")]
    if len(before_lines) != 34 or added != INSERTION:
        raise ValueError("Only the four reviewed Boolean selector lines may be added")
    before, after = "".join(before_lines), "".join(line[1:] for line in body)
    if (before.count(ANCHOR) != 1 or "".join(before_lines[18:]) != BEFORE_MODULE
            or after != before.replace(ANCHOR, ANCHOR + INSERTION, 1)):
        raise ValueError("The selector must follow this image's name and preserve every original property")
    expected_body = ([" " + line for line in before_lines[:20]]
                     + ["+" + line for line in INSERTION.splitlines(keepends=True)]
                     + [" " + line for line in before_lines[20:]])
    if body != expected_body:
        raise ValueError("The enabled selector moved or a neighboring definition changed")
    for stage, value in [("before", before), ("after", after)]:
        if digest(value.encode()) != HUNK_SHA256[stage]:
            raise ValueError("The reviewed original hunk or resulting hunk changed")
    return before, after


def expected_android_image_enabled(profile, *, patched, forced_disabled=False):
    """Model only the source-reviewed Android image contract, not Soong.

    At SOONG_REVISION, arch.go registers Android with DefaultDisabled=false;
    module.go ModuleBase.Enabled checks ForcedDisabled first and otherwise
    defaults to !Os.DefaultDisabled. The original module/defaults have no
    enabled override. mutator.go:478 guards both dependency mutators with
    Enabled; these unit tests do not execute or independently prove that gate.
    Inputs represent values after typed Boolean conversion, or absence.
    """
    if profile is not None and type(profile) is not bool:
        raise ValueError("Expected a typed Boolean or an absent selector")
    if type(patched) is not bool or type(forced_disabled) is not bool:
        raise ValueError("Controlled fixture switches must be Booleans")
    if forced_disabled:
        return False
    return not (patched and profile is True)


class GenericSystemImageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        cls.rows = cls.series["patches"]
        cls.row = cls.rows[20]
        cls.path = ROOT / "patches/twrp" / (PATCH_ID + ".patch")
        cls.patch = cls.path.read_bytes()

    def test_historical_prefix_and_metadata_survive_future_appends(self):
        self.assertGreaterEqual(len(self.rows), 21)
        self.assertEqual(canonical(self.rows[:20]), OLD_TWENTY)
        self.assertEqual(canonical({k: v for k, v in self.series.items() if k != "patches"}), OLD_METADATA)

    def test_exact_record_and_all_twenty_one_payloads(self):
        self.assertEqual(self.row["id"], PATCH_ID)
        self.assertEqual(canonical(self.row), ENTRY_SHA256)
        self.assertEqual(self.row["patch"], "patches/twrp/" + PATCH_ID + ".patch")
        for row in self.rows[:21]:
            with self.subTest(patch=row["id"]):
                path = ROOT / row["patch"]
                self.assertFalse(path.is_symlink())
                self.assertTrue(path.is_file())
                self.assertEqual(digest(path.read_bytes()), row["patch_sha256"])

    def test_frozen_make_and_soong_owners_and_existing_typed_flag(self):
        raw = (ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml").read_bytes()
        self.assertEqual(digest(raw), SOURCE_SNAPSHOT_SHA256)
        projects = list(ET.fromstring(raw).iter("project"))
        for path, revision in [(PROJECT, REVISION), ("build/soong", SOONG_REVISION)]:
            with self.subTest(project=path):
                owners = [p for p in projects if p.get("path", p.get("name")) == path]
                self.assertEqual(len(owners), 1)
                self.assertEqual(owners[0].get("revision"), revision)
        self.assertEqual((self.row["project"], self.row["base_commit"], self.row["repository"]),
                         (PROJECT, REVISION, REPOSITORY))
        self.assertEqual(self.row["files"][0]["source_url"],
                         f"https://raw.githubusercontent.com/TWRP-Test/android_build/{REVISION}/{FILE['path']}")
        board = (ROOT / "recovery/twrp/device/xiaomi/nezha/BoardConfig.mk").read_text()
        self.assertEqual(board.count("$(call soong_config_set_bool, nezha_twrp, native_recovery_only, true)"), 1)

    def test_fresh_file_full_identities_and_135_byte_addition(self):
        self.assertEqual(len(self.row["files"]), 1)
        self.assertEqual({k: self.row["files"][0][k] for k in FILE}, FILE)
        self.assertNotIn((PROJECT, FILE["path"]), {(r["project"], f["path"])
                         for r in self.rows[:20] for f in r["files"]})
        for stage in ["before", "after"]:
            self.assertRegex(FILE[stage + "_git_blob"], r"^[0-9a-f]{40}$")
            self.assertRegex(FILE[stage + "_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(FILE["after_size_bytes"] - FILE["before_size_bytes"], len(INSERTION.encode()))
        self.assertEqual(len(INSERTION.encode()), 135)

    def test_exact_payload_hunk_and_complete_module_identities(self):
        self.assertEqual(len(self.patch), 1344)
        self.assertEqual(digest(self.patch), PATCH_SHA256)
        self.assertEqual(self.row["patch_sha256"], PATCH_SHA256)
        self.assertEqual(self.row["files"][0]["profile_image_modules"], [MODULE])
        self.assertNotIn("profile_modules", self.row["files"][0])
        before, after = validate_patch(self.patch)
        self.assertEqual((len(before.splitlines()), len(after.splitlines())), (34, 38))
        for stage, fragment in [("before", BEFORE_MODULE), ("after", AFTER_MODULE)]:
            self.assertEqual(digest(fragment.encode()), MODULE[stage + "_module_sha256"])
        self.assertEqual(before[before.index(ANCHOR):], BEFORE_MODULE)
        self.assertEqual(after[after.index(ANCHOR):], AFTER_MODULE)

    def test_dependencies_shared_defaults_and_image_properties_are_preserved(self):
        before, after = validate_patch(self.patch)
        self.assertEqual(after.replace(INSERTION, "", 1), before)
        self.assertEqual(before.splitlines()[:18], after.splitlines()[:18])
        self.assertNotIn("enabled:", BEFORE_MODULE)
        for field in ['defaults: ["system_image_defaults"]', "dirs: android_rootdirs",
                      "symlinks: android_symlinks", 'type: "erofs"', 'compressor: "lz4hc,9"',
                      'compress_hints: "erofs_compress_hints.txt"', '"logpersist.start"']:
            self.assertIn(field, BEFORE_MODULE)
            self.assertIn(field, AFTER_MODULE)
        # A one-file, insertion-only patch cannot cut the GSI BP or VTS
        # providers, change source scope, or edit the validator implementations.
        self.assertEqual([f["path"] for f in self.row["files"]], [FILE["path"]])
        self.assertEqual(self.patch.count(b"diff --git "), 1)
        device = (ROOT / "recovery/twrp/device/xiaomi/nezha/device.mk").read_text()
        scopes = assignments(device)["PRODUCT_SOURCE_ROOT_DIRS"].split()
        # Future reviewed source additions may append rules; never pin the
        # current total or silently permit a cut of these retained providers.
        self.assertGreaterEqual(len(scopes), HISTORICAL_SOURCE_RULE_COUNT)
        self.assertEqual(canonical(scopes[:HISTORICAL_SOURCE_RULE_COUNT]), HISTORICAL_SOURCE_RULES)
        for path in ["build/make/target/product/generic/Android.bp",
                     "build/make/target/product/gsi/Android.bp",
                     "test/vts-testcase/vndk/Android.bp", "system/sepolicy/Android.bp",
                     "external/avb/Android.bp", "system/libvintf/Android.bp"]:
            with self.subTest(retained_source=path):
                self.assertTrue(source_path_allowed(path, scopes))
                self.assertFalse(source_path_allowed(path, scopes + ["-" + path]))

    def test_typed_true_false_and_absence_preserve_the_original_default(self):
        validate_patch(self.patch)
        for profile, original, selected in [(True, True, False), (False, True, True), (None, True, True)]:
            for forced in [False, True]:
                with self.subTest(profile=profile, forced_disabled=forced):
                    self.assertIs(expected_android_image_enabled(profile, patched=False, forced_disabled=forced),
                                  original and not forced)
                    self.assertIs(expected_android_image_enabled(profile, patched=True, forced_disabled=forced),
                                  selected and not forced)
        self.assertIs(MODULE["enabled_property_present_before"], False)
        self.assertIs(MODULE["enabled_when_true"], False)
        self.assertIs(MODULE["enabled_otherwise"], True)

    def test_truth_matrix_does_not_coerce_untyped_fixture_values(self):
        for value in ["true", "false", 0, 1, [], {}, object()]:
            with self.subTest(profile=value), self.assertRaises(ValueError):
                expected_android_image_enabled(value, patched=True)
        for kwargs in [{"patched": "true"}, {"patched": 1}, {"patched": True, "forced_disabled": 1}]:
            with self.subTest(switches=kwargs), self.assertRaises(ValueError):
                expected_android_image_enabled(False, **kwargs)

    def test_selector_and_source_mutations_fail_without_payload_checksum_gate(self):
        raw = self.patch
        addition = "".join("+" + line for line in INSERTION.splitlines(keepends=True)).encode()
        mutations = {
            "unconditional_disabled": raw.replace(addition, b"+    enabled: false,\n", 1),
            "wrong_namespace": raw.replace(b'"nezha_twrp"', b'"other_product"', 1),
            "wrong_variable": raw.replace(b'"native_recovery_only"', b'"disable_all_images"', 1),
            "wrong_condition": raw.replace(b"+        true: false,", b"+        false: false,", 1),
            "enabled_when_true": raw.replace(b"+        true: false,", b"+        true: true,", 1),
            "default_false": raw.replace(b"+        default: true,", b"+        default: false,", 1),
            "unreviewed_unset": raw.replace(b"+        default: true,", b"+        default: unset,", 1),
            "string_default": raw.replace(b"+        default: true,", b'+        default: "true",', 1),
            "duplicate_enabled": raw.replace(addition, addition + b"+    enabled: false,\n", 1),
            "different_module": raw.replace(b'name: "aosp_shared_system_image"', b'name: "other_image"', 1),
            "different_constructor": raw.replace(b" android_system_image {", b" android_filesystem {", 1),
            "dropped_default": raw.replace(b'     defaults: ["system_image_defaults"],', b'-    defaults: ["system_image_defaults"],', 1),
            "dropped_dependency": raw.replace(b'         "logpersist.start", // cf only', b'-        "logpersist.start", // cf only', 1),
            "changed_image_type": raw.replace(b'     type: "erofs",', b'     type: "ext4",', 1),
            "changed_neighbor_defaults": raw.replace(b'                 "libc_hwasan",', b'                 "libc",', 1),
            "security_bypass": raw.replace(addition, addition + b"+    disable_signing: true,\n", 1),
            "validator_bypass": raw.replace(addition, addition + b"+    skip_fsck: true,\n", 1),
            "moved_after_default": raw.replace(addition + b'     defaults: ["system_image_defaults"],\n',
                                                b'     defaults: ["system_image_defaults"],\n' + addition, 1),
        }
        for name, changed in mutations.items():
            with self.subTest(mutation=name):
                self.assertNotEqual(changed, raw)
                with self.assertRaises(ValueError):
                    validate_patch(changed)

    def test_malformed_diff_security_edits_and_source_cuts_are_rejected(self):
        raw = self.patch
        mutations = {
            "old_path": raw.replace(b"--- a/target/product/generic/Android.bp", b"--- a/other.bp", 1),
            "new_path": raw.replace(b"+++ b/target/product/generic/Android.bp", b"+++ b/other.bp", 1),
            "mode": raw.replace(b" 100644\n", b" 100755\n", 1),
            "short_old_blob": raw.replace(FILE["before_git_blob"].encode(), FILE["before_git_blob"][:12].encode(), 1),
            "short_new_blob": raw.replace(FILE["after_git_blob"].encode(), FILE["after_git_blob"][:12].encode(), 1),
            "old_start": raw.replace(b"@@ -1036,34", b"@@ -1035,34", 1),
            "new_count": raw.replace(b"+1036,38 @@", b"+1036,37 @@", 1),
            "preamble": b"unreviewed preamble\n" + raw,
            "trailer": raw + b"GIT binary patch\n",
            "security_second_hunk": raw + b"@@ -20,1 +20,1 @@\n-    avb_enable: true,\n+    avb_enable: false,\n",
            "source_cut": raw + b"diff --git a/device.mk b/device.mk\n@@ -1,1 +1,2 @@\n source\n+PRODUCT_SOURCE_ROOT_DIRS += -build/make/target/product/generic/\n",
            "gsi_cut": raw + b"diff --git a/target/product/gsi/Android.bp b/target/product/gsi/Android.bp\n",
            "validator_edit": raw + b"diff --git a/build/soong/android/mutator.go b/build/soong/android/mutator.go\n",
            "no_final_lf": raw[:-1],
            "crlf": raw.replace(b"\n", b"\r\n"),
            "nul": raw.replace(b"+    enabled:", b"+    enabled:\0", 1),
            "invalid_utf8": raw.replace(b"+    enabled:", b"+    enabled:\xff", 1),
            "not_bytes": raw.decode(),
        }
        for name, changed in mutations.items():
            with self.subTest(mutation=name), self.assertRaises(ValueError):
                validate_patch(changed)


if __name__ == "__main__":
    unittest.main()
