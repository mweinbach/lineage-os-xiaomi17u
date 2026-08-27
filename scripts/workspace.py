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
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlparse
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/sources.json"
GIB = 1024 ** 3
HOST_MODES = ("native", "apple-rosetta")
APPLE_BUILDER_MARKER = Path("/opt/evolution/apple-container-builder")
APPLE_BUILDER_MARKER_CONTENT = b"evolution-apple-container-builder-v1\n"
ROSETTA_PROBE = Path("/opt/evolution/bin/rosetta-probe")
ROSETTA_PROBE_OUTPUT = "evolution-x86_64-probe-ok"
AMD64_RUNTIME = {
    "loader": Path("/lib64/ld-linux-x86-64.so.2"),
    "libc": Path("/lib/x86_64-linux-gnu/libc.so.6"),
    "libstdc++": Path("/usr/lib/x86_64-linux-gnu/libstdc++.so.6"),
    "zlib": Path("/lib/x86_64-linux-gnu/libz.so.1"),
}


def checked_path(root, relative):
    """Keep managed checkouts below the workspace, including through symlinks."""
    part = PurePosixPath(relative)
    if part.is_absolute() or ".." in part.parts or not part.parts:
        raise ValueError(f"Unsafe managed path: {relative!r}")
    target = root.resolve()
    for component in part.parts:
        target = target / component
        if target.is_symlink():
            raise ValueError(f"Symlink in managed path: {relative!r}")
    target = target.resolve()
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
        stdin=subprocess.DEVNULL, shell=False,
    )


def git_value(target, *args):
    return run(["git", "-C", target, *args], capture=True).stdout.strip()


