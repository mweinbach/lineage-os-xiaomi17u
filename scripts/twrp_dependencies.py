#!/usr/bin/env python3
"""Fetch and verify reviewed supplementary sources without changing Repo's lock."""

import argparse
from contextlib import contextmanager
import ctypes
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile

try:
    from scripts import twrp_workspace
except ModuleNotFoundError:
    import twrp_workspace


ROOT = Path(__file__).resolve().parents[1]
CONFIG = "config/twrp-dependencies.json"
HEX256 = re.compile(r"[0-9a-f]{64}")
NOTE = ("Supplementary source only. The immutable Repo snapshot is unchanged; its 391 projects "
        "alone are not a complete recovery build closure. No phone or build command is run.")


def config_file(control_root):
    root = twrp_workspace.absolute_path(control_root)
    path = root / CONFIG
    twrp_workspace.absolute_path(path)
    if not path.exists():
        return None
    if not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise ValueError("Supplementary configuration must be a small regular JSON file")
    return path


def load_config(control_root=ROOT):
    """Old control bundles without this optional configuration require no additions."""
    path = config_file(control_root)
    if path is None:
        return None
    config = json.loads(path.read_text())
    if config.get("schema_version") != 1 or config.get("device") != "nezha":
        raise ValueError("Unsupported supplementary source configuration")
    base = config["base"]
    twrp_workspace.absolute_path(base["source_dir"])
    if (not twrp_workspace.SHA.fullmatch(base["manifest_commit"])
            or not twrp_workspace.SHA.fullmatch(base["repo_commit"])
            or not HEX256.fullmatch(base["frozen_manifest_sha256"])
            or type(base["project_count"]) is not int or base["project_count"] < 1):
        raise ValueError("Supplementary sources require an exact frozen base identity")
    if not isinstance(config["projects"], list) or not config["projects"]:
        raise ValueError("Supplementary configuration must declare reviewed projects")
    paths = []
    for project in config["projects"]:
        path = twrp_workspace.relative_path(project["path"])
        twrp_workspace.public_url(project["url"])
        if (not twrp_workspace.SHA.fullmatch(project["commit"])
                or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", project["tag"])):
            raise ValueError("Supplementary projects need exact commits and safe upstream tags")
        if any(twrp_workspace.overlap(path, previous) for previous in paths):
            raise ValueError("Supplementary project paths overlap")
        paths.append(path)
    return config


def descriptor(control_root=ROOT):
    config = load_config(control_root)
    if config is None:
        return None
    return {"configuration_sha256": hashlib.sha256(config_file(control_root).read_bytes()).hexdigest(),
            "base": config["base"], "projects": config["projects"]}


def base_context(control_root, source_dir, paths=None):
    reviewed = descriptor(control_root)
    if reviewed is None:
        return None
    config = twrp_workspace.load_config(Path(control_root) / "config/twrp.json")
    source = twrp_workspace.absolute_path(source_dir)
    base = reviewed["base"]
    if source != Path(base["source_dir"]) or source != Path(config["source_dir"]):
        raise ValueError("Supplementary sources are admitted only in the explicitly selected base checkout")
    paths = paths or twrp_workspace.paths_for(config, source=source)
    paths = twrp_workspace.paths_for(config, paths["source_dir"], paths["out_dir"], paths["report_dir"])
    if paths["source_dir"] != source:
        raise ValueError("Base source path and supplementary source path disagree")
    if (config["manifest"]["commit"] != base["manifest_commit"]
            or config["repo_tool"]["commit"] != base["repo_commit"]):
        raise ValueError("Supplementary configuration does not match the pinned base manifest and Repo")
    twrp_workspace.verify_control(config, source)
    frozen = twrp_workspace.load_snapshot(config, paths)
    snapshot = twrp_workspace.checked_report(paths["report_dir"] / twrp_workspace.SNAPSHOT)
    if len(frozen) != base["project_count"] or hashlib.sha256(snapshot.read_bytes()).hexdigest() != base["frozen_manifest_sha256"]:
        raise ValueError("Supplementary sources do not match the exact immutable base snapshot")
    current = twrp_workspace.parse_manifest(twrp_workspace.manifest_text(source / ".repo/repo/repo", source))
    if set(current) != set(frozen) or any(
            any(current[path][key] != frozen[path][key] for key in ("name", "remote", "url")) for path in current):
        raise ValueError("Base Repo project selection changed")
    for project in reviewed["projects"]:
        relative = PurePosixPath(project["path"])
        if any(twrp_workspace.overlap(relative, PurePosixPath(path)) for path in frozen):
            raise ValueError("Supplementary source overlaps a frozen Repo project")
        target = twrp_workspace.absolute_path(source / project["path"])
        for parent in target.parents:
            if parent == source:
                break
            if any((parent / metadata).exists() or (parent / metadata).is_symlink() for metadata in (".git", ".repo")):
                raise ValueError("Supplementary source is nested in an unrelated checkout")
    return {"reviewed": reviewed, "config": config, "source": source, "paths": paths, "frozen": frozen}


def git_value(target, *args):
    # A local core.fileMode=false setting must not hide executable-bit changes.
    return twrp_workspace.run(["git", "-c", "core.fileMode=true", "-C", target, *args], capture=True).stdout.strip()


def verify_project(project, target):
    target = twrp_workspace.absolute_path(target)
    metadata = target / ".git"
    if not target.is_dir() or not metadata.is_dir() or metadata.is_symlink():
        raise ValueError(f"Missing or non-standalone supplementary checkout: {project['path']}")
    root = Path(git_value(target, "rev-parse", "--show-toplevel")).resolve()
    git_dir = Path(git_value(target, "rev-parse", "--absolute-git-dir")).resolve()
    head = git_value(target, "rev-parse", "HEAD")
    origin = git_value(target, "remote", "get-url", "origin")
    status = git_value(target, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching")
    if root != target or git_dir != metadata:
        raise ValueError(f"Supplementary Git root or metadata differs: {project['path']}")
    if head != project["commit"] or origin != project["url"]:
        raise ValueError(f"Supplementary HEAD or origin differs from its reviewed pin: {project['path']}")
    if status:
        raise ValueError(f"Supplementary source has local, ignored or mode changes; preserved: {project['path']}")
    return {**project, "actual_head": head, "actual_origin": origin, "root": str(root),
            "git_dir": str(git_dir), "clean": True, "mode_changes_checked": True, "ignored_files_checked": True}


def verify(control_root, source_dir, paths=None):
    """Verify additions; the caller build runner separately validates base patches."""
    context = base_context(control_root, source_dir, paths)
    if context is None:
        return None
    reviewed = context["reviewed"]
    projects = [verify_project(project, context["source"] / project["path"]) for project in reviewed["projects"]]
    return {"configuration_sha256": reviewed["configuration_sha256"], "base": reviewed["base"],
            "base_worktrees_checked": False, "projects": projects, "verified": True,
            "note": "The caller must also verify the base project worktrees and exact reviewed patch closure."}


def publish_exclusive(staging, target):
    """Linux renameat2 prevents replacing even an empty directory created in a race."""
    libc = ctypes.CDLL(None, use_errno=True)
    rename = getattr(libc, "renameat2", None)
    if rename is None:
        raise ValueError("Exclusive source publication requires Linux renameat2 support")
    rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    rename.restype = ctypes.c_int
    if rename(-100, os.fsencode(staging), -100, os.fsencode(target), 1) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(target))


def fetch_project(project, source):
    target = twrp_workspace.absolute_path(source / project["path"])
    if target.exists() or target.is_symlink():
        return verify_project(project, target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".twrp-dependency-", dir=target.parent) as directory:
        staging = Path(directory) / "checkout"
        twrp_workspace.run(["git", "init", staging])
        twrp_workspace.run(["git", "-C", staging, "remote", "add", "origin", project["url"]])
        twrp_workspace.run(["git", "-C", staging, "fetch", "--depth=1", "--no-tags", "origin", "refs/tags/" + project["tag"]])
        if git_value(staging, "rev-parse", "--verify", "FETCH_HEAD^{commit}") != project["commit"]:
            raise ValueError("Fetched upstream tag differs from the reviewed supplementary commit")
        twrp_workspace.run(["git", "-C", staging, "checkout", "--detach", project["commit"]])
        verify_project(project, staging)
        twrp_workspace.absolute_path(target)
        publish_exclusive(staging, target)
    return verify_project(project, target)


@contextmanager
def operation_lock(paths):
    """Share the build runner's exclusive lock without importing its mutators."""
    directory = twrp_workspace.absolute_path(paths["report_dir"])
    if not directory.is_dir():
        raise ValueError("Frozen source reports must exist before fetching additions")
    path = directory / "build-operation.lock"
    data = (json.dumps({"action": "dependencies-fetch", "pid": os.getpid(),
                       "started_at": datetime.now(timezone.utc).isoformat()}) + "\n").encode()
    try:
        with path.open("xb") as stream:
            stream.write(data)
            inode = os.fstat(stream.fileno()).st_ino
    except FileExistsError as error:
        raise ValueError("Another or interrupted build/source operation owns the lock; inspect before retrying") from error
    try:
        yield
    finally:
        if not path.is_symlink() and path.is_file() and path.stat().st_ino == inode and path.read_bytes() == data:
            path.unlink()


def fetch(control_root, source_dir, host_mode, paths=None):
    config = twrp_workspace.load_config(Path(control_root) / "config/twrp.json")
    selected = paths or twrp_workspace.paths_for(config, source=source_dir)
    host = twrp_workspace.require_host(config, selected, host_mode)
    with operation_lock(selected):
        return _fetch_locked(control_root, source_dir, host, selected)


def _fetch_locked(control_root, source_dir, host, selected):
    context = base_context(control_root, source_dir, selected)
    if context is None:
        raise ValueError("No reviewed supplementary source configuration in this control bundle")
    base = twrp_workspace.project_report(context["source"], context["frozen"])
    failures = [f"{project['path']}: {error}" for project in base["projects"]
                for error in project["errors"] if error != "Local changes preserved"]
    if not base["all_present"] or len(base["projects"]) != len(context["frozen"]) or failures:
        raise ValueError("Base project HEAD/origin verification failed: " + "; ".join(failures))
    projects = [fetch_project(project, context["source"]) for project in context["reviewed"]["projects"]]
    report = {"schema_version": 1, "configuration_sha256": context["reviewed"]["configuration_sha256"],
              "base": context["reviewed"]["base"], "base_worktrees_checked": True,
              "base_dirty_projects": [{"path": project["path"], "local_changes": project.get("local_changes", "")}
                                      for project in base["projects"] if not project["clean"]],
              "host_preflight": host, "projects": projects, "verified": True, "note": NOTE}
    now = datetime.now(timezone.utc)
    report["recorded_at"] = now.isoformat()
    twrp_workspace.write_report(context["paths"], "dependencies-fetch-" + now.strftime("%Y%m%dT%H%M%S%fZ") + ".json",
                                json.dumps(report, indent=2) + "\n")
    return report


def plan(control_root=ROOT, source_dir=None):
    reviewed = descriptor(control_root)
    if reviewed is None:
        return {"action": "plan", "executes_commands": False, "writes_files": False, "projects": []}
    source = twrp_workspace.absolute_path(source_dir or reviewed["base"]["source_dir"])
    if source != Path(reviewed["base"]["source_dir"]):
        raise ValueError("Plan source path differs from the explicitly selected base checkout")
    return {"action": "plan", "executes_commands": False, "writes_files": False,
            "source_dir": str(source), **reviewed, "note": NOTE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("plan", "fetch", "verify"), default="plan")
    parser.add_argument("--control-root", type=Path, default=ROOT)
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--host-mode", choices=twrp_workspace.workspace.HOST_MODES, default="native")
    args = parser.parse_args(argv)
    try:
        reviewed = descriptor(args.control_root)
        source = args.source_dir or (Path(reviewed["base"]["source_dir"]) if reviewed else None)
        if args.action == "plan":
            report = plan(args.control_root, source)
        elif args.action == "fetch":
            report = fetch(args.control_root, source, args.host_mode)
        else:
            report = verify(args.control_root, source)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
