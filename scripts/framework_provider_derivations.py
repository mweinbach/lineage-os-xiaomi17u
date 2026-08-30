"""Exact reviewed ELF dependency derivations; no files are read or written here.

The caller must establish ABI compatibility before approving a rule. Successful
derivation proves only the exact byte transformation and parsed dynamic metadata.
It does not enumerate symbol/version string references. Their non-aliasing is
part of the separately bound review of the exact original input, not a generic
property inferred by this helper.
"""

from __future__ import annotations

import hashlib
import re
import struct

if __package__:
    from .apex_inputs import ApexError, elf_dynamic
else:
    from apex_inputs import ApexError, elf_dynamic


KIND = "exact-equal-length-dt-needed-string-replacement"
MAX_BYTES = 64 * 1024 * 1024
RULE_FIELDS = {
    "kind", "original", "derived", "old", "new",
    "dt_needed_string_file_offset", "changed_byte_file_offset",
    "original_byte_hex", "derived_byte_hex",
}
IDENTITY_FIELDS = {"sha256", "size_bytes"}
SHA256 = re.compile(r"[0-9a-f]{64}")
SONAME = re.compile(r"[A-Za-z0-9_+.-]+[.]so")


class DerivationError(ValueError):
    """An exact reviewed ELF derivation precondition did not hold."""


def _require(condition, message):
    if not condition:
        raise DerivationError(message)


def _identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def validate_rule(rule):
    _require(type(rule) is dict and set(rule) == RULE_FIELDS,
             "rule must contain exactly the reviewed fields")
    _require(rule["kind"] == KIND, "unsupported derivation kind")
    for key in ("original", "derived"):
        item = rule[key]
        _require(type(item) is dict and set(item) == IDENTITY_FIELDS,
                 "identity must bind exactly SHA256 and size")
        _require(type(item["sha256"]) is str
                 and SHA256.fullmatch(item["sha256"]) is not None,
                 "identity SHA256 must be lowercase hexadecimal")
        _require(type(item["size_bytes"]) is int
                 and 64 <= item["size_bytes"] <= MAX_BYTES,
                 "identity size is out of bounds")
    _require(rule["original"]["size_bytes"] == rule["derived"]["size_bytes"]
             and rule["original"]["sha256"] != rule["derived"]["sha256"],
             "derivation must change bytes without changing file length")
    for key in ("old", "new"):
        _require(type(rule[key]) is str and len(rule[key]) <= 4096
                 and SONAME.fullmatch(rule[key]) is not None,
                 "DT_NEEDED names must be bounded ASCII library names")
    old, new = rule["old"].encode("ascii"), rule["new"].encode("ascii")
    _require(len(old) == len(new), "DT_NEEDED names must have equal length")
    changes = [index for index, pair in enumerate(zip(old, new))
               if pair[0] != pair[1]]
    _require(len(changes) == 1, "DT_NEEDED names must differ by exactly one byte")
    for key in ("dt_needed_string_file_offset", "changed_byte_file_offset"):
        _require(type(rule[key]) is int
                 and 0 <= rule[key] < rule["original"]["size_bytes"],
                 "derivation offset is out of bounds")
    _require(rule["changed_byte_file_offset"]
             == rule["dt_needed_string_file_offset"] + changes[0],
             "changed byte must match the one differing name byte")
    for key, expected in (("original_byte_hex", old[changes[0]]),
                          ("derived_byte_hex", new[changes[0]])):
        _require(type(rule[key]) is str and rule[key] == f"{expected:02x}",
                 "pinned byte does not match the reviewed name change")
    return old, new


