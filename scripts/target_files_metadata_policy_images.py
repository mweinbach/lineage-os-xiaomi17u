#!/usr/bin/env python3
"""Maintained metadata delivery basis for policy-bearing vendor and ODM images.

Promoted from the reviewed delivery-v1 adapter, SHA256
f99b3e14bc50aba9449a4b0698f1a64ac63473b631acfb0e7062cf522a88ae5e.
The original and combined metadata implementations remain byte-identical.
Host staging copies the original small metadata bundle, never image bodies.
The generated native tool is self-contained and retains the frozen installer's
publication code. Current policy-build evidence has no admitted positive form.
"""

import argparse
import ast
import copy
import hashlib
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile
import types

sys.dont_write_bytecode = True
HERE = "scripts"
ADAPTER = "scripts/target_files_metadata_policy_images.py"
IMAGE_CONTRACT = "config/nezha-policy-image-delivery-basis.json"
IMAGE_CONTRACT_ID = "nezha-v13h-final-leaf-metadata-delivery-v1"
PROOF_OPERATION = "verify-v13h-final-leaf-metadata-delivery-v1"
STAGE_OPERATION = "stage-policy-image-target-files-metadata-v1"
INSTALL_OPERATION = "project-policy-image-target-files-metadata-v1"
ORIGINAL_COPY = "provenance/original-target-files-metadata.json"
PROOF_COPY = "provenance/policy-image-delivery-proof.json"
BASE = "scripts/target_files_metadata.py"
COMBINED = "scripts/target_files_metadata_combined.py"
FROZEN = {
    BASE: {"sha256": "60e54729e5e9b3e261af45898752717eb7213b98aafb51beac8b96b848ee6184", "size_bytes": 39730},
    COMBINED: {"sha256": "239a136605f858efe4de4ad310aa16a1d8b3a1739e17fa815029fa8de8f9d23c", "size_bytes": 24503},
}
PREDECESSOR_ID = {"sha256": "8f050bd146f1136a496ba9adf80281abab4dee4d31a579df7a7f3c0dc6ece59e", "size_bytes": 64462}
ORIGINAL_ID = {"sha256": "8c1c78d19d786fee2be6c92a3f93fd28677ab24500f74da3bb911f96e6de89df", "size_bytes": 197440}
PACKAGED_IMAGES = {
    "vendor": {"sha256": "ce11f1c6dfc87c29ade267e53d968426cb1e4fa7ce7decca9b1ee85dcb5c7a43", "size_bytes": 959709184},
    "odm": {"sha256": "854c0047709496136557fbdaf2f3ee0a124fa6a18c1bfaddd063d2a3d006d257", "size_bytes": 4767621120},
}
MAIN_BOUNDARY = b'\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
MEMBER_COUNT, MEMBER_BYTES = 205, 6460780
COMPILER_RUNTIME_PATHS = (
    "/system/etc/selinux/plat_sepolicy.cil", "/system/etc/selinux/mapping/202504.cil",
    "/system_ext/etc/selinux/system_ext_sepolicy.cil", "/system_ext/etc/selinux/mapping/202504.cil",
    "/product/etc/selinux/product_sepolicy.cil", "/product/etc/selinux/mapping/202504.cil",
    "/vendor/etc/selinux/plat_pub_versioned.cil", "/vendor/etc/selinux/vendor_sepolicy.cil",
    "/odm/etc/selinux/odm_sepolicy.cil", "/system/etc/selinux/plat_sepolicy_genfs_202504.cil")
PROOF_SCOPE = {name: False for name in (
    "current_policy_build_equivalence_verified", "selected_guest_images_rehashed",
    "packaged_framework_policy_verified", "delivery_images_adopted", "target_files_metadata_installed",
    "complete_target_files_verified", "target_files_vintf_compatible", "signed_parent_chain_verified",
    "physical_partition_fit_verified", "device_rollback_compatibility_verified", "runtime_verified",
    "native_commands_run", "images_or_keys_read", "host_large_images_copied", "guest_accessed",
    "public_or_frozen_files_modified", "phone_accessed", "complete_rom_ready")}
