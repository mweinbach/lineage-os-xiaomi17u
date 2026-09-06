"""Offline safety and provenance tests; no ADB server or phone is required."""

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock


SPEC = importlib.util.spec_from_file_location(
    "collect_stock", Path(__file__).resolve().parents[1] / "scripts" / "collect_stock.py"
)
stock = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(stock)


class StockCollectorTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.output = Path(self.temporary.name) / "private-evidence"
        self.serial = "PRIVATE-DEVICE-SERIAL"
        self.codename = "fixture_phone"
        self.arguments = [
            "--serial", self.serial, "--expected-device", self.codename,
            "--output", str(self.output),
        ]

    def fake_adb(self, command, **kwargs):
        self.assertIsInstance(command, list)
        self.assertIs(kwargs["shell"], False)
        self.assertFalse(kwargs["check"])
        self.assertGreater(kwargs["timeout"], 0)
        if command[1:] == ["version"]:
            return subprocess.CompletedProcess(command, 0, b"Android Debug Bridge fixture\n", b"")
        if command[1:] == ["devices", "-l"]:
            output = f"List of devices attached\n{self.serial}\tdevice usb:fixture product:fixture model:Fixture\n"
            return subprocess.CompletedProcess(command, 0, output.encode(), b"")
        self.assertEqual(command[1:3], ["-s", self.serial])
        arguments = command[3:]
        if arguments[:2] == ["shell", "getprop"]:
            properties = {
                "ro.product.manufacturer": "Xiaomi",
                "ro.product.device": self.codename,
                "ro.kernel.qemu": "0",
                "ro.product.model": "Fixture stock phone",
            }
            output = properties.get(arguments[2], "") + "\n"
        elif arguments == ["shell", "pm", "list", "packages", "-s", "-f"]:
            output = "package:/product/priv-app/MiuiCamera/MiuiCamera.apk=com.android.camera\n"
        elif arguments == ["shell", "pm", "path", "com.android.camera"]:
            output = "package:/product/priv-app/MiuiCamera/MiuiCamera.apk\n"
        elif arguments[0] == "pull":
            source, destination = arguments[1:]
            destination = Path(destination)
            if source.endswith(".apk"):
                destination.write_bytes(b"private-fixture-apk")
            else:
                destination.mkdir()
                (destination / "fixture.xml").write_text("<manifest/>\n", encoding="utf-8")
            output = "1 file pulled\n"
        else:
            output = "fixture read-only output\n"
        return subprocess.CompletedProcess(command, 0, output.encode(), b"")

    def invoke(self, extra=(), effect=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        with mock.patch.object(stock.subprocess, "run", side_effect=effect or self.fake_adb) as process:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                result = stock.main([*self.arguments, *extra])
        return result, stdout.getvalue(), stderr.getvalue(), process

    def manifest(self):
        return json.loads((self.output / "manifest.json").read_text(encoding="utf-8"))

    def test_dry_run_never_executes_or_creates_output_and_redacts_serial(self):
        result, stdout, stderr, process = self.invoke(["--dry-run", "--include-dumpsys", "--pull-stock-apks"])
        self.assertEqual(result, 0)
        process.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertNotIn(self.serial, stdout + stderr)
        self.assertIn("no ADB commands", stdout)
        self.assertIn("enabled (sensitive)", stdout)

    def test_serial_and_expected_device_are_required(self):
        for arguments in ([], ["--serial", "a"], ["--expected-device", "b"]):
            with self.subTest(arguments=arguments), mock.patch.object(stock.subprocess, "run") as process:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                    stock.main([*arguments, "--dry-run"])
                self.assertEqual(exc.exception.code, 2)
                process.assert_not_called()

    def test_feature_dry_run_lists_observations_without_accessing_phone(self):
        result, stdout, _, process = self.invoke(["--dry-run", "--feature-diagnostics"])
        self.assertEqual(result, 0)
        process.assert_not_called()
        self.assertFalse(self.output.exists())
        self.assertIn("observations only", stdout)
        self.assertIn("dumpsys telephony_ims", stdout)
        self.assertIn("android:bool/config_automatic_brightness_available", stdout)
        self.assertNotIn(self.serial, stdout)

    def test_feature_diagnostics_are_explicit_private_and_read_only(self):
        result, _, _, process = self.invoke(["--feature-diagnostics", "--include-dumpsys"])
        self.assertEqual(result, 0)
        manifest = self.manifest()
        self.assertTrue(manifest["options"]["feature_diagnostics"])
        commands = [call.args[0][3:] for call in process.call_args_list if call.args[0][1:3] == ["-s", self.serial]]
        for label, command in stock.FEATURE_READ_COMMANDS:
            self.assertEqual(commands.count(["shell", *command]), 1, label)
        for service in stock.DUMPSYS_SERVICES:
            self.assertEqual(commands.count(["shell", "dumpsys", service]), 1)
        forbidden = {"root", "reboot", "remount", "setprop", "install", "uninstall", "push",
                     "su", "settings", "--reset", "--enable", "--disable", "call"}
        self.assertFalse(any(forbidden.intersection(command) for command in commands))
        for artifact in manifest["artifacts"]:
            self.assertEqual(stat.S_IMODE((self.output / artifact["path"]).stat().st_mode), 0o600)

    def test_feature_failure_preserves_partial_result_and_continues(self):
        def effect(command, **kwargs):
            if command[3:] == ["shell", "dumpsys", "telephony_ims"]:
                return subprocess.CompletedProcess(command, 1, b"", b"service unavailable")
            return self.fake_adb(command, **kwargs)
        result, _, _, _ = self.invoke(["--feature-diagnostics"], effect=effect)
        self.assertEqual(result, 3)
        manifest = self.manifest()
        self.assertEqual(manifest["status"], "partial")
        records = {row["label"]: row for row in manifest["commands"]}
        self.assertEqual(records["feature-ims"]["status"], "failed")
        self.assertEqual(records["feature-vibrator"]["status"], "ok")

    def test_rejects_invalid_serial_before_execution(self):
        self.arguments[1] = "SERIAL;reboot"
        with mock.patch.object(stock.subprocess, "run") as process:
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr), self.assertRaises(SystemExit):
                stock.main(self.arguments)
            process.assert_not_called()
            self.assertNotIn("SERIAL;reboot", stderr.getvalue())

    def test_rejects_invalid_codename_and_timeout(self):
        for extra in (["--expected-device", "$(id)"], ["--timeout", "0"], ["--timeout", "nan"], ["--timeout", "601"]):
            with self.subTest(extra=extra), mock.patch.object(stock.subprocess, "run") as process:
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    stock.main([*self.arguments, *extra])
                process.assert_not_called()

    def test_apk_package_requires_opt_in(self):
        with mock.patch.object(stock.subprocess, "run") as process:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                stock.main([*self.arguments, "--apk-package", "com.miui.gallery"])
            process.assert_not_called()

    def test_arbitrary_package_is_not_allowlisted(self):
        with mock.patch.object(stock.subprocess, "run") as process:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                stock.main([*self.arguments, "--pull-stock-apks", "--apk-package", "org.example.privateapp"])
            process.assert_not_called()

    def test_success_records_private_hashes_and_explicit_device_selection(self):
        result, stdout, stderr, process = self.invoke()
        self.assertEqual(result, 0)
        self.assertNotIn(self.serial, stdout + stderr)
        manifest = self.manifest()
        self.assertEqual(manifest["status"], "complete")
        self.assertEqual(manifest["device"]["serial"], self.serial)
        self.assertEqual(manifest["device"]["codename"], self.codename)
        self.assertTrue(manifest["completed_at"])
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((self.output / "manifest.json").stat().st_mode), 0o600)
        for artifact in manifest["artifacts"]:
            path = self.output / artifact["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), artifact["sha256"])
            self.assertEqual(path.stat().st_size, artifact["bytes"])
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertTrue(all(record["exit_code"] == 0 for record in manifest["commands"]))
        for call in process.call_args_list:
            arguments = call.args[0]
            if arguments[1:] not in (["version"], ["devices", "-l"]):
                self.assertEqual(arguments[1:3], ["-s", self.serial])

    def test_default_commands_are_allowlisted_and_have_no_mutations_or_logs(self):
        result, _, _, process = self.invoke()
        self.assertEqual(result, 0)
        self.assertFalse(self.manifest()["options"]["feature_diagnostics"])
        self.assertFalse(any(row["label"].startswith("feature-") for row in self.manifest()["commands"]))
        forbidden = {"root", "reboot", "remount", "install", "uninstall", "push", "logcat", "bugreport", "dumpsys", "su", "settings", "fastboot"}
        for call in process.call_args_list:
            arguments = call.args[0]
            self.assertFalse(forbidden.intersection(arguments))
            if "getprop" in arguments:
                self.assertIn(arguments[-1], stock.IDENTITY_PROPERTIES + stock.PROPERTIES)
                self.assertNotIn(arguments[-1], {"ro.serialno", "ro.boot.serialno"})
            if "pull" in arguments:
                self.assertIn(arguments[-2], stock.METADATA_DIRECTORIES)

    def test_existing_output_is_never_reused(self):
        self.output.mkdir()
        (self.output / "keep.txt").write_text("existing evidence")
        result, _, _, process = self.invoke()
        self.assertEqual(result, 2)
        process.assert_not_called()
        self.assertEqual((self.output / "keep.txt").read_text(), "existing evidence")

    def test_absent_selected_device_does_not_choose_other_phone(self):
        def effect(command, **kwargs):
            if command[1:] == ["devices", "-l"]:
                return subprocess.CompletedProcess(command, 0, b"List of devices attached\nOTHER\tdevice\n", b"")
            return self.fake_adb(command, **kwargs)
        result, stdout, stderr, process = self.invoke(effect=effect)
        self.assertEqual(result, 2)
        self.assertEqual(process.call_count, 2)
        self.assertEqual(self.manifest()["status"], "preflight_failed")
        self.assertNotIn(self.serial, stdout + stderr)

    def test_unauthorized_and_offline_devices_are_refused(self):
        for state in ("unauthorized", "offline", "no permissions"):
            with self.subTest(state=state):
                self.output = Path(self.temporary.name) / state.replace(" ", "-")
                self.arguments[-1] = str(self.output)
                def effect(command, **kwargs):
                    if command[1:] == ["devices", "-l"]:
                        return subprocess.CompletedProcess(command, 0, f"{self.serial}\t{state}\n".encode(), b"")
                    return self.fake_adb(command, **kwargs)
                result, _, _, process = self.invoke(effect=effect)
                self.assertEqual(result, 2)
                self.assertEqual(process.call_count, 2)

    def test_wrong_manufacturer_or_codename_stops_before_collection(self):
        for property_name, value in (("ro.product.manufacturer", "OtherOEM"), ("ro.product.device", "wrong_phone")):
            with self.subTest(property_name=property_name):
                self.output = Path(self.temporary.name) / property_name
                self.arguments[-1] = str(self.output)
                def effect(command, **kwargs):
                    if command[-3:] == ["shell", "getprop", property_name]:
                        return subprocess.CompletedProcess(command, 0, value.encode(), b"")
                    return self.fake_adb(command, **kwargs)
                result, _, _, process = self.invoke(effect=effect)
                self.assertEqual(result, 2)
                self.assertEqual(process.call_count, 5)
                self.assertEqual(self.manifest()["status"], "preflight_failed")

    def test_emulator_is_refused_even_if_properties_claim_xiaomi(self):
        def effect(command, **kwargs):
            if command[-3:] == ["shell", "getprop", "ro.kernel.qemu"]:
                return subprocess.CompletedProcess(command, 0, b"1\n", b"")
            return self.fake_adb(command, **kwargs)
        result, _, _, process = self.invoke(effect=effect)
        self.assertEqual(result, 2)
        self.assertEqual(process.call_count, 5)

    def test_adb_missing_has_manifest_and_redacted_error(self):
        result, stdout, stderr, _ = self.invoke(effect=FileNotFoundError("No adb"))
        self.assertEqual(result, 2)
        self.assertEqual(self.manifest()["commands"][0]["status"], "unavailable")
        self.assertEqual(self.manifest()["status"], "preflight_failed")
        self.assertNotIn(self.serial, stdout + stderr)

    def test_timeout_retains_partial_output_and_reports_partial(self):
        def effect(command, **kwargs):
            if command[-2:] == ["shell", "lshal"]:
                raise subprocess.TimeoutExpired(command, kwargs["timeout"], output=b"partial HAL\n", stderr=b"timeout note\n")
            return self.fake_adb(command, **kwargs)
        result, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 3)
        manifest = self.manifest()
        self.assertEqual(manifest["status"], "partial")
        record = next(record for record in manifest["commands"] if record["label"] == "hal-services")
        self.assertEqual(record["status"], "timeout")
        self.assertIsNone(record["exit_code"])
        self.assertEqual((self.output / record["stdout"]).read_bytes(), b"partial HAL\n")

    def test_failed_read_keeps_exit_code_and_continues(self):
        def effect(command, **kwargs):
            if command[-2:] == ["shell", "lpdump"]:
                return subprocess.CompletedProcess(command, 13, b"", b"Permission denied\n")
            return self.fake_adb(command, **kwargs)
        result, stdout, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 3)
        manifest = self.manifest()
        record = next(record for record in manifest["commands"] if record["label"] == "dynamic-partitions")
        self.assertEqual(record["exit_code"], 13)
        self.assertTrue(any(record["label"] == "hal-services" for record in manifest["commands"]))
        self.assertIn("Do not escalate to root", stdout)

    def test_successful_pull_without_files_is_not_complete(self):
        def effect(command, **kwargs):
            if "pull" in command:
                return subprocess.CompletedProcess(command, 0, b"", b"")
            return self.fake_adb(command, **kwargs)
        result, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 3)
        self.assertEqual(len(self.manifest()["errors"]), len(stock.METADATA_DIRECTORIES))

    def test_failed_pull_retains_hashes_for_files_already_copied(self):
        def effect(command, **kwargs):
            result = self.fake_adb(command, **kwargs)
            if command[3:5] == ["pull", "/vendor/etc/vintf"]:
                result.returncode = 1
                result.stderr = b"partial transfer"
            return result
        result, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 3)
        self.assertTrue(any(item["path"] == "metadata/vendor-etc-vintf/fixture.xml" for item in self.manifest()["artifacts"]))

    def test_sensitive_dumpsys_requires_explicit_opt_in(self):
        result, _, _, process = self.invoke(["--include-dumpsys"])
        self.assertEqual(result, 0)
        dumps = [call.args[0][-1] for call in process.call_args_list if "dumpsys" in call.args[0]]
        self.assertEqual(dumps, list(stock.DUMPSYS_SERVICES))

    def test_stock_camera_apk_is_opt_in_and_hashed(self):
        result, _, _, process = self.invoke(["--pull-stock-apks"])
        self.assertEqual(result, 0)
        artifact = next(item for item in self.manifest()["artifacts"] if item["path"].endswith(".apk"))
        self.assertEqual(artifact["sha256"], hashlib.sha256(b"private-fixture-apk").hexdigest())
        apk_pulls = [call.args[0] for call in process.call_args_list if "pull" in call.args[0] and call.args[0][-2].endswith(".apk")]
        self.assertEqual(len(apk_pulls), 1)

    def test_updated_system_apk_under_data_is_never_pulled(self):
        def effect(command, **kwargs):
            if command[-4:] == ["shell", "pm", "path", "com.android.camera"]:
                return subprocess.CompletedProcess(command, 0, b"package:/data/app/com.android.camera/base.apk\n", b"")
            return self.fake_adb(command, **kwargs)
        result, _, _, process = self.invoke(["--pull-stock-apks"], effect=effect)
        self.assertEqual(result, 3)
        self.assertFalse(any("pull" in call.args[0] and "/data/" in call.args[0][-2] for call in process.call_args_list))
        self.assertFalse((self.output / "apks").exists())

    def test_camera_package_must_be_a_system_app(self):
        def effect(command, **kwargs):
            if command[-6:] == ["shell", "pm", "list", "packages", "-s", "-f"]:
                return subprocess.CompletedProcess(command, 0, b"package:/system/app/Other.apk=org.example.other\n", b"")
            return self.fake_adb(command, **kwargs)
        result, _, _, process = self.invoke(["--pull-stock-apks"], effect=effect)
        self.assertEqual(result, 3)
        self.assertTrue(self.manifest()["skipped"])
        self.assertFalse(any(call.args[0][-4:] == ["shell", "pm", "path", "com.android.camera"] for call in process.call_args_list))

    def test_malformed_or_traversal_apk_paths_are_refused_as_a_batch(self):
        for path in (
            "/product/../data/base.apk", "/product/app/$(id).apk", "/product/app/good.apk\nnot-a-package-path",
        ):
            with self.subTest(path=path):
                self.output = Path(self.temporary.name) / f"bad-apk-{len(list(Path(self.temporary.name).iterdir()))}"
                self.arguments[-1] = str(self.output)
                def effect(command, **kwargs):
                    if command[-4:] == ["shell", "pm", "path", "com.android.camera"]:
                        return subprocess.CompletedProcess(command, 0, f"package:{path}\n".encode(), b"")
                    return self.fake_adb(command, **kwargs)
                result, _, _, process = self.invoke(["--pull-stock-apks"], effect=effect)
                self.assertEqual(result, 3)
                self.assertFalse(any("pull" in call.args[0] and call.args[0][-2].endswith(".apk") for call in process.call_args_list))

    def test_interrupt_marks_collection_incomplete(self):
        def effect(command, **kwargs):
            if command[-2:] == ["shell", "lshal"]:
                raise KeyboardInterrupt
            return self.fake_adb(command, **kwargs)
        result, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 130)
        self.assertEqual(self.manifest()["status"], "interrupted")

    def test_interrupt_during_preflight_is_also_recorded(self):
        def effect(command, **kwargs):
            if command[1:] == ["devices", "-l"]:
                raise KeyboardInterrupt
            return self.fake_adb(command, **kwargs)
        result, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 130)
        self.assertEqual(self.manifest()["status"], "interrupted")

    def test_manufacturer_check_is_case_insensitive(self):
        def effect(command, **kwargs):
            if command[-3:] == ["shell", "getprop", "ro.product.manufacturer"]:
                return subprocess.CompletedProcess(command, 0, b"XIAOMI\n", b"")
            return self.fake_adb(command, **kwargs)
        result, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 0)
        self.assertEqual(self.manifest()["device"]["manufacturer"], "XIAOMI")

    def test_multiple_authorized_devices_do_not_change_explicit_selection(self):
        def effect(command, **kwargs):
            if command[1:] == ["devices", "-l"]:
                output = f"List of devices attached\nOTHER\tdevice\n{self.serial}\tdevice\n"
                return subprocess.CompletedProcess(command, 0, output.encode(), b"")
            return self.fake_adb(command, **kwargs)
        result, _, _, process = self.invoke(effect=effect)
        self.assertEqual(result, 0)
        self.assertTrue(all(call.args[0][2] == self.serial for call in process.call_args_list if call.args[0][1] == "-s"))

    def test_apk_split_paths_are_preserved_and_deduplicated(self):
        def effect(command, **kwargs):
            if command[-4:] == ["shell", "pm", "path", "com.android.camera"]:
                output = "package:/product/priv-app/Camera/base.apk\npackage:/product/priv-app/Camera/split_config.arm64_v8a.apk\npackage:/product/priv-app/Camera/base.apk\n"
                return subprocess.CompletedProcess(command, 0, output.encode(), b"")
            return self.fake_adb(command, **kwargs)
        result, _, _, _ = self.invoke(["--pull-stock-apks"], effect=effect)
        self.assertEqual(result, 0)
        apks = [item["path"] for item in self.manifest()["artifacts"] if item["path"].endswith(".apk")]
        self.assertEqual(apks, ["apks/com.android.camera/001-base.apk", "apks/com.android.camera/002-split_config.arm64_v8a.apk"])

    def test_selected_serial_is_redacted_from_output_path(self):
        self.output = Path(self.temporary.name) / self.serial
        self.arguments[-1] = str(self.output)
        result, stdout, stderr, _ = self.invoke()
        self.assertEqual(result, 0)
        self.assertNotIn(self.serial, stdout + stderr)

    def test_pulled_symlinks_are_not_followed_or_hashed(self):
        private_file = Path(self.temporary.name) / "outside.txt"
        private_file.write_text("do not hash")
        def effect(command, **kwargs):
            result = self.fake_adb(command, **kwargs)
            if command[3:5] == ["pull", "/system/etc/vintf"]:
                (Path(command[-1]) / "outside-link.xml").symlink_to(private_file)
            return result
        result, _, _, _ = self.invoke(effect=effect)
        self.assertEqual(result, 3)
        self.assertFalse(any(item["path"].endswith("outside-link.xml") for item in self.manifest()["artifacts"]))
        self.assertTrue(any("symlink" in error for error in self.manifest()["errors"]))


