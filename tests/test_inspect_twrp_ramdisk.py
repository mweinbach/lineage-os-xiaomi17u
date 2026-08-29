"""Offline synthetic CPIO/ELF tests; no stock bytes, extraction, or device tools."""

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import inspect_twrp_ramdisk as inspector


SECURE = b"ro.secure=1\nro.adb.secure=1\nro.debuggable=0\n"
PROPERTIES = SECURE + b"vendor.synthetic.private=do-not-publish-this-value\n"
POLICY = b"synthetic-policy-not-a-real-compiled-policy\0"
REGULAR = stat.S_IFREG | 0o644
EXECUTABLE = stat.S_IFREG | 0o755
DIRECTORY = stat.S_IFDIR | 0o755
SYMLINK = stat.S_IFLNK | 0o777


def _entry(name, data=b"", *, mode=REGULAR, nlink=1, inode=1, uid=0,
           gid=0, check=0, raw_name=None, namesize=None, size=None):
    """Produce a newc entry with explicit, independently mutable fields."""
    raw_name = name.encode("utf-8") + b"\0" if raw_name is None else raw_name
    fields = (inode, mode, uid, gid, nlink, 0, len(data) if size is None else size,
              0, 0, 0, 0, len(raw_name) if namesize is None else namesize, check)
    header = b"070701" + b"".join(f"{value:08x}".encode("ascii") for value in fields)
    assert len(header) == 110
    prefix = header + raw_name
    return prefix + bytes((-len(prefix)) % 4) + data + bytes((-len(data)) % 4)


def _elf64(*, needed=False):
    """An inert ELF64 AArch64 image with real, bounded program headers."""
    count = 2 if needed else 1
    prefix_size = 64 + 56 * count
    strings = b"\0libsynthetic.so\0"
    if needed:
        dynamic_size = 64
        string_offset = prefix_size + dynamic_size
        tail = (struct.pack("<qQ", 1, 1)
                + struct.pack("<qQ", 5, 0x400000 + string_offset)
                + struct.pack("<qQ", 10, len(strings))
                + bytes(16) + strings)
    else:
        tail = b"inert!!!"
    size = prefix_size + len(tail)
    ident = b"\x7fELF\x02\x01\x01" + bytes(9)
    header = struct.pack("<16sHHIQQQIHHHHHH", ident, 3, 183, 1,
                         0x400000 + prefix_size, 64, 0, 0, 64, 56, count, 0, 0, 0)
    programs = struct.pack("<IIQQQQQQ", 1, 5, 0, 0x400000, 0, size, size, 4096)
    if needed:
        programs += struct.pack("<IIQQQQQQ", 2, 4, prefix_size,
                                0x400000 + prefix_size, 0, 64, 64, 8)
    return header + programs + tail


def _required_entries():
    return {
        ".": _entry(".", mode=DIRECTORY, nlink=2),
        "prop.default": _entry("prop.default", PROPERTIES),
        "sepolicy": _entry("sepolicy", POLICY),
        "system": _entry("system", mode=DIRECTORY, nlink=2),
        "system/bin": _entry("system/bin", mode=DIRECTORY, nlink=2),
        "system/bin/init": _entry("system/bin/init", _elf64(), mode=EXECUTABLE),
        "system/bin/adbd": _entry("system/bin/adbd", _elf64(), mode=EXECUTABLE),
    }


def _cpio(*, overrides=None, omit=(), extra=(), trailer=None, padding=0):
    entries = _required_entries()
    entries.update(overrides or {})
    for name in omit:
        entries.pop(name)
    trailer = _entry("TRAILER!!!", mode=0) if trailer is None else trailer
    return b"".join(entries.values()) + b"".join(extra) + trailer + bytes(padding)


def _field(data, index, value):
    result = bytearray(data)
    start = 6 + index * 8
    result[start:start + 8] = f"{value:08x}".encode("ascii")
    return bytes(result)


def _binary_field(data, offset, fmt, value):
    result = bytearray(data)
    struct.pack_into("<" + fmt, result, offset, value)
    return bytes(result)


