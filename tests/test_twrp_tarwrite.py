"""Offline source contract for tarWrite.c's intentionally unused descriptor.

Only the public patch and series are inputs. No compiler, network, process,
phone, or ignored source capture is needed; this is not runtime validation.
"""

import hashlib
import json
from pathlib import Path
import re
import unittest

from support import canonical_json_sha256 as canonical, sha256_bytes as digest


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0031-explicit-unused-tarwrite-parameter"
PATCH_SHA256 = "af2d8b202bd4953d8d565065bcac08fce14b9c70d6bf4746db94e456140ffe88"
ENTRY_SHA256 = "848dafd77c23910ac45764c0d1acb257ce1cc7aa0088ec3653579fe8fa50a1d9"
PRIOR30_SERIALIZED_SHA256 = "5217d75732aadb799a34cb1550e1ca37e1f532266de8a9f459bdbd5f6ea40fe8"
REVISION = "b70f8e998b302381ecefc6e7f46df1614bd61afc"
FILE = {
    "path": "tarWrite.c", "mode": "100644",
    "before_size_bytes": 2861, "after_size_bytes": 2872,
    "before_sha256": "9ef2f2afaa18d405ba28d4d0d6d34293eb74799f468db5705e6fff5047040d1c",
    "after_sha256": "d55d8913c19c1d0271b7a98bf9f22fcaaafe12f8cac5de6fafe57be8ea5c73ad",
    "before_git_blob": "98461452a42ff0e28d4fa22c3fba065683d59994",
    "after_git_blob": "d1b4555716099760e39688b3cdfbbf2003032496",
}
SIGNATURE = "void flush_libtar_buffer(int fd) {\n"
CAST = "\t(void)fd;\n"
ORIGINAL = SIGNATURE + "\teot_count = 0;\n\tif (buffer_status)\n\t\tbuffer_status = 2;\n}\n"
REVISED = ORIGINAL.replace(SIGNATURE, SIGNATURE + CAST, 1)
HEADER = (
    "diff --git a/tarWrite.c b/tarWrite.c\n"
    f"index {FILE['before_git_blob']}..{FILE['after_git_blob']} 100644\n"
    "--- a/tarWrite.c\n+++ b/tarWrite.c\n@@ -1,113 +1,114 @@\n"
)


def exact_edit(before, after):
    """Allow one entry cast and preserve every original source byte."""
    if before.count(ORIGINAL) != 1 or after != before.replace(ORIGINAL, REVISED, 1):
        raise ValueError("Only the unused fd cast at flush_libtar_buffer entry may change")


def source_pair(raw):
    if not isinstance(raw, bytes) or b"\r" in raw or b"\0" in raw or not raw.endswith(b"\n"):
        raise ValueError("Expected complete LF-terminated text")
    text = raw.decode("utf-8")
    if not text.startswith(HEADER):
        raise ValueError("Unreviewed path, mode, complete Git blobs or full-file hunk")
    lines = text[len(HEADER):].splitlines(keepends=True)
    if (any(line[:1] not in (" ", "+", "-") for line in lines)
            or sum(line.startswith((" ", "-")) for line in lines) != 113
            or sum(line.startswith((" ", "+")) for line in lines) != 114):
        raise ValueError("Malformed or additional patch content")
    before = "".join(line[1:] for line in lines if line.startswith((" ", "-")))
    after = "".join(line[1:] for line in lines if line.startswith((" ", "+")))
    for stage, text in (("before", before), ("after", after)):
        data = text.encode()
        if (len(data), digest(data)) != (FILE[stage + "_size_bytes"], FILE[stage + "_sha256"]):
            raise ValueError("Complete source identity changed")
    exact_edit(before, after)
    return before, after


def select_entry(rows):
    selected = [row for row in rows if row.get("id") == PATCH_ID]
    if len(selected) != 1:
        raise ValueError("Expected one tarWrite patch selected by ID")
    return selected[0]


