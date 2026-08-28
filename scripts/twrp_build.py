#!/usr/bin/env python3
"""Stage reviewed Nezha TWRP sources and run isolated compile-only checks."""

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

try:
    from scripts import twrp_workspace
except ModuleNotFoundError:  # Direct execution from a copied control bundle.
    import twrp_workspace


ROOT = Path(__file__).resolve().parents[1]
TARGET = "device/xiaomi/nezha"
TARGET_SOURCE = "recovery/twrp/" + TARGET
SERIES = "patches/twrp/series.json"
STATE = "build-state.json"
OUT_ALIAS = "out-twrp"
PRODUCT = "twrp_nezha"
RELEASE = "bp2a"
VARIANTS = ("user", "userdebug")
HEX256 = re.compile(r"[0-9a-f]{64}")
SAFE_PATH = re.compile(r"[A-Za-z0-9_./+-]+")
SOURCE_SUFFIXES = {".mk", ".bp", ".fstab", ".rc", ".te", ".prop", ".xml", ".txt", ".md"}
REQUIRED_TARGET = {"AndroidProducts.mk", "BoardConfig.mk", "twrp_nezha.mk", "device.mk", "recovery.fstab"}
LIMITATION = ("Compile-only recovery experiment. No phone command is run. Kernel, vendor_boot, "
              "modules, display/touch, storage, authenticated ADB and enforcing device behavior "
              "remain separate validation gates; no image is admitted for flashing.")


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def relative_path(value):
    if not isinstance(value, str) or not SAFE_PATH.fullmatch(value):
        raise ValueError(f"Unsupported source path: {value!r}")
    return twrp_workspace.relative_path(value)


def regular_file(root, relative):
    """Reject symlink components, special files and paths outside their owner."""
    path = root / str(relative_path(relative))
    for candidate in (path, *path.parents):
        if candidate.is_symlink():
            raise ValueError(f"Symlink in controlled source path: {candidate}")
        if candidate == root:
            break
    if not path.is_file() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"Expected a regular source file: {path}")
    return path


def text_file(root, relative):
    path = regular_file(root, relative)
    if path.stat().st_size > 1024 * 1024 or path.stat().st_mode & 0o111:
        raise ValueError(f"Source-only staging rejects large or executable payloads: {path}")
    data = path.read_bytes()
    if b"\0" in data:
        raise ValueError(f"Source-only staging rejects binary payloads: {path}")
    data.decode("utf-8")
    return data


