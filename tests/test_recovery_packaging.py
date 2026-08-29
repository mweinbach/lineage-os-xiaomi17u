"""Offline recovery packaging checks using synthetic bytes and source fixtures.

No complete source checkout, native image tool, phone, or network is needed.
The actual selected Make/releasetools sources are checked separately by the
source-bound command; these tests verify its guards and recovery cases.
"""

from contextlib import redirect_stderr, redirect_stdout
import copy
import io
import json
import os
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

from scripts import recovery_packaging as packaging


ROOT = Path(__file__).resolve().parents[1]

# Function-shape fixtures only. The integration probe loads the full, hash-bound
# pinned source functions instead of these deliberately smaller substitutes.
COMMON_FIXTURE = '''def GetBootableImage(name, prebuilt_name, unpack_dir, tree_subdir,
                     info_dict=None, two_step_image=False, dev_nodes=False):
  for directory in ("BOOTABLE_IMAGES", "IMAGES"):
    prebuilt_path = os.path.join(unpack_dir, directory, prebuilt_name)
    if os.path.exists(prebuilt_path):
      return File.FromLocalFile(name, prebuilt_path)
  return _BuildBootableImage(prebuilt_name)

def _FindAndLoadRecoveryFstab(info_dict, input_file, read_helper):
  if info_dict.get("ab_update") == "true" and info_dict.get("allow_non_ab") != "true":
    return None
  return "synthetic non-A/B fstab requested"
'''

OTA_FIXTURE = '''def main(argv):
  ab_update = OPTIONS.info_dict.get("ab_update") == "true"
  allow_non_ab = OPTIONS.info_dict.get("allow_non_ab") == "true"
  if OPTIONS.force_non_ab:
    assert allow_non_ab, "--force_non_ab only allowed on devices that supports non-A/B"
    assert ab_update, "--force_non_ab only allowed on A/B devices"
  generate_ab = not OPTIONS.force_non_ab and ab_update
'''


def patch_sides():
    patch = (ROOT / packaging.PATCH_PATH).read_text()
    headers = list(re.finditer(r"^@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", patch, re.M))
    if len(headers) != 1:
        raise ValueError("expected one packaging hunk")
    header = headers[0]
    lines = patch[header.end():].splitlines(keepends=True)
    if not all(line.startswith((" ", "-", "+")) for line in lines):
        raise ValueError("unexpected patch line")
    old = "".join(line[1:] for line in lines if line.startswith((" ", "-")))
    new = "".join(line[1:] for line in lines if line.startswith((" ", "+")))
    return header, old, new


def fixture_source():
    _, _, new = patch_sides()
    prefix = '''def AddImagesToTargetFiles(filename):
  recovery_image = None
  if has_recovery:
    banner("recovery")
    recovery_image = common.GetBootableImage(
        "IMAGES/recovery.img", "recovery.img", OPTIONS.input_tmp, "RECOVERY")
'''
    return prefix + new.split("\n  def add_partition(", 1)[0] + "\n"


