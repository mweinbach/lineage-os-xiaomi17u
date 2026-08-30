"""Synthetic ELF tests only. No proprietary firmware or subprocesses used."""

import copy
import hashlib
import struct
import unittest

from scripts.framework_provider_derivations import DerivationError, KIND, derive_needed
from scripts.apex_inputs import elf_dynamic


OLD = "libaudio-types-V2.so"
NEW = "libaudio-types-V4.so"
PHOFF, PHSIZE, DYNOFF, STROFF, FILESIZE = 64, 56, 288, 640, 1024
OLD_OFFSET = STROFF + 1
BYTE_OFFSET = OLD_OFFSET + OLD.index("2")


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def fixture(*, duplicate_needed=False, duplicate_string=False,
            existing_new=False, alias_tag=None, interpreter_alias=False,
            executable=False, target_is_needed=True):
    """Minimal inert AArch64 DSO with full dynamic and interpreter metadata."""
    raw = bytearray(FILESIZE)
    raw[:16] = b"\x7fELF\x02\x01\x01" + bytes(9)
    phcount = 3
    struct.pack_into("<HHIQQQIHHHHHH", raw, 16, 3, 183, 1, 0, PHOFF, 0, 0,
                     64, PHSIZE, phcount, 0, 0, 0)
    strings = bytearray(b"\0")
    indices = {}
    for name in (OLD, "libother.so", "libfixture.so", "$ORIGIN/../lib64"):
        indices[name] = len(strings)
        strings.extend(name.encode("ascii") + b"\0")
    if duplicate_string:
        strings.extend(OLD.encode("ascii") + b"\0")
    if existing_new:
        indices[NEW] = len(strings)
        strings.extend(NEW.encode("ascii") + b"\0")
    raw[STROFF:STROFF + len(strings)] = strings
    entries = [(5, 0x1000 + STROFF), (10, len(strings))]
    if target_is_needed:
        entries.append((1, indices[OLD]))
    entries.extend([(1, indices["libother.so"]),
                    (14, indices["libfixture.so"]),
                    (29, indices["$ORIGIN/../lib64"])])
    if duplicate_needed:
        entries.append((1, indices[OLD]))
    if existing_new:
        entries.append((1, indices[NEW]))
    if alias_tag is not None:
        if alias_tag in (14, 29):
            entries = [(tag, indices[OLD] if tag == alias_tag else value)
                       for tag, value in entries]
        else:
            entries.append((alias_tag, indices[OLD] + 1))
    entries.append((0, 0))
    for index, entry in enumerate(entries):
        struct.pack_into("<qQ", raw, DYNOFF + 16 * index, *entry)
    dynsize = 16 * len(entries)
    struct.pack_into("<IIQQQQQQ", raw, PHOFF, 1, 5 if executable else 4,
                     0, 0x1000, 0, FILESIZE, FILESIZE, 4096)
    struct.pack_into("<IIQQQQQQ", raw, PHOFF + PHSIZE, 2, 4, DYNOFF,
                     0x1000 + DYNOFF, 0, dynsize, dynsize, 8)
    interpreter = b"/system/bin/linker64\0"
    interpoff, interpsize = (OLD_OFFSET, len(OLD) + 1) if interpreter_alias else (560, len(interpreter))
    if not interpreter_alias:
        raw[interpoff:interpoff + interpsize] = interpreter
    struct.pack_into("<IIQQQQQQ", raw, PHOFF + 2 * PHSIZE, 3, 4, interpoff,
                     0x1000 + interpoff, 0, interpsize, interpsize, 1)
    return bytes(raw)


def recipe(raw):
    derived = raw[:BYTE_OFFSET] + b"4" + raw[BYTE_OFFSET + 1:]
    return {"kind": KIND, "original": identity(raw), "derived": identity(derived),
            "old": OLD, "new": NEW, "dt_needed_string_file_offset": OLD_OFFSET,
            "changed_byte_file_offset": BYTE_OFFSET, "original_byte_hex": "32",
            "derived_byte_hex": "34"}


