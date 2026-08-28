"""Offline checks of pinned TWRP source edits, not build or device validation."""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import unittest
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "patches/twrp/series.json"
SOURCE_SNAPSHOT = ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml"
SOURCE_SNAPSHOT_SHA256 = "e967ec0392a3438f4706278e9e77b0810c4401a36f0e64c211a1e5c6e5bfb051"
ORIGINAL_PREFIX_SHA256 = "2ec5f5d4c7574391b4f2a2be94081bcddc99af5a4b0b01f665c5ffffd57e8895"
PROFILE_BLOCK = (
    '    enabled: select(soong_config_variable("nezha_twrp", "native_recovery_only"), {\n'
    '        true: false,\n'
    '        default: unset,\n'
    '    }),\n'
)
PROFILE_PROJECTS = {
    "0005-native-recovery-cts-robolectric": (
        "cts", "e70f92f52c9830ee8f93d89d032e2b14765c5941", {
            "tests/location/Android.bp": ["CtsLocationTestCasesRobo"]}),
    "0006-native-recovery-mobile-data-robolectric": (
        "external/mobile-data-download", "7cecd5acc893660c66d2e7695bd6723dc0346f5d", {
            "javatests/Android.bp": ["MobileDataDownloadRoboTests"]}),
    "0007-native-recovery-framework-robolectric": (
        "frameworks/base", "99b01a65cc4c104933788b3143285ab6bae65827", {
            "libs/WindowManager/Shell/multivalentTests/Android.bp": ["WMShellRobolectricTests"],
            "packages/CredentialManager/tests/robotests/Android.bp": ["CredentialManagerScreenshotTest"],
            "packages/CredentialManager/wear/robotests/Android.bp": ["CredentialSelectorTests"],
            "packages/SettingsLib/DataStore/tests/Android.bp": ["SettingsLibDataStoreTest"],
            "packages/SettingsLib/Spa/screenshot/robotests/Android.bp": ["SpaRoboRNGTests"],
            "packages/SettingsLib/SpaPrivileged/tests/robotests/Android.bp": ["SpaPrivilegedRoboTests"],
            "packages/SettingsLib/tests/robotests/Android.bp": ["SettingsLibRoboTests"],
            "packages/SystemUI/Android.bp": ["SystemUiRoboTests", "SystemUiRoboTestsInplace"],
            "services/robotests/Android.bp": ["FrameworksServicesRoboTests"],
            "services/robotests/backup/Android.bp": ["BackupFrameworksServicesRoboTests"],
            "tests/InputScreenshotTest/robotests/Android.bp": ["InputRoboRNGTests"]}),
    "0008-native-recovery-bluetooth-robolectric": (
        "packages/modules/Bluetooth", "4b73ee6039271ffbf71ebdc8c109fc98eac8e137", {
            "service/Android.bp": ["ServiceBluetoothRoboTests"]}),
    "0009-native-recovery-devicelock-robolectric": (
        "packages/modules/DeviceLock", "952de0dacfb9bd720c9ee604affea6bff8132a8a", {
            "DeviceLockController/tests/robolectric/Android.bp": ["DeviceLockControllerRoboTests"],
            "tests/unittests/Android.bp": ["DeviceLockUnitTests"]}),
    "0010-native-recovery-healthfitness-robolectric": (
        "packages/modules/HealthFitness", "c0d64b5a3b88c614e25394499610c39d8926f69d", {
            "tests/Android.bp": ["HealthFitnessRoboUnitTests"]}),
    "0011-native-recovery-robolectric-runtimes": (
        "prebuilts/misc", "6e84ee6ddafe39d475876c511a516dbc9f2f19a6", {
            "common/robolectric/Android.bp": ["robolectric-android-all-prebuilts"]}),
}


def profile_type(name):
    return ("android_robolectric_runtimes" if name == "robolectric-android-all-prebuilts"
            else "android_robolectric_test")


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


