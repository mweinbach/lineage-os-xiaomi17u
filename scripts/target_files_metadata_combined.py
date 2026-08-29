#!/usr/bin/env python3
"""Explicit combined source admission for the unchanged factory metadata bundle.

The original metadata tool is frozen.  This adapter loads only that exact local
source and derives a self-contained native checker without private code imports.
Its source hooks do not change capture, image, or atomic publication semantics.
"""

import hashlib
import os
from pathlib import Path
import stat

FROZEN_BASE = "scripts/target_files_metadata.py"
ADAPTER = "scripts/target_files_metadata_combined.py"
FROZEN_BASE_IDENTITY = {
    "sha256": "60e54729e5e9b3e261af45898752717eb7213b98aafb51beac8b96b848ee6184",
    "size_bytes": 39730,
}
_BASE_MAIN = b'\n\nif __name__ == "__main__":\n    raise SystemExit(main())\n'
_NATIVE_MARKER = b"\n_NEZHA_COMBINED_BASE_LOADED = True\n"


def _base_body(raw):
    """Apply only exact API/data-plumbing substitutions to the frozen source."""
    if (len(raw) != FROZEN_BASE_IDENTITY["size_bytes"]
            or hashlib.sha256(raw).hexdigest() != FROZEN_BASE_IDENTITY["sha256"]):
        raise ValueError("combined metadata frozen base identity differs")
    if not raw.endswith(_BASE_MAIN) or raw.count(_BASE_MAIN) != 1:
        raise ValueError("combined metadata frozen base main boundary differs")
    body = raw[:-len(_BASE_MAIN)]
    changes = (
        (b"def stage(inputs_root, output, *, vendor_image, odm_image, controls_root=None):",
         b"def stage(inputs_root, output, *, vendor_image, odm_image, controls_root=None, source_contract=None):", 1),
        (b"profile, composition, controls = _controls(controls_root, reader)",
         b"profile, composition, controls = _controls(controls_root, reader, source_contract=source_contract)", 1),
        (b"def verify_bundle(bundle, *, expected_receipt, source_tree=None, vendor_image=None, odm_image=None):",
         b"def verify_bundle(bundle, *, expected_receipt, source_tree=None, vendor_image=None, odm_image=None, source_contract=None):", 1),
        (b'profile, composition, controls = _controls(bundle / "controls", reader)',
         b'profile, composition, controls = _controls(bundle / "controls", reader, source_contract=source_contract)', 1),
        (b'payloads.update({"tools/" + Path(path).name: controls[path] for path in CONTROL_TOOLS})',
         b"payloads.update(runtime_tool_payloads(controls))", 2),
        (b'vendor_image=target / "IMAGES/vendor.img", odm_image=target / "IMAGES/odm.img")',
         b'vendor_image=target / "IMAGES/vendor.img", odm_image=target / "IMAGES/odm.img",\n'
         b"        source_contract=_selected_receipt_source_contract(bundle, expected_receipt))", 1),
        (b"def selection(bundle, *, expected_receipt):",
         b"def selection(bundle, *, expected_receipt, source_contract=None):", 1),
        (b"receipt, _, _ = verify_bundle(bundle, expected_receipt=expected_receipt)",
         b"receipt, _, _ = verify_bundle(bundle, expected_receipt=expected_receipt, source_contract=source_contract)", 1),
        (b'require(receipt.get("schema_version") == 1',
         b'require(type(receipt.get("schema_version")) is int and receipt["schema_version"] == 1', 1),
        (b'and receipt.get("scope") == SCOPE, "bundle profile or scope differs")',
         b'and encoded(receipt.get("scope")) == encoded(SCOPE), "bundle profile or scope differs")', 1),
        (b'receipt.get("source_composition") == composition',
         b'encoded(receipt.get("source_composition")) == encoded(composition)', 1),
    )
    for before, after, count in changes:
        if body.count(before) != count:
            raise ValueError("combined metadata frozen base hook differs")
        body = body.replace(before, after)
    return body


