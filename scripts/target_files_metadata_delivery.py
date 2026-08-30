#!/usr/bin/env python3
"""Explicit metadata delivery for the reviewed v13i policy-bearing image pair.

Promoted from the audited delivery-v2 adapter with canonical maintained controls.
The generated checker embeds all four admitted sources; staging reads metadata
and evidence only. Native installation still requires actual images, source and
framework policy/sidecars and does not establish a complete or bootable ROM.
"""

import ast
import copy
import hashlib
import os
from pathlib import Path
import stat
import sys
import types

sys.dont_write_bytecode = True
HERE = "scripts"
V1_HERE = "scripts"
ADAPTER = "scripts/target_files_metadata_delivery.py"
IMAGE_CONTRACT = "config/nezha-policy-image-delivery.json"
V1_ADAPTER = "scripts/target_files_metadata_policy_images.py"
V1_CONTRACT = "config/nezha-policy-image-delivery-basis.json"
V1_SOURCE_ID = {"sha256": "a94c652998dc9b1d16b07c0da5e26e3bcca292b2941ca2adeaf4df907a8b457d", "size_bytes": 32074}
V1_RUNTIME_ID = {"sha256": "0e3ef9267b6b719bf574043279731a434e9595520ae8ccf9e930fb9107f505ca", "size_bytes": 98011}
V1_CONTRACT_ID = {"sha256": "3900acae006d7df191fa81a1c7cc28a92402dc5098510809c9d41b3d239cae34", "size_bytes": 92641}
CURRENT_REPORT_ID = {"sha256": "8ec546ed3e3e9992cce543c3c1cb80103edc2f8a1adc2fc496b5f343571a008d", "size_bytes": 85108}
COPY_INPUT_ID = {"sha256": "719aae506df871f87371aa4555204a921363a27174563e95272c320d500ac429", "size_bytes": 1822}
CURRENT_COPY = "provenance/current-policy-evidence.json"
SELECTED_COPY = "provenance/selected-delivery-evidence.json"
COPY_DIRECTORY = "/work/validation/nezha-oem-policy-integration-20260829/delivery-v2-images-v1"
IMAGE_CONTRACT_ID = "nezha-v13i-final-leaf-metadata-delivery-v2"
CURRENT_OPERATION = "verify-v13i-wrapper-policy-equality-with-frozen-v13h-raw-proof-v1"
COPY_OPERATION = "prepare-v13i-policy-delivery-images-v1"
MAIN = b'\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
COPY_SCOPE = {"private_validation_bundle_prepared": True, "selected_guest_images_rehashed": True,
    "current_policy_source_runtime_rehashed": True, **{name: False for name in (
        "source_or_android_output_written", "delivery_images_adopted", "metadata_installed",
        "android_native_tools_executed", "full_vintf_compatibility_verified", "signed_parent_chain_verified",
        "physical_partition_fit_verified", "device_rollback_compatibility_verified", "runtime_verified",
        "phone_accessed", "private_keys_accessed", "complete_rom_ready")}}


