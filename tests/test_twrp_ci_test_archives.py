"""Offline contract for four original CI archive task profile guards.

These tests inspect public patch/metadata bytes and a controlled Make-value
model. They do not run Make, Kati, Soong, network/process calls or a phone, and
need no ignored receipts or source checkout. Full source/body and actual GNU
Make trace equivalence were separately reviewed before patch admission.
"""
import hashlib
import itertools
import json
from pathlib import Path
import unittest

from test_twrp_patches import hunks, SOURCE_SNAPSHOT_SHA256
from scripts import twrp_patch_state, twrp_workspace

ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0027-native-recovery-ci-test-archives"
PROJECT = "platform_testing"
REVISION = "7b48625b052b94b1ef24573ef5e8ffa5e2ea9783"
REPOSITORY = "https://android.googlesource.com/platform/platform_testing"
OLD_26 = "ca0e3ba36abba28c4445196e33aae6db806457c858e38e6cf7a89892c62aa7e6"
OLD_METADATA = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
OLD_SERIES_BYTES = "690c196755503011a1272a57fd3add9eed341ee8766bc31b7f11958ca65b20ea"
GUARD = 'ifneq ($(filter nezha_twrp,$(sort $(SOONG_CONFIG_NAMESPACES))):$(filter native_recovery_only,$(sort $(SOONG_CONFIG_nezha_twrp))):$(SOONG_CONFIG_TYPE_nezha_twrp_native_recovery_only):$(call soong_config_get,nezha_twrp,native_recovery_only):,nezha_twrp:native_recovery_only:bool:true:)\n'
COMMENT = '# This native recovery profile does not package framework CI test archives.\n'
SUFFIX = '\nendif # registered nezha_twrp.native_recovery_only bool:true\n'
PATCH_SHA256 = '5ae39f0f9b033d1e083b6f32e69e284d35792de46f61341eeb6641a60c3462f3'
ENTRY_SHA256 = '26553801e31eb95d0d04ed5f08143acb2f7b61b9c1ebc20f8efdc961dcea6b0c'
FILES = [{'path': 'build/tasks/continuous_instrumentation_metric_tests.mk', 'mode': '100644', 'before_sha256': '9258ae71cc7c8260cb73ea19bd209cc70ca055ee5bde11977320c061564a8811', 'after_sha256': 'b7ea184b30be1fedd3fa7472278e9c544fbd92c0bd2df9aab6fffdb6a7e0f9ab', 'before_size_bytes': 1432, 'after_size_bytes': 1855, 'before_git_blob': '0ff0aba51ff1a37058ff1bd6dd5c77f08d7c3b35', 'after_git_blob': 'e3224fc58cdf26389b632962e3b10b2feaae5368', 'source_url': 'https://android.googlesource.com/platform/platform_testing/+/7b48625b052b94b1ef24573ef5e8ffa5e2ea9783/build/tasks/continuous_instrumentation_metric_tests.mk'}, {'path': 'build/tasks/continuous_instrumentation_tests.mk', 'mode': '100644', 'before_sha256': 'b2dc47a69d0bb8f6c098be80eeca76332f0c7c47ce73cba5dc1a1910531e7bba', 'after_sha256': 'b8300b270a3abd39b1f8ce94ee44694bd0f33eff3d7baddad0b6631a745aab46', 'before_size_bytes': 3779, 'after_size_bytes': 4202, 'before_git_blob': 'f8da9fc06892d1fc8c9fd8f5cc35a9ca1c25f959', 'after_git_blob': '977317c804866ef664bb8993971173f5da9b4314', 'source_url': 'https://android.googlesource.com/platform/platform_testing/+/7b48625b052b94b1ef24573ef5e8ffa5e2ea9783/build/tasks/continuous_instrumentation_tests.mk'}, {'path': 'build/tasks/continuous_native_metric_tests.mk', 'mode': '100644', 'before_sha256': '8b4940eb7c208ec63c8670dab332307c47fc6bb30d769cfb30db6149528c76ad', 'after_sha256': '659b3c74cb37c26b6175f22661f4b767da62377516b152acf1dcc84dc95aa518', 'before_size_bytes': 1381, 'after_size_bytes': 1804, 'before_git_blob': '14ae3f69b0881269eb079e66781f2680ee46fdf0', 'after_git_blob': '148ae57931898deb0833613fbc2306b473636ec7', 'source_url': 'https://android.googlesource.com/platform/platform_testing/+/7b48625b052b94b1ef24573ef5e8ffa5e2ea9783/build/tasks/continuous_native_metric_tests.mk'}, {'path': 'build/tasks/continuous_native_tests.mk', 'mode': '100644', 'before_sha256': '028aa9d345fe1a2b3742c2167d98362ea23ca69cb6b4a58fd1d1a160b462f03e', 'after_sha256': '8f42ff01e745606ab956618cb83cdcc7ada4a6c76c0eab80ed0dfc2bc0ca6a4d', 'before_size_bytes': 1311, 'after_size_bytes': 1734, 'before_git_blob': 'ef452f8cbdb5ec8ffb3a46baeac2b648afc7af5c', 'after_git_blob': 'b0e6163a38a168a3c45109d60b007c8a986f6378', 'source_url': 'https://android.googlesource.com/platform/platform_testing/+/7b48625b052b94b1ef24573ef5e8ffa5e2ea9783/build/tasks/continuous_native_tests.mk'}]
CONTEXTS = {'build/tasks/continuous_instrumentation_metric_tests.mk': {'first': ['\n', '# Rules to generate a tests zip file that included test modules\n', '# based on the configuration.\n', '\n', 'LOCAL_PATH := $(call my-dir)\n', 'include $(LOCAL_PATH)/tests/instrumentation_metric_test_list.mk\n'], 'last': ['\n', '# Also build this when you run "make tests".\n', 'tests: continuous_instrumentation_metric_tests\n'], 'original_line_count': 36}, 'build/tasks/continuous_instrumentation_tests.mk': {'first': ['\n', '# Rules to generate a tests zip file that included test modules\n', '# based on the configuration.\n', '\n', 'LOCAL_PATH := $(call my-dir)\n', 'include $(LOCAL_PATH)/tests/instrumentation_test_list.mk\n'], 'last': ['dexdeps_exe :=\n', 'test_apks :=\n', 'api_coverage_dep :=\n'], 'original_line_count': 98}, 'build/tasks/continuous_native_metric_tests.mk': {'first': ['\n', '# Rules to generate a tests zip file that included test modules\n', '# based on the configuration for continuous metric testing.\n', '\n', 'LOCAL_PATH := $(call my-dir)\n', 'include $(LOCAL_PATH)/tests/native_metric_test_list.mk\n'], 'last': ['\n', '# Also build this when you run "make tests".\n', 'tests: continuous_native_metric_tests\n'], 'original_line_count': 36}, 'build/tasks/continuous_native_tests.mk': {'first': ['\n', '# Rules to generate a tests zip file that included test modules\n', '# based on the configuration for continuous testing.\n', '\n', 'LOCAL_PATH := $(call my-dir)\n', 'include $(LOCAL_PATH)/tests/native_test_list.mk\n'], 'last': ['\n', '# Also build this when you run "make tests".\n', 'tests: continuous_native_tests\n'], 'original_line_count': 36}}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def validate_task_patch(raw):
    """Require exactly two insertion-only hunks per original task, no hash shortcut."""
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected complete LF text patch")
    text = raw.decode()
    pieces = text.split("diff --git ")
    if pieces[0] or len(pieces) != len(FILES) + 1:
        raise ValueError("Expected only the four reviewed file sections")
    for item, piece in zip(FILES, pieces[1:]):
        path = item["path"]
        expected_header = (f"a/{path} b/{path}\n"
                           f"index {item['before_git_blob']}..{item['after_git_blob']} 100644\n"
                           f"--- a/{path}\n+++ b/{path}\n")
        if not piece.startswith(expected_header):
            raise ValueError("Wrong original task path, Git identity, or mode")
        parsed = list(hunks(piece))
        context = CONTEXTS[path]
        if len(parsed) != 2 or parsed[0][:4] != (14, 6, 14, 9):
            raise ValueError("The guard must precede every active task line")
        last = context["original_line_count"] - 2
        if parsed[1][:4] != (last, 3, last + 3, 5):
            raise ValueError("The guard must close after the complete task body")
        opening = ([" " + line for line in context["first"][:3]]
                   + ["+\n", "+" + COMMENT, "+" + GUARD]
                   + [" " + line for line in context["first"][3:]])
        closing = [" " + line for line in context["last"]] + ["+" + line for line in SUFFIX.splitlines(True)]
        if parsed[0][4] != opening or parsed[1][4] != closing:
            raise ValueError("Only the exact registered Boolean guard may be inserted")
        expected = (expected_header + "@@ -14,6 +14,9 @@\n" + "".join(opening)
                    + f"@@ -{last},3 +{last + 3},5 @@\n" + "".join(closing))
        if piece != expected:
            raise ValueError("No extra text, declarations, removals or targets are allowed")
    return True


