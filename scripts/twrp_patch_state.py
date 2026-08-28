"""Read-only identities and patch-state checks shared by TWRP source tools.

This module never fetches, applies patches, publishes receipts or acquires a
writer lock. Callers choose the exact before/after phase and hold their existing
operation lock when performing a transition.
"""

import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess

try:
    from scripts import twrp_workspace
except ModuleNotFoundError:  # Direct execution from a copied control bundle.
    import twrp_workspace


TARGET = "device/xiaomi/nezha"
TARGET_SOURCE = "recovery/twrp/" + TARGET
SERIES = "patches/twrp/series.json"
STATE = "build-state.json"
OUT_ALIAS = "out-twrp"
PRODUCT = "twrp_nezha"
RELEASE = "bp2a"
HEX256 = re.compile(r"[0-9a-f]{64}")
SAFE_PATH = re.compile(r"[A-Za-z0-9_./+-]+")
SOURCE_SUFFIXES = {".mk", ".bp", ".fstab", ".rc", ".te", ".prop", ".xml", ".txt", ".md"}
REQUIRED_TARGET = {"AndroidProducts.mk", "BoardConfig.mk", "twrp_nezha.mk", "device.mk", "recovery.fstab"}


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
    identifiers, bases = set(), {}
    payloads = {}
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
        payloads[identifier] = data
        expected_paths = set()
        if not isinstance(patch["files"], list) or not patch["files"]:
            raise ValueError("Each patch must declare its complete file closure")
        for item in patch["files"]:
            relative = str(relative_path(item["path"]))
            if relative in expected_paths:
                raise ValueError("Duplicate path within a patch")
            expected_paths.add(relative)
            for phase in ("before", "after"):
                size = item[phase + "_size_bytes"]
                if (not HEX256.fullmatch(item[phase + "_sha256"]) or type(size) is not int
                        or size < 0 or size > 16 * 1024 * 1024):
                    raise ValueError("Invalid patch preimage/postimage identity")
                if (phase + "_git_blob" in item
                        and not twrp_workspace.SHA.fullmatch(item[phase + "_git_blob"])):
                    raise ValueError("Invalid patch Git blob identity")
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
    plan = patch_plan({"patches": patches})
    for project in plan["projects"].values():
        for chain in project["files"].values():
            if len(chain["steps"]) > 1:
                for step in chain["steps"]:
                    chain_patch_index(payloads[step["patch_id"]], chain["path"], step["item"])
    return {"series_sha256": sha256(raw), "patches": patches}


def control_inventory(config, root, supplementary=None):
    result = {"target_files": target_inventory(root), **patch_inventory(config, root)}
    if supplementary is not None:
        result["supplementary_projects"] = supplementary
    return result


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


