"""Offline tests for reproducible IMS staging and its closed activation gate."""

import copy
import json
from pathlib import Path
import re
import runpy
import tempfile
import unittest
from unittest import mock

from scripts import ims_inputs as ims


class ImsInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.source = self.root / "source"
        self.source.mkdir()
        self.output = self.root / "packet"
        self.spec, _ = ims.contract()
        self.spec = copy.deepcopy(self.spec)
        for number, item in enumerate(self.spec["files"]):
            raw = ("IMS fixture %d\n" % number).encode()
            item.update(sha256=ims.digest(raw), size_bytes=len(raw))
            target = self.source / item["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        self.raw = ims.encoded(self.spec)

    def prepare(self):
        with mock.patch.object(ims, "contract", return_value=(self.spec, self.raw)):
            return ims.prepare(self.source, self.output)

    def test_reviewed_contract_and_templates(self):
        spec, _ = ims.contract()
        self.assertEqual(len(spec["files"]), 20)
        self.assertEqual(sum(f["size_bytes"] for f in spec["files"]), 3899108)
        self.assertEqual(sum(f["kind"] == "native-optional" for f in spec["files"]), 1)
        plan = ims.templates(spec)
        blueprint = plan[ims.PUBLIC + "/Android.bp.in"].decode()
        self.assertEqual(blueprint.count("enabled: false"), 24)
        self.assertEqual(blueprint.count("check_elf_files: true"), 13)
        self.assertEqual(blueprint.count("allow_undefined_symbols: false"), 13)
        self.assertIn("enforce_uses_libs: true", blueprint)
        self.assertNotIn("certificate:", blueprint)
        self.assertIn("presigned: true", blueprint)
        self.assertEqual(set(re.findall(r"//vendor/xiaomi/nezha-ims:([A-Za-z0-9_]+)", blueprint)),
                         {row["filegroup"] for row in spec["files"]})

    def test_roundtrip_preserves_bytes_and_is_not_activated(self):
        receipt = self.prepare()
        self.assertFalse(receipt["activation_allowed"])
        self.assertFalse(receipt["android_build_verified"])
        self.assertEqual(receipt, ims.verify(self.output, self.spec, self.raw))
        self.assertEqual(list(self.output.rglob("Android.bp")), [])
        self.assertIn("$(error Nezha IMS admission blocked",
                      (self.output / ims.PUBLIC / "admission.mk").read_text())

    def test_input_hash_mismatch_publishes_nothing(self):
        path = self.source / self.spec["files"][0]["path"]
        path.write_bytes(b"x" * path.stat().st_size)
        with self.assertRaisesRegex(ims.ImsInputError, "hash or size mismatch"):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_missing_input_publishes_nothing(self):
        (self.source / self.spec["files"][0]["path"]).unlink()
        with self.assertRaises(FileNotFoundError):
            self.prepare()
        self.assertFalse(self.output.exists())

    def test_existing_destination_preserved(self):
        self.output.mkdir()
        sentinel = self.output / "user-data"
        sentinel.write_text("preserve")
        with self.assertRaisesRegex(ims.ImsInputError, "already exists"):
            self.prepare()
        self.assertEqual(sentinel.read_text(), "preserve")

    def test_input_file_symlink_rejected(self):
        file = self.source / self.spec["files"][0]["path"]
        backup = self.root / "backup"
        file.rename(backup)
        file.symlink_to(backup)
        with self.assertRaisesRegex(ims.ImsInputError, "regular file"):
            self.prepare()

    def test_source_directory_symlink_rejected(self):
        alias = self.root / "alias"
        alias.symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ims.ImsInputError, "symlink ancestor"):
            ims.layout(self.spec, self.raw, alias)

    def test_duplicate_path_or_filegroup_rejected(self):
        self.spec["files"].append(copy.deepcopy(self.spec["files"][0]))
        with self.assertRaisesRegex(ims.ImsInputError, "duplicate"):
            self.prepare()

    def test_relative_traversal_and_unsafe_paths_rejected(self):
        for value in ("../outside", "/absolute", "a/../b", "a//b", "a\\b", "a/./b", "$(shell)"):
            with self.subTest(value=value), self.assertRaises(ims.ImsInputError):
                ims.relative(value)

    def test_runtime_path_mismatch_rejected(self):
        self.spec["files"][0]["runtime_path"] = "/vendor/lib64/other.so"
        with self.assertRaisesRegex(ims.ImsInputError, "runtime path"):
            self.prepare()

    def test_tampered_private_output_rejected(self):
        self.prepare()
        target = self.output / ims.PRIVATE / self.spec["files"][0]["path"]
        target.write_bytes(b"changed")
        with self.assertRaisesRegex(ims.ImsInputError, "hash or size mismatch"):
            ims.verify(self.output, self.spec, self.raw)

    def test_tampered_template_rejected(self):
        self.prepare()
        target = self.output / ims.PUBLIC / "Android.bp.in"
        target.write_text(target.read_text().replace("enabled: false", "enabled: true"))
        with self.assertRaisesRegex(ims.ImsInputError, "packet content mismatch"):
            ims.verify(self.output, self.spec, self.raw)

    def test_forged_activation_receipt_rejected(self):
        self.prepare()
        target = self.output / ims.RECEIPT
        receipt = json.loads(target.read_text())
        receipt["activation_allowed"] = True
        receipt["open_gates"] = []
        target.write_bytes(ims.encoded(receipt))
        with self.assertRaisesRegex(ims.ImsInputError, "packet content mismatch"):
            ims.verify(self.output, self.spec, self.raw)
        with self.assertRaisesRegex(ims.ImsInputError, "activation blocked"):
            ims.require_admission(receipt)

    def test_added_build_file_rejected(self):
        self.prepare()
        (self.output / "Android.bp").write_text("soong_namespace {}")
        with self.assertRaisesRegex(ims.ImsInputError, "unexpected packet file"):
            ims.verify(self.output, self.spec, self.raw)

    def test_packet_directory_symlink_rejected(self):
        self.prepare()
        (self.output / "outside").symlink_to(self.source, target_is_directory=True)
        with self.assertRaisesRegex(ims.ImsInputError, "symlink directory"):
            ims.verify(self.output, self.spec, self.raw)

    def test_missing_generated_file_rejected(self):
        self.prepare()
        (self.output / ims.PUBLIC / "admission.mk").unlink()
        with self.assertRaisesRegex(ims.ImsInputError, "file missing"):
            ims.verify(self.output, self.spec, self.raw)

    def guard(self):
        self.prepare()
        script = self.output / ims.PRIVATE / "tools/verify_inputs.py"
        produce = runpy.run_path(str(script))["produce"]
        sources = [str(self.source / row["path"]) for row in self.spec["files"]]
        build_output = self.root / "gen"
        build_output.mkdir()
        return produce, sources, build_output

    def test_generated_build_guard_produces_exact_bytes(self):
        produce, sources, output = self.guard()
        produce(sources, output)
        for row in self.spec["files"]:
            self.assertEqual((output / "verified" / row["path"]).read_bytes(),
                             (self.source / row["path"]).read_bytes())
        bp = (self.output / ims.PRIVATE / "Android.bp.in").read_text()
        for row in self.spec["files"]:
            self.assertIn(":nezha_ims_verified_inputs{verified/" + row["path"] + "}", bp)

    def test_generated_build_guard_rejects_same_size_tampering_before_writes(self):
        produce, sources, output = self.guard()
        target = Path(sources[-1])
        target.write_bytes(b"!" * target.stat().st_size)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            produce(sources, output)
        self.assertEqual(list(output.iterdir()), [])

    def test_generated_build_guard_rejects_duplicate_inputs(self):
        produce, sources, output = self.guard()
        sources[-1] = sources[0]
        with self.assertRaisesRegex(ValueError, "duplicate input"):
            produce(sources, output)
        self.assertEqual(list(output.iterdir()), [])

    def test_generated_build_guard_rejects_mixed_roots(self):
        produce, sources, output = self.guard()
        other = self.root / "other" / self.spec["files"][0]["path"]
        other.parent.mkdir(parents=True)
        other.write_bytes(Path(sources[0]).read_bytes())
        sources[0] = str(other)
        with self.assertRaisesRegex(ValueError, "mixed-root"):
            produce(sources, output)
        self.assertEqual(list(output.iterdir()), [])

    def test_generated_build_guard_preserves_existing_outputs(self):
        produce, sources, output = self.guard()
        target = output / "verified" / self.spec["files"][0]["path"]
        target.parent.mkdir(parents=True)
        target.write_text("user output")
        with self.assertRaisesRegex(ValueError, "existing IMS output"):
            produce(sources, output)
        self.assertEqual(target.read_text(), "user output")


if __name__ == "__main__":
    unittest.main()
