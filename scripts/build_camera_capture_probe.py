#!/usr/bin/env python3
"""Build the foreground Camera2 capture diagnostic off-device using installed SDK 36."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def build(sdk, output, java_home, build_tools="36.0.0"):
    sdk, output, java_home = map(lambda path: Path(path).resolve(), (sdk, output, java_home))
    source = ROOT / "tools/camera-capture-probe"
    android_jar = sdk / "platforms/android-36/android.jar"
    tool_dir = sdk / "build-tools" / build_tools
    sources = sorted(source.glob("*.java"))
    required = [Path(__file__).resolve(), android_jar, source / "AndroidManifest.xml", *sources]
    required += [tool_dir / name for name in ("aapt2", "d8", "zipalign", "apksigner")]
    required += [java_home / "bin" / name for name in ("javac", "keytool")]
    if not sources:
        raise ValueError("No authored capture-probe Java sources")
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError("Missing installed inputs: " + ", ".join(missing))
    if not output.is_relative_to(ROOT / "artifacts"):
        raise ValueError("Diagnostic APK and signing key output must be in ignored artifacts/")
    if output.exists():
        raise ValueError("Output already exists; select a new private artifact directory")
    # Refuse a public artifact root even if local ignore rules change in a future checkout.
    ignored = subprocess.run(["git", "check-ignore", "--quiet", str(output)], cwd=ROOT, check=False)
    if ignored.returncode != 0:
        raise ValueError("Output is not Git-ignored")
    input_hashes = {
        str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path):
            hashlib.sha256(path.read_bytes()).hexdigest() for path in required
    }
    output.mkdir(parents=True, mode=0o700)
    classes, dex = output / "classes", output / "dex"
    classes.mkdir()
    dex.mkdir()
    env = dict(os.environ, JAVA_HOME=str(java_home))

    def run(*args):
        subprocess.run([str(arg) for arg in args], check=True, env=env)

    run(java_home / "bin/javac", "--release", "8", "-classpath", android_jar,
        "-d", classes, *sources)
    run(tool_dir / "d8", "--lib", android_jar, "--min-api", "34", "--output", dex,
        *sorted(classes.rglob("*.class")))
    unsigned = output / "probe-unsigned.apk"
    run(tool_dir / "aapt2", "link", "-I", android_jar, "--manifest", source / "AndroidManifest.xml",
        "--min-sdk-version", "34", "--target-sdk-version", "36", "--version-code", "1",
        "--version-name", "1.0", "-o", unsigned)
    with zipfile.ZipFile(unsigned, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(dex.glob("classes*.dex")):
            archive.write(path, path.name)
    aligned = output / "probe-aligned.apk"
    run(tool_dir / "zipalign", "-p", "4", unsigned, aligned)
    keystore = output / "diagnostic-only.p12"
    run(java_home / "bin/keytool", "-genkeypair", "-keystore", keystore,
        "-storepass", "android", "-keypass", "android", "-alias", "probe",
        "-keyalg", "RSA", "-keysize", "2048", "-validity", "3650",
        "-dname", "CN=Nezha Camera Capture Diagnostic")
    keystore.chmod(0o600)
    apk = output / "camera-capture-probe.apk"
    run(tool_dir / "apksigner", "sign", "--ks", keystore, "--ks-pass", "pass:android",
        "--key-pass", "pass:android", "--out", apk, aligned)
    run(tool_dir / "apksigner", "verify", "--verbose", apk)
    run(tool_dir / "zipalign", "-c", "-p", "4", apk)
    for path in required:
        key = str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != input_hashes[key]:
            raise ValueError("Build input changed during compilation: " + key)
    receipt = {
        "schema_version": 1,
        "apk": str(apk),
        "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "installed": False,
        "camera_opened": False,
        "capture_verified": False,
        "build_tools": build_tools,
        "min_sdk": 34,
        "target_sdk": 36,
        "package": "org.nezha.cameracaptureprobe",
        "inputs": input_hashes,
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
