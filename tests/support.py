"""Shared record walkers for the workspace checks.

Discovery does not collect this module; test modules import it by name, the same
way they already import pinned constants from each other.
"""

import hashlib
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
# Markers that must never reach a public record, whatever its forbidden keys are.
PRIVATE_MARKERS = ("-----BEGIN PRIVATE KEY-----", "(allow ", "(neverallow ", "<manifest")


def walk_objects(value):
    """Yield every mapping inside a decoded record, including the record itself."""
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk_objects(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_objects(child)


def assert_no_private_material(case, record, forbidden, markers=PRIVATE_MARKERS):
    """Check a record carries no forbidden key, embedded rule text or key blob.

    Each caller keeps its own `forbidden` key set, because the keys that would
    leak private material differ between the policy and SELinux records.
    """
    for item in walk_objects(record):
        case.assertFalse(forbidden.intersection(item))
        for key, child in item.items():
            if key.endswith("sha256") and child is not None:
                case.assertRegex(child, r"^[0-9a-f]{64}$")

    def check_strings(value):
        if isinstance(value, dict):
            for child in value.values():
                check_strings(child)
        elif isinstance(value, list):
            for child in value:
                check_strings(child)
        elif isinstance(value, str):
            for marker in markers:
                case.assertNotIn(marker, value)

    check_strings(record)


def assert_frozen_owner_revision(case, row, project, revision, repository, snapshot_sha256):
    """Resolve a patch's owning project from the pinned snapshot, not from its label."""
    raw = (ROOT / "research/source-snapshots/twrp-16.0-linux-20260828.xml").read_bytes()
    case.assertEqual(hashlib.sha256(raw).hexdigest(), snapshot_sha256)
    owners = [item for item in ET.fromstring(raw).iter("project")
              if item.get("path", item.get("name")) == project]
    case.assertEqual(len(owners), 1)
    case.assertEqual(owners[0].get("revision"), revision)
    case.assertEqual((row["project"], row["base_commit"], row["repository"]),
                     (project, revision, repository))


def write_file(path, raw):
    """Write bytes to a temp-tree path, creating parents. Shared by delivery tests."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