ADMISSION_KEYS = {"schema_version", "contract_id", "factory_package_sha256", "original_images",
                  "packaged_images", "source_composition", "metadata_members", "expected_root_descriptors",
                  "policy_inputs", "delivery_proof", "current_policy_build_evidence", "scope"}
RECEIPT_KEYS = {"schema_version", "operation", "profile", "images", "packaged_images", "source_composition",
                "files", "property_closure", "bundle_files", "image_admission", "original_receipt",
                "delivery_proof", "scope", "delivery_scope"}


def _bootstrap_identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _bootstrap_read(path, wanted=None, maximum=2 << 20):
    path = Path(os.path.abspath(path))
    for parent in path.parents:
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise ValueError("adapter bootstrap requires real parent directories")
    before = path.lstat()
    def binding(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns)
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > maximum:
        raise ValueError("adapter bootstrap requires bounded single-link regular source")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        if binding(before) != binding(os.fstat(stream.fileno())):
            raise ValueError("adapter bootstrap source replaced")
        raw = stream.read(maximum + 1)
        if len(raw) > maximum or binding(before) != binding(os.fstat(stream.fileno())) or binding(before) != binding(path.lstat()):
            raise ValueError("adapter bootstrap source changed")
    if wanted is not None and _bootstrap_identity(raw) != wanted:
        raise ValueError("adapter frozen predecessor identity differs")
    return raw


def _function_source(raw, name):
    text = raw.decode("utf-8")
    nodes = [node for node in ast.parse(text).body if isinstance(node, ast.FunctionDef) and node.name == name]
    if len(nodes) != 1:
        raise ValueError("adapter predecessor function boundary differs")
    return ast.get_source_segment(text, nodes[0]) + "\n"


def _predecessor_program(base, combined):
    if _bootstrap_identity(base) != FROZEN[BASE] or _bootstrap_identity(combined) != FROZEN[COMBINED]:
        raise ValueError("adapter frozen source identity differs")
    # Only the admitted pure source assembler executes in this tiny namespace.
    namespace = {"hashlib": hashlib, "FROZEN_BASE_IDENTITY": FROZEN[BASE], "_BASE_MAIN": MAIN_BOUNDARY}
    exec(compile(_function_source(combined, "_base_body"), "<frozen-combined-assembler>", "exec"), namespace)
    result = namespace["_base_body"](base) + b"\n_NEZHA_COMBINED_BASE_LOADED = True\n" + combined
    _predecessor_body(result)
    return result


def _predecessor_body(raw):
    if type(raw) is not bytes or _bootstrap_identity(raw) != PREDECESSOR_ID:
        raise ValueError("adapter predecessor runtime identity differs")
    if not raw.endswith(MAIN_BOUNDARY) or raw.count(MAIN_BOUNDARY) != 1:
        raise ValueError("adapter predecessor terminal main differs")
    return raw[:-len(MAIN_BOUNDARY)]


NATIVE = "_DELIVERY_PREDECESSOR_PAYLOAD" in globals()
if NATIVE:
    _predecessor_raw = _DELIVERY_PREDECESSOR_PAYLOAD
    _self_identity = _DELIVERY_ADAPTER_IDENTITY
    ROOT = Path(os.path.abspath(__file__)).parent.parent
else:
    ROOT = Path(os.path.abspath(__file__)).parents[1]
    _self_identity = _bootstrap_identity(_bootstrap_read(__file__))
    _predecessor_raw = _predecessor_program(*[_bootstrap_read(ROOT / path, FROZEN[path]) for path in (BASE, COMBINED)])