def _read_bootstrap_base(path):
    """Bound and hash source before executing it; never follow copied code."""
    path = Path(os.path.abspath(path))
    for parent in reversed(path.parents):
        if not stat.S_ISDIR(parent.lstat().st_mode):
            raise ValueError("combined metadata base requires real parent directories")
    before = path.lstat()
    if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1
            or before.st_size != FROZEN_BASE_IDENTITY["size_bytes"]):
        raise ValueError("combined metadata base must be a bounded single-link regular file")
    def binding(info):
        return (info.st_dev, info.st_ino, info.st_mode, info.st_nlink, info.st_size,
                info.st_mtime_ns, info.st_ctime_ns)
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK), "rb") as stream:
        if binding(before) != binding(os.fstat(stream.fileno())):
            raise ValueError("combined metadata base replaced before read")
        raw = stream.read(FROZEN_BASE_IDENTITY["size_bytes"] + 1)
        if binding(before) != binding(os.fstat(stream.fileno())) or binding(before) != binding(path.lstat()):
            raise ValueError("combined metadata base changed during read")
    _base_body(raw)
    return raw


# A generated native checker has already evaluated the same verified base body.
# Host imports execute only the admitted adjacent public base, in this module's
# private namespace; the separately imported legacy module is never modified.
if not globals().get("_NEZHA_COMBINED_BASE_LOADED", False):
    _bootstrap_path = Path(os.path.abspath(__file__)).parent / "target_files_metadata.py"
    exec(compile(_base_body(_read_bootstrap_base(_bootstrap_path)), str(_bootstrap_path), "exec"), globals())

_legacy_compose_sources = compose_sources
CONTROL_TOOLS = (FROZEN_BASE, ADAPTER)
COMBINED_SOURCE_CONTRACT = "patches/evolution/target-files-source-composition.json"
COMBINED_SOURCE_ID = "nezha-target-files-source-composition-v1"
READONLY_CONTRACT = "patches/evolution/direct-avb-readonly.json"
READONLY_PATCH = "patches/evolution/0010-initialize-direct-avb-readonly.patch"
VINTF_CONTRACT = "patches/evolution/vintf-shipping-api.json"
VINTF_PATCH = "patches/evolution/0011-vintf-shipping-api-from-odm.patch"
COMBINED_CONTRACTS = (*SOURCE_CONTRACTS, READONLY_CONTRACT, VINTF_CONTRACT)
COMBINED_PATCHES = (*SOURCE_PATCHES, READONLY_PATCH, VINTF_PATCH)
PRODUCT = "build/make/core/product.mk"
VINTF = "build/make/tools/releasetools/check_target_files_vintf.py"
FROZEN_CONTRACT_IDENTITIES = (
    ("4d4b49050e5808f72d74fe023b80c2e83b646a542856182361ee594f48a9656b", 4741),
    ("8dc262578a254ca6e2f4a6a342c8d0e0a1b82d38585b2f1c059d848929938a2b", 5058),
    ("47008985f4972699e9c25fb91de7780abd433d7748dc5028e1fb21098d9113fc", 3189),
    ("ffe4dba8ffcdf202d57d263bf8ebbf40dfba1ed484f1f96122322b6901914e23", 3641),
    ("595382e29c0d03a203bf40e08649f42280c88d982e04eef2826813262b4b01b9", 3680),
    ("81fc394ebd031317a93ec374846f927209c0b03572463deb74bfc401a51cdcb1", 3275),
    ("c0a555d4b0aa6cddad58e788e9cf45026b7578c98a2a3cd1e7e66e4ef2c8fcf1", 4789),
)
COMBINED_CORE = {"sha256": "bf6e0668ff571f3858fc09d5cefa039ff6a8fdebf5b9ecfdc690794f25889ba7",
                 "size_bytes": 392084}
FROZEN_PROFILE = {"path": PROFILE,
                  "sha256": "139682bc8d8d2644771b9d62656763a837da558c629c5b1a8765a933ad8e0b49",
                  "size_bytes": 4734}
