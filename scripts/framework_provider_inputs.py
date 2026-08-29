#!/usr/bin/env python3
"""Stage exact Nezha framework HAL inputs with native Android checks intact.

This copies selected, previously captured stock files into a new private bundle.
It never executes firmware, applies source patches, installs policy, builds an
image, or accesses a phone. Native ELF checks and runtime validation are separate.
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
import struct
import sys
import tempfile
import xml.etree.ElementTree as ET

if __package__:
    from .apex_inputs import elf_dynamic
    from .artifact_files import publish_new_directory
    from .vendor_policy import Reader, real_directory
else:
    from apex_inputs import elf_dynamic
    from artifact_files import publish_new_directory
    from vendor_policy import Reader, real_directory


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "config/nezha-framework-providers.json"
BUNDLE = "vendor/xiaomi/nezha-framework-providers"
MODULE_PACKAGE = "device/xiaomi/nezha/framework-providers"
MODULE_BLUEPRINT = "framework-providers.Android.bp"
RECEIPT = "framework-provider-inputs.json"
CHECK = "nezha_framework_provider_inputs_check"
TOOL = "nezha_framework_provider_inputs_verifier"
NATIVE_OUTPUT_RECIPE = {
    "producer": CHECK,
    "receipt_output": "framework-provider-inputs-checked.json",
    "payload_output_prefix": "verified",
    "consumer_inputs": "verified_producer_outputs",
    "all_inputs_checked_before_outputs": True,
}
MAX_BUNDLE_BYTES = 64 * 1024 * 1024
SAFE_NAME = re.compile(r"[A-Za-z0-9_+.@-]+")
SCOPE = {
    "firmware_executed": False,
    "platform_libraries_replaced": False,
    "source_patches_applied": False,
    "elf_checks_disabled": False,
    "undefined_symbols_allowed": False,
    "native_build_verified": False,
    "runtime_policy_admitted": False,
    "linker_namespace_runtime_verified": False,
    "services_started": False,
    "hardware_tested": False,
    "complete_rom_admitted": False,
    "phone_accessed": False,
}


class FrameworkProviderError(ValueError):
    """An input does not satisfy the reviewed provider contract."""


def require(condition, message):
    if not condition:
        raise FrameworkProviderError(message)


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _unique(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON object key")
        result[key] = value
    return result


def _json(raw):
    value = json.loads(raw, object_pairs_hook=_unique)
    require(type(value) is dict, "expected a JSON object")
    return value


def _relative(value):
    require(type(value) is str and 0 < len(value) <= 1024, "invalid relative path")
    path = PurePosixPath(value)
    require(not path.is_absolute() and path.as_posix() == value
            and all(part not in {".", ".."} and SAFE_NAME.fullmatch(part)
                    for part in value.split("/")), "unsafe relative path")
    return value


def _name(value):
    require(type(value) is str and SAFE_NAME.fullmatch(value), "invalid native module name")
    return value


def _module(value):
    require(type(value) is str, "invalid dependency module")
    if value.startswith("//"):
        namespace, separator, name = value[2:].partition(":")
        require(separator, "qualified module must include a name")
        _relative(namespace)
        _name(name)
    else:
        _name(value)
    return value


def _expected(value):
    require(type(value) is dict and type(value.get("sha256")) is str
            and re.fullmatch(r"[a-f0-9]{64}", value["sha256"])
            and type(value.get("size_bytes")) is int
            and 0 < value["size_bytes"] <= 16 * 1024 * 1024,
            "invalid bounded file identity")
    return {key: value[key] for key in ("sha256", "size_bytes")}


def _read_bound(reader, path, expected):
    return reader.read(path, **{"expected_sha": _expected(expected)["sha256"],
                                "expected_size": expected["size_bytes"]})


def load_contract(reader=None, contract_path=None):
    reader = reader or Reader()
    raw = reader.read(ROOT / CONTRACT)
    if contract_path is not None:
        require(reader.read(contract_path) == raw, "alternate provider contract is not reviewed")
    contract = _json(raw)
    require(set(contract) == {"schema_version", "device", "platform", "bundle", "module_package", "factory_package_sha256",
                              "factory_image", "source_lock", "captures", "files", "providers",
                              "source_dependencies", "source_replacements", "required_source_patches",
                              "runtime_requirements", "native_output_recipe", "scope"}, "unexpected provider contract fields")
    require(type(contract["schema_version"]) is int and contract["schema_version"] == 1
            and contract["device"] == "nezha" and contract["bundle"] == BUNDLE
            and contract["module_package"] == MODULE_PACKAGE
            and contract["platform"] == {"branch": "bka", "release": "bp4a", "board_api": "202504"},
            "provider inputs must retain the selected Nezha platform")
    require(contract["scope"] == SCOPE, "staging cannot claim a build, policy or hardware result")
    require(contract["native_output_recipe"] == NATIVE_OUTPUT_RECIPE
            and type(contract["native_output_recipe"]["all_inputs_checked_before_outputs"]) is bool,
            "native consumers must use the strict verified output producer")
    require(type(contract["factory_package_sha256"]) is str
            and re.fullmatch(r"[a-f0-9]{64}", contract["factory_package_sha256"]), "invalid factory package")
    image = contract["factory_image"]
    require(set(image) == {"partition", "sha256", "size_bytes"} and image["partition"] == "system_ext"
            and type(image["size_bytes"]) is int and image["size_bytes"] > 0
            and re.fullmatch(r"[a-f0-9]{64}", image["sha256"]), "unexpected source image")
    lock = contract["source_lock"]
    require(set(lock) == {"path", "sha256", "size_bytes"}, "source lock binding is required")
    _read_bound(reader, ROOT / _relative(lock["path"]), lock)
    captures = contract["captures"]
    require(type(captures) is dict and 1 <= len(captures) <= 32, "invalid capture selection")
    for name, capture in captures.items():
        _name(name)
        require(set(capture) == {"path", "sha256", "size_bytes"}, "invalid capture reference")
        _relative(capture["path"])
        _expected(capture)
    files = contract["files"]
    require(type(files) is list and 6 <= len(files) <= 128, "invalid provider file selection")
    paths, runtime_paths, modules = set(), set(), set()
    library_names = {}
    for row in files:
        require(type(row) is dict, "invalid provider file")
        kind = row.get("kind")
        common = {"kind", "runtime_path", "capture", "capture_path", "sha256", "size_bytes", "mode"}
        expected_keys = common | ({"module", "needed", "soname"} if kind in {"binary", "shared_library"}
                                  else {"module"} if kind == "etc" else set())
        require(kind in {"binary", "shared_library", "init_rc", "vintf_fragment", "etc"}
                and set(row) == expected_keys, "unexpected provider input kind or fields")
        require(type(row["runtime_path"]) is str and row["runtime_path"].startswith("/system_ext/"),
                "provider files must remain in system_ext")
        runtime = _relative(row["runtime_path"][1:])
        require(runtime not in runtime_paths and runtime.casefold() not in paths, "duplicate provider destination")
        runtime_paths.add(runtime)
        paths.add(runtime.casefold())
        _expected(row)
        require(row["capture"] in captures, "unknown source capture")
        _relative(row["capture_path"])
        require(row["mode"] == ("0755" if kind == "binary" else "0644"), "unexpected factory file mode")
        prefix = {"binary": "system_ext/bin/", "shared_library": "system_ext/lib64/",
                  "init_rc": "system_ext/etc/init/", "vintf_fragment": "system_ext/etc/vintf/manifest/",
                  "etc": "system_ext/etc/"}[kind]
        require(runtime.startswith(prefix) and "/" not in runtime[len(prefix):],
                "provider runtime path differs from its native installation kind")
        if "module" in row:
            _name(row["module"])
            require(row["module"].startswith("nezha_framework_") and row["module"] not in modules,
                    "provider module names must be unique and scoped")
            modules.add(row["module"])
        if kind in {"binary", "shared_library"}:
            needed = row["needed"]
            require(type(needed) is list and needed and len(needed) == len(set(needed)),
                    "ELF dependency list must be explicit and unique")
            for library in needed:
                require(_name(library).endswith(".so"), "ELF dependency must be a shared library")
            expected_soname = PurePosixPath(runtime).name if kind == "shared_library" else None
            require(row["soname"] == expected_soname, "library SONAME or executable identity differs")
            if kind == "shared_library":
                require(expected_soname not in library_names, "duplicate private SONAME")
                library_names[expected_soname] = row["module"]
    dependencies = contract["source_dependencies"]
    require(type(dependencies) is dict and dependencies, "pinned source dependencies are required")
    for soname, module in dependencies.items():
        require(_name(soname).endswith(".so") and soname not in library_names,
                "a source library cannot also be replaced with a private prebuilt")
        _module(module)
    all_needed = {name for row in files for name in row.get("needed", [])}
    require(all_needed <= set(library_names) | set(dependencies), "unresolved explicit DT_NEEDED dependency")
    require(set(dependencies) <= all_needed, "unused source dependency in contract")
    providers = contract["providers"]
    require(type(providers) is list and len(providers) == 2, "the two reviewed providers are required")
    by_runtime = {row["runtime_path"]: row for row in files}
    attached = set()
    for provider in providers:
        require(set(provider) == {"binary", "init_rc", "vintf_fragment", "hal", "interface", "instance",
                                  "init_service", "service_context", "domain", "exec_type"},
                "unexpected provider registration fields")
        for key, kind in (("binary", "binary"), ("init_rc", "init_rc"), ("vintf_fragment", "vintf_fragment")):
            require(provider[key] in by_runtime and by_runtime[provider[key]]["kind"] == kind
                    and provider[key] not in attached, "provider registration must bind one actual input of each kind")
            attached.add(provider[key])
        for key in ("hal", "interface", "instance", "init_service", "service_context", "domain", "exec_type"):
            _name(provider[key])
    require(attached == {row["runtime_path"] for row in files
                         if row["kind"] in {"binary", "init_rc", "vintf_fragment"}},
            "unattached provider executable, init rule or manifest")
    for replacement in contract["source_replacements"]:
        require(type(replacement) is dict and set(replacement) == {"soname", "module", "reason"}
                and dependencies.get(replacement["soname"]) == replacement["module"]
                and type(replacement["reason"]) is str and replacement["reason"],
                "invalid source replacement")
    for patch in contract["required_source_patches"]:
        require(type(patch) is dict and set(patch) == {"path", "sha256", "size_bytes"}, "invalid source patch")
        _read_bound(reader, ROOT / _relative(patch["path"]), patch)
    require(type(contract["runtime_requirements"]) is list
            and all(type(item) is str and item for item in contract["runtime_requirements"]),
            "runtime limitations must remain explicit")
    require(sum(row["size_bytes"] for row in files) <= MAX_BUNDLE_BYTES, "provider bundle exceeds byte bound")
    return contract, raw


def _validate_xml(raw, kind):
    require(b"<!DOCTYPE" not in raw.upper() and b"<!ENTITY" not in raw.upper(), "XML cannot declare DTD/entities")
    root = ET.fromstring(raw)
    if kind == "vintf_fragment":
        require(root.tag == "manifest" and root.attrib == {"version": "9.0", "type": "framework"},
                "provider must retain its original framework manifest")
    return root


def validate_inputs(contract, payload):
    """Inspect actual ELF and XML data; no firmware process is started."""
    by_runtime = {row["runtime_path"]: row for row in contract["files"]}
    for runtime, row in by_runtime.items():
        raw = payload[runtime]
        require(identity(raw) == _expected(row), "provider source file hash or size mismatch")
        if row["kind"] in {"binary", "shared_library"}:
            require(len(raw) >= 64 and raw[:7] == b"\x7fELF\x02\x01\x01"
                    and struct.unpack_from("<H", raw, 16)[0] == 3,
                    "provider must be an AArch64 ELF64 shared object or PIE")
            elf = elf_dynamic(raw)
            require(elf is not None and elf["class_bits"] == 64 and elf["machine"] == 183
                    and elf["endianness"] == "little" and elf["needed"] == row["needed"]
                    and elf["soname"] == row["soname"] and not elf["search_paths"],
                    "ELF machine, SONAME, DT_NEEDED order or search paths differ from review")
            phoff = struct.unpack_from("<Q", raw, 32)[0]
            phsize, phcount = struct.unpack_from("<HH", raw, 54)
            interpreters = []
            for index in range(phcount):
                kind, _, offset, _, _, size, _, _ = struct.unpack_from("<IIQQQQQQ", raw, phoff + phsize * index)
                if kind == 3:
                    interpreters.append(raw[offset:offset + size])
            require(interpreters == ([b"/system/bin/linker64\0"] if row["kind"] == "binary" else []),
                    "ELF interpreter does not match its executable or library role")
        elif row["kind"] in {"vintf_fragment", "etc"}:
            _validate_xml(raw, row["kind"])
        else:
            require(b"\0" not in raw, "init RC cannot contain NUL")
            raw.decode("utf-8", "strict")
    for provider in contract["providers"]:
        rc = payload[provider["init_rc"]].decode("utf-8")
        declarations = [line.split() for line in rc.splitlines()
                        if line and not line[0].isspace() and line.split()[0] == "service"]
        require(declarations == [["service", provider["init_service"], provider["binary"]]],
                "init declaration must point only to the selected provider executable")
        root = _validate_xml(payload[provider["vintf_fragment"]], "vintf_fragment")
        require(len(root) == 1, "manifest must declare exactly the reviewed HAL")
        hal = root[0]
        require(hal.tag == "hal" and hal.attrib == {"format": "aidl"}
                and [item.tag for item in hal] == ["name", "fqname"]
                and hal.findtext("name") == provider["hal"]
                and hal.findtext("fqname") == provider["interface"] + "/" + provider["instance"],
                "VINTF declaration differs from its actual reviewed provider")


def _native_outputs(contract):
    return {"verified" + row["runtime_path"]: "proprietary" + row["runtime_path"]
            for row in contract["files"]}


def _native_checker(identities, payloads):
    """A small standalone native build tool; exact data is generated from the contract."""
    return ('''#!/usr/bin/env python3
"""Produce only verified provider files for native Android consumers."""
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import shutil
import stat
import sys
import tempfile

EXPECTED = ''' + repr(identities) + '''
PAYLOADS = ''' + repr(payloads) + '''
RECEIPT = "framework-provider-inputs-checked.json"

def signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)

def verify_inputs(arguments):
    if len(arguments) != len(EXPECTED):
        raise ValueError("unexpected native provider input count")
    seen, contents, states = set(), {}, []
    for argument in arguments:
        path = Path(argument)
        names = [name for name in EXPECTED if argument == name or argument.endswith("/" + name)]
        if len(names) != 1 or names[0] in seen:
            raise ValueError("unrecognized or duplicate native provider input")
        name = names[0]
        seen.add(name)
        before = path.lstat()
        if not stat.S_ISREG(before.st_mode) or before.st_size != EXPECTED[name]["size_bytes"]:
            raise ValueError("native provider input is not the expected regular file")
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
            opened = os.fstat(stream.fileno())
            if signature(opened) != signature(before):
                raise ValueError("native provider input replaced before opening")
            raw = stream.read(before.st_size + 1)
            after = path.lstat()
            if signature(os.fstat(stream.fileno())) != signature(opened) or signature(after) != signature(before):
                raise ValueError("native provider input changed during verification")
        if len(raw) != before.st_size or hashlib.sha256(raw).hexdigest() != EXPECTED[name]["sha256"]:
            raise ValueError("native provider input failed SHA256 verification")
        contents[name] = raw
        states.append((path, signature(before)))
    return contents, states

def unchanged(states):
    for path, original in states:
        if signature(path.lstat()) != original:
            raise ValueError("native provider input changed before output publication")

def checked_directory(path):
    for parent in [*reversed(path.parents), path]:
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise ValueError("native output directory or ancestor is not a real directory")

def output_root(value):
    root = Path(os.path.abspath(value))
    checked_directory(root.parent)
    if not os.path.lexists(root):
        root.mkdir(mode=0o700)
    checked_directory(root)
    allowed = {str(parent) for name in PAYLOADS for parent in PurePosixPath(name).parents
               if str(parent) != "."}
    # sbox creates the declared output parent directories before invoking us.
    # Accept only those empty directory trees; never replace existing files.
    for path in root.rglob("*"):
        if not stat.S_ISDIR(path.lstat().st_mode) or str(path.relative_to(root)) not in allowed:
            raise ValueError("native output directory contains existing or unexpected entries")
    return root

def write_checked(root, name, raw):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes() != raw:
        raise ValueError("native provider output failed exact-byte readback")

def main(arguments):
    if len(arguments) < 2 or arguments[0] != "--output-dir":
        raise ValueError("an explicit native output directory is required")
    # Hold the actual verified bytes. Do not reopen the source files for copies.
    # Every control and payload input must pass before any payload is written.
    contents, states = verify_inputs(arguments[2:])
    unchanged(states)
    root = output_root(arguments[1])
    receipt = {"verified": True, "input_count": len(contents), "payload_count": len(PAYLOADS),
               "firmware_executed": False,
               "contract": EXPECTED["provenance/nezha-framework-providers.json"],
               "outputs": [{"path": name, **EXPECTED[source]} for name, source in PAYLOADS.items()]}
    receipt_bytes = (json.dumps(receipt, sort_keys=True, indent=2) + "\\n").encode()
    staging = Path(tempfile.mkdtemp(prefix=".provider-verified-", dir=root))
    published = []
    try:
        for name, source in PAYLOADS.items():
            write_checked(staging, name, contents[source])
        write_checked(staging, RECEIPT, receipt_bytes)
        unchanged(states)
        # Hard-link newly created staging files, never original inputs. This
        # publishes each complete file exclusively without replacing a path.
        # sbox may expose outputs from a failed command, so publish the success
        # receipt last and remove our published files if any operation fails.
        for name in [*PAYLOADS, RECEIPT]:
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            checked_directory(target.parent)
            info = (staging / name).lstat()
            published.append((target, info.st_dev, info.st_ino))
            os.link(staging / name, target, follow_symlinks=False)
        unchanged(states)
        shutil.rmtree(staging)
        staging = None
    except BaseException:
        for path, device, inode in reversed(published):
            try:
                info = path.lstat()
                if (info.st_dev, info.st_ino) == (device, inode):
                    path.unlink()
            except FileNotFoundError:
                pass
        raise
    finally:
        if staging is not None:
            shutil.rmtree(staging)
    print(json.dumps({"verified": True, "input_count": len(contents),
                      "payload_count": len(PAYLOADS), "firmware_executed": False}, sort_keys=True))

if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except (OSError, ValueError) as error:
        print("provider input verification failed: " + str(error), file=sys.stderr)
        raise SystemExit(2)
''').encode()


def _input_groups(contract):
    return {row["runtime_path"]: "nezha_framework_provider_input_" + str(index).zfill(3)
            for index, row in enumerate(contract["files"])}


def _bp(contract, native_files):
    """The private package exposes byte inputs only to the reviewed device package."""
    output = ['// Generated by framework_provider_inputs.py; original firmware bytes remain private.',
              'soong_namespace {}', '',
              'python_binary_host {', '    name: "' + TOOL + '",',
              '    visibility: [":__pkg__"],',
              '    main: "tools/verify_framework_provider_inputs.py",',
              '    srcs: ["tools/verify_framework_provider_inputs.py"],', '}', '',
              'genrule {', '    name: "' + CHECK + '",',
              '    visibility: [":__pkg__", "//' + MODULE_PACKAGE + ':__pkg__",',
              '                 "//vendor/xiaomi/nezha-policy:__pkg__"],',
              '    tools: ["' + TOOL + '"],', '    srcs: [']
    output += ['        ' + json.dumps(name) + ',' for name in sorted(native_files)]
    output += ['    ],', '    out: ["framework-provider-inputs-checked.json",']
    output += ['        ' + json.dumps(name) + ',' for name in _native_outputs(contract)]
    output += ['    ],', '    cmd: "$(location ' + TOOL + ') --output-dir $(genDir) $(in)",', '}', '']
    for runtime, name in _input_groups(contract).items():
        output += ['filegroup {', '    name: ' + json.dumps(name) + ',',
                   '    srcs: [' + json.dumps(":" + CHECK + "{verified" + runtime + "}") + '],',
                   '    visibility: ["//' + MODULE_PACKAGE + ':__pkg__"],', '}', '']
    return ("\n".join(output) + "\n").encode()


def _module_bp(contract):
    """Keep source-library consumers outside vendor's broad-visibility restriction."""
    libraries = {row["soname"]: row["module"] for row in contract["files"] if row["kind"] == "shared_library"}
    dependencies = {**contract["source_dependencies"], **libraries}
    providers = {row["binary"]: row for row in contract["providers"]}
    groups = _input_groups(contract)
    output = ['// Generated by framework_provider_inputs.py; install only with explicit bundle admission.',
              '// Proprietary bytes stay in the separate vendor bundle.',
              'soong_namespace { imports: ["' + BUNDLE + '"] }', '']
    for row in contract["files"]:
        if "module" not in row:
            continue
        kind = row["kind"]
        path = ":" + groups[row["runtime_path"]]
        module_type = {"binary": "cc_prebuilt_binary", "shared_library": "cc_prebuilt_library_shared",
                       "etc": "prebuilt_etc"}[kind]
        output += [module_type + ' {', '    name: ' + json.dumps(row["module"]) + ',',
                   '    system_ext_specific: true,', '    required: ["' + CHECK + '"],']
        if kind == "etc":
            output += ['    src: ' + json.dumps(path) + ',',
                       '    filename: ' + json.dumps(PurePosixPath(row["runtime_path"]).name) + ',']
        else:
            stem = PurePosixPath(row["runtime_path"]).name
            if kind == "shared_library":
                stem = stem.removesuffix(".so")
            output += ['    stem: ' + json.dumps(stem) + ',', '    compile_multilib: "64",',
                       '    arch: { arm64: { srcs: [' + json.dumps(path) + '] } },',
                       '    check_elf_files: true,', '    allow_undefined_symbols: false,',
                       '    strip: { none: true },', '    stl: "none",', '    system_shared_libs: [],',
                       '    shared_libs: [']
            output += ['        ' + json.dumps(dependencies[name]) + ',' for name in row["needed"]]
            output += ['    ],']
            if kind == "binary":
                provider = providers[row["runtime_path"]]
                output += ['    init_rc: [' + json.dumps(":" + groups[provider["init_rc"]]) + '],',
                           '    vintf_fragments: [' + json.dumps(":" + groups[provider["vintf_fragment"]]) + '],']
        output += ['}', '']
    return ("\n".join(output) + "\n").encode()


