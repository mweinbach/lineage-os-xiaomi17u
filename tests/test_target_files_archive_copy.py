"""Synthetic ZIP-copy tests only; no Android image, native tool, VM, or key.

The tiny public-profile-shaped budgets here cannot admit a production artifact.
"""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
import unittest
from unittest import mock
import warnings
import zipfile
import zlib

from scripts import target_files_archive_copy as subject


def pin(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def extra(tag, payload):
    return struct.pack("<HH", tag, len(payload)) + payload


class RawNameInfo(zipfile.ZipInfo):
    def _encodeFilenameFlags(self):
        return self.raw_name, self.flag_bits & ~0x800


class Nonseekable(io.BytesIO):
    def seek(self, *args):
        raise io.UnsupportedOperation("nonseekable fixture")


class ArchiveCopyTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("no native process")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("no network")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("no shell")))
        directory = tempfile.TemporaryDirectory(prefix="synthetic-archive-copy-")
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.source = self.root / "original.zip"
        self.output = self.root / "reconciled.zip"
        self.payloads = {
            "META/vbmeta_digest.txt": b"a" * 64 + b"\n",
            "IMAGES/boot.img": b"old synthetic boot, never bootable" * 3,
            "IMAGES/vbmeta.img": b"old synthetic vbmeta, no signature" * 5,
            "IMAGES/vbmeta_system.img": b"old synthetic system vbmeta" * 7,
            "BOOTABLE_IMAGES/boot.img": b"old alias deliberately differs",
            "PREBUILT_IMAGES/vbmeta_system.img": b"different old system alias",
            "IMAGES/recovery.img": b"synthetic retained recovery, not working76",
            "PREBUILT_IMAGES/recovery.img": b"synthetic retained recovery alias",
            "META/misc_info.txt": b"avb_enable=true\n",
            "SYSTEM/": b"",
            "SYSTEM/etc/unchanged.txt": b"ordinary bytes\x00\xff" * 13,
            "SYSTEM/bin/link": b"../../private/unread-target",
            "SYSTEM/empty": b"",
        }
        self.new = {role: ("new SYNTHETIC unsigned " + role).encode() * 11
                    for role in ("boot", "vbmeta", "vbmeta_system")}
        self.paths, self.replacements = {}, {}
        for role, data in self.new.items():
            path = self.root / (role + ".fixture")
            path.write_bytes(data)
            self.paths[role] = path
        for name in self.payloads:
            role = Path(name).stem
            if name.split("/")[0] in ("IMAGES", "BOOTABLE_IMAGES", "PREBUILT_IMAGES") and role in self.new:
                self.replacements[name] = {"path": self.paths[role], **pin(self.new[role])}
        self.replacements[subject.DIGEST_MEMBER] = {"data": b"b" * 64 + b"\n"}
        self.profile = {"profile_id": "nezha-avb-image-set-v1",
                        "image_budgets": {role: 4096 for role in self.new}}

    def write_zip(self, *, compression=zipfile.ZIP_STORED, custom=None,
                  payloads=None, force64=False, descriptor=False):
        custom = custom or {}
        target = Nonseekable() if descriptor else self.source
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(target, "w") as archive:
                archive.comment = b"private synthetic archive comment\x00\xff"
                for name, data in (payloads or self.payloads).items():
                    options = custom.get(name, {})
                    cls = RawNameInfo if "raw_name" in options else zipfile.ZipInfo
                    info = cls(name, (2026, 8, 31, 22, 14, 26))
                    info.create_system = options.get("create_system", 3)
                    mode = stat.S_IFDIR | 0o751 if name.endswith("/") else stat.S_IFREG | 0o640
                    if name == "SYSTEM/bin/link":
                        mode = stat.S_IFLNK | 0o777
                    info.external_attr = options.get("external_attr", mode << 16)
                    info.internal_attr = options.get("internal_attr", 1)
                    info.comment = options.get("comment", b"member comment\xff")
                    info.extra = options.get("local_extra", extra(0xBEEF, b"local only"))
                    info.compress_type = options.get("compression", compression)
                    if "raw_name" in options:
                        info.raw_name = options["raw_name"]
                    wanted_attr = info.external_attr
                    with archive.open(info, "w", force_zip64=force64) as stream:
                        stream.write(data)
                    info.extra = options.get("central_extra", extra(0xCAFE, b"central only"))
                    info.external_attr = wanted_attr
        if descriptor:
            self.source.write_bytes(target.getvalue())
        return pin(self.source.read_bytes())

    def run_copy(self, *, expected=None, replacements=None, source=None, output=None, profile=None):
        return subject.rewrite_archive(source or self.source,
                                       expected or pin(self.source.read_bytes()),
                                       output or self.output,
                                       self.replacements if replacements is None else replacements,
                                       profile=self.profile if profile is None else profile)

    def assert_success(self, report):
        self.assertEqual(report["status"], "passed")
        self.assertEqual(report["member_count"], len(self.payloads))
        self.assertEqual(report["selected_replacement_count"], len(self.replacements))
        self.assertEqual(report["preserved_member_count"], len(self.payloads) - len(self.replacements))
        self.assertTrue(report["inputs_unchanged"])
        self.assertTrue(report["all_members_independently_read_back"])
        self.assertTrue(all(value is False for value in report["scope"].values()))
        self.assertEqual(stat.S_IMODE(self.output.stat().st_mode), 0o600)
        self.assertEqual({key: report["output_archive"][key] for key in ("sha256", "size_bytes")},
                         pin(self.output.read_bytes()))
        self.assertGreaterEqual(report["space"]["output_upper_bound_bytes"], self.output.stat().st_size)
        json.dumps(report)
        with zipfile.ZipFile(self.source) as source, zipfile.ZipFile(self.output) as output:
            self.assertEqual(source.namelist(), output.namelist())
            self.assertEqual(source.comment, output.comment)
            for name in source.namelist():
                wanted = self.replacements.get(name)
                if wanted:
                    data = wanted.get("data") if "data" in wanted else wanted["path"].read_bytes()
                else:
                    data = source.read(name)
                self.assertEqual(output.read(name), data, name)
                before, after = source.getinfo(name), output.getinfo(name)
                for field in ("filename", "date_time", "create_system", "external_attr", "internal_attr", "comment", "compress_type"):
                    self.assertEqual(getattr(before, field), getattr(after, field), (name, field))
                self.assertEqual(subject._without_zip64(before.extra), subject._without_zip64(after.extra))

    def central_entries(self, raw):
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            cursor = archive.start_dir
        rows = {}
        while raw[cursor:cursor + 4] == b"PK\x01\x02":
            name_size, extra_size, comment_size = struct.unpack_from("<HHH", raw, cursor + 28)
            name = bytes(raw[cursor + 46:cursor + 46 + name_size]).decode("utf-8")
            end = cursor + 46 + name_size + extra_size + comment_size
            rows[name] = (cursor, end)
            cursor = end
        return rows

    def patch_headers(self, name, *, flags=None, compression=None, crc=None, file_size=None):
        raw = bytearray(self.source.read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            offset = archive.getinfo(name).header_offset
        central = self.central_entries(raw)[name][0]
        for value, fmt, local_delta, central_delta in (
                (flags, "<H", 6, 8), (compression, "<H", 8, 10),
                (crc, "<I", 14, 16), (file_size, "<I", 22, 24)):
            if value is not None:
                struct.pack_into(fmt, raw, offset + local_delta, value)
                struct.pack_into(fmt, raw, central + central_delta, value)
        self.source.write_bytes(raw)

    def patch_deflate_payload(self, name, transform):
        raw = bytearray(self.source.read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo(name)
            old_directory = archive.start_dir
        name_size, extra_size = struct.unpack_from("<HH", raw, info.header_offset + 26)
        start = info.header_offset + 30 + name_size + extra_size
        old_end = start + info.compress_size
        new_payload = transform(bytes(raw[start:old_end]))
        delta = len(new_payload) - info.compress_size
        raw[start:old_end] = new_payload
        entries = self.central_entries_after_shift(raw, old_directory + delta)
        struct.pack_into("<I", raw, info.header_offset + 18, len(new_payload))
        for member, (central, _) in entries.items():
            if member == name:
                struct.pack_into("<I", raw, central + 20, len(new_payload))
            offset = struct.unpack_from("<I", raw, central + 42)[0]
            if offset > info.header_offset:
                struct.pack_into("<I", raw, central + 42, offset + delta)
        end = raw.rfind(b"PK\x05\x06")
        struct.pack_into("<I", raw, end + 16, old_directory + delta)
        self.source.write_bytes(raw)

    @staticmethod
    def central_entries_after_shift(raw, cursor):
        rows = {}
        while raw[cursor:cursor + 4] == b"PK\x01\x02":
            name_size, extra_size, comment_size = struct.unpack_from("<HHH", raw, cursor + 28)
            name = bytes(raw[cursor + 46:cursor + 46 + name_size]).decode("utf-8")
            end = cursor + 46 + name_size + extra_size + comment_size
            rows[name] = (cursor, end)
            cursor = end
        return rows

    def test_streamed_stored_and_deflated_rewrites_preserve_all_metadata_and_payloads(self):
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            with self.subTest(compression=compression):
                self.write_zip(compression=compression)
                report = self.run_copy(output=self.root / ("output-%d.zip" % compression))
                original_output = self.output
                self.output = self.root / ("output-%d.zip" % compression)
                try:
                    self.assert_success(report)
                finally:
                    self.output = original_output

    def test_rewrites_are_deterministic_for_fixed_runtime_and_inputs(self):
        self.write_zip(compression=zipfile.ZIP_DEFLATED)
        first = self.run_copy()
        second = self.run_copy(output=self.root / "second.zip")
        self.assertEqual(first["output_archive"]["sha256"], second["output_archive"]["sha256"])
        self.assertEqual(first["output_archive"]["member_identity_metadata_sha256"],
                         second["output_archive"]["member_identity_metadata_sha256"])

    def test_already_new_alias_and_digest_are_reported_without_inflating_changes(self):
        self.payloads["BOOTABLE_IMAGES/boot.img"] = self.new["boot"]
        self.payloads[subject.DIGEST_MEMBER] = self.replacements[subject.DIGEST_MEMBER]["data"]
        self.write_zip()
        report = self.run_copy()
        self.assert_success(report)
        self.assertEqual(report["identical_replacement_count"], 2)
        self.assertEqual(report["changed_member_count"], len(self.replacements) - 2)

    def test_image_data_and_digest_file_replacement_forms(self):
        self.write_zip()
        for name, row in self.replacements.items():
            if Path(name).stem == "boot":
                self.replacements[name] = {"data": self.new["boot"]}
        digest = self.root / "digest.fixture"
        digest.write_bytes(b"b" * 64 + b"\n")
        self.replacements[subject.DIGEST_MEMBER] = {"path": digest, **pin(digest.read_bytes())}
        self.assert_success(self.run_copy())

    def test_cp437_filename_unicode_extra_and_zero_external_attributes_are_preserved(self):
        name = "SYSTEM/etc/é.txt"
        self.payloads[name] = b"opaque filename fixture"
        raw_name = name.encode("cp437")
        unicode_extra = extra(0x7075, b"\x01" + struct.pack("<I", zlib.crc32(raw_name)) + name.encode("utf-8"))
        self.write_zip(custom={name: {"raw_name": raw_name, "external_attr": 0,
                                     "local_extra": unicode_extra, "central_extra": unicode_extra}})
        self.assert_success(self.run_copy())
        with zipfile.ZipFile(self.output) as archive:
            info = archive.getinfo(name)
            self.assertEqual(info.flag_bits & 0x800, 0)
            self.assertEqual(info.external_attr, 0)

    def test_utf8_filenames_are_preserved(self):
        self.payloads["SYSTEM/etc/测试.txt"] = b"unicode name fixture"
        self.write_zip()
        self.assert_success(self.run_copy())

    def test_local_zip64_and_signed_descriptors_are_rebuilt_safely(self):
        for force64, descriptor in ((True, False), (False, True), (True, True)):
            with self.subTest(force64=force64, descriptor=descriptor):
                self.write_zip(compression=zipfile.ZIP_DEFLATED, force64=force64, descriptor=descriptor)
                self.run_copy(output=self.root / ("zip64-%s-%s.zip" % (force64, descriptor)))

    def test_central_order_different_from_physical_order_is_preserved(self):
        self.write_zip()
        raw = bytearray(self.source.read_bytes())
        entries = list(self.central_entries(raw).values())
        first, last = entries[0][0], entries[-1][1]
        raw[first:last] = b"".join(raw[start:end] for start, end in reversed(entries))
        self.source.write_bytes(raw)
        self.assert_success(self.run_copy())

    def test_missing_extra_and_unknown_replacements_are_rejected_without_output(self):
        self.write_zip()
        for delta in ("missing", "unrelated", "absent_alias"):
            replacements = copy.deepcopy(self.replacements)
            if delta == "missing":
                replacements.pop("BOOTABLE_IMAGES/boot.img")
            else:
                name = "IMAGES/recovery.img" if delta == "unrelated" else "PREBUILT_IMAGES/vbmeta.img"
                replacements[name] = {"data": b"unexpected"}
            with self.subTest(delta=delta), self.assertRaisesRegex(subject.ArchiveCopyError, "replacement set"):
                self.run_copy(replacements=replacements)
            self.assertFalse(self.output.exists())

    def test_canonical_member_cannot_be_added_if_absent(self):
        self.payloads.pop("IMAGES/vbmeta.img")
        self.write_zip()
        with self.assertRaisesRegex(subject.ArchiveCopyError, "missing required"):
            self.run_copy()

    def test_new_alias_must_equal_its_canonical_new_image(self):
        self.write_zip()
        self.replacements["BOOTABLE_IMAGES/boot.img"] = {"data": b"different alias"}
        with self.assertRaisesRegex(subject.ArchiveCopyError, "alias differs"):
            self.run_copy()

    def test_digest_has_exact_lowercase_hex_and_newline_format(self):
        self.write_zip()
        for raw in (b"B" * 64 + b"\n", b"b" * 64, b"b" * 64 + b"\r\n", b"b" * 63 + b"\n", b"z" * 64 + b"\n"):
            with self.subTest(raw=raw), self.assertRaises(subject.ArchiveCopyError):
                self.run_copy(replacements={**self.replacements, subject.DIGEST_MEMBER: {"data": raw}})
            self.assertFalse(self.output.exists())

    def test_source_pin_and_replacement_pin_mismatches(self):
        self.write_zip()
        actual = pin(self.source.read_bytes())
        for expected in ({**actual, "sha256": "0" * 64}, {**actual, "size_bytes": actual["size_bytes"] + 1},
                         {**actual, "size_bytes": True}):
            with self.assertRaises(subject.ArchiveCopyError):
                self.run_copy(expected=expected)
        self.paths["boot"].write_bytes(b"mutated")
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy()
        self.assertFalse(self.output.exists())

    def test_selected_zip_symlinks_and_symlink_ancestors_fail(self):
        for target in ("IMAGES/boot.img", "META/vbmeta_digest.txt", "IMAGES/"):
            with self.subTest(target=target):
                payloads = dict(self.payloads)
                payloads.setdefault(target, b"elsewhere")
                self.write_zip(payloads=payloads, custom={target: {"external_attr": (stat.S_IFLNK | 0o777) << 16}})
                with self.assertRaises(subject.ArchiveCopyError):
                    self.run_copy()
                self.assertFalse(self.output.exists())

    def test_source_and_replacement_symlinks_hardlinks_and_parent_symlinks_fail(self):
        self.write_zip()
        source_link = self.root / "source-link"
        source_link.symlink_to(self.source)
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy(source=source_link)
        parent_link = self.root / "parent-link"
        parent_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy(source=parent_link / self.source.name)
        replacement_link = self.root / "replacement-link"
        replacement_link.symlink_to(self.paths["boot"])
        self.replacements["IMAGES/boot.img"]["path"] = replacement_link
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy()
        self.replacements["IMAGES/boot.img"]["path"] = self.paths["boot"]
        os.link(self.paths["boot"], self.root / "replacement-hardlink")
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy()
        self.assertFalse(self.output.exists())

    def test_existing_output_and_symlink_parent_fail_without_overwrite(self):
        self.write_zip()
        self.output.write_bytes(b"do not overwrite")
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy()
        self.assertEqual(self.output.read_bytes(), b"do not overwrite")
        alias = self.root / "parent-alias"
        alias.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy(output=alias / "new-output")
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy(output=self.source)

    def test_duplicate_names_case_aliases_and_unsafe_paths_fail(self):
        self.write_zip()
        for name in ("IMAGES/boot.img", "images/boot.img", "SYSTEM/../escape", "SYSTEM\\escape"):
            self.write_zip()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(self.source, "a") as archive:
                    archive.writestr(name, b"invalid member")
            with self.subTest(name=name), self.assertRaises(subject.ArchiveCopyError):
                self.run_copy()
            self.assertFalse(self.output.exists())

    def test_unchanged_member_crc_corruption_is_not_laundered(self):
        self.write_zip()
        name = "SYSTEM/etc/unchanged.txt"
        self.patch_headers(name, crc=0)
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy()

    def test_changed_old_member_crc_corruption_is_not_laundered(self):
        self.write_zip()
        self.patch_headers("IMAGES/boot.img", crc=0)
        with self.assertRaises(subject.ArchiveCopyError):
            self.run_copy()

    def test_trailing_deflate_bytes_on_unchanged_member_fail(self):
        self.write_zip(compression=zipfile.ZIP_DEFLATED)
        self.patch_deflate_payload("SYSTEM/etc/unchanged.txt", lambda raw: raw + b"junk")
        with self.assertRaisesRegex(subject.ArchiveCopyError, "DEFLATE"):
            self.run_copy()

    def test_truncated_deflate_end_marker_fails_even_if_zipfile_reads_plaintext(self):
        self.write_zip(compression=zipfile.ZIP_DEFLATED)
        name = "SYSTEM/etc/unchanged.txt"
        compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
        incomplete = compressor.compress(self.payloads[name]) + compressor.flush(zlib.Z_SYNC_FLUSH)
        self.patch_deflate_payload(name, lambda raw: incomplete)
        with zipfile.ZipFile(self.source) as archive:
            self.assertEqual(archive.read(name), self.payloads[name])
        with self.assertRaisesRegex(subject.ArchiveCopyError, "DEFLATE"):
            self.run_copy()

    def test_hidden_extra_decoded_byte_is_not_clipped_into_a_pass(self):
        self.write_zip(compression=zipfile.ZIP_DEFLATED)
        name = "SYSTEM/etc/unchanged.txt"
        compressor = zlib.compressobj(6, zlib.DEFLATED, -15)
        excessive = compressor.compress(self.payloads[name] + b"X") + compressor.flush()
        self.patch_deflate_payload(name, lambda raw: excessive)
        with zipfile.ZipFile(self.source) as archive:
            self.assertEqual(archive.read(name), self.payloads[name])
        with self.assertRaisesRegex(subject.ArchiveCopyError, "DEFLATE"):
            self.run_copy()

    def test_encryption_or_unsupported_compression_anywhere_fails(self):
        for kwargs in ({"flags": 1}, {"flags": 64}, {"flags": 8192}, {"flags": 0x80},
                       {"flags": 2}, {"compression": zipfile.ZIP_BZIP2}):
            self.write_zip()
            self.patch_headers("SYSTEM/etc/unchanged.txt", **kwargs)
            with self.subTest(kwargs=kwargs), self.assertRaises(subject.ArchiveCopyError):
                self.run_copy()

    def test_duplicate_local_offsets_and_overlapping_spans_fail(self):
        for duplicate in (True, False):
            self.write_zip()
            raw = bytearray(self.source.read_bytes())
            entries = self.central_entries(raw)
            first = entries["IMAGES/boot.img"][0]
            second = entries["IMAGES/vbmeta.img"][0]
            offset = struct.unpack_from("<I", raw, first + 42)[0]
            struct.pack_into("<I", raw, second + 42, offset if duplicate else offset + 31)
            self.source.write_bytes(raw)
            with self.subTest(duplicate=duplicate), self.assertRaises(subject.ArchiveCopyError):
                self.run_copy()

    def test_local_and_central_header_mismatch_fails(self):
        self.write_zip()
        raw = bytearray(self.source.read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            offset = archive.getinfo("SYSTEM/etc/unchanged.txt").header_offset
        struct.pack_into("<I", raw, offset + 14, 0)
        self.source.write_bytes(raw)
        with self.assertRaisesRegex(subject.ArchiveCopyError, "local/central"):
            self.run_copy()

    def test_nonzero_member_disk_and_local_time_or_version_mismatches_fail(self):
        for field in ("disk", "time", "version"):
            self.write_zip()
            raw = bytearray(self.source.read_bytes())
            name = "SYSTEM/etc/unchanged.txt"
            with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                offset = archive.getinfo(name).header_offset
            if field == "disk":
                central = self.central_entries(raw)[name][0]
                struct.pack_into("<H", raw, central + 34, 1)
            else:
                delta = 10 if field == "time" else 4
                value = struct.unpack_from("<H", raw, offset + delta)[0]
                struct.pack_into("<H", raw, offset + delta, value ^ 1)
            self.source.write_bytes(raw)
            with self.subTest(field=field), self.assertRaises(subject.ArchiveCopyError):
                self.run_copy()
            self.assertFalse(self.output.exists())

    def test_geometry_uses_constant_work_per_selected_span(self):
        self.write_zip()
        real = subject.inventory._selected_span
        seen = []
        def bounded(archive, info):
            seen.append(len(archive.infolist()))
            self.assertIsInstance(archive, subject._SpanBoundary)
            return real(archive, info)
        with mock.patch.object(subject.inventory, "_selected_span", side_effect=bounded):
            self.run_copy()
        self.assertEqual(set(seen), {0})

    def test_early_replacement_mutation_and_same_byte_inode_rebind_are_caught(self):
        real = subject._write_replacement
        for rebind in (False, True):
            self.write_zip()
            self.paths["boot"].write_bytes(self.new["boot"])
            fired = False
            def mutate(row, opened, sink):
                nonlocal fired
                result = real(row, opened, sink)
                if row.get("role") == "vbmeta_system" and not fired:
                    fired = True
                    if rebind:
                        replacement = self.root / "swap-file"
                        replacement.write_bytes(self.new["boot"])
                        replacement.replace(self.paths["boot"])
                    else:
                        self.paths["boot"].write_bytes(b"changed after copy")
                return result
            with mock.patch.object(subject, "_write_replacement", side_effect=mutate):
                with self.subTest(rebind=rebind), self.assertRaises(subject.ArchiveCopyError):
                    self.run_copy(output=self.root / ("mutation-%s.zip" % rebind))

    def test_source_mutation_after_copy_is_caught(self):
        self.write_zip()
        real = subject._readback
        def mutate(*args):
            result = real(*args)
            with self.source.open("ab") as stream:
                stream.write(b"mutation")
            return result
        with mock.patch.object(subject, "_readback", side_effect=mutate):
            with self.assertRaises(subject.ArchiveCopyError):
                self.run_copy()

    def test_output_mutation_and_private_mode_change_during_readback_are_caught(self):
        real = subject._readback
        for change_mode in (False, True):
            self.write_zip()
            output = self.root / ("readback-mutation-%s.zip" % change_mode)
            def mutate(*args):
                result = real(*args)
                if change_mode:
                    output.chmod(0o644)
                else:
                    with output.open("ab") as stream:
                        stream.write(b"mutation")
                return result
            with mock.patch.object(subject, "_readback", side_effect=mutate):
                with self.subTest(change_mode=change_mode), self.assertRaises(subject.ArchiveCopyError):
                    self.run_copy(output=output)

    def test_output_privacy_change_before_initial_postcopy_guard_is_caught(self):
        self.write_zip()
        real = subject._copy_members
        def alter(*args):
            result = real(*args)
            self.output.chmod(0o644)
            return result
        with mock.patch.object(subject, "_copy_members", side_effect=alter):
            with self.assertRaisesRegex(subject.ArchiveCopyError, "private mode"):
                self.run_copy()

    def test_same_byte_source_rebinding_through_renamed_parent_is_caught(self):
        self.write_zip()
        original_bytes = self.source.read_bytes()
        parent = self.root / "source-parent"
        parent.mkdir()
        nested = parent / "archive.zip"
        self.source.replace(nested)
        self.source = nested
        real = subject._readback
        def rebind(*args):
            result = real(*args)
            parent.rename(self.root / "retained-parent")
            parent.mkdir()
            nested.write_bytes(original_bytes)
            return result
        with mock.patch.object(subject, "_readback", side_effect=rebind):
            with self.assertRaisesRegex(subject.ArchiveCopyError, "pathname/inode"):
                self.run_copy()

    def test_readback_detects_rewritten_unchanged_metadata(self):
        self.write_zip()
        real = subject._write_info
        def altered(info, *args):
            result = real(info, *args)
            if info.filename == "SYSTEM/etc/unchanged.txt":
                result.internal_attr ^= 1
            return result
        with mock.patch.object(subject, "_write_info", side_effect=altered):
            with self.assertRaisesRegex(subject.ArchiveCopyError, "semantic metadata differs"):
                self.run_copy()

    def test_nonseekable_descriptor_corruption_fails(self):
        self.write_zip(descriptor=True)
        raw = bytearray(self.source.read_bytes())
        with zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.getinfo("SYSTEM/etc/unchanged.txt")
        names, extras = struct.unpack_from("<HH", raw, info.header_offset + 26)
        descriptor = info.header_offset + 30 + names + extras + info.compress_size
        self.assertEqual(raw[descriptor:descriptor + 4], b"PK\x07\x08")
        struct.pack_into("<I", raw, descriptor + 4, 0)
        self.source.write_bytes(raw)
        with self.assertRaisesRegex(subject.ArchiveCopyError, "descriptor"):
            self.run_copy()

    def test_allocation_and_cumulative_payload_bounds_fail(self):
        self.write_zip()
        for name, value in (("MAX_MEMBERS", 2), ("MAX_CENTRAL_DIRECTORY", 10), ("MAX_DECLARED_BYTES", 10)):
            with mock.patch.object(subject.inventory, name, value):
                with self.subTest(bound=name), self.assertRaises(subject.ArchiveCopyError):
                    self.run_copy()
            self.assertFalse(self.output.exists())
        with mock.patch.object(subject, "MAX_OUTPUT", 100):
            with self.assertRaises(subject.ArchiveCopyError):
                self.run_copy()

    def test_output_free_space_uses_recompression_bound_and_keeps_reserve(self):
        self.write_zip(compression=zipfile.ZIP_DEFLATED)
        with mock.patch.object(subject, "_available", return_value=1):
            with self.assertRaisesRegex(subject.ArchiveCopyError, "insufficient output space"):
                self.run_copy()
        self.assertFalse(self.output.exists())
        with mock.patch.object(subject, "SPACE_CHECK_BYTES", 1), mock.patch.object(
                subject, "_available", side_effect=[10**12, 10**12] + [0] * 20):
            with self.assertRaisesRegex(subject.ArchiveCopyError, "free-space floor"):
                self.run_copy()
        self.assertTrue(self.output.exists())

    def test_fsync_failure_retains_partial_archive_and_never_returns_success(self):
        self.write_zip()
        with mock.patch.object(subject.os, "fsync", side_effect=OSError("synthetic fsync failure")):
            with self.assertRaisesRegex(subject.ArchiveCopyError, "fsync failure"):
                self.run_copy()
        self.assertTrue(self.output.exists())

    def test_small_chunks_do_not_read_whole_member_payloads(self):
        self.payloads["SYSTEM/etc/unchanged.txt"] = b"bounded large synthetic payload" * 2048
        self.write_zip(compression=zipfile.ZIP_DEFLATED)
        real = zipfile.ZipExtFile.read
        requests = []
        def bounded(stream, length=-1):
            requests.append(length)
            self.assertGreater(length, 0)
            self.assertLessEqual(length, 127)
            return real(stream, length)
        with mock.patch.object(subject, "CHUNK", 127), mock.patch.object(zipfile.ZipExtFile, "read", new=bounded):
            self.run_copy()
        self.assertGreater(len(requests), 500)


if __name__ == "__main__":
    unittest.main(verbosity=2)
