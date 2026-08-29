"""Offline contract for the seven pinned recovery-domain declarations.

The finite projections below model the two reviewed selector conditions only.
They do not execute m4, compile SELinux policy, or validate a device or image.
"""

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0032-enforce-user-recovery-domains"
PATCH_SHA = "50df430c25bb2feb3ed0b07fbe39a2d110310d03a14adc8e5e574db44039a323"
ENTRY_SHA = "69d91fa5efdfb8be1fa2767e73426d7553cd46dbf82671aa668412d63be8df72"
PREFIX31_SHA = "32401e2a65c9086d264013f53b3bc146285d9199e9fb3410c0b5787197990c94"
REVISION = "f0270686ee017f4de42e1032aca7527031bcc484"
BEFORE_SHA = "03b63947499c6abbacf35d5a830c1dae03a01dae625bfa27de5fde8df2453833"
AFTER_SHA = "a4d257213731dc8a2560f1674d4045002eef0a145c01c217223921e51378e510"
BEFORE_BLOB = "be4a1e9637c64aea610c0404b15cc7a2fbf11db1"
AFTER_BLOB = "0179e3ff26123f8bbed6a457adf5716f4762d135"
DOMAINS = ("recovery", "init", "logd", "adbd", "fastbootd", "postinstall", "ueventd")
RECOVERY_DEFINITION = "define(`recovery_only', ifelse(target_recovery, `true', $1, ))\n"
DEBUG_DEFINITION = (
    "define(`userdebug_or_eng', ifelse(target_build_variant, `eng', $1, "
    "ifelse(target_build_variant, `userdebug', $1,\n"
    "#\n"
    "# SUPPRESSED_BY_USERDEBUG_OR_ENG -- this marker is used by CTS -- do not modify\n"
    ")))\n"
)
HEADER = (
    "diff --git a/private/twrp.te b/private/twrp.te\n"
    f"index {BEFORE_BLOB}..{AFTER_BLOB} 100644\n"
    "--- a/private/twrp.te\n+++ b/private/twrp.te\n"
    "@@ -1,15 +1,17 @@\n"
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
    if (len(before.encode()), sha(before.encode())) != (416, BEFORE_SHA):
        raise ValueError("Original source identity changed")
    if (len(after.encode()), sha(after.encode())) != (456, AFTER_SHA):
        raise ValueError("Revised source identity changed")
    old = before.splitlines(keepends=True)
    expected = (old[0] + "  userdebug_or_eng(`\n"
                + "".join("  " + line for line in old[1:8])
                + "  ')\n" + "".join(old[8:]))
    if after != expected:
        raise ValueError("Only the seven declarations may receive the debug guard")
    return before, after


def projected_statements(source, *, target_recovery, target_build_variant):
    """Finite source projection, not a general macro or policy interpreter."""
    if type(target_recovery) is not bool or not isinstance(target_build_variant, str):
        raise ValueError("Use a boolean recovery selector and a literal variant")
    identity = sha(source.encode())
    if identity not in (BEFORE_SHA, AFTER_SHA):
        raise ValueError("Projection is restricted to the two reviewed source bodies")
    if not target_recovery:
        return ()
    statements = tuple(line.strip() for line in source.splitlines()
                       if line.strip().startswith(("permissive ", "allow ")))
    if identity == AFTER_SHA and target_build_variant not in ("eng", "userdebug"):
        return tuple(line for line in statements if not line.startswith("permissive "))
    return statements


class TwrpRecoveryPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue = json.loads((ROOT / "patches/twrp/series.json").read_bytes())
        entries = [row for row in cls.queue["patches"] if row["id"] == PATCH_ID]
        if len(entries) != 1:
            raise ValueError("Select exactly one recovery policy patch by ID")
        cls.entry = entries[0]
        cls.raw = (ROOT / cls.entry["patch"]).read_bytes()
        cls.before, cls.after = source_pair(cls.raw)

    def test_exact_patch_entry_source_and_mode(self):
        self.assertEqual((len(self.raw), sha(self.raw)), (837, PATCH_SHA))
        self.assertEqual(canonical(self.entry), ENTRY_SHA)
        self.assertEqual(self.entry["base_commit"], REVISION)
        self.assertEqual(self.entry["project"], "system/sepolicy")
        self.assertEqual(self.entry["repository"], "https://github.com/TWRP-Test/android_system_sepolicy")
        self.assertEqual(self.entry["patch_sha256"], PATCH_SHA)
        self.assertEqual(len(self.entry["files"]), 1)
        item = self.entry["files"][0]
        self.assertEqual(item["path"], "private/twrp.te")
        self.assertEqual(item["mode"], "100644")
        for prefix, source, expected in (("before", self.before, BEFORE_BLOB),
                                         ("after", self.after, AFTER_BLOB)):
            raw = source.encode()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual(blob, expected)
            self.assertEqual(item[prefix + "_git_blob"], blob)
            self.assertEqual(item[prefix + "_sha256"], sha(raw))
            self.assertEqual(item[prefix + "_size_bytes"], len(raw))

    def test_prior31_prefix_and_first_touch_are_preserved(self):
        rows = self.queue["patches"]
        self.assertEqual(canonical(rows[:31]), PREFIX31_SHA)
        self.assertEqual(rows[31]["id"], PATCH_ID)
        touched = {(row["project"], item["path"]) for row in rows[:31] for item in row["files"]}
        self.assertNotIn(("system/sepolicy", "private/twrp.te"), touched)
        self.assertNotIn("predecessor_patch_id", self.entry["files"][0])

    def test_only_the_seven_original_declarations_are_nested(self):
        old, new = self.before.splitlines(), self.after.splitlines()
        self.assertEqual((len(old), len(new)), (15, 17))
        self.assertEqual(old[0], new[0])
        self.assertEqual(new[1], "  userdebug_or_eng(`")
        self.assertEqual(new[9], "  ')")
        self.assertEqual(new[2:9], ["  " + line for line in old[1:8]])
        self.assertEqual(old[8:], new[10:])
        self.assertEqual(old[1:8], [f"  permissive {domain};" for domain in DOMAINS])

    def test_allow_suffix_and_neverallow_rules_are_unchanged(self):
        for keyword in ("allow ", "neverallow "):
            before = [line for line in self.before.splitlines(keepends=True) if line.lstrip().startswith(keyword)]
            after = [line for line in self.after.splitlines(keepends=True) if line.lstrip().startswith(keyword)]
            self.assertEqual(before, after)
        self.assertEqual(sum(line.lstrip().startswith("allow ") for line in self.after.splitlines()), 6)
        self.assertEqual(self.raw.count(b"diff --git "), 1)

    def test_pinned_existing_macro_definitions_and_cts_marker(self):
        macro = self.entry["policy_contract"]["macro_source"]
        self.assertEqual(macro["path"], "public/te_macros")
        self.assertEqual(macro["commit"], REVISION)
        self.assertEqual(macro["sha256"], "39876a485ea1fe6cf76418268bc058dde7ae50690fd2901051e32125c5678243")
        self.assertEqual(macro["definitions"], {"recovery_only": RECOVERY_DEFINITION,
                                                "userdebug_or_eng": DEBUG_DEFINITION})
        self.assertNotIn(b"b/public/te_macros", self.raw)

    def test_user_recovery_has_no_projected_permissive_declarations(self):
        before = projected_statements(self.before, target_recovery=True, target_build_variant="user")
        after = projected_statements(self.after, target_recovery=True, target_build_variant="user")
        self.assertEqual(sum(line.startswith("permissive ") for line in before), 7)
        self.assertEqual(sum(line.startswith("permissive ") for line in after), 0)
        self.assertEqual(after, tuple(line for line in before if line.startswith("allow ")))
        self.assertEqual(len(after), 6)

    def test_debug_and_eng_recovery_preserve_all_original_statements(self):
        for variant in ("userdebug", "eng"):
            with self.subTest(variant=variant):
                before = projected_statements(self.before, target_recovery=True, target_build_variant=variant)
                after = projected_statements(self.after, target_recovery=True, target_build_variant=variant)
                self.assertEqual(before, after)
                self.assertEqual(len(after), 13)

    def test_non_recovery_variants_stay_empty(self):
        for variant in ("user", "userdebug", "eng"):
            for source in (self.before, self.after):
                with self.subTest(variant=variant, source=sha(source.encode())):
                    self.assertEqual(projected_statements(source, target_recovery=False,
                                                          target_build_variant=variant), ())

    def test_other_variant_literals_do_not_select_debug_declarations(self):
        for variant in ("", "USERDEBUG", "true", "userdebug ", "eng ", "custom"):
            with self.subTest(variant=variant):
                result = projected_statements(self.after, target_recovery=True, target_build_variant=variant)
                self.assertEqual(len(result), 6)
                self.assertTrue(all(line.startswith("allow ") for line in result))

    def test_projection_is_restricted_and_rejects_ambiguous_selectors(self):
        for recovery, variant in ((1, "user"), ("true", "user"), (None, "user"), (True, None)):
            with self.subTest(recovery=recovery, variant=variant), self.assertRaises(ValueError):
                projected_statements(self.after, target_recovery=recovery, target_build_variant=variant)
        with self.assertRaises(ValueError):
            projected_statements(self.after + "permissive other;\n", target_recovery=True,
                                 target_build_variant="user")

    def test_source_module_and_native_validation_bindings_are_unchanged(self):
        contract = self.entry["policy_contract"]
        self.assertEqual(contract["build_variant_source"]["sha256"],
                         "eaae44efdf8b42ec75acfa024b8f86bc48d96227013eeec078bacc9c1be1d57f")
        self.assertEqual(contract["recovery_module_source"]["sha256"],
                         "28828e32c7a2031195fb7c164ab7389dc210e63668c9f24893c498ab562e8ba4")
        for key in ("allow_and_neverallow_rules_unchanged", "shared_macros_unchanged",
                    "native_validation_unchanged", "compiled_policy_revalidation_required"):
            self.assertIs(contract[key], True)
        self.assertEqual(contract["permissive_domains_in_source_order"], list(DOMAINS))

    def test_unreviewed_source_guard_and_patch_mutations_fail_closed(self):
        changes = ((b"+  userdebug_or_eng(`", b"+  recovery_only(`"),
                   (b"+    permissive adbd;", b"+    permissive other;"),
                   (b" allow kernel tmpfs:file { read };", b" allow kernel tmpfs:file { write };"),
                   (b" 100644\n", b" 100755\n"),
                   (b"@@ -1,15 +1,17 @@", b"@@ -1,15 +1,18 @@"),
                   (b"--- a/private/twrp.te", b"--- a/private/domain.te"))
        for old, new in changes:
            with self.subTest(mutation=new), self.assertRaises(ValueError):
                source_pair(self.raw.replace(old, new, 1))
        for raw in (self.raw[:-1], self.raw + self.raw, self.raw.replace(b"\n", b"\r\n")):
            with self.assertRaises(ValueError):
                source_pair(raw)

    def test_scope_keeps_native_policy_and_runtime_validation_separate(self):
        limits = " ".join(self.entry["limits"])
        self.assertIn("not execution of m4", limits)
        self.assertIn("unfiltered permissive-domain output must be empty", limits)
        self.assertIn("no current successful policy or image is claimed", limits)
        self.assertIn("debug/eng recovery declarations are intentionally retained", limits)


if __name__ == "__main__":
    unittest.main()
