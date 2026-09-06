#!/usr/bin/env python3
"""Derive the both-physical-slot write route from a reviewed version-1 delivery plan.

The version-1 plan and bundle describe the A-only fastboot route the f9e
installation used. This tool validates such a plan with the maintained bundle
validator, then derives the route the roadmap selected: Super written once
(logical A populated, logical B empty, as Virtual A/B requires), followed by the
seven physical images written to slot B and then to slot A. Each physical image
is written twice from the same bytes; nothing is stored twice.

The route is a reviewable document with pending device gates. It generates no
fastboot commands, never contacts a phone, and does not authorize a write. The
bundle assembler still produces version-1 bundles; wiring the route into it is
a later reviewed change.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

try:
    from . import experimental_flash_bundle as bundle
except ImportError:
    import experimental_flash_bundle as bundle

SCHEMA_VERSION = 2
OPERATION = "nezha-both-physical-slot-route-v2"
SLOTS = ("a", "b")
SLOT_WRITE_SEQUENCE = ("b", "a")
PHYSICAL_WRITE_ORDER = ("dtbo", "init_boot", "vendor_boot", "recovery", "boot", "vbmeta_system", "vbmeta")
SUPER_SPARSE_CHUNK_LIMIT = "512M"
PREFLIGHT_ADDITIONS = ("slot-successful:a", "slot-successful:b", "slot-unbootable:a", "slot-unbootable:b",
                       "slot-retry-count:a", "slot-retry-count:b")
WARNING = ("Super is written once and stays single-copy: logical A populated, logical B empty, as Virtual A/B "
           "requires. The physical chain is written to both slots so no stock boot chain remains on B. "
           "No slot change, wipe or reboot is part of this route; installation needs its own authorization.")
LAYOUT = {
    "physical_slots": list(SLOTS), "candidate_boot_slot": "a", "populated_logical_slot": "a",
    "empty_logical_slot": "b", "logical_single_copy_by_virtual_ab_design": True,
    "physical_super_is_shared_and_unslotted": True, "slot_change_requested": False,
    "automatic_reboot": False, "automatic_userdata_or_metadata_format": False,
    "slot_switch_is_standalone_fresh_authorization_gate": True,
}
EXPECTED_WRITE_COUNT = 1 + len(SLOT_WRITE_SEQUENCE) * len(PHYSICAL_WRITE_ORDER)


class RouteError(ValueError):
    pass


def require(condition, message):
    if not condition:
        raise RouteError(message)


def derive(plan, plan_sha256):
    """Validate a version-1 plan and return the version-2 route document."""
    try:
        rows = bundle.validate_plan(plan)
    except bundle.BundleError as exc:
        raise RouteError(f"delivery plan rejected: {exc}") from exc
    require(set(PHYSICAL_WRITE_ORDER) == set(bundle.PHYSICAL), "physical write order must cover every physical role")
    writes = [{"order": 1, "role": "super", "target": "super", "slot": None,
               "sparse_chunk_limit": SUPER_SPARSE_CHUNK_LIMIT, **bundle.identity(plan["super"])}]
    for slot in SLOT_WRITE_SEQUENCE:
        for role in PHYSICAL_WRITE_ORDER:
            writes.append({"order": len(writes) + 1, "role": role, "target": f"{role}_{slot}", "slot": slot,
                           **bundle.identity(rows[role])})
    return {
        "schema_version": SCHEMA_VERSION, "operation": OPERATION,
        "reviewed_plan_sha256": bundle.digest(plan_sha256),
        "artifact_set_id": plan.get("artifact_set_id"), "build_number": plan.get("build_number"),
        "device": plan["device"], "platform": plan["platform"],
        "layout": dict(LAYOUT), "warning": WARNING,
        "write_count": len(writes), "writes": writes,
        "retained_firmware_readback": {
            role: {"targets": [f"{role}_{slot}" for slot in SLOTS], **bundle.identity(rows[role]),
                   "descriptor_requirement": plan["retained_firmware_avb_requirements"][role]}
            for role in bundle.REFERENCES},
        "preflight_additions": list(PREFLIGHT_ADDITIONS),
        "device_preflight": plan["device_preflight"],
        **{key: False for key in bundle.FALSE_FLAGS},
        "fresh_experimental_flash_authorization": None,
        "status": "route-derived-not-device-admitted-not-flash-ready",
    }


def validate(route):
    """Re-check a route document; returns it when consistent."""
    require(isinstance(route, dict) and route.get("schema_version") == SCHEMA_VERSION
            and route.get("operation") == OPERATION, "unsupported route document")
    require(route.get("layout") == LAYOUT and route.get("warning") == WARNING, "route layout or warning differs")
    require(all(route.get(key) is False for key in bundle.FALSE_FLAGS)
            and route.get("fresh_experimental_flash_authorization") is None, "route promotes readiness or authorization")
    bundle.pending_preflight(route.get("device_preflight"))
    bundle.digest(route.get("reviewed_plan_sha256"))
    writes = route.get("writes")
    require(isinstance(writes, list) and len(writes) == EXPECTED_WRITE_COUNT == route.get("write_count"),
            f"route must contain exactly {EXPECTED_WRITE_COUNT} writes")
    expected = [("super", "super", None)] + [(role, f"{role}_{slot}", slot)
                                             for slot in SLOT_WRITE_SEQUENCE for role in PHYSICAL_WRITE_ORDER]
    identities = {}
    for index, (row, (role, target, slot)) in enumerate(zip(writes, expected), start=1):
        require(isinstance(row, dict) and row.get("order") == index and row.get("role") == role
                and row.get("target") == target and row.get("slot") == slot, f"write {index} is out of order or mislabeled")
        identity = bundle.identity(row)
        require(identities.setdefault(role, identity) == identity, f"{role} has different bytes for its two slots")
        if role == "super":
            require(row.get("sparse_chunk_limit") == SUPER_SPARSE_CHUNK_LIMIT, "Super chunk limit differs")
    readback = route.get("retained_firmware_readback")
    require(isinstance(readback, dict) and set(readback) == set(bundle.REFERENCES), "retained firmware readback roles differ")
    for role, row in readback.items():
        require(row.get("targets") == [f"{role}_{slot}" for slot in SLOTS], f"{role} readback must cover both slots")
        bundle.identity(row)
    require(route.get("preflight_additions") == list(PREFLIGHT_ADDITIONS), "preflight additions differ")
    return route


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    derive_command = commands.add_parser("derive")
    derive_command.add_argument("--plan", type=Path, required=True)
    derive_command.add_argument("--expected-plan-sha256", required=True)
    derive_command.add_argument("--output", type=Path, required=True)
    validate_command = commands.add_parser("validate")
    validate_command.add_argument("--route", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "derive":
            with bundle.json_input(args.plan, args.expected_plan_sha256) as (plan, unchanged):
                route = validate(derive(plan, args.expected_plan_sha256))
                unchanged()
            if args.output.exists() or args.output.is_symlink():
                raise FileExistsError(f"output exists: {args.output}")
            args.output.write_bytes(bundle.json_bytes(route))
            print(json.dumps({"output": str(args.output), "write_count": route["write_count"],
                              "status": route["status"]}, indent=2))
            return 0
        route = validate(json.loads(Path(args.route).read_bytes()))
        print(json.dumps({"route": str(args.route), "write_count": route["write_count"], "valid": True}, indent=2))
        return 0
    except (RouteError, bundle.BundleError, KeyError, OSError, ValueError) as exc:
        print(json.dumps({"error": f"{type(exc).__name__}: {exc}"}, indent=2))
        return 1 if isinstance(exc, (RouteError, bundle.BundleError)) else 2


if __name__ == "__main__":
    sys.exit(main())