class CpioStructureTests(unittest.TestCase):
    def reject(self, data, message="."):
        with self.assertRaisesRegex(inspector.RamdiskInspectionError, message):
            inspector.inspect_cpio(data)

    def test_valid_archive_reports_hashes_offsets_and_limited_claims(self):
        data = _cpio()
        report = inspector.inspect_cpio(data)
        self.assertEqual(report["schema_version"], 1)
        self.assertEqual(report["operation"], "inspect-twrp-ramdisk")
        archive = report["archive"]
        self.assertEqual(archive["format"], "newc")
        self.assertEqual(archive["archive_count"], 1)
        self.assertEqual(archive["entry_count"], 7)
        self.assertEqual(archive["size_bytes"], len(data))
        self.assertEqual(archive["sha256"], hashlib.sha256(data).hexdigest())
        self.assertEqual(archive["file_type_counts"], {"directory": 3, "regular": 4})
        self.assertEqual(data[archive["trailer_offset_bytes"]:][:6], b"070701")
        self.assertEqual(archive["trailing_zero_padding_bytes"], 0)
        self.assertEqual(set(report["key_members"]),
                         {"prop.default", "sepolicy", "system/bin/init", "system/bin/adbd"})
        for name, content in (("prop.default", PROPERTIES), ("sepolicy", POLICY),
                              ("system/bin/init", _elf64()), ("system/bin/adbd", _elf64())):
            row = report["key_members"][name]
            with self.subTest(name=name):
                self.assertEqual(row["kind"], "regular")
                self.assertEqual(row["nlink"], 1)
                self.assertEqual(row["sha256"], hashlib.sha256(content).hexdigest())
                self.assertEqual(row["size_bytes"], len(content))
                self.assertEqual(data[row["offset_bytes"]:][:len(content)], content)
        self.assertEqual(report["properties"]["required_values"], inspector.SECURE_PROPERTIES)
        self.assertEqual(report["properties"]["property_count"], 4)
        self.assertEqual(report["properties"]["default_prop_relation"], "absent")
        rendered = json.dumps(report)
        self.assertNotIn("do-not-publish-this-value", rendered)
        self.assertNotIn("vendor.synthetic.private", rendered)
        self.assertNotIn(POLICY[:-1].decode(), rendered)
        for key in ("structurally_valid", "secure_property_literals_verified",
                    "key_elf_headers_verified", "member_paths_unique"):
            self.assertIs(report["validation"][key], True, key)
        for key in ("ramdisk_extracted", "firmware_executed", "phone_accessed", "archive_mutated",
                    "twrp_build_provenance_verified", "compressed_ramdisk_binding_verified",
                    "effective_runtime_properties_verified", "adb_authentication_verified",
                    "sepolicy_contents_parsed", "compiled_selinux_policy_verified",
                    "selinux_enforcement_verified", "boot_tested", "avb_trusted", "flash_admitted"):
            self.assertIs(report["validation"][key], False, key)

    def test_accepts_memoryview_and_does_not_mutate_bytearray_input(self):
        data = bytearray(_cpio())
        before = bytes(data)
        self.assertEqual(inspector.inspect_cpio(memoryview(data))["archive"]["size_bytes"], len(data))
        self.assertEqual(bytes(data), before)

    def test_inspection_does_not_open_extract_or_execute_members(self):
        with mock.patch("builtins.open", side_effect=AssertionError("unexpected file open")), \
                mock.patch.object(os, "open", side_effect=AssertionError("unexpected os.open")), \
                mock.patch.object(os, "mkdir", side_effect=AssertionError("unexpected extraction")), \
                mock.patch("subprocess.run", side_effect=AssertionError("unexpected process")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("unexpected process")):
            report = inspector.inspect_cpio(_cpio())
        self.assertFalse(report["validation"]["ramdisk_extracted"])

    def test_accepts_bounded_final_zero_padding_but_not_another_archive(self):
        report = inspector.inspect_cpio(_cpio(padding=508))
        self.assertEqual(report["archive"]["trailing_zero_padding_bytes"], 508)
        for data in (_cpio(padding=512), _cpio() + _cpio(), _cpio() + b"junk"):
            self.reject(data, "after newc trailer")

    def test_rejects_empty_truncated_or_unaligned_archive(self):
        data = _cpio()
        for value in (b"", bytes(108), data[:-1], data[:-2], data[:-3], data[:-4],
                      _entry("filename")[:112], _entry("payload", b"1234567")[:-4],
                      b"".join(_required_entries().values())):
            with self.subTest(size=len(value)):
                self.reject(value, "bounds|aligned|truncated")

    def test_archive_and_member_count_limits_are_enforced(self):
        self.assertEqual(inspector.MAX_ARCHIVE_BYTES, 512 * 1024**2)
        data = _cpio()
        with mock.patch.object(inspector, "MAX_ARCHIVE_BYTES", len(data) - 4):
            self.reject(data, "bounds")
        with mock.patch.object(inspector, "MAX_ENTRIES", 6):
            self.reject(data, "too many newc members")

    def test_rejects_wrong_magic_crc_format_and_nonhex_headers(self):
        data = _cpio()
        for prefix in (b"070702", b"070707", b"\x1f\x8bGZIP", b"\x02\x21\x4c\x18XX"):
            with self.subTest(prefix=prefix):
                self.reject(prefix + data[6:], "070701")
        self.reject(data[:6] + b"G" + data[7:], "070701")

    def test_rejects_invalid_name_size_checksum_and_payload_size(self):
        for index, value in ((11, 0), (11, 1), (11, inspector.MAX_NAME_BYTES + 1),
                             (11, 0xFFFFFFFF), (12, 1), (6, 0xFFFFFFFF)):
            with self.subTest(field=index, value=value):
                self.reject(_field(_cpio(), index, value), "name size|check field|payload")

    def test_rejects_nonzero_name_and_payload_padding(self):
        for name, content, offset in (("pad", b"x", 114), ("pad", b"x", 117)):
            entry = bytearray(_entry(name, content))
            entry[offset] = 1
            self.reject(_cpio(extra=(bytes(entry),)), "alignment padding")

    def test_rejects_invalid_trailer_fields_and_noncanonical_trailer(self):
        valid = _entry("TRAILER!!!", mode=0)
        for index, value in ((1, REGULAR), (2, 1), (3, 1), (4, 2), (9, 1), (10, 1)):
            with self.subTest(field=index):
                self.reject(_cpio(trailer=_field(valid, index, value)), "trailer fields")
        self.reject(_cpio(trailer=_entry("TRAILER!!!", b"x", mode=0)), "trailer fields")
        self.reject(_cpio(trailer=_entry("./TRAILER!!!", mode=0)), "noncanonical newc trailer")
        self.assertEqual(inspector.inspect_cpio(_cpio(trailer=_field(valid, 4, 0)))["archive"]["archive_count"], 1)

    def test_accepts_android_mkbootfs_trailer_permissions(self):
        # Pinned mkbootfs zeroes the trailer stat, then applies directory
        # fs_config: permission bits 0755, with no file-type bits or payload.
        for mode in (0, 0o755):
            for links in (0, 1):
                with self.subTest(mode=oct(mode), links=links):
                    trailer = _entry("TRAILER!!!", mode=mode, nlink=links, inode=300770)
                    data = _cpio(trailer=trailer, padding=248)
                    report = inspector.inspect_cpio(data)
                    self.assertEqual(report["archive"]["entry_count"], 7)
                    self.assertEqual(report["archive"]["archive_count"], 1)
                    self.assertEqual(report["archive"]["trailing_zero_padding_bytes"], 248)
                    self.assertEqual(report["archive"]["sha256"], hashlib.sha256(data).hexdigest())

    def test_android_trailer_does_not_admit_other_modes_or_regular_members(self):
        for mode in (1, 0o644, 0o700, 0o777, 0o1755, 0o2755, 0o4755,
                     EXECUTABLE, DIRECTORY, SYMLINK, stat.S_IFCHR, 0xFFFFFFFF):
            with self.subTest(mode=oct(mode)):
                self.reject(_cpio(trailer=_entry("TRAILER!!!", mode=mode)), "trailer fields")
        self.reject(_cpio(extra=(_entry("not-a-trailer", mode=0o755),)), "file type")

    def test_android_trailer_still_checks_ownership_links_devices_and_payload(self):
        trailer = _entry("TRAILER!!!", mode=0o755)
        for index, value in ((2, 1), (3, 1), (4, 2), (4, 0xFFFFFFFF), (9, 1), (10, 1)):
            with self.subTest(field=index, value=value):
                self.reject(_cpio(trailer=_field(trailer, index, value)), "trailer fields")
        self.reject(_cpio(trailer=_entry("TRAILER!!!", b"x", mode=0o755)), "trailer fields")
        self.reject(_cpio(trailer=_field(trailer, 12, 1)), "check field")

    def test_android_trailer_still_checks_name_alignment_and_bounds(self):
        for name, pattern in (("./TRAILER!!!", "noncanonical newc trailer"),
                              ("/TRAILER!!!", "unsafe")):
            self.reject(_cpio(trailer=_entry(name, mode=0o755)), pattern)
        self.reject(_cpio(trailer=_entry("TRAILER!!!", mode=0o755,
                                        raw_name=b"TRAILER!!!\0\0")), "termination")
        trailer = bytearray(_entry("TRAILER!!!", mode=0o755))
        trailer[-1] = 1
        self.reject(_cpio(trailer=bytes(trailer)), "alignment padding")
        self.reject(_cpio(trailer=_field(_entry("TRAILER!!!", mode=0o755), 6, 0xFFFFFFFF)),
                    "payload")

    def test_android_trailer_does_not_allow_another_archive_or_trailing_garbage(self):
        data = _cpio(trailer=_entry("TRAILER!!!", mode=0o755))
        self.assertEqual(inspector.inspect_cpio(data + bytes(508))["archive"]
                         ["trailing_zero_padding_bytes"], 508)
        for after in (bytes(512), b"junk", data):
            with self.subTest(size=len(after)):
                self.reject(data + after, "after newc trailer")
        self.reject(data[:-4], "truncated|bounds")

    def test_android_trailer_does_not_bypass_member_path_or_count_checks(self):
        trailer = _entry("TRAILER!!!", mode=0o755)
        self.reject(_cpio(extra=(_entry("./prop.default", b"x"),), trailer=trailer), "duplicate")
        self.reject(_cpio(extra=(_entry("../escape", b"x"),), trailer=trailer), "traversing")
        extra = (_entry("link", b"system", mode=SYMLINK), _entry("link/child", b"x"))
        self.reject(_cpio(extra=extra, trailer=trailer), "descends through")
        data = _cpio(trailer=trailer)
        with mock.patch.object(inspector, "MAX_ENTRIES", 6):
            self.reject(data, "too many")
        with mock.patch.object(inspector, "MAX_ARCHIVE_BYTES", len(data) - 4):
            self.reject(data, "bounds")

    def test_android_trailer_does_not_cause_extraction_execution_or_mutation(self):
        data = bytearray(_cpio(trailer=_entry("TRAILER!!!", mode=0o755)))
        before = bytes(data)
        with mock.patch("builtins.open", side_effect=AssertionError("unexpected file open")), \
                mock.patch.object(os, "open", side_effect=AssertionError("unexpected os.open")), \
                mock.patch.object(os, "mkdir", side_effect=AssertionError("unexpected extraction")), \
                mock.patch("subprocess.run", side_effect=AssertionError("unexpected process")), \
                mock.patch("subprocess.Popen", side_effect=AssertionError("unexpected process")):
            report = inspector.inspect_cpio(data)
        self.assertEqual(bytes(data), before)
        for flag in ("ramdisk_extracted", "firmware_executed", "phone_accessed", "archive_mutated",
                     "boot_tested", "flash_admitted"):
            self.assertIs(report["validation"][flag], False)

    def test_normalizes_single_dot_prefix_and_rejects_duplicate_paths(self):
        overrides = {
            "prop.default": _entry("./prop.default", PROPERTIES),
            "system": _entry("./system", mode=DIRECTORY),
            "system/bin": _entry("./system/bin", mode=DIRECTORY),
            "system/bin/init": _entry("./system/bin/init", _elf64(), mode=EXECUTABLE),
        }
        self.assertIn("system/bin/init", inspector.inspect_cpio(_cpio(overrides=overrides))["key_members"])
        for alias in ("prop.default", "./prop.default"):
            self.reject(_cpio(extra=(_entry(alias, PROPERTIES),)), "duplicate normalized")

    def test_rejects_unsafe_noncanonical_and_overdeep_paths(self):
        for name in ("/absolute", "../escape", "x/../escape", "x/./file", "x//file", "x/",
                     "./", "././file", "C:file", "C:/file", "./C:file", "./C:/file",
                     "back\\slash", "new\nline",
                     "a" * inspector.MAX_NAME_BYTES, "/".join(["part"] * 65)):
            with self.subTest(name=name[:80]):
                self.reject(_cpio(extra=(_entry(name, b"data"),)), "path|name size")

    def test_rejects_missing_embedded_nul_and_invalid_utf8_names(self):
        for raw in (b"missing-nul", b"embedded\0name\0", b"\xff\0"):
            with self.subTest(raw=raw):
                self.reject(_cpio(extra=(_entry("ignored", raw_name=raw),)), "filename")

    def test_rejects_invalid_member_modes_links_and_nonfile_payloads(self):
        for entry in (_entry("extra", mode=0), _entry("extra", mode=0x10000 | REGULAR),
                      _entry("extra", mode=0xFFFFFFFF),
                      _entry("extra", nlink=0), _entry("extra", b"x", mode=DIRECTORY),
                      _entry("extra", b"x", mode=stat.S_IFIFO | 0o600)):
            self.reject(_cpio(extra=(entry,)), "mode|file type|link count|payload")
        self.reject(_cpio(overrides={".": _entry(".")}), "root entry")

    def test_nonkey_special_files_are_only_counted_not_created(self):
        extras = tuple(_entry(name, mode=kind | 0o600) for name, kind in (
            ("fake-character", stat.S_IFCHR), ("fake-block", stat.S_IFBLK),
            ("fake-fifo", stat.S_IFIFO), ("fake-socket", stat.S_IFSOCK)))
        report = inspector.inspect_cpio(_cpio(extra=extras))
        for kind in ("character", "block", "fifo", "socket"):
            self.assertEqual(report["archive"]["file_type_counts"][kind], 1)
        self.assertFalse(report["validation"]["ramdisk_extracted"])

    def test_rejects_invalid_symlink_payloads(self):
        for content in (b"", b"a\0b", b"\xff", b"line\nfeed", b"a" * (inspector.MAX_NAME_BYTES + 1)):
            with self.subTest(length=len(content)):
                self.reject(_cpio(extra=(_entry("link", content, mode=SYMLINK),)), "symlink")

    def test_rejects_non_directory_ancestors_in_either_entry_order(self):
        child = _entry("logs/entry", b"not extracted")
        for ancestor in (_entry("logs", b"/outside", mode=SYMLINK), _entry("logs", b"file")):
            for entries in ((ancestor, child), (child, ancestor)):
                self.reject(_cpio(extra=entries), "non-directory or symlink")


