#!/usr/bin/env python3
"""Plan or collect private, bounded recovery diagnostics without changing a phone."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import re
import selectors
import shlex
import subprocess
import sys
import tempfile
import time
from typing import Any, Sequence

if __package__:
    from .collect_stock import CollectionError, file_receipt, secure_write, utc_now
else:
    from collect_stock import CollectionError, file_receipt, secure_write, utc_now


ROOT = Path(__file__).resolve().parents[1]
MAX_SESSION_BYTES = 32 * 1024 * 1024
MAX_PSTORE_FILES = 8
PSTORE_NAME = re.compile(r"(?:console-ramoops(?:-[0-9]+)?|dmesg-ramoops-[0-9]+)\Z")
IDENTITY_PROPERTIES = (
    "ro.product.manufacturer", "ro.product.device", "ro.kernel.qemu",
)
MODE_PROPERTIES = (
    "ro.bootmode", "ro.boot.mode", "init.svc.recovery", "sys.boot_completed",
)
PROPERTIES = (
    "ro.twrp.version", "ro.build.fingerprint", "ro.build.version.release",
    "ro.build.version.sdk", "ro.build.version.security_patch",
    "ro.vendor.build.security_patch", "ro.bootimage.build.version.security_patch",
    "ro.boot.hardware", "ro.board.platform", "ro.boot.slot_suffix",
    "ro.boot.verifiedbootstate", "ro.boot.vbmeta.device_state",
    "ro.boot.flash.locked", "ro.boot.veritymode", "ro.boot.bootreason",
    "ro.crypto.state", "ro.crypto.type",
)
LOGCAT_COMMAND = (
    "logcat", "-d", "-b", "main", "-b", "system", "-b", "crash",
    "-v", "threadtime", "-t", "1000", "recovery:*", "Recovery:*", "twrp:*",
    "TWRP:*", "init:*", "adbd:*", "vold:*", "fs_mgr:*", "libfs_mgr:*",
    "libvintf:*", "avc:*", "DEBUG:*", "*:S",
)
READ_COMMANDS = (
    ("kernel", ("uname", "-r")),
    ("dmesg", ("dmesg",)),
    ("logcat", LOGCAT_COMMAND),
    ("selinux", ("getenforce",)),
    ("mounts", ("cat", "/proc/self/mounts")),
    ("partitions", ("cat", "/proc/partitions")),
)


class SessionLimit(CollectionError):
    """The collection's time or byte budget has been consumed."""


