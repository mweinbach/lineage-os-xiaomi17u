#!/usr/bin/env python3
"""Verify the narrow, source-owned Nezha OEM SELinux restoration profiles.

The default source check admits only three reviewed type declarations. An
explicit additional property contract admits four public properties, eight
original prefix contexts, and two exact framework read clauses. A separate
explicit provider contract admits its independently checked private type,
permission, transition, registration assertion, and context budgets. The native check
reads freshly produced framework CIL and the unchanged, pinned factory inputs;
it verifies ownership, roles, public mappings, and the existing disabled-helper
capability. Neither command edits source, derives CIL, invokes a compiler, or
admits an image. Native strict compilation and context checks remain separate.
"""

from __future__ import annotations

import argparse
from collections import Counter
import copy
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
PROPERTY_CONTRACT_PATH = "config/nezha-oem-properties.json"
PROPERTY_CONTRACT_SHA256 = "f5796d6df4b7232d32ffdece83bc2d5726669fbb6f34f0ba2ef86be6cbc1d711"
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


def load_property_contract(path, reader=None):
    """The four-property profile requires a separate explicit pinned contract."""
    require(path is not None, "the property contract must be selected explicitly")
    reader = reader or vp.Reader()
    return json.loads(reader.read(path, PROPERTY_CONTRACT_SHA256))


def _provider_module():
    # Legacy native bundles do not contain this optional checker. Import it
    # only when the caller explicitly selects the provider contract.
    if __package__:
        from . import framework_provider_policy
    else:
        import framework_provider_policy
    return framework_provider_policy


def _evolution_base_module():
    # Older private bundles deliberately omit this explicit base profile.
    if __package__:
        from . import evolution_policy_base
    else:
        import evolution_policy_base
    return evolution_policy_base


def _check_provider_binding(base, provider):
    required = provider["required_contracts"]
    require(required["oem_policy"] == {"path": CONTRACT_PATH, "sha256": CONTRACT_SHA256}
            and required["init_helper"] == {key: base["required_capability_contract"][key]
                                            for key in ("path", "sha256")},
            "provider profile does not bind the selected OEM and helper contracts")
    require(provider["device"] == base["device"]["codename"]
            and provider["platform"] == base["platform"]
            and provider["factory_package_sha256"] == base["factory_package_sha256"],
            "provider profile uses a different device, platform, or factory")
    require(not set(provider["types"]) & set(base["types"]),
            "provider profile duplicates an OEM or property source owner")


def _compose_contract(base, properties):
    require(properties["base_oem_contract"] == {"path": CONTRACT_PATH, "sha256": CONTRACT_SHA256,
                                               "size_bytes": 12375},
            "property profile does not bind the frozen three-type OEM contract")
    require(properties["factory_package_sha256"] == base["factory_package_sha256"]
            and properties["required_capability_contract"] == base["required_capability_contract"]
            and properties["platform"] == base["platform"],
            "property profile uses a different factory, capability, or platform")
    require(not set(properties["types"]).intersection(base["types"]), "property profile duplicates a base OEM type")
    result = copy.deepcopy(base)
    result["types"].update(properties["types"])
    duplicate_owners = result["duplicate_declarations"]["expected_factory_type_declarations"]
    duplicate_owners[INPUT_FLAGS["factory_pub"]].extend(properties["types"])
    result["native_read_clauses"] = copy.deepcopy(properties["read_clauses"])
    return result


def _property_context_rows(raw, *, source=False):
    try:
        text = raw.decode("ascii")
    except UnicodeError as exc:
        raise OemPolicyError("property contexts must be ASCII") from exc
    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        require("#" not in line, "inline property context comments are not part of the reviewed native syntax")
        words = line.split()
        require(len(words) in ({2} if source else {2, 3}),
                "property contexts must preserve the original untyped prefix semantics")
        require(re.fullmatch(r"[A-Za-z0-9_.-]+", words[0]) and words[1].startswith("u:object_r:")
                and words[1].endswith(":s0") and (len(words) == 2 or words[2] == "prefix"),
                "property context syntax or prefix matching differs")
        result.append({"property_pattern": words[0], "context": words[1], "match": "prefix", "value_type": None})
    return result


