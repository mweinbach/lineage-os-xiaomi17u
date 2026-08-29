#!/usr/bin/env python3
"""Validate the explicit, private Nezha framework HAL provider policy.

This is a source and compiler-input guard. It does not compile policy, install
providers, alter original firmware, or establish runtime service availability.
The older OEM policy profiles remain independent and strict by default.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import sys

if __package__:
    from . import vendor_policy as vp
else:
    import vendor_policy as vp


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "config/nezha-framework-provider-policy.json"
CONTRACT_SHA256 = "6515395854a7cdc08f2d9c9ed5f7119164a9c0376ca8710a152ffb1999dc52f8"
EXT_RUNTIME = "/system_ext/etc/selinux/system_ext_sepolicy.cil"
EXT_MAPPING = "/system_ext/etc/selinux/mapping/202504.cil"
CONTROLLED_HEADS = frozenset({"allow", "auditallow", "dontaudit", "allowx", "typetransition"})
SCOPE = {
    "source_files_modified": False,
    "factory_inputs_modified": False,
    "cil_generated_or_modified": False,
    "policy_compiler_invoked": False,
    "native_context_tests_run": False,
    "binary_permissive_analysis_run": False,
    "image_adoption_proven": False,
    "runtime_service_availability_proven": False,
    "client_feature_closure_proven": False,
    "complete_rom_admitted": False,
}


class FrameworkProviderPolicyError(ValueError):
    """A reviewed provider source or native policy invariant did not hold."""


def require(condition, message):
    if not condition:
        raise FrameworkProviderPolicyError(message)


def load_contract(path=None, reader=None):
    reader = reader or vp.Reader()
    return json.loads(reader.read(path or ROOT / CONTRACT_PATH, CONTRACT_SHA256))


def _lines(raw):
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise FrameworkProviderPolicyError("provider source must be ASCII") from exc
    return [line.split("#", 1)[0].strip() for line in text.splitlines()
            if line.split("#", 1)[0].strip()]


def verify_source_contents(contents, contract):
    """Pin both exact bytes and the independently reviewed source statements."""
    require(set(contents) == {row["path"] for row in contract["source_files"]},
            "provider source file set differs")
    for row in contract["source_files"]:
        raw = contents[row["path"]]
        require(vp.sha(raw) == row["sha256"] and len(raw) == row["size_bytes"],
                "provider source hash or size differs")
        require(_lines(raw) == row["statements"], "provider source statement budget differs")
    return {name: {key: spec[key] for key in ("attributes", "roles", "domain", "scope")}
            for name, spec in contract["types"].items()}


def verify_macro_sources(android_source_root, contract, reader=None):
    """Read the selected Android source or its bounded, hash-identical capture."""
    reader = reader or vp.Reader()
    root = vp.real_directory(android_source_root)
    for row in contract["pinned_android_sources"]:
        reader.read(root / row["path"], row["sha256"], row["size_bytes"])
    reader.recheck()
    return list(reader.bindings.values())


def verify_sources(source_root, *, contract_path=None, control_root=None,
                   provider_bundle=None, android_source_root=None):
    """Source-only verification is useful, but does not admit absent providers."""
    source_root = vp.real_directory(source_root)
    control_root = vp.real_directory(control_root or ROOT)
    reader = vp.Reader()
    contract = load_contract(contract_path, reader)
    for row in contract["required_contracts"].values():
        reader.read(control_root / row["path"], row["sha256"])
    paths = {source_root / row["path"] for row in contract["source_files"]}
    for directory in {path.parent for path in paths}:
        vp.real_directory(directory)
        require(set(directory.iterdir()) == {path for path in paths if path.parent == directory},
                "unreviewed file or directory in provider policy source")
    contents = {row["path"]: reader.read(source_root / row["path"], row["sha256"], row["size_bytes"])
                for row in contract["source_files"]}
    types = verify_source_contents(contents, contract)
    macro_bindings = verify_macro_sources(android_source_root, contract, reader) if android_source_root else None
    provider = None
    if provider_bundle is not None:
        if __package__:
            from . import framework_provider_inputs as fpi
        else:
            import framework_provider_inputs as fpi
        profile = control_root / contract["required_contracts"]["provider_inputs"]["path"]
        provider = fpi.verify_bundle(provider_bundle, contract_path=profile)
        require(provider.get("status") == "verified", "provider input bundle was not verified")
    reader.recheck()
    return {
        "schema_version": 1, "operation": "verify-nezha-framework-provider-policy-sources",
        "status": "verified", "contract_id": contract["contract_id"],
        "contract_sha256": CONTRACT_SHA256, "types": types,
        "source_files": contract["source_files"],
        "provider_bundle_verified": provider is not None,
        "provider_bundle": provider, "pinned_android_macro_sources_verified": macro_bindings is not None,
        "all_inputs_rehashed_unchanged": True, "input_bindings": list(reader.bindings.values()),
        "scope": dict(SCOPE),
    }


def normalized_form(expr):
    """Permission ordering may change; duplicate or nonliteral permissions may not."""
    if expr[0] in {"allow", "auditallow", "dontaudit", "neverallow"}:
        require(len(expr) == 4 and isinstance(expr[3], tuple) and len(expr[3]) == 2,
                "unsupported provider access-vector form")
        cls, perms = expr[3]
        require(isinstance(cls, str) and isinstance(perms, tuple) and perms
                and all(isinstance(perm, str) for perm in perms) and len(perms) == len(set(perms)),
                "provider access-vector permissions must be unique literals")
        return (expr[0], expr[1], expr[2], (cls, tuple(sorted(perms))))
    return expr


def expected_native_forms(contract):
    """Exact source-authored forms, separate from inherited platform grants."""
    budget = contract["native_policy_budget"]
    result = Counter()
    for key, head in (("allows", "allow"), ("dontaudits", "dontaudit")):
        for row in budget[key]:
            result[(head, row["source"], row["target"],
                    (row["class"], tuple(sorted(row["permissions"]))))] += 1
    for row in budget["type_transitions"]:
        result[("typetransition", row["source"], row["executable"], "process", row["target"])] += 1
    return result


def native_form_allowed(form, contract):
    """Composition hook; never grants a blanket exception for a provider name."""
    return normalized_form(form.expr) in expected_native_forms(contract)


def _literal_endpoint_identity(policy, expected_forms):
    """The reviewed names must denote their concrete types, not retargetable sets."""
    names, processes = set(), set()
    for expr in expected_forms:
        if expr[0] == "typetransition":
            names.update((expr[1], expr[2], expr[4]))
            processes.update((expr[1], expr[4]))
        else:
            names.update((expr[1], expr[2]))
            processes.add(expr[1])
            if expr[3][0] in {"binder", "fd", "process"}:
                processes.add(expr[2])
    for name in names:
        require(isinstance(name, str) and name in policy.types
                and name not in policy.aliases and name not in policy.attrs
                and policy.resolve(name) == {name},
                "provider literal endpoint is not its concrete singleton type")
    require(processes <= policy.resolve("domain"),
            "provider process endpoint is not a concrete process domain")
    return {"concrete_singleton_types": sorted(names), "process_domains": sorted(processes)}


def _endpoint(policy, expr, source=None):
    if expr == "self":
        require(source is not None, "self cannot be a provider source endpoint")
        return source
    return policy.evaluate(expr, policy.resolve, policy.types)


def _references_provider(form, policy, provider_types):
    expr = form.expr
    if expr[0] in {"allow", "auditallow", "dontaudit", "allowx"}:
        require(len(expr) >= 3, "unsupported native provider permission")
        source = _endpoint(policy, expr[1])
        target = _endpoint(policy, expr[2], source)
        return bool(provider_types & (source | target))
    if expr[0] == "typetransition":
        require(len(expr) in {5, 6}, "unsupported native provider transition")
        endpoints = set().union(*(_endpoint(policy, item) for item in (expr[1], expr[2], expr[-1])))
        return bool(provider_types & endpoints)
    return False


def _registration_assertions(policy, ext_forms, contract):
    matched = []
    domains = policy.resolve("domain")
    for row in contract["native_policy_budget"]["registration_assertions"]:
        require(set(row["exclude_domains"]) <= domains,
                "provider registration restriction refers to an absent process domain")
        expected_source = domains - set(row["exclude_domains"])
        matches = []
        for form in ext_forms:
            if form.expr[0] != "neverallow":
                continue
            expr = normalized_form(form.expr)
            if expr[3] != ("service_manager", (row["permission"],)):
                continue
            if _endpoint(policy, expr[2]) != {row["service"]}:
                continue
            if _endpoint(policy, expr[1]) == expected_source:
                matches.append(form)
        require(len(matches) == 1, "provider service registration/find restriction is missing or duplicated")
        matched.append({"service": row["service"], "permission": row["permission"],
                        "line": matches[0].line,
                        "normalized_form_sha256": vp.sha(vp.render(matches[0].expr).encode())})
    return matched


def check_native_extension(policy, parsed, contract):
    """Validate the FULL compiler corpus; callers still validate other profiles.

    Extra permissions materialized by a future compiler are rejected for review,
    even if their endpoint is one of these providers. This function never strips
    provider forms out of a corpus to make the older guard accept it.
    """
    require(EXT_RUNTIME in parsed and EXT_MAPPING in parsed, "native system_ext inputs are missing")
    ext_forms = parsed[EXT_RUNTIME]
    provider_types = set(contract["types"])
    require(not policy.by_head["typepermissive"] and not policy.by_head["permissive"],
            "native policy contains a permissive declaration")
    require(provider_types <= policy.types, "native policy is missing a provider type")
    # These types are private and absent from every retained factory/API input.
    # Generic pinned platform attribute rules may apply to the new domains, but
    # no other partition may author literal or alias references to these names.
    for runtime, forms in parsed.items():
        if runtime != EXT_RUNTIME:
            require(not any(_atoms(form.expr) & provider_types for form in forms),
                    "private provider symbol is referenced outside its system_ext source owner")
    require(not any(policy.resolve(alias) & provider_types for alias in policy.aliases),
            "private provider type acquired an unreviewed alias")
    expected = expected_native_forms(contract)
    endpoint_identity = _literal_endpoint_identity(policy, expected)
    roles = policy.role_bindings()
    domains, core_domains = policy.resolve("domain"), policy.resolve("coredomain")
    observed = {}
    for name, spec in contract["types"].items():
        owners = Counter(form.runtime for form in policy.by_head["type"] if form.expr[1] == name)
        require(owners == Counter({EXT_RUNTIME: 1}), "private provider type has a duplicate or wrong owner")
        own_roles = [form for form in ext_forms if form.expr == ("roletype", "object_r", name)]
        require(len(own_roles) == 1 and roles.get(name, set()) == set(spec["roles"]),
                "provider type role binding differs")
        require((name in domains) is spec["domain"] and (name in core_domains) is spec["domain"],
                "provider process/object classification differs")
        attrs = {attr for attr in policy.attrs if not attr.startswith("base_typeattr_")
                 and name in policy.resolve(attr)}
        require(attrs == set(spec["attributes"]), "provider named attributes differ or were broadened")
        source_attrs = {form.expr[1] for form in ext_forms
                        if form.expr[0] == "typeattributeset" and not form.expr[1].startswith("base_typeattr_")
                        and name in _endpoint(policy, form.expr[2])}
        require(source_attrs == set(spec["attributes"]), "source-owned provider memberships differ")
        require(name + "_202504" not in policy.attrs, "private provider type acquired a public mapping")
        for runtime, forms in parsed.items():
            if "/mapping/" in runtime:
                require(not any(name in _atoms(form.expr) for form in forms),
                        "private provider type leaked into a mapping input")
        observed[name] = {"attributes": sorted(attrs), "roles": sorted(roles[name]),
                          "domain": spec["domain"], "declaration_owners": dict(owners),
                          "public_mapping": None}

    forms = [form for form in ext_forms if form.expr[0] in CONTROLLED_HEADS
             and _references_provider(form, policy, provider_types)]
    actual = Counter(normalized_form(form.expr) for form in forms)
    require(actual == expected, "native provider permission/transition budget differs")
    assertions = _registration_assertions(policy, ext_forms, contract)
    return {"schema_version": 1, "operation": "check-nezha-framework-provider-policy-extension",
            "status": "verified", "contract_id": contract["contract_id"],
            "contract_sha256": CONTRACT_SHA256, "type_ownership": observed,
            "literal_endpoint_identity": endpoint_identity,
            "source_allow_clauses": len(contract["native_policy_budget"]["allows"]),
            "source_dontaudit_clauses": len(contract["native_policy_budget"]["dontaudits"]),
            "source_type_transitions": len(contract["native_policy_budget"]["type_transitions"]),
            "registration_assertions": assertions, "permissive_cil_declarations": 0,
            "scope": dict(SCOPE)}


def _atoms(expr):
    if isinstance(expr, str):
        return {expr}
    return set().union(*(_atoms(item) for item in expr)) if expr else set()


def verify_native_contexts(file_contexts, service_contexts, contract):
    """Check exact provider rows in native framework or full aggregated contexts."""
    types = set(contract["types"])
    observed = {}
    for key, raw in (("file_contexts", file_contexts), ("service_contexts", service_contexts)):
        rows = []
        expected = [tuple(row) for row in contract["context_entries"][key]]
        expected_keys = {row[0] for row in expected}
        for line in _lines(raw):
            fields = line.split()
            if fields[0] in expected_keys or any(
                    field.startswith("u:object_r:") and field.split(":")[2] in types for field in fields):
                rows.append(tuple(fields))
        require(Counter(rows) == Counter(expected), "native provider contexts differ or have duplicate labels")
        observed[key] = len(rows)
    return {"status": "verified", "provider_context_rows": observed,
            "scope": dict(SCOPE)}


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
    require(vp.Reader().read(path) == raw, "provider policy receipt readback differs")
    print(json.dumps({"status": "verified", "receipt": str(path), "sha256": vp.sha(raw)}, sort_keys=True))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    source = commands.add_parser("verify-sources")
    source.add_argument("--source-root", required=True, type=Path)
    source.add_argument("--contract", type=Path)
    source.add_argument("--control-root", type=Path)
    source.add_argument("--provider-bundle", type=Path)
    source.add_argument("--android-source-root", type=Path)
    source.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    try:
        result = verify_sources(args.source_root, contract_path=args.contract, control_root=args.control_root,
                                provider_bundle=args.provider_bundle, android_source_root=args.android_source_root)
        _write_result(result, args.output)
    except (OSError, ValueError) as exc:
        print(f"framework-provider-policy: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