class KeyMemberAndPropertyTests(unittest.TestCase):
    def reject(self, data, message="."):
        with self.assertRaisesRegex(inspector.RamdiskInspectionError, message):
            inspector.inspect_cpio(data)

    def properties(self, content, *, alias=None):
        overrides = {"prop.default": _entry("prop.default", content)}
        extra = () if alias is None else (_entry("default.prop", alias),)
        return _cpio(overrides=overrides, extra=extra)

    def test_rejects_missing_required_members(self):
        for name in ("prop.default", "sepolicy", "system/bin/init", "system/bin/adbd"):
            with self.subTest(name=name):
                self.reject(_cpio(omit=(name,)), "required ramdisk member is absent")

    def test_key_member_parents_must_be_explicit_directories(self):
        for name in ("system", "system/bin"):
            with self.subTest(name=name):
                self.reject(_cpio(omit=(name,)), "absent or non-directory ancestor")
                self.reject(_cpio(overrides={name: _entry(name, b"elsewhere", mode=SYMLINK)}),
                            "non-directory or symlink")
        self.assertEqual(inspector.inspect_cpio(_cpio(omit=(".",)))["archive"]["entry_count"], 6)

    def test_rejects_group_or_world_writable_critical_directory_parents(self):
        for name in (".", "system", "system/bin"):
            for permissions in (0o775, 0o757, 0o777):
                entry = _entry(name, mode=stat.S_IFDIR | permissions, nlink=2)
                with self.subTest(name=name, permissions=oct(permissions)):
                    self.reject(_cpio(overrides={name: entry}), "writable directory ancestor")
        # A separate writable scratch directory does not hold a key member.
        report = inspector.inspect_cpio(_cpio(extra=(
            _entry("tmp", mode=stat.S_IFDIR | 0o1777, nlink=2),)))
        self.assertTrue(report["validation"]["structurally_valid"])

    def test_rejects_symlink_and_empty_required_files(self):
        for name in ("prop.default", "sepolicy", "system/bin/init", "system/bin/adbd"):
            with self.subTest(name=name):
                self.reject(_cpio(overrides={name: _entry(name, b"elsewhere", mode=SYMLINK)}),
                            "regular file")
                self.reject(_cpio(overrides={name: _entry(name, mode=EXECUTABLE)}), "size is invalid")

    def test_rejects_hard_linked_required_and_optional_key_members(self):
        for name, content, mode in (("prop.default", PROPERTIES, REGULAR),
                                    ("sepolicy", POLICY, REGULAR),
                                    ("system/bin/init", _elf64(), EXECUTABLE),
                                    ("system/bin/adbd", _elf64(), EXECUTABLE),
                                    ("default.prop", b"prop.default", SYMLINK),
                                    ("init", b"system/bin/init", SYMLINK)):
            entry = _entry(name, content, mode=mode, nlink=2)
            with self.subTest(name=name):
                self.reject(_cpio(overrides={name: entry}), "hard-linked key member")

    def test_key_and_property_byte_limits_are_enforced(self):
        with mock.patch.object(inspector, "MAX_KEY_BYTES", len(_elf64()) - 1):
            self.reject(_cpio(), "key member size")
        with mock.patch.object(inspector, "MAX_PROPERTY_BYTES", len(PROPERTIES) - 1):
            self.reject(_cpio(), "property file size")

    def test_records_key_ownership_and_modes_without_claiming_runtime_permissions(self):
        entry = _entry("system/bin/adbd", _elf64(), mode=EXECUTABLE, uid=0, gid=2000)
        report = inspector.inspect_cpio(_cpio(overrides={"system/bin/adbd": entry}))
        member = report["key_members"]["system/bin/adbd"]
        self.assertEqual((member["uid"], member["gid"]), (0, 2000))
        self.assertEqual(int(member["mode"], 8), EXECUTABLE)
        self.assertFalse(report["validation"]["adb_authentication_verified"])

    def test_rejects_group_or_world_writable_critical_regular_files(self):
        for name, content in (("prop.default", PROPERTIES), ("default.prop", PROPERTIES),
                              ("sepolicy", POLICY), ("system/bin/init", _elf64()),
                              ("system/bin/adbd", _elf64()), ("init", _elf64())):
            for permissions in (0o664, 0o666, 0o777):
                entry = _entry(name, content, mode=stat.S_IFREG | permissions)
                with self.subTest(name=name, permissions=oct(permissions)):
                    self.reject(_cpio(overrides={name: entry}), "writable")

    def test_ascii_whitespace_comments_crlf_and_equals_in_values_are_allowed(self):
        content = (b"  # synthetic comment\r\n ro.adb.secure = 1 \r\nro.secure=1\r\n"
                   b"\tro.debuggable=0\t\r\nextra=value=with=equals\nempty=\n")
        report = inspector.inspect_cpio(self.properties(content))
        self.assertEqual(report["properties"]["property_count"], 5)

    def test_rejects_missing_or_insecure_security_properties(self):
        for key, good, bad in ((b"ro.secure", b"1", b"0"), (b"ro.adb.secure", b"1", b"0"),
                               (b"ro.debuggable", b"0", b"1")):
            assignment = key + b"=" + good + b"\n"
            for content in (SECURE.replace(assignment, b""),
                            SECURE.replace(assignment, key + b"=" + bad + b"\n")):
                with self.subTest(key=key, content=content):
                    self.reject(self.properties(content), "required secure properties")

    def test_rejects_duplicate_equal_or_conflicting_assignments(self):
        for suffix in (b"ro.secure=1\n", b"ro.secure=0\n", b"other=one\nother=one\n"):
            self.reject(self.properties(SECURE + suffix), "duplicate property assignment")

    def test_rejects_property_imports_invalid_names_and_nonprintable_values(self):
        for suffix in (b"import /other.prop\n", b"no-assignment\n", b"=empty-key\n",
                       b"bad key=value\n", b"nonascii-\xc3\xa9=value\n", b"other=a\x01b\n"):
            with self.subTest(suffix=suffix):
                self.reject(self.properties(SECURE + suffix), "property|nonprintable")

    def test_rejects_nul_even_in_comments_and_invalid_utf8(self):
        for content in (b"# hidden\0NUL\n" + SECURE, SECURE + b"other=a\0b\n",
                        b"# invalid \xff\n" + SECURE):
            self.reject(self.properties(content), "NUL|UTF-8")

    def test_unicode_or_control_separators_cannot_create_hidden_assignments(self):
        for separator in ("\u2028", "\u2029", "\x85", "\v", "\f"):
            content = separator.join(("ro.secure=1", "ro.adb.secure=1", "ro.debuggable=0")).encode()
            with self.subTest(separator=repr(separator)):
                self.reject(self.properties(content), "nonprintable|secure properties")
        self.reject(self.properties(b"\xc2\xa0ro.secure=1\nro.adb.secure=1\nro.debuggable=0\n"),
                    "invalid or duplicate property")

    def test_default_prop_regular_alias_requires_the_entire_property_map(self):
        alias = (b"# order and whitespace do not change the map\n"
                 b"vendor.synthetic.private=do-not-publish-this-value\n"
                 b"ro.debuggable = 0\nro.adb.secure=1\nro.secure=1\n")
        report = inspector.inspect_cpio(self.properties(PROPERTIES, alias=alias))
        self.assertEqual(report["properties"]["default_prop_relation"], "identical-property-map")
        self.assertIn("default.prop", report["key_members"])
        for alias in (SECURE, PROPERTIES + b"extra=override\n",
                      PROPERTIES.replace(b"do-not-publish-this-value", b"other-value")):
            self.reject(self.properties(PROPERTIES, alias=alias), "property override")

    def test_default_prop_symlink_must_be_a_direct_known_alias(self):
        for target in (b"prop.default", b"./prop.default", b"/prop.default"):
            report = inspector.inspect_cpio(_cpio(extra=(_entry("default.prop", target, mode=SYMLINK),)))
            self.assertEqual(report["properties"]["default_prop_relation"], "symlink-to-prop.default")
        for target in (b"../prop.default", b"etc/prop.default", b"default.prop", b"/elsewhere"):
            self.reject(_cpio(extra=(_entry("default.prop", target, mode=SYMLINK),)), "point directly")

    def test_optional_root_init_accepts_valid_regular_file_or_direct_symlink(self):
        report = inspector.inspect_cpio(_cpio(extra=(_entry("init", _elf64(), mode=EXECUTABLE),)))
        self.assertEqual(report["key_members"]["init"]["elf"]["machine"], 183)
        for target in (b"system/bin/init", b"./system/bin/init", b"/system/bin/init"):
            report = inspector.inspect_cpio(_cpio(extra=(_entry("init", target, mode=SYMLINK),)))
            self.assertEqual(report["key_members"]["init"]["symlink_target"], target.decode())
        for target in (b"../system/bin/init", b"bin/init", b"init", b"/other/init"):
            self.reject(_cpio(extra=(_entry("init", target, mode=SYMLINK),)), "point directly")