def _generated(contract, raw, capture_bytes):
    result = {"provenance/nezha-framework-providers.json": raw}
    result.update({"provenance/captures/" + name + ".json": value for name, value in capture_bytes.items()})
    result[MODULE_BLUEPRINT] = _module_bp(contract)
    native_files = {"proprietary" + row["runtime_path"]: _expected(row) for row in contract["files"]}
    native_files.update({name: identity(data) for name, data in result.items()})
    result["tools/verify_framework_provider_inputs.py"] = _native_checker(dict(sorted(native_files.items())),
                                                                        _native_outputs(contract))
    result["Android.bp"] = _bp(contract, native_files)
    packages = [row["module"] for row in contract["files"] if "module" in row]
    product = ["# Explicitly admitted private Nezha provider bundle.",
               "# Native ELF checks and runtime SELinux integration remain required.",
               "PRODUCT_SOONG_NAMESPACES += " + BUNDLE + " " + MODULE_PACKAGE]
    product.extend("PRODUCT_PACKAGES += " + name for name in packages + [CHECK])
    result["framework-providers.mk"] = ("\n".join(product) + "\n").encode()
    return result


def _capture_bytes(reader, contract, root):
    captures = {}
    entries = {}
    for name, reference in contract["captures"].items():
        raw = _read_bound(reader, root / reference["path"], reference)
        receipt = _json(raw)
        image = contract["factory_image"]
        require(receipt.get("schema_version") == 1 and receipt.get("operation") == "erofs-capture"
                and receipt.get("image", {}).get("sha256") == image["sha256"]
                and receipt.get("image", {}).get("size_bytes") == image["size_bytes"]
                and receipt.get("firmware_executed") is False and receipt.get("image_mounted") is False
                and receipt.get("symlinks_followed") is False, "capture provenance differs from original factory image")
        rows = receipt.get("files")
        require(type(rows) is list and rows, "capture has no files")
        selected = {}
        for row in rows:
            require(type(row) is dict and row.get("type") == "regular" and row.get("readback_verified") is True,
                    "capture includes an unverified or nonregular file")
            path = _relative(row["output_path"])
            require(path not in selected, "capture includes duplicate files")
            selected[path] = row
        captures[name], entries[name] = raw, selected
    return captures, entries