def _identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _read_bootstrap(path, wanted=None):
    path = Path(os.path.abspath(path))
    if any(not stat.S_ISDIR(parent.lstat().st_mode) for parent in path.parents):
        raise ValueError("v2 bootstrap requires real parent directories")
    def signature(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2 << 20:
        raise ValueError("v2 bootstrap requires bounded single-link regular code")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        if signature(before) != signature(os.fstat(stream.fileno())):
            raise ValueError("v2 bootstrap source replaced")
        raw = stream.read((2 << 20) + 1)
        if len(raw) > 2 << 20 or signature(before) != signature(os.fstat(stream.fileno())) or signature(before) != signature(path.lstat()):
            raise ValueError("v2 bootstrap source changed")
    if wanted is not None and _identity(raw) != wanted:
        raise ValueError("v2 frozen predecessor identity differs")
    return raw


def _strip_main(raw, wanted):
    if type(raw) is not bytes or _identity(raw) != wanted:
        raise ValueError("v2 predecessor identity differs before main stripping")
    if not raw.endswith(MAIN) or raw.count(MAIN) != 1:
        raise ValueError("v2 predecessor terminal main differs")
    return raw[:-len(MAIN)]


NATIVE = "_V2_PREDECESSOR_PAYLOAD" in globals()
ROOT = Path(os.path.abspath(__file__)).parent.parent if NATIVE else Path(os.path.abspath(__file__)).parents[1]
_v1 = types.ModuleType("_frozen_policy_images_metadata_v1")
_v1.__file__ = str(ROOT / V1_ADAPTER)
if NATIVE:
    _runtime_v1 = _V2_PREDECESSOR_PAYLOAD
    _self_identity = _V2_ADAPTER_IDENTITY
    exec(compile(_strip_main(_runtime_v1, V1_RUNTIME_ID), "<bound-policy-images-v1-runtime>", "exec"), _v1.__dict__)
else:
    _self_identity = _identity(_read_bootstrap(__file__))
    raw_v1 = _read_bootstrap(ROOT / V1_ADAPTER, V1_SOURCE_ID)
    exec(compile(_strip_main(raw_v1, V1_SOURCE_ID), "<bound-policy-images-v1-source>", "exec"), _v1.__dict__)
    predecessor_controls = {name: _read_bootstrap(ROOT / name, ref) for name, ref in _v1.FROZEN.items()}
    predecessor_controls[V1_ADAPTER] = raw_v1
    _runtime_v1 = _v1.runtime_tool_payloads(predecessor_controls)["tools/target_files_metadata.py"]
    _strip_main(_runtime_v1, V1_RUNTIME_ID)

Reader, encoded, identity = _v1.Reader, _v1.encoded, _v1.identity
require, expected, relative = _v1.require, _v1.expected, _v1.relative
TargetFilesMetadataError = _v1.TargetFilesMetadataError
PROFILE, RECEIPT, BUNDLE = _v1.PROFILE, _v1.RECEIPT, _v1.BUNDLE
CONTROL_TOOLS = (*_v1.CONTROL_TOOLS, ADAPTER)


def same(actual, wanted, message):
    require(encoded(actual) == encoded(wanted), message)


def _v1_view(admission):
    require(type(admission) is dict and set(admission) == _v1.ADMISSION_KEYS | {"selected_delivery_evidence"}
            and type(admission["schema_version"]) is int and admission["schema_version"] == 2
            and admission["contract_id"] == IMAGE_CONTRACT_ID, "unknown explicit v2 image admission")
    view = copy.deepcopy(admission)
    view.update(schema_version=1, contract_id=_v1.IMAGE_CONTRACT_ID, current_policy_build_evidence=None)
    del view["selected_delivery_evidence"]
    same(identity(encoded(view)), V1_CONTRACT_ID, "v2 admission changes its frozen v1 image/proof basis")
    return view


def _validate_admission(admission, composition):
    _v1._validate_admission(_v1_view(admission), composition)
    same(admission["current_policy_build_evidence"], CURRENT_REPORT_ID, "exact current-policy evidence identity required")
    same(admission["selected_delivery_evidence"], expected(admission["selected_delivery_evidence"]),
         "actual selected-delivery receipt identity required")


def _validate_proof(raw, admission):
    return _v1._validate_proof(raw, _v1_view(admission))


def _runtime_payloads(controls):
    require(all(name in controls for name in CONTROL_TOOLS), "v2 assembly source controls missing")
    same(identity(controls[V1_ADAPTER]), V1_SOURCE_ID, "policy-images v1 maintained source changed")
    raw_v1 = _v1.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]
    _strip_main(raw_v1, V1_RUNTIME_ID)
    extension = controls[ADAPTER]
    require(type(extension) is bytes and 0 < len(extension) <= 2 << 20, "bounded maintained v2 source required")
    prefix = ("#!/usr/bin/env python3\n# Generated from explicitly admitted maintained metadata sources.\n"
              "_V2_PREDECESSOR_PAYLOAD = " + repr(raw_v1) + "\n"
              "_V2_ADAPTER_IDENTITY = " + repr(identity(extension)) + "\n").encode()
    return {"tools/target_files_metadata.py": prefix + extension}


