"""Offline tests for source-only TWRP staging and guarded compilation."""

from contextlib import ExitStack, redirect_stdout, redirect_stderr
import copy
import io
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts import twrp_build as build


class BuildFixture(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.root = Path(self.stack.enter_context(tempfile.TemporaryDirectory())).resolve()
        self.control = self.root / "control"
        self.paths = {"source_dir": self.root / "source", "out_dir": self.root / "output",
                      "report_dir": self.root / "reports"}
        self.source = self.paths["source_dir"]
        self.source.mkdir()
        self.paths["report_dir"].mkdir()
        (self.paths["report_dir"] / build.twrp_workspace.SNAPSHOT).write_text("frozen source manifest\n")
        self.config = {"schema_version": 1, "device": "nezha",
                       "manifest": {"url": "https://example.org/manifest", "branch": "twrp-16.0",
                                    "commit": "b" * 40, "name": "default.xml"},
                       "repo_tool": {"url": "https://example.org/repo", "commit": "c" * 40},
                       "pinned_projects": {},
                       "project_selection": {"host_os": "Linux", "groups": ["default", "platform-linux"],
                                             "expanded_project_count": 1, "excluded_projects": []}}
        self.project = "bootable/recovery"
        self.base = "a" * 40
        self.before = b"before\n"
        self.after = b"after\n"
        self.source_file = self.source / self.project / "init.rc"
        self.source_file.parent.mkdir(parents=True)
        self.source_file.write_bytes(self.before)
        target = self.control / build.TARGET_SOURCE
        target.mkdir(parents=True)
        for name in build.REQUIRED_TARGET:
            (target / name).write_text("# source-only fixture\n")
        self.patch_path = self.control / "patches/twrp/0001-test.patch"
        self.patch_path.parent.mkdir(parents=True)
        self.patch_path.write_text("diff --git a/init.rc b/init.rc\nindex 1234567..7654321 100644\n"
                                   "--- a/init.rc\n+++ b/init.rc\n@@ -1 +1 @@\n-before\n+after\n")
        self.series = {"schema_version": 1, "manifest": {"commit": "b" * 40}, "patches": [{
            "id": "0001-test", "project": self.project, "base_commit": self.base,
            "patch": "patches/twrp/0001-test.patch", "patch_sha256": build.sha256(self.patch_path.read_bytes()),
            "files": [{"path": "init.rc", "before_sha256": build.sha256(self.before),
                       "after_sha256": build.sha256(self.after), "before_size_bytes": len(self.before),
                       "after_size_bytes": len(self.after)}]}]}
        self.write_series()
        self.frozen = {self.project: {"name": "android_bootable_recovery", "path": self.project,
                                     "revision": self.base, "remote": "origin",
                                     "url": "https://example.org/android_bootable_recovery"}}
        self.host = {"supported_build_host": True, "checks": {"fixture": True}, "host_mode": "native"}
        self.host_mock = self.stack.enter_context(patch.object(build.twrp_workspace, "require_host", return_value=self.host))
        self.control_mock = self.stack.enter_context(patch.object(build.twrp_workspace, "verify_control"))
        self.stack.enter_context(patch.object(build.twrp_workspace, "load_snapshot", return_value=self.frozen))
        self.stack.enter_context(patch.object(build.twrp_workspace, "manifest_text", return_value="manifest"))
        self.manifest_mock = self.stack.enter_context(patch.object(build.twrp_workspace, "parse_manifest", return_value=self.frozen))
        self.projects_mock = self.stack.enter_context(patch.object(build.twrp_workspace, "project_report", side_effect=self.project_report))
        self.run_mock = self.stack.enter_context(patch.object(build.twrp_workspace, "run", side_effect=self.fake_git))
        self.process_mock = self.stack.enter_context(patch.object(build.subprocess, "run", side_effect=AssertionError("Unexpected process")))

    def write_series(self):
        (self.control / build.SERIES).write_text(json.dumps(self.series))

    def project_report(self, source, projects):
        changed = self.source_file.read_bytes() != self.before
        entry = {**self.frozen[self.project], "head": self.base,
                 "actual_url": self.frozen[self.project]["url"], "clean": not changed, "missing": False,
                 "local_changes": " M init.rc" if changed else "",
                 "errors": ["Local changes preserved"] if changed else []}
        return {"projects": [entry], "project_count": 1, "all_present": True,
                "verified": not changed, "failures": entry["errors"]}

    def fake_git(self, args, **kwargs):
        if "status" in args:
            return SimpleNamespace(stdout=" M init.rc\0")
        if "ls-tree" in args:
            return SimpleNamespace(stdout="100644 blob " + self.base + "\tinit.rc\0")
        self.assertIn("apply", args)
        if "--check" in args:
            self.assertFalse((self.source / build.TARGET).exists())
            self.assertEqual(self.source_file.read_bytes(), self.before)
        else:
            self.source_file.write_bytes(self.after)
        return SimpleNamespace(stdout="", returncode=0)

    def prepare(self):
        return build.prepare(self.config, self.paths, "native", self.control)

    def check(self):
        return build.check(self.config, self.paths, "native", self.control)

    def write_artifact(self):
        image = self.paths["out_dir"] / "target/product/nezha/recovery.img"
        image.parent.mkdir(parents=True, exist_ok=True)
        content = bytearray(16384)
        content[:8] = b"ANDROID!"
        struct.pack_into("<II", content, 8, 0, 128)
        struct.pack_into("<I", content, 20, 1584)
        struct.pack_into("<I", content, 40, 4)
        content[8192:8196] = b"AVB0"
        struct.pack_into("!4sIIQQQ28s", content, len(content) - 64, b"AVBf", 1, 0,
                         8192, 8192, 512, b"\0" * 28)
        image.write_bytes(content)
        return image


class ControlTests(BuildFixture):
    def test_plan_is_read_only_and_has_no_process_or_host_probe(self):
        before = set(self.root.rglob("*"))
        report = build.plan(self.config, self.paths, "apple-rosetta", 8, "userdebug", self.control)
        self.assertFalse(report["executes_commands"])
        self.assertFalse(report["writes_files"])
        self.assertFalse(report["flash_admitted"])
        self.assertEqual(set(self.root.rglob("*")), before)
        self.host_mock.assert_not_called()
        self.run_mock.assert_not_called()
        self.process_mock.assert_not_called()

    def test_environment_does_not_inherit_check_bypasses_or_startup_hooks(self):
        unsafe = {"ALLOW_MISSING_DEPENDENCIES": "true", "SELINUX_IGNORE_NEVERALLOWS": "true",
                  "BUILD_BROKEN_PLUGIN_VALIDATION": "all", "BASH_ENV": "/tmp/hook",
                  "JAVA_TOOL_OPTIONS": "injected", "GOFLAGS": "injected", "PYTHONPATH": "/tmp/hook",
                  "TARGET_PRODUCT": "wrong-device", "OUT_DIR": "/work/evolution/out"}
        with patch.dict(build.os.environ, unsafe):
            env = build.environment(self.source, self.paths["out_dir"], "user")
        for key in unsafe.keys() - {"TARGET_PRODUCT", "OUT_DIR"}:
            self.assertNotIn(key, env)
        self.assertEqual(env["OUT_DIR"], "out-twrp")
        self.assertEqual(env["OUT"], str(self.paths["out_dir"] / "target/product/nezha"))
        self.assertEqual(env["ANDROID_PRODUCT_OUT"], env["OUT"])
        self.assertEqual(env["TARGET_PRODUCT"], "twrp_nezha")
        self.assertEqual(env["TARGET_RELEASE"], "bp2a")
        self.assertEqual(env["TARGET_BUILD_VARIANT"], "user")
        self.assertEqual(env["GOTOOLCHAIN"], "local")
        self.assertEqual({env[key] for key in ("GOENV", "GOPROXY", "GOSUMDB")}, {"off"})
        self.assertTrue(env["PATH"].startswith(str(self.source / "prebuilts/build-tools/path/linux-x86")))
        self.assertEqual(env["GOCACHE"], str(self.paths["out_dir"] / "cache/go"))
        self.assertEqual(env["XDG_CACHE_HOME"], str(self.paths["out_dir"] / "cache/xdg"))
        self.assertEqual(env["PYTHONDONTWRITEBYTECODE"], "1")

    def test_only_guarded_build_targets_and_valid_jobs_are_admitted(self):
        self.assertEqual(build.command("build", 8)[-1], "recoveryimage")
        self.assertEqual(build.command("graph", 8)[-1], "nothing")
        for jobs in (0, 65, True, "8"):
            with self.subTest(jobs=jobs), self.assertRaises(ValueError):
                build.command("build", jobs)
        for action in ("flash", "recoveryimage-nodeps", "otapackage"):
            with self.subTest(action=action), self.assertRaises(ValueError):
                build.command(action, 8)
        with self.assertRaises(ValueError):
            build.environment(self.source, self.paths["out_dir"], "eng")

    def test_symlink_target_and_proprietary_payloads_are_rejected(self):
        target = self.control / build.TARGET_SOURCE
        (target / "kernel.img").write_bytes(b"payload")
        with self.assertRaisesRegex(ValueError, "payload type"):
            build.target_inventory(self.control)
        (target / "kernel.img").unlink()
        (target / "linked.mk").symlink_to(target / "device.mk")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build.target_inventory(self.control)

    def test_nontext_and_executable_source_are_rejected(self):
        path = self.control / build.TARGET_SOURCE / "device.mk"
        path.write_bytes(b"binary\0payload")
        with self.assertRaisesRegex(ValueError, "binary"):
            build.target_inventory(self.control)
        path.write_text("text\n")
        path.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "executable"):
            build.target_inventory(self.control)

    def test_patch_hash_and_undeclared_paths_are_rejected(self):
        self.patch_path.write_text(self.patch_path.read_text().replace("+after", "+unexpected"))
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            build.controls(self.config, self.control)
        self.series["patches"][0]["patch_sha256"] = build.sha256(self.patch_path.read_bytes())
        self.series["patches"][0]["files"][0]["path"] = "different.rc"
        self.write_series()
        with self.assertRaisesRegex(ValueError, "file closure"):
            build.controls(self.config, self.control)

    def test_path_traversal_and_overlapping_patches_are_rejected(self):
        self.series["patches"][0]["files"][0]["path"] = "../escape.rc"
        self.write_series()
        with self.assertRaises(ValueError):
            build.controls(self.config, self.control)
        self.series["patches"][0]["files"][0]["path"] = "init.rc"
        duplicate = copy.deepcopy(self.series["patches"][0])
        duplicate["id"] = "0002-overlap"
        self.series["patches"].append(duplicate)
        self.write_series()
        with self.assertRaisesRegex(ValueError, "Overlapping"):
            build.controls(self.config, self.control)


