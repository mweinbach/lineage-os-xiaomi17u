"""Offline recovery-collection safety tests; all device/process calls are mocked."""

import contextlib
import hashlib
import io
import json
from pathlib import Path
import shlex
import stat
import subprocess
import tempfile
import types
import unittest
from unittest import mock

from scripts import collect_recovery as recovery


def command_result(stdout=b"", *, stderr=b"", status="ok", exit_code=0, truncated=()):
    return {
        "stdout": stdout, "stderr": stderr, "status": status, "exit_code": exit_code,
        "truncated_streams": list(truncated), "elapsed_seconds": 0.001,
    }


class RecoveryCollectorTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        patch = mock.patch.object(recovery, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)
        self.output = self.root / "evidence" / "fixture-recovery"
        self.serial = "PRIVATE-DEVICE-SERIAL"
        self.arguments = [
            "--collect", "--serial", self.serial, "--expected-device", "nezha",
            "--output", str(self.output),
        ]
        self.properties = {
            "ro.product.manufacturer": "Xiaomi", "ro.product.device": "nezha",
            "ro.kernel.qemu": "0", "ro.bootmode": "recovery", "ro.boot.mode": "",
            "sys.boot_completed": "", "init.svc.recovery": "running", "ro.twrp.version": "fixture",
        }
        self.state = "recovery"
        self.pstore_names = "console-ramoops-0\ndmesg-ramoops-0\n"

    def fake_adb(self, command, *, timeout, max_bytes):
        self.assertGreater(timeout, 0)
        self.assertLessEqual(timeout, 60)
        self.assertGreater(max_bytes, 0)
        if command == ["adb", "version"]:
            return command_result(b"Android Debug Bridge fixture\n")
        if command == ["adb", "devices", "-l"]:
            return command_result(f"List of devices attached\n{self.serial}\t{self.state} usb:fixture transport_id:7\n".encode())
        self.assertEqual(command[:3], ["adb", "-t", "7"])
        if command[3:] == ["get-state"]:
            return command_result((self.state + "\n").encode())
        if command[3:] == ["features"]:
            return command_result(b"shell_v2,cmd,stat_v2\n")
        self.assertEqual(command[3:5], ["shell", "-T"])
        tokens = shlex.split(command[5])
        if tokens[:1] == ["getprop"]:
            return command_result((self.properties.get(tokens[1], "") + "\n").encode())
        if tokens == ["pidof", "recovery"]:
            return command_result(b"321\n")
        if tokens == ["readlink", "/proc/321/exe"]:
            return command_result(b"/system/bin/recovery\n")
        if tokens == ["getenforce"]:
            return command_result(b"Enforcing\n")
        if tokens == ["ls", "-1", "/sys/fs/pstore"]:
            return command_result(self.pstore_names.encode())
        return command_result(b"fixture recovery diagnostic\n")

    def invoke(self, extra=(), *, effect=None, arguments=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(recovery, "bounded_run", side_effect=effect or self.fake_adb) as process:
            # A forgotten direct subprocess path must fail without ever starting ADB.
            with mock.patch.object(recovery.subprocess, "Popen", side_effect=AssertionError("Unmocked process")):
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    result = recovery.main([*(self.arguments if arguments is None else arguments), *extra])
        return result, stdout.getvalue(), stderr.getvalue(), process

    def manifest(self):
        return json.loads((self.output / "manifest.json").read_text())

    def diagnostic_commands(self, process):
        return [call.args[0][-1] for call in process.call_args_list
                if call.args[0][3:5] == ["shell", "-T"] and
                not shlex.split(call.args[0][-1])[0] in {"getprop", "pidof", "readlink"}]

    def test_default_is_plan_only_without_serial_files_or_adb(self):
        result, stdout, _, process = self.invoke(arguments=[])
        self.assertEqual(result, 0)
        self.assertIn("Plan only", stdout)
        process.assert_not_called()
        self.assertFalse((self.root / "evidence").exists())

    def test_explicit_dry_run_does_not_reveal_serial_or_create_output(self):
        result, stdout, stderr, process = self.invoke(arguments=[
            "--dry-run", "--serial", self.serial, "--expected-device", "nezha", "--include-pstore",
        ])
        self.assertEqual(result, 0)
        self.assertNotIn(self.serial, stdout + stderr)
        self.assertIn("enabled (sensitive, opt in)", stdout)
        process.assert_not_called()
        self.assertFalse((self.root / "evidence").exists())

    def test_selection_without_collect_remains_plan_only(self):
        result, _, _, process = self.invoke(arguments=["--serial", self.serial, "--expected-device", "nezha"])
        self.assertEqual(result, 0)
        process.assert_not_called()

    def test_collection_requires_both_identity_arguments(self):
        for args in (["--collect"], ["--collect", "--serial", self.serial], ["--collect", "--expected-device", "nezha"]):
            with self.subTest(args=args), mock.patch.object(recovery, "bounded_run") as process:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                    recovery.main(args)
                self.assertEqual(exc.exception.code, 2)
                process.assert_not_called()

    def test_invalid_arguments_are_rejected_without_execution(self):
        extras = [
            ["--serial", "SERIAL;reboot"], ["--serial", "192.0.2.1:5555"],
            ["--serial", "emulator-5554"], ["--serial", "adb-a._adb-tls-connect._tcp"],
            ["--expected-device", "other-phone"], ["--expected-device", "nezha;id"],
            ["--timeout", "0"], ["--timeout", "nan"], ["--timeout", "61"],
            ["--total-timeout", "inf"], ["--total-timeout", "901"], ["--total-timeout", "0"],
            ["--max-bytes", "4095"], ["--max-bytes", "4194305"], ["--dry-run"],
        ]
        for extra in extras:
            with self.subTest(extra=extra), mock.patch.object(recovery, "bounded_run") as process:
                error = io.StringIO()
                with contextlib.redirect_stderr(error), self.assertRaises(SystemExit):
                    recovery.main([*self.arguments, *extra])
                process.assert_not_called()
                self.assertNotIn(self.serial, error.getvalue())

    def test_success_writes_private_hashed_receipts_and_pins_transport(self):
        result, stdout, stderr, process = self.invoke()
        self.assertEqual(result, 0, stderr)
        manifest = self.manifest()
        self.assertEqual(manifest["status"], "complete")
        self.assertTrue(manifest["recovery_preflight_passed"])
        self.assertEqual(manifest["device"]["serial"], self.serial)
        self.assertEqual(manifest["device"]["transport_id"], "7")
        self.assertTrue(manifest["device"]["shell_v2_verified"])
        self.assertNotIn(self.serial, stdout + stderr)
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        for entry in self.output.rglob("*"):
            self.assertEqual(stat.S_IMODE(entry.stat().st_mode), 0o700 if entry.is_dir() else 0o600)
        self.assertEqual((self.output / ".gitignore").read_text(), "*\n!.gitignore\n")
        for receipt in manifest["artifacts"]:
            data = (self.output / receipt["path"]).read_bytes()
            self.assertEqual(receipt["bytes"], len(data))
            self.assertEqual(receipt["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(manifest["captured_output_bytes"], sum(item["bytes"] for item in manifest["artifacts"]))
        for call in process.call_args_list[2:]:
            self.assertEqual(call.args[0][:3], ["adb", "-t", "7"])
        self.assertFalse(any("pstore" in command for command in self.diagnostic_commands(process)))

    def test_plan_and_success_never_print_selected_serial_even_in_output_path(self):
        self.output = self.root / "evidence" / self.serial
        self.arguments[-1] = str(self.output)
        result, stdout, stderr, _ = self.invoke()
        self.assertEqual(result, 0)
        self.assertNotIn(self.serial, stdout + stderr)

    def test_output_must_stay_in_ignored_evidence_and_never_reuse_existing(self):
        outside = self.root / "outside"
        for output in (outside, self.root / "evidence", self.root / "evidence" / ".." / "outside"):
            with self.subTest(output=output):
                result, _, _, process = self.invoke(["--output", str(output)])
                self.assertEqual(result, 2)
                process.assert_not_called()
        self.output.mkdir(parents=True)
        (self.output / "keep.txt").write_text("keep")
        result, _, _, process = self.invoke()
        self.assertEqual(result, 2)
        process.assert_not_called()
        self.assertEqual((self.output / "keep.txt").read_text(), "keep")

    def test_evidence_symlink_is_refused_without_reading_or_writing_target(self):
        target = self.root / "private-outside"
        target.mkdir()
        (self.root / "evidence").symlink_to(target, target_is_directory=True)
        result, _, _, process = self.invoke()
        self.assertEqual(result, 2)
        process.assert_not_called()
        self.assertEqual(list(target.iterdir()), [])

    def test_unauthorized_offline_sideload_or_missing_device_is_refused(self):
        for state in ("unauthorized", "offline", "sideload", "no permissions", "bootloader"):
            with self.subTest(state=state):
                self.output = self.root / "evidence" / state.replace(" ", "-")
                self.arguments[-1] = str(self.output)
                self.state = state
                result, _, _, process = self.invoke()
                self.assertEqual(result, 2)
                self.assertEqual(process.call_count, 2)
                self.assertEqual(self.manifest()["status"], "preflight_failed")

    def test_multiple_devices_never_change_explicit_selection(self):
        def effect(command, **kwargs):
            if command == ["adb", "devices", "-l"]:
                return command_result(f"OTHER\tdevice transport_id:6\n{self.serial}\trecovery transport_id:7\n".encode())
            return self.fake_adb(command, **kwargs)
        result, _, _, process = self.invoke(effect=effect)
        self.assertEqual(result, 0)
        self.assertTrue(all(call.args[0][2] == "7" for call in process.call_args_list[2:]))

    def test_disconnect_does_not_fall_back_to_serial_or_other_device(self):
        def effect(command, **kwargs):
            if command[3:] == ["get-state"]:
                return command_result(stderr=b"transport not found", status="failed", exit_code=1)
            return self.fake_adb(command, **kwargs)
        result, _, _, process = self.invoke(effect=effect)
        self.assertEqual(result, 2)
        self.assertEqual(process.call_count, 3)
        self.assertFalse(any("-s" in call.args[0] for call in process.call_args_list))

    def test_shell_v2_support_is_required_before_trusting_read_exit_codes(self):
        for index, features in enumerate((b"cmd,stat_v2", b"not_shell_v2", b"")):
            with self.subTest(features=features):
                self.output = self.root / "evidence" / f"legacy-shell-{index}"
                self.arguments[-1] = str(self.output)
                def effect(command, **kwargs):
                    if command[3:] == ["features"]:
                        return command_result(features)
                    return self.fake_adb(command, **kwargs)
                result, _, _, process = self.invoke(effect=effect)
                self.assertEqual(result, 2)
                self.assertEqual(process.call_count, 4)
                self.assertFalse(self.diagnostic_commands(process))
                self.assertFalse(any(call.args[0][3:5] == ["shell", "-T"] for call in process.call_args_list))

    def test_wrong_identity_emulator_normal_android_or_stopped_recovery_blocks_logs(self):
        cases = [
            ("ro.product.manufacturer", "OtherOEM"), ("ro.product.device", "popsicle"),
            ("ro.kernel.qemu", "1"), ("ro.bootmode", "normal"),
            ("ro.boot.mode", "normal"), ("sys.boot_completed", "1"),
            ("init.svc.recovery", "stopped"),
        ]
        for index, (name, value) in enumerate(cases):
            with self.subTest(name=name):
                self.output = self.root / "evidence" / f"gate-{index}"
                self.arguments[-1] = str(self.output)
                with mock.patch.dict(self.properties, {name: value}):
                    result, _, _, process = self.invoke()
                self.assertEqual(result, 2)
                self.assertEqual(self.manifest()["status"], "preflight_failed")
                self.assertFalse(self.diagnostic_commands(process))

    def test_device_adb_state_is_accepted_only_with_recovery_boot_marker(self):
        self.state = "device"
        result, _, _, _ = self.invoke()
        self.assertEqual(result, 0)
        self.output = self.root / "evidence" / "unmarked-device"
        self.arguments[-1] = str(self.output)
        self.properties["ro.bootmode"] = ""
        result, _, _, process = self.invoke()
        self.assertEqual(result, 2)
        self.assertFalse(self.diagnostic_commands(process))

    def test_recovery_process_and_executable_are_required_not_just_properties(self):
        for index, (target, output) in enumerate((
            ("pidof recovery", b""), ("pidof recovery", b"321 456"),
            ("pidof recovery", b"321;id"), ("readlink /proc/321/exe", b"/data/local/tmp/recovery"),
            ("readlink /proc/321/exe", b"/system/bin/recovery (deleted)"),
        )):
            with self.subTest(target=target, output=output):
                self.output = self.root / "evidence" / f"process-{index}"
                self.arguments[-1] = str(self.output)
                def effect(command, **kwargs):
                    if command[-1] == target:
                        return command_result(output)
                    return self.fake_adb(command, **kwargs)
                result, _, _, process = self.invoke(effect=effect)
                self.assertEqual(result, 2)
                self.assertFalse(self.diagnostic_commands(process))

    def test_denied_or_truncated_preflight_never_reads_diagnostics(self):
        def effect(command, **kwargs):
            if command[-1] == "getprop ro.bootmode":
                return command_result(b"recovery", status="byte_limit", exit_code=None, truncated=["stdout"])
            return self.fake_adb(command, **kwargs)
        result, _, _, process = self.invoke(effect=effect)
        self.assertEqual(result, 2)
        self.assertFalse(self.diagnostic_commands(process))

    def test_partial_reads_keep_hashes_exit_codes_and_continue(self):
        cases = [
            ("permission_denied", 1, b"", b"Operation not permitted", []),
            ("timeout", None, b"partial kernel log", b"", []),
            ("byte_limit", None, b"capped kernel log", b"", ["stdout"]),
            ("missing", 1, b"", b"No such file or directory", []),
        ]
        for index, (status, exit_code, output, error, truncated) in enumerate(cases):
            with self.subTest(status=status):
                self.output = self.root / "evidence" / f"partial-{index}"
                self.arguments[-1] = str(self.output)
                def effect(command, **kwargs):
                    if command[-1] == "dmesg":
                        return command_result(output, stderr=error, status=status, exit_code=exit_code, truncated=truncated)
                    return self.fake_adb(command, **kwargs)
                result, stdout, _, _ = self.invoke(effect=effect)
                self.assertEqual(result, 3)
                manifest = self.manifest()
                self.assertEqual(manifest["status"], "partial")
                record = next(item for item in manifest["commands"] if item["label"] == "dmesg")
                self.assertEqual(record["status"], status)
                self.assertEqual(record["exit_code"], exit_code)
                self.assertEqual(record["truncated_streams"], truncated)
                self.assertEqual((self.output / record["stdout"]).read_bytes(), output)
                self.assertEqual((self.output / record["stderr"]).read_bytes(), error)
                self.assertTrue(any(item["label"] == "mounts" for item in manifest["commands"]))
                self.assertIn("Do not escalate to root", stdout)

    def test_selinux_non_enforcing_is_recorded_without_changing_it(self):
        def effect(command, **kwargs):
            if command[-1] == "getenforce":
                return command_result(b"Permissive\n")
            return self.fake_adb(command, **kwargs)
        result, stdout, _, process = self.invoke(effect=effect)
        self.assertEqual(result, 0)
        self.assertTrue(self.manifest()["warnings"])
        self.assertIn("Security observations need review", stdout)
        self.assertFalse(any("setenforce" in str(call) for call in process.call_args_list))

    def test_pstore_opt_in_reads_only_allowlisted_files_with_no_symlink_follow(self):
        self.pstore_names += "pmsg-ramoops-0\n../../../data/secrets\nconsole-ramoops-0;id\nconsole-ramoops-0\n"
        result, _, _, _ = self.invoke(["--include-pstore"])
        self.assertEqual(result, 0)
        manifest = self.manifest()
        records = [item for item in manifest["commands"] if item["label"].startswith("pstore-") and item["label"] != "pstore-inventory"]
        self.assertEqual(len(records), 2)
        self.assertEqual(manifest["skipped"][0]["count"], 3)
        for record in records:
            self.assertIn("[ -L /sys/fs/pstore/", record["argv"][-1])
            self.assertTrue(recovery.safe_pstore_name(record["remote_argv"][-1].split("/")[-1]))
            self.assertNotIn("pull", record["argv"])

    def test_pstore_file_count_limit_is_partial_and_not_unrestricted(self):
        self.pstore_names = "\n".join(f"dmesg-ramoops-{index}" for index in range(20))
        result, _, _, _ = self.invoke(["--include-pstore"])
        self.assertEqual(result, 3)
        records = [item for item in self.manifest()["commands"] if item["label"].startswith("pstore-dmesg-")]
        self.assertEqual(len(records), recovery.MAX_PSTORE_FILES)

    def test_interrupt_retains_partial_command_and_marks_manifest(self):
        def effect(command, **kwargs):
            if command[-1] == "dmesg":
                return command_result(b"before interruption", status="interrupted", exit_code=None)
            return self.fake_adb(command, **kwargs)
        result, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 130)
        manifest = self.manifest()
        self.assertEqual(manifest["status"], "interrupted")
        record = next(item for item in manifest["commands"] if item["label"] == "dmesg")
        self.assertEqual((self.output / record["stdout"]).read_bytes(), b"before interruption")

    def test_interrupted_manifest_write_can_still_save_final_interrupted_status(self):
        make_file = recovery.tempfile.NamedTemporaryFile
        files = []
        def temporary_file(**kwargs):
            stream = make_file(**kwargs)
            files.append(stream.name)
            if len(files) == 2:
                write = stream.write
                def interrupt_write(content):
                    write(content[:20])
                    raise KeyboardInterrupt
                stream.write = interrupt_write
            return stream
        with mock.patch.object(recovery.tempfile, "NamedTemporaryFile", side_effect=temporary_file):
            result, _, _, _ = self.invoke()
        self.assertEqual(result, 130)
        self.assertEqual(self.manifest()["status"], "interrupted")
        self.assertTrue(all(not Path(path).exists() for path in files))
        self.assertEqual(list(self.output.glob(".manifest-*.tmp")), [])

    def test_interrupted_preflight_and_missing_adb_are_recorded(self):
        for index, status in enumerate(("interrupted", "unavailable")):
            with self.subTest(status=status):
                self.output = self.root / "evidence" / f"unavailable-{index}"
                self.arguments[-1] = str(self.output)
                result, stdout, stderr, process = self.invoke(effect=lambda *a, **k: command_result(status=status, exit_code=None))
                self.assertEqual(result, 130 if status == "interrupted" else 2)
                self.assertEqual(self.manifest()["status"], "interrupted" if status == "interrupted" else "preflight_failed")
                self.assertEqual(process.call_count, 1)
                self.assertNotIn(self.serial, stdout + stderr)

    def test_session_time_budget_stops_without_additional_process(self):
        args = recovery.parser().parse_args(self.arguments)
        collector = recovery.Collector(args)
        with mock.patch.object(collector, "preflight") as preflight:
            def expire():
                collector.verified = True
                collector.transport_id = "7"
                collector.deadline = 0
            preflight.side_effect = expire
            with mock.patch.object(recovery, "bounded_run") as process:
                self.assertEqual(collector.collect(), 3)
                process.assert_not_called()
        self.assertEqual(collector.manifest["status"], "partial")
        self.assertIn("limit", collector.manifest["errors"][0])

    def test_session_byte_budget_is_enforced_before_process(self):
        def effect(command, **kwargs):
            result = self.fake_adb(command, **kwargs)
            for stream in ("stdout", "stderr"):
                if len(result[stream]) > kwargs["max_bytes"]:
                    result[stream] = result[stream][:kwargs["max_bytes"]]
                    result["status"], result["exit_code"] = "byte_limit", None
                    result["truncated_streams"].append(stream)
            return result
        with mock.patch.object(recovery, "MAX_SESSION_BYTES", 128):
            result, _, _, process = self.invoke(effect=effect)
        self.assertEqual(result, 2)
        self.assertLessEqual(self.manifest()["captured_output_bytes"], 128)
        self.assertLessEqual(process.call_count, 3)

    def test_consumed_session_byte_budget_never_starts_another_read(self):
        args = recovery.parser().parse_args(self.arguments)
        collector = recovery.Collector(args)
        collector.transport_id = "7"
        collector.verified = True
        collector.captured_bytes = recovery.MAX_SESSION_BYTES - 1
        with mock.patch.object(recovery, "bounded_run") as process:
            with self.assertRaises(recovery.SessionLimit):
                collector.shell("dmesg", ("dmesg",))
            process.assert_not_called()

    def test_diagnostics_cannot_use_shell_interface_before_recovery_verification(self):
        args = recovery.parser().parse_args(self.arguments)
        collector = recovery.Collector(args)
        collector.transport_id = "7"
        with mock.patch.object(recovery, "bounded_run") as process:
            with self.assertRaises(recovery.CollectionError):
                collector.shell("dmesg", ("dmesg",))
            process.assert_not_called()

    def test_only_explicit_properties_and_read_commands_are_issued(self):
        result, _, _, process = self.invoke(["--include-pstore"])
        self.assertEqual(result, 0)
        forbidden = {"root", "unroot", "reboot", "remount", "mount", "umount", "push", "pull", "su", "dd", "setprop", "setenforce", "twrp", "fastboot", "rm", "wipe", "decrypt", "sideload", "connect", "disconnect"}
        for call in process.call_args_list:
            command = call.args[0]
            if command[3:5] == ["shell", "-T"]:
                tokens = shlex.split(command[-1])
                self.assertFalse(forbidden.intersection(tokens), tokens)
                if tokens[0] == "getprop":
                    self.assertEqual(len(tokens), 2)
                    self.assertIn(tokens[1], recovery.IDENTITY_PROPERTIES + recovery.MODE_PROPERTIES + recovery.PROPERTIES)
                self.assertFalse(any("/data/" in token or "ro.serialno" in token or "ro.boot.serialno" in token for token in tokens))
                if tokens[0] == "logcat":
                    self.assertIn("-d", tokens)
                    self.assertIn("-t", tokens)
                    self.assertIn("*:S", tokens)
                    self.assertNotIn("-c", tokens)


class ReadAllowlistTests(unittest.TestCase):
    def test_unrestricted_commands_and_properties_are_refused(self):
        for tokens in (
            ("getprop",), ("getprop", "ro.serialno"), ("getprop", "ro.boot.serialno"),
            ("setprop", "ro.bootmode", "recovery"), ("twrp", "decrypt", "secret"),
            ("logcat", "-c"), ("dmesg", "-c"), ("mount",), ("cat", "/data/system/secret"),
            ("tail", "-c", "1024", "/data/media/0/photo.jpg"),
            ("tail", "-c", "1024", "/sys/fs/pstore/../secret"),
            ("tail", "-c", "1024", "/sys/fs/pstore/pmsg-ramoops-0"),
            ("tail", "-c", "1024;id", "/tmp/recovery.log"),
            ("readlink", "/proc/321;id/exe"),
        ):
            with self.subTest(tokens=tokens), self.assertRaises(recovery.CollectionError):
                recovery.remote_command(tokens)

    def test_logcat_wildcards_are_quoted_for_remote_shell(self):
        command = recovery.remote_command(recovery.LOGCAT_COMMAND)
        self.assertIn("'*:S'", command)
        self.assertIn("'recovery:*'", command)
        self.assertEqual(shlex.split(command), list(recovery.LOGCAT_COMMAND))

    def test_diagnostic_files_are_guarded_without_fabricating_permission_errors(self):
        command = recovery.remote_command(("tail", "-c", "4096", "/tmp/recovery.log"))
        self.assertIn("[ -L /tmp/recovery.log ]", command)
        self.assertIn("[ -e /tmp/recovery.log ] && [ ! -f /tmp/recovery.log ]", command)
        self.assertNotIn("No such file", command)

    def test_selected_transport_requires_exact_unique_identity_and_transport(self):
        invalid = (
            "OTHER\tdevice transport_id:1\n", "A\tdevice\n", "A\trecovery transport_id:0\n",
            "A\tdevice transport_id:1 transport_id:2\n", "A\tdevice transport_id:1\nA\tdevice transport_id:2\n",
            "A\tdevice transport_id:$(id)\n", "A\tunauthorized transport_id:1\n",
        )
        for inventory in invalid:
            with self.subTest(inventory=inventory), self.assertRaises(recovery.CollectionError):
                recovery.selected_transport(inventory, "A")
        self.assertEqual(recovery.selected_transport("* daemon started\nList of devices attached\nA\trecovery transport_id:4\n", "A"), ("recovery", "4"))


class FakePipe:
    def __init__(self, descriptor):
        self.descriptor = descriptor
        self.closed = False

    def fileno(self):
        return self.descriptor

    def close(self):
        self.closed = True


class FakeSelector:
    def __init__(self):
        self.keys = {}
        self.closed = False

    def register(self, stream, _events, name):
        self.keys[stream.fileno()] = types.SimpleNamespace(fileobj=stream, data=name)

    def unregister(self, stream):
        self.keys.pop(stream.fileno())

    def get_map(self):
        return self.keys

    def select(self, *, timeout):
        return [(key, 1) for key in list(self.keys.values())]

    def close(self):
        self.closed = True


class BoundedProcessTests(unittest.TestCase):
    def run_fake(self, stdout, stderr=b"", *, max_bytes=16, returncode=0, interrupt=False, ticks=None, wait_timeout=False):
        pipes = {101: bytearray(stdout), 102: bytearray(stderr)}
        process = mock.Mock()
        process.stdout, process.stderr = FakePipe(101), FakePipe(102)
        process.poll.return_value = None
        waits = []
        def wait(*, timeout):
            waits.append(timeout)
            if wait_timeout and len(waits) == 1:
                raise subprocess.TimeoutExpired(["adb", "version"], timeout)
            process.poll.return_value = returncode
            return returncode
        process.wait.side_effect = wait
        selector = FakeSelector()
        reads = []
        def read(descriptor, size):
            reads.append(size)
            if interrupt and len(reads) > 1:
                raise KeyboardInterrupt
            content = bytes(pipes[descriptor][:size])
            del pipes[descriptor][:size]
            return content
        with mock.patch.object(recovery.subprocess, "Popen", return_value=process) as popen:
            with mock.patch.object(recovery.selectors, "DefaultSelector", return_value=selector):
                with mock.patch.object(recovery.os, "read", side_effect=read):
                    with mock.patch.object(recovery.time, "monotonic", side_effect=ticks or (lambda: 0)):
                        result = recovery.bounded_run(["adb", "version"], timeout=1, max_bytes=max_bytes)
        self.assertTrue(selector.closed)
        self.assertTrue(process.stdout.closed and process.stderr.closed)
        self.assertIs(popen.call_args.kwargs["shell"], False)
        self.assertEqual(popen.call_args.kwargs["stdin"], subprocess.DEVNULL)
        return result, process, reads

    def test_both_streams_are_drained_and_exact_size_is_not_marked_truncated(self):
        result, process, reads = self.run_fake(b"s" * 16, b"e" * 16)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["stdout"], b"s" * 16)
        self.assertEqual(result["stderr"], b"e" * 16)
        self.assertEqual(result["truncated_streams"], [])
        self.assertLessEqual(max(reads), 17)
        process.kill.assert_not_called()

    def test_stdout_limit_stops_client_and_never_buffers_excess(self):
        result, process, reads = self.run_fake(b"s" * 10000)
        self.assertEqual(result["status"], "byte_limit")
        self.assertEqual(result["stdout"], b"s" * 16)
        self.assertEqual(result["truncated_streams"], ["stdout"])
        self.assertIsNone(result["exit_code"])
        process.kill.assert_called_once()
        self.assertEqual(reads, [17])

    def test_stderr_limit_is_independent(self):
        result, process, _ = self.run_fake(b"small", b"e" * 10000)
        self.assertEqual(result["status"], "byte_limit")
        self.assertEqual(result["stdout"], b"small")
        self.assertEqual(result["stderr"], b"e" * 16)
        self.assertEqual(result["truncated_streams"], ["stderr"])
        process.kill.assert_called_once()

    def test_timeout_stops_client_with_bounded_cleanup(self):
        result, process, reads = self.run_fake(b"unread", ticks=[0, 2, 2])
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(reads, [])
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_args.kwargs["timeout"], 1)

    def test_client_that_closes_pipes_but_keeps_running_is_also_timed_out(self):
        result, process, _ = self.run_fake(b"finished output", wait_timeout=True)
        self.assertEqual(result["status"], "timeout")
        self.assertEqual(result["stdout"], b"finished output")
        self.assertIsNone(result["exit_code"])
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_args.kwargs["timeout"], 1)

    def test_interrupt_preserves_already_read_output(self):
        result, process, _ = self.run_fake(b"before interrupt", interrupt=True)
        self.assertEqual(result["status"], "interrupted")
        self.assertEqual(result["stdout"], b"before interrupt")
        process.kill.assert_called_once()

    def test_denied_and_missing_reads_keep_actual_exit_code(self):
        for error, status in ((b"Permission denied", "permission_denied"), (b"Operation not permitted", "permission_denied"), (b"No such file or directory", "missing")):
            with self.subTest(error=error):
                result, _, _ = self.run_fake(b"", error, max_bytes=100, returncode=1)
                self.assertEqual(result["status"], status)
                self.assertEqual(result["exit_code"], 1)
                self.assertEqual(result["stderr"], error)

    def test_missing_executable_has_no_spawn_or_unbounded_error_buffer(self):
        with mock.patch.object(recovery.subprocess, "Popen", side_effect=FileNotFoundError("x" * 1000)):
            result = recovery.bounded_run(["missing-adb"], timeout=1, max_bytes=16)
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(len(result["stderr"]), 16)
        self.assertEqual(result["truncated_streams"], ["stderr"])


if __name__ == "__main__":
    unittest.main()
