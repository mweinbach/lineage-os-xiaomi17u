#!/usr/bin/env python3
"""Verify private snapshot receipts and report qualified measured deltas offline."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import stat

MAX_FILE = 262144
MAX_RECEIPT = 1048576


class AnalysisError(ValueError):
    pass


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AnalysisError("Duplicate JSON object key")
        result[key] = value
    return result


def finite(value):
    result = float(value)
    if not math.isfinite(result):
        raise AnalysisError("Nonfinite measurement")
    return result


def private_file(root, relative, limit):
    if not re.fullmatch(r"commands/[0-9]{3}-[A-Za-z0-9_.-]+\.(stdout|stderr)\.txt|manifest\.json", relative):
        raise AnalysisError("Unsafe receipt path")
    path = root
    for component in Path(relative).parts:
        path = path / component
        if path.is_symlink():
            raise AnalysisError("Symlink receipt path")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > limit:
        raise AnalysisError("Nonregular or oversized receipt input")
    with path.open("rb") as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        raise AnalysisError("Receipt input grew beyond bound")
    return data


def load_snapshot(root):
    root = Path(root).absolute()
    if any(part.is_symlink() for part in (root, *root.parents)):
        raise AnalysisError("Snapshot directory has a symlink component")
    try:
        manifest_bytes = private_file(root, "manifest.json", MAX_RECEIPT)
        manifest = json.loads(manifest_bytes, object_pairs_hook=unique_object)
        if type(manifest["schema_version"]) is not int or manifest["schema_version"] != 1 or manifest["tool"] != "collect_performance.py" or manifest["collection_kind"] != "read-only-performance-snapshot":
            raise AnalysisError("Not a performance snapshot receipt")
        if manifest["status"] not in ("complete", "partial"):
            raise AnalysisError("Unfinished snapshot")
        commands, artifacts = manifest["commands"], manifest["artifacts"]
        if not isinstance(commands, list) or not 1 <= len(commands) <= 120 or not isinstance(artifacts, list) or len(artifacts) != 2 * len(commands):
            raise AnalysisError("Invalid receipt command/artifact bounds")
        contents = {}
        for artifact in artifacts:
            name = artifact["path"]
            if name == "manifest.json" or name in contents:
                raise AnalysisError("Duplicate or self-referencing artifact")
            data = private_file(root, name, MAX_FILE)
            if type(artifact["bytes"]) is not int or artifact["bytes"] != len(data) or hashlib.sha256(data).hexdigest() != artifact["sha256"]:
                raise AnalysisError("Artifact size/hash mismatch")
            contents[name] = data.decode("utf-8", errors="replace").strip()
        readings, statuses, referenced = {}, {}, set()
        for command in commands:
            label = command["label"]
            if not isinstance(label, str) or label in readings or not re.fullmatch(r"[A-Za-z0-9_.-]+", label):
                raise AnalysisError("Duplicate or invalid command label")
            for stream in ("stdout", "stderr"):
                name = command[stream]
                if name not in contents or name in referenced or not name.endswith(f"-{label}.{stream}.txt"):
                    raise AnalysisError("Missing, reused or mislabelled command artifact")
                referenced.add(name)
            status_value = command["status"]
            if status_value not in ("ok", "unavailable", "timeout", "output_limit"):
                raise AnalysisError("Invalid observation status")
            if status_value == "ok" and command["exit_code"] != 0:
                raise AnalysisError("Contradictory success status")
            statuses[label] = status_value
            readings[label] = contents[command["stdout"]] if status_value == "ok" else None
        if referenced != contents.keys():
            raise AnalysisError("Unreferenced receipt artifact")
        return {"manifest": manifest, "readings": readings, "statuses": statuses,
                "receipt_sha256": hashlib.sha256(manifest_bytes).hexdigest()}
    except (KeyError, TypeError, OSError, json.JSONDecodeError) as exc:
        raise AnalysisError(f"Invalid or incomplete snapshot: {type(exc).__name__}") from exc


def required(snapshot, key):
    value = snapshot["readings"].get(key)
    if not value:
        raise AnalysisError(f"Required identity/time observation unavailable: {key}")
    return value


def uptime(snapshot, key):
    try:
        value = finite(required(snapshot, key).split()[0])
    except (ValueError, IndexError) as exc:
        raise AnalysisError("Invalid uptime") from exc
    if value < 0:
        raise AnalysisError("Negative uptime")
    return value


def timestamp(value):
    try:
        parsed = dt.datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            raise ValueError("No timezone")
        return parsed.timestamp()
    except (ValueError, TypeError) as exc:
        raise AnalysisError("Invalid wall-clock timestamp") from exc


def integer(value):
    if value is None or not re.fullmatch(r"[0-9]+", value):
        return None
    return int(value)


def delta(before, after, unit):
    if before is None or after is None:
        return {"status": "unavailable", "unit": unit}
    if after < before:
        return {"status": "rejected-counter-reset-or-wrap", "before": before, "after": after, "unit": unit}
    return {"status": "measured", "before": before, "after": after, "delta": after - before, "unit": unit}


def named_counters(value, pattern):
    if value is None:
        return {}
    counters = {}
    for line in value.splitlines():
        match = re.fullmatch(pattern, line.strip())
        if match:
            if match[1] in counters:
                return {}
            counters[match[1]] = int(match[2])
    return counters


def wake_counts(value):
    """Only named count columns; do not guess vendor timing-column units."""
    if not value:
        return {}
    lines = value.splitlines()
    header = lines[0].split()
    columns = [name for name in ("active_count", "event_count", "wakeup_count", "expire_count") if name in header]
    if not header or header[0] != "name" or len(set(header)) != len(header) or not columns:
        return {}
    result = {}
    for line in lines[1:]:
        fields = line.split()
        if len(fields) != len(header):
            return {}
        for name in columns:
            key = f"{fields[0]}/{name}"
            value = integer(fields[header.index(name)])
            if value is None or key in result:
                return {}
            result[key] = value
    return result


def context(snapshot):
    battery = snapshot["readings"].get("battery") or ""
    power = snapshot["readings"].get("power") or ""
    flags = re.findall(r"^\s*(AC|USB|Wireless|Dock) powered:\s*(true|false)\s*$", battery, re.M | re.I)
    plugged = {key.lower(): value.lower() == "true" for key, value in flags}
    ambiguous = len(plugged) != len(flags) or "UPDATES STOPPED" in battery.upper()
    wakefulness = re.findall(r"\bmWakefulness=(Awake|Asleep|Dozing|Dreaming)\b", power)
    screen = wakefulness[0] if len(wakefulness) == 1 else "unavailable"
    unplugged = not ambiguous and all(k in plugged for k in ("ac", "usb", "wireless")) and not any(plugged.values())
    return {"power_flags": plugged, "ambiguous_or_simulated_battery_state": ambiguous, "unplugged_at_endpoint": unplugged,
            "wakefulness_at_endpoint": screen, "operator_context": snapshot["manifest"]["options"].get("operator_context", "unspecified")}


def analyze(before, after):
    a, b = before["readings"], after["readings"]
    identity_keys = ("property-ro.product.manufacturer", "property-ro.product.device", "property-ro.build.fingerprint",
                     "property-ro.build.version.incremental", "property-ro.vendor.build.fingerprint", "kernel")
    for key in identity_keys:
        if required(before, key) != required(after, key):
            raise AnalysisError(f"Different exact device/build/kernel identity: {key}")
    if required(before, "property-ro.product.manufacturer").lower() != "xiaomi" or required(before, "property-ro.product.device") != "nezha":
        raise AnalysisError("Not the expected Xiaomi nezha")
    for snap in (before, after):
        device = snap["manifest"]["device"]
        if device.get("expected_device") != "nezha" or not isinstance(device.get("serial"), str) or not re.fullmatch(r"[A-Za-z0-9_.:\-]{1,256}", device["serial"]) or device["serial"].startswith(("-", "emulator-")):
            raise AnalysisError("Invalid explicit physical device identity")
        if snap["readings"].get("property-ro.kernel.qemu") not in ("", "0"):
            raise AnalysisError("Emulated or unverifiable physical device")
    if before["manifest"]["device"]["serial"] != after["manifest"]["device"]["serial"]:
        raise AnalysisError("Different explicitly selected devices")
    boot_ids = [required(snap, key) for snap in (before, after) for key in ("boot-id-start", "boot-id-end")]
    if len(set(boot_ids)) != 1 or not re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", boot_ids[0]):
        raise AnalysisError("Different or invalid boot identity; counter comparison refused")
    intervals = [(uptime(s, "uptime-start"), uptime(s, "uptime-end")) for s in (before, after)]
    if any(end < start or end - start > 240 for start, end in intervals) or intervals[1][0] <= intervals[0][1]:
        raise AnalysisError("Nonpositive, overlapping or reset uptime interval")
    elapsed = sum(intervals[1]) / 2 - sum(intervals[0]) / 2
    wall = []
    for snap in (before, after):
        start = timestamp(snap["manifest"]["started_at"])
        end = timestamp(snap["manifest"]["completed_at"])
        if end < start or end - start > 240:
            raise AnalysisError("Invalid snapshot wall duration")
        wall.append((start, end))
    wall_elapsed = sum(wall[1]) / 2 - sum(wall[0]) / 2
    if wall[1][0] <= wall[0][1] or abs(wall_elapsed - elapsed) > max(60, elapsed * 0.05):
        raise AnalysisError("Wall clock and device uptime disagree; interval refused")
    contexts = [context(s) for s in (before, after)]
    qualified = all(c["unplugged_at_endpoint"] and c["wakefulness_at_endpoint"] == "Asleep" and c["operator_context"] == "screen-off-unplugged" for c in contexts)
    result = {
        "schema_version": 1, "status": "measured-observations-only", "receipt_sha256": [s["receipt_sha256"] for s in (before, after)],
        "receipt_integrity": "Artifact hashes verified against retained manifests; manifests are not signed attestations.",
        "interval": {"device_uptime_midpoint_seconds": elapsed, "wall_midpoint_seconds": wall_elapsed,
                     "endpoint_capture_uptime_ranges": intervals, "screen_off_unplugged_endpoints_and_declaration": qualified},
        "contexts": contexts, "counters": {}, "warnings": [
            "Endpoint state and operator declarations do not prove screen/plug conditions throughout the interval.",
            "ADB collection and USB reconnection can wake the device, affect suspend and charging; no polling through idle.",
            "Snapshot commands are sequential, not simultaneous; midpoint duration is approximate.",
            "Service registration or dumpsys output is not evidence of effective boosts, efficiency or a performance pass.",
            "LMKD log tail is a bounded observation and may rotate, omit events or duplicate prior events; no kill-rate delta inferred.",
            "No battery-life improvement or tuning recommendation is established by this report."],
        "unavailable": [{k: v for k, v in s["statuses"].items() if v != "ok"} for s in (before, after)],
        "memory_gauges": {},
    }
    for key in ("suspend-success", "suspend-fail"):
        result["counters"][key] = delta(integer(a.get(key)), integer(b.get(key)), "count")
    for label, pattern, unit in (
        ("vmstat", r"((?:pgscan|pgsteal|allocstall|compact_|workingset_refault|workingset_activate)\w*|pgmajfault|pswpin|pswpout|oom_kill)\s+([0-9]+)", "kernel event/page count, field-dependent"),
        ("cpuidle", r"(/sys/devices/system/cpu/cpu[0-9]+/cpuidle/state[0-9]+/(?:time|usage)):([0-9]+)", "time: microseconds; usage: count; per CPU/state"),
        ("psi-memory", r"(some|full)\s+avg10=[0-9.]+\s+avg60=[0-9.]+\s+avg300=[0-9.]+\s+total=([0-9]+)", "microseconds"),
        ("psi-cpu", r"(some|full)\s+avg10=[0-9.]+\s+avg60=[0-9.]+\s+avg300=[0-9.]+\s+total=([0-9]+)", "microseconds"),
        ("psi-io", r"(some|full)\s+avg10=[0-9.]+\s+avg60=[0-9.]+\s+avg300=[0-9.]+\s+total=([0-9]+)", "microseconds"),
    ):
        first, second = named_counters(a.get(label), pattern), named_counters(b.get(label), pattern)
        result["counters"][label] = {name: delta(first.get(name), second.get(name), unit) for name in sorted(first.keys() | second.keys())} or {"status": "unavailable"}
    for label in ("meminfo", "swaps", "swappiness", "page-cluster", "read-ahead", *(f"zram{i}-stats" for i in range(8))):
        result["memory_gauges"][label] = {"before": a.get(label), "after": b.get(label), "interpretation": "Gauge/configuration snapshots, not cumulative event counters or a performance verdict"}
    for label in ("wake-sources", "wake-sources-fallback"):
        first, second = wake_counts(a.get(label)), wake_counts(b.get(label))
        result["counters"][label] = {name: delta(first.get(name), second.get(name), "count") for name in sorted(first.keys() | second.keys())} or {"status": "unavailable"}
    first, second = integer(a.get("charge-counter")), integer(b.get("charge-counter"))
    charge = {"status": "unavailable", "unit": "microampere-hours (Linux power_supply charge_counter ABI; vendor implementation uncalibrated)", "source": "/sys/class/power_supply/battery/charge_counter"}
    if first is not None and second is not None:
        if first <= 0 or second <= 0:
            charge["status"] = "rejected-zero-or-reset-charge-counter"
        elif second > first:
            charge["status"] = "rejected-charging-or-counter-reset"
        else:
            charge.update(status="measured-net-counter-drop", before=first, after=second, delta_uAh=first - second,
                          approximate_average_net_mA=(first - second) * 3.6 / elapsed,
                          screen_off_unplugged_qualified_endpoints=qualified)
            if not qualified:
                result["warnings"].append("Charge delta is not an idle-drain result: screen-off/unplugged endpoint qualification is absent.")
    result["charge"] = charge
    result["observations"] = {label: {"before_status": before["statuses"].get(label, "unavailable"), "after_status": after["statuses"].get(label, "unavailable"), "meaning": "Retained snapshot only; no effective-operation or efficiency verdict"} for label in ("power", "power-hints", "thermal", "display", "workload-classifier", "lmkd", "lmkd-log-tail", "wake-sources", "wake-sources-fallback", "suspend-service")}
    result["warnings"].append("Charge-counter drop is not energy; no mWh estimate is fabricated from instantaneous voltage or power_profile.xml.")
    result["warnings"].append("A fuel-gauge recalibration/reset to a smaller nonzero value cannot be distinguished from discharge by two endpoints alone.")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    args = parser.parse_args(argv)
    try:
        result = analyze(load_snapshot(args.before), load_snapshot(args.after))
    except (AnalysisError, KeyError, TypeError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "reason": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
