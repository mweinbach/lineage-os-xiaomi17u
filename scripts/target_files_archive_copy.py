"""Stream a narrowly selected signed-image replacement into a fresh ZIP.

This helper copies bytes; it does not verify AVB, signatures, FEC, source origin,
partition fit, package compatibility, or a bootable ROM. The caller must bind
the public profile, original inventory, and actual signed-image verification.
Only three image roles, their existing aliases, and vbmeta_digest can change.
No archive member is extracted to the filesystem. A failure retains any partial
destination for diagnosis, never returns success, and never deletes inputs.
"""
from __future__ import annotations

from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys
import zipfile
import zlib

sys.dont_write_bytecode = True
if __package__:
    from . import target_files_avb_inventory as inventory
else:
    import target_files_avb_inventory as inventory

avb = inventory.avb
ROLES = frozenset(("boot", "vbmeta", "vbmeta_system"))
DIGEST_MEMBER = "META/vbmeta_digest.txt"
MAX_OUTPUT = 128 * 1024**3
CHUNK = avb.CHUNK
SPACE_CHECK_BYTES = 64 * 1024**2


class ArchiveCopyError(ValueError):
    """An input, copy, resource bound, or independent readback was rejected."""


def _require(value, message):
    if not value:
        raise ArchiveCopyError(message)


def _encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii") + b"\n"


def _identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def _pin(value, maximum, label):
    _require(type(value) is dict and set(value) == {"sha256", "size_bytes"},
             label + " identity fields differ")
    _require(type(value["sha256"]) is str and re.fullmatch(r"[0-9a-f]{64}", value["sha256"]),
             label + " SHA256 is invalid")
    _require(type(value["size_bytes"]) is int and 0 < value["size_bytes"] <= maximum,
             label + " size exceeds bound")
    return dict(value)


def _budgets(profile):
    _require(type(profile) is dict and profile.get("profile_id") == avb.PROFILE_ID
             and type(profile.get("image_budgets")) is dict,
             "the caller must supply the reviewed image-set profile")
    result = {}
    for role in ROLES:
        value = profile["image_budgets"].get(role)
        _require(type(value) is int and 0 < value <= inventory.MAX_ARCHIVE,
                 "invalid image budget: " + role)
        result[role] = value
    return result


def _without_zip64(extra):
    """Keep every non-ZIP64 extra byte, its framing, and original order."""
    cursor, result, seen = 0, bytearray(), False
    while cursor < len(extra):
        _require(cursor + 4 <= len(extra), "truncated ZIP extra")
        tag, length = struct.unpack_from("<HH", extra, cursor)
        end = cursor + 4 + length
        _require(end <= len(extra), "ZIP extra length exceeds record")
        if tag == 1:
            _require(not seen, "duplicate ZIP64 extra")
            seen = True
        else:
            result.extend(extra[cursor:end])
        cursor = end
    return bytes(result)


def _geometry(archive, bounds):
    """One offset sort and one successor index; never scan all rows per member."""
    offsets = sorted(info.header_offset for info in archive.infolist())
    _require(offsets and offsets[0] == 0 and len(offsets) == len(set(offsets)),
             "missing first local header or duplicate local header offsets")
    return dict(zip(offsets, offsets[1:] + [bounds["central_directory_offset"]]))


class _SpanBoundary:
    """Reuse the maintained local-header checker with its exact next boundary.

    Its old all-member scan sees an empty list. start_dir is deliberately the
    next physical header (or actual directory), so descriptors and compressed
    data still cannot cross an adjacent record. Central order may differ.
    """
    def __init__(self, archive, following):
        self.fp = archive.fp
        self.start_dir = following

    def infolist(self):
        return ()