class NeededDerivationTests(unittest.TestCase):
    def test_positive_preserves_input_and_all_unselected_bytes_and_metadata(self):
        raw = fixture()
        saved = bytes(raw)
        rule = recipe(raw)
        saved_rule = copy.deepcopy(rule)
        result = derive_needed(raw, rule)
        self.assertIs(type(result), bytes)
        self.assertEqual(raw, saved)
        self.assertEqual(rule, saved_rule)
        self.assertEqual(result[:BYTE_OFFSET], raw[:BYTE_OFFSET])
        self.assertEqual(result[BYTE_OFFSET + 1:], raw[BYTE_OFFSET + 1:])
        self.assertEqual(result[BYTE_OFFSET], ord("4"))
        self.assertEqual(identity(result), rule["derived"])
        before, after = elf_dynamic(raw), elf_dynamic(result)
        self.assertEqual(before.pop("needed"), [OLD, "libother.so"])
        self.assertEqual(after.pop("needed"), [NEW, "libother.so"])
        self.assertEqual(before, after)

    def test_mutable_source_is_rejected(self):
        raw = fixture()
        with self.assertRaisesRegex(DerivationError, "immutable"):
            derive_needed(bytearray(raw), recipe(raw))

    def test_original_hash_and_size_are_bound(self):
        raw = fixture()
        for change in ({"sha256": "a" * 64}, {"size_bytes": len(raw) - 1}):
            rule = recipe(raw)
            rule["original"].update(change)
            if "size_bytes" in change:
                rule["derived"]["size_bytes"] = change["size_bytes"]
            with self.subTest(change=change), self.assertRaisesRegex(DerivationError, "original hash or size"):
                derive_needed(raw, rule)

    def test_derived_hash_and_size_are_bound(self):
        raw = fixture()
        for change in ({"sha256": "a" * 64}, {"size_bytes": len(raw) + 1}):
            rule = recipe(raw)
            rule["derived"].update(change)
            with self.subTest(change=change), self.assertRaises(DerivationError):
                derive_needed(raw, rule)

    def test_unrelated_changed_input_byte_is_rejected(self):
        raw = fixture()
        rule = recipe(raw)
        changed = raw[:-1] + b"x"
        with self.assertRaisesRegex(DerivationError, "original hash or size"):
            derive_needed(changed, rule)

    def test_reviewed_offsets_must_agree_with_actual_dt_needed(self):
        raw = fixture()
        for shifted in ("string", "byte", "both"):
            rule = recipe(raw)
            if shifted in ("string", "both"):
                rule["dt_needed_string_file_offset"] += 1
            if shifted in ("byte", "both"):
                rule["changed_byte_file_offset"] += 1
            with self.subTest(shifted=shifted), self.assertRaises(DerivationError):
                derive_needed(raw, rule)

    def test_multiple_byte_same_length_replacement_is_rejected(self):
        raw = fixture()
        rule = recipe(raw)
        rule["new"] = NEW.replace("audio", "radio")
        with self.assertRaisesRegex(DerivationError, "exactly one byte"):
            derive_needed(raw, rule)

    def test_different_length_replacement_is_rejected(self):
        raw = fixture()
        rule = recipe(raw)
        rule["new"] = NEW.replace("V4", "V40")
        with self.assertRaisesRegex(DerivationError, "equal length"):
            derive_needed(raw, rule)

    def test_noop_is_rejected(self):
        raw = fixture()
        rule = recipe(raw)
        rule["new"] = OLD
        with self.assertRaisesRegex(DerivationError, "exactly one byte"):
            derive_needed(raw, rule)

    def test_names_must_be_ascii_sonames_without_paths_or_nulls(self):
        raw = fixture()
        for name in ("../libaudio-types-V4.so", "libaudio-types-V4.so\0", "libáudio-types-V4.so"):
            rule = recipe(raw)
            rule["new"] = name
            with self.subTest(name=name), self.assertRaisesRegex(DerivationError, "ASCII"):
                derive_needed(raw, rule)

    def test_both_pinned_hex_bytes_must_match_names(self):
        raw = fixture()
        for key in ("original_byte_hex", "derived_byte_hex"):
            for value in ("33", "0x32", 50, "0A"):
                rule = recipe(raw)
                rule[key] = value
                with self.subTest(key=key, value=value), self.assertRaisesRegex(DerivationError, "pinned byte"):
                    derive_needed(raw, rule)

    def test_exact_rule_schema_and_fixed_kind(self):
        raw = fixture()
        rules = []
        for change in ({"kind": "generic-replace"}, {"unchecked_flag": True},
                       {"changed_byte_file_offset": True}, {"old": 1}):
            rule = recipe(raw)
            rule.update(change)
            rules.append(rule)
        rule = recipe(raw)
        del rule["derived"]
        rules.append(rule)
        for rule in rules:
            with self.subTest(rule=rule), self.assertRaises(DerivationError):
                derive_needed(raw, rule)

    def test_identity_schema_and_integer_types_are_strict(self):
        raw = fixture()
        for change in ({"sha256": "F" * 64}, {"sha256": 1}, {"size_bytes": True},
                       {"size_bytes": 2 ** 64}, {"unexpected": 1}):
            rule = recipe(raw)
            rule["original"].update(change)
            with self.subTest(change=change), self.assertRaises(DerivationError):
                derive_needed(raw, rule)

    def test_duplicate_dt_needed_entry_is_rejected(self):
        raw = fixture(duplicate_needed=True)
        with self.assertRaisesRegex(DerivationError, "exactly once"):
            derive_needed(raw, recipe(raw))

    def test_duplicate_string_table_name_is_rejected(self):
        raw = fixture(duplicate_string=True)
        with self.assertRaisesRegex(DerivationError, "ambiguous"):
            derive_needed(raw, recipe(raw))

    def test_result_cannot_duplicate_existing_dependency(self):
        raw = fixture(existing_new=True)
        with self.assertRaisesRegex(DerivationError, "duplicate an existing dependency"):
            derive_needed(raw, recipe(raw))

    def test_string_occurrence_without_dt_needed_selection_is_rejected(self):
        raw = fixture(target_is_needed=False)
        with self.assertRaisesRegex(DerivationError, "exactly once"):
            derive_needed(raw, recipe(raw))

    def test_soname_or_search_path_alias_cannot_change(self):
        for tag in (14, 29):
            raw = fixture(alias_tag=tag)
            with self.subTest(tag=tag), self.assertRaisesRegex(DerivationError, "unreviewed ELF metadata"):
                derive_needed(raw, recipe(raw))

    def test_other_needed_suffix_alias_cannot_change(self):
        raw = fixture(alias_tag=1)
        with self.assertRaisesRegex(DerivationError, "unreviewed ELF metadata"):
            derive_needed(raw, recipe(raw))

    def test_interpreter_alias_cannot_change(self):
        raw = fixture(interpreter_alias=True)
        with self.assertRaisesRegex(DerivationError, "aliases"):
            derive_needed(raw, recipe(raw))

    def test_executable_bytes_cannot_change(self):
        raw = fixture(executable=True)
        with self.assertRaisesRegex(DerivationError, "aliases"):
            derive_needed(raw, recipe(raw))

    def test_less_common_dynamic_string_aliases_cannot_change(self):
        for tag in (0x6ffffefa, 0x6ffffefb, 0x6ffffefc, 0x7ffffffd, 0x7fffffff):
            raw = fixture(alias_tag=tag)
            with self.subTest(tag=tag), self.assertRaisesRegex(DerivationError, "aliases"):
                derive_needed(raw, recipe(raw))

    def test_section_header_alias_cannot_change(self):
        raw = bytearray(fixture())
        struct.pack_into("<Q", raw, 40, STROFF)
        struct.pack_into("<HH", raw, 58, 64, 1)
        raw = bytes(raw)
        with self.assertRaisesRegex(DerivationError, "aliases"):
            derive_needed(raw, recipe(raw))

    def test_ambiguous_dynamic_or_load_segments_are_rejected(self):
        for kind, offset, address, size in ((2, DYNOFF, 0x1000 + DYNOFF, 112),
                                           (1, 0, 0x1000, FILESIZE)):
            raw = bytearray(fixture())
            struct.pack_into("<IIQQQQQQ", raw, PHOFF + 2 * PHSIZE, kind, 4,
                             offset, address, 0, size, size, 8)
            raw = bytes(raw)
            with self.subTest(kind=kind), self.assertRaises(DerivationError):
                derive_needed(raw, recipe(raw))

    def test_duplicate_string_table_tags_are_rejected(self):
        raw = bytearray(fixture())
        struct.pack_into("<qQ", raw, DYNOFF + 3 * 16, 5, 0x1000 + STROFF)
        raw = bytes(raw)
        with self.assertRaisesRegex(DerivationError, "duplicate ELF string table"):
            derive_needed(raw, recipe(raw))

    def test_misaligned_dynamic_segment_is_rejected(self):
        raw = bytearray(fixture())
        struct.pack_into("<Q", raw, PHOFF + PHSIZE + 32, 111)
        raw = bytes(raw)
        with self.assertRaisesRegex(DerivationError, "misaligned"):
            derive_needed(raw, recipe(raw))

    def test_malformed_elf_is_rejected_even_when_raw_hash_is_reviewed(self):
        mutations = [(0, b"BAD!"), (4, b"\x01"), (5, b"\x02"), (16, b"\x02\0"),
                     (18, b"\x28\0"), (52, b"\x01\0"), (54, b"\x01\0"),
                     (32, struct.pack("<Q", len(fixture()) + 1)),
                     (DYNOFF + 8, struct.pack("<Q", 0xffffffffffffffff)),
                     (DYNOFF + 24, struct.pack("<Q", 0xffffffffffffffff)),
                     (DYNOFF + 40, struct.pack("<Q", 0xffffffffffffffff)),
                     (DYNOFF + 96, struct.pack("<qQ", 1, 1))]
        for offset, data in mutations:
            raw = bytearray(fixture())
            raw[offset:offset + len(data)] = data
            raw = bytes(raw)
            with self.subTest(offset=offset, data=data), self.assertRaises(DerivationError):
                derive_needed(raw, recipe(raw))

    def test_truncated_elf_is_rejected_even_when_raw_hash_is_reviewed(self):
        for length in (64, 120, 300, 700):
            raw = fixture()[:length]
            rule = recipe(raw)
            if length <= BYTE_OFFSET:
                # Keep the rule syntactically in range; structural parsing must
                # still reject this truncated file before a derivation is made.
                rule["dt_needed_string_file_offset"] = 0
                rule["changed_byte_file_offset"] = OLD.index("2")
                rule["derived"] = identity(raw[:OLD.index("2")] + b"4" + raw[OLD.index("2") + 1:])
            with self.subTest(length=length), self.assertRaises(DerivationError):
                derive_needed(raw, rule)


if __name__ == "__main__":
    unittest.main()
