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
    from scripts import twrp_workspace, twrp_patch_state
except ModuleNotFoundError:
    import twrp_workspace
    import twrp_patch_state


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
        if twrp_workspace.overlap(relative, PurePosixPath(twrp_patch_state.TARGET)):
            raise ValueError("Supplementary source overlaps the controlled Nezha target")
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
    # Do not trust local settings that suppress worktree or executable checks,
    # or invoke a filesystem-monitor hook while verifying source identity.
    value = twrp_workspace.run(["git", "-c", "core.fileMode=true", "-c", "core.fsmonitor=false",
                                "-c", "core.ignoreStat=false", "-C", target, *args], capture=True).stdout
    # Porcelain's leading space is the index/worktree distinction. Trimming
    # NUL records could turn an unstaged edit into a different authorization.
    return value if "-z" in args else value.strip()


def verify_project(project, target, patches=(), phase="before"):
    if phase not in {"before", "after"}:
        raise ValueError("Supplementary patch verification requires an explicit before or after phase")
    patches = list(patches)
    reviewed = {"patches": patches, "supplementary_projects": {"projects": [project]}}
    twrp_patch_state.validate_patch_bases({}, reviewed)
    if any(entry["project"] != project["path"] for entry in patches):
        raise ValueError("Supplementary patch belongs to a different source owner")
    files = [str(twrp_patch_state.relative_path(item["path"])) for entry in patches for item in entry["files"]]
    if len(files) != len(set(files)):
        raise ValueError("Overlapping supplementary patch files are not admitted")
    target = twrp_workspace.absolute_path(target)
    metadata = target / ".git"
    if not target.is_dir() or not metadata.is_dir() or metadata.is_symlink():
        raise ValueError(f"Missing or non-standalone supplementary checkout: {project['path']}")
    root = Path(git_value(target, "rev-parse", "--show-toplevel")).resolve()
    git_dir = Path(git_value(target, "rev-parse", "--absolute-git-dir")).resolve()
    head = git_value(target, "rev-parse", "HEAD")
    origin = git_value(target, "remote", "get-url", "origin")
    if root != target or git_dir != metadata:
        raise ValueError(f"Supplementary Git root or metadata differs: {project['path']}")
    if head != project["commit"] or origin != project["url"]:
        raise ValueError(f"Supplementary HEAD or origin differs from its reviewed pin: {project['path']}")
    entries = git_value(target, "ls-files", "-v", "-z").split("\0")
    # Lowercase tags mark assume-unchanged entries; S marks skip-worktree.
    # Neither can be accepted merely because `git status` then looks clean.
    # Normal tracked entries have exactly the uppercase H prefix.
    if len(entries) < 2 or entries[-1] or any(not entry.startswith("H ") or len(entry) < 3 for entry in entries[:-1]):
        raise ValueError(f"Supplementary index has hidden or unexpected tracked-file flags; preserved: {project['path']}")
    status = git_value(target, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=matching")
    if patches and phase == "after":
        expected = {" M " + relative for relative in files}
        entries = status.split("\0")
        if (not entries or entries[-1] or set(entries[:-1]) != expected
                or len(entries) - 1 != len(expected)):
            raise ValueError(f"Supplementary modifications differ from the exact unstaged patch closure; preserved: {project['path']}")
    elif status:
        raise ValueError(f"Supplementary source has local, ignored or mode changes; preserved: {project['path']}")
    if patches:
        source = target.parents[len(PurePosixPath(project["path"]).parts) - 1]
        if source / project["path"] != target:
            raise ValueError("Patched supplementary checkout is outside its declared source path")
        twrp_patch_state.verify_patch_files(source, reviewed, phase, require_head_preimage=phase == "before")
    return {**project, "actual_head": head, "actual_origin": origin, "root": str(root),
            "git_dir": str(git_dir), "clean": not (patches and phase == "after"),
            "mode_changes_checked": True, "ignored_files_checked": True,
            **({"patch_phase": phase, "patch_ids": [entry["id"] for entry in patches],
                "exact_patch_state_verified": True} if patches else {})}


def verify(control_root, source_dir, paths=None, patches=(), phase="before", previous_control_root=None):
    """Verify additions; the caller build runner separately validates base patches."""
    context = base_context(control_root, source_dir, paths)
    if context is None:
        return None
    patches = list(patches)
    if previous_control_root is not None:
        if patches or phase != "before":
            raise ValueError("Choose either a prepared previous bundle or an explicit internal patch phase")
        active = active_patch_context(control_root, previous_control_root, context)
        patches, phase = active["controls"]["patches"], "after"
    reviewed = context["reviewed"]
    twrp_patch_state.validate_patch_bases(context["frozen"], {
        "patches": list(patches), "supplementary_projects": reviewed})
    projects = [verify_project(project, context["source"] / project["path"],
                               patches=[entry for entry in patches if entry["project"] == project["path"]],
                               phase=phase) for project in reviewed["projects"]]
    return {"configuration_sha256": reviewed["configuration_sha256"], "base": reviewed["base"],
            "base_worktrees_checked": False, "projects": projects, "verified": True,
            "note": "The caller must also verify the base project worktrees and exact reviewed patch closure."}


def active_patch_context(control_root, previous_control_root, context, base_report=None):
    """Authorize only the queue in the active receipt, never a proposed queue.

    Both bundles and the entire prepared source state are verified read-only.
    Fetch holds the common writer lock around this check and source publication.
    The direct verify action makes no mutation and provides a point-in-time check.
    """
    previous_root = twrp_workspace.absolute_path(previous_control_root)
    root = twrp_workspace.absolute_path(control_root)
    config, paths = context["config"], context["paths"]
    if any(twrp_workspace.overlap(previous_root, path) for path in paths.values()):
        raise ValueError("Previous control bundle must be separate from source, output and reports")
    previous_config = twrp_workspace.load_config(previous_root / "config/twrp.json")
    if previous_config != config or twrp_workspace.load_config(root / "config/twrp.json") != config:
        raise ValueError("Prepared supplementary verification requires unchanged base source configuration")
    previous = twrp_patch_state.control_inventory(previous_config, previous_root, descriptor(previous_root))
    current = twrp_patch_state.control_inventory(config, root, descriptor(root))
    if current.get("supplementary_projects") != context["reviewed"]:
        raise ValueError("Supplementary source controls changed during verification")
    twrp_patch_state.validate_patch_extension(previous, current)
    twrp_patch_state.validate_supplementary_extension(previous, current)
    twrp_patch_state.validate_patch_bases(context["frozen"], current)
    if set(previous["target_files"]) != set(current["target_files"]):
        raise ValueError("Prepared source extension cannot change the controlled target file set")
    state_path = twrp_workspace.checked_report(paths["report_dir"] / twrp_patch_state.STATE)
    state_bytes = state_path.read_bytes()
    state = twrp_patch_state.read_state(config, paths, previous, raw=state_bytes)
    source = twrp_patch_state.verify_sources(config, paths, previous, prepared=True,
                                             frozen=context["frozen"], report=base_report)
    if state.get("source") != source:
        raise ValueError("Prepared source snapshot differs from the active receipt")
    old_supplementary = previous.get("supplementary_projects")
    for project in old_supplementary["projects"] if old_supplementary is not None else ():
        verify_project(project, context["source"] / project["path"],
                       patches=[entry for entry in previous["patches"] if entry["project"] == project["path"]],
                       phase="after")
    twrp_patch_state.verify_target(context["source"], previous["target_files"])
    twrp_patch_state.verify_output(paths)
    if (twrp_patch_state.control_inventory(config, root, descriptor(root)) != current
            or twrp_patch_state.control_inventory(previous_config, previous_root, descriptor(previous_root)) != previous):
        raise ValueError("A control bundle changed during supplementary verification")
    if twrp_workspace.checked_report(state_path).read_bytes() != state_bytes:
        raise ValueError("Prepared receipt changed during supplementary verification")
    return {"controls": previous, "current_controls": current,
            "previous_control_root": str(previous_root), "source": source,
            "build_state_sha256": hashlib.sha256(state_bytes).hexdigest()}


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


def fetch_project(project, source, patches=(), phase="before"):
    target = twrp_workspace.absolute_path(source / project["path"])
    if target.exists() or target.is_symlink():
        return verify_project(project, target, patches=patches, phase=phase)
    if patches:
        raise ValueError("Prepared supplementary checkout is missing; fetch will not recreate or patch it")
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


def fetch(control_root, source_dir, host_mode, paths=None, previous_control_root=None):
    config = twrp_workspace.load_config(Path(control_root) / "config/twrp.json")
    selected = paths or twrp_workspace.paths_for(config, source=source_dir)
    host = twrp_workspace.require_host(config, selected, host_mode)
    with operation_lock(selected):
        return _fetch_locked(control_root, source_dir, host, selected, previous_control_root)


def _fetch_locked(control_root, source_dir, host, selected, previous_control_root=None):
    context = base_context(control_root, source_dir, selected)
    if context is None:
        raise ValueError("No reviewed supplementary source configuration in this control bundle")
    base = twrp_workspace.project_report(context["source"], context["frozen"])
    failures = [f"{project['path']}: {error}" for project in base["projects"]
                for error in project["errors"] if error != "Local changes preserved"]
    if not base["all_present"] or len(base["projects"]) != len(context["frozen"]) or failures:
        raise ValueError("Base project HEAD/origin verification failed: " + "; ".join(failures))
    active = (active_patch_context(control_root, previous_control_root, context, base_report=base)
              if previous_control_root is not None else None)
    patches = active["controls"]["patches"] if active is not None else []
    phase = "after" if active is not None else "before"
    selected_patches = {project["path"]: [entry for entry in patches if entry["project"] == project["path"]]
                        for project in context["reviewed"]["projects"]}
    # Reject unexpected changes in any existing addition before a network or
    # publication operation. Missing new additions have no patch authorization.
    for project in context["reviewed"]["projects"]:
        target = context["source"] / project["path"]
        if target.exists() or target.is_symlink():
            verify_project(project, target, patches=selected_patches[project["path"]], phase=phase)
    projects = [fetch_project(project, context["source"], patches=selected_patches[project["path"]], phase=phase)
                for project in context["reviewed"]["projects"]]
    if active is not None:
        after = active_patch_context(control_root, previous_control_root, context)
        if after != active:
            raise ValueError("Prepared source authorization changed during supplementary fetch")
        projects = [verify_project(project, context["source"] / project["path"],
                                   patches=selected_patches[project["path"]], phase=phase)
                    for project in context["reviewed"]["projects"]]
    report = {"schema_version": 1, "configuration_sha256": context["reviewed"]["configuration_sha256"],
              "base": context["reviewed"]["base"], "base_worktrees_checked": True,
              "base_dirty_projects": [{"path": project["path"], "local_changes": project.get("local_changes", "")}
                                      for project in base["projects"] if not project["clean"]],
              "host_preflight": host, "projects": projects, "verified": True, "note": NOTE}
    if active is not None:
        report["prepared_build_state_sha256"] = active["build_state_sha256"]
        report["previous_control_root"] = active["previous_control_root"]
        report["patches_applied"] = False
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
    parser.add_argument("--previous-control-root", type=Path,
                        help="Exact active prepared bundle, required to verify existing supplementary patches")
    parser.add_argument("--host-mode", choices=twrp_workspace.workspace.HOST_MODES, default="native")
    args = parser.parse_args(argv)
    try:
        if args.action == "plan" and args.previous_control_root is not None:
            raise ValueError("Previous prepared controls are only used by fetch or verify")
        reviewed = descriptor(args.control_root)
        source = args.source_dir or (Path(reviewed["base"]["source_dir"]) if reviewed else None)
        if args.action == "plan":
            report = plan(args.control_root, source)
        elif args.action == "fetch":
            report = fetch(args.control_root, source, args.host_mode,
                           previous_control_root=args.previous_control_root)
        else:
            report = verify(args.control_root, source, previous_control_root=args.previous_control_root)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
