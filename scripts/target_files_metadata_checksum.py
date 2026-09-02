#!/usr/bin/env python3
"""Explicit checksum-recipe source successor for unchanged policy3 metadata.

The six previous consumers, image admission and policy evidence stay frozen.
Only the separately pinned 0023 Makefile transition changes the current source
composition. Staging copies metadata and evidence, never an image.
"""

import ast
import copy
import hashlib
import os
from pathlib import Path
import stat
import types

ADAPTER = "scripts/target_files_metadata_checksum.py"
PREDECESSOR = "scripts/target_files_metadata_delivery_policy3.py"
PREDECESSOR_ID = {"sha256": "78011adb294b16c1efc8af425fbcda0a0065293af84ea174507c98dd96ad5de5", "size_bytes": 27759}
PREDECESSOR_RUNTIME_ID = {"sha256": "7920d0e838a2cb7a61c65cb008a40a587cd8431838e4529218647cdb6665e566", "size_bytes": 193228}
SOURCE_CONTRACT = "patches/evolution/target-files-metadata-checksum.json"
SOURCE_CONTRACT_ID = "nezha-target-files-metadata-checksum-v1"
SOURCE_CONTRACT_IDENTITY = {"sha256": "ee28f64d09c75d724c0be5dc07d98816cf30c4f59cf09a45c6163f6c96428e01", "size_bytes": 1455}
BASE_SOURCE_CONTRACT = "patches/evolution/target-files-source-composition.json"
BASE_SOURCE_CONTRACT_ID = {"sha256": "b9c6c485ad7a1617bc29a315ba8ff89034ff28cbe4e8a9196eff726ee1811f2a", "size_bytes": 19228}
BASE_COMPOSITION_ID = {"sha256": "152f6413cdeaa7221d4602da1f29fcaf472dd0b2cc4a71c320f8e9505fe0b427", "size_bytes": 10955}
PATCH = {"path": "patches/evolution/0023-portable-target-files-metadata-checksum.patch",
         "sha256": "b09a642a578e44767a816896e604481ee4e6e79988bfd07f6ff4bc81a4daf66f", "size_bytes": 1143}
CORE = "build/make/core/Makefile"
CORE_BEFORE = {"sha256": "bf6e0668ff571f3858fc09d5cefa039ff6a8fdebf5b9ecfdc690794f25889ba7", "size_bytes": 392084}
CORE_AFTER = {"sha256": "8fffff47144a95bd8a56bc3797b2984b61964da0777d19964faa24541eebbb3d", "size_bytes": 392273}
MAIN = b'\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


