import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import performance_analysis as pa


def fixture(later=False):
    return {
        "manifest": {"device": {"serial": "TEST_ONLY", "expected_device": "nezha"},
                     "options": {"operator_context": "screen-off-unplugged"},
                     "started_at": "2026-09-05T00:10:00+00:00" if later else "2026-09-05T00:00:00+00:00",
                     "completed_at": "2026-09-05T00:10:10+00:00" if later else "2026-09-05T00:00:10+00:00"},
        "receipt_sha256": "fixture-not-a-live-measurement",
        "statuses": {},
        "readings": {
            "property-ro.product.manufacturer": "Xiaomi", "property-ro.product.device": "nezha", "property-ro.kernel.qemu": "",
            "property-ro.build.fingerprint": "test/fingerprint", "property-ro.build.version.incremental": "test-only",
            "property-ro.vendor.build.fingerprint": "test/vendor", "kernel": "test-kernel",
            "boot-id-start": "11111111-1111-1111-1111-111111111111", "boot-id-end": "11111111-1111-1111-1111-111111111111",
            "uptime-start": "700.0 0" if later else "100.0 0", "uptime-end": "710.0 0" if later else "110.0 0",
            "battery": "  AC powered: false\n  USB powered: false\n  Wireless powered: false\n  Dock powered: false",
            "power": "mWakefulness=Asleep", "charge-counter": "2990000" if later else "3000000",
            "suspend-success": "12" if later else "10", "suspend-fail": "0",
            "vmstat": "pgmajfault 8\npswpin 20\nnr_free_pages 100" if later else "pgmajfault 3\npswpin 15\nnr_free_pages 999",
            "psi-memory": "some avg10=0.00 avg60=0.00 avg300=0.00 total=200" if later else "some avg10=0.00 avg60=0.00 avg300=0.00 total=100",
            "cpuidle": "/sys/devices/system/cpu/cpu0/cpuidle/state0/time:200" if later else "/sys/devices/system/cpu/cpu0/cpuidle/state0/time:100",
        }}


def write_receipt(root):
    root.mkdir()
    (root / "commands").mkdir()
    manifest = fixture()["manifest"]
    manifest.update(schema_version=1, tool="collect_performance.py", collection_kind="read-only-performance-snapshot", status="complete", artifacts=[], commands=[])
    for i, (label, text) in enumerate(fixture()["readings"].items()):
        record = {"label": label, "status": "ok", "exit_code": 0}
        for stream, content in (("stdout", text.encode()), ("stderr", b"")):
            name = f"commands/{i:03d}-{label}.{stream}.txt"
            (root / name).write_bytes(content)
            manifest["artifacts"].append({"path": name, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()})
            record[stream] = name
        manifest["commands"].append(record)
    (root / "manifest.json").write_text(json.dumps(manifest))
    return manifest