_predecessor_source = _predecessor_body(_predecessor_raw)
_factory = types.ModuleType("_nezha_frozen_combined_metadata")
_factory.__file__ = str(ROOT / COMBINED)
exec(compile(_predecessor_source, "<hash-bound-combined-metadata>", "exec"), _factory.__dict__)
TargetFilesMetadataError = _factory.TargetFilesMetadataError
Reader, encoded, identity = _factory.Reader, _factory.encoded, _factory.identity
require, expected, relative = _factory.require, _factory.expected, _factory.relative
PROFILE, RECEIPT, BUNDLE = _factory.PROFILE, _factory.RECEIPT, _factory.BUNDLE
MAX_TEXT, MAX_PAYLOAD, MAX_IMAGE = _factory.MAX_TEXT, _factory.MAX_PAYLOAD, _factory.MAX_IMAGE
CONTROL_TOOLS = (BASE, COMBINED, ADAPTER)
_files = _factory._files


class CurrentPolicyEvidenceRequired(TargetFilesMetadataError):
    """The pending current-build gate has no admitted positive form."""


def same(actual, wanted, message):
    require(encoded(actual) == encoded(wanted), message)


def compose_sources(root=ROOT, *, source_contract=None):
    return _factory.compose_sources(root, source_contract=source_contract)


def runtime_tool_payloads(controls):
    require(all(path in controls for path in CONTROL_TOOLS), "delivery source controls missing")
    predecessor = _predecessor_program(controls[BASE], controls[COMBINED])
    extension = controls[ADAPTER]
    require(type(extension) is bytes and 0 < len(extension) <= 2 << 20, "delivery adapter source is unbounded")
    prefix = ("#!/usr/bin/env python3\n# Generated from exact frozen predecessors and the delivery adapter.\n"
              "_DELIVERY_PREDECESSOR_PAYLOAD = " + repr(predecessor) + "\n"
              "_DELIVERY_ADAPTER_IDENTITY = " + repr(identity(extension)) + "\n").encode()
    return {"tools/target_files_metadata.py": prefix + extension}


def _validate_admission(admission, composition):
    require(type(admission) is dict and set(admission) == ADMISSION_KEYS
            and type(admission["schema_version"]) is int and admission["schema_version"] == 1
            and admission["contract_id"] == IMAGE_CONTRACT_ID, "unknown image admission schema or selector")
    require(admission["factory_package_sha256"] == _factory.EXPECTED_PACKAGE, "image admission factory differs")
    same(admission["original_images"], _factory.EXPECTED_IMAGES, "image admission rewrites original images")
    same(admission["packaged_images"], PACKAGED_IMAGES, "image admission final pair differs")
    same(admission["source_composition"], composition, "image admission ten-file source composition differs")
    same(admission["scope"], PROOF_SCOPE, "image admission cannot promote adoption or runtime scope")
    require(admission["current_policy_build_evidence"] is None,
            "no positive current policy-build evidence form is admitted by this candidate")
    same(admission["delivery_proof"], expected(admission["delivery_proof"]), "invalid delivery proof identity")
    members = admission["metadata_members"]
    require(type(members) is list and len(members) == MEMBER_COUNT, "exact metadata member count required")
    paths = []
    for row in members:
        require(type(row) is dict and set(row) == {"target_path", "partition", "path", "kind", "payload"},
                "invalid metadata member fields")
        require(row["partition"] in ("vendor", "odm") and type(row["path"]) is str and row["path"].startswith("/")
                and row["target_path"] == row["partition"].upper() + row["path"], "metadata member partition/path differs")
        relative(row["target_path"])
        require(row["kind"] == _factory._kind(row["path"]) and row["kind"] in ("properties", "vintf", "apex"),
                "metadata member kind differs")
        same(row["payload"], expected(row["payload"], MAX_PAYLOAD), "invalid metadata payload identity")
        paths.append(row["target_path"])
    require(paths == sorted(set(paths)) and sum(row["payload"]["size_bytes"] for row in members) == MEMBER_BYTES,
            "metadata member ordering, uniqueness or byte count differs")
    require(type(admission["expected_root_descriptors"]) is dict
            and set(admission["expected_root_descriptors"]) == {"vendor", "odm"}, "exact root descriptor pair required")
    for partition, descriptor in admission["expected_root_descriptors"].items():
        require(type(descriptor) is dict and descriptor.get("kind") == "hashtree"
                and descriptor.get("partition") == partition, "root descriptor role differs")
    policy = admission["policy_inputs"]
    require(type(policy) is dict and set(policy) == {"actual_compiler_inputs", "exact_five_replacement_identities"}
            and type(policy["actual_compiler_inputs"]) is list and len(policy["actual_compiler_inputs"]) == 10,
            "exact ten compiler input references required")
    for row, runtime_path in zip(policy["actual_compiler_inputs"], COMPILER_RUNTIME_PATHS):
        require(type(row) is dict and set(row) == {"compiler_input", "resolved_path", "runtime_path", "sha256", "size_bytes"}
                and row["runtime_path"] == runtime_path and type(row["compiler_input"]) is str
                and 0 < len(row["compiler_input"]) <= 4096 and type(row["resolved_path"]) is str
                and 0 < len(row["resolved_path"]) <= 4096, "compiler input role or fields differ")
        expected(row, MAX_PAYLOAD)
    changes = policy["exact_five_replacement_identities"]
    require(type(changes) is dict and set(changes) == {"vendor", "odm"}
            and set(changes["vendor"]) == {"/etc/selinux/vendor_sepolicy.cil"}
            and set(changes["odm"]) == {"/etc/selinux/precompiled_sepolicy", *{
                "/etc/selinux/precompiled_sepolicy." + part + "_sepolicy_and_mapping.sha256"
                for part in ("plat", "system_ext", "product")}}, "exact five policy replacements required")
    for rows in changes.values():
        for value in rows.values():
            same(value, expected(value, MAX_PAYLOAD), "invalid policy replacement identity")