def verify_property_source_contents(contents, contract):
    require(set(contents) == {row["path"] for row in contract["source_files"]}, "property source file set differs")
    declarations, reads, contexts = [], [], []
    for row in contract["source_files"]:
        raw = contents[row["path"]]
        require(vp.sha(raw) == row["sha256"] and len(raw) == row["size_bytes"], "property source hash or size differs")
        if row["kind"] == "property_contexts":
            contexts.extend(_property_context_rows(raw, source=True))
            continue
        try:
            text = raw.decode("ascii")
        except UnicodeError as exc:
            raise OemPolicyError("property source must be ASCII") from exc
        lines = [line.split("#", 1)[0].strip() for line in text.splitlines()]
        for line in filter(None, lines):
            if row["kind"] == "system_public_prop":
                match = re.fullmatch(r"system_public_prop\(([A-Za-z_][A-Za-z0-9_]*)\)", line)
                require(match is not None, "only reviewed system_public_prop declarations are permitted")
                declarations.append(match.group(1))
            elif row["kind"] == "get_prop":
                match = re.fullmatch(r"get_prop\(([A-Za-z_][A-Za-z0-9_]*),\s*([A-Za-z_][A-Za-z0-9_]*)\)", line)
                require(match is not None, "only reviewed get_prop reads are permitted")
                reads.append((match.group(1), match.group(2)))
            else:
                raise OemPolicyError("unknown property source kind")
    require(Counter(declarations) == Counter({name: 1 for name in contract["types"]}),
            "public property declarations are missing, duplicated, or unreviewed")
    require(Counter(reads) == Counter((row["source_type"], row["target_type"]) for row in contract["read_clauses"]),
            "property reads are missing, duplicated, or unreviewed")
    expected_contexts = [{key: row[key] for key in ("property_pattern", "context", "match", "value_type")}
                         for row in contract["property_contexts"]]
    require(Counter(tuple(sorted(row.items())) for row in contexts)
            == Counter(tuple(sorted(row.items())) for row in expected_contexts),
            "property context patterns, labels, or matching semantics differ")
    return {"declarations": sorted(declarations), "read_clauses": contract["read_clauses"], "property_contexts": contexts}


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


def verify_sources(source_root, contract_path=None, capability_path=None, property_contract_path=None,
                   provider_contract_path=None):
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
    property_result = None
    if property_contract_path is not None:
        properties = load_property_contract(property_contract_path, reader)
        _compose_contract(contract, properties)
        expected_property_files = {source_root / row["path"] for row in properties["source_files"]}
        for parent in {path.parent for path in expected_property_files}:
            vp.real_directory(parent)
            require(set(parent.iterdir()) == {path for path in expected_property_files if path.parent == parent},
                    "unreviewed file or directory in a property source directory")
        property_contents = {row["path"]: reader.read(source_root / row["path"], row["sha256"], row["size_bytes"])
                             for row in properties["source_files"]}
        property_result = verify_property_source_contents(property_contents, properties)
    provider_result = None
    if provider_contract_path is not None:
        fp = _provider_module()
        provider = fp.load_contract(provider_contract_path, reader)
        _check_provider_binding(_compose_contract(contract, properties) if property_result is not None else contract,
                                provider)
        provider_input_contract = provider["required_contracts"]["provider_inputs"]
        reader.read(source_root / provider_input_contract["path"], provider_input_contract["sha256"])
        provider_files = {source_root / row["path"] for row in provider["source_files"]}
        for parent in {path.parent for path in provider_files}:
            vp.real_directory(parent)
            require(set(parent.iterdir()) == {path for path in provider_files if path.parent == parent},
                    "unreviewed file or directory in a provider source directory")
        provider_contents = {row["path"]: reader.read(source_root / row["path"], row["sha256"], row["size_bytes"])
                             for row in provider["source_files"]}
        provider_result = fp.verify_source_contents(provider_contents, provider)
    reader.recheck()
    result = {"schema_version": 1, "operation": "verify-nezha-oem-policy-sources", "status": "verified",
            "contract_id": contract["contract_id"], "contract_sha256": CONTRACT_SHA256,
            "declarations": declarations, "source_files": contract["source_files"],
            "capability_contract_sha256": vp.sha(capability),
            "all_inputs_rehashed_unchanged": True, "input_bindings": list(reader.bindings.values()),
            "scope": dict(SCOPE)}
    if property_result is not None:
        result["property_contract_id"] = properties["contract_id"]
        result["property_contract_sha256"] = PROPERTY_CONTRACT_SHA256
        result["property_source_files"] = properties["source_files"]
        result["property_source_verification"] = property_result
    if provider_result is not None:
        result["provider_contract_id"] = provider["contract_id"]
        result["provider_contract_sha256"] = fp.CONTRACT_SHA256
        result["provider_source_files"] = provider["source_files"]
        result["provider_source_verification"] = provider_result
        result["provider_artifact_bundle_verified"] = False
    return result


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