def includes_original_task(namespaces, keys, kind, value):
    """Model the exact Make tuple only; not a Make or Soong evaluator.

    Registry fields use sort/filter membership. Stored type and value stay raw,
    including whitespace. The real bool setter converts false to an empty value;
    malformed direct assignments are intentionally kept on the original path.
    """
    if not all(isinstance(x, str) for x in (namespaces, keys, kind, value)):
        raise ValueError("Fixture values must be stored Make strings")
    namespace = "nezha_twrp" if "nezha_twrp" in namespaces.split() else ""
    key = "native_recovery_only" if "native_recovery_only" in keys.split() else ""
    return f"{namespace}:{key}:{kind}:{value}:" != "nezha_twrp:native_recovery_only:bool:true:"


class CiTestArchiveProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        cls.rows = cls.series["patches"]
        cls.row = next(row for row in cls.rows if row["id"] == PATCH_ID)
        cls.patch = (ROOT / cls.row["patch"]).read_bytes()

    def test_old_26_records_and_all_series_metadata_survive(self):
        self.assertGreaterEqual(len(self.rows), 27)
        self.assertEqual(self.rows[26]["id"], PATCH_ID)
        self.assertEqual(canonical(self.rows[:26]), OLD_26)
        self.assertEqual(canonical({k: v for k, v in self.series.items() if k != "patches"}), OLD_METADATA)
        original = {**self.series, "patches": self.rows[:26]}
        self.assertEqual(digest((json.dumps(original, indent=2) + "\n").encode()), OLD_SERIES_BYTES)

    def test_existing_supplementary_owner_and_exact_revision(self):
        config = json.loads((ROOT / "config/twrp-dependencies.json").read_bytes())
        owner = [row for row in config["projects"] if row["path"] == PROJECT]
        self.assertEqual(len(owner), 1)
        self.assertEqual((owner[0]["url"], owner[0]["tag"], owner[0]["commit"]),
                         (REPOSITORY, "android-16.0.0_r1", REVISION))
        self.assertEqual((self.row["project"], self.row["repository"], self.row["base_commit"]),
                         (PROJECT, REPOSITORY, REVISION))
        self.assertEqual(self.row["source_snapshot_sha256"], SOURCE_SNAPSHOT_SHA256)

    def test_exact_new_entry_and_complete_original_four_file_closure(self):
        self.assertEqual(canonical(self.row), ENTRY_SHA256)
        self.assertEqual(self.row["files"], FILES)
        previous = {(row["project"], item["path"]) for row in self.rows[:26] for item in row["files"]}
        for item in FILES:
            self.assertNotIn((PROJECT, item["path"]), previous)
            self.assertNotIn("predecessor_patch_id", item)
            self.assertEqual(item["after_size_bytes"] - item["before_size_bytes"], 423)
            self.assertEqual(item["mode"], "100644")
            self.assertEqual(item["source_url"], REPOSITORY + "/+/" + REVISION + "/" + item["path"])
        self.assertTrue(all(item["path"].startswith("build/tasks/continuous_") for item in FILES))
        self.assertFalse(any("/tests/" in item["path"] or item["path"].endswith("package-modules.mk") for item in FILES))

    def test_exact_insertion_only_payload_and_all_admitted_hashes(self):
        self.assertTrue(validate_task_patch(self.patch))
        self.assertEqual(len(self.patch), 4215)
        self.assertEqual(digest(self.patch), PATCH_SHA256)
        for row in self.rows:
            with self.subTest(patch=row["id"]):
                self.assertEqual(digest((ROOT / row["patch"]).read_bytes()), row["patch_sha256"])

    def test_real_shared_inventory_and_full_plan_accept_the_new_supplement(self):
        inventory = twrp_patch_state.patch_inventory(twrp_workspace.load_config(), ROOT)
        self.assertEqual(inventory["patches"], self.rows)
        plan = twrp_patch_state.patch_plan(inventory)
        self.assertEqual(plan["patch_count"], len(self.rows))
        owner = plan["projects"][PROJECT]
        self.assertEqual(owner["base_commit"], REVISION)
        self.assertEqual(set(owner["files"]), {item["path"] for item in FILES})

    def test_existing_flag_declaration_is_unchanged_and_uses_typed_helper(self):
        board = (ROOT / "recovery/twrp/device/xiaomi/nezha/BoardConfig.mk").read_text()
        setter = "$(call soong_config_set_bool, nezha_twrp, native_recovery_only, true)"
        self.assertEqual(board.count(setter), 1)
        self.assertIn("SOONG_CONFIG_NAMESPACES", GUARD)
        self.assertIn("SOONG_CONFIG_nezha_twrp", GUARD)
        self.assertIn("SOONG_CONFIG_TYPE_nezha_twrp_native_recovery_only", GUARD)
        self.assertIn("$(call soong_config_get,nezha_twrp,native_recovery_only):", GUARD)

    def test_only_registered_exact_bool_true_removes_the_task(self):
        for namespaces, keys, kind, value in itertools.product(
                ("", "other", "nezha_twrp", "other nezha_twrp nezha_twrp"),
                ("", "other", "native_recovery_only", "other native_recovery_only"),
                ("", "string", "bool", "bool "),
                ("", "false", "true", "true false", "true ", " true", "TRUE", "1")):
            with self.subTest(namespaces=namespaces, keys=keys, kind=kind, value=value):
                expected = not ("nezha_twrp" in namespaces.split() and "native_recovery_only" in keys.split()
                                and kind == "bool" and value == "true")
                self.assertEqual(includes_original_task(namespaces, keys, kind, value), expected)

    def test_absent_false_and_string_true_preserve_original_tasks(self):
        for args in [("", "", "", ""), ("nezha_twrp", "native_recovery_only", "bool", ""),
                     ("nezha_twrp", "native_recovery_only", "bool", "false"),
                     ("nezha_twrp", "native_recovery_only", "string", "true"),
                     ("", "", "bool", "true")]:
            with self.subTest(args=args):
                self.assertTrue(includes_original_task(*args))

    def test_safety_scope_and_projection_limits_are_explicit(self):
        reason = self.row["reason"]
        for text in ("Only that missing name is an observed graph50 archive error",
                     "other three archives are a reviewed sibling CI scope projection",
                     "not a platform API compatibility check", "shared package-modules.mk",
                     "strict missing-provider/required-module checks", "SELinux, VINTF, AVB",
                     "No empty phony target, fake archive, broad test switch",
                     "No archive, recovery image or device success is claimed"):
            self.assertIn(text, reason)
        additions = "".join(line[1:] for line in self.patch.decode().splitlines(True)
                            if line.startswith("+") and not line.startswith("+++"))
        for forbidden in ("ALLOW_MISSING_DEPENDENCIES", "BUILD_BROKEN", "my_modules_strict", "PRODUCT_PACKAGES",
                          "SELINUX_IGNORE", "tests:", ".PHONY:", "touch ", "skip_tests"):
            self.assertNotIn(forbidden, additions)

    def test_guard_path_and_hunk_mutations_are_rejected_without_checksum_shortcut(self):
        raw = self.patch
        mutations = {
            "wrong_namespace": raw.replace(b"filter nezha_twrp,", b"filter other,", 1),
            "wrong_variable": raw.replace(b"filter native_recovery_only,", b"filter skip_tests,", 1),
            "wrong_type": raw.replace(b":bool:true:)", b":string:true:)", 1),
            "value_filter": raw.replace(b"$(call soong_config_get,nezha_twrp,native_recovery_only):",
                                         b"$(filter true,$(call soong_config_get,nezha_twrp,native_recovery_only)):", 1),
            "no_terminal_marker": raw.replace(b"native_recovery_only):,", b"native_recovery_only),", 1),
            "inverted_guard": raw.replace(b"+ifneq ", b"+ifeq ", 1),
            "moved_start": raw.replace(b"@@ -14,6 +14,9 @@", b"@@ -15,6 +15,9 @@", 1),
            "moved_end": raw.replace(b"@@ -34,3 +37,5 @@", b"@@ -33,3 +36,5 @@", 1),
            "missing_end": raw.replace(("+"+SUFFIX.splitlines(True)[1]).encode(), b"", 1),
            "extra_target": raw + b"+continuous_native_tests:\n",
            "source_removal": raw.replace(b" tests: continuous_native_tests", b"-tests: continuous_native_tests", 1),
            "mode_change": raw.replace(b" 100644\n", b" 100755\n", 1),
            "abbreviated_blob": raw.replace(FILES[0]["before_git_blob"].encode(), b"0ff0aba", 1),
            "broad_path": raw.replace(b"build/tasks/continuous_native_tests.mk", b"Android.mk"),
            "missing_newline": raw[:-1],
        }
        for name, mutated in mutations.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_task_patch(mutated)


if __name__ == "__main__":
    unittest.main()
