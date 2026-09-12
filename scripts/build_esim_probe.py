#!/usr/bin/env python3
"""Build the eSIM diagnostic APK locally with an explicitly supplied platform key."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"


def build(sdk, output, java_home, platform_key, platform_cert,
          build_tools="37.0.0", platform=36):
    sdk, output, java_home, platform_key, platform_cert = (
        Path(path).resolve() for path in
        (sdk, output, java_home, platform_key, platform_cert)
    )
    source = ROOT / "tools/esim-probe"
    manifest = source / "AndroidManifest.xml"
    sources = sorted((source / "src").rglob("*.java"))
    android_jar = sdk / f"platforms/android-{platform}/android.jar"
    tool_dir = sdk / "build-tools" / build_tools
    # Only public inputs belong in this list. The PK8 is passed to apksigner
    # directly and is never read, copied, hashed, or included in the receipt.
    required = [Path(__file__).resolve(), manifest, *sources, android_jar, platform_cert]
    required += [tool_dir / name for name in ("aapt2", "d8", "zipalign", "apksigner")]
    required += [java_home / "bin/javac"]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise ValueError("Missing installed public inputs: " + ", ".join(missing))
    if not sources:
        raise ValueError("No authored eSIM probe Java sources")
    if not platform_key.is_file():
        raise ValueError("An existing platform PK8 key is required")
    artifact_root = ROOT / "artifacts"
    if output == artifact_root or not output.is_relative_to(artifact_root):
        raise ValueError("APK output must be inside ignored artifacts/")
    if output.exists():
        raise ValueError("Output already exists; select a new private artifact directory")
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", str(output)], cwd=ROOT, check=False,
        capture_output=True,
    )
    if ignored.returncode != 0:
        raise ValueError("Output is not Git-ignored")

    manifest_root = ET.parse(manifest).getroot()
    uses_sdk = manifest_root.find("uses-sdk")
    if uses_sdk is None:
        raise ValueError("Manifest must declare minSdkVersion and targetSdkVersion")
    try:
        min_sdk = int(uses_sdk.attrib[ANDROID + "minSdkVersion"])
        target_sdk = int(uses_sdk.attrib[ANDROID + "targetSdkVersion"])
        version_code = int(manifest_root.attrib[ANDROID + "versionCode"])
        version_name = manifest_root.attrib[ANDROID + "versionName"]
        package = manifest_root.attrib["package"]
    except (KeyError, ValueError) as exc:
        raise ValueError("Manifest must declare numeric SDK/versionCode and package/versionName") from exc
    if not 1 <= min_sdk <= target_sdk <= platform or version_code < 1:
        raise ValueError("Manifest SDK/version values are incompatible with the selected platform")
    cert_der = ssl.PEM_cert_to_DER_cert(platform_cert.read_text())
    expected_signer = hashlib.sha256(cert_der).hexdigest()

    def public_name(path):
        return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)

    input_hashes = {
        public_name(path): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in required
    }
    output.mkdir(parents=True, mode=0o700)
    classes, dex = output / "classes", output / "dex"
    classes.mkdir()
    dex.mkdir()
    env = dict(os.environ, JAVA_HOME=str(java_home))

    def run(*args, private=False):
        # In particular, a failed signing command must not expose the PK8 path
        # through CalledProcessError, argv logging, or signer diagnostics.
        result = subprocess.run(
            [str(arg) for arg in args], check=False, env=env,
            capture_output=True, text=True, stdin=subprocess.DEVNULL,
        )
        if result.returncode:
            detail = "" if private else "\n" + (result.stderr or result.stdout).strip()
            raise RuntimeError(f"{Path(args[0]).name} failed (exit {result.returncode}){detail}")
        return result.stdout

    run(java_home / "bin/javac", "--release", "8", "-classpath", android_jar,
        "-d", classes, *sources)
    run(tool_dir / "d8", "--lib", android_jar, "--min-api", min_sdk,
        "--output", dex, *sorted(classes.rglob("*.class")))
    unsigned = output / "probe-unsigned.apk"
    # Package metadata stays in the manifest; do not override its versions.
    run(tool_dir / "aapt2", "link", "-I", android_jar, "--manifest", manifest,
        "-o", unsigned)
    dex_files = sorted(dex.glob("classes*.dex"))
    if not dex_files:
        raise ValueError("D8 produced no DEX files")
    with zipfile.ZipFile(unsigned, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in dex_files:
            archive.write(path, path.name)
    aligned = output / "probe-aligned.apk"
    run(tool_dir / "zipalign", "-p", "4", unsigned, aligned)
    apk = output / "nezha-esim-probe.apk"
    run(tool_dir / "apksigner", "sign", "--key", platform_key, "--cert", platform_cert,
        "--out", apk, aligned, private=True)
    verification = run(tool_dir / "apksigner", "verify", "--verbose", "--print-certs", apk)
    signer_counts = re.findall(r"^Number of signers:\s*(\d+)\s*$", verification,
                               flags=re.MULTILINE)
    signer_digests = re.findall(
        r"^(?:Signer #\d+|V[123](?:\.\d+)? Signer:) certificate SHA-256 digest:"
        r"\s*([0-9a-fA-F]{64})\s*$",
        verification, flags=re.MULTILINE,
    )
    if ((signer_counts and signer_counts != ["1"])
            or [value.lower() for value in signer_digests] != [expected_signer]):
        raise ValueError("APK signer does not uniquely match the supplied public platform certificate")
    run(tool_dir / "zipalign", "-c", "-p", "4", apk)
    for path in required:
        name = public_name(path)
        if hashlib.sha256(path.read_bytes()).hexdigest() != input_hashes[name]:
            raise ValueError("Public build input changed during compilation: " + name)
    receipt = {
        "schema_version": 1,
        "apk": str(apk),
        "apk_sha256": hashlib.sha256(apk.read_bytes()).hexdigest(),
        "package": package,
        "version_code": version_code,
        "version_name": version_name,
        "min_sdk": min_sdk,
        "target_sdk": target_sdk,
        "compile_sdk": platform,
        "build_tools": build_tools,
        "signer_certificate_sha256": expected_signer,
        "signer_matches_supplied_certificate": True,
        "apk_signature_verified": True,
        "apk_alignment_verified": True,
        "private_key_included_in_receipt": False,
        "installed": False,
        "inputs": input_hashes,
    }
    (output / "build-receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", type=Path, required=True)
    parser.add_argument("--java-home", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--platform-key", type=Path, required=True)
    parser.add_argument("--platform-cert", type=Path, required=True)
    parser.add_argument("--build-tools", default="37.0.0")
    parser.add_argument("--platform", type=int, default=36)
    args = parser.parse_args()
    print(json.dumps(build(args.sdk, args.output, args.java_home, args.platform_key,
                           args.platform_cert, args.build_tools, args.platform), indent=2))


if __name__ == "__main__":
    main()