def _identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _bootstrap(path, wanted=None):
    path = Path(os.path.abspath(path))
    if any(not stat.S_ISDIR(parent.lstat().st_mode) for parent in path.parents):
        raise ValueError("checksum bootstrap requires real parent directories")
    def signature(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2 << 20:
        raise ValueError("checksum bootstrap requires bounded single-link regular code")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        if signature(before) != signature(os.fstat(stream.fileno())):
            raise ValueError("checksum bootstrap source replaced")
        raw = stream.read((2 << 20) + 1)
        if (len(raw) > 2 << 20 or signature(before) != signature(os.fstat(stream.fileno()))
                or signature(before) != signature(path.lstat())):
            raise ValueError("checksum bootstrap source changed")
    if wanted is not None and _identity(raw) != wanted:
        raise ValueError("checksum frozen predecessor identity differs")
    return raw


def _body(raw, wanted):
    if (type(raw) is not bytes or _identity(raw) != wanted
            or not raw.endswith(MAIN) or raw.count(MAIN) != 1):
        raise ValueError("checksum predecessor or terminal main differs")
    return raw[:-len(MAIN)]


NATIVE = "_CHECKSUM_PREDECESSOR_PAYLOAD" in globals()
ROOT = Path(os.path.abspath(__file__)).parent.parent
_old = types.ModuleType("_frozen_checksum_policy3_predecessor")
_old.__file__ = str(ROOT / PREDECESSOR)
if NATIVE:
    _runtime_old = _CHECKSUM_PREDECESSOR_PAYLOAD
    _self_identity = _CHECKSUM_ADAPTER_IDENTITY
    exec(compile(_body(_runtime_old, PREDECESSOR_RUNTIME_ID), "<bound-policy3-runtime>", "exec"), _old.__dict__)
else:
    _self_identity = _identity(_bootstrap(__file__))
    exec(compile(_body(_bootstrap(ROOT / PREDECESSOR, PREDECESSOR_ID), PREDECESSOR_ID),
                 "<bound-policy3-source>", "exec"), _old.__dict__)
    _runtime_old = _old.runtime_tool_payloads(
        {name: _bootstrap(ROOT / name) for name in _old.CONTROL_TOOLS})["tools/target_files_metadata.py"]
    _body(_runtime_old, PREDECESSOR_RUNTIME_ID)

Reader, encoded, identity = _old.Reader, _old.encoded, _old.identity
require, expected, relative, same = _old.require, _old.expected, _old.relative, _old.same
TargetFilesMetadataError = _old.TargetFilesMetadataError
PROFILE, RECEIPT, BUNDLE = _old.PROFILE, _old.RECEIPT, _old.BUNDLE
IMAGE_CONTRACT = _old.IMAGE_CONTRACT
CONTROL_TOOLS = (*_old.CONTROL_TOOLS, ADAPTER)


def _descriptor(base):
    return {"schema_version": 1, "contract_id": SOURCE_CONTRACT_ID, "project": base["project"],
            "predecessor_contract": {"path": BASE_SOURCE_CONTRACT, **BASE_SOURCE_CONTRACT_ID},
            "predecessor_composition": BASE_COMPOSITION_ID, "patch": PATCH,
            "source_file": {"path": CORE, "before": CORE_BEFORE, "after": CORE_AFTER},
            "scope": {"checksum_recipe_only": True, "metadata_payloads_changed": False,
                      "image_bytes_changed": False, "policy_provenance_changed": False,
                      "source_installed": False, "native_packaging_verified": False,
                      "hardware_tested": False, "complete_rom_ready": False}}


def _derive_composition(base):
    same(identity(encoded(base)), BASE_COMPOSITION_ID, "checksum predecessor composition differs")
    require(len(base["contracts"]) == 8 and len(base["ordered_patches"]) == 7
            and len(base["source_transitions"]) == 7 and len(base["final_source_files"]) == 10,
            "checksum predecessor source closure differs")
    current = copy.deepcopy(base)
    rows = [row for row in current["final_source_files"] if row["path"] == CORE]
    require(len(rows) == 1 and rows[0] == {"path": CORE, **CORE_BEFORE},
            "checksum transition requires the exact complete Makefile preimage")
    rows[0].update(CORE_AFTER)
    current["contracts"].append({"path": SOURCE_CONTRACT, **SOURCE_CONTRACT_IDENTITY})
    current["ordered_patches"].append(copy.deepcopy(PATCH))
    current["source_transitions"].append(
        {"patch": copy.deepcopy(PATCH), "path": CORE,
         "before": copy.deepcopy(CORE_BEFORE), "after": copy.deepcopy(CORE_AFTER)})
    return current


def _read_successor(root, reader, source_contract, base):
    require(source_contract is not None, "explicit checksum source contract required")
    root = _old._factory.real_directory(root)
    raw = reader.read(root / SOURCE_CONTRACT, SOURCE_CONTRACT_IDENTITY)
    selected = Path(source_contract)
    selected = selected if selected.is_absolute() else root / relative(selected.as_posix())
    require(reader.read(selected, SOURCE_CONTRACT_IDENTITY) == raw,
            "selected checksum source contract differs from controls")
    same(_old._factory._json(raw), _descriptor(base), "checksum descriptor transition or scope differs")
    patch = reader.read(root / PATCH["path"], PATCH)
    return raw, patch


def compose_sources(root=ROOT, *, source_contract=None):
    require(source_contract is not None, "explicit checksum source contract required")
    reader = Reader()
    base = _old.compose_sources(root, source_contract=BASE_SOURCE_CONTRACT)
    _read_successor(root, reader, source_contract, base)
    current = _derive_composition(base)
    reader.recheck()
    return current


def _controls(root, reader, *, source_contract=None, image_contract=None):
    require(source_contract is not None, "explicit checksum source contract required")
    profile, base, controls = _old._controls(
        root, reader, source_contract=BASE_SOURCE_CONTRACT, image_contract=image_contract)
    raw, patch = _read_successor(root, reader, source_contract, base)
    controls.update({SOURCE_CONTRACT: raw, PATCH["path"]: patch,
                     ADAPTER: reader.read(Path(root) / ADAPTER, _self_identity, maximum=2 << 20)})
    runtime_tool_payloads(controls)
    return profile, _derive_composition(base), controls


def runtime_tool_payloads(controls):
    require(all(name in controls for name in CONTROL_TOOLS), "checksum maintained assembly source missing")
    same(identity(controls[PREDECESSOR]), PREDECESSOR_ID, "frozen policy3 consumer changed")
    predecessor = _old.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]
    _body(predecessor, PREDECESSOR_RUNTIME_ID)
    extension = controls[ADAPTER]
    require(type(extension) is bytes and 0 < len(extension) <= 2 << 20,
            "bounded checksum adapter required")
    same(identity(extension), _self_identity, "checksum adapter differs from selected source")
    prefix = ("#!/usr/bin/env python3\n# Generated from seven explicitly admitted maintained sources.\n"
              "_CHECKSUM_PREDECESSOR_PAYLOAD = " + repr(predecessor) + "\n"
              "_CHECKSUM_ADAPTER_IDENTITY = " + repr(identity(extension)) + "\n").encode()
    return {"tools/target_files_metadata.py": prefix + extension}


