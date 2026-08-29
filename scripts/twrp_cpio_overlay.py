"""Replace existing newc file contents without extraction or native tools."""

from __future__ import annotations

if __package__:
    from .inspect_twrp_ramdisk import MAX_ARCHIVE_BYTES, RamdiskInspectionError, _archive, _name
else:
    from inspect_twrp_ramdisk import MAX_ARCHIVE_BYTES, RamdiskInspectionError, _archive, _name


class CpioOverlayError(ValueError):
    """The archive or an exact existing-file replacement is not admissible."""


def _require(condition, message):
    if not condition:
        raise CpioOverlayError(message)


def replace_files(data: bytes, replacements: dict[str, tuple[bytes, bytes]]) -> bytes:
    """Replace exact preimages, preserving other frames, metadata and trailer.

    Each mapping value is (expected_old_bytes, replacement_bytes). Only an
    existing regular file with nlink=1 may be selected. Names normalize one
    leading './' using the archive validator's rules. Empty new contents are
    permitted; empty expected preimages are not. No file or device is accessed.
    """
    _require(type(data) is bytes, "archive input must be immutable bytes")
    _require(type(replacements) is dict, "replacements must be a dictionary")
    try:
        members, archive = _archive(data)
        selected, output_size = {}, len(data)
        for path, pair in replacements.items():
            _require(type(path) is str, "replacement path must be a string")
            name = _name(path.encode("utf-8") + b"\0")
            _require(name not in selected, "duplicate normalized replacement path")
            _require(type(pair) is tuple and len(pair) == 2
                     and type(pair[0]) is bytes and type(pair[1]) is bytes,
                     "replacement must be a tuple of two immutable bytes values")
            old, new = pair
            _require(bool(old), "expected preimage must be nonempty")
            _require(name in members, f"replacement path is absent: {name}")
            row = members[name]
            _require(row["kind"] == "regular" and row["nlink"] == 1,
                     f"replacement requires a regular file with nlink=1: {name}")
            start, size = row["offset_bytes"], row["size_bytes"]
            _require(data[start:start + size] == old, f"expected preimage differs: {name}")
            _require(len(new) <= 0xFFFFFFFF, "replacement exceeds newc filesize field")
            output_size += ((len(new) + 3) & ~3) - ((size + 3) & ~3)
            selected[name] = new
        _require(output_size <= MAX_ARCHIVE_BYTES, "replacement archive exceeds size bound")
        parts, position = [], 0
        while position < archive["trailer_offset_bytes"]:
            header = data[position:position + 110]
            size, namesize = int(header[54:62], 16), int(header[94:102], 16)
            name_end = position + 110 + namesize
            name = _name(data[position + 110:name_end])
            content_start = (name_end + 3) & ~3
            frame_end = (content_start + size + 3) & ~3
            if name in selected:
                new = selected[name]
                size_field = header[54:62] if len(new) == size else f"{len(new):08x}".encode("ascii")
                parts.extend((data[position:position + 54], size_field, data[position + 62:content_start],
                              new, bytes((-len(new)) % 4)))
            else:
                parts.append(data[position:frame_end])
            position = frame_end
        parts.append(data[position:])  # Preserve the full trailer and its original zero padding.
        result = b"".join(parts)
        _archive(result)
        return result
    except (RamdiskInspectionError, UnicodeError) as exc:
        raise CpioOverlayError(str(exc)) from exc
