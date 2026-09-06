#!/usr/bin/env python3
"""Collect private, read-only Android stock evidence; never modify the phone."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import time
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[1]
IDENTITY_PROPERTIES = (
    "ro.product.manufacturer", "ro.product.device", "ro.kernel.qemu",
)
PROPERTIES = (
    "ro.product.brand", "ro.product.model", "ro.product.name", "ro.product.mod_device",
    "ro.product.board", "ro.product.vendor.manufacturer",
    "ro.product.vendor.device", "ro.product.vendor.model",
    "ro.product.vendor.marketname", "ro.product.odm.device",
    "ro.product.cpu.abilist", "ro.hardware", "ro.boot.hardware",
    "ro.board.platform", "ro.soc.manufacturer", "ro.soc.model",
    "ro.build.fingerprint", "ro.vendor.build.fingerprint",
    "ro.odm.build.fingerprint", "ro.build.id", "ro.build.version.incremental",
    "ro.vendor.build.version.incremental", "ro.odm.build.version.incremental",
    "ro.build.version.release", "ro.build.version.sdk",
    "ro.build.version.security_patch", "ro.vendor.build.security_patch",
    "ro.miui.ui.version.name", "ro.mi.os.version.name", "ro.mi.os.version.incremental", "ro.build.ab_update",
    "ro.boot.hwc",
    "ro.boot.slot_suffix", "ro.boot.verifiedbootstate", "ro.boot.flash.locked",
    "ro.boot.vbmeta.device_state", "ro.boot.veritymode",
    "ro.boot.dynamic_partitions", "ro.boot.super_partition",
)
READ_COMMANDS = (
    ("kernel", ("uname", "-a")),
    ("kernel-version", ("cat", "/proc/version")),
    ("page-size", ("getconf", "PAGESIZE")),
    ("selinux", ("getenforce",)),
    ("partition-sizes", ("cat", "/proc/partitions")),
    ("block-by-name", ("ls", "-l", "/dev/block/by-name")),
    ("bootdevice-by-name", ("ls", "-l", "/dev/block/bootdevice/by-name")),
    ("dynamic-partitions", ("lpdump",)),
    ("hardware-model", ("cat", "/sys/firmware/devicetree/base/model")),
    ("hardware-compatible", ("cat", "/sys/firmware/devicetree/base/compatible")),
    ("system-features", ("pm", "list", "features")),
    ("system-packages", ("pm", "list", "packages", "-s", "-f")),
    ("overlays", ("cmd", "overlay", "list")),
    ("services", ("service", "list")),
    ("hal-services", ("lshal",)),
)
METADATA_DIRECTORIES = tuple(
    f"/{partition}/etc/{kind}"
    for partition in ("system", "system_ext", "product", "vendor", "odm")
    for kind in ("vintf", "permissions")
)
DUMPSYS_SERVICES = (
    "media.camera", "display", "sensorservice", "audio", "media.audio_policy",
    "thermalservice", "power", "battery",
)
# Explicit opt-in Package7/successor feature diagnostics. These are observations,
# not functional tests: a registered service or a successful dump is not a pass.
FEATURE_READ_COMMANDS = (
    ("feature-mounts", ("cat", "/proc/mounts")),
    ("feature-mi-ext", ("ls", "-ld", "/mnt/vendor/mi_ext", "/mi_ext")),
    ("feature-displayconfig", ("ls", "-l", "/product/etc/displayconfig")),
    ("feature-auto-brightness", ("cmd", "overlay", "lookup", "android",
                                 "android:bool/config_automatic_brightness_available")),
    ("feature-ims-package", ("dumpsys", "package", "org.codeaurora.ims")),
    ("feature-camera-package", ("dumpsys", "package", "com.android.camera")),
    ("feature-ims", ("dumpsys", "telephony_ims")),
    ("feature-phone", ("dumpsys", "phone")),
    ("feature-location", ("dumpsys", "location")),
    ("feature-nfc", ("dumpsys", "nfc")),
    ("feature-secure-element", ("dumpsys", "secure_element")),
    ("feature-bluetooth", ("dumpsys", "bluetooth_manager")),
    ("feature-wifi", ("dumpsys", "wifi")),
    ("feature-batterystats", ("dumpsys", "batterystats", "--charged")),
    ("feature-vibrator", ("dumpsys", "vibrator_manager")),
)
FEATURE_PROPERTIES = (
    "sys.boot_completed", "ro.miui.ui.version.code",
    "ro.audio.audiozoom", "ro.audio.ozo.channelmask.in",
    "ro.audio.ullunique", "ro.config.WlanAntTunerPolicy", "ro.thermal.iec.enable",
    "persist.sys.power_mode_support", "ro.audio.bt.connect.disable.mute",
    "persist.bluetooth.avrcp.skip.map.update",
)
APK_PACKAGES = ("com.android.camera", "com.miui.gallery")
STOCK_PARTITIONS = {"system", "system_ext", "product", "vendor", "odm"}


class CollectionError(Exception):
    """A safe, user-facing collection/preflight failure."""


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def as_bytes(value: bytes | str | None) -> bytes:
    if value is None:
        return b""
    return value if isinstance(value, bytes) else value.encode("utf-8")


def secure_write(path: Path, content: bytes) -> None:
    """Create private output without following an existing symlink."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(content)


