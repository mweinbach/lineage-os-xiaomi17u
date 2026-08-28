"""Offline checks of pinned TWRP source edits, not build or device validation."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "patches/twrp/series.json"


def changed_lines(patch, prefix):
    return [line[1:] for line in patch.splitlines()
            if line.startswith(prefix) and not line.startswith(prefix * 3)]


def hunks(section):
    """Return strict unified diff hunks without invoking a patch process."""
    pattern = r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n"
    matches = list(re.finditer(pattern, section, re.M))
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        body = section[match.end():end].splitlines(keepends=True)
        yield (int(match[1]), int(match[2] or 1), int(match[3]),
               int(match[4] or 1), body)


def select_android_variant(lines, recovery):
    """Select the simple exact CPP guards present in the reviewed auth hunks."""
    active = [True]
    selected = []
    for line in lines:
        directive = line.strip()
        if directive in ("#if defined(__ANDROID__)",
                         "#if defined(__ANDROID_RECOVERY__)",
                         "#if !defined(__ANDROID_RECOVERY__)"):
            condition = {
                "#if defined(__ANDROID__)": True,
                "#if defined(__ANDROID_RECOVERY__)": recovery,
                "#if !defined(__ANDROID_RECOVERY__)": not recovery,
            }[directive]
            active.append(active[-1] and condition)
        elif directive == "#else":
            if len(active) < 2:
                raise ValueError("Unmatched #else in reviewed fixture")
            active[-1] = active[-2] and not active[-1]
        elif directive == "#endif":
            if len(active) < 2:
                raise ValueError("Unmatched #endif in reviewed fixture")
            active.pop()
        elif directive.startswith("#"):
            raise ValueError("Unexpected preprocessor directive in reviewed fixture")
        elif active[-1]:
            selected.append(line)
    if len(active) != 1:
        raise ValueError("Unclosed preprocessor guard in reviewed fixture")
    return "".join(selected)


class TwrpPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(SERIES.read_text())
        cls.patches = {row["id"]: row for row in cls.record["patches"]}
        cls.raw = {key: (ROOT / row["patch"]).read_bytes()
                   for key, row in cls.patches.items()}
        cls.text = {key: value.decode() for key, value in cls.raw.items()}

    def test_selected_manifest_and_exact_project_heads_are_bound(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["manifest"], {
            "repository": "https://github.com/TWRP-Test/platform_manifest_twrp_aosp",
            "branch": "twrp-16.0",
            "commit": "d2188a9345857fb078c391e8cb3e259a21e941e5",
        })
        expected = {
            "0001-remove-permissive-su": (
                "system/sepolicy", "f0270686ee017f4de42e1032aca7527031bcc484", "private/su.te"),
            "0002-do-not-force-adb-root": (
                "bootable/recovery", "b70f8e998b302381ecefc6e7f46df1614bd61afc", "etc/init.rc"),
            "0003-preserve-source-on-envsetup": (
                "vendor/twrp", "b53296dfc420ce65fffe712de380d5abf6c4c2f1", "build/envsetup.sh"),
            "0004-require-recovery-adb-auth": (
                "packages/modules/adb", "ce023afef190b0cea7f8939e9dd5ee3ee79b137b", "daemon/main.cpp"),
        }
        self.assertEqual(list(self.patches), list(expected))
        for key, (project, commit, path) in expected.items():
            with self.subTest(patch=key):
                row = self.patches[key]
                self.assertEqual(row["project"], project)
                self.assertEqual(row["base_commit"], commit)
                self.assertEqual([item["path"] for item in row["files"]], [path])
                self.assertIn(commit, row["files"][0]["source_url"])

    def test_patch_bytes_and_source_versions_are_hash_bound(self):
        seen = set()
        for key, row in self.patches.items():
            with self.subTest(patch=key):
                raw = self.raw[key]
                self.assertTrue(raw.endswith(b"\n"))
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["patch_sha256"])
                self.assertEqual(self.text[key].count("diff --git "), len(row["files"]))
                for source in row["files"]:
                    identity = (row["project"], source["path"])
                    self.assertNotIn(identity, seen)
                    seen.add(identity)
                    self.assertIn(source["before_git_blob"] + ".." + source["after_git_blob"],
                                  self.text[key])
                    for name in ("before_sha256", "after_sha256"):
                        self.assertRegex(source[name], r"^[0-9a-f]{64}$")
                    for name in ("before_git_blob", "after_git_blob"):
                        self.assertRegex(source[name], r"^[0-9a-f]{40}$")
                    self.assertNotEqual(source["before_sha256"], source["after_sha256"])
                    self.assertGreater(source["before_size_bytes"], 0)
                    self.assertGreater(source["after_size_bytes"], 0)

    def test_all_application_paths_stay_inside_the_declared_projects(self):
        for key, row in self.patches.items():
            with self.subTest(patch=key):
                for value in [row["project"], row["patch"],
                              *(source["path"] for source in row["files"])]:
                    path = PurePosixPath(value)
                    self.assertFalse(path.is_absolute())
                    self.assertNotIn("..", path.parts)
                    self.assertNotIn("\\", value)
                    self.assertEqual(str(path), value)
                self.assertTrue(row["patch"].startswith("patches/twrp/"))
                for source in row["files"]:
                    path = source["path"]
                    self.assertIn(f"diff --git a/{path} b/{path}\n", self.text[key])
                    self.assertIn(f"--- a/{path}\n+++ b/{path}\n", self.text[key])

    def test_hunk_counts_order_and_byte_deltas_match_metadata(self):
        for key, row in self.patches.items():
            sections = self.text[key].split("diff --git ")[1:]
            for section, source in zip(sections, row["files"]):
                with self.subTest(patch=key, path=source["path"]):
                    parsed = list(hunks(section))
                    self.assertTrue(parsed)
                    delta = 0
                    previous_old_end = previous_new_end = 0
                    for old_start, old_count, new_start, new_count, lines in parsed:
                        self.assertGreaterEqual(old_start, previous_old_end)
                        self.assertGreaterEqual(new_start, previous_new_end)
                        self.assertTrue(all(line[:1] in (" ", "+", "-") for line in lines))
                        self.assertEqual(sum(line.startswith((" ", "-")) for line in lines), old_count)
                        self.assertEqual(sum(line.startswith((" ", "+")) for line in lines), new_count)
                        delta += sum(len(line[1:].encode()) for line in lines if line.startswith("+"))
                        delta -= sum(len(line[1:].encode()) for line in lines if line.startswith("-"))
                        previous_old_end = old_start + old_count
                        previous_new_end = new_start + new_count
                    self.assertEqual(source["before_size_bytes"] + delta, source["after_size_bytes"])

    def test_policy_patch_removes_only_the_debug_permissive_declaration(self):
        patch = self.text["0001-remove-permissive-su"]
        self.assertEqual(changed_lines(patch, "-"), [
            "", "  # su is also permissive to permit setenforce.",
            "  permissive su;",
        ])
        self.assertEqual(changed_lines(patch, "+"), [])
        self.assertIn("   app_domain(su)", patch)
        self.assertNotIn("-  allow ", patch)
        self.assertNotIn("-  neverallow ", patch)

    def test_recovery_init_no_longer_requests_root_automatically(self):
        patch = self.text["0002-do-not-force-adb-root"]
        self.assertEqual(changed_lines(patch, "-"), [
            "", "# Always start adbd on userdebug and eng builds",
            "on property:ro.debuggable=1",
            "    #write /sys/class/android_usb/android0/enable 1",
            "    #start adbd", "    setprop service.adb.root 1",
        ])
        self.assertEqual(changed_lines(patch, "+"), [])
        # Removing auto-root does not weaken authentication or change the daemon domain.
        self.assertNotIn("ro.adb.secure", patch)
        self.assertNotIn("ro.secure", patch)
        self.assertNotIn("-    seclabel", patch)

    def test_envsetup_patch_removes_only_the_immediate_source_truncation(self):
        patch = self.text["0003-preserve-source-on-envsetup"]
        self.assertEqual(changed_lines(patch, "-"), [
            "", "# Empty the vts makefile",
            "if [ -s $(gettop)/frameworks/base/services/core/xsd/vts/Android.mk ]; then",
            '\techo -n "" > $(gettop)/frameworks/base/services/core/xsd/vts/Android.mk', "fi",
        ])
        self.assertEqual(changed_lines(patch, "+"), [])
        self.assertNotIn("ALLOW_MISSING_DEPENDENCIES", patch)
        self.assertNotIn("BUILD_BROKEN", patch)

    def test_recovery_auth_is_required_even_on_debug_unlocked_or_tradein_devices(self):
        patch = self.text["0004-require-recovery-adb-auth"]
        source = self.patches["0004-require-recovery-adb-auth"]["files"][0]
        self.assertEqual(source["before_sha256"],
                         "8b9ea62b9ec742a6f3fe15b3c2612b929dbdc2d57aa86f3609ad54744ddba8ca")
        self.assertEqual(source["before_size_bytes"], 13274)
        sections = patch.split("diff --git ")[1:]
        self.assertEqual(len(sections), 1)
        post_hunks = [[line[1:] for line in body if line.startswith((" ", "+"))]
                      for _, _, _, _, body in hunks(sections[0])]
        self.assertEqual(len(post_hunks), 2)
        recovery_code = "".join(select_android_variant(lines, True) for lines in post_hunks)
        self.assertIn("auth_required = true;", recovery_code)
        for absent in ("auth_required = false;", "device_unlocked", "__android_log_is_debuggable",
                       "GetBoolProperty", "should_enter_tradeinmode", "enter_tradeinmode",
                       "is_in_tradein_evaluation_mode"):
            with self.subTest(absent=absent):
                self.assertNotIn(absent, recovery_code)

    def test_non_recovery_authentication_selection_and_privilege_dropping_are_preserved(self):
        patch = self.text["0004-require-recovery-adb-auth"]
        section = patch.split("diff --git ")[1]
        for _, _, _, _, body in hunks(section):
            before = [line[1:] for line in body if line.startswith((" ", "-"))]
            after = [line[1:] for line in body if line.startswith((" ", "+"))]
            self.assertEqual(select_android_variant(before, False),
                             select_android_variant(after, False))
        removed = "\n".join(changed_lines(patch, "-"))
        added = "\n".join(changed_lines(patch, "+"))
        for untouched in ("minijail_change_uid", "minijail_change_gid", "cap_set_proc",
                          "should_drop_privileges", "adbd_auth_init", "usb_init"):
            self.assertNotIn(untouched, removed)
            self.assertNotIn(untouched, added)
        self.assertNotIn("auth_required = false", added)

    def test_checked_guards_do_not_claim_a_safe_boot_or_write_lock(self):
        self.assertTrue(all(value is True for value in self.record["preserved_checks"].values()))
        checks = " ".join(self.record["verification_requirements"])
        self.assertIn("unfiltered sepolicy-analyze permissive", checks)
        self.assertIn("require empty output", checks)
        self.assertIn("ro.secure=1 and ro.adb.secure=1", checks)
        limits = " ".join(self.record["runtime_limitations"])
        self.assertIn("No build, boot, authenticated ADB", limits)
        self.assertIn("BCB", limits)
        self.assertIn("not create a write lock", limits)
        self.assertIn("No phone access or change", limits)
        self.assertNotIn("device_tested", self.record)
        requirements = " ".join(self.record["application_requirements"])
        self.assertIn("never /work/evolution", requirements)
        self.assertIn("every preimage SHA256", requirements)
        self.assertIn("every postimage SHA256", requirements)


if __name__ == "__main__":
    unittest.main()