def _property_effective_allow_edges(policy, properties):
    """Check both directions of every ordinary edge involving a property type.

    This includes inherited framework grants, retained vendor grants activated
    by the singleton mappings, and the property-to-tmpfs associate permission.
    It is a finite type-enforcement check, not an MLS or runtime access proof.
    """
    names = set(properties["types"])
    edges = set()
    for form in policy.by_head["allow"]:
        cls, permissions = _classes(form)
        source = policy.resolve(form.expr[1])
        if form.expr[2] == "self":
            for name in source & names:
                edges.update((name, name, cls, permission) for permission in permissions)
            continue
        target = policy.resolve(form.expr[2])
        for src in source & names:
            for tgt in target:
                edges.update((src, tgt, cls, permission) for permission in permissions)
        for tgt in target & names:
            for src in source:
                edges.update((src, tgt, cls, permission) for permission in permissions)
    actual = {}
    for name in sorted(names):
        selected = sorted(edge for edge in edges if name in edge[:2])
        raw = b"".join(json.dumps(row, separators=(",", ":")).encode() + b"\n" for row in selected)
        actual[name] = {"count": len(selected), "sha256_sorted_compact_json_rows": vp.sha(raw)}
    return actual


def _property_effective_allow_budget(policy, properties, *, reference=None):
    actual = _property_effective_allow_edges(policy, properties)
    expected = (properties["native_effective_ordinary_allow_edges"] if reference is None else
                _property_effective_allow_edges(reference, properties))
    require(actual == expected,
            "property effective ordinary permissions differ from the reviewed finite edge budget" if reference is None
            else "property effective ordinary permissions differ from the independent Evolution base plus owned budget")
    return actual


