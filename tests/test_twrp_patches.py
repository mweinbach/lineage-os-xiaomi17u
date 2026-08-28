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
PREVIOUS_ELEVEN_SHA256 = "5a55847341ce6f0a3b84b7108a3dd142405c3e2e2d48f89c7be3343db510d8a9"
PREVIOUS_THIRTEEN_SHA256 = "e1025aba5aeeffa043b1c4b584f8cafcd986ad1fa4a02d97fc910d456424937c"
PREVIOUS_FOURTEEN_SHA256 = "d92b7a0e4b47b036a16046af964b895d16d7cdd300f47594746b7864c93b340d"
SUPPLEMENT_PROFILE_IDS = [
    "0015-native-recovery-systemui-robolectric",
    "0016-native-recovery-robolectric-integration-tests",
]
INITIAL_PROFILE_SHA256 = "fc455a257d125784e99d6f9e01706f51157e00c2416e3a192a4b34c8adc9de59"
MINADBD_GATE_ID = "0014-native-recovery-disable-minadbd"
ACONFIG_VARIANT_ID = "0017-restore-aconfig-storage-core-images"
AIDL_ANALYZER_VARIANT_ID = "0018-enable-aidl-analyzer-main-recovery"
OMAPI_VARIANT_ID = "0019-enable-omapi-interface-recovery"
RECOVERY_RESOURCES_ID = "0020-restore-common-mdpi-recovery-resources"
GENERIC_SYSTEM_IMAGE_ID = "0021-native-recovery-generic-system-image"
TRUSTY_AVB_TEST_ID = "0022-native-recovery-trusty-avb-test"
TRUSTY_VINTF_TEST_ID = "0023-native-recovery-trusty-vintf-test"
USB_TRANSPORT_ID = "0024-recovery-usb-only-adb"
VOLD_HOST_LIBRARIES_ID = "0025-vold-bionic-system-libraries"
PACKAGING_CONTRACT_ID = "0026-repair-recovery-packaging-contracts"
CI_ARCHIVES_ID = "0027-native-recovery-ci-test-archives"
OZIP_GUARD_ID = "0028-guard-unconfigured-ozip-decryption"
UNUSED_PARAMETERS_ID = "0029-explicit-unused-recovery-parameters"
DEVICE_VERSION_ID = "0030-correct-default-device-version"
TARWRITE_PARAMETER_ID = "0031-explicit-unused-tarwrite-parameter"
RECOVERY_POLICY_ID = "0032-enforce-user-recovery-domains"
MINADBD_GATE_SHA256 = "4a8f59d1351d9a2d935b628f2c95e8d45d8cde3ea64e0087a99987f16e072705"
RECOVERY_REVISION = "b70f8e998b302381ecefc6e7f46df1614bd61afc"
MINADBD_PREIMAGES = {
    "minadbd/Android.bp": (
        "11f64ef3e3361b26e4d659db454c098f830d5da9f529f88973dc13d7cfb933af", 3342, 86),
    "minadbd/minadbd.cpp": (
        "e0e4c332a30cfd80692e85196fb6ff415742040332030a56aa9cd67a7a149665", 2063, 33),
    "twrpinstall/Android.bp": (
        "c1a67f61e6257c9a009f7ef41390f5931e582fd602f2d66673929ac4f402dc94", 1978, 57),
    "twrpinstall/adb_install.cpp": (
        "6d083eedf0b3c803ee650b85d5c8d34f6d53a6143b44da5016fc52636b080977", 14214, 335),
}
MINADBD_SELECT = (
    'select(soong_config_variable("nezha_twrp", "native_recovery_only"), {\n'
    '        true: ["-DNEZHA_TWRP_DISABLE_MINADBD=1"],\n'
    '        default: unset,\n'
    '    })'
)
MINADBD_BINARY_ANCHOR = 'cc_binary {\n    name: "minadbd",\n    recovery: true,\n\n'
MINADBD_BINARY_FLAGS = (
    '    // Keep the binary dependency, but deny its unauthenticated transport in this profile.\n'
    '    cflags: ' + MINADBD_SELECT + ',\n\n'
)
MINADBD_INSTALLER_FLAGS = '    cflags: [\n        "-DAB_OTA_UPDATER=1"\n    ],\n'
MINADBD_INSTALLER_GATED_FLAGS = (
    '    cflags: [\n        "-DAB_OTA_UPDATER=1"\n    ] + ' + MINADBD_SELECT + ',\n'
)
MINADBD_DAEMON_ANCHOR = '  android::base::InitLogging(argv, &android::base::StderrLogger);\n'
MINADBD_DAEMON_GUARD = (
    '#if defined(NEZHA_TWRP_DISABLE_MINADBD)\n'
    '  LOG(ERROR) << "minadbd sideload and rescue are disabled by the Nezha native recovery profile";\n'
    '  return kMinadbdUnsupportedCommandError;\n'
    '#endif\n\n'
)
MINADBD_CALLER_ANCHOR = (
    '  int twrp_sideload(const char* install_file, Device::BuiltinAction* reboot_action) {\n\n'
)
MINADBD_CALLER_GUARD = (
    '#if defined(NEZHA_TWRP_DISABLE_MINADBD)\n'
    '  LOG(ERROR) << "ADB sideload is disabled by the Nezha native recovery profile";\n'
    '  return INSTALL_ERROR;\n'
    '#endif\n\n'
)
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
HELPER_PROFILE_PROJECTS = {
    "0012-native-recovery-settings-ipc-testutils": (
        "frameworks/base", "99b01a65cc4c104933788b3143285ab6bae65827", {
            "packages/SettingsLib/Ipc/Android.bp": ["SettingsLibIpc-testutils"]}),
    "0013-native-recovery-car-ui-test-support": (
        "prebuilts/sdk", "3b7daadc4e54d51439e5ae9b4dbd96cda8b6104e", {
            "current/aaos-libs/Android.bp": [
                "car-ui-lib-testing-support", "car-ui-lib-testing-support-source"]}),
}
HELPER_MODULE_TYPES = {
    "SettingsLibIpc-testutils": "android_library",
    "car-ui-lib-testing-support": "android_library",
    "car-ui-lib-testing-support-source": "android_library_import",
}
ALL_PROFILE_PROJECTS = {**PROFILE_PROJECTS, **HELPER_PROFILE_PROJECTS}