def _write(root, name, raw):
    target = root / _relative(name)
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with target.open("xb") as stream:
        os.chmod(target, 0o600)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def _manifest(contract, raw, files):
    return {"schema_version": 1, "device": "nezha", "bundle": BUNDLE,
            "module_package": MODULE_PACKAGE,
            "module_blueprint": {"path": MODULE_BLUEPRINT, **identity(files[MODULE_BLUEPRINT])},
            "operation": "stage-framework-provider-inputs", "contract": identity(raw),
            "factory_package_sha256": contract["factory_package_sha256"],
            "factory_image": contract["factory_image"], "source_lock": contract["source_lock"],
            "files": [{"path": name, **identity(data)} for name, data in sorted(files.items())],
            "native_check_target": CHECK,
            "native_output_recipe": contract["native_output_recipe"],
            "packages": [row["module"] for row in contract["files"] if "module" in row],
            "providers": contract["providers"], "scope": SCOPE, "readback_verified": True}


def stage_inputs(capture_root, output, *, contract_path=None):
    reader = Reader()
    contract, raw = load_contract(reader, contract_path)
    captures, entries = _capture_bytes(reader, contract, real_directory(capture_root))
    files = _generated(contract, raw, captures)
    payload = {}
    for row in contract["files"]:
        entry = entries[row["capture"]].get(row["capture_path"], {})
        require(entry.get("path") == row["runtime_path"].removeprefix("/system_ext")
                and entry.get("mode") == row["mode"]
                and all(entry.get(key) == value for key, value in _expected(row).items()),
                "provider selection disagrees with its sealed capture")
        receipt_path = Path(capture_root) / contract["captures"][row["capture"]]["path"]
        data = _read_bound(reader, receipt_path.parent / row["capture_path"], row)
        payload[row["runtime_path"]] = data
        files["proprietary" + row["runtime_path"]] = data
    validate_inputs(contract, payload)
    destination = Path(os.path.abspath(output))
    require(any(private in destination.parents for private in (ROOT / "artifacts", ROOT / "evidence")),
            "provider staging must stay in ignored artifacts/ or evidence/")
    require(not os.path.lexists(destination), "provider bundle destination already exists")
    parent = real_directory(destination.parent)
    staging = Path(tempfile.mkdtemp(prefix="." + destination.name + "-", dir=parent))
    try:
        manifest = _manifest(contract, raw, files)
        for name, data in {**files, RECEIPT: encoded(manifest)}.items():
            _write(staging, name, data)
        verify_bundle(staging, contract_path=contract_path)
        reader.recheck()
        publish_new_directory(staging, destination)
        staging = None
        return manifest
    finally:
        if staging is not None:
            shutil.rmtree(staging)


