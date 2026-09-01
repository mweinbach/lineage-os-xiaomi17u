#!/usr/bin/env python3
"""Explicit policy3 image delivery; pending descriptors cannot select this mode.

The five historical consumers remain immutable. This adapter reuses their
metadata projection and atomic installer, changing only the closed evidence
selection and its policy3 checks. It never builds, signs, or copies an image.
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
ADAPTER = "scripts/target_files_metadata_delivery_policy3.py"
IMAGE_CONTRACT = "config/nezha-policy-image-delivery-policy3.json"
IMAGE_CONTRACT_ID = "nezha-policy3-final-leaf-metadata-delivery-v1"
# Exact actual raw/footer/copy proofs and the independently rendered product.
# Historical adapters and their default selection remain unchanged.
IMAGE_CONTRACT_IDENTITY = {"sha256": "1c0548bccc990794fab45ffa15b6159d9c4294ac2dde9f4b202e437844bdc5c1", "size_bytes": 240384}
PREDECESSOR = "scripts/target_files_metadata_delivery_4k.py"
PREDECESSOR_ID = {"sha256": "735732de59ac095832528fc5e99562527246cfaf1bc478d3ddc1f0a3ae996c56", "size_bytes": 26635}
PREDECESSOR_RUNTIME_ID = {"sha256": "667e3626bc068e3ebba7096321f210e5a3a91363a6c5b4fc2219b46850a45405", "size_bytes": 157922}
POLICY_PROFILE = "config/nezha-policy-images.json"
POLICY_PROFILE_ID = {"sha256": "878ab8f5e6aba3ccc343771dc964d263d6784912ab8cacb50529e2900593137b", "size_bytes": 61326}
CURRENT_REPORT_ID = {"sha256": "344ba909febe8be29479f5bf1d48d122e931e88fb1d4d71dbcdab08708483c18", "size_bytes": 10165316}
CURRENT_MAXIMUM = 16 << 20
STAGE_OPERATION = "stage-policy3-image-target-files-metadata-v1"
PROOF_OPERATION = "verify-policy3-final-leaf-metadata-delivery-v1"
COPY_OPERATION = "prepare-policy3-policy-delivery-images-v1"
PAGE_PROFILE = {"path": "config/nezha-page-size-profile-v2.json", "sha256": "bed228b0595ef2dc1dd814e98c0966ba9b9452b542de50354db522e2420bed1e", "size_bytes": 15567}
PAGE_SETTINGS = {"PRODUCT_CHECK_PREBUILT_MAX_PAGE_SIZE": True, "PRODUCT_MAX_PAGE_SIZE_SUPPORTED": 4096, "PRODUCT_NO_BIONIC_PAGE_SIZE_MACRO": True}
REQUIRED_POLICY = {"sha256": "b02f5822de8057206e36ee7b90af09a5937b8250b037a2bdad1a33a61075142c", "size_bytes": 35407}
REQUIRED_PROVIDERS = {"sha256": "c8d2ec1822e45181f45af57fd2389a9939eb635e14866dce41b85736fe65513e", "size_bytes": 13737}
MAIN = b'\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'


def _identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _bootstrap(path, wanted=None):
    path = Path(os.path.abspath(path))
    if any(not stat.S_ISDIR(parent.lstat().st_mode) for parent in path.parents):
        raise ValueError("policy3 bootstrap requires real parent directories")
    def signature(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or not 0 < before.st_size <= 2 << 20:
        raise ValueError("policy3 bootstrap requires bounded single-link regular code")
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        if signature(before) != signature(os.fstat(stream.fileno())):
            raise ValueError("policy3 bootstrap source replaced")
        raw = stream.read((2 << 20) + 1)
        if len(raw) > 2 << 20 or signature(before) != signature(os.fstat(stream.fileno())) or signature(before) != signature(path.lstat()):
            raise ValueError("policy3 bootstrap source changed")
    if wanted is not None and _identity(raw) != wanted:
        raise ValueError("policy3 frozen predecessor identity differs")
    return raw


def _body(raw, wanted):
    if type(raw) is not bytes or _identity(raw) != wanted or not raw.endswith(MAIN) or raw.count(MAIN) != 1:
        raise ValueError("policy3 predecessor or terminal main differs")
    return raw[:-len(MAIN)]


NATIVE = "_POLICY3_PREDECESSOR_PAYLOAD" in globals()
ROOT = Path(os.path.abspath(__file__)).parent.parent
_old = types.ModuleType("_frozen_policy3_predecessor")
_old.__file__ = str(ROOT / PREDECESSOR)
if NATIVE:
    _runtime_old = _POLICY3_PREDECESSOR_PAYLOAD
    _self_identity = _POLICY3_ADAPTER_IDENTITY
    exec(compile(_body(_runtime_old, PREDECESSOR_RUNTIME_ID), "<bound-4k-runtime>", "exec"), _old.__dict__)
else:
    _self_identity = _identity(_bootstrap(__file__))
    exec(compile(_body(_bootstrap(ROOT / PREDECESSOR, PREDECESSOR_ID), PREDECESSOR_ID), "<bound-4k-source>", "exec"), _old.__dict__)
    _runtime_old = _old.runtime_tool_payloads({name: _bootstrap(ROOT / name) for name in _old.CONTROL_TOOLS})["tools/target_files_metadata.py"]
    _body(_runtime_old, PREDECESSOR_RUNTIME_ID)

_v2, _v1, _factory = _old._v2, _old._v2._v1, _old._v2._v1._factory
Reader, encoded, identity = _old.Reader, _old.encoded, _old.identity
require, expected, relative, same = _old.require, _old.expected, _old.relative, _old.same
TargetFilesMetadataError = _old.TargetFilesMetadataError
PROFILE, RECEIPT, BUNDLE = _old.PROFILE, _old.RECEIPT, _old.BUNDLE
CONTROL_TOOLS = (*_old.CONTROL_TOOLS, ADAPTER)
ADMISSION_KEYS = _v1.ADMISSION_KEYS | {"selected_delivery_evidence", "page_size_context", "policy3_basis"}
BASIS_KEYS = {"input_profile", "required_policy_inputs", "required_framework_providers", "source_spec", "source_inventory", "source_projects", "source_count", "sidecar_capture", "sidecar_validation", "raw_metadata_proof", "production_receipt", "production_review", "copy_contract", "copy_directory", "copy_verified_inputs"}


def _ready():
    require(IMAGE_CONTRACT_IDENTITY is not None,
            "policy3 delivery is blocked: actual raw/footer/copy and final product descriptor bindings are missing")
    same(IMAGE_CONTRACT_IDENTITY, expected(IMAGE_CONTRACT_IDENTITY), "invalid released policy3 descriptor identity")


def _packaged_images(admission):
    rows = admission.get("packaged_images")
    require(type(rows) is dict and set(rows) == {"vendor", "odm"}, "policy3 final image pair missing")
    for part, size in (("vendor", 959709184), ("odm", 4767621120)):
        same(rows[part], expected(rows[part], _v1.MAX_IMAGE), "invalid final policy3 image identity")
        require(rows[part]["size_bytes"] == size, "policy3 final image budget differs")
    return rows


def _validate_admission(admission, composition):
    _ready()
    same(identity(encoded(admission)), IMAGE_CONTRACT_IDENTITY, "policy3 descriptor differs from reviewed release")
    _admission_structure(admission, composition)
    basis = admission["policy3_basis"]
    require(type(basis) is dict and set(basis) == BASIS_KEYS, "policy3 basis fields differ")
    same(basis["input_profile"], {"path": POLICY_PROFILE, **POLICY_PROFILE_ID,
         "selected_profile": "policy3-evolution", "contract_id": "nezha-five-file-policy-image-inputs-policy3-evolution-v1"}, "policy3 input profile differs")
    same(basis["required_policy_inputs"], REQUIRED_POLICY, "policy3 private policy receipt differs")
    same(basis["required_framework_providers"], REQUIRED_PROVIDERS, "policy3 provider receipt differs")
    require(type(basis["source_count"]) is int and basis["source_count"] == 539, "policy3 production source basis differs")
    for role in ("source_spec", "source_inventory", "source_projects", "sidecar_capture", "sidecar_validation",
                 "raw_metadata_proof", "production_receipt", "production_review", "copy_contract"):
        same(basis[role], expected(basis[role], CURRENT_MAXIMUM), "missing or invalid policy3 binding: " + role)
    require(type(basis["copy_directory"]) is str and basis["copy_directory"].startswith("/work/validation/")
            and ".." not in Path(basis["copy_directory"]).parts, "actual independent-copy directory required")
    same(admission["selected_delivery_evidence"], expected(admission["selected_delivery_evidence"]), "actual policy3 copy receipt required")
    page = admission["page_size_context"]
    require(type(page) is dict and set(page) == {"profile", "profile_id", "production_source_product", "source_product", "product_settings"}, "policy3 page context differs")
    same(page["profile"], PAGE_PROFILE, "current provider page profile differs")
    require(page["profile_id"] == "nezha-stock-4k-bringup-v2", "policy3 page profile selector differs")
    same(page["product_settings"], PAGE_SETTINGS, "strict 4 KiB policy3 settings required")
    for role in ("production_source_product", "source_product"):
        row = page[role]
        require(type(row) is dict and set(row) == {"path", "sha256", "size_bytes"}
                and row["path"] == "device/xiaomi/nezha/generated/device-candidate.mk", "exact policy3 product source required")
        expected(row)
    groups = basis["copy_verified_inputs"]
    require(type(groups) is dict and set(groups) == {"source", "policy", "runtime"}, "copy protection groups are not bound")
    for role, rows in groups.items():
        require(type(rows) is list and len(rows) == {"source": 539, "policy": 14, "runtime": 11}[role],
                "complete policy3 source539/policy14/runtime11 copy protection required")
        paths = []
        for row in rows:
            require(type(row) is dict and set(row) == {"path", "sha256", "size_bytes"}
                    and type(row["path"]) is str and row["path"].startswith("/work/")
                    and ".." not in Path(row["path"]).parts, "invalid copy protection row")
            expected(row, _v1.MAX_IMAGE)
            paths.append(row["path"])
        require(paths == sorted(set(paths)), "missing, duplicate, or unordered copy protection paths")
    same(identity(encoded(groups["source"])), basis["source_inventory"], "copy source protection differs from policy3 production source")


def _controls(root, reader, *, source_contract=None, image_contract=None):
    _ready()
    require(image_contract is not None, "explicit policy3 image contract required")
    root = _factory.real_directory(root)
    profile, composition, controls = _factory._controls(root, reader, source_contract=source_contract)
    raw = reader.read(root / IMAGE_CONTRACT, IMAGE_CONTRACT_IDENTITY)
    selected = Path(image_contract)
    selected = selected if selected.is_absolute() else root / relative(selected.as_posix())
    require(reader.read(selected, IMAGE_CONTRACT_IDENTITY) == raw, "selected policy3 contract differs from controls")
    admission = _factory._json(raw)
    _validate_admission(admission, composition)
    controls[IMAGE_CONTRACT] = raw
    for path in CONTROL_TOOLS:
        controls[path] = reader.read(root / path, _self_identity if path == ADAPTER else None, maximum=2 << 20)
    controls[PAGE_PROFILE["path"]] = reader.read(root / PAGE_PROFILE["path"], PAGE_PROFILE)
    controls[POLICY_PROFILE] = reader.read(root / POLICY_PROFILE, POLICY_PROFILE_ID)
    selected_policy = _factory._json(controls[POLICY_PROFILE])["profiles"]["policy3-evolution"]
    for actual, wanted in zip(admission["policy_inputs"]["actual_compiler_inputs"], selected_policy["evolution_policy"]["compiler_inputs"]):
        same(expected(actual), expected(wanted), "policy3 compiler input identity differs from admitted image profile")
        same([actual["runtime_path"], actual["resolved_path"]], [wanted["runtime_path"], wanted["native_path"]], "policy3 compiler input role differs")
    changes = admission["policy_inputs"]["exact_five_replacement_identities"]
    same(changes["odm"]["/etc/selinux/precompiled_sepolicy"], expected(selected_policy["evolution_policy"]["combined"]), "policy3 combined binary differs")
    same(changes["vendor"]["/etc/selinux/vendor_sepolicy.cil"], expected(selected_policy["evolution_policy"]["compiler_inputs"][7]), "policy3 vendor CIL differs")
    wanted_policy = [{"path": row["native_path"], **expected(row)} for row in selected_policy["evolution_policy"]["compiler_inputs"]]
    combined = selected_policy["evolution_policy"]["combined"]
    wanted_policy.append({"path": combined["native_path"], **expected(combined)})
    for name, partition in (("plat", "system"), ("system_ext", "system_ext"), ("product", "product")):
        wanted_policy.append({"path": "/work/out/nezha-user-policy-20260827T2220Z/target/product/nezha/" + partition
            + "/etc/selinux/" + name + "_sepolicy_and_mapping.sha256",
            **changes["odm"]["/etc/selinux/precompiled_sepolicy." + name + "_sepolicy_and_mapping.sha256"]})
    same(admission["policy3_basis"]["copy_verified_inputs"]["policy"], sorted(wanted_policy, key=lambda row: row["path"]),
         "copy protection omits or changes a compiler input, combined binary, or installed sidecar")
    for role in ("sidecar_capture", "sidecar_validation"):
        same(admission["policy3_basis"][role], selected_policy["native_records"]["policy_" + role], "ordinary sidecar evidence differs")
    _runtime_payloads(controls)
    return profile, composition, controls


def _validate_proof(raw, admission):
    proof = _proof_structure(raw, admission)
    basis = admission["policy3_basis"]
    for field, role in (("raw_metadata_proof", "raw_metadata_proof"), ("production_receipt", "production_receipt"),
                        ("production_independent_review", "production_review")):
        same(expected(proof[field], CURRENT_MAXIMUM), basis[role], "policy3 delivery proof basis differs: " + field)
    require(set(proof["leaf_derivations"]) == {"vendor-1", "vendor-2", "odm-1", "odm-2"}, "two complete footer passes required")
    for partition in ("vendor", "odm"):
        for pass_number in (1, 2):
            same(expected(proof["leaf_derivations"][partition + "-" + str(pass_number)]["image"], _v1.MAX_IMAGE),
                 admission["packaged_images"][partition], "final policy3 footer pass differs")
    return proof


def _validate_current(raw, admission, proof):
    same(identity(raw), CURRENT_REPORT_ID, "actual policy3 build differs")
    same(admission["current_policy_build_evidence"], CURRENT_REPORT_ID, "policy3 current build selection differs")
    current = _factory._json(raw)
    require(type(current["schema_version"]) is int and current["schema_version"] == 1
            and current["operation"] == "first-ordinary-target-files-construction"
            and current["phase"] == "first-target-files-policy-3" and current["profile"] == "policy", "actual policy3 build context required")
    for field in ("profile_completed", "native_process_succeeded", "preflight_completed", "profile_validation_verified", "native_invocation_executed"):
        require(current[field] is True, "policy3 build did not complete: " + field)
    require(current["preflight_error"] is None and current["postcheck_errors"] == [], "policy3 preflight or postcheck failed")
    require(len(current["goals"]) == 32 and len(set(current["goals"])) == 32, "exact policy3 ordinary goal closure required")
    invocation = current["invocation"]
    require(type(invocation["exit_code"]) is int and invocation["exit_code"] == 0
            and invocation["timed_out"] is False and invocation["forced_kill"] is False
            and invocation["sandbox_fallback"] is False and invocation["sandbox_checks_passed"] is True
            and invocation["ninja_argv_verified"] is True and invocation["streams_complete"] is True, "policy3 native process failed or relaxed checks")
    env = current["fixed_environment"]
    same({key: env[key] for key in ("TARGET_PRODUCT", "TARGET_RELEASE", "TARGET_BUILD_VARIANT", "WITH_GMS")},
         {"TARGET_PRODUCT": "lineage_nezha", "TARGET_RELEASE": "bp4a", "TARGET_BUILD_VARIANT": "user", "WITH_GMS": "true"}, "policy3 product context differs")
    basis = admission["policy3_basis"]
    for when in ("before", "after"):
        observation = current["source_observations_" + when]
        strict = observation["strict_settings"]
        require(type(strict["maximum"]) is int and strict["maximum"] == 4096
                and all(strict[key] is True for key in ("no_bionic_page_size_macro", "prebuilt_alignment_check", "strict_elf_checks")), "actual strict 4 KiB settings differ")
        history = observation["source_history"]
        require(history["verified"] is True and history["source_files_checked"] == 539, "actual policy3 source proof differs")
        same(expected(history["source_spec"]), basis["source_spec"], "policy3 source specification differs")
        same(identity(encoded(history["source_inventory"])), basis["source_inventory"], "policy3 current source inventory differs")
        same(identity(encoded(history["source_projects"])), basis["source_projects"], "policy3 source projects differ")
        same(basis["copy_verified_inputs"]["source"], history["source_inventory"], "copy source vector differs from actual539")
        product = admission["page_size_context"]["production_source_product"]
        same([row for row in history["source_inventory"] if row["path"] == "/work/evolution/" + product["path"]],
             [{"path": "/work/evolution/" + product["path"], **expected(product)}], "policy3 production product missing or duplicated")
        runtime = current["source_and_input_admission_" + when]["verify_protected_inputs"]["live_corpus_and_runtime"]
        runtime = sorted([row for row in runtime if row["path"].startswith("/work/out/")], key=lambda row: row["path"])
        require(len(runtime) == 11, "policy3 protected runtime closure differs")
        same(basis["copy_verified_inputs"]["runtime"], runtime, "copy runtime vector differs from actual policy3 protection")
    for field in ("complete_rom_ready", "signed_flashable_rom_verified", "image_reproducibility_verified", "phone_accessed", "source_mutation_requested"):
        require(current[field] is False, "policy3 evidence promotes unverified scope")
    return current


def _validate_selected(raw, admission, current, proof):
    # Reuse the exact copy receipt validator. Its formerly fixed old-source
    # vectors become the closed policy3 descriptor vectors, never live aliases.
    basis = admission["policy3_basis"]
    namespace = dict(_v2.__dict__)
    namespace.update(COPY_OPERATION=COPY_OPERATION, COPY_INPUT_ID=basis["copy_contract"],
                     COPY_DIRECTORY=basis["copy_directory"], CURRENT_REPORT_ID=CURRENT_REPORT_ID)
    source = _v1._function_source(_bootstrap_v2_source, "_validate_selected")
    before = ('expected_inputs = {"policy": current["policy_equality"]["protected_policy_outputs"],\n'
              '                       "runtime": current["policy_equality"]["protected_runtime_outputs"],\n'
              '                       "source": current["current_source_binding"]["source_inventory"]}')
    require(source.count(before) == 1, "frozen copy input vector boundary changed")
    source = source.replace(before, 'expected_inputs = admission["policy3_basis"]["copy_verified_inputs"]')
    before = 'for role, count in (("policy", 13), ("runtime", 11), ("source", 204)):'
    require(source.count(before) == 1, "frozen copy count boundary changed")
    source = source.replace(before, 'for role, count in ((name, len(rows)) for name, rows in expected_inputs.items()):')
    exec(compile(source, "<exact-copy-validator-with-policy3-vectors>", "exec"), namespace)
    return namespace["_validate_selected"](raw, admission, current, proof)


def _validate_evidence(current_raw, selected_raw, admission, proof_raw):
    proof = _validate_proof(proof_raw, admission)
    current = _validate_current(current_raw, admission, proof)
    return current, _validate_selected(selected_raw, admission, current, proof)


def _runtime_payloads(controls):
    require(all(name in controls for name in CONTROL_TOOLS), "policy3 maintained assembly source missing")
    same(identity(controls[PREDECESSOR]), PREDECESSOR_ID, "frozen 4 KiB consumer changed")
    predecessor = _old.runtime_tool_payloads(controls)["tools/target_files_metadata.py"]
    _body(predecessor, PREDECESSOR_RUNTIME_ID)
    extension = controls[ADAPTER]
    require(type(extension) is bytes and 0 < len(extension) <= 2 << 20, "bounded policy3 adapter required")
    prefix = ("#!/usr/bin/env python3\n# Generated from six explicitly admitted maintained sources.\n"
              "_POLICY3_PREDECESSOR_PAYLOAD = " + repr(predecessor) + "\n"
              "_POLICY3_ADAPTER_IDENTITY = " + repr(identity(extension)) + "\n").encode()
    return {"tools/target_files_metadata.py": prefix + extension}


def _policy_gate(admission, target, reader, current):
    same(identity(encoded(current)), CURRENT_REPORT_ID, "packaged policy lacks actual policy3 evidence")
    require(getattr(reader, "policy3_product_verified", False) is True, "actual selected policy3 product source must be verified")
    namespace = dict(_v2.__dict__)
    namespace.update(CURRENT_REPORT_ID=CURRENT_REPORT_ID)
    source = _v1._function_source(_bootstrap_v2_source, "_policy_gate")
    exec(compile(source, "<unchanged-seven-input-three-sidecar-gate>", "exec"), namespace)
    result = namespace["_policy_gate"](admission, target, reader, current)
    result.update(operation="verify-actual-packaged-policy3-policy-v1", page_size_context=copy.deepcopy(admission["page_size_context"]),
                  actual_policy3_product_source_verified=True, production_source_basis_is_historical=True)
    return result


def _installation_report(receipt, digest, reader):
    result = getattr(reader, "current_policy_result", None)
    require(type(result) is dict and result.get("operation") == "verify-actual-packaged-policy3-policy-v1"
            and all(result.get(key) is True for key in ("seven_actual_framework_inputs_verified",
                "three_actual_framework_sidecars_recomputed", "actual_policy3_product_source_verified")),
            "actual packaged policy3 gate must complete before metadata publication")
    return {"schema_version": 5, "operation": "project-policy3-image-target-files-metadata-v1",
        "bundle_receipt_sha256": digest, **{name: receipt[name] for name in (
            "profile", "images", "packaged_images", "files", "property_closure", "source_composition", "image_admission",
            "original_receipt", "delivery_proof", "current_policy_evidence", "selected_delivery_evidence", "page_size_context", "policy3_basis", "scope")},
        "packaged_policy_checks": result, "complete_rom_ready": False}


TRANSFORMS = {
    "_receipt": [('"schema_version": 3', '"schema_version": 5'),
        ('"selected_delivery_evidence": {"path": SELECTED_COPY, **admission["selected_delivery_evidence"]},',
         '"selected_delivery_evidence": {"path": SELECTED_COPY, **admission["selected_delivery_evidence"]},\n'
         '            "page_size_context": copy.deepcopy(admission["page_size_context"]),\n'
         '            "policy3_basis": copy.deepcopy(admission["policy3_basis"]),')],
    "stage_from_original": [('require(not NATIVE,', '_ready()\n    require(not NATIVE,'),
        ("reader.read(current_policy_evidence, admission['current_policy_build_evidence'])", "reader.read(current_policy_evidence, admission['current_policy_build_evidence'], maximum=CURRENT_MAXIMUM)")],
    "verify_bundle": [('receipt["schema_version"] == 3', 'receipt["schema_version"] == 5'),
        ("require(type(expected_receipt) is str", "_ready()\n    require(type(expected_receipt) is str"),
        ("_factory._check_source(source_tree, composition, reader)",
         "_factory._check_source(source_tree, composition, reader)\n"
         "        product = admission['page_size_context']['source_product']\n"
         "        reader.read(_factory.real_directory(source_tree) / relative(product['path']), product)\n"
         "        reader.policy3_product_verified = True"),
        ("reader.read(path, ref) == raw_bytes", "reader.read(path, ref, maximum=CURRENT_MAXIMUM if path == current_policy_evidence else MAX_TEXT) == raw_bytes")],
    "_selected_image_contract": [('receipt["schema_version"] == 3', 'receipt["schema_version"] == 5'),
        ("require(type(expected_receipt) is str", "_ready()\n    require(type(expected_receipt) is str")],
}


def _definitions():
    source = _v2._function_definitions(_v2._runtime_v1)
    output, seen = [], set()
    for node in ast.parse(source).body:
        if not isinstance(node, ast.FunctionDef) or node.name == "_controls":
            continue
        require(node.name not in seen, "duplicate frozen metadata function")
        seen.add(node.name)
        text = ast.get_source_segment(source, node) + "\n"
        for before, after in TRANSFORMS.get(node.name, ()):
            require(text.count(before) == 1, "policy3 transform boundary differs: " + node.name)
            text = text.replace(before, after)
        output.append(text)
    require(set(TRANSFORMS).issubset(seen), "policy3 transform function missing")
    return "\n".join(output)


# Extract the predecessor's already hash-bound literal source, not an import
# from the runtime's filesystem. Both native and host assembly use these bytes.
_bootstrap_v2_source = _old._runtime_v2
_admission_text = _v1._function_source(_v2._runtime_v1, "_validate_admission")
for _before, _after in (
    ('admission["schema_version"] == 1', 'admission["schema_version"] == 4'),
    ('same(admission["packaged_images"], PACKAGED_IMAGES, "image admission final pair differs")', '_packaged_images(admission)'),
    ('require(admission["current_policy_build_evidence"] is None,\n            "no positive current policy-build evidence form is admitted by this candidate")',
     'same(admission["current_policy_build_evidence"], CURRENT_REPORT_ID, "actual policy3 build required")'),
):
    require(_admission_text.count(_before) == 1, "frozen admission boundary differs")
    _admission_text = _admission_text.replace(_before, _after)
_structure = dict(_v1.__dict__)
_structure.update(ADMISSION_KEYS=ADMISSION_KEYS, IMAGE_CONTRACT_ID=IMAGE_CONTRACT_ID,
                  _packaged_images=_packaged_images, CURRENT_REPORT_ID=CURRENT_REPORT_ID, PROOF_OPERATION=PROOF_OPERATION)
exec(compile(_admission_text, "<frozen-admission-with-policy3-selection>", "exec"), _structure)
exec(compile(_v1._function_source(_v2._runtime_v1, "_validate_proof"), "<frozen-delivery-proof-structure>", "exec"), _structure)
_admission_structure, _proof_structure = _structure["_validate_admission"], _structure["_validate_proof"]
_impl = dict(_v2._impl)
_impl.update(ROOT=ROOT, NATIVE=NATIVE, ADAPTER=ADAPTER, IMAGE_CONTRACT=IMAGE_CONTRACT, __doc__=__doc__,
    IMAGE_CONTRACT_ID=IMAGE_CONTRACT_ID, _self_identity=_self_identity, STAGE_OPERATION=STAGE_OPERATION,
    CONTROL_TOOLS=CONTROL_TOOLS, CURRENT_MAXIMUM=CURRENT_MAXIMUM,
    RECEIPT_KEYS=_v2._impl["RECEIPT_KEYS"] | {"page_size_context", "policy3_basis"}, _ready=_ready)
exec(compile(_definitions(), "<frozen-metadata-functions-with-policy3-selection>", "exec"), _impl)
_impl.update(_controls=_controls, _validate_admission=_validate_admission, _validate_proof=_validate_proof,
             runtime_tool_payloads=_runtime_payloads, _validate_evidence=_validate_evidence,
             _current_policy_gate=_policy_gate, _installation_report=_installation_report)
_install_namespace = dict(_factory.__dict__)
_install_namespace.update(verify_bundle=_impl["_install_verify"], _delivery_installation_report=_installation_report)
exec(compile(_v2._install_source, "<unchanged-atomic-install-with-policy3-report>", "exec"), _install_namespace)
_impl.update(_install_namespace=_install_namespace, _install_impl=_install_namespace["install"])
for _name in ("stage_from_original", "verify_bundle", "install", "selection", "compose_sources", "main"):
    globals()[_name] = _impl[_name]
runtime_tool_payloads = _runtime_payloads
_files = _old._files


if __name__ == "__main__":
    raise SystemExit(main())