def profile_type(name):
    if name in HELPER_MODULE_TYPES:
        return HELPER_MODULE_TYPES[name]
    if not any(name in names for _, _, paths in PROFILE_PROJECTS.values()
               for names in paths.values()):
        raise ValueError("Unapproved native profile module")
    return ("android_robolectric_runtimes" if name == "robolectric-android-all-prebuilts"
            else "android_robolectric_test")


def changed_lines(patch, prefix):
    return [line[1:] for line in patch.splitlines()
            if line.startswith(prefix) and not line.startswith(prefix * 3)]


def hunks(section):
    """Return strict unified diff hunks without invoking a patch process."""
    pattern = r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@[^\n]*\n"
    matches = list(re.finditer(pattern, section, re.M))
    prefix = section[:matches[0].start()] if matches else section
    if any(line.startswith("\\") for line in prefix.splitlines()):
        raise ValueError("A source EOF marker must belong to a hunk line")
    closed_sides = set()
    for index, match in enumerate(matches):
        if closed_sides:
            raise ValueError("A source EOF marker cannot precede a later hunk")
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        body = []
        for line in section[match.end():end].splitlines(keepends=True):
            if line.startswith("\\"):
                if (line != "\\ No newline at end of file\n" or not body
                        or body[-1][:1] not in (" ", "+", "-")
                        or not body[-1].endswith("\n")):
                    raise ValueError("Malformed, orphaned or duplicate source EOF marker")
                prefix = body[-1][0]
                closed_sides.update({"old", "new"} if prefix == " " else
                                    {"old"} if prefix == "-" else {"new"})
                body[-1] = body[-1][:-1]
            else:
                sides = ({"old", "new"} if line.startswith(" ") else
                         {"old"} if line.startswith("-") else
                         {"new"} if line.startswith("+") else set())
                if sides & closed_sides:
                    raise ValueError("A hunk cannot continue a source after its EOF marker")
                body.append(line)
        yield (int(match[1]), int(match[2] or 1), int(match[3]),
               int(match[4] or 1), body)


def validate_profile_insertions(section, expected_names):
    """Require only the exact enabled blocks, anchored to approved modules."""
    if any(name in HELPER_MODULE_TYPES for name in expected_names):
        context = "".join(line[1:] for _, _, _, _, body in hunks(section)
                          for line in body if line.startswith(" "))
        if re.search(r"^\s*enabled\s*:", context, re.M):
            raise ValueError("A helper gate must not duplicate an existing enabled property")
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
                r'(android_robolectric_test|android_robolectric_runtimes|android_library|android_library_import)\s*\{\n'
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