class ElfStructureTests(unittest.TestCase):
    def reject_elf(self, data, message="ELF|AArch64|execute mode", *, mode=EXECUTABLE):
        for name in ("system/bin/init", "system/bin/adbd", "init"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(inspector.RamdiskInspectionError, message):
                    inspector.inspect_cpio(_cpio(overrides={name: _entry(name, data, mode=mode)}))

    def test_valid_arm64_headers_and_dynamic_dependencies_remain_unverified(self):
        elf = _elf64(needed=True)
        report = inspector.inspect_cpio(_cpio(overrides={
            "system/bin/adbd": _entry("system/bin/adbd", elf, mode=EXECUTABLE)}))
        metadata = report["key_members"]["system/bin/adbd"]["elf"]
        self.assertEqual(metadata["class_bits"], 64)
        self.assertEqual(metadata["endianness"], "little")
        self.assertEqual(metadata["machine"], 183)
        self.assertEqual(metadata["type"], 3)
        self.assertEqual(metadata["declared_needed_library_count"], 1)
        self.assertFalse(metadata["dependencies_resolved"])
        self.assertFalse(metadata["executed"])
        self.assertNotIn("libsynthetic.so", json.dumps(report))
        executable = _binary_field(_elf64(), 16, "H", 2)
        inspector.inspect_cpio(_cpio(overrides={
            "system/bin/init": _entry("system/bin/init", executable, mode=EXECUTABLE)}))

    def test_rejects_missing_execute_mode_and_nonelf_or_truncated_headers(self):
        self.reject_elf(_elf64(), mode=REGULAR)
        for data in (b"#!/system/bin/sh\n", _elf64()[:63], b"NOPE" + _elf64()[4:]):
            self.reject_elf(data)

    def test_rejects_wrong_class_endianness_architecture_or_header_version(self):
        for offset, fmt, value in ((4, "B", 1), (5, "B", 2), (6, "B", 0),
                                   (16, "H", 1), (18, "H", 62), (20, "I", 2),
                                   (52, "H", 63), (32, "Q", 0), (32, "Q", 63)):
            with self.subTest(offset=offset, value=value):
                self.reject_elf(_binary_field(_elf64(), offset, fmt, value))

    def test_rejects_invalid_or_out_of_bounds_program_header_tables(self):
        for offset, fmt, value in ((32, "Q", 0xFFFFFFFFFFFFFFFF), (54, "H", 55),
                                   (56, "H", 0), (56, "H", 0xFFFF)):
            with self.subTest(offset=offset):
                self.reject_elf(_binary_field(_elf64(), offset, fmt, value))

    def test_rejects_out_of_bounds_segments_and_invalid_executable_loads(self):
        for offset, fmt, value in ((72, "Q", 0xFFFFFFFFFFFFFFFF),
                                   (96, "Q", len(_elf64()) + 1),
                                   (104, "Q", len(_elf64()) - 1),
                                   (64, "I", 0), (68, "I", 4), (96, "Q", 0)):
            with self.subTest(offset=offset, value=value):
                self.reject_elf(_binary_field(_elf64(), offset, fmt, value))

    def test_rejects_unterminated_dynamic_segment_and_invalid_string_table(self):
        elf = _elf64(needed=True)
        # Second program header is PT_DYNAMIC, beginning at file offset 176.
        for data in (_binary_field(elf, 176 + 48, "q", 1),
                     _binary_field(elf, 176 + 24, "Q", 0xFFFFFFFFFFFFFFFF),
                     _binary_field(elf, 176 + 8, "Q", 0xFFFFFFFFFFFFFFFF),
                     elf[:-1] + b"X"):
            self.reject_elf(data, "malformed ELF segments")

    def test_dynamic_segment_limit_is_enforced_before_parsing_tags(self):
        archive = _cpio(overrides={
            "system/bin/init": _entry("system/bin/init", _elf64(needed=True), mode=EXECUTABLE)})
        with mock.patch.object(inspector, "MAX_ELF_DYNAMIC_BYTES", 48):
            with mock.patch.object(inspector, "elf_dynamic", side_effect=AssertionError(
                    "oversized dynamic segment was passed to the tag parser")):
                with self.assertRaisesRegex(inspector.RamdiskInspectionError, "dynamic"):
                    inspector.inspect_cpio(archive)


class FileSafetyAndCliTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name).resolve()
        self.artifacts = self.root / "artifacts"
        self.reports = self.root / "reports"
        self.artifacts.mkdir()
        self.reports.mkdir()
        self.input = self.root / "ramdisk.cpio"
        self.input.write_bytes(_cpio())
        patch = mock.patch.object(inspector, "ROOT", self.root)
        patch.start()
        self.addCleanup(patch.stop)

    def cli(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = inspector.main(list(arguments))
        return result, stdout.getvalue(), stderr.getvalue()

    def test_read_only_file_inspection_preserves_bytes_and_creates_no_members(self):
        before = set(self.root.rglob("*"))
        report = inspector.inspect_ramdisk(self.input)
        self.assertEqual(report["archive"]["name"], "ramdisk.cpio")
        self.assertTrue(report["validation"]["input_stable_during_read"])
        self.assertEqual(self.input.read_bytes(), _cpio())
        self.assertEqual(set(self.root.rglob("*")), before)

    def test_rejects_symlink_fifo_directory_missing_and_symlink_ancestor_inputs(self):
        link = self.root / "link.cpio"
        link.symlink_to(self.input)
        fifo = self.root / "fifo.cpio"
        os.mkfifo(fifo)
        for path in (link, fifo, self.root):
            with self.subTest(path=path.name), self.assertRaisesRegex(
                    inspector.RamdiskInspectionError, "regular file"):
                inspector.inspect_ramdisk(path)
        with self.assertRaises(FileNotFoundError):
            inspector.inspect_ramdisk(self.root / "missing.cpio")
        directory_link = self.root / "linked-parent"
        directory_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "ancestors"):
            inspector.inspect_ramdisk(directory_link / self.input.name)
        self.assertEqual(self.input.read_bytes(), _cpio())

    def test_rejects_oversized_sparse_input_before_opening_file(self):
        with self.input.open("ab") as stream:
            stream.truncate(inspector.MAX_ARCHIVE_BYTES + 4)
        original_open = os.open

        def no_input_open(path, flags, mode=0o777, *, dir_fd=None):
            self.assertNotEqual(path, self.input.name, "oversized input was opened")
            return original_open(path, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(inspector.os, "open", side_effect=no_input_open):
            with self.assertRaisesRegex(inspector.RamdiskInspectionError, "size bounds"):
                inspector.inspect_ramdisk(self.input)

    def test_rejects_input_identity_change_before_read_and_during_inspection(self):
        before = (1, 2, self.input.stat().st_size, 3, 4)
        after = (1, 2, self.input.stat().st_size, 3, 5)
        for signatures, message in (([before, after], "before read"),
                                    ([before, before, after], "during inspection")):
            with self.subTest(message=message), mock.patch.object(
                    inspector, "_signature", side_effect=signatures):
                with self.assertRaisesRegex(inspector.RamdiskInspectionError, message):
                    inspector.inspect_ramdisk(self.input)

    def test_input_ancestor_replacement_cannot_redirect_read(self):
        directory = self.root / "input-directory"
        directory.mkdir()
        path = directory / "recovery.cpio"
        path.write_bytes(_cpio())
        other = self.root / "other-directory"
        other.mkdir()
        (other / path.name).write_bytes(b"not a recovery ramdisk")
        moved = self.root / "moved-directory"
        original_open = os.open

        def swapping_open(name, flags, mode=0o777, *, dir_fd=None):
            if name == path.name:
                directory.rename(moved)
                directory.symlink_to(other, target_is_directory=True)
            return original_open(name, flags, mode, dir_fd=dir_fd)

        with mock.patch.object(inspector.os, "open", side_effect=swapping_open):
            report = inspector.inspect_ramdisk(path)
        self.assertEqual(report["archive"]["sha256"], hashlib.sha256(_cpio()).hexdigest())
        self.assertEqual((moved / path.name).read_bytes(), _cpio())

    def test_report_is_private_exclusive_json_in_either_allowed_root(self):
        report = inspector.inspect_ramdisk(self.input)
        for directory in (self.artifacts, self.reports):
            nested = directory / "existing-parent"
            nested.mkdir()
            output = nested / "inspection.json"
            inspector.write_report(output, report)
            self.assertEqual(json.loads(output.read_text()), report)
            self.assertEqual(stat.S_IMODE(output.stat().st_mode) & 0o077, 0)
            with self.assertRaises(FileExistsError):
                inspector.write_report(output, report)
        self.assertEqual(self.input.read_bytes(), _cpio())

    def test_report_rejects_outside_lookalike_and_traversing_destinations(self):
        report = inspector.inspect_ramdisk(self.input)
        lookalike = self.root / "artifacts-other"
        lookalike.mkdir()
        for output in (self.root / "outside.json", lookalike / "outside.json",
                       self.artifacts / ".." / "escaped.json"):
            with self.subTest(output=str(output)), self.assertRaisesRegex(
                    inspector.RamdiskInspectionError, "ignored artifacts/ or reports/"):
                inspector.write_report(output, report)
            self.assertFalse(output.exists())

    def test_report_never_overwrites_existing_regular_symlink_directory_or_input(self):
        report = inspector.inspect_ramdisk(self.input)
        regular = self.artifacts / "existing.json"
        regular.write_bytes(b"preserve me")
        symlink = self.artifacts / "symlink.json"
        symlink.symlink_to(regular)
        dangling = self.artifacts / "dangling.json"
        dangling.symlink_to(self.artifacts / "absent.json")
        directory = self.artifacts / "directory.json"
        directory.mkdir()
        json_input = self.artifacts / "ramdisk.json"
        json_input.write_bytes(_cpio())
        for output in (regular, symlink, dangling, directory, json_input):
            with self.subTest(output=output.name), self.assertRaises(FileExistsError):
                inspector.write_report(output, report)
        self.assertEqual(regular.read_bytes(), b"preserve me")
        self.assertTrue(symlink.is_symlink())
        self.assertTrue(dangling.is_symlink())
        self.assertTrue(directory.is_dir())
        self.assertEqual(json_input.read_bytes(), _cpio())

    def test_report_requires_real_existing_parent_json_suffix_and_bounded_content(self):
        report = inspector.inspect_ramdisk(self.input)
        parent_link = self.artifacts / "linked"
        parent_link.symlink_to(self.reports, target_is_directory=True)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "ancestors"):
            inspector.write_report(parent_link / "inspection.json", report)
        with self.assertRaises(FileNotFoundError):
            inspector.write_report(self.artifacts / "absent" / "inspection.json", report)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "suffix"):
            inspector.write_report(self.artifacts / "inspection.txt", report)
        with self.assertRaisesRegex(inspector.ImageInspectionError, "output bound"):
            inspector.write_report(self.artifacts / "large.json", {"data": "x" * 70000})
        self.assertFalse((self.artifacts / "absent").exists())
        self.assertFalse((self.artifacts / "large.json").exists())
        self.assertFalse((self.reports / "inspection.json").exists())

    def test_failed_report_write_preserves_partial_and_unrelated_replacement(self):
        report = inspector.inspect_ramdisk(self.input)
        output = self.artifacts / "new.json"
        moved = self.artifacts / "partial.json"

        def replacing_fsync(_descriptor):
            output.rename(moved)
            output.write_bytes(b"unrelated replacement")
            raise OSError("synthetic failure")

        with mock.patch.object(inspector.os, "fsync", side_effect=replacing_fsync):
            with self.assertRaisesRegex(inspector.ImageInspectionError, "partial artifact"):
                inspector.write_report(output, report)
        self.assertEqual(output.read_bytes(), b"unrelated replacement")
        self.assertTrue(moved.is_file())

    def test_cli_prints_report_without_extraction_or_output_file(self):
        before = set(self.root.rglob("*"))
        result, stdout, stderr = self.cli(str(self.input))
        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout)["archive"]["name"], self.input.name)
        self.assertEqual(set(self.root.rglob("*")), before)

    def test_cli_writes_identical_new_json_and_preserves_input(self):
        output = self.reports / "inspection.json"
        result, stdout, stderr = self.cli(str(self.input), "--output", str(output))
        self.assertEqual(result, 0)
        self.assertEqual(stderr, "")
        self.assertEqual(json.loads(stdout), json.loads(output.read_text()))
        self.assertEqual(self.input.read_bytes(), _cpio())

    def test_cli_invalid_archive_missing_input_and_bad_output_return_errors(self):
        output = self.reports / "invalid.json"
        self.input.write_bytes(bytes(112))
        result, stdout, stderr = self.cli(str(self.input), "--output", str(output))
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("ramdisk inspection failed", stderr)
        self.assertFalse(output.exists())
        result, stdout, stderr = self.cli(str(self.root / "missing.cpio"))
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("ramdisk inspection failed", stderr)
        self.input.write_bytes(_cpio())
        outside = self.root / "outside.json"
        result, stdout, stderr = self.cli(str(self.input), "--output", str(outside))
        self.assertEqual((result, stdout), (2, ""))
        self.assertIn("ignored artifacts/ or reports/", stderr)
        self.assertFalse(outside.exists())


if __name__ == "__main__":
    unittest.main()
