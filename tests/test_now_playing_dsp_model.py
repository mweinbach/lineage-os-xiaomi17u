"""The Now Playing DSP model fragment: selector rules, contract-driven hash admission, and the
copy it emits. Offline; the proprietary blobs are never required (synthetic bundles stand in)."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FRAGMENT = ROOT / "device/xiaomi/nezha/now-playing-dsp-model.mk"
VERIFY = ROOT / "device/xiaomi/nezha/now-playing-dsp-model/verify.py"
CONTRACT = ROOT / "config/nezha-now-playing-dsp-model.json"
DEVICE = ROOT / "device/xiaomi/nezha/device.mk"
# macOS puts temp dirs under /var, itself a symlink; the verifier rightly refuses symlinked ancestors.
REAL_TMP = os.path.realpath(tempfile.gettempdir())


def load_verify():
    spec = importlib.util.spec_from_file_location("np_verify", VERIFY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_bundle(tmp: Path):
    """A bundle + contract whose hashes agree, without the real blobs."""
    bundle = tmp / "bundle"; bundle.mkdir(parents=True)
    files = []
    for name, body in (("music_detector.sound_model", b"\x10\x00\x00\x10" + b"m" * 300), ("music_detector.descriptor", b"\x10\x00\x1a" + b"d" * 40)):
        (bundle / name).write_bytes(body)
        files.append({"name": name, "size_bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()})
    contract = tmp / "contract.json"
    contract.write_text(json.dumps({"files": files}))
    return bundle, contract


class ContractTests(unittest.TestCase):
    def test_contract_names_fragment_verifier_bundle_and_two_pinned_files(self):
        c = json.loads(CONTRACT.read_text())
        self.assertEqual(c["fragment"], str(FRAGMENT.relative_to(ROOT)))
        self.assertEqual(c["verifier"], str(VERIFY.relative_to(ROOT)))
        make = FRAGMENT.read_text()
        self.assertIn(c["selector"], make)
        self.assertIn(c["bundle"], make)
        names = [f["name"] for f in c["files"]]
        self.assertEqual(names, ["music_detector.sound_model", "music_detector.descriptor"])
        for f in c["files"]:
            self.assertRegex(f["sha256"], r"^[0-9a-f]{64}$")
            self.assertRegex(f["git_blob_sha1"], r"^[0-9a-f]{40}$")
            self.assertGreater(f["size_bytes"], 0)
            self.assertIn(f["name"] + ":$(TARGET_COPY_OUT_PRODUCT)/etc/firmware/" + f["name"], make)
        self.assertTrue(c["not_device_admitted"])
        self.assertIn("GENERIC_TRIGGER", c["gate_analysis"]["soundtrigger_module_0"])
        self.assertIn("include $(NEZHA_DEVICE_PATH)/now-playing-dsp-model.mk", DEVICE.read_text())
        # the build reads the in-tree copy (the guest has no repo config/ dir); it must not drift
        tree_copy = ROOT / "device/xiaomi/nezha/now-playing-dsp-model/contract.json"
        self.assertEqual(tree_copy.read_bytes(), CONTRACT.read_bytes())
        self.assertIn("NEZHA_NOW_PLAYING_CONTRACT ?= $(NEZHA_DEVICE_PATH)/now-playing-dsp-model/contract.json", make)

    def test_generator_lists_the_fragment_and_verifier(self):
        sys.path.insert(0, str(ROOT))
        from scripts import generate_device_tree as generator
        self.assertEqual(generator.TEMPLATE_FILES.count("now-playing-dsp-model.mk"), 1)
        self.assertEqual(generator.TEMPLATE_FILES.count("now-playing-dsp-model/verify.py"), 1)
        self.assertEqual(generator.TEMPLATE_FILES.count("now-playing-dsp-model/contract.json"), 1)


class VerifierTests(unittest.TestCase):
    def test_accepts_a_matching_bundle_and_rejects_drift(self):
        verify = load_verify()
        with tempfile.TemporaryDirectory(dir=REAL_TMP) as d:
            tmp = Path(d); bundle, contract = synthetic_bundle(tmp)
            self.assertEqual(verify.verify(bundle, contract), verify.TOKEN)
            # one flipped byte in the model -> refused
            p = bundle / "music_detector.sound_model"; b = bytearray(p.read_bytes()); b[10] ^= 1; p.write_bytes(bytes(b))
            with self.assertRaises(ValueError):
                verify.verify(bundle, contract)

    def test_rejects_missing_file_symlink_and_bad_names(self):
        verify = load_verify()
        with tempfile.TemporaryDirectory(dir=REAL_TMP) as d:
            tmp = Path(d); bundle, contract = synthetic_bundle(tmp)
            (bundle / "music_detector.descriptor").unlink()
            with self.assertRaises((ValueError, FileNotFoundError)):
                verify.verify(bundle, contract)
            bundle2, contract2 = synthetic_bundle(tmp / "s");
            real = bundle2 / "music_detector.descriptor"; data = real.read_bytes(); real.unlink()
            (tmp / "elsewhere").write_bytes(data); real.symlink_to(tmp / "elsewhere")
            with self.assertRaises(ValueError):
                verify.verify(bundle2, contract2)
            bad = tmp / "bad.json"; bad.write_text(json.dumps({"files": [{"name": "../x", "size_bytes": 1, "sha256": "0" * 64}]}))
            with self.assertRaises(ValueError):
                verify.verify(bundle, bad)

    def test_real_contract_pins_agree_with_the_bundle_when_present(self):
        # The real blobs are ignored inputs; when staged locally, the pins must match them exactly.
        staged = ROOT / "artifacts/nowplaying-dsp-model"
        if not staged.is_dir():
            self.skipTest("proprietary model not staged locally")
        verify = load_verify()
        self.assertEqual(verify.verify(staged, CONTRACT), verify.TOKEN)


class MakeSelectorTests(unittest.TestCase):
    def run_make(self, flag, bundle, contract):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                    f"TARGET_COPY_OUT_PRODUCT := product\n"
                    f"NEZHA_NOW_PLAYING_DSP_MODEL := {flag}\n"
                    f"NEZHA_NOW_PLAYING_BUNDLE := {bundle}\n"
                    f"NEZHA_NOW_PLAYING_CONTRACT := {contract}\n"
                    f"include {FRAGMENT}\n"
                    "all:\n\t@echo [$(PRODUCT_COPY_FILES)]\n")
        return subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile, capture_output=True, text=True,
                              env={"PATH": "/usr/bin:/bin:" + str(Path(sys.executable).parent)})

    def test_copies_both_files_only_when_true_and_admitted(self):
        with tempfile.TemporaryDirectory(dir=REAL_TMP) as d:
            bundle, contract = synthetic_bundle(Path(d))
            for flag, ok, copies in (("", True, False), ("false", True, False), ("true", True, True), ("yes", False, False), ("true false", False, False)):
                with self.subTest(flag=flag):
                    run = self.run_make(flag, bundle, contract)
                    self.assertEqual(run.returncode == 0, ok, run.stderr)
                    if ok:
                        self.assertEqual("music_detector.sound_model:product/etc/firmware/music_detector.sound_model" in run.stdout, copies, run.stdout)
                        self.assertEqual("music_detector.descriptor:product/etc/firmware/music_detector.descriptor" in run.stdout, copies, run.stdout)

    def test_refuses_a_drifted_bundle_when_true(self):
        with tempfile.TemporaryDirectory(dir=REAL_TMP) as d:
            bundle, contract = synthetic_bundle(Path(d))
            (bundle / "music_detector.sound_model").write_bytes(b"not the model")
            run = self.run_make("true", bundle, contract)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("admission failed", run.stderr)


if __name__ == "__main__":
    unittest.main()