def _provider_anonymous_ownership(parsed, policy, membership_budget):
    """A new private registration expression cannot alter an inherited rule.

    Generated names are not a grant exemption. Compare inherited attributes to
    an auxiliary symbol table using the independently admitted named membership
    budget and new types, without source-owned assignments to inherited
    anonymous names. Legitimate closure growth from new domains is preserved.
    The original complete inputs remain untouched for every other guard.
    """
    outside_references, outside_declarations = set(), set()
    outside_expansions = set()
    for runtime, forms in parsed.items():
        if runtime == INPUT_FLAGS["system_ext_cil"]:
            continue
        for form in forms:
            expr = form.expr
            pending = [expr]
            while pending:
                item = pending.pop()
                if isinstance(item, str):
                    if item.startswith("base_typeattr_"):
                        outside_references.add(item)
                else:
                    pending.extend(item)
            if expr[0] == "typeattribute":
                outside_declarations.add(expr[1])
            elif expr[0] == "expandtypeattribute":
                outside_expansions.add(expr)
    changed_assignments = set()
    for form in parsed[INPUT_FLAGS["system_ext_cil"]]:
        expr = form.expr
        if expr[0] in {"typeattribute", "typeattributeset"} and expr[1] in outside_references:
            require(expr[1] in outside_declarations,
                    "provider source cannot redefine an inherited anonymous attribute")
            if expr[0] == "typeattributeset":
                changed_assignments.add(expr[1])
        elif expr[0] == "expandtypeattribute":
            require(len(expr) == 3 and isinstance(expr[1], tuple), "unsupported source attribute expansion")
            if outside_references & set(expr[1]):
                require(expr in outside_expansions,
                        "provider source cannot change inherited anonymous attribute expansion")
    if not changed_assignments:
        return
    reference_forms = []
    for runtime, forms in parsed.items():
        for form in forms:
            if runtime == INPUT_FLAGS["system_ext_cil"] and form.expr[0] == "typeattributeset":
                name = form.expr[1]
                if name in membership_budget or name in outside_references:
                    continue
            reference_forms.append(form)
    # Use literal members computed from the isolated platform and explicit
    # contracts, never the actual system_ext expressions as their own budget.
    modeled = "\n".join(vp.render(("typeattributeset", attr, tuple(sorted(members))))
                         for attr, members in sorted(membership_budget.items()))
    reference_forms.extend(vp.parse(modeled.encode(), INPUT_FLAGS["system_ext_cil"]))
    reference = vp.Policy(reference_forms)
    for name in sorted(changed_assignments):
        require(policy.resolve(name) == reference.resolve(name),
                "provider source changes an inherited anonymous attribute beyond admitted type memberships")