def bounded_run(command: Sequence[str], *, timeout: float, max_bytes: int) -> dict[str, Any]:
    """Drain both pipes incrementally; stop the local ADB client at a hard limit.

    No output buffer ever exceeds max_bytes. Reading one extra byte lets an
    exactly-sized, complete stream differ from a truncated stream. Stopping the
    client never issues a device-side kill, reboot, log clear or other command.
    """
    started = time.monotonic()
    deadline = started + timeout
    buffers = {"stdout": bytearray(), "stderr": bytearray()}
    truncated = {"stdout": False, "stderr": False}
    status, exit_code = "running", None
    process = None
    selector = selectors.DefaultSelector()
    try:
        process = subprocess.Popen(
            list(command), stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, shell=False, bufsize=0,
        )
        for name in buffers:
            selector.register(getattr(process, name), selectors.EVENT_READ, name)
        while selector.get_map() and status == "running":
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                status = "timeout"
                break
            for key, _ in selector.select(timeout=min(remaining, 0.25)):
                name = key.data
                room = max_bytes - len(buffers[name])
                chunk = os.read(key.fileobj.fileno(), min(65536, room + 1))
                if not chunk:
                    selector.unregister(key.fileobj)
                    continue
                buffers[name].extend(chunk[:room])
                if len(chunk) > room:
                    truncated[name] = True
                    status = "byte_limit"
                    break
        if status == "running":
            try:
                exit_code = process.wait(timeout=max(0, deadline - time.monotonic()))
                status = "ok" if exit_code == 0 else "failed"
            except subprocess.TimeoutExpired:
                status = "timeout"
    except KeyboardInterrupt:
        status = "interrupted"
    except OSError as exc:
        status = "unavailable"
        note = str(exc).encode("utf-8", errors="replace")
        room = max_bytes - len(buffers["stderr"])
        buffers["stderr"].extend(note[:room])
        truncated["stderr"] |= len(note) > room
    finally:
        # Cleanup is separately bounded and never invokes another executable.
        if process is not None:
            if process.poll() is None:
                try:
                    process.kill()
                except ProcessLookupError:
                    pass
            try:
                process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                pass
            for name in buffers:
                stream = getattr(process, name)
                if stream is not None:
                    stream.close()
        selector.close()
    if status == "failed":
        diagnostic = bytes(buffers["stderr"] + buffers["stdout"]).lower()
        if b"permission denied" in diagnostic or b"operation not permitted" in diagnostic:
            status = "permission_denied"
        elif b"no such file or directory" in diagnostic:
            status = "missing"
    return {
        "status": status, "exit_code": exit_code,
        "stdout": bytes(buffers["stdout"]), "stderr": bytes(buffers["stderr"]),
        "truncated_streams": [name for name in buffers if truncated[name]],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def selected_transport(output: str, serial: str) -> tuple[str, str]:
    """Pin a transport within its ADB server lifetime; never connect or reconnect."""
    selected = []
    seen = set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[0] in {"List", "*", "adb"}:
            continue
        if fields[0] in seen:
            raise CollectionError("ADB reported duplicate device identifiers.")
        seen.add(fields[0])
        if fields[0] == serial:
            selected.append(fields)
    if len(selected) != 1:
        raise CollectionError("The explicitly selected device is not connected.")
    fields = selected[0]
    if fields[1] not in {"device", "recovery"}:
        raise CollectionError("The selected ADB device is not online and authorized; diagnostics were not read.")
    transports = [field.removeprefix("transport_id:") for field in fields[2:] if field.startswith("transport_id:")]
    if len(transports) != 1 or not re.fullmatch(r"[1-9][0-9]{0,9}", transports[0]):
        raise CollectionError("ADB did not provide one usable transport ID; use current platform-tools.")
    return fields[1], transports[0]


def safe_pstore_name(name: str) -> bool:
    return len(name) <= 80 and PSTORE_NAME.fullmatch(name) is not None


def remote_command(tokens: Sequence[str]) -> str:
    """Admit only fixed reads; quote every token for ADB's remote shell."""
    command = tuple(tokens)
    fixed = {item for _, item in READ_COMMANDS}
    fixed.update({("pidof", "recovery"), ("ls", "-1", "/sys/fs/pstore")})
    if command in fixed:
        return shlex.join(command)
    if len(command) == 2 and command[0] == "getprop" and command[1] in (
        IDENTITY_PROPERTIES + MODE_PROPERTIES + PROPERTIES
    ):
        return shlex.join(command)
    if len(command) == 2 and command[0] == "readlink" and re.fullmatch(r"/proc/[1-9][0-9]{0,9}/exe", command[1]):
        return shlex.join(command)
    if len(command) == 4 and command[:2] == ("tail", "-c"):
        count, path = command[2:]
        allowed_path = path == "/tmp/recovery.log" or (
            path.startswith("/sys/fs/pstore/") and safe_pstore_name(path.removeprefix("/sys/fs/pstore/"))
        )
        if count.isdecimal() and 0 < int(count) <= 4 * 1024 * 1024 and allowed_path:
            quoted = shlex.quote(path)
            # A symlink or non-regular entry must never redirect a diagnostic
            # read into user data. These tests do not mount or change anything.
            return (
                f"if [ -L {quoted} ]; then printf '%s\\n' 'Refusing symlink diagnostic' >&2; exit 4; "
                f"elif [ -e {quoted} ] && [ ! -f {quoted} ]; then printf '%s\\n' 'Refusing non-regular diagnostic' >&2; exit 4; "
                f"else {shlex.join(command)}; fi"
            )
    raise CollectionError("A command outside the recovery diagnostic allowlist was refused.")


class Collector:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.output = args.output.expanduser().absolute()
        self.transport_id: str | None = None
        self.deadline = time.monotonic() + args.total_timeout
        self.captured_bytes = 0
        self.verified = False
        self.manifest: dict[str, Any] = {
            "schema_version": 1,
            "tool": "collect_recovery.py",
            "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "helper_sha256": hashlib.sha256(Path(__file__).with_name("collect_stock.py").read_bytes()).hexdigest(),
            "collection_kind": "bounded-read-only-recovery-diagnostics",
            "started_at": utc_now(), "status": "collecting",
            "device": {"serial": args.serial, "expected_device": args.expected_device},
            "options": {
                "include_pstore": args.include_pstore, "timeout_seconds": args.timeout,
                "total_timeout_seconds": args.total_timeout, "max_bytes_per_stream": args.max_bytes,
                "max_session_output_bytes": MAX_SESSION_BYTES, "max_pstore_files": MAX_PSTORE_FILES,
            },
            "properties": {}, "commands": [], "artifacts": [], "errors": [], "skipped": [], "warnings": [],
            "privacy": "Private evidence: serials and logs can contain personal data or secrets. Review and redact before sharing.",
            "scope": "Bounded observations only; complete means requested reads finished, not that all logs or a working recovery were verified.",
        }

    def prepare(self) -> None:
        evidence = ROOT / "evidence"
        try:
            relative = self.output.relative_to(evidence)
        except ValueError as exc:
            raise CollectionError("--output must be a new directory inside this checkout's ignored evidence directory.") from exc
        if not relative.parts or any(part in {".", ".."} for part in relative.parts):
            raise CollectionError("Choose a new evidence subdirectory without traversal components.")
        current = ROOT
        for part in ("evidence", *relative.parts[:-1]):
            current /= part
            if current.is_symlink():
                raise CollectionError("Evidence directory ancestors must not be symlinks.")
            try:
                current.mkdir(mode=0o700)
            except FileExistsError:
                if not current.is_dir():
                    raise CollectionError("Evidence directory ancestors must be directories.")
        try:
            self.output.mkdir(mode=0o700)
        except FileExistsError as exc:
            raise CollectionError("Output directory already exists; choose a new directory.") from exc
        (self.output / "commands").mkdir(mode=0o700)
        secure_write(self.output / ".gitignore", b"*\n!.gitignore\n")
        self.save()

    def save(self) -> None:
        temporary = None
        try:
            # A fixed temporary path could be stranded by an interruption and
            # then prevent finish("interrupted") from saving the final status.
            with tempfile.NamedTemporaryFile(mode="wb", prefix=".manifest-", suffix=".tmp",
                                             dir=self.output, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write((json.dumps(self.manifest, indent=2) + "\n").encode("utf-8"))
            temporary.replace(self.output / "manifest.json")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def run(self, label: str, arguments: Sequence[str], *, selected: bool = True,
            limit: int | None = None, scope: str | None = None) -> tuple[dict[str, Any], str]:
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise SessionLimit("The session time limit was reached; remaining reads were not attempted.")
        byte_limit = min(limit or self.args.max_bytes, self.args.max_bytes,
                         (MAX_SESSION_BYTES - self.captured_bytes) // 2)
        if byte_limit <= 0:
            raise SessionLimit("The session output byte limit was reached; remaining reads were not attempted.")
        if selected:
            if self.transport_id is None or tuple(arguments) not in {("get-state",), ("features",)}:
                raise CollectionError("Only selected transport state and feature checks are accepted by the direct ADB interface.")
            command = [self.args.adb, "-t", self.transport_id, *arguments]
        else:
            if tuple(arguments) not in {("version",), ("devices", "-l")}:
                raise CollectionError("Only ADB version and inventory are allowed without a selected transport.")
            command = [self.args.adb, *arguments]
        return self.execute(label, command, remaining, byte_limit, scope)

    def shell(self, label: str, tokens: Sequence[str], *, limit: int | None = None,
              scope: str | None = None) -> tuple[dict[str, Any], str]:
        # Validate before considering the budget, so no future extension can
        # use this helper as an unrestricted shell interface.
        quoted = remote_command(tokens)
        if self.transport_id is None:
            raise CollectionError("A selected transport is required before device reads.")
        preflight_property = len(tokens) == 2 and tokens[0] == "getprop" and tokens[1] in IDENTITY_PROPERTIES + MODE_PROPERTIES
        preflight_process = tuple(tokens) == ("pidof", "recovery") or (len(tokens) == 2 and tokens[0] == "readlink")
        if not self.verified and not (preflight_property or preflight_process):
            raise CollectionError("Recovery mode must pass preflight before diagnostic reads.")
        remaining = self.deadline - time.monotonic()
        byte_limit = min(limit or self.args.max_bytes, self.args.max_bytes,
                         (MAX_SESSION_BYTES - self.captured_bytes) // 2)
        if remaining <= 0 or byte_limit <= 0:
            raise SessionLimit("The session time or output byte limit was reached; remaining reads were not attempted.")
        command = [self.args.adb, "-t", self.transport_id, "shell", "-T", quoted]
        return self.execute(label, command, remaining, byte_limit, scope, remote_argv=list(tokens))

    def execute(self, label: str, command: list[str], remaining: float, byte_limit: int,
                scope: str | None, **metadata: Any) -> tuple[dict[str, Any], str]:
        result = bounded_run(command, timeout=min(self.args.timeout, remaining), max_bytes=byte_limit)
        record = {key: value for key, value in result.items() if key not in {"stdout", "stderr"}}
        record.update({"label": label, "argv": command, "max_bytes_per_stream": byte_limit, **metadata})
        if scope is not None:
            record["scope"] = scope
        number = len(self.manifest["commands"]) + 1
        for name in ("stdout", "stderr"):
            content = result[name]
            self.captured_bytes += len(content)
            path = self.output / "commands" / f"{number:03d}-{label}.{name}.txt"
            secure_write(path, content)
            receipt = file_receipt(path, self.output)
            self.manifest["artifacts"].append(receipt)
            record[name] = receipt["path"]
        self.manifest["commands"].append(record)
        self.manifest["captured_output_bytes"] = self.captured_bytes
        self.save()
        if record["status"] == "interrupted":
            raise KeyboardInterrupt
        return record, result["stdout"].decode("utf-8", errors="replace").strip()

    def property(self, name: str) -> tuple[dict[str, Any], str]:
        record, value = self.shell(f"property-{name}", ("getprop", name), limit=4096)
        self.manifest["properties"][name] = {"status": record["status"], "value": value if record["status"] == "ok" else None}
        self.save()
        return record, value

    def preflight(self) -> None:
        record, _ = self.run("adb-version", ("version",), selected=False, limit=4096)
        if record["status"] != "ok":
            raise CollectionError("ADB is unavailable; no recovery diagnostics were read.")
        record, inventory = self.run("device-inventory", ("devices", "-l"), selected=False, limit=65536)
        if record["status"] != "ok":
            raise CollectionError("A complete ADB device inventory is required before collection.")
        state, self.transport_id = selected_transport(inventory, self.args.serial)
        self.manifest["device"].update({
            "adb_state": state, "transport_id": self.transport_id,
            "transport_scope": "Transport IDs are scoped to one ADB server lifetime. A server restart invalidates this session.",
        })
        record, selected_state = self.run("selected-transport-state", ("get-state",), limit=256)
        if record["status"] != "ok" or selected_state not in {"device", "recovery"} or selected_state != state:
            raise CollectionError("The selected transport changed or is no longer online; collection stopped.")
        record, features = self.run("selected-transport-features", ("features",), limit=4096)
        if record["status"] != "ok" or "shell_v2" not in re.split(r"[,\s]+", features):
            raise CollectionError("The selected recovery must support ADB shell_v2 exit statuses; diagnostics were not read.")
        self.manifest["device"]["shell_v2_verified"] = True
        for name in IDENTITY_PROPERTIES:
            record, _ = self.property(name)
            if record["status"] != "ok":
                raise CollectionError("The selected device identity could not be verified.")
        properties = self.manifest["properties"]
        manufacturer = properties["ro.product.manufacturer"]["value"]
        codename = properties["ro.product.device"]["value"]
        if manufacturer.casefold() != "xiaomi" or codename != "nezha":
            raise CollectionError("Device identity must be Xiaomi and exactly nezha; diagnostics were not read.")
        if properties["ro.kernel.qemu"]["value"] not in {"", "0"}:
            raise CollectionError("An emulator cannot supply physical recovery evidence.")
        for name in MODE_PROPERTIES:
            record, _ = self.property(name)
            if record["status"] != "ok":
                raise CollectionError("Recovery mode could not be verified; diagnostics were not read.")
        modes = {properties[name]["value"] for name in ("ro.bootmode", "ro.boot.mode")}
        if "recovery" not in modes and state != "recovery":
            raise CollectionError("The selected device has no recovery boot-mode marker; normal Android is refused.")
        if any(mode not in {"", "recovery"} for mode in modes):
            raise CollectionError("Conflicting boot-mode properties prevent recovery verification.")
        if properties["sys.boot_completed"]["value"] not in {"", "0"}:
            raise CollectionError("A completed normal Android boot was reported; recovery diagnostics were not read.")
        if properties["init.svc.recovery"]["value"] != "running":
            raise CollectionError("The recovery init service is not running; collection stopped.")
        record, pid = self.shell("recovery-process", ("pidof", "recovery"), limit=256)
        if record["status"] != "ok" or not re.fullmatch(r"[1-9][0-9]{0,9}", pid):
            raise CollectionError("One running recovery process is required; diagnostics were not read.")
        record, executable = self.shell("recovery-executable", ("readlink", f"/proc/{pid}/exe"), limit=4096)
        if record["status"] != "ok" or executable not in {"/system/bin/recovery", "/sbin/recovery"}:
            raise CollectionError("The running recovery executable could not be verified; collection stopped.")
        self.verified = True
        self.manifest["device"].update({"manufacturer": manufacturer, "codename": codename, "recovery_executable": executable})
        self.manifest["recovery_preflight_passed"] = True
        self.save()

    def pstore(self) -> None:
        record, inventory = self.shell("pstore-inventory", ("ls", "-1", "/sys/fs/pstore"), limit=16384)
        if record["status"] != "ok":
            return
        names = inventory.splitlines() if inventory else []
        allowed = sorted(set(name for name in names if safe_pstore_name(name)))
        excluded = len(names) - sum(safe_pstore_name(name) for name in names)
        if excluded:
            self.manifest["skipped"].append({"kind": "pstore", "count": excluded, "reason": "Outside console/dmesg ramoops basename allowlist; not read."})
        if len(allowed) > MAX_PSTORE_FILES:
            self.manifest["errors"].append("Pstore file-count limit reached; additional allowlisted entries were not read.")
        for name in allowed[:MAX_PSTORE_FILES]:
            self.shell(f"pstore-{name}", ("tail", "-c", str(self.args.max_bytes), f"/sys/fs/pstore/{name}"),
                       scope=f"Last at most {self.args.max_bytes} bytes of one regular pstore file; previous-boot data may be sensitive.")
        self.save()

    def finish(self, status: str) -> None:
        self.manifest["status"] = status
        self.manifest["completed_at"] = utc_now()
        self.save()

    def collect(self) -> int:
        self.prepare()
        try:
            self.preflight()
            for name in PROPERTIES:
                self.property(name)
            self.shell("recovery-log", ("tail", "-c", str(self.args.max_bytes), "/tmp/recovery.log"),
                       scope=f"Last at most {self.args.max_bytes} bytes; no claim to capture the entire live log.")
            for label, command in READ_COMMANDS:
                scope = "Last at most 1000 lines, only selected recovery/service tags in main/system/crash buffers." if label == "logcat" else None
                record, value = self.shell(label, command, scope=scope)
                if label == "selinux" and record["status"] == "ok" and value != "Enforcing":
                    self.manifest["warnings"].append("SELinux did not report Enforcing; this does not meet the recovery security requirement. No setting was changed.")
            if self.args.include_pstore:
                self.pstore()
        except KeyboardInterrupt:
            self.finish("interrupted")
            return 130
        except SessionLimit as exc:
            self.manifest["errors"].append(str(exc))
            self.finish("partial" if self.verified else "preflight_failed")
            return 3 if self.verified else 2
        except CollectionError as exc:
            self.manifest["errors"].append(str(exc))
            self.finish("aborted" if self.verified else "preflight_failed")
            raise
        partial = bool(self.manifest["errors"]) or any(command["status"] != "ok" for command in self.manifest["commands"])
        self.finish("partial" if partial else "complete")
        return 3 if partial else 0


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    modes = result.add_mutually_exclusive_group()
    modes.add_argument("--collect", action="store_true", help="Opt in to reads from one explicitly selected, authorized device already in recovery.")
    modes.add_argument("--dry-run", action="store_true", help="Print the no-device plan (also the default); no ADB execution or files.")
    result.add_argument("--serial", help="Explicit authorized physical ADB serial; required with --collect.")
    result.add_argument("--expected-device", help="Must be exactly nezha; required with --collect.")
    result.add_argument("--output", type=Path, default=None, help="New subdirectory under this checkout's ignored evidence directory.")
    result.add_argument("--adb", default="adb", help="ADB executable (default: adb); no connect, root or server-management commands are issued.")
    result.add_argument("--include-pstore", action="store_true", help="Opt in to bounded console/dmesg ramoops reads; never read pmsg or clear pstore.")
    result.add_argument("--timeout", type=float, default=15, help="Per-command seconds, greater than zero and at most 60 (default: 15).")
    result.add_argument("--total-timeout", type=float, default=180, help="Whole-session seconds, greater than zero and at most 900 (default: 180); cleanup may add one second.")
    result.add_argument("--max-bytes", type=int, default=1024 * 1024, help="Per-stream byte cap, 4096 through 4194304 (default: 1048576); session cap is 32 MiB.")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if args.collect and (not args.serial or not args.expected_device):
        argument_parser.error("--collect requires --serial and --expected-device nezha.")
    if args.serial and (not re.fullmatch(r"[A-Za-z0-9_.-]{1,256}", args.serial) or
                        args.serial.startswith("emulator-") or "_adb-tls-" in args.serial):
        argument_parser.error("--serial must identify a physical device without shell syntax, emulator or network endpoint syntax.")
    if args.expected_device is not None and args.expected_device != "nezha":
        argument_parser.error("--expected-device must be exactly nezha.")
    if not math.isfinite(args.timeout) or not 0 < args.timeout <= 60:
        argument_parser.error("--timeout must be greater than zero and at most 60 seconds.")
    if not math.isfinite(args.total_timeout) or not 0 < args.total_timeout <= 900:
        argument_parser.error("--total-timeout must be greater than zero and at most 900 seconds.")
    if not 4096 <= args.max_bytes <= 4 * 1024 * 1024:
        argument_parser.error("--max-bytes must be between 4096 and 4194304.")
    if not args.collect:
        print("Plan only: no ADB commands executed and no evidence files written.")
        print("Collection requires --collect --serial <authorized-physical-device> --expected-device nezha.")
        print("Preflight pins the selected ADB transport, verifies Xiaomi/nezha identity and a running recovery, and refuses normal Android.")
        print(f"Read scope: recovery.log tail, dmesg, filtered bounded logcat, SELinux state, mount/partition inventory and {len(PROPERTIES)} selected diagnostic properties.")
        print(f"Pstore console/dmesg ramoops: {'enabled (sensitive, opt in)' if args.include_pstore else 'disabled'}.")
        print(f"Limits: {args.max_bytes} bytes per stream, 32 MiB session output, {args.timeout:g} seconds per command, {args.total_timeout:g} seconds per session.")
        print("No root, reboot, flash, unlock, mount, decrypt, format, writes to the phone, log clearing, arbitrary pulls or network downloads.")
        return 0
    if args.output is None:
        args.output = ROOT / "evidence" / dt.datetime.now(dt.timezone.utc).strftime("recovery-%Y%m%dT%H%M%S.%fZ")
    collector = Collector(args)
    try:
        status = collector.collect()
    except (CollectionError, OSError) as exc:
        message = str(exc) if isinstance(exc, CollectionError) else "Private evidence could not be created or written completely."
        print(f"Collection stopped: {message.replace(args.serial, '<selected-device>')}", file=sys.stderr)
        return 2
    print(f"Collection status: {collector.manifest['status']}. Private evidence: {str(collector.output).replace(args.serial, '<selected-device>')}")
    if status in {2, 3}:
        print("Some reads were refused, unavailable, denied, incomplete or limited; see manifest.json. Do not escalate to root.")
    if collector.manifest["warnings"]:
        print("Security observations need review; see the private manifest warnings. No device settings were changed.")
    return status


if __name__ == "__main__":
    sys.exit(main())