class PreparationTests(BuildFixture):
    def test_prepare_stages_exact_files_and_patch_with_receipt(self):
        report = self.prepare()
        self.assertFalse(report["already_prepared"])
        self.assertFalse(report["flash_admitted"])
        self.assertEqual(self.source_file.read_bytes(), self.after)
        self.assertEqual((self.source / build.OUT_ALIAS).readlink(), self.paths["out_dir"])
        state = json.loads((self.paths["report_dir"] / build.STATE).read_text())
        self.assertEqual(state["target_product"], "twrp_nezha")
        build.verify_target(self.source, state["controls"]["target_files"])
        self.assertTrue(self.check()["prepared_sources_verified"])
        self.process_mock.assert_not_called()

    def test_prepare_is_idempotent_only_with_exact_receipt(self):
        self.prepare()
        self.run_mock.reset_mock()
        result = self.prepare()
        self.assertTrue(result["already_prepared"])
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))
        (self.control / build.TARGET_SOURCE / "device.mk").write_text("# changed controls\n")
        with self.assertRaisesRegex(ValueError, "identity or controlled sources changed"):
            self.prepare()

    def test_arbitrary_target_edits_and_files_are_preserved(self):
        self.prepare()
        extra = self.source / build.TARGET / "extra.mk"
        extra.write_text("unreviewed\n")
        with self.assertRaisesRegex(ValueError, "Staged Nezha files differ"):
            self.check()
        self.assertEqual(extra.read_text(), "unreviewed\n")

    def test_preexisting_target_and_output_are_never_adopted(self):
        target = self.source / build.TARGET
        target.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "target already exists"):
            self.prepare()
        self.assertEqual(self.source_file.read_bytes(), self.before)
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))
        target.rmdir()
        self.paths["out_dir"].mkdir()
        owned = self.paths["out_dir"] / "existing.img"
        owned.write_text("preserve\n")
        with self.assertRaisesRegex(ValueError, "nonempty"):
            self.prepare()
        self.assertEqual(owned.read_text(), "preserve\n")
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_patch_context_failure_does_not_stage_or_apply(self):
        self.run_mock.side_effect = subprocess.CalledProcessError(1, ["git", "apply", "--check"])
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare()
        self.assertFalse((self.source / build.TARGET).exists())
        self.assertFalse(self.paths["out_dir"].exists())
        self.assertEqual(self.source_file.read_bytes(), self.before)

    def test_partial_prepare_is_journaled_and_not_overwritten(self):
        def fail_apply(args, **kwargs):
            if "apply" in args and "--check" not in args:
                raise subprocess.CalledProcessError(1, args)
            return self.fake_git(args, **kwargs)
        self.run_mock.side_effect = fail_apply
        with self.assertRaises(subprocess.CalledProcessError):
            self.prepare()
        self.assertTrue(list(self.paths["report_dir"].glob("prepare-start-*.json")))
        self.assertTrue((self.source / build.TARGET).is_dir())
        self.assertFalse((self.paths["report_dir"] / build.STATE).exists())
        self.run_mock.side_effect = self.fake_git
        with self.assertRaisesRegex(ValueError, "target already exists"):
            self.prepare()

    def test_preimage_hash_mismatch_blocks_all_writes(self):
        self.source_file.write_bytes(b"wrong!\n")
        clean = self.project_report(self.source, self.frozen)
        clean["projects"][0]["errors"] = []
        self.projects_mock.side_effect = None
        self.projects_mock.return_value = clean
        with self.assertRaisesRegex(ValueError, "beforeimage differs"):
            self.prepare()
        self.assertFalse((self.source / build.TARGET).exists())
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))

    def test_postimage_mismatch_and_staged_changes_are_rejected(self):
        self.prepare()
        self.source_file.write_bytes(b"after but different\n")
        with self.assertRaisesRegex(ValueError, "afterimage differs"):
            self.check()
        self.source_file.write_bytes(self.after)
        self.run_mock.side_effect = lambda *args, **kwargs: SimpleNamespace(stdout="M  init.rc\0")
        with self.assertRaisesRegex(ValueError, "exact unstaged patch closure"):
            self.check()

    def test_unreviewed_patch_mode_changes_are_rejected(self):
        self.prepare()
        self.source_file.chmod(0o755)
        with self.assertRaisesRegex(ValueError, "executable mode differs"):
            self.check()

    def test_untracked_files_in_patched_project_are_rejected(self):
        self.prepare()
        self.run_mock.side_effect = lambda *args, **kwargs: SimpleNamespace(stdout=" M init.rc\0?? extra.rc\0")
        with self.assertRaisesRegex(ValueError, "exact unstaged patch closure"):
            self.check()

    def test_other_project_errors_are_not_hidden_by_patch_exception(self):
        self.prepare()
        report = self.project_report(self.source, self.frozen)
        report["projects"][0]["errors"].append("HEAD differs from frozen project revision")
        self.projects_mock.side_effect = None
        self.projects_mock.return_value = report
        with self.assertRaisesRegex(ValueError, "HEAD differs"):
            self.check()

    def test_base_revision_and_manifest_selection_must_match(self):
        self.frozen[self.project]["revision"] = "d" * 40
        with self.assertRaisesRegex(ValueError, "frozen base revision"):
            self.prepare()
        self.frozen[self.project]["revision"] = self.base
        self.manifest_mock.return_value = {}
        with self.assertRaisesRegex(ValueError, "Selected projects differ"):
            self.prepare()

    def test_manifest_owned_target_is_rejected(self):
        self.frozen["device/xiaomi"] = {"name": "device/xiaomi", "path": "device/xiaomi",
                                        "revision": "d" * 40, "remote": "origin",
                                        "url": "https://example.org/device/xiaomi"}
        with self.assertRaisesRegex(ValueError, "manifest-owned"):
            self.prepare()

    def test_output_alias_cannot_be_retargeted(self):
        self.prepare()
        alias = self.source / build.OUT_ALIAS
        alias.unlink()
        alias.symlink_to(self.root / "unrelated")
        with self.assertRaisesRegex(ValueError, "output alias differs"):
            self.check()

    def test_product_output_symlink_cannot_escape_isolated_output(self):
        self.prepare()
        product = self.paths["out_dir"] / "target/product"
        product.mkdir(parents=True)
        (product / "nezha").symlink_to(self.root / "elsewhere")
        with self.assertRaisesRegex(ValueError, "Symlink"):
            self.check()

    def test_host_preflight_failure_blocks_every_mutation(self):
        self.host_mock.side_effect = ValueError("unsupported host")
        with self.assertRaisesRegex(ValueError, "unsupported host"):
            self.prepare()
        self.run_mock.assert_not_called()
        self.assertEqual(self.source_file.read_bytes(), self.before)
        self.assertFalse((self.source / build.TARGET).exists())


