#!/usr/bin/env python3
"""Stage reviewed Nezha TWRP sources and run isolated compile-only checks."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

try:
    from scripts import twrp_workspace, twrp_patch_state
except ModuleNotFoundError:  # Direct execution from a copied control bundle.
    import twrp_workspace
    import twrp_patch_state


ROOT = Path(__file__).resolve().parents[1]
TARGET = twrp_patch_state.TARGET
TARGET_SOURCE = twrp_patch_state.TARGET_SOURCE
SERIES = twrp_patch_state.SERIES
STATE = twrp_patch_state.STATE
OUT_ALIAS = twrp_patch_state.OUT_ALIAS
PRODUCT = twrp_patch_state.PRODUCT
RELEASE = twrp_patch_state.RELEASE
VARIANTS = ("user", "userdebug")
HEX256 = twrp_patch_state.HEX256
SAFE_PATH = twrp_patch_state.SAFE_PATH
SOURCE_SUFFIXES = twrp_patch_state.SOURCE_SUFFIXES
REQUIRED_TARGET = twrp_patch_state.REQUIRED_TARGET
LIMITATION = ("Compile-only recovery experiment. No phone command is run. Kernel, vendor_boot, "
              "modules, display/touch, storage, authenticated ADB and enforcing device behavior "
              "remain separate validation gates; no image is admitted for flashing.")


# Keep the existing public read-only helpers while sharing one implementation
# with the dependency verifier. This does not import any fetch/apply mutators.
sha256 = twrp_patch_state.sha256
relative_path = twrp_patch_state.relative_path
regular_file = twrp_patch_state.regular_file
text_file = twrp_patch_state.text_file
target_inventory = twrp_patch_state.target_inventory
patch_inventory = twrp_patch_state.patch_inventory
validate_supplementary_extension = twrp_patch_state.validate_supplementary_extension
patched_projects = twrp_patch_state.patched_projects
validate_patch_extension = twrp_patch_state.validate_patch_extension
validate_patch_bases = twrp_patch_state.validate_patch_bases
git_blob_sha1 = twrp_patch_state.git_blob_sha1
verify_patch_files = twrp_patch_state.verify_patch_files
verify_sources = twrp_patch_state.verify_sources
verify_target = twrp_patch_state.verify_target
verify_output = twrp_patch_state.verify_output
read_state = twrp_patch_state.read_state


def controls(config, root=ROOT):
    return twrp_patch_state.control_inventory(config, root, supplementary_descriptor(root))


def dependency_module():
    try:
        from scripts import twrp_dependencies
    except ModuleNotFoundError:
        import twrp_dependencies
    return twrp_dependencies


def supplementary_descriptor(root):
    path = root / "config/twrp-dependencies.json"
    if not path.exists() and not path.is_symlink():
        return None
    return dependency_module().descriptor(root)


def verify_supplementary(root, paths, reviewed, source, phase="after", patches=None):
    descriptor = reviewed.get("supplementary_projects")
    if descriptor is None:
        if supplementary_descriptor(root) is not None:
            raise ValueError("Supplementary source controls changed during verification")
        return None
    report = dependency_module().verify(root, paths["source_dir"], paths=paths,
                                        patches=reviewed["patches"] if patches is None else patches,
                                        phase=phase)
    if (report is None or report["configuration_sha256"] != descriptor["configuration_sha256"]
            or any(report["base"].get(key) != value for key, value in source.items())):
        raise ValueError("Supplementary sources do not match the prepared base or reviewed configuration")
    return report


@contextmanager
def operation_lock(paths, action):
    directory = twrp_workspace.absolute_path(paths["report_dir"])
    if not directory.is_dir():
        raise ValueError("Frozen source reports must exist before a build operation")
    path = directory / "build-operation.lock"
    data = (json.dumps({"action": action, "pid": os.getpid(),
                       "started_at": datetime.now(timezone.utc).isoformat()}) + "\n").encode()
    try:
        with path.open("xb") as stream:
            stream.write(data)
            inode = os.fstat(stream.fileno()).st_ino
    except FileExistsError as error:
        raise ValueError("Another or interrupted build operation owns the lock; inspect before retrying: " + str(path)) from error
    try:
        yield
    finally:
        # Never clear a replaced lock or silently recover a stale one. The
        # runner releases only its own exact file after this operation ends.
        if not path.is_symlink() and path.is_file() and path.stat().st_ino == inode and path.read_bytes() == data:
            path.unlink()


def command(action, jobs, *, keep_going=False):
    if type(jobs) is not int or not 1 <= jobs <= 64:
        raise ValueError("Build jobs must be between 1 and 64")
    if action not in {"graph", "build"}:
        raise ValueError("Only graph and dependency-checked recovery compilation are supported")
    if type(keep_going) is not bool:
        raise ValueError("keep_going must be a boolean")
    if keep_going and action != "build":
        raise ValueError("--keep-going is valid only for the build action")
    args = ["bash", "build/soong/soong_ui.bash", "--make-mode", f"-j{jobs}",
            "nothing" if action == "graph" else "recoveryimage"]
    if keep_going:
        args.insert(-1, "-k0")
    return args


def environment(source, output, variant):
    if variant not in VARIANTS:
        raise ValueError("TWRP build variant must be user or userdebug")
    # Build flags, Java options, Git overrides, injected Python paths and shell
    # startup hooks are deliberately not inherited from the caller.
    result = {key: os.environ[key] for key in ("HOME", "USER", "LOGNAME") if key in os.environ}
    result.update({"PATH": str(source / "prebuilts/build-tools/path/linux-x86")
                   + ":/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                   "SHELL": "/bin/bash", "LANG": "C.UTF-8", "LC_ALL": "C.UTF-8",
                   "TMPDIR": str(output / "tmp"), "OUT_DIR": OUT_ALIAS,
                   "OUT": str(output / "target/product/nezha"),
                   "ANDROID_PRODUCT_OUT": str(output / "target/product/nezha"),
                   "GOCACHE": str(output / "cache/go"), "XDG_CACHE_HOME": str(output / "cache/xdg"),
                   "PYTHONDONTWRITEBYTECODE": "1",
                   "TARGET_PRODUCT": PRODUCT, "TARGET_RELEASE": RELEASE,
                   "TARGET_BUILD_VARIANT": variant, "GOTOOLCHAIN": "local", "GOENV": "off",
                   "GOPROXY": "off", "GOSUMDB": "off"})
    return result


def plan(config, paths, host_mode, jobs, variant, root=ROOT):
    reviewed = controls(config, root)
    env = environment(paths["source_dir"], paths["out_dir"], variant)
    report = {**twrp_workspace.identity(config, paths), "action": "plan", "executes_commands": False,
            "writes_files": False, "compile_only": True, "flash_admitted": False,
            "host_mode": host_mode, "target": TARGET, "target_files": reviewed["target_files"],
            "patch_series_sha256": reviewed["series_sha256"],
            "patch_ids": [patch["id"] for patch in reviewed["patches"]],
            "output_alias": str(paths["source_dir"] / OUT_ALIAS),
            "commands": {action: command(action, jobs) for action in ("graph", "build")},
            "build_environment": {key: value for key, value in env.items() if key not in {"HOME", "USER", "LOGNAME"}},
            "note": LIMITATION + " Plan does not probe the host, execute processes or write files."}
    if "supplementary_projects" in reviewed:
        report["supplementary_projects"] = reviewed["supplementary_projects"]
    return report


def check(config, paths, host_mode, root=ROOT, host=None, record=True):
    host = host if host is not None else twrp_workspace.require_host(config, paths, host_mode)
    reviewed = controls(config, root)
    state_path = paths["report_dir"] / STATE
    state_bytes = twrp_workspace.checked_report(state_path).read_bytes()
    state = read_state(config, paths, reviewed, raw=state_bytes)
    source = verify_sources(config, paths, reviewed, prepared=True)
    if state.get("source") != source:
        raise ValueError("Prepared build source snapshot changed")
    supplementary = verify_supplementary(root, paths, reviewed, source)
    verify_target(paths["source_dir"], reviewed["target_files"])
    verify_output(paths)
    if (controls(config, root) != reviewed
            or twrp_workspace.checked_report(state_path).read_bytes() != state_bytes):
        raise ValueError("Prepared receipt or control bundle changed during build verification")
    report = {"compile_only": True, "flash_admitted": False, "prepared_sources_verified": True,
              "build_state_sha256": sha256(state_bytes),
              "host_preflight": host, "source": source, "note": LIMITATION}
    if supplementary is not None:
        report["supplementary_projects"] = supplementary
    return twrp_workspace.record_action(config, paths, "build-check", report) if record else report


def prepare(config, paths, host_mode, root=ROOT):
    host = twrp_workspace.require_host(config, paths, host_mode)
    with operation_lock(paths, "prepare"):
        return prepare_locked(config, paths, host_mode, root, host)


def prepare_locked(config, paths, host_mode, root, host):
    reviewed = controls(config, root)
    state_path = paths["report_dir"] / STATE
    if state_path.exists() or state_path.is_symlink():
        report = check(config, paths, host_mode, root, host=host, record=False)
        return twrp_workspace.record_action(config, paths, "prepare", {**report, "already_prepared": True})
    source = paths["source_dir"]
    source_record = verify_sources(config, paths, reviewed, prepared=False)
    verify_supplementary(root, paths, reviewed, source_record, phase="before")
    target = twrp_workspace.absolute_path(source / TARGET)
    if target.exists():
        raise ValueError("Nezha target already exists without a preparation receipt; changes preserved")
    alias = source / OUT_ALIAS
    if alias.exists() or alias.is_symlink():
        raise ValueError("Output alias already exists without a preparation receipt; changes preserved")
    output = paths["out_dir"]
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory is nonempty without a preparation receipt; files preserved")
    if twrp_patch_state.patch_plan(reviewed)["has_chains"]:
        return prepare_chain(config, paths, root, host, reviewed, source_record)
    for patch in reviewed["patches"]:
        twrp_workspace.run(["git", "-C", source / patch["project"], "apply", "--check",
                            "--whitespace=error-all", "--", root / patch["patch"]])
    state = {**twrp_workspace.identity(config, paths), "controls": reviewed, "source": source_record,
             "target_product": PRODUCT, "target_release": RELEASE, "output_alias": OUT_ALIAS,
             "compile_only": True, "flash_admitted": False, "host_preflight": host,
             "recorded_at": datetime.now(timezone.utc).isoformat(), "note": LIMITATION}
    # This journal remains if a later write/apply fails. There is no reset,
    # forced overwrite, rollback or automatic adoption of a partial prepare.
    twrp_workspace.record_action(config, paths, "prepare-start", state)
    target.mkdir(parents=True, exist_ok=False)
    for relative, identity in reviewed["target_files"].items():
        data = text_file(root / TARGET_SOURCE, relative)
        if sha256(data) != identity["sha256"]:
            raise ValueError("Controlled target changed during preparation")
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("xb") as stream:
            stream.write(data)
        destination.chmod(0o644)
    for patch in reviewed["patches"]:
        if sha256(text_file(root, patch["patch"])) != patch["patch_sha256"]:
            raise ValueError("Controlled patch changed during preparation")
        twrp_workspace.run(["git", "-C", source / patch["project"], "apply", "--whitespace=error-all",
                            "--", root / patch["patch"]])
    verify_patch_files(source, reviewed, "after")
    verify_target(source, reviewed["target_files"])
    output.mkdir(parents=True, exist_ok=True)
    for relative in ("tmp", "cache/go", "cache/xdg"):
        (output / relative).mkdir(parents=True, exist_ok=False)
    alias.symlink_to(output, target_is_directory=True)
    verify_output(paths)
    # Applying patches must not authorize unrelated changes made during the
    # operation. Recheck every owner before publishing the first receipt.
    verified_source = verify_sources(config, paths, reviewed, prepared=True)
    if verified_source != source_record or controls(config, root) != reviewed:
        raise ValueError("Reviewed sources or controls changed during preparation")
    verify_supplementary(root, paths, reviewed, source_record, phase="after")
    verify_target(source, reviewed["target_files"])
    verify_output(paths)
    if state_path.exists() or state_path.is_symlink():
        raise ValueError("Build receipt appeared during preparation; changes preserved")
    twrp_workspace.write_report(paths, STATE, json.dumps(state, indent=2) + "\n")
    return twrp_workspace.record_action(config, paths, "prepare", {
        "already_prepared": False, "compile_only": True, "flash_admitted": False,
        "target_file_count": len(reviewed["target_files"]),
        "patch_ids": [patch["id"] for patch in reviewed["patches"]],
        "source": source_record, "host_preflight": host, "note": LIMITATION})


def require_file_identity(root, relative, expected):
    path = regular_file(root, relative)
    actual = {"sha256": sha256(path.read_bytes()), "size_bytes": path.stat().st_size,
              "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}"}
    if actual != expected:
        raise ValueError(f"File changed during target revision; changes preserved: {relative}")
    return path


def write_new_file(root, relative, data):
    path = twrp_workspace.absolute_path(root / str(relative_path(relative)))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(data)
    path.chmod(0o644)
    return path


def chain_git(directory, home, *args):
    """Run scratch Git without inheriting live indexes, config or attributes."""
    return subprocess.run(["git", "-c", "core.fileMode=true", "-c", "core.autocrlf=false",
                           "-c", "core.fsmonitor=false", "-c", "core.ignoreStat=false",
                           "-c", "core.hooksPath=/dev/null", "-c", "core.attributesFile=/dev/null",
                           "-C", str(directory), *map(str, args)],
                          env=twrp_patch_state.chain_git_environment(home), check=True,
                          capture_output=True, stdin=subprocess.DEVNULL, shell=False, timeout=60)


def rehearse_chain(source, reviewed, root, boundary):
    """Replay and reverse the full queue only in ordinary scratch file copies."""
    plan = twrp_patch_state.patch_plan(reviewed)
    if any(Path(relative).name == ".gitattributes" for owner in plan["projects"].values()
           for relative in owner["files"]):
        # core.attributesFile disables the global file, not per-directory
        # attributes. Never copy one into the scratch proof's worktree.
        raise ValueError("Patch chain rehearsal does not admit Git attribute files")
    initial = twrp_patch_state.verify_chain_boundary(source, reviewed, boundary)
    payloads = [text_file(root, entry["patch"]) for entry in reviewed["patches"]]
    if any(sha256(data) != entry["patch_sha256"] for entry, data in zip(reviewed["patches"], payloads)):
        raise ValueError("Patch controls changed before scratch rehearsal")
    with tempfile.TemporaryDirectory(prefix="twrp-chain-rehearsal-") as temporary:
        scratch = Path(temporary).resolve()
        home, files, payload_dir = scratch / "home", scratch / "files", scratch / "payloads"
        for directory in (home, files, payload_dir):
            directory.mkdir()
        modes = {}
        for project, owner in plan["projects"].items():
            directory = files / project
            directory.mkdir(parents=True)
            chain_git(scratch, home, "init", "--quiet", "--template=" + str(home), directory)
            for relative, chain in owner["files"].items():
                data, mode = twrp_patch_state.pinned_file(source, project, owner["base_commit"], relative, chain["root"])
                destination = directory / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open("xb") as stream:
                    stream.write(data)
                destination.chmod(mode)
                modes[f"{project}/{relative}"] = mode
                if len(chain["steps"]) > 1:
                    for step in chain["steps"]:
                        twrp_patch_state.chain_patch_index(payloads[step["index"]], relative, step["item"], mode)
        archived_payloads = [write_new_file(payload_dir, f"{index:04d}.patch", data)
                             for index, data in enumerate(payloads)]

        def verify_scratch(count):
            actual = {}
            for project, owner in plan["projects"].items():
                directory = files / project
                found = set()
                for candidate in directory.rglob("*"):
                    relative = candidate.relative_to(directory).as_posix()
                    if relative == ".git" or relative.startswith(".git/"):
                        continue
                    if candidate.is_symlink():
                        raise ValueError("Scratch rehearsal produced a symlink")
                    if candidate.is_dir():
                        continue
                    found.add(relative)
                if found != set(owner["files"]):
                    raise ValueError("Scratch rehearsal changed undeclared paths")
                for relative, chain in owner["files"].items():
                    item, phase = twrp_patch_state.boundary_item(chain, count)
                    path = regular_file(directory, relative)
                    expected = {"sha256": item[phase + "_sha256"], "size_bytes": item[phase + "_size_bytes"],
                                "mode": f"{modes[f'{project}/{relative}']:04o}"}
                    require_file_identity(directory, relative, expected)
                    if phase + "_git_blob" in item and git_blob_sha1(path.read_bytes()) != item[phase + "_git_blob"]:
                        raise ValueError("Scratch Git blob differs at explicit boundary")
                    actual[f"{project}/{relative}"] = expected
            if count == boundary and actual != initial:
                raise ValueError("Scratch prefix differs from independently verified live boundary")
            return actual

        verify_scratch(0)
        for index, entry in enumerate(reviewed["patches"]):
            verify_scratch(index)
            directory, payload = files / entry["project"], archived_payloads[index]
            chain_git(directory, home, "apply", "--check", "--whitespace=error-all", "--", payload)
            chain_git(directory, home, "apply", "--whitespace=error-all", "--", payload)
            verify_scratch(index + 1)
        for index in reversed(range(len(reviewed["patches"]))):
            entry = reviewed["patches"][index]
            directory, payload = files / entry["project"], archived_payloads[index]
            verify_scratch(index + 1)
            chain_git(directory, home, "apply", "--reverse", "--check", "--whitespace=error-all", "--", payload)
            chain_git(directory, home, "apply", "--reverse", "--whitespace=error-all", "--", payload)
            verify_scratch(index)
    if twrp_patch_state.verify_chain_boundary(source, reviewed, boundary) != initial:
        raise ValueError("Live source changed during scratch rehearsal")
    return {"initial_boundary": boundary, "final_boundary": len(reviewed["patches"]),
            "initial_files": initial, "forward_and_reverse_verified": True,
            "source_mutated": False, "power_loss_durability_claimed": False}


def verify_live_prefix(config, paths, root, reviewed, boundary, expected_source):
    prefix = {**reviewed, "patches": reviewed["patches"][:boundary]}
    source = verify_sources(config, paths, prefix, prepared=bool(boundary))
    if source != expected_source:
        raise ValueError("Frozen source identity changed during patch chain")
    verify_supplementary(root, paths, reviewed, source,
                         patches=prefix["patches"], phase="after" if boundary else "before")
    return twrp_patch_state.verify_chain_boundary(paths["source_dir"], reviewed, boundary)


def archive_chain(archive, source, reviewed, previous, boundary, rehearsal, state_before):
    """Exclusive process-failure evidence; no claim of fsync/power-loss safety."""
    evidence = {}
    def record(relative, data):
        write_new_file(archive, relative, data)
        evidence[relative] = {"sha256": sha256(data), "size_bytes": len(data), "mode": "0644"}
    record("controls.after.json", (json.dumps(reviewed, indent=2) + "\n").encode())
    record("controls.before.json", (json.dumps(previous, indent=2) + "\n").encode())
    record("chain-plan.json", (json.dumps({"old_boundary": boundary,
                   "old_build_state_sha256": sha256(state_before) if state_before is not None else None,
                   "plan": twrp_patch_state.patch_plan(reviewed), "rehearsal": rehearsal}, indent=2) + "\n").encode())
    for relative, identity in rehearsal["initial_files"].items():
        data = require_file_identity(source, relative, identity).read_bytes()
        record("source-before/" + relative, data)
    return evidence


def verify_chain_archive(archive, evidence):
    for relative, identity in evidence.items():
        require_file_identity(archive, relative, identity)


def apply_chain_steps(config, paths, root, reviewed, previous, previous_root, archive,
                      boundary, rehearsal, state_before, expected_source, payloads, report, evidence):
    """Apply only a rehearsed suffix; failure preserves source and old receipt."""
    state_path = paths["report_dir"] / STATE
    def record(relative, data):
        write_new_file(archive, relative, data)
        evidence[relative] = {"sha256": sha256(data), "size_bytes": len(data), "mode": "0644"}
    def stable():
        if controls(config, root) != reviewed:
            raise ValueError("A control bundle changed during patch chain")
        if previous_root is not None and controls(config, previous_root) != previous:
            raise ValueError("Previous control bundle changed during patch chain")
        if state_before is None:
            if state_path.exists() or state_path.is_symlink():
                raise ValueError("Build receipt appeared during patch chain")
        elif twrp_workspace.checked_report(state_path).read_bytes() != state_before:
            raise ValueError("Active build receipt changed during patch chain")
        for relative, identity in rehearsal["initial_files"].items():
            require_file_identity(archive, "source-before/" + relative, {**identity, "mode": "0644"})
        for name, value in (("controls.before.json", previous), ("controls.after.json", reviewed)):
            data = (json.dumps(value, indent=2) + "\n").encode()
            require_file_identity(archive, name, {"sha256": sha256(data), "size_bytes": len(data), "mode": "0644"})
        if state_before is not None:
            require_file_identity(archive, "build-state.before.json", {
                "sha256": sha256(state_before), "size_bytes": len(state_before), "mode": "0644"})
        verify_chain_archive(archive, evidence)
        for entry, data, relative in payloads:
            require_file_identity(archive, relative, {
                "sha256": entry["patch_sha256"], "size_bytes": len(data), "mode": "0644"})
    stable()
    verify_live_prefix(config, paths, root, reviewed, boundary, expected_source)
    for offset, (entry, data, payload_relative) in enumerate(payloads):
        index = boundary + offset
        stable()
        before = verify_live_prefix(config, paths, root, reviewed, index, expected_source)
        payload = require_file_identity(archive, payload_relative, {
            "sha256": entry["patch_sha256"], "size_bytes": len(data), "mode": "0644"})
        step = f"steps/{index:04d}"
        intent = {"queue_index": index, "patch_id": entry["id"], "patch_sha256": entry["patch_sha256"],
                  "previous_build_state_sha256": sha256(state_before) if state_before is not None else None,
                  "controls_before_sha256": sha256((json.dumps(previous, indent=2) + "\n").encode()),
                  "controls_after_sha256": sha256((json.dumps(reviewed, indent=2) + "\n").encode()),
                  "files": entry["files"], "before": before, "status": "attempted-not-yet-verified",
                  "power_loss_durability_claimed": False}
        record(step + "/intent.json", (json.dumps(intent, indent=2) + "\n").encode())
        # Detect even an intercepted archive write before touching the source.
        stable()
        verify_live_prefix(config, paths, root, reviewed, index, expected_source)
        report["attempted_patch_ids"].append(entry["id"])
        # Only this forward call touches live source; scratch reverse is never
        # reused as a rollback or inferred partial-transition repair.
        twrp_workspace.run(["git", "-C", paths["source_dir"] / entry["project"], "apply",
                            "--whitespace=error-all", "--", payload])
        after = verify_live_prefix(config, paths, root, reviewed, index + 1, expected_source)
        stable()
        for item in entry["files"]:
            relative = f"{entry['project']}/{item['path']}"
            data = require_file_identity(paths["source_dir"], relative, after[relative]).read_bytes()
            record(step + "/source-after/" + relative, data)
        record(step + "/complete.json", (json.dumps({**intent, "status": "verified",
               "after": after}, indent=2) + "\n").encode())
        stable()
        report["applied_patch_ids"].append(entry["id"])


def prepare_chain(config, paths, root, host, reviewed, source_record):
    rehearsal = rehearse_chain(paths["source_dir"], reviewed, root, 0)
    now = datetime.now(timezone.utc)
    revision = now.strftime("%Y%m%dT%H%M%S%fZ")
    archive = twrp_workspace.absolute_path(paths["report_dir"] / "build-preparations" / revision)
    archive.mkdir(parents=True, exist_ok=False)
    evidence = archive_chain(archive, paths["source_dir"], reviewed, None, 0, rehearsal, None)
    payloads = [(entry, text_file(root, entry["patch"]), f"patches/{index:04d}.patch")
                for index, entry in enumerate(reviewed["patches"])]
    for _, data, relative in payloads:
        write_new_file(archive, relative, data)
        evidence[relative] = {"sha256": sha256(data), "size_bytes": len(data), "mode": "0644"}
    report = {"compile_only": True, "flash_admitted": False, "already_prepared": False,
              "preparation_archive": str(archive), "source": source_record,
              "attempted_patch_ids": [], "applied_patch_ids": [], "note": LIMITATION}
    twrp_workspace.record_action(config, paths, "prepare-start", report)
    try:
        apply_chain_steps(config, paths, root, reviewed, None, None, archive, 0, rehearsal,
                          None, source_record, payloads, report, evidence)
        target = paths["source_dir"] / TARGET
        target.mkdir(parents=True, exist_ok=False)
        for relative, identity in reviewed["target_files"].items():
            data = text_file(root / TARGET_SOURCE, relative)
            if sha256(data) != identity["sha256"]:
                raise ValueError("Controlled target changed during preparation")
            write_new_file(target, relative, data)
        output = paths["out_dir"]
        output.mkdir(parents=True, exist_ok=True)
        for relative in ("tmp", "cache/go", "cache/xdg"):
            (output / relative).mkdir(parents=True, exist_ok=False)
        (paths["source_dir"] / OUT_ALIAS).symlink_to(output, target_is_directory=True)
        verify_live_prefix(config, paths, root, reviewed, len(reviewed["patches"]), source_record)
        verify_target(paths["source_dir"], reviewed["target_files"])
        verify_output(paths)
        if controls(config, root) != reviewed:
            raise ValueError("Controlled sources changed before preparation receipt")
        verify_chain_archive(archive, evidence)
        state = {**twrp_workspace.identity(config, paths), "controls": reviewed, "source": source_record,
                 "target_product": PRODUCT, "target_release": RELEASE, "output_alias": OUT_ALIAS,
                 "compile_only": True, "flash_admitted": False, "host_preflight": host,
                 "recorded_at": now.isoformat(), "preparation_archive": str(archive), "note": LIMITATION}
        # Deliberately retain the existing exclusive first-receipt contract.
        # Atomic no-replace/fsync publication is independent hardening.
        twrp_workspace.write_report(paths, STATE, json.dumps(state, indent=2) + "\n")
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        twrp_workspace.record_action(config, paths, "prepare-failed", {**report, "error": str(error)})
        raise
    return twrp_workspace.record_action(config, paths, "prepare", report)


def replace_target_file(target, relative, expected, data, revision):
    path = require_file_identity(target, relative, expected)
    temporary = path.with_name(f".{path.name}.twrp-revise-{revision}.tmp")
    write_new_file(target, temporary.relative_to(target).as_posix(), data)
    # Verify again immediately before replacement. Only a file matching the
    # old receipt can be replaced, and its exact bytes are already archived.
    require_file_identity(target, relative, expected)
    os.replace(temporary, path)


def reviewed_target_additions(previous, reviewed, allowed):
    if not isinstance(allowed, (tuple, list)):
        raise ValueError("Target additions require an explicit list of root-level file names")
    names = []
    for name in allowed:
        relative = relative_path(name)
        if len(relative.parts) != 1 or relative.as_posix() != name or name in names:
            raise ValueError("Target additions require unique canonical root-level file names")
        names.append(name)
    old, new = set(previous["target_files"]), set(reviewed["target_files"])
    added = sorted(new - old)
    if old - new or (added and not names):
        raise ValueError("Target revision requires the same file set; additions and removals need separate review")
    if set(names) != set(added):
        raise ValueError("Allowed target additions must exactly match the new control file set")
    return added


@contextmanager
def target_directory(target, expected=None):
    """Hold an existing target directory without following any ancestor link."""
    target = Path(target)
    # Validate, but retain the lexical path for the descriptor walk: resolving
    # a concurrently inserted ancestor link must not redirect the operation.
    twrp_workspace.absolute_path(target)
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
    descriptor = os.open(target.anchor, flags)
    try:
        for part in target.parts[1:]:
            child = os.open(part, flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        info = os.fstat(descriptor)
        identity = {"device": info.st_dev, "inode": info.st_ino}
        if expected is not None and identity != expected:
            raise ValueError("Target directory changed during addition; changes preserved")
        yield descriptor, identity
    finally:
        os.close(descriptor)


def require_absent_target_name(descriptor, relative):
    try:
        os.stat(relative, dir_fd=descriptor, follow_symlinks=False)
    except OSError as error:
        if error.errno != errno.ENOENT:
            raise
    else:
        raise ValueError(f"Target addition already exists; changes preserved: {relative}")


def require_target_additions_absent(target, additions, expected_directory=None):
    with target_directory(target, expected_directory) as (descriptor, identity):
        for relative in additions:
            require_absent_target_name(descriptor, relative)
        return identity


def create_target_addition(target, relative, data, expected, directory_identity):
    """Create only an absent reviewed leaf; retain partial files on failure."""
    with target_directory(target, directory_identity) as (parent, _):
        require_absent_target_name(parent, relative)
        descriptor = os.open(relative, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                             0o600, dir_fd=parent)
        with os.fdopen(descriptor, "wb") as stream:
            os.fchmod(stream.fileno(), 0o644)
            if stream.write(data) != len(data):
                raise OSError("Incomplete target addition write; partial file preserved")
    require_file_identity(target, relative, expected)


def revise(config, paths, host_mode, previous_root, root=ROOT, *, allow_target_additions=()):
    """Advance reviewed controls while preserving the base and existing patches."""
    host = twrp_workspace.require_host(config, paths, host_mode)
    with operation_lock(paths, "revise"):
        return revise_locked(config, paths, host_mode, previous_root, root, host,
                             allow_target_additions=allow_target_additions)


def revise_locked(config, paths, host_mode, previous_root, root, host, *, allow_target_additions=()):
    previous_root = twrp_workspace.absolute_path(previous_root)
    root = twrp_workspace.absolute_path(root)
    if any(twrp_workspace.overlap(previous_root, path) for path in paths.values()):
        raise ValueError("Previous control bundle must be separate from source, output and reports")
    previous_config = twrp_workspace.load_config(previous_root / "config/twrp.json")
    if previous_config != config:
        raise ValueError("Target revision requires unchanged source configuration; source extensions need separate review")
    previous = controls(previous_config, previous_root)
    reviewed = controls(config, root)
    appended = validate_patch_extension(previous, reviewed)
    additions = reviewed_target_additions(previous, reviewed, allow_target_additions)
    validate_supplementary_extension(previous, reviewed)
    # An identical retry after a committed transition verifies the new state
    # instead of trying to restore the previous target from its bundle.
    current_state = json.loads(twrp_workspace.checked_report(paths["report_dir"] / STATE).read_text())
    if current_state.get("controls") == reviewed:
        current = check(config, paths, host_mode, root, host=host, record=False)
        return twrp_workspace.record_action(config, paths, "revise", {
            **current, "already_current": True, "changed_target_files": [], "added_patch_ids": [], "outputs_preserved": True})
    checked = check(config, paths, host_mode, previous_root, host=host, record=False)
    supplementary = verify_supplementary(root, paths, reviewed, checked["source"],
                                         phase="after", patches=previous["patches"])
    validate_patch_bases(twrp_workspace.load_snapshot(config, paths), reviewed)
    chained = twrp_patch_state.patch_plan(reviewed)["has_chains"]
    rehearsal = rehearse_chain(paths["source_dir"], reviewed, root, len(previous["patches"])) if chained else None
    preimages = rehearsal["initial_files"] if chained else verify_patch_files(
        paths["source_dir"], appended, "before", require_head_preimage=True)
    payloads = []
    for index, patch in enumerate(appended["patches"]):
        data = text_file(root, patch["patch"])
        if sha256(data) != patch["patch_sha256"]:
            raise ValueError("Controlled patch changed during revision planning")
        if not chained:
            twrp_workspace.run(["git", "-C", paths["source_dir"] / patch["project"], "apply", "--check",
                                "--whitespace=error-all", "--", root / patch["patch"]])
        payloads.append((patch, data, f"patches/{index:04d}.patch"))
    state_path = twrp_workspace.checked_report(paths["report_dir"] / STATE)
    state_before = state_path.read_bytes()
    if sha256(state_before) != checked["build_state_sha256"]:
        raise ValueError("Build receipt changed during target revision")
    changed = sorted(path for path in previous["target_files"]
                     if previous["target_files"][path] != reviewed["target_files"][path])
    target = paths["source_dir"] / TARGET
    directory_identity = require_target_additions_absent(target, additions) if additions else None
    before, after = {}, {}
    for relative in changed:
        before[relative] = require_file_identity(target, relative, previous["target_files"][relative]).read_bytes()
    for relative in changed + additions:
        after[relative] = text_file(root / TARGET_SOURCE, relative)
        if (sha256(after[relative]) != reviewed["target_files"][relative]["sha256"]
                or len(after[relative]) != reviewed["target_files"][relative]["size_bytes"]):
            raise ValueError("Controlled target changed during revision planning")
    absence_bytes = (json.dumps({"previous_build_state_sha256": sha256(state_before),
                                "allowed_target_additions": additions, "target_directory": directory_identity,
                                "before": {name: {"exists": False} for name in additions},
                                "after": {name: reviewed["target_files"][name] for name in additions}},
                               indent=2) + "\n").encode() if additions else None
    now = datetime.now(timezone.utc)
    revision = now.strftime("%Y%m%dT%H%M%S%fZ")
    archive = twrp_workspace.absolute_path(paths["report_dir"] / "build-revisions" / revision)
    archive.mkdir(parents=True, exist_ok=False)
    write_new_file(archive, "build-state.before.json", state_before)
    for relative in changed:
        write_new_file(archive, "target-before/" + relative, before[relative])
    for relative in changed + additions:
        write_new_file(archive, "target-after/" + relative, after[relative])
    if additions:
        write_new_file(archive, "target-additions.json", absence_bytes)
    if chained:
        evidence = archive_chain(archive, paths["source_dir"], reviewed, previous,
                                 len(previous["patches"]), rehearsal, state_before)
        evidence["build-state.before.json"] = {"sha256": sha256(state_before),
                                                "size_bytes": len(state_before), "mode": "0644"}
        for relative in changed:
            for prefix, data in (("target-before/", before[relative]), ("target-after/", after[relative])):
                evidence[prefix + relative] = {"sha256": sha256(data), "size_bytes": len(data), "mode": "0644"}
        if additions:
            evidence["target-additions.json"] = {"sha256": sha256(absence_bytes),
                                                 "size_bytes": len(absence_bytes), "mode": "0644"}
            for relative in additions:
                evidence["target-after/" + relative] = reviewed["target_files"][relative]
    else:
        for relative, identity in preimages.items():
            data = require_file_identity(paths["source_dir"], relative, identity).read_bytes()
            write_new_file(archive, "source-before/" + relative, data)
    for patch, data, relative in payloads:
        write_new_file(archive, relative, data)
        if chained:
            evidence[relative] = {"sha256": sha256(data), "size_bytes": len(data), "mode": "0644"}
    report = {"compile_only": True, "flash_admitted": False, "already_current": False,
              "previous_control_root": str(previous_root), "revision_archive": str(archive),
              "previous_build_state_sha256": sha256(state_before), "changed_target_files": changed,
              "source": checked["source"], "outputs_preserved": True,
              "added_patch_ids": [patch["id"] for patch in appended["patches"]],
              "attempted_patch_ids": [], "applied_patch_ids": [], "source_preimages": preimages,
              "build_for_this_revision_verified": False, "note": LIMITATION}
    if additions:
        report.update(added_target_files=additions, attempted_target_additions=[], verified_target_additions=[])
    if supplementary is not None:
        report["supplementary_projects"] = supplementary
    transition_bytes = (json.dumps({**report, "controls_after": reviewed}, indent=2) + "\n").encode()
    write_new_file(archive, "transition.json", transition_bytes)
    if chained:
        evidence["transition.json"] = {"sha256": sha256(transition_bytes), "size_bytes": len(transition_bytes), "mode": "0644"}
    twrp_workspace.record_action(config, paths, "revise-start", report)
    def verify_addition_evidence():
        if not additions:
            return
        require_file_identity(archive, "target-additions.json", {
            "sha256": sha256(absence_bytes), "size_bytes": len(absence_bytes), "mode": "0644"})
        for relative in additions:
            require_file_identity(archive, "target-after/" + relative, reviewed["target_files"][relative])
        if controls(config, root) != reviewed or controls(previous_config, previous_root) != previous:
            raise ValueError("A control bundle changed during target addition")
        if twrp_workspace.checked_report(state_path).read_bytes() != state_before:
            raise ValueError("Build receipt changed during target addition; changes preserved")
        with target_directory(target, directory_identity):
            pass
    try:
        # The prior bundle authorizes only the exact prepared files. Never
        # reset projects, remove output/cache, or adopt partial local edits.
        require_file_identity(archive, "build-state.before.json", {
            "sha256": sha256(state_before), "size_bytes": len(state_before), "mode": "0644"})
        for relative in changed:
            require_file_identity(archive, "target-before/" + relative, previous["target_files"][relative])
            require_file_identity(archive, "target-after/" + relative, reviewed["target_files"][relative])
        for relative, identity in preimages.items():
            # Archives stay nonexecutable; the original source mode is kept
            # separately in the transition receipt and verified after apply.
            require_file_identity(archive, "source-before/" + relative, {**identity, "mode": "0644"})
        for patch, data, relative in payloads:
            require_file_identity(archive, relative, {
                "sha256": patch["patch_sha256"], "size_bytes": len(data), "mode": "0644"})
        verify_target(paths["source_dir"], previous["target_files"])
        if controls(config, root) != reviewed or controls(previous_config, previous_root) != previous:
            raise ValueError("A control bundle changed during target revision")
        verify_addition_evidence()
        if additions:
            require_target_additions_absent(target, additions, directory_identity)
        if chained:
            apply_chain_steps(config, paths, root, reviewed, previous, previous_root, archive,
                              len(previous["patches"]), rehearsal, state_before, checked["source"], payloads, report, evidence)
        for patch, _, relative in (() if chained else payloads):
            single = {"patches": [patch]}
            verify_patch_files(paths["source_dir"], single, "before", require_head_preimage=True)
            payload = regular_file(archive, relative)
            if sha256(payload.read_bytes()) != patch["patch_sha256"]:
                raise ValueError("Archived patch payload changed; source application refused")
            report["attempted_patch_ids"].append(patch["id"])
            twrp_workspace.run(["git", "-C", paths["source_dir"] / patch["project"], "apply",
                                "--whitespace=error-all", "--", payload])
            verify_patch_files(paths["source_dir"], single, "after")
            for item in patch["files"]:
                source_relative = f"{patch['project']}/{item['path']}"
                expected = {"sha256": item["after_sha256"], "size_bytes": item["after_size_bytes"],
                            "mode": preimages[source_relative]["mode"]}
                postimage = require_file_identity(paths["source_dir"], source_relative, expected).read_bytes()
                write_new_file(archive, "source-after/" + source_relative, postimage)
            report["applied_patch_ids"].append(patch["id"])
        expected_target = dict(previous["target_files"])
        for relative in changed:
            if additions:
                verify_addition_evidence()
                verify_target(paths["source_dir"], expected_target)
                require_target_additions_absent(target, additions, directory_identity)
            replace_target_file(target, relative, previous["target_files"][relative], after[relative], revision)
            expected_target[relative] = reviewed["target_files"][relative]
        for index, relative in enumerate(additions):
            verify_addition_evidence()
            verify_target(paths["source_dir"], expected_target)
            require_target_additions_absent(target, additions[index:], directory_identity)
            report["attempted_target_additions"].append(relative)
            create_target_addition(target, relative, after[relative], reviewed["target_files"][relative],
                                   directory_identity)
            expected_target[relative] = reviewed["target_files"][relative]
            report["verified_target_additions"].append(relative)
            verify_target(paths["source_dir"], expected_target)
        source = verify_sources(config, paths, reviewed, prepared=True)
        if source != checked["source"]:
            raise ValueError("Frozen source changed during target revision")
        verify_supplementary(root, paths, reviewed, source)
        verify_target(paths["source_dir"], reviewed["target_files"])
        verify_output(paths)
        if controls(config, root) != reviewed or controls(previous_config, previous_root) != previous:
            raise ValueError("A control bundle changed during target revision; receipt replacement refused")
        verify_addition_evidence()
        if chained:
            verify_chain_archive(archive, evidence)
        state_after = {**json.loads(state_before), "controls": reviewed, "source": source,
                       "host_preflight": host, "recorded_at": now.isoformat(),
                       "previous_build_state_sha256": sha256(state_before), "revision_archive": str(archive),
                       "outputs_preserved": True, "build_for_this_revision_verified": False}
        state_bytes = (json.dumps(state_after, indent=2) + "\n").encode()
        write_new_file(archive, "build-state.after.json", state_bytes)
        temporary = write_new_file(paths["report_dir"], f"build-state.{revision}.pending.json", state_bytes)
        if twrp_workspace.checked_report(state_path).read_bytes() != state_before:
            raise ValueError("Build receipt changed during target revision; replacement refused")
        os.replace(temporary, state_path)
        report["build_state_sha256"] = sha256(state_bytes)
        report["revision_committed"] = True
        report["status"] = "reviewed-inputs-revised; graph and artifact validation required"
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        # Preserve both the old receipt and all backups on failure; partial
        # target changes require inspection, not an automatic reset/retry.
        twrp_workspace.record_action(config, paths, "revise-failed", {**report, "status": "failed", "error": str(error)})
        raise
    try:
        return twrp_workspace.record_action(config, paths, "revise-complete", {**report, "completion_report_written": True})
    except OSError as error:
        # The receipt and both archived states already prove this transition.
        # A history-write failure must not imply that target replacement failed.
        return {**twrp_workspace.identity(config, paths), **report, "action": "revise-complete",
                "completion_report_written": False,
                "warning": "Revision committed; completion history could not be appended: " + str(error)}


def inspect_artifact(paths):
    """Inspect the expected dedicated v4 recovery layout, not runtime admission."""
    image = twrp_workspace.absolute_path(paths["out_dir"] / "target/product/nezha/recovery.img")
    if not image.is_file() or not stat.S_ISREG(image.stat().st_mode):
        raise ValueError("Build command returned without a regular recovery.img artifact")
    size = image.stat().st_size
    if not 4096 < size <= 104857600:
        raise ValueError("Recovery artifact is empty, truncated or exceeds the verified partition extent")
    with image.open("rb") as stream:
        header = stream.read(1584)
        stream.seek(-64, os.SEEK_END)
        footer = stream.read(64)
        if header[:8] != b"ANDROID!" or struct.unpack_from("<I", header, 40)[0] != 4:
            raise ValueError("Recovery artifact does not have the expected Android v4 header")
        kernel, ramdisk = struct.unpack_from("<II", header, 8)
        header_size = struct.unpack_from("<I", header, 20)[0]
        signature_size = struct.unpack_from("<I", header, 1580)[0]
        ramdisk_end = 4096 + ((ramdisk + 4095) // 4096) * 4096
        image_end = ramdisk_end + ((signature_size + 4095) // 4096) * 4096
        if kernel != 0 or ramdisk == 0 or header_size != 1584 or image_end > size - 64:
            raise ValueError("Recovery artifact violates the kernel-free stock layout contract")
        magic, major, minor, original, vbmeta_offset, vbmeta_size, _ = struct.unpack("!4sIIQQQ28s", footer)
        if (magic != b"AVBf" or major != 1 or original < image_end or original > vbmeta_offset
                or vbmeta_size < 256 or vbmeta_offset + vbmeta_size > size - 64):
            raise ValueError("Recovery artifact is missing a valid bounded AVB footer")
        stream.seek(vbmeta_offset)
        if stream.read(4) != b"AVB0":
            raise ValueError("Recovery artifact AVB metadata is absent")
    digest = hashlib.sha256()
    with image.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return {"path": str(image), "size_bytes": size, "sha256": digest.hexdigest(),
            "boot_header_version": 4, "kernel_size": kernel, "ramdisk_size": ramdisk,
            "boot_signature_size": signature_size, "padded_image_end": image_end,
            "avb_footer_version": f"{major}.{minor}", "avb_original_size": original,
            "avb_metadata_offset": vbmeta_offset, "avb_metadata_size": vbmeta_size,
            "format_inspected": True, "runtime_verified": False, "flash_admitted": False}


def run_build(config, paths, action, host_mode, jobs, variant, root=ROOT, *, keep_going=False):
    command(action, jobs, keep_going=keep_going)
    environment(paths["source_dir"], paths["out_dir"], variant)
    host = twrp_workspace.require_host(config, paths, host_mode)
    with operation_lock(paths, action):
        return run_build_locked(config, paths, action, host_mode, jobs, variant, root, host,
                                keep_going=keep_going)


def run_build_locked(config, paths, action, host_mode, jobs, variant, root, host, *, keep_going=False):
    args = command(action, jobs, keep_going=keep_going)
    env = environment(paths["source_dir"], paths["out_dir"], variant)
    verified = check(config, paths, host_mode, root, host=host)
    now = datetime.now(timezone.utc)
    log_path = paths["report_dir"] / (action + "-" + now.strftime("%Y%m%dT%H%M%S%fZ") + ".log")
    report = {"compile_only": True, "flash_admitted": False, "command": args,
              "target_product": PRODUCT, "target_release": RELEASE, "target_build_variant": variant,
              "log_path": str(log_path), "source": verified["source"],
              "build_state_sha256": verified["build_state_sha256"],
              "host_preflight": verified["host_preflight"], "note": LIMITATION}
    if keep_going:
        report["diagnostic_only"] = True
        report["canonical_build_receipt_required"] = True
        report["note"] += (" Keep-going collects independent Ninja failures without admitting failed builds. "
                           "Even after success, rerun without --keep-going for the canonical artifact receipt.")
    if variant == "userdebug":
        report["variant_caveat"] = ("userdebug permits bootconfig-selected permissive init behavior. "
                                    "This diagnostic compile does not establish enforcing recovery behavior.")
    twrp_workspace.record_action(config, paths, action + "-start", report)
    try:
        print("Compile-only " + action + "; log: " + str(log_path), flush=True)
        with log_path.open("x") as log:
            subprocess.run(args, cwd=paths["source_dir"], env=env, check=True, text=True,
                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, shell=False)
            report["command_exit_code"] = 0
            log.flush()
            with log_path.open(errors="replace") as output:
                if any("Build sandboxing disabled due to nsjail error" in line for line in output):
                    report["sandbox_fallback_detected"] = True
                    raise ValueError("Build reported an nsjail sandbox fallback; unsandboxed success is not admitted")
            report["sandbox_fallback_detected"] = False
            # Upstream build hooks must not silently modify the pinned sources.
            after = check(config, paths, host_mode, root, host=verified["host_preflight"], record=False)
            if after["build_state_sha256"] != verified["build_state_sha256"]:
                raise ValueError("Prepared build revision changed during compilation; artifact provenance is not admitted")
            if action == "build":
                report["artifact"] = inspect_artifact(paths)
                avb = [sys.executable, "external/avb/avbtool.py", "verify_image", "--image",
                       report["artifact"]["path"], "--key", "external/avb/test/data/testkey_rsa4096.pem"]
                subprocess.run(avb, cwd=paths["source_dir"], env=env, check=True, text=True,
                               stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, shell=False)
                report["artifact"]["engineering_test_key_signature_verified"] = True
                report["artifact"]["oem_authority_verified"] = False
                report["status"] = "compiled-artifact-inspected; security and device validation pending"
                report["pending_validation"] = ["actual recovery SELinux policy and init selection",
                    "generated secure/ADB properties and authentication", "ramdisk contents and runtime dependencies",
                    "device compatibility, AVB trust and rollback admission"]
            else:
                report["status"] = "build-graph-checked; recovery artifact not built"
    except (ValueError, OSError, subprocess.SubprocessError) as error:
        report["status"] = "failed"
        report["error"] = str(error)
        if isinstance(error, subprocess.CalledProcessError):
            report["failed_command_exit_code"] = error.returncode
        twrp_workspace.record_action(config, paths, action + "-failed", report)
        raise
    return twrp_workspace.record_action(config, paths, action + "-complete", report)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=("plan", "prepare", "revise", "check", "graph", "build"), default="plan")
    parser.add_argument("--source-dir", type=Path)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--report-dir", type=Path)
    parser.add_argument("--previous-control-root", type=Path,
                        help="Exact prior control bundle; required only for an explicit target revision")
    parser.add_argument("--allow-target-addition", action="append", default=[], metavar="NAME",
                        help="Revise only: explicitly allow this new target root file; repeat for each addition")
    parser.add_argument("--host-mode", choices=twrp_workspace.workspace.HOST_MODES, default="native")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--variant", choices=VARIANTS, default="user")
    parser.add_argument("--keep-going", action="store_true",
                        help="Build-only diagnostic: collect independent Ninja failures; errors still fail. "
                             "Rerun without this flag for the canonical artifact receipt.")
    args = parser.parse_args(argv)
    try:
        if args.keep_going and args.action != "build":
            raise ValueError("--keep-going is valid only for the build action")
        if args.allow_target_addition and args.action != "revise":
            raise ValueError("--allow-target-addition is valid only for the revise action")
        config = twrp_workspace.load_config()
        paths = twrp_workspace.paths_for(config, args.source_dir, args.out_dir, args.report_dir)
        command("build", args.jobs)
        if (args.action == "revise") != (args.previous_control_root is not None):
            raise ValueError("revise requires --previous-control-root, which is valid only for that action")
        if args.action == "plan":
            report = plan(config, paths, args.host_mode, args.jobs, args.variant)
        elif args.action == "prepare":
            report = prepare(config, paths, args.host_mode)
        elif args.action == "revise":
            report = revise(config, paths, args.host_mode, args.previous_control_root,
                            allow_target_additions=args.allow_target_addition)
        elif args.action == "check":
            report = check(config, paths, args.host_mode)
        else:
            report = run_build(config, paths, args.action, args.host_mode, args.jobs, args.variant,
                               keep_going=args.keep_going)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, UnicodeError, OSError, subprocess.SubprocessError, ET.ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