def patch_plan(reviewed):
    """Derive ordered roots and tips without changing the reviewed controls.

    This validates metadata even for internal callers. A detached successor is
    always an orphan; matching bytes alone never authorize a starting state.
    """
    projects, identifiers, has_chains = {}, set(), False
    for index, patch in enumerate(reviewed["patches"]):
        identifier = patch["id"]
        if not isinstance(identifier, str) or not identifier or identifier in identifiers:
            raise ValueError("Duplicate or invalid patch identifier")
        identifiers.add(identifier)
        project = str(relative_path(patch["project"]))
        base = patch["base_commit"]
        if not isinstance(base, str) or not twrp_workspace.SHA.fullmatch(base):
            raise ValueError("Each patched project needs one full pinned base revision")
        owner = projects.setdefault(project, {"base_commit": base, "files": {}})
        if owner["base_commit"] != base:
            raise ValueError("Each patched project needs one full pinned base revision")
        seen = set()
        if not isinstance(patch["files"], list) or not patch["files"]:
            raise ValueError("Each patch must declare its complete file closure")
        for item in patch["files"]:
            path = str(relative_path(item["path"]))
            if path in seen:
                raise ValueError("Duplicate path within a patch")
            seen.add(path)
            for phase in ("before", "after"):
                digest, size = item[phase + "_sha256"], item[phase + "_size_bytes"]
                if (not isinstance(digest, str) or not HEX256.fullmatch(digest)
                        or type(size) is not int or not 0 <= size <= 16 * 1024 * 1024):
                    raise ValueError("Invalid patch preimage/postimage identity")
                blob = item.get(phase + "_git_blob")
                if phase + "_git_blob" in item and (not isinstance(blob, str)
                        or not twrp_workspace.SHA.fullmatch(blob)):
                    raise ValueError("Invalid patch Git blob identity")
            if item["before_sha256"] == item["after_sha256"]:
                raise ValueError("Patch metadata declares no content change")
            chain = owner["files"].get(path)
            predecessor = item.get("predecessor_patch_id")
            if chain is None:
                if "predecessor_patch_id" in item:
                    raise ValueError("First patch touch cannot declare a predecessor")
                chain = owner["files"][path] = {"path": path, "root": item, "steps": []}
            else:
                previous = chain["steps"][-1]
                if (not isinstance(predecessor, str) or not predecessor
                        or predecessor != previous["patch_id"]):
                    raise ValueError("Overlapping patch files require their explicit immediate predecessor")
                for participant in (previous["item"], item):
                    if any(not isinstance(participant.get(phase + "_git_blob"), str)
                           or not twrp_workspace.SHA.fullmatch(participant[phase + "_git_blob"])
                           for phase in ("before", "after")):
                        raise ValueError("Every chain record requires complete Git blob identities")
                if any(item["before_" + key] != previous["item"]["after_" + key]
                       for key in ("sha256", "size_bytes", "git_blob")):
                    raise ValueError("Patch chain predecessor identity is discontinuous")
                if item["after_sha256"] == chain["root"]["before_sha256"]:
                    raise ValueError("Patch chain cannot revert to its original root")
                has_chains = True
            chain["steps"].append({"index": index, "patch_id": identifier, "item": item})
    return {"projects": projects, "has_chains": has_chains, "patch_count": len(reviewed["patches"])}


def chain_patch_index(data, relative, item, mode=None):
    """Require complete Git object IDs for a chain's exact file transition."""
    sections = data.decode("utf-8").split("diff --git ")[1:]
    selected = [section for section in sections if section.splitlines()[0] == f"a/{relative} b/{relative}"]
    if len(selected) != 1:
        raise ValueError("Chained patch is missing its exact file header")
    indexes = [line for line in selected[0].splitlines() if line.startswith("index ")]
    match = re.fullmatch(r"index ([0-9a-f]{40})\.\.([0-9a-f]{40}) (100644|100755)", indexes[0]) if len(indexes) == 1 else None
    if (match is None or match[1] != item["before_git_blob"] or match[2] != item["after_git_blob"]
            or mode is not None and int(match[3], 8) & 0o777 != mode):
        raise ValueError("Chained patch requires full matching Git index identities and pinned mode")


def patched_projects(reviewed):
    return {project: {"base_commit": owner["base_commit"],
                      "files": {path: chain["steps"][-1]["item"] for path, chain in owner["files"].items()}}
            for project, owner in patch_plan(reviewed)["projects"].items()}


def validate_patch_extension(previous, reviewed):
    old, new = previous["patches"], reviewed["patches"]
    if len(new) < len(old) or new[:len(old)] != old:
        raise ValueError("The existing patch queue must remain an exact unchanged prefix")
    appended = new[len(old):]
    if not appended and previous["series_sha256"] != reviewed["series_sha256"]:
        raise ValueError("Without appended patches, revision requires the exact existing patch queue")
    patch_plan(previous)
    patch_plan(reviewed)
    # Preserve full context: an appended successor cannot be verified as an
    # independently authorized root. The old receipt still supplies authority.
    return {"patches": appended, "complete_patches": new, "previous_patch_count": len(old)}


