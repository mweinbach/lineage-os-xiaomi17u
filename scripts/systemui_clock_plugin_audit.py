#!/usr/bin/env python3
"""Audit SystemUI clock plugin APKs against their plugin hosts without a phone.

A clock plugin declares the ``PLUGIN_CLOCK_PROVIDER`` service action and
annotates its provider class with ``@Requires(target = ClockProviderPlugin)``.
Each host (SystemUI, the Google wallpaper picker) checks that annotation against
its own ``ClockProviderPlugin`` class object. The plugin class loader delegates
``com.android.systemui.plugin*`` names to the host, so a plugin built against a
different interface package resolves its own bundled copy instead. The host then
reports ``Missing required dependency ClockProviderPlugin``; the wallpaper
picker prebuilt lets that exception escape and crashes.

This tool reads only DEX type descriptors and manifest strings. It does not run
Android code, unpack resources or prove that a compatible plugin renders.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import sys
import zipfile
from pathlib import Path, PurePosixPath

CONTRACT = Path(__file__).resolve().parents[1] / "config/systemui-clocks-flex-removal.json"
CONTRACT_SHA256 = "96f105ca82370fccc6c7ceafd7c489d405eee9d776c62be286de12b0610bac51"

ACTION = "com.android.systemui.action.PLUGIN_CLOCK_PROVIDER"
INTERFACE_PATTERN = re.compile(rb"L[A-Za-z0-9_/]*/ClockProviderPlugin;")
PROVIDES_INTERFACE = b"Lcom/android/systemui/plugins/annotations/ProvidesInterface;"
REQUIRES = b"Lcom/android/systemui/plugins/annotations/Requires;"
VERSION_INFO = b"Lcom/android/systemui/shared/plugins/VersionInfo;"
DEX_NAME = re.compile(r"classes\d*\.dex")
ARCHIVE_APK_DIRS = ("SYSTEM/app/", "SYSTEM/priv-app/", "SYSTEM_EXT/app/", "SYSTEM_EXT/priv-app/",
                    "PRODUCT/app/", "PRODUCT/priv-app/")


class AuditError(ValueError):
    """Raised for malformed inputs; the audit never guesses."""


def _require(condition, message):
    if not condition:
        raise AuditError(message)


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def read_apk(raw):
    """Return the concatenated DEX bodies and manifest bytes of one APK."""
    _require(type(raw) is bytes, "APK bytes required")
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw))
    except zipfile.BadZipFile as exc:
        raise AuditError("not a ZIP archive: " + str(exc)) from None
    names = archive.namelist()
    _require("AndroidManifest.xml" in names, "APK has no AndroidManifest.xml")
    dex = b"".join(archive.read(name) for name in sorted(names) if DEX_NAME.fullmatch(name))
    return dex, archive.read("AndroidManifest.xml")


def declares_action(manifest):
    """The binary manifest string pool stores the action as UTF-8 or UTF-16LE."""
    return ACTION.encode() in manifest or ACTION.encode("utf-16-le") in manifest


def classify(name, raw):
    dex, manifest = read_apk(raw)
    interfaces = sorted({match.decode() for match in INTERFACE_PATTERN.findall(dex)})
    host = VERSION_INFO in dex
    plugin = declares_action(manifest) and not host
    return {
        "name": name,
        "sha256": sha256(raw),
        "size_bytes": len(raw),
        "role": "host" if host else "plugin" if plugin else "other",
        "declares_clock_provider_action": declares_action(manifest),
        "clock_provider_interfaces": interfaces,
        "requires_annotation_referenced": REQUIRES in dex,
        "bundles_plugin_interface_copy": PROVIDES_INTERFACE in dex and not host,
    }


def check(rows):
    """Judge plugin/host interface identity; returns a report with failures."""
    hosts = [row for row in rows if row["role"] == "host"]
    plugins = [row for row in rows if row["role"] == "plugin"]
    failures = []
    if not hosts:
        failures.append({"kind": "no_host", "detail": "no APK carries the shared plugin version checker"})
    host_sets = {tuple(row["clock_provider_interfaces"]) for row in hosts}
    if len(host_sets) > 1:
        failures.append({"kind": "host_interface_disagreement",
                         "detail": {row["name"]: row["clock_provider_interfaces"] for row in hosts}})
    expected = sorted(host_sets.pop()) if len(host_sets) == 1 else []
    for row in plugins:
        if not row["clock_provider_interfaces"]:
            failures.append({"kind": "plugin_without_interface", "name": row["name"]})
            continue
        foreign = sorted(set(row["clock_provider_interfaces"]) - set(expected))
        if foreign and hosts:
            failures.append({"kind": "plugin_interface_not_provided_by_host", "name": row["name"],
                             "foreign_interfaces": foreign, "host_interfaces": expected})
        if row["bundles_plugin_interface_copy"]:
            failures.append({"kind": "plugin_bundles_interface_copy", "name": row["name"]})
    return {
        "schema_version": 1,
        "passed": not failures,
        "host_count": len(hosts),
        "plugin_count": len(plugins),
        "host_interfaces": expected,
        "failures": failures,
        "rows": rows,
        "scope": ("DEX descriptor and manifest string identity only; no Android execution, "
                  "resource decoding, signature check or rendering result."),
    }


def archive_members(path):
    """Yield (member name, bytes) for APKs under the packaged app directories."""
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            if info.filename.endswith(".apk") and info.filename.startswith(ARCHIVE_APK_DIRS):
                yield info.filename, archive.read(info)


def collect(apks, target_files):
    rows = []
    for apk in apks:
        rows.append(classify(str(apk), Path(apk).read_bytes()))
    members = []
    if target_files is not None:
        for member, raw in archive_members(target_files):
            members.append(member)
            row = classify(member, raw)
            if row["role"] != "other" or row["clock_provider_interfaces"]:
                rows.append(row)
    return rows, members


def module_names(members):
    """Installed module directory names, e.g. SYSTEM_EXT/priv-app/<name>/<name>.apk."""
    return sorted({PurePosixPath(member).parent.name for member in members})


def contract_report(contract_path=CONTRACT, expected_sha256=CONTRACT_SHA256):
    """Replay the pinned full-file patch and recompute both source identities."""
    raw = Path(contract_path).read_bytes()
    _require(sha256(raw) == expected_sha256, "contract hash differs from the pinned value")
    contract = json.loads(raw)
    patch_path = Path(contract_path).resolve().parents[1] / contract["patch"]
    patch = patch_path.read_bytes()
    _require(sha256(patch) == contract["patch_sha256"], "patch hash differs from the contract")
    (relative, entry), = contract["files"].items()
    header = re.match(rb"diff --git a/(\S+) b/\1\nindex ([0-9a-f]{40})\.\.([0-9a-f]{40}) 100644\n"
                      rb"--- a/\1\n\+\+\+ b/\1\n@@ -1,(\d+) \+1,(\d+) @@\n", patch)
    _require(header is not None and header.group(1).decode() == relative, "unexpected patch header")
    body = patch[header.end():].splitlines(keepends=True)
    _require(all(line[:1] in (b" ", b"+", b"-") and line.endswith(b"\n") for line in body),
             "complete LF source lines required")
    before = b"".join(line[1:] for line in body if line[:1] in (b" ", b"-"))
    after = b"".join(line[1:] for line in body if line[:1] in (b" ", b"+"))
    _require((len(before.splitlines()), len(after.splitlines())) ==
             (int(header.group(4)), int(header.group(5))), "hunk line counts differ")
    for data, digest, size, blob in ((before, entry["before_sha256"], entry["before_bytes"], header.group(2)),
                                     (after, entry["after_sha256"], entry["after_bytes"], header.group(3))):
        _require(sha256(data) == digest and len(data) == size, "source identity differs from the contract")
        _require(hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest() == blob.decode(),
                 "git blob identity differs from the patch index line")
    removed = [line[1:].decode() for line in body if line[:1] == b"-"]
    added = [line[1:].decode() for line in body if line[:1] == b"+"]
    return {"contract_id": contract["contract_id"], "project": contract["project"], "file": relative,
            "removed_lines": removed, "added_lines": added,
            "before": {"sha256": sha256(before), "size_bytes": len(before)},
            "after": {"sha256": sha256(after), "size_bytes": len(after)},
            "before_text": before.decode(), "after_text": after.decode()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("inspect", "check"):
        p = sub.add_parser(name)
        p.add_argument("--apk", action="append", default=[], help="APK file to classify")
        p.add_argument("--target-files", help="target-files ZIP whose packaged APKs are scanned")
        p.add_argument("--expect-absent", action="append", default=[], help="module directory that must not be packaged")
        p.add_argument("--expect-present", action="append", default=[], help="module directory that must be packaged")
        p.add_argument("--output", help="write the JSON report to this new file")
    sub.add_parser("contract")
    args = parser.parse_args(argv)
    if args.command == "contract":
        report = contract_report()
        report = {k: v for k, v in report.items() if not k.endswith("_text")}
        print(json.dumps(report, indent=2))
        return 0
    _require(args.apk or args.target_files, "give at least one --apk or a --target-files archive")
    rows, members = collect(args.apk, args.target_files)
    report = check(rows) if args.command == "check" else {"schema_version": 1, "rows": rows}
    modules = module_names(members)
    if args.target_files:
        report["packaged_modules_scanned"] = len(members)
        for name in args.expect_absent:
            if name in modules:
                report.setdefault("failures", []).append({"kind": "unexpected_module_present", "name": name})
        for name in args.expect_present:
            if name not in modules:
                report.setdefault("failures", []).append({"kind": "expected_module_missing", "name": name})
        report["expect_absent"] = args.expect_absent
        report["expect_present"] = args.expect_present
        report["passed"] = not report.get("failures")
    text = json.dumps(report, indent=2) + "\n"
    if args.output:
        with open(args.output, "x") as handle:
            handle.write(text)
    sys.stdout.write(text)
    return 0 if report.get("passed", True) else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        print("error: " + str(exc), file=sys.stderr)
        raise SystemExit(2)
