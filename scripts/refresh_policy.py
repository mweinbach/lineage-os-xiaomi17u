#!/usr/bin/env python3
"""Offline Nezha refresh-policy source checks and saved display-dump diagnosis.

No adb, settings writes, subprocesses, timers, or hardware qualification claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
OVERLAY = Path("device/xiaomi/nezha/refresh-overlay/frameworks/base/core/res/res/values/config.xml")
RESOURCES = {"config_defaultPeakRefreshRate": 120, "config_defaultRefreshRate": 120}
MAX_BYTES = 8 * 1024 * 1024


def read(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("expected regular, non-symlink input: " + str(path))
    with path.open("rb") as source:
        raw = source.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("input exceeds bounded read limit")
    return raw


def verify_source(root=ROOT):
    root = Path(root)
    contract = json.loads(read(root / "config/nezha-refresh-policy.json"))
    if contract.get("resources") != RESOURCES or contract.get("selector") != "NEZHA_REFRESH_POLICY":
        raise ValueError("refresh policy contract changed")
    resources = ET.fromstring(read(root / OVERLAY))
    if resources.tag != "resources" or len(resources) != len(RESOURCES):
        raise ValueError("unexpected refresh overlay resources")
    seen = {}
    for child in resources:
        name = child.get("name")
        if child.tag != "integer" or name in seen or len(child):
            raise ValueError("non-integer or duplicate refresh resource")
        seen[name] = int(child.text)
    if seen != RESOURCES:
        raise ValueError("refresh resource values differ from reviewed policy")
    return {"schema_version": 1, "source_resources_verified": True,
            "resources": seen, "native_overlay_precedence_verified": False,
            "phone_accessed": False, "hardware_behavior_verified": False,
            "battery_improvement_measured": False}


def analyze_display(raw):
    text = raw.decode("utf-8", errors="strict")
    if "DisplayDeviceInfo" not in text or "mDefaultPeakRefreshRate:" not in text:
        raise ValueError("not a supported complete DisplayManager dump")
    def unique_number(pattern):
        values = {float(value) for value in re.findall(pattern, text)}
        if len(values) != 1:
            raise ValueError("missing or ambiguous display field: " + pattern)
        return values.pop()
    peak = unique_number(r"mDefaultPeakRefreshRate:\s*([0-9.]+)")
    default = unique_number(r"mDefaultRefreshRate:\s*([0-9.]+)")
    # Report all advertisements, not an assertion of physical transitions.
    rates = sorted({round(float(rate), 3) for rate in re.findall(r"\bfps=([0-9.]+)", text)})
    if not rates:
        raise ValueError("display dump has no advertised physical modes")
    vote_lines = [line.strip() for line in text.splitlines()
                  if "PRIORITY_" in line and " -> " in line]
    min_votes = [line for line in vote_lines if "PRIORITY_USER_SETTING_MIN_RENDER_FRAME_RATE" in line]
    min_rates = sorted({float(value) for line in min_votes
                        for value in re.findall(r"mMinRefreshRate=([0-9.]+)", line)})
    desired_specs = sorted({line.strip() for line in text.splitlines()
                            if "mDesiredDisplayModeSpecs=" in line or "mDisplayModeSpecs=" in line})
    render_rates = sorted({round(float(value), 3) for value in
                           re.findall(r"renderFrameRate[ =]([0-9.]+)", text)})
    return {
        "schema_version": 1, "input_sha256": hashlib.sha256(raw).hexdigest(),
        "default_peak_hz": peak, "default_hz": default,
        "candidate_defaults_observed": peak == 120 and default == 120,
        "advertised_physical_hz": rates, "snapshot_render_hz": render_rates,
        "minimum_render_votes_hz": min_rates,
        "minimum_vote_origin": "unknown; pinned Evolution fallback is 60 Hz even without a saved setting",
        "default_peak_exceeds_advertised_maximum": peak > max(rates) + 0.01,
        "idle_config_null_observed": "idleScreenRefreshRateConfig=null" in text,
        "desired_specs": desired_specs, "rate_votes": vote_lines,
        "scope": "single saved DisplayManager snapshot; may contain stale, off-screen or multiple-display state",
        "surfaceflinger_timer_state_verified": False,
        "physical_transitions_verified": False, "low_brightness_flicker_verified": False,
        "battery_improvement_measured": False, "phone_accessed": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    source = sub.add_parser("verify-source")
    source.add_argument("--workspace-root", type=Path, default=ROOT)
    snapshot = sub.add_parser("analyze-display")
    snapshot.add_argument("--display-dump", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = (verify_source(args.workspace_root) if args.command == "verify-source"
                  else analyze_display(read(args.display_dump)))
    except (ValueError, OSError, ET.ParseError) as error:
        print("refresh-policy: " + str(error), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