def verify_reference(reference, root=ROOT):
    target = checked_path(root, reference["path"])
    if not (target / ".git").is_dir() or (target / ".git").is_symlink():
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
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError(f"Refusing nonempty reference directory: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    # Publish only a verified checkout. A failed fetch must not leave an
    # incomplete .git at the final path that poisons the next safe retry.
    with tempfile.TemporaryDirectory(prefix=f".{reference['name']}-fetch-", dir=target.parent) as directory:
        staging = Path(directory)
        run(["git", "init", staging])
        run(["git", "-C", staging, "remote", "add", "origin", reference["url"]])
        run(["git", "-C", staging, "fetch", "--depth=1", "--no-tags", "origin",
             reference["commit"]])
        run(["git", "-C", staging, "checkout", "--detach", reference["commit"]])
        staged_reference = dict(reference, path=staging.relative_to(root.resolve()).as_posix())
        verify_reference(staged_reference, root)
        checked_path(root, reference["path"])
        if target.exists():
            if not target.is_dir() or any(target.iterdir()):
                raise ValueError(f"Reference directory changed during fetch; preserved: {target}")
            target.rmdir()
        staging.rename(target)
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


def trusted_root_file(path, allow_symlinks=False, executable=False):
    """Verify image-owned files and parent directories before executing a probe."""
    path = Path(path)
    if not path.is_absolute():
        raise ValueError("Builder paths must be absolute")
    # Runtime libraries use standard root-owned multiarch symlinks. The marker
    # and probe themselves must not be links to a writable workspace mount.
    resolved = path.resolve(strict=True)
    for candidate in dict.fromkeys((path, *path.parents, resolved, *resolved.parents)):
        metadata = candidate.lstat()
        if stat.S_ISLNK(metadata.st_mode):
            if not allow_symlinks or metadata.st_uid != 0:
                raise ValueError(f"Untrusted symlink in builder path: {path}")
        elif metadata.st_uid != 0 or metadata.st_mode & 0o022:
            raise ValueError(f"Builder file or parent is not protected and root-owned: {path}")
    metadata = resolved.stat()
    if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o6000:
        raise ValueError(f"Builder path is not a regular unprivileged file: {path}")
    if executable and (not metadata.st_mode & 0o111 or not os.access(resolved, os.X_OK)):
        raise ValueError(f"Builder probe is not executable: {path}")
    return resolved


def require_x86_64_elf(path):
    """Inspect ELF identity before attempting any execution; scripts are refused."""
    with Path(path).open("rb") as stream:
        header = stream.read(64)
    if (len(header) < 64 or header[:7] != b"\x7fELF\x02\x01\x01"
            or int.from_bytes(header[16:18], "little") not in {2, 3}
            or int.from_bytes(header[18:20], "little") != 62
            or int.from_bytes(header[20:24], "little") != 1):
        raise ValueError(f"Not an x86-64 ELF64 executable/shared object: {path}")


def rosetta_report(system, machine):
    report = {
        "marker_path": str(APPLE_BUILDER_MARKER), "marker_trusted": False,
        "probe_path": str(ROSETTA_PROBE), "probe_elf_verified": False,
        "runtime": {name: False for name in AMD64_RUNTIME},
        "probe_attempted": False, "probe_executed": False, "probe_exit_code": None,
        "probe_success": False, "errors": [],
    }
    if system != "Linux" or machine.lower() not in {"aarch64", "arm64"}:
        report["errors"].append("apple-rosetta requires the ARM64 Linux builder container, not the macOS host.")
        return report
    try:
        marker = trusted_root_file(APPLE_BUILDER_MARKER)
        if marker.stat().st_size != len(APPLE_BUILDER_MARKER_CONTENT) or marker.read_bytes() != APPLE_BUILDER_MARKER_CONTENT:
            raise ValueError("Builder marker does not match the reviewed Apple Container image")
        report["marker_trusted"] = True
        probe = trusted_root_file(ROSETTA_PROBE, executable=True)
        require_x86_64_elf(probe)
        report["probe_elf_verified"] = True
        for name, path in AMD64_RUNTIME.items():
            library = trusted_root_file(path, allow_symlinks=True)
            require_x86_64_elf(library)
            report["runtime"][name] = True
        # Invoke the fixed ELF directly, with no host shell, compiler, downloaded
        # code, or LD_* environment injection. Rosetta/binfmt must execute it.
        report["probe_attempted"] = True
        result = subprocess.run(
            [str(probe)], stdin=subprocess.DEVNULL, capture_output=True,
            text=True, shell=False, check=False, timeout=15,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin", "LANG": "C", "LC_ALL": "C"},
        )
        report["probe_executed"] = True
        report["probe_exit_code"] = result.returncode
        report["probe_stdout"] = result.stdout[:256]
        report["probe_stderr"] = result.stderr[:1024]
        report["probe_success"] = result.returncode == 0 and result.stdout in {
            ROSETTA_PROBE_OUTPUT, ROSETTA_PROBE_OUTPUT + "\n",
        }
        if not report["probe_success"]:
            report["errors"].append("The x86-64 probe did not return the exact success token with exit code zero.")
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        report["errors"].append(f"Rosetta preflight failed: {error}")
    return report


def host_report(source_dir, requirements, host_mode="native"):
    if host_mode not in HOST_MODES:
        raise ValueError(f"Unknown host mode: {host_mode}")
    parent = existing_parent(source_dir.resolve())
    output_dir = Path(os.environ.get("OUT_DIR") or "out").expanduser()
    if not output_dir.is_absolute():
        output_dir = source_dir / output_dir
    output_dir = output_dir.resolve()
    output_parent = existing_parent(output_dir)
    shared_filesystem = parent.stat().st_dev == output_parent.stat().st_dev
    source_disk = shutil.disk_usage(parent)
    output_disk = source_disk if shared_filesystem else shutil.disk_usage(output_parent)
    ram = memory_gib()
    system, machine = platform.system(), platform.machine()
    tools = {name: shutil.which(name) for name in ("git", "git-lfs", "gpg", "python3", "make", "adb", "fastboot")}
    checks = {
        "linux": system == "Linux",
        "case_sensitive": case_sensitive(parent),
        "output_case_sensitive": case_sensitive(output_parent) if output_parent != parent else None,
        "free_disk": source_disk.free >= requirements["min_free_disk_gib"] * GIB,
        "ram": ram is not None and ram >= requirements["min_ram_gib"],
        "source_tools": all(tools[name] for name in ("git", "git-lfs", "gpg", "python3", "make")),
    }
    if checks["output_case_sensitive"] is None:
        checks["output_case_sensitive"] = checks["case_sensitive"]
    common_passed = all(checks.values())
    native_architecture = machine.lower() in {"x86_64", "amd64"}
    translation = None
    if host_mode == "native":
        checks["x86_64"] = native_architecture
    else:
        translation = rosetta_report(system, machine)
        checks.update({
            "arm64": machine.lower() in {"aarch64", "arm64"},
            "trusted_apple_builder": translation["marker_trusted"],
            "x86_64_runtime": all(translation["runtime"].values()),
            "x86_64_execution": translation["probe_elf_verified"] and translation["probe_success"],
        })
    selected_passed = all(checks.values())
    status = ("native-ready" if host_mode == "native" else "experimental-rosetta-ready") if selected_passed else "blocked"
    return {
        "os": system, "architecture": machine,
        "host_mode": host_mode, "host_status": status,
        "native_build_host": common_passed and native_architecture,
        "experimental_build_host": host_mode == "apple-rosetta" and selected_passed,
        "source_dir": str(source_dir.resolve()), "filesystem_checked_at": str(parent),
        "output_dir": str(output_dir), "output_filesystem_checked_at": str(output_parent),
        "source_output_share_filesystem": shared_filesystem,
        "ram_gib": None if ram is None else round(ram, 1),
        "free_disk_gib": round(source_disk.free / GIB, 1),
        "output_free_disk_gib": round(output_disk.free / GIB, 1),
        "minimum_source_free_disk_gib": requirements["min_free_disk_gib"],
        "storage_note": "Source and output free space are not additive when they share a filesystem. This gate checks initial source capacity, not a completed build's space requirements.",
        "tools": tools, "checks": checks, "supported_build_host": selected_passed,
        "rosetta": translation,
        "note": ("Experimental Apple Container/Rosetta execution was requested; it is not native x86-64 or proof of a successful full Android build. " if host_mode == "apple-rosetta" else "")
                + "A host preflight is not proof of a complete toolchain or a buildable device tree.",
    }


def require_host(source_dir, config, host_mode="native"):
    report = host_report(source_dir, config["host_requirements"], host_mode)
    failures = [key for key, passed in report["checks"].items() if not passed]
    if failures:
        raise ValueError("Source operation blocked by host preflight: " + ", ".join(failures)
                         + ". Use native Linux x86-64 or explicitly select apple-rosetta inside the verified ARM64 Linux builder."
                         + f" Require case-sensitive source/output filesystems, {config['host_requirements']['min_ram_gib']} GiB RAM"
                         + f" and at least {config['host_requirements']['min_free_disk_gib']} GiB initially free for sources."
                         + (" " + "; ".join(report.get("rosetta", {}).get("errors", [])) if report.get("rosetta") else ""))


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
            "--manifest-name", "default.xml",
            "--git-lfs", "--no-clone-bundle", "--current-branch",
            "--repo-url", tool["url"], "--repo-rev", tool["commit"]]


