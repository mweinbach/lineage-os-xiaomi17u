import contextlib
import io
import json
import argparse
from pathlib import Path
import sys
import tempfile
import shlex
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import collect_performance as cp
from collect_stock import CollectionError


class PerformanceCollectionTests(unittest.TestCase):
    def test_dry_run_has_no_device_or_filesystem_side_effects(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(cp, "bounded_run") as run, contextlib.redirect_stdout(io.StringIO()):
            output = Path(directory) / "new"
            self.assertEqual(cp.main(["--serial", "EXPLICIT", "--expected-device", "nezha", "--output", str(output), "--dry-run"]), 0)
            run.assert_not_called()
            self.assertFalse(output.exists())

    def test_invalid_serial_and_timeout(self):
        for extra in (["--serial", "a;reboot"], ["--serial", "a\nreboot"], ["--serial=-x"], ["--timeout", "nan"], ["--timeout", "inf"], ["--timeout", "16"], ["--timeout", "0"]):
            with self.subTest(extra=extra), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                cp.main(["--serial", "GOOD", "--expected-device", "nezha", "--output", "/unused", "--dry-run", *extra])

    def test_stream_output_limit(self):
        status, _, stdout, stderr = cp.bounded_run([sys.executable, "-c", "import sys;sys.stdout.write('x'*200000);sys.stderr.write('y'*200000)"], 2, 8192)
        self.assertEqual(status, "output_limit")
        self.assertLessEqual(len(stdout) + len(stderr), 8192)

    def test_timeout(self):
        status, _, _, _ = cp.bounded_run([sys.executable, "-c", "import time;time.sleep(2)"], .05)
        self.assertEqual(status, "timeout")

    def test_permission_denied_even_exit_zero(self):
        for text in ("Permission denied", "Can't find service: lmkd", "No such file or directory", "Permission Denial"):
            with self.subTest(text=text):
                self.assertEqual(cp.bounded_run([sys.executable, "-c", f"print({text!r})"], 2)[0], "unavailable")

    def test_missing_command(self):
        self.assertEqual(cp.bounded_run(["/does/not/exist"], 1)[0], "unavailable")

    def test_valid_discovery(self):
        self.assertEqual(cp.discovered_paths("cpuidle", "/sys/devices/system/cpu/cpu0/cpuidle/state0"), ["/sys/devices/system/cpu/cpu0/cpuidle/state0"])
        self.assertEqual(cp.discovered_paths("block", "sda\nzram0"), ["sda", "zram0"])

    def test_malicious_and_out_of_bounds_discovery(self):
        for kind, output in (("block", "../data"), ("block", "zram0;reboot"), ("block", "zram0\nzram0"), ("block", "zram8"), ("cpuidle", "/sys/devices/system/cpu/cpu16/cpuidle/state0"), ("cpuidle", "/sys/devices/system/cpu/cpu0/cpuidle/state8"), ("cpuidle", "/sys/devices/system/cpu/cpu0/cpuidle/state0/../../power")):
            with self.subTest(output=output), self.assertRaises(CollectionError):
                cp.discovered_paths(kind, output)

    def test_static_commands_read_only(self):
        self.assertTrue(all(command[0] in {"cat", "dumpsys", "settings", "logcat"} for _, command in cp.READS))
        for _, command in cp.READS:
            if command[0] == "settings":
                self.assertEqual(command[1], "get")
            if command[0] == "logcat":
                self.assertIn("-d", command)
                self.assertIn("-t", command)
                self.assertNotIn("-c", command)
            self.assertFalse(set(command) & {"root", "su", "setprop", "reboot", "input", "put", "reset", "--reset", "--enable", "--disable"})

    def test_config_matches_code_bounds(self):
        configuration = json.loads((Path(__file__).resolve().parents[1] / "config/nezha-performance-qualification.json").read_text())["collection"]
        self.assertEqual(configuration["max_commands"], cp.MAX_COMMANDS)
        self.assertEqual(configuration["max_combined_output_bytes_per_command"], cp.MAX_BYTES)
        self.assertEqual(configuration["max_total_seconds"], cp.TOTAL_SECONDS)

    def test_full_collection_preflight_receipts_and_offline_analysis(self):
        import performance_analysis as pa
        from test_performance_analysis import fixture
        with tempfile.TemporaryDirectory() as directory:
            snapshots = []
            for later in (False, True):
                facts = fixture(later)
                readings = facts["readings"]
                counter = {"uptime": 0}

                def fake_run(argv, timeout):
                    if argv[-1] == "version":
                        return "ok", 0, b"Android Debug Bridge version fixture", b""
                    if argv[-2:] == ["devices", "-l"]:
                        return "ok", 0, b"List of devices attached\nTEST_ONLY device\n", b""
                    self.assertEqual(argv[1:4], ["-s", "TEST_ONLY", "shell"])
                    args = shlex.split(argv[-1])
                    self.assertFalse(set(args) & {"su", "root", "reboot", "setprop", "put", "-c", "--reset"})
                    if args[0] == "getprop":
                        return "ok", 0, readings.get(f"property-{args[1]}", "").encode(), b""
                    if args == ["uname", "-a"]:
                        text = readings["kernel"]
                    elif args == ["cat", "/proc/sys/kernel/random/boot_id"]:
                        text = readings["boot-id-start"]
                    elif args == ["cat", "/proc/uptime"]:
                        text = readings["uptime-start" if counter["uptime"] == 0 else "uptime-end"]
                        counter["uptime"] += 1
                    elif args == ["ls", "/sys/block"]:
                        text = "unexpected-block-entry"
                    elif args[0] == "find":
                        text = "/unexpected/path"
                    else:
                        label = next((label for label, command in cp.READS if list(command) == args), "unknown")
                        text = readings.get(label)
                        if text is None:
                            return "unavailable", 1, b"", b"Permission denied"
                    return "ok", 0, text.encode(), b""

                output = Path(directory).resolve() / ("after" if later else "before")
                args = argparse.Namespace(serial="TEST_ONLY", expected_device="nezha", output=output, adb="adb-fixture", timeout=5, context="screen-off-unplugged", dry_run=False)
                with patch.object(cp, "bounded_run", side_effect=fake_run), patch("collect_stock.utc_now", side_effect=[facts["manifest"]["started_at"], facts["manifest"]["completed_at"]]):
                    collector = cp.PerformanceCollector(args)
                    self.assertEqual(collector.collect(), 3)
                self.assertEqual(len(collector.manifest["skipped"]), 2)
                self.assertLessEqual(len(collector.manifest["commands"]), cp.MAX_COMMANDS)
                snapshots.append(pa.load_snapshot(output))
                self.assertEqual(output.stat().st_mode & 0o777, 0o700)
                self.assertEqual((output / "manifest.json").stat().st_mode & 0o777, 0o600)
            result = pa.analyze(*snapshots)
            self.assertEqual(result["charge"]["delta_uAh"], 10000)
            self.assertEqual(result["counters"]["suspend-success"]["delta"], 2)
            self.assertEqual(result["counters"]["cpuidle"]["status"], "unavailable")

    def test_wrong_identity_stops_before_measurements(self):
        with tempfile.TemporaryDirectory() as directory:
            args = argparse.Namespace(serial="TEST_ONLY", expected_device="nezha", output=Path(directory) / "snapshot", adb="adb-fixture", timeout=5, context="unspecified", dry_run=False)
            def fake_run(argv, timeout):
                if argv[-2:] == ["devices", "-l"]:
                    return "ok", 0, b"List of devices attached\nTEST_ONLY device\n", b""
                if "ro.product.manufacturer" in argv[-1]:
                    return "ok", 0, b"Other", b""
                if "ro.product.device" in argv[-1]:
                    return "ok", 0, b"nezha", b""
                return "ok", 0, b"", b""
            with patch.object(cp, "bounded_run", side_effect=fake_run):
                collector = cp.PerformanceCollector(args)
                self.assertEqual(collector.collect(), 3)
            labels = {command["label"] for command in collector.manifest["commands"]}
            self.assertNotIn("battery", labels)
            self.assertNotIn("uptime-start", labels)


if __name__ == "__main__":
    unittest.main()
