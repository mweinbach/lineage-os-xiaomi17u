"""Offline source-contract tests; no Make, image, signer, guest or phone is run."""

import ast
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
PATCH_PATH = "patches/evolution/0005-verified-prebuilt-recovery.patch"
RECORD_PATH = "patches/evolution/prebuilt-recovery.json"
BASE_SHA256 = "c88f2df44f4210243cdccce6cfeffc156d778aab00a7d7108777b9217b70146e"
AFTER_SHA256 = "61a40da9741cae2119263ca0a92cd717874a88320e28fb0ee67505bed6829d31"
COMMON_SHA256 = "78b74437cb9916eda2b25ac4c8afd13b50847648f10c2e4fd66df0e02ab90bc2"

# Exact source excerpt from the pinned build/make/tools/releasetools/common.py,
# lines 1961-1978. It is parsed as text, never imported or executed.
BOOTABLE_IMAGE_EXCERPT = '''  prebuilt_path = os.path.join(unpack_dir, "BOOTABLE_IMAGES", prebuilt_name)
  if os.path.exists(prebuilt_path):
    logger.info("using prebuilt %s from BOOTABLE_IMAGES...", prebuilt_name)
    return File.FromLocalFile(name, prebuilt_path)

  prebuilt_path = os.path.join(unpack_dir, "IMAGES", prebuilt_name)
  if os.path.exists(prebuilt_path):
    logger.info("using prebuilt %s from IMAGES...", prebuilt_name)
    return File.FromLocalFile(name, prebuilt_path)

  partition_name = tree_subdir.lower()
  prebuilt_path = os.path.join(unpack_dir, "PREBUILT_IMAGES", prebuilt_name)
  if os.path.exists(prebuilt_path):
    logger.info("Re-signing prebuilt %s from PREBUILT_IMAGES...", prebuilt_name)
    signed_img = MakeTempFile()
    shutil.copy(prebuilt_path, signed_img)
    _SignBootableImage(signed_img, prebuilt_name, partition_name, info_dict)
    return File.FromLocalFile(name, signed_img)
'''


def _hunks(patch):
    """Read the one-file unified patch with bounded, exact hunk counts."""
    if len(patch) > 20000 or not patch.endswith("\n"):
        raise ValueError("invalid patch envelope")
    header = ("diff --git a/core/Makefile b/core/Makefile\n"
              r"index [0-9a-f]{40}\.\.[0-9a-f]{40} 100644" "\n"
              r"--- a/core/Makefile" "\n" r"\+\+\+ b/core/Makefile" "\n")
    match = re.match(header, patch)
    if match is None:
        raise ValueError("unexpected patch file")
    chunks = re.split(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@[^\n]*\n",
                      patch[match.end():], flags=re.M)
    if chunks[0] or len(chunks) == 1 or (len(chunks) - 1) % 5:
        raise ValueError("invalid hunk headers")
    result = []
    for index in range(1, len(chunks), 5):
        old_start, old_count, new_start, new_count = map(int, chunks[index:index + 4])
        body = chunks[index + 4].splitlines(keepends=True)
        if not all(line.startswith((" ", "+", "-")) and line.endswith("\n")
                   for line in body):
            raise ValueError("invalid hunk body")
        old = [line[1:] for line in body if line.startswith((" ", "-"))]
        new = [line[1:] for line in body if line.startswith((" ", "+"))]
        if len(old) != old_count or len(new) != new_count:
            raise ValueError("hunk count mismatch")
        result.append((old_start, new_start, old, new, body))
    return result


def _apply(source, hunks):
    """Apply only exact text contexts, without git, patch or native processes."""
    source_lines = source.splitlines(keepends=True)
    result = []
    cursor = 0
    for old_start, new_start, old, new, _ in hunks:
        if old_start - 1 < cursor:
            raise ValueError("overlapping hunks")
        result.extend(source_lines[cursor:old_start - 1])
        if len(result) != new_start - 1:
            raise ValueError("new hunk position mismatch")
        if source_lines[old_start - 1:old_start - 1 + len(old)] != old:
            raise ValueError("source context mismatch")
        result.extend(new)
        cursor = old_start - 1 + len(old)
    return "".join(result + source_lines[cursor:])