class RecoveryPackagingContractTests(unittest.TestCase):
    def test_explicit_metadata_composition_binds_new_common_and_all_nine_sources(self):
        from scripts import target_files_metadata
        baseline = packaging._contract()
        selected, identity = packaging._selected_contract(ROOT / target_files_metadata.SOURCE_CONTRACT)
        chain = target_files_metadata.compose_sources(ROOT)
        self.assertEqual(selected["composition"], chain)
        self.assertEqual(identity, packaging._identity(target_files_metadata.encoded(chain)))
        self.assertEqual(selected["source_files"], baseline[0]["source_files"])
        self.assertEqual(len(selected["semantic_files"]), 8)
        self.assertEqual(selected["validation_scope"], packaging.SCOPE)
        self.assertEqual(packaging._contract(), baseline)

    def test_explicit_composition_keeps_all_final_source_checks(self):
        baseline, baseline_id = packaging._contract()
        selected, selected_id = packaging._selected_contract(
            ROOT / "patches/evolution/direct-avb-custom-images.json")
        self.assertNotEqual(selected_id, baseline_id)
        self.assertEqual(selected["source_files"], baseline["source_files"])
        self.assertEqual(len(selected["semantic_files"]), 6)
        core = next(row for row in selected["semantic_files"] if row["path"] == "build/make/core/Makefile")
        self.assertEqual(core["sha256"], selected["composition"]["core_transitions"][-1]["after"]["sha256"])
        self.assertNotEqual(core, baseline["semantic_files"][0])
        self.assertEqual(packaging._contract(), (baseline, baseline_id))

    def test_device_mode_guard_preserves_product_readonly_ordering(self):
        source = (ROOT / "device/xiaomi/nezha/recovery-prebuilt.mk").read_text()
        guard = source.split("# working76 is only a dedicated recovery payload", 1)[1]
        guard = guard.split("# The follow-up keeps two-step construction", 1)[0]
        self.assertIn("ifneq ($(value AB_OTA_UPDATER),true)", guard)
        self.assertIn("ifneq ($(value PRODUCT_OTA_FORCE_NON_AB_PACKAGE),false)", guard)
        self.assertIn("ifneq ($(origin TARGET_OTA_ALLOW_NON_AB),undefined)", guard)
        self.assertIn("ifneq ($(value TARGET_OTA_ALLOW_NON_AB),false)", guard)
        self.assertIn(".KATI_READONLY := AB_OTA_UPDATER", guard)
        for name in ("AB_OTA_UPDATER", "PRODUCT_OTA_FORCE_NON_AB_PACKAGE", "TARGET_OTA_ALLOW_NON_AB"):
            self.assertNotRegex(guard, rf"(?m)^{name}\s*[:?+]?=")
        self.assertIn("ef2e4014238ad323e8157a3bf80190d1795f01b6dd0c087b5e8c2cc167a43c51", source)

    def test_public_contract_binds_patch_and_current_upstream(self):
        record, identity = packaging._contract()
        self.assertEqual(record["project"]["commit"], packaging.PROJECT_COMMIT)
        self.assertEqual(record["source_files"], [{
            "path": packaging.EDIT_PATH,
            "before": {"sha256": "9ace653e00cc3635ae476d15e03b44b7bf6c70898497c343bf41f6ce521dbd98", "size_bytes": 48004},
            "after": {"sha256": "ef2e4014238ad323e8157a3bf80190d1795f01b6dd0c087b5e8c2cc167a43c51", "size_bytes": 48289},
        }])
        self.assertEqual(identity, packaging._identity((ROOT / packaging.CONTRACT_PATH).read_bytes()))
        self.assertEqual(record["semantics"]["two_step_destination"], "/boot")
        self.assertEqual(record["validation_scope"], packaging.SCOPE)
        for flag in ("ordinary_recovery_bytes_changed", "two_step_image_fabricated",
                     "recovery_source_metadata_fabricated", "signature_or_avb_rules_changed",
                     "readiness_flags_changed"):
            self.assertIs(record["semantics"][flag], False)

    def test_patch_only_wraps_the_existing_non_ab_body(self):
        header, old, new = patch_sides()
        self.assertEqual(tuple(map(int, header.groups())), (1023, 28, 1023, 32))
        self.assertEqual(len(old.splitlines()), 28)
        self.assertEqual(len(new.splitlines()), 32)
        self.assertEqual(len(new.encode()) - len(old.encode()), 285)
        original = old[old.index('      banner("recovery (two-step image)")'):]
        original = original.split("\n  def add_partition(", 1)[0]
        wrapped = new[new.index('        banner("recovery (two-step image)")'):]
        wrapped = wrapped.split("\n  def add_partition(", 1)[0]
        self.assertEqual("".join(line[2:] if line.strip() else line
                                 for line in wrapped.splitlines(keepends=True)), original)
        self.assertEqual(old.split('      banner("recovery (two-step image)")')[0],
                         new.split("      # Non-A/B two-step updates")[0])
        self.assertIn('assert recovery_image, "Failed to create recovery.img."', new)
        self.assertIn('assert recovery_two_step_image, "Failed to create recovery-two-step.img."', new)
        self.assertNotIn("no_recovery", new)
        self.assertNotIn("ignore", new)


class RecoveryPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.source_tree = self.root / "source"
        self.enterContext(mock.patch.object(packaging, "ROOT", self.root))
        for name in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(name, side_effect=AssertionError("offline test: " + name)))
        self.data = {packaging.EDIT_PATH: fixture_source().encode(),
                     packaging.COMMON_PATH: COMMON_FIXTURE.encode(), packaging.OTA_PATH: OTA_FIXTURE.encode(),
                     packaging.SEMANTIC_PATHS[0]: b"synthetic prebuilt Make consumer\n",
                     packaging.SEMANTIC_PATHS[2]: b"synthetic non-A/B consumer\n"}
        self.record = json.loads((ROOT / packaging.CONTRACT_PATH).read_bytes())
        self.patch = (ROOT / packaging.PATCH_PATH).read_bytes()
        self.record["source_files"][0]["after"] = packaging._identity(self.data[packaging.EDIT_PATH])
        for row in self.record["semantic_files"]:
            row.update(packaging._identity(self.data[row["path"]]))
        for relative, data in self.data.items():
            path = self.source_tree / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        patch = self.root / packaging.PATCH_PATH
        patch.parent.mkdir(parents=True, exist_ok=True)
        patch.write_bytes(self.patch)
        self.save_contract()

    def save_contract(self):
        (self.root / packaging.CONTRACT_PATH).write_text(json.dumps(self.record) + "\n")

    def test_source_check_binds_every_file_without_mutation(self):
        result = packaging.check_source(self.source_tree)
        self.assertEqual(result["status"], "verified-source")
        self.assertEqual(len(result["files"]), 5)
        self.assertFalse(result["whole_source_tree_verified"])
        self.assertFalse(result["source_modified"])
        self.assertEqual(result["scope"], packaging.SCOPE)
        self.assertEqual(self.data, {path: (self.source_tree / path).read_bytes() for path in self.data})

    def test_probe_proves_ab_omission_and_retains_non_ab_failures(self):
        result = packaging.probe(self.source_tree)
        self.assertEqual(result["status"], "verified-python-recovery-branch")
        self.assertEqual(len(result["cases"]), 12)
        self.assertTrue(all(case["status"] == "passed" for case in result["cases"]))
        cases = {case["name"]: case for case in result["cases"]}
        self.assertEqual(cases["ab-only-fresh-zip"]["written_artifacts"], ["IMAGES/recovery.img"])
        self.assertEqual(cases["ab-only-fresh-zip"]["stubbed_missing_image_requests"], [])
        self.assertEqual(cases["ab-only-missing-real-recovery"]["expected_error"], "Failed to create recovery.img.")
        for name in ("non-ab-missing-two-step", "legacy-missing-two-step", "hybrid-missing-two-step"):
            self.assertEqual(cases[name]["expected_error"], "Failed to create recovery-two-step.img.")
        self.assertEqual(cases["hybrid-with-distinct-two-step"]["written_artifacts"],
                         ["IMAGES/recovery.img", "OTA/recovery-two-step.img"])
        self.assertTrue(result["force_non_ab_without_permission_rejected"])
        self.assertTrue(result["explicit_hybrid_selection_preserved"])
        self.assertTrue(result["ab_only_recovery_fstab_not_required"])
        self.assertEqual(result["native_commands_executed"], [])
        self.assertEqual(result["scope"]["phone_operations"], [])
        self.assertEqual(self.data, {path: (self.source_tree / path).read_bytes() for path in self.data})

    def test_unknown_metadata_does_not_suppress_two_step_requirement(self):
        for value in (True, None, "TRUE", "1", "false"):
            with self.subTest(value=value):
                result = packaging._case(self.data, name="unknown", info={"ab_update": value},
                                         expected_error="Failed to create recovery-two-step.img.")
                self.assertEqual(len(result["image_requests"]), 2)

    def test_ab_with_an_unneeded_two_step_input_does_not_publish_it(self):
        result = packaging._case(self.data, name="ab-with-unused-special", info={"ab_update": "true"}, two_step=True)
        self.assertEqual(result["written_artifacts"], ["IMAGES/recovery.img"])

    def test_probe_refuses_the_old_unconditional_consumer(self):
        source = self.data[packaging.EDIT_PATH].decode()
        start = source.index("      # Non-A/B two-step updates")
        body = source[source.index('        banner("recovery (two-step image)")', start):]
        old = source[:start] + "".join(line[2:] if line.strip() else line for line in body.splitlines(keepends=True))
        self.data[packaging.EDIT_PATH] = old.encode()
        (self.source_tree / packaging.EDIT_PATH).write_bytes(self.data[packaging.EDIT_PATH])
        self.record["source_files"][0]["after"] = packaging._identity(self.data[packaging.EDIT_PATH])
        self.save_contract()
        with self.assertRaisesRegex(packaging.RecoveryPackagingError, "unexpected recovery result"):
            packaging.probe(self.source_tree)

    def test_probe_rejects_suppression_for_hybrid_products(self):
        raw = self.data[packaging.EDIT_PATH].replace(
            b'if (OPTIONS.info_dict.get("ab_update") != "true" or\n          OPTIONS.info_dict.get("allow_non_ab") == "true"):',
            b'if OPTIONS.info_dict.get("ab_update") != "true":')
        self.assertNotEqual(raw, self.data[packaging.EDIT_PATH])
        (self.source_tree / packaging.EDIT_PATH).write_bytes(raw)
        self.record["source_files"][0]["after"] = packaging._identity(raw)
        self.save_contract()
        with self.assertRaisesRegex(packaging.RecoveryPackagingError, "unexpected recovery result"):
            packaging.probe(self.source_tree)

    def test_every_unreviewed_source_file_is_refused(self):
        for relative, original in self.data.items():
            with self.subTest(relative=relative):
                path = self.source_tree / relative
                path.write_bytes(original + b"# changed\n")
                with self.assertRaisesRegex(packaging.RecoveryPackagingError, "source differs"):
                    packaging.check_source(self.source_tree)
                path.write_bytes(original)

    def test_control_metadata_cannot_change_paths_or_promote_readiness(self):
        mutations = [
            lambda r: r.update(schema_version=True),
            lambda r: r["project"].update(commit="0" * 40),
            lambda r: r["patch"].update(path="../elsewhere"),
            lambda r: r["source_files"][0].update(path="../elsewhere"),
            lambda r: r["source_files"][0]["after"].update(size_bytes=True),
            lambda r: r["source_files"][0]["after"].update(sha256="x" * 64),
            lambda r: r.update(semantic_files=r["semantic_files"][:-1]),
            lambda r: r["semantic_files"][1].update(path=r["semantic_files"][0]["path"]),
            lambda r: r["validation_scope"].update(ota_verified=True),
        ]
        original = copy.deepcopy(self.record)
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                self.record = copy.deepcopy(original)
                mutate(self.record)
                self.save_contract()
                with self.assertRaises(ValueError):
                    packaging.check_source(self.source_tree)

    def test_patch_mismatch_or_duplicate_json_key_is_refused(self):
        (self.root / packaging.PATCH_PATH).write_bytes(self.patch + b"# altered\n")
        with self.assertRaisesRegex(packaging.RecoveryPackagingError, "patch differs"):
            packaging.check_source(self.source_tree)
        (self.root / packaging.PATCH_PATH).write_bytes(self.patch)
        contract = self.root / packaging.CONTRACT_PATH
        contract.write_text(contract.read_text().replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
        with self.assertRaisesRegex(ValueError, "invalid JSON input"):
            packaging.check_source(self.source_tree)

    def test_symlinks_and_hardlinks_are_refused(self):
        path = self.source_tree / packaging.EDIT_PATH
        other = self.root / "other.py"
        path.rename(other)
        path.symlink_to(other)
        with self.assertRaises(ValueError):
            packaging.check_source(self.source_tree)
        path.unlink()
        os.link(other, path)
        with self.assertRaisesRegex(ValueError, "hard-linked"):
            packaging.check_source(self.source_tree)

    def test_source_changes_during_probe_are_not_accepted(self):
        original = packaging._case
        changed = False

        def mutate(*args, **kwargs):
            nonlocal changed
            result = original(*args, **kwargs)
            if not changed:
                changed = True
                (self.source_tree / packaging.COMMON_PATH).write_bytes(b"changed while probing\n")
            return result

        with mock.patch.object(packaging, "_case", side_effect=mutate):
            with self.assertRaisesRegex(packaging.RecoveryPackagingError, "source differs"):
                packaging.probe(self.source_tree)

    def test_returned_scope_cannot_mutate_next_verification(self):
        result = packaging.check_source(self.source_tree)
        result["scope"]["ota_verified"] = True
        result["scope"]["phone_operations"].append("not permitted")
        self.assertEqual(packaging.check_source(self.source_tree)["scope"], packaging.SCOPE)
        self.assertFalse(packaging.SCOPE["ota_verified"])
        self.assertEqual(packaging.SCOPE["phone_operations"], [])

    def test_cli_reports_success_and_source_refusal_without_native_tools(self):
        output, errors = io.StringIO(), io.StringIO()
        with redirect_stdout(output), redirect_stderr(errors):
            self.assertEqual(packaging.main(["check-source", "--source-tree", str(self.source_tree)]), 0)
        self.assertEqual(json.loads(output.getvalue())["status"], "verified-source")
        self.assertEqual(errors.getvalue(), "")
        (self.source_tree / packaging.EDIT_PATH).unlink()
        with redirect_stdout(io.StringIO()), redirect_stderr(errors):
            self.assertEqual(packaging.main(["check-source", "--source-tree", str(self.source_tree)]), 2)
        self.assertIn("recovery packaging:", errors.getvalue())


if __name__ == "__main__":
    unittest.main()
