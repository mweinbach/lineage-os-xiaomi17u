import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest import mock
import zipfile


PATH = Path(__file__).resolve().parents[3] / "scripts/build_esim_probe.py"
SPEC = importlib.util.spec_from_file_location("build_esim_probe", PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class EsimProbeBuilderTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.sdk, self.jdk = self.root / "sdk", self.root / "jdk"
        self.output = self.root / "artifacts/probe"
        self.key, self.cert = self.root / "private.pk8", self.root / "platform.x509.pem"
        self.key.write_bytes(b"synthetic private key; never a real signing key")
        self.cert.write_text("-----BEGIN CERTIFICATE-----\nY2VydGlmaWNhdGU=\n-----END CERTIFICATE-----\n")
        self.cert_digest = hashlib.sha256(b"certificate").hexdigest()
        for relative in ("platforms/android-36/android.jar", "build-tools/37.0.0/aapt2",
                         "build-tools/37.0.0/d8", "build-tools/37.0.0/zipalign",
                         "build-tools/37.0.0/apksigner"):
            path = self.sdk / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("synthetic SDK input")
        (self.jdk / "bin").mkdir(parents=True)
        (self.jdk / "bin/javac").write_text("synthetic compiler")
        source = self.root / "tools/esim-probe"
        (source / "src/org/nezha/esimprobe").mkdir(parents=True)
        (source / "src/org/nezha/esimprobe/Probe.java").write_text("class Probe {}")
        (source / "AndroidManifest.xml").write_text(
            '<manifest xmlns:android="http://schemas.android.com/apk/res/android" '
            'package="org.nezha.esimprobe" android:versionCode="3" android:versionName="3">'
            '<uses-sdk android:minSdkVersion="35" android:targetSdkVersion="36"/>'
            '</manifest>'
        )
        self.calls = []
        self.signer_digest = self.cert_digest
        self.signer_label = "Signer #1"
        self.signer_count = None
        self.fail_signing = False

    def run_fake(self, argv, **kwargs):
        self.calls.append(argv)
        name = Path(argv[0]).name
        stdout = ""
        if name == "javac":
            (Path(argv[argv.index("-d") + 1]) / "Probe.class").write_bytes(b"class")
        elif name == "d8":
            (Path(argv[argv.index("--output") + 1]) / "classes.dex").write_bytes(b"dex")
        elif name == "aapt2":
            with zipfile.ZipFile(argv[argv.index("-o") + 1], "w") as archive:
                archive.writestr("AndroidManifest.xml", b"compiled manifest")
        elif name == "zipalign" and "-c" not in argv:
            shutil.copyfile(argv[-2], argv[-1])
        elif name == "apksigner" and argv[1] == "sign":
            if self.fail_signing:
                return subprocess.CompletedProcess(argv, 1, "", f"failure reading {self.key}")
            shutil.copyfile(argv[-1], argv[argv.index("--out") + 1])
        elif name == "apksigner" and argv[1] == "verify":
            stdout = f"{self.signer_label} certificate SHA-256 digest: {self.signer_digest}\n"
            if self.signer_count is not None:
                stdout = f"Number of signers: {self.signer_count}\n" + stdout
        return subprocess.CompletedProcess(argv, 0, stdout, "")

    def build(self):
        with mock.patch.object(MODULE, "ROOT", self.root), mock.patch.object(
                MODULE.subprocess, "run", side_effect=self.run_fake):
            return MODULE.build(self.sdk, self.output, self.jdk, self.key, self.cert)

    def test_success_uses_manifest_and_never_reads_or_records_private_key(self):
        original_read = Path.read_bytes

        def public_read(path):
            if path == self.key:
                raise AssertionError("Builder attempted to read private key")
            return original_read(path)

        with mock.patch.object(Path, "read_bytes", public_read):
            receipt = self.build()
        self.assertEqual(receipt["version_code"], 3)
        self.assertEqual(receipt["version_name"], "3")
        self.assertEqual(receipt["min_sdk"], 35)
        self.assertEqual(receipt["target_sdk"], 36)
        self.assertEqual(receipt["signer_certificate_sha256"], self.cert_digest)
        self.assertTrue(receipt["apk_alignment_verified"])
        self.assertNotIn(str(self.key), json.dumps(receipt))
        self.assertFalse(receipt["installed"])
        aapt = next(args for args in self.calls if Path(args[0]).name == "aapt2")
        self.assertNotIn("--version-code", aapt)
        self.assertNotIn("--target-sdk-version", aapt)
        d8 = next(args for args in self.calls if Path(args[0]).name == "d8")
        self.assertEqual(d8[d8.index("--min-api") + 1], "35")

    def test_mismatched_signer_has_no_success_receipt(self):
        self.signer_digest = "0" * 64
        with self.assertRaisesRegex(ValueError, "signer does not uniquely match"):
            self.build()
        self.assertFalse((self.output / "build-receipt.json").exists())

    def test_apksigner_37_v3_signer_format(self):
        self.signer_label = "V3.0 Signer:"
        self.signer_count = 1
        receipt = self.build()
        self.assertEqual(receipt["signer_certificate_sha256"], self.cert_digest)
        self.assertTrue(receipt["apk_signature_verified"])

    def test_signer_count_must_be_one_when_reported(self):
        self.signer_label = "V3.0 Signer:"
        self.signer_count = 2
        with self.assertRaisesRegex(ValueError, "signer does not uniquely match"):
            self.build()
        self.assertFalse((self.output / "build-receipt.json").exists())

    def test_signing_error_does_not_expose_private_key_path(self):
        self.fail_signing = True
        with self.assertRaises(RuntimeError) as caught:
            self.build()
        self.assertNotIn(str(self.key), str(caught.exception))
        self.assertFalse((self.output / "build-receipt.json").exists())

    def test_existing_and_nonignored_output_fail_before_compilation(self):
        self.output.mkdir(parents=True)
        with self.assertRaisesRegex(ValueError, "Output already exists"):
            self.build()
        self.assertEqual(self.calls, [])
        self.output.rmdir()
        with mock.patch.object(MODULE, "ROOT", self.root), mock.patch.object(
                MODULE.subprocess, "run", return_value=subprocess.CompletedProcess([], 1)) as run:
            with self.assertRaisesRegex(ValueError, "not Git-ignored"):
                MODULE.build(self.sdk, self.output, self.jdk, self.key, self.cert)
        self.assertEqual(run.call_count, 1)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
