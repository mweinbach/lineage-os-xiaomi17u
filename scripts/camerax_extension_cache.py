#!/usr/bin/env python3
"""Rebuild the pinned CameraX cache class and preserve the rest of its public AAR."""
from __future__ import annotations

import argparse
import copy
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "config/nezha-camerax-extension-cache.json"


def identity(path: Path) -> dict:
    with path.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    return {"sha256": digest, "size_bytes": path.stat().st_size}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def checked(path: Path, expected: dict) -> dict:
    require(path.is_file() and not path.is_symlink(), f"Not a regular input: {path}")
    actual = identity(path)
    require(actual == expected, f"Input identity differs: {path}")
    return {"path": str(path.resolve()), **actual}


def members(raw: bytes) -> tuple[list[zipfile.ZipInfo], dict[str, bytes]]:
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        infos = archive.infolist()
        names = [item.filename for item in infos]
        require(len(names) == len(set(names)), "Duplicate ZIP member")
        for name in names:
            path = PurePosixPath(name)
            require(not path.is_absolute() and ".." not in path.parts and "\\" not in name,
                    f"Unsafe ZIP member: {name}")
        require(sum(item.file_size for item in infos) < 512 * 1024 * 1024,
                "Unexpectedly large archive")
        return infos, {item.filename: archive.read(item) for item in infos}


def replace_members(raw: bytes, replacements: dict[str, bytes]) -> bytes:
    infos, original = members(raw)
    require(set(replacements) <= original.keys(), "Replacement introduces an archive member")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        for info in infos:
            archive.writestr(copy.copy(info), replacements.get(info.filename, original[info.filename]))
    result = output.getvalue()
    _, after = members(result)
    require(after.keys() == original.keys(), "Archive member set changed")
    for name, data in original.items():
        require(after[name] == replacements.get(name, data), f"Unexpected member change: {name}")
    return result


def rebuild_aar(original: bytes, compiled: bytes, allowed_classes: list[str]) -> tuple[bytes, dict]:
    _, aar = members(original)
    require("classes.jar" in aar, "AAR has no classes.jar")
    _, generated = members(compiled)
    classes = {name: data for name, data in generated.items() if name.endswith(".class")}
    require(set(classes) == set(allowed_classes), "Compiler emitted an unexpected class set")
    original_jar = aar["classes.jar"]
    _, original_classes = members(original_jar)
    require(set(classes) <= original_classes.keys(), "Compiled class is absent from original AAR")
    patched_jar = replace_members(original_jar, classes)
    patched_aar = replace_members(original, {"classes.jar": patched_jar})
    changed = [name for name in classes if classes[name] != original_classes[name]]
    return patched_aar, {
        "allowed_classes": sorted(classes), "changed_classes": sorted(changed),
        "unchanged_class_jar_members": len(original_classes) - len(changed),
        "unchanged_outer_members": len(aar) - 1,
        "member_sets_preserved": True,
    }


def public_signatures(raw: str) -> list[str]:
    # javap may reorder synthetic accessors without changing their JVM interface.
    return sorted(block.strip() for block in raw.split("\n\n") if "descriptor:" in block)


def materialize(args: argparse.Namespace) -> dict:
    contract = json.loads(CONTRACT.read_text())
    require(contract["operation"] == "nezha-camerax-extension-cache-backport-v1", "Wrong contract")
    require(not args.output.exists(), "Output already exists")
    source = ROOT / contract["template"]
    inputs = {
        "source": checked(source, contract["template_identity"]),
        "source_patch": checked(ROOT / contract["patch"], contract["patch_identity"]),
        "original_aar": checked(args.original_aar, contract["original_aar"]),
        "dependency_jar": checked(args.dependency_jar, contract["dependency_jar"]),
        "android_jar": checked(args.android_jar, contract["android_jar"]),
        "compiler": {name: checked(args.compiler_dir / name, pin)
                     for name, pin in contract["compiler_jars"].items()},
    }
    args.output.mkdir(parents=True)
    _, aar = members(args.original_aar.read_bytes())
    original_jar = args.output / "original-classes.jar"
    original_jar.write_bytes(aar["classes.jar"])
    checked(original_jar, contract["original_classes_jar"])
    compiled = args.output / "compiled-cache.jar"
    classpath = ":".join(str(p.resolve()) for p in (
        original_jar, args.dependency_jar, args.android_jar,
        args.compiler_dir / "kotlin-stdlib.jar", args.compiler_dir / "annotations-13.0.jar"))
    compiler_classpath = ":".join(str((args.compiler_dir / name).resolve())
                                  for name in contract["compiler_jars"])
    command = [args.java, "-cp", compiler_classpath, "org.jetbrains.kotlin.cli.jvm.K2JVMCompiler",
               "-jvm-target", contract["jvm_target"], "-module-name", contract["module_name"],
               "-no-stdlib", "-no-reflect",
               "-Xfriend-paths=" + str(original_jar.resolve()) + "," + str(args.dependency_jar.resolve()),
               "-classpath", classpath, "-d", str(compiled.resolve()), str(source.resolve())]
    (args.output / "compile-command.json").write_text(json.dumps(command, indent=2) + "\n")
    with (args.output / "compile.log").open("wb") as log:
        result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, timeout=120)
    require(result.returncode == 0, "Kotlin compilation failed; see compile.log")
    abi = []
    for name in contract["classes"]:
        class_name = name[:-6].replace("/", ".")
        before = subprocess.check_output([args.javap, "-public", "-s", "-classpath",
                                          str(original_jar), class_name], text=True, timeout=30)
        after = subprocess.check_output([args.javap, "-public", "-s", "-classpath",
                                         str(compiled), class_name], text=True, timeout=30)
        require(public_signatures(before) == public_signatures(after), f"Public ABI changed: {name}")
        abi.append({"class": name, "public_signatures_identical": True})
    output, audit = rebuild_aar(args.original_aar.read_bytes(), compiled.read_bytes(), contract["classes"])
    destination = args.output / "camera-camera2-pipe-1.7.0-alpha03-nezha-cache.aar"
    destination.write_bytes(output)
    receipt = {"schema_version": 1, "operation": contract["operation"], "status": "materialized",
               "contract": {"path": str(CONTRACT), **identity(CONTRACT)}, "inputs": inputs,
               "compiled_jar": identity(compiled), "class_audit": audit, "abi_audit": abi,
               "output": {"path": str(destination.resolve()), **identity(destination)},
               "phone_accessed": False, "android_app_build_verified": False, "runtime_verified": False}
    (args.output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-aar", type=Path, required=True)
    parser.add_argument("--dependency-jar", type=Path, required=True)
    parser.add_argument("--android-jar", type=Path, required=True)
    parser.add_argument("--compiler-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--java", default="java")
    parser.add_argument("--javap", default="javap")
    print(json.dumps(materialize(parser.parse_args()), indent=2))


if __name__ == "__main__":
    main()
