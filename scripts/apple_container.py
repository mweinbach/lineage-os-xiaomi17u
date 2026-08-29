#!/usr/bin/env python3
"""Manage this project's Apple Container builder without touching phone data."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

if __package__:
    from . import container_task, workspace
else:
    import container_task
    import workspace


ROOT = Path(__file__).resolve().parents[1]
LOCAL = ROOT / ".tools/apple-container"
STATE = LOCAL / "last-task.json"
CONFIG = ROOT / "config/apple-container.json"
GIB = 1024 ** 3


def load_config(path=CONFIG):
    config = json.loads(path.read_text())
    if config.get("schema_version") != 1 or config.get("host_mode") != "apple-rosetta":
        raise ValueError("Unsupported Apple Container configuration")
    if not re.fullmatch(r"[a-z0-9][a-z0-9./:_-]*", config["image"]):
        raise ValueError("Invalid builder image reference")
    for key in ("volume", "project_label"):
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{1,80}", config[key]):
            raise ValueError(f"Invalid {key}")
    for key, minimum, maximum in (("cpus", 1, 128), ("builder_cpus", 1, 128),
                                  ("memory_gib", 64, 512), ("builder_memory_gib", 2, 64),
                                  ("volume_size_gib", 500, 2048), ("host_reserve_gib", 50, 1024)):
        if type(config[key]) is not int or not minimum <= config[key] <= maximum:
            raise ValueError(f"Invalid {key}")
    for key in ("source_dir", "out_dir", "cache_dir"):
        value = config[key]
        path_value = Path(value)
        if (not re.fullmatch(r"/work/[a-z0-9/_-]+", value) or ".." in path_value.parts
                or path_value == Path("/work")):
            raise ValueError(f"Invalid {key}; use a path below the persistent /work volume")
    return config


def run(command, *, capture=False, check=True):
    if not capture:
        print("+ " + shlex.join(map(str, command)), flush=True)
    return subprocess.run(list(map(str, command)), text=True, capture_output=capture,
                          check=check, shell=False)


def json_command(command):
    value = json.loads(run(command, capture=True).stdout)
    if not isinstance(value, list):
        raise ValueError("Unexpected Apple Container JSON response")
    return value


def require_mac(config, *, check_disk=True):
    if platform.system() != "Darwin" or platform.machine().lower() not in {"arm64", "aarch64"}:
        raise ValueError("Apple Container orchestration runs on Apple silicon macOS")
    if shutil.which("container") is None:
        raise ValueError("Install Apple's signed Container CLI first")
    if check_disk and shutil.disk_usage(ROOT).free < config["host_reserve_gib"] * GIB:
        raise ValueError("Host free space is below the configured reserve; no operation started")


def volume_info(config):
    values = json_command(["container", "volume", "list", "--format", "json"])
    match = [value for value in values if value.get("id") == config["volume"]
             or value.get("configuration", {}).get("name") == config["volume"]]
    if not match:
        return None
    if len(match) != 1:
        raise ValueError("Ambiguous volume identity")
    result = match[0]["configuration"]
    if (result.get("format") != "ext4" or result.get("labels", {}).get("project") != config["project_label"]
            or result.get("sizeInBytes", 0) < config["volume_size_gib"] * GIB):
        raise ValueError("Existing volume does not match this project's ext4 size/ownership labels; preserved unchanged")
    return result


def ensure_volume(config):
    current = volume_info(config)
    if current is not None:
        return current
    if shutil.disk_usage(ROOT).free < (config["volume_size_gib"] + config["host_reserve_gib"]) * GIB:
        raise ValueError("Not enough host space for the volume's full capacity plus reserve; adjust the configuration")
    run(["container", "volume", "create", "--label", f"project={config['project_label']}",
         "--label", "purpose=aosp-source-and-build", "-s", f"{config['volume_size_gib']}G", config["volume"]])
    return volume_info(config)


def active_volume_users(config, volume, containers=None):
    backing = volume.get("source")
    if not isinstance(backing, str) or not Path(backing).is_absolute():
        raise ValueError("Cannot verify the persistent volume's backing-file identity")
    backing = Path(backing).resolve()
    users = []
    if containers is None:
        containers = json_command(["container", "list", "--all", "--format", "json"])
    for item in containers:
        if item.get("status", {}).get("state") == "stopped":
            continue
        settings = item.get("configuration", {})
        # Apple Container 1.0 represents BuildKit's memory-backed /run as an
        # enum-shaped tmpfs mount with an empty source. It cannot attach an
        # ext4 backing file. Continue to reject every other unknown identity.
        sources = [mount.get("source") for mount in settings.get("mounts", [])
                   if not (mount.get("type") == {"tmpfs": {}} and mount.get("source") == "")]
        if any(not isinstance(source, str) or not source for source in sources):
            raise ValueError("Cannot interpret an active container mount; refusing a second volume attachment")
        if (config["volume"] in sources
                or any(Path(source).is_absolute() and Path(source).resolve() == backing for source in sources)):
            users.append(item)
    return users


def write_state(record):
    """Publish one complete state record so concurrent status reads are safe."""
    STATE.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".task-", dir=STATE.parent, delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(record, stream, indent=2)
        stream.write("\n")
    try:
        temporary.replace(STATE)
    finally:
        temporary.unlink(missing_ok=True)


def task_result(logs, record):
    """Read an explicit guest result; a successful detached launch is not one."""
    for line in reversed(logs.splitlines()):
        if not line.startswith("EVOLUTION_TASK_RESULT="):
            continue
        try:
            result = json.loads(line.partition("=")[2])
        except json.JSONDecodeError:
            continue
        if (not isinstance(result, dict) or result.get("operation") != record["operation"]
                or type(result.get("exit_code")) is not int
                or result.get("control_id", record["control_id"]) != record["control_id"]
                or result.get("status") != ("complete" if result["exit_code"] == 0 else "failed")):
            continue
        return result
    return None


@contextmanager
def operation_lock():
    LOCAL.mkdir(parents=True, exist_ok=True)
    with (LOCAL / "operation.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("Another Apple Container workspace operation is active") from error
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def build_command(config):
    return ["container", "build", "--platform", "linux/arm64", "--cpus", str(config["builder_cpus"]),
            "--memory", f"{config['builder_memory_gib']}G", "--progress", "plain", "--tag", config["image"],
            "--file", str(ROOT / "containers/apple/Containerfile"), str(ROOT / "containers/apple")]


def source_lock_path(source_lock):
    if source_lock is None:
        return None
    lock = workspace.load_source_lock(workspace.load_config(), source_lock, root=ROOT)
    if (lock["descriptor"] != container_task.SOURCE_LOCK_FILES[0]
            or lock["record"]["snapshot"]["path"] != container_task.SOURCE_LOCK_FILES[1]):
        raise ValueError("Apple Container requires the reviewed config/evolution-source-lock.json source lock")
    return lock["descriptor"]


def prepare_bundle(source_lock=None):
    source_config = workspace.load_config()
    tool = workspace.reference_named(source_config, "repo-tool")
    workspace.verify_reference(tool)
    selected_lock = source_lock_path(source_lock)
    control_files = container_task.CONTROL_FILES + (container_task.SOURCE_LOCK_FILES if selected_lock else ())
    files = {}
    for name in control_files:
        path = container_task.bundle_path(ROOT, name)
        if not path.is_file():
            raise ValueError(f"Missing regular control file: {name}")
        files[name] = container_task.sha256(path)
    identity = container_task.bundle_digest(files, tool["commit"])
    parent = LOCAL / "bundles"
    parent.mkdir(parents=True, exist_ok=True)
    target = parent / identity
    if target.exists():
        container_task.verify_bundle(target, identity)
        workspace.verify_reference(tool, target)
        return target, identity
    with tempfile.TemporaryDirectory(prefix=".bundle-", dir=parent) as directory:
        staging = Path(directory)
        for relative in control_files:
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(container_task.bundle_path(ROOT, relative), destination)
        repository = staging / tool["path"]
        repository.parent.mkdir(parents=True, exist_ok=True)
        # A fresh local clone excludes untracked/private files and does not
        # share mutable Git metadata or host hooks with the original checkout.
        workspace.run(["git", "-c", "init.templateDir=", "clone", "--no-hardlinks", "--no-checkout",
                       str(ROOT / tool["path"]), repository])
        workspace.run(["git", "-C", repository, "remote", "set-url", "origin", tool["url"]])
        workspace.run(["git", "-C", repository, "checkout", "--detach", tool["commit"]])
        workspace.verify_reference(tool, staging)
        (staging / "bundle.json").write_text(json.dumps({"schema_version": 1, "files": files,
                                                        "repo_commit": tool["commit"]}, indent=2) + "\n")
        container_task.verify_bundle(staging, identity)
        staging.rename(target)
    return target, identity


def task_command(config, operation, bundle, identity, name, jobs=8, detach=False, source_lock=None):
    if "," in str(bundle):
        raise ValueError("Apple Container mount paths cannot contain commas")
    command = ["container", "run", "--name", name, "--arch", "arm64", "--rosetta",
               "--cpus", str(config["cpus"]), "--memory", f"{config['memory_gib']}G",
               "--label", f"project={config['project_label']}",
               "--label", f"evolution.operation={operation}",
               "--mount", f"type=volume,source={config['volume']},target=/work",
               "--mount", f"type=bind,source={bundle},target=/control,readonly",
               "--workdir", "/work", "--env", f"OUT_DIR={config['out_dir']}",
               "--env", f"CCACHE_DIR={config['cache_dir']}/ccache"]
    if detach:
        command += ["--detach"]
    else:
        command += ["--rm"]
    if operation == "shell":
        command += ["--interactive", "--tty"]
    command += [config["image"], "python3", "/control/scripts/container_task.py",
                "--control-id", identity, operation, "--jobs", str(jobs)]
    if source_lock is not None:
        if operation not in {"init", "sync"} or source_lock != container_task.SOURCE_LOCK_FILES[0]:
            raise ValueError("Only init/sync may use the reviewed bundled source lock")
        command += ["--source-lock", source_lock]
    return command


def image_info(config):
    images = json_command(["container", "image", "inspect", config["image"]])
    if len(images) != 1:
        raise ValueError("Builder image is unavailable or ambiguous; run setup")
    return images[0]["configuration"]["descriptor"]["digest"]


def execute_task(config, operation, jobs=8, detach=False, source_lock=None):
    volume = volume_info(config)
    if volume is None:
        raise ValueError("Persistent volume missing; run setup")
    active = active_volume_users(config, volume)
    if active:
        names = ", ".join(item["id"] for item in active)
        raise ValueError(f"Volume is already attached to an active VM ({names}); use status or exec in that VM")
    if operation == "shell" and not sys.stdin.isatty():
        raise ValueError("Run shell from an interactive terminal")
    digest = image_info(config)
    selected_lock = source_lock_path(source_lock)
    bundle, identity = prepare_bundle(selected_lock)
    # Bundle preparation can take time. Recheck just before launch so an
    # externally started VM is not missed by the earlier inspection.
    if active_volume_users(config, volume):
        raise ValueError("Volume became active during bundle preparation; no second container was launched")
    name = "evolution-nezha-" + operation + "-" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    command = task_command(config, operation, bundle, identity, name, jobs, detach, selected_lock)
    record = {"container": name, "operation": operation, "control_id": identity,
              "image": config["image"], "image_digest": digest, "volume": config["volume"],
              "detached": detach, "lifecycle": "launching", "started_at": datetime.now(timezone.utc).isoformat()}
    if selected_lock:
        record["source_lock"] = selected_lock
    write_state(record)
    try:
        result = run(command, check=False)
    except (OSError, subprocess.SubprocessError, KeyboardInterrupt) as error:
        record["lifecycle"] = "client_interrupted" if isinstance(error, KeyboardInterrupt) else "launch_failed"
        record["client_error"] = str(error)
        write_state(record)
        raise
    record["launch_exit_code" if detach else "exit_code"] = result.returncode
    record["lifecycle"] = ("launch_failed" if detach else "failed") if result.returncode else ("launched" if detach else "complete")
    if not detach or result.returncode:
        record["completed_at"] = datetime.now(timezone.utc).isoformat()
    write_state(record)
    if result.returncode:
        raise ValueError(f"Container task returned {result.returncode}; source volume was preserved")
    if detach:
        print(f"Started {name}. Inspect with: python3 scripts/apple_container.py status")


def status(config):
    run(["container", "system", "status"])
    volume = volume_info(config)
    if volume is None:
        print("Project volume has not been created.")
        return
    print(json.dumps({"volume": config["volume"], "format": volume["format"],
                      "capacity_gib": volume["sizeInBytes"] / GIB}, indent=2))
    containers = json_command(["container", "list", "--all", "--format", "json"])
    active = active_volume_users(config, volume, containers)
    print(json.dumps({"active_volume_users": [
        {"container": item["id"], "state": item.get("status", {}).get("state", "unknown")}
        for item in active
    ], "status_note": "Live volume attachments are independent of the historical last-task receipt."}, indent=2))
    if not STATE.exists():
        print("No last-task receipt is available in this checkout.")
        if active:
            print("Active volume users were not adopted; inspect the existing VM without starting another writer.")
        return
    record = json.loads(STATE.read_text())
    if record.get("volume") != config["volume"]:
        raise ValueError("Recorded task belongs to a different volume; state was preserved")
    active_ids = {item["id"] for item in active}
    if active_ids - {record["container"]}:
        print("Active volume users differ from the last recorded task; its receipt was preserved unchanged.")
    record = {**record, "record_kind": "last_recorded_task",
              "active_volume_user": record["container"] in active_ids}
    matches = [item for item in containers if item["id"] == record["container"]]
    if not matches:
        known_exit = record.get("exit_code")
        known_foreground = not record.get("detached") and type(known_exit) is int
        completion = ("complete" if known_exit == 0 else "failed") if known_foreground else "unknown"
        if record.get("lifecycle") == "launch_failed" or record.get("launch_exit_code", 0):
            completion = "launch_failed"
        print(json.dumps({**record, "state": "removed" if known_foreground else "missing",
                          "task_status": completion}, indent=2))
        return
    state = matches[0].get("status", {}).get("state", "unknown")
    logs = run(["container", "logs", "-n", "40", record["container"]], capture=True, check=False)
    outcome = task_result(logs.stdout, record) if logs.returncode == 0 else None
    print(json.dumps({**record, "state": state,
                      "task_status": outcome["status"] if outcome else (state if state != "stopped" else "unknown"),
                      "guest_result": outcome, "logs_available": logs.returncode == 0}, indent=2))
    if state == "running" and record["active_volume_user"]:
        run(["container", "exec", record["container"], "python3", "/control/scripts/container_task.py",
             "--control-id", record["control_id"], "inventory"])
    if logs.stdout:
        print(logs.stdout, end="" if logs.stdout.endswith("\n") else "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["setup", "build-image", "doctor", "smoke", "init", "sync", "shell", "status"])
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--detach", action="store_true", help="Keep a named sync container and return immediately")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source-lock", help="Use the reviewed config/evolution-source-lock.json for init/sync")
    args = parser.parse_args(argv)
    try:
        config = load_config()
        if not 1 <= args.jobs <= 64 or (args.detach and args.operation != "sync"):
            raise ValueError("Jobs must be 1-64; --detach is only supported for sync")
        if args.source_lock is not None and args.operation not in {"init", "sync"}:
            raise ValueError("--source-lock is only supported for init/sync")
        selected_lock = source_lock_path(args.source_lock)
        if args.dry_run:
            if args.operation in {"setup", "build-image"}:
                print(shlex.join(build_command(config)))
            if args.operation != "build-image":
                operation = "smoke" if args.operation == "setup" else args.operation
                if operation != "status":
                    print(shlex.join(task_command(config, operation, LOCAL / "bundles/PREVIEW", "0" * 64,
                                                  "evolution-nezha-preview", args.jobs, args.detach, selected_lock)))
            print("Preview only: no services, VMs, images, volumes, or source files changed.")
            return 0
        require_mac(config, check_disk=args.operation != "status")
        if args.operation == "status":
            status(config)
            return 0
        with operation_lock():
            if args.operation in {"setup", "build-image"}:
                run(["container", "system", "start"])
                if args.operation == "setup":
                    ensure_volume(config)
                run(build_command(config))
                image_info(config)
                if args.operation == "build-image":
                    return 0
                execute_task(config, "smoke", args.jobs)
            else:
                execute_task(config, args.operation, args.jobs, args.detach, selected_lock)
        return 0
    except (ValueError, KeyError, OSError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
