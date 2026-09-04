"""Offline source-contract checks; real no-key JDK fixtures are run separately."""

import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock
import xml.etree.ElementTree as ET

from scripts import partition_build_props
from scripts import signapk_stored_entry_timestamps as signer
from scripts import twrp_patch_state
from tests.test_signapk_source_stamp import fixture_source, reverse_patch


ROOT = Path(__file__).resolve().parents[1]
PATCH = "patches/evolution/0025-signapk-stored-entry-timestamps.patch"
CONTRACT = "patches/evolution/signapk-stored-entry-timestamps.json"
JAVA_FIXTURE = "tests/fixtures/SignApkStoredEntryTimestampRepro.java"


class SignApkStoredEntryTimestampsTests(unittest.TestCase):
    def setUp(self):
        for target in ("subprocess.run", "subprocess.Popen", "os.system", "socket.socket"):
            self.enterContext(mock.patch(target, side_effect=AssertionError("offline: " + target)))
        self.patch = (ROOT / PATCH).read_bytes()
        self.record = json.loads((ROOT / CONTRACT).read_bytes())
        self.fixture = fixture_source(self.patch)

    def test_patch_replaces_only_cloning_with_explicit_payload_metadata_copy(self):
        header, body = self.patch.split(b"@@ -454,8 +454,13 @@\n")
        self.assertEqual(header, (
            f"diff --git a/{signer.SOURCE_PATH} b/{signer.SOURCE_PATH}\n"
            f'index {signer.BEFORE["git_blob"]}..{signer.AFTER["git_blob"]} 100644\n'
            f"--- a/{signer.SOURCE_PATH}\n+++ b/{signer.SOURCE_PATH}\n"
        ).encode())
        for prefix, expected in ((b"-", signer.OLD_BLOCK), (b"+", signer.NEW_BLOCK)):
            self.assertEqual(b"".join(line[1:] for line in body.splitlines(keepends=True)
                                      if line.startswith(prefix)), expected)
        self.assertEqual(self.patch.count(b"diff --git "), 1)

    def test_fresh_entry_preserves_only_name_and_stored_payload_fields(self):
        code = [line.strip() for line in signer.NEW_BLOCK.decode().splitlines()
                if not line.strip().startswith("//")]
        self.assertEqual(code, [
            "JarEntry outEntry = new JarEntry(inEntry.getName());",
            "outEntry.setMethod(inEntry.getMethod());",
            "outEntry.setSize(inEntry.getSize());",
            "outEntry.setCompressedSize(inEntry.getCompressedSize());",
            "outEntry.setCrc(inEntry.getCrc());",
        ])
        for prohibited in (b"setCreationTime", b"setLastAccessTime", b"setLastModifiedTime",
                           b"getExtra", b"getComment", b"reflect", b"setAccessible"):
            self.assertNotIn(prohibited, signer.NEW_BLOCK)

    def test_exact_patch_replay_matches_pure_transform_and_reverses(self):
        after = signer._replace_metadata_block(self.fixture)
        self.assertEqual(partition_build_props._apply_patch(self.fixture, self.patch), after)
        self.assertEqual(partition_build_props._apply_patch(after, reverse_patch(self.patch)), self.fixture)
        self.assertEqual(after.replace(signer.NEW_BLOCK, signer.OLD_BLOCK, 1), self.fixture)

    def test_surrounding_signing_timestamp_and_alignment_text_is_unchanged(self):
        stamp = b"// Existing 0020 source-stamp filter stays outside the changed block.\n"
        source = stamp + self.fixture + b"outEntry.setComment(null);\noutEntry.setExtra(null);\n"
        before_prefix, before_suffix = source.split(signer.OLD_BLOCK)
        after = signer._replace_metadata_block(source)
        after_prefix, after_suffix = after.split(signer.NEW_BLOCK)
        self.assertEqual((before_prefix, before_suffix), (after_prefix, after_suffix))
        self.assertIn(b"outEntry.setTime(timestamp);", after)

    def test_duplicate_application_or_multiple_old_blocks_rejected(self):
        for source in (signer._replace_metadata_block(self.fixture), self.fixture + signer.OLD_BLOCK,
                       self.fixture + signer.NEW_BLOCK):
            with self.subTest(source=source), self.assertRaises(ValueError):
                signer._replace_metadata_block(source)

    def test_missing_or_modified_old_block_rejected(self):
        for source in (b"class Empty {}\n", self.fixture.replace(b"new JarEntry(inEntry);", b"other();"),
                       self.fixture.replace(b"Preserve the STORED", b"Changed the STORED")):
            with self.subTest(source=source), self.assertRaises(ValueError):
                signer._replace_metadata_block(source)

    def test_crlf_nul_incomplete_and_non_bytes_rejected(self):
        for source in (self.fixture.replace(b"\n", b"\r\n"), self.fixture + b"\0\n",
                       self.fixture[:-1], self.fixture.decode(), bytearray(self.fixture)):
            with self.subTest(source=source), self.assertRaises(ValueError):
                signer._replace_metadata_block(source)

    def test_public_entrypoints_reject_unpinned_source(self):
        for source in (self.fixture, signer._replace_metadata_block(self.fixture), b"\n"):
            with self.subTest(source=source):
                with self.assertRaisesRegex(ValueError, "preimage differs"):
                    signer.derive(source)
                with self.assertRaisesRegex(ValueError, "postimage differs"):
                    signer.reverse(source)

    def test_contract_matches_full_pair_mode_and_patch(self):
        row = {
            "path": signer.SOURCE_PATH, "mode": "100644", "line_endings": "LF",
            **{"before_" + key: value for key, value in signer.BEFORE.items()},
            **{"after_" + key: value for key, value in signer.AFTER.items()},
        }
        self.assertEqual(self.record["files"], [row])
        self.assertEqual((self.record["patch"], self.record["patch_sha256"], self.record["patch_size_bytes"]),
                         (PATCH, hashlib.sha256(self.patch).hexdigest(), len(self.patch)))
        twrp_patch_state.chain_patch_index(self.patch, signer.SOURCE_PATH, row, mode=0o644)

    def test_source_preimage_is_exact_prior_0020_postimage(self):
        previous = self.record["predecessor_contract"]
        raw = (ROOT / previous["path"]).read_bytes()
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)),
                         (previous["sha256"], previous["size_bytes"]))
        rows = [r for r in json.loads(raw)["files"] if r["path"] == signer.SOURCE_PATH]
        self.assertEqual(len(rows), 1)
        self.assertEqual({key: rows[0]["after_" + key] for key in signer.BEFORE}, signer.BEFORE)

    def test_origin_revision_and_branch_match_source_snapshot(self):
        snapshot = self.record["source_snapshot"]
        raw = (ROOT / snapshot["path"]).read_bytes()
        self.assertEqual((hashlib.sha256(raw).hexdigest(), len(raw)),
                         (snapshot["sha256"], snapshot["size_bytes"]))
        manifest = ET.fromstring(raw)
        projects = [p for p in manifest.findall("project") if p.get("path") == "build/make"]
        self.assertEqual(len(projects), 1)
        project = projects[0]
        self.assertEqual((project.get("revision"), self.record["base_commit"]),
                         ("a438ca40c6ed779042f806142b1165ba1360a7b2",) * 2)
        self.assertEqual((project.get("upstream"), self.record["branch"]), ("refs/heads/bka", "bka"))
        remote = next(r for r in manifest.findall("remote") if r.get("name") == project.get("remote"))
        self.assertEqual(remote.get("fetch").rstrip("/") + "/" + project.get("name"), self.record["origin"])

    def test_public_java_fixture_uses_exact_corrected_block_and_old_control(self):
        raw = (ROOT / JAVA_FIXTURE).read_bytes()
        self.assertIn(signer.NEW_BLOCK, raw)
        self.assertEqual(raw.count(signer.NEW_BLOCK), 1)
        self.assertIn(b"return new JarEntry(inEntry);", raw)
        for marker in (b"outEntry.setTime(1230768000000L)", b"outEntry.setComment(null);",
                       b"outEntry.setExtra(null);", b"StandardOpenOption.CREATE_NEW"):
            self.assertIn(marker, raw)
        self.assertEqual(self.record["reproduction"]["java_fixture"]["path"], JAVA_FIXTURE)
        self.assertEqual(self.record["reproduction"]["java_fixture"]["sha256"], hashlib.sha256(raw).hexdigest())

    def test_no_rebuild_signing_or_readiness_claimed_by_preparation(self):
        self.assertEqual(self.record["status"], "tested_source_patch_not_installed")
        self.assertTrue(all(value is False for value in self.record["preparation_limits"].values()))
        scope = self.record["scope"]
        self.assertEqual(scope["payload_fields_copied"], ["name", "method", "size", "compressed_size", "crc"])
        self.assertEqual(scope["input_comments"], "discarded, preserving existing behavior")
        self.assertEqual(scope["input_extra_fields"], "discarded, preserving existing behavior")
        for key in ("timestamp_normalization_changed", "alignment_algorithm_changed", "compressed_branch_changed",
                    "source_stamp_filter_changed", "signing_checks_changed", "original_apk_changed",
                    "platform_certificate_changed", "privileges_changed", "page_size_changed", "selinux_changed"):
            self.assertIs(scope[key], False)


if __name__ == "__main__":
    unittest.main()