class AnalysisTests(unittest.TestCase):
    def test_measured_deltas_and_units_not_a_pass(self):
        report = pa.analyze(fixture(), fixture(True))
        self.assertEqual(report["counters"]["suspend-success"]["delta"], 2)
        self.assertEqual(report["counters"]["vmstat"]["pgmajfault"]["delta"], 5)
        self.assertNotIn("nr_free_pages", report["counters"]["vmstat"])
        self.assertEqual(report["counters"]["psi-memory"]["some"]["delta"], 100)
        self.assertEqual(report["charge"]["delta_uAh"], 10000)
        self.assertEqual(report["charge"]["approximate_average_net_mA"], 60)
        self.assertTrue(report["interval"]["screen_off_unplugged_endpoints_and_declaration"])
        self.assertEqual(report["status"], "measured-observations-only")
        self.assertNotIn("mWh", report["charge"])

    def test_identity_differences_rejected(self):
        for key in ("property-ro.build.fingerprint", "property-ro.build.version.incremental", "property-ro.vendor.build.fingerprint", "kernel", "property-ro.product.device", "boot-id-start", "boot-id-end"):
            before, after = fixture(), fixture(True)
            after["readings"][key] = "different"
            with self.subTest(key=key), self.assertRaises(pa.AnalysisError):
                pa.analyze(before, after)

    def test_serial_mismatch(self):
        after = fixture(True)
        after["manifest"]["device"]["serial"] = "different"
        with self.assertRaises(pa.AnalysisError):
            pa.analyze(fixture(), after)

    def test_missing_identity_rejected(self):
        after = fixture(True)
        after["readings"]["kernel"] = None
        with self.assertRaises(pa.AnalysisError):
            pa.analyze(fixture(), after)

    def test_nonpositive_reset_overlap_nonfinite_uptime(self):
        for value in ("0 0", "100 0", "105 0", "nan 0", "inf 0", "-1 0", "invalid"):
            after = fixture(True)
            after["readings"]["uptime-start"] = value
            with self.subTest(value=value), self.assertRaises(pa.AnalysisError):
                pa.analyze(fixture(), after)

    def test_wall_disagreement_and_naive_date(self):
        for value in ("2026-09-06T00:10:00+00:00", "2026-09-05T00:10:00", "invalid"):
            after = fixture(True)
            after["manifest"]["started_at"] = value
            with self.subTest(value=value), self.assertRaises(pa.AnalysisError):
                pa.analyze(fixture(), after)

    def test_counter_reset_not_negative_delta(self):
        after = fixture(True)
        after["readings"]["suspend-success"] = "1"
        report = pa.analyze(fixture(), after)
        self.assertEqual(report["counters"]["suspend-success"]["status"], "rejected-counter-reset-or-wrap")
        self.assertNotIn("delta", report["counters"]["suspend-success"])

    def test_unavailable_is_not_zero(self):
        after = fixture(True)
        after["readings"]["suspend-success"] = None
        after["readings"]["psi-memory"] = None
        report = pa.analyze(fixture(), after)
        self.assertEqual(report["counters"]["suspend-success"]["status"], "unavailable")
        self.assertEqual(report["counters"]["psi-memory"]["some"]["status"], "unavailable")

    def test_charging_and_counter_reset(self):
        for value, status in (("4000000", "rejected-charging-or-counter-reset"), ("0", "rejected-zero-or-reset-charge-counter"), ("-1", "unavailable")):
            after = fixture(True)
            after["readings"]["charge-counter"] = value
            with self.subTest(value=value):
                self.assertEqual(pa.analyze(fixture(), after)["charge"]["status"], status)

    def test_context_qualification(self):
        for label, value in (("battery", "USB powered: false"), ("battery", "AC powered: false\nUSB powered: true\nWireless powered: false"), ("power", "mWakefulness=Awake"), ("power", None)):
            after = fixture(True)
            after["readings"][label] = value
            with self.subTest(label=label, value=value):
                self.assertFalse(pa.analyze(fixture(), after)["interval"]["screen_off_unplugged_endpoints_and_declaration"])

    def test_context_requires_operator_declaration(self):
        after = fixture(True)
        after["manifest"]["options"]["operator_context"] = "unspecified"
        self.assertFalse(pa.analyze(fixture(), after)["interval"]["screen_off_unplugged_endpoints_and_declaration"])

    def test_receipt_verifies(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "snapshot"
            write_receipt(root)
            snap = pa.load_snapshot(root)
            self.assertEqual(snap["readings"], {key: value.strip() for key, value in fixture()["readings"].items()})
            self.assertEqual(len(snap["receipt_sha256"]), 64)

    def test_tampered_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "snapshot"
            manifest = write_receipt(root)
            (root / manifest["artifacts"][0]["path"]).write_text("tampered")
            with self.assertRaises(pa.AnalysisError):
                pa.load_snapshot(root)

    def test_symlink_artifact_and_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "snapshot"
            manifest = write_receipt(root)
            file = root / manifest["artifacts"][0]["path"]
            file.unlink()
            file.symlink_to("/etc/hosts")
            with self.assertRaises(pa.AnalysisError):
                pa.load_snapshot(root)
            link = Path(directory).resolve() / "link"
            link.symlink_to(root, target_is_directory=True)
            with self.assertRaises(pa.AnalysisError):
                pa.load_snapshot(link)

    def test_bad_receipt_shapes(self):
        changes = (
            lambda m: m["artifacts"][0].update(path="../../outside"),
            lambda m: m["artifacts"][0].update(bytes=-1),
            lambda m: m["artifacts"].append(copy.deepcopy(m["artifacts"][0])),
            lambda m: m["commands"][0].update(label="wrong-label"),
            lambda m: m["commands"][0].update(status="ok", exit_code=1),
            lambda m: m.update(status="collecting"),
            lambda m: m.update(schema_version=99),
        )
        for change in changes:
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                root = Path(directory).resolve() / "snapshot"
                manifest = write_receipt(root)
                change(manifest)
                (root / "manifest.json").write_text(json.dumps(manifest))
                with self.assertRaises(pa.AnalysisError):
                    pa.load_snapshot(root)

    def test_oversized_manifest(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "snapshot"
            write_receipt(root)
            (root / "manifest.json").write_bytes(b" " * (pa.MAX_RECEIPT + 1))
            with self.assertRaises(pa.AnalysisError):
                pa.load_snapshot(root)

    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / "snapshot"
            write_receipt(root)
            manifest = root / "manifest.json"
            manifest.write_text(manifest.read_text().replace('"schema_version": 1', '"schema_version": 1, "schema_version": 1'))
            with self.assertRaises(pa.AnalysisError):
                pa.load_snapshot(root)

    def test_duplicate_battery_flags_and_simulated_state_unqualified(self):
        for extra in ("\nUSB powered: false", "\nusb powered: true", "\nUPDATES STOPPED"):
            after = fixture(True)
            after["readings"]["battery"] += extra
            self.assertFalse(pa.analyze(fixture(), after)["interval"]["screen_off_unplugged_endpoints_and_declaration"])

    def test_wakeup_counts_without_guessing_time_units(self):
        before, after = fixture(), fixture(True)
        before["readings"]["wake-sources"] = "name active_count event_count total_time\nfixture 2 10 9999"
        after["readings"]["wake-sources"] = "name active_count event_count total_time\nfixture 3 15 10000"
        counters = pa.analyze(before, after)["counters"]["wake-sources"]
        self.assertEqual(counters["fixture/event_count"]["delta"], 5)
        self.assertNotIn("fixture/total_time", counters)
        after["readings"]["wake-sources"] += "\nfixture 3 15 10000"
        self.assertEqual(pa.analyze(before, after)["counters"]["wake-sources"]["fixture/event_count"]["status"], "unavailable")


if __name__ == "__main__":
    unittest.main()
