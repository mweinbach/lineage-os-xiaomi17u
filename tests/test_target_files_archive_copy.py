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
from tests import test_avb_image_set as avb_fixture


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

    def run_copy(self, *, expected=None, replacements=None, source=None, output=None, profile=None,
                 dtbo_alias_proof=None):
        return subject.rewrite_archive(source or self.source,
                                       expected or pin(self.source.read_bytes()),
                                       output or self.output,
                                       self.replacements if replacements is None else replacements,
                                       profile=self.profile if profile is None else profile,
                                       dtbo_alias_proof=dtbo_alias_proof)

    def dtbo_image(self, *, payload=None, salt=b"C" * 32, fingerprint=b"canonical fixture",
                   descriptors=None, descriptor_end_offsets=False):
        payload = avb_fixture.dtbo_payload() if payload is None else payload
        if descriptors is None:
            descriptors = [avb_fixture.hash_descriptor("dtbo", payload, salt=salt),
                           avb_fixture.property_descriptor(subject.DTBO_FINGERPRINT.encode(), fingerprint)]
        metadata = bytearray(avb_fixture.vbmeta(descriptors))
        if descriptor_end_offsets:
            length = struct.unpack_from(">Q", metadata, 104)[0]
            struct.pack_into(">Q", metadata, 64, length)
            struct.pack_into(">Q", metadata, 80, length)
        return avb_fixture.with_footer(payload, bytes(metadata))

    def add_dtbo_pair(self, *, canonical=None, alias=None, descriptor_end_offsets=False):
        self.profile["image_budgets"]["dtbo"] = 16 * 1024
        canonical = self.dtbo_image(descriptor_end_offsets=descriptor_end_offsets) if canonical is None else canonical
        alias = (self.dtbo_image(salt=b"A" * 64, fingerprint=b"different alias fixture " * 4,
                                 descriptor_end_offsets=descriptor_end_offsets) if alias is None else alias)
        self.payloads[subject.DTBO_CANONICAL_MEMBER] = canonical
        self.payloads[subject.DTBO_ALIAS_MEMBER] = alias
        path = self.root / "canonical-dtbo.fixture"
        path.write_bytes(canonical)
        return {**self.replacements, subject.DTBO_ALIAS_MEMBER: {"path": path, **pin(canonical)}}

    def inspect_dtbo(self, *, profile=None, expected=None):
        return subject.inspect_dtbo_alias(self.source, expected or pin(self.source.read_bytes()),
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

    def test_dtbo_alias_only_normalization_preserves_canonical_and_every_other_member(self):
        # Make the three ordinary replacement roles no-ops; DTBO alias is the
        # only byte change, never an additional canonical replacement role.
        for name, replacement in self.replacements.items():
            self.payloads[name] = (replacement["data"] if "data" in replacement
                                   else replacement["path"].read_bytes())
        for end_offsets in (False, True):
            for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
                with self.subTest(end_offsets=end_offsets, compression=compression):
                    replacements = self.add_dtbo_pair(descriptor_end_offsets=end_offsets)
                    expected = self.write_zip(compression=compression)
                    before_paths = sorted(self.root.iterdir())
                    proof = self.inspect_dtbo(expected=expected)
                    self.assertEqual(sorted(self.root.iterdir()), before_paths)
                    self.assertEqual(proof, self.inspect_dtbo(expected=expected))
                    self.assertEqual(proof["source_archive"], expected)
                    self.assertEqual(proof["before"], pin(self.payloads[subject.DTBO_ALIAS_MEMBER]))
                    self.assertEqual(proof["after"], pin(self.payloads[subject.DTBO_CANONICAL_MEMBER]))
                    self.assertEqual(proof["payload"], pin(avb_fixture.dtbo_payload()))
                    self.assertNotEqual(proof["before_metadata"]["vbmeta"]["identity"],
                                        proof["after_metadata"]["vbmeta"]["identity"])
                    self.assertEqual(proof["before_metadata"]["vbmeta"]["invariant_header"],
                                     proof["after_metadata"]["vbmeta"]["invariant_header"])
                    self.output = self.root / f"dtbo-{end_offsets}-{compression}.zip"
                    report = self.run_copy(replacements=replacements, dtbo_alias_proof=proof)
                    ordinary = self.replacements
                    self.replacements = replacements
                    try:
                        self.assert_success(report)
                    finally:
                        self.replacements = ordinary
                    self.assertEqual(report["changed_member_count"], 1)
                    self.assertEqual(report["dtbo_alias_proof"], proof)
                    self.assertNotIn(subject.DTBO_CANONICAL_MEMBER,
                                     {row["member"] for row in report["replacement_members"]})
                    self.assertEqual(pin(self.source.read_bytes()), expected)

    def test_default_copy_keeps_dtbo_alias_unchanged_and_rejects_extra_replacement(self):
        replacements = self.add_dtbo_pair()
        self.write_zip()
        report = self.run_copy()
        self.assertNotIn("dtbo_alias_proof", report)
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(archive.read(subject.DTBO_ALIAS_MEMBER), self.payloads[subject.DTBO_ALIAS_MEMBER])
        target = self.root / "unproved.zip"
        with self.assertRaisesRegex(subject.ArchiveCopyError, "replacement set"):
            self.run_copy(replacements=replacements, output=target)
        self.assertFalse(target.exists())
        self.assertEqual(subject.ROLES, frozenset(("boot", "vbmeta", "vbmeta_system")))

    def test_dtbo_proof_cannot_add_missing_alias_canonical_or_any_other_replacement(self):
        replacements = self.add_dtbo_pair()
        self.payloads["BOOTABLE_IMAGES/dtbo.img"] = self.payloads[subject.DTBO_CANONICAL_MEMBER]
        self.write_zip()
        proof = self.inspect_dtbo()
        for name in (subject.DTBO_CANONICAL_MEMBER, "BOOTABLE_IMAGES/dtbo.img", "IMAGES/recovery.img"):
            with self.subTest(extra=name), self.assertRaisesRegex(subject.ArchiveCopyError, "replacement set"):
                self.run_copy(replacements={**replacements, name: {"data": b"unauthorized"}},
                              dtbo_alias_proof=proof)
            self.assertFalse(self.output.exists())
        for missing in (subject.DTBO_ALIAS_MEMBER, subject.DTBO_CANONICAL_MEMBER):
            payloads = dict(self.payloads)
            payloads.pop(missing)
            self.write_zip(payloads=payloads)
            with self.subTest(missing=missing), self.assertRaisesRegex(subject.ArchiveCopyError, "existing canonical"):
                self.run_copy(replacements=replacements, dtbo_alias_proof=proof)
            self.assertFalse(self.output.exists())

    def test_dtbo_proof_is_recomputed_type_exact_and_not_a_trusted_boolean(self):
        replacements = self.add_dtbo_pair()
        self.write_zip()
        valid = self.inspect_dtbo()
        forged = [True, [], {}, {"verified": True}, {**valid, "schema_version": True},
                  {**valid, "unexpected": False}, {**valid, "before": valid["after"]},
                  {**valid, "after": valid["before"]},
                  {**valid, "source_archive": {**valid["source_archive"], "sha256": "0" * 64}}]
        missing = copy.deepcopy(valid)
        del missing["payload"]
        forged.append(missing)
        nested = copy.deepcopy(valid)
        nested["before_metadata"]["salted_payload_digest_verified"] = 1
        forged.append(nested)
        for proof in forged:
            with self.subTest(proof=repr(proof)[:80]), self.assertRaisesRegex(subject.ArchiveCopyError, "proof differs"):
                self.run_copy(replacements=replacements, dtbo_alias_proof=proof)
            self.assertFalse(self.output.exists())
        with self.assertRaisesRegex(subject.ArchiveCopyError, "replacement set"):
            self.run_copy(dtbo_alias_proof=valid)  # The proved alias must actually be selected.
        self.assertFalse(self.output.exists())

    def test_dtbo_replacement_must_be_exact_canonical_bytes_not_just_the_same_payload(self):
        replacements = self.add_dtbo_pair()
        self.write_zip()
        proof = self.inspect_dtbo()
        for data in (self.payloads[subject.DTBO_ALIAS_MEMBER], b"unrelated replacement"):
            bad = {**replacements, subject.DTBO_ALIAS_MEMBER: {"data": data}}
            with self.assertRaisesRegex(subject.ArchiveCopyError, "unchanged canonical"):
                self.run_copy(replacements=bad, dtbo_alias_proof=proof)
            self.assertFalse(self.output.exists())
        # A correctly declared identity with different actual file bytes also fails.
        replacements[subject.DTBO_ALIAS_MEMBER]["path"].write_bytes(self.payloads[subject.DTBO_ALIAS_MEMBER])
        with self.assertRaisesRegex(subject.ArchiveCopyError, "replacement file identity"):
            self.run_copy(replacements=replacements, dtbo_alias_proof=proof)
        self.assertFalse(self.output.exists())

    def test_dtbo_proof_is_bound_to_the_whole_archive_not_just_the_two_members(self):
        replacements = self.add_dtbo_pair()
        self.write_zip()
        proof = self.inspect_dtbo()
        self.payloads["SYSTEM/etc/unchanged.txt"] += b"different archive"
        self.write_zip()
        current = self.inspect_dtbo()
        self.assertEqual(current["before"], proof["before"])
        self.assertEqual(current["after"], proof["after"])
        self.assertNotEqual(current["source_archive"], proof["source_archive"])
        with self.assertRaisesRegex(subject.ArchiveCopyError, "proof differs"):
            self.run_copy(replacements=replacements, dtbo_alias_proof=proof)
        self.assertFalse(self.output.exists())

    def test_dtbo_complete_payload_comparison_includes_later_entries_table_words_and_gaps(self):
        fdt = avb_fixture.dtbo_payload()[64:]
        payload = (struct.pack(">8I", 0xD7B7AB1E, 200, 32, 32, 2, 32, 4096, 0)
                   + struct.pack(">8I", 40, 96, 1, 0, 0, 0, 0, 0)
                   + struct.pack(">8I", 40, 160, 2, 0, 0, 0, 0, 0)
                   + fdt + bytes(24) + fdt)
        canonical = self.dtbo_image(payload=payload)
        for offset in (199, 60, 145):
            altered = bytearray(payload)
            altered[offset] ^= 1
            # Deliberately valid freshly recomputed salted digest: equality of
            # the entire declared payload, not just its first DTB, rejects this.
            alias = self.dtbo_image(payload=bytes(altered), salt=b"A" * 64)
            self.add_dtbo_pair(canonical=canonical, alias=alias)
            self.write_zip()
            with self.subTest(offset=offset), self.assertRaisesRegex(subject.ArchiveCopyError, "complete canonical payload"):
                self.inspect_dtbo()

    def test_dtbo_payload_geometry_and_independent_salted_digests_are_required(self):
        payload = avb_fixture.dtbo_payload()
        invalid = {}
        bad_size = [avb_fixture.hash_descriptor("dtbo", payload, size=len(payload) - 1),
                    avb_fixture.property_descriptor(subject.DTBO_FINGERPRINT.encode(), b"alias")]
        invalid["hash coverage"] = self.dtbo_image(descriptors=bad_size)
        for label, offset in (("header total", 7), ("entry outside payload", 35), ("sparse magic", 0)):
            changed = bytearray(payload)
            changed[offset] ^= 1
            invalid[label] = self.dtbo_image(payload=bytes(changed))
        changed = bytearray(self.dtbo_image())
        changed[-1] = 1
        invalid["footer reserved"] = bytes(changed)
        changed = bytearray(self.dtbo_image())
        changed[100] ^= 1
        invalid["unhashed payload mutation"] = bytes(changed)
        changed = bytearray(self.dtbo_image(salt=b"A" * 64))
        offset = subject.avb.FOOTER.unpack(changed[-64:])[4]
        changed[offset + 256 + subject.avb.HASH.size + 4 + 64] ^= 1
        invalid["unverified metadata digest"] = bytes(changed)
        for label, alias in invalid.items():
            self.add_dtbo_pair(alias=alias)
            self.write_zip()
            with self.subTest(label=label), self.assertRaises(subject.ArchiveCopyError):
                self.inspect_dtbo()

    def test_dtbo_canonical_and_alias_both_require_verified_digests_and_zero_padding(self):
        base = self.dtbo_image(fingerprint=b"short")
        _, _, _, original, offset, size, _ = subject.avb.FOOTER.unpack(base[-64:])
        first_size = struct.unpack_from(">Q", base, offset + 256 + 8)[0] + 16
        property_at = offset + 256 + first_size
        property_size = struct.unpack_from(">Q", base, property_at + 8)[0] + 16
        key_length, value_length = struct.unpack_from(">QQ", base, property_at + 16)
        property_padding = property_at + 32 + key_length + value_length + 2
        self.assertLess(property_padding, property_at + property_size)
        desc_size = struct.unpack_from(">Q", base, offset + 104)[0]
        self.assertLess(256 + desc_size, size)
        offsets = {
            "pre-metadata padding": original, "post-metadata padding": offset + size,
            "auxiliary padding": offset + size - 1, "property padding": property_padding,
            "header reserved": offset + 176, "hash reserved": offset + 256 + 72,
            "hash flags": offset + 256 + 71, "footer reserved": len(base) - 1,
            "late payload digest": original - 1,
            "declared digest": offset + 256 + subject.avb.HASH.size + 4 + 32,
        }
        for side in ("canonical", "alias"):
            for label, changed_at in offsets.items():
                changed = bytearray(base)
                changed[changed_at] ^= 1
                self.add_dtbo_pair(**{side: bytes(changed)})
                self.write_zip()
                with self.subTest(side=side, label=label), self.assertRaises(subject.ArchiveCopyError):
                    self.inspect_dtbo()

    def test_dtbo_raw_header_differences_cannot_hide_in_semantic_parser_omissions(self):
        payload = avb_fixture.dtbo_payload()
        base = self.dtbo_image()
        _, _, _, _, offset, size, _ = subject.avb.FOOTER.unpack(base[-64:])
        metadata = base[offset:offset + size]
        desc_size = struct.unpack_from(">Q", metadata, 104)[0]
        changes = {}
        for label, at, data in (
                ("release prefix", 128, b"X"), ("release after NUL", 175, b"X"),
                ("required version", 8, struct.pack(">I", 1)),
                ("arbitrary key offset", 64, struct.pack(">Q", 8)),
                ("arbitrary metadata offset", 80, struct.pack(">Q", 1)),
                ("key offset convention", 64, struct.pack(">Q", desc_size))):
            changed = bytearray(metadata)
            changed[at:at + len(data)] = data
            changes[label] = bytes(changed)
        changed = bytearray(metadata + bytes(64))
        struct.pack_into(">Q", changed, 20, len(changed) - 256)
        changes["unjustified auxiliary padding block"] = bytes(changed)
        header = bytearray(metadata[:256])
        auxiliary = avb_fixture.padded(bytes(8) + metadata[256:256 + desc_size], 64)
        struct.pack_into(">Q", header, 20, len(auxiliary))
        struct.pack_into(">Q", header, 96, 8)
        changes["relocated descriptors"] = bytes(header) + auxiliary
        for label, changed in changes.items():
            # Every variant deliberately passes the general AVB parser, so
            # these assertions exercise the additional narrow raw-layout guard.
            subject.avb.parse_vbmeta(changed)
            self.add_dtbo_pair(canonical=base, alias=avb_fixture.with_footer(payload, changed))
            self.write_zip()
            with self.subTest(label=label), self.assertRaises(subject.ArchiveCopyError):
                self.inspect_dtbo()
        descriptors = [avb_fixture.hash_descriptor("dtbo", payload),
                       avb_fixture.property_descriptor(subject.DTBO_FINGERPRINT.encode(), b"alias")]
        for kwargs in ({"rollback": 1}, {"location": 1}, {"key": avb_fixture.public_blob(7)}):
            changed = avb_fixture.vbmeta(descriptors, **kwargs)
            subject.avb.parse_vbmeta(changed)
            self.add_dtbo_pair(canonical=base, alias=avb_fixture.with_footer(payload, changed))
            self.write_zip()
            with self.subTest(fields=sorted(kwargs)), self.assertRaisesRegex(subject.ArchiveCopyError, "unsigned NONE"):
                self.inspect_dtbo()

    def test_dtbo_zero_padding_cannot_justify_relocating_metadata_or_changing_full_size(self):
        payload = avb_fixture.dtbo_payload()
        base = self.dtbo_image()
        footer = list(subject.avb.FOOTER.unpack(base[-64:]))
        metadata = base[footer[4]:footer[4] + footer[5]]
        def image_at(at):
            footer[4] = at
            prefix = payload + bytes(at - len(payload)) + metadata
            return prefix + bytes(16384 - len(prefix) - 64) + subject.avb.FOOTER.pack(*footer)
        self.add_dtbo_pair(canonical=image_at(4096), alias=image_at(8192))
        self.write_zip()
        with self.assertRaisesRegex(subject.ArchiveCopyError, "metadata placement"):
            self.inspect_dtbo()

    def test_dtbo_only_its_fingerprint_value_and_hash_salt_may_change(self):
        payload = avb_fixture.dtbo_payload()
        own = avb_fixture.hash_descriptor("dtbo", payload)
        fingerprint = avb_fixture.property_descriptor(subject.DTBO_FINGERPRINT.encode(), b"canonical")
        same_other = avb_fixture.property_descriptor(b"com.android.build.dtbo.security_patch", b"2026-03-05")
        canonical = self.dtbo_image(descriptors=[own, fingerprint, same_other])
        changed_fp = avb_fixture.property_descriptor(subject.DTBO_FINGERPRINT.encode(), b"alias" * 31)
        alias_own = avb_fixture.hash_descriptor("dtbo", payload, salt=b"S" * 64)
        self.add_dtbo_pair(canonical=canonical,
                           alias=self.dtbo_image(descriptors=[alias_own, changed_fp, same_other]))
        self.write_zip()
        self.inspect_dtbo()  # Identical extra properties are preserved, not removed.
        bad = {
            "other property changed": [alias_own, changed_fp, avb_fixture.property_descriptor(
                b"com.android.build.dtbo.security_patch", b"2026-04-05")],
            "other property missing": [alias_own, changed_fp],
            "other property added": [alias_own, changed_fp, same_other,
                                     avb_fixture.property_descriptor(b"extra", b"value")],
            "wrong fingerprint namespace": [alias_own, avb_fixture.property_descriptor(
                b"com.android.build.boot.fingerprint", b"alias"), same_other],
            "reordered property": [changed_fp, alias_own, same_other],
            "duplicate property": [alias_own, changed_fp, changed_fp, same_other],
            "second hash": [alias_own, changed_fp, same_other,
                            avb_fixture.hash_descriptor("boot", payload)],
            "wrong hash owner": [avb_fixture.hash_descriptor("boot", payload), changed_fp, same_other],
            "hashtree instead of hash": [avb_fixture.tree_descriptor("dtbo"), changed_fp, same_other],
            "chain instead of hash": [avb_fixture.chain_descriptor(
                "dtbo", 1, avb_fixture.public_blob(9)), changed_fp, same_other],
        }
        for label, rows in bad.items():
            self.add_dtbo_pair(canonical=canonical, alias=self.dtbo_image(descriptors=rows))
            self.write_zip()
            with self.subTest(label=label), self.assertRaises(subject.ArchiveCopyError):
                self.inspect_dtbo()

    def test_dtbo_inspection_has_a_fixed_memory_bound_and_requires_equal_full_sizes(self):
        self.add_dtbo_pair()
        self.write_zip()
        for budget in (None, False, 0, -1, "33554432", subject.MAX_DTBO_BYTES + 1, 8191):
            profile = copy.deepcopy(self.profile)
            profile["image_budgets"]["dtbo"] = budget
            with self.subTest(budget=budget), mock.patch.object(
                    subject, "_read_member", side_effect=AssertionError("must fail before member collection")):
                with self.assertRaises(subject.ArchiveCopyError):
                    self.inspect_dtbo(profile=profile)
        self.payloads[subject.DTBO_ALIAS_MEMBER] += bytes(4096)
        self.write_zip()
        with self.assertRaisesRegex(subject.ArchiveCopyError, "sizes differ"):
            self.inspect_dtbo()

    def test_dtbo_alias_inspection_retains_zip_integrity_and_member_safety_guards(self):
        self.add_dtbo_pair()
        for compression in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            self.write_zip(compression=compression)
            self.patch_headers(subject.DTBO_ALIAS_MEMBER, crc=0)
            with self.subTest(compression=compression), self.assertRaises(subject.ArchiveCopyError):
                self.inspect_dtbo()
        self.write_zip(compression=zipfile.ZIP_DEFLATED)
        self.patch_deflate_payload(subject.DTBO_ALIAS_MEMBER, lambda data: data + b"trailing")
        with self.assertRaisesRegex(subject.ArchiveCopyError, "DEFLATE"):
            self.inspect_dtbo()
        self.write_zip(custom={subject.DTBO_ALIAS_MEMBER: {"external_attr": (stat.S_IFLNK | 0o777) << 16}})
        with self.assertRaisesRegex(subject.ArchiveCopyError, "regular"):
            self.inspect_dtbo()
        for name in (subject.DTBO_ALIAS_MEMBER, "prebuilt_images/dtbo.img", "PREBUILT_IMAGES/../dtbo.img"):
            self.write_zip()
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                with zipfile.ZipFile(self.source, "a") as archive:
                    archive.writestr(name, b"invalid member")
            with self.subTest(name=name), self.assertRaises(subject.ArchiveCopyError):
                self.inspect_dtbo()

    def test_dtbo_inspection_and_copy_detect_same_byte_source_rebinding_before_output(self):
        replacements = self.add_dtbo_pair()
        self.write_zip()
        proof = self.inspect_dtbo()
        real = subject._inspect_dtbo_members
        def rebind(*args):
            result = real(*args)
            alternate = self.root / "source-rebind.zip"
            alternate.write_bytes(self.source.read_bytes())
            alternate.replace(self.source)
            return result
        for copying in (False, True):
            with self.subTest(copying=copying), mock.patch.object(subject, "_inspect_dtbo_members", side_effect=rebind):
                with self.assertRaisesRegex(subject.ArchiveCopyError, "pathname/inode"):
                    if copying:
                        self.run_copy(replacements=replacements, dtbo_alias_proof=proof)
                    else:
                        self.inspect_dtbo()
            self.assertFalse(self.output.exists())

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

    def test_offset_only_zip64_promotion_preserves_local_and_central_versions(self):
        self.write_zip()
        member = "SYSTEM/etc/unchanged.txt"
        baseline = self.root / "offset-baseline.zip"
        self.run_copy(output=baseline)
        with zipfile.ZipFile(baseline) as archive:
            offset = archive.getinfo(member).header_offset
            largest = max(info.file_size for info in archive.infolist())
        # Only the offset crosses this tiny threshold, not the file-size
        # threshold or stdlib's additional 5 percent size allowance.
        self.assertLess(largest * 1.05, offset - 1)
        for offset_minus_limit, version in ((-1, 20), (0, 20), (1, 45)):
            with self.subTest(offset_minus_limit=offset_minus_limit):
                limit = offset - offset_minus_limit
                self.output = self.root / ("offset-boundary-%s.zip" % offset_minus_limit)
                with mock.patch.object(zipfile, "ZIP64_LIMIT", limit):
                    self.assert_success(self.run_copy())
                    with zipfile.ZipFile(self.output) as archive:
                        info = archive.getinfo(member)
                        self.assertEqual(info.header_offset, offset)
                        self.assertEqual(info.extract_version, version)
                        with self.output.open("rb") as stream:
                            stream.seek(info.header_offset)
                            local = struct.unpack("<4s5H3I2H", stream.read(30))
                        self.assertEqual(local[1], version)
                        self.assertEqual(local[2] & 8, 0)

    def streaming_zip64_headers(self, *, size=0x100000007, signed=True, local_zip64=False):
        """Tiny span-only fixture; no valid large payload is generated or decoded."""
        name, payload, crc = b"IMAGES/odm.img", b"x", 0x12345678
        local_extra = extra(1, struct.pack("<QQ", 0, 0)) if local_zip64 else b""
        placeholder = 0xffffffff if local_zip64 else 0
        local = struct.pack("<4s5H3I2H", b"PK\x03\x04", 20, 8, zipfile.ZIP_DEFLATED,
                            0, 33, 0, placeholder, placeholder, len(name), len(local_extra))
        fmt = "<IQQ" if local_zip64 or size > 0xffffffff else "<III"
        descriptor = (b"PK\x07\x08" if signed else b"") + struct.pack(fmt, crc, len(payload), size)
        central_extra = extra(1, struct.pack("<QQQ", size, len(payload), 0))
        central = struct.pack("<4s6H3I5H2I", b"PK\x01\x02", 20, 45, 8,
                              zipfile.ZIP_DEFLATED, 0, 33, crc, 0xffffffff, 0xffffffff,
                              len(name), len(central_extra), 0, 0, 0, 0, 0)
        prefix = local + name + local_extra + payload + descriptor
        directory = central + name + central_extra
        end = struct.pack("<4s4H2IH", b"PK\x05\x06", 0, 0, 1, 1,
                          len(directory), len(prefix), 0)
        return bytearray(prefix + directory + end)

    def test_streaming_zip64_version_upgrade_preserves_span_and_output_bound(self):
        for signed in (False, True):
            with self.subTest(signed=signed):
                raw = self.streaming_zip64_headers(signed=signed)
                self.assertLess(len(raw), 256)
                with zipfile.ZipFile(io.BytesIO(raw)) as archive:
                    info = archive.getinfo("IMAGES/odm.img")
                    following = archive.start_dir
                    self.assertEqual(subject._span(archive, info, following),
                                     (30 + len(info.filename), info.filename.encode(), b""))
                    bound = subject._output_bound(archive, {info.filename: info}, {0: following}, {})
                    self.assertGreater(bound, info.file_size)

    def test_streaming_zip64_version_upgrade_rejects_other_header_shapes(self):
        for field in ("local_version", "central_version", "reserved", "small_size",
                      "local_zip64", "crc", "compressed_size", "flags", "method"):
            raw = self.streaming_zip64_headers(size=7 if field == "small_size" else 0x100000007,
                                               local_zip64=field == "local_zip64")
            central = self.central_entries(raw)["IMAGES/odm.img"][0]
            if field == "local_version":
                struct.pack_into("<H", raw, 4, 21)
            elif field in ("central_version", "reserved"):
                struct.pack_into("<H", raw, central + 6, 46 if field == "central_version" else 45 | 0x100)
            elif field == "crc":
                struct.pack_into("<I", raw, 14, 0x12345678)
            elif field == "compressed_size":
                struct.pack_into("<I", raw, 18, 1)
            elif field in ("flags", "method"):
                local_offset, central_offset = (6, 8) if field == "flags" else (8, 10)
                struct.pack_into("<H", raw, local_offset, 0)
                struct.pack_into("<H", raw, central + central_offset, 0)
            with self.subTest(field=field), zipfile.ZipFile(io.BytesIO(raw)) as archive:
                with self.assertRaises(ValueError):
                    subject._span(archive, archive.getinfo("IMAGES/odm.img"), archive.start_dir)

    def test_streaming_zip64_version_upgrade_keeps_descriptor_and_overlap_checks(self):
        for field in ("signature", "crc", "compressed_size", "file_size", "descriptor_boundary", "data_boundary"):
            raw = self.streaming_zip64_headers()
            descriptor = 30 + len(b"IMAGES/odm.img") + 1
            if field in ("signature", "crc", "compressed_size", "file_size"):
                offset = {"signature": 0, "crc": 4, "compressed_size": 8, "file_size": 16}[field]
                raw[descriptor + offset] ^= 1
            with self.subTest(field=field), zipfile.ZipFile(io.BytesIO(raw)) as archive:
                following = archive.start_dir
                if field == "descriptor_boundary":
                    following -= 1
                elif field == "data_boundary":
                    following = descriptor - 1
                with self.assertRaises(ValueError):
                    subject._span(archive, archive.getinfo("IMAGES/odm.img"), following)

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