class ExecutionTests(BuildFixture):
    def test_graph_uses_sanitized_process_and_never_reports_an_artifact(self):
        self.prepare()
        self.process_mock.side_effect = None
        self.process_mock.return_value = SimpleNamespace(returncode=0)
        with redirect_stdout(io.StringIO()):
            result = build.run_build(self.config, self.paths, "graph", "native", 4, "userdebug", self.control)
        args, kwargs = self.process_mock.call_args
        self.assertEqual(args[0][-1], "nothing")
        self.assertFalse(kwargs["shell"])
        self.assertEqual(kwargs["env"]["TARGET_BUILD_VARIANT"], "userdebug")
        self.assertNotIn("artifact", result)
        self.assertFalse(result["flash_admitted"])

    def test_build_inspects_artifact_and_checks_engineering_signature(self):
        self.prepare()
        def process(args, **kwargs):
            if args[-1] == "recoveryimage":
                self.write_artifact()
            else:
                self.assertIn("verify_image", args)
                self.assertIn("external/avb/test/data/testkey_rsa4096.pem", args)
            return SimpleNamespace(returncode=0)
        self.process_mock.side_effect = process
        with redirect_stdout(io.StringIO()):
            report = build.run_build(self.config, self.paths, "build", "native", 4, "user", self.control)
        self.assertEqual(self.process_mock.call_count, 2)
        self.assertTrue(report["artifact"]["format_inspected"])
        self.assertTrue(report["artifact"]["engineering_test_key_signature_verified"])
        self.assertFalse(report["artifact"]["oem_authority_verified"])
        self.assertFalse(report["artifact"]["runtime_verified"])
        self.assertFalse(report["flash_admitted"])
        self.assertTrue(report["pending_validation"])

    def test_zero_exit_without_artifact_is_not_build_success(self):
        self.prepare()
        self.process_mock.side_effect = None
        self.process_mock.return_value = SimpleNamespace(returncode=0)
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "without a regular recovery.img"):
            build.run_build(self.config, self.paths, "build", "native", 4, "userdebug", self.control)
        reports = list(self.paths["report_dir"].glob("build-failed-*.json"))
        self.assertEqual(len(reports), 1)
        self.assertEqual(json.loads(reports[0].read_text())["status"], "failed")

    def test_process_failure_has_a_preserved_log_and_report(self):
        self.prepare()
        self.process_mock.side_effect = subprocess.CalledProcessError(1, ["bash", "soong_ui"])
        with redirect_stdout(io.StringIO()), self.assertRaises(subprocess.CalledProcessError):
            build.run_build(self.config, self.paths, "graph", "native", 4, "userdebug", self.control)
        self.assertEqual(len(list(self.paths["report_dir"].glob("graph-*.log"))), 1)
        report = json.loads(next(self.paths["report_dir"].glob("graph-failed-*.json")).read_text())
        self.assertEqual(report["failed_command_exit_code"], 1)
        self.assertFalse(report["flash_admitted"])

    def test_nsjail_fallback_is_failure_even_when_build_returns_zero(self):
        self.prepare()
        def process(args, **kwargs):
            kwargs["stdout"].write("Build sandboxing disabled due to nsjail error.\n")
            return SimpleNamespace(returncode=0)
        self.process_mock.side_effect = process
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "sandbox fallback"):
            build.run_build(self.config, self.paths, "graph", "native", 4, "user", self.control)
        report = json.loads(next(self.paths["report_dir"].glob("graph-failed-*.json")).read_text())
        self.assertTrue(report["sandbox_fallback_detected"])
        self.assertEqual(report["command_exit_code"], 0)
        self.assertEqual(report["status"], "failed")

    def test_build_cannot_mutate_known_source_and_still_complete(self):
        self.prepare()
        def process(*args, **kwargs):
            self.source_file.write_text("source changed by hook\n")
            return SimpleNamespace(returncode=0)
        self.process_mock.side_effect = process
        with redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "afterimage differs"):
            build.run_build(self.config, self.paths, "graph", "native", 4, "userdebug", self.control)
        self.assertEqual(self.source_file.read_text(), "source changed by hook\n")

    def test_build_cannot_report_a_different_prepared_revision(self):
        self.prepare()
        real_check = build.check
        checks = 0
        def changed_revision(*args, **kwargs):
            nonlocal checks
            report = real_check(*args, **kwargs)
            checks += 1
            if checks > 1:
                report["build_state_sha256"] = "0" * 64
            return report
        self.process_mock.side_effect = None
        self.process_mock.return_value = SimpleNamespace(returncode=0)
        with patch.object(build, "check", side_effect=changed_revision), redirect_stdout(io.StringIO()), \
                self.assertRaisesRegex(ValueError, "revision changed during compilation"):
            build.run_build(self.config, self.paths, "graph", "native", 4, "user", self.control)
        self.assertFalse((self.paths["report_dir"] / "build-operation.lock").exists())

    def test_image_header_kernel_and_avb_bounds_are_checked(self):
        image = self.write_artifact()
        self.assertEqual(build.inspect_artifact(self.paths)["kernel_size"], 0)
        content = bytearray(image.read_bytes())
        struct.pack_into("<I", content, 8, 123)
        image.write_bytes(content)
        with self.assertRaisesRegex(ValueError, "kernel-free"):
            build.inspect_artifact(self.paths)
        self.write_artifact()
        content = bytearray(image.read_bytes())
        struct.pack_into("!Q", content, len(content) - 64 + 20, 999999)
        image.write_bytes(content)
        with self.assertRaisesRegex(ValueError, "AVB footer"):
            build.inspect_artifact(self.paths)

    def test_image_symlink_is_rejected(self):
        image = self.write_artifact()
        external = self.root / "external.img"
        image.rename(external)
        image.symlink_to(external)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build.inspect_artifact(self.paths)

    def test_image_padding_and_boot_signature_region_must_fit(self):
        image = self.write_artifact()
        content = bytearray(image.read_bytes())
        struct.pack_into("!Q", content, len(content) - 64 + 12, 4096 + 128)
        image.write_bytes(content)
        with self.assertRaisesRegex(ValueError, "AVB footer"):
            build.inspect_artifact(self.paths)
        self.write_artifact()
        content = bytearray(image.read_bytes())
        struct.pack_into("<I", content, 1580, 8192)
        image.write_bytes(content)
        with self.assertRaisesRegex(ValueError, "kernel-free"):
            build.inspect_artifact(self.paths)