def validate_minadbd_gate(section, path):
    """Check the exact four reviewed edits using only tracked patch hunks.

    This checks source changes, not a C++ or Soong execution model. Full-file
    preimage identities bind context outside these hunks to the reviewed pin.
    """
    contracts = {
        "minadbd/Android.bp": (MINADBD_BINARY_ANCHOR,
                               MINADBD_BINARY_ANCHOR + MINADBD_BINARY_FLAGS),
        "minadbd/minadbd.cpp": (MINADBD_DAEMON_ANCHOR,
                                MINADBD_DAEMON_ANCHOR + MINADBD_DAEMON_GUARD),
        "twrpinstall/Android.bp": (MINADBD_INSTALLER_FLAGS, MINADBD_INSTALLER_GATED_FLAGS),
        "twrpinstall/adb_install.cpp": (MINADBD_CALLER_ANCHOR,
                                       MINADBD_CALLER_ANCHOR + MINADBD_CALLER_GUARD),
    }
    if path not in contracts:
        raise ValueError("Unapproved minadbd gate path")
    parsed = list(hunks(section))
    if len(parsed) != 1:
        raise ValueError("The minadbd gate requires exactly one reviewed hunk per file")
    old_start, old_count, new_start, new_count, lines = parsed[0]
    if old_start != MINADBD_PREIMAGES[path][2] or new_start != old_start:
        raise ValueError("The minadbd hunk moved from its reviewed source position")
    if (any(line[:1] not in (" ", "+", "-") for line in lines)
            or sum(line.startswith((" ", "-")) for line in lines) != old_count
            or sum(line.startswith((" ", "+")) for line in lines) != new_count):
        raise ValueError("Invalid minadbd hunk body or counts")
    before = "".join(line[1:] for line in lines if line.startswith((" ", "-")))
    after = "".join(line[1:] for line in lines if line.startswith((" ", "+")))
    anchor, replacement = contracts[path]
    if before.count(anchor) != 1 or after != before.replace(anchor, replacement, 1):
        raise ValueError("The minadbd gate is missing, misplaced or contains additional source changes")
    return before, after


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
        self.assertEqual(list(self.patches), list(expected) + list(ALL_PROFILE_PROJECTS)
                         + [MINADBD_GATE_ID] + SUPPLEMENT_PROFILE_IDS
                         + [ACONFIG_VARIANT_ID, AIDL_ANALYZER_VARIANT_ID, OMAPI_VARIANT_ID,
                            RECOVERY_RESOURCES_ID, GENERIC_SYSTEM_IMAGE_ID,
                            TRUSTY_AVB_TEST_ID, TRUSTY_VINTF_TEST_ID, USB_TRANSPORT_ID,
                            VOLD_HOST_LIBRARIES_ID, PACKAGING_CONTRACT_ID, CI_ARCHIVES_ID,
                            OZIP_GUARD_ID, UNUSED_PARAMETERS_ID, DEVICE_VERSION_ID,
                            TARWRITE_PARAMETER_ID, RECOVERY_POLICY_ID])
        self.assertEqual(len(self.patches), 32)
        for key, (project, commit, path) in expected.items():
            with self.subTest(patch=key):
                row = self.patches[key]
                self.assertEqual(row["project"], project)
                self.assertEqual(row["base_commit"], commit)
                self.assertEqual([item["path"] for item in row["files"]], [path])
                self.assertIn(commit, row["files"][0]["source_url"])

    def test_explicit_successors_preserve_usb_and_mdpi_predecessors(self):
        prefix = self.record["patches"][:23]
        canonical = json.dumps(prefix, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(),
                         "8f70a8034f55d4646beac906a3edf9ede454fd9fac512a1c471c90786900d8ed")
        row = self.patches[USB_TRANSPORT_ID]
        predecessor = self.patches["0004-require-recovery-adb-auth"]
        self.assertEqual(row["project"], predecessor["project"])
        self.assertEqual(row["base_commit"], predecessor["base_commit"])
        self.assertEqual(row["repository"], predecessor["repository"])
        self.assertEqual([item["path"] for item in row["files"]],
                         ["daemon/main.cpp", "daemon/adb_wifi.cpp"])
        successors = [(entry["id"], item["path"], item["predecessor_patch_id"])
                      for entry in self.record["patches"] for item in entry["files"]
                      if "predecessor_patch_id" in item]
        self.assertEqual(successors, [
            (USB_TRANSPORT_ID, "daemon/main.cpp", predecessor["id"]),
            (PACKAGING_CONTRACT_ID, "Android.bp", RECOVERY_RESOURCES_ID),
        ])
        for field in ("sha256", "git_blob", "size_bytes"):
            self.assertEqual(row["files"][0]["before_" + field], predecessor["files"][0]["after_" + field])
        paths = [(entry["project"], item["path"])
                 for entry in self.record["patches"] for item in entry["files"]]
        self.assertEqual((len(paths), len(set(paths))), (58, 56))
        self.assertEqual(paths.count((row["project"], "daemon/main.cpp")), 2)
        self.assertEqual(paths.count((row["project"], "daemon/adb_wifi.cpp")), 1)
        self.assertEqual(row["patch_sha256"],
                         "e472bfde972d168fdc8dd1190298a2891d165a083ce3e02898dcd88e8882d792")
        self.assertEqual(row["reviewed_candidate_sha256"],
                         "8ecb76333df2f0a21323ad929204a9cd78bbf1f650c218fe98ce25740fcc8d4d")

    def test_original_four_patch_records_and_payloads_are_an_unchanged_prefix(self):
        prefix = self.record["patches"][:4]
        canonical = json.dumps(prefix, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), ORIGINAL_PREFIX_SHA256)
        for row in prefix:
            self.assertEqual(hashlib.sha256(self.raw[row["id"]]).hexdigest(), row["patch_sha256"])

    def test_previous_eleven_patches_and_initial_profile_audit_are_unchanged(self):
        prefix = self.record["patches"][:11]
        canonical = json.dumps(prefix, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), PREVIOUS_ELEVEN_SHA256)
        for row in prefix:
            self.assertEqual(hashlib.sha256(self.raw[row["id"]]).hexdigest(), row["patch_sha256"])
        initial = json.dumps(self.record["native_recovery_profile"], sort_keys=True,
                             separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(initial).hexdigest(), INITIAL_PROFILE_SHA256)

    def test_previous_thirteen_patch_records_and_payloads_are_unchanged(self):
        prefix = self.record["patches"][:13]
        canonical = json.dumps(prefix, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), PREVIOUS_THIRTEEN_SHA256)
        for row in prefix:
            self.assertEqual(hashlib.sha256(self.raw[row["id"]]).hexdigest(), row["patch_sha256"])

    def test_previous_fourteen_patch_records_and_payloads_are_unchanged(self):
        prefix = self.record["patches"][:14]
        canonical = json.dumps(prefix, sort_keys=True, separators=(",", ":")).encode()
        self.assertEqual(hashlib.sha256(canonical).hexdigest(), PREVIOUS_FOURTEEN_SHA256)
        for row in prefix:
            self.assertEqual(hashlib.sha256(self.raw[row["id"]]).hexdigest(), row["patch_sha256"])

    def test_native_profile_projects_and_files_are_bound_to_the_frozen_base(self):
        snapshot = SOURCE_SNAPSHOT.read_bytes()
        self.assertEqual(hashlib.sha256(snapshot).hexdigest(), SOURCE_SNAPSHOT_SHA256)
        frozen = {item.get("path", item.get("name")): item.attrib
                  for item in ET.fromstring(snapshot).findall("project")}
        modules = []
        for key, (project, revision, paths) in ALL_PROFILE_PROJECTS.items():
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
        self.assertEqual(len(modules), 22)
        self.assertEqual(len(set(modules)), 22)
        self.assertEqual(sum(len(row[2]) for row in PROFILE_PROJECTS.values()), 18)
        self.assertEqual(sum(len(row[2]) for row in HELPER_PROFILE_PROJECTS.values()), 2)

    def test_native_profile_adds_only_enabled_fields_to_the_exact_module_inventory(self):
        for key, (_, _, paths) in ALL_PROFILE_PROJECTS.items():
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

    def test_helper_gates_reject_production_names_wrong_types_and_existing_properties(self):
        for key, (_, _, paths) in HELPER_PROFILE_PROJECTS.items():
            section = self.text[key].split("diff --git ")[1]
            names = next(iter(paths.values()))
            mutations = {
                "production module": section.replace(f'name: "{names[0]}"',
                                                     'name: "SettingsLibIpc"'),
                "wrong factory": section.replace(" android_library {", " java_library {"),
                "existing enabled property": section.replace(
                    f'     name: "{names[0]}",\n',
                    f'     name: "{names[0]}",\n     enabled: true,\n'),
                "changed default": section.replace("+        default: unset,",
                                                   "+        default: true,"),
                "changed source selection": section.replace("+    }),\n",
                                                           "+    }),\n+    srcs: [],\n"),
            }
            if "car-ui-lib-testing-support-source" in names:
                mutations["prebuilt changed to source factory"] = section.replace(
                    " android_library_import {", " android_library {")
            for label, mutated in mutations.items():
                with self.subTest(patch=key, case=label), self.assertRaises(ValueError):
                    validate_profile_insertions(mutated, names)
        with self.assertRaises(ValueError):
            profile_type("car-ui-lib-source")

    def test_helper_preimages_are_the_reviewed_fresh_mixed_files(self):
        expected = {
            "0012-native-recovery-settings-ipc-testutils": (
                "1a5eb0fdf2f24b926ed51cd01935cbafceed9578b5d26ddea945e0e94d251a2d", 721,
                ["5b91fb9b4036e3edf7f54ba26806098e262a8264652e1c1e80c9acc66fa2ebd6"]),
            "0013-native-recovery-car-ui-test-support": (
                "153d3b207a6e905d899aa1b176fa5eaa30e55d3462792a8c940ed66f61cca0e1", 24289,
                ["aba241518d4cf577f7d31bd1c00b02d3b773311a617ef1e724a32300e124ee8c",
                 "58f28bd87fe0eb3469b74d4430550a91bead4e7a03f8e9ffa74fe32352979adb"]),
        }
        prior_files = {(row["project"], source["path"])
                       for row in self.record["patches"][:11] for source in row["files"]}
        for key, (digest, size, module_digests) in expected.items():
            row = self.patches[key]
            source = row["files"][0]
            with self.subTest(patch=key):
                self.assertNotIn((row["project"], source["path"]), prior_files)
                self.assertEqual(source["before_sha256"], digest)
                self.assertEqual(source["before_size_bytes"], size)
                self.assertEqual([item["before_module_sha256"] for item in source["profile_modules"]],
                                 module_digests)
                self.assertTrue(all(item["enabled_property_before"] is False
                                    for item in source["profile_modules"]))

    def test_helper_audit_is_separate_from_historical_test_inventory(self):
        profile = self.record["native_recovery_helper_profile"]
        self.assertEqual(profile["namespace"], "nezha_twrp")
        self.assertEqual(profile["boolean_variable"], "native_recovery_only")
        self.assertIs(profile["selected_value"], True)
        self.assertIs(profile["enabled_when_selected"], False)
        self.assertEqual(profile["otherwise"], "unset")
        self.assertEqual(profile["patch_ids"], list(HELPER_PROFILE_PROJECTS))
        self.assertEqual(profile["helper_module_count"], 3)
        self.assertEqual(profile["affected_file_count"], 2)
        self.assertEqual(profile["affected_base_project_count"], 2)
        self.assertEqual(profile["total_declared_gate_count"], 22)
        self.assertIs(profile["supplemental_projects_modified"], False)
        self.assertEqual(profile["previous_eleven_patch_records_sha256"], PREVIOUS_ELEVEN_SHA256)
        self.assertEqual(profile["initial_profile_record_sha256"], INITIAL_PROFILE_SHA256)
        self.assertEqual(len(profile["companion_source_exclusions"]), 6)
        self.assertIn("frameworks/base/packages/SettingsLib/tests/robotests/Android.bp",
                      profile["companion_source_exclusions"])
        self.assertEqual(profile["audited_blueprint_file_count"], 10855)
        self.assertEqual(profile["audited_make_go_file_count"], 14901)
        self.assertEqual(len(profile["closed_cut_names"]), 17)
        self.assertEqual(profile["closed_cut_edge_count"], 12)
        self.assertEqual(profile["retained_external_consumers_found"], 0)
        self.assertEqual(profile["helper_internal_dependency"], {
            "consumer": "car-ui-lib-testing-support", "provider": "car-ui-lib-testing-support-source"})
        self.assertIn("historical", profile["audit_scope"])
        self.assertIn("not three additional observed graph errors", profile["provenance"])
        self.assertIn("not a complete evaluated Soong graph", profile["validation_boundary"])
        self.assertIn("no missing-dependency or security validation is waived", profile["validation_boundary"])

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

    def minadbd_sections(self):
        row = self.patches[MINADBD_GATE_ID]
        sections = self.text[MINADBD_GATE_ID].split("diff --git ")[1:]
        self.assertEqual(len(sections), len(row["files"]))
        return {source["path"]: section for source, section in zip(row["files"], sections)}

    def test_minadbd_gate_touches_exactly_four_fresh_pinned_recovery_files(self):
        row = self.patches[MINADBD_GATE_ID]
        self.assertEqual(row["project"], "bootable/recovery")
        self.assertEqual(row["repository"], "https://github.com/TWRP-Test/android_bootable_recovery")
        self.assertEqual(row["base_commit"], RECOVERY_REVISION)
        self.assertEqual(row["patch_sha256"], MINADBD_GATE_SHA256)
        self.assertEqual(row["source_snapshot_sha256"], SOURCE_SNAPSHOT_SHA256)
        self.assertEqual([source["path"] for source in row["files"]], list(MINADBD_PREIMAGES))
        frozen = {item.get("path", item.get("name")): item.attrib
                  for item in ET.fromstring(SOURCE_SNAPSHOT.read_bytes()).findall("project")}
        self.assertEqual(frozen["bootable/recovery"]["revision"], RECOVERY_REVISION)
        prior = {(patch["project"], source["path"])
                 for patch in self.record["patches"][:13] for source in patch["files"]}
        for source in row["files"]:
            with self.subTest(path=source["path"]):
                expected_hash, expected_size, _ = MINADBD_PREIMAGES[source["path"]]
                self.assertEqual(source["before_sha256"], expected_hash)
                self.assertEqual(source["before_size_bytes"], expected_size)
                self.assertEqual(source["mode"], "100644")
                self.assertNotIn((row["project"], source["path"]), prior)
                self.assertIn(RECOVERY_REVISION + "/" + source["path"], source["source_url"])

    def test_minadbd_flags_are_typed_and_confined_to_the_two_reviewed_modules(self):
        sections = self.minadbd_sections()
        for path in ("minadbd/Android.bp", "twrpinstall/Android.bp"):
            with self.subTest(path=path):
                before, after = validate_minadbd_gate(sections[path], path)
                self.assertEqual(after.count(MINADBD_SELECT), 1)
                self.assertEqual(after.count("cflags:"), 1)
                self.assertNotIn("NEZHA_TWRP_DISABLE_MINADBD", before)
        before, _ = validate_minadbd_gate(sections["minadbd/Android.bp"], "minadbd/Android.bp")
        self.assertIn('cc_binary {\n    name: "minadbd",', before)
        # The audited full-file preimage pins the libtwrpinstall declaration
        # at lines 52-53; this hunk starts at its defaults at line 57.
        self.assertIn('         "libtwrpinstall_defaults",\n', sections["twrpinstall/Android.bp"])
        board = (ROOT / "recovery/twrp/device/xiaomi/nezha/BoardConfig.mk").read_text()
        self.assertIn("$(call soong_config_set_bool, nezha_twrp, native_recovery_only, true)", board)

    def test_minadbd_false_or_unset_profile_preserves_existing_flags(self):
        sections = self.minadbd_sections()
        before, after = validate_minadbd_gate(sections["minadbd/Android.bp"], "minadbd/Android.bp")
        self.assertEqual(after.replace(MINADBD_BINARY_FLAGS, "", 1), before)
        before, after = validate_minadbd_gate(sections["twrpinstall/Android.bp"], "twrpinstall/Android.bp")
        self.assertEqual(after.replace("] + " + MINADBD_SELECT, "]", 1), before)
        self.assertEqual(before.count('"-DAB_OTA_UPDATER=1"'), 1)
        self.assertEqual(after.count('"-DAB_OTA_UPDATER=1"'), 1)
        # The exact selector has only literal Boolean true and default unset;
        # false and unset therefore leave these old lists unmodified. This
        # is a source contract assertion, not an evaluated Soong graph.
        self.assertIn('true: ["-DNEZHA_TWRP_DISABLE_MINADBD=1"]', MINADBD_SELECT)
        self.assertIn("default: unset", MINADBD_SELECT)

    def test_minadbd_daemon_returns_after_logging_before_argument_handling(self):
        path = "minadbd/minadbd.cpp"
        before, after = validate_minadbd_gate(self.minadbd_sections()[path], path)
        prefix, suffix = after.split(MINADBD_DAEMON_GUARD)
        main_prefix = prefix.split("int main(int argc, char** argv) {\n", 1)[1]
        self.assertEqual(main_prefix, MINADBD_DAEMON_ANCHOR)
        self.assertIn('if ((argc != 3 && argc != 4) || argv[1] != "--socket_fd"s', suffix)
        self.assertIn('argv[3] != "--rescue"s', suffix)
        self.assertEqual(after.replace(MINADBD_DAEMON_GUARD, "", 1), before)
        self.assertIn("return kMinadbdUnsupportedCommandError;", MINADBD_DAEMON_GUARD)
        self.assertNotIn("argc", MINADBD_DAEMON_GUARD)
        self.assertNotIn("argv", MINADBD_DAEMON_GUARD)

    def test_twrp_sideload_returns_before_first_usb_property_or_state_change(self):
        path = "twrpinstall/adb_install.cpp"
        before, after = validate_minadbd_gate(self.minadbd_sections()[path], path)
        caller = after.split(MINADBD_CALLER_ANCHOR, 1)[1]
        self.assertTrue(caller.startswith(MINADBD_CALLER_GUARD))
        for operation in ('GetProperty("sys.usb.state", "none")', 'SetUsbConfig("none")'):
            self.assertGreater(caller.index(operation), len(MINADBD_CALLER_GUARD))
        self.assertIn("return INSTALL_ERROR;", MINADBD_CALLER_GUARD)
        self.assertEqual(after.replace(MINADBD_CALLER_GUARD, "", 1), before)

    def test_minadbd_guards_have_only_logging_and_failure_returns(self):
        sections = self.minadbd_sections()
        for path, guard in (("minadbd/minadbd.cpp", MINADBD_DAEMON_GUARD),
                            ("twrpinstall/adb_install.cpp", MINADBD_CALLER_GUARD)):
            with self.subTest(path=path):
                validate_minadbd_gate(sections[path], path)
                additions = "\n".join(changed_lines(sections[path], "+")) + "\n"
                self.assertEqual(additions, guard)
                self.assertEqual(additions.count("LOG(ERROR)"), 1)
                self.assertEqual(additions.count("return "), 1)
                for forbidden in ("#else", "auth_required", "adbd_auth_init", "usb_init",
                                  "GetProperty", "SetProperty", "SetUsbConfig", "fork(", "exec",
                                  "socket", "SetMinadbd", "reboot_action", "return 0;"):
                    self.assertNotIn(forbidden, additions)

    def test_minadbd_gate_keeps_dependencies_security_and_robolectric_counts(self):
        patch = self.text[MINADBD_GATE_ID]
        self.assertEqual(changed_lines(patch, "-"), ["    ],"])
        for path, section in self.minadbd_sections().items():
            validate_minadbd_gate(section, path)
        changed = "\n".join(changed_lines(patch, "+") + changed_lines(patch, "-"))
        for forbidden in ("auth_required", "ro.adb.secure", "ro.secure", "service.adb.root",
                          "SELINUX", "permissive", "neverallow", "BOARD_AVB", "ROLLBACK",
                          "ALLOW_MISSING_DEPENDENCIES", "BUILD_BROKEN", "check_elf_files",
                          "required:", "shared_libs:", "static_libs:", "defaults:", "srcs:", "enabled:"):
            self.assertNotIn(forbidden, changed)
        self.assertEqual(sum(len(names) for _, _, paths in ALL_PROFILE_PROJECTS.values()
                             for names in paths.values()), 22)
        self.assertEqual(sum(len(paths) for _, _, paths in ALL_PROFILE_PROJECTS.values()), 20)

    def test_minadbd_gate_has_pinned_source_evidence_and_explicit_runtime_limits(self):
        row = self.patches[MINADBD_GATE_ID]
        self.assertEqual(row["profile"], {
            "namespace": "nezha_twrp", "boolean_variable": "native_recovery_only",
            "true_cflag": "-DNEZHA_TWRP_DISABLE_MINADBD=1", "default": "unset",
            "modules": ["minadbd", "libtwrpinstall"],
            "declaration_in_existing_target":
                "$(call soong_config_set_bool, nezha_twrp, native_recovery_only, true)",
        })
        # The error declarations and installer factory are outside the diff
        # context. Keep their reviewed source identities explicit; do not
        # pretend a hunk reconstructs the rest of either complete source file.
        evidence = row["source_evidence"]
        self.assertEqual(evidence["minadbd_error"], {
            "path": "minadbd/include/minadbd/types.h", "line": 35,
            "sha256": "3dd5a3de6e60d130b5c6c30df291abf812f0ee97cb15f92b7b7356fe85b886d6",
            "name": "kMinadbdUnsupportedCommandError", "value": 7,
        })
        self.assertEqual(evidence["installer_error"], {
            "path": "twrpinstall/include/twinstall/install.h", "line": 31,
            "sha256": "76cf95bb937d4200d3f538a9dc155dbdc913782f4a5f0b312d0a6f3f274a2d8b",
            "name": "INSTALL_ERROR", "value": 1,
        })
        self.assertEqual(evidence["installer_module"], {
            "path": "twrpinstall/Android.bp", "line": 52,
            "sha256": MINADBD_PREIMAGES["twrpinstall/Android.bp"][0],
            "type": "cc_library_static", "name": "libtwrpinstall",
        })
        self.assertIn("kMinadbdUnsupportedCommandError (7)", row["gate_contract"]["minadbd"])
        self.assertIn("Before GetProperty, SetUsbConfig, fork", row["gate_contract"]["twrp_sideload"])
        self.assertIn("INSTALL_ERROR (1)", row["gate_contract"]["twrp_sideload"])
        limits = " ".join(row["limits"])
        for statement in ("No Android compile", "No host keys", "No recovery image is authorized",
                          "not a general read-only recovery lock", "separate rescue launcher",
                          "verified as typed true", "not a runtime property toggle"):
            self.assertIn(statement, limits)

    def test_minadbd_flags_reject_wrong_types_defaults_namespaces_and_extra_edits(self):
        for path, section in self.minadbd_sections().items():
            if not path.endswith("Android.bp"):
                continue
            mutations = {
                "string Boolean": section.replace("+        true:", '+        "true":'),
                "other namespace": section.replace('"nezha_twrp"', '"other_product"'),
                "default enable": section.replace("+        default: unset,", '+        default: ["-DNEZHA_TWRP_DISABLE_MINADBD=1"],'),
                "inherited flags replaced": section.replace("+        default: unset,", "+        default: [],"),
                "wrong macro value": section.replace("DISABLE_MINADBD=1", "DISABLE_MINADBD=0"),
                "extra property": section.replace("+    }),\n", "+    }),\n+    required: [],\n"),
            }
            if path == "minadbd/Android.bp":
                mutations["different module"] = section.replace('name: "minadbd"', 'name: "minadbd_test"')
            else:
                mutations["remove AB OTA flag"] = section.replace('         "-DAB_OTA_UPDATER=1"\n', "")
            for label, mutated in mutations.items():
                with self.subTest(path=path, case=label), self.assertRaises(ValueError):
                    validate_minadbd_gate(mutated, path)

    def test_minadbd_guards_reject_delayed_successful_or_duplicate_returns(self):
        for path, guard, late_anchor, result in (
                ("minadbd/minadbd.cpp", MINADBD_DAEMON_GUARD,
                 "     exit(kMinadbdArgumentsParsingError);\n", "kMinadbdUnsupportedCommandError"),
                ("twrpinstall/adb_install.cpp", MINADBD_CALLER_GUARD,
                 '   std::string usb_state = android::base::GetProperty("sys.usb.state", "none");\n',
                 "INSTALL_ERROR")):
            section = self.minadbd_sections()[path]
            added_guard = "".join("+" + line for line in guard.splitlines(keepends=True))
            self.assertIn(late_anchor, section)
            mutations = {
                "successful return": section.replace("return " + result + ";", "return 0;"),
                "late gate": section.replace(added_guard, "", 1).replace(
                    late_anchor, late_anchor + added_guard, 1),
                "duplicate gate": section.replace(added_guard, added_guard * 2, 1),
                "wrapped old body": section.replace("+#endif\n", "+#else\n"),
                "USB mutation before return": section.replace("+  return ", '+  SetUsbConfig("none");\n+  return '),
            }
            for label, mutated in mutations.items():
                with self.subTest(path=path, case=label), self.assertRaises(ValueError):
                    validate_minadbd_gate(mutated, path)

    def test_patch_bytes_and_source_versions_are_hash_bound(self):
        # Independent transition checks: repeated paths need an explicit
        # immediate predecessor, while duplicate records inside a patch never
        # become a chain. The exact approved queue assertion remains separate.
        seen = {}
        for key, row in self.patches.items():
            with self.subTest(patch=key):
                raw = self.raw[key]
                self.assertTrue(raw.endswith(b"\n"))
                self.assertEqual(hashlib.sha256(raw).hexdigest(), row["patch_sha256"])
                self.assertEqual(self.text[key].count("diff --git "), len(row["files"]))
                seen_in_patch = set()
                for source in row["files"]:
                    identity = (row["project"], source["path"])
                    self.assertNotIn(identity, seen_in_patch)
                    seen_in_patch.add(identity)
                    if identity in seen:
                        previous_id, previous_row, previous_source, original = seen[identity]
                        self.assertEqual(source.get("predecessor_patch_id"), previous_id)
                        self.assertEqual(row["base_commit"], previous_row["base_commit"])
                        self.assertEqual(row.get("repository"), previous_row.get("repository"))
                        for component in ("sha256", "size_bytes", "git_blob"):
                            self.assertEqual(source["before_" + component], previous_source["after_" + component])
                        self.assertNotEqual(source["after_sha256"], original["before_sha256"])
                    else:
                        self.assertNotIn("predecessor_patch_id", source)
                        original = source
                    seen[identity] = (key, row, source, original)
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
                     "Patch 14 adds a reviewed fail-closed gate", "`-DNEZHA_TWRP_DISABLE_MINADBD=1`",
                     "`kMinadbdUnsupportedCommandError` (7)",
                     "`INSTALL_ERROR` before its first property read, USB change or fork",
                     "The `default: unset` branches preserve other products' flags",
                     "does not implement authenticated minadbd or add a host key",
                     "Before any diagnostic boot, verify both selected compiler flags and the compiled early returns"):
            self.assertIn(fact, minadbd_section)
        requirements = " ".join(self.record["application_requirements"])
        self.assertIn("never /work/evolution", requirements)
        self.assertIn("every preimage SHA256", requirements)
        self.assertIn("every postimage SHA256", requirements)


if __name__ == "__main__":
    unittest.main()
