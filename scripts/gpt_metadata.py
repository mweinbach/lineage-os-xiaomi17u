#!/usr/bin/env python3
"""Capture and inspect inert GPT/XML package metadata without applying it."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import sys
import tarfile
import tempfile
import uuid
import xml.etree.ElementTree as ET
import zlib

if __package__:
    from .artifact_files import publish_new_directory
    from .firmware import CHUNK_SIZE, MAX_ARCHIVE_MEMBERS, MAX_METADATA_BYTES, IntakeError, _directory, _open_regular, _signature, _checksum
    from .firmware_images import _existing_directory, _intake
    from .firmware_tar import BoundedReader, BoundedTarInfo, MAX_ARCHIVE_BYTES, MAX_TRAILER_BYTES, _outside_intake, member_name
else:
    from artifact_files import publish_new_directory
    from firmware import CHUNK_SIZE, MAX_ARCHIVE_MEMBERS, MAX_METADATA_BYTES, IntakeError, _directory, _open_regular, _signature, _checksum
    from firmware_images import _existing_directory, _intake
    from firmware_tar import BoundedReader, BoundedTarInfo, MAX_ARCHIVE_BYTES, MAX_TRAILER_BYTES, _outside_intake, member_name


MAX_MEMBER_BYTES = 1024**2
MAX_CAPTURE_BYTES = 2 * 1024**2
SECTOR_BYTES = 4096
MAX_XML_NODES = 1024
MAX_GPT_ENTRIES = 128
UINT64_MAX = 2**64 - 1
GPT_HEADER = struct.Struct("<8sIIIIQQQQ16sQIII")
SAFE_LABEL = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,35}\Z")
SAFE_FILENAME = re.compile(r"(?:[A-Za-z0-9][A-Za-z0-9_.-]{0,127})?\Z")
ALLOWED_NAMES = frozenset(
    [f"gpt_{kind}{lun}.bin" for kind in ("main", "backup", "both", "empty") for lun in range(6)]
    + [f"{kind}{lun}.xml" for kind in ("rawprogram", "patch") for lun in range(6)]
    + ["partition_ext_p1.xml"]
)


def _selected(name):
    parts = name.split("/")
    if (len(parts) in (2, 3) and parts[-2] == "images" and parts[-1] in ALLOWED_NAMES
            and all(part not in ("", ".", "..") and part.isprintable()
                    and "\\" not in part and ":" not in part for part in parts)):
        return "/".join(parts[:-1]), parts[-1]
    return None


def _file_hash(path):
    digest = hashlib.sha256()
    size = 0
    with _open_regular(path) as stream:
        before = _signature(os.fstat(stream.fileno()))
        while block := stream.read(CHUNK_SIZE):
            digest.update(block)
            size += len(block)
        if before != _signature(os.fstat(stream.fileno())) or before != _signature(Path(path).lstat()):
            raise IntakeError("file changed while hashing")
    return digest.hexdigest(), size


def capture_metadata(intake_dir, output_dir, *, expected_sha256):
    """Copy exactly 37 inert names, and verify the complete original TAR/GZIP.

    The XML is data, not instructions: no programmer, patcher, shell or firmware
    executable is invoked. TAR extraction APIs never create files or links.
    """
    expected = _checksum(expected_sha256)
    if expected is None:
        raise IntakeError("expected package SHA256 is required")
    intake_dir = _existing_directory(Path(intake_dir))
    metadata, metadata_raw = _intake(intake_dir, expected)
    output_dir = Path(os.path.abspath(output_dir))
    _outside_intake(output_dir, intake_dir)
    package = intake_dir / metadata["filename"]
    with _open_regular(package) as source:
        signature = _signature(os.fstat(source.fileno()))
        digest = hashlib.sha256()
        while block := source.read(CHUNK_SIZE):
            digest.update(block)
        if signature[2] != metadata["size_bytes"] or digest.hexdigest() != expected:
            raise IntakeError("package size or SHA256 mismatch")
        source.seek(0)
        if source.read(2) != b"\x1f\x8b":
            raise IntakeError("only a gzip-compressed TAR is supported")
        source.seek(0)
        parent = _directory(output_dir.parent)
        if shutil.disk_usage(parent).free < MAX_CAPTURE_BYTES + 64 * 1024**2:
            raise IntakeError("insufficient free space for bounded metadata capture")
        lock = parent / ("." + output_dir.name + ".lock")
        try:
            descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise IntakeError("capture lock exists; existing lock preserved") from exc
        os.close(descriptor)
        staging = None
        try:
            staging = Path(tempfile.mkdtemp(prefix="." + output_dir.name + "-", dir=parent))
            members, files = [], []
            names, prefixes = set(), set()
            selected_bytes = total_member_bytes = 0
            with gzip.GzipFile(fileobj=source, mode="rb") as compressed:
                bounded = BoundedReader(compressed, MAX_ARCHIVE_BYTES)
                with tarfile.open(fileobj=bounded, mode="r|", bufsize=CHUNK_SIZE, tarinfo=BoundedTarInfo) as archive:
                    for entry in archive:
                        if len(members) >= MAX_ARCHIVE_MEMBERS:
                            raise IntakeError("archive member count exceeds limit")
                        name = member_name(entry)
                        if name.casefold() in names:
                            raise IntakeError("duplicate or case-colliding TAR member")
                        names.add(name.casefold())
                        if not (entry.isfile() or entry.isdir()) or entry.issparse():
                            raise IntakeError("TAR links, sparse members and special files are refused")
                        if entry.size < 0 or (entry.isdir() and entry.size):
                            raise IntakeError("invalid TAR member size")
                        total_member_bytes += entry.size
                        if total_member_bytes > MAX_ARCHIVE_BYTES:
                            raise IntakeError("declared archive size exceeds limit")
                        members.append({"name": name, "size_bytes": entry.size, "kind": "directory" if entry.isdir() else "file"})
                        selected = _selected(name) if entry.isfile() else None
                        if selected is None:
                            continue
                        prefix, basename = selected
                        prefixes.add(prefix)
                        if len(prefixes) != 1:
                            raise IntakeError("multiple metadata directories are ambiguous")
                        if not 0 < entry.size <= MAX_MEMBER_BYTES:
                            raise IntakeError("metadata member size exceeds bounds")
                        selected_bytes += entry.size
                        if selected_bytes > MAX_CAPTURE_BYTES:
                            raise IntakeError("total metadata capture exceeds bounds")
                        target = staging / basename
                        checksum = hashlib.sha256()
                        copied = 0
                        with archive.extractfile(entry) as member, target.open("xb") as output:
                            os.chmod(target, 0o600)
                            while block := member.read(CHUNK_SIZE):
                                copied += len(block)
                                if copied > entry.size:
                                    raise IntakeError("metadata expanded beyond declared length")
                                checksum.update(block)
                                output.write(block)
                            output.flush()
                            os.fsync(output.fileno())
                        if copied != entry.size:
                            raise IntakeError("truncated metadata member")
                        readback_hash, readback_size = _file_hash(target)
                        if readback_hash != checksum.hexdigest() or readback_size != copied:
                            raise IntakeError("captured metadata readback mismatch")
                        files.append({"archive_member": name, "path": basename, "size_bytes": copied,
                                      "sha256": checksum.hexdigest(), "readback_verified": True})
                    trailer = 0
                    while block := archive.fileobj.read(CHUNK_SIZE):
                        trailer += len(block)
                        if trailer > MAX_TRAILER_BYTES or any(block):
                            raise IntakeError("unexpected data after TAR end marker")
                    if trailer < tarfile.BLOCKSIZE:
                        raise IntakeError("missing second TAR end marker")
            if {row["path"] for row in files} != ALLOWED_NAMES:
                raise IntakeError("archive does not contain the exact 37-file metadata allowlist")
            if signature != _signature(os.fstat(source.fileno())) or signature != _signature(package.lstat()):
                raise IntakeError("package changed during metadata capture")
            with _open_regular(intake_dir / "metadata.json") as current:
                if current.read(MAX_METADATA_BYTES + 1) != metadata_raw:
                    raise IntakeError("intake metadata changed during capture")
            receipt = {
                "schema_version": 1, "operation": "capture-inert-gpt-xml-allowlist",
                "created_at_utc": datetime.now(timezone.utc).isoformat(),
                "parent_package_sha256": expected,
                "intake_metadata_sha256": hashlib.sha256(metadata_raw).hexdigest(),
                "intake_provenance": metadata,
                "gzip_stream_crc_verified": True, "tar_header_checksums_verified": True,
                "decompressed_archive_bytes": bounded.count,
                "member_count": len(members), "members": members,
                "file_count": len(files), "total_file_bytes": selected_bytes,
                "files": sorted(files, key=lambda row: row["path"]),
                "allowlist": sorted(ALLOWED_NAMES),
                "xml_instructions_applied": False, "firmware_executed": False,
                "device_programmer_extracted_or_executed": False,
                "phone_accessed": False, "physical_phone_geometry_verified": False,
            }
            (staging / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
            publish_new_directory(staging, output_dir)
            staging = None
            return receipt
        finally:
            if staging is not None:
                shutil.rmtree(staging)
            lock.unlink()


def _bounded_file(path, limit):
    """Read a stable regular file; refuse excessive declared or observed sizes."""
    with _open_regular(path) as stream:
        before = _signature(os.fstat(stream.fileno()))
        if not 0 < before[2] <= limit:
            raise IntakeError("metadata file size exceeds bounds")
        data = stream.read(limit + 1)
        if len(data) != before[2] or before != _signature(os.fstat(stream.fileno())):
            raise IntakeError("metadata changed while reading")
        if before != _signature(path.lstat()):
            raise IntakeError("metadata path changed while reading")
    return data, before


def _uint(value, *, maximum=UINT64_MAX):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,20}", value):
        raise IntakeError("expected a bounded unsigned decimal integer")
    number = int(value)
    if number > maximum:
        raise IntakeError("unsigned integer exceeds bounds")
    return number


def _boolean(value):
    if not isinstance(value, str) or value.strip() not in ("true", "false"):
        raise IntakeError("expected a literal XML boolean")
    return value.strip() == "true"


def _label(value):
    if not isinstance(value, str) or not SAFE_LABEL.fullmatch(value):
        raise IntakeError("invalid partition label")
    return value


def _filename_literal(value):
    if not isinstance(value, str) or not SAFE_FILENAME.fullmatch(value):
        raise IntakeError("metadata filename is not an inert basename")
    return value


def _xml(data, tag):
    """Bound XML before building a tree; no DTD, entities or expression engine."""
    if not isinstance(data, bytes) or not 0 < len(data) <= MAX_MEMBER_BYTES:
        raise IntakeError("XML byte size exceeds bounds")
    try:
        text = data.decode("utf-8-sig")
    except UnicodeError as exc:
        raise IntakeError("only UTF-8 XML is supported") from exc
    if "\0" in text or re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        raise IntakeError("XML DTDs, entities and alternate encodings are refused")
    parser = ET.XMLPullParser(events=("start", "end"))
    root, depth, count = None, 0, 0
    try:
        for offset in range(0, len(text), 4096):
            parser.feed(text[offset:offset + 4096])
            for event, node in parser.read_events():
                if event == "start":
                    depth += 1
                    count += 1
                    if root is None:
                        root = node
                    if depth > 4 or count > MAX_XML_NODES or len(node.attrib) > 16:
                        raise IntakeError("XML structure exceeds bounds")
                    if len(node.tag) > 64 or any(
                        len(key) > 64 or len(value) > 512 or not value.isprintable()
                        for key, value in node.attrib.items()
                    ):
                        raise IntakeError("XML names or attribute values exceed bounds")
                else:
                    depth -= 1
        parser.close()
    except ET.ParseError as exc:
        raise IntakeError("invalid metadata XML") from exc
    if root is None or root.tag != tag or root.attrib:
        raise IntakeError("unexpected XML root or root attributes")
    return root


def _attributes(node, tag, required, optional=()):
    if node.tag != tag or len(node) or set(node.attrib) - set(required) - set(optional):
        raise IntakeError("unsupported XML element or attributes")
    if set(required) - set(node.attrib):
        raise IntakeError("missing required XML attributes")
    if (node.text and node.text.strip()) or (node.tail and node.tail.strip()):
        raise IntakeError("unexpected XML text")
    return node.attrib


def _guid_type(value):
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value
    ):
        raise IntakeError("invalid partition type GUID")
    raw = uuid.UUID(value).bytes_le
    # Raw disk/partition identifiers are not needed in inspection output.
    return hashlib.sha256(raw).hexdigest(), not any(raw)


def parse_partition_xml(data):
    root = _xml(data, "configuration")
    children = list(root)
    if (root.text and root.text.strip()) or len(children) != 7:
        raise IntakeError("partition XML must describe exactly six LUNs")
    instructions = children[0]
    if instructions.tag != "parser_instructions" or instructions.attrib or len(instructions):
        raise IntakeError("missing literal partition parser declarations")
    declarations = {}
    for line in (instructions.text or "").splitlines():
        if not line.strip():
            continue
        match = re.fullmatch(r"\s*([A-Z_]+)\s*=\s*([A-Za-z0-9]+)\s*", line)
        if not match or match[1] in declarations:
            raise IntakeError("unsupported or duplicate partition parser declaration")
        declarations[match[1]] = match[2]
    if set(declarations) != {
        "WRITE_PROTECT_BOUNDARY_IN_KB", "SECTOR_SIZE_IN_BYTES",
        "GROW_LAST_PARTITION_TO_FILL_DISK",
    }:
        raise IntakeError("unsupported partition parser declarations")
    if (_uint(declarations["SECTOR_SIZE_IN_BYTES"]) != SECTOR_BYTES
            or _uint(declarations["WRITE_PROTECT_BOUNDARY_IN_KB"]) != 0):
        raise IntakeError("only the captured 4096-byte, zero write-boundary schema is supported")
    growth = _boolean(declarations["GROW_LAST_PARTITION_TO_FILL_DISK"])
    luns = []
    for lun, physical in enumerate(children[1:]):
        if (physical.tag != "physical_partition" or physical.attrib
                or not 1 <= len(physical) <= MAX_GPT_ENTRIES
                or (physical.text and physical.text.strip())
                or (physical.tail and physical.tail.strip())):
            raise IntakeError("invalid physical partition XML")
        rows, labels = [], set()
        for node in physical:
            attrs = _attributes(
                node, "partition",
                ("label", "size_in_kb", "type", "bootable", "readonly"),
                ("filename", "sparse", "system"),
            )
            name = _label(attrs["label"])
            if name in labels:
                raise IntakeError("duplicate partition XML label")
            labels.add(name)
            type_hash, type_zero = _guid_type(attrs["type"])
            size = _uint(attrs["size_in_kb"], maximum=UINT64_MAX // 1024) * 1024
            if size % SECTOR_BYTES:
                raise IntakeError("partition XML size is not sector aligned")
            # This is a package convention crosscheck, not a claim that bit 60
            # means read-only for every UEFI partition type.
            flags = (
                int(_boolean(attrs["system"])) if "system" in attrs else 0
            ) | (int(_boolean(attrs["bootable"])) << 2) | (
                int(_boolean(attrs["readonly"])) << 60
            )
            rows.append({
                "label": name, "requested_size_bytes": size,
                "type_guid_sha256": type_hash, "type_guid_zero": type_zero,
                "attributes_hex": f"0x{flags:016x}",
                "filename": _filename_literal(attrs.get("filename", "")),
                "sparse": _boolean(attrs.get("sparse", "false")),
            })
        luns.append({"lun": lun, "partitions": rows})
    return {"sector_size_bytes": SECTOR_BYTES,
            "grow_last_partition_to_fill_disk": growth,
            "declarations_executed": False, "luns": luns}


def parse_rawprogram_xml(data, lun):
    if type(lun) is not int or not 0 <= lun < 6:
        raise IntakeError("invalid LUN number")
    root = _xml(data, "data")
    if (root.text and root.text.strip()) or not 3 <= len(root) <= MAX_GPT_ENTRIES + 2:
        raise IntakeError("rawprogram entry count exceeds bounds")
    rows, labels = [], set()
    for node in root:
        attrs = _attributes(node, "program", (
            "SECTOR_SIZE_IN_BYTES", "file_sector_offset", "filename", "label",
            "num_partition_sectors", "partofsingleimage", "physical_partition_number",
            "readbackverify", "size_in_KB", "sparse", "start_byte_hex", "start_sector",
        ))
        if (_uint(attrs["SECTOR_SIZE_IN_BYTES"]) != SECTOR_BYTES
                or _uint(attrs["physical_partition_number"]) != lun
                or _uint(attrs["file_sector_offset"]) != 0):
            raise IntakeError("rawprogram sector size, LUN or file offset mismatch")
        label = _label(attrs["label"])
        if label in labels:
            raise IntakeError("duplicate rawprogram label")
        labels.add(label)
        count = _uint(attrs["num_partition_sectors"], maximum=UINT64_MAX // SECTOR_BYTES)
        size_kib = attrs["size_in_KB"]
        if not re.fullmatch(r"[0-9]{1,20}(?:\.0{1,8})?", size_kib):
            raise IntakeError("unsupported rawprogram size expression")
        if _uint(size_kib.split(".")[0]) * 1024 != count * SECTOR_BYTES:
            raise IntakeError("rawprogram size and sector count disagree")
        start = attrs["start_sector"]
        if label == "BackupGPT" and start == "NUM_DISK_SECTORS-5.":
            if attrs["start_byte_hex"] != "(4096*NUM_DISK_SECTORS)-20480.":
                raise IntakeError("backup GPT byte expression mismatch")
            first_lba = None
        else:
            first_lba = _uint(start, maximum=UINT64_MAX // SECTOR_BYTES)
            if (not re.fullmatch(r"0x[0-9a-fA-F]{1,16}", attrs["start_byte_hex"])
                    or int(attrs["start_byte_hex"], 16) != first_lba * SECTOR_BYTES):
                raise IntakeError("rawprogram byte offset and LBA disagree")
        rows.append({
            "label": label, "filename": _filename_literal(attrs["filename"]),
            "first_lba": first_lba, "start_sector_expression": start if first_lba is None else None,
            "sectors": count, "size_bytes": count * SECTOR_BYTES,
            "sparse": _boolean(attrs["sparse"]),
            "part_of_single_image": _boolean(attrs["partofsingleimage"]),
            "package_readbackverify": _boolean(attrs["readbackverify"]),
        })
    return rows


def _patch_sector_literal(value):
    """Recognize a small inert grammar; deliberately never evaluate a formula."""
    if re.fullmatch(r"[0-9]{1,20}", value):
        _uint(value)
        return
    match = re.fullmatch(r"NUM_DISK_SECTORS-([0-9]{1,20})\.?", value)
    if not match or _uint(match[1]) == 0:
        raise IntakeError("unsupported patch sector expression")


def parse_patch_xml(data, lun):
    if type(lun) is not int or not 0 <= lun < 6:
        raise IntakeError("invalid LUN number")
    root = _xml(data, "patches")
    if (root.text and root.text.strip()) or not 1 <= len(root) <= 256:
        raise IntakeError("patch XML entry count exceeds bounds")
    symbolic, crc_requests = 0, 0
    targets = set()
    for node in root:
        attrs = _attributes(node, "patch", (
            "SECTOR_SIZE_IN_BYTES", "byte_offset", "filename",
            "physical_partition_number", "size_in_bytes", "start_sector", "value", "what",
        ))
        if (_uint(attrs["SECTOR_SIZE_IN_BYTES"]) != SECTOR_BYTES
                or _uint(attrs["physical_partition_number"]) != lun):
            raise IntakeError("patch sector size or LUN mismatch")
        if attrs["filename"] not in ("DISK", f"gpt_main{lun}.bin", f"gpt_backup{lun}.bin"):
            raise IntakeError("unsupported inert patch target")
        width = _uint(attrs["size_in_bytes"])
        if width not in (4, 8) or _uint(attrs["byte_offset"]) + width > SECTOR_BYTES:
            raise IntakeError("patch byte range exceeds one sector")
        _patch_sector_literal(attrs["start_sector"])
        value = attrs["value"]
        crc = re.fullmatch(r"CRC32\(([^,()]{1,64}),([0-9]{1,20})\)", value)
        if crc:
            _patch_sector_literal(crc[1])
            if not 0 < _uint(crc[2]) <= MAX_CAPTURE_BYTES:
                raise IntakeError("patch CRC byte count exceeds bounds")
            crc_requests += 1
        else:
            _patch_sector_literal(value)
        symbolic += int("NUM_DISK_SECTORS" in attrs["start_sector"] or "NUM_DISK_SECTORS" in value)
        targets.add(attrs["filename"])
    return {
        "entry_count": len(root), "symbolic_disk_sector_rows": symbolic,
        "crc_recalculation_requests": crc_requests, "targets": sorted(targets),
        "expressions_evaluated": False, "instructions_applied": False,
    }


def _partition_entries(data, count, size):
    entries, labels, identifiers = [], set(), set()
    for index in range(count):
        entry = data[index * size:(index + 1) * size]
        if not any(entry):
            continue
        try:
            decoded = entry[56:128].decode("utf-16-le")
        except UnicodeError as exc:
            raise IntakeError("invalid UTF-16 GPT partition name") from exc
        label, separator, padding = decoded.partition("\0")
        if separator and any(character != "\0" for character in padding):
            raise IntakeError("nonzero bytes after GPT partition name")
        _label(label)
        if label in labels or entry[16:32] in identifiers or not any(entry[16:32]):
            raise IntakeError("duplicate or missing GPT partition identity")
        labels.add(label)
        identifiers.add(entry[16:32])
        first, last, attributes = struct.unpack_from("<QQQ", entry, 32)
        if first > UINT64_MAX // SECTOR_BYTES or last > UINT64_MAX // SECTOR_BYTES:
            raise IntakeError("GPT partition byte offsets exceed supported bounds")
        if last < first and last + 1 != first:
            raise IntakeError("GPT partition has an invalid inverted interval")
        entries.append({
            "index": index, "label": label, "first_lba": first, "last_lba": last,
            "sectors": last - first + 1, "size_bytes": (last - first + 1) * SECTOR_BYTES,
            "attributes_hex": f"0x{attributes:016x}",
            "type_guid_sha256": hashlib.sha256(entry[:16]).hexdigest(),
            "type_guid_zero": not any(entry[:16]),
            "unique_guid_sha256": hashlib.sha256(entry[16:32]).hexdigest(),
        })
    return entries


def parse_gpt_blob(data, kind, *, sector_size=SECTOR_BYTES):
    """Validate the captured fragment format, not a live disk or flash layout."""
    if type(sector_size) is not int or sector_size != SECTOR_BYTES:
        raise IntakeError("only 4096-byte GPT sectors are supported")
    lengths = {"main": 6, "backup": 5, "both": 11, "empty": 6}
    if kind not in lengths or not isinstance(data, bytes) or len(data) != lengths[kind] * sector_size:
        raise IntakeError("unexpected GPT fragment kind or exact length")
    offsets = [sector_size] if kind in ("main", "empty") else (
        [4 * sector_size] if kind == "backup" else [sector_size, 10 * sector_size]
    )
    mbr = None
    if kind != "backup":
        if (data[510:512] != b"\x55\xaa" or data[450] != 0xEE
                or struct.unpack_from("<I", data, 454)[0] != 1
                or any(data[462:510]) or any(data[512:sector_size])):
            raise IntakeError("invalid protective MBR structure")
        mbr = {"signature_verified": True, "protective_type_verified": True,
               "starting_lba": 1, "size_in_lba": struct.unpack_from("<I", data, 458)[0],
               "physical_disk_coverage_verified": False}
    headers = []
    for offset in offsets:
        values = GPT_HEADER.unpack_from(data, offset)
        (signature, revision, header_size, header_crc, reserved, current, alternate,
         first, last, disk_guid, array_lba, count, entry_size, array_crc) = values
        if (signature != b"EFI PART" or revision != 0x10000 or header_size != GPT_HEADER.size
                or reserved != 0 or any(data[offset + header_size:offset + sector_size])):
            raise IntakeError("unsupported GPT header or nonzero reserved bytes")
        header_bytes = bytearray(data[offset:offset + header_size])
        header_bytes[16:20] = b"\0" * 4
        if zlib.crc32(header_bytes) != header_crc:
            raise IntakeError("GPT header CRC32 mismatch")
        if not 1 <= count <= MAX_GPT_ENTRIES or entry_size != 128:
            raise IntakeError("GPT entry array dimensions exceed supported bounds")
        array_offset = offset + (array_lba - current) * sector_size
        expected_offset = 2 * sector_size if offset == sector_size else offset - 4 * sector_size
        if array_offset != expected_offset:
            raise IntakeError("GPT entry LBA does not locate this fragment's array")
        array_bytes = count * entry_size
        array = data[array_offset:array_offset + array_bytes]
        if len(array) != array_bytes or zlib.crc32(array) != array_crc:
            raise IntakeError("GPT entry-array CRC32 mismatch")
        if any(data[array_offset + array_bytes:array_offset + 4 * sector_size]):
            raise IntakeError("nonzero reserved GPT entry-array padding")
        primary = offset == sector_size
        if kind == "empty":
            if (current, alternate, first, last, array_lba, count) != (1, 0, 34, 0, 2, 4):
                raise IntakeError("unrecognized empty GPT template")
        elif (first != 6 or last < first or last > UINT64_MAX // sector_size - 5
              or (current, alternate) != ((1, last + 5) if primary else (last + 5, 1))
              or array_lba != (2 if primary else last + 1)):
            raise IntakeError("GPT primary/backup template geometry is inconsistent")
        if not any(disk_guid):
            raise IntakeError("GPT disk identity is zero")
        entries = _partition_entries(array, count, entry_size)
        headers.append({
            "header_offset_bytes": offset, "header_size_bytes": header_size,
            "revision": revision, "current_lba": current, "alternate_lba": alternate,
            "first_usable_lba": first, "last_usable_lba": last,
            "entry_array_lba": array_lba, "entry_array_offset_bytes": array_offset,
            "entry_count": count, "entry_size_bytes": entry_size,
            "header_crc32": f"{header_crc:08x}", "header_crc32_verified": True,
            "entry_array_crc32": f"{array_crc:08x}", "entry_array_crc32_verified": True,
            "disk_guid_sha256": hashlib.sha256(disk_guid).hexdigest(),
            "entry_array_sha256": hashlib.sha256(array).hexdigest(), "entries": entries,
        })
    if kind == "both":
        left, right = headers
        if (left["entry_array_sha256"] != right["entry_array_sha256"]
                or left["disk_guid_sha256"] != right["disk_guid_sha256"]
                or left["alternate_lba"] != right["current_lba"]
                or right["alternate_lba"] != left["current_lba"]):
            raise IntakeError("combined primary and backup GPT metadata disagree")
    return {"kind": kind, "size_bytes": len(data), "sector_size_bytes": sector_size,
            "protective_mbr": mbr, "headers": headers,
            "empty_template": kind == "empty",
            "usable_physical_disk_geometry_verified": False}


def analyze_metadata(blobs):
    if set(blobs) != ALLOWED_NAMES:
        raise IntakeError("inspection needs the exact 37-file metadata allowlist")
    layout = parse_partition_xml(blobs["partition_ext_p1.xml"])
    luns = []
    for lun, configured in enumerate(layout["luns"]):
        parsed = {kind: parse_gpt_blob(blobs[f"gpt_{kind}{lun}.bin"], kind)
                  for kind in ("main", "backup", "both", "empty")}
        main, backup = parsed["main"]["headers"][0], parsed["backup"]["headers"][0]
        if blobs[f"gpt_both{lun}.bin"] != blobs[f"gpt_main{lun}.bin"] + blobs[f"gpt_backup{lun}.bin"]:
            raise IntakeError("combined GPT bytes differ from main plus backup fragments")
        if (main["entry_array_sha256"] != backup["entry_array_sha256"]
                or main["disk_guid_sha256"] != backup["disk_guid_sha256"]
                or main["alternate_lba"] != backup["current_lba"]
                or backup["alternate_lba"] != main["current_lba"]
                or main["first_usable_lba"] != backup["first_usable_lba"]
                or main["last_usable_lba"] != backup["last_usable_lba"]):
            raise IntakeError("main and backup GPT disagree")
        raw = parse_rawprogram_xml(blobs[f"rawprogram{lun}.xml"], lun)
        patches = parse_patch_xml(blobs[f"patch{lun}.xml"], lun)
        rows = configured["partitions"]
        if [row["label"] for row in raw] != [row["label"] for row in rows] + ["PrimaryGPT", "BackupGPT"]:
            raise IntakeError("rawprogram partition order differs from partition XML")
        if [row["label"] for row in main["entries"]] != [row["label"] for row in rows]:
            raise IntakeError("GPT partition order differs from partition XML")
        primary_program, backup_program = raw[-2:]
        for program, label, name, start, count in (
            (primary_program, "PrimaryGPT", f"gpt_main{lun}.bin", 0, 6),
            (backup_program, "BackupGPT", f"gpt_backup{lun}.bin", None, 5),
        ):
            if (program["label"] != label or program["filename"] != name
                    or program["first_lba"] != start or program["sectors"] != count
                    or not program["part_of_single_image"] or program["sparse"]):
                raise IntakeError("rawprogram GPT fragment mapping mismatch")
        partitions, next_lba, placeholders = [], main["first_usable_lba"], 0
        for index, (entry, xml, program) in enumerate(zip(main["entries"], rows, raw[:-2])):
            if (entry["index"] != index or entry["type_guid_sha256"] != xml["type_guid_sha256"]
                    or entry["attributes_hex"] != xml["attributes_hex"]
                    or entry["first_lba"] != next_lba
                    or program["first_lba"] != entry["first_lba"]
                    or program["sectors"] != entry["sectors"]
                    or program["filename"] != xml["filename"]
                    or program["sparse"] != xml["sparse"] or program["part_of_single_image"]):
                raise IntakeError("GPT/XML partition identity, offset, size or attributes disagree")
            if entry["sectors"] == 0:
                if (not layout["grow_last_partition_to_fill_disk"] or index != len(rows) - 1
                        or entry["last_lba"] != main["last_usable_lba"]):
                    raise IntakeError("zero-sized GPT entry is not a terminal growth placeholder")
                placeholders += 1
                role = "unresolved-growth-placeholder"
            else:
                if (entry["type_guid_zero"] or entry["size_bytes"] != xml["requested_size_bytes"]
                        or entry["last_lba"] > main["last_usable_lba"]):
                    raise IntakeError("finite GPT/XML partition extent is inconsistent")
                role = "finite-package-extent"
                next_lba = entry["last_lba"] + 1
            partitions.append({
                key: entry[key] for key in
                ("index", "label", "first_lba", "last_lba", "sectors", "size_bytes",
                 "attributes_hex", "type_guid_zero")
            } | {"role": role, "xml_requested_size_bytes": xml["requested_size_bytes"],
                 "filename": program["filename"], "sparse": program["sparse"],
                 "physical_phone_capacity_verified": False})
        if next_lba != main["last_usable_lba"] + 1:
            raise IntakeError("GPT finite partitions do not cover the declared template range")
        empty = parsed["empty"]["headers"][0]
        if (len(empty["entries"]) != 1 or empty["entries"][0]["label"] != "empty"
                or not empty["entries"][0]["type_guid_zero"]):
            raise IntakeError("unrecognized unused empty-template entry")
        luns.append({
            "lun": lun, "sector_size_bytes": SECTOR_BYTES,
            "primary_backup_entry_arrays_identical": True, "combined_fragment_bytes_match": True,
            "header_entry_crc_pairs_verified": sum(len(item["headers"]) for item in parsed.values()),
            "gpt_entry_capacity": main["entry_count"],
            "finite_partition_count": len(partitions) - placeholders,
            "growth_placeholder_count": placeholders,
            "template_last_usable_lba": main["last_usable_lba"],
            "template_backup_header_lba": backup["current_lba"],
            "template_disk_size_is_phone_capacity": False,
            "empty_template_has_valid_usable_lba_range": False,
            "empty_template_active_partition_count": 0,
            "partitions": partitions, "gpt": parsed, "patch_xml": patches,
        })
    return {
        "schema_version": 1, "operation": "inspect-inert-gpt-xml-package-geometry",
        "sector_size_bytes": SECTOR_BYTES, "lun_count": len(luns),
        "finite_partition_count": sum(lun["finite_partition_count"] for lun in luns),
        "growth_placeholder_count": sum(lun["growth_placeholder_count"] for lun in luns),
        "header_entry_crc_pairs_verified": sum(lun["header_entry_crc_pairs_verified"] for lun in luns),
        "partition_xml_declarations": {
            key: value for key, value in layout.items() if key != "luns"
        },
        "luns": luns, "xml_instructions_applied": False,
        "firmware_executed": False, "phone_accessed": False,
        "physical_phone_geometry_verified": False, "flashable_gpt_admitted": False,
    }


def inspect_metadata(capture_dir, output_dir, *, expected_sha256, expected_capture_sha256):
    """Bind a bounded static inspection to a previously verified capture."""
    expected, capture_hash = _checksum(expected_sha256), _checksum(expected_capture_sha256)
    if expected is None or capture_hash is None:
        raise IntakeError("expected package and capture-receipt SHA256 values are required")
    capture_dir = _existing_directory(Path(capture_dir))
    output_dir = Path(os.path.abspath(output_dir))
    _outside_intake(output_dir, capture_dir)
    receipt_bytes, receipt_signature = _bounded_file(capture_dir / "receipt.json", MAX_METADATA_BYTES)
    if hashlib.sha256(receipt_bytes).hexdigest() != capture_hash:
        raise IntakeError("capture receipt SHA256 mismatch")
    try:
        capture = json.loads(receipt_bytes)
    except (ValueError, UnicodeError) as exc:
        raise IntakeError("invalid capture receipt JSON") from exc
    if (not isinstance(capture, dict) or type(capture.get("schema_version")) is not int
            or capture["schema_version"] != 1
            or capture.get("operation") != "capture-inert-gpt-xml-allowlist"
            or capture.get("parent_package_sha256") != expected
            or capture.get("allowlist") != sorted(ALLOWED_NAMES)
            or type(capture.get("file_count")) is not int or capture["file_count"] != len(ALLOWED_NAMES)
            or not isinstance(capture.get("files"), list) or len(capture["files"]) != len(ALLOWED_NAMES)
            or capture.get("gzip_stream_crc_verified") is not True
            or capture.get("tar_header_checksums_verified") is not True
            or any(capture.get(key) is not False for key in (
                "xml_instructions_applied", "firmware_executed",
                "device_programmer_extracted_or_executed", "phone_accessed",
                "physical_phone_geometry_verified",
            ))):
        raise IntakeError("capture receipt does not establish the required bounded capture")
    provenance = capture.get("intake_provenance")
    if not isinstance(provenance, dict) or provenance.get("sha256") != expected:
        raise IntakeError("capture provenance is not bound to the package")
    blobs, snapshots, inputs, prefixes = {}, {}, [], set()
    total = 0
    for row in capture["files"]:
        if not isinstance(row, dict):
            raise IntakeError("invalid capture file row")
        name = row.get("path")
        if not isinstance(name, str) or name not in ALLOWED_NAMES or name in blobs:
            raise IntakeError("capture filenames are duplicated or outside the allowlist")
        if (type(row.get("size_bytes")) is not int or not 0 < row["size_bytes"] <= MAX_MEMBER_BYTES
                or not isinstance(row.get("sha256"), str) or _checksum(row["sha256"]) != row["sha256"]
                or row.get("readback_verified") is not True
                or not isinstance(row.get("archive_member"), str)):
            raise IntakeError("invalid capture file size, hash or verification")
        selected = _selected(row["archive_member"])
        if selected is None or selected[1] != name:
            raise IntakeError("capture member path does not match its basename")
        prefixes.add(selected[0])
        if len(prefixes) != 1:
            raise IntakeError("capture members have ambiguous directories")
        total += row["size_bytes"]
        if total > MAX_CAPTURE_BYTES:
            raise IntakeError("capture byte total exceeds bounds")
        data, signature = _bounded_file(capture_dir / name, MAX_MEMBER_BYTES)
        if len(data) != row["size_bytes"] or hashlib.sha256(data).hexdigest() != row["sha256"]:
            raise IntakeError("captured file size or SHA256 mismatch")
        blobs[name], snapshots[name] = data, signature
        inputs.append({key: row[key] for key in ("path", "size_bytes", "sha256")})
    if type(capture.get("total_file_bytes")) is not int or capture["total_file_bytes"] != total:
        raise IntakeError("capture total-file byte count mismatch")
    analysis = analyze_metadata(blobs)
    parent = _directory(output_dir.parent)
    lock = parent / ("." + output_dir.name + ".lock")
    try:
        descriptor = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise IntakeError("inspection lock exists; existing lock preserved") from exc
    os.close(descriptor)
    staging = None
    try:
        staging = Path(tempfile.mkdtemp(prefix="." + output_dir.name + "-", dir=parent))
        analysis_bytes = (json.dumps(analysis, indent=2, sort_keys=True) + "\n").encode()
        with (staging / "analysis.json").open("xb") as stream:
            os.chmod(stream.name, 0o600)
            stream.write(analysis_bytes)
            stream.flush()
            os.fsync(stream.fileno())
        # Re-open all 37 inputs and their receipt. Atomic publication never
        # reports a changed source as the same immutable input snapshot.
        _existing_directory(capture_dir)
        for name, old_signature in snapshots.items():
            current, signature = _bounded_file(capture_dir / name, MAX_MEMBER_BYTES)
            if signature != old_signature or current != blobs[name]:
                raise IntakeError("captured metadata changed during inspection")
        current, signature = _bounded_file(capture_dir / "receipt.json", MAX_METADATA_BYTES)
        if current != receipt_bytes or signature != receipt_signature:
            raise IntakeError("capture receipt changed during inspection")
        readback, _ = _bounded_file(staging / "analysis.json", 16 * MAX_CAPTURE_BYTES)
        if readback != analysis_bytes:
            raise IntakeError("analysis output readback mismatch")
        script_hash, script_size = _file_hash(Path(__file__).resolve())
        result = {
            "schema_version": 1, "operation": analysis["operation"],
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "parent_package_sha256": expected, "capture_receipt_sha256": capture_hash,
            "source_kind": provenance.get("source_kind"),
            "source_url": provenance.get("source_url"),
            "origin_verified": provenance.get("origin_verified"),
            "script_sha256": script_hash, "script_size_bytes": script_size,
            "inputs": sorted(inputs, key=lambda row: row["path"]),
            "input_count": len(inputs), "total_input_bytes": total,
            "input_hashes_and_identity_rechecked": True,
            "output": {"path": "analysis.json", "size_bytes": len(analysis_bytes),
                       "sha256": hashlib.sha256(analysis_bytes).hexdigest(),
                       "readback_verified": True},
            "xml_instructions_applied": False, "firmware_executed": False,
            "phone_accessed": False, "physical_phone_geometry_verified": False,
            "flashable_gpt_admitted": False,
        }
        (staging / "receipt.json").write_text(json.dumps(result, indent=2) + "\n")
        publish_new_directory(staging, output_dir)
        staging = None
        return result
    finally:
        if staging is not None:
            shutil.rmtree(staging)
        lock.unlink()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)
    capture = sub.add_parser("capture", help="copy only the fixed inert metadata allowlist")
    capture.add_argument("--intake", type=Path, required=True)
    capture.add_argument("--expected-sha256", required=True)
    capture.add_argument("--output", type=Path, required=True)
    inspect = sub.add_parser("inspect", help="validate captured GPT/XML without evaluating patch instructions")
    inspect.add_argument("--capture", type=Path, required=True)
    inspect.add_argument("--expected-sha256", required=True)
    inspect.add_argument("--expected-capture-sha256", required=True)
    inspect.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == "capture":
            result = capture_metadata(args.intake, args.output, expected_sha256=args.expected_sha256)
        else:
            result = inspect_metadata(args.capture, args.output, expected_sha256=args.expected_sha256,
                                      expected_capture_sha256=args.expected_capture_sha256)
    except (IntakeError, OSError, EOFError, tarfile.TarError) as exc:
        print(f"GPT metadata: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"output": str(args.output),
                      "file_count": result.get("file_count", result.get("input_count")),
                      "parent_package_sha256": result["parent_package_sha256"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
