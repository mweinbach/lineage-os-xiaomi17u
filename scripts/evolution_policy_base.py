#!/usr/bin/env python3
"""Factor a pinned native Evolution reference from the Nezha-owned policy.

The reference is produced by ordinary Android M4/checkpolicy modules. This
module never compiles, edits, filters, or publishes a policy input. Its model is
an in-memory comparison budget, assembled from that separately produced base,
eight immutable CIL inputs, and the existing explicit device contracts.
"""
from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path, PurePosixPath
import re

if __package__:
    from . import vendor_policy as vp
    from . import framework_provider_policy as fp
else:
    import vendor_policy as vp
    import framework_provider_policy as fp


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "config/evolution-policy-base.json"
CONTRACT_SHA256 = "7f187d6ab76df8acfd83d0791f5dd9576c5ac43e1d8a43bff02615fbebec8032"
EXT = "/system_ext/etc/selinux/system_ext_sepolicy.cil"
MAPPING = "/system_ext/etc/selinux/mapping/202504.cil"
BASE_EXT = "evolution-base/system_ext_sepolicy.cil"
BASE_MAPPING = "evolution-base/202504.cil"
INPUT_FLAGS = {
    "evolution_base_system_ext_cil": "system_ext_cil",
    "evolution_base_system_ext_mapping": "system_ext_mapping",
    "evolution_base_public_cil": "public_cil",
    "evolution_base_property_contexts": "property_contexts",
    "evolution_base_file_contexts": "file_contexts",
    "evolution_base_service_contexts": "service_contexts",
}
AV_HEADS = frozenset({"allow", "auditallow", "dontaudit", "neverallow",
                      "allowx", "auditallowx", "dontauditx", "neverallowx"})
DECL_HEADS = frozenset({"type", "typeattribute", "typeattributeset", "roletype",
                       "expandtypeattribute"})
ANONYMOUS = "base_typeattr_"


class EvolutionBaseError(vp.VendorPolicyError):
    """The explicit base reference does not close the actual native policy."""


def require(value, message):
    if not value:
        raise EvolutionBaseError(message)


def digest(value):
    return vp.sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def load_contract(path=None, reader=None):
    reader = reader or vp.Reader()
    result = json.loads(reader.read(path or ROOT / CONTRACT_PATH, CONTRACT_SHA256))
    require(result["schema_version"] == 1
            and result["contract_id"] == "nezha-evolution-system-ext-base-v1"
            and result["build_variant"] == "user", "unsupported Evolution base contract")
    rows = source_rows(result)
    require(len(rows) == 46 and len({r["path"] for r in rows}) == 46,
            "Evolution base source selection is not the exact forty-six-file scope")
    for row in rows:
        name = row["path"]
        require(type(name) is str and str(PurePosixPath(name)) == name
                and not name.startswith("/") and ".." not in PurePosixPath(name).parts
                and name.startswith("device/lineage/sepolicy/")
                and re.fullmatch(r"[0-9a-f]{64}", row["sha256"]) is not None
                and type(row["size_bytes"]) is int and 0 < row["size_bytes"] <= 1024**2,
                "invalid Evolution base source identity")
    return result


def source_rows(contract):
    return (contract["base_policy_sources"]["system_ext_public"]
            + contract["base_policy_sources"]["system_ext_private"]
            + contract["base_context_sources"]["property_contexts"]
            + contract["base_context_sources"]["file_contexts"]
            + contract["base_context_sources"]["service_contexts"])


def verify_source_files(paths, contract, reader=None):
    """Verify the actual source-filegroup expansion, including its order."""
    reader = reader or vp.Reader()
    rows = source_rows(contract)
    require(type(paths) in (list, tuple) and len(paths) == len(rows),
            "Evolution reference source list is incomplete or contains extra files")
    roots, observed = set(), []
    for selected, row in zip(paths, rows):
        path = os.path.abspath(selected)
        suffix = "/" + row["path"]
        require(path.endswith(suffix), "Evolution reference source order or selector differs")
        roots.add(path[:-len(suffix)])
        data = reader.read(path, row["sha256"])
        require(len(data) == row["size_bytes"], "Evolution reference source size differs")
        observed.append({**row, "selected_path": path})
    require(len(roots) == 1, "Evolution reference sources have multiple source roots")
    reader.recheck()
    return observed