class ParsingTests(unittest.TestCase):
    def test_parse_devices_ignores_daemon_banner_and_preserves_states(self):
        output = "* daemon started successfully\nList of devices attached\nA\tdevice model:Phone\nB\tunauthorized\nC\tno permissions\n"
        self.assertEqual(stock.parse_devices(output), {"A": "device", "B": "unauthorized", "C": "no"})

    def test_duplicate_device_is_refused(self):
        with self.assertRaises(stock.CollectionError):
            stock.parse_devices("A\tdevice\nA\tdevice\n")

    def test_parse_system_packages(self):
        output = "package:/product/priv-app/Camera.apk=com.android.camera\nwarning\npackage:invalid\n"
        self.assertEqual(stock.system_package_names(output), {"com.android.camera"})

    def test_safe_stock_apk_path_boundaries(self):
        accepted = ["/system/app/Camera/base.apk", "/product/priv-app/Camera/split_config.arm64_v8a.apk"]
        rejected = [
            "/data/app/base.apk", "relative.apk", "/systemx/app/base.apk", "/system/../data/base.apk",
            "/system/app/./base.apk", "/system//base.apk", "/system/app/base;id.apk", "/system/app/base.apk\n",
            "/system/app/base.apk/extra", "/system/app/base.txt", "/system/app/`id`.apk",
        ]
        for path in accepted:
            self.assertTrue(stock.safe_stock_apk(path), path)
        for path in rejected:
            self.assertFalse(stock.safe_stock_apk(path), path)


if __name__ == "__main__":
    unittest.main()
