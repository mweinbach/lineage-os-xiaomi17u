"""The AICore fragment: selector rules, hash admission, the three copies it emits, and the feature
declaration that is the actual gate. Offline; the proprietary files are never required."""
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
FRAGMENT = ROOT / "device/xiaomi/nezha/aicore.mk"
VERIFY = ROOT / "device/xiaomi/nezha/aicore/verify.py"
CONTRACT = ROOT / "config/nezha-aicore.json"
IN_TREE = ROOT / "device/xiaomi/nezha/aicore/contract.json"
DEVICE = ROOT / "device/xiaomi/nezha/device.mk"
# macOS temp dirs live under /var, itself a symlink; the verifier rightly refuses symlinked ancestors.
REAL_TMP = os.path.realpath(tempfile.gettempdir())
FEATURE = "com.google.android.feature.AICORE_QC_SM8850"


def load_verify():
    spec = importlib.util.spec_from_file_location("aicore_verify", VERIFY)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def synthetic_bundle(tmp: Path):
    """A bundle and contract whose hashes agree, without the real files."""
    bundle = tmp / "bundle"
    bundle.mkdir(parents=True)
    files = []
    for name, body in (("AiCore.apk", b"PK\x03\x04" + b"a" * 400),
                       ("google_aicore.xml", b"<config/>\n"),
                       ("privapp-permissions-aicore-product.xml", b"<permissions/>\n")):
        (bundle / name).write_bytes(body)
        files.append({"name": name, "size_bytes": len(body),
                      "sha256": hashlib.sha256(body).hexdigest()})
    contract = tmp / "contract.json"
    contract.write_text(json.dumps({"files": files}))
    return bundle, contract


class ContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract = json.loads(CONTRACT.read_text())

    def test_the_in_tree_copy_is_identical(self):
        # The guest has no repo config/ directory, so the fragment reads a copy beside itself.
        self.assertEqual(IN_TREE.read_bytes(), CONTRACT.read_bytes())

    def test_selector_fragment_and_verifier_exist_and_agree(self):
        self.assertEqual(self.contract["selector"], "NEZHA_AICORE")
        for key in ("fragment", "verifier"):
            self.assertTrue((ROOT / self.contract[key]).exists(), key)
        text = FRAGMENT.read_text()
        self.assertIn("NEZHA_AICORE", text)
        self.assertIn("verified-aicore-global", text)
        self.assertIn(f"include $(NEZHA_DEVICE_PATH)/aicore.mk", DEVICE.read_text())

    def test_the_fragment_adds_the_module_and_never_copies_the_apk(self):
        text = FRAGMENT.read_text()
        self.assertEqual(len(self.contract["files"]), 3)
        # Make rejects a prebuilt apk in PRODUCT_COPY_FILES, so the app is a Soong module.
        directives = [l for l in text.splitlines() if not l.lstrip().startswith("#")]
        self.assertFalse([l for l in directives if "PRODUCT_COPY_FILES" in l], directives)
        self.assertIn("PRODUCT_PACKAGES += AiCore", text)
        self.assertIn("$(filter AiCore,$(PRODUCT_PACKAGES))", text)
        self.assertEqual(self.contract["install"]["module"], "AiCore")

    def test_the_blueprint_installs_every_contract_file_where_the_contract_says(self):
        staged = ROOT / "artifacts/aicore-global/soong/Android.bp"
        if not staged.is_file():
            self.skipTest("blueprint not staged locally")
        bp = staged.read_text()
        self.assertEqual(hashlib.sha256(staged.read_bytes()).hexdigest(),
                         self.contract["soong_blueprint"]["sha256"])
        # signature preserved, privileged, and on /product where the global firmware puts it
        for token in ('name: "AiCore"', "presigned: true", "privileged: true", "product_specific: true"):
            self.assertIn(token, bp)
        for row in self.contract["files"]:
            self.assertIn(f"proprietary/{row['name']}", bp, row["name"])
            self.assertTrue(row["installed_as"].startswith("/product/"), row["installed_as"])
        self.assertIn("sub_dir: \"sysconfig\"", bp)
        self.assertIn("sub_dir: \"permissions\"", bp)

    def test_the_gate_is_the_feature_declaration(self):
        analysis = self.contract["gate_analysis"]
        self.assertIn(FEATURE, analysis["cause"])
        self.assertIn("isn't compatible", analysis["measured_before"])
        # The whole point: Google names this SoC, so the silicon is supported.
        self.assertIn("SM8850", analysis["significance"])
        dest = {row["destination"] for row in self.contract["files"]}
        self.assertIn("etc/sysconfig/google_aicore.xml", dest)

    def test_provenance_is_this_phones_own_global_firmware(self):
        prov = self.contract["provenance"]
        self.assertIn("nezha_eea_global", prov["device"])
        self.assertTrue(prov["archive_url"].endswith(".zip"))
        self.assertEqual(len(prov["product_img_sha256"]), 64)
        self.assertIn("global", prov["note"])
        # Risks are kept explicit rather than buried.
        self.assertTrue(self.contract["not_device_admitted"])
        self.assertTrue(any("stub" in r for r in self.contract["deviations_and_risks"]))
        self.assertTrue(any("ACCESS_NPU_MODEL_MANAGER_API" in r for r in self.contract["deviations_and_risks"]))

    def test_real_bundle_matches_the_pins_when_staged(self):
        staged = ROOT / "artifacts/aicore-global"
        if not staged.is_dir():
            self.skipTest("proprietary bundle not staged locally")
        verify = load_verify()
        self.assertEqual(verify.verify(staged, CONTRACT), verify.TOKEN)
        # the declaration really does name this SoC
        self.assertIn(FEATURE, (staged / "google_aicore.xml").read_text())