def file_receipt(path: Path, root: Path) -> dict[str, Any]:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "path": path.relative_to(root).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": digest.hexdigest(),
    }


def parse_devices(output: str) -> dict[str, str]:
    """Read serial/state only; never implicitly select an attached device."""
    devices: dict[str, str] = {}
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 2 or fields[0] in {"List", "*", "adb"}:
            continue
        if fields[1] in {"device", "offline", "unauthorized", "no"}:
            if fields[0] in devices:
                raise CollectionError("ADB reported a duplicate device identifier.")
            devices[fields[0]] = fields[1]
    return devices


def system_package_names(output: str) -> set[str]:
    packages = set()
    for line in output.splitlines():
        if line.startswith("package:"):
            _, separator, name = line.rpartition("=")
            if separator and re.fullmatch(r"[A-Za-z0-9_.]+", name):
                packages.add(name)
    return packages


def safe_stock_apk(path: str) -> bool:
    """Reject /data, traversal, shell syntax, and paths outside stock partitions."""
    if not re.fullmatch(r"/[A-Za-z0-9_./+\-]+\.apk", path):
        return False
    components = path.split("/")
    return (
        len(components) >= 3
        and components[1] in STOCK_PARTITIONS
        and all(part not in {"", ".", ".."} for part in components[1:])
    )