COMBINED_SCOPE = {
    "complete_rom_admitted": False, "hardware_tested": False, "metadata_only": True,
    "native_kati_verified": False, "native_vintf_verified": False,
    "original_images_preserved": True, "ota_verified": False, "phone_operations": [],
    "readiness_flags_changed": False, "source_composition_only": True,
    "source_modified": False, "target_files_verified": False,
}
COMBINED_SEMANTICS = {
    "fresh_metadata_receipt_required": True, "native_entrypoint_self_contained": True,
    "old_selectors_and_contracts_preserved": True, "original_metadata_payloads_required": True,
    "original_metadata_profile_preserved": True, "patch_order_explicit": True,
    "readonly_macro_source_bound": True, "shipping_api_from_original_vendor_or_odm": True,
    "source_checks_preserved": True, "source_hash_fallback_allowed": False,
}


def runtime_tool_payloads(controls):
    """Reproduce the single native program from the frozen base and adapter."""
    require(FROZEN_BASE in controls and ADAPTER in controls,
            "combined metadata tool source controls missing")
    base, extension = controls[FROZEN_BASE], controls[ADAPTER]
    require(type(base) is bytes and type(extension) is bytes and 0 < len(extension) <= MAX_TEXT,
            "combined metadata tool source controls invalid")
    body = _base_body(base)
    return {"tools/target_files_metadata.py": body + _NATIVE_MARKER + extension}


def _select_contract(root, source_contract, reader):
    require(source_contract is not None, "explicit combined source contract required")
    canonical = Path(root) / COMBINED_SOURCE_CONTRACT
    selected = Path(source_contract)
    if not selected.is_absolute():
        selected = Path(root) / relative(selected.as_posix())
    raw = reader.read(canonical)
    require(reader.read(selected) == raw, "selected combined source contract differs")
    descriptor = _json(raw)
    require(type(descriptor.get("schema_version")) is int and descriptor["schema_version"] == 1
            and descriptor.get("contract_id") == COMBINED_SOURCE_ID
            and descriptor.get("project") == PROJECT, "combined source contract identity differs")
    return descriptor, {"path": COMBINED_SOURCE_CONTRACT, **identity(raw)}


def _same(actual, wanted, message):
    """Canonical JSON comparison distinguishes true/false from integer aliases."""
    require(encoded(actual) == encoded(wanted), message)


def _rows(values):
    return [values[path] for path in sorted(values)]


def _historical_readonly(records, refs):
    """Reconstruct the frozen legacy serializer without another code dependency."""
    first, packaging, extra, _, _, readonly, _ = records
    rows = {
        CORE: {"path": CORE, **extra["source_files"][0]["after"]},
        ADD_IMG: {"path": ADD_IMG, **packaging["source_files"][0]["after"]},
    }
    for record in (first, packaging, extra):
        for row in record["semantic_files"]:
            if row["path"] == CORE:
                continue
            require(row["path"] not in rows or rows[row["path"]] == row,
                    "historical source semantics conflict")
            rows[row["path"]] = copy.deepcopy(row)
    base = {"schema_version": 1, "project": copy.deepcopy(PROJECT), "contracts": refs[:3],
            "ordered_patches": [record["patch"] for record in records[:3]],
            "core_transitions": [first["source_files"][0], extra["source_files"][0]],
            "final_source_files": _rows(rows),
            "patches_applied_by_this_tool": False, "whole_source_tree_verified": False}
    _same(readonly["predecessor_composition"], identity(encoded(base)),
          "readonly legacy predecessor identity differs")
    _same(readonly["required_predecessor_contracts"], refs[:3],
          "readonly legacy predecessor contracts differ")
    result = copy.deepcopy(base)
    result["contracts"].append(refs[5])
    result["ordered_patches"].append(readonly["patch"])
    result["core_transitions"].append(readonly["source_files"][0])
    rows[CORE] = {"path": CORE, **readonly["source_files"][0]["after"]}
    for row in readonly["semantic_files"]:
        require(row["path"] not in rows or rows[row["path"]] == row,
                "readonly semantic source conflicts with predecessor")
        rows[row["path"]] = copy.deepcopy(row)
    result["final_source_files"] = _rows(rows)
    return base, result


