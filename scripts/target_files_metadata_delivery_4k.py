#!/usr/bin/env python3
"""Explicit 4 KiB successor of the frozen Nezha metadata delivery consumer.

Historical image, policy and copy records keep their original identities.
The successor requires a separately reviewed actual current 4 KiB policy
record; an unfinished native build cannot qualify this mode.
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
ADAPTER = "scripts/target_files_metadata_delivery_4k.py"
IMAGE_CONTRACT = "config/nezha-policy-image-delivery-v2.json"
BASIS_CONTRACT = "config/nezha-policy-image-delivery-basis-v2.json"
V2_ADAPTER = "scripts/target_files_metadata_delivery.py"
V2_CONTRACT = "config/nezha-policy-image-delivery.json"
V2_SOURCE_ID = {"sha256": "2d9d4a51eda659523fd64d39de914fa8294d9480f20c46688736295467508144", "size_bytes": 27341}
V2_RUNTIME_ID = {"sha256": "bf5197bcb231153ddc0cb68d7d293e4848db188ec0bbc9192255e38a5010350b", "size_bytes": 127425}
V2_CONTRACT_ID = {"sha256": "a6883fd115c75336fc9152b0f38549d5e40706d45e7a2d88da1dfe8b246dbc02", "size_bytes": 92893}
BASIS_ID = {"sha256": "ad7c2a705d085a98af4e264f4ce429c9825b9cd6faee52a57a2eda0872ed67fa", "size_bytes": 93636}
HISTORICAL_CURRENT_ID = {"sha256": "8ec546ed3e3e9992cce543c3c1cb80103edc2f8a1adc2fc496b5f343571a008d", "size_bytes": 85108}
HISTORICAL_COPY = "provenance/historical-v13i-policy-evidence.json"
IMAGE_CONTRACT_ID = "nezha-4k-final-leaf-metadata-delivery-v3"
BASIS_CONTRACT_ID = "nezha-4k-final-leaf-metadata-basis-v2"
STAGE_OPERATION = "stage-policy-image-target-files-metadata-4k-v3"
# Actual completed 37-goal result, independently read back with its source,
# settings and protected-output evidence. It proves scoped component checks.
CURRENT_REPORT_ID = {"sha256": "949bd0882087d403637e542a0bc82c37b4ecabc8196ba0c160fe8a3ddd46e145", "size_bytes": 206610}
INSTALLATION_IDS = {
    "profile": {"sha256": "832ce4c8ab50415caad30120bc3c0b06e412272482df57ab70dd6b8f42c239dd", "size_bytes": 172678},
    "manifest": {"sha256": "41e29d298d1217176e31098674bd6026b92825ee690eec0ebf0ef67344bf79ca", "size_bytes": 110578},
    "installation": {"sha256": "0c477a6a405fec0f3a282fcdf3f1fb726ba0fd2bee69b9c5cb8dd03ae72f109a", "size_bytes": 74664},
    "journal": {"sha256": "26dbbec24fb165541072a2645a4c929bf05a05d00336d7f6ae10865267d08db9", "size_bytes": 9083},
    "commit": {"sha256": "64088a158bec3820c454dde8660f9e37add746a026a620de2306b3d8c461202b", "size_bytes": 536},
}
SETTINGS_IDS = {
    "before": {"sha256": "b015597e8302969947d1ada72b0476cd14060d57bcace7b3bcff2a71760b6172", "size_bytes": 340603},
    "after": {"sha256": "b0e9e56381a74a981b8e8754d5da0b7dbb420c8f052e9647faf031b687494ecb", "size_bytes": 340602},
}
PAGE_CONTEXT = {
    "profile": {"path": "config/nezha-page-size-profile-v2.json", "sha256": "bed228b0595ef2dc1dd814e98c0966ba9b9452b542de50354db522e2420bed1e", "size_bytes": 15567},
    "profile_id": "nezha-stock-4k-bringup-v2",
    "source_candidate": {"sha256": "392485b8ef5005f6d8079487c7a8ee7931597bacaab593478277f8201c4d03a2", "size_bytes": 127103},
    "source_product": {"path": "device/xiaomi/nezha/generated/device-candidate.mk", "sha256": "d336169a8f683bd798bb63360fbc62ee9ebdc03343e2f7ab91906052cde568a9", "size_bytes": 1661},
    "product_settings": {"PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE": True, "PRODUCT_MAX_PAGE_SIZE_SUPPORTED": 4096, "PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO": True},
}
MAIN = b'\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


def _identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _read_bootstrap(path, wanted=None):
    path = Path(os.path.abspath(path))
    if any(not stat.S_ISDIR(parent.lstat().st_mode) for parent in path.parents):
        raise ValueError("4 KiB bootstrap requires real parent directories")
    def signature(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2 << 20:
        raise ValueError("4 KiB bootstrap requires bounded single-link regular code")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        if signature(before) != signature(os.fstat(stream.fileno())):
            raise ValueError("4 KiB bootstrap source replaced")
        raw = stream.read((2 << 20) + 1)
        if len(raw) > 2 << 20 or signature(before) != signature(os.fstat(stream.fileno())) or signature(before) != signature(path.lstat()):
            raise ValueError("4 KiB bootstrap source changed")
    if wanted is not None and _identity(raw) != wanted:
        raise ValueError("4 KiB frozen predecessor identity differs")
    return raw


def _strip_main(raw, wanted):
    if type(raw) is not bytes or _identity(raw) != wanted:
        raise ValueError("4 KiB predecessor identity differs before main stripping")
    if not raw.endswith(MAIN) or raw.count(MAIN) != 1:
        raise ValueError("4 KiB predecessor terminal main differs")
    return raw[:-len(MAIN)]


NATIVE = "_FOURK_PREDECESSOR_PAYLOAD" in globals()
ROOT = Path(os.path.abspath(__file__)).parent.parent if NATIVE else Path(os.path.abspath(__file__)).parents[1]
_v2 = types.ModuleType("_frozen_metadata_delivery_v2")
_v2.__file__ = str(ROOT / V2_ADAPTER)
if NATIVE:
    _runtime_v2 = _FOURK_PREDECESSOR_PAYLOAD
    _self_identity = _FOURK_ADAPTER_IDENTITY
    exec(compile(_strip_main(_runtime_v2, V2_RUNTIME_ID), "<bound-delivery-v2-runtime>", "exec"), _v2.__dict__)
else:
    _self_identity = _identity(_read_bootstrap(__file__))
    raw_v2 = _read_bootstrap(ROOT / V2_ADAPTER, V2_SOURCE_ID)
    exec(compile(_strip_main(raw_v2, V2_SOURCE_ID), "<bound-delivery-v2-source>", "exec"), _v2.__dict__)
    predecessor_controls = {name: _read_bootstrap(ROOT / name) for name in _v2.CONTROL_TOOLS}
    _runtime_v2 = _v2.runtime_tool_payloads(predecessor_controls)["tools/target_files_metadata.py"]
    _strip_main(_runtime_v2, V2_RUNTIME_ID)

Reader, encoded, identity = _v2.Reader, _v2.encoded, _v2.identity
require, expected, relative, same = _v2.require, _v2.expected, _v2.relative, _v2.same
TargetFilesMetadataError = _v2.TargetFilesMetadataError
PROFILE, RECEIPT, BUNDLE = _v2.PROFILE, _v2.RECEIPT, _v2.BUNDLE
CONTROL_TOOLS = (*_v2.CONTROL_TOOLS, ADAPTER)


def _basis_view(admission):
    require(type(admission) is dict and set(admission) == _v2._v1.ADMISSION_KEYS | {
        "selected_delivery_evidence", "historical_current_policy_evidence", "historical_delivery_admission", "page_size_context"}
        and type(admission["schema_version"]) is int and admission["schema_version"] == 3
        and admission["contract_id"] == IMAGE_CONTRACT_ID, "unknown explicit 4 KiB image admission")
    view = copy.deepcopy(admission)
    view.update(schema_version=2, contract_id=BASIS_CONTRACT_ID, current_policy_build_evidence=None)
    del view["selected_delivery_evidence"], view["historical_current_policy_evidence"]
    same(identity(encoded(view)), BASIS_ID, "4 KiB admission changes its reviewed page/image basis")
    return view


def _historical_view(admission):
    _basis_view(admission)
    view = copy.deepcopy(admission)
    for key in ("historical_current_policy_evidence", "historical_delivery_admission", "page_size_context"):
        del view[key]
    view.update(schema_version=2, contract_id=_v2.IMAGE_CONTRACT_ID, current_policy_build_evidence=HISTORICAL_CURRENT_ID)
    same(identity(encoded(view)), V2_CONTRACT_ID, "4 KiB admission changes historical images, metadata, source or copy provenance")
    return view


def _validate_admission(admission, composition):
    _v2._validate_admission(_historical_view(admission), composition)
    same(admission["page_size_context"], PAGE_CONTEXT, "exact current-provider 4 KiB context required")
    same(admission["historical_current_policy_evidence"], HISTORICAL_CURRENT_ID, "historical current-policy identity differs")
    same(admission["historical_delivery_admission"], {"path": V2_CONTRACT, **V2_CONTRACT_ID}, "historical delivery identity differs")
    require(CURRENT_REPORT_ID is not None, "actual completed 4 KiB policy equality is not yet bound")
    same(admission["current_policy_build_evidence"], CURRENT_REPORT_ID, "actual current 4 KiB policy identity differs")


def _validate_proof(raw, admission):
    return _v2._validate_proof(raw, _historical_view(admission))


def _validate_current_fields(current, admission, historical):
    require(type(current) is dict and type(current.get("schema_version")) is int and current["schema_version"] == 1
            and current.get("operation") == "build-post-v13j-4k-framework-components"
            and current.get("phase") == "pagesize-v13j-1", "actual selected 4 KiB component result required")
    same([current["target_product"], current["target_release"], current["variant"]],
         ["lineage_nezha", "bp4a", "user"], "4 KiB product selection differs")
    same(current["goals"], historical["goals"], "exact historical 37 ordinary component goals required")
    require(len(current["goals"]) == 37 and type(current["exit_code"]) is int and current["exit_code"] == 0
            and current["build_passed"] is True and current["native_component_build_passed"] is True
            and current["build_passed_scope"] == "native-37-goal-component-build-only"
            and current["timed_out"] is False and current["forced_kill_after_timeout"] is False
            and current["remaining_build_processes"] == [] and current["post_build_error"] is None
            and current["sandbox_fallback"] is False and current["ninja_argv_verified"] is True
            and current["ninja_argv_error"] is None, "native component build did not complete its scoped checks")
    require(current["sandbox"]["namespace_and_mount_checks_passed"] is True
            and current["sandbox"]["source_readonly_output_writable"] is True
            and current["native_settings_transition_verified"] is True
            and current["page_size_profile_selected"] is True
            and type(current["selected_max_page_size"]) is int and current["selected_max_page_size"] == 4096,
            "native source/settings observation differs")
    for role, maximum in (("before", "16384"), ("after", "4096")):
        same(current["strict_settings_" + role], {
            "settings": {"path": "/work/out/nezha-user-policy-20260827T2220Z/soong/soong.lineage_nezha.variables", **SETTINGS_IDS[role]},
            "max_page_size": maximum, "strict_soong_elf_checks_selected": True,
            "prebuilt_max_page_size_check": True, "no_bionic_page_size_macro": True,
            "checker_actions_verified": False}, "actual strict page-size settings differ")
    same(current["page_size_transition"], {"verified": True, "before_max_page_size": 16384,
         "after_max_page_size": 4096, "prebuilt_max_page_size_check": True,
         "no_bionic_page_size_macro_unchanged": True, "strict_soong_elf_checks_selected": True,
         "checker_actions_verified": False, "vsr_16k_compatibility_verified": False},
         "actual 4 KiB transition or evidence scope differs")
    history = current["source_history_proof"]
    require(history["verified"] is True and history["operation"] == "verify-v13j-pagesize-sources-after-build"
            and history["base"] == "/work/candidates/nezha-stock-4k-v13ja"
            and type(history["source_files_checked"]) is int and history["source_files_checked"] == 204
            and history["max_page_size_supported"] == 4096 and history["normal_android_enforcing_required"] is True,
            "actual installed 4 KiB source evidence differs")
    for field, role in (("profile_identity", "profile"), ("manifest_identity", "manifest")):
        same(history[field], INSTALLATION_IDS[role], "installed source context differs")
        same(current["bindings"][field], INSTALLATION_IDS[role], "native build installation context differs")
    same(history["actual_commit_canonical_identity"], INSTALLATION_IDS["commit"], "actual installation commit differs")
    require(history["actual_commit"]["verified"] is True, "actual installation was not committed")
    for role in ("installation", "journal"):
        same(history["actual_commit"][role], INSTALLATION_IDS[role], "installation transaction identity differs")
        same(expected(history["records"][role]), INSTALLATION_IDS[role], "installation history record differs")
    rows = copy.deepcopy(historical["current_source_binding"]["source_inventory"])
    product = admission["page_size_context"]["source_product"]
    path = "/work/evolution/" + product["path"]
    require(sum(row["path"] == path for row in rows) == 1, "historical product source is missing or duplicated")
    rows = [{"path": path, **expected(product)} if row["path"] == path else row for row in rows]
    same(history["source_inventory"], rows, "actual current source differs beyond the exact 4 KiB product change")
    same(history["source_inventory_identity"], identity(encoded(rows)), "current source inventory identity differs")
    same(expected(current["source_manifest"]), identity(encoded(rows)), "native source manifest differs from current inventory")
    same(history["source_projects"], history["predecessor_history"]["source_projects"], "upstream revision or reviewed source changes differ")
    same(current["protected_policy_outputs"], historical["policy_equality"]["protected_policy_outputs"],
         "actual 13 policy input/binary identities differ from the image basis")
    same(current["protected_runtime_outputs"], historical["policy_equality"]["protected_runtime_outputs"],
         "actual 11 protected runtime identities differ")
    require(current["prior_policy_analysis_reused"] is True, "reviewed native policy analysis linkage missing")
    for name in ("fresh_policy_compiler_actions_verified", "policy_outputs_invalidated_or_moved",
                 "metadata_source_selected", "vsr_16k_compatibility_verified", "full_vendor_kernel_apex_compatibility_executed",
                 "compatibility_verified", "allocator_runtime_registration_verified", "apex_cryptographic_validation_performed",
                 "provider_elf_compatibility_verified", "provider_runtime_requested", "strict_provider_elf_actions_verified",
                 "images_requested", "complete_rom_ready", "phone_accessed"):
        require(current[name] is False, "4 KiB result promotes unverified scope: " + name)
    return current


def _validate_current(raw, admission, proof, historical):
    require(CURRENT_REPORT_ID is not None, "actual completed 4 KiB policy equality is not yet bound")
    same(identity(raw), CURRENT_REPORT_ID, "actual current 4 KiB policy report differs")
    same(identity(raw), admission["current_policy_build_evidence"], "4 KiB current-policy selection differs")
    same(historical["raw_policy_proof"], proof["raw_metadata_proof"], "historical raw-policy link differs")
    return _validate_current_fields(_v2._v1._factory._json(raw), admission, historical)


def _validate_evidence(current_raw, selected_raw, admission, proof_raw, historical_raw):
    proof = _validate_proof(proof_raw, admission)
    same(identity(historical_raw), HISTORICAL_CURRENT_ID, "historical v13i evidence changed")
    historical, selected = _v2._validate_evidence(historical_raw, selected_raw, _historical_view(admission), proof_raw)
    current = _validate_current(current_raw, admission, proof, historical)
    return current, selected


def _runtime_payloads(controls):
    require(all(name in controls for name in CONTROL_TOOLS), "4 KiB assembly source controls missing")
    same(identity(controls[V2_ADAPTER]), V2_SOURCE_ID, "maintained v2 source changed")
    raw_v2 = _v2.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]
    _strip_main(raw_v2, V2_RUNTIME_ID)
    extension = controls[ADAPTER]
    require(type(extension) is bytes and 0 < len(extension) <= 2 << 20, "bounded maintained 4 KiB source required")
    prefix = ("#!/usr/bin/env python3\n# Generated from explicitly admitted maintained metadata sources.\n"
              "_FOURK_PREDECESSOR_PAYLOAD = " + repr(raw_v2) + "\n"
              "_FOURK_ADAPTER_IDENTITY = " + repr(identity(extension)) + "\n").encode()
    return {"tools/target_files_metadata.py": prefix + extension}


def _policy_gate(admission, target, reader, current):
    require(CURRENT_REPORT_ID is not None, "actual completed 4 KiB policy equality is not yet bound")
    same(identity(encoded(current)), CURRENT_REPORT_ID, "packaged policy lacks exact current 4 KiB evidence")
    require(getattr(reader, "fourk_product_verified", False) is True, "actual 4 KiB product source must be verified")
    framework, sidecars = _v2._policy_layout(admission)
    actual = {}
    for row in framework:
        path = relative(row["target_files_path"])
        actual[path] = reader.read(target / path, row, maximum=_v2._v1.MAX_PAYLOAD)
    results = []
    for row in sidecars:
        first, second = row["ordered_target_files_inputs"]
        raw = (hashlib.sha256(actual[first] + actual[second]).hexdigest() + "\n").encode("ascii")
        wanted = row["frozen_derived_odm_sidecar_identity"]
        same(identity(raw), wanted, "packaged CIL/mapping digest differs from derived ODM sidecar")
        path = relative(row["framework_sidecar_path"])
        require(reader.read(target / path, wanted) == raw, "actual framework sidecar differs from packaged policy")
        results.append({"path": path, **identity(raw), "ordered_inputs": row["ordered_target_files_inputs"]})
    return {"operation": "verify-actual-packaged-4k-policy-v3", "framework_inputs": framework, "sidecars": results,
        "current_policy_evidence": admission["current_policy_build_evidence"],
        "historical_current_policy_evidence": admission["historical_current_policy_evidence"],
        "selected_delivery_evidence": admission["selected_delivery_evidence"], "page_size_context": PAGE_CONTEXT,
        "seven_actual_framework_inputs_verified": True, "three_actual_framework_sidecars_recomputed": True,
        "actual_fourk_product_source_verified": True,
        "opaque_odm_sidecars_bound_by_final_image": True, "odm_selinux_tree_projected": False,
        "full_vintf_compatibility_verified": False, "signed_parent_chain_verified": False,
        "physical_partition_fit_verified": False, "runtime_verified": False, "complete_rom_ready": False}


def _installation_report(receipt, digest, reader):
    result = getattr(reader, "current_policy_result", None)
    require(type(result) is dict and result.get("operation") == "verify-actual-packaged-4k-policy-v3"
            and result.get("seven_actual_framework_inputs_verified") is True
            and result.get("three_actual_framework_sidecars_recomputed") is True
            and result.get("actual_fourk_product_source_verified") is True,
            "actual packaged policy gate must complete before metadata publication")
    return {"schema_version": 4, "operation": "project-policy-image-target-files-metadata-4k-v3",
        "bundle_receipt_sha256": digest, **{name: receipt[name] for name in (
            "profile", "images", "packaged_images", "files", "property_closure", "source_composition",
            "image_admission", "original_receipt", "delivery_proof", "current_policy_evidence", "selected_delivery_evidence",
            "historical_current_policy_evidence", "page_size_context", "scope")},
        "packaged_policy_checks": result, "complete_rom_ready": False}


# The predecessor emits these definitions from its exact frozen runtime. Each
# replacement is counted once; its original evidence and file checks survive.
TRANSFORMS = {
    "_controls": [("V1_CONTRACT: reader.read(root / V1_CONTRACT, V1_CONTRACT_ID)})",
        "V1_CONTRACT: reader.read(root / V1_CONTRACT, V1_CONTRACT_ID),\n"
        "        V2_ADAPTER: reader.read(root / V2_ADAPTER, V2_SOURCE_ID),\n"
        "        V2_CONTRACT: reader.read(root / V2_CONTRACT, V2_CONTRACT_ID),\n"
        "        BASIS_CONTRACT: reader.read(root / BASIS_CONTRACT, BASIS_ID),\n"
        "        PAGE_CONTEXT['profile']['path']: reader.read(root / PAGE_CONTEXT['profile']['path'], PAGE_CONTEXT['profile'])})")],
    "_payloads": [("proof, current_raw, selected_raw):", "proof, current_raw, selected_raw, historical_raw):"),
        ("payloads.update({ORIGINAL_COPY: original, PROOF_COPY: proof, CURRENT_COPY: current_raw, SELECTED_COPY: selected_raw})",
         "require(HISTORICAL_COPY not in payloads, '4 KiB historical evidence collision')\n"
         "    payloads.update({ORIGINAL_COPY: original, PROOF_COPY: proof, CURRENT_COPY: current_raw, SELECTED_COPY: selected_raw, HISTORICAL_COPY: historical_raw})")],
    "_receipt": [('"schema_version": 3', '"schema_version": 4'),
        ('"selected_delivery_evidence": {"path": SELECTED_COPY, **admission["selected_delivery_evidence"]},',
         '"selected_delivery_evidence": {"path": SELECTED_COPY, **admission["selected_delivery_evidence"]},\n'
         '            "historical_current_policy_evidence": {"path": HISTORICAL_COPY, **admission["historical_current_policy_evidence"]},\n'
         '            "page_size_context": copy.deepcopy(admission["page_size_context"]),')],
    "stage_from_original": [("selected_delivery_evidence, controls_root=None):", "selected_delivery_evidence, historical_policy_evidence, controls_root=None):"),
        ("_validate_evidence(current_raw, selected_raw, admission, proof)",
         "historical_raw = reader.read(historical_policy_evidence, admission['historical_current_policy_evidence'])\n"
         "    _validate_evidence(current_raw, selected_raw, admission, proof, historical_raw)"),
        ("_payloads(files, provenance, controls, original, proof, current_raw, selected_raw)",
         "_payloads(files, provenance, controls, original, proof, current_raw, selected_raw, historical_raw)")],
    "verify_bundle": [("selected_delivery_evidence=None):", "selected_delivery_evidence=None, historical_policy_evidence=None):"),
        ('receipt["schema_version"] == 3', 'receipt["schema_version"] == 4'),
        ("_factory._check_source(source_tree, composition, reader)",
         "_factory._check_source(source_tree, composition, reader)\n"
         "        product = admission['page_size_context']['source_product']\n"
         "        reader.read(_factory.real_directory(source_tree) / relative(product['path']), product)\n"
         "        reader.fourk_product_verified = True"),
        ("current_record, selected_record = _validate_evidence(current_raw, selected_raw, admission, proof)",
         "require(HISTORICAL_COPY in mapping, 'historical current-policy evidence missing')\n"
         "    historical_raw = mapping[HISTORICAL_COPY]\n"
         "    if historical_policy_evidence is not None:\n"
         "        require(reader.read(historical_policy_evidence, admission['historical_current_policy_evidence']) == historical_raw, 'historical evidence differs from copied provenance')\n"
         "    current_record, selected_record = _validate_evidence(current_raw, selected_raw, admission, proof, historical_raw)"),
        ("_payloads(files, provenance, controls, original, proof, current_raw, selected_raw)",
         "_payloads(files, provenance, controls, original, proof, current_raw, selected_raw, historical_raw)")],
    "_selected_image_contract": [('receipt["schema_version"] == 3', 'receipt["schema_version"] == 4')],
    "main": [('"delivery-proof", "current-policy-evidence", "selected-delivery-evidence")',
              '"delivery-proof", "current-policy-evidence", "selected-delivery-evidence", "historical-policy-evidence")'),
             ('"target-files", "current-policy-evidence", "selected-delivery-evidence")',
              '"target-files", "current-policy-evidence", "selected-delivery-evidence", "historical-policy-evidence")'),
             ("selected_delivery_evidence=args.selected_delivery_evidence)",
              "selected_delivery_evidence=args.selected_delivery_evidence, historical_policy_evidence=args.historical_policy_evidence)")],
}


def _function_definitions():
    source = _v2._function_definitions(_v2._runtime_v1)
    output, seen = [], set()
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef):
            continue
        require(node.name not in seen, "duplicate frozen v2 function")
        seen.add(node.name)
        text = ast.get_source_segment(source, node) + "\n"
        for before, after in TRANSFORMS.get(node.name, ()):
            wanted = 2 if node.name == "main" and before.startswith("selected_delivery_evidence=") else 1
            require(text.count(before) == wanted, "frozen v2 transform preimage differs: " + node.name)
            text = text.replace(before, after)
        output.append(text)
    require(set(TRANSFORMS).issubset(seen), "frozen v2 function transform missing")
    return "\n".join(output)


_impl = dict(_v2._impl)
_impl.update(ROOT=ROOT, NATIVE=NATIVE, ADAPTER=ADAPTER, IMAGE_CONTRACT=IMAGE_CONTRACT,
    __doc__=__doc__, IMAGE_CONTRACT_ID=IMAGE_CONTRACT_ID, _self_identity=_self_identity,
    STAGE_OPERATION=STAGE_OPERATION, CONTROL_TOOLS=CONTROL_TOOLS,
    RECEIPT_KEYS=_v2._impl["RECEIPT_KEYS"] | {"historical_current_policy_evidence", "page_size_context"},
    V2_ADAPTER=V2_ADAPTER, V2_CONTRACT=V2_CONTRACT, V2_SOURCE_ID=V2_SOURCE_ID, V2_CONTRACT_ID=V2_CONTRACT_ID,
    BASIS_CONTRACT=BASIS_CONTRACT, BASIS_ID=BASIS_ID, PAGE_CONTEXT=PAGE_CONTEXT, HISTORICAL_COPY=HISTORICAL_COPY)
exec(compile(_function_definitions(), "<explicit-4k-functions-from-frozen-v2>", "exec"), _impl)
_impl.update(_validate_admission=_validate_admission, _validate_proof=_validate_proof,
    runtime_tool_payloads=_runtime_payloads, _validate_evidence=_validate_evidence,
    _current_policy_gate=_policy_gate, _installation_report=_installation_report)
_install_namespace = dict(_v2._v1._factory.__dict__)
_install_namespace.update(verify_bundle=_impl["_install_verify"], _delivery_installation_report=_installation_report)
exec(compile(_v2._install_source, "<unchanged-v2-install-with-explicit-4k-report>", "exec"), _install_namespace)
_impl.update(_install_namespace=_install_namespace, _install_impl=_install_namespace["install"])
for _name in ("stage_from_original", "verify_bundle", "install", "selection", "compose_sources", "_controls", "main"):
    globals()[_name] = _impl[_name]
runtime_tool_payloads = _runtime_payloads
_files = _v2._files


if __name__ == "__main__":
    raise SystemExit(main())
