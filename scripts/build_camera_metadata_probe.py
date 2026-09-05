#!/usr/bin/env python3
"""Build the read-only Camera2 probe off-device with an installed Android SDK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(sdk, output, java_home, build_tools="36.0.0"):
    sdk, output, java_home = map(lambda p: Path(p).resolve(), (sdk, output, java_home))
    source = ROOT / "tools/camera-metadata-probe"
    android_jar = sdk / "platforms/android-36/android.jar"
    tools = sdk / "build-tools" / build_tools
    required = [android_jar, source / "AndroidManifest.xml", source / "ProbeActivity.java"]
    required += [tools / name for name in ("aapt2", "d8", "zipalign", "apksigner")]
    required += [java_home / "bin" / name for name in ("javac", "keytool")]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError("Missing installed inputs: " + ", ".join(missing))
    if output.exists():
        raise ValueError("Output already exists; use a new private output directory")
    # New private directory holds a dedicated diagnostic key, never the ROM key.
    output.mkdir(parents=True, mode=0o700)
    classes, dex = output / "classes", output / "dex"
    classes.mkdir()
    dex.mkdir()
    env = dict(os.environ, JAVA_HOME=str(java_home))

    def run(*args):
        subprocess.run([str(arg) for arg in args], check=True, env=env)

    run(java_home / "bin/javac", "--release", "8", "-classpath", android_jar,
        "-d", classes, source / "ProbeActivity.java")
    run(tools / "d8", "--lib", android_jar, "--min-api", "30", "--output", dex,
        *sorted(classes.rglob("*.class")))
    unsigned = output / "probe-unsigned.apk"
    run(tools / "aapt2", "link", "-I", android_jar, "--manifest",
        source / "AndroidManifest.xml", "--min-sdk-version", "30",
        "--target-sdk-version", "36", "--version-code", "1", "--version-name", "1.0",
        "-o", unsigned)
    with zipfile.ZipFile(unsigned, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.write(dex / "classes.dex", "classes.dex")
    aligned = output / "probe-aligned.apk"
    run(tools / "zipalign", "-p", "4", unsigned, aligned)
    keystore = output / "diagnostic-only.p12"
    run(java_home / "bin/keytool", "-genkeypair", "-keystore", keystore,
        "-storepass", "android", "-keypass", "android", "-alias", "probe",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
        "-dname", "CN=Nezha Camera Metadata Diagnostic")
    keystore.chmod(0o600)
    apk = output / "camera-metadata-probe.apk"
    run(tools / "apksigner", "sign", "--ks", keystore, "--ks-pass", "pass:android",
        "--key-pass", "pass:android", "--out", apk, aligned)
    run(tools / "apksigner", "verify", "--verbose", apk)
    run(tools / "zipalign", "-c", "-p", "4", apk)
    receipt = {
        "schema_version": 1, "apk": str(apk), "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "installed": False, "camera_opened": False, "build_tools": build_tools,
        "target_sdk": 36, "package": "org.nezha.camerametadataprobe",
        "inputs": {str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path):
                   hashlib.sha256(path.read_bytes()).hexdigest() for path in required},
    }
    (output / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.sdk, args.output, args.java_home), indent=2))


if __name__ == "__main__":
    main()
