"""Offline OZIP source contract; no compiler, key, network or phone is used.

The preprocessor projection selects only the exact reviewed helper guard. It
does not execute C++, simulate an Android build, or claim runtime validation.
"""

import hashlib
import json
from pathlib import Path
import re
import unittest

from support import canonical_json_sha256 as canonical, sha256_bytes as digest


ROOT = Path(__file__).resolve().parents[1]
PATCH_ID = "0028-guard-unconfigured-ozip-decryption"
PATCH_SHA256 = "9a51886ddc1c0f69d1a9884b6ecf79c1cb30f815be820a72e4e6c631e7a70531"
ENTRY_SHA256 = "3180e3ec327397a24aeb93130c23489ce78375d0b00fdb714a34fe26d7007670"
REVISION = "b70f8e998b302381ecefc6e7f46df1614bd61afc"
BEFORE27_SERIALIZED_SHA256 = "efd8258f4d55e687e2885a0cf9c30db544ecd13eea624bda1f25254af2acb7e9"
FILE = {
    "path": "gui/action.cpp", "mode": "100644",
    "before_size_bytes": 80100, "after_size_bytes": 80276,
    "before_sha256": "35f21ddd81d67d8ff299e3e47af76ec4d0e9056a74a9d15d9f34590f80ead290",
    "after_sha256": "db3eb2a0495b990423cea830c54df9fb3da033846db4ff4840a2e0a6055cc2cb",
    "before_git_blob": "65e71b085568f94b3fc58a436901bb299d1eaa74",
    "after_git_blob": "8252b0643cf2bebf3c1a180dcb0373c69563d6be",
}
SIGNATURE = "int GUIAction::ozip_decrypt(string zip_path)\n{\n"
DISABLED_BODY = (
    '\t(void)zip_path;\n'
    '\tgui_err("ozip_decrypt_no_key=OZIP decryption is not configured in this recovery.");\n'
    '\treturn 1;\n'
)
GUARD = "#ifndef TW_OZIP_DECRYPT_KEY\n" + DISABLED_BODY + "#else\n"
OLD_ERROR = '\t\t\t\tLOGERR("Unable to find ozip_decrypt!");\n'
NEW_ERROR = '\t\t\t\tret_val = 1;\n\t\t\t\tLOGERR("Unable to decrypt OZIP package!\\n");\n'
HEADER = ("diff --git a/gui/action.cpp b/gui/action.cpp\n"
          f"index {FILE['before_git_blob']}..{FILE['after_git_blob']} 100644\n"
          "--- a/gui/action.cpp\n+++ b/gui/action.cpp\n@@ -1,2772 +1,2779 @@\n")


def function(text, signature):
    if text.count(signature) != 1:
        raise ValueError("Expected one exact function definition")
    start = text.index(signature)
    end = text.index("\n}\n", start) + 3
    return text[start:end]


def project_helper(text, macro_defined):
    """Select the one reviewed conditional without assigning any key value."""
    active = True
    phase = "before"
    selected = []
    for line in text.splitlines(keepends=True):
        token = line.rstrip("\n")
        if token == "#ifndef TW_OZIP_DECRYPT_KEY" and phase == "before":
            active = not macro_defined
            phase = "missing"
        elif token == "#else" and phase == "missing":
            active = macro_defined
            phase = "defined"
        elif token == "#endif" and phase == "defined":
            active = True
            phase = "after"
        elif token.startswith("#"):
            raise ValueError("Unreviewed OZIP conditional")
        elif active:
            selected.append(line)
    if phase != "after":
        raise ValueError("Incomplete OZIP guard")
    return "".join(selected)