def _form(expr, runtime=EXT):
    return vp.Form(expr, 0, 0, 0, 0, runtime)


def _atoms(expr):
    if isinstance(expr, str):
        return {expr}
    return set().union(*(_atoms(item) for item in expr)) if expr else set()


def _rename(expr, renames):
    if isinstance(expr, str):
        return renames.get(expr, expr)
    return tuple(_rename(item, renames) for item in expr)


def _closed(forms):
    policy = vp.Policy(forms)
    for name in sorted(policy.attrs | set(policy.aliases)):
        policy.resolve(name)
    policy.role_bindings()
    require(not policy.by_head["typepermissive"] and not policy.by_head["permissive"],
            "Evolution composition contains a permissive declaration")
    return policy


def _owned_forms(contract, provider, attribute_declarations):
    """Use existing reviewed source budgets; no generated CIL is emitted."""
    specs = {**contract["types"], **provider["types"]}
    forms = [_form(("typeattribute", name)) for name in attribute_declarations]
    members, mappings = {}, []
    for name, spec in specs.items():
        forms += [_form(("type", name)), _form(("roletype", "object_r", name))]
        for attribute in spec["attributes"]:
            members.setdefault(attribute, set()).add(name)
        version = spec.get("versioned_attribute")
        if version is not None:
            mappings += [_form(("typeattribute", version), MAPPING),
                         _form(("typeattributeset", version, (name,)), MAPPING),
                         _form(("expandtypeattribute", (version,), "true"), MAPPING)]
    forms += [_form(("typeattributeset", attr, tuple(sorted(names))))
              for attr, names in sorted(members.items())]
    for row in contract.get("native_read_clauses", []):
        forms.append(_form(("allow", row["source_type"], row["target_type"],
                            (row["class"], tuple(sorted(row["permissions"]))))))
    for expression, count in fp.expected_native_forms(provider).items():
        forms.extend(_form(expression) for _ in range(count))
    for index, row in enumerate(provider["native_policy_budget"]["registration_assertions"]):
        name = "nezha_reference_registration_" + str(index)
        forms += [_form(("typeattribute", name)),
                  _form(("typeattributeset", name,
                         ("and", ("domain",), ("not", tuple(row["exclude_domains"]))))),
                  _form(("neverallow", name, row["service"],
                         ("service_manager", (row["permission"],))))]
    return forms, mappings, specs, members


def _endpoint(policy, expression, source=None):
    if expression == "self":
        require(source is not None, "self is not a valid source endpoint")
        return source
    return policy.evaluate(expression, policy.resolve, policy.types)


def _rules(policy, forms):
    """Close all AV/audit/assertion endpoints, preserving rule multiplicity."""
    result = Counter()
    for form in forms:
        expr, head = form.expr, form.expr[0]
        if head not in AV_HEADS:
            continue
        require(len(expr) == 4 and isinstance(expr[3], tuple), "unsupported access-vector form")
        source = _endpoint(policy, expr[1])
        target = _endpoint(policy, expr[2], source)
        diagonal = expr[2] == "self" or (len(source) == 1 and target == source)
        tail = expr[3]
        if head.endswith("x"):
            require(len(tail) == 3 and isinstance(tail[0], str) and isinstance(tail[1], str),
                    "unsupported extended-permission form")
        else:
            require(len(tail) == 2 and isinstance(tail[0], str)
                    and isinstance(tail[1], tuple) and all(isinstance(p, str) for p in tail[1]),
                    "unsupported ordinary permissions")
            require(len(set(tail[1])) == len(tail[1]), "duplicate permission in a native rule")
            tail = tail[0], tuple(sorted(tail[1]))
        result[(head, digest(sorted(source)), "self" if diagonal else digest(sorted(target)), tail)] += 1
    return result


def _anonymous_expression(expr, policy, local):
    if isinstance(expr, str):
        return ("resolved_anonymous", digest(sorted(policy.resolve(expr)))) if expr in local else expr
    return tuple(_anonymous_expression(item, policy, local) for item in expr)


