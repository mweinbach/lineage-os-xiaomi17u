#!/usr/bin/env python3
"""Plan, initialize, sync, freeze and verify isolated, pinned TWRP sources."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
from urllib.parse import urljoin, urlparse
import xml.etree.ElementTree as ET

try:
    from scripts import workspace
except ModuleNotFoundError:  # Direct execution from a copied control bundle.
    import workspace


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config/twrp.json"
SNAPSHOT = "resolved-manifest.xml"
STATE = "source-state.json"
SHA = re.compile(r"[0-9a-f]{40}")
RESERVED = (Path("/work/evolution"), Path("/work/out/evolution"), Path("/work/cache"))


def public_url(value):
    parsed = urlparse(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username
            or parsed.password or parsed.query or parsed.fragment
            or any(character.isspace() for character in value)):
        raise ValueError("Source URLs must be public HTTPS URLs without credentials")
    return value


def load_config(path=CONFIG):
    config = json.loads(path.read_text())
    if config.get("schema_version") != 1 or config.get("device") != "nezha":
        raise ValueError("Unsupported TWRP source configuration")
    for name in ("manifest", "repo_tool"):
        if not SHA.fullmatch(config[name]["commit"]):
            raise ValueError("Source and Repo revisions must be full commit hashes")
        public_url(config[name]["url"])
    requirements = config["host_requirements"]
    if (config["manifest"]["name"] != "default.xml" or config["depth"] != 1
            or requirements["min_free_disk_gib"] < 150
            or requirements["min_ram_gib"] < 16
            or requirements["filesystem"] != "ext4"):
        raise ValueError("TWRP configuration must retain the reviewed manifest, depth and host gates")
    if not isinstance(config["expected_project_count"], int) or config["expected_project_count"] < 1:
        raise ValueError("Expected source project count must be a positive integer")
    if not config["pinned_projects"]:
        raise ValueError("Reviewed GitHub project pins are required")
    for path, pin in config["pinned_projects"].items():
        relative_path(path)
        relative_path(pin["name"])
        if not SHA.fullmatch(pin["commit"]) or urlparse(public_url(pin["url"])).hostname != "github.com":
            raise ValueError("GitHub source overrides need reviewed full commit hashes and public URLs")
    sync_command(config, Path(config["repo_tool"]["launcher"]), config["sync_jobs"])
    return config


def absolute_path(value):
    path = Path(value).expanduser()
    if not path.is_absolute() or ".." in path.parts or path == Path("/"):
        raise ValueError(f"Expected an absolute, non-root path without traversal: {path}")
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError(f"Symlink in managed path: {candidate}")
    return path.resolve()


def overlap(first, second):
    return first == second or first.is_relative_to(second) or second.is_relative_to(first)


def paths_for(config, source=None, output=None, reports=None):
    paths = {name: absolute_path(value or config[name]) for name, value in
             (("source_dir", source), ("out_dir", output), ("report_dir", reports))}
    for name, path in paths.items():
        if any(overlap(path, reserved) for reserved in RESERVED):
            raise ValueError(f"TWRP {name} overlaps a reserved Evolution source/output/cache path")
        for parent in path.parents:
            if any((parent / metadata).exists() or (parent / metadata).is_symlink()
                   for metadata in (".repo", ".git")):
                raise ValueError(f"TWRP {name} is nested in an unrelated source checkout")
        metadata_names = (".git",) if name == "source_dir" else (".repo", ".git")
        if any((path / metadata).exists() or (path / metadata).is_symlink() for metadata in metadata_names):
            raise ValueError(f"TWRP {name} is an unrelated source checkout")
    values = list(paths.values())
    if any(overlap(first, second) for index, first in enumerate(values) for second in values[index + 1:]):
        raise ValueError("TWRP source, output and report directories must not overlap")
    return paths


def run(args, cwd=None, capture=False, timeout=600):
    environment = os.environ.copy()
    environment.update(GIT_TERMINAL_PROMPT="0", REPO_SKIP_SELF_UPDATE="1", GIT_OPTIONAL_LOCKS="0")
    environment.pop("GIT_LFS_SKIP_SMUDGE", None)
    if not capture:
        print("+ " + shlex.join(str(arg) for arg in args), flush=True)
    return subprocess.run([str(arg) for arg in args], cwd=cwd, env=environment,
                          check=True, text=True, capture_output=capture,
                          stdin=subprocess.DEVNULL, shell=False, timeout=timeout)


def git_value(path, *args):
    return run(["git", "-C", path, *args], capture=True).stdout.strip()


@contextmanager
def output_environment(output):
    previous = os.environ.get("OUT_DIR")
    os.environ["OUT_DIR"] = str(output)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("OUT_DIR", None)
        else:
            os.environ["OUT_DIR"] = previous


def filesystem_type(path, mountinfo=Path("/proc/self/mountinfo")):
    """Read the real Linux mount type; stat's ext2/ext3 token is ambiguous."""
    candidates = []
    for line in mountinfo.read_text().splitlines():
        left, separator, right = line.partition(" - ")
        fields = left.split()
        if not separator or len(fields) < 6 or not right.split():
            continue
        mount = Path(re.sub(r"\\([0-7]{3})", lambda match: chr(int(match[1], 8)), fields[4]))
        if path == mount or path.is_relative_to(mount):
            candidates.append((len(mount.parts), right.split()[0]))
    if not candidates:
        raise ValueError(f"No Linux mount identity for {path}")
    return max(candidates)[1]


