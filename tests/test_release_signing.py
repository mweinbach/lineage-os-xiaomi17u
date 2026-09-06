"""Offline checks for the parameterized signing orchestrator; every stage is mocked."""

import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts import release_signing as signing

BUILD = "nezha." + "89abcdef" * 3
SET = "example-signing-20260906-v1"


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


class SigningFixture:
    """A selection whose pins, admission and transfer records agree with each other."""

    def __init__(self, root):
        self.root = root
        self.source_path = root / "source-installed.json"
        rows = [{"path": "/work/evolution/a", "sha256": "0" * 64, "size_bytes": 10, "mode": 420},
                {"path": "/work/evolution/b", "sha256": "1" * 64, "size_bytes": 20, "mode": 420}]
        self.source_path.write_text(json.dumps({"build_number": BUILD, "transaction": "/work/validation/t",
                                                "changed_files": 1, "source_inventory": rows}))
        self.target = root / "lineage_nezha-target_files.zip"
        self.target.write_bytes(b"PK\x05\x06" + b"\x00" * 18 + b"not a real archive")
        target_pin = signing.pin(self.target)
        source_pin = signing.pin(self.source_path)
        source_identity = {k: source_pin[k] for k in ("sha256", "size_bytes")}
        archive_identity = {k: target_pin[k] for k in ("sha256", "size_bytes")}
        self.admission_path = root / "admission.json"
        self.admission = {"operation": "admit-nezha-package-v1", "verified": True, "build_number": BUILD,
                          "source_inventory_record": source_identity,
                          "archive": {"path": "/work/out/target-files.zip", **archive_identity}}
        self.admission_path.write_text(json.dumps(self.admission))
        admission_pin = signing.pin(self.admission_path)
        self.transfer_path = root / "transfer.json"
        self.transfer = {"operation": "transfer-admitted-nezha-image-v1", "kind": "package", "verified": True,
                         "build_number": BUILD, "source_inventory_record": source_identity,
                         "source_admission": admission_pin, "file": target_pin,
                         "source": self.admission["archive"], "stream_identity": archive_identity,
                         "host_readback_identity": archive_identity, "guest_final_rehash_identity": archive_identity,
                         "guest_writes": False, "source_or_android_output_written": False,
                         "phone_accessed": False, "complete_rom_ready": False}
        self.transfer_path.write_text(json.dumps(self.transfer))
        self.retained = root / "retained.json"
        self.retained.write_text('{"schema_version": 1}\n')
        self.local = root / "recovery-local.json"
        self.local.write_text("{}\n")
        self.base = root / "artifacts/avb/nezha" / SET
        self.selection = {
            "schema_version": 2, "artifact_set_id": SET, "build_number": BUILD,
            "source": {**source_pin, "entry_count": 2, "total_bytes": 30, "transaction": "/work/validation/t"},
            "target_files": target_pin,
            "package_admission": {**admission_pin, "operation": "admit-nezha-package-v1"},
            "package_transfer": {**signing.pin(self.transfer_path), "operation": "transfer-admitted-nezha-image-v1"},
            "retained_input_manifest": signing.pin(self.retained),
            "local_config": str(self.local), "artifact_base": str(self.base),
        }

    def rewrite_transfer(self, change):
        change(self.transfer)
        self.transfer_path.write_text(json.dumps(self.transfer))
        self.selection["package_transfer"] = {**signing.pin(self.transfer_path),
                                              "operation": self.selection["package_transfer"]["operation"]}

    def rewrite_admission(self, change):
        change(self.admission)
        self.admission_path.write_text(json.dumps(self.admission))
        pin = signing.pin(self.admission_path)
        self.selection["package_admission"] = {**pin, "operation": self.selection["package_admission"]["operation"]}
        self.rewrite_transfer(lambda t: t.update(source_admission=pin))

    def write_selection(self):
        path = self.root / "selection.json"
        raw = json.dumps(self.selection).encode()
        path.write_bytes(raw)
        return path, sha256(raw)


class FakeStages:
    """Stand-in for subprocess.run that writes each stage's expected outputs."""

    def __init__(self, fail_stage=None):
        self.calls = []
        self.fail_stage = fail_stage

    def __call__(self, command, cwd, stdout, stderr, timeout):
        script, argv = Path(command[2]).name, list(command[3:])
        self.calls.append((script, argv))

        def option(name):
            return Path(argv[argv.index(name) + 1])

        if script == "target_files_avb_inventory.py":
            output = option("--output")
            output.write_text('{"status": "complete"}\n')
            payload, stage = {"status": "complete"}, "01" if output.name.startswith("original") else "06"
        elif script == "materialize_target_files_inputs.py":
            output = option("--output-dir")
            output.mkdir(parents=True)
            manifest = output / "input-manifest.json"
            manifest.write_text("{}\n")
            payload, stage = {"status": "materialized-inputs-only", "input_manifest": signing.pin(manifest)}, "02"
        elif script == "avb_signing.py" and argv[0] == "prepare":
            output = option("--output-dir")
            output.mkdir(parents=True)
            (output / "preparation.json").write_text("{}\n")
            payload, stage = {"status": "prepared_public_only"}, "03"
        elif script == "avb_signing.py":
            output = option("--output-dir")
            output.mkdir(parents=True)
            (output / "signing-receipt.json").write_text('{"verified": true}\n')
            (output / "verification-manifest.json").write_text("{}\n")
            payload, stage = {"status": "signed_and_verified"}, "04"
        else:
            output = option("--output-dir")
            output.mkdir(parents=True)
            archive = output / "reconciled-target-files.zip"
            archive.write_bytes(b"reconciled")
            payload, stage = {"status": "signed-image-archive-reconciled-only", "archive": signing.pin(archive)}, "05"
        if stage == self.fail_stage:
            stderr.write(b"stage failed\n")
            return subprocess.CompletedProcess(command, 1)
        stdout.write(json.dumps(payload).encode())
        return subprocess.CompletedProcess(command, 0)


class ReleaseSigningTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fixture = SigningFixture(self.root)

    def test_plan_lists_six_stages_without_hashing_the_archive(self):
        hashed = []
        original = signing.pin

        def recording_pin(path):
            hashed.append(Path(path).name)
            return original(path)

        with mock.patch.object(signing, "pin", recording_pin), \
                mock.patch("subprocess.run", side_effect=AssertionError("dispatched")):
            result = signing.plan(self.fixture.selection)
        self.assertEqual([stage["name"] for stage in result["stages"]], list(signing.STAGE_NAMES))
        self.assertFalse(result["dispatches"])
        self.assertNotIn(self.fixture.target.name, hashed)
        materialize = result["stages"][1]["argv"]
        self.assertIn("--artifact-set-id", materialize)
        self.assertEqual(materialize[materialize.index("--artifact-set-id") + 1], SET)
        self.assertEqual(materialize.count("--source-record"), 2)
        self.assertIn("<02-materialize input_manifest.path>", result["stages"][2]["argv"])
        self.assertTrue(all(str(self.fixture.base) in " ".join(stage["argv"]) for stage in result["stages"]))

    def test_selection_records_must_agree(self):
        cases = {
            "unverified admission": lambda: self.fixture.rewrite_admission(lambda a: a.update(verified=False)),
            "transfer operation": lambda: self.fixture.selection["package_transfer"].update(operation="transfer-other-v1"),
            "transfer archive": lambda: self.fixture.rewrite_transfer(
                lambda t: t.update(file={**t["file"], "sha256": "f" * 64})),
            "transfer readiness": lambda: self.fixture.rewrite_transfer(lambda t: t.update(complete_rom_ready=True)),
            "source count": lambda: self.fixture.selection["source"].update(entry_count=3),
            "build number": lambda: self.fixture.selection.update(build_number="nezha." + "0" * 24),
            "extra key": lambda: self.fixture.selection.update(surprise=True),
        }
        for label, mutate in cases.items():
            with self.subTest(label=label):
                self.setUp()
                mutate()
                with self.assertRaises(signing.ReleaseSigningError):
                    signing.validate_selection(self.fixture.selection)

    def test_run_executes_the_stages_in_order_and_records_receipts(self):
        stages = FakeStages()
        path, digest = self.fixture.write_selection()
        raw, selection = signing.load_selection(path, digest)
        result = signing.run(selection, raw, runner=stages, host_check=False)
        self.assertEqual([call[0] for call in stages.calls],
                         ["target_files_avb_inventory.py", "materialize_target_files_inputs.py", "avb_signing.py",
                          "avb_signing.py", "reconcile_signed_target_files.py", "target_files_avb_inventory.py"])
        self.assertEqual(result["status"], "signing-sequence-completed")
        self.assertFalse(result["flash_ready"])
        self.assertEqual(result["archive"]["size_bytes"], len(b"reconciled"))
        logs = self.fixture.base / "stage-logs"
        for name in signing.STAGE_NAMES:
            self.assertEqual(json.loads((logs / f"{name}.exit.json").read_text()), {"returncode": 0})
        self.assertEqual((logs / "selection.json").read_bytes(), raw)
        request = json.loads((logs / "reconcile-request.json").read_text())
        self.assertEqual(request["operation"], "reconcile-nezha-signed-target-files-v1")
        self.assertEqual(request["target_files"], self.fixture.selection["target_files"])
        self.assertEqual(request["inventory"], signing.pin(self.fixture.base / "original-inventory.json"))
        reconcile = stages.calls[4][1]
        self.assertEqual(reconcile[reconcile.index("--expected-sha256") + 1],
                         signing.pin(logs / "reconcile-request.json")["sha256"])
        published = stages.calls[5][1]
        self.assertEqual(published[published.index("--expected-sha256") + 1], result["archive"]["sha256"])

    def test_failed_stage_stops_the_sequence_and_preserves_logs(self):
        stages = FakeStages(fail_stage="03")
        path, digest = self.fixture.write_selection()
        raw, selection = signing.load_selection(path, digest)
        with self.assertRaisesRegex(signing.ReleaseSigningError, "03-prepare failed"):
            signing.run(selection, raw, runner=stages, host_check=False)
        self.assertEqual(len(stages.calls), 3)
        logs = self.fixture.base / "stage-logs"
        self.assertEqual(json.loads((logs / "03-prepare.exit.json").read_text()), {"returncode": 1})
        self.assertEqual((logs / "03-prepare.stderr").read_bytes(), b"stage failed\n")
        self.assertFalse((logs / "04-sign.exit.json").exists())

    def test_existing_artifact_base_and_wrong_selection_hash_are_refused(self):
        self.fixture.base.mkdir(parents=True)
        path, digest = self.fixture.write_selection()
        raw, selection = signing.load_selection(path, digest)
        with self.assertRaisesRegex(signing.ReleaseSigningError, "already exists"):
            signing.run(selection, raw, runner=FakeStages(), host_check=False)
        self.assertEqual(signing.main(["plan", "--selection", str(path), "--expected-sha256", "0" * 64]), 2)
        self.assertEqual(signing.main(["plan", "--selection", str(path), "--expected-sha256", digest]), 0)


if __name__ == "__main__":
    unittest.main()