def verify_bundle(bundle, *, contract_path=None):
    reader = Reader()
    contract, raw = load_contract(reader, contract_path)
    root = real_directory(bundle)
    manifest_raw = reader.read(root / RECEIPT)
    manifest = _json(manifest_raw)
    captures = {name: _read_bound(reader, root / ("provenance/captures/" + name + ".json"), reference)
                for name, reference in contract["captures"].items()}
    files = _generated(contract, raw, captures)
    payload = {}
    for row in contract["files"]:
        name = "proprietary" + row["runtime_path"]
        data = _read_bound(reader, root / name, row)
        payload[row["runtime_path"]] = data
        files[name] = data
    validate_inputs(contract, payload)
    require(manifest == _manifest(contract, raw, files), "provider receipt differs from its reviewed exact inputs")
    seen, directories = set(), set()
    for name, expected in files.items():
        require(reader.read(root / name) == expected, "generated provider definitions differ from trusted renderer")
        path = PurePosixPath(name)
        directories.update(str(parent) for parent in path.parents if str(parent) != ".")
    for path in root.rglob("*"):
        mode = path.lstat().st_mode
        relative = str(path.relative_to(root))
        if stat.S_ISDIR(mode):
            require(relative in directories, "unexpected directory in provider bundle")
        else:
            require(stat.S_ISREG(mode), "provider bundle contains a symlink or special file")
            seen.add(relative)
    require(seen == set(files) | {RECEIPT}, "provider bundle includes missing or extra files")
    reader.recheck()
    return {**manifest, "status": "verified", "receipt": {"path": RECEIPT, **identity(manifest_raw)}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage")
    stage.add_argument("--capture-root", type=Path, required=True)
    stage.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--bundle", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            result = stage_inputs(args.capture_root, args.output, contract_path=args.contract)
        else:
            result = verify_bundle(args.bundle, contract_path=args.contract)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, ET.ParseError) as error:
        print("framework provider input admission failed: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