def preflight(config, paths, host_mode):
    with output_environment(paths["out_dir"]):
        report = workspace.host_report(paths["source_dir"], config["host_requirements"], host_mode)
    report["filesystems"] = {}
    for name, path in paths.items():
        parent = workspace.existing_parent(path)
        try:
            filesystem = filesystem_type(parent)
        except (OSError, ValueError) as error:
            filesystem = f"unverified: {error}"
        report["filesystems"][name] = filesystem
        report["checks"][name + "_ext4"] = filesystem == "ext4"
    report["checks"]["output_free_disk"] = (
        workspace.shutil.disk_usage(workspace.existing_parent(paths["out_dir"])).free
        >= config["host_requirements"]["min_free_disk_gib"] * workspace.GIB)
    report["supported_build_host"] = all(report["checks"].values())
    if not report["supported_build_host"]:
        report["host_status"] = "blocked"
    report["note"] += " This checks source operations only; the host must separately confirm sole ownership of the named volume."
    return report


def require_host(config, paths, host_mode):
    report = preflight(config, paths, host_mode)
    failures = [name for name, passed in report["checks"].items() if not passed]
    if failures:
        raise ValueError("TWRP source operation blocked by host preflight: " + ", ".join(failures))
    return report


def verify_launcher(config, launcher):
    launcher = absolute_path(launcher)
    checkout = launcher.parent
    if (launcher.name != "repo" or not launcher.is_file()
            or not (checkout / ".git").is_dir() or (checkout / ".git").is_symlink()):
        raise ValueError("Repo launcher must be a regular file in its pinned standalone checkout")
    if Path(git_value(checkout, "rev-parse", "--show-toplevel")).resolve() != checkout:
        raise ValueError("Repo launcher is not in the expected standalone checkout")
    for args, expected in ((("remote", "get-url", "origin"), config["repo_tool"]["url"]),
                           (("rev-parse", "HEAD"), config["repo_tool"]["commit"])):
        if git_value(checkout, *args) != expected:
            raise ValueError("Repo launcher origin or revision differs from its pin")
    if git_value(checkout, "status", "--porcelain", "--untracked-files=all"):
        raise ValueError("Repo launcher has local changes; preserve and review them first")
    return launcher


def verify_control(config, source):
    # Reuse the reviewed checks for .repo metadata roots, clean worktrees,
    # exact origin/HEAD and the default.xml selector without local overrides.
    for relative, reference, description in (("repo", config["repo_tool"], "Repo implementation"),
                                              ("manifests", config["manifest"], "TWRP manifest")):
        workspace.verify_source_checkout(source, relative, reference, description)
    workspace.verify_manifest_selection(source)


def init_command(config, launcher):
    manifest, repo = config["manifest"], config["repo_tool"]
    return [sys.executable, str(launcher), "init", "--manifest-url", manifest["url"],
            "--manifest-branch", manifest["commit"], "--manifest-name", manifest["name"],
            "--depth=1", "--git-lfs", "--current-branch", "--no-clone-bundle",
            "--repo-url", repo["url"], "--repo-rev", repo["commit"]]


def sync_command(config, launcher, jobs):
    if not isinstance(jobs, int) or isinstance(jobs, bool) or not 1 <= jobs <= 64:
        raise ValueError("Sync jobs must be between 1 and 64")
    return [sys.executable, str(launcher), "sync", "-c", f"-j{jobs}",
            "--no-clone-bundle", "--no-tags", "--no-manifest-update", "--fail-fast"]


