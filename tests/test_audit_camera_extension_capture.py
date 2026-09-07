"""Offline behavior tests for receipt auditing, using synthetic JPEG headers."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "audit_camera_extension_capture", ROOT / "scripts/audit_camera_extension_capture.py")
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


def synthetic_jpeg(width=64, height=48, marker=0xC0):
    # Only a header fixture: its successful audit must never claim pixel decode.
    frame = struct.pack(">BHHB", 8, height, width, 1) + b"\x01\x11\x00"
    return (b"\xff\xd8\xff\xe1\x00\x06test\xff" + bytes([marker])
            + struct.pack(">H", len(frame) + 2) + frame + b"\xff\xd9")


class ExtensionReceiptAuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.artifact = self.directory / "capture.jpg"
        self.artifact.write_bytes(synthetic_jpeg())
        self.report_path = self.directory / "report.json"
        self.report = {
            "outcome": "captured", "api": "CameraExtensionSession", "admitted": True,
            "camera_id": "0", "extension_name": "HDR", "extension_mode": 3,
            "format": "jpeg", "width": 64, "height": 48,
            "requested_captures": 1, "still_requests_submitted": 1,
            "extension_available": True, "preview_frame_count": 8,
            "sequence_completed": True, "process_started": True,
            "result_metadata_expected": True, "timestamp_match": True,
            "image_timestamp_ns": 123456, "result_timestamp_ns": 123456,
            "file_name": "capture.jpg", "file_bytes": self.artifact.stat().st_size,
            "file_sha256": hashlib.sha256(self.artifact.read_bytes()).hexdigest(),
            "jpeg_width": 64, "jpeg_height": 48, "jpeg_decoded": True,
            "has_gainmap": False,
        }

    def run_audit(self):
        self.report_path.write_text(json.dumps(self.report))
        return AUDIT.audit(self.report_path)

    def test_admits_matching_receipt_bytes_and_dimensions_without_claiming_decode(self):
        result = self.run_audit()
        self.assertTrue(result["receipt_admitted"])
        self.assertEqual(result["artifact_sha256"], hashlib.sha256(self.artifact.read_bytes()).hexdigest())
        self.assertFalse(result["independent_pixel_decode_verified"])
        self.assertFalse(result["independent_gainmap_verified"])
        self.assertFalse(result["camera_callbacks_independently_verified"])

    def test_accepts_explicitly_unavailable_result_metadata_without_match_claim(self):
        self.report["result_metadata_expected"] = False
        self.report["timestamp_match"] = None
        del self.report["image_timestamp_ns"]
        del self.report["result_timestamp_ns"]
        self.assertTrue(self.run_audit()["receipt_admitted"])
        self.report["timestamp_match"] = True
        with self.assertRaisesRegex(ValueError, "Unavailable result metadata"):
            self.run_audit()

    def test_rejects_missing_callback_proof_cancelled_partial_or_multishot(self):
        for key, value in (("outcome", "cancelled"), ("admitted", False),
                           ("partial_artifact", {}), ("requested_captures", 2),
                           ("still_requests_submitted", 0), ("preview_frame_count", 7),
                           ("process_started", False), ("sequence_completed", False),
                           ("extension_available", False), ("jpeg_decoded", False)):
            with self.subTest(key=key):
                original = dict(self.report)
                self.report[key] = value
                with self.assertRaises(ValueError):
                    self.run_audit()
                self.report = original

    def test_rejects_camerax_numbering_and_boolean_counts(self):
        self.report["extension_mode"] = 2  # CameraX HDR; Camera2 2 means BOKEH.
        with self.assertRaisesRegex(ValueError, "name/number mismatch"):
            self.run_audit()
        self.report["extension_mode"] = 3
        self.report["still_requests_submitted"] = True
        with self.assertRaisesRegex(ValueError, "must be an integer"):
            self.run_audit()

    def test_recomputes_timestamp_equality(self):
        self.report["result_timestamp_ns"] += 1
        with self.assertRaisesRegex(ValueError, "timestamps differ"):
            self.run_audit()

    def test_recomputes_artifact_size_hash_and_frame_dimensions(self):
        for key, value, message in (("file_bytes", 1, "byte count"),
                                    ("file_sha256", "0" * 64, "SHA-256")):
            with self.subTest(key=key):
                original = self.report[key]
                self.report[key] = value
                with self.assertRaisesRegex(ValueError, message):
                    self.run_audit()
                self.report[key] = original
        self.report["width"] = self.report["jpeg_width"] = 65
        with self.assertRaisesRegex(ValueError, "frame dimensions"):
            self.run_audit()

    def test_jpeg_r_requires_reported_gainmap_and_retains_independent_check_limit(self):
        self.report["format"] = "jpeg_r"
        with self.assertRaisesRegex(ValueError, "gain map"):
            self.run_audit()
        self.report["has_gainmap"] = True
        self.assertFalse(self.run_audit()["independent_gainmap_verified"])

    def test_rejects_escaping_artifact_names_and_symlinks(self):
        for name in ("../capture.jpg", "/tmp/capture.jpg", "sub/capture.jpg", "..", "x\\capture.jpg"):
            with self.subTest(name=name):
                self.report["file_name"] = name
                with self.assertRaisesRegex(ValueError, "within the report directory"):
                    self.run_audit()
        self.report["file_name"] = "linked.jpg"
        (self.directory / "linked.jpg").symlink_to(self.artifact)
        with self.assertRaisesRegex(ValueError, "symlinks"):
            self.run_audit()

    def test_header_parser_handles_progressive_and_rejects_truncation(self):
        self.assertEqual(AUDIT.jpeg_dimensions(io.BytesIO(synthetic_jpeg(19, 17, 0xC2))), (19, 17))
        for data in (b"not jpeg", b"\xff\xd8\xff\xd9", b"\xff\xd8\xff\xe1\x00\x01",
                     synthetic_jpeg()[:14], synthetic_jpeg(0, 48)):
            with self.subTest(data=data):
                with self.assertRaises(ValueError):
                    AUDIT.jpeg_dimensions(io.BytesIO(data))


if __name__ == "__main__":
    unittest.main()
