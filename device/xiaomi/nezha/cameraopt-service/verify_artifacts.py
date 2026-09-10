#!/usr/bin/env python3
"""Validate built CameraOpt runtime ownership using ZIP members and DEX definitions.

This check is offline. It consumes build artifacts and an extracted system-server
classpath list; it does not start a service or contact a phone.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile


class ValidationError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dex_classes(data: bytes) -> set[str]:
    """Read class definitions, not mere referenced class-name strings."""
    require(len(data) >= 112, "DEX header is truncated")
    require(data[:4] == b"dex\n" and data[4:7].isdigit() and data[7] == 0,
            "Unsupported DEX magic")

    def u32(offset: int) -> int:
        require(0 <= offset <= len(data) - 4, "DEX integer is out of bounds")
        return struct.unpack_from("<I", data, offset)[0]

    require(u32(32) == len(data), "DEX file size does not match its header")
    require(u32(36) == 112 and u32(40) == 0x12345678, "Unsupported DEX header layout")

    def table(count_offset: int, entry_size: int) -> tuple[int, int]:
        count, offset = u32(count_offset), u32(count_offset + 4)
        require(offset <= len(data) and count <= (len(data) - offset) // entry_size,
                "DEX table is out of bounds")
        return count, offset

    string_count, strings_offset = table(56, 4)
    type_count, types_offset = table(64, 4)
    class_count, classes_offset = table(96, 32)

    def descriptor(string_index: int) -> str:
        require(string_index < string_count, "DEX descriptor string index is out of bounds")
        offset = u32(strings_offset + string_index * 4)
        require(offset < len(data), "DEX string is out of bounds")
        for _ in range(5):
            require(offset < len(data), "DEX string length is truncated")
            item = data[offset]
            offset += 1
            if item < 0x80:
                break
        else:
            raise ValidationError("DEX string length is malformed")
        end = data.find(b"\0", offset)
        require(end != -1, "DEX descriptor has no terminator")
        try:
            value = data[offset:end].decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValidationError("DEX class descriptor is not UTF-8") from error
        require(value.startswith("L") and value.endswith(";") and len(value) > 2,
                "DEX class definition has an invalid descriptor")
        return value

    definitions: set[str] = set()
    for index in range(class_count):
        type_index = u32(classes_offset + index * 32)
        require(type_index < type_count, "DEX class type index is out of bounds")
        value = descriptor(u32(types_offset + type_index * 4))
        require(value not in definitions, "DEX repeats a class definition")
        definitions.add(value)
    return definitions


def jar_members(path: Path) -> dict[str, bytes]:
    with zipfile.ZipFile(path) as archive:
        names = [item.filename for item in archive.infolist() if not item.is_dir()]
        require(len(names) == len(set(names)), f"Duplicate ZIP members in {path.name}")
        return {name: archive.read(name) for name in names}


def jar_classes(members: dict[str, bytes]) -> set[str]:
    result: set[str] = set()
    dex_members = [name for name in members
                   if name.startswith("classes") and name.endswith(".dex") and "/" not in name]
    require(bool(dex_members), "Runtime JAR has no DEX members")
    for name in sorted(dex_members):
        classes = dex_classes(members[name])
        require(not result.intersection(classes), "JAR repeats definitions across DEX members")
        result.update(classes)
    return result


def validate(contract: dict, original_input: Path, original_runtime: Path,
             adapter: Path, services: Path, classpath: list[str]) -> dict:
    require(sha256(original_input.read_bytes()) == contract["factory_jar_sha256"],
            "Factory input JAR differs from the selected original")
    input_members = jar_members(original_input)
    runtime_members = jar_members(original_runtime)
    require(input_members.keys() == runtime_members.keys(),
            "Runtime original JAR has added or removed members")
    for name, value in input_members.items():
        require(value == runtime_members[name],
                f"Runtime original JAR changed member {name}")
    original_classes = jar_classes(runtime_members)
    require(set(contract["factory_required_classes"]) <= original_classes,
            "Original JAR is missing required Binder/verifier classes")

    adapter_members = jar_members(adapter)
    adapter_classes = jar_classes(adapter_members)
    require(set(contract["adapter_required_classes"]) <= adapter_classes,
            "Adapter JAR is missing required authored classes")
    require(not original_classes.intersection(adapter_classes),
            "Adapter JAR duplicates a factory runtime class")
    require(all(not value.startswith("Lcom/miui/cameraopt/") for value in adapter_classes),
            "Compile-only CameraOpt declarations leaked into the adapter JAR")
    require(all(value.startswith("Lcom/android/server/cameraopt/") for value in adapter_classes),
            "Adapter JAR contains an unexpected runtime class")

    services_classes = jar_classes(jar_members(services))
    require(contract["process_helper_class"] in services_classes,
            "services.jar does not contain the selected process-policy helper")
    for helper in contract.get("reclaim_helper_classes", []):
        require(helper in services_classes,
                f"services.jar does not contain the selected reclaim helper {helper}")
    platform_duplicates = original_classes.intersection(services_classes)
    require(platform_duplicates <= set(contract.get("allowed_platform_duplicates", [])),
            "services.jar introduces an unreviewed duplicate of a factory class")

    require(isinstance(classpath, list) and all(isinstance(item, str) for item in classpath),
            "System-server classpath must be a list of actual installed JAR paths")
    ordered = contract["runtime_classpath_order"]
    for entry in ordered:
        require(classpath.count(entry) == 1,
                f"Expected exactly one system-server classpath entry: {entry}")
    indices = [classpath.index(entry) for entry in ordered]
    require(indices == sorted(indices), "System-server JAR dependency order is wrong")
    require(not any("compile-stubs" in entry for entry in classpath),
            "Compile-only declarations appear in the runtime classpath")
    return {
        "status": "artifact_ownership_verified",
        "factory_input_sha256": sha256(original_input.read_bytes()),
        "original_runtime_sha256": sha256(original_runtime.read_bytes()),
        "adapter_sha256": sha256(adapter.read_bytes()),
        "services_sha256": sha256(services.read_bytes()),
        "original_class_count": len(original_classes),
        "adapter_class_count": len(adapter_classes),
        "baseline_platform_duplicates": sorted(platform_duplicates),
        "classpath_order": ordered,
        "limitations": ["No service startup, native initialization, or camera capture was tested"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--original-input", type=Path, required=True)
    parser.add_argument("--original-runtime", type=Path, required=True)
    parser.add_argument("--adapter", type=Path, required=True)
    parser.add_argument("--services", type=Path, required=True)
    parser.add_argument("--classpath-json", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(json.loads(args.contract.read_text()), args.original_input,
                          args.original_runtime, args.adapter, args.services,
                          json.loads(args.classpath_json.read_text()))
    except (ValidationError, OSError, zipfile.BadZipFile, json.JSONDecodeError) as error:
        parser.exit(1, f"CameraOpt artifact validation failed: {error}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