def plan(config, paths, launcher, host_mode, jobs):
    return {"action": "plan", "executes_commands": False, "host_mode": host_mode,
            **{name: str(path) for name, path in paths.items()},
            "manifest": config["manifest"], "repo_tool": config["repo_tool"],
            "reviewed_project_pins": len(config["pinned_projects"]),
            "host_requirements": config["host_requirements"],
            "commands": {"init": init_command(config, launcher),
                         "sync": sync_command(config, launcher, jobs)},
            "snapshot": str(paths["report_dir"] / SNAPSHOT),
            "note": config["note"] + " No host probes, network calls or filesystem writes run in plan mode."}


def relative_path(value):
    path = PurePosixPath(value)
    if (not value or path.is_absolute() or any(part in {"..", ".repo", ".git"} for part in path.parts)
            or str(path) != value or str(path) == "."):
        raise ValueError(f"Unsafe manifest path: {value!r}")
    return path


def parse_manifest(text, resolved=False):
    if len(text) > 32 * 1024 * 1024 or "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("Unexpected manifest size or XML declaration")
    root = ET.fromstring(text)
    if root.tag != "manifest" or root.findall("include") or root.findall("remove-project"):
        raise ValueError("Expected the flattened Repo manifest")
    remotes = {}
    for remote in root.findall("remote"):
        name = remote.attrib["name"]
        if name in remotes:
            raise ValueError("Duplicate manifest remote")
        remotes[name] = remote.attrib
    default = root.find("default")
    defaults = {} if default is None else default.attrib
    projects = {}
    for project in root.findall("project"):
        if project.findall("project"):
            raise ValueError("Nested projects need explicit review")
        item = project.attrib
        name = str(relative_path(item["name"]))
        path = str(relative_path(item.get("path", name)))
        remote = remotes[item.get("remote", defaults.get("remote"))]
        revision = item.get("revision", remote.get("revision", defaults.get("revision", "")))
        if path in projects or (resolved and not SHA.fullmatch(revision)):
            raise ValueError("Duplicate project path or unresolved project revision")
        url = public_url(urljoin(public_url(remote["fetch"]).rstrip("/") + "/", name))
        projects[path] = {"name": name, "path": path, "revision": revision,
                          "remote": remote.get("alias", remote["name"]), "url": url}
    if not projects:
        raise ValueError("Manifest contains no projects")
    return projects


def manifest_text(launcher, source, resolved=False):
    command = [sys.executable, str(launcher), "manifest", "--output-file=-"]
    if resolved:
        command.append("--revision-as-HEAD")
    return run(command, cwd=source, capture=True).stdout


def project_report(source, projects, allow_missing=False):
    records, failures = [], []
    metadata = source / ".repo"
    for relative, expected in sorted(projects.items()):
        record = {**expected, "head": None, "clean": False, "missing": False, "errors": []}
        try:
            target = absolute_path(source / relative)
            if not (target / ".git").exists():
                record["missing"] = True
                if allow_missing and (not target.exists() or not any(target.iterdir())):
                    records.append(record)
                    continue
                raise ValueError("Project is missing or has unmanaged files; preserve it before retrying")
            if Path(git_value(target, "rev-parse", "--show-toplevel")).resolve() != target:
                raise ValueError("Unexpected project worktree root")
            gitdir = Path(git_value(target, "rev-parse", "--absolute-git-dir")).resolve()
            if not gitdir.is_relative_to(metadata):
                raise ValueError("Project Git metadata escapes this Repo checkout")
            record["head"] = git_value(target, "rev-parse", "HEAD")
            record["actual_url"] = git_value(target, "remote", "get-url", expected["remote"])
            record["local_changes"] = git_value(target, "status", "--porcelain", "--untracked-files=all")
            record["clean"] = not record["local_changes"]
            if not SHA.fullmatch(record["head"]):
                record["errors"].append("Invalid project HEAD")
            if SHA.fullmatch(expected["revision"]) and record["head"] != expected["revision"]:
                record["errors"].append("HEAD differs from frozen project revision")
            if record["actual_url"] != expected["url"]:
                record["errors"].append("Remote differs from manifest")
            if not record["clean"]:
                record["errors"].append("Local changes preserved")
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            record["errors"].append(str(error))
        failures.extend(f"{relative}: {error}" for error in record["errors"])
        records.append(record)
    return {"projects": records, "project_count": len(records), "failures": failures,
            "all_present": not any(record["missing"] for record in records),
            "verified": not failures and not any(record["missing"] for record in records)}


