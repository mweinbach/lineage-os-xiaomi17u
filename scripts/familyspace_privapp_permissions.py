"""Reproduce the exact FamilySpace product allowlist source correction.

This module transforms supplied bytes only. It does not read a checkout,
install files, change enforcement, modify APKs, or qualify a bootable image.
The full source XML stays in ignored evidence; the public patch is a small hunk.
"""

import hashlib
import xml.etree.ElementTree as ET


PACKAGE = "com.google.android.apps.pixel.familyspace"
PERMISSIONS = (
    "android.permission.GET_ACCOUNTS_PRIVILEGED",
    "android.permission.WRITE_SECURE_SETTINGS",
)
SOURCE_PATH = "product/blobs/etc/permissions/privapp-permissions-google-p.xml"
BEFORE = {
    "sha256": "1a923edbfaa765eccb40ee7a11cec65e627349cfe8f33a7a1ff433e089a6a7f5",
    "size_bytes": 65108,
    "git_blob": "5f37c2a0e6398f406f029a9801fd37ce7547c16b",
}
AFTER = {
    "sha256": "79ec429edf7269c1bf5a084cffabba08860ed981134ba75c8f00bd3cc196db71",
    "size_bytes": 65356,
    "git_blob": "0700b43c14ae3393b5ca0c894f84ee85f09e5148",
}
BLOCK = (
    '\n    <privapp-permissions package="com.google.android.apps.pixel.familyspace">\n'
    '        <permission name="android.permission.GET_ACCOUNTS_PRIVILEGED"/>\n'
    '        <permission name="android.permission.WRITE_SECURE_SETTINGS"/>\n'
    '    </privapp-permissions>\n'
).encode("utf-8")
END = b"</permissions>\n"


def identity(raw):
    if type(raw) is not bytes:
        raise ValueError("source must be bytes")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
    }


def _insert_block(source):
    """Validate XML structure and preserve bytes when inserting the fixed block.

    The public derive() entry point additionally pins the complete source pair.
    This structural step can be exercised with small, public test fixtures.
    """
    if (type(source) is not bytes or b"\r" in source or b"\0" in source
            or b"<!DOCTYPE" in source or b"<!ENTITY" in source
            or not source.endswith(END) or source.count(END) != 1):
        raise ValueError("one complete LF-only permissions XML is required")
    try:
        root = ET.fromstring(source.decode("utf-8"))
    except (UnicodeDecodeError, ET.ParseError) as exc:
        raise ValueError("invalid permissions XML") from exc
    if root.tag != "permissions" or root.attrib:
        raise ValueError("unexpected permissions root")
    packages = []
    for child in root:
        if child.tag != "privapp-permissions" or set(child.attrib) != {"package"}:
            raise ValueError("unexpected product allowlist structure")
        package = child.get("package")
        if not package or package == PACKAGE or package in packages:
            raise ValueError("target or duplicate package already present")
        if any(node.tag == "privapp-permissions" for node in child.iter() if node is not child):
            raise ValueError("nested package block")
        packages.append(package)
    return source[:-len(END)] + BLOCK + END


def derive(source):
    """Return the pinned postimage; reject drift and duplicate application."""
    if identity(source) != BEFORE:
        raise ValueError("FamilySpace source preimage differs")
    result = _insert_block(source)
    if identity(result) != AFTER:
        raise ValueError("FamilySpace source postimage differs")
    return result


def reverse(source):
    """Recover the complete pinned original without an XML serialization."""
    if identity(source) != AFTER or source.count(BLOCK) != 1:
        raise ValueError("FamilySpace source postimage differs")
    result = source.replace(BLOCK, b"", 1)
    if identity(result) != BEFORE:
        raise ValueError("FamilySpace source preimage differs")
    return result