def _controls(root, reader, *, source_contract=None, image_contract=None):
    require(image_contract is not None, "explicit image contract required")
    root = _factory.real_directory(root)
    profile, composition, controls = _factory._controls(root, reader, source_contract=source_contract)
    adapter = reader.read(root / ADAPTER, _self_identity, maximum=2 << 20)
    raw = reader.read(root / IMAGE_CONTRACT)
    selected = Path(image_contract)
    selected = selected if selected.is_absolute() else root / relative(selected.as_posix())
    require(reader.read(selected) == raw, "selected image contract differs from controls")
    _validate_admission(_factory._json(raw), composition)
    controls.update({ADAPTER: adapter, IMAGE_CONTRACT: raw})
    runtime_tool_payloads(controls)
    return profile, composition, controls


def _validate_proof(raw, admission):
    same(identity(raw), admission["delivery_proof"], "delivery proof differs from admitted digest")
    proof = _factory._json(raw)
    require(type(proof.get("schema_version")) is int and proof["schema_version"] == 1
            and proof.get("operation") == PROOF_OPERATION and proof.get("derivation_verified") is True
            and proof.get("bound_evidence_rehashed") is True, "reviewed delivery derivation proof required")
    for key in ("factory_package_sha256", "original_images", "packaged_images", "source_composition",
                "metadata_members", "expected_root_descriptors", "policy_inputs", "current_policy_build_evidence", "scope"):
        same(proof.get(key), admission[key], "delivery proof linkage differs: " + key)
    require(type(proof.get("metadata_count")) is int and proof["metadata_count"] == MEMBER_COUNT
            and type(proof.get("metadata_bytes")) is int and proof["metadata_bytes"] == MEMBER_BYTES,
            "delivery proof metadata closure differs")
    same(expected(proof.get("original_metadata_receipt")), ORIGINAL_ID,
         "delivery proof original receipt differs")
    return proof


def _members(files):
    return [{"target_path": path, "partition": row["partition"], "path": row["path"],
             "kind": row["kind"], "payload": identity(raw)} for path, (row, raw) in sorted(files.items())]


