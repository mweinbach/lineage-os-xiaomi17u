#!/usr/bin/env python3
"""Stage a separate platform-signed Xiaomi Camera source candidate; never sign it."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import tempfile

if __package__:
    from . import camera_apk_inputs as base
    from . import camera_product_inputs as original
else:
    import camera_apk_inputs as base
    import camera_product_inputs as original


NAMESPACE = "vendor/xiaomi/nezha-camera-platform"
MODULE = "NezhaXiaomiCameraPlatform"
PERMISSION_MODULE = "nezha_xiaomi_camera_platform_privapp_permissions"
PERMISSION_FILE = "permissions/privapp-permissions-nezha-camera-platform.xml"
PRODUCT_FILE = "camera-platform-product.mk"
RECEIPT = "camera-platform-product-inputs.json"
POLICY_FILE = "provenance/platform-signing.json"
SIGNING_POLICY = {
    "schema_version": 1,
    "selector": "NEZHA_CAMERA_PLATFORM_SIGNED",
    "requires_selectors": ["NEZHA_XIAOMI_CAMERA", "NEZHA_CAMERA_FRAMEWORK"],
    "package": "com.android.camera",
    "certificate": "platform",
    "signing_stage": "android_app_import in a separately authorized Android build",
    "original_apk_bytes_preserved_in_packet": True,
    "apk_verifier_or_package_manager_modified": False,
    "strict_uses_libraries": True,
    "additional_privapp_permissions": [],
    "existing_app_data_migration": "unverified signer transition; no migration performed",
    "native_verifier_result": "unverified; original factory verifier remains required",
}


def render(source):
    """Retain the verified factory payload and request ordinary Soong signing."""
    files = {name: raw for name, raw in source.items()
             if name not in {"Android.bp", "tools/verify_camera_apk.py"}}
    # Reuse the original candidate's reviewed eleven-entry privileged policy.
    # Platform signature permissions are resolved normally by PackageManager.
    files[PERMISSION_FILE] = original.permission_policy(
        base.metadata(files["provenance/review.json"]))
    files[POLICY_FILE] = base.encoded(SIGNING_POLICY)
    files[PRODUCT_FILE] = (
        "# Platform signing candidate; source staging does not sign or install the APK.\n"
        f"PRODUCT_SOONG_NAMESPACES += {NAMESPACE}\n"
        f"PRODUCT_PACKAGES += {MODULE} {PERMISSION_MODULE} "
        "androidx.window.extensions androidx.window.sidecar\n"
    ).encode()
    blueprint = base._blueprint([*files, "Android.bp"]).decode()
    replacements = {
        "// Generated build-only input packet; no product or image admission.":
            "// Platform signing candidate; preserve payload and strict library checks.",
        "    presigned: true,\n": "    certificate: \"platform\",\n",
        "    preprocessed: true,\n": "",
        "    product_specific: true,": "    system_ext_specific: true,",
        f'    name: "{base.MODULE}",': f'    name: "{MODULE}",',
        '    owner: "xiaomi",':
            '    owner: "xiaomi",\n    filename: "MiuiCamera.apk",\n'
            f'    required: ["{PERMISSION_MODULE}"],',
    }
    for before, after in replacements.items():
        base.require(blueprint.count(before) == 1,
                     "original Camera Blueprint signing or placement contract changed")
        blueprint = blueprint.replace(before, after, 1)
    blueprint = blueprint.replace("nezha_factory_camera_", "nezha_platform_camera_")
    blueprint += f'''\nprebuilt_etc {{
    name: "{PERMISSION_MODULE}",
    src: "{PERMISSION_FILE}",
    filename: "privapp-permissions-nezha-camera-platform.xml",
    sub_dir: "permissions",
    system_ext_specific: true,
}}\n'''
    base.require("presigned:" not in blueprint and "preprocessed:" not in blueprint
                 and "product_specific:" not in blueprint,
                 "platform candidate has conflicting signing or partition properties")
    files["Android.bp"] = blueprint.encode()
    files["tools/verify_camera_apk.py"] = base._native(
        {name: base.identity(raw) for name, raw in sorted(files.items())})
    return files


def expected_packet(input_packet):
    verified = base.verify_bundle(input_packet)
    reader = base.Reader()
    source = {
        row["path"].removeprefix("source/"):
            reader.read(Path(input_packet) / row["path"], row, base.MAX_APK)
        for row in verified["files"] if row["path"].startswith("source/")
    }
    files = {"source/" + name: raw for name, raw in render(source).items()}
    receipt = {
        "schema_version": 1,
        "purpose": "factory-camera-platform-signing-system-ext-candidate",
        "partition": "system_ext",
        "namespace": NAMESPACE,
        "module": MODULE,
        "original_packet": verified["receipt"],
        "original_apk": base.identity(source[base.PAYLOAD]),
        "include": NAMESPACE + "/" + PRODUCT_FILE,
        "signing_policy": SIGNING_POLICY,
        "apk_transformed_or_signed": False,
        "key_accessed": False,
        "phone_accessed": False,
        "native_build_verified": False,
        "runtime_verified": False,
        "files": [
            {"path": name,
             "destination": NAMESPACE + "/" + name.removeprefix("source/"),
             **base.identity(raw)}
            for name, raw in sorted(files.items())
        ],
    }
    files[RECEIPT] = base.encoded(receipt)
    reader.recheck()
    return files, receipt


def verify(input_packet, bundle):
    files, receipt = expected_packet(input_packet)
    reader = base.Reader()
    base._inventory(base.directory(bundle), files, reader)
    reader.recheck()
    return receipt


def stage(input_packet, output):
    files, receipt = expected_packet(input_packet)
    output = Path(os.path.abspath(output))
    base.require(any(root in output.parents for root in
                     (base.ROOT / "artifacts", base.ROOT / "evidence")),
                 "output must stay in ignored artifacts/ or evidence/")
    base.directory(output.parent)
    base.require(not os.path.lexists(output), "output already exists")
    base.require(not output.is_relative_to(Path(input_packet).resolve()),
                 "output overlaps input packet")
    scratch = Path(tempfile.mkdtemp(prefix=".camera-platform-product-", dir=output.parent))
    try:
        for name, raw in files.items():
            path = scratch / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with path.open("xb") as stream:
                os.chmod(path, 0o600)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        verify(input_packet, scratch)
        base.publish_new_directory(scratch, output)
        scratch = None
    finally:
        if scratch is not None:
            shutil.rmtree(scratch)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["stage", "verify"])
    parser.add_argument("--input-packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = (stage(args.input_packet, args.output) if args.command == "stage"
                  else verify(args.input_packet, args.output))
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, str(error) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