def _policy_layout(admission):
    inputs = admission["policy_inputs"]["actual_compiler_inputs"]
    framework = []
    for index in (0, 1, 2, 3, 4, 5, 9):
        row = inputs[index]
        partition, suffix = row["runtime_path"].lstrip("/").split("/", 1)
        framework.append({"target_files_path": partition.upper() + "/" + suffix,
                          "compiler_resolved_path": row["resolved_path"], **expected(row, _v1.MAX_PAYLOAD)})
    sidecars = []
    for index, name in enumerate(("plat", "system_ext", "product")):
        path = "/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256"
        pair = [row["target_files_path"] for row in framework[index * 2:index * 2 + 2]]
        prefix = pair[0].split("/", 1)[0]
        sidecars.append({"framework_sidecar_path": prefix + "/etc/selinux/" + name + "_sepolicy_and_mapping.sha256",
                        "ordered_target_files_inputs": pair,
                        "frozen_derived_odm_sidecar_identity": admission["policy_inputs"]["exact_five_replacement_identities"]["odm"][path]})
    return framework, sidecars


def _validate_current(raw, admission, proof):
    same(identity(raw), CURRENT_REPORT_ID, "current-policy report differs from the reviewed record")
    same(identity(raw), admission["current_policy_build_evidence"], "current-policy selection differs")
    current = _v1._factory._json(raw)
    require(type(current.get("schema_version")) is int and current["schema_version"] == 1
            and current.get("operation") == CURRENT_OPERATION
            and current.get("status") == "captured-current-wrapper-policy-identity-equality-verified"
            and current.get("captured_current_wrapper_policy_identity_equality_verified") is True
            and current.get("bound_evidence_rehashed_after_verification") is True
            and type(current.get("requested_goal_count")) is int and current["requested_goal_count"] == 37,
            "reviewed current-wrapper policy equality is required")
    require(type(current.get("scope")) is dict and current["scope"]
            and all(value is False for value in current["scope"].values()), "current-policy record promotes unverified scope")
    same(current["raw_policy_proof"], proof["raw_metadata_proof"], "current-policy and delivery raw-proof linkage differs")
    policy = current["policy_equality"]
    same(policy["actual_compiler_inputs"], admission["policy_inputs"]["actual_compiler_inputs"], "current compiler input identities differ")
    same(expected(policy["selected_factory_combined_binary"]),
         admission["policy_inputs"]["exact_five_replacement_identities"]["odm"]["/etc/selinux/precompiled_sepolicy"],
         "current factory-combined binary differs")
    require(expected(policy["installed_odm_binary_still_distinct"]) != expected(policy["selected_factory_combined_binary"]),
            "source-only binary was substituted for factory-combined policy")
    framework, sidecars = _policy_layout(admission)
    checks = current["future_packaging_checks"]
    same(checks["framework_inputs"], framework, "current-policy framework packaging map differs")
    require(type(checks["sidecars"]) is list and len(checks["sidecars"]) == 3,
            "three framework sidecar checks required")
    for actual, wanted in zip(checks["sidecars"], sidecars):
        same({key: actual[key] for key in wanted}, wanted, "current-policy sidecar recipe differs")
        require(actual["odm_sidecar_tree_projection_required"] is False
                and actual["recomputed_from_actual_packaged_files"] is False,
                "current evidence cannot fabricate packaged sidecars")
    require(checks["opaque_odm_target_files_image"] == "IMAGES/odm.img"
            and checks["odm_selinux_tree_is_not_part_of_the_original_205_member_metadata_projection"] is True
            and checks["artifacts_fabricated"] is False, "opaque ODM metadata boundary differs")
    return current


