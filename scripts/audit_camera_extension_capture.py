#!/usr/bin/env python3
"""Audit a retained CameraExtensionSession receipt and artifact without a phone.

This verifies receipt requirements, artifact bytes and JPEG header dimensions.
It does not independently decode pixels, validate a gain map, or prove the
reported camera callbacks occurred. Those remain separate evidence checks.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct


# Android SDK 36 CameraExtensionCharacteristics constants, not CameraX values.
EXTENSIONS = {"AUTO": 0, "FACE_RETOUCH": 1, "BOKEH": 2, "HDR": 3, "NIGHT": 4}
SOF_MARKERS = frozenset({0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                         0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF})


def jpeg_dimensions(stream):
    """Read the primary JPEG's frame dimensions; do not decode its scan data."""
    def read_exact(length):
        data = stream.read(length)
        if len(data) != length:
            raise ValueError("Truncated JPEG header")
        return data

    if read_exact(2) != b"\xff\xd8":
        raise ValueError("Artifact is not a JPEG codestream")
    while True:
        if read_exact(1) != b"\xff":
            raise ValueError("Invalid JPEG marker boundary")
        marker = read_exact(1)[0]
        while marker == 0xFF:
            marker = read_exact(1)[0]
        if marker in {0, 0xD8}:
            raise ValueError("Invalid JPEG header marker")
        if marker in {0xD9, 0xDA}:
            raise ValueError("JPEG has no frame dimensions before scan/end")
        if marker == 0x01 or 0xD0 <= marker <= 0xD7:
            continue
        length = struct.unpack(">H", read_exact(2))[0]
        if length < 2:
            raise ValueError("Invalid JPEG segment length")
        payload = read_exact(length - 2)
        if marker in SOF_MARKERS:
            if len(payload) < 6:
                raise ValueError("Truncated JPEG frame header")
            precision, height, width, components = struct.unpack(">BHHB", payload[:6])
            if precision == 0 or components == 0 or len(payload) != 6 + 3 * components:
                raise ValueError("Invalid JPEG frame header")
            if width == 0 or height == 0:
                raise ValueError("JPEG frame dimensions must be positive")
            return width, height


def audit(report_path):
    report_path = Path(report_path)
    raw_report = report_path.read_bytes()
    if len(raw_report) > 1024 * 1024:
        raise ValueError("Report exceeds 1 MiB")
    report = json.loads(raw_report)
    if not isinstance(report, dict):
        raise ValueError("Report must be a JSON object")

    def require(condition, message):
        if not condition:
            raise ValueError(message)

    def integer(key, minimum=0):
        value = report.get(key)
        require(type(value) is int and value >= minimum, key + " must be an integer >= " + str(minimum))
        return value

    require(report.get("outcome") == "captured", "Outcome is not captured")
    require(report.get("api") == "CameraExtensionSession", "Wrong capture API")
    require(report.get("admitted") is True, "Probe did not admit the capture")
    require("partial_artifact" not in report, "Partial artifacts cannot be admitted")
    require(isinstance(report.get("camera_id"), str) and report["camera_id"].strip(),
            "Missing exact camera ID")
    name = report.get("extension_name")
    require(name in EXTENSIONS, "Unknown Camera2 extension name")
    require(integer("extension_mode") == EXTENSIONS[name], "Camera2 extension name/number mismatch")
    require(report.get("format") in {"jpeg", "jpeg_r"}, "Unsupported extension output format")
    width, height = integer("width", 1), integer("height", 1)
    require(width * height <= 210_000_000, "Requested dimensions exceed probe limit")
    require(integer("requested_captures") == 1, "Exactly one requested capture is required")
    require(integer("still_requests_submitted") == 1, "Exactly one submitted still is required")
    require(integer("preview_frame_count") >= 8, "Insufficient visible preview frames")
    for key in ("extension_available", "sequence_completed", "process_started", "jpeg_decoded"):
        require(report.get(key) is True, "Missing successful " + key + " proof")
    require(type(report.get("result_metadata_expected")) is bool,
            "Result metadata availability must be explicit")
    if report["result_metadata_expected"]:
        image_timestamp = integer("image_timestamp_ns", 1)
        result_timestamp = integer("result_timestamp_ns", 1)
        require(image_timestamp == result_timestamp, "Image/result sensor timestamps differ")
        require(report.get("timestamp_match") is True, "Missing image/result timestamp match")
    else:
        require(report.get("timestamp_match") is None or report.get("timestamp_match") is False,
                "Unavailable result metadata cannot establish timestamp matching")
    require((integer("jpeg_width", 1), integer("jpeg_height", 1)) == (width, height),
            "Probe JPEG dimensions differ from requested dimensions")
    if report["format"] == "jpeg_r":
        require(report.get("has_gainmap") is True, "JPEG_R requires reported decoded gain map")

    filename = report.get("file_name")
    require(isinstance(filename, str) and filename not in {"", ".", ".."}
            and Path(filename).name == filename and "/" not in filename and "\\" not in filename,
            "Artifact must be a filename within the report directory")
    artifact = report_path.parent / filename
    require(not artifact.is_symlink(), "Artifact symlinks are not admitted")
    require(artifact.is_file(), "Artifact is missing or is not a regular file")
    expected_bytes = integer("file_bytes", 1)
    require(expected_bytes <= 1024 * 1024 * 1024, "Artifact exceeds 1 GiB")
    expected_hash = report.get("file_sha256")
    require(isinstance(expected_hash, str) and len(expected_hash) == 64
            and all(char in "0123456789abcdef" for char in expected_hash), "Invalid artifact SHA-256")
    with artifact.open("rb") as stream:
        stat_before = artifact.stat()
        dimensions = jpeg_dimensions(stream)
        stream.seek(0)
        hasher = hashlib.sha256()
        actual_bytes = 0
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
            actual_bytes += len(chunk)
            require(actual_bytes <= 1024 * 1024 * 1024, "Artifact exceeds 1 GiB")
        stat_after = artifact.stat()
    require((stat_before.st_ino, stat_before.st_size, stat_before.st_mtime_ns)
            == (stat_after.st_ino, stat_after.st_size, stat_after.st_mtime_ns),
            "Artifact changed while being audited")
    require(actual_bytes == expected_bytes, "Artifact byte count differs from receipt")
    require(hasher.hexdigest() == expected_hash, "Artifact SHA-256 differs from receipt")
    require(dimensions == (width, height), "JPEG frame dimensions differ from requested dimensions")
    return {
        "schema_version": 1,
        "receipt_admitted": True,
        "report_sha256": hashlib.sha256(raw_report).hexdigest(),
        "camera_id": report["camera_id"],
        "extension_name": name,
        "extension_mode": report["extension_mode"],
        "format": report["format"],
        "width": width,
        "height": height,
        "artifact": str(artifact),
        "artifact_bytes": actual_bytes,
        "artifact_sha256": hasher.hexdigest(),
        "independent_pixel_decode_verified": False,
        "independent_gainmap_verified": False,
        "camera_callbacks_independently_verified": False,
        "evidence_scope": "Receipt requirements, artifact bytes and primary JPEG frame dimensions only",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path, help="Retained extension capture report.json")
    args = parser.parse_args()
    try:
        result = audit(args.report)
    except (OSError, ValueError, TypeError) as error:
        print(json.dumps({"receipt_admitted": False, "error": str(error)}, indent=2))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
