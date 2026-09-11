"""The Now Playing music-trigger shim: patch/template identity, the exact HAL-chain edit, and the
Qualcomm ACD wire format the Java constants encode. Offline; no device and no Android source needed."""
import hashlib
import json
from pathlib import Path
import re
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = json.loads((ROOT / "config/nezha-now-playing-trigger.json").read_text())
TEMPLATE = ROOT / "templates/now-playing-trigger/NezhaMusicTriggerHal.java"
PATCH = ROOT / "patches/evolution/nezha-now-playing-trigger.patch"
SHIM = ("frameworks/base/services/voiceinteraction/java/com/android/server/"
        "soundtrigger_middleware/NezhaMusicTriggerHal.java")
MODULE = ("frameworks/base/services/voiceinteraction/java/com/android/server/"
          "soundtrigger_middleware/SoundTriggerModule.java")


def section(path):
    """The unified-diff section of the patch that touches one file."""
    for chunk in PATCH.read_text().split("diff --git ")[1:]:
        if chunk.splitlines()[0] == f"a/{path} b/{path}":
            return chunk
    raise AssertionError("no diff section for " + path)


def java_int(name):
    """A static int constant from the authored shim, decimal or hex."""
    match = re.search(rf"static final int {name} = (0x[0-9a-fA-F]+|\d+);", TEMPLATE.read_text())
    assert match, name
    return int(match.group(1), 0)


class ContractTests(unittest.TestCase):
    def test_patch_and_template_hashes(self):
        self.assertEqual(hashlib.sha256(PATCH.read_bytes()).hexdigest(), CONTRACT["patch_sha256"])
        for path, row in CONTRACT["authored_templates"].items():
            data = (ROOT / path).read_bytes()
            self.assertEqual(hashlib.sha256(data).hexdigest(), row["sha256"])
            self.assertEqual(len(data), row["size_bytes"])

    def test_the_patch_reconstructs_the_authored_shim_exactly(self):
        lines = section(SHIM).splitlines(keepends=True)
        starts = [i for i, line in enumerate(lines) if line.startswith("@@ ")]
        self.assertEqual(len(starts), 1)
        match = re.fullmatch(r"@@ -0,0 \+1,(\d+) @@\n", lines[starts[0]])
        self.assertIsNotNone(match)
        body = lines[starts[0] + 1:]
        self.assertTrue(all(line.startswith("+") for line in body))
        self.assertEqual(len(body), int(match.group(1)))
        data = "".join(line[1:] for line in body).encode()
        self.assertEqual(data, TEMPLATE.read_bytes())
        row = CONTRACT["files"][SHIM]
        self.assertIsNone(row["before_sha256"])
        self.assertEqual(hashlib.sha256(data).hexdigest(), row["after_sha256"])
        self.assertEqual(len(data), row["after_bytes"])

    def test_the_only_framework_edit_wraps_the_hal_factory(self):
        body = section(MODULE).splitlines()
        removed = [line[1:] for line in body if line.startswith("-") and not line.startswith("---")]
        added = [line[1:] for line in body if line.startswith("+") and not line.startswith("+++")]
        self.assertEqual(removed, ["                            new SoundTriggerDuplicateModelHandler(mHalFactory.create())));"])
        self.assertEqual(added, ["                            new SoundTriggerDuplicateModelHandler(",
                                 "                                NezhaMusicTriggerHal.wrap(mHalFactory.create()))));"])
        # The shim sits below the enforcer, so a refusal it raises is recoverable rather than a reboot.
        self.assertEqual(len(added) - len(removed), CONTRACT["files"][MODULE]["added_lines"])
        self.assertIn("RecoverableException(Status.OPERATION_NOT_SUPPORTED", TEMPLATE.read_text())

    def test_modes_and_selector_agree_with_the_shim(self):
        java = TEMPLATE.read_text()
        self.assertIn(f'PROP_MODE = "{CONTRACT["selector"]}"', java)
        for mode in CONTRACT["fix"]["modes"]:
            self.assertIn(f'MODE_{mode.upper()} = "{mode}"', java)
        # Anything unrecognized must fall back to the safe mode.
        self.assertRegex(java, r"return MODE_OFF;\n\s*\}")


class AcdWireFormatTests(unittest.TestCase):
    """Recompute the packed PAL payloads from the shim's own constants."""

    def test_recognition_config_bytes_match_the_reviewed_layout(self):
        example = CONTRACT["wire_format"]["recognition_config_example"]
        payload = struct.pack(
            "<IIIIIII",
            java_int("ST_PARAM_KEY_CONTEXT_RECOGNITION_INFO"),
            20,  # st_param_header.payload_size: acd_recognition_cfg + one acd_per_context_cfg
            java_int("ACD_RECOGNITION_CFG_VERSION"),
            1,   # num_contexts
            java_int("ACD_CONTEXT_AMBIENCE_MUSIC"),
            example["threshold"],
            example["step_size"])
        self.assertEqual(payload.hex(), example["hex"])
        self.assertEqual(len(payload), 28)
        self.assertEqual(java_int("ST_PARAM_KEY_CONTEXT_RECOGNITION_INFO"),
                         CONTRACT["wire_format"]["st_param_key_context_recognition_info"])
        self.assertEqual(java_int("ACD_CONTEXT_AMBIENCE_MUSIC"),
                         CONTRACT["wire_format"]["context_id_ambience_music"])

    def test_event_payload_parses_to_the_music_context(self):
        example = CONTRACT["wire_format"]["event_example"]
        raw = bytes.fromhex(example["hex"])
        key, payload_size, version, timestamp, contexts = struct.unpack_from("<IIIQI", raw, 0)
        self.assertEqual(key, java_int("ST_PARAM_KEY_CONTEXT_EVENT_INFO"))
        self.assertEqual(key, CONTRACT["wire_format"]["st_param_key_context_event_info"])
        self.assertEqual(version, java_int("ACD_RECOGNITION_CFG_VERSION"))
        self.assertEqual(contexts, 1)
        # acd_context_event is 16 packed bytes; each acd_per_context_event_info is 20.
        self.assertEqual(payload_size, 16 + 20 * contexts)
        self.assertEqual(len(raw), 8 + payload_size)
        context_id, event_type, confidence, _ts = struct.unpack_from("<IIIQ", raw, 8 + 16)
        self.assertEqual(context_id, java_int("ACD_CONTEXT_AMBIENCE_MUSIC"))
        self.assertEqual(event_type, java_int("ACD_EVENT_STARTED"))
        self.assertEqual(confidence, example["confidence_score"])
        self.assertEqual(timestamp, struct.unpack_from("<Q", raw, 8 + 16 + 12)[0])

    def test_the_shim_reads_the_same_offsets_it_writes(self):
        java = TEMPLATE.read_text()
        # The parser must skip the 16-byte acd_context_event header and step 20 bytes per context.
        self.assertIn("b.getInt(); // acd_context_event.version", java)
        self.assertIn("b.getLong(); // detection_ts", java)
        self.assertIn("b.remaining() >= 20", java)
        self.assertIn("b.getLong(); // per-context detection_ts", java)
        self.assertIn("ByteOrder.LITTLE_ENDIAN", java)


if __name__ == "__main__":
    unittest.main()