def _check_original(raw, receipt, files, admission):
    same(identity(raw), ORIGINAL_ID, "original metadata receipt differs")
    original = _factory._json(raw)
    require(type(original.get("schema_version")) is int and original["schema_version"] == 1
            and original.get("operation") == "stage-factory-target-files-metadata", "original metadata receipt operation differs")
    for key in ("profile", "images", "source_composition", "files", "property_closure", "scope"):
        same(original.get(key), receipt[key], "original metadata semantics differ: " + key)
    same(admission["metadata_members"], _members(files), "205 original metadata bytes differ from image bridge")


def _payloads(files, provenance, controls, original, proof):
    payloads = {"tree/" + path: raw for path, (_, raw) in files.items()}
    payloads.update(provenance)
    payloads.update({"controls/" + path: raw for path, raw in controls.items()})
    payloads.update(runtime_tool_payloads(controls))
    require(ORIGINAL_COPY not in payloads and PROOF_COPY not in payloads, "delivery provenance collision")
    payloads.update({ORIGINAL_COPY: original, PROOF_COPY: proof})
    return payloads


def _receipt(profile, composition, controls, original, files, closure, payloads, admission):
    return {"schema_version": 2, "operation": STAGE_OPERATION,
            "profile": {"path": PROFILE, **identity(controls[PROFILE])},
            "images": copy.deepcopy(_factory.EXPECTED_IMAGES), "packaged_images": copy.deepcopy(admission["packaged_images"]),
            "source_composition": composition, "files": [files[path][0] for path in sorted(files)],
            "property_closure": closure, "scope": copy.deepcopy(_factory.SCOPE), "delivery_scope": copy.deepcopy(PROOF_SCOPE),
            "image_admission": {"path": IMAGE_CONTRACT, **identity(controls[IMAGE_CONTRACT])},
            "original_receipt": {"path": ORIGINAL_COPY, **identity(original)},
            "delivery_proof": {"path": PROOF_COPY, **admission["delivery_proof"]},
            "bundle_files": [{"path": path, **identity(raw)} for path, raw in sorted(payloads.items())]}


def stage_from_original(original_bundle, output, *, expected_original_receipt, source_contract,
                        image_contract, delivery_proof, controls_root=None):
    """Stage small metadata/provenance only; do not read or copy image bodies."""
    require(not NATIVE, "staging is a host-only candidate operation")
    require(expected_original_receipt == ORIGINAL_ID["sha256"], "exact original receipt digest required")
    original_bundle = _factory.real_directory(original_bundle)
    # No image arguments: the frozen predecessor retains factory image semantics.
    original_receipt, files, reader = _factory.verify_bundle(original_bundle,
        expected_receipt=expected_original_receipt, source_contract=source_contract)
    original = reader.read(original_bundle / RECEIPT, ORIGINAL_ID)
    profile, composition, controls = _controls(ROOT if controls_root is None else controls_root, reader,
        source_contract=source_contract, image_contract=image_contract)
    admission = _factory._json(controls[IMAGE_CONTRACT])
    proof = reader.read(delivery_proof, admission["delivery_proof"])
    _validate_proof(proof, admission)
    provenance = {row["path"]: reader.read(original_bundle / row["path"], row, maximum=MAX_PAYLOAD)
                  for row in original_receipt["bundle_files"] if row["path"].startswith("provenance/")}
    payloads = _payloads(files, provenance, controls, original, proof)
    receipt = _receipt(profile, composition, controls, original, files, original_receipt["property_closure"], payloads, admission)
    _check_original(original, receipt, files, admission)
    output = Path(os.path.abspath(output))
    _factory.real_directory(output.parent)
    require(not output.exists() and not output.is_symlink(), "new bundle destination required")
    temporary = Path(tempfile.mkdtemp(prefix=".nezha-delivery-metadata-", dir=output.parent))
    temporary_owner = _factory._inode(temporary.lstat())
    try:
        for path, raw in payloads.items():
            _factory._write(temporary / path, raw)
        _factory._write(temporary / RECEIPT, encoded(receipt))
        # Read back the actual staged payloads without requiring any image body.
        _, _, staged_reader = verify_bundle(temporary, expected_receipt=identity(encoded(receipt))["sha256"],
            source_contract=_factory.COMBINED_SOURCE_CONTRACT, image_contract=IMAGE_CONTRACT)
        reader.recheck()
        require(_factory._files(original_bundle) == {row["path"] for row in original_receipt["bundle_files"]} | {RECEIPT},
                "original bundle inventory changed during staging")
        staged_reader.recheck()
        _factory.publish_new_directory(temporary, output)
    finally:
        if (temporary.exists() or temporary.is_symlink()) and _factory._inode(temporary.lstat()) == temporary_owner:
            shutil.rmtree(temporary)
    return receipt