def compose_sources(root=ROOT, *, source_contract=None):
    """Validate the explicit seven-patch graph as data, never by source guessing."""
    root, reader = real_directory(root), Reader()
    descriptor, selected_ref = _select_contract(root, source_contract, reader)
    require(set(descriptor) == {"schema_version", "contract_id", "project", "required_contracts",
            "metadata_predecessor_composition", "readonly_legacy_predecessor_composition", "metadata_profile",
            "readonly_macro", "readonly_upgrade", "rebased_readonly_transition", "initial_source_files",
            "final_source_files", "source_transitions", "scope", "semantics", "limitations"},
            "combined source descriptor fields differ")
    limitations = descriptor["limitations"]
    require(type(limitations) is list and 1 <= len(limitations) <= 32
            and all(type(note) is str and 0 < len(note) <= 2048 for note in limitations),
            "combined source limitations must remain bounded text")
    _same(descriptor.get("scope"), COMBINED_SCOPE, "combined source admission scope differs")
    _same(descriptor.get("semantics"), COMBINED_SEMANTICS, "combined source semantics differ")
    _same(descriptor.get("metadata_profile"), FROZEN_PROFILE, "original metadata profile pin differs")
    records, refs, patches = [], [], []
    paths = (CORE, ADD_IMG, CORE, COMMON, CORE, CORE, VINTF)
    for index, (path, (digest, size)) in enumerate(zip(COMBINED_CONTRACTS, FROZEN_CONTRACT_IDENTITIES)):
        reference = {"path": path, "sha256": digest, "size_bytes": size}
        record = _json(reader.read(root / path, reference))
        require(type(record.get("schema_version")) is int and record["schema_version"] == 1
                and record.get("project") == PROJECT, "combined source project differs")
        patch = record["patch"]
        require(patch["path"] == COMBINED_PATCHES[index], "combined patch order differs")
        data = reader.read(root / patch["path"], patch)
        short = paths[index].removeprefix("build/make/")
        require(re.findall(rb"^--- (.+)$", data, re.M) == [f"a/{short}".encode()]
                and re.findall(rb"^\+\+\+ (.+)$", data, re.M) == [f"b/{short}".encode()]
                and re.findall(rb"^diff --git (.+)$", data, re.M)
                in ([], [f"a/{short} b/{short}".encode()]), "combined patch source scope differs")
        require(len(record["source_files"]) == 1 and record["source_files"][0]["path"] == paths[index],
                "combined source transition scope differs")
        records.append(record)
        refs.append(reference)
        patches.append({"path": patch["path"], **identity(data)})
    _same(descriptor.get("required_contracts"), refs, "combined frozen contract references differ")
    metadata = _legacy_compose_sources(root)
    _same(metadata["contracts"], refs[:5], "metadata predecessor contracts differ")
    _same(descriptor.get("metadata_predecessor_composition"), identity(encoded(metadata)),
          "metadata predecessor composition differs")
    historical_base, historical_readonly = _historical_readonly(records, refs)
    _same(descriptor.get("readonly_legacy_predecessor_composition"), identity(encoded(historical_base)),
          "combined readonly legacy predecessor differs")
    readonly, vintf = records[5:]
    _same(descriptor.get("readonly_macro"), readonly["readonly_macro"], "readonly macro differs")
    require([row["path"] for row in readonly["semantic_files"]] == [PRODUCT]
            and vintf["semantic_files"] == [{"path": COMMON, **records[3]["source_files"][0]["after"]}],
            "combined product macro or VINTF common semantics differ")
    rebased = {"path": CORE, "before": records[4]["source_files"][0]["after"],
               "after": COMBINED_CORE, "historical_transition": readonly["source_files"][0]}
    _same(descriptor.get("rebased_readonly_transition"), rebased,
          "combined readonly transition differs from reviewed rebase")
    transitions = [{"patch": patch, **record["source_files"][0]}
                   for patch, record in zip(patches, records)]
    transitions[5] = {"patch": patches[5], **{key: rebased[key] for key in ("path", "before", "after")}}
    _same(descriptor.get("source_transitions"), transitions, "combined source transitions differ")
    final = {row["path"]: copy.deepcopy(row) for row in metadata["final_source_files"]}
    final[PRODUCT] = copy.deepcopy(readonly["semantic_files"][0])
    require(final[VINTF] == {"path": VINTF, **vintf["source_files"][0]["before"]},
            "VINTF shipping API does not follow the exact metadata wrapper")
    final[CORE] = {"path": CORE, **COMBINED_CORE}
    final[VINTF] = {"path": VINTF, **vintf["source_files"][0]["after"]}
    initial = copy.deepcopy(final)
    for transition in reversed(transitions):
        name = transition["path"]
        require(initial[name] == {"path": name, **transition["after"]},
                "combined source transition chain has a gap")
        initial[name] = {"path": name, **transition["before"]}
    require(len(initial) == len(final) == 10, "combined source guard must bind ten files")
    _same(descriptor.get("initial_source_files"), _rows(initial), "combined initial source files differ")
    _same(descriptor.get("final_source_files"), _rows(final), "combined final source files differ")
    upgrade_initial = {row["path"]: copy.deepcopy(row) for row in historical_readonly["final_source_files"]}
    for name in (VINTF, "build/make/tools/releasetools/apex_utils.py"):
        upgrade_initial[name] = copy.deepcopy(initial[name])
    upgrade_transitions = [transitions[3],
        {"patch": patches[4], "path": CORE, "before": readonly["source_files"][0]["after"],
         "after": COMBINED_CORE}, transitions[6]]
    upgrade = {"predecessor_contract": refs[5],
               "predecessor_composition": identity(encoded(historical_readonly)),
               "initial_source_files": _rows(upgrade_initial), "final_source_files": _rows(final),
               "ordered_patches": [patches[i] for i in (3, 4, 6)], "source_transitions": upgrade_transitions}
    _same(descriptor.get("readonly_upgrade"), upgrade, "readonly source upgrade differs")
    reader.recheck()
    return {"schema_version": 1, "project": copy.deepcopy(PROJECT), "contracts": [*refs, selected_ref],
            "ordered_patches": patches, "initial_source_files": _rows(initial),
            "source_transitions": transitions, "final_source_files": _rows(final),
            "patches_applied_by_this_tool": False, "whole_source_tree_verified": False}


