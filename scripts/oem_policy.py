#!/usr/bin/env python3
"""Verify the narrow, source-owned Nezha OEM SELinux type restoration.

The source check admits only three reviewed type declarations. The native check
reads freshly produced framework CIL and the unchanged, pinned factory inputs;
it verifies ownership, roles, public mappings, and the existing disabled-helper
capability. Neither command edits source, derives CIL, invokes a compiler, or
admits an image. Native strict compilation and context checks remain separate.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import re
import sys

if __package__:
    from . import vendor_policy as vp
else:
    import vendor_policy as vp


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SHA256 = "3de325f5ff8ba52dc8e43e20556fe876cc44905b04d40ed3b0ff038eaff10cc7"
CONTRACT_PATH = "config/nezha-oem-policy.json"
INPUT_FLAGS = {
    "platform_cil": "/system/etc/selinux/plat_sepolicy.cil",
    "platform_mapping": "/system/etc/selinux/mapping/202504.cil",
    "system_ext_cil": "/system_ext/etc/selinux/system_ext_sepolicy.cil",
    "system_ext_mapping": "/system_ext/etc/selinux/mapping/202504.cil",
    "product_cil": "/product/etc/selinux/product_sepolicy.cil",
    "product_mapping": "/product/etc/selinux/mapping/202504.cil",
    "factory_pub": "/vendor/etc/selinux/plat_pub_versioned.cil",
    "derived_vendor": "/vendor/etc/selinux/vendor_sepolicy.cil",
    "factory_odm": "/odm/etc/selinux/odm_sepolicy.cil",
    "platform_genfs": "/system/etc/selinux/plat_sepolicy_genfs_202504.cil",
}
TYPE_DECLARATION = re.compile(r"type\s+([A-Za-z_][A-Za-z0-9_]*)\s*((?:,\s*[A-Za-z_][A-Za-z0-9_]*\s*)+);\Z")
HELPER_PROPERTIES = frozenset({"apexd_select_prop", "media_variant_prop"})
SCOPE = {
    "source_files_modified": False,
    "factory_inputs_modified": False,
    "cil_generated_or_modified": False,
    "policy_compiler_invoked": False,
    "native_context_tests_run": False,
    "binary_permissive_analysis_run": False,
    "image_or_runtime_support_proven": False,
}


class OemPolicyError(ValueError):
    """An input did not satisfy the reviewed OEM source-restoration contract."""


def require(condition, message):
    if not condition:
        raise OemPolicyError(message)


def load_contract(path=None, reader=None):
    """A copied control bundle is allowed; alternate contract bytes are not."""
    reader = reader or vp.Reader()
    return json.loads(reader.read(path or ROOT / CONTRACT_PATH, CONTRACT_SHA256))


def source_declarations(raw):
    """Only unconditional type declarations, never M4 or permission statements."""
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise OemPolicyError("OEM source must be ASCII") from exc
    text = re.sub(r"#[^\n]*", "", text).strip()
    require(text.endswith(";"), "OEM source must contain complete type declarations")
    result = {}
    for statement in text[:-1].split(";"):
        match = TYPE_DECLARATION.fullmatch(statement.strip() + ";")
        require(match is not None, "OEM source may contain only reviewed type declarations")
        name = match.group(1)
        attrs = [item.strip() for item in match.group(2).split(",")[1:]]
        require(name not in result and len(attrs) == len(set(attrs)), "duplicate type or attribute declaration")
        result[name] = sorted(attrs)
    return result


def verify_capability(raw, contract):
    expected = contract["required_capability_contract"]
    require(vp.sha(raw) == expected["sha256"], "init-helper capability contract hash differs")
    record = json.loads(raw)
    capability = record.get("capability", {})
    require(capability.get("symbol") == expected["symbol"] and capability.get("value") == expected["value"]
            and capability.get("board_variable") == "BOARD_SEPOLICY_M4DEFS"
            and capability.get("api_version_inference_used") is False,
            "init-helper capability binding differs")
    require(record.get("factory_package_sha256") == contract["factory_package_sha256"],
            "OEM source and helper capability use different factory packages")


def verify_source_contents(contents, contract):
    require(set(contents) == {row["path"] for row in contract["source_files"]}, "OEM source file set differs")
    observed = {}
    for row in contract["source_files"]:
        raw = contents[row["path"]]
        require(vp.sha(raw) == row["sha256"] and len(raw) == row["size_bytes"], "OEM source hash or size differs")
        parsed = source_declarations(raw)
        expected = {name: spec["attributes"] for name, spec in contract["types"].items()
                    if spec["scope"] == row["scope"]}
        require(parsed == expected, "OEM source scope or exact attributes differ")
        require(not set(observed).intersection(parsed), "OEM type has more than one authored source owner")
        observed.update(parsed)
    require(set(observed) == set(contract["types"]), "OEM source is missing a reviewed type")
    return observed


def verify_sources(source_root, contract_path=None, capability_path=None):
    """Verify an explicit repository or generated candidate root without writes."""
    source_root = vp.real_directory(source_root)
    reader = vp.Reader()
    contract = load_contract(contract_path, reader)
    capability = reader.read(capability_path or source_root / contract["required_capability_contract"]["path"])
    verify_capability(capability, contract)
    expected_files = {source_root / row["path"] for row in contract["source_files"]}
    for parent in {path.parent for path in expected_files}:
        vp.real_directory(parent)
        require(set(parent.iterdir()) == {path for path in expected_files if path.parent == parent},
                "unreviewed file or directory in an OEM source directory")
    contents = {row["path"]: reader.read(source_root / row["path"], row["sha256"], row["size_bytes"])
                for row in contract["source_files"]}
    declarations = verify_source_contents(contents, contract)
    reader.recheck()
    return {"schema_version": 1, "operation": "verify-nezha-oem-policy-sources", "status": "verified",
            "contract_id": contract["contract_id"], "contract_sha256": CONTRACT_SHA256,
            "declarations": declarations, "source_files": contract["source_files"],
            "capability_contract_sha256": vp.sha(capability),
            "all_inputs_rehashed_unchanged": True, "input_bindings": list(reader.bindings.values()),
            "scope": dict(SCOPE)}


def _classes(form):
    expr = form.expr
    require(len(expr) == 4 and isinstance(expr[3], tuple) and len(expr[3]) == 2,
            "unsupported ordinary allow shape")
    cls, permissions = expr[3]
    require(isinstance(cls, str) and isinstance(permissions, tuple)
            and all(isinstance(item, str) for item in permissions), "unsupported ordinary allow permissions")
    return cls, frozenset(permissions)


def _helper_grants(policy):
    require("init_dev_config" in policy.types and HELPER_PROPERTIES <= policy.types,
            "native platform is missing the reviewed init-helper or property types")
    grants = []
    for form in policy.by_head["allow"]:
        cls, permissions = _classes(form)
        if cls != "property_service" or "set" not in permissions:
            continue
        source = policy.resolve(form.expr[1])
        target = source if form.expr[2] == "self" else policy.resolve(form.expr[2])
        if "init_dev_config" in source and HELPER_PROPERTIES & target:
            grants.append(form)
    return grants


def _record(form):
    return {"runtime_path": form.runtime, "line": form.line,
            "normalized_form_sha256": vp.sha(vp.render(form.expr).encode())}


def _declaration_only_outputs(ext_forms, mapping_forms, policy, contract, platform_forms):
    """The existing system_ext DSP attribute is empty; OEM files add no grants.

    Native filtering can retain generated negative assertions and base-type
    expressions, but it must not introduce permissions, transitions, unrelated
    named memberships, roles, or public mappings from this source slice.
    """
    allowed = {"type", "typeattribute", "typeattributeset", "roletype",
               "expandtypeattribute", "neverallow", "neverallowx"}
    require(all(form.expr[0] in allowed for form in ext_forms),
            "declaration-only system_ext output contains a permission, transition, or unsupported form")
    expected_members = {}
    for name, spec in contract["types"].items():
        for attr in spec["attributes"]:
            expected_members.setdefault(attr, set()).add(name)
    # checkpolicy emits a full membership list for each changed named attribute.
    # Resolve the inherited part from the separate platform input: resolving it
    # in the combined policy would already include unreviewed vendor additions.
    try:
        platform = vp.Policy(platform_forms)
        membership_budget = {attr: platform.resolve(attr) | members for attr, members in expected_members.items()}
    except vp.VendorPolicyError as exc:
        raise OemPolicyError("source-owned membership baseline is not a self-contained platform input") from exc
    named_assignments = Counter()
    for form in ext_forms:
        expr = form.expr
        if expr[0] == "typeattribute":
            require(expr[1] in expected_members or expr[1] == "vendor_hal_dspmanager_client"
                    or expr[1].startswith("base_typeattr_"), "unreviewed source attribute declaration")
        elif expr[0] == "typeattributeset" and not expr[1].startswith("base_typeattr_"):
            require(expr[1] in membership_budget
                    and policy.evaluate(expr[2], policy.resolve, policy.types) == membership_budget[expr[1]],
                    "unreviewed source-owned named attribute membership")
            named_assignments[expr[1]] += 1
        elif expr[0] == "roletype":
            require(len(expr) == 3 and expr[1] == "object_r" and expr[2] in contract["types"],
                    "unreviewed source role binding")
    require(named_assignments == Counter({attr: 1 for attr in expected_members}),
            "source-owned named memberships must occur once per changed attribute")
    versions = {spec["versioned_attribute"] for spec in contract["types"].values()
                if spec["versioned_attribute"] is not None}
    for form in mapping_forms:
        expr = form.expr
        if expr[0] in {"typeattribute", "typeattributeset"}:
            require(expr[1] in versions, "unreviewed public mapping symbol")
        elif expr[0] == "expandtypeattribute":
            require(len(expr) == 3 and isinstance(expr[1], tuple) and set(expr[1]) <= versions
                    and expr[2] in {"true", "false"}, "unreviewed public mapping expansion")
        else:
            raise OemPolicyError("declaration-only public mapping contains an unsupported form")


def check_native_contents(corpus, original_vendor, contract, capability):
    """Static checks of actual compiler inputs, not a substitute for compilation."""
    require(list(corpus) == list(INPUT_FLAGS.values()), "native CIL input order or set differs")
    verify_capability(capability, contract)
    vendor_runtime = INPUT_FLAGS["derived_vendor"]
    for row in contract["unchanged_factory_inputs"]:
        raw = original_vendor if row["runtime_path"] == vendor_runtime else corpus[row["runtime_path"]]
        require(vp.sha(raw) == row["sha256"] and len(raw) == row["size_bytes"],
                "an original factory CIL input was modified")
    derived = contract["existing_vendor_derivation"]
    require(vp.sha(corpus[vendor_runtime]) == derived["sha256"]
            and len(corpus[vendor_runtime]) == derived["size_bytes"],
            "vendor policy differs from the separately reviewed Binder derivation")
    parsed = {runtime: vp.parse(raw, runtime) for runtime, raw in corpus.items()}
    all_forms = [form for forms in parsed.values() for form in forms]
    policy = vp.Policy(all_forms)
    for attr in sorted(policy.attrs | set(policy.aliases)):
        policy.resolve(attr)
    require(not policy.by_head["typepermissive"] and not policy.by_head["permissive"],
            "native CIL contains a permissive domain declaration")
    require(not _helper_grants(policy), "native init-helper property-write capability is enabled")

    system_ext_runtime = INPUT_FLAGS["system_ext_cil"]
    mapping_runtime = INPUT_FLAGS["system_ext_mapping"]
    ext_forms, mapping_forms = parsed[system_ext_runtime], parsed[mapping_runtime]
    _declaration_only_outputs(ext_forms, mapping_forms, policy, contract, parsed[INPUT_FLAGS["platform_cil"]])
    expected_types = set(contract["types"])
    source_types = Counter(form.expr[1] for form in ext_forms if form.expr[0] == "type")
    require(source_types == Counter({name: 1 for name in expected_types}),
            "system_ext must own exactly the three reviewed OEM type declarations")
    original_factory = {runtime: parsed[runtime] for runtime in (INPUT_FLAGS["factory_pub"], INPUT_FLAGS["factory_odm"])}
    original_factory[vendor_runtime] = vp.parse(original_vendor, vendor_runtime)
    for runtime, names in contract["duplicate_declarations"]["expected_factory_type_declarations"].items():
        relevant = Counter(form.expr[1] for form in original_factory[runtime]
                           if form.expr[0] == "type" and form.expr[1] in expected_types)
        require(relevant == Counter({name: 1 for name in names}), "factory duplicate declaration ownership differs")

    domains = policy.resolve("domain")
    core_domains = policy.resolve("coredomain")
    roles = policy.role_bindings()
    observed = {}
    for name, spec in contract["types"].items():
        require(name not in domains and name not in core_domains and roles.get(name, set()) == {"object_r"},
                "OEM object was promoted into a process domain or has incorrect roles")
        own_roles = [form for form in ext_forms if form.expr == ("roletype", "object_r", name)]
        require(len(own_roles) == 1, "system_ext source did not generate exactly one object_r role binding")
        source_memberships = set()
        for form in ext_forms:
            if form.expr[0] != "typeattributeset" or form.expr[1].startswith("base_typeattr_"):
                continue
            if name in policy.evaluate(form.expr[2], policy.resolve, policy.types):
                source_memberships.add(form.expr[1])
        require(source_memberships == set(spec["attributes"]), "source-owned OEM named memberships differ")
        expected_memberships = set(spec["attributes"])
        versioned = spec["versioned_attribute"]
        if versioned is not None:
            expected_memberships.add(versioned)
            own_mapping = [form for form in mapping_forms
                           if form.expr == ("typeattributeset", versioned, (name,))]
            all_assignments = [form for form in policy.by_head["typeattributeset"] if form.expr[1] == versioned]
            require(len(own_mapping) == 1 and all_assignments == own_mapping,
                    "public OEM singleton mapping must be generated exactly once by system_ext")
            require(policy.resolve(versioned) == {name}, "public OEM mapping is not an exact singleton")
        else:
            require(name + "_202504" not in policy.attrs and not any(name in vp.render(form.expr) for form in mapping_forms),
                    "private offlinelog type unexpectedly acquired a public mapping")
        actual_memberships = {attr for attr in policy.attrs if not attr.startswith("base_typeattr_")
                              and name in policy.resolve(attr)}
        require(actual_memberships == expected_memberships, "combined OEM named memberships differ or were broadened")
        declaration_owners = Counter(form.runtime for form in policy.by_head["type"] if form.expr[1] == name)
        factory_owner = INPUT_FLAGS["factory_pub"] if versioned is not None else vendor_runtime
        require(declaration_owners == Counter({system_ext_runtime: 1, factory_owner: 1}),
                "OEM bare type declaration has an unexpected source owner or duplicate")
        observed[name] = {"scope": spec["scope"], "attributes": sorted(actual_memberships),
                          "roles": sorted(roles[name]), "domain": False, "coredomain": False,
                          "versioned_mapping": sorted(policy.resolve(versioned)) if versioned is not None else None,
                          "source_role": _record(own_roles[0]), "declaration_owners": dict(declaration_owners)}

    return {"schema_version": 1, "operation": "check-nezha-oem-native-policy-inputs", "status": "verified",
            "contract_id": contract["contract_id"], "contract_sha256": CONTRACT_SHA256,
            "type_ownership": observed, "helper_effective_property_set_grants": 0,
            "original_factory_inputs_preserved": True, "existing_binder_derivation_preserved": True,
            "permissive_cil_declarations": 0,
            "assertion_statement_counts": {head: len(policy.by_head[head]) for head in ("neverallow", "neverallowx")},
            "scope": dict(SCOPE)}


def check_native(inputs, original_vendor, capability_path, *, contract_path=None, tool_source=None):
    reader = vp.Reader()
    contract = load_contract(contract_path, reader)
    require(set(inputs) == set(INPUT_FLAGS), "native input flags differ")
    corpus = {runtime: reader.read(inputs[flag]) for flag, runtime in INPUT_FLAGS.items()}
    original = reader.read(original_vendor)
    capability = reader.read(capability_path)
    source = Path(tool_source) if tool_source is not None else Path(__file__)
    tools = {name: vp.sha(reader.read(source.with_name(name)))
             for name in ("oem_policy.py", "vendor_policy.py", "artifact_files.py")}
    result = check_native_contents(corpus, original, contract, capability)
    reader.recheck()
    result["input_bindings"] = list(reader.bindings.values())
    result["tool_sources_sha256"] = tools
    result["all_inputs_rehashed_unchanged"] = True
    return result


def _write_result(result, path):
    if path is None:
        print(json.dumps(result, indent=2, sort_keys=True))
        return
    path = Path(os.path.abspath(path))
    vp.real_directory(path.parent)
    raw = vp.encoded(result)
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    require(vp.Reader().read(path) == raw, "OEM check receipt readback differs")
    print(json.dumps({"status": "verified", "receipt": str(path), "sha256": vp.sha(raw)}, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    source = commands.add_parser("verify-sources")
    source.add_argument("--source-root", required=True, type=Path)
    source.add_argument("--contract", type=Path)
    source.add_argument("--capability-contract", type=Path)
    source.add_argument("--output", type=Path)
    native = commands.add_parser("check-native")
    native.add_argument("--contract", required=True, type=Path)
    native.add_argument("--capability-contract", required=True, type=Path)
    native.add_argument("--factory-vendor", required=True, type=Path)
    native.add_argument("--tool-source", type=Path)
    native.add_argument("--output", type=Path)
    for flag in INPUT_FLAGS:
        native.add_argument("--" + flag.replace("_", "-"), required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-sources":
            result = verify_sources(args.source_root, args.contract, args.capability_contract)
        else:
            result = check_native({flag: getattr(args, flag) for flag in INPUT_FLAGS}, args.factory_vendor,
                                  args.capability_contract, contract_path=args.contract, tool_source=args.tool_source)
        _write_result(result, args.output)
    except (OSError, ValueError) as exc:
        print(f"oem-policy: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
