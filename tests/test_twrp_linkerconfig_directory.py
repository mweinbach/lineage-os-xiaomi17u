"""Offline source contract and temporary fixtures for mkdir-before-touch.

These tests do not execute Make, Ninja, a compiler, init or device commands.
"""

import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0033-create-recovery-linkerconfig-directory"
PATCH_SHA = "85939f746a65497e152b79d59fe24bf28a28f2b0207a87f446404f4746a44986"
ENTRY_SHA = "f1ef21ee2a0dc1319584416d6033e74daadaf98ede427d299010237c86a200de"
PREFIX32_SHA = "a3298dbaf00277c2dde1e5d2d5226223ead07b3b350c5311621a041c3037873f"
REVISION = "3b5b2b43b8e2200ef92b7b814a84c8dde8b74121"
BEFORE_SHA = "619ebc4a0abc3190e84565fea9721b6c4864cafdbee43cc1761d826a5a5a2297"
AFTER_SHA = "b7ce1d382209101e2951193e60f456d281bcd485cfd69a0048296f4f292b3dc7"
BEFORE_BLOB = "a997efabf54e268c956585924d4c0588d67dc1e2"
AFTER_BLOB = "e09041ca031c437f03d2fb7dea753869218288a6"
ADDED = "\tmkdir -p $(TARGET_RECOVERY_ROOT_OUT)/linkerconfig\n"
TOUCH = "\ttouch $(TARGET_RECOVERY_ROOT_OUT)/linkerconfig/ld.config.txt\n"
HEADER = (
    "diff --git a/core/Makefile b/core/Makefile\n"
    f"index {BEFORE_BLOB}..{AFTER_BLOB} 100644\n"
    "--- a/core/Makefile\n+++ b/core/Makefile\n"
    "@@ -1,8216 +1,8217 @@\n"
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
    if (len(before.encode()), sha(before.encode())) != (377838, BEFORE_SHA):
        raise ValueError("Original source identity changed")
    if (len(after.encode()), sha(after.encode())) != (377889, AFTER_SHA):
        raise ValueError("Revised source identity changed")
    if before.count(TOUCH) != 1 or after != before.replace(TOUCH, ADDED + TOUCH, 1):
        raise ValueError("Only the parent mkdir immediately before touch may be added")
    return before, after


def fixture_recipe(staging):
    """Model the two reviewed filesystem operations in an explicit fixture."""
    parent = staging / "linkerconfig"
    parent.mkdir(parents=True, exist_ok=True)
    (parent / "ld.config.txt").touch(exist_ok=True)


class TwrpLinkerconfigDirectoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        entries = [row for row in cls.queue["patches"] if row["id"] == PATCH_ID]
        if len(entries) != 1:
            raise ValueError("Select exactly one linkerconfig directory patch by ID")
        cls.entry = entries[0]
        cls.raw = (ROOT / cls.entry["patch"]).read_bytes()
        cls.before, cls.after = source_pair(cls.raw)

    def test_exact_patch_entry_pin_mode_and_file_identities(self):
        self.assertEqual((len(self.raw), sha(self.raw)), (386307, PATCH_SHA))
        self.assertEqual(canonical(self.entry), ENTRY_SHA)
        self.assertEqual(self.entry["project"], "build/make")
        self.assertEqual(self.entry["base_commit"], REVISION)
        self.assertEqual(self.entry["repository"], "https://github.com/TWRP-Test/android_build")
        self.assertEqual(self.entry["patch_sha256"], PATCH_SHA)
        self.assertEqual(len(self.entry["files"]), 1)
        item = self.entry["files"][0]
        self.assertEqual((item["path"], item["mode"]), ("core/Makefile", "100644"))
        for prefix, source, expected in (("before", self.before, BEFORE_BLOB),
                                         ("after", self.after, AFTER_BLOB)):
            raw = source.encode()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual(blob, expected)
            self.assertEqual(item[prefix + "_git_blob"], blob)
            self.assertEqual(item[prefix + "_sha256"], sha(raw))
            self.assertEqual(item[prefix + "_size_bytes"], len(raw))

    def test_prior32_prefix_and_first_touch_remain_unchanged(self):
        rows = self.queue["patches"]
        self.assertEqual(canonical(rows[:32]), PREFIX32_SHA)
        self.assertEqual(rows[32]["id"], PATCH_ID)
        touched = {(row["project"], item["path"]) for row in rows[:32] for item in row["files"]}
        self.assertNotIn(("build/make", "core/Makefile"), touched)
        self.assertNotIn("predecessor_patch_id", self.entry["files"][0])

    def test_one_added_command_preserves_the_entire_original_recipe(self):
        changed = [line for line in self.raw.decode().splitlines()
                   if line.startswith(("+", "-")) and not line.startswith(("+++", "---"))]
        self.assertEqual(changed, ["+" + ADDED.rstrip("\n")])
        self.assertEqual(self.after, self.before.replace(TOUCH, ADDED + TOUCH, 1))
        self.assertEqual((len(self.before.splitlines()), len(self.after.splitlines())), (8216, 8217))
        self.assertEqual(self.raw.count(b"diff --git "), 1)
        self.assertIn("\t# Silence warnings in first_stage_console.\n" + ADDED + TOUCH, self.after)

    def test_empty_staging_reproduces_old_failure_and_new_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory) / "recovery/root"
            staging.mkdir(parents=True)
            config = staging / "linkerconfig/ld.config.txt"
            with self.assertRaises(FileNotFoundError):
                config.touch()
            fixture_recipe(staging)
            self.assertTrue(config.is_file())
            self.assertEqual(config.read_bytes(), b"")

    def test_existing_config_content_modes_and_touch_behavior_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            parent = staging / "linkerconfig"
            parent.mkdir(mode=0o750)
            parent.chmod(0o750)
            config = parent / "ld.config.txt"
            content = b"# existing fixture config\nnamespace.default.isolated = true\n"
            config.write_bytes(content)
            config.chmod(0o640)
            os.utime(config, ns=(1_000_000_000, 1_000_000_000))
            for _ in range(2):
                fixture_recipe(staging)
                self.assertEqual(config.read_bytes(), content)
                self.assertEqual(stat.S_IMODE(config.stat().st_mode), 0o640)
                self.assertEqual(stat.S_IMODE(parent.stat().st_mode), 0o750)
                self.assertGreater(config.stat().st_mtime_ns, 1_000_000_000)

    def test_non_directory_parent_fails_without_overwrite_or_placeholder(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            obstruction = staging / "linkerconfig"
            obstruction.write_bytes(b"do not replace")
            with self.assertRaises(FileExistsError):
                fixture_recipe(staging)
            self.assertEqual(obstruction.read_bytes(), b"do not replace")

    def test_other_staged_files_are_untouched(self):
        with tempfile.TemporaryDirectory() as directory:
            staging = Path(directory)
            other = staging / "unrelated-file"
            other.write_bytes(b"preserved")
            before = other.stat()
            fixture_recipe(staging)
            after = other.stat()
            self.assertEqual(other.read_bytes(), b"preserved")
            self.assertEqual((before.st_mode, before.st_mtime_ns), (after.st_mode, after.st_mtime_ns))

    def test_original_runtime_init_copy_and_permissions_are_not_changed(self):
        contract = self.entry["placeholder_contract"]
        init = contract["runtime_init"]
        self.assertEqual(init["project"], "bootable/recovery")
        self.assertEqual(init["commit"], "b70f8e998b302381ecefc6e7f46df1614bd61afc")
        self.assertEqual(init["path"], "etc/init.rc")
        self.assertEqual(init["before_sha256"], "29d50cc909060f5a3bd1b649eb95cff98997ddda14c7cc814bd7131791a5d274")
        self.assertEqual(init["unchanged_commands"], [
            "    copy /system/etc/ld.config.txt /linkerconfig/ld.config.txt",
            "    chmod 444 /linkerconfig/ld.config.txt",
        ])
        self.assertEqual(contract["added_recipe_line"], ADDED)
        self.assertEqual(contract["unchanged_touch_line"], TOUCH)
        self.assertIs(contract["new_config_contents_or_provider"], False)
        self.assertIs(contract["explicit_chmod_or_chown_added"], False)

    def test_unreviewed_path_permission_or_recipe_changes_are_rejected(self):
        for old, new in ((ADDED.encode(), ADDED.replace("mkdir -p", "mkdir -m 777 -p").encode()),
                         (ADDED.encode(), ADDED.replace("linkerconfig", "other").encode()),
                         (b" 100644\n", b" 100755\n"),
                         (b"@@ -1,8216 +1,8217 @@", b"@@ -1,8216 +1,8218 @@"),
                         (b"--- a/core/Makefile", b"--- a/core/other")):
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                source_pair(self.raw.replace(old, new, 1))
        for raw in (self.raw[:-1], self.raw + self.raw, self.raw.replace(b"\n", b"\r\n")):
            with self.assertRaises(ValueError):
                source_pair(raw)

    def test_limits_keep_actual_build_image_and_runtime_checks_required(self):
        limits = " ".join(self.entry["limits"])
        self.assertIn("do not run Make, Ninja, a native compiler or the device", limits)
        self.assertIn("does not truncate an existing config", limits)
        self.assertIn("unchanged image, ramdisk, SELinux and signature validations remain required", limits)
        self.assertIn("no image or runtime success is claimed", limits)


if __name__ == "__main__":
    unittest.main()
