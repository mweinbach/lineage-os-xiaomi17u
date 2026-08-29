#!/usr/bin/env python3
"""Reproduce the reviewed Nezha factory Binder correction from exact CIL inputs.

This is a private vendor-input derivation, not a policy compiler or image builder.
It reclassifies the pinned v9 corpus, removes only the 67 reviewed ill-typed
Binder grants, and requires the exact previously validated output hash. Original
inputs, assertions, valid Binder grants, FD grants, and all other bytes remain
unchanged. New source policy still requires a strict compiler and context tests.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import tempfile

if __package__:
    from .artifact_files import publish_new_directory
else:
    from artifact_files import publish_new_directory


WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_SHA256 = "6adafb4ada4a96a926289009a43ec8039d2b7108572f52b938d575d29de3990b"
PLATFORM_RUNTIME = "/system/etc/selinux/plat_sepolicy.cil"
MAX_BYTES, MAX_TOKENS, MAX_DEPTH = 16 * 1024 * 1024, 2_000_000, 256
BINDER_PERMISSIONS = frozenset({"call", "transfer", "impersonate", "set_context_mgr"})
TOKEN = re.compile(rb';[^\n]*|"(?:\\.|[^"\\])*"|[()]|[^\s();"]+')


class VendorPolicyError(ValueError):
    """The exact-input derivation contract was not satisfied."""


def require(condition, message):
    if not condition:
        raise VendorPolicyError(message)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def encoded(value):
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()


def identity(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size,
            info.st_mtime_ns, info.st_ctime_ns)


def real_directory(path):
    path = Path(os.path.abspath(path))
    for parent in [*reversed(path.parents), path]:
        require(stat.S_ISDIR(parent.lstat().st_mode), "directory or ancestor is a symlink/non-directory")
    return path


class Reader:
    """Hash bounded regular files and detect replacement during the operation."""

    def __init__(self):
        self.bindings = {}

    def read(self, path, expected_sha=None, expected_size=None):
        path = Path(os.path.abspath(path))
        real_directory(path.parent)
        before = path.lstat()
        require(stat.S_ISREG(before.st_mode) and 0 <= before.st_size <= MAX_BYTES,
                "input is not a bounded regular file")
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
            require(identity(before) == identity(os.fstat(stream.fileno())), "input replaced before read")
            data = stream.read(MAX_BYTES + 1)
            require(len(data) == before.st_size and identity(before) == identity(os.fstat(stream.fileno()))
                    == identity(path.lstat()), "input changed during read")
        require(expected_sha is None or sha(data) == expected_sha, "input SHA256 mismatch")
        require(expected_size is None or len(data) == expected_size, "input byte count mismatch")
        row = {"path": str(path), "sha256": sha(data), "size_bytes": len(data),
               "identity": list(identity(before))}
        require(path not in self.bindings or self.bindings[path] == row, "input changed between reads")
        self.bindings[path] = row
        return data

    def recheck(self):
        for path, row in list(self.bindings.items()):
            self.read(path, row["sha256"], row["size_bytes"])


def load_contract(path=None, reader=None):
    reader = reader or Reader()
    path = path or WORKSPACE_ROOT / "config/vendor-policy-correction.json"
    # A custom path supports a copied Linux control bundle, not alternate rules.
    raw = reader.read(path, CONTRACT_SHA256)
    return json.loads(raw)


@dataclass(frozen=True)
class Form:
    expr: tuple
    start: int
    end: int
    line: int
    end_line: int
    runtime: str


def freeze(value):
    return tuple(freeze(item) for item in value) if isinstance(value, list) else value


def render(value):
    return "(" + " ".join(render(item) for item in value) + ")" if isinstance(value, tuple) else value


def parse(data, runtime=""):
    """Offset-preserving flat-form parser adapted from the reviewed prototype.

    Strings and comments are tokens, never reparsed as rules. The finite policy
    model below rejects constructs whose nested semantics it does not implement.
    """
    require(isinstance(data, bytes) and len(data) <= MAX_BYTES and b"\0" not in data,
            "unsupported CIL size or NUL")
    try:
        data.decode("utf-8", "strict")
    except UnicodeError as exc:
        raise VendorPolicyError("CIL must be UTF-8") from exc
    roots, stack, line, previous, count = [], [], 1, 0, 0
    for match in TOKEN.finditer(data):
        gap = data[previous:match.start()]
        require(not gap.strip(), "unparsed CIL token gap")
        line += gap.count(b"\n")
        token_line, raw = line, match.group()
        line += raw.count(b"\n")
        previous = match.end()
        count += 1
        require(count <= MAX_TOKENS, "CIL token limit")
        if raw.startswith(b";"):
            continue
        if raw == b"(":
            stack.append(([], match.start(), token_line))
            require(len(stack) <= MAX_DEPTH, "CIL depth limit")
        elif raw == b")":
            require(stack, "unbalanced closing parenthesis")
            items, start, first_line = stack.pop()
            if stack:
                stack[-1][0].append(items)
            else:
                require(items and isinstance(items[0], str), "invalid top-level CIL form")
                roots.append(Form(freeze(items), start, match.end(), first_line, token_line, runtime))
        else:
            require(stack, "atom outside CIL form")
            stack[-1][0].append(raw.decode("utf-8"))
    require(not stack and not data[previous:].strip(), "unbalanced or unparsed CIL input")
    return roots


class Policy:
    """Finite type/role closure; never guesses semantics of unsupported forms."""

    def __init__(self, forms):
        self.forms = forms
        self.by_head = defaultdict(list)
        for form in forms:
            self.by_head[form.expr[0]].append(form)
        forbidden = {"block", "blockabstract", "blockinherit", "in", "macro", "call",
                     "booleanif", "tunableif", "optional", "classpermission", "classpermissionset",
                     "classmap", "classmapping", "permissionx", "deny"}
        require(not forbidden.intersection(self.by_head), "unsupported nested or permission semantics")
        self.types = self.declarations("type")
        self.attrs = self.declarations("typeattribute")
        self.roles = self.declarations("role")
        self.roleattrs = self.declarations("roleattribute")
        aliases = self.declarations("typealias")
        self.aliases = {}
        for form in self.by_head["typealiasactual"]:
            expr = form.expr
            require(len(expr) == 3 and all(isinstance(item, str) for item in expr)
                    and expr[1] in aliases and expr[1] not in self.aliases, "invalid or duplicate alias definition")
            self.aliases[expr[1]] = expr[2]
        require(aliases == set(self.aliases), "unbound type alias")
        require(not (self.types & self.attrs or self.types & aliases or self.attrs & aliases
                     or self.roles & self.roleattrs), "ambiguous type or role namespace")
        self.assignments = self.assignments_for("typeattributeset", self.attrs)
        self.roleassignments = self.assignments_for("roleattributeset", self.roleattrs)
        self.cache, self.active, self.rolecache, self.roleactive = {}, set(), {}, set()

    def declarations(self, head):
        result = set()
        for form in self.by_head[head]:
            require(len(form.expr) == 2 and isinstance(form.expr[1], str), "unsupported declaration")
            result.add(form.expr[1])
        return result

    def assignments_for(self, head, declared):
        result = defaultdict(list)
        for form in self.by_head[head]:
            require(len(form.expr) == 3 and isinstance(form.expr[1], str)
                    and form.expr[1] in declared, "invalid or undeclared attribute assignment")
            result[form.expr[1]].append(form.expr[2])
        return result

    @staticmethod
    def evaluate(expr, symbol, universe):
        if isinstance(expr, str):
            return symbol(expr)
        require(isinstance(expr, tuple), "unsupported set expression")
        if not expr:
            return frozenset()
        op, *args = expr
        if isinstance(op, str) and op in {"and", "or", "not", "xor", "all"}:
            if op == "all":
                require(not args, "all takes no operands")
                return frozenset(universe)
            if op == "not":
                require(len(args) == 1, "not takes one operand")
                return frozenset(universe) - Policy.evaluate(args[0], symbol, universe)
            require(args, "empty logical expression")
            result = Policy.evaluate(args[0], symbol, universe)
            for arg in args[1:]:
                other = Policy.evaluate(arg, symbol, universe)
                result = result & other if op == "and" else result | other if op == "or" else result ^ other
            return result
        result = frozenset()
        for arg in expr:
            result |= Policy.evaluate(arg, symbol, universe)
        return result

    def _resolve(self, name, *, role=False):
        require(isinstance(name, str), "endpoint must be a type or attribute symbol")
        types, attrs = (self.roles, self.roleattrs) if role else (self.types, self.attrs)
        cache, active = (self.rolecache, self.roleactive) if role else (self.cache, self.active)
        assignments, aliases = (self.roleassignments, {}) if role else (self.assignments, self.aliases)
        if name in types:
            return frozenset({name})
        if name in cache:
            return cache[name]
        require(name not in active, "cyclic type/role attribute or alias")
        require(name in attrs or name in aliases, "unknown type/role attribute or alias")
        active.add(name)
        try:
            resolve = lambda item: self._resolve(item, role=role)
            result = resolve(aliases[name]) if name in aliases else frozenset()
            for expr in assignments[name]:
                result |= self.evaluate(expr, resolve, types)
            cache[name] = result
            return result
        finally:
            active.remove(name)

    def resolve(self, name):
        return self._resolve(name)

    def role_bindings(self):
        result = defaultdict(set)
        for form in self.by_head["roletype"]:
            require(len(form.expr) == 3, "unsupported roletype")
            for role in self._resolve(form.expr[1], role=True):
                for concrete in self.resolve(form.expr[2]):
                    result[concrete].add(role)
        return result


def rule_class(form):
    expr = form.expr
    return expr[3][0] if len(expr) == 4 and isinstance(expr[3], tuple) and expr[3] else None


def binder_rules(policy):
    require([form.expr for form in policy.by_head["class"] if form.expr[1] == "binder"]
            == [("class", "binder", ("impersonate", "call", "set_context_mgr", "transfer"))],
            "Binder class definition changed")
    require(not any(form.expr[1] == "binder" for form in policy.by_head["classcommon"]),
            "Binder common permission semantics unsupported")
    for form in policy.by_head["allowx"]:
        expr = form.expr
        require(len(expr) == 4 and isinstance(expr[3], tuple) and len(expr[3]) == 3,
                "extended allow shape unsupported")
        require(expr[3][1] != "binder", "extended Binder allow semantics unsupported")
    result = []
    for form in policy.by_head["allow"]:
        expr = form.expr
        require(len(expr) == 4 and isinstance(expr[3], tuple) and len(expr[3]) == 2,
                "unsupported allow shape")
        if expr[3][0] != "binder":
            continue
        perms = expr[3][1]
        require(isinstance(perms, tuple) and perms and all(isinstance(item, str) for item in perms)
                and set(perms) <= BINDER_PERMISSIONS, "unsupported Binder permissions")
        source = policy.resolve(expr[1])
        target = source if expr[2] == "self" else policy.resolve(expr[2])
        result.append((form, source, target))
    return result


def audit_binder(policy, contract):
    domain = policy.resolve("domain")
    assertions = {}
    for direction, digest in contract["binder_assertions"].items():
        matches = [form for form in policy.by_head["neverallow"] if form.runtime == PLATFORM_RUNTIME
                   and sha(render(form.expr).encode()) == digest]
        require(len(matches) == 1, "missing or duplicate reviewed Binder assertion")
        expr = matches[0].expr
        require(len(expr) == 4 and expr[3] == ("binder", ("impersonate", "call", "set_context_mgr", "transfer")),
                "Binder assertion shape changed")
        source, target = policy.resolve(expr[1]), policy.resolve(expr[2])
        expected = ((policy.types, policy.types - domain) if direction == "target_non_domain"
                    else (policy.types - domain, policy.types))
        require((source, target) == expected, "Binder assertion closure changed")
        assertions[direction] = (source, target)
    require(set(assertions) == {"source_non_domain", "target_non_domain"}, "both Binder assertions required")
    rules = binder_rules(policy)
    groups, selected = {direction: 0 for direction in assertions}, {}
    for form, source, target in rules:
        for direction, (asserted_source, asserted_target) in assertions.items():
            src, tgt = source & asserted_source, target & asserted_target
            if form.expr[2] == "self":
                src = tgt = src & tgt
            if src and tgt:
                groups[direction] += 1
                selected[form] = (source, target)
    return groups, selected, rules


def derive_corpus(corpus, contract):
    """Pure derivation; production entrypoints load only the hash-pinned contract."""
    rows = contract["inputs"]
    require(list(corpus) == [row["runtime_path"] for row in rows], "CIL input order or corpus differs")
    parsed = {}
    for row in rows:
        runtime, data = row["runtime_path"], corpus[row["runtime_path"]]
        require(sha(data) == row["sha256"] and len(data) == row["size_bytes"], "CIL input hash or size mismatch")
        parsed[runtime] = parse(data, runtime)
    before = [form for forms in parsed.values() for form in forms]
    policy = Policy(before)
    # Resolve every attribute and alias, not only symbols in the selected rules.
    for name in sorted(policy.attrs | set(policy.aliases)):
        policy.resolve(name)
    domain, roles = policy.resolve("domain"), policy.role_bindings()
    role_r = {name for name, memberships in roles.items() if "r" in memberships}
    require(domain == role_r, "role r differs from process domain closure")
    services = set(contract["service_object_types"])
    for name in services:
        require(name in policy.types and name not in domain and roles[name] == {"object_r"},
                "reviewed service object is missing or has acquired a process role")
    groups, selected, rules = audit_binder(policy, contract)
    vendor_runtime = contract["vendor_runtime_path"]
    for form, (source, target) in selected.items():
        source_object, target_object = source <= services, target <= services
        require(form.runtime == vendor_runtime and len(source) == len(target) == 1
                and source_object != target_object and (target if source_object else source) <= domain,
                "correction requires one singleton service object and one singleton process domain in vendor CIL")
    vendor = corpus[vendor_runtime]
    selected_forms = sorted(selected, key=lambda form: form.start)
    result = bytearray(vendor)
    removals, cursor = [], 0
    for form in selected_forms:
        require(cursor <= form.start < form.end <= len(vendor), "overlapping removal spans")
        original = vendor[form.start:form.end]
        result[form.start:form.end] = bytes(byte if byte in (10, 13) else 32 for byte in original)
        removals.append({"start_byte": form.start, "end_byte_exclusive": form.end,
                         "line": form.line, "end_line": form.end_line,
                         "normalized_form_sha256": sha(render(form.expr).encode()),
                         "raw_statement_sha256": sha(original)})
        cursor = form.end
    result = bytes(result)
    after_vendor = parse(result, vendor_runtime)
    kept = [form for form in parsed[vendor_runtime] if form not in selected]
    require(after_vendor == kept, "unselected forms, offsets, or lines changed")
    cursor = 0
    for form in selected_forms:
        require(vendor[cursor:form.start] == result[cursor:form.start], "unselected bytes changed")
        cursor = form.end
    require(vendor[cursor:] == result[cursor:] and len(result) == len(vendor), "unselected trailing bytes changed")
    require([i for i, byte in enumerate(vendor) if byte in (10, 13)]
            == [i for i, byte in enumerate(result) if byte in (10, 13)], "line delimiters changed")
    after = [form for runtime, forms in parsed.items() for form in (after_vendor if runtime == vendor_runtime else forms)]
    require(Counter(form.expr for form in before) == Counter(form.expr for form in after)
            + Counter(form.expr for form in selected), "statement multiset delta differs")
    after_groups, after_selected, after_rules = audit_binder(Policy(after), contract)
    require(not after_selected and not any(after_groups.values()), "ill-typed Binder grants remain")
    fd = []
    for form in policy.by_head["allow"]:
        if rule_class(form) != "fd":
            continue
        source = policy.resolve(form.expr[1])
        target = source if form.expr[2] == "self" else policy.resolve(form.expr[2])
        if services & (source | target):
            fd.append(form)
    measured = {
        "domain_types": len(domain), "role_r_types": len(role_r),
        "bad_binder_groups_before": groups,
        "removed_occurrences": len(selected),
        "removed_distinct_normalized_statements": len({form.expr for form in selected}),
        "selected_span_bytes": sum(form.end - form.start for form in selected),
        "changed_byte_values": sum(a != b for a, b in zip(vendor, result)),
        "vendor_statement_count_before": len(parsed[vendor_runtime]),
        "vendor_statement_count_after": len(after_vendor),
        "vendor_binder_allow_count_before": sum(form.runtime == vendor_runtime for form, _, _ in rules),
        "vendor_binder_allow_count_after": sum(form.runtime == vendor_runtime for form, _, _ in after_rules),
        "combined_binder_allow_count_before": len(rules), "combined_binder_allow_count_after": len(after_rules),
        "neverallow_statements": len(policy.by_head["neverallow"]),
        "neverallowx_statements": len(policy.by_head["neverallowx"]),
        "vendor_neverallow_statements": sum(form.runtime == vendor_runtime for form in policy.by_head["neverallow"]),
        "related_fd_occurrences": len(fd), "related_fd_distinct_statements": len({form.expr for form in fd}),
    }
    for name, expected in contract["expected"].items():
        require(measured.get(name) == expected, f"reviewed aggregate differs: {name}")
    require(sha(result) == contract["output"]["sha256"] and len(result) == contract["output"]["size_bytes"],
            "derived CIL differs from the validated prototype")
    return result, {
        "schema_version": 1, "operation": "nezha-factory-binder-correction-v1", "device": "nezha",
        "factory_package_sha256": contract["factory_package_sha256"], "factory_origin_authenticated": False,
        "contract_sha256": CONTRACT_SHA256, "classification_corpus": contract["classification_corpus"],
        "inputs": rows, "output": contract["output"], "measured": measured, "removals": removals,
        "preservation": {"all_unselected_bytes_and_line_positions": True, "all_assertions": True,
                         "type_role_alias_attribute_and_mapping_declarations": True,
                         "valid_process_binder_grants": True, "fd_and_service_manager_grants": True},
        "scope": {"policy_compiler_executed": False, "source_policy_regenerated": False,
                  "image_packaging_performed": False, "hardware_support_proven": False},
    }


def _destination(output, corpus_root, private_output_root=None):
    destination = Path(os.path.abspath(output))
    private_roots = [WORKSPACE_ROOT / "artifacts", WORKSPACE_ROOT / "evidence"]
    if sys.platform == "linux":
        private_roots.append(Path("/work/validation"))
    if private_output_root is not None:
        # Android genrules run in a fresh sbox directory, outside this tool's
        # source workspace. The caller explicitly identifies that private root;
        # it is never inferred from the vendor input or silently created.
        private_root = real_directory(private_output_root)
        require(private_root != Path(private_root.anchor), "filesystem root cannot be private output")
        if private_root == WORKSPACE_ROOT or WORKSPACE_ROOT in private_root.parents:
            require(any(root == private_root or root in private_root.parents for root in private_roots),
                    "workspace build output must stay in an ignored private directory")
        private_roots.append(private_root)
    require(any(root in destination.parents for root in private_roots),
            "output must be under private artifacts/, evidence/, or Linux /work/validation/")
    require(not os.path.lexists(destination), "output already exists; never overwrite a derivation")
    require(corpus_root not in destination.parents and destination not in corpus_root.parents,
            "output must remain separate from the input corpus")
    real_directory(destination.parent)
    return destination


def _write_new(directory, name, data):
    path = directory / name
    with os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600), "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(path, 0o444)
    require(Reader().read(path) == data, "published bytes failed readback")


def derive(corpus_root, output, *, contract_path=None, private_output_root=None, tool_source=None):
    """Publish one new private directory atomically, or leave no result behind."""
    corpus_root = real_directory(corpus_root)
    destination = _destination(output, corpus_root, private_output_root)
    reader = Reader()
    contract = load_contract(contract_path, reader)
    # Soong's python_binary_host can load this module from an executable ZIP;
    # its __file__ is then virtual. The genrule supplies the separately declared
    # source input so provenance still binds the checked-in implementation.
    tool_path = Path(tool_source) if tool_source is not None else Path(__file__)
    tool = reader.read(tool_path)
    publisher = reader.read(tool_path.with_name("artifact_files.py"))
    corpus = {row["runtime_path"]: reader.read(corpus_root / row["runtime_path"].lstrip("/"),
                                             row["sha256"], row["size_bytes"])
              for row in contract["inputs"]}
    result, receipt = derive_corpus(corpus, contract)
    receipt["tool_sha256"] = sha(tool)
    receipt["publisher_sha256"] = sha(publisher)
    receipt["input_manifest"] = [{**row, "path": str(corpus_root / row["runtime_path"].lstrip("/"))}
                                 for row in contract["inputs"]]
    require(shutil.disk_usage(destination.parent).free >= len(result) + MAX_BYTES, "insufficient output disk space")
    staging = Path(tempfile.mkdtemp(prefix="." + destination.name + "-", dir=destination.parent))
    try:
        _write_new(staging, "vendor_sepolicy.cil", result)
        receipt["output_readback_verified"] = True
        reader.recheck()
        receipt["all_inputs_rehashed_unchanged"] = True
        _write_new(staging, "receipt.json", encoded(receipt))
        real_directory(destination.parent)
        reader.recheck()
        publish_new_directory(staging, destination)
        staging = None
        return receipt
    finally:
        if staging is not None:
            shutil.rmtree(staging)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    command = commands.add_parser("derive", help="derive into a new private directory; never compile or mutate inputs")
    command.add_argument("--corpus-root", required=True, type=Path,
                         help="root containing the exact ten runtime-relative CIL files in the public contract")
    command.add_argument("--output", required=True, type=Path)
    command.add_argument("--contract", type=Path, help="copied contract with the exact reviewed hash")
    command.add_argument("--private-output-root", type=Path,
                         help="existing private external build/sbox root; output must be a new descendant")
    command.add_argument("--tool-source", type=Path,
                         help="explicit original script input when python_binary_host uses a virtual __file__")
    args = parser.parse_args(argv)
    try:
        receipt = derive(args.corpus_root, args.output, contract_path=args.contract,
                         private_output_root=args.private_output_root, tool_source=args.tool_source)
    except (OSError, VendorPolicyError) as exc:
        print(f"vendor-policy: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output), "sha256": receipt["output"]["sha256"],
                      "removed_occurrences": receipt["measured"]["removed_occurrences"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