def _fixture(hunks):
    """Surround exact patch contexts with synthetic unrelated source lines."""
    final = hunks[-1][0] + len(hunks[-1][2]) + 4
    lines = [f"# synthetic untouched source line {number}\n"
             for number in range(1, final)]
    for old_start, _, old, _, _ in hunks:
        lines[old_start - 1:old_start - 1 + len(old)] = old
    return "".join(lines)


def _project_added_selectors(hunks, selected):
    """Project only NEW selector conditionals; this is not a Make evaluator.

    Existing source lines are opaque. Only added conditional directives change
    the projection, so intervening untouched source is not needed as a fixture.
    """
    frames = []
    result = []
    for _, _, _, _, body in hunks:
        for line in body:
            if line.startswith("-"):
                continue
            text = line[1:]
            directive = text.strip()
            active = all(frame[1] for frame in frames)
            if line.startswith("+"):
                if directive in ("ifdef TARGET_PREBUILT_RECOVERY",
                                 "ifndef TARGET_PREBUILT_RECOVERY"):
                    frames.append(("selector", selected == directive.startswith("ifdef")))
                    continue
                if re.match(r"^(ifdef|ifndef|ifeq|ifneq)\b", directive):
                    frames.append(("opaque", True))
                elif directive.startswith("endif"):
                    kind, _ = frames.pop()
                    if kind == "selector":
                        continue
                elif directive == "else":
                    kind, enabled = frames[-1]
                    if kind == "selector":
                        frames[-1] = (kind, not enabled)
                        continue
            if active:
                result.append(text)
    if frames:
        raise ValueError("unclosed added selector")
    return "".join(result)


class PrebuiltRecoveryPatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads((ROOT / RECORD_PATH).read_text())
        cls.raw = (ROOT / PATCH_PATH).read_bytes()
        cls.patch = cls.raw.decode("utf-8")
        cls.hunks = _hunks(cls.patch)
        cls.added = "".join(line[1:] for hunk in cls.hunks for line in hunk[4]
                            if line.startswith("+"))
        cls.selected = _project_added_selectors(cls.hunks, True)

    def test_exact_patch_and_source_identities_are_bound(self):
        self.assertEqual(self.record["schema_version"], 1)
        self.assertEqual(self.record["project"], {
            "path": "build/make",
            "commit": "a438ca40c6ed779042f806142b1165ba1360a7b2",
            "repository": "https://github.com/Evolution-X/build",
            "branch": "bka",
        })
        self.assertEqual(self.record["patch"], {
            "path": PATCH_PATH, "sha256": hashlib.sha256(self.raw).hexdigest(),
            "size_bytes": len(self.raw),
        })
        self.assertEqual(self.record["source_files"], [{
            "path": "build/make/core/Makefile",
            "before": {"sha256": BASE_SHA256, "size_bytes": 378285},
            "after": {"sha256": AFTER_SHA256, "size_bytes": 382008},
        }])
        self.assertEqual(self.record["semantic_files"][0], {
            "path": "build/make/tools/releasetools/common.py",
            "sha256": COMMON_SHA256, "size_bytes": 156263,
        })

    def test_hunks_have_consistent_positions_counts_and_size_delta(self):
        self.assertEqual(len(self.hunks), 11)
        self.assertEqual(self.patch.count("diff --git "), 1)
        line_delta = 0
        byte_delta = 0
        previous_end = 0
        for old_start, new_start, old, new, _ in self.hunks:
            self.assertGreaterEqual(old_start, previous_end)
            self.assertEqual(new_start, old_start + line_delta)
            previous_end = old_start + len(old)
            line_delta += len(new) - len(old)
            byte_delta += len("".join(new).encode()) - len("".join(old).encode())
        row = self.record["source_files"][0]
        self.assertEqual(row["before"]["size_bytes"] + byte_delta,
                         row["after"]["size_bytes"])
        removed = [line[1:] for hunk in self.hunks for line in hunk[4]
                   if line.startswith("-")]
        self.assertEqual(removed, [])

    def test_patch_applies_to_synthetic_contexts_without_touching_other_lines(self):
        source = _fixture(self.hunks)
        result = _apply(source, self.hunks)
        self.assertNotEqual(source, result)
        self.assertEqual(result.count("# synthetic untouched source line "),
                         source.count("# synthetic untouched source line "))
        self.assertEqual([line for line in source.splitlines() if line.startswith("# synthetic")],
                         [line for line in result.splitlines() if line.startswith("# synthetic")])
        self.assertIn("define copy-verified-prebuilt-recovery\n", result)
        self.assertIn("$(zip_root)/BOOTABLE_IMAGES/recovery.img", result)

    def test_malformed_or_mismatched_patch_context_is_rejected(self):
        source = _fixture(self.hunks)
        with self.assertRaisesRegex(ValueError, "source context"):
            _apply(source.replace("# Recovery image\n", "# different source\n", 1), self.hunks)
        for broken in (
            self.patch.replace("@@ -2421,6 +2421,31 @@", "@@ -2421,7 +2421,31 @@", 1),
            self.patch.replace("a/core/Makefile b/core/Makefile", "a/core/main.mk b/core/main.mk", 1),
            self.patch[:-1],
            self.patch + "unexpected trailer\n",
        ):
            with self.subTest(broken=broken[:80]), self.assertRaises(ValueError):
                _hunks(broken)
        wrong_offset = self.patch.replace("@@ -2421,6 +2421,31 @@", "@@ -2421,6 +2422,31 @@", 1)
        with self.assertRaisesRegex(ValueError, "position"):
            _apply(source, _hunks(wrong_offset))

    def test_unselected_branch_preserves_all_original_nonblank_source(self):
        before = "".join("".join(hunk[2]) for hunk in self.hunks)
        projected = _project_added_selectors(self.hunks, False)
        self.assertEqual([line for line in projected.splitlines() if line.strip()],
                         [line for line in before.splitlines() if line.strip()])
        self.assertNotIn("TARGET_PREBUILT_RECOVERY", projected)
        self.assertIn("$(call build-recoveryimage-target, $@,", projected)
        self.assertIn("$(call build-recoveryimage-target, $(INSTALLED_RECOVERYIMAGE_TARGET),", projected)

    def test_selector_requires_dedicated_recovery_topology_and_avb(self):
        guards = self.hunks[0][3]
        text = "".join(guards)
        self.assertLess(text.index("ifdef TARGET_PREBUILT_RECOVERY"),
                        text.index("ifdef BUILDING_RECOVERY_IMAGE"))
        for required in (
            "BUILDING_RECOVERY_IMAGE=true", "INSTALLED_RECOVERYIMAGE_TARGET",
            "TARGET_PREBUILT_RECOVERY_SHA256", "BOARD_RECOVERYIMAGE_PARTITION_SIZE",
            "BOARD_AVB_ENABLE=true", "requires a dedicated recovery partition",
            "cannot use custom boot image rules",
        ):
            self.assertIn("$(error TARGET_PREBUILT_RECOVERY " +
                          (required if required.startswith(("requires", "cannot")) else "requires " + required)
                          + ")", text)
        for incompatible in (
            "BOARD_USES_RECOVERY_AS_BOOT", "BOARD_MOVE_RECOVERY_RESOURCES_TO_VENDOR_BOOT",
            "BOARD_INCLUDE_RECOVERY_RAMDISK_IN_VENDOR_BOOT", "BOARD_CUSTOM_BOOTIMG_MK",
            "BOARD_CUSTOM_BOOTIMG",
        ):
            self.assertIn("$(" + incompatible + ")", text)

    def test_copy_checks_input_temporary_and_final_bytes_before_accepting(self):
        macro = self.added.split("define copy-verified-prebuilt-recovery\n", 1)[1].split("\nendef", 1)[0]
        self.assertIn("$(hide) set -eu;", macro)
        self.assertIn('test "$${#recovery_sha}" -eq 64;', macro)
        self.assertIn('case "$$recovery_sha" in *[!0-9a-f]*) exit 1;; esac;', macro)
        self.assertIn('case "$$recovery_size" in \'\'|*[!0-9]*) exit 1;; esac;', macro)
        self.assertIn('test "$$recovery_size" -gt 0;', macro)
        self.assertIn('test -f "$$recovery_src"; test ! -L "$$recovery_src";', macro)
        self.assertIn('test ! -L "$$recovery_dst"; test ! -d "$$recovery_dst";', macro)
        stages = []
        for name in ("src", "tmp", "dst"):
            size = f'test "$$(wc -c < "$$recovery_{name}")" -eq "$$recovery_size"'
            digest = f'test "$$(sha256sum < "$$recovery_{name}" | cut -d \' \' -f 1)" = "$$recovery_sha"'
            self.assertIn(size, macro)
            self.assertIn(digest, macro)
            self.assertLess(macro.index(size), macro.index(digest))
            stages.append(macro.index(digest))
        copy = macro.index('cp -f "$$recovery_src" "$$recovery_tmp"')
        rename = macro.index('mv -f "$$recovery_tmp" "$$recovery_dst"')
        self.assertEqual(sorted([stages[0], copy, stages[1], rename, stages[2]]),
                         [stages[0], copy, stages[1], rename, stages[2]])
        self.assertIn('mktemp "$$recovery_dst.tmp.XXXXXX"', macro)
        self.assertIn("trap 'rm -f \"$$recovery_tmp\"' EXIT;", macro)
        for forbidden in ("MKBOOTIMG", "AVBTOOL", "add_hash_footer", "--flags",
                          "--disable-verity", "--disable-verification", "chmod", "truncate"):
            self.assertNotIn(forbidden, macro)

    def test_real_output_has_normal_dependencies_and_both_entrypoints_always_copy(self):
        self.assertIn("recoveryimage-deps := $(TARGET_PREBUILT_RECOVERY)\n", self.selected)
        prerequisites = re.findall(
            r"^\$\(INSTALLED_RECOVERYIMAGE_TARGET\): ([^\n]+)$", self.selected, flags=re.M)
        self.assertEqual(prerequisites, ["$(recoveryimage-deps)"])
        self.assertIn("$(call copy-verified-prebuilt-recovery,$(TARGET_PREBUILT_RECOVERY),$@)", self.selected)
        entrypoint_copy = ("\t$(call copy-verified-prebuilt-recovery,$(TARGET_PREBUILT_RECOVERY),"
                           "$(INSTALLED_RECOVERYIMAGE_TARGET))\n")
        nodeps = self.selected.split("recoveryimage-nodeps:\n", 1)[1].split("\n\n", 1)[0]
        recovery = self.selected.split(
            "recoveryimage: $(INSTALLED_RECOVERYIMAGE_TARGET) $(RECOVERY_RESOURCE_ZIP)\n", 1)[1]
        recovery = recovery.split("\n\n", 1)[0]
        self.assertEqual(nodeps, entrypoint_copy.rstrip("\n"))
        self.assertTrue(recovery.endswith(entrypoint_copy.rstrip("\n")))
        self.assertEqual(self.selected.count(entrypoint_copy), 2)
        self.assertIn(".PHONY: recoveryimage\n", self.selected)
        self.assertIn(".PHONY: recoveryimage-nodeps\n", self.selected)
        self.assertNotIn("$(call build-recoveryimage-target", self.selected)
        self.assertNotIn("ignoring dependencies", nodeps)

    def test_revalidation_does_not_disable_kati_checks_or_use_a_force_prerequisite(self):
        for forbidden in ("FORCE", ".KATI_ALLOW_PHONY_FILE", "KATI_ALLOW_PHONY", "--werror",
                          ".PHONY: $(INSTALLED_RECOVERYIMAGE_TARGET)"):
            self.assertNotIn(forbidden, self.added)
        self.assertEqual(self.record["semantics"]["selected_target_always_rechecks_bytes"], False)
        self.assertIs(self.record["semantics"]["real_output_has_phony_prerequisites"], False)
        self.assertIs(self.record["semantics"]["recoveryimage_always_uses_verified_copy"], True)
        self.assertIs(self.record["semantics"]["recoveryimage_nodeps_uses_verified_copy"], True)

    def test_selected_target_files_uses_unchanged_bytes_without_fake_recovery_tree(self):
        self.assertIn("$(call copy-verified-prebuilt-recovery,$(INSTALLED_RECOVERYIMAGE_TARGET),$(zip_root)/BOOTABLE_IMAGES/recovery.img)", self.selected)
        for absent in ("$(PRIVATE_RECOVERY_OUT)", "$(INTERNAL_RECOVERYIMAGE_FILES)",
                       "$(zip_root)/RECOVERY/RAMDISK", "recovery_filesystem_config.txt"):
            self.assertNotIn(absent, self.selected)
        self.assertIn("RECOVERY_RESOURCE_ZIP :=\n", self.selected)
        self.assertNotIn("PREBUILT_IMAGES/recovery.img", self.patch)
        self.assertNotIn("recovery-two-step.img", self.added)

    def test_pinned_releasetools_excerpt_distinguishes_copy_from_resigning(self):
        body = ast.parse("def fixture():\n" + BOOTABLE_IMAGE_EXCERPT).body[0].body
        paths = [node.value.args[1].value for node in body if isinstance(node, ast.Assign)
                 and isinstance(node.value, ast.Call)
                 and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == "join"]
        self.assertEqual(paths, ["BOOTABLE_IMAGES", "IMAGES", "PREBUILT_IMAGES"])
        branches = [node for node in body if isinstance(node, ast.If)]
        self.assertEqual(len(branches), 3)
        for branch in branches[:2]:
            self.assertEqual(len(branch.body), 2)
            self.assertIsInstance(branch.body[-1], ast.Return)
            self.assertEqual(ast.unparse(branch.body[-1].value),
                             "File.FromLocalFile(name, prebuilt_path)")
        calls = [node.func.id for node in ast.walk(branches[2])
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)]
        self.assertIn("_SignBootableImage", calls)
        anchors = self.record["source_anchors"]
        self.assertEqual([row["line"] for row in anchors if row["path"].endswith("common.py")],
                         [1961, 1972])

    def test_metadata_does_not_claim_runtime_build_ota_or_trust_validation(self):
        semantics = self.record["semantics"]
        self.assertEqual(semantics["partition_size_rule"], "exact")
        self.assertEqual(semantics["target_files_location"], "BOOTABLE_IMAGES/recovery.img")
        for key in ("prebuilt_recovery_resigned", "generated_recovery_ramdisk_metadata_used",
                    "normal_boot_rules_changed", "normal_init_boot_rules_changed",
                    "normal_vendor_boot_rules_changed", "normal_avb_rules_changed"):
            self.assertIs(semantics[key], False)
        self.assertIs(self.record["validation_scope"]["offline_source_contract_tests_only"], True)
        for key, value in self.record["validation_scope"].items():
            if key != "offline_source_contract_tests_only":
                self.assertIs(value, False)
        limits = " ".join(self.record["limitations"])
        for required in ("does not attest the entire current source checkout",
                         "not an AVB signature or key trust verifier",
                         "does not validate generated misc_info as TWRP metadata",
                         "Full target-files, OTA and super build goals remain denied",
                         "recovery-two-step.img", "unsupported and remains denied",
                         "Direct raw file targets alone do not promise unconditional revalidation"):
            self.assertIn(required, limits)
        serialized = json.dumps(self.record)
        for private in ("/Users/", "/work/", "BEGIN PRIVATE KEY", "serial"):
            self.assertNotIn(private, serialized)

    def test_fixture_and_patch_analysis_need_no_native_process_network_or_device(self):
        with ExitStack() as stack:
            for target in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError(target)))
            hunks = _hunks(self.patch)
            self.assertIn("BOOTABLE_IMAGES/recovery.img", _apply(_fixture(hunks), hunks))
            self.assertNotIn("TARGET_PREBUILT_RECOVERY", _project_added_selectors(hunks, False))


if __name__ == "__main__":
    unittest.main()
