"""Exact SignApk successor after 0020, with no signing or filesystem access.

A cloned STORED JarEntry retains parsed access/creation FileTimes even after
setTime() and setExtra(null). Start with a fresh entry so the JDK cannot add
unaccounted timestamp extra fields after the signer's alignment calculation.
"""

import hashlib


SOURCE_PATH = "tools/signapk/src/com/android/signapk/SignApk.java"
BEFORE = {
    "sha256": "a1ef3eaac711108c867c1834c475a84a4425d0fb29d07364b3fd20ed71f260f9",
    "size_bytes": 61172,
    "git_blob": "196daba1088e143f9a6f0a32915bded7b5a93c56",
}
AFTER = {
    "sha256": "e36126abbaa95f6762fb652139100a27032f2fe5ee4621f2be7debf4c9639111",
    "size_bytes": 61517,
    "git_blob": "49693b19155b034e23781fd19f6f8e1f837f150e",
}
OLD_BLOCK = (
    "            // Preserve the STORED method of the input entry.\n"
    "            JarEntry outEntry = new JarEntry(inEntry);\n"
).encode()
NEW_BLOCK = (
    "            // Copy payload metadata without inheriting access/creation timestamps.\n"
    "            // JarOutputStream can emit those as unaccounted extra fields and break alignment.\n"
    "            JarEntry outEntry = new JarEntry(inEntry.getName());\n"
    "            outEntry.setMethod(inEntry.getMethod());\n"
    "            outEntry.setSize(inEntry.getSize());\n"
    "            outEntry.setCompressedSize(inEntry.getCompressedSize());\n"
    "            outEntry.setCrc(inEntry.getCrc());\n"
).encode()


def identity(raw):
    if type(raw) is not bytes:
        raise ValueError("source must be bytes")
    return {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "size_bytes": len(raw),
        "git_blob": hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest(),
    }


def _replace_metadata_block(source):
    """Pure structural step for small public fixtures; derive pins full input."""
    if (type(source) is not bytes or b"\r" in source or b"\0" in source
            or not source.endswith(b"\n") or source.count(OLD_BLOCK) != 1
            or NEW_BLOCK in source):
        raise ValueError("one exact unmodified STORED-entry block required")
    return source.replace(OLD_BLOCK, NEW_BLOCK, 1)


def derive(source):
    """Require the complete 0020 postimage and return only the 0025 postimage."""
    if identity(source) != BEFORE:
        raise ValueError("SignApk source preimage differs")
    result = _replace_metadata_block(source)
    if identity(result) != AFTER:
        raise ValueError("SignApk source postimage differs")
    return result


def reverse(source):
    """Recover the complete 0020 postimage without changing any other source."""
    if identity(source) != AFTER or source.count(NEW_BLOCK) != 1:
        raise ValueError("SignApk source postimage differs")
    result = source.replace(NEW_BLOCK, OLD_BLOCK, 1)
    if identity(result) != BEFORE:
        raise ValueError("SignApk source preimage differs")
    return result