def validate_project_pins(config, projects, resolved=False):
    if len(projects) != config["expected_project_count"]:
        raise ValueError("Source project count differs from the reviewed TWRP manifest")
    github = {path for path, project in projects.items() if urlparse(project["url"]).hostname == "github.com"}
    if github != set(config["pinned_projects"]):
        raise ValueError("GitHub overrides differ from the reviewed project selection")
    for path, pin in config["pinned_projects"].items():
        project = projects[path]
        if any(project[key] != pin[key] for key in ("name", "remote", "url")):
            raise ValueError(f"Reviewed project identity differs: {path}")
        if resolved and project["revision"] != pin["commit"]:
            raise ValueError(f"Project HEAD moved from the reviewed GitHub pin: {path}")


def expected_projects(config, projects):
    validate_project_pins(config, projects)
    return {path: dict(project, revision=config["pinned_projects"][path]["commit"])
            if path in config["pinned_projects"] else project for path, project in projects.items()}


def validate_resolved_selection(config, source, selected, resolved):
    validate_project_pins(config, resolved, resolved=True)
    if set(selected) != set(resolved) or any(
            any(selected[path][key] != resolved[path][key] for key in ("name", "remote", "url")) for path in selected):
        raise ValueError("Resolved manifest differs from the selected source projects")
    for path, project in selected.items():
        revision = project["revision"]
        if path in config["pinned_projects"]:
            expected = config["pinned_projects"][path]["commit"]
        elif SHA.fullmatch(revision):
            expected = revision
        elif revision.startswith("refs/tags/"):
            # AOSP annotated tags name tag objects; compare their peeled
            # commits, not an arbitrary local HEAD captured after sync.
            expected = git_value(source / path, "rev-parse", "--verify", revision + "^{commit}")
        else:
            raise ValueError(f"Unreviewed moving source revision: {path}: {revision}")
        if resolved[path]["revision"] != expected:
            raise ValueError(f"Project HEAD differs from its selected tag or commit: {path}")