def validate_patch(raw):
    """Require the complete source identities and exact two reviewed edits."""
    if not isinstance(raw, bytes) or not raw.endswith(b"\n") or b"\r" in raw or b"\0" in raw:
        raise ValueError("Expected a complete LF-terminated text patch")
    text = raw.decode("utf-8")
    if not text.startswith(HEADER):
        raise ValueError("Unreviewed path, complete Git blobs, mode or hunk coordinates")
    body = text[len(HEADER):].splitlines(keepends=True)
    if (any(line[:1] not in (" ", "+", "-") for line in body)
            or sum(line.startswith((" ", "-")) for line in body) != 2772
            or sum(line.startswith((" ", "+")) for line in body) != 2779):
        raise ValueError("Malformed or additional patch content")
    before = "".join(line[1:] for line in body if line.startswith((" ", "-")))
    after = "".join(line[1:] for line in body if line.startswith((" ", "+")))
    for stage, value in [("before", before), ("after", after)]:
        data = value.encode()
        if len(data) != FILE[stage + "_size_bytes"] or digest(data) != FILE[stage + "_sha256"]:
            raise ValueError("Complete source bytes changed")
    old_helper = function(before, SIGNATURE)
    replacement = SIGNATURE + GUARD + old_helper[len(SIGNATURE):-2] + "#endif\n}\n"
    if before.count(OLD_ERROR) != 1:
        raise ValueError("Unexpected original caller failure block")
    expected = before.replace(old_helper, replacement, 1).replace(OLD_ERROR, NEW_ERROR, 1)
    if after != expected:
        raise ValueError("Only the helper guard and OZIP caller failure status may change")
    return before, after


def ordinary_zip_body(flash):
    start = flash.index('\t\tif((zip_path.substr(zip_path.size() - 4, 4)) == "ozip")\n')
    end = flash.index('\t\tDataManager::SetValue("tw_filename", zip_path);', start)
    return flash[:start] + flash[end:]


def serialized_patch_records(text):
    """Read object slices without normalizing their approved serialized bytes."""
    decoder = json.JSONDecoder()
    start = re.search(r'"patches"\s*:\s*\[', text)
    if start is None:
        raise ValueError("Missing patch array")
    position = start.end()
    records = []
    while True:
        while text[position].isspace() or text[position] == ",":
            position += 1
        if text[position] == "]":
            return records
        value, end = decoder.raw_decode(text, position)
        if not isinstance(value, dict):
            raise ValueError("Expected a patch record")
        records.append(text[position:end])
        position = end


class TwrpOzipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.queue_text = (ROOT / "patches/twrp/series.json").read_text()
        cls.queue = json.loads(cls.queue_text)
        entries = [row for row in cls.queue["patches"] if row["id"] == PATCH_ID]
        if len(entries) != 1:
            raise ValueError("Expected one OZIP patch record selected by ID")
        cls.entry = entries[0]
        cls.patch = (ROOT / "patches/twrp" / (PATCH_ID + ".patch")).read_bytes()
        cls.before, cls.after = validate_patch(cls.patch)

    def test_original_key_reference_is_unconditional_and_new_branch_is_optional(self):
        original = function(self.before, SIGNATURE)
        self.assertIn("(string)TW_OZIP_DECRYPT_KEY", original)
        self.assertNotIn("#if", original)
        guarded = function(self.after, SIGNATURE)
        self.assertIn("#ifndef TW_OZIP_DECRYPT_KEY", guarded)
        self.assertNotIn("TW_OZIP_DECRYPT_KEY", project_helper(guarded, False))

    def test_exact_patch_entry_and_full_file_identities(self):
        self.assertEqual((len(self.patch), digest(self.patch)), (83305, PATCH_SHA256))
        self.assertEqual(canonical(self.entry), ENTRY_SHA256)
        self.assertEqual(self.entry["patch_sha256"], PATCH_SHA256)
        self.assertEqual({key: self.entry["files"][0][key] for key in FILE}, FILE)
        for stage, text in [("before", self.before), ("after", self.after)]:
            raw = text.encode()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual(blob, FILE[stage + "_git_blob"])

    def test_first_touch_preserves_serialized_prior27_without_fixing_final_queue_length(self):
        records = serialized_patch_records(self.queue_text)
        self.assertGreaterEqual(len(records), 28)
        self.assertEqual(digest("\n".join(records[:27]).encode()), BEFORE27_SERIALIZED_SHA256)
        rows = self.queue["patches"]
        index = next(i for i, row in enumerate(rows) if row["id"] == PATCH_ID)
        prior = {(row["project"], file["path"])
                 for row in rows[:index] for file in row["files"]}
        self.assertNotIn(("bootable/recovery", "gui/action.cpp"), prior)
        self.assertNotIn("predecessor_patch_id", self.entry["files"][0])
        self.assertEqual(self.entry["base_commit"], REVISION)
        self.assertEqual(self.entry["project"], "bootable/recovery")

    def test_full_context_source_sizes_delta_and_eof_are_preserved(self):
        self.assertEqual((len(self.before.encode()), len(self.after.encode())), (80100, 80276))
        self.assertEqual((len(self.before.splitlines()), len(self.after.splitlines())), (2772, 2779))
        self.assertTrue(self.before.endswith("\n"))
        self.assertTrue(self.after.endswith("\n"))
        self.assertEqual(len(self.after.encode()) - len(self.before.encode()), 176)

    def test_absent_macro_branch_rejects_before_path_access_execution_or_output_change(self):
        helper = function(self.after, SIGNATURE)
        selected = project_helper(helper, False)
        self.assertEqual(selected, SIGNATURE + DISABLED_BODY + "}\n")
        for forbidden in ("Path_Exists", "Exec_Cmd", "TW_OZIP_DECRYPT_KEY", "return 0;",
                          "rename(", "unlink(", "DataManager", "zip_filename", "flash_zip"):
            self.assertNotIn(forbidden, selected)
        self.assertLess(selected.index("gui_err("), selected.index("return 1;"))

    def test_macro_supplied_branch_retains_exact_original_helper(self):
        self.assertEqual(project_helper(function(self.after, SIGNATURE), True),
                         function(self.before, SIGNATURE))
        self.assertIn('TWFunc::Exec_Cmd("ozip_decrypt "', function(self.before, SIGNATURE))
        self.assertIn("(string)TW_OZIP_DECRYPT_KEY", function(self.before, SIGNATURE))

    def test_caller_records_failure_before_break_and_archive_name_changes(self):
        flash = function(self.after, "int GUIAction::flash(std::string arg)\n{\n")
        start = flash.index("if((ozip_decrypt(zip_path)) != 0)")
        end = flash.index("zip_filename =", start)
        error = flash[start:end]
        self.assertIn(NEW_ERROR + "\t\t\t\tbreak;", error)
        self.assertEqual(error.count("ret_val = 1;"), 1)
        self.assertLess(error.index("ret_val = 1;"), error.index("break;"))
        self.assertNotIn("Exec_Cmd", error)
        self.assertIn("operation_end(ret_val);", flash)
        # GUI actions conventionally return zero after publishing the operation status.
        self.assertTrue(flash.endswith("\treturn 0;\n}\n"))

    def test_ordinary_zip_flow_and_signature_checking_are_byte_identical(self):
        before = function(self.before, "int GUIAction::flash(std::string arg)\n{\n")
        after = function(self.after, "int GUIAction::flash(std::string arg)\n{\n")
        self.assertEqual(ordinary_zip_body(before), ordinary_zip_body(after))
        signature = "int GUIAction::flash_zip(std::string filename, int* wipe_cache)\n{\n"
        self.assertEqual(function(self.before, signature), function(self.after, signature))

    def test_existing_operation_status_and_cleanup_semantics_are_not_rewritten(self):
        signature = "void GUIAction::operation_end(const int operation_status)\n{\n"
        self.assertEqual(function(self.before, signature), function(self.after, signature))
        flash_before = function(self.before, "int GUIAction::flash(std::string arg)\n{\n")
        flash_after = function(self.after, "int GUIAction::flash(std::string arg)\n{\n")
        self.assertEqual(flash_before.split("\tzip_queue_index = 0;", 1)[1],
                         flash_after.split("\tzip_queue_index = 0;", 1)[1])

    def test_all_unrelated_source_and_license_bytes_are_unchanged(self):
        old_helper = function(self.before, SIGNATURE)
        new_helper = function(self.after, SIGNATURE)
        normalized = self.after.replace(new_helper, old_helper, 1).replace(NEW_ERROR, OLD_ERROR, 1)
        self.assertEqual(normalized, self.before)
        self.assertEqual(self.before.split("#include", 1)[0], self.after.split("#include", 1)[0])

    def test_no_key_definition_feature_enablement_or_compiler_waiver(self):
        additions = "".join(line[1:] for line in self.patch.decode().splitlines(keepends=True)
                            if line.startswith("+") and not line.startswith("+++"))
        for forbidden in ("#define", "TW_INCLUDE_CRYPTO", "-Wno", "-Werror", "ALLOW_MISSING",
                          "SELINUX_IGNORE", "setenforce", "BUILD_BROKEN", "GetProperty"):
            self.assertNotIn(forbidden, additions)
        self.assertIs(self.entry["feature_contract"]["supplies_key_or_macro"], False)
        self.assertIs(self.entry["feature_contract"]["changes_feature_selection"], False)

    def test_configured_wiring_and_runtime_limits_are_explicit(self):
        limits = " ".join(self.entry["limits"])
        for fact in ("nonempty Make variable reaching libtwrpgui is not established",
                     "ignores the subprocess exit status", "bookkeeping before the check",
                     "not a global no-side-effects", "do not replace the actual Android compile"):
            self.assertIn(fact, limits)

    def test_unreviewed_guard_and_failure_mutations_are_rejected(self):
        raw = self.patch
        changes = {
            "path": (b"--- a/gui/action.cpp", b"--- a/gui/other.cpp"),
            "mode": (b" 100644\n", b" 100755\n"),
            "short_blob": (FILE["before_git_blob"].encode(), FILE["before_git_blob"][:12].encode()),
            "inverted_guard": (b"+#ifndef TW_OZIP_DECRYPT_KEY", b"+#ifdef TW_OZIP_DECRYPT_KEY"),
            "wrong_macro": (b"+#ifndef TW_OZIP_DECRYPT_KEY", b"+#ifndef TW_INCLUDE_CRYPTO"),
            "missing_failure": (b"+\treturn 1;", b"+\treturn 0;"),
            "missing_error": (b'+\tgui_err("ozip_decrypt_no_key=', b'+\tgui_msg("ozip_decrypt_no_key='),
            "caller_success": (b"+\t\t\t\tret_val = 1;", b"+\t\t\t\tret_val = 0;"),
            "missing_caller_status": (b"+\t\t\t\tret_val = 1;\n", b""),
            "extra_execution": (b"+\t(void)zip_path;", b'+\tTWFunc::Exec_Cmd("ozip_decrypt");'),
            "fake_macro": (b"+#else\n", b"+#else\n+#define TW_OZIP_DECRYPT_KEY\n"),
            "configured_branch_change": (b'TWFunc::Path_Exists("/system/bin/ozip_decrypt")',
                                         b'TWFunc::Path_Exists("/other")'),
            "other_action": (b'operation_start("Flashing")', b'operation_start("Other")'),
            "hunk_count": (b"-1,2772", b"-1,2771"),
            "second_file": (raw, raw + raw),
            "extra_trailer": (raw, raw + b"GIT binary patch\n"),
            "truncation": (raw, raw[:-1]),
        }
        for label, (old, new) in changes.items():
            with self.subTest(mutation=label):
                self.assertIn(old, raw)
                changed = raw.replace(old, new, 1)
                self.assertNotEqual(changed, raw)
                with self.assertRaises(ValueError):
                    validate_patch(changed)

    def test_projection_rejects_unbalanced_or_extra_cpp_directives(self):
        helper = function(self.after, SIGNATURE)
        for changed in (helper.replace("#else\n", "", 1),
                        helper.replace("#endif\n", "", 1),
                        helper.replace("#else\n", "#elif defined(OTHER)\n", 1),
                        helper.replace("#ifndef TW_OZIP_DECRYPT_KEY", "#ifdef TW_OZIP_DECRYPT_KEY", 1)):
            for configured in (False, True):
                with self.subTest(configured=configured), self.assertRaises(ValueError):
                    project_helper(changed, configured)


if __name__ == "__main__":
    unittest.main()