def _captured_bundle(bundle, profile, mapping, reader):
    sources = {}
    for partition, rule in profile["partitions"].items():
        sources[rule["inventory"]["path"]] = bundle / f"provenance/{partition}-inventory.json"
        sources[rule["inventory_receipt"]["path"]] = bundle / f"provenance/{partition}-inventory-receipt.json"
        for index, ref in enumerate(rule["captures"]):
            name = f"provenance/{partition}-capture-{index:02}.json"
            sources[ref["path"]] = bundle / name
            for row in _factory._json(mapping[name])["files"]:
                if row.get("type") == "regular" and _factory._kind(row["path"]) is not None:
                    original = (Path(ref["path"]).parent / relative(row["output_path"])).as_posix()
                    sources[original] = bundle / ("tree/" + partition.upper() + row["path"])
    def locate(path):
        require(path in sources, "unbound captured metadata source")
        return sources[path]
    return _factory._captured(profile, reader, locate)


def _current_policy_gate(admission, target_files, reader):
    # Do not invent a positive current-build form or turn a missing result into a Boolean override.
    raise CurrentPolicyEvidenceRequired(
        "actual v13i 37-goal policy equality and packaged seven-input/three-sidecar evidence are required; "
        "current_policy_build_evidence is not admitted")


def verify_bundle(bundle, *, expected_receipt, source_contract=None, image_contract=None,
                  source_tree=None, vendor_image=None, odm_image=None, target_files=None):
    require(type(expected_receipt) is str and re.fullmatch(r"[0-9a-f]{64}", expected_receipt),
            "an external expected bundle receipt SHA256 is required")
    bundle, reader = _factory.real_directory(bundle), Reader()
    raw = reader.read(bundle / RECEIPT)
    require(identity(raw)["sha256"] == expected_receipt, "bundle receipt differs from selected digest")
    receipt = _factory._json(raw)
    require(set(receipt) == RECEIPT_KEYS and type(receipt["schema_version"]) is int and receipt["schema_version"] == 2
            and receipt["operation"] == STAGE_OPERATION, "unknown delivery bundle schema or operation")
    profile, composition, controls = _controls(bundle / "controls", reader,
        source_contract=source_contract, image_contract=image_contract)
    admission = _factory._json(controls[IMAGE_CONTRACT])
    bindings = receipt["bundle_files"]
    require(type(bindings) is list and len(bindings) <= 2048, "invalid bundle file inventory")
    mapping = {}
    for row in bindings:
        require(type(row) is dict and set(row) == {"path", "sha256", "size_bytes"}, "invalid bundle file binding")
        path = relative(row["path"])
        require(path not in mapping, "duplicate bundle file")
        mapping[path] = reader.read(bundle / path, row, maximum=MAX_PAYLOAD)
    require(_factory._files(bundle) == set(mapping) | {RECEIPT}, "unlisted or missing bundle file")
    require(ORIGINAL_COPY in mapping and PROOF_COPY in mapping, "delivery provenance missing")
    original, proof = mapping[ORIGINAL_COPY], mapping[PROOF_COPY]
    _validate_proof(proof, admission)
    files, provenance, closure = _captured_bundle(bundle, profile, mapping, reader)
    payloads = _payloads(files, provenance, controls, original, proof)
    wanted = _receipt(profile, composition, controls, original, files, closure, payloads, admission)
    same(receipt, wanted, "delivery bundle derivation differs")
    require(mapping == payloads, "delivery bundle payload inventory differs")
    _check_original(original, receipt, files, admission)
    if source_tree is not None:
        _factory._check_source(source_tree, composition, reader)
    require((vendor_image is None) == (odm_image is None), "both selected final images are required")
    if vendor_image is not None:
        for partition, path in {"vendor": vendor_image, "odm": odm_image}.items():
            reader.read(path, admission["packaged_images"][partition], maximum=MAX_IMAGE, data=False)
    if target_files is not None:
        target = _factory.real_directory(target_files)
        require(source_tree is not None and vendor_image is not None
                and Path(os.path.abspath(vendor_image)) == target / "IMAGES/vendor.img"
                and Path(os.path.abspath(odm_image)) == target / "IMAGES/odm.img",
                "policy gate requires actual source and canonical selected final images")
        _current_policy_gate(admission, target, reader)
    reader.recheck()
    require(_factory._files(bundle) == set(mapping) | {RECEIPT}, "bundle inventory changed during verification")
    return receipt, files, reader