class Collector:
    def __init__(self, args: argparse.Namespace):
        self.args = args
        self.output = args.output.expanduser().absolute()
        self.manifest: dict[str, Any] = {
            "schema_version": 1,
            "tool": "collect_stock.py",
            "tool_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "collection_kind": "read-only-stock-evidence",
            "firmware_provenance": "Current installed firmware; OEM authenticity and modification history are not verified.",
            "started_at": utc_now(),
            "status": "collecting",
            "device": {"serial": args.serial, "expected_device": args.expected_device},
            "options": {
                "include_dumpsys": args.include_dumpsys,
                "feature_diagnostics": args.feature_diagnostics,
                "pull_stock_apks": args.pull_stock_apks,
                "apk_packages": args.apk_package if args.pull_stock_apks else [],
                "timeout_seconds": args.timeout,
            },
            "properties": {},
            "commands": [],
            "artifacts": [],
            "errors": [],
            "skipped": [],
            "privacy": "Private evidence: device serials, firmware details, and possibly personal data. Do not publish.",
        }

    def prepare(self) -> None:
        try:
            self.output.mkdir(mode=0o700, parents=True, exist_ok=False)
        except FileExistsError as exc:
            raise CollectionError("Output directory already exists; choose a new directory.") from exc
        (self.output / "commands").mkdir(mode=0o700)
        # Protect evidence even if --output points outside the usual ignored tree.
        secure_write(self.output / ".gitignore", b"*\n!.gitignore\n")
        self.save()

    def save(self) -> None:
        temporary = self.output / "manifest.json.tmp"
        secure_write(temporary, (json.dumps(self.manifest, indent=2) + "\n").encode("utf-8"))
        temporary.replace(self.output / "manifest.json")

    def error(self, message: str) -> None:
        self.manifest["errors"].append(message)
        self.save()

    def run(self, label: str, arguments: Sequence[str], *, selected: bool = True,
            pull: bool = False) -> tuple[dict[str, Any], str]:
        command = [self.args.adb]
        if selected:
            command += ["-s", self.args.serial]
        command += list(arguments)
        started = time.monotonic()
        returncode = None
        stdout = stderr = b""
        try:
            result = subprocess.run(
                command, capture_output=True, shell=False, check=False,
                timeout=max(self.args.timeout, 120) if pull else self.args.timeout,
            )
            returncode = result.returncode
            stdout, stderr = as_bytes(result.stdout), as_bytes(result.stderr)
            status = "ok" if returncode == 0 else "failed"
        except subprocess.TimeoutExpired as exc:
            status = "timeout"
            stdout, stderr = as_bytes(exc.stdout), as_bytes(exc.stderr)
        except OSError as exc:
            status = "unavailable"
            stderr = str(exc).encode("utf-8")
        record: dict[str, Any] = {
            "label": label, "argv": command, "status": status,
            "exit_code": returncode,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        number = len(self.manifest["commands"]) + 1
        for stream, content in (("stdout", stdout), ("stderr", stderr)):
            path = self.output / "commands" / f"{number:03d}-{label}.{stream}.txt"
            secure_write(path, content)
            receipt = file_receipt(path, self.output)
            self.manifest["artifacts"].append(receipt)
            record[stream] = receipt["path"]
        self.manifest["commands"].append(record)
        self.save()
        return record, stdout.decode("utf-8", errors="replace").strip()

    def property(self, name: str) -> tuple[dict[str, Any], str]:
        record, value = self.run(f"property-{name}", ("shell", "getprop", name))
        self.manifest["properties"][name] = {
            "value": value if record["status"] == "ok" else None,
            "status": record["status"],
        }
        self.save()
        return record, value

    def preflight(self) -> None:
        record, _ = self.run("adb-version", ("version",), selected=False)
        if record["status"] != "ok":
            raise CollectionError("ADB is unavailable; install Android platform-tools or use --adb.")
        record, devices = self.run("device-inventory", ("devices", "-l"), selected=False)
        if record["status"] != "ok":
            raise CollectionError("Cannot read the ADB device inventory; see private evidence.")
        state = parse_devices(devices).get(self.args.serial)
        if state is None:
            raise CollectionError("The explicitly selected device is not connected.")
        if state != "device":
            raise CollectionError("The selected device is not online and authorized; no collection was performed.")
        if self.args.serial.startswith("emulator-"):
            raise CollectionError("An emulator cannot supply physical Xiaomi stock evidence.")
        for name in IDENTITY_PROPERTIES:
            record, _ = self.property(name)
            if record["status"] != "ok":
                raise CollectionError("Unable to verify the selected device identity; see private evidence.")
        properties = self.manifest["properties"]
        manufacturer = properties["ro.product.manufacturer"]["value"]
        codename = properties["ro.product.device"]["value"]
        if manufacturer.casefold() != "xiaomi" or codename != self.args.expected_device:
            raise CollectionError("Device identity does not match Xiaomi and --expected-device; collection stopped.")
        if properties["ro.kernel.qemu"]["value"] == "1":
            raise CollectionError("An emulator cannot supply physical Xiaomi stock evidence.")
        self.manifest["device"].update({"manufacturer": manufacturer, "codename": codename})
        self.save()

    def register_pull(self, destination: Path) -> None:
        if not destination.exists() and not destination.is_symlink():
            return
        paths = [destination]
        if destination.is_dir() and not destination.is_symlink():
            for parent, directories, files in os.walk(destination, followlinks=False):
                paths += [Path(parent) / name for name in directories + files]
        for path in paths:
            if path.is_symlink():
                self.error("Unexpected symlink in pulled metadata; it was not read or hashed.")
            elif path.is_dir():
                path.chmod(0o700)
            elif path.is_file():
                path.chmod(0o600)
                self.manifest["artifacts"].append(file_receipt(path, self.output))
            else:
                self.error("Unexpected non-regular file in pulled evidence; it was not read or hashed.")
        self.save()

    def pull(self, label: str, source: str, destination: Path) -> None:
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        record, _ = self.run(label, ("pull", source, str(destination)), pull=True)
        # Retain and hash partial pull output as well; never imply it was complete.
        self.register_pull(destination)
        if record["status"] == "ok" and not destination.exists():
            self.error(f"{label}: ADB reported success but produced no output.")

    def pull_apks(self, packages: set[str]) -> None:
        for package in self.args.apk_package:
            if package not in packages:
                self.manifest["skipped"].append({
                    "package": package, "reason": "Not present in the system-package inventory; not pulled.",
                })
                continue
            record, output = self.run(f"apk-path-{package}", ("shell", "pm", "path", package))
            if record["status"] != "ok":
                continue
            lines = output.splitlines()
            paths = [line[len("package:"):] for line in lines if line.startswith("package:")]
            if not paths or len(paths) != len(lines) or any(not safe_stock_apk(path) for path in paths):
                self.error(f"{package}: APK paths are missing or outside the stock partition allowlist; no APKs pulled.")
                continue
            for index, path in enumerate(dict.fromkeys(paths), start=1):
                destination = self.output / "apks" / package / f"{index:03d}-{PurePosixPath(path).name}"
                self.pull(f"apk-{package}-{index:03d}", path, destination)
        self.save()

    def collect(self) -> int:
        self.prepare()
        try:
            self.preflight()
        except CollectionError as exc:
            self.error(str(exc))
            self.finish("preflight_failed")
            raise
        except KeyboardInterrupt:
            self.finish("interrupted")
            return 130
        try:
            for name in PROPERTIES:
                self.property(name)
            packages: set[str] = set()
            for label, command in READ_COMMANDS:
                record, output = self.run(label, ("shell", *command))
                if label == "system-packages" and record["status"] == "ok":
                    packages = system_package_names(output)
            for source in METADATA_DIRECTORIES:
                label = source.strip("/").replace("/", "-")
                self.pull(label, source, self.output / "metadata" / label)
            if self.args.include_dumpsys or self.args.feature_diagnostics:
                for service in DUMPSYS_SERVICES:
                    self.run(f"dumpsys-{service}", ("shell", "dumpsys", service))
            if self.args.feature_diagnostics:
                for name in FEATURE_PROPERTIES:
                    self.property(name)
                for label, command in FEATURE_READ_COMMANDS:
                    self.run(label, ("shell", *command))
            if self.args.pull_stock_apks:
                self.pull_apks(packages)
        except KeyboardInterrupt:
            self.finish("interrupted")
            return 130
        except OSError:
            # Preserve the truthful in-progress manifest if the disk itself fails.
            raise CollectionError("Local evidence could not be written completely; inspect the output directory.")
        partial = bool(self.manifest["errors"] or self.manifest["skipped"]) or any(
            command["status"] != "ok" for command in self.manifest["commands"]
        )
        self.finish("partial" if partial else "complete")
        return 3 if partial else 0

    def finish(self, status: str) -> None:
        self.manifest["status"] = status
        self.manifest["completed_at"] = utc_now()
        self.save()


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--serial", required=True, help="Explicit authorized physical ADB device; never auto-selected.")
    result.add_argument("--expected-device", required=True, help="Exact stock ro.product.device codename independently verified for this phone.")
    default_output = ROOT / "evidence" / dt.datetime.now(dt.timezone.utc).strftime("stock-%Y%m%dT%H%M%S.%fZ")
    result.add_argument("--output", type=Path, default=default_output, help="New private output directory (default: evidence/stock-UTC).")
    result.add_argument("--adb", default="adb", help="ADB executable path (default: adb).")
    result.add_argument("--timeout", type=float, default=30, help="Per-command seconds; pulls get at least 120 seconds (default: 30).")
    result.add_argument("--dry-run", action="store_true", help="Describe collection without running ADB or writing files.")
    result.add_argument("--include-dumpsys", action="store_true", help="Opt in to potentially sensitive camera/audio/sensor/display reports.")
    result.add_argument("--feature-diagnostics", action="store_true", help="Opt in to hardware dumps plus sensitive radio/location/network, mi_ext and brightness observations; never runs functional tests.")
    result.add_argument("--pull-stock-apks", action="store_true", help="Opt in to private copies of allowlisted stock system APKs.")
    result.add_argument("--apk-package", action="append", choices=APK_PACKAGES, help="Allowlisted package to pull; repeatable (default with --pull-stock-apks: com.android.camera).")
    return result


def main(argv: Sequence[str] | None = None) -> int:
    argument_parser = parser()
    args = argument_parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9_.:\-]{1,256}", args.serial):
        argument_parser.error("--serial contains unsupported characters.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.\-]{0,127}", args.expected_device):
        argument_parser.error("--expected-device must be a plain Android device codename.")
    if not 0 < args.timeout <= 600:
        argument_parser.error("--timeout must be greater than zero and at most 600 seconds.")
    if args.apk_package and not args.pull_stock_apks:
        argument_parser.error("--apk-package requires --pull-stock-apks.")
    args.apk_package = list(dict.fromkeys(args.apk_package or ["com.android.camera"]))
    if args.dry_run:
        print("Dry run: no ADB commands executed and no evidence files written.")
        print("Preflight: one explicitly selected authorized physical Xiaomi device; exact expected codename required.")
        print(f"Plan: {len(IDENTITY_PROPERTIES) + len(PROPERTIES)} allowlisted properties, {len(READ_COMMANDS)} hardware/package/HAL reads, {len(METADATA_DIRECTORIES)} VINTF/permission directory pulls.")
        print(f"Detailed dumpsys reports: {'enabled (sensitive)' if args.include_dumpsys or args.feature_diagnostics else 'disabled'}.")
        print(f"Feature diagnostics: {'enabled (sensitive, observations only)' if args.feature_diagnostics else 'disabled'}.")
        if args.feature_diagnostics:
            for label, command in FEATURE_READ_COMMANDS:
                print(f"  {label}: shell {' '.join(command)}")
            print("  Additional properties: " + ", ".join(FEATURE_PROPERTIES))
        print(f"Stock APK pulls: {', '.join(args.apk_package) if args.pull_stock_apks else 'disabled'}.")
        print("No root, reboot, unlock, flash, install, settings changes, logcat, bugreport, or user-data pulls.")
        return 0
    collector = Collector(args)
    try:
        status = collector.collect()
    except (CollectionError, OSError) as exc:
        message = str(exc) if isinstance(exc, CollectionError) else "Cannot create or write private evidence output."
        print(f"Collection stopped: {message.replace(args.serial, '<selected-device>')}", file=sys.stderr)
        return 2
    print(f"Collection status: {collector.manifest['status']}. Private evidence: {str(collector.output).replace(args.serial, '<selected-device>')}")
    if status == 3:
        print("Some reads were unavailable, failed, or timed out; see manifest.json. Do not escalate to root.")
    return status


if __name__ == "__main__":
    sys.exit(main())