def _span(archive, info, following):
    allowed_flags = 0x800 | 8 | (6 if info.compress_type == zipfile.ZIP_DEFLATED else 0)
    _require(not info.flag_bits & ~allowed_flags
             and info.compress_type in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED),
             "ZIP encryption, unknown flags, or compression is unsupported")
    _require(info.volume == 0, "ZIP member references a nonzero disk")
    start = inventory._selected_span(_SpanBoundary(archive, following), info)
    header = inventory._read_at(archive.fp, info.header_offset, 30)
    local_version = struct.unpack_from("<H", header, 4)[0]
    central_version = info.extract_version | (info.reserved << 8)
    # AOSP's streaming writer emits v20 with empty local CRC/sizes, then
    # promotes only the central entry to v45 when the final sizes need ZIP64.
    # _selected_span already validated the 64-bit descriptor and its bounds.
    # Support that writer convention, not arbitrary version disagreements.
    streaming_zip64 = (local_version == 20 and central_version == 45
                       and info.compress_type == zipfile.ZIP_DEFLATED and info.flag_bits & 8
                       and max(info.file_size, info.compress_size) > 0xffffffff
                       and header[14:26] == b"\x00" * 12)
    _require(local_version == central_version or streaming_zip64,
             "local and central ZIP extraction versions differ")
    local_time, local_date = struct.unpack_from("<HH", header, 10)
    year, month, day, hour, minute, second = info.date_time
    _require(local_time == ((hour << 11) | (minute << 5) | (second // 2))
             and local_date == (((year - 1980) << 9) | (month << 5) | day),
             "local and central ZIP timestamps differ")
    name_length, extra_length = struct.unpack_from("<HH", header, 26)
    raw_name = inventory._read_at(archive.fp, info.header_offset + 30, name_length)
    encoding = "utf-8" if info.flag_bits & 0x800 else "cp437"
    _require(raw_name.decode(encoding) == info.filename,
             "local and central ZIP names differ")
    _require(info.filename.encode(encoding) == raw_name,
             "ZIP filename encoding does not round-trip")
    local_extra = inventory._read_at(archive.fp, info.header_offset + 30 + name_length,
                                     extra_length)
    if info.compress_type == zipfile.ZIP_STORED:
        _require(info.compress_size == info.file_size, "stored member sizes differ")
    return start, raw_name, _without_zip64(local_extra)


def _metadata(info, raw_name, local_extra):
    # Binary metadata is represented by identities to bound the saved inventory;
    # equality is still over every original byte, not an interpreted subset.
    return {"date_time": list(info.date_time), "create_system": info.create_system,
            "external_attr": info.external_attr, "internal_attr": info.internal_attr,
            "comment": _identity(info.comment), "compress_type": info.compress_type,
            "central_extra_non_zip64": _identity(_without_zip64(info.extra)),
            "local_extra_non_zip64": _identity(local_extra),
            "encoded_name": _identity(raw_name), "name_utf8": bool(info.flag_bits & 0x800)}


def _read_member(archive, info, following, sink=None):
    """Decode/CRC/hash every member, including replaced members and symlinks."""
    start, raw_name, local_extra = _span(archive, info, following)
    digest, count, crc = hashlib.sha256(), 0, 0
    with archive.open(info, "r") as source:
        while True:
            part = source.read(min(CHUNK, info.file_size - count + 1))
            if not part:
                break
            count += len(part)
            _require(count <= info.file_size, "decoded member exceeds declared length")
            digest.update(part)
            crc = zlib.crc32(part, crc)
            if sink is not None:
                _require(sink.write(part) == len(part), "short ZIP member write")
    _require(count == info.file_size and crc == info.CRC, "decoded member size or CRC differs")
    if info.compress_type == zipfile.ZIP_DEFLATED:
        inventory._deflate_complete(archive.fp, start, info)
    return {"member": info.filename, "sha256": digest.hexdigest(), "size_bytes": count,
            "semantic_metadata": _metadata(info, raw_name, local_extra)}


class _PreservedZipInfo(zipfile.ZipInfo):
    """Prevent stdlib from re-encoding CP437 and invalidating Unicode extras."""
    def _encodeFilenameFlags(self):
        return self.raw_name, (self.flag_bits & ~0x800) | self.utf8_bit


def _write_info(info, raw_name, local_extra, size):
    result = _PreservedZipInfo(info.filename, info.date_time)
    result.raw_name = raw_name
    result.utf8_bit = info.flag_bits & 0x800
    for field in ("create_system", "create_version", "extract_version", "reserved",
                  "volume", "internal_attr", "external_attr", "comment", "compress_type"):
        setattr(result, field, getattr(info, field))
    result.extra = local_extra
    result.file_size = size
    # Compression is deterministic for the fixed host runtime, but compressed
    # bytes, CRC/header fields, offsets, ZIP64 framing and flags are re-emitted.
    result._compresslevel = 6
    return result


class _BoundedOutput:
    """Bound every physical ZIP write, including headers and final directory."""
    def __init__(self, stream, maximum):
        self.stream, self.maximum = stream, maximum
        self.high_water = self.checked_at = 0
        _require(_available(stream.fileno()) >= maximum + avb.RESERVE_BYTES,
                 "insufficient output space for bounded ZIP plus reserve")

    def write(self, data):
        _require(self.stream.tell() + len(data) <= self.maximum, "output ZIP exceeds byte bound")
        count = self.stream.write(data)
        _require(count == len(data), "short output ZIP write")
        self.high_water = max(self.high_water, self.stream.tell())
        if self.high_water - self.checked_at >= SPACE_CHECK_BYTES:
            _require(_available(self.stream.fileno()) >= self.maximum - self.high_water + avb.RESERVE_BYTES,
                     "output free-space floor was crossed")
            self.checked_at = self.high_water
        return count

    def seek(self, offset, whence=0):
        value = self.stream.seek(offset, whence)
        _require(0 <= value <= self.maximum, "output ZIP seek exceeds bound")
        return value

    def tell(self):
        return self.stream.tell()

    def flush(self):
        self.stream.flush()


def _available(descriptor):
    info = os.fstatvfs(descriptor)
    return info.f_bavail * info.f_frsize


def _output_bound(archive, members, following, specs):
    # Conservative deflateBound-style allowance: expanded literals, block
    # framing and trailer. A streamed member is finished once, without any
    # intervening full/sync flush. This deliberately overestimates zlib's
    # default raw-deflate bound rather than guessing from input compression.
    total = 22 + 20 + 56 + len(archive.comment)
    for name, info in members.items():
        _, raw_name, local_extra = _span(archive, info, following[info.header_offset])
        size = specs[name]["identity"]["size_bytes"] if name in specs else info.file_size
        payload = size
        if info.compress_type == zipfile.ZIP_DEFLATED:
            payload += (size + 7) // 8 + (size + 63) // 64 + 64
        # Local/central fixed headers, both names/extras, comment, worst-case
        # ZIP64 local sizes, central sizes+offset, and signed 64-bit descriptor.
        total += payload + 30 + 46 + 2 * len(raw_name) + len(local_extra)
        total += len(_without_zip64(info.extra)) + len(info.comment) + 20 + 28 + 24
        _require(total <= MAX_OUTPUT, "bounded rewritten ZIP would exceed 128 GiB")
    return total


def _required_replacements(members):
    canonical = {f"IMAGES/{role}.img" for role in ROLES} | {DIGEST_MEMBER}
    _require(canonical <= members.keys(), "missing required image or digest member")
    aliases = {f"{prefix}/{role}.img" for prefix in inventory.PREFIXES[1:] for role in ROLES}
    selected = canonical | (aliases & members.keys())
    _require(all(inventory._regular_member(members[name]) for name in selected),
             "replacement target is not a regular ZIP member")
    return selected


def _replacement_specs(replacements, selected, budgets):
    _require(type(replacements) is dict and set(replacements) == selected,
             "replacement set must exactly match canonical images, existing aliases, and digest")
    result = {}
    for name in sorted(selected):
        row = replacements[name]
        _require(type(row) is dict, "replacement must be an object")
        role = Path(name).stem if name != DIGEST_MEMBER else None
        maximum = budgets[role] if role else 65
        if set(row) == {"data"}:
            _require(type(row["data"]) is bytes and 0 < len(row["data"]) <= maximum,
                     "replacement data exceeds bound")
            result[name] = {"data": row["data"], "identity": _identity(row["data"])}
        else:
            _require(set(row) == {"path", "sha256", "size_bytes"} and isinstance(row["path"], Path),
                     "replacement path identity fields differ")
            pin = _pin({key: row[key] for key in ("sha256", "size_bytes")}, maximum, "replacement")
            result[name] = {"path": avb.envelope._absolute_path(row["path"]), "identity": pin}
        if role:
            result[name]["role"] = role
    for name, row in result.items():
        if name != DIGEST_MEMBER:
            _require(row["identity"] == result[f"IMAGES/{row['role']}.img"]["identity"],
                     "replacement alias differs from canonical image")
    return result


def _fresh_guard(path, stream, signature):
    # _input also checks its original held parent; reopening here additionally
    # catches replacement or symlinking of a lexical ancestor during the run.
    with avb.envelope._parent_directory(path) as parent:
        current = os.stat(path.name, dir_fd=parent, follow_symlinks=False)
        _require(avb._signature(current) == signature == avb._signature(os.fstat(stream.fileno())),
                 "input or output pathname/inode changed")


def _open_replacements(stack, specs):
    opened = {}
    for row in specs.values():
        if "path" not in row:
            continue
        path, pin = row["path"], row["identity"]
        if path in opened:
            _require(opened[path][2] == pin, "one replacement path has inconsistent identities")
            continue
        stream, info = stack.enter_context(avb._input(path, pin["size_bytes"]))
        _require(info.st_size == pin["size_bytes"]
                 and inventory._stream_identity(stream, info.st_size) == pin,
                 "replacement file identity differs")
        opened[path] = (stream, avb._signature(info), pin)
    digest = specs[DIGEST_MEMBER]
    if "data" in digest:
        raw = digest["data"]
    else:
        stream = opened[digest["path"]][0]
        stream.seek(0)
        raw = stream.read(66)
    _require(re.fullmatch(rb"[0-9a-f]{64}\n", raw) is not None,
             "vbmeta digest must be exactly lowercase SHA256 and one newline")
    return opened


def _write_replacement(row, opened, sink):
    expected, digest, count = row["identity"], hashlib.sha256(), 0
    if "path" in row:
        source = opened[row["path"]][0]
        source.seek(0)
        chunks = iter(lambda: source.read(CHUNK), b"")
    else:
        raw = row["data"]
        chunks = (raw[offset:offset + CHUNK] for offset in range(0, len(raw), CHUNK))
    for part in chunks:
        count += len(part)
        _require(count <= expected["size_bytes"], "replacement grew during copy")
        digest.update(part)
        _require(sink.write(part) == len(part), "short replacement write")
    _require({"sha256": digest.hexdigest(), "size_bytes": count} == expected,
             "replacement bytes differ during copy")


def _aggregate_start(comment):
    digest = hashlib.sha256()
    digest.update(_encoded({"schema_version": 1, "archive_comment": _identity(comment)}))
    return digest


def _copy_members(source_zip, output_zip, members, following, specs, opened):
    before, after, source_digest = {}, {}, _aggregate_start(source_zip.comment)
    for name, info in members.items():
        _, raw_name, local_extra = _span(source_zip, info, following[info.header_offset])
        expected = specs.get(name)
        size = expected["identity"]["size_bytes"] if expected else info.file_size
        output_info = _write_info(info, raw_name, local_extra, size)
        if expected:
            original = _read_member(source_zip, info, following[info.header_offset])
            with output_zip.open(output_info, "w", force_zip64=size >= zipfile.ZIP64_LIMIT) as sink:
                _write_replacement(expected, opened, sink)
            wanted = {**original, **expected["identity"]}
        else:
            with output_zip.open(output_info, "w", force_zip64=size >= zipfile.ZIP64_LIMIT) as sink:
                original = _read_member(source_zip, info, following[info.header_offset], sink)
            wanted = original
        # stdlib supplies 0600 for zero external_attr. Restore the actual source
        # value before its central directory is emitted. Local headers do not
        # carry this field. The final local header has already used local extras.
        output_info.external_attr = info.external_attr
        output_info.extra = _without_zip64(info.extra)
        before[name], after[name] = original, wanted
        source_digest.update(_encoded(original))
    output_zip.comment = source_zip.comment
    return before, after, source_digest.hexdigest()


def _readback(stream, size, expected_rows, comment):
    """Reopen the completed ZIP and independently decode all members again."""
    bounds = inventory._zip_bounds(stream, size)
    with zipfile.ZipFile(stream, "r") as archive:
        members = inventory._members(archive, bounds, avb.PARTITIONS)
        _require(list(members) == list(expected_rows), "output ZIP membership or order differs")
        _require(archive.comment == comment, "output archive comment differs")
        following, digest = _geometry(archive, bounds), _aggregate_start(archive.comment)
        for name, info in members.items():
            actual = _read_member(archive, info, following[info.header_offset])
            _require(actual == expected_rows[name], "output member payload or semantic metadata differs: " + name)
            digest.update(_encoded(actual))
    return {**bounds, "member_identity_metadata_sha256": digest.hexdigest()}


def _rewrite(source, expected_archive, destination, replacements, profile):
    _require(isinstance(source, Path) and isinstance(destination, Path), "source and destination must be Paths")
    source, destination = avb.envelope._absolute_path(source), avb.envelope._absolute_path(destination)
    _require(source != destination, "output must be a fresh archive path")
    pin, budgets = _pin(expected_archive, inventory.MAX_ARCHIVE, "archive"), _budgets(profile)
    with ExitStack() as stack:
        stream, source_info = stack.enter_context(avb._input(source, inventory.MAX_ARCHIVE))
        source_signature = avb._signature(source_info)
        _require(source_info.st_size == pin["size_bytes"], "source archive size differs")
        bounds = inventory._zip_bounds(stream, source_info.st_size)
        _require(inventory._stream_identity(stream, source_info.st_size) == pin, "source archive identity differs")
        with zipfile.ZipFile(stream, "r") as archive:
            members = inventory._members(archive, bounds, avb.PARTITIONS)
            selected, following = _required_replacements(members), _geometry(archive, bounds)
            specs = _replacement_specs(replacements, selected, budgets)
            for name in selected:
                maximum = budgets[specs[name]["role"]] if name != DIGEST_MEMBER else inventory.MAX_METADATA
                _require(0 < members[name].file_size <= maximum, "original selected member exceeds budget")
            expected_total = sum(specs[name]["identity"]["size_bytes"] if name in specs else info.file_size
                                 for name, info in members.items())
            _require(expected_total <= inventory.MAX_DECLARED_BYTES, "output declared payload exceeds bound")
            opened = _open_replacements(stack, specs)
            output_bound = _output_bound(archive, members, following, specs)
            parent = stack.enter_context(avb.envelope._parent_directory(destination))
            free_before = _available(parent)
            _require(free_before >= output_bound + avb.RESERVE_BYTES,
                     "insufficient output space for bounded ZIP plus reserve")
            descriptor = os.open(destination.name, os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                                 0o600, dir_fd=parent)
            output = stack.enter_context(os.fdopen(descriptor, "w+b", buffering=0))
            created = os.fstat(output.fileno())
            _require(stat.S_ISREG(created.st_mode) and created.st_nlink == 1
                     and stat.S_IMODE(created.st_mode) == 0o600, "output must be a new private regular file")
            with zipfile.ZipFile(_BoundedOutput(output, output_bound), "w", allowZip64=True) as written:
                before, wanted, source_aggregate = _copy_members(archive, written, members, following, specs, opened)
            original_comment = archive.comment
        output.flush()
        os.fsync(output.fileno())
        output_info = os.fstat(output.fileno())
        output_signature = avb._signature(output_info)
        _require(output_info.st_size <= MAX_OUTPUT and stat.S_IMODE(output_info.st_mode) == 0o600
                 and output_info.st_nlink == 1
                 and (created.st_dev, created.st_ino) == (output_info.st_dev, output_info.st_ino),
                 "completed ZIP size, private mode, or inode differs")
        _fresh_guard(destination, output, output_signature)
        verified, read_info = stack.enter_context(avb._input(destination, MAX_OUTPUT))
        _require(avb._signature(read_info) == output_signature, "output changed before readback")
        output_pin = inventory._stream_identity(verified, read_info.st_size)
        readback = _readback(verified, read_info.st_size, wanted, original_comment)
        # Keep all source contexts open until output readback, then rehash them.
        # Earlier copied replacements cannot change unnoticed while later files
        # or aliases are being read. Fresh traversal closes parent-rename gaps.
        _require(inventory._stream_identity(stream, source_info.st_size) == pin,
                 "source archive changed after copy")
        for path, (replacement, signature, expected) in opened.items():
            _require(inventory._stream_identity(replacement, expected["size_bytes"]) == expected,
                     "replacement changed after copy")
            _fresh_guard(path, replacement, signature)
        _require(inventory._stream_identity(verified, read_info.st_size) == output_pin,
                 "output archive changed after readback")
        _fresh_guard(source, stream, source_signature)
        _fresh_guard(destination, output, output_signature)
        free_after = _available(output.fileno())
        _require(free_after >= avb.RESERVE_BYTES, "output free-space reserve was crossed")
        rows = [{"member": name, "before": before[name], "after": wanted[name],
                 "bytes_changed": (before[name]["sha256"], before[name]["size_bytes"]) !=
                                  (wanted[name]["sha256"], wanted[name]["size_bytes"])}
                for name in sorted(selected)]
        changed = sum(row["bytes_changed"] for row in rows)
        return {"schema_version": 1, "operation": "rewrite-selected-target-files-images-v1",
                "status": "passed", "source_archive": {"path": str(source), **pin, **bounds},
                "output_archive": {"path": str(destination), **output_pin, **readback},
                "archive_comment": _identity(original_comment), "member_count": len(members),
                "preserved_member_count": len(members) - len(selected),
                "selected_replacement_count": len(selected), "changed_member_count": changed,
                "identical_replacement_count": len(selected) - changed,
                "source_member_identity_metadata_sha256": source_aggregate,
                "replacement_members": rows, "inputs_unchanged": True,
                "all_members_independently_read_back": True,
                "membership_order_and_semantic_metadata_preserved": True,
                "space": {"output_upper_bound_bytes": output_bound,
                          "reserve_bytes": avb.RESERVE_BYTES,
                          "required_initial_bytes": output_bound + avb.RESERVE_BYTES,
                          "available_initial_bytes": free_before,
                          "available_after_readback_bytes": free_after,
                          "periodic_check_bytes": SPACE_CHECK_BYTES},
                "limits": {"archive_bytes": inventory.MAX_ARCHIVE, "output_bytes": MAX_OUTPUT,
                           "declared_payload_bytes": inventory.MAX_DECLARED_BYTES,
                           "central_directory_bytes": inventory.MAX_CENTRAL_DIRECTORY,
                           "member_count": inventory.MAX_MEMBERS, "chunk_bytes": CHUNK,
                           "selected_image_bytes": budgets},
                "container_changes": ["local record order follows central member order",
                                      "compression bytes and container checksums are regenerated",
                                      "offsets, descriptors, ZIP64 framing, required versions and mechanical flags may change",
                                      "names, filename encodings and non-ZIP64 extras are preserved"],
                "scope": {name: False for name in (
                    "image_format_verified", "signatures_verified", "complete_chain_verified",
                    "fec_payload_verified", "source_provenance_verified",
                    "target_files_compatibility_verified", "physical_partition_fit_verified",
                    "runtime_verified", "complete_rom_ready", "native_commands_run",
                    "private_key_or_local_config_accessed", "guest_accessed", "phone_accessed",
                    "source_archive_or_replacement_files_modified")}}


def rewrite_archive(source: Path, expected_archive: dict, destination: Path,
                    replacements: dict, *, profile: dict) -> dict:
    """Return a completed copy/readback summary or raise ArchiveCopyError.

    Replacement values are exact {path: Path, sha256: str, size_bytes: int}
    objects or {data: bytes}. The digest must be 65 lowercase-hex/newline bytes.
    The caller supplies a pinned public AVB profile; small synthetic budgets are
    useful in offline tests but cannot admit production artifacts by themselves.
    """
    try:
        return _rewrite(source, expected_archive, destination, replacements, profile)
    except ArchiveCopyError:
        raise
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile,
            NotImplementedError, RuntimeError, EOFError, zlib.error) as exc:
        raise ArchiveCopyError(str(exc)) from exc