def _selected_image_contract(bundle, expected_receipt):
    require(type(expected_receipt) is str and re.fullmatch(r"[0-9a-f]{64}", expected_receipt),
            "external receipt digest required before image selection")
    bundle, reader = _factory.real_directory(bundle), Reader()
    raw = reader.read(bundle / RECEIPT)
    require(identity(raw)["sha256"] == expected_receipt, "receipt differs before image selection")
    receipt = _factory._json(raw)
    require(set(receipt) == RECEIPT_KEYS and type(receipt["schema_version"]) is int and receipt["schema_version"] == 2
            and receipt["operation"] == STAGE_OPERATION, "unknown image selector receipt")
    ref = receipt["image_admission"]
    require(type(ref) is dict and set(ref) == {"path", "sha256", "size_bytes"}
            and ref["path"] == IMAGE_CONTRACT, "unknown image contract path")
    copied = reader.read(bundle / "controls" / IMAGE_CONTRACT, ref)
    require(_factory._json(copied).get("contract_id") == IMAGE_CONTRACT_ID, "unknown copied image contract")
    require(type(receipt["bundle_files"]) is list and [row for row in receipt["bundle_files"]
            if type(row) is dict and row.get("path") == "controls/" + IMAGE_CONTRACT]
            == [{"path": "controls/" + IMAGE_CONTRACT, **expected(ref)}], "image contract is not uniquely inventoried")
    reader.recheck()
    return IMAGE_CONTRACT


def _install_verify(bundle, *, expected_receipt, source_tree, vendor_image, odm_image, source_contract):
    return verify_bundle(bundle, expected_receipt=expected_receipt, source_tree=source_tree,
        vendor_image=vendor_image, odm_image=odm_image, source_contract=source_contract,
        image_contract=_selected_image_contract(bundle, expected_receipt),
        target_files=Path(vendor_image).parent.parent)


def _installation_report(receipt, expected_receipt):
    raise CurrentPolicyEvidenceRequired("no installation report is admitted while current policy evidence is pending")


INSTALL_REPORT_PREIMAGE = '''    report = {"schema_version": 1, "operation": "project-factory-target-files-metadata",
              "bundle_receipt_sha256": expected_receipt, "images": receipt["images"],
              "files": receipt["files"], "property_closure": receipt["property_closure"],
              "source_composition": receipt["source_composition"], "scope": copy.deepcopy(SCOPE)}'''