def _check_original(raw, receipt, files, admission):
    # The original images were produced before 0023. Authenticate the complete
    # new source transition before using the historical comparison view.
    _old._validate_admission(admission, admission["source_composition"])
    same(receipt["source_composition"], _derive_composition(admission["source_composition"]),
         "metadata current source is not the exact checksum successor")
    historical = dict(receipt, source_composition=admission["source_composition"])
    _old._impl["_check_original"](raw, historical, files, admission)


# Only these two selectors change the frozen staging function. The original
# factory receipt stays on its historical selector; the newly staged bundle
# must be verified with the explicit checksum successor selector.
STAGE_TRANSFORMS = (
    ("expected_receipt=expected_original_receipt, source_contract=source_contract)",
     "expected_receipt=expected_original_receipt, source_contract=BASE_SOURCE_CONTRACT)"),
    ("source_contract=_factory.COMBINED_SOURCE_CONTRACT, image_contract=IMAGE_CONTRACT)",
     "source_contract=SOURCE_CONTRACT, image_contract=IMAGE_CONTRACT)"),
)


def _definitions():
    source = _old._definitions()
    parsed = ast.parse(source)
    stages = [node for node in parsed.body if isinstance(node, ast.FunctionDef)
              and node.name == "stage_from_original"]
    require(len(stages) == 1, "one frozen policy3 staging function required")
    before = ast.get_source_segment(source, stages[0])
    after = before
    for old, new in STAGE_TRANSFORMS:
        require(after.count(old) == 1, "checksum stage source-selector boundary differs")
        after = after.replace(old, new)
    require(source.count(before) == 1, "duplicate frozen policy3 staging body")
    return source.replace(before, after)


# The original selector reads the externally pinned receipt before choosing a
# source contract. Keep its function bytecode and reader checks unchanged.
_selector_original = _old._factory._selected_receipt_source_contract
_selector_globals = dict(_selector_original.__globals__)
_selector_globals.update(
    COMBINED_CONTRACTS=(*_old._factory.COMBINED_CONTRACTS, SOURCE_CONTRACT),
    COMBINED_SOURCE_CONTRACT=SOURCE_CONTRACT, COMBINED_SOURCE_ID=SOURCE_CONTRACT_ID)
_selected_receipt_source_contract = types.FunctionType(
    _selector_original.__code__, _selector_globals, _selector_original.__name__,
    _selector_original.__defaults__, _selector_original.__closure__)

_impl = dict(_old._impl)
_impl.update(ROOT=ROOT, NATIVE=NATIVE, ADAPTER=ADAPTER, CONTROL_TOOLS=CONTROL_TOOLS,
             SOURCE_CONTRACT=SOURCE_CONTRACT, BASE_SOURCE_CONTRACT=BASE_SOURCE_CONTRACT,
             _self_identity=_self_identity, __doc__=__doc__)
exec(compile(_definitions(), "<frozen-policy3-functions-with-checksum-source-selection>", "exec"), _impl)
# The extracted definitions include historical structural validators. Restore
# every policy3-specific callback exactly as the predecessor does; this source
# successor must not select an older policy or evidence validator.
_impl.update({name: _old._impl[name] for name in (
    "_validate_admission", "_validate_proof", "_validate_evidence",
    "_current_policy_gate", "_installation_report", "_ready")})
_impl.update(_controls=_controls, compose_sources=compose_sources, _check_original=_check_original,
             runtime_tool_payloads=runtime_tool_payloads)
_install_namespace = dict(_old._install_namespace)
_install_namespace.update(
    verify_bundle=_impl["_install_verify"],
    _selected_receipt_source_contract=_selected_receipt_source_contract)
exec(compile(_old._v2._install_source, "<unchanged-atomic-install-with-checksum-selector>", "exec"),
     _install_namespace)
_impl.update(_install_namespace=_install_namespace, _install_impl=_install_namespace["install"])
for _name in ("stage_from_original", "verify_bundle", "install", "selection", "main"):
    globals()[_name] = _impl[_name]
_files = _old._files


if __name__ == "__main__":
    raise SystemExit(main())
