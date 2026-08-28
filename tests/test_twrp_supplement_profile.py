"""Offline checks for the exact supplementary TWRP selector patches.

Payload and metadata identities bind the reviewed source outside patch hunks.
These tests do not execute Soong, read ignored source reports, or validate a
device. Android default expectations are specific to the pinned SystemUI
constructor; Robolectric insertions retain their original absent property.
"""

from dataclasses import dataclass
import difflib
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SERIES = ROOT / "patches/twrp/series.json"
PROFILE_BLOCK = (
    '    enabled: select(soong_config_variable("nezha_twrp", "native_recovery_only"), {\n'
    '        true: false,\n'
    '        default: unset,\n'
    '    }),\n'
)
SYSTEMUI = "frameworks/libs/systemui"
ROBOLECTRIC = "external/robolectric"
SYSTEMUI_COMMIT = "9aacbcb77aa9353e75bc7c4ebc51d20b8b241b62"
ROBOLECTRIC_COMMIT = "559c38b2cb0fbd87f2118bdcb8bea6f536164d70"
SOONG_COMMIT = "91bdc79cffb29d35b2d46a33204c061c3e7ed4f7"
BLUEPRINT_COMMIT = "dcb14f2e146f40cf1f212efb220e9aa1f3cfc280"
SYSTEMUI_DEFAULT_PROOF_SHA256 = "1bffca8f85a32746fe595ab98b884881f8f5e5966fe196568274b5a5d7b11f2d"
PREVIOUS_FOURTEEN_SHA256 = "d92b7a0e4b47b036a16046af964b895d16d7cdd300f47594746b7864c93b340d"
PREVIOUS_METADATA_SHA256 = "61b0ecdb6721facb6f131c009345d8b424f34f0ccdd321f01d33fba222f0f637"
SUPPLEMENT_PROFILE_KEY = "native_recovery_supplement_profile"
PATCH_IDS = (
    "0015-native-recovery-systemui-robolectric",
    "0016-native-recovery-robolectric-integration-tests",
)
PATCH_CONTRACTS = {
    PATCH_IDS[0]: {
        "project": SYSTEMUI,
        "commit": SYSTEMUI_COMMIT,
        "repository": "https://android.googlesource.com/platform/frameworks/libs/systemui",
        "patch_sha256": "2942d41d013026ead5c5b0fc8582d003a181e60ae5654db9f7f55e7164ebf046",
        "patch_size": 526,
        "file_records_sha256": "4f3020301fe84f6cfa2ca5c4568726f9bc353489ab5e5654f4e08e6344bfc652",
    },
    PATCH_IDS[1]: {
        "project": ROBOLECTRIC,
        "commit": ROBOLECTRIC_COMMIT,
        "repository": "https://android.googlesource.com/platform/external/robolectric",
        "patch_sha256": "f98c8119f416ddf9deff180abddced58417646ce9e890c2ea18e76c233beadf2",
        "patch_size": 1290,
        "file_records_sha256": "8abb7bc5ec8a75d2ca0fd75e937f6be20fa2cd97089e2a95d00018bba91eef18",
    },
}
SOURCE_PROOF_FILES = {
    "build/soong/android/module.go": "0220bdc66ff68ee95ff0f1d00433ce13ef3a46b599059ccd1e3befbef74b5c05",
    "build/soong/android/arch.go": "e2ccc72ad54ccc36b4ed56baf6f8dabde7c9e9a275b712e916dc475244f837ac",
    "build/soong/java/robolectric.go": "b2ddae1c9b310d894298f8b35beecb2774ecd3d36ee1f71ebd60dbe4f440210f",
    "build/soong/java/base.go": "b2fb9345a48c5e050252ec8529d79f81e35e990c5e6a241a884527fbafcf7c65",
    "build/blueprint/proptools/configurable.go": "272a7b80f9504332e4f7520aff51c8f3e1873c9efa0f79d14b1f31869853fe50",
}
HUNK_POSITIONS = {
    "animationlib/Android.bp": (60, 7, 10),
    "integration_tests/ctesque/Android.bp": (2, 10, 14),
    "integration_tests/nativegraphics/Android.bp": (45, 10, 14),
}
UNSET = object()