class VerifierTests(unittest.TestCase):
    def test_accepts_a_matching_bundle_and_rejects_drift(self):
        verify = load_verify()
        with tempfile.TemporaryDirectory(dir=REAL_TMP) as d:
            bundle, contract = synthetic_bundle(Path(d))
            self.assertEqual(verify.verify(bundle, contract), verify.TOKEN)
            (bundle / "google_aicore.xml").write_bytes(b"<config>tampered</config>\n")
            with self.assertRaises(ValueError):
                verify.verify(bundle, contract)

    def test_rejects_a_missing_member_and_a_symlinked_one(self):
        verify = load_verify()
        with tempfile.TemporaryDirectory(dir=REAL_TMP) as d:
            tmp = Path(d)
            bundle, contract = synthetic_bundle(tmp)
            (bundle / "AiCore.apk").unlink()
            with self.assertRaises((ValueError, FileNotFoundError)):
                verify.verify(bundle, contract)
            bundle2, contract2 = synthetic_bundle(tmp / "s")
            real = bundle2 / "AiCore.apk"
            data = real.read_bytes(); real.unlink()
            (tmp / "elsewhere").write_bytes(data); real.symlink_to(tmp / "elsewhere")
            with self.assertRaises(ValueError):
                verify.verify(bundle2, contract2)


class MakeSelectorTests(unittest.TestCase):
    def run_make(self, flag, bundle, contract):
        make = shutil.which("make")
        if make is None:
            self.skipTest("host GNU Make unavailable")
        makefile = (f"NEZHA_DEVICE_PATH := {ROOT}/device/xiaomi/nezha\n"
                    f"TARGET_COPY_OUT_PRODUCT := product\n"
                    f"NEZHA_AICORE := {flag}\n"
                    f"NEZHA_AICORE_BUNDLE := {bundle}\n"
                    f"NEZHA_AICORE_CONTRACT := {contract}\n"
                    f"include {FRAGMENT}\n"
                    "all:\n\t@echo [$(PRODUCT_PACKAGES)]\n")
        return subprocess.run([make, "--no-print-directory", "-f", "-"], input=makefile,
                              capture_output=True, text=True,
                              env={"PATH": "/usr/bin:/bin:" + str(Path(sys.executable).parent)})

    def test_copies_only_when_true_and_admitted(self):
        with tempfile.TemporaryDirectory(dir=REAL_TMP) as d:
            bundle, contract = synthetic_bundle(Path(d))
            for flag, ok, copies in (("", True, False), ("false", True, False), ("true", True, True),
                                     ("yes", False, False), ("true false", False, False)):
                with self.subTest(flag=flag):
                    run = self.run_make(flag, bundle, contract)
                    self.assertEqual(run.returncode == 0, ok, run.stderr)
                    if ok:
                        self.assertEqual("AiCore" in run.stdout, copies, run.stdout)

    def test_refuses_a_drifted_bundle(self):
        with tempfile.TemporaryDirectory(dir=REAL_TMP) as d:
            bundle, contract = synthetic_bundle(Path(d))
            (bundle / "AiCore.apk").write_bytes(b"not the app")
            run = self.run_make("true", bundle, contract)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn("AICore admission failed", run.stderr)


if __name__ == "__main__":
    unittest.main()