def _controls(root, reader, *, source_contract=None):
    root = real_directory(root)
    composition = compose_sources(root, source_contract=source_contract)
    profile_raw = reader.read(root / PROFILE, FROZEN_PROFILE)
    profile = _json(profile_raw)
    require(type(profile.get("schema_version")) is int and profile["schema_version"] == 1
            and profile.get("contract_id") == "nezha-factory-target-files-metadata-v1"
            and profile.get("device") == "nezha" and profile.get("branch") == "bka"
            and profile.get("release") == "bp4a" and profile.get("bundle") == BUNDLE
            and profile.get("factory_package_sha256") == EXPECTED_PACKAGE,
            "unexpected combined metadata profile")
    _same(profile.get("scope"), SCOPE, "combined metadata projection scope differs")
    require(type(profile.get("partitions")) is dict and set(profile["partitions"]) == {"vendor", "odm"},
            "exact vendor/ODM pair required")
    for name, row in profile["partitions"].items():
        require(expected(row.get("image"), MAX_IMAGE) == EXPECTED_IMAGES[name], "factory image identity differs")
        require(row.get("counts", {}).get("properties") == EXPECTED_COUNTS[name]["properties"]
                and row["counts"].get("apex") == EXPECTED_COUNTS[name]["apex"], "factory metadata counts differ")
    controls = {PROFILE: profile_raw}
    for path in CONTROL_TOOLS:
        controls[path] = reader.read(root / path, FROZEN_BASE_IDENTITY if path == FROZEN_BASE else None)
    for row in [*composition["contracts"], *composition["ordered_patches"]]:
        controls[row["path"]] = reader.read(root / row["path"], row)
    runtime_tool_payloads(controls)
    return profile, composition, controls