@dataclass(frozen=True)
class Gate:
    path: str
    name: str
    operation: str
    constructor: str = "android_robolectric_test"

    @property
    def before_anchor(self):
        prefix = self.constructor + " {\n"
        if self.operation == "replace_existing_literal_true":
            prefix += "    enabled: true,\n"
        return prefix + f'    name: "{self.name}",\n'

    @property
    def after_anchor(self):
        if self.operation == "replace_existing_literal_true":
            return self.before_anchor.replace("    enabled: true,\n", PROFILE_BLOCK, 1)
        return self.before_anchor + PROFILE_BLOCK


GATES = {
    SYSTEMUI: (
        Gate("animationlib/Android.bp", "animationlib_robo_tests", "replace_existing_literal_true"),
    ),
    ROBOLECTRIC: (
        Gate("integration_tests/ctesque/Android.bp", "CtesqueRoboTests", "insert_new_property"),
        Gate("integration_tests/nativegraphics/Android.bp", "NativeGraphicsTests", "insert_new_property"),
    ),
}


@dataclass(frozen=True)
class Hunk:
    path: str
    old_start: int
    new_start: int
    before_blob: str
    after_blob: str
    before: str
    after: str
    body: tuple


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical_sha256(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def git_blob(raw):
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def unquoted_code(text):
    """Mask complete BP strings/comments while retaining every byte position."""
    chars = list(text)
    index = 0
    while index < len(text):
        start = index
        if text.startswith("//", index):
            index = text.find("\n", index)
            if index < 0:
                index = len(text)
        elif text.startswith("/*", index):
            end = text.find("*/", index + 2)
            if end < 0:
                raise ValueError("Hunk contains an incomplete block comment")
            index = end + 2
        elif text[index] == '"':
            index += 1
            while index < len(text) and text[index] != '"':
                if text[index] == "\n":
                    raise ValueError("Hunk contains an incomplete string")
                if text[index] == "\\":
                    if index + 1 >= len(text) or text[index + 1] in "\r\n":
                        raise ValueError("Hunk contains a dangling escape or escaped newline")
                    index += 2
                else:
                    index += 1
            if index >= len(text):
                raise ValueError("Hunk contains an incomplete string")
            index += 1
        else:
            index += 1
            continue
        for position in range(start, index):
            if chars[position] != "\n":
                chars[position] = " "
    return "".join(chars)


def validate_supplement_patch(text, project):
    """Accept only the three named source edits, with strict counted diff syntax.

    These checks constrain the hunks. The sealed full-file hashes and Git blobs
    separately bind source outside the hunks; this is not a general BP parser.
    """
    if project not in GATES:
        raise ValueError("Unapproved supplementary patch project")
    if not isinstance(text, str) or not text.endswith("\n") or "\r" in text or "\0" in text:
        raise ValueError("Patch must contain complete LF-terminated text")
    lines = text.splitlines(keepends=True)
    starts = [index for index, line in enumerate(lines) if line.startswith("diff --git ")]
    if not starts or starts[0] != 0 or len(starts) != len(GATES[project]):
        raise ValueError("Patch must have exactly the reviewed file sections and no preamble")
    result = {}
    for number, gate in enumerate(GATES[project]):
        start = starts[number]
        stop = starts[number + 1] if number + 1 < len(starts) else len(lines)
        section = lines[start:stop]
        if len(section) < 6 or section[0] != f"diff --git a/{gate.path} b/{gate.path}\n":
            raise ValueError("Patch file path, ordering, or rename differs")
        index = re.fullmatch(r"index ([0-9a-f]{40})\.\.([0-9a-f]{40}) 100644\n", section[1])
        if not index or index[1] == index[2]:
            raise ValueError("Patch requires two different full Git blobs and unchanged 100644 mode")
        if section[2:4] != [f"--- a/{gate.path}\n", f"+++ b/{gate.path}\n"]:
            raise ValueError("Patch must modify the same existing regular file")
        header = re.fullmatch(
            r"@@ -([1-9][0-9]*),([1-9][0-9]*) \+([1-9][0-9]*),([1-9][0-9]*) @@(?: [^\n]*)?\n",
            section[4],
        )
        if not header:
            raise ValueError("Exactly one explicit counted hunk is required per file")
        old_start, old_count, new_start, new_count = map(int, header.groups())
        body = section[5:]
        if old_start != new_start or any(line[:1] not in (" ", "+", "-") for line in body):
            raise ValueError("Unexpected hunk, trailer, marker, or changed start position")
        if (sum(line.startswith((" ", "-")) for line in body) != old_count
                or sum(line.startswith((" ", "+")) for line in body) != new_count):
            raise ValueError("Hunk line counts differ from its complete body")
        before = "".join(line[1:] for line in body if line.startswith((" ", "-")))
        after = "".join(line[1:] for line in body if line.startswith((" ", "+")))
        additions = "".join(line[1:] for line in body if line.startswith("+"))
        removals = "".join(line[1:] for line in body if line.startswith("-"))
        if additions != PROFILE_BLOCK:
            raise ValueError("Only the literal typed Boolean selector with default unset may be added")
        expected_removed = "    enabled: true,\n" if gate.operation == "replace_existing_literal_true" else ""
        if removals != expected_removed:
            raise ValueError("Only the declared literal-true replacement may remove source")
        before_code, after_code = unquoted_code(before), unquoted_code(after)
        before_enabled = re.findall(r"\benabled\s*:", before_code)
        if len(before_enabled) != bool(expected_removed):
            raise ValueError("Existing enabled properties would be duplicated or were not reviewed")
        anchors = [
            match for match in re.finditer("^" + re.escape(gate.before_anchor), before, re.M)
            if before_code[match.start():match.start() + len(gate.constructor)] == gate.constructor
        ]
        if len(anchors) != 1:
            raise ValueError("Gate is not anchored to the exact approved constructor and name")
        anchor = anchors[0]
        expected_after = before[:anchor.start()] + gate.after_anchor + before[anchor.end():]
        if after != expected_after:
            raise ValueError("Gate placement or other module properties changed")
        if len(re.findall(r"\benabled\s*:", after_code)) != 1:
            raise ValueError("Expected exactly one resulting enabled property")
        result[gate.path] = Hunk(gate.path, old_start, new_start, index[1], index[2],
                                 before, after, tuple(body))
    return result


def apply_exact_hunk(before, hunk):
    """Replay one reviewed text hunk in memory; never invoke Git or patch."""
    lines = before.decode("utf-8").splitlines(keepends=True)
    start = hunk.old_start - 1
    old_lines = hunk.before.splitlines(keepends=True)
    if lines[start:start + len(old_lines)] != old_lines:
        raise ValueError("Complete preimage does not match the hunk at its declared position")
    after = ("".join(lines[:start]) + hunk.after + "".join(lines[start + len(old_lines):])).encode()
    if git_blob(before) != hunk.before_blob or git_blob(after) != hunk.after_blob:
        raise ValueError("Complete preimage or postimage differs from the indexed Git blob")
    return after


def typed_profile_branch(value):
    """Expected branch for this exact literal selector; not a Soong evaluator."""
    if value is not None and type(value) is not bool:
        raise ValueError("Only typed Booleans or absence are accepted by this expectation")
    return False if value is True else UNSET


def documented_systemui_android_enabled(value, forced_disabled=False):
    """Expected Android result from the cited factory/ModuleBase source proof.

    Scoped to animationlib_robo_tests without an enabled/default override.
    A returned value is a source-contract expectation, not an executed graph.
    """
    if type(forced_disabled) is not bool:
        raise ValueError("ForcedDisabled expectation must be a Boolean")
    if forced_disabled:
        return False
    branch = typed_profile_branch(value)
    return True if branch is UNSET else branch


def make_section(gate, before=None, after=None):
    """Synthetic, explicitly named fixture for validator mutation tests."""
    if before is None:
        before = gate.before_anchor + '    srcs: ["src/**/*.java"],\n}\n'
    if after is None:
        after = before.replace(gate.before_anchor, gate.after_anchor, 1)
    diff = "".join(difflib.unified_diff(before.splitlines(keepends=True), after.splitlines(keepends=True),
                                      fromfile="a/" + gate.path, tofile="b/" + gate.path, n=3))
    return (f"diff --git a/{gate.path} b/{gate.path}\n"
            f"index {git_blob(before.encode())}..{git_blob(after.encode())} 100644\n" + diff)


def fixture_patch(project):
    return "".join(make_section(gate) for gate in GATES[project])


def recount(text):
    """Keep mutated hunk counts valid so semantic negatives cannot pass by syntax alone."""
    lines = text.splitlines(keepends=True)
    indexes = [i for i, line in enumerate(lines) if line.startswith("@@ ")]
    for number, index in enumerate(indexes):
        stop = indexes[number + 1] if number + 1 < len(indexes) else len(lines)
        for candidate in range(index + 1, stop):
            if lines[candidate].startswith("diff --git "):
                stop = candidate
                break
        header = re.fullmatch(r"@@ -(\d+),\d+ \+(\d+),\d+ @@(.*)\n", lines[index])
        if header is None:
            raise AssertionError("Fixture hunk header is not explicit")
        body = lines[index + 1:stop]
        old_count = sum(line.startswith((" ", "-")) for line in body)
        new_count = sum(line.startswith((" ", "+")) for line in body)
        lines[index] = f"@@ -{header[1]},{old_count} +{header[2]},{new_count} @@{header[3]}\n"
    return "".join(lines)


class SupplementSelectorMutationTests(unittest.TestCase):
    def test_incomplete_strings_comments_and_escaped_newlines_are_rejected(self):
        for text in ('"unfinished', '"dangling\\', '"line\\\ncontinued"', '/* missing terminator'):
            with self.subTest(text=text), self.assertRaises(ValueError):
                unquoted_code(text)

    def test_three_named_gates_have_distinct_replacement_and_insertion_contracts(self):
        for project, gates in GATES.items():
            with self.subTest(project=project):
                parsed = validate_supplement_patch(fixture_patch(project), project)
                self.assertEqual(list(parsed), [gate.path for gate in gates])
                for gate in gates:
                    item = parsed[gate.path]
                    self.assertEqual(item.after.replace(PROFILE_BLOCK, "", 1),
                                     item.before.replace("    enabled: true,\n", "", 1))
        self.assertEqual(sum(len(gates) for gates in GATES.values()), 3)

    def test_wrong_constructor_or_production_name_cannot_receive_the_gate(self):
        for project, gates in GATES.items():
            original = fixture_patch(project)
            for gate in gates:
                for old, new in ((gate.constructor + " {", "android_library {"),
                                 (gate.constructor + " {", "custom_android_robolectric_test {"),
                                 (f'name: "{gate.name}"', 'name: "production_library"')):
                    with self.subTest(project=project, module=gate.name, replacement=new), self.assertRaises(ValueError):
                        validate_supplement_patch(original.replace(old, new, 1), project)

    def test_selector_rejects_string_patterns_wrong_namespace_and_changed_defaults(self):
        replacements = (
            ('true: false', '"true": false'), ('true: false', 'true: true'),
            ('default: unset', 'default: true'), ('default: unset', 'default: false'),
            ('default: unset', 'default: "unset"'), ('default: unset', 'default: null'),
            ('"nezha_twrp"', '"other_product"'), ('"native_recovery_only"', '"different_flag"'),
        )
        for project in GATES:
            for before, after in replacements:
                with self.subTest(project=project, replacement=after), self.assertRaises(ValueError):
                    validate_supplement_patch(fixture_patch(project).replace(before, after, 1), project)

    def test_extra_selector_branches_properties_and_removals_are_rejected(self):
        for project in GATES:
            original = fixture_patch(project)
            mutations = (
                original.replace("+        default: unset,\n", "+        false: false,\n+        default: unset,\n", 1),
                original.replace("+    }),\n", "+    }),\n+    defaults: [\"extra\"],\n", 1),
                original.replace('     srcs: ["src/**/*.java"],\n', '-    srcs: ["src/**/*.java"],\n', 1),
                original.replace('     srcs: ["src/**/*.java"],\n',
                                 '-    srcs: ["src/**/*.java"],\n+    srcs: ["other/**/*.java"],\n', 1),
            )
            for mutation in mutations:
                with self.subTest(project=project, mutation=mutation), self.assertRaises(ValueError):
                    validate_supplement_patch(recount(mutation), project)

    def test_duplicate_or_preexisting_enabled_is_rejected_with_valid_hunk_counts(self):
        for project, gates in GATES.items():
            original = fixture_patch(project)
            for gate in gates:
                name = f'     name: "{gate.name}",\n'
                for extra in ("     enabled: true,\n", " \tenabled : false,\n"):
                    mutation = original.replace(name, name + extra, 1)
                    with self.subTest(module=gate.name, extra=extra), self.assertRaises(ValueError):
                        validate_supplement_patch(recount(mutation), project)

    def test_inline_or_comment_separated_existing_enabled_cannot_escape_duplicate_check(self):
        for project, gates in GATES.items():
            for extra in ('    srcs: ["src/**/*.java"], enabled: false,\n',
                          '    enabled /* existing property */ : false,\n'):
                first = gates[0]
                before = first.before_anchor + extra + '    libs: ["unchanged"],\n}\n'
                sections = [make_section(first, before)] + [make_section(gate) for gate in gates[1:]]
                with self.subTest(project=project, extra=extra), self.assertRaises(ValueError):
                    validate_supplement_patch("".join(sections), project)

    def test_enabled_text_inside_unchanged_strings_or_comments_is_not_a_property(self):
        for project, gates in GATES.items():
            sections = []
            for gate in gates:
                before = (gate.before_anchor + '    srcs: ["enabled: false"],\n'
                          '    // enabled: false is only a comment.\n}\n')
                sections.append(make_section(gate, before))
            with self.subTest(project=project):
                validate_supplement_patch("".join(sections), project)

    def test_replacement_cannot_turn_into_an_insertion_or_remove_a_false_literal(self):
        original = fixture_patch(SYSTEMUI)
        mutations = (
            original.replace("-    enabled: true,\n", "", 1),
            original.replace("-    enabled: true,\n", "-    enabled: false,\n", 1),
            original.replace("-    enabled: true,\n", '-    enabled: "true",\n', 1),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_supplement_patch(recount(mutation), SYSTEMUI)

    def test_insertion_cannot_replace_an_existing_property(self):
        original = fixture_patch(ROBOLECTRIC)
        mutation = original.replace("+    enabled:", "-    enabled: true,\n+    enabled:", 1)
        with self.assertRaises(ValueError):
            validate_supplement_patch(recount(mutation), ROBOLECTRIC)

    def test_header_context_cannot_substitute_for_the_actual_constructor_anchor(self):
        original = fixture_patch(SYSTEMUI)
        mutation = original.replace(" android_robolectric_test {\n", " android_library {\n", 1)
        mutation = re.sub(r"(@@ -\d+,\d+ \+\d+,\d+ @@)[^\n]*", r"\1 android_robolectric_test {", mutation, count=1)
        with self.assertRaises(ValueError):
            validate_supplement_patch(mutation, SYSTEMUI)

    def test_commented_constructor_cannot_authorize_a_gate(self):
        for project, gates in GATES.items():
            sections = []
            for gate in gates:
                before = "/*\n" + gate.before_anchor + '    srcs: ["unchanged"],\n}\n*/\n'
                sections.append(make_section(gate, before))
            with self.subTest(project=project), self.assertRaises(ValueError):
                validate_supplement_patch("".join(sections), project)

    def test_gate_cannot_move_past_another_module_property(self):
        for project, gates in GATES.items():
            pieces = []
            for number, gate in enumerate(gates):
                before = gate.before_anchor + '    srcs: ["src/**/*.java"],\n}\n'
                after = before.replace("    enabled: true,\n", "", 1)
                after = after.replace('    srcs: ["src/**/*.java"],\n',
                                      '    srcs: ["src/**/*.java"],\n' + PROFILE_BLOCK, 1)
                pieces.append(make_section(gate, before, after) if number == 0 else make_section(gate))
            with self.subTest(project=project), self.assertRaises(ValueError):
                validate_supplement_patch("".join(pieces), project)

    def test_paths_modes_new_files_renames_and_extra_sections_are_rejected(self):
        for project, gates in GATES.items():
            original = fixture_patch(project)
            path = gates[0].path
            mutations = (
                original.replace(path, "../outside/Android.bp"),
                original.replace(f"b/{path}\n", "b/other/Android.bp\n", 1),
                original.replace(" 100644\n", " 100755\n", 1),
                original.replace("--- a/" + path, "--- /dev/null", 1),
                original.replace("index ", "old mode 100644\nnew mode 100755\nindex ", 1),
                original.replace("index ", "rename from old\nrename to new\nindex ", 1),
                original + make_section(gates[0]),
            )
            for mutation in mutations:
                with self.subTest(project=project, mutation=mutation), self.assertRaises(ValueError):
                    validate_supplement_patch(mutation, project)

    def test_hunk_counts_boundaries_and_diff_trailers_are_rejected(self):
        for project in GATES:
            original = fixture_patch(project)
            mutations = (
                "preamble\n" + original, original + "trailer\n",
                original + "\\ No newline at end of file\n", original.rstrip("\n"),
                original.replace("\n", "\r\n"), original + "\0\n",
                re.sub(r"(@@ -\d+,)\d+", r"\g<1>999", original, count=1),
                re.sub(r"(@@ -\d+,\d+ \+)\d+", r"\g<1>999", original, count=1),
                original + "@@ -1,1 +1,1 @@\n old\n",
            )
            for mutation in mutations:
                with self.subTest(project=project, mutation=mutation), self.assertRaises(ValueError):
                    validate_supplement_patch(mutation, project)

    def test_missing_reordered_or_duplicate_robolectric_file_sections_are_rejected(self):
        first, second = (make_section(gate) for gate in GATES[ROBOLECTRIC])
        for mutation in (first, second, second + first, first + first):
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_supplement_patch(mutation, ROBOLECTRIC)

    def test_unreviewed_project_is_not_an_alternate_contract(self):
        with self.assertRaises(ValueError):
            validate_supplement_patch(fixture_patch(SYSTEMUI), "frameworks/base")

    def test_full_file_replay_binds_unchanged_source_and_git_blob_identities(self):
        gate = GATES[SYSTEMUI][0]
        before = gate.before_anchor + '    srcs: ["src/**/*.java"],\n}\n'
        after = before.replace(gate.before_anchor, gate.after_anchor, 1)
        hunk = validate_supplement_patch(make_section(gate, before, after), SYSTEMUI)[gate.path]
        self.assertEqual(apply_exact_hunk(before.encode(), hunk), after.encode())
        for changed in (before.replace("src/**/*.java", "other/**/*.java").encode(), before.encode() + b"extra\n"):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                apply_exact_hunk(changed, hunk)


class SupplementSelectorExpectationTests(unittest.TestCase):
    def test_exact_literal_selector_has_typed_true_false_and_absent_branches(self):
        for gates in GATES.values():
            for gate in gates:
                with self.subTest(module=gate.name):
                    self.assertIs(typed_profile_branch(True), False)
                    self.assertIs(typed_profile_branch(False), UNSET)
                    self.assertIs(typed_profile_branch(None), UNSET)

    def test_wrong_present_types_are_not_treated_as_false_or_absent(self):
        for value in ("true", "false", "unset", "", 0, 1, (), [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                typed_profile_branch(value)

    def test_systemui_expected_android_values_keep_forced_disabled_precedence(self):
        # Expected results only. The pinned source proof below supplies the
        # Android factory and default; this Python helper does not execute Soong.
        self.assertIs(documented_systemui_android_enabled(True), False)
        self.assertIs(documented_systemui_android_enabled(False), True)
        self.assertIs(documented_systemui_android_enabled(None), True)
        for value in (True, False, None, "not_evaluated_when_forced_disabled"):
            self.assertIs(documented_systemui_android_enabled(value, forced_disabled=True), False)

    def test_robolectric_unset_branches_preserve_original_absent_enabled_property(self):
        parsed = validate_supplement_patch(fixture_patch(ROBOLECTRIC), ROBOLECTRIC)
        for gate in GATES[ROBOLECTRIC]:
            with self.subTest(module=gate.name):
                self.assertNotRegex(unquoted_code(parsed[gate.path].before), r"\benabled\s*:")
                self.assertEqual(parsed[gate.path].after.replace(PROFILE_BLOCK, "", 1), parsed[gate.path].before)
                self.assertIs(typed_profile_branch(False), UNSET)
                self.assertIs(typed_profile_branch(None), UNSET)


class SupplementProfileRecordTests(unittest.TestCase):
    def setUp(self):
        self.record = json.loads(SERIES.read_text())
        self.profile = self.record[SUPPLEMENT_PROFILE_KEY]
        self.entries = {entry["id"]: entry for entry in self.record["patches"]}

    def test_original_fourteen_patch_records_and_all_historical_metadata_are_unchanged(self):
        self.assertEqual(len(self.record["patches"]), 16)
        self.assertEqual([entry["id"] for entry in self.record["patches"][-2:]], list(PATCH_IDS))
        self.assertEqual(canonical_sha256(self.record["patches"][:14]), PREVIOUS_FOURTEEN_SHA256)
        historical = {key: value for key, value in self.record.items()
                      if key not in ("patches", SUPPLEMENT_PROFILE_KEY)}
        self.assertEqual(canonical_sha256(historical), PREVIOUS_METADATA_SHA256)

    def test_new_profile_inventory_is_separate_and_names_exactly_three_operations(self):
        common = {
            "namespace": "nezha_twrp",
            "boolean_variable": "native_recovery_only",
            "selected_value": True,
            "enabled_when_selected": False,
            "otherwise": "unset",
            "patch_ids": list(PATCH_IDS),
            "test_module_type": "android_robolectric_test",
            "test_module_count": 3,
            "affected_file_count": 3,
            "affected_supplementary_project_count": 2,
            "supplemental_projects_modified": True,
            "previous_fourteen_patch_records_sha256": PREVIOUS_FOURTEEN_SHA256,
            "previous_metadata_sha256": PREVIOUS_METADATA_SHA256,
            "operations": {gate.name: gate.operation for gates in GATES.values() for gate in gates},
        }
        self.assertEqual({key: self.profile[key] for key in common}, common)
        self.assertIs(self.profile["selected_value"], True)
        self.assertIs(self.profile["enabled_when_selected"], False)
        self.assertIs(self.profile["supplemental_projects_modified"], True)
        self.assertEqual(set(self.profile), {
            *common, "default_enabled_source_proof", "tooling_contract_commit", "provenance",
            "historical_boundary", "dependency_dispatch", "candidate_validation", "preserved_behavior",
            "source_selection_boundary", "validation_boundary",
        })

    def test_new_record_keeps_source_projection_and_validation_limits_explicit(self):
        self.assertEqual(self.profile["tooling_contract_commit"], "8b4ad6edc0fb090df2cca4b73ec456357790fe06")
        self.assertEqual(self.profile["candidate_validation"], {
            "systemui_candidate_checks": 14,
            "systemui_semantics_checks": 25,
            "robolectric_candidate_checks": 18,
            "robolectric_incoming_checks": 20,
            "android_graph_verified": False,
            "recovery_compile_verified": False,
            "device_behavior_verified": False,
        })
        for name in ("android_graph_verified", "recovery_compile_verified", "device_behavior_verified"):
            self.assertIs(self.profile["candidate_validation"][name], False)
        self.assertEqual(self.profile["dependency_dispatch"], {
            "soong_commit": SOONG_COMMIT,
            "source": "build/soong/android/mutator.go:478-482",
            "disabled_skips": ["baseDepsMutator", "robolectricTest.DepsMutator"],
            "boundary": "Disabling these modules skips their normal dependency-mutator dispatch, not Blueprint parsing or all Soong validation.",
        })
        self.assertIn("not three additional observed graph failures", self.profile["provenance"])
        self.assertIn("historical audits", self.profile["historical_boundary"])
        self.assertIn("NativeGraphicsTestsAssetsLib", self.profile["preserved_behavior"])
        self.assertIn("separate reviewed device/config changes", self.profile["source_selection_boundary"])
        self.assertIn("does not claim full Android test coverage", self.profile["validation_boundary"])
        self.assertIn("No missing-dependency, SELinux, signature, AVB, VINTF, ELF", self.profile["validation_boundary"])

    def test_source_pins_payloads_and_complete_file_metadata_match_the_sealed_candidates(self):
        for identifier, contract in PATCH_CONTRACTS.items():
            with self.subTest(patch=identifier):
                entry = self.entries[identifier]
                self.assertEqual(entry["project"], contract["project"])
                self.assertEqual(entry["base_commit"], contract["commit"])
                self.assertEqual(entry["repository"], contract["repository"])
                self.assertEqual(entry["source_owner"], "supplementary")
                self.assertEqual(entry["patch"], "patches/twrp/" + identifier + ".patch")
                self.assertEqual(entry["patch_sha256"], contract["patch_sha256"])
                self.assertEqual(canonical_sha256(entry["files"]), contract["file_records_sha256"])
                payload = ROOT / entry["patch"]
                self.assertFalse(payload.is_symlink())
                raw = payload.read_bytes()
                self.assertEqual(len(raw), contract["patch_size"])
                self.assertEqual(sha256(raw), contract["patch_sha256"])
                sections = validate_supplement_patch(raw.decode(), contract["project"])
                self.assertEqual([item["path"] for item in entry["files"]], list(sections))

    def test_actual_named_hunks_match_full_blob_metadata_positions_and_exact_size_deltas(self):
        for identifier, contract in PATCH_CONTRACTS.items():
            entry = self.entries[identifier]
            sections = validate_supplement_patch((ROOT / entry["patch"]).read_text(), contract["project"])
            gates = {gate.path: gate for gate in GATES[contract["project"]]}
            for item in entry["files"]:
                gate, hunk = gates[item["path"]], sections[item["path"]]
                with self.subTest(module=gate.name):
                    self.assertEqual((hunk.old_start, len(hunk.before.splitlines()), len(hunk.after.splitlines())),
                                     HUNK_POSITIONS[item["path"]])
                    self.assertEqual(hunk.new_start, hunk.old_start)
                    self.assertEqual(hunk.before_blob, item["before_git_blob"])
                    self.assertEqual(hunk.after_blob, item["after_git_blob"])
                    removed = len("    enabled: true,\n".encode()) if gate.operation == "replace_existing_literal_true" else 0
                    self.assertEqual(item["after_size_bytes"] - item["before_size_bytes"], len(PROFILE_BLOCK.encode()) - removed)
                    self.assertEqual(item["source_url"], contract["repository"] + "/+/" + contract["commit"]
                                     + "/" + item["path"] + "?format=TEXT")
                    self.assertEqual(len(item["profile_modules"]), 1)
                    module = item["profile_modules"][0]
                    self.assertEqual(module["name"], gate.name)
                    self.assertEqual(module["type"], gate.constructor)
                    self.assertIs(module["enabled_property_before"], gate.operation == "replace_existing_literal_true")
                    if gate.operation == "replace_existing_literal_true":
                        self.assertIs(module["enabled_value_before"], True)
                        self.assertIs(module["original_enabled_value"], True)
                        self.assertEqual(module["enabled_property_operation"], gate.operation)
                        self.assertEqual(module["defaults_before"], [])
                        self.assertEqual(hunk.after.replace(PROFILE_BLOCK, "    enabled: true,\n", 1), hunk.before)
                    else:
                        self.assertNotIn("enabled_value_before", module)
                        self.assertEqual(hunk.after.replace(PROFILE_BLOCK, "", 1), hunk.before)

    def test_systemui_default_expectation_is_bound_to_pinned_source_evidence(self):
        # Verify the tracked evidence descriptor without opening ignored reports
        # or treating this Python source expectation as an executed Soong graph.
        proof = self.profile["default_enabled_source_proof"]
        self.assertEqual(proof, {
            "soong_commit": SOONG_COMMIT,
            "blueprint_commit": BLUEPRINT_COMMIT,
            "report": {"path": "reports/twrp-systemui-animation-robo-gate-review.json",
                       "sha256": SYSTEMUI_DEFAULT_PROOF_SHA256},
            "files": SOURCE_PROOF_FILES,
            "replacement_module": "animationlib_robo_tests",
            "android_os_default_disabled": False,
            "explicit_defaults": [],
            "enable_overrides": [],
            "forced_disabled_preserved": True,
            "typed_false_or_absent_effective_enabled": True,
            "present_wrong_type": "error",
            "scope": "Exact reviewed DeviceSupported Android module; not a general unset/true equivalence.",
            "source_chain": [
                "build/soong/java/robolectric.go:332-347 selects DeviceSupported.",
                "build/soong/android/arch.go:278,328 registers Android with DefaultDisabled=false.",
                "build/soong/android/module.go:1439-1443 honors ForcedDisabled before Enabled.GetOrDefault(..., !Os.DefaultDisabled).",
                "build/blueprint/proptools/configurable.go:1237-1238 represents unset as nil; 647-654 returns the fallback.",
                "build/soong/android/module.go:2709-2736 and build/blueprint/proptools/configurable.go:829-831 distinguish typed Boolean, missing and incorrectly typed conditions.",
            ],
        })
        self.assertIs(proof["android_os_default_disabled"], False)
        self.assertIs(proof["forced_disabled_preserved"], True)
        self.assertIs(proof["typed_false_or_absent_effective_enabled"], True)




if __name__ == "__main__":
    unittest.main()