def _validate_selected(raw, admission, current, proof):
    same(identity(raw), admission["selected_delivery_evidence"], "selected-delivery receipt differs from explicit identity")
    selected = _v1._factory._json(raw)
    keys = {"schema_version", "operation", "status", "passed", "skipped", "input_contract", "controls",
            "output_directory", "selected_copies", "originals", "verified_inputs", "provenance", "disk", "scope"}
    require(set(selected) == keys and type(selected["schema_version"]) is int and selected["schema_version"] == 1
            and selected["operation"] == COPY_OPERATION and selected["status"] == "prepared-private-validation-bundle"
            and selected["passed"] is True and type(selected["skipped"]) is int and selected["skipped"] == 0,
            "actual successful independent-copy receipt required")
    same(selected["input_contract"], COPY_INPUT_ID, "independent-copy input contract differs")
    same(selected["scope"], COPY_SCOPE, "independent-copy scope differs")
    same(selected["controls"], {"current_policy": {"path": "current-policy.json", **CURRENT_REPORT_ID},
         "delivery_proof": {"path": "delivery-proof.json", **admission["delivery_proof"]}}, "independent-copy selected controls differ")
    require(selected["output_directory"] == COPY_DIRECTORY
            and set(selected["selected_copies"]) == set(selected["originals"]) == {"vendor", "odm"},
            "independent-copy output directory or pair differs")
    for role in ("vendor", "odm"):
        row = selected["selected_copies"][role]
        require(set(row) == {"source", "destination", "independent_inode", "source_rehashed_before_and_after", "destination_rehashed_after_copy"}
                and all(row[name] is True for name in ("independent_inode", "source_rehashed_before_and_after", "destination_rehashed_after_copy")),
                "selected image was not independently copied and rehashed")
        same(row["source"], proof["leaf_derivations"][role + "-1"]["image"], "selected production image source differs")
        same(row["destination"], {"path": COPY_DIRECTORY + "/images/" + role + ".img", **admission["packaged_images"][role]},
             "selected copied image identity differs")
        original = selected["originals"][role]
        require(set(original) == {"path", "sha256", "size_bytes", "rehashed_before_and_after"}
                and original["rehashed_before_and_after"] is True, "factory original preservation was not checked")
        require(original["path"] == "/work/evolution/vendor/xiaomi/nezha/proprietary/images/" + role + ".img",
                "factory original source path differs from the reviewed copy input")
        same(expected(original, _v1.MAX_IMAGE), admission["original_images"][role], "factory original identity differs")
    expected_inputs = {"policy": current["policy_equality"]["protected_policy_outputs"],
                       "runtime": current["policy_equality"]["protected_runtime_outputs"],
                       "source": current["current_source_binding"]["source_inventory"]}
    require(set(selected["verified_inputs"]) == set(expected_inputs), "copy input verification roles differ")
    for role, count in (("policy", 13), ("runtime", 11), ("source", 204)):
        row = selected["verified_inputs"][role]
        require(set(row) == {"count", "identities", "rehashed_before_and_after"}
                and type(row["count"]) is int and row["count"] == count
                and row["rehashed_before_and_after"] is True, "copy source/policy/runtime verification differs")
        same(row["identities"], expected_inputs[role], "copy source/policy/runtime identities differ")
    same(selected["provenance"], {"production_receipt": proof["production_receipt"],
         "production_independent_review": proof["production_independent_review"], "raw_metadata_proof": proof["raw_metadata_proof"],
         "source_composition": identity(encoded(admission["source_composition"])),
         "metadata_members": {**identity(encoded(admission["metadata_members"])),
                              "count": len(admission["metadata_members"]),
                              "payload_bytes": sum(row["payload"]["size_bytes"] for row in admission["metadata_members"])}},
         "copy proof-chain provenance differs")
    disk = selected["disk"]
    require(type(disk) is dict and set(disk) == {"copy_bytes", "reserve_bytes", "available_before_bytes", "available_after_bytes"}
            and all(type(value) is int and value >= 0 for value in disk.values())
            and disk["copy_bytes"] == sum(row["size_bytes"] for row in admission["packaged_images"].values())
            and disk["reserve_bytes"] == 1 << 30
            and disk["available_before_bytes"] >= disk["copy_bytes"] + disk["reserve_bytes"]
            and disk["available_after_bytes"] >= disk["reserve_bytes"], "independent-copy disk budget differs")
    return selected


