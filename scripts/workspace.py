#!/usr/bin/env python3
"""Fetch pinned references and prepare a supported Evolution X source host."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/sources.json"
GIB = 1024 ** 3


def checked_path(root, relative):
    """Keep managed checkouts below the workspace, including through symlinks."""
    part = PurePosixPath(relative)
    if part.is_absolute() or ".." in part.parts or not part.parts:
        raise ValueError(f"Unsafe managed path: {relative!r}")
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()) or target == root.resolve():
        raise ValueError(f"Managed path escapes workspace: {relative!r}")
    return target


def load_config(path=CONFIG):
    config = json.loads(path.read_text())
    if config.get("schema_version") != 1:
        raise ValueError("Unsupported source configuration schema")
    names, paths = set(), set()
    for reference in config["references"]:
        name, relative = reference["name"], reference["path"]
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", name) or name in names:
            raise ValueError("Invalid or duplicate reference name")
        names.add(name)
        target = checked_path(ROOT, relative)
        if PurePosixPath(relative).parts[0] not in {"upstream", ".tools"}:
            raise ValueError("References belong in upstream/ or .tools/")
        if any(target == old or target.is_relative_to(old) or old.is_relative_to(target)
               for old in paths):
            raise ValueError("Reference paths overlap")
        paths.add(target)
        if not re.fullmatch(r"[0-9a-f]{40}", reference["commit"]):
            raise ValueError("Reference revisions must be full commit hashes")
        url = urlparse(reference["url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError("Reference URLs must be public HTTPS URLs")
        if any(character.isspace() for character in reference["url"]):
            raise ValueError("Reference URLs must not contain whitespace")
    if config["platform"]["reference"] not in names or "repo-tool" not in names:
        raise ValueError("Missing platform manifest or repo tool reference")
    checked_path(ROOT, config["platform"]["source_dir"])
    return config


def run(args, cwd=None, capture=False, timeout=600):
    environment = os.environ.copy()
    environment.update(GIT_TERMINAL_PROMPT="0", GIT_LFS_SKIP_SMUDGE="1")
    if not capture:
        print("+ " + shlex.join(str(arg) for arg in args), flush=True)
    return subprocess.run(
        [str(arg) for arg in args], cwd=cwd, env=environment,
        text=True, capture_output=capture, check=True, timeout=timeout,
    )


def git_value(target, *args):
    return run(["git", "-C", target, *args], capture=True).stdout.strip()


def verify_reference(reference, root=ROOT):
    target = checked_path(root, reference["path"])
    if not (target / ".git").is_dir():
        raise ValueError(f"Missing reference: {reference['name']}; run fetch")
    if Path(git_value(target, "rev-parse", "--show-toplevel")).resolve() != target:
        raise ValueError(f"Not a standalone checkout: {target}")
    if git_value(target, "remote", "get-url", "origin") != reference["url"]:
        raise ValueError(f"Unexpected origin for {reference['name']}")
    if git_value(target, "rev-parse", "HEAD") != reference["commit"]:
        raise ValueError(f"Revision mismatch for {reference['name']}")
    if git_value(target, "status", "--porcelain", "--untracked-files=normal"):
        raise ValueError(f"Local changes in {reference['name']}; preserve them first")
    return {"name": reference["name"], "commit": reference["commit"],
            "path": str(target), "url": reference["url"]}


def fetch_reference(reference, root=ROOT):
    target = checked_path(root, reference["path"])
    if (target / ".git").exists():
        # Never reset or silently update an existing checkout.
        return verify_reference(reference, root)
    if target.exists() and any(target.iterdir()):
        raise ValueError(f"Refusing nonempty reference directory: {target}")
    target.mkdir(parents=True, exist_ok=True)
    run(["git", "init", target])
    run(["git", "-C", target, "remote", "add", "origin", reference["url"]])
    run(["git", "-C", target, "fetch", "--depth=1", "--no-tags", "origin",
         reference["commit"]])
    run(["git", "-C", target, "checkout", "--detach", reference["commit"]])
    return verify_reference(reference, root)


def existing_parent(path):
    while not path.exists():
        if path == path.parent:
            raise ValueError("No existing parent for source directory")
        path = path.parent
    if not path.is_dir():
        raise ValueError(f"Expected directory: {path}")
    return path


def case_sensitive(path):
    with tempfile.TemporaryDirectory(prefix=".evo-case-probe-", dir=path) as directory:
        probe = Path(directory) / "Probe"
        probe.write_text("probe")
        return not probe.with_name("probe").exists()


def memory_gib():
    if platform.system() == "Darwin":
        return int(run(["sysctl", "-n", "hw.memsize"], capture=True).stdout) / GIB
    try:
        return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / GIB
    except (AttributeError, OSError, ValueError):
        return None


def host_report(source_dir, requirements):
    parent = existing_parent(source_dir.resolve())
    ram = memory_gib()
    tools = {name: shutil.which(name) for name in ("git", "git-lfs", "python3", "make", "adb", "fastboot")}
    checks = {
        "linux": platform.system() == "Linux",
        "x86_64": platform.machine().lower() in {"x86_64", "amd64"},
        "case_sensitive": case_sensitive(parent),
        "free_disk": shutil.disk_usage(parent).free >= requirements["min_free_disk_gib"] * GIB,
        "ram": ram is not None and ram >= requirements["min_ram_gib"],
        "source_tools": all(tools[name] for name in ("git", "git-lfs", "python3", "make")),
    }
    return {
        "os": platform.system(), "architecture": platform.machine(),
        "source_dir": str(source_dir.resolve()), "filesystem_checked_at": str(parent),
        "ram_gib": None if ram is None else round(ram, 1),
        "free_disk_gib": round(shutil.disk_usage(parent).free / GIB, 1),
        "tools": tools, "checks": checks, "supported_build_host": all(checks.values()),
        "note": "A host preflight is not proof of a complete toolchain or a buildable device tree.",
    }


def require_host(source_dir, config):
    report = host_report(source_dir, config["host_requirements"])
    failures = [key for key, passed in report["checks"].items() if not passed]
    if failures:
        raise ValueError("Source operation blocked by host preflight: " + ", ".join(failures)
                         + ". Use Linux x86-64, a case-sensitive filesystem, 64 GiB RAM"
                         + " and at least 400 GiB free. Use fetch for Mac reference checkouts.")


def reference_named(config, name):
    return next(reference for reference in config["references"] if reference["name"] == name)


def repo_command(config):
    tool = reference_named(config, "repo-tool")
    verify_reference(tool)
    return [sys.executable, str(checked_path(ROOT, tool["path"]) / "repo")]


def init_command(config):
    manifest = reference_named(config, config["platform"]["reference"])
    tool = reference_named(config, "repo-tool")
    # The branch name is metadata; initialize to the exact manifest commit.
    return [sys.executable, str(checked_path(ROOT, tool["path"]) / "repo"), "init",
            "--manifest-url", manifest["url"], "--manifest-branch", manifest["commit"],
            "--git-lfs", "--no-clone-bundle", "--current-branch",
            "--repo-url", tool["url"], "--repo-rev", tool["commit"]]


def sync_command(config, jobs):
    if not 1 <= jobs <= 64:
        raise ValueError("Sync jobs must be between 1 and 64")
    tool = reference_named(config, "repo-tool")
    # Do not use --force-sync: preserve local source work on reruns.
    return [sys.executable, str(checked_path(ROOT, tool["path"]) / "repo"),
            "sync", "--current-branch", f"--jobs={jobs}", "--no-clone-bundle",
            "--no-tags", "--fail-fast"]


def verify_source_manifest(config, source_dir):
    manifest = reference_named(config, config["platform"]["reference"])
    checkout = source_dir / ".repo/manifests"
    if not checkout.is_dir():
        raise ValueError("No initialized platform manifest; run init first")
    if git_value(checkout, "remote", "get-url", "origin") != manifest["url"]:
        raise ValueError("Source checkout uses a different manifest origin")
    if git_value(checkout, "rev-parse", "HEAD") != manifest["commit"]:
        raise ValueError("Source checkout uses a different manifest revision")
    if git_value(checkout, "status", "--porcelain"):
        raise ValueError("Source manifest has local changes; preserve and review them first")


def initialize(config, source_dir, dry_run=False):
    command = init_command(config)
    if dry_run:
        print(f"In {source_dir}:\n" + shlex.join(command))
        print("Execution requires a supported host; this preview does not initialize or sync.")
        return
    require_host(source_dir, config)
    repo_command(config)
    if (source_dir / ".repo").exists():
        verify_source_manifest(config, source_dir)
        print("Platform manifest already initialized at the configured revision.")
        return
    if source_dir.exists() and any(source_dir.iterdir()):
        raise ValueError("Refusing to initialize a nonempty source directory")
    source_dir.mkdir(parents=True, exist_ok=True)
    run(command, cwd=source_dir)
    verify_source_manifest(config, source_dir)


def synchronize(config, source_dir, jobs, dry_run=False):
    command = sync_command(config, jobs)
    if dry_run:
        print(f"In {source_dir}:\n" + shlex.join(command))
        print("This previews a full platform download, not a complete Xiaomi device build.")
        return
    require_host(source_dir, config)
    repo = repo_command(config)
    verify_source_manifest(config, source_dir)
    # LFS must be fetched for build sources, unlike lightweight references.
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment.pop("GIT_LFS_SKIP_SMUDGE", None)
    print("+ " + shlex.join(command), flush=True)
    subprocess.run(command, cwd=source_dir, env=environment, check=True)
    output = ROOT / "reports" / ("resolved-manifest-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".xml")
    output.parent.mkdir(parents=True, exist_ok=True)
    run(repo + ["manifest", "--revision-as-HEAD", "--output-file", output], cwd=source_dir)
    print(f"Saved fully resolved project revisions: {output}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    doctor = commands.add_parser("doctor", help="Report supported Android build-host prerequisites")
    doctor.add_argument("--source-dir", type=Path)
    doctor.add_argument("--require-build-host", action="store_true")
    for name in ("fetch", "verify"):
        command = commands.add_parser(name, help=f"{name.capitalize()} pinned reference checkouts")
        command.add_argument("names", nargs="*")
    for name in ("init", "sync"):
        command = commands.add_parser(name, help=f"{name.capitalize()} the full platform on a supported host")
        command.add_argument("--source-dir", type=Path)
        command.add_argument("--dry-run", action="store_true")
        if name == "sync":
            command.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        config = load_config()
        source_dir = getattr(args, "source_dir", None) or checked_path(ROOT, config["platform"]["source_dir"])
        source_dir = source_dir.expanduser().resolve()
        if args.action == "doctor":
            report = host_report(source_dir, config["host_requirements"])
            print(json.dumps(report, indent=2))
            return 2 if args.require_build_host and not report["supported_build_host"] else 0
        if args.action in {"fetch", "verify"}:
            references = config["references"]
            unknown = set(args.names) - {reference["name"] for reference in references}
            if unknown:
                raise ValueError("Unknown references: " + ", ".join(sorted(unknown)))
            selected = [reference for reference in references if not args.names or reference["name"] in args.names]
            operation = fetch_reference if args.action == "fetch" else verify_reference
            records = [operation(reference) for reference in selected]
            print(json.dumps({"references": records, "lfs": "Reference fetches skip LFS assets; not a build checkout."}, indent=2))
        elif args.action == "init":
            initialize(config, source_dir, args.dry_run)
        elif args.action == "sync":
            synchronize(config, source_dir, args.jobs, args.dry_run)
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, StopIteration) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
