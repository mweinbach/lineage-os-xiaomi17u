#!/usr/bin/env python3
"""Inspect the explicit, currently unbound Nezha construction prerequisites.

This consumer never dispatches a build or opens a framework-checks target gate.
Known component evidence is distinct from admission for a later selected input
set. A new reviewed contract/consumer revision must bind actual native results
and coverage before a construction-enabled source derivative can be generated.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

try:
    from . import target_files_metadata as metadata
except ImportError:
    import target_files_metadata as metadata


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "config/nezha-rom-construction.json"
CONTRACT_ID = "nezha-rom-construction-prerequisites-v1"
CONTRACT_SHA256 = "a225e4c4e3307b0b4472fd6ff6e59b35874b826c8737e88d07f003ff73e0f6fb"
CONTEXT = {
    "device": "nezha", "product": "lineage_nezha", "variant": "user",
    "branch": "bka", "release_config": "bp4a", "shipping_api_level": 36,
    "maximum_page_size_bytes": 4096,
}
ROLES = (
    "source_and_private_input_closure", "policy_and_context_checks",
    "provider_elf_and_install_closure", "full_vintf_native_result",
    "necessary_vintf_coverage",
)
PHASES = {
    "target-files": ("target-files-package", []),
    "super": ("superimage", ["validated_target_files_and_image_set"]),
    "ota": ("otapackage", ["validated_signed_target_files_and_image_set",
                          "apk_apex_payload_zip_signing_and_trust",
                          "qualified_care_map_and_snapshot_inputs"]),
}
BASIS = frozenset({"four_kib_component_result", "four_kib_provider_checks", "four_kib_provider_review"})
COVERAGE = {
    "native_result_is_not_complete_coverage": True,
    "reported_skips_remain_uncovered": True,
    "check_one_stub_runtime_is_not_kernel_compatibility": True,
    "mainline_kernel_bypass_is_not_requirement_matching": True,
    "size_max_is_not_kernel_selinux_policy_version_evidence": True,
    "default_disabled_avb_version_check_is_not_avb_verification": True,
    "absence_of_warnings_is_not_coverage": True,
}
SCOPE = {
    "input_admission_schema_only": True, "native_goal_dispatch_allowed": False,
    "framework_target_guards_changed": False, "complete_target_files_allowed": False,
    "complete_rom_ready": False, "flash_allowed": False, "hardware_tested": False,
    "phone_operations": [],
}
DOWNSTREAM = ["final-image-avb-signing-and-complete-descriptor-chain",
              "actual-image-partition-fit-and-device-rollback-review",
              "authorized-first-boot-and-hardware-stabilization"]
REPRODUCIBILITY = {
    "source_contract": {"path": "patches/evolution/pinned-version-date.json",
                        "sha256": "f49518af8e607cd2b1cfb1b2137de5ab720ec725ed6365661753fed124d61734",
                        "size_bytes": 12604},
    "selected": False, "manifest_epoch_evidence": None,
    "build_metadata_environment_evidence": None, "ordinary_product_route_evidence": None,
    "changes_current_packaging_composition": False,
}


class ConstructionError(ValueError):
    """The explicit construction contract or its evidence is not admitted."""


def require(condition, message):
    if not condition:
        raise ConstructionError(message)


def same(actual, expected, message):
    require(metadata.encoded(actual) == metadata.encoded(expected), message)


def _schema(contract):
    require(type(contract) is dict and set(contract) == {
        "schema_version", "contract_id", "status", "context", "available_basis",
        "required_selected_input_roles", "phases", "vintf_coverage_requirements", "downstream_only", "scope",
        "reproducibility",
    }, "construction contract fields differ")
    require(type(contract["schema_version"]) is int and contract["schema_version"] == 1 and
            contract["contract_id"] == CONTRACT_ID and contract["status"] == "native-prerequisites-unbound",
            "unsupported construction contract or activation state")
    same(contract["context"], CONTEXT, "construction requires the exact Nezha bka/bp4a user 4 KiB context")
    same(contract["scope"], SCOPE, "construction preparation cannot promote dispatch, ROM or flash readiness")
    same(contract["vintf_coverage_requirements"], COVERAGE, "construction cannot waive VINTF coverage limits")
    same(contract["downstream_only"], DOWNSTREAM, "artifact/device checks must remain downstream of input construction")
    same(contract["reproducibility"], REPRODUCIBILITY,
         "reproducibility must use separately qualified 0012 and actual metadata evidence")
    same(contract["required_selected_input_roles"], dict.fromkeys(ROLES),
         "v1 has no reviewed selected-input native admission; supplied pass flags or receipts cannot activate it")
    basis = contract["available_basis"]
    require(type(basis) is dict and set(basis) == BASIS, "available component basis differs")
    names = []
    for row in basis.values():
        require(type(row) is dict and set(row) == {"path", "sha256", "size_bytes"}, "invalid basis identity")
        names.append(metadata.relative(row["path"]))
        metadata.expected(row, maximum=16 * 1024**2)
        require(row["size_bytes"] > 0, "empty native basis is not evidence")
    require(len(set(names)) == len(names), "basis evidence paths must be distinct")
    require(type(contract["phases"]) is dict and set(contract["phases"]) == set(PHASES),
            "construction phase set differs")
    for name, (goal, inputs) in PHASES.items():
        phase = contract["phases"][name]
        require(type(phase) is dict and set(phase) == {"ordinary_goal", "additional_input_roles", "artifact_checks"},
                "construction phase fields differ")
        same(phase["ordinary_goal"], goal, "construction must use the ordinary phase target")
        same(phase["additional_input_roles"], inputs, "construction phase prerequisites differ")
        checks = phase["artifact_checks"]
        require(type(checks) is list and len(checks) > 0 and
                all(type(item) is str and item and item.isascii() and item.replace("-", "").isalnum()
                    for item in checks) and len(set(checks)) == len(checks),
                "artifact checks must remain explicit and distinct")


def load_contract(path=None):
    """Accept only the exact maintained v1 bytes, never a caller's resealed plan."""
    reader = metadata.Reader()
    canonical = reader.read(ROOT / CONTRACT)
    require(metadata.identity(canonical)["sha256"] == CONTRACT_SHA256,
            "maintained construction contract changed; review a new consumer binding")
    selected = canonical if path is None else reader.read(path)
    require(selected == canonical, "construction selector differs from the maintained contract")
    contract = metadata._json(selected)
    _schema(contract)
    reader.recheck()
    return contract, metadata.identity(selected)