def checked_report(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Missing or symlinked source report: {path}")
    return path


def identity(config, paths):
    return {"schema_version": 1, "manifest": config["manifest"],
            "repo_tool": {key: config["repo_tool"][key] for key in ("url", "commit")},
            "reviewed_project_pins_sha256": hashlib.sha256(
                json.dumps(config["pinned_projects"], sort_keys=True).encode()).hexdigest(),
            **{name: str(path) for name, path in paths.items()}}


def write_report(paths, name, data):
    directory = paths["report_dir"]
    absolute_path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / name
    with target.open("x") as stream:
        stream.write(data)
    return target


def record_action(config, paths, action, report):
    now = datetime.now(timezone.utc)
    record = {**identity(config, paths), "action": action, "recorded_at": now.isoformat(), **report}
    name = action + "-" + now.strftime("%Y%m%dT%H%M%S%fZ") + ".json"
    write_report(paths, name, json.dumps(record, indent=2) + "\n")
    return record


def load_snapshot(config, paths):
    directory = paths["report_dir"]
    state = json.loads(checked_report(directory / STATE).read_text())
    if any(state.get(name) != expected for name, expected in identity(config, paths).items()):
        raise ValueError("Frozen source identity differs from this configuration; reports preserved")
    text = checked_report(directory / SNAPSHOT).read_text()
    if hashlib.sha256(text.encode()).hexdigest() != state.get("resolved_manifest_sha256"):
        raise ValueError("Frozen manifest hash differs from its recorded identity")
    projects = parse_manifest(text, resolved=True)
    validate_project_pins(config, projects, resolved=True)
    if state.get("project_count") != len(projects):
        raise ValueError("Frozen project count differs from its recorded identity")
    return projects


def verify(config, paths, launcher, host_mode, host=None):
    verify_launcher(config, launcher)
    verify_control(config, paths["source_dir"])
    frozen = load_snapshot(config, paths)
    current = parse_manifest(manifest_text(launcher, paths["source_dir"]))
    if set(current) != set(frozen) or any(
            any(current[path][key] != frozen[path][key] for key in ("name", "remote", "url")) for path in current):
        raise ValueError("Project selection differs from the frozen manifest")
    report = project_report(paths["source_dir"], frozen)
    report["host_preflight"] = host if host is not None else preflight(config, paths, host_mode)
    report = record_action(config, paths, "verify", report)
    if not report["verified"]:
        raise ValueError("TWRP source verification failed; files preserved: " + "; ".join(report["failures"]))
    return report


def initialize(config, paths, launcher, host_mode):
    host = require_host(config, paths, host_mode)
    verify_launcher(config, launcher)
    source = paths["source_dir"]
    if (source / ".repo").exists() or (source / ".repo").is_symlink():
        verify_control(config, source)
        return record_action(config, paths, "init", {"already_initialized": True, "host_preflight": host})
    if source.exists() and (not source.is_dir() or any(source.iterdir())):
        raise ValueError("Refusing to initialize a nonempty unrelated source directory")
    source.mkdir(parents=True, exist_ok=True)
    run(init_command(config, launcher), cwd=source)
    verify_control(config, source)
    return record_action(config, paths, "init", {"already_initialized": False, "host_preflight": host})


def synchronize(config, paths, launcher, host_mode, jobs):
    host = require_host(config, paths, host_mode)
    verify_launcher(config, launcher)
    source, reports = paths["source_dir"], paths["report_dir"]
    verify_control(config, source)
    # Once captured, the first full revision set is immutable. A repeat sync
    # verifies it without following moving branches or resetting local work.
    if any((reports / name).exists() or (reports / name).is_symlink() for name in (STATE, SNAPSHOT)):
        return verify(config, paths, launcher, host_mode, host=host)
    projects = parse_manifest(manifest_text(launcher, source))
    before = project_report(source, expected_projects(config, projects), allow_missing=True)
    if before["failures"]:
        record_action(config, paths, "sync-blocked", {**before, "host_preflight": host})
        raise ValueError("Sync refused local source changes: " + "; ".join(before["failures"]))
    record_action(config, paths, "sync-start", {"host_preflight": host, "command": sync_command(config, launcher, jobs)})
    run(sync_command(config, launcher, jobs), cwd=source, timeout=None)
    return freeze(config, paths, launcher, host_mode, host=host)


def freeze(config, paths, launcher, host_mode, host=None):
    """Capture a manually completed sync without fetching or changing sources."""
    host = require_host(config, paths, host_mode) if host is None else host
    verify_launcher(config, launcher)
    source, reports = paths["source_dir"], paths["report_dir"]
    verify_control(config, source)
    if any((reports / name).exists() or (reports / name).is_symlink() for name in (STATE, SNAPSHOT)):
        return verify(config, paths, launcher, host_mode, host=host)
    projects = parse_manifest(manifest_text(launcher, source))
    before = project_report(source, expected_projects(config, projects))
    if not before["verified"]:
        record_action(config, paths, "freeze-incomplete", {**before, "host_preflight": host})
        raise ValueError("Cannot freeze incomplete or modified sources: " + "; ".join(before["failures"]))
    text = manifest_text(launcher, source, resolved=True)
    resolved = parse_manifest(text, resolved=True)
    validate_resolved_selection(config, source, projects, resolved)
    after = project_report(source, resolved)
    if not after["verified"]:
        record_action(config, paths, "freeze-incomplete", {**after, "host_preflight": host})
        raise ValueError("Sources changed while freezing revisions: " + "; ".join(after["failures"]))
    state = {**identity(config, paths), "recorded_at": datetime.now(timezone.utc).isoformat(),
             "resolved_manifest_sha256": hashlib.sha256(text.encode()).hexdigest(),
             "project_count": len(resolved), "host_preflight": host}
    write_report(paths, SNAPSHOT, text)
    write_report(paths, STATE, json.dumps(state, indent=2) + "\n")
    return record_action(config, paths, "freeze-complete", {**after, "host_preflight": host})


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("plan", "init", "sync", "freeze", "verify"), default="plan")
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--repo-launcher", type=Path)
    parser.add_argument("--host-mode", choices=workspace.HOST_MODES, default="native")
    parser.add_argument("--jobs", type=int)
    args = parser.parse_args(argv)
    try:
        config = load_config()
        paths = paths_for(config, args.source_dir, args.out_dir, args.report_dir)
        launcher = absolute_path(args.repo_launcher or config["repo_tool"]["launcher"])
        jobs = config["sync_jobs"] if args.jobs is None else args.jobs
        sync_command(config, launcher, jobs)
        if args.action == "plan":
            report = plan(config, paths, launcher, args.host_mode, jobs)
        elif args.action == "init":
            report = initialize(config, paths, launcher, args.host_mode)
        elif args.action == "sync":
            report = synchronize(config, paths, launcher, args.host_mode, jobs)
        elif args.action == "freeze":
            report = freeze(config, paths, launcher, args.host_mode)
        else:
            report = verify(config, paths, launcher, args.host_mode)
        summary = {name: value for name, value in report.items() if name != "projects"}
        print(json.dumps(summary, indent=2))
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError, ET.ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
