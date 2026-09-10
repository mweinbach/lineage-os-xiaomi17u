"""The MPEG4Writer length-prefixed-NAL fix: algorithm correctness/safety and patch/contract pins.

The conversion below is a faithful port of ConvertLengthPrefixedNalToAnnexB in
patches/evolution/nezha-hevc-length-prefixed-nal.patch. Keep the two in step.
"""

import hashlib
import json
import random
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "patches/evolution/nezha-hevc-length-prefixed-nal.json"
PATCH = ROOT / "patches/evolution/nezha-hevc-length-prefixed-nal.patch"


def convert_length_prefixed_to_annexb(data: bytearray) -> bool:
    """Port of the C++ helper: returns True and rewrites 4-byte length prefixes to 4-byte
    Annex-B start codes iff the whole buffer is a valid length-prefixed NAL chain."""
    size = len(data)
    if size < 6:
        return False
    offset = 0
    nal_count = 0
    while offset + 4 <= size:
        length = (data[offset] << 24) | (data[offset + 1] << 16) | (data[offset + 2] << 8) | data[offset + 3]
        if length < 2 or length > size - offset - 4 or (data[offset + 4] & 0x80) != 0:
            return False
        offset += 4 + length
        nal_count += 1
    if offset != size or nal_count == 0:
        return False
    offset = 0
    while offset < size:
        length = (data[offset] << 24) | (data[offset + 1] << 16) | (data[offset + 2] << 8) | data[offset + 3]
        data[offset:offset + 4] = b"\x00\x00\x00\x01"
        offset += 4 + length
    return True


def _nal(header: int, payload_len: int, fill: int = 0xAB) -> bytes:
    return bytes([header, 0x01]) + bytes([fill]) * payload_len


def _length_prefixed(nals) -> bytearray:
    out = bytearray()
    for n in nals:
        out += len(n).to_bytes(4, "big") + n
    return out


def _annexb(nals) -> bytearray:
    out = bytearray()
    for n in nals:
        out += b"\x00\x00\x00\x01" + n
    return out


def _annexb_split(data: bytes):
    """Recover NAL units the way MPEG4Writer's Annex-B path does (leading start code stripped)."""
    n = len(data)

    def sc(j):
        if data[j:j + 4] == b"\x00\x00\x00\x01":
            return 4
        if data[j:j + 3] == b"\x00\x00\x01":
            return 3
        return 0

    assert sc(0), "no leading start code"
    i = sc(0)
    start = i
    nals = []
    while i < n:
        s = sc(i)
        if s:
            nals.append(bytes(data[start:i]))
            i += s
            start = i
        else:
            i += 1
    nals.append(bytes(data[start:]))
    return nals


class AlgorithmTests(unittest.TestCase):
    def test_annexb_input_is_never_touched(self):
        buf = _annexb([_nal(0x40, 10), _nal(0x26, 300)])
        before = bytes(buf)
        self.assertFalse(convert_length_prefixed_to_annexb(buf))
        self.assertEqual(bytes(buf), before)

    def test_crash_trigger_nal_length_256_to_511_is_converted_and_splits_exactly(self):
        # A 300-byte NAL has a length prefix 00 00 01 2C, which the start-code scanner
        # misreads as a 3-byte start code -> the underflow/overflow the fix removes.
        nals = [_nal(0x40, 20), _nal(0x42, 50), _nal(0x44, 8), _nal(0x26, 298)]
        buf = _length_prefixed(nals)
        self.assertGreaterEqual(bytes(buf).count(b"\x00\x00\x01"), 1)  # a false start code is present
        self.assertTrue(convert_length_prefixed_to_annexb(buf))
        self.assertEqual(_annexb_split(bytes(buf)), nals)  # downstream recovers the exact NALs

    def test_single_nal_round_trips(self):
        nals = [_nal(0x26, 5000)]
        buf = _length_prefixed(nals)
        self.assertTrue(convert_length_prefixed_to_annexb(buf))
        self.assertEqual(_annexb_split(bytes(buf)), nals)

    def test_malformed_buffers_are_rejected_unchanged(self):
        for buf in (
            _length_prefixed([_nal(0x40, 10)]) + bytearray(b"\x00\x00"),   # trailing garbage
            bytearray(b"\x00\x00\x00\x00" + b"\xAB" * 4),                    # zero length
            _length_prefixed([bytes([0x80, 0x01]) + b"\xAB" * 10]),         # forbidden_zero_bit set
            bytearray(b"\x00\x00\x00"),                                       # too short
        ):
            before = bytes(buf)
            self.assertFalse(convert_length_prefixed_to_annexb(buf))
            self.assertEqual(bytes(buf), before)

    def test_random_annexb_never_false_positive(self):
        rng = random.Random(1234)
        false_positives = 0
        for _ in range(20000):
            nals = []
            for _ in range(rng.randint(1, 5)):
                nals.append(bytes([rng.randint(0, 0x7F), rng.randint(0, 255)])
                            + bytes(rng.randint(0, 255) for _ in range(rng.randint(2, 40))))
            buf = _annexb(nals)
            if convert_length_prefixed_to_annexb(buf):
                false_positives += 1
        self.assertEqual(false_positives, 0)


class PatchContractTests(unittest.TestCase):
    def test_patch_hash_and_target_match_the_contract(self):
        contract = json.loads(CONTRACT.read_text())
        patch_bytes = PATCH.read_bytes()
        self.assertEqual(hashlib.sha256(patch_bytes).hexdigest(), contract["patch_sha256"])
        self.assertEqual(contract["file"]["path"], "frameworks/av/media/libstagefright/MPEG4Writer.cpp")
        text = patch_bytes.decode()
        self.assertIn("+++ b/frameworks/av/media/libstagefright/MPEG4Writer.cpp", text)
        self.assertIn("+static bool ConvertLengthPrefixedNalToAnnexB", text)
        self.assertIn("vendor.qti-ext-enc-nal-length-bs", text)
        # the conversion call is added right before the existing StripStartcode(copy) context line
        self.assertIn("+            ConvertLengthPrefixedNalToAnnexB(", text)
        self.assertIn("             StripStartcode(copy);", text)

    def test_contract_records_the_cause_and_gate(self):
        contract = json.loads(CONTRACT.read_text())
        self.assertEqual(contract["problem"]["evidence"]["fortify_count"], "18446744073709551615")
        self.assertIn("num-bytes = 4", contract["problem"]["evidence"]["encoder_output_format_key"])
        self.assertTrue(contract["activation_allowed"])
        self.assertRegex(contract["file"]["before_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(contract["file"]["after_sha256"], r"^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