def inspect(phase="target-files", *, contract_path=None, evidence_root=None):
    """Report exact missing roles; optionally hash the three existing basis files.

    Hash equality here proves identity only. It does not replay the component
    build, provider checks, their review, or any native compatibility command.
    No evidence path is opened by the default planning operation.
    """
    require(type(phase) is str and phase in PHASES, "unsupported construction phase")
    contract, identity = load_contract(contract_path)
    checked = {}
    if evidence_root is not None:
        root = metadata.real_directory(evidence_root)
        reader = metadata.Reader()
        for role, row in sorted(contract["available_basis"].items()):
            reader.read(root / metadata.relative(row["path"]), row, maximum=16 * 1024**2)
            checked[role] = copy.deepcopy(row)
        reader.recheck()
    missing = [*ROLES, *PHASES[phase][1]]
    return {
        "schema_version": 1, "operation": "inspect-nezha-rom-construction-prerequisites",
        "contract": {"path": CONTRACT, **identity}, "context": copy.deepcopy(CONTEXT),
        "phase": phase, "ordinary_goal": PHASES[phase][0], "status": "blocked",
        "missing_selected_input_roles": missing,
        "available_basis": copy.deepcopy(contract["available_basis"]),
        "basis_identities_verified": checked, "native_evidence_reexecuted": False,
        "available_basis_is_selected_input_admission": False,
        "required_artifact_checks": copy.deepcopy(contract["phases"][phase]["artifact_checks"]),
        "vintf_coverage_requirements": copy.deepcopy(COVERAGE),
        "reproducibility": copy.deepcopy(REPRODUCIBILITY),
        "downstream_only": copy.deepcopy(DOWNSTREAM), "scope": copy.deepcopy(SCOPE),
    }


def require_admission(contract_path, *, phase="target-files"):
    """The generator cannot turn this unbound schema into an enabled product."""
    result = inspect(phase, contract_path=contract_path)
    raise ConstructionError("construction admission blocked: unbound selected-input roles: " +
                            ", ".join(result["missing_selected_input_roles"]) +
                            "; existing framework-checks target guards remain active")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "check"))
    parser.add_argument("--contract", type=Path)
    parser.add_argument("--phase", choices=tuple(PHASES), default="target-files")
    parser.add_argument("--verify-available-evidence", type=Path, metavar="WORKSPACE_ROOT",
                        help="hash only the three known basis records; does not admit selected inputs")
    args = parser.parse_args(argv)
    try:
        result = inspect(args.phase, contract_path=args.contract, evidence_root=args.verify_available_evidence)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if args.command == "plan" else 2
    except (ConstructionError, metadata.TargetFilesMetadataError, OSError, ValueError, KeyError, TypeError) as exc:
        parser.exit(1, "construction inspection refused: " + str(exc) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
