#!/usr/bin/env python3
"""Prepare the exact factory Camera APK for an unselected Android component build.

This stages a separate source namespace. It neither installs that namespace nor
runs Android, signs an APK, grants permissions, or admits an image. The native
producer checks immutable input bytes; the recorded host audit supplies the
cryptographic signature evidence, independently of Soong's packaging check.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import sys
import tempfile

if __package__:
    from .artifact_files import publish_new_directory
else:
    from artifact_files import publish_new_directory


ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/nezha-camera-apk.json"
CONTRACT_SHA256 = "0db6561f34300f7c7aea527ed5a60513f3f12bb241e8d448820a8467e23870ac"
NAMESPACE = "vendor/xiaomi/nezha-camera-apk-check"
MODULE = "nezha_factory_camera_build_check"
PRODUCER = "nezha_factory_camera_inputs_check"
VERIFIER = "nezha_factory_camera_inputs_verifier"
PAYLOAD = "proprietary/MiuiCamera.apk"
VERIFIED = "verified/MiuiCamera.apk"
RECEIPT = "camera-apk-inputs.json"
INSTALL = "source-install.json"
MAX_METADATA = 8 * 1024 * 1024
MAX_APK = 256 * 1024 * 1024
IMPORT = {"presigned": True, "preprocessed": True, "privileged": True,
          "product_specific": True, "enforce_uses_libs": True, "uses_libs": [],
          "optional_uses_libs": ["miui-cameraopt", "androidx.window.extensions", "androidx.window.sidecar"]}
SCOPE = {"source_packet_only": True, "product_packages": [], "make_namespace_exports": [],
         "native_build_verified": False, "permission_admission_complete": False,
         "mac_admission_complete": False, "image_adoption_allowed": False,
         "apk_transformed_or_signed": False, "phone_accessed": False}
BUILD_REQUIREMENTS = {
    "execution_runner_admitted": False,
    "resolve_exact_targets_from_current_graph": True,
    "required_output_roles": ["apk", "packaging_stamp", "strict_library_status", "dexpreopt_config", "odex", "vdex"],
    "required_global_settings": {"DisablePreopt": False, "OnlyPreoptArtBootImage": False,
                                 "RelaxUsesLibraryCheck": False},
    "required_providers": IMPORT["optional_uses_libs"],
    "forbidden_targets": ["module", "phony", "checkbuild", "installed_output", "image", "packaging"],
    "reject_install_writes_in_dependency_closure": True,
    "protect_install_trees_and_images_readonly_through_all_aliases": True,
    "reject_existing_camera_install_artifacts": True,
    "verify_install_inventory_unchanged_after_build": True,
    "require_fresh_empty_strict_library_status": True,
    "require_original_apk_hash_after_build": True,
    "bind_graph_sources_configs_and_providers_before_execution": True,
}


class CameraApkError(ValueError):
    pass


def require(value, message):
    if not value:
        raise CameraApkError(message)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def directory(path):
    path = Path(os.path.abspath(path))
    for parent in [*reversed(path.parents), path]:
        require(stat.S_ISDIR(parent.lstat().st_mode), "symlink or non-directory ancestor")
    return path


def relative(value):
    require(type(value) is str and re.fullmatch(r"[A-Za-z0-9_./+-]+", value), "unsafe relative path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value and
            all(part not in {"", ".", ".."} for part in value.split("/")), "noncanonical relative path")
    return value


def unique(pairs):
    value = {}
    for key, item in pairs:
        require(key not in value, "duplicate JSON key")
        value[key] = item
    return value


def metadata(raw):
    value = json.loads(raw, object_pairs_hook=unique)
    require(type(value) is dict, "metadata must be an object")
    return value


class Reader:
    def __init__(self):
        self.states = {}

    def read(self, path, expected=None, maximum=MAX_METADATA):
        path = Path(os.path.abspath(path))
        directory(path.parent)
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= maximum, "not a bounded regular input")
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
            require(signature(before) == signature(os.fstat(stream.fileno())), "input replaced before read")
            raw = stream.read(maximum + 1)
            require(signature(before) == signature(os.fstat(stream.fileno())) == signature(path.lstat())
                    and len(raw) == before.st_size, "input changed during read")
        record = identity(raw)
        require(expected is None or record == {k: expected[k] for k in record}, "input hash or size mismatch")
        previous = self.states.get(path)
        require(previous is None or previous[:2] == (signature(before), record), "input changed between reads")
        self.states[path] = (signature(before), record, min(maximum, previous[2]) if previous else maximum)
        return raw

    def recheck(self):
        for path, (_, expected, maximum) in list(self.states.items()):
            self.read(path, expected, maximum)


def load_contract(reader, contract_path=None):
    raw = reader.read(ROOT / CONFIG)
    require(identity(raw)["sha256"] == CONTRACT_SHA256, "unreviewed Camera APK contract")
    if contract_path is not None:
        require(reader.read(contract_path) == raw, "alternate contract changes reviewed inputs")
    contract = metadata(raw)
    require(contract["namespace"] == NAMESPACE and contract["module"] == MODULE
            and contract["device"] == "nezha" and contract["purpose"] == "factory-camera-build-only-inputs"
            and contract["platform"] == {"branch": "bka", "release": "bp4a"}
            and contract["import"] == IMPORT and contract["scope"] == SCOPE,
            "Camera packet must remain strictly build-only")
    return contract, raw


def _blueprint(inputs):
    sources = ",\n        ".join(json.dumps(name) for name in sorted(inputs))
    properties = "\n".join("    " + name + ": " + json.dumps(value) + "," for name, value in IMPORT.items())
    return (f'''// Generated build-only input packet; no product or image admission.
soong_namespace {{ imports: ["vendor/xiaomi/nezha"] }}

python_binary_host {{
    name: "{VERIFIER}",
    visibility: [":__pkg__"],
    main: "tools/verify_camera_apk.py",
    srcs: ["tools/verify_camera_apk.py"],
}}

genrule {{
    name: "{PRODUCER}",
    visibility: [":__pkg__"],
    tools: ["{VERIFIER}"],
    srcs: [
        {sources},
    ],
    out: ["{VERIFIED}", "camera-apk-checked.json"],
    cmd: "$(location {VERIFIER}) --output-dir $(genDir) $(in)",
}}

filegroup {{
    name: "nezha_factory_camera_verified_apk",
    visibility: [":__pkg__"],
    srcs: [":{PRODUCER}{{{VERIFIED}}}"],
}}

android_app_import {{
    name: "{MODULE}",
    visibility: [":__pkg__"],
    owner: "xiaomi",
    apk: ":nezha_factory_camera_verified_apk",
{properties}
}}
''').encode()


def _native(expected):
    # Generated identities are trusted literals, never selected by input receipts.
    return ('''#!/usr/bin/env python3
"""Publish the exact verified Camera APK; never execute or sign it."""
import hashlib, json, os, shutil, stat, sys, tempfile
from pathlib import Path, PurePosixPath
EXPECTED = ''' + repr(expected) + '''
PAYLOAD = "proprietary/MiuiCamera.apk"
OUTPUT = "verified/MiuiCamera.apk"
RECEIPT = "camera-apk-checked.json"
def need(value, message):
    if not value: raise ValueError(message)
def sig(s):
    return (s.st_dev,s.st_ino,s.st_mode,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
def realdir(p):
    for q in [*reversed(p.parents),p]:
        need(stat.S_ISDIR(q.lstat().st_mode), "non-directory or symlink ancestor")
def main(args):
    need(len(args)==len(EXPECTED)+2 and args[0]=="--output-dir", "exact native inputs required")
    contents, states, roots = {}, [], set()
    for argument in args[2:]:
        matches=[n for n in EXPECTED if argument==n or argument.endswith("/"+n)]
        need(len(matches)==1 and matches[0] not in contents, "unknown or duplicate native input")
        name=matches[0]; path=Path(os.path.abspath(argument)); realdir(path.parent)
        roots.add(path.parents[len(PurePosixPath(name).parts)-1])
        before=path.lstat(); row=EXPECTED[name]
        need(stat.S_ISREG(before.st_mode) and before.st_size==row["size_bytes"], "wrong input type or size")
        with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),"rb") as stream:
            need(sig(before)==sig(os.fstat(stream.fileno())), "input replaced")
            raw=stream.read(before.st_size+1)
            need(sig(before)==sig(os.fstat(stream.fileno()))==sig(path.lstat()), "input changed")
        need(len(raw)==row["size_bytes"] and hashlib.sha256(raw).hexdigest()==row["sha256"], "input hash mismatch")
        contents[name]=raw; states.append((path,sig(before)))
    need(len(roots)==1, "inputs must share one packet root")
    def unchanged():
        for path, original in states: need(sig(path.lstat())==original, "input changed before publication")
    unchanged()
    root=Path(os.path.abspath(args[1])); realdir(root.parent)
    source=next(iter(roots))
    need(not root.is_relative_to(source) and not any(p.exists() and p.samefile(source) for p in root.parents), "output overlaps input packet")
    if not os.path.lexists(root): root.mkdir(mode=0o700)
    realdir(root)
    for p in root.rglob("*"):
        need(stat.S_ISDIR(p.lstat().st_mode) and str(p.relative_to(root))=="verified", "output is not new and empty")
    receipt=json.dumps({"schema_version":1,"verified":True,"apk":EXPECTED[PAYLOAD],
        "contract":EXPECTED["provenance/contract.json"],"input_count":len(EXPECTED),
        "apk_executed_or_signed":False,"image_adoption_allowed":False},sort_keys=True,indent=2).encode()+b"\\n"
    staging=Path(tempfile.mkdtemp(prefix=".camera-verified-",dir=root)); published=[]
    try:
        for name,raw in ((OUTPUT,contents[PAYLOAD]),(RECEIPT,receipt)):
            p=staging/name; p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
            with p.open("xb") as f:
                os.chmod(p,0o600); f.write(raw); f.flush(); os.fsync(f.fileno())
            need(p.read_bytes()==raw, "output readback mismatch")
        unchanged()
        for name in (OUTPUT,RECEIPT):
            target=root/name; target.parent.mkdir(parents=True,exist_ok=True,mode=0o700); realdir(target.parent)
            original=(staging/name).lstat(); published.append((target,original.st_dev,original.st_ino))
            os.link(staging/name,target,follow_symlinks=False)
        unchanged()
    except BaseException:
        for p,dev,ino in reversed(published):
            try:
                s=p.lstat()
                if (s.st_dev,s.st_ino)==(dev,ino): p.unlink()
            except FileNotFoundError: pass
        raise
    finally: shutil.rmtree(staging)
    print(json.dumps({"verified":True,"image_adoption_allowed":False}))
if __name__=="__main__":
    try: main(sys.argv[1:])
    except (OSError,ValueError) as error:
        print("Camera input verification failed: "+str(error),file=sys.stderr); sys.exit(2)
''').encode()


REFERENCES = ("capture", "review", "runtime_contract", "runtime_bundle", "source_lock", "provider_patch", "native_fixture_record")
PROVENANCE = {name: "provenance/" + name + (".patch" if name == "provider_patch" else ".json")
              for name in REFERENCES}


def _sources(contract, raw, controls, apk):
    review = metadata(controls["review"])
    capture = metadata(controls["capture"])
    require(review["factory_input"]["capture"] == contract["capture"]
            and review["factory_input"]["sha256"] == contract["apk"]["sha256"]
            and review["factory_input"]["size_bytes"] == contract["apk"]["size_bytes"]
            and review["signature"]["certificate_sha256"] == contract["signer_certificate_sha256"]
            and review["signature"]["verified_schemes"] == ["v3"]
            and review["packaging"]["preprocessed_privileged_with_uncompress_priv_app_dex_exit_code"] == 0
            and review["uses_libraries"]["optional_in_order"] == IMPORT["optional_uses_libs"]
            and review["uses_libraries"]["exact_strict_check_exit_code"] == 0
            and review["runtime_dependencies"]["contract"] == contract["runtime_contract"]
            and review["runtime_dependencies"]["bundle_receipt"] == contract["runtime_bundle"],
            "APK audit does not support these exact inputs")
    image = contract["factory_image"]
    require(capture["operation"] == "erofs-capture" and capture["image"]["sha256"] == image["sha256"]
            and capture["image"]["size_bytes"] == image["size_bytes"]
            and all(capture[k] is False for k in ("firmware_executed", "image_mounted", "symlinks_followed"))
            and len(capture["files"]) == 1, "capture is not the original bounded factory input")
    row = capture["files"][0]
    require(row["path"] == contract["apk"]["image_relative_path"] and row["nid"] == contract["apk"]["nid"]
            and row["output_path"] == "files/0001" and row["type"] == "regular" and row["readback_verified"] is True
            and identity(apk) == {k: row[k] for k in ("sha256", "size_bytes")}
            == {k: contract["apk"][k] for k in ("sha256", "size_bytes")}, "captured APK identity mismatch")
    files = {"provenance/contract.json": raw, PAYLOAD: apk}
    files.update({PROVENANCE[name]: controls[name] for name in REFERENCES})
    files["Android.bp"] = _blueprint([*files, "Android.bp"])
    files["tools/verify_camera_apk.py"] = _native({name: identity(data) for name, data in sorted(files.items())})
    return files


def _packet(contract, raw, source):
    install = {"schema_version": 1, "namespace": NAMESPACE, "module": MODULE,
               "destination_must_be_new": True, "contract": identity(raw),
               "files": [{"packet_path": "source/" + name, "destination": NAMESPACE + "/" + name,
                          **identity(data)} for name, data in sorted(source.items())],
               "source_requirements": contract["source_requirements"], "scope": SCOPE,
               "build_requirements": BUILD_REQUIREMENTS}
    files = {"source/" + name: data for name, data in source.items()}
    files[INSTALL] = encoded(install)
    receipt = {"schema_version": 1, "operation": "stage-factory-camera-build-only-inputs",
               "contract": identity(raw), "namespace": NAMESPACE, "module": MODULE,
               "files": [{"path": name, **identity(data)} for name, data in sorted(files.items())],
               "scope": SCOPE, "build_requirements": BUILD_REQUIREMENTS}
    files[RECEIPT] = encoded(receipt)
    return files, receipt


def _inventory(root, files, reader):
    allowed_dirs = {str(p) for name in files for p in PurePosixPath(name).parents if str(p) != "."}
    seen = set()
    for path in root.rglob("*"):
        name = path.relative_to(root).as_posix()
        mode = path.lstat().st_mode
        if stat.S_ISDIR(mode):
            require(name in allowed_dirs, "extra packet directory")
        else:
            require(stat.S_ISREG(mode) and name in files, "extra, symlinked or special packet file")
            require(reader.read(path, maximum=MAX_APK if name.endswith(".apk") else MAX_METADATA) == files[name],
                    "packet differs from the reviewed renderer")
            seen.add(name)
    require(seen == set(files), "missing packet file")


def verify_bundle(bundle, *, contract_path=None):
    reader = Reader()
    contract, raw = load_contract(reader, contract_path)
    root = directory(bundle)
    controls = {name: reader.read(root / "source" / PROVENANCE[name], contract[name]) for name in REFERENCES}
    apk = reader.read(root / "source" / PAYLOAD, contract["apk"], MAX_APK)
    files, receipt = _packet(contract, raw, _sources(contract, raw, controls, apk))
    _inventory(root, files, reader)
    reader.recheck()
    _inventory(root, files, reader)
    return {**receipt, "receipt": {"path": RECEIPT, **identity(files[RECEIPT])},
            "source_install_contract": {"path": INSTALL, **identity(files[INSTALL])}, "readback_verified": True}


def stage_inputs(inputs_root, output, *, contract_path=None):
    reader = Reader()
    contract, raw = load_contract(reader, contract_path)
    root = directory(inputs_root)
    destination = Path(os.path.abspath(output))
    require(any(p in destination.parents for p in (ROOT / "artifacts", ROOT / "evidence")), "output must stay in ignored artifacts/ or evidence/")
    require(not os.path.lexists(destination), "output already exists")
    directory(destination.parent)
    for name in REFERENCES:
        protected = root / relative(contract[name]["path"])
        parent = directory(protected.parent)
        require(not destination.is_relative_to(parent) and not any(p.exists() and p.samefile(parent) for p in destination.parents),
                "output overlaps preserved input directory")
    controls = {name: reader.read(root / relative(contract[name]["path"]), contract[name]) for name in REFERENCES}
    capture = metadata(controls["capture"])
    require(len(capture.get("files", [])) == 1 and capture["files"][0].get("output_path") == "files/0001", "unexpected capture selection")
    apk = reader.read((root / contract["capture"]["path"]).parent / "files/0001", contract["apk"], MAX_APK)
    files, receipt = _packet(contract, raw, _sources(contract, raw, controls, apk))
    staging = Path(tempfile.mkdtemp(prefix=".camera-apk-", dir=destination.parent))
    try:
        for name, data in files.items():
            path = staging / name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with path.open("xb") as stream:
                os.chmod(path, 0o600)
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
        verify_bundle(staging, contract_path=contract_path)
        reader.recheck()
        verify_bundle(staging, contract_path=contract_path)
        publish_new_directory(staging, destination)
        staging = None
        return receipt
    finally:
        if staging is not None:
            shutil.rmtree(staging)


def verify_installed(bundle, source_root, *, contract_path=None):
    """Read back only the owned namespace and required Soong source identities."""
    verified = verify_bundle(bundle, contract_path=contract_path)
    reader = Reader()
    contract, _ = load_contract(reader, contract_path)
    root = directory(source_root)
    packet = directory(bundle)
    expected = {row["path"].removeprefix("source/"): reader.read(packet / row["path"], row, MAX_APK)
                for row in verified["files"] if row["path"].startswith("source/")}
    _inventory(directory(root / NAMESPACE), expected, reader)
    source = contract["source_requirements"]
    project = directory(root / source["project"])
    head = subprocess.run(["git", "-C", str(project), "rev-parse", "--show-toplevel", "HEAD"],
                          capture_output=True, text=True, check=True, timeout=30).stdout.splitlines()
    require(len(head) == 2 and Path(head[0]).resolve() == project and head[1] == source["revision"], "wrong Soong project or revision")
    for name, digest in source["files"].items():
        require(identity(reader.read(project / relative(name)))["sha256"] == digest, "required Soong source state differs")
    runtime = metadata(reader.read(packet / "source/provenance/runtime_bundle.json", contract["runtime_bundle"]))
    require(len(runtime["extras"]) == 9, "runtime dependency profile no longer has nine inputs")
    for row in runtime["extras"]:
        reader.read(root / "vendor/xiaomi/nezha" / relative(row["path"]), row)
    blueprint = [row for row in runtime["generated_files"] if row["path"] == "Android.bp"]
    require(len(blueprint) == 1, "runtime namespace Blueprint is missing or duplicated")
    reader.read(root / "vendor/xiaomi/nezha/Android.bp", blueprint[0])
    reader.recheck()
    _inventory(directory(root / NAMESPACE), expected, reader)
    return {"namespace": NAMESPACE, "exact_namespace_readback_verified": True,
            "required_soong_files_verified": True, "nine_runtime_inputs_and_blueprint_verified": True,
            "product_membership_verified": False,
            "native_execution_admitted": False, "scope": SCOPE, "receipt": verified["receipt"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    stage = sub.add_parser("stage")
    stage.add_argument("--inputs-root", type=Path, default=ROOT)
    stage.add_argument("--output", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    installed = sub.add_parser("verify-installed")
    installed.add_argument("--bundle", type=Path, required=True)
    installed.add_argument("--source-root", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            result = stage_inputs(args.inputs_root, args.output)
        elif args.command == "verify":
            result = verify_bundle(args.bundle)
        else:
            result = verify_installed(args.bundle, args.source_root)
        print(json.dumps(result, indent=2, sort_keys=True))
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print("Camera APK admission failed: " + str(error), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