def _layout(raw):
    """Resolve the actual ELF64 dynamic table; do not search arbitrary bytes."""
    _require(len(raw) >= 64 and raw[:7] == b"\x7fELF\x02\x01\x01",
             "only little-endian ELF64 version 1 is supported")
    header = struct.unpack_from("<HHIQQQIHHHHHH", raw, 16)
    _require(header[0:3] == (3, 183, 1) and header[7] == 64,
             "an AArch64 ET_DYN ELF with its canonical header is required")
    phoff, phsize, phcount = header[4], header[8], header[9]
    _require(phsize == 56 and 0 < phcount <= 4096 and phoff >= 64
             and phoff + phsize * phcount <= len(raw),
             "invalid program header table")
    segments = []
    for index in range(phcount):
        kind, flags, offset, address, _, size, memory_size, _ = struct.unpack_from(
            "<IIQQQQQQ", raw, phoff + phsize * index)
        _require(offset + size <= len(raw) and size <= memory_size,
                 "invalid segment bounds")
        segments.append((kind, flags, offset, address, size))
    dynamic = [segment for segment in segments if segment[0] == 2]
    _require(len(dynamic) == 1, "exactly one dynamic segment is required")
    _, _, start, _, size = dynamic[0]
    _require(size >= 16 and size % 16 == 0, "invalid dynamic segment length")
    entries = []
    for position in range(start, start + size, 16):
        tag, value = struct.unpack_from("<qQ", raw, position)
        if tag == 0:
            break
        entries.append((tag, value))
    else:
        raise DerivationError("unterminated dynamic segment")
    tables = [value for tag, value in entries if tag == 5]
    sizes = [value for tag, value in entries if tag == 10]
    _require(len(tables) == len(sizes) == 1 and 0 < sizes[0] <= MAX_BYTES,
             "exactly one bounded dynamic string table is required")
    mappings = [(offset + tables[0] - address, sizes[0])
                for kind, _, offset, address, segment_size in segments
                if kind == 1 and address <= tables[0]
                and tables[0] + sizes[0] <= address + segment_size]
    _require(len(mappings) == 1, "dynamic string table must map uniquely")
    table_offset, table_size = mappings[0]
    strings = raw[table_offset:table_offset + table_size]
    needed = []
    for tag, value in entries:
        if tag != 1:
            continue
        _require(value < len(strings), "DT_NEEDED string offset is out of bounds")
        end = strings.find(b"\0", value)
        _require(0 <= end - value <= 4096, "invalid DT_NEEDED string termination")
        needed.append((table_offset + value, strings[value:end]))
    # Structural and interpreter aliasing is forbidden even if metadata decoded
    # by the existing parser would happen to ignore the affected byte.
    protected = [(0, 64), (phoff, phoff + phsize * phcount), (start, start + size)]
    shoff, shsize, shcount = header[5], header[10], header[11]
    if shoff or shcount:
        _require(shoff >= 64 and shsize == 64 and 0 < shcount <= 4096
                 and shoff + shsize * shcount <= len(raw),
                 "invalid or extended section header table")
        protected.append((shoff, shoff + shsize * shcount))
    # These additional dynamic tags hold string offsets but are intentionally
    # not included in apex_inputs.elf_dynamic's narrower metadata summary.
    for tag, value in entries:
        if tag in {0x6ffffefa, 0x6ffffefb, 0x6ffffefc, 0x7ffffffd, 0x7fffffff}:
            _require(value < len(strings), "dynamic string offset is out of bounds")
            end = strings.find(b"\0", value)
            _require(0 <= end - value <= 4096, "invalid dynamic string termination")
            protected.append((table_offset + value, table_offset + end + 1))
    interpreters = []
    for kind, flags, offset, _, segment_size in segments:
        if kind == 3:
            interpreters.append(raw[offset:offset + segment_size])
            protected.append((offset, offset + segment_size))
        if kind == 1 and flags & 1:
            protected.append((offset, offset + segment_size))
    return needed, strings, protected, interpreters


def derive_needed(raw: bytes, rule: dict) -> bytes:
    """Return the exact pinned derivation without mutating input or filesystem.

    This is not an ABI or runtime admission check. The caller must validate all
    original bundle inputs before deriving or publishing any output.
    """
    old, new = validate_rule(rule)
    _require(type(raw) is bytes, "immutable source bytes are required")
    _require(_identity(raw) == rule["original"], "original hash or size mismatch")
    try:
        before = elf_dynamic(raw)
        needed, strings, protected, interpreters = _layout(raw)
    except (ApexError, UnicodeError, struct.error) as exc:
        raise DerivationError(f"malformed original ELF: {exc}") from exc
    matches = [offset for offset, name in needed if name == old]
    _require(matches == [rule["dt_needed_string_file_offset"]],
             "DT_NEEDED must select the reviewed string exactly once")
    _require(strings.count(old + b"\0") == 1,
             "reviewed DT_NEEDED name is ambiguous in the string table")
    _require(not any(name == new for _, name in needed),
             "replacement would duplicate an existing dependency")
    offset = rule["changed_byte_file_offset"]
    _require(not any(start <= offset < end for start, end in protected),
             "changed byte aliases ELF structure, interpreter or executable bytes")
    _require(raw[offset] == int(rule["original_byte_hex"], 16),
             "original byte mismatch")
    derived = raw[:offset] + bytes([int(rule["derived_byte_hex"], 16)]) + raw[offset + 1:]
    _require(_identity(derived) == rule["derived"], "derived hash or size mismatch")
    _require([index for index, pair in enumerate(zip(raw, derived))
              if pair[0] != pair[1]] == [offset],
             "derivation must change only the reviewed byte")
    try:
        after = elf_dynamic(derived)
        after_needed, _, _, after_interpreters = _layout(derived)
    except (ApexError, UnicodeError, struct.error) as exc:
        raise DerivationError(f"malformed derived ELF: {exc}") from exc
    expected = dict(before)
    expected["needed"] = [rule["new"] if name == rule["old"] else name
                          for name in before["needed"]]
    _require(after == expected and after_interpreters == interpreters
             and after_needed == [(where, new if name == old else name)
                                  for where, name in needed],
             "unreviewed ELF metadata, interpreter, SONAME or search path change")
    return derived
