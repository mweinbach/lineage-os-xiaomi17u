"""Exercise the offline ledger using synthetic evidence and no phone/network."""

import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts import hardware_qualification as qualification


class HardwareQualificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.build = "nezha.synthetic-unit-test"
        self.record = qualification.template(self.build)

    def save(self):
        (self.root / "results.json").write_text(json.dumps(self.record))

    def measured(self, identifier="camera.aperture.front", status="fail"):
        data = b"Synthetic operator note: front selector absent after attempting selection.\n"
        (self.root / "observation.txt").write_bytes(data)
        return {"id": identifier, "status": status,
                "observed_at": "2026-09-05T15:00:00Z",
                "observation": "Front selection attempted; no front selector exposed.",
                "evidence": [{"path": "observation.txt",
                              "sha256": hashlib.sha256(data).hexdigest()}]}

    def test_complete_template_and_missing_results_remain_not_run(self):
        ids = [entry["id"] for entry in self.record["checks"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreater(len(ids), 20)
        self.record["checks"] = []
        (self.root / "services.txt").write_text("IGnss/default\ncamera\naudio\n")
        self.save()
        result = qualification.analyze(self.root, self.build)
        self.assertEqual(result["counts"], {"pass": 0, "fail": 0, "not-run": len(ids)})
        self.assertFalse(result["all_scoped_checks_pass"])

    def test_measured_failure_does_not_promote_related_checks(self):
        self.record["checks"] = [self.measured()]
        self.save()
        result = qualification.analyze(self.root, self.build)
        statuses = {item["id"]: item["status"] for item in result["checks"]}
        self.assertEqual(statuses["camera.aperture.front"], "fail")
        self.assertEqual(statuses["camera.aperture.rear"], "not-run")
        self.assertEqual(result["verdict_source"], "operator-recorded")
        self.assertEqual(result["counts"]["fail"], 1)

    def test_pass_is_preserved_only_with_verified_evidence(self):
        self.record["checks"] = [self.measured("audio.speaker", "pass")]
        self.save()
        result = qualification.analyze(self.root, self.build)
        self.assertEqual(result["counts"]["pass"], 1)
        self.assertFalse(result["all_scoped_checks_pass"])
        (self.root / "observation.txt").write_text("changed")
        with self.assertRaisesRegex(ValueError, "SHA-256 differs"):
            qualification.analyze(self.root, self.build)

    def test_wrong_build_device_and_schema_rejected(self):
        for key, value in (("build_identity", "another-build"), ("device", "another-phone"),
                           ("schema_version", 2)):
            with self.subTest(key=key):
                self.record = qualification.template(self.build)
                self.record[key] = value
                self.save()
                with self.assertRaisesRegex(ValueError, "differs"):
                    qualification.analyze(self.root, self.build)

    def test_duplicate_unknown_and_invalid_status_rejected(self):
        sample = self.measured()
        for entries in ([sample, sample], [{"id": "invented", "status": "pass"}],
                        [{"id": sample["id"], "status": "registered"}]):
            with self.subTest(entries=entries):
                self.record["checks"] = entries
                self.save()
                with self.assertRaises(ValueError):
                    qualification.analyze(self.root, self.build)

    def test_measured_result_requires_observation_time_and_files(self):
        for key in ("observation", "observed_at", "evidence"):
            with self.subTest(key=key):
                sample = self.measured()
                del sample[key]
                self.record["checks"] = [sample]
                self.save()
                with self.assertRaises(ValueError):
                    qualification.analyze(self.root, self.build)
        sample = self.measured()
        sample["observed_at"] = "2026-09-05T15:00:00"
        self.record["checks"] = [sample]
        self.save()
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            qualification.analyze(self.root, self.build)

    def test_not_run_cannot_hide_a_measured_result(self):
        sample = self.measured(status="not-run")
        self.record["checks"] = [sample]
        self.save()
        with self.assertRaisesRegex(ValueError, "not-run check"):
            qualification.analyze(self.root, self.build)

    def test_evidence_cannot_escape_directory_or_be_empty_or_missing(self):
        for path in ("../outside", "/etc/passwd", "missing.txt", "empty.txt"):
            with self.subTest(path=path):
                sample = self.measured()
                (self.root / "empty.txt").write_bytes(b"")
                sample["evidence"][0]["path"] = path
                self.record["checks"] = [sample]
                self.save()
                with self.assertRaises(ValueError):
                    qualification.analyze(self.root, self.build)
        with tempfile.TemporaryDirectory() as outside:
            external = Path(outside) / "external.txt"
            external.write_text("external")
            (self.root / "link.txt").symlink_to(external)
            sample = self.measured()
            sample["evidence"][0]["path"] = "link.txt"
            self.record["checks"] = [sample]
            self.save()
            with self.assertRaisesRegex(ValueError, "outside"):
                qualification.analyze(self.root, self.build)

    def test_contract_covers_registered_hardware_and_targeted_runtime_risks(self):
        areas = {item["area"] for item in qualification.contract()["checks"]}
        self.assertEqual(areas, {"display", "radio", "audio", "sensors", "haptics", "power", "gnss",
                                 "nfc", "wifi", "bluetooth", "camera", "mi_ext", "vendor"})

    def test_ledger_cannot_be_its_own_evidence_via_link(self):
        sample = self.measured()
        sample["evidence"][0]["path"] = "ledger-alias.json"
        self.record["checks"] = [sample]
        self.save()
        for link_type in ("symlink", "hardlink"):
            with self.subTest(link_type=link_type):
                alias = self.root / "ledger-alias.json"
                if link_type == "symlink":
                    alias.symlink_to(self.root / "results.json")
                else:
                    alias.hardlink_to(self.root / "results.json")
                with self.assertRaisesRegex(ValueError, "own behavioral evidence"):
                    qualification.analyze(self.root, self.build)
                alias.unlink()

    def test_cli_does_not_report_incomplete_matrix_as_success(self):
        self.save()
        proc = subprocess.run([sys.executable, str(qualification.ROOT / "scripts/hardware_qualification.py"),
                               "analyze", "--evidence-dir", str(self.root),
                               "--build-identity", self.build], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["evidence_validation"], "valid")


if __name__ == "__main__":
    unittest.main()