def patch_owners(frozen, reviewed):
    """Combine identities for lookup without changing the frozen Repo manifest."""
    owners = {path: {"commit": entry["revision"], "url": entry["url"], "kind": "base"}
              for path, entry in frozen.items()}
    supplementary = reviewed.get("supplementary_projects")
    for entry in supplementary["projects"] if supplementary is not None else ():
        relative = str(relative_path(entry["path"]))
        candidate = PurePosixPath(relative)
        if (twrp_workspace.overlap(candidate, PurePosixPath(TARGET))
                or any(twrp_workspace.overlap(candidate, PurePosixPath(path)) for path in owners)):
            raise ValueError("Supplementary patch owner overlaps another source owner or the controlled target")
        if not twrp_workspace.SHA.fullmatch(entry["commit"]):
            raise ValueError("Supplementary patch owner needs an exact reviewed commit")
        twrp_workspace.public_url(entry["url"])
        owners[relative] = {"commit": entry["commit"], "url": entry["url"], "kind": "supplementary"}
    return owners


def validate_patch_bases(frozen, reviewed):
    owners = patch_owners(frozen, reviewed)
    for patch in reviewed["patches"]:
        relative = str(relative_path(patch["project"]))
        owner = owners.get(relative)
        if owner is None or owner["commit"] != patch["base_commit"]:
            raise ValueError(f"Patch project does not match the frozen base revision or reviewed supplementary pin: {relative}")
        if ((owner["kind"] == "supplementary" or "repository" in patch)
                and patch.get("repository") != owner["url"]):
            raise ValueError("Patch repository differs from its pinned source origin")
        if owner["kind"] == "supplementary":
            for item in patch["files"]:
                for phase in ("before", "after"):
                    if not twrp_workspace.SHA.fullmatch(item.get(phase + "_git_blob", "")):
                        raise ValueError("Supplementary patches require explicit before and after Git blob identities")
    return owners