def serialized_patch_records(text):
    """Retain exact approved object bytes, independent of later appends."""
    start = re.search(r'"patches"\s*:\s*\[', text)
    if start is None:
        raise ValueError("Missing patch array")
    position = start.end()
    records = []
    decoder = json.JSONDecoder()
    while position < len(text):
        while position < len(text) and (text[position].isspace() or text[position] == ","):
            position += 1
        if position == len(text):
            break
        if text[position] == "]":
            return records
        value, end = decoder.raw_decode(text, position)
        if not isinstance(value, dict):
            raise ValueError("Expected a patch record")
        records.append(text[position:end])
        position = end
    raise ValueError("Incomplete patch array")


class TwrpTarWriteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue_text = (ROOT / "patches/twrp/series.json").read_text()
        cls.queue = json.loads(cls.queue_text)
        cls.entry = select_entry(cls.queue["patches"])
        cls.raw = (ROOT / "patches/twrp" / (PATCH_ID + ".patch")).read_bytes()
        cls.before, cls.after = source_pair(cls.raw)

    def test_pinned_entry_payload_and_complete_source_identities(self):
        self.assertEqual((len(self.raw), digest(self.raw)), (3173, PATCH_SHA256))
        self.assertEqual(canonical(self.entry), ENTRY_SHA256)
        self.assertEqual(self.entry["patch_sha256"], PATCH_SHA256)
        self.assertEqual(self.entry["project"], "bootable/recovery")
        self.assertEqual(self.entry["base_commit"], REVISION)
        self.assertEqual(self.entry["repository"], "https://github.com/TWRP-Test/android_bootable_recovery")
        self.assertEqual(self.entry["patch"], "patches/twrp/" + PATCH_ID + ".patch")
        self.assertEqual(len(self.entry["files"]), 1)
        file = self.entry["files"][0]
        self.assertEqual({key: file[key] for key in FILE}, FILE)
        self.assertEqual(file["source_url"], self.entry["repository"] + "/blob/" + REVISION + "/tarWrite.c")
        for stage, text in (("before", self.before), ("after", self.after)):
            data = text.encode()
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            self.assertEqual(blob, FILE[stage + "_git_blob"])

    def test_first_touch_preserves_prior30_without_fixing_final_queue_length(self):
        records = serialized_patch_records(self.queue_text)
        self.assertGreaterEqual(len(records), 31)
        self.assertEqual(digest("\n".join(records[:30]).encode()), PRIOR30_SERIALIZED_SHA256)
        rows = self.queue["patches"]
        index = next(i for i, row in enumerate(rows) if row["id"] == PATCH_ID)
        prior = {(row["project"], file["path"])
                 for row in rows[:index] for file in row["files"]}
        self.assertNotIn(("bootable/recovery", "tarWrite.c"), prior)
        self.assertNotIn("predecessor_patch_id", self.entry["files"][0])

    def test_entry_selection_is_unique_and_does_not_depend_on_the_tail(self):
        self.assertEqual(select_entry([self.entry, {"id": "future-patch"}]), self.entry)
        for rows in ([], [{"id": "another-patch"}], [self.entry, self.entry]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                select_entry(rows)

    def test_reported_parameter_is_unused_in_the_unconditional_original_body(self):
        self.assertEqual(self.before.splitlines()[97], SIGNATURE.rstrip("\n"))
        self.assertEqual(ORIGINAL.count("fd"), 1)
        self.assertNotIn("#", ORIGINAL)
        self.assertEqual(self.before.count(ORIGINAL), 1)
        contract = self.entry["parameter_contract"]
        self.assertEqual(contract["function"], SIGNATURE.rstrip(" {\n"))
        self.assertEqual((contract["parameter"], contract["original_line"], contract["original_column"]),
                         ("fd", 98, 30))
        self.assertEqual(contract["diagnostic"], "-Werror,-Wunused-parameter")

    def test_only_one_explicit_void_cast_is_inserted(self):
        self.assertEqual(self.after, self.before.replace(ORIGINAL, REVISED, 1))
        changes = [line for line in self.raw.decode()[len(HEADER):].splitlines(keepends=True)
                   if line.startswith(("+", "-"))]
        self.assertEqual(changes, ["+" + CAST])
        self.assertEqual(len(self.after.encode()) - len(self.before.encode()), 11)
        self.assertEqual((len(self.before.splitlines()), len(self.after.splitlines())), (113, 114))
        self.assertTrue(self.before.endswith("\n") and self.after.endswith("\n"))
        self.assertEqual(self.entry["parameter_contract"]["insertion"], CAST)

    def test_deferred_flush_state_changes_and_all_other_source_are_identical(self):
        old_prefix, old_suffix = self.before.split(ORIGINAL)
        new_prefix, new_suffix = self.after.split(REVISED)
        self.assertEqual((new_prefix, new_suffix), (old_prefix, old_suffix))
        self.assertEqual(REVISED.replace(CAST, "", 1), ORIGINAL)
        self.assertIs(self.entry["parameter_contract"]["deferred_flush_preserved"], True)
        for forbidden in ("write(", "close(", "fsync(", "fdatasync(", "return", "flush ="):
            self.assertNotIn(forbidden, REVISED)
        self.assertIn("write(fd, write_buffer, buffer_loc)", old_prefix)
        self.assertIn("return write(fd, buffer, size);", old_suffix)

    def test_copyright_headers_and_feature_and_warning_directives_are_unchanged(self):
        self.assertEqual(self.before.split("int flush =", 1)[0], self.after.split("int flush =", 1)[0])
        self.assertIn("Copyright 2012 bigbiff/Dees_Troy TeamWin", self.after)
        self.assertEqual([line for line in self.before.splitlines() if line.startswith("#")],
                         [line for line in self.after.splitlines() if line.startswith("#")])
        self.assertNotIn("#pragma", self.after)
        self.assertNotIn("__attribute__", self.after)

    def test_source_mutations_cannot_pass_the_narrow_edit_contract(self):
        mutations = [
            self.before,
            self.after.replace(CAST, "\t(void)buffer_status;\n", 1),
            self.after.replace(CAST, "\tclose(fd);\n", 1),
            self.after.replace(CAST, "\tfsync(fd);\n", 1),
            self.after.replace(CAST, CAST + "\treturn;\n", 1),
            self.after.replace(CAST, CAST + "\tflush = 1;\n", 1),
            self.after.replace(CAST, CAST + CAST, 1),
            self.after.replace(CAST, "#ifdef TW_INCLUDE_CRYPTO\n" + CAST + "#endif\n", 1),
            self.after.replace(SIGNATURE, "void flush_libtar_buffer(void) {\n", 1),
            self.after.replace("\teot_count = 0;\n", "\teot_count = 2;\n", 1),
            self.after.replace("\t\tbuffer_status = 2;\n", "\t\tbuffer_status = 0;\n", 1),
            self.after.replace(CAST, '#pragma clang diagnostic ignored "-Wunused-parameter"\n', 1),
        ]
        for number, changed in enumerate(mutations):
            with self.subTest(mutation=number), self.assertRaises(ValueError):
                exact_edit(self.before, changed)

    def test_malformed_or_additional_patch_content_is_rejected(self):
        substitutions = (
            (b" 100644\n", b" 100755\n"),
            (FILE["before_git_blob"].encode(), b"0" * 40),
            (b"--- a/tarWrite.c", b"--- a/other.c"),
            (b"@@ -1,113 +1,114 @@", b"@@ -1,113 +1,113 @@"),
            (("+" + CAST).encode(), b"+\t(void)buffer_status;\n"),
            (("+" + CAST).encode(), b""),
            (b"Copyright 2012", b"Copyright 2013"),
        )
        variants = [self.raw.replace(old, new, 1) for old, new in substitutions]
        variants += [self.raw[:-1], self.raw + self.raw, self.raw + b"trailer\n",
                     self.raw.replace(b"\n", b"\r\n"), b"\\ No newline at end of file\n" + self.raw]
        for number, changed in enumerate(variants):
            with self.subTest(mutation=number), self.assertRaises(ValueError):
                source_pair(changed)

    def test_limits_require_actual_build_and_device_validation(self):
        limits = " ".join(self.entry["limits"])
        self.assertIn("Actual Android recompilation and device validation remain required", limits)
        self.assertIn("does not add I/O", limits)
        self.assertIn("do not establish a successful build or runtime behavior", limits)


if __name__ == "__main__":
    unittest.main()
