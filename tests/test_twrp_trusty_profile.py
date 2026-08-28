"""Offline contracts for the two Trusty test architecture selectors.

Both tracked patches contain their complete original Blueprint files. Tests
reconstruct and seal the full preimages and postimages, including unrelated
production libraries, test fixtures, defaults and validation definitions.
The Boolean matrix describes the reviewed architecture override contract;
it does not execute Soong, prove dependency closure, or validate a recovery.
No ignored report, source checkout, subprocess, network or phone is needed.
"""

import hashlib
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from test_twrp_device import assignments, source_path_allowed
from test_twrp_patches import hunks, SOURCE_SNAPSHOT_SHA256


ROOT = Path(__file__).resolve().parents[1]
OLD_TWENTY_ONE = "8dba773d14062a7a4606e4a3f4ceabffb02e1aad437d4f168c2cd971816cb9af"
OLD_METADATA = "bfc07bb50df273b5b72af1b92a9d7f8b00741e2acb73192bbe7cde5d216b0f22"
HISTORICAL_SCOPE_COUNT = 173
HISTORICAL_SCOPES = "5296e6dcc35c038e0528b85ab19fb9ffb09a2604edd999f4d8f363b04882fb16"
SOONG_REVISION = "91bdc79cffb29d35b2d46a33204c061c3e7ed4f7"
SELECTOR = (
    '            enabled: select(soong_config_variable("nezha_twrp", "native_recovery_only"), {\n'
    '                true: false,\n'
    '                default: true,\n'
    '            }),\n'
)
ORIGINAL_ENABLE = "            enabled: true,\n"
TRUSTY_EXCLUSIONS = (
    "-packages/modules/Virtualization/guest/trusty/test_vm/Android.bp",
    "-packages/modules/Virtualization/guest/trusty/test_vm/vm/Android.bp",
    "-packages/modules/Virtualization/guest/trusty/test_vm_os/Android.bp",
    "-packages/modules/Virtualization/guest/trusty/test_vm_os/vm/Android.bp",
)
RETAINED_BLUEPRINTS = (
    "packages/modules/Virtualization/guest/pvmfw/avb/Android.bp",
    "test/vts-testcase/hal/treble/vintf/Android.bp",
    "packages/modules/Virtualization/guest/pvmfw/Android.bp",
    "packages/modules/Virtualization/guest/trusty/security_vm/Android.bp",
    "packages/modules/Virtualization/virtualizationmanager/Android.bp",
    "external/avb/Android.bp",
    "system/libvintf/Android.bp",
    "system/sepolicy/Android.bp",
    "system/sepolicy/tests/Android.bp",
    "build/soong/Android.bp",
)
CONTRACTS = (
    {
        "id": "0022-native-recovery-trusty-avb-test",
        "project": "packages/modules/Virtualization",
        "revision": "c984fc337c11ca5edc03ccf02037b2455dd8fcaf",
        "repository": "https://android.googlesource.com/platform/packages/modules/Virtualization",
        "entry_sha256": "17f8bfdb3aa6a2f45ff169faf9e1532c020a71e138d4c4f264d74e57861282ca",
        "patch_sha256": "409b9000671ce029298dd3f318afd6969758cc511799f80744bd63a9e1eb263c",
        "patch_size": 9039,
        "file": {
            "path": "guest/pvmfw/avb/Android.bp", "mode": "100644",
            "before_sha256": "1dc1eedbe30b6f6e8b8ae69399bcb3c67525a689565627b288b505d471612a77",
            "after_sha256": "41fd6eb66e6ef8f2583f399470f58877891b109fa4c9a24afca3c521145c8fc0",
            "before_git_blob": "0d55d7c48ffda774b4d27e2933ab44bbd5390160",
            "after_git_blob": "44c04413fe524b45983b871d95d5a05e0245ad9b",
            "before_size_bytes": 8109, "after_size_bytes": 8389,
        },
        "before_lines": 337, "after_lines": 343,
        "module_type": "rust_test", "module_name": "libpvmfw_avb.integration_test",
        "module_start": 24, "module_end": 76, "base_enabled_line": 66,
        "before_module_sha256": "0ac043b3c28f10473ca9b1a2c02b28402caef954f9d07a7b4d725bcf76e9f0d7",
        "after_module_sha256": "93e57c25ceea33d8a6ddffd476d2387b49cf37afd5e463bd65df4104eb4efa60",
        "overrides": ((70, "arm64"), (73, "x86_64")),
    },
    {
        "id": "0023-native-recovery-trusty-vintf-test",
        "project": "test/vts-testcase/hal",
        "revision": "9705f94b4d727578335a79e957bf839f273664b6",
        "repository": "https://android.googlesource.com/platform/test/vts-testcase/hal",
        "entry_sha256": "5de14c938faaf6a7805584844b86d48e4ac7fd2cdaf15ec96da73fd3dc50e33e",
        "patch_sha256": "b8344beffe45185ee4d601f4e819f7c2be5d40f2f87c1c87ef92c5e1862406a3",
        "patch_size": 4744,
        "file": {
            "path": "treble/vintf/Android.bp", "mode": "100644",
            "before_sha256": "e8225a141ca8cf6d8da0037569c24a32c5cace3b0091a6b08714c5172076d989",
            "after_sha256": "15427c057477fd54669beeeade52caa2166dc59e037622b932138890f73ee191",
            "before_git_blob": "1453bac3ab42c109dc8fc18f538f214ffa762943",
            "after_git_blob": "3311dfa09586e35212631d7a5417327c515df6f3",
            "before_size_bytes": 4170, "after_size_bytes": 4310,
        },
        "before_lines": 164, "after_lines": 167,
        "module_type": "cc_test", "module_name": "vts_treble_vintf_trusted_hal_test",
        "module_start": 89, "module_end": 119, "base_enabled_line": 113,
        "before_module_sha256": "e651691bac797115d857dbcfbb8762b7032a03d79cfc34f08efdbd04b02675f8",
        "after_module_sha256": "edbd3fe943c22c0dabe413eb4a45351bbc54994dbd9ab8bb77bc674bd1d1a7c3",
        "overrides": ((116, "arm64"),),
    },
)
BY_ID = {entry["id"]: entry for entry in CONTRACTS}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def canonical(value):
    return digest(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def expected_header(contract):
    file = contract["file"]
    path = file["path"]
    return (f"diff --git a/{path} b/{path}\n"
            f"index {file['before_git_blob']}..{file['after_git_blob']} 100644\n"
            f"--- a/{path}\n+++ b/{path}\n"
            f"@@ -1,{contract['before_lines']} +1,{contract['after_lines']} @@\n")


def validate_patch(raw, patch_id):
    """Reconstruct exact whole files; do not use a payload checksum gate."""
    if (not isinstance(raw, bytes) or not raw.endswith(b"\n")
            or b"\r" in raw or b"\0" in raw or len(raw) > 16384):
        raise ValueError("Expected bounded complete LF-terminated patch bytes")
    if patch_id not in BY_ID:
        raise ValueError("Unreviewed patch identity")
    contract = BY_ID[patch_id]
    text = raw.decode("utf-8")
    header = expected_header(contract)
    parsed = list(hunks(text))
    coordinates = (1, contract["before_lines"], 1, contract["after_lines"])
    if not text.startswith(header) or len(parsed) != 1 or parsed[0][:4] != coordinates:
        raise ValueError("Unreviewed file, Git identities, mode, or whole-file hunk")
    body = parsed[0][4]
    count = len(contract["overrides"])
    if (len(body) != contract["before_lines"] + 4 * count
            or any(line[:1] not in (" ", "+", "-") for line in body)):
        raise ValueError("Malformed hunk, unreviewed source changes, or extra section")
    before_lines = [line[1:] for line in body if line.startswith((" ", "-"))]
    after_lines = [line[1:] for line in body if line.startswith((" ", "+"))]
    if (len(before_lines), len(after_lines)) != (contract["before_lines"], contract["after_lines"]):
        raise ValueError("Incomplete file reconstruction")
    start, end = contract["module_start"] - 1, contract["module_end"]
    if (before_lines[start] != contract["module_type"] + " {\n"
            or before_lines[start + 1] != f'    name: "{contract["module_name"]}",\n'
            or before_lines[end - 1] != "}\n"
            or before_lines[contract["base_enabled_line"] - 1] != "    enabled: false,\n"):
        raise ValueError("The approved test and original top-level disable must remain")
    replacements = dict(contract["overrides"])
    expected_body = []
    for line_number, line in enumerate(before_lines, 1):
        if line_number in replacements:
            arch = replacements[line_number]
            if (not start < line_number < end or line != ORIGINAL_ENABLE
                    or before_lines[line_number - 2] != f"        {arch}: {{\n"):
                raise ValueError("Only the original approved architecture enables may change")
            expected_body.append("-" + line)
            expected_body.extend("+" + item for item in SELECTOR.splitlines(keepends=True))
        else:
            expected_body.append(" " + line)
    if body != expected_body or text != header + "".join(expected_body):
        raise ValueError("Only three architecture-specific Boolean replacements are allowed")
    before, after = "".join(before_lines), "".join(after_lines)
    if before_lines[:start] != after_lines[:start] or before_lines[end:] != after_lines[end + 3 * count:]:
        raise ValueError("Definitions outside the approved test changed")
    for stage, full, module in [
        ("before", before, "".join(before_lines[start:end])),
        ("after", after, "".join(after_lines[start:end + 3 * count])),
    ]:
        encoded = full.encode("utf-8")
        file = contract["file"]
        if (len(encoded) != file[stage + "_size_bytes"]
                or digest(encoded) != file[stage + "_sha256"]
                or git_blob(encoded) != file[stage + "_git_blob"]
                or digest(module.encode()) != contract[stage + "_module_sha256"]):
            raise ValueError("Unreviewed complete source file or test module bytes")
    return before, after


def expected_enabled(patch_id, arch, profile, *, patched, forced_disabled=False):
    """Controlled source expectation, not an implementation of Soong.

    Pinned module.go:288 marks Enabled arch_variant and replace_instead_of_append;
    the reviewed original architecture true overrides replace the base false.
    ModuleBase.Enabled:1439 honors ForcedDisabled first; depsMutator:478 guards
    both dependency mutators. These tests execute none of those Go functions.
    Inputs describe a hypothetical created architecture variant, not proof that
    either factory creates a variant on every listed architecture or host OS.
    """
    if patch_id not in BY_ID or not isinstance(arch, str) or not arch:
        raise ValueError("Expected a reviewed test and named architecture")
    if profile is not None and type(profile) is not bool:
        raise ValueError("Expected a typed Boolean or absent selector")
    if type(patched) is not bool or type(forced_disabled) is not bool:
        raise ValueError("Fixture switches must be Boolean")
    enabled_arches = {name for _, name in BY_ID[patch_id]["overrides"]}
    return not forced_disabled and arch in enabled_arches and not (patched and profile is True)


class TrustyProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.series = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        cls.rows = cls.series["patches"]
        cls.patches = {c["id"]: (ROOT / "patches/twrp" / (c["id"] + ".patch")).read_bytes()
                       for c in CONTRACTS}

    def test_first_twenty_one_records_and_nonpatch_metadata_remain_immutable(self):
        self.assertGreaterEqual(len(self.rows), 23)
        self.assertEqual(canonical(self.rows[:21]), OLD_TWENTY_ONE)
        self.assertEqual(canonical({k: v for k, v in self.series.items() if k != "patches"}), OLD_METADATA)

    def test_exact_two_new_records_and_existing_payloads_allow_future_appends(self):
        for row, contract in zip(self.rows[21:23], CONTRACTS):
            with self.subTest(patch=contract["id"]):
                self.assertEqual(row["id"], contract["id"])
                self.assertEqual(canonical(row), contract["entry_sha256"])
                self.assertEqual(row["patch"], "patches/twrp/" + contract["id"] + ".patch")
        for row in self.rows[:23]:
            with self.subTest(payload=row["id"]):
                path = ROOT / row["patch"]
                self.assertFalse(path.is_symlink())
                self.assertTrue(path.is_file())
                self.assertEqual(digest(path.read_bytes()), row["patch_sha256"])

    def test_source_owners_are_pinned_in_the_existing_source_inventories(self):
        raw = (ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml").read_bytes()
        self.assertEqual(digest(raw), SOURCE_SNAPSHOT_SHA256)
        projects = list(ET.fromstring(raw).iter("project"))
        supplements = json.loads((ROOT / "config/twrp-dependencies.json").read_bytes())["projects"]
        for row, contract in zip(self.rows[21:23], CONTRACTS):
            with self.subTest(project=contract["project"]):
                self.assertEqual((row["project"], row["base_commit"], row["repository"]),
                                 (contract["project"], contract["revision"], contract["repository"]))
                owners = [p.get("revision") for p in projects
                          if p.get("path", p.get("name")) == contract["project"]]
                owners += [p["commit"] for p in supplements if p["path"] == contract["project"]]
                self.assertEqual(owners, [contract["revision"]])
                self.assertEqual(row["files"][0]["source_url"],
                                 f"{contract['repository']}/+/{contract['revision']}/{contract['file']['path']}")
        self.assertEqual([p.get("revision") for p in projects if p.get("path") == "build/soong"],
                         [SOONG_REVISION])

    def test_both_files_are_fresh_and_all_full_file_identities_are_sealed(self):
        previous = {(row["project"], file["path"]) for row in self.rows[:21] for file in row["files"]}
        for row, contract in zip(self.rows[21:23], CONTRACTS):
            with self.subTest(patch=contract["id"]):
                self.assertEqual(len(row["files"]), 1)
                self.assertEqual({k: row["files"][0][k] for k in contract["file"]}, contract["file"])
                self.assertNotIn((row["project"], contract["file"]["path"]), previous)
                self.assertNotIn("predecessor_patch_id", row["files"][0])
                self.assertEqual(contract["file"]["after_size_bytes"] - contract["file"]["before_size_bytes"],
                                 140 * len(contract["overrides"]))

    def test_payloads_reconstruct_both_complete_blueprint_preimages_and_postimages(self):
        for row, contract in zip(self.rows[21:23], CONTRACTS):
            with self.subTest(patch=contract["id"]):
                raw = self.patches[contract["id"]]
                self.assertEqual((len(raw), digest(raw)), (contract["patch_size"], contract["patch_sha256"]))
                self.assertEqual(row["patch_sha256"], contract["patch_sha256"])
                before, after = validate_patch(raw, contract["id"])
                self.assertEqual((len(before.splitlines()), len(after.splitlines())),
                                 (contract["before_lines"], contract["after_lines"]))
                self.assertEqual(raw.count(b"diff --git "), 1)
                self.assertEqual(len(SELECTOR.encode()) - len(ORIGINAL_ENABLE.encode()), 140)

    def test_architecture_metadata_matches_the_three_boolean_replacements(self):
        self.assertEqual(sum(len(c["overrides"]) for c in CONTRACTS), 3)
        for row, contract in zip(self.rows[21:23], CONTRACTS):
            with self.subTest(patch=contract["id"]):
                metadata = {
                    "type": contract["module_type"], "name": contract["module_name"],
                    "constructor_line": contract["module_start"],
                    "before_module_sha256": contract["before_module_sha256"],
                    "after_module_sha256": contract["after_module_sha256"],
                    "base_enabled_before": False, "base_enabled_after": False,
                    "architecture_enabled_overrides": [
                        {"arch": arch, "enabled_before": True, "enabled_when_true": False, "enabled_otherwise": True}
                        for _, arch in contract["overrides"]
                    ],
                    "selector_namespace": "nezha_twrp", "selector_variable": "native_recovery_only",
                    "selector_type": "bool",
                }
                self.assertEqual(row["files"][0]["profile_arch_test_modules"], [metadata])
                self.assertNotIn("profile_modules", row["files"][0])
                self.assertNotIn("profile_image_modules", row["files"][0])

    def test_only_the_named_test_changes_and_its_base_disable_is_preserved(self):
        for contract in CONTRACTS:
            with self.subTest(test=contract["module_name"]):
                before, after = validate_patch(self.patches[contract["id"]], contract["id"])
                count = len(contract["overrides"])
                self.assertNotIn("soong_config_variable", before)
                self.assertEqual(after.count(SELECTOR), count)
                self.assertEqual(after.replace(SELECTOR, ORIGINAL_ENABLE), before)
                self.assertEqual(before.count("    enabled: false,\n"), after.count("    enabled: false,\n"))
                before_lines, after_lines = before.splitlines(keepends=True), after.splitlines(keepends=True)
                start, end = contract["module_start"] - 1, contract["module_end"]
                self.assertEqual(before_lines[:start], after_lines[:start])
                self.assertEqual(before_lines[end:], after_lines[end + 3 * count:])

    def test_production_avb_library_signing_and_rollback_fixtures_remain_identical(self):
        contract = CONTRACTS[0]
        before, after = validate_patch(self.patches[contract["id"]], contract["id"])
        self.assertEqual(before.splitlines()[:23], after.splitlines()[:23])
        self.assertEqual(before.splitlines()[76:], after.splitlines()[82:])
        for property in ['name: "libpvmfw_avb_nostd"', 'srcs: ["src/lib.rs"]',
                         '"libavb_baremetal"', '"libavb_rs_nostd"', '"libtinyvec_nostd"',
                         'tools: ["avbtool"]', 'private_key: ":pvmfw_sign_key"',
                         "rollback_index: 5", 'name: "test_image_with_all_capabilities"']:
            with self.subTest(property=property):
                self.assertEqual(before.count(property), after.count(property))
                self.assertGreater(before.count(property), 0)
        self.assertIn('        ":trusty_test_vm_signed_bin",\n', after)

    def test_general_vintf_tests_defaults_aidl_and_security_dependencies_remain_identical(self):
        contract = CONTRACTS[1]
        before, after = validate_patch(self.patches[contract["id"]], contract["id"])
        self.assertEqual(before.splitlines()[:88], after.splitlines()[:88])
        self.assertEqual(before.splitlines()[119:], after.splitlines()[122:])
        for name in ["vts_treble_vintf_test_defaults", "libvintf_service_info_aidl",
                     "vts_treble_vintf_vendor_test", "vts_treble_no_hidl",
                     "vts_treble_vintf_framework_test", "vts_treble_vintf_test_all"]:
            with self.subTest(module=name):
                self.assertEqual(before.count(f'name: "{name}"'), 1)
                self.assertEqual(after.count(f'name: "{name}"'), 1)
        for property in ['"libselinux"', '"libvintf"', '"-Werror"', '"-DTRUSTED_HAL_TEST"',
                         '"DeviceManifestTest.cpp"', '"DeviceMatrixTest.cpp"', '"SingleManifestTest.cpp"',
                         '":trusty_test_vm_elf"', '":trusty_test_vm_config"', '":trusty-ut-ctrl.system"']:
            with self.subTest(property=property):
                self.assertEqual(before.count(property), after.count(property))
                self.assertGreater(before.count(property), 0)

    def test_scope_keeps_mixed_provider_files_and_only_adds_four_exact_test_paths(self):
        text = (ROOT / "recovery/twrp/device/xiaomi/nezha/device.mk").read_text()
        scopes = assignments(text)["PRODUCT_SOURCE_ROOT_DIRS"].split()
        self.assertGreaterEqual(len(scopes), HISTORICAL_SCOPE_COUNT + 4)
        self.assertEqual(canonical(scopes[:HISTORICAL_SCOPE_COUNT]), HISTORICAL_SCOPES)
        self.assertEqual(tuple(scopes[173:177]), TRUSTY_EXCLUSIONS)
        for excluded in TRUSTY_EXCLUSIONS:
            with self.subTest(excluded=excluded):
                self.assertFalse(excluded.endswith("/"))
                self.assertEqual(scopes.count(excluded), 1)
                self.assertTrue(source_path_allowed(excluded[1:], scopes[:173]))
                self.assertFalse(source_path_allowed(excluded[1:], scopes))
        for retained in RETAINED_BLUEPRINTS:
            with self.subTest(retained=retained):
                self.assertTrue(source_path_allowed(retained, scopes))
        board = (ROOT / "recovery/twrp/device/xiaomi/nezha/BoardConfig.mk").read_text()
        self.assertEqual(board.count("$(call soong_config_set_bool, nezha_twrp, native_recovery_only, true)"), 1)

    def test_controlled_true_false_absence_matrix_preserves_other_architectures(self):
        for contract in CONTRACTS:
            validate_patch(self.patches[contract["id"]], contract["id"])
            enabled_arches = {arch for _, arch in contract["overrides"]}
            for arch in ["arm64", "x86_64", "arm", "x86", "riscv64", "common"]:
                for profile in [True, False, None]:
                    for forced in [False, True]:
                        with self.subTest(test=contract["module_name"], arch=arch, profile=profile, forced=forced):
                            original = arch in enabled_arches and not forced
                            self.assertIs(expected_enabled(contract["id"], arch, profile,
                                                           patched=False, forced_disabled=forced), original)
                            self.assertIs(expected_enabled(contract["id"], arch, profile,
                                                           patched=True, forced_disabled=forced),
                                          original and profile is not True)

    def test_controlled_matrix_rejects_untyped_values_and_unknown_tests(self):
        patch_id = CONTRACTS[0]["id"]
        for value in ["true", "false", 0, 1, [], {}, object()]:
            with self.subTest(profile=value), self.assertRaises(ValueError):
                expected_enabled(patch_id, "arm64", value, patched=True)
        for kwargs in [{"patched": "true"}, {"patched": 1}, {"patched": True, "forced_disabled": 1}]:
            with self.subTest(switches=kwargs), self.assertRaises(ValueError):
                expected_enabled(patch_id, "arm64", None, **kwargs)
        for unknown, arch in [("unknown", "arm64"), (patch_id, ""), (patch_id, 64)]:
            with self.subTest(identity=unknown, arch=arch), self.assertRaises(ValueError):
                expected_enabled(unknown, arch, None, patched=True)

    def test_selector_architecture_and_base_property_mutations_are_rejected(self):
        selector = "".join("+" + line for line in SELECTOR.splitlines(keepends=True)).encode()
        for contract in CONTRACTS:
            raw = self.patches[contract["id"]]
            mutations = {
                "wrong_namespace": raw.replace(b'"nezha_twrp"', b'"other_product"', 1),
                "wrong_variable": raw.replace(b'"native_recovery_only"', b'"all_modules"', 1),
                "wrong_condition": raw.replace(b"+                true: false,", b"+                false: false,", 1),
                "true_enabled": raw.replace(b"+                true: false,", b"+                true: true,", 1),
                "default_false": raw.replace(b"+                default: true,", b"+                default: false,", 1),
                "default_unset": raw.replace(b"+                default: true,", b"+                default: unset,", 1),
                "default_string": raw.replace(b"+                default: true,", b'+                default: "true",', 1),
                "unconditional_disable": raw.replace(selector, b"+            enabled: false,\n", 1),
                "duplicate_enable": raw.replace(selector, selector + b"+            enabled: true,\n", 1),
                "base_enable_changed": raw.replace(b"     enabled: false,\n", b"     enabled: true,\n", 1),
                "base_disable_removed": raw.replace(b"     enabled: false,\n", b"-    enabled: false,\n", 1),
                "wrong_architecture": raw.replace(b"         arm64: {", b"         arm: {", 1),
                "changed_original_override": raw.replace(b"-            enabled: true,", b"-            enabled: false,", 1),
                "different_test": raw.replace(contract["module_name"].encode(), b"replacement_test", 1),
                "fake_stub_type": raw.replace((" " + contract["module_type"] + " {\n").encode(), b" filegroup {\n", 1),
                "bypass_property": raw.replace(selector, selector + b"+            skip_checks: true,\n", 1),
            }
            replacement = ("-" + ORIGINAL_ENABLE).encode() + selector
            for _, arch in contract["overrides"]:
                anchor = f"         {arch}: {{\n".encode()
                original = anchor + replacement
                self.assertIn(original, raw)
                mutations[f"only_{arch}_unconditional"] = raw.replace(
                    original, anchor + (" " + ORIGINAL_ENABLE).encode(), 1)
                mutations[f"only_{arch}_wrong_namespace"] = raw.replace(
                    original, original.replace(b'"nezha_twrp"', b'"other_product"'), 1)
            for name, changed in mutations.items():
                with self.subTest(patch=contract["id"], mutation=name):
                    self.assertNotEqual(changed, raw)
                    with self.assertRaises(ValueError):
                        validate_patch(changed, contract["id"])

    def test_production_source_fixture_and_validator_mutations_are_rejected(self):
        for contract, changes in [
            (CONTRACTS[0], [
                (b'name: "libpvmfw_avb_nostd"', b'name: "libpvmfw_avb_stub"'),
                (b'srcs: ["src/lib.rs"]', b'srcs: ["stub.rs"]'),
                (b'"libavb_baremetal"', b'"fake_avb"'),
                (b'"libavb_rs_nostd"', b'"fake_validator"'),
                (b'private_key: ":pvmfw_sign_key"', b'private_key: ":unreviewed_key"'),
                (b'rollback_index: 5', b'rollback_index: 0'),
                (b'":trusty_test_vm_signed_bin"', b'":unsigned_test_image"'),
                (b'value: "remote_attest|secretkeeper_protection"', b'value: "none"'),
            ]),
            (CONTRACTS[1], [
                (b'name: "vts_treble_vintf_vendor_test"', b'name: "vts_stub"'),
                (b'name: "vts_treble_vintf_test_defaults"', b'name: "empty_defaults"'),
                (b'"DeviceManifestTest.cpp"', b'"SkippedManifestTest.cpp"'),
                (b'"DeviceMatrixTest.cpp"', b'"SkippedMatrixTest.cpp"'),
                (b'"libselinux"', b'"fake_selinux"'),
                (b'"libvintf"', b'"fake_vintf"'),
                (b'"-Werror"', b'"-w"'),
                (b'":trusty_test_vm_elf"', b'":fake_trusty_elf"'),
                (b'default_team: "trendy_team_android_kernel"', b'default_team: "other_team"'),
            ]),
        ]:
            raw = self.patches[contract["id"]]
            for old, new in changes:
                with self.subTest(patch=contract["id"], property=old):
                    changed = raw.replace(old, new, 1)
                    self.assertNotEqual(changed, raw)
                    with self.assertRaises(ValueError):
                        validate_patch(changed, contract["id"])

    def test_malformed_envelopes_and_unrelated_file_edits_are_rejected(self):
        for contract in CONTRACTS:
            raw = self.patches[contract["id"]]
            file = contract["file"]
            mutations = {
                "old_path": raw.replace(("--- a/" + file["path"]).encode(), b"--- a/other.bp", 1),
                "new_path": raw.replace(("+++ b/" + file["path"]).encode(), b"+++ b/other.bp", 1),
                "mode": raw.replace(b" 100644\n", b" 100755\n", 1),
                "short_old_blob": raw.replace(file["before_git_blob"].encode(), file["before_git_blob"][:12].encode(), 1),
                "short_new_blob": raw.replace(file["after_git_blob"].encode(), file["after_git_blob"][:12].encode(), 1),
                "old_start": raw.replace(b"@@ -1,", b"@@ -2,", 1),
                "new_count": raw.replace(f"+1,{contract['after_lines']} @@".encode(), b"+1,1 @@", 1),
                "preamble": b"unreviewed preamble\n" + raw,
                "trailer": raw + b"GIT binary patch\n",
                "extra_validator": raw + b"diff --git a/build/soong/check.go b/build/soong/check.go\n",
                "extra_sepolicy": raw + b"diff --git a/system/sepolicy/Android.bp b/system/sepolicy/Android.bp\n",
                "extra_fuzzer_registry": raw + b"diff --git a/service_fuzzer_bindings.go b/service_fuzzer_bindings.go\n",
                "second_patch": raw + raw,
                "no_final_lf": raw[:-1],
                "crlf": raw.replace(b"\n", b"\r\n"),
                "nul": raw.replace(b"true: false", b"true:\0false", 1),
                "invalid_utf8": raw.replace(b"true: false", b"true:\xfffalse", 1),
                "not_bytes": raw.decode(),
            }
            for name, changed in mutations.items():
                with self.subTest(patch=contract["id"], mutation=name), self.assertRaises(ValueError):
                    validate_patch(changed, contract["id"])


if __name__ == "__main__":
    unittest.main()