def _installation_source(raw):
    source = _function_source(_predecessor_body(raw), "install")
    require(source.count(INSTALL_REPORT_PREIMAGE) == 1, "frozen install report hook differs")
    return source.replace(INSTALL_REPORT_PREIMAGE, "    report = _delivery_installation_report(receipt, expected_receipt)")


_install_namespace = dict(_factory.__dict__)
_install_namespace.update(verify_bundle=_install_verify, _delivery_installation_report=_installation_report)
exec(compile(_installation_source(_predecessor_raw), "<hash-bound-delivery-install>", "exec"), _install_namespace)
_install_impl = _install_namespace["install"]


def install(bundle, target_files, *, expected_receipt, source_tree):
    return _install_impl(bundle, target_files, expected_receipt=expected_receipt, source_tree=source_tree)


def selection(bundle, *, expected_receipt, source_contract=None, image_contract=None):
    receipt, _, _ = verify_bundle(bundle, expected_receipt=expected_receipt,
        source_contract=source_contract, image_contract=image_contract)
    tool = next(row for row in receipt["bundle_files"] if row["path"] == "tools/target_files_metadata.py")
    return ("# Explicit candidate metadata delivery; current policy adoption remains blocked.\n"
            "BOARD_NEZHA_PREBUILT_METADATA := true\n"
            f"BOARD_NEZHA_PREBUILT_METADATA_RECEIPT_SHA256 := {expected_receipt}\n"
            f"BOARD_NEZHA_PREBUILT_METADATA_TOOL_SHA256 := {tool['sha256']}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage")
    for name in ("original-bundle", "output", "source-contract", "image-contract", "delivery-proof"):
        stage.add_argument("--" + name, type=Path, required=True)
    stage.add_argument("--expected-original-receipt", required=True)
    stage.add_argument("--controls-root", type=Path)
    for name in ("verify", "install", "selection"):
        command = commands.add_parser(name)
        command.add_argument("--bundle", type=Path, required=True)
        command.add_argument("--expected-receipt", required=True)
        if name == "install":
            command.add_argument("--source-tree", type=Path, required=True)
            command.add_argument("--target-files", type=Path, required=True)
        else:
            command.add_argument("--source-contract", type=Path, required=True)
            command.add_argument("--image-contract", type=Path, required=True)
            if name == "verify":
                for option in ("source-tree", "vendor-image", "odm-image", "target-files"):
                    command.add_argument("--" + option, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "stage":
            result = stage_from_original(args.original_bundle, args.output,
                expected_original_receipt=args.expected_original_receipt, source_contract=args.source_contract,
                image_contract=args.image_contract, delivery_proof=args.delivery_proof, controls_root=args.controls_root)
        elif args.command == "install":
            result = install(args.bundle, args.target_files, expected_receipt=args.expected_receipt, source_tree=args.source_tree)
        elif args.command == "selection":
            print(selection(args.bundle, expected_receipt=args.expected_receipt,
                source_contract=args.source_contract, image_contract=args.image_contract), end="")
            return 0
        else:
            receipt, _, _ = verify_bundle(args.bundle, expected_receipt=args.expected_receipt,
                source_contract=args.source_contract, image_contract=args.image_contract,
                source_tree=args.source_tree, vendor_image=args.vendor_image, odm_image=args.odm_image,
                target_files=args.target_files)
            result = {"receipt": receipt, "host_metadata_verified": True,
                      "actual_selected_images_rehashed": args.vendor_image is not None,
                      "source_tree_rehashed": args.source_tree is not None,
                      "current_policy_build_verified": False, "images_adopted": False}
        print(encoded(result).decode(), end="")
        return 0
    except CurrentPolicyEvidenceRequired as exc:
        print(encoded({"status": "blocked", "error": str(exc), "images_adopted": False}).decode(), end="")
        return 3
    except (TargetFilesMetadataError, OSError, KeyError, TypeError, ValueError) as exc:
        print("candidate metadata delivery: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
