"""Offline contract for the pinned Make default and unchanged Soong template.

These tests inspect public source patches and model literal default selection.
They do not invoke Make, a compiler, a network client, or a device.
"""

import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0030-correct-default-device-version"
PATCH_SHA = "30949471c74952e11412626b265ae487079ab01ce24a16699d30f1cca3b44d24"
ENTRY_SHA = "2f27b131c6b53cb06d907d8091b37c3ab221860ef469c48a5216398c1974a2b0"
PREFIX28_SHA = "f8e03952957932c5ea1bfa0cc7fd84628fe1132fb2348338522319035f4d9ff6"
REVISION = "b53296dfc420ce65fffe712de380d5abf6c4c2f1"
BEFORE_SHA = "0b858d8e1457701ca054edc89eb01aec514ae83170f1b83ef31be93c25e5dcd6"
AFTER_SHA = "123be11a3240ca63ff1011a67d7d05b7f27bab0c16618af980b5d524ba0e6267"
BEFORE_BLOB = "79b2361eed30162a8e55f992c05fded9a66fb43d"
AFTER_BLOB = "5dd951ad87a2b2073fde014db8b629a2e33a3b7a"
OLD = 'TW_DEVICE_VERSION ?= "-0"\n'
NEW = "TW_DEVICE_VERSION ?= 0\n"
HEADER = (
    "diff --git a/config/BoardConfigSoong.mk b/config/BoardConfigSoong.mk\n"
    f"index {BEFORE_BLOB}..{AFTER_BLOB} 100644\n"
    "--- a/config/BoardConfigSoong.mk\n+++ b/config/BoardConfigSoong.mk\n"
    "@@ -1,357 +1,357 @@\n"
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def source_pair(raw):
    if not isinstance(raw, bytes) or b"\0" in raw or b"\r" in raw or not raw.endswith(b"\n"):
        raise ValueError("Expected complete LF text")
    text = raw.decode("utf-8")
    if not text.startswith(HEADER):
        raise ValueError("Unreviewed path, mode, blobs or full-file hunk")
    lines = text[len(HEADER):].splitlines(keepends=True)
    if any(line[:1] not in (" ", "+", "-") for line in lines):
        raise ValueError("Unexpected patch syntax")
    before = "".join(line[1:] for line in lines if line.startswith((" ", "-")))
    after = "".join(line[1:] for line in lines if line.startswith((" ", "+")))
    if (len(before.encode()), sha(before.encode())) != (15760, BEFORE_SHA):
        raise ValueError("Original source identity changed")
    if (len(after.encode()), sha(after.encode())) != (15757, AFTER_SHA):
        raise ValueError("Revised source identity changed")
    if before.count(OLD) != 1 or after != before.replace(OLD, NEW, 1):
        raise ValueError("Only the undefined version default may change")
    return before, after


def literal_default(source, *, defined=False, value=None):
    """Model ?= for an undefined variable or an already expanded literal value."""
    matches = re.findall(r"^TW_DEVICE_VERSION \?= ([^\r\n]+)$", source, re.M)
    if len(matches) != 1:
        raise ValueError("Expected one conditional version default")
    if defined:
        if not isinstance(value, str):
            raise ValueError("An explicit fixture value must be a string")
        return value
    return matches[0]


class TwrpDeviceVersionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        entries = [row for row in cls.queue["patches"] if row["id"] == PATCH_ID]
        if len(entries) != 1:
            raise ValueError("Select exactly one version patch by ID")
        cls.entry = entries[0]
        cls.raw = (ROOT / "patches/twrp" / (PATCH_ID + ".patch")).read_bytes()
        cls.before, cls.after = source_pair(cls.raw)
        # The recorded template is the decoded compiler argument, not BP syntax.
        cls.template = cls.entry["version_contract"]["consumer"]["cflag_template"]

    def test_exact_source_patch_and_entry_identities(self):
        self.assertEqual((len(self.raw), sha(self.raw)), (16392, PATCH_SHA))
        self.assertEqual(canonical(self.entry), ENTRY_SHA)
        self.assertEqual(self.entry["base_commit"], REVISION)
        self.assertEqual(self.entry["project"], "vendor/twrp")
        self.assertEqual(self.entry["repository"], "https://github.com/TWRP-Test/android_vendor_twrp")
        self.assertEqual(self.entry["patch_sha256"], PATCH_SHA)
        self.assertEqual(self.entry["files"][0]["mode"], "100644")
        for prefix, text, expected in (("before", self.before, BEFORE_BLOB),
                                       ("after", self.after, AFTER_BLOB)):
            raw = text.encode()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual(blob, expected)
            self.assertEqual(self.entry["files"][0][prefix + "_git_blob"], blob)
            self.assertEqual(self.entry["files"][0][prefix + "_sha256"], sha(raw))
            self.assertEqual(self.entry["files"][0][prefix + "_size_bytes"], len(raw))

    def test_first_touch_and_old28_prefix_remain_independent_of_later_appends(self):
        rows = self.queue["patches"]
        self.assertEqual(canonical(rows[:28]), PREFIX28_SHA)
        index = next(i for i, row in enumerate(rows) if row["id"] == PATCH_ID)
        prior = {(row["project"], item["path"]) for row in rows[:index] for item in row["files"]}
        self.assertNotIn(("vendor/twrp", "config/BoardConfigSoong.mk"), prior)
        self.assertNotIn("predecessor_patch_id", self.entry["files"][0])

    def test_only_the_default_assignment_changes(self):
        self.assertEqual(self.after, self.before.replace(OLD, NEW, 1))
        changed = [line for line in self.raw.decode().splitlines()
                   if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
        self.assertEqual(changed, ['-' + OLD.rstrip("\n"), '+' + NEW.rstrip("\n")])
        self.assertEqual(len(self.before.splitlines()), 357)
        self.assertEqual(len(self.after.splitlines()), 357)

    def test_unchanged_consumer_is_the_pinned_soong_value_template(self):
        consumer = self.entry["version_contract"]["consumer"]
        self.assertEqual(consumer["path"], "build/soong/Android.bp")
        self.assertEqual(consumer["commit"], REVISION)
        self.assertEqual(consumer["sha256"], "7ee79252369daf5dedcb30e4d106827a219378249cbe447ceeba3ac296ee38ec")
        self.assertEqual(self.template, '-DTW_DEVICE_VERSION="-%s"')
        self.assertNotIn("b/build/soong/Android.bp", self.raw.decode())

    def test_new_default_renders_one_valid_string_literal(self):
        self.assertEqual(literal_default(self.after), "0")
        flag = self.template % literal_default(self.after)
        self.assertEqual(flag, '-DTW_DEVICE_VERSION="-0"')
        replacement = flag.split("=", 1)[1]
        self.assertEqual(json.loads(replacement), "-0")
        self.assertEqual(replacement, self.entry["version_contract"]["default_cpp_replacement"])

    def test_old_default_reproduces_the_reported_malformed_replacement(self):
        self.assertEqual(literal_default(self.before), '"-0"')
        flag = self.template % literal_default(self.before)
        self.assertEqual(flag, '-DTW_DEVICE_VERSION="-"-0""')
        with self.assertRaises(json.JSONDecodeError):
            json.loads(flag.split("=", 1)[1])

    def test_explicit_values_including_empty_and_quotes_are_not_normalized(self):
        for value in ("", "0", "7", "private-build", '"already-quoted"', "-custom"):
            with self.subTest(value=value):
                old = literal_default(self.before, defined=True, value=value)
                new = literal_default(self.after, defined=True, value=value)
                self.assertEqual((old, new), (value, value))
                self.assertEqual(self.template % old, self.template % new)

    def test_conditional_assignment_cannot_be_replaced_by_forced_assignment(self):
        for token in ("=", ":=", "+=", "!="):
            with self.subTest(token=token), self.assertRaises(ValueError):
                literal_default(self.after.replace(NEW, "TW_DEVICE_VERSION " + token + " 0\n", 1))

    def test_unreviewed_default_or_source_mutations_are_rejected(self):
        for old, new in ((b"+TW_DEVICE_VERSION ?= 0", b'+TW_DEVICE_VERSION ?= "0"'),
                         (b"+TW_DEVICE_VERSION ?= 0", b"+TW_DEVICE_VERSION ?= -0"),
                         (b"+TW_DEVICE_VERSION ?= 0", b"+TW_DEVICE_VERSION := 0"),
                         (b"+TW_DEVICE_VERSION ?= 0", b"+TW_DEVICE_VERSION ?= 1"),
                         (b" 100644\n", b" 100755\n"),
                         (b"@@ -1,357 +1,357 @@", b"@@ -1,357 +1,356 @@"),
                         (b"--- a/config/BoardConfigSoong.mk", b"--- a/config/Other.mk")):
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                source_pair(self.raw.replace(old, new, 1))
        for raw in (self.raw[:-1], self.raw + self.raw, self.raw.replace(b"\n", b"\r\n")):
            with self.assertRaises(ValueError):
                source_pair(raw)

    def test_scope_does_not_claim_explicit_input_validation_or_a_release(self):
        limits = " ".join(self.entry["limits"])
        self.assertIn("does not validate or sanitize explicitly configured values", limits)
        self.assertIn("actual Android compile remains required", limits)
        self.assertIs(self.entry["version_contract"]["explicit_make_values_unchanged"], True)


if __name__ == "__main__":
    unittest.main()