def _validate_evidence(current_raw, selected_raw, admission, proof_raw):
    proof = _validate_proof(proof_raw, admission)
    current = _validate_current(current_raw, admission, proof)
    return current, _validate_selected(selected_raw, admission, current, proof)


def _policy_gate(admission, target, reader, current):
    same(identity(encoded(current)), CURRENT_REPORT_ID, "packaged policy gate lacks the exact current evidence")
    framework, sidecars = _policy_layout(admission)
    actual = {}
    for row in framework:
        path = relative(row["target_files_path"])
        actual[path] = reader.read(target / path, row, maximum=_v1.MAX_PAYLOAD)
    results = []
    for row in sidecars:
        first, second = row["ordered_target_files_inputs"]
        raw = (hashlib.sha256(actual[first] + actual[second]).hexdigest() + "\n").encode("ascii")
        wanted = row["frozen_derived_odm_sidecar_identity"]
        same(identity(raw), wanted, "packaged CIL/mapping digest differs from derived ODM sidecar")
        path = relative(row["framework_sidecar_path"])
        require(reader.read(target / path, wanted) == raw, "actual framework sidecar differs from packaged policy")
        results.append({"path": path, **identity(raw), "ordered_inputs": row["ordered_target_files_inputs"]})
    return {"operation": "verify-actual-packaged-v13i-policy-v2", "framework_inputs": framework, "sidecars": results,
            "current_policy_evidence": admission["current_policy_build_evidence"],
            "selected_delivery_evidence": admission["selected_delivery_evidence"],
            "seven_actual_framework_inputs_verified": True, "three_actual_framework_sidecars_recomputed": True,
            "opaque_odm_sidecars_bound_by_final_image": True, "odm_selinux_tree_projected": False,
            "full_vintf_compatibility_verified": False, "signed_parent_chain_verified": False,
            "physical_partition_fit_verified": False, "runtime_verified": False, "complete_rom_ready": False}


def _installation_report(receipt, digest, reader):
    result = getattr(reader, "current_policy_result", None)
    require(type(result) is dict and result.get("operation") == "verify-actual-packaged-v13i-policy-v2"
            and result.get("seven_actual_framework_inputs_verified") is True
            and result.get("three_actual_framework_sidecars_recomputed") is True,
            "actual packaged policy gate must complete before metadata publication")
    return {"schema_version": 3, "operation": "project-policy-image-target-files-metadata-v2",
            "bundle_receipt_sha256": digest, **{name: receipt[name] for name in (
                "profile", "images", "packaged_images", "files", "property_closure", "source_composition",
                "image_admission", "original_receipt", "delivery_proof", "current_policy_evidence", "selected_delivery_evidence", "scope")},
            "packaged_policy_checks": result, "complete_rom_ready": False}