def _other_forms(forms, policy, local):
    return Counter(_anonymous_expression(form.expr, policy, local) for form in forms
                   if form.expr[0] not in DECL_HEADS | AV_HEADS)


def _expansions(forms):
    result = Counter()
    for form in forms:
        expr = form.expr
        if expr[0] != "expandtypeattribute":
            continue
        require(len(expr) == 3 and isinstance(expr[1], tuple)
                and all(isinstance(name, str) for name in expr[1])
                and expr[2] in {"true", "false"}, "unsupported attribute expansion")
        result.update((name, expr[2]) for name in expr[1])
    return result


def _local_attributes(forms, policy, inherited):
    declarations = Counter(f.expr[1] for f in forms if f.expr[0] == "typeattribute")
    assignments = Counter(f.expr[1] for f in forms if f.expr[0] == "typeattributeset")
    expansions = _expansions(forms)
    local = set(declarations) - inherited
    require(all(name.startswith(ANONYMOUS) or name.startswith("nezha_reference_") for name in local),
            "unexpected local named attribute")
    signatures = Counter()
    for name in local:
        flags = tuple(sorted((value, count) for (attr, value), count in expansions.items() if attr == name))
        signatures[(digest(sorted(policy.resolve(name))), declarations[name], assignments[name], flags)] += 1
    return local, signatures


def _mapping_counter(forms):
    result = Counter()
    for form in forms:
        expr = form.expr
        require(expr[0] in {"typeattribute", "typeattributeset", "expandtypeattribute"},
                "unsupported public mapping form")
        if expr[0] == "expandtypeattribute":
            result.update(("expandtypeattribute", name, value) for (name, value), count
                          in _expansions([form]).items() for _ in range(count))
        else:
            result[expr] += 1
    return result


def _context_rows(raw, kind):
    require(type(raw) is bytes and b"\x00" not in raw, "invalid context bytes")
    result = []
    for line in raw.decode("utf-8").splitlines():
        fields = tuple(line.partition("#")[0].split())
        if not fields:
            continue
        require(2 <= len(fields) <= 5, "unsupported context row")
        require(any(re.fullmatch(r"u:object_r:[A-Za-z0-9_]+:s0", value) for value in fields[1:]),
                "context row lacks its exact object label")
        if kind == "property_contexts":
            require(len(fields) in {2, 3, 4}, "unsupported property context fields")
            if len(fields) == 2:
                fields += ("prefix", None)
            elif len(fields) == 3:
                fields += (None,)
            require(fields[2] in {"prefix", "exact"}, "unsupported property matching semantics")
        result.append(fields)
    return result


def check_contexts(base, full, property_contract, provider_contract):
    owned = {
        "property_contexts": [tuple(row[key] for key in
            ("property_pattern", "context", "match", "value_type"))
            for row in property_contract["property_contexts"]],
        "file_contexts": [tuple(row) for row in provider_contract["context_entries"]["file_contexts"]],
        "service_contexts": [tuple(row) for row in provider_contract["context_entries"]["service_contexts"]],
    }
    result = {}
    for kind in owned:
        base_rows, actual_rows = _context_rows(base[kind], kind), _context_rows(full[kind], kind)
        expected = base_rows + owned[kind]
        # File contexts can distinguish object kinds, but a source collision
        # across the ownership boundary still needs an explicit new contract.
        require(len({row[0] for row in expected}) == len(expected),
                "duplicate or base/owned context selector")
        require(Counter(actual_rows) == Counter(expected), "full context rows differ from base plus owned: " + kind)
        if kind == "property_contexts":
            for base_row in base_rows:
                for own_row in owned[kind]:
                    require(not (base_row[2] == "prefix" and own_row[0].startswith(base_row[0]))
                            and not (own_row[2] == "prefix" and base_row[0].startswith(own_row[0])),
                            "base and owned property prefixes overlap")
        result[kind] = {"base_rows": len(base_rows), "owned_rows": len(owned[kind]),
                        "full_rows": len(actual_rows), "row_multiset_sha256": digest(sorted(actual_rows, key=repr))}
    return result