def git_blob_sha1(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def chain_git_environment(home):
    # No inherited GIT_*, alternate object stores/indexes, startup hooks or
    # caller configuration. The scratch HOME is empty and never a source home.
    return {"PATH": "/usr/local/bin:/usr/bin:/bin", "HOME": str(home),
            "XDG_CONFIG_HOME": str(home), "LANG": "C", "LC_ALL": "C",
            "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_ATTR_NOSYSTEM": "1", "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_TERMINAL_PROMPT": "0", "GIT_OPTIONAL_LOCKS": "0"}


def pinned_file(source, project, base, relative, root):
    """Read bounded original bytes from the immutable owner, not its index."""
    directory = twrp_workspace.absolute_path(source / project)
    args = ["git", "-c", "core.fsmonitor=false", "-c", "core.attributesFile=/dev/null",
            "-C", str(directory)]
    def query(*parts):
        return subprocess.run([*args, *parts], check=True, capture_output=True,
                              stdin=subprocess.DEVNULL, shell=False, timeout=60,
                              env=chain_git_environment("/nonexistent")).stdout
    tree = query("ls-tree", "-z", base, "--", relative)
    header, separator, name = tree.partition(b"\t")
    fields = header.split()
    if (not separator or name != relative.encode() + b"\0" or len(fields) != 3
            or fields[0] not in {b"100644", b"100755"} or fields[1] != b"blob"
            or not re.fullmatch(b"[0-9a-f]{40}", fields[2])):
        raise ValueError("Chain root is not an original pinned regular Git blob")
    blob = fields[2].decode("ascii")
    size_raw = query("cat-file", "-s", blob).strip()
    if not re.fullmatch(b"[0-9]+", size_raw) or int(size_raw) > 16 * 1024 * 1024:
        raise ValueError("Chain root exceeds its bounded Git blob size")
    data = query("cat-file", "blob", blob)
    if (len(data) != int(size_raw) or len(data) != root["before_size_bytes"]
            or sha256(data) != root["before_sha256"] or git_blob_sha1(data) != blob
            or "before_git_blob" in root and root["before_git_blob"] != blob):
        raise ValueError("Chain root bytes differ from the immutable original Git blob")
    if b"\0" in data:
        raise ValueError("Chain roots must remain text")
    data.decode("utf-8")
    return data, int(fields[0], 8) & 0o777


def boundary_item(chain, boundary):
    candidates = [step for step in chain["steps"] if step["index"] < boundary]
    return (candidates[-1]["item"], "after") if candidates else (chain["root"], "before")


def verify_chain_boundary(source, reviewed, boundary):
    """Check all declared files at one explicit full-queue prefix."""
    plan = patch_plan(reviewed)
    if type(boundary) is not int or not 0 <= boundary <= plan["patch_count"]:
        raise ValueError("Invalid explicit patch boundary")
    identities = {}
    for project, owner in plan["projects"].items():
        for relative, chain in owner["files"].items():
            _, mode = pinned_file(source, project, owner["base_commit"], relative, chain["root"])
            item, phase = boundary_item(chain, boundary)
            path = regular_file(source / project, relative)
            if path.stat().st_size != item[phase + "_size_bytes"]:
                raise ValueError(f"Chain boundary size differs; changes preserved: {project}/{relative}")
            data = path.read_bytes()
            if (sha256(data) != item[phase + "_sha256"] or stat.S_IMODE(path.stat().st_mode) != mode
                    or phase + "_git_blob" in item and git_blob_sha1(data) != item[phase + "_git_blob"]):
                raise ValueError(f"Chain boundary identity or mode differs; changes preserved: {project}/{relative}")
            identities[f"{project}/{relative}"] = {"sha256": sha256(data), "size_bytes": len(data), "mode": f"{mode:04o}"}
    return identities


def verify_patch_files(source, reviewed, phase, require_head_preimage=False):
    if phase not in {"before", "after"}:
        raise ValueError("A patch verification phase must be before or after")
    if require_head_preimage and phase != "before":
        raise ValueError("A frozen Git preimage can only be checked before applying a patch")
    if patch_plan(reviewed)["has_chains"]:
        return verify_chain_boundary(source, reviewed, 0 if phase == "before" else len(reviewed["patches"]))
    identities = {}
    for project, patch in patched_projects(reviewed).items():
        directory = twrp_workspace.absolute_path(source / project)
        for relative, item in patch["files"].items():
            path = regular_file(directory, relative)
            tree = twrp_workspace.run(["git", "-C", directory, "ls-tree", "-z", patch["base_commit"], "--", relative],
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
            if path.stat().st_size != item[phase + "_size_bytes"]:
                raise ValueError(f"Patch {phase}image differs; preserve changes: {project}/{relative}")
            data = path.read_bytes()
            if sha256(data) != item[phase + "_sha256"]:
                raise ValueError(f"Patch {phase}image differs; preserve changes: {project}/{relative}")
            mode = stat.S_IMODE(path.stat().st_mode)
            if require_head_preimage and (git_blob_sha1(data) != fields[2] or mode != (int(fields[0], 8) & 0o777)):
                raise ValueError(f"New patch preimage or mode is not the frozen Git blob: {project}/{relative}")
            if mode != (int(fields[0], 8) & 0o777):
                raise ValueError(f"Patched file mode differs from the pinned source: {project}/{relative}")
            if phase + "_git_blob" in item and git_blob_sha1(data) != item[phase + "_git_blob"]:
                raise ValueError(f"Patch Git {phase}image identity differs: {project}/{relative}")
            identities[f"{project}/{relative}"] = {"sha256": sha256(data), "size_bytes": len(data), "mode": f"{mode:04o}"}
    return identities


def verify_sources(config, paths, reviewed, prepared, frozen=None, report=None):
    source = paths["source_dir"]
    twrp_workspace.verify_control(config, source)
    frozen = frozen if frozen is not None else twrp_workspace.load_snapshot(config, paths)
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
    validate_patch_bases(frozen, reviewed)
    report = report if report is not None else twrp_workspace.project_report(source, frozen)
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


def read_state(config, paths, reviewed, raw=None):
    raw = twrp_workspace.checked_report(paths["report_dir"] / STATE).read_bytes() if raw is None else raw
    state = json.loads(raw)
    if (any(state.get(key) != value for key, value in twrp_workspace.identity(config, paths).items())
            or state.get("controls") != reviewed or state.get("target_product") != PRODUCT
            or state.get("target_release") != RELEASE or state.get("output_alias") != OUT_ALIAS
            or state.get("compile_only") is not True or state.get("flash_admitted") is not False):
        raise ValueError("Prepared build identity or controlled sources changed; preserve the existing experiment")
    return state