def _selected_receipt_source_contract(bundle, expected_receipt):
    """Only the unchanged install hook infers mode, after external admission."""
    require(type(expected_receipt) is str and re.fullmatch(r"[0-9a-f]{64}", expected_receipt),
            "an external expected bundle receipt SHA256 is required")
    bundle, reader = real_directory(bundle), Reader()
    raw = reader.read(bundle / RECEIPT)
    require(identity(raw)["sha256"] == expected_receipt, "bundle receipt differs from selected digest")
    receipt = _json(raw)
    composition = receipt.get("source_composition")
    require(type(composition) is dict and type(composition.get("contracts")) is list
            and len(composition["contracts"]) == len(COMBINED_CONTRACTS) + 1,
            "combined metadata receipt source selection missing")
    reference = composition["contracts"][-1]
    require(type(reference) is dict and set(reference) == {"path", "sha256", "size_bytes"}
            and reference.get("path") == COMBINED_SOURCE_CONTRACT,
            "combined metadata receipt source selector differs")
    copied = reader.read(bundle / "controls" / COMBINED_SOURCE_CONTRACT, reference)
    descriptor = _json(copied)
    require(descriptor.get("contract_id") == COMBINED_SOURCE_ID,
            "combined metadata copied source contract differs")
    controls = receipt.get("bundle_files")
    require(type(controls) is list and [row for row in controls if type(row) is dict
            and row.get("path") == "controls/" + COMBINED_SOURCE_CONTRACT]
            == [{"path": "controls/" + COMBINED_SOURCE_CONTRACT, **expected(reference)}],
            "combined metadata source contract is not bound by receipt inventory")
    reader.recheck()
    return COMBINED_SOURCE_CONTRACT


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--source-contract", type=Path, required=True)
    stage_parser = sub.add_parser("stage")
    stage_parser.add_argument("--inputs-root", type=Path, required=True)
    stage_parser.add_argument("--output", type=Path, required=True)
    stage_parser.add_argument("--vendor-image", type=Path, required=True)
    stage_parser.add_argument("--odm-image", type=Path, required=True)
    stage_parser.add_argument("--source-contract", type=Path, required=True)
    for name in ("verify", "install", "selection"):
        check = sub.add_parser(name)
        check.add_argument("--bundle", type=Path, required=True)
        check.add_argument("--expected-receipt", required=True)
        if name == "install":
            check.add_argument("--target-files", type=Path, required=True)
            check.add_argument("--source-tree", type=Path, required=True)
        else:
            check.add_argument("--source-contract", type=Path, required=True)
            if name == "verify":
                check.add_argument("--source-tree", type=Path)
                check.add_argument("--vendor-image", type=Path)
                check.add_argument("--odm-image", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "plan":
            profile, composition, _ = _controls(ROOT, Reader(), source_contract=args.source_contract)
            result = {"profile": profile, "source_composition": composition, "scope": SCOPE}
        elif args.command == "stage":
            result = stage(args.inputs_root, args.output, vendor_image=args.vendor_image,
                           odm_image=args.odm_image, source_contract=args.source_contract)
        elif args.command == "install":
            result = install(args.bundle, args.target_files, expected_receipt=args.expected_receipt,
                             source_tree=args.source_tree)
        elif args.command == "selection":
            print(selection(args.bundle, expected_receipt=args.expected_receipt,
                            source_contract=args.source_contract), end="")
            return 0
        else:
            result, _, _ = verify_bundle(args.bundle, expected_receipt=args.expected_receipt,
                                         source_tree=args.source_tree, vendor_image=args.vendor_image,
                                         odm_image=args.odm_image, source_contract=args.source_contract)
        print(encoded(result).decode(), end="")
        return 0
    except (TargetFilesMetadataError, OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
        print(f"combined target-files metadata: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
