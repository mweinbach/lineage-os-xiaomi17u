#!/usr/bin/env python3
"""Run controlled source operations inside the persistent Apple Container VM."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile


CONTROL_FILES = (
    "config/sources.json", "config/apple-container.json",
    "scripts/workspace.py", "scripts/container_task.py",
)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def bundle_digest(files, repo_commit):
    payload = json.dumps({"files": files, "repo_commit": repo_commit}, sort_keys=True).encode()
    return hashlib.sha256(payload).hexdigest()


def bundle_path(root, relative):
    """Control inputs may not escape via either a file or parent symlink."""
    relative = Path(relative)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise ValueError("Unsafe control bundle path")
    candidate = root
    if root.is_symlink():
        raise ValueError("Control bundle must not be a symlink")
    for component in relative.parts:
        candidate = candidate / component
        if candidate.is_symlink():
            raise ValueError(f"Symlink in control bundle path: {relative}")
    return candidate


def bundle_repo(path, record):
    config = json.loads(bundle_path(path, "config/sources.json").read_text())
    references = [reference for reference in config["references"] if reference.get("name") == "repo-tool"]
    if len(references) != 1 or references[0].get("commit") != record["repo_commit"]:
        raise ValueError("Control bundle Repo pin disagrees with its source configuration")
    relative = references[0]["path"]
    if Path(relative).parts[:1] != (".tools",):
        raise ValueError("Control bundle Repo checkout must be under .tools")
    bundle_path(path, relative)
    return relative


def verify_bundle(path, expected_id):
    record = json.loads(bundle_path(path, "bundle.json").read_text())
    if record.get("schema_version") != 1 or set(record["files"]) != set(CONTROL_FILES):
        raise ValueError("Unexpected control bundle contents")
    if (not re.fullmatch(r"[0-9a-f]{40}", record["repo_commit"])
            or bundle_digest(record["files"], record["repo_commit"]) != expected_id):
        raise ValueError("Control bundle identity mismatch")
    for relative, expected in record["files"].items():
        file = bundle_path(path, relative)
        if file.is_symlink() or not file.is_file() or sha256(file) != expected:
            raise ValueError(f"Control file changed: {relative}")
    bundle_repo(path, record)
    return record


def prepare_control(source, volume, control_id):
    if not re.fullmatch(r"[0-9a-f]{64}", control_id):
        raise ValueError("Invalid control bundle ID")
    record = verify_bundle(source, control_id)
    repo_relative = bundle_repo(source, record)
    parent = volume / "control"
    if parent.is_symlink():
        raise ValueError("Control directory must not be a symlink")
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / control_id
    if target.is_symlink():
        raise ValueError("Existing control snapshot must not be a symlink")
    if not target.exists():
        with tempfile.TemporaryDirectory(prefix=".control-", dir=parent) as temporary:
            staging = Path(temporary) / "snapshot"
            # Copy only the reviewed control allowlist and its pinned Repo
            # checkout, never unrelated extras placed beside a cached bundle.
            staging.mkdir()
            for relative in (*CONTROL_FILES, "bundle.json"):
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(bundle_path(source, relative), destination)
            destination = staging / repo_relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(bundle_path(source, repo_relative), destination, symlinks=True)
            verify_bundle(staging, control_id)
            staging.rename(target)
    verify_bundle(target, control_id)
    return target


def workspace_command(control, operation, source_dir, jobs=8):
    command = [sys.executable, str(control / "scripts/workspace.py"), operation,
               "--source-dir", str(source_dir), "--host-mode", "apple-rosetta"]
    if operation == "sync":
        command += ["--jobs", str(jobs)]
    elif operation == "doctor":
        command += ["--require-build-host"]
    return command


def smoke(control, source_dir, volume):
    subprocess.run(workspace_command(control, "doctor", source_dir), check=True)
    with tempfile.TemporaryDirectory(prefix=".evolution-smoke-", dir=volume) as directory:
        path = Path(directory)
        code = path / "probe.c"
        code.write_text('#include <stdio.h>\nint main(void) { puts("evolution-cross-compile-ok"); return 0; }\n')
        executable = path / "probe-x86_64"
        subprocess.run(["x86_64-linux-gnu-gcc", str(code), "-o", str(executable)], check=True)
        result = subprocess.run([str(executable)], text=True, capture_output=True, check=True)
        if result.stdout != "evolution-cross-compile-ok\n":
            raise ValueError("The compiled x86_64 program did not execute correctly")
        (path / "Case").write_text("upper")
        (path / "case").write_text("lower")
        if (path / "Case").read_text() != "upper":
            raise ValueError("Source volume is not case-sensitive")
        filesystem = subprocess.run(["stat", "-f", "-c", "%T", str(volume)],
                                    text=True, capture_output=True, check=True).stdout.strip()
        if filesystem not in {"ext2/ext3", "ext4"}:
            raise ValueError(f"Expected the Linux ext4 named volume, got {filesystem}")
    persistence = volume / "evolution-persistence-check.json"
    reused = persistence.exists()
    if reused:
        record = json.loads(persistence.read_text())
        if record.get("project") != "evonezha":
            raise ValueError("Unexpected persistence marker")
    else:
        persistence.write_text(json.dumps({"project": "evonezha", "created_at": datetime.now(timezone.utc).isoformat()}) + "\n")
    print(json.dumps({"smoke": "passed", "x86_64_compile_and_execution": True,
                      "case_sensitive_volume": True, "filesystem": filesystem,
                      "persisted_from_previous_run": reused,
                      "android_build_tested": False}, indent=2))


def inventory(source_dir):
    project_list = source_dir / ".repo/project.list"
    available = project_list.is_file() and not project_list.is_symlink()
    projects = project_list.read_text().splitlines() if available else []
    projects = [name for name in projects if name and not Path(name).is_absolute() and ".." not in Path(name).parts]
    checked_out = [name for name in projects if (source_dir / name / ".git").exists()]
    prepared = 0
    for _, directories, _ in os.walk(source_dir / ".repo/project-objects", followlinks=False):
        repositories = [name for name in directories if name.endswith(".git")]
        prepared += len(repositories)
        directories[:] = [name for name in directories if name not in repositories]
    print(json.dumps({"source_dir": str(source_dir), "manifest_initialized": (source_dir / ".repo/manifests").is_dir(),
                      "project_list_pending": not available,
                      "listed_projects": len(projects) if available else None,
                      "checked_out_projects": len(checked_out) if available else None,
                      "prepared_object_git_dirs": prepared,
                      "progress_note": "Prepared Git directories do not prove completed downloads; project.list may be absent during the network phase.",
                      "free_gib": round(shutil.disk_usage(source_dir.parent).free / 1024 ** 3, 1)}, indent=2))


def emit_result(args, exit_code):
    print("EVOLUTION_TASK_RESULT=" + json.dumps({"operation": args.operation,
          "control_id": args.control_id, "exit_code": exit_code,
          "status": "complete" if exit_code == 0 else "failed",
          "completed_at": datetime.now(timezone.utc).isoformat()}), flush=True)


def run_workspace(command):
    """Forward cancellation to the whole Repo/Git process group in the guest."""
    process = subprocess.Popen(command, start_new_session=True, stdin=subprocess.DEVNULL, shell=False)
    previous = {number: signal.getsignal(number) for number in (signal.SIGINT, signal.SIGTERM)}
    def forward(number, _frame):
        try:
            os.killpg(process.pid, number)
        except ProcessLookupError:
            pass
    for number in previous:
        signal.signal(number, forward)
    try:
        result = process.wait()
        return result if result >= 0 else 128 - result
    finally:
        for number, handler in previous.items():
            signal.signal(number, handler)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--control-id", required=True)
    parser.add_argument("operation", choices=["doctor", "init", "sync", "smoke", "shell", "inventory"])
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.jobs <= 64:
            raise ValueError("Jobs must be between 1 and 64")
        volume = Path("/work")
        if not re.fullmatch(r"[0-9a-f]{64}", args.control_id):
            raise ValueError("Invalid control bundle ID")
        if args.operation == "inventory":
            # Status inspection is read-only: do not copy a snapshot, create
            # cache/output/temp directories, or run the workspace preflight.
            control = Path("/control")
            verify_bundle(control, args.control_id)
        else:
            control = prepare_control(Path("/control"), volume, args.control_id)
        config = json.loads((control / "config/apple-container.json").read_text())
        for key in ("source_dir", "out_dir", "cache_dir"):
            path = Path(config[key])
            if not path.is_absolute() or not path.resolve().is_relative_to(volume) or path == volume:
                raise ValueError(f"Unsafe container {key}")
            if key != "source_dir" and args.operation != "inventory":
                path.mkdir(parents=True, exist_ok=True)
        if args.operation == "inventory":
            inventory(Path(config["source_dir"]))
            return 0
        (volume / "tmp").mkdir(exist_ok=True)
        os.environ["OUT_DIR"] = config["out_dir"]
        os.environ["CCACHE_DIR"] = str(Path(config["cache_dir"]) / "ccache")
        os.environ["TMPDIR"] = str(volume / "tmp")
        source_dir = Path(config["source_dir"])
        if args.operation == "smoke":
            smoke(control, source_dir, volume)
        elif args.operation == "shell":
            source_dir.mkdir(parents=True, exist_ok=True)
            os.chdir(source_dir)
            print("Persistent source shell. No lunch target or build is selected automatically.", flush=True)
            os.execvp("bash", ["bash"])
        else:
            command = workspace_command(control, args.operation, source_dir, args.jobs)
            exit_code = run_workspace(command)
            emit_result(args, exit_code)
            return exit_code
        emit_result(args, 0)
        return 0
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        if args.operation != "inventory":
            emit_result(args, 2)
        return 2
    except KeyboardInterrupt:
        if args.operation != "inventory":
            emit_result(args, 130)
        return 130


if __name__ == "__main__":
    sys.exit(main())