class RevisionTests(BuildFixture):
    def setUp(self):
        super().setUp()
        (self.control / build.TARGET_SOURCE / "notes.txt").write_text("old notes\n")
        self.previous = self.root / "previous-control"
        shutil.copytree(self.control, self.previous)
        (self.previous / "config").mkdir()
        (self.previous / "config/twrp.json").write_text(json.dumps(self.config))
        self.prepare()
        self.before_state = (self.paths["report_dir"] / build.STATE).read_bytes()
        self.stack.enter_context(patch.object(build.twrp_workspace, "load_config",
                                             side_effect=lambda path: json.loads(path.read_text())))
        self.run_mock.reset_mock()

    def change_target(self, relative="device.mk", text="# reviewed revision\n"):
        (self.control / build.TARGET_SOURCE / relative).write_text(text)

    def revise(self):
        return build.revise(self.config, self.paths, "native", self.previous, self.control)

    def supplementary_fixture(self):
        descriptor = {"configuration_sha256": "d" * 64,
                      "base": {"project_count": 1, "source_dir": str(self.source),
                               "frozen_manifest_sha256": build.sha256(
                                   (self.paths["report_dir"] / build.twrp_workspace.SNAPSHOT).read_bytes())},
                      "projects": [{"path": "system/bpf", "url": "https://example.org/system/bpf",
                                    "commit": "e" * 40, "tag": "android-16.0.0_r1", "reason": "reviewed provider"}]}
        self.stack.enter_context(patch.object(build, "supplementary_descriptor",
                                             side_effect=lambda root: descriptor if root == self.control else None))
        module = SimpleNamespace(verify=Mock(return_value={"configuration_sha256": descriptor["configuration_sha256"],
                                                           "base": descriptor["base"], "projects": [], "verified": True}))
        self.stack.enter_context(patch.object(build, "dependency_module", return_value=module))
        return descriptor, module

    def test_revision_archives_exact_prior_state_and_changed_files(self):
        self.change_target()
        retained = self.paths["out_dir"] / "cache/go/keep"
        retained.write_text("retained cache\n")
        report = self.revise()
        archive = Path(report["revision_archive"])
        self.assertEqual((archive / "build-state.before.json").read_bytes(), self.before_state)
        self.assertEqual((archive / "target-before/device.mk").read_text(), "# source-only fixture\n")
        self.assertEqual((archive / "target-after/device.mk").read_text(), "# reviewed revision\n")
        self.assertEqual((self.source / build.TARGET / "device.mk").read_text(), "# reviewed revision\n")
        self.assertEqual(retained.read_text(), "retained cache\n")
        self.assertEqual(self.source_file.read_bytes(), self.after)
        self.assertEqual(report["changed_target_files"], ["device.mk"])
        self.assertTrue(report["outputs_preserved"])
        self.assertFalse(report["build_for_this_revision_verified"])
        self.assertFalse(report["flash_admitted"])
        state = json.loads((self.paths["report_dir"] / build.STATE).read_text())
        self.assertEqual(state["previous_build_state_sha256"], build.sha256(self.before_state))
        self.assertEqual(report["build_state_sha256"], self.check()["build_state_sha256"])
        self.assertFalse(any("apply" in call.args[0] for call in self.run_mock.call_args_list))
        self.process_mock.assert_not_called()

    def test_unchanged_revision_is_a_verified_noop(self):
        report = self.revise()
        self.assertTrue(report["already_current"])
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)

    def test_repeating_a_completed_transition_is_idempotent(self):
        self.change_target()
        first = self.revise()
        state = (self.paths["report_dir"] / build.STATE).read_bytes()
        second = self.revise()
        self.assertTrue(second["already_current"])
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), state)
        self.assertEqual(len(list((self.paths["report_dir"] / "build-revisions").iterdir())), 1)
        self.assertEqual(second["build_state_sha256"], first["build_state_sha256"])

    def test_completion_history_failure_does_not_misreport_committed_revision(self):
        self.change_target()
        record = build.twrp_workspace.record_action
        def fail_completion(config, paths, action, report):
            if action == "revise-complete":
                raise OSError("fixture completion-history failure")
            return record(config, paths, action, report)
        with patch.object(build.twrp_workspace, "record_action", side_effect=fail_completion):
            report = self.revise()
        self.assertTrue(report["revision_committed"])
        self.assertFalse(report["completion_report_written"])
        self.assertIn("Revision committed", report["warning"])
        self.assertEqual(report["build_state_sha256"], self.check()["build_state_sha256"])
        self.assertTrue(self.revise()["already_current"])

    def test_wrong_previous_bundle_cannot_authorize_replacement(self):
        self.change_target()
        (self.previous / build.TARGET_SOURCE / "device.mk").write_text("unrecorded previous content\n")
        with self.assertRaisesRegex(ValueError, "identity or controlled sources changed"):
            self.revise()
        self.assertEqual((self.source / build.TARGET / "device.mk").read_text(), "# source-only fixture\n")
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())

    def test_unknown_live_edits_are_never_overwritten(self):
        self.change_target()
        path = self.source / build.TARGET / "device.mk"
        path.write_text("someone else's work\n")
        with self.assertRaisesRegex(ValueError, "Staged Nezha files differ"):
            self.revise()
        self.assertEqual(path.read_text(), "someone else's work\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())

    def test_unknown_source_patch_edits_block_target_revision(self):
        self.change_target()
        self.source_file.write_text("unreviewed source change\n")
        with self.assertRaisesRegex(ValueError, "afterimage differs"):
            self.revise()
        self.assertEqual((self.source / build.TARGET / "device.mk").read_text(), "# source-only fixture\n")

    def test_configuration_and_patch_transitions_are_not_admitted(self):
        self.change_target()
        self.config["note"] = "changed config"
        with self.assertRaisesRegex(ValueError, "unchanged source configuration"):
            self.revise()
        del self.config["note"]
        self.series["scope"] = "changed patch queue"
        self.write_series()
        with self.assertRaisesRegex(ValueError, "exact existing patch queue"):
            self.revise()

    def test_target_file_additions_and_removals_require_separate_review(self):
        path = self.control / build.TARGET_SOURCE / "new.mk"
        path.write_text("new file\n")
        with self.assertRaisesRegex(ValueError, "same file set"):
            self.revise()
        path.unlink()
        (self.control / build.TARGET_SOURCE / "notes.txt").unlink()
        with self.assertRaisesRegex(ValueError, "same file set"):
            self.revise()

    def test_partial_revision_preserves_receipt_backups_and_failure_history(self):
        self.change_target("BoardConfig.mk", "# board revision\n")
        self.change_target()
        replace = build.replace_target_file
        calls = 0
        def fail_second(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise OSError("fixture write failure")
            return replace(*args)
        with patch.object(build, "replace_target_file", side_effect=fail_second), \
                self.assertRaisesRegex(OSError, "fixture write failure"):
            self.revise()
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        failure = json.loads(next(self.paths["report_dir"].glob("revise-failed-*.json")).read_text())
        archive = Path(failure["revision_archive"])
        self.assertEqual((archive / "target-before/BoardConfig.mk").read_text(), "# source-only fixture\n")
        self.assertEqual((archive / "target-before/device.mk").read_text(), "# source-only fixture\n")
        self.assertEqual((self.source / build.TARGET / "BoardConfig.mk").read_text(), "# board revision\n")
        self.assertEqual((self.source / build.TARGET / "device.mk").read_text(), "# source-only fixture\n")
        with self.assertRaisesRegex(ValueError, "Staged Nezha files differ"):
            self.revise()

    def test_file_changed_during_revision_is_preserved(self):
        self.change_target()
        replace = build.replace_target_file
        path = self.source / build.TARGET / "device.mk"
        def concurrent_change(*args):
            path.write_text("concurrent writer\n")
            return replace(*args)
        with patch.object(build, "replace_target_file", side_effect=concurrent_change), \
                self.assertRaisesRegex(ValueError, "File changed during target revision"):
            self.revise()
        self.assertEqual(path.read_text(), "concurrent writer\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)

    def test_receipt_changed_during_revision_is_not_replaced(self):
        self.change_target()
        replace = build.replace_target_file
        receipt = self.paths["report_dir"] / build.STATE
        def concurrent_receipt(*args):
            result = replace(*args)
            receipt.write_text("concurrent receipt owner\n")
            return result
        with patch.object(build, "replace_target_file", side_effect=concurrent_receipt), \
                self.assertRaisesRegex(ValueError, "replacement refused"):
            self.revise()
        self.assertEqual(receipt.read_text(), "concurrent receipt owner\n")
        archive = next((self.paths["report_dir"] / "build-revisions").iterdir())
        self.assertEqual((archive / "build-state.before.json").read_bytes(), self.before_state)

    def test_previous_control_symlinks_and_source_overlap_are_rejected(self):
        linked = self.root / "linked-control"
        linked.symlink_to(self.previous)
        with self.assertRaisesRegex(ValueError, "Symlink"):
            build.revise(self.config, self.paths, "native", linked, self.control)
        with self.assertRaisesRegex(ValueError, "separate from source"):
            build.revise(self.config, self.paths, "native", self.source, self.control)

    def test_supplementary_addition_preserves_immutable_base_and_old_receipt_shape(self):
        descriptor, module = self.supplementary_fixture()
        report = self.revise()
        state = json.loads((self.paths["report_dir"] / build.STATE).read_text())
        self.assertEqual(state["controls"]["supplementary_projects"], descriptor)
        self.assertNotIn("supplementary_projects", json.loads(self.before_state)["controls"])
        self.assertEqual(state["source"], json.loads(self.before_state)["source"])
        self.assertEqual(report["changed_target_files"], [])
        self.assertEqual(module.verify.call_args.kwargs["paths"], self.paths)
        self.assertGreaterEqual(module.verify.call_count, 2)
        self.assertTrue(self.revise()["already_current"])
        self.process_mock.assert_not_called()

    def test_unverified_supplementary_addition_cannot_modify_the_target(self):
        self.change_target()
        _, module = self.supplementary_fixture()
        module.verify.side_effect = ValueError("supplementary checkout is dirty")
        with self.assertRaisesRegex(ValueError, "checkout is dirty"):
            self.revise()
        self.assertEqual((self.source / build.TARGET / "device.mk").read_text(), "# source-only fixture\n")
        self.assertEqual((self.paths["report_dir"] / build.STATE).read_bytes(), self.before_state)
        self.assertFalse((self.paths["report_dir"] / "build-revisions").exists())

    def test_supplementary_source_must_match_exact_base_snapshot(self):
        _, module = self.supplementary_fixture()
        module.verify.return_value = {**module.verify.return_value,
                                      "base": {"project_count": 1, "frozen_manifest_sha256": "0" * 64}}
        with self.assertRaisesRegex(ValueError, "do not match the prepared base"):
            self.revise()

    def test_existing_supplementary_projects_cannot_be_changed_or_removed(self):
        descriptor, _ = self.supplementary_fixture()
        previous = {"supplementary_projects": descriptor}
        with self.assertRaisesRegex(ValueError, "cannot remove"):
            build.validate_supplementary_extension(previous, {})
        changed = copy.deepcopy(descriptor)
        changed["projects"][0]["commit"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "must remain unchanged"):
            build.validate_supplementary_extension(previous, {"supplementary_projects": changed})
        extended = copy.deepcopy(descriptor)
        extended["projects"].append({"path": "system/other", "url": "https://example.org/system/other",
                                      "commit": "f" * 40, "tag": "android-16.0.0_r1", "reason": "another provider"})
        build.validate_supplementary_extension(previous, {"supplementary_projects": extended})

    def test_build_operation_lock_prevents_concurrent_revision(self):
        self.change_target()
        def process(*args, **kwargs):
            with self.assertRaisesRegex(ValueError, "owns the lock"):
                self.revise()
            return SimpleNamespace(returncode=0)
        self.process_mock.side_effect = process
        with redirect_stdout(io.StringIO()):
            result = build.run_build(self.config, self.paths, "graph", "native", 4, "user", self.previous)
        self.assertEqual(result["command_exit_code"], 0)
        self.assertEqual((self.source / build.TARGET / "device.mk").read_text(), "# source-only fixture\n")
        self.assertFalse((self.paths["report_dir"] / "build-operation.lock").exists())

    def test_existing_operation_lock_is_never_automatically_removed(self):
        lock = self.paths["report_dir"] / "build-operation.lock"
        lock.write_text("another or interrupted owner\n")
        with self.assertRaisesRegex(ValueError, "owns the lock"):
            self.revise()
        self.assertEqual(lock.read_text(), "another or interrupted owner\n")


class RealControlTests(unittest.TestCase):
    def test_checked_in_controls_are_valid_and_source_only(self):
        config = build.twrp_workspace.load_config()
        reviewed = build.controls(config)
        self.assertTrue(build.REQUIRED_TARGET.issubset(reviewed["target_files"]))
        self.assertGreaterEqual(len(reviewed["patches"]), 3)

    def test_default_cli_does_not_probe_or_mutate(self):
        with patch.object(build.twrp_workspace, "run", side_effect=AssertionError("process")), \
                patch.object(build.subprocess, "run", side_effect=AssertionError("process")), \
                patch.object(build.twrp_workspace, "require_host", side_effect=AssertionError("host probe")), \
                patch.object(build.twrp_workspace, "write_report", side_effect=AssertionError("write")), \
                redirect_stdout(io.StringIO()) as stdout, redirect_stderr(io.StringIO()):
            result = build.main([])
        self.assertEqual(result, 0)
        self.assertEqual(json.loads(stdout.getvalue())["action"], "plan")
        self.assertEqual(json.loads(stdout.getvalue())["build_environment"]["TARGET_BUILD_VARIANT"], "user")

    def test_revise_requires_explicit_previous_control_bundle(self):
        with redirect_stderr(io.StringIO()) as stderr, \
                patch.object(build.twrp_workspace, "require_host", side_effect=AssertionError("host probe")):
            result = build.main(["revise"])
        self.assertEqual(result, 2)
        self.assertIn("requires --previous-control-root", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
