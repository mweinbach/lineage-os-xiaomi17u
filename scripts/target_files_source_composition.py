#!/usr/bin/env python3
"""Verify the explicit combined packaging source closure without changing it.

The source descriptor composes seven reviewed patches. Optional replay checks
all ten complete files from either the original base or the existing readonly
base; it never applies patches to a checkout or admits an Android build.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
import re
import sys

if __package__:
    from . import target_files_metadata as metadata
else:
    import target_files_metadata as metadata


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "patches/evolution/target-files-source-composition.json"
CONTRACT_ID = "nezha-target-files-source-composition-v1"
PRODUCT = "build/make/core/product.mk"
HOST_CONTROL_TOOLS = (
    "scripts/target_files_source_composition.py",
    "scripts/target_files_metadata_combined.py",
    "scripts/target_files_metadata.py",
)


class TargetFilesSourceCompositionError(ValueError):
    """The selected source closure or exact patch replay differs."""


def require(condition, message):
    if not condition:
        raise TargetFilesSourceCompositionError(message)


def compose_sources(root=ROOT):
    """Select only the new descriptor; historical composition APIs stay intact."""
    try:
        if __package__:
            from . import target_files_metadata_combined as combined
        else:
            import target_files_metadata_combined as combined
        return combined.compose_sources(root, source_contract=Path(root) / CONTRACT)
    except (ValueError, OSError, KeyError, TypeError, ImportError) as exc:
        raise TargetFilesSourceCompositionError("combined source composition refused: " + str(exc)) from exc


def _apply_exact_patch(before, patch, source_path):
    """Apply reviewed unified hunks in memory at their exact recorded positions."""
    require(type(before) is bytes and type(patch) is bytes
            and before.endswith(b"\n") and patch.endswith(b"\n"),
            "complete newline-terminated source and patch bytes are required")
    require(len(before) <= metadata.MAX_TEXT and len(patch) <= metadata.MAX_TEXT,
            "source or patch exceeds the input bound")
    source_path = metadata.relative(source_path)
    require(source_path.startswith("build/make/"), "patch source is outside build/make")
    short = source_path.removeprefix("build/make/")
    lines, patch_lines = before.decode("utf-8").splitlines(keepends=True), patch.decode("utf-8").splitlines(keepends=True)
    starts = [index for index, line in enumerate(patch_lines) if line.startswith("@@ ")]
    require(starts and re.findall(rb"^--- (.+)$", patch, re.M) == [f"a/{short}".encode()]
            and re.findall(rb"^\+\+\+ (.+)$", patch, re.M) == [f"b/{short}".encode()]
            and re.findall(rb"^diff --git (.+)$", patch, re.M) in
            ([], [f"a/{short} b/{short}".encode()]),
            "patch must have exactly one declared source header")
    output, cursor = [], 0
    for index, start in enumerate(starts):
        match = re.fullmatch(r"@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", patch_lines[start])
        require(match is not None, "patch hunk header differs")
        old_line, old_count, new_line, new_count = map(int, match.groups())
        require(old_line > 0 and new_line > 0 and old_count > 0 and new_count > 0,
                "empty or zero-position hunks are not admitted")
        body = patch_lines[start + 1:starts[index + 1] if index + 1 < len(starts) else None]
        require(all(line.startswith((" ", "+", "-")) for line in body), "patch hunk content differs")
        old = [line[1:] for line in body if line.startswith((" ", "-"))]
        new = [line[1:] for line in body if line.startswith((" ", "+"))]
        require(len(old) == old_count and len(new) == new_count, "patch hunk counts differ")
        position = old_line - 1
        require(position >= cursor and lines[position:position + old_count] == old,
                "patch exact source preimage differs; offsets and fuzz are forbidden")
        output.extend(lines[cursor:position])
        require(len(output) == new_line - 1, "patch exact output position differs")
        output.extend(new)
        cursor = position + old_count
    output.extend(lines[cursor:])
    return "".join(output).encode("utf-8")


def _load_rows(source_tree, rows, reader):
    root = metadata.real_directory(source_tree)
    require(type(rows) is list and all(type(row) is dict for row in rows), "invalid complete source closure")
    names = [metadata.relative(row.get("path")) for row in rows]
    require(names == sorted(set(names)), "source closure must be sorted and duplicate-free")
    return {row["path"]: reader.read(root / row["path"], row) for row in rows}


def _readonly_macro(product, expected):
    require(expected.get("name") == "readonly-variables" and expected.get("source") == PRODUCT,
            "unexpected readonly macro declaration")
    matches = re.findall(rb"^define readonly-variables\n.*?^endef\n", product, re.M | re.S)
    require(len(matches) == 1 and metadata.identity(matches[0])["sha256"] == expected.get("body_sha256"),
            "complete readonly macro definition differs")
    return metadata.identity(matches[0])


def check_source(source_tree, *, root=ROOT, predecessor_source_tree=None, predecessor="pristine"):
    """Check final files and optionally replay the explicitly selected predecessor."""
    require(predecessor in {"pristine", "readonly"}, "unknown source predecessor")
    require(predecessor_source_tree is not None or predecessor == "pristine",
            "a readonly predecessor requires its complete source tree")
    root = metadata.real_directory(root)
    reader = metadata.Reader()
    composition = compose_sources(root)
    reference = composition["contracts"][-1]
    require(reference["path"] == CONTRACT, "composition is missing its explicit selector")
    descriptor = metadata._json(reader.read(root / CONTRACT, reference))
    sources = _load_rows(source_tree, composition["final_source_files"], reader)
    macro = _readonly_macro(sources[PRODUCT], descriptor["readonly_macro"])
    replayed, initial_rows = [], None
    if predecessor_source_tree is not None:
        route = composition if predecessor == "pristine" else descriptor["readonly_upgrade"]
        initial_rows = route["initial_source_files"]
        initial = _load_rows(predecessor_source_tree, initial_rows, reader)
        current = dict(initial)
        for transition in route["source_transitions"]:
            path, patch = transition["path"], transition["patch"]
            require(path in current and metadata.identity(current[path]) == transition["before"],
                    "complete patch preimage differs: " + path)
            raw = reader.read(root / metadata.relative(patch["path"]), patch)
            current[path] = _apply_exact_patch(current[path], raw, path)
            require(metadata.identity(current[path]) == transition["after"],
                    "complete patch output differs: " + path)
            replayed.append(copy.deepcopy(transition))
        require(current == sources, "ordered patch replay does not reproduce every final source byte")
    require(compose_sources(root) == composition, "composition changed during source verification")
    reader.recheck()
    return {
        "schema_version": 1, "operation": "verify-combined-target-files-source",
        "project": composition["project"], "contract": reference,
        "composition_identity": metadata.identity(metadata.encoded(composition)),
        "source_files": composition["final_source_files"],
        "readonly_macro": {**descriptor["readonly_macro"], **macro},
        "predecessor": predecessor if predecessor_source_tree is not None else None,
        "initial_source_files": initial_rows, "patches_replayed_in_memory": replayed,
        "complete_patch_replay_verified": predecessor_source_tree is not None,
        "whole_source_tree_verified": False, "scope": copy.deepcopy(descriptor["scope"]),
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--controls-root", type=Path, default=ROOT)
    parser.add_argument("--source-tree", type=Path)
    parser.add_argument("--predecessor-source-tree", type=Path)
    parser.add_argument("--predecessor", choices=("pristine", "readonly"), default="pristine")
    args = parser.parse_args(argv)
    try:
        if args.source_tree is None:
            require(args.predecessor_source_tree is None and args.predecessor == "pristine",
                    "a source tree is required for predecessor verification")
            result = compose_sources(args.controls_root)
        else:
            result = check_source(args.source_tree, root=args.controls_root,
                                  predecessor_source_tree=args.predecessor_source_tree,
                                  predecessor=args.predecessor)
        print(metadata.encoded(result).decode(), end="")
        return 0
    except (TargetFilesSourceCompositionError, metadata.TargetFilesMetadataError,
            OSError, ValueError, UnicodeError, KeyError, TypeError) as exc:
        print(f"target-files source composition: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