def check_composition(corpus, parsed, actual, owned_contract, properties, provider,
                      base, contract, full_contexts, full_public):
    """Validate the full actual corpus; no owned-only filtered input is made."""
    require(set(base) == set(INPUT_FLAGS.values()), "missing or extra native base reference input")
    fixed = []
    immutable_assertions = 0
    for row in contract["unchanged_cil_inputs"]:
        raw = corpus[row["runtime_path"]]
        require(vp.sha(raw) == row["sha256"] and len(raw) == row["size_bytes"],
                "unchanged policy input differs from the reviewed assertion anchor")
        forms = parsed[row["runtime_path"]]
        require(sum(f.expr[0] == "neverallow" for f in forms) == row["neverallow"]
                and sum(f.expr[0] == "neverallowx" for f in forms) == row["neverallowx"],
                "immutable assertion count differs")
        immutable_assertions += row["neverallow"] + row["neverallowx"]
        fixed += forms
    require(set(corpus) - {EXT, MAPPING} == {r["runtime_path"] for r in contract["unchanged_cil_inputs"]},
            "immutable policy input set differs")
    base_forms = vp.parse(base["system_ext_cil"], BASE_EXT)
    base_maps = vp.parse(base["system_ext_mapping"], BASE_MAPPING)
    own_forms, own_maps, specs, own_members = _owned_forms(
        owned_contract, provider, contract["owned_attribute_declarations"])
    require(not any(_atoms(f.expr) & set(specs) for f in base_forms + base_maps),
            "independent Evolution base references device-owned types")
    inherited = {f.expr[1] for f in fixed if f.expr[0] == "typeattribute"}
    base_declared = {f.expr[1] for f in base_forms if f.expr[0] == "typeattribute"}
    base_local = {name for name in base_declared - inherited if name.startswith(ANONYMOUS)}
    renames = {name: "nezha_reference_base_" + str(i) for i, name in enumerate(sorted(base_local))}
    modeled_base = [_form(_rename(f.expr, renames), BASE_EXT) for f in base_forms]
    reference = _closed(fixed + modeled_base + base_maps + own_forms + own_maps)
    require(actual.types == reference.types and actual.aliases == reference.aliases,
            "full type or alias namespace differs from independent base plus owned")
    named = {name for name in reference.attrs if not name.startswith("nezha_reference_")}
    require({name for name in actual.attrs if not name.startswith(ANONYMOUS)}
            == {name for name in named if not name.startswith(ANONYMOUS)},
            "full named attribute namespace differs")
    require(named <= actual.attrs, "inherited or base named attribute is missing")
    for name in sorted(named):
        require(actual.resolve(name) == reference.resolve(name),
                "inherited or named attribute closure differs: " + name)
    require(actual.role_bindings() == reference.role_bindings(), "full role closure differs")
    current_forms, expected_forms = parsed[EXT], modeled_base + own_forms
    for head in ("type", "roletype"):
        require(Counter(f.expr for f in current_forms if f.expr[0] == head)
                == Counter(f.expr for f in expected_forms if f.expr[0] == head),
                "source declaration/role multiplicity differs: " + head)
    source_named = {f.expr[1] for f in expected_forms if f.expr[0] == "typeattributeset"
                    and not f.expr[1].startswith((ANONYMOUS, "nezha_reference_"))}
    observed_named = Counter(f.expr[1] for f in current_forms if f.expr[0] == "typeattributeset"
                             and not f.expr[1].startswith(ANONYMOUS))
    require(observed_named == Counter({name: 1 for name in source_named}),
            "full source named assignments are missing, duplicated, or extra")
    expected_named_decls = Counter(f.expr for f in expected_forms if f.expr[0] == "typeattribute"
                                   and not f.expr[1].startswith((ANONYMOUS, "nezha_reference_")))
    require(Counter(f.expr for f in current_forms if f.expr[0] == "typeattribute"
                    and not f.expr[1].startswith(ANONYMOUS)) == expected_named_decls,
            "source named attribute declarations differ")
    for head in ("typeattribute", "typeattributeset"):
        require(Counter(f.expr[1] for f in current_forms
                        if f.expr[0] == head and f.expr[1] in inherited and f.expr[1].startswith(ANONYMOUS))
                == Counter(f.expr[1] for f in expected_forms
                           if f.expr[0] == head and f.expr[1] in inherited and f.expr[1].startswith(ANONYMOUS)),
                "source inherited anonymous attribute definition multiplicity differs: " + head)
    current_local, current_signatures = _local_attributes(current_forms, actual, named)
    reference_local, reference_signatures = _local_attributes(expected_forms, reference, named)
    require(current_signatures == reference_signatures, "local anonymous definition/closure budget differs")
    current_flags, reference_flags = _expansions(actual.forms), _expansions(reference.forms)
    require(Counter({key: count for key, count in current_flags.items() if key[0] in named})
            == Counter({key: count for key, count in reference_flags.items() if key[0] in named}),
            "inherited or named attribute expansion flags differ")
    require(_rules(actual, current_forms) == _rules(reference, expected_forms),
            "full source access, audit, or assertion forms differ from base plus owned")
    require(_other_forms(current_forms, actual, current_local)
            == _other_forms(expected_forms, reference, reference_local),
            "full source transition or other forms differ from base plus owned")
    require(_mapping_counter(parsed[MAPPING]) == _mapping_counter(base_maps + own_maps),
            "full public mapping differs from exact base plus owned mapping")
    base_types = {f.expr[1] for f in base_forms if f.expr[0] == "type"}
    fixed_types = {f.expr[1] for f in fixed if f.expr[0] == "type"}
    collisions = base_types & fixed_types
    require(collisions == set(contract["base_factory_duplicate_types"]),
            "Evolution/factory duplicate type set differs")
    for name, spec in contract["base_factory_duplicate_types"].items():
        owners = Counter(f.runtime for f in actual.by_head["type"] if f.expr[1] == name)
        require(owners == Counter({spec["factory_runtime"]: 1, spec["source_runtime"]: 1})
                and actual.role_bindings()[name] == {spec["role"]}
                and actual.resolve(spec["mapping_attribute"]) == {name},
                "Evolution/factory duplicate ownership, role or singleton mapping differs")
    base_public_forms = vp.parse(base["public_cil"], "base-public-exporter")
    full_public_forms = vp.parse(full_public, "full-public-exporter")
    base_public_types = Counter(f.expr[1] for f in base_public_forms if f.expr[0] == "type")
    own_public = {name for name, spec in owned_contract["types"].items()
                  if spec["versioned_attribute"] is not None}
    require(not (set(base_public_types) & set(specs)), "base public exporter contains an owned type")
    require(Counter(f.expr[1] for f in full_public_forms if f.expr[0] == "type")
            == base_public_types + Counter({name: 1 for name in own_public}),
            "full public exporter type inventory differs or leaks private types")
    context_result = check_contexts(base, full_contexts, properties, provider)
    require(immutable_assertions == contract["original_assertions"]["immutable_input_neverallows"]
            + contract["original_assertions"]["immutable_input_neverallowx"], "assertion anchor differs")
    result = {
        "operation": "check-native-evolution-base-plus-owned-policy", "status": "verified",
        "contract_id": contract["contract_id"], "contract_sha256": CONTRACT_SHA256,
        "immutable_original_assertions": immutable_assertions,
        "owned_provider_assertions": len(provider["native_policy_budget"]["registration_assertions"]),
        "base_assertions": sum(f.expr[0] in {"neverallow", "neverallowx"} for f in base_forms),
        "base_type_count": len(base_types), "owned_type_count": len(specs),
        "base_factory_duplicate_types": sorted(collisions),
        "full_named_and_inherited_anonymous_closures_match_independent_reference": True,
        "all_source_access_audit_assertion_transition_forms_accounted_for": True,
        "context_composition": context_result,
        "binary_zero_permissive_check_performed": False,
        "native_recipe_and_source_action_provenance_requires_separate_evidence": True,
        "vendor_source_delivery_into_factory_images_proven": False,
        "image_or_runtime_admitted": False,
    }
    return {"reference": reference, "membership_budget": {
        name: reference.resolve(name) for name in source_named},
        "base_types": base_types, "result": result}