# Only these counted substitutions alter the admitted v1 function definitions.
TRANSFORMS = {
    "_controls": [("controls.update({ADAPTER: adapter, IMAGE_CONTRACT: raw})",
        "controls.update({ADAPTER: adapter, IMAGE_CONTRACT: raw,\n"
        "        V1_ADAPTER: reader.read(root / V1_ADAPTER, V1_SOURCE_ID),\n"
        "        V1_CONTRACT: reader.read(root / V1_CONTRACT, V1_CONTRACT_ID)})")],
    "_payloads": [("def _payloads(files, provenance, controls, original, proof):",
        "def _payloads(files, provenance, controls, original, proof, current_raw, selected_raw):"),
        ("payloads.update({ORIGINAL_COPY: original, PROOF_COPY: proof})",
         "require(CURRENT_COPY not in payloads and SELECTED_COPY not in payloads, 'v2 evidence provenance collision')\n"
         "    payloads.update({ORIGINAL_COPY: original, PROOF_COPY: proof, CURRENT_COPY: current_raw, SELECTED_COPY: selected_raw})")],
    "_receipt": [("\"schema_version\": 2", "\"schema_version\": 3"),
        ('"delivery_proof": {"path": PROOF_COPY, **admission["delivery_proof"]},',
         '"delivery_proof": {"path": PROOF_COPY, **admission["delivery_proof"]},\n'
         '            "current_policy_evidence": {"path": CURRENT_COPY, **admission["current_policy_build_evidence"]},\n'
         '            "selected_delivery_evidence": {"path": SELECTED_COPY, **admission["selected_delivery_evidence"]},')],
    "stage_from_original": [("image_contract, delivery_proof, controls_root=None):",
        "image_contract, delivery_proof, current_policy_evidence, selected_delivery_evidence, controls_root=None):"),
        ("_validate_proof(proof, admission)",
         "current_raw = reader.read(current_policy_evidence, admission['current_policy_build_evidence'])\n"
         "    selected_raw = reader.read(selected_delivery_evidence, admission['selected_delivery_evidence'])\n"
         "    _validate_evidence(current_raw, selected_raw, admission, proof)"),
        ("_payloads(files, provenance, controls, original, proof)", "_payloads(files, provenance, controls, original, proof, current_raw, selected_raw)")],
    "verify_bundle": [("source_tree=None, vendor_image=None, odm_image=None, target_files=None):",
        "source_tree=None, vendor_image=None, odm_image=None, target_files=None, current_policy_evidence=None, selected_delivery_evidence=None):"),
        ('receipt["schema_version"] == 2', 'receipt["schema_version"] == 3'),
        ("_validate_proof(proof, admission)",
         "require(CURRENT_COPY in mapping and SELECTED_COPY in mapping, 'v2 evidence provenance missing')\n"
         "    current_raw, selected_raw = mapping[CURRENT_COPY], mapping[SELECTED_COPY]\n"
         "    current_record, selected_record = _validate_evidence(current_raw, selected_raw, admission, proof)\n"
         "    for path, raw_bytes, ref in ((current_policy_evidence, current_raw, admission['current_policy_build_evidence']),\n"
         "                                 (selected_delivery_evidence, selected_raw, admission['selected_delivery_evidence'])):\n"
         "        if path is not None:\n"
         "            require(reader.read(path, ref) == raw_bytes, 'external v2 evidence differs from copied provenance')"),
        ("_payloads(files, provenance, controls, original, proof)", "_payloads(files, provenance, controls, original, proof, current_raw, selected_raw)"),
        ("_current_policy_gate(admission, target, reader)", "reader.current_policy_result = _current_policy_gate(admission, target, reader, current_record)")],
    "_selected_image_contract": [('receipt["schema_version"] == 2', 'receipt["schema_version"] == 3')],
    "main": [('("original-bundle", "output", "source-contract", "image-contract", "delivery-proof")',
              '("original-bundle", "output", "source-contract", "image-contract", "delivery-proof", "current-policy-evidence", "selected-delivery-evidence")'),
             ('("source-tree", "vendor-image", "odm-image", "target-files")',
              '("source-tree", "vendor-image", "odm-image", "target-files", "current-policy-evidence", "selected-delivery-evidence")'),
             ("image_contract=args.image_contract, delivery_proof=args.delivery_proof, controls_root=args.controls_root)",
              "image_contract=args.image_contract, delivery_proof=args.delivery_proof, controls_root=args.controls_root,\n"
              "                current_policy_evidence=args.current_policy_evidence, selected_delivery_evidence=args.selected_delivery_evidence)"),
             ("target_files=args.target_files)", "target_files=args.target_files, current_policy_evidence=args.current_policy_evidence, selected_delivery_evidence=args.selected_delivery_evidence)"),
             ('"current_policy_build_verified": False, "images_adopted": False',
              '"current_policy_equality_evidence_verified": True, "packaged_framework_policy_verified": args.target_files is not None, "images_adopted": False')],
    "selection": [("current policy adoption remains blocked", "actual packaged policy and image checks required at install")],
}