def validate_profile_insertions(section, expected_names):
    """Require only the exact enabled blocks, anchored to named test modules."""
    found = []
    for _, _, _, _, body in hunks(section):
        index = 0
        while index < len(body):
            line = body[index]
            if line.startswith("-"):
                raise ValueError("A native profile patch must not remove or replace source")
            if not line.startswith("+"):
                index += 1
                continue
            end = index
            while end < len(body) and body[end].startswith("+"):
                end += 1
            addition = "".join(item[1:] for item in body[index:end])
            if addition != PROFILE_BLOCK:
                raise ValueError("Only the exact enabled select with default unset is permitted")
            context = "".join(item[1:] for item in body[:index] if item.startswith(" "))
            match = re.search(
                r'(android_robolectric_test|android_robolectric_runtimes)\s*\{\n'
                r'(?:[ \t]*\n)*    name: "([^"\n]+)",\n$', context)
            if not match or match[2] not in expected_names or match[1] != profile_type(match[2]):
                raise ValueError("Enabled addition is not anchored to an approved module")
            if match[2] in found:
                raise ValueError("Duplicate enabled addition")
            found.append(match[2])
            index = end
    if found != list(expected_names):
        raise ValueError("Profile module inventory does not match the exact additions")
    return found


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
        self.assertEqual(list(self.patches), list(expected) + list(PROFILE_PROJECTS))
        for key, (project, commit, path) in expected.items():
            with self.subTest(patch=key):
                row = self.patches[key]
                self.assertEqual(row["project"], project)
                self.assertEqual(row["base_commit"], commit)
                self.assertEqual([item["path"] for item in row["files"]], [path])
                self.assertIn(commit, row["files"][0]["source_url"])

    def test_original_four_patch_records_and_payloads_are_an_unchanged_prefix(self):
        prefix = self.record["patches"][:4]
        canonical = json.dumps(prefix, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), ORIGINAL_PREFIX_SHA256)
        for row in prefix:
            self.assertEqual(hashlib.sha256(self.raw[row["id"]]).hexdigest(), row["patch_sha256"])

    def test_native_profile_projects_and_files_are_bound_to_the_frozen_base(self):
        snapshot = SOURCE_SNAPSHOT.read_bytes()
        self.assertEqual(hashlib.sha256(snapshot).hexdigest(), SOURCE_SNAPSHOT_SHA256)
        frozen = {item.get("path", item.get("name")): item.attrib
                  for item in ET.fromstring(snapshot).findall("project")}
        modules = []
        for key, (project, revision, paths) in PROFILE_PROJECTS.items():
            with self.subTest(patch=key):
                row = self.patches[key]
                self.assertEqual(row["project"], project)
                self.assertEqual(row["base_commit"], revision)
                self.assertEqual(frozen[project]["revision"], revision)
                self.assertEqual(row["source_snapshot_sha256"], SOURCE_SNAPSHOT_SHA256)
                self.assertEqual([item["path"] for item in row["files"]], list(paths))
                expected_repo = ("https://github.com/TWRP-Test/android_cts" if project == "cts"
                                 else "https://android.googlesource.com/platform/" + project)
                self.assertEqual(row["repository"], expected_repo)
                for source in row["files"]:
                    self.assertIn(revision, source["source_url"])
                    self.assertIn(source["path"], source["source_url"])
                    inventory = source["profile_modules"]
                    self.assertEqual([item["name"] for item in inventory], paths[source["path"]])
                    for item in inventory:
                        self.assertEqual(item["type"], profile_type(item["name"]))
                        self.assertIs(item["enabled_property_before"], False)
                        self.assertRegex(item["before_module_sha256"], r"^[0-9a-f]{64}$")
                        modules.append(item["name"])
        self.assertEqual(len(modules), 19)
        self.assertEqual(len(set(modules)), 19)
        self.assertEqual(sum(len(row[2]) for row in PROFILE_PROJECTS.values()), 18)

    def test_native_profile_adds_only_enabled_fields_to_the_exact_test_inventory(self):
        for key, (_, _, paths) in PROFILE_PROJECTS.items():
            sections = self.text[key].split("diff --git ")[1:]
            for section, source in zip(sections, self.patches[key]["files"]):
                with self.subTest(patch=key, path=source["path"]):
                    names = paths[source["path"]]
                    self.assertEqual(validate_profile_insertions(section, names), names)
                    self.assertEqual(changed_lines(section, "-"), [])
                    self.assertEqual(changed_lines(section, "+"),
                                     PROFILE_BLOCK.splitlines() * len(names))
                    self.assertEqual(source["after_size_bytes"] - source["before_size_bytes"],
                                     len(PROFILE_BLOCK.encode()) * len(names))

    def test_native_profile_guard_rejects_production_modules_and_other_edits(self):
        key = "0005-native-recovery-cts-robolectric"
        section = self.text[key].split("diff --git ")[1]
        names = ["CtsLocationTestCasesRobo"]
        mutations = {
            "wrong module type": section.replace(" android_robolectric_test {", " android_library {"),
            "wrong module name": section.replace('name: "CtsLocationTestCasesRobo"', 'name: "production-service"'),
            "overwrite source": section.replace('     name: "CtsLocationTestCasesRobo",', '-    name: "CtsLocationTestCasesRobo",'),
            "default enable override": section.replace("+        default: unset,", "+        default: true,"),
            "disable unrelated products": section.replace("+        default: unset,", "+        default: false,"),
            "wrong flag namespace": section.replace('"nezha_twrp"', '"other_product"'),
            "wrong flag type": section.replace("+        true: false,", '+        "true": false,'),
            "missing dependency bypass": section.replace("+    }),\n", "+    }),\n+    allow_missing_dependencies: true,\n"),
            "replace inherited property": section.replace("+    enabled:", "-    enabled:"),
        }
        for label, mutated in mutations.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                validate_profile_insertions(mutated, names)

    def test_native_profile_inventory_and_semantics_do_not_claim_runtime_validation(self):
        profile = self.record["native_recovery_profile"]
        self.assertEqual(profile["namespace"], "nezha_twrp")
        self.assertEqual(profile["boolean_variable"], "native_recovery_only")
        self.assertIs(profile["selected_value"], True)
        self.assertIs(profile["enabled_when_selected"], False)
        self.assertEqual(profile["otherwise"], "unset")
        self.assertEqual(profile["test_module_count"], 18)
        self.assertEqual(profile["runtime_module_name"], "robolectric-android-all-prebuilts")
        self.assertEqual(profile["affected_file_count"], 18)
        self.assertEqual(profile["affected_base_project_count"], 7)
        self.assertIs(profile["supplemental_projects_modified"], False)
        self.assertEqual(profile["direct_test_constructor_count"],
                         profile["selected_test_constructor_count"] +
                         profile["already_source_excluded_test_constructor_count"])
        self.assertEqual(profile["secondary_blueprint_test_constructor_count"], 0)
        self.assertEqual(profile["configurable_test_module_alias_count"], 0)
        self.assertEqual(profile["explicit_references_to_gated_names_in_retained_blueprints"], 0)
        self.assertIn("build/soong/android/mutator.go:478", profile["semantics_sources"])
        self.assertIn("build/soong/docs/selects.md:64", profile["semantics_sources"])
        self.assertIn("build/make/core/config.mk:320", profile["semantics_sources"])
        self.assertIn("does not claim to run them", profile["preserved_behavior"])
        self.assertIn("do not prove", profile["validation_boundary"])
        self.assertIn("VendorVarTypes", profile["validation_boundary"])

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
        readme = (ROOT / "patches/twrp/README.md").read_text()
        minadbd_section = readme.split("The separate `minadbd` executable", 1)[1].split(
            "\n\nThe queue does not change", 1)[0]
        minadbd_section = " ".join(minadbd_section.split())
        for fact in ("already selected for building and packaging", "preserves that dependency",
                     "`auth_required = false` before `usb_init()`", "GUI's sideload action",
                     "OpenRecoveryScript's `sideload`", "not admitted for runtime use",
                     "Before any diagnostic boot", "reviewed fail-closed gate"):
            self.assertIn(fact, minadbd_section)
        requirements = " ".join(self.record["application_requirements"])
        self.assertIn("never /work/evolution", requirements)
        self.assertIn("every preimage SHA256", requirements)
        self.assertIn("every postimage SHA256", requirements)


if __name__ == "__main__":
    unittest.main()