def _declaration_only_outputs(ext_forms, mapping_forms, policy, contract, platform_forms, provider_contract=None):
    """Keep the three-type default and explicit property read budget separate.

    Native filtering can retain generated negative assertions and base-type
    expressions. The explicit property profile adds only its two literal read
    clauses. The optional provider profile contributes its independently bounded
    forms and private declarations. No profile admits other permissions,
    transitions, named memberships, roles, or public mappings from this slice.
    """
    allowed = {"type", "typeattribute", "typeattributeset", "roletype",
               "expandtypeattribute", "neverallow", "neverallowx"}
    expected_reads = contract.get("native_read_clauses", [])
    source_types = dict(contract["types"])
    provider_budget = Counter()
    if provider_contract is not None:
        fp = _provider_module()
        provider_budget = fp.expected_native_forms(provider_contract)
        source_types.update(provider_contract["types"])
        allowed.update(expr[0] for expr in provider_budget)
    if expected_reads:
        allowed.add("allow")
    require(all(form.expr[0] in allowed for form in ext_forms),
            "declaration-only system_ext output contains a permission, transition, or unsupported form")
    source_grants = Counter()
    for form in ext_forms:
        if provider_contract is not None and form.expr[0] in {"allow", "dontaudit", "typetransition"}:
            source_grants[fp.normalized_form(form.expr)] += 1
        elif form.expr[0] == "allow":
            cls, permissions = _classes(form)
            source_grants[("allow", form.expr[1], form.expr[2], (cls, tuple(sorted(permissions))))] += 1
    expected_source = Counter(("allow", row["source_type"], row["target_type"],
                               (row["class"], tuple(row["permissions"]))) for row in expected_reads)
    expected_source.update(provider_budget)
    require(source_grants == expected_source,
            "source permissions differ from the explicit provider and property budgets" if provider_contract is not None
            else "source permissions differ from the explicitly reviewed property read clauses")
    expected_members = {}
    for name, spec in source_types.items():
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
            require(len(expr) == 3 and expr[1] == "object_r" and expr[2] in source_types,
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
    return membership_budget


def check_native_contents(corpus, original_vendor, contract, capability, property_contract=None, property_contexts=None,
                          provider_contract=None, provider_file_contexts=None, provider_service_contexts=None,
                          evolution_base_contract=None, evolution_base_inputs=None, system_ext_public_cil=None,
                          camera_property_contract=None, factory_contexts_contract=None,
                          factory_property_contexts=None):
    """Static checks of actual compiler inputs, not a substitute for compilation."""
    require(list(corpus) == list(INPUT_FLAGS.values()), "native CIL input order or set differs")
    evolution_selected = evolution_base_contract is not None
    require(evolution_selected == (evolution_base_inputs is not None)
            and evolution_selected == (system_ext_public_cil is not None),
            "Evolution base contract, complete native references, and full exporter must be selected together")
    require(camera_property_contract is None or evolution_selected,
            "camera property capability requires the complete explicit Evolution base profile")
    require((factory_contexts_contract is None) == (factory_property_contexts is None),
            "factory context capability and four complete context inputs must be selected together")
    require(factory_contexts_contract is None or camera_property_contract is not None,
            "factory context capability requires the explicit camera capability")
    if evolution_selected:
        require(property_contract is not None and provider_contract is not None,
                "Evolution base requires the explicit property and provider profiles")
        eb = _evolution_base_module()
        required = evolution_base_contract["required_contracts"]
        require(required == {
            "oem_policy": {"path": CONTRACT_PATH, "sha256": CONTRACT_SHA256, "size_bytes": 12375},
            "oem_properties": {"path": PROPERTY_CONTRACT_PATH, "sha256": PROPERTY_CONTRACT_SHA256,
                               "size_bytes": 65716},
            "framework_provider_policy": {"path": _provider_module().CONTRACT_PATH,
                "sha256": _provider_module().CONTRACT_SHA256, "size_bytes": 34809},
        } and evolution_base_contract["device"] == contract["device"]
            and evolution_base_contract["platform"] == contract["platform"]
            and evolution_base_contract["build_variant"] == "user",
            "Evolution base does not bind the selected device, platform, variant, and owned contracts")
    if property_contract is not None:
        contract = _compose_contract(contract, property_contract)
        require(property_contexts is not None, "the property profile requires its current native context output")
        expected_contexts = [{key: row[key] for key in ("property_pattern", "context", "match", "value_type")}
                             for row in property_contract["property_contexts"]]
        if evolution_selected:
            selectors = {row["property_pattern"] for row in expected_contexts}
            observed_contexts = [dict(zip(("property_pattern", "context", "match", "value_type"), row))
                                 for row in eb._context_rows(property_contexts, "property_contexts")
                                 if row[0] in selectors]
            # Every remaining row is independently checked as a base row below.
        else:
            observed_contexts = _property_context_rows(property_contexts)
        require(Counter(tuple(sorted(row.items())) for row in observed_contexts)
                == Counter(tuple(sorted(row.items())) for row in expected_contexts),
                "native property context output differs from the eight reviewed prefixes")
    else:
        require(property_contexts is None, "property contexts cannot silently enable the property profile")
    provider_context_result = None
    if provider_contract is not None:
        _check_provider_binding(contract, provider_contract)
        require(provider_file_contexts is not None and provider_service_contexts is not None,
                "the provider profile requires both current native context outputs")
        fp = _provider_module()
        provider_context_result = fp.verify_native_contexts(provider_file_contexts, provider_service_contexts,
                                                            provider_contract)
    else:
        require(provider_file_contexts is None and provider_service_contexts is None,
                "provider contexts cannot silently enable the provider profile")
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
    evolution_result = None
    if evolution_selected:
        evolution_result = eb.check_composition(
            corpus, parsed, policy, contract, property_contract, provider_contract,
            evolution_base_inputs, evolution_base_contract,
            {"property_contexts": property_contexts, "file_contexts": provider_file_contexts,
             "service_contexts": provider_service_contexts}, system_ext_public_cil,
            camera_contract=camera_property_contract, factory_contexts_contract=factory_contexts_contract,
            factory_property_contexts=factory_property_contexts)
        membership_budget = evolution_result["membership_budget"]
    else:
        membership_budget = _declaration_only_outputs(ext_forms, mapping_forms, policy, contract,
                                                       parsed[INPUT_FLAGS["platform_cil"]], provider_contract)
    expected_types = set(contract["types"])
    all_source_types = expected_types | (set(provider_contract["types"]) if provider_contract is not None else set())
    if evolution_result is not None:
        all_source_types |= evolution_result["base_types"]
    source_types = Counter(form.expr[1] for form in ext_forms if form.expr[0] == "type")
    require(source_types == Counter({name: 1 for name in all_source_types}),
            "system_ext must own exactly the explicitly reviewed OEM type declarations")
    if provider_contract is not None and not evolution_selected:
        # The explicit Evolution profile already checks every inherited
        # attribute against the independent native base plus owned contracts,
        # including definition counts. The older isolation check assumes a
        # platform-only reference and cannot represent that selected base.
        _provider_anonymous_ownership(parsed, policy, membership_budget)
    original_factory = {runtime: parsed[runtime] for runtime in (INPUT_FLAGS["factory_pub"], INPUT_FLAGS["factory_odm"])}
    original_factory[vendor_runtime] = vp.parse(original_vendor, vendor_runtime)
    for runtime, names in contract["duplicate_declarations"]["expected_factory_type_declarations"].items():
        relevant = Counter(form.expr[1] for form in original_factory[runtime]
                           if form.expr[0] == "type" and form.expr[1] in expected_types)
        require(relevant == Counter({name: 1 for name in names}), "factory duplicate declaration ownership differs")

    domains = policy.resolve("domain")
    core_domains = policy.resolve("coredomain")
    roles = policy.role_bindings()
    read_sources = {}
    for clause in contract.get("native_read_clauses", []):
        name = clause["source_type"]
        spec = clause["source_classification"]
        require(name in policy.types and name not in policy.attrs and name not in policy.aliases
                and policy.resolve(name) == {name} and name in domains and name in core_domains
                and roles.get(name, set()) == set(spec["roles"]),
                "property reader must remain the reviewed concrete singleton core process type")
        owners = Counter(form.runtime for form in policy.by_head["type"] if form.expr[1] == name)
        require(owners == Counter(spec["declaration_owners"]), "property reader declaration ownership differs")
        read_sources[name] = {"domain": True, "coredomain": True, "roles": sorted(roles[name]),
                              "concrete_singleton": True, "declaration_owners": dict(owners)}
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

    result = {"schema_version": 1, "operation": "check-nezha-oem-native-policy-inputs", "status": "verified",
            "contract_id": contract["contract_id"], "contract_sha256": CONTRACT_SHA256,
            "type_ownership": observed, "helper_effective_property_set_grants": 0,
            "original_factory_inputs_preserved": True, "existing_binder_derivation_preserved": True,
            "permissive_cil_declarations": 0,
            "assertion_statement_counts": {head: len(policy.by_head[head]) for head in ("neverallow", "neverallowx")},
            "scope": dict(SCOPE)}
    if property_contract is not None:
        result["property_contract_id"] = property_contract["contract_id"]
        result["property_contract_sha256"] = PROPERTY_CONTRACT_SHA256
        result["property_contexts_verified"] = observed_contexts
        result["explicit_source_read_clauses"] = property_contract["read_clauses"]
        result["property_read_sources"] = read_sources
        result["property_effective_ordinary_allow_edges"] = _property_effective_allow_budget(
            policy, property_contract, reference=evolution_result["reference"] if evolution_result is not None else None)
    if provider_contract is not None:
        # Validate the original full corpus. Nothing is removed to make the
        # older OEM or property checks pass; their own budgets remain enforced.
        result["provider_policy_verification"] = fp.check_native_extension(policy, parsed, provider_contract)
        result["provider_context_verification"] = provider_context_result
        result["provider_contract_id"] = provider_contract["contract_id"]
        result["provider_contract_sha256"] = fp.CONTRACT_SHA256
    if evolution_result is not None:
        result["evolution_policy_base_verification"] = evolution_result["result"]
        result["property_effective_edge_budget_basis"] = "independent-native-evolution-base-plus-owned-contracts"
        result["legacy_property_edge_budget_reused_as_current"] = False
    return result


def check_native(inputs, original_vendor, capability_path, *, contract_path=None, tool_source=None,
                 property_contract_path=None, property_contexts_path=None, provider_contract_path=None,
                 provider_file_contexts_path=None, provider_service_contexts_path=None,
                 evolution_base_contract_path=None, evolution_base_inputs=None,
                 system_ext_public_cil_path=None, evolution_base_source_files=None,
                 camera_property_contract_path=None, factory_contexts_contract_path=None,
                 factory_property_context_paths=None):
    reader = vp.Reader()
    contract = load_contract(contract_path, reader)
    require((property_contract_path is None) == (property_contexts_path is None),
            "property contract and native property contexts must be selected together")
    properties = load_property_contract(property_contract_path, reader) if property_contract_path is not None else None
    property_contexts = reader.read(property_contexts_path) if property_contexts_path is not None else None
    provider_selected = provider_contract_path is not None
    require(provider_selected == (provider_file_contexts_path is not None)
            and provider_selected == (provider_service_contexts_path is not None),
            "provider contract and both native contexts must be selected together")
    provider = _provider_module().load_contract(provider_contract_path, reader) if provider_selected else None
    provider_files = reader.read(provider_file_contexts_path) if provider_selected else None
    provider_services = reader.read(provider_service_contexts_path) if provider_selected else None
    evolution_selected = evolution_base_contract_path is not None
    require(evolution_selected == (evolution_base_inputs is not None)
            and evolution_selected == (system_ext_public_cil_path is not None)
            and evolution_selected == (evolution_base_source_files is not None),
            "Evolution base contract, references, exporter, and exact source list must be selected together")
    require(camera_property_contract_path is None or evolution_selected,
            "camera property capability requires the complete explicit Evolution base profile")
    require((factory_contexts_contract_path is None) == (factory_property_context_paths is None),
            "factory context capability and four complete context inputs must be selected together")
    require(factory_contexts_contract_path is None or camera_property_contract_path is not None,
            "factory context capability requires the explicit camera capability")
    evolution_contract = evolution_inputs = full_public = source_files = camera_contract = None
    factory_contexts_contract = factory_contexts = None
    if evolution_selected:
        require(provider_selected and properties is not None,
                "Evolution base requires the explicit property and provider profiles")
        eb = _evolution_base_module()
        evolution_contract = eb.load_contract(evolution_base_contract_path, reader)
        if camera_property_contract_path is not None:
            camera_contract = eb.load_camera_contract(camera_property_contract_path, reader)
        if factory_contexts_contract_path is not None:
            factory_contexts_contract = eb.load_factory_contexts_contract(factory_contexts_contract_path, reader)
            require(set(factory_property_context_paths) == set(eb.FACTORY_CONTEXT_FLAGS)
                    and all(path is not None for path in factory_property_context_paths.values()),
                    "factory capability requires all four complete property context inputs")
            factory_contexts = {role: reader.read(factory_property_context_paths[flag])
                                for flag, role in eb.FACTORY_CONTEXT_FLAGS.items()}
        require(set(evolution_base_inputs) == set(eb.INPUT_FLAGS)
                and all(path is not None for path in evolution_base_inputs.values()),
                "native Evolution reference input flags differ or are incomplete")
        evolution_inputs = {role: reader.read(evolution_base_inputs[flag]) for flag, role in eb.INPUT_FLAGS.items()}
        full_public = reader.read(system_ext_public_cil_path)
        source_files = eb.verify_source_files(evolution_base_source_files, evolution_contract, reader,
                                               camera_contract=camera_contract,
                                               factory_contexts_contract=factory_contexts_contract)
    require(set(inputs) == set(INPUT_FLAGS), "native input flags differ")
    corpus = {runtime: reader.read(inputs[flag]) for flag, runtime in INPUT_FLAGS.items()}
    original = reader.read(original_vendor)
    capability = reader.read(capability_path)
    source = Path(tool_source) if tool_source is not None else Path(__file__)
    tool_names = ["oem_policy.py", "vendor_policy.py", "artifact_files.py"]
    if provider_selected:
        tool_names.append("framework_provider_policy.py")
    if evolution_selected:
        tool_names.append("evolution_policy_base.py")
    tools = {name: vp.sha(reader.read(source.with_name(name))) for name in tool_names}
    result = check_native_contents(corpus, original, contract, capability, properties, property_contexts,
                                   provider, provider_files, provider_services,
                                   evolution_contract, evolution_inputs, full_public,
                                   camera_property_contract=camera_contract,
                                   factory_contexts_contract=factory_contexts_contract,
                                   factory_property_contexts=factory_contexts)
    if evolution_selected:
        result["evolution_policy_base_source_files"] = source_files
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
    source.add_argument("--property-contract", type=Path)
    source.add_argument("--provider-contract", type=Path)
    source.add_argument("--output", type=Path)
    native = commands.add_parser("check-native")
    native.add_argument("--contract", required=True, type=Path)
    native.add_argument("--capability-contract", required=True, type=Path)
    native.add_argument("--factory-vendor", required=True, type=Path)
    native.add_argument("--tool-source", type=Path)
    native.add_argument("--property-contract", type=Path)
    native.add_argument("--system-ext-property-contexts", type=Path)
    native.add_argument("--provider-contract", type=Path)
    native.add_argument("--system-ext-file-contexts", type=Path)
    native.add_argument("--system-ext-service-contexts", type=Path)
    native.add_argument("--evolution-policy-base-contract", type=Path)
    native.add_argument("--camera-property-capability-contract", type=Path)
    native.add_argument("--factory-property-contexts-capability-contract", type=Path)
    native.add_argument("--system-ext-public-cil", type=Path)
    native.add_argument("--evolution-base-source-files", nargs="+", type=Path)
    # Do not import the optional helper while parsing a legacy bundle command.
    evolution_flags = ("evolution_base_system_ext_cil", "evolution_base_system_ext_mapping",
                       "evolution_base_public_cil", "evolution_base_property_contexts",
                       "evolution_base_file_contexts", "evolution_base_service_contexts")
    for flag in evolution_flags:
        native.add_argument("--" + flag.replace("_", "-"), type=Path)
    factory_context_flags = ("platform_property_contexts", "product_property_contexts",
                             "factory_vendor_property_contexts", "factory_odm_property_contexts")
    for flag in factory_context_flags:
        native.add_argument("--" + flag.replace("_", "-"), type=Path)
    native.add_argument("--output", type=Path)
    for flag in INPUT_FLAGS:
        native.add_argument("--" + flag.replace("_", "-"), required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify-sources":
            result = verify_sources(args.source_root, args.contract, args.capability_contract, args.property_contract,
                                     args.provider_contract)
        else:
            result = check_native({flag: getattr(args, flag) for flag in INPUT_FLAGS}, args.factory_vendor,
                                  args.capability_contract, contract_path=args.contract, tool_source=args.tool_source,
                                  property_contract_path=args.property_contract,
                                  property_contexts_path=args.system_ext_property_contexts,
                                  provider_contract_path=args.provider_contract,
                                  provider_file_contexts_path=args.system_ext_file_contexts,
                                  provider_service_contexts_path=args.system_ext_service_contexts,
                                  evolution_base_contract_path=args.evolution_policy_base_contract,
                                  evolution_base_inputs=({flag: getattr(args, flag) for flag in evolution_flags}
                                      if any(getattr(args, flag) is not None for flag in evolution_flags) else None),
                                  system_ext_public_cil_path=args.system_ext_public_cil,
                                  evolution_base_source_files=args.evolution_base_source_files,
                                  camera_property_contract_path=args.camera_property_capability_contract,
                                  factory_contexts_contract_path=args.factory_property_contexts_capability_contract,
                                  factory_property_context_paths=(
                                      {flag: getattr(args, flag) for flag in factory_context_flags}
                                      if any(getattr(args, flag) is not None for flag in factory_context_flags) else None))
        _write_result(result, args.output)
    except (OSError, ValueError) as exc:
        print(f"oem-policy: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
