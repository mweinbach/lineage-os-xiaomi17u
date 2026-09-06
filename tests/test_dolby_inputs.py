import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.camera_apk_inputs import Reader, identity
from scripts.dolby_inputs import CONTRACT, capture_files


class DolbyInputsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "vendor/files").mkdir(parents=True)
        self.raw = b"synthetic offline fixture"
        (self.root / "vendor/files/0001").write_bytes(self.raw)
        self.row = dict(path="/etc/test.xml", output_path="files/0001",
                        readback_verified=True, type="regular", **identity(self.raw))
        self.receipt = dict(operation="erofs-capture", image={"sha256": "a" * 64},
                            image_mounted=False, firmware_executed=False,
                            symlinks_followed=False, files=[self.row])
        self.contract = {"captures": {"vendor": {"image_sha256": "a" * 64,
                        "files": {"/etc/test.xml": identity(self.raw)}}}}

    def run_capture(self):
        (self.root / "vendor/receipt.json").write_text(json.dumps(self.receipt))
        return capture_files(Reader(), self.root, self.contract)

    def test_fixture(self):
        self.assertEqual(self.run_capture(), {"vendor/etc/test.xml": self.raw})

    def test_wrong_image(self):
        self.receipt["image"]["sha256"] = "b" * 64
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_changed_bytes(self):
        (self.root / "vendor/files/0001").write_bytes(b"changed")
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_duplicate(self):
        self.receipt["files"].append(copy.deepcopy(self.row))
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_traversal(self):
        self.row["output_path"] = "files/../../other"
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_symlink(self):
        path = self.root / "vendor/files/0001"
        path.rename(path.with_name("actual"))
        path.symlink_to("actual")
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_execution_rejected(self):
        self.receipt["firmware_executed"] = True
        with self.assertRaises(ValueError):
            self.run_capture()

    def test_contract_scope(self):
        contract = json.loads(CONTRACT.read_text())
        self.assertFalse(contract["hardware_verified"])
        self.assertEqual(contract["device"], "nezha")
        self.assertEqual(sum(len(x["files"]) for x in contract["captures"].values()), 7)
        self.assertEqual(contract["control_interface"]["set_payload"], ["parameter_id", 1, "value"])


if __name__ == "__main__":
    unittest.main()