def sync_command(config, jobs):
    if not 1 <= jobs <= 64:
        raise ValueError("Sync jobs must be between 1 and 64")
    tool = reference_named(config, "repo-tool")
    # Do not use --force-sync: preserve local source work on reruns.
    return [sys.executable, str(checked_path(ROOT, tool["path"]) / "repo"),
            "sync", "--current-branch", f"--jobs={jobs}", "--no-clone-bundle",
            "--no-tags", "--no-manifest-update", "--fail-fast"]


def verify_source_checkout(source_dir, relative, reference, description):
    metadata = source_dir.resolve() / ".repo"
    checkout = metadata / relative
    if metadata.is_symlink() or checkout.is_symlink() or not checkout.is_dir():
        raise ValueError(f"Missing or symlinked {description}; preserve incomplete initialization and use a new empty source directory")
    if Path(git_value(checkout, "rev-parse", "--show-toplevel")).resolve() != checkout:
        raise ValueError(f"Unexpected worktree for {description}")
    git_directory = Path(git_value(checkout, "rev-parse", "--absolute-git-dir")).resolve()
    if not git_directory.is_relative_to(metadata):
        raise ValueError(f"Git metadata for {description} escapes the source checkout")
    if git_value(checkout, "remote", "get-url", "origin") != reference["url"]:
        raise ValueError(f"Source checkout uses a different {description} origin")
    if git_value(checkout, "rev-parse", "HEAD") != reference["commit"]:
        raise ValueError(f"Source checkout uses a different {description} revision")
    if git_value(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError(f"Source {description} has local changes; preserve and review them first")


def verify_manifest_selection(source_dir):
    metadata = source_dir.resolve() / ".repo"
    selection = metadata / "manifest.xml"
    if selection.is_symlink() or not selection.is_file() or selection.stat().st_size > 65536:
        raise ValueError("Missing or unexpected active manifest selector")
    try:
        selected = ET.fromstring(selection.read_bytes())
    except ET.ParseError as error:
        raise ValueError("Invalid active manifest selector") from error
    children = list(selected)
    if (selected.tag != "manifest" or selected.attrib or len(children) != 1
            or children[0].tag != "include" or children[0].attrib != {"name": "default.xml"}
            or list(children[0])):
        raise ValueError("Active manifest must select only the pinned default.xml")
    local = metadata / "local_manifests"
    legacy = metadata / "local_manifest.xml"
    if (local.is_symlink() or (local.exists() and (not local.is_dir() or any(local.glob("*.xml"))))
            or legacy.exists() or legacy.is_symlink()):
        raise ValueError("Local manifests need reviewed configuration; files were preserved unchanged")


def verify_source_manifest(config, source_dir):
    manifest = reference_named(config, config["platform"]["reference"])
    tool = reference_named(config, "repo-tool")
    # The launcher delegates to .repo/repo: verifying only .tools/git-repo
    # does not establish which implementation would execute in this checkout.
    verify_source_checkout(source_dir, "repo", tool, "Repo implementation")
    verify_source_checkout(source_dir, "manifests", manifest, "manifest")
    verify_manifest_selection(source_dir)


def refuse_nested_source(source_dir):
    # Repo searches parent directories for .repo and could reinitialize an
    # unrelated outer tree instead of the requested empty nested directory.
    for parent in source_dir.resolve().parents:
        metadata = parent / ".repo"
        if metadata.exists() or metadata.is_symlink():
            raise ValueError("Nested Repo source directories are unsafe; the outer checkout was preserved")


def initialize(config, source_dir, dry_run=False, host_mode="native"):
    command = init_command(config)
    if dry_run:
        print(f"In {source_dir}:\n" + shlex.join(command))
        print(f"Execution requires host mode {host_mode}; this preview does not initialize or sync.")
        return
    require_host(source_dir, config, host_mode)
    refuse_nested_source(source_dir)
    repo_command(config)
    if (source_dir / ".repo").exists() or (source_dir / ".repo").is_symlink():
        verify_source_manifest(config, source_dir)
        print("Platform manifest already initialized at the configured revision.")
        return
    if source_dir.exists() and any(source_dir.iterdir()):
        raise ValueError("Refusing to initialize a nonempty source directory")
    source_dir.mkdir(parents=True, exist_ok=True)
    run(command, cwd=source_dir)
    verify_source_manifest(config, source_dir)


def synchronize(config, source_dir, jobs, dry_run=False, host_mode="native"):
    command = sync_command(config, jobs)
    if dry_run:
        print(f"In {source_dir}:\n" + shlex.join(command))
        print(f"Host mode {host_mode}: this previews a full platform download, not a complete Xiaomi device build.")
        return
    require_host(source_dir, config, host_mode)
    refuse_nested_source(source_dir)
    repo = repo_command(config)
    verify_source_manifest(config, source_dir)
    # LFS must be fetched for build sources, unlike lightweight references.
    environment = os.environ.copy()
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["REPO_SKIP_SELF_UPDATE"] = "1"
    environment.pop("GIT_LFS_SKIP_SMUDGE", None)
    print("+ " + shlex.join(command), flush=True)
    subprocess.run(command, cwd=source_dir, env=environment, check=True,
                   stdin=subprocess.DEVNULL, shell=False)
    verify_source_manifest(config, source_dir)
    output = ROOT / "reports" / ("resolved-manifest-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".xml")
    output.parent.mkdir(parents=True, exist_ok=True)
    run(repo + ["manifest", "--revision-as-HEAD", "--output-file", output], cwd=source_dir)
    print(f"Saved fully resolved project revisions: {output}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    doctor = commands.add_parser("doctor", help="Report supported Android build-host prerequisites")
    doctor.add_argument("--source-dir", type=Path)
    doctor.add_argument("--host-mode", choices=HOST_MODES, default="native")
    doctor.add_argument("--require-build-host", action="store_true")
    for name in ("fetch", "verify"):
        command = commands.add_parser(name, help=f"{name.capitalize()} pinned reference checkouts")
        command.add_argument("names", nargs="*")
    for name in ("init", "sync"):
        command = commands.add_parser(name, help=f"{name.capitalize()} the full platform on a supported host")
        command.add_argument("--source-dir", type=Path)
        command.add_argument("--host-mode", choices=HOST_MODES, default="native")
        command.add_argument("--dry-run", action="store_true")
        if name == "sync":
            command.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        config = load_config()
        source_dir = getattr(args, "source_dir", None) or checked_path(ROOT, config["platform"]["source_dir"])
        source_dir = source_dir.expanduser().resolve()
        if args.action == "doctor":
            report = host_report(source_dir, config["host_requirements"], args.host_mode)
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
            initialize(config, source_dir, args.dry_run, args.host_mode)
        elif args.action == "sync":
            synchronize(config, source_dir, args.jobs, args.dry_run, args.host_mode)
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, StopIteration) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
