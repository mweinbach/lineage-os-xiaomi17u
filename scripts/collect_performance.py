#!/usr/bin/env python3
"""One explicit-device, read-only performance snapshot; never poll during idle."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shlex
import subprocess
import time

if __package__:
    from .collect_stock import Collector, CollectionError, secure_write, file_receipt, utc_now
else:
    from collect_stock import Collector, CollectionError, secure_write, file_receipt, utc_now

PROPERTIES = (
    "ro.build.fingerprint", "ro.build.version.incremental", "ro.vendor.build.fingerprint",
    "init.svc.lmkd", "init.svc.vendor.perfservice", "init.svc.vendor.perfservice_aidl",
    "init.svc.vendor.power-hal", "vendor.perf.workloadclassifier.enable",
    "vendor.mpctl.init.complete", "ro.vendor.wlc.exit.timeout",
    "ro.vendor.qti.skip_wlc_default_scan", "ro.vendor.qti.set_wlc_deferred_scan",
    "persist.vendor.build.date.utc", "ro.bootimage.build.date.utc", "ro.board.first_api_level",
    "init.svc.memory-init-boot", "init.svc.memory-post-boot", "ro.lmk.use_psi",
    "ro.lmk.psi_partial_stall_ms", "ro.lmk.psi_complete_stall_ms", "ro.lmk.thrashing_limit",
    "ro.lmk.swap_free_low_percentage", "ro.lmk.low", "ro.lmk.medium", "ro.lmk.critical",
)
READS = (
    ("battery", ("dumpsys", "battery")),
    ("power", ("dumpsys", "power")),
    ("display", ("dumpsys", "display")),
    ("surface-flinger", ("dumpsys", "SurfaceFlinger")),
    ("power-hints", ("dumpsys", "performance_hint")),
    ("thermal", ("dumpsys", "thermalservice")),
    ("min-refresh", ("settings", "get", "system", "min_refresh_rate")),
    ("peak-refresh", ("settings", "get", "system", "peak_refresh_rate")),
    ("suspend-success", ("cat", "/sys/power/suspend_stats/success")),
    ("suspend-fail", ("cat", "/sys/power/suspend_stats/fail")),
    ("suspend-debug", ("cat", "/sys/kernel/debug/suspend_stats")),
    ("wake-sources", ("cat", "/sys/kernel/debug/wakeup_sources")),
    ("wake-sources-fallback", ("cat", "/sys/kernel/wakeup_sources")),
    ("suspend-service", ("dumpsys", "suspend_control_internal")),
    ("charge-counter", ("cat", "/sys/class/power_supply/battery/charge_counter")),
    ("current-now", ("cat", "/sys/class/power_supply/battery/current_now")),
    ("voltage-now", ("cat", "/sys/class/power_supply/battery/voltage_now")),
    ("psi-memory", ("cat", "/proc/pressure/memory")),
    ("psi-cpu", ("cat", "/proc/pressure/cpu")),
    ("psi-io", ("cat", "/proc/pressure/io")),
    ("meminfo", ("cat", "/proc/meminfo")),
    ("vmstat", ("cat", "/proc/vmstat")),
    ("swaps", ("cat", "/proc/swaps")),
    ("swappiness", ("cat", "/proc/sys/vm/swappiness")),
    ("page-cluster", ("cat", "/proc/sys/vm/page-cluster")),
    ("lmkd", ("dumpsys", "lmkd")),
    ("lmkd-log-tail", ("logcat", "-d", "-b", "system", "-t", "200", "-v", "threadtime", "lmkd:I", "*:S")),
    ("workload-classifier", ("dumpsys", "package", "com.qualcomm.qti.workloadclassifier")),
)
UNAVAILABLE = re.compile(r"permission denied|no such file|can't find service|cannot find service|not found|not permitted|error:|permission denial", re.I)
MAX_COMMANDS = 120
MAX_BYTES = 262144
TOTAL_SECONDS = 180


def bounded_run(argv, timeout, max_bytes=MAX_BYTES):
    """Drain both pipes with a combined strict cap; never buffer unbounded output."""
    data = {"stdout": bytearray(), "stderr": bytearray()}
    started = time.monotonic()
    status = "ok"
    try:
        process = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    except OSError as exc:
        return "unavailable", None, b"", str(exc).encode()[:max_bytes]
    try:
        with selectors.DefaultSelector() as selector:
            for name in data:
                stream = getattr(process, name)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = timeout - (time.monotonic() - started)
                if remaining <= 0:
                    status = "timeout"
                    break
                for key, _ in selector.select(min(remaining, 0.1)):
                    chunk = os.read(key.fileobj.fileno(), 8192)
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    room = max_bytes - sum(map(len, data.values()))
                    data[key.data].extend(chunk[:room])
                    if len(chunk) > room:
                        status = "output_limit"
                        break
                if status != "ok":
                    break
            if status == "ok":
                try:
                    process.wait(timeout=max(0.001, timeout - (time.monotonic() - started)))
                except subprocess.TimeoutExpired:
                    status = "timeout"
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        process.stdout.close()
        process.stderr.close()
    if status == "ok" and (process.returncode != 0 or UNAVAILABLE.search(bytes(data["stdout"] + data["stderr"]).decode(errors="replace"))):
        status = "unavailable"
    return status, process.returncode, bytes(data["stdout"]), bytes(data["stderr"])


def discovered_paths(kind, output):
    """Never execute a path supplied by the device without a narrow allowlist."""
    lines = output.splitlines()
    if kind == "cpuidle":
        pattern, limit = r"/sys/devices/system/cpu/cpu(?:[0-9]|1[0-5])/cpuidle/state[0-7]", 128
    elif kind == "block":
        pattern, limit = r"(?:zram[0-7]|sd[a-z]|mmcblk[0-9]|nvme[0-9]n[0-9]|dm-[0-9]{1,3}|loop[0-9]{1,3})", 64
    else:
        raise CollectionError("Unknown discovery category")
    if len(lines) > limit or len(set(lines)) != len(lines) or any(not re.fullmatch(pattern, line) for line in lines):
        raise CollectionError("Discovery exceeds the bounded path allowlist; skipped")
    return sorted(lines)


class PerformanceCollector(Collector):
    def __init__(self, args):
        super().__init__(argparse.Namespace(**vars(args), include_dumpsys=False, feature_diagnostics=False, pull_stock_apks=False, apk_package=[]))
        self.deadline = time.monotonic() + TOTAL_SECONDS
        self.manifest.update(tool="collect_performance.py", tool_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                             collection_kind="read-only-performance-snapshot", schema_version=1)
        self.manifest["options"] = {"timeout_seconds": args.timeout, "max_command_bytes": MAX_BYTES,
                                    "max_commands": MAX_COMMANDS, "total_seconds": TOTAL_SECONDS,
                                    "operator_context": args.context}

    def run(self, label, arguments, *, selected=True, pull=False):
        if pull or len(self.manifest["commands"]) >= MAX_COMMANDS or time.monotonic() >= self.deadline:
            raise CollectionError("Read-only collection budget exhausted")
        command = [self.args.adb] + (["-s", self.args.serial] if selected else [])
        command += ["shell", shlex.join(arguments[1:])] if arguments[0] == "shell" else list(arguments)
        started = time.monotonic()
        started_at = utc_now()
        status, code, stdout, stderr = bounded_run(command, min(self.args.timeout, self.deadline - started))
        record = {"label": label, "argv": command, "status": status, "exit_code": code,
                  "started_at": started_at, "elapsed_seconds": time.monotonic() - started}
        for stream, content in (("stdout", stdout), ("stderr", stderr)):
            path = self.output / "commands" / f"{len(self.manifest['commands']):03d}-{label}.{stream}.txt"
            secure_write(path, content)
            receipt = file_receipt(path, self.output)
            self.manifest["artifacts"].append(receipt)
            record[stream] = receipt["path"]
        self.manifest["commands"].append(record)
        self.save()
        return record, stdout.decode(errors="replace").strip()

    def collect(self):
        self.prepare()
        started = time.monotonic()
        try:
            self.preflight()
            for label, command in (("boot-id-start", ("cat", "/proc/sys/kernel/random/boot_id")),
                                   ("uptime-start", ("cat", "/proc/uptime")), ("kernel", ("uname", "-a"))):
                self.run(label, ("shell", *command))
            for prop in PROPERTIES:
                self.property(prop)
            for label, command in READS:
                self.run(label, ("shell", *command))
            record, output = self.run("discover-cpuidle", ("shell", "find", "/sys/devices/system/cpu", "-maxdepth", "3", "-name", "state[0-9]*"))
            if record["status"] == "ok":
                paths = self.discovery("cpuidle", output)
                if paths:
                    self.run("cpuidle", ("shell", "grep", "-H", "^", *(f"{p}/{f}" for p in paths for f in ("name", "time", "usage"))))
            record, output = self.run("discover-block", ("shell", "ls", "/sys/block"))
            if record["status"] == "ok":
                blocks = self.discovery("block", output)
                if blocks:
                    self.run("read-ahead", ("shell", "grep", "-H", "^", *(f"/sys/block/{b}/queue/read_ahead_kb" for b in blocks)))
                for block in (b for b in blocks if re.fullmatch("zram[0-7]", b)):
                    self.run(f"{block}-stats", ("shell", "grep", "-H", "^", *(f"/sys/block/{block}/{f}" for f in ("mm_stat", "io_stat", "bd_stat", "disksize", "comp_algorithm"))))
            self.run("uptime-end", ("shell", "cat", "/proc/uptime"))
            self.run("boot-id-end", ("shell", "cat", "/proc/sys/kernel/random/boot_id"))
        except (CollectionError, OSError) as exc:
            self.error(str(exc))
        except KeyboardInterrupt:
            self.manifest["errors"].append("Interrupted")
        self.manifest["host_elapsed_seconds"] = time.monotonic() - started
        partial = bool(self.manifest["errors"]) or any(c["status"] != "ok" for c in self.manifest["commands"])
        self.finish("partial" if partial else "complete")
        return 3 if partial else 0

    def discovery(self, kind, output):
        try:
            return discovered_paths(kind, output)
        except CollectionError as exc:
            self.manifest["skipped"].append({"discovery": kind, "status": "unavailable", "reason": str(exc)})
            self.error(f"{kind}: {exc}")
            return []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True)
    parser.add_argument("--expected-device", required=True, choices=("nezha",))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--adb", default="adb")
    parser.add_argument("--timeout", default=5.0, type=float)
    parser.add_argument("--context", choices=("screen-off-unplugged", "interactive", "unspecified"), default="unspecified",
                        help="Operator declaration, not proof of interval conditions")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.:\-]{1,256}", args.serial) or args.serial.startswith("-"):
        parser.error("Explicit serial must be a plain non-option device identifier")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 15:
        parser.error("Timeout must be finite, >0 and <=15 seconds")
    if args.dry_run:
        print("No ADB execution or filesystem writes. One identity-checked read-only snapshot; no polling or phone changes.")
        print(f"Bounds: {MAX_COMMANDS} commands, {MAX_BYTES} combined bytes/command, {TOTAL_SECONDS}s total; failures remain unavailable.")
        return 0
    try:
        return PerformanceCollector(args).collect()
    except (OSError, CollectionError) as exc:
        print(f"Collection stopped: {exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