def _function_definitions(raw):
    source = _strip_main(raw, V1_RUNTIME_ID).decode("utf-8")
    output = []
    seen = set()
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        require(node.name not in seen, "duplicate frozen v1 function")
        seen.add(node.name)
        text = ast.get_source_segment(source, node) + "\n"
        for before, after in TRANSFORMS.get(node.name, ()):
            require(text.count(before) == 1, "frozen v1 transform preimage differs: " + node.name)
            text = text.replace(before, after)
        output.append(text)
    require(set(TRANSFORMS).issubset(seen), "frozen v1 function transform missing")
    return "\n".join(output)


_impl = dict(_v1.__dict__)
_impl.update(ROOT=ROOT, NATIVE=NATIVE, HERE=HERE, ADAPTER=ADAPTER, IMAGE_CONTRACT=IMAGE_CONTRACT,
    __doc__="Explicit metadata delivery using reviewed current-policy and independent-copy evidence. "
            "Native installation additionally verifies actual packaged policy, sidecars, images and source guards.",
    IMAGE_CONTRACT_ID=IMAGE_CONTRACT_ID, _self_identity=_self_identity,
    STAGE_OPERATION="stage-policy-image-target-files-metadata-v2", CONTROL_TOOLS=CONTROL_TOOLS,
    RECEIPT_KEYS=_v1.RECEIPT_KEYS | {"current_policy_evidence", "selected_delivery_evidence"},
    V1_ADAPTER=V1_ADAPTER, V1_CONTRACT=V1_CONTRACT, V1_SOURCE_ID=V1_SOURCE_ID, V1_CONTRACT_ID=V1_CONTRACT_ID,
    CURRENT_COPY=CURRENT_COPY, SELECTED_COPY=SELECTED_COPY)
exec(compile(_function_definitions(_runtime_v1), "<explicit-v2-functions-from-frozen-v1>", "exec"), _impl)
_impl.update(_validate_admission=_validate_admission, _validate_proof=_validate_proof,
             runtime_tool_payloads=_runtime_payloads, _validate_evidence=_validate_evidence,
             _current_policy_gate=_policy_gate, _installation_report=_installation_report)
_install_source = _v1._installation_source(_v1._predecessor_raw)
_report_call = "report = _delivery_installation_report(receipt, expected_receipt)"
require(_install_source.count(_report_call) == 1, "v1 install report callback boundary differs")
_install_source = _install_source.replace(_report_call, "report = _delivery_installation_report(receipt, expected_receipt, reader)")
_install_namespace = dict(_v1._factory.__dict__)
_install_namespace.update(verify_bundle=_impl["_install_verify"], _delivery_installation_report=_installation_report)
exec(compile(_install_source, "<exact-v2-install-report-plumbing>", "exec"), _install_namespace)
_impl.update(_install_namespace=_install_namespace, _install_impl=_install_namespace["install"])
for _name in ("stage_from_original", "verify_bundle", "install", "selection", "compose_sources", "_controls", "main"):
    globals()[_name] = _impl[_name]
runtime_tool_payloads = _runtime_payloads
_files = _v1._factory._files


if __name__ == "__main__":
    raise SystemExit(main())