def target_inventory(root):
    directory = root / TARGET_SOURCE
    twrp_workspace.absolute_path(directory)
    if not directory.is_dir():
        raise ValueError("Missing controlled Nezha TWRP target")
    inventory = {}
    for path in sorted(directory.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink in controlled target: {path}")
        if path.is_dir():
            relative_path(path.relative_to(directory).as_posix())
            continue
        relative = path.relative_to(directory).as_posix()
        if path.suffix not in SOURCE_SUFFIXES and path.name not in {"file_contexts", "property_contexts"}:
            raise ValueError(f"Source-only target rejects payload type: {relative}")
        data = text_file(directory, relative)
        inventory[relative] = {"sha256": sha256(data), "size_bytes": len(data), "mode": "0644"}
    if not REQUIRED_TARGET.issubset(inventory):
        raise ValueError("Controlled target is missing required Android product files")
    return inventory


def patch_inventory(config, root):
    raw = text_file(root, SERIES)
    series = json.loads(raw)
    if series.get("schema_version") != 1 or series.get("manifest", {}).get("commit") != config["manifest"]["commit"]:
        raise ValueError("Patch queue does not match the pinned TWRP manifest")
    patches = series.get("patches")
    if not isinstance(patches, list) or not patches:
        raise ValueError("The reviewed TWRP patch queue must not be empty")
    identifiers, affected, bases = set(), set(), {}
    for patch in patches:
        identifier = patch["id"]
        if not isinstance(identifier, str) or identifier in identifiers:
            raise ValueError("Duplicate or invalid patch identifier")
        identifiers.add(identifier)
        project = str(relative_path(patch["project"]))
        base = patch["base_commit"]
        if not twrp_workspace.SHA.fullmatch(base) or bases.get(project, base) != base:
            raise ValueError("Each patched project needs one full pinned base revision")
        bases[project] = base
        patch_path = relative_path(patch["patch"])
        if not patch_path.is_relative_to(PurePosixPath("patches/twrp")) or patch_path.suffix != ".patch":
            raise ValueError("Patch must be in the controlled TWRP patch queue")
        data = text_file(root, str(patch_path))
        if not HEX256.fullmatch(patch["patch_sha256"]) or sha256(data) != patch["patch_sha256"]:
            raise ValueError(f"Patch hash mismatch: {identifier}")
        expected_paths = set()
        if not isinstance(patch["files"], list) or not patch["files"]:
            raise ValueError("Each patch must declare its complete file closure")
        for item in patch["files"]:
            relative = str(relative_path(item["path"]))
            key = project, relative
            if key in affected:
                raise ValueError("Overlapping patch files require a reviewed consolidated patch")
            affected.add(key)
            expected_paths.add(relative)
            for phase in ("before", "after"):
                size = item[phase + "_size_bytes"]
                if (not HEX256.fullmatch(item[phase + "_sha256"]) or type(size) is not int
                        or size < 0 or size > 16 * 1024 * 1024):
                    raise ValueError("Invalid patch preimage/postimage identity")
            if item["before_sha256"] == item["after_sha256"]:
                raise ValueError("Patch metadata declares no content change")
        # Only edits of existing, same-path text files are admitted. Git then
        # validates actual context before any source change is made.
        headers, old_paths, new_paths = [], [], []
        for line in data.decode("utf-8").splitlines():
            if line.startswith("diff --git "):
                match = re.fullmatch(r"diff --git a/(\S+) b/(\S+)", line)
                if not match or match[1] != match[2]:
                    raise ValueError("Patch renames or quoted paths are not admitted")
                headers.append(str(relative_path(match[1])))
            elif line.startswith("--- "):
                old_paths.append(line[6:] if line.startswith("--- a/") else None)
            elif line.startswith("+++ "):
                new_paths.append(line[6:] if line.startswith("+++ b/") else None)
            elif line.startswith(("GIT binary patch", "Binary files ", "new file mode ",
                                  "deleted file mode ", "old mode ", "new mode ", "rename ", "copy ")):
                raise ValueError("Only regular text edits are admitted in the patch queue")
        if (len(headers) != len(expected_paths) or set(headers) != expected_paths
                or headers != old_paths or headers != new_paths):
            raise ValueError("Patch contents differ from the declared file closure")
    return {"series_sha256": sha256(raw), "patches": patches}


def controls(config, root=ROOT):
    result = {"target_files": target_inventory(root), **patch_inventory(config, root)}
    supplementary = supplementary_descriptor(root)
    if supplementary is not None:
        result["supplementary_projects"] = supplementary
    return result


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


def verify_supplementary(root, paths, reviewed, source):
    descriptor = reviewed.get("supplementary_projects")
    if descriptor is None:
        if supplementary_descriptor(root) is not None:
            raise ValueError("Supplementary source controls changed during verification")
        return None
    report = dependency_module().verify(root, paths["source_dir"], paths=paths)
    if (report is None or report["configuration_sha256"] != descriptor["configuration_sha256"]
            or any(report["base"].get(key) != value for key, value in source.items())):
        raise ValueError("Supplementary sources do not match the prepared base or reviewed configuration")
    return report


def validate_supplementary_extension(previous, reviewed):
    old = previous.get("supplementary_projects")
    new = reviewed.get("supplementary_projects")
    if old is None:
        return
    if new is None or old["base"] != new["base"]:
        raise ValueError("Target revision cannot remove or change the supplementary source baseline")
    old_projects = {entry["path"]: entry for entry in old["projects"]}
    new_projects = {entry["path"]: entry for entry in new["projects"]}
    if any(new_projects.get(path) != entry for path, entry in old_projects.items()):
        raise ValueError("Existing supplementary projects must remain unchanged; only reviewed additions are admitted")


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


def command(action, jobs):
    if type(jobs) is not int or not 1 <= jobs <= 64:
        raise ValueError("Build jobs must be between 1 and 64")
    if action not in {"graph", "build"}:
        raise ValueError("Only graph and dependency-checked recovery compilation are supported")
    return ["bash", "build/soong/soong_ui.bash", "--make-mode", f"-j{jobs}",
            "nothing" if action == "graph" else "recoveryimage"]


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


def patched_projects(reviewed):
    result = {}
    for patch in reviewed["patches"]:
        entry = result.setdefault(patch["project"], {"base_commit": patch["base_commit"], "files": {}})
        entry["files"].update({item["path"]: item for item in patch["files"]})
    return result


def verify_patch_files(source, reviewed, phase):
    for project, patch in patched_projects(reviewed).items():
        directory = twrp_workspace.absolute_path(source / project)
        for relative, item in patch["files"].items():
            path = regular_file(directory, relative)
            tree = twrp_workspace.run(["git", "-C", directory, "ls-tree", "-z", "HEAD", "--", relative],
                                      capture=True).stdout
            header, separator, name = tree.partition("\t")
            fields = header.split()
            if (not separator or name != relative + "\0" or len(fields) != 3 or fields[1] != "blob"
                    or fields[0] not in {"100644", "100755"} or not twrp_workspace.SHA.fullmatch(fields[2])):
                raise ValueError(f"Patched path is not a pinned regular Git blob: {project}/{relative}")
            if "before_git_blob" in item and fields[2] != item["before_git_blob"]:
                raise ValueError(f"Patch Git preimage identity differs: {project}/{relative}")
            if path.stat().st_mode & 0o111 != (0o111 if fields[0] == "100755" else 0):
                raise ValueError(f"Patched file executable mode differs from the pinned source: {project}/{relative}")
            if path.stat().st_size != item[phase + "_size_bytes"] or sha256(path.read_bytes()) != item[phase + "_sha256"]:
                raise ValueError(f"Patch {phase}image differs; preserve changes: {project}/{relative}")


def verify_sources(config, paths, reviewed, prepared):
    source = paths["source_dir"]
    twrp_workspace.verify_control(config, source)
    frozen = twrp_workspace.load_snapshot(config, paths)
    current = twrp_workspace.parse_manifest(twrp_workspace.manifest_text(source / ".repo/repo/repo", source))
    if set(current) != set(frozen) or any(
            any(current[path][key] != frozen[path][key] for key in ("name", "remote", "url")) for path in current):
        raise ValueError("Selected projects differ from the frozen TWRP manifest")
    target = PurePosixPath(TARGET)
    for relative in frozen:
        project = PurePosixPath(relative)
        if target == project or target.is_relative_to(project) or project.is_relative_to(target):
            raise ValueError("Controlled Nezha target overlaps a manifest-owned project")
    patched = patched_projects(reviewed)
    for relative, entry in patched.items():
        if relative not in frozen or frozen[relative]["revision"] != entry["base_commit"]:
            raise ValueError(f"Patch project does not match the frozen base revision: {relative}")
    for patch in reviewed["patches"]:
        if "repository" in patch and patch["repository"] != frozen[patch["project"]]["url"]:
            raise ValueError("Patch repository differs from the frozen source origin")
    report = twrp_workspace.project_report(source, frozen)
    failures = []
    if report["project_count"] != len(frozen) or not report["all_present"]:
        failures.append("Frozen project inventory is incomplete")
    for record in report["projects"]:
        errors = list(record["errors"])
        if prepared and record["path"] in patched:
            errors = [error for error in errors if error != "Local changes preserved"]
            status = twrp_workspace.run(["git", "-C", source / record["path"], "status", "--porcelain=v1",
                                         "-z", "--untracked-files=all"], capture=True).stdout
            expected = {" M " + relative for relative in patched[record["path"]]["files"]}
            entries = status.split("\0")
            if not entries or entries[-1] or set(entries[:-1]) != expected or len(entries) - 1 != len(expected):
                errors.append("Project modifications differ from the exact unstaged patch closure")
        failures.extend(f"{record['path']}: {error}" for error in errors)
    if failures:
        raise ValueError("TWRP source verification failed; changes preserved: " + "; ".join(failures))
    verify_patch_files(source, reviewed, "after" if prepared else "before")
    return {"project_count": len(frozen), "frozen_manifest_sha256":
            sha256(twrp_workspace.checked_report(paths["report_dir"] / twrp_workspace.SNAPSHOT).read_bytes())}


def verify_target(source, expected):
    target = twrp_workspace.absolute_path(source / TARGET)
    if not target.is_dir():
        raise ValueError("Prepared Nezha target is missing")
    actual = {}
    for path in sorted(target.rglob("*")):
        if path.is_symlink():
            raise ValueError(f"Symlink in staged Nezha target: {path}")
        if path.is_dir():
            continue
        relative = path.relative_to(target).as_posix()
        path = regular_file(target, relative)
        actual[relative] = {"sha256": sha256(path.read_bytes()), "size_bytes": path.stat().st_size,
                            "mode": f"{stat.S_IMODE(path.stat().st_mode):04o}"}
    if actual != expected:
        raise ValueError("Staged Nezha files differ from the prepared target; changes preserved")


def verify_output(paths):
    alias = paths["source_dir"] / OUT_ALIAS
    if not alias.is_symlink() or alias.readlink() != paths["out_dir"] or not paths["out_dir"].is_dir():
        raise ValueError("Source-relative output alias differs from the isolated output directory")
    twrp_workspace.absolute_path(paths["out_dir"])
    twrp_workspace.absolute_path(paths["out_dir"] / "target/product/nezha")
    for relative in ("tmp", "cache/go", "cache/xdg"):
        directory = twrp_workspace.absolute_path(paths["out_dir"] / relative)
        if not directory.is_dir():
            raise ValueError("Prepared output temporary or cache directory is missing")


def read_state(config, paths, reviewed):
    state = json.loads(twrp_workspace.checked_report(paths["report_dir"] / STATE).read_text())
    if (any(state.get(key) != value for key, value in twrp_workspace.identity(config, paths).items())
            or state.get("controls") != reviewed or state.get("target_product") != PRODUCT
            or state.get("target_release") != RELEASE or state.get("output_alias") != OUT_ALIAS
            or state.get("compile_only") is not True or state.get("flash_admitted") is not False):
        raise ValueError("Prepared build identity or controlled sources changed; preserve the existing experiment")
    return state


def check(config, paths, host_mode, root=ROOT, host=None, record=True):
    host = host if host is not None else twrp_workspace.require_host(config, paths, host_mode)
    reviewed = controls(config, root)
    state = read_state(config, paths, reviewed)
    source = verify_sources(config, paths, reviewed, prepared=True)
    if state.get("source") != source:
        raise ValueError("Prepared build source snapshot changed")
    supplementary = verify_supplementary(root, paths, reviewed, source)
    verify_target(paths["source_dir"], reviewed["target_files"])
    verify_output(paths)
    report = {"compile_only": True, "flash_admitted": False, "prepared_sources_verified": True,
              "build_state_sha256": sha256(twrp_workspace.checked_report(paths["report_dir"] / STATE).read_bytes()),
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
    verify_supplementary(root, paths, reviewed, source_record)
    target = twrp_workspace.absolute_path(source / TARGET)
    if target.exists():
        raise ValueError("Nezha target already exists without a preparation receipt; changes preserved")
    alias = source / OUT_ALIAS
    if alias.exists() or alias.is_symlink():
        raise ValueError("Output alias already exists without a preparation receipt; changes preserved")
    output = paths["out_dir"]
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError("Output directory is nonempty without a preparation receipt; files preserved")
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


def replace_target_file(target, relative, expected, data, revision):
    path = require_file_identity(target, relative, expected)
    temporary = path.with_name(f".{path.name}.twrp-revise-{revision}.tmp")
    write_new_file(target, temporary.relative_to(target).as_posix(), data)
    # Verify again immediately before replacement. Only a file matching the
    # old receipt can be replaced, and its exact bytes are already archived.
    require_file_identity(target, relative, expected)
    os.replace(temporary, path)


def revise(config, paths, host_mode, previous_root, root=ROOT):
    """Advance reviewed target/dependency controls, preserving base and patches."""
    host = twrp_workspace.require_host(config, paths, host_mode)
    with operation_lock(paths, "revise"):
        return revise_locked(config, paths, host_mode, previous_root, root, host)


def revise_locked(config, paths, host_mode, previous_root, root, host):
    previous_root = twrp_workspace.absolute_path(previous_root)
    root = twrp_workspace.absolute_path(root)
    if any(twrp_workspace.overlap(previous_root, path) for path in paths.values()):
        raise ValueError("Previous control bundle must be separate from source, output and reports")
    previous_config = twrp_workspace.load_config(previous_root / "config/twrp.json")
    if previous_config != config:
        raise ValueError("Target revision requires unchanged source configuration; source extensions need separate review")
    previous = controls(previous_config, previous_root)
    reviewed = controls(config, root)
    if (previous["patches"] != reviewed["patches"]
            or previous["series_sha256"] != reviewed["series_sha256"]):
        raise ValueError("Target revision requires the exact existing patch queue; patch transitions are not admitted")
    if set(previous["target_files"]) != set(reviewed["target_files"]):
        raise ValueError("Target revision requires the same file set; additions and removals need separate review")
    validate_supplementary_extension(previous, reviewed)
    # An identical retry after a committed transition verifies the new state
    # instead of trying to restore the previous target from its bundle.
    current_state = json.loads(twrp_workspace.checked_report(paths["report_dir"] / STATE).read_text())
    if current_state.get("controls") == reviewed:
        current = check(config, paths, host_mode, root, host=host, record=False)
        return twrp_workspace.record_action(config, paths, "revise", {
            **current, "already_current": True, "changed_target_files": [], "outputs_preserved": True})
    checked = check(config, paths, host_mode, previous_root, host=host, record=False)
    supplementary = verify_supplementary(root, paths, reviewed, checked["source"])
    state_path = twrp_workspace.checked_report(paths["report_dir"] / STATE)
    state_before = state_path.read_bytes()
    if sha256(state_before) != checked["build_state_sha256"]:
        raise ValueError("Build receipt changed during target revision")
    changed = sorted(path for path in previous["target_files"]
                     if previous["target_files"][path] != reviewed["target_files"][path])
    target = paths["source_dir"] / TARGET
    before, after = {}, {}
    for relative in changed:
        before[relative] = require_file_identity(target, relative, previous["target_files"][relative]).read_bytes()
        after[relative] = text_file(root / TARGET_SOURCE, relative)
        if sha256(after[relative]) != reviewed["target_files"][relative]["sha256"]:
            raise ValueError("Controlled target changed during revision planning")
    now = datetime.now(timezone.utc)
    revision = now.strftime("%Y%m%dT%H%M%S%fZ")
    archive = twrp_workspace.absolute_path(paths["report_dir"] / "build-revisions" / revision)
    archive.mkdir(parents=True, exist_ok=False)
    write_new_file(archive, "build-state.before.json", state_before)
    for relative in changed:
        write_new_file(archive, "target-before/" + relative, before[relative])
        write_new_file(archive, "target-after/" + relative, after[relative])
    report = {"compile_only": True, "flash_admitted": False, "already_current": False,
              "previous_control_root": str(previous_root), "revision_archive": str(archive),
              "previous_build_state_sha256": sha256(state_before), "changed_target_files": changed,
              "source": checked["source"], "outputs_preserved": True,
              "build_for_this_revision_verified": False, "note": LIMITATION}
    if supplementary is not None:
        report["supplementary_projects"] = supplementary
    write_new_file(archive, "transition.json", (json.dumps({**report, "controls_after": reviewed}, indent=2) + "\n").encode())
    twrp_workspace.record_action(config, paths, "revise-start", report)
    try:
        # The prior bundle authorizes only the exact prepared files. Never
        # reset projects, remove output/cache, or adopt partial local edits.
        verify_target(paths["source_dir"], previous["target_files"])
        if controls(config, root) != reviewed or controls(previous_config, previous_root) != previous:
            raise ValueError("A control bundle changed during target revision")
        for relative in changed:
            replace_target_file(target, relative, previous["target_files"][relative], after[relative], revision)
        source = verify_sources(config, paths, reviewed, prepared=True)
        if source != checked["source"]:
            raise ValueError("Frozen source changed during target revision")
        verify_supplementary(root, paths, reviewed, source)
        verify_target(paths["source_dir"], reviewed["target_files"])
        verify_output(paths)
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
        report["status"] = "target-revised; graph and artifact validation required"
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


def run_build(config, paths, action, host_mode, jobs, variant, root=ROOT):
    command(action, jobs)
    environment(paths["source_dir"], paths["out_dir"], variant)
    host = twrp_workspace.require_host(config, paths, host_mode)
    with operation_lock(paths, action):
        return run_build_locked(config, paths, action, host_mode, jobs, variant, root, host)


def run_build_locked(config, paths, action, host_mode, jobs, variant, root, host):
    args = command(action, jobs)
    env = environment(paths["source_dir"], paths["out_dir"], variant)
    verified = check(config, paths, host_mode, root, host=host)
    now = datetime.now(timezone.utc)
    log_path = paths["report_dir"] / (action + "-" + now.strftime("%Y%m%dT%H%M%S%fZ") + ".log")
    report = {"compile_only": True, "flash_admitted": False, "command": args,
              "target_product": PRODUCT, "target_release": RELEASE, "target_build_variant": variant,
              "log_path": str(log_path), "source": verified["source"],
              "build_state_sha256": verified["build_state_sha256"],
              "host_preflight": verified["host_preflight"], "note": LIMITATION}
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
    parser.add_argument("--host-mode", choices=twrp_workspace.workspace.HOST_MODES, default="native")
    parser.add_argument("--jobs", type=int, default=8)
    parser.add_argument("--variant", choices=VARIANTS, default="user")
    args = parser.parse_args(argv)
    try:
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
            report = revise(config, paths, args.host_mode, args.previous_control_root)
        elif args.action == "check":
            report = check(config, paths, args.host_mode)
        else:
            report = run_build(config, paths, args.action, args.host_mode, args.jobs, args.variant)
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, KeyError, TypeError, UnicodeError, OSError, subprocess.SubprocessError, ET.ParseError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
