"""Offline working76 tests with synthetic newc/AVB bytes and mocked native tools.

The fixture key, PEM, signature, tool files and image are deliberately invalid
for real use. Native success in these tests checks orchestration, not RSA,
compression, hardware behavior or the proprietary recovery contents.
"""

from contextlib import ExitStack, redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import twrp_working as working


PATCH_PATH = "recovery/twrp-working/0001-permissive-and-no-vibration-defaults.patch"
INIT_PATH = "system/etc/init/hw/init.rc"
UI_PATH = "twres/ui.xml"
PUBLIC_PEM = (b"-----BEGIN PUBLIC KEY-----\nSYNTHETIC, NOT A VALID KEY\n"
              b"-----END PUBLIC KEY-----\n")
FAKE_PRIVATE = b"synthetic fixture marker, not a private key\n"
FAKE_AVB_KEY = struct.pack(">II", 4096, 0) + bytes(1024)


def _sha(data):
    return hashlib.sha256(data).hexdigest()


def _identity(data):
    return {"sha256": _sha(data), "size_bytes": len(data)}


def _pad(data, alignment=4096):
    return data + bytes(-len(data) % alignment)


def _blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest().encode()


def _entry(name, data=b"", *, mode=stat.S_IFREG | 0o640, nlink=1, uid=0, gid=0):
    raw = name.encode() + b"\0"
    fields = (17, mode, uid, gid, nlink, 1234, len(data), 2, 3, 0, 0, len(raw), 0)
    header = b"070701" + b"".join(f"{value:08x}".encode() for value in fields) + raw
    return _pad(header, 4) + _pad(data, 4)


def _cpio(contents, *, opaque=b"\0opaque fixture\xff", init_uid=12, extra=b""):
    directories = (".", "system", "system/etc", "system/etc/init", "system/etc/init/hw", "twres")
    prefix = b"".join(_entry(name, mode=stat.S_IFDIR | 0o755, nlink=2) for name in directories)
    keep = _entry("opaque", opaque)
    keep = keep[:110].upper() + keep[110:]  # Preserve raw header spelling too.
    return (prefix + _entry(INIT_PATH, contents[INIT_PATH], uid=init_uid, gid=34) + keep
            + _entry(UI_PATH, contents[UI_PATH])
            + _entry("link", b"opaque", mode=stat.S_IFLNK | 0o777)
            + extra + _entry("TRAILER!!!", mode=0o755) + bytes(44))


def _synthetic_patch(public_patch):
    """Retain public hunk text; replace full-index hashes for invented files."""
    sections, before, after = [], {}, {}
    for chunk in public_patch.split(b"diff --git ")[1:]:
        lines = (b"diff --git " + chunk).splitlines(keepends=True)
        name = lines[0].split()[2][2:].decode("ascii")
        hunk = re.fullmatch(rb"@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", lines[4])
        if hunk is None:
            raise AssertionError("public patch fixture requires one additive hunk per file")
        prefix = b"synthetic padding line\n" * (int(hunk[1]) - 1)
        suffix = b"untouched synthetic suffix\n"
        before[name] = prefix + b"".join(line[1:] for line in lines[5:] if line[:1] == b" ") + suffix
        after[name] = prefix + b"".join(line[1:] for line in lines[5:]) + suffix
        lines[1] = b"index " + _blob(before[name]) + b".." + _blob(after[name]) + b"\n"
        sections.append(b"".join(lines))
    return b"".join(sections), before, after


def _legacy_literals(data):
    length = len(data)
    block = bytes((min(length, 15) << 4,))
    if length >= 15:
        quotient, remainder = divmod(length - 15, 255)
        block += bytes((255,)) * quotient + bytes((remainder,))
    block += data
    return b"\x02\x21\x4c\x18" + struct.pack("<I", len(block)) + block


def _unsigned(ramdisk, os_version):
    header = bytearray(4096)
    struct.pack_into("<8s9I", header, 0, b"ANDROID!", 0, len(ramdisk), os_version, 1584, 0, 0, 0, 0, 4)
    return bytes(header) + _pad(ramdisk)


def _property(key, value):
    key, value = key.encode("ascii"), value.encode("ascii")
    payload = _pad(struct.pack(">QQ", len(key), len(value)) + key + b"\0" + value + b"\0", 8)
    return struct.pack(">QQ", 0, len(payload)) + payload


def _stale_baseline_footer(unsigned):
    """Algorithm NONE AVB envelope with an intentionally stale recovery digest."""
    name, salt, stale_digest = b"recovery", b"b" * 32, b"Z" * 32
    hash_size = (132 + len(name) + len(salt) + len(stale_digest) + 7) // 8 * 8
    descriptor = struct.pack(">QQQ32sIIII60s", 2, hash_size - 16, len(unsigned), b"sha256",
                             len(name), len(salt), len(stale_digest), 0, bytes(60))
    descriptors = _pad(descriptor + name + salt + stale_digest, 8)
    auxiliary = _pad(descriptors, 64)
    header = bytearray(256)
    struct.pack_into(">4sIIQQI", header, 0, b"AVB0", 1, 0, 0, len(auxiliary), 0)
    struct.pack_into(">10Q", header, 32, 0, 0, 0, 0, 0, 0, 0, 0, 0, len(descriptors))
    release = b"synthetic stale baseline"
    header[128:128 + len(release)] = release
    vbmeta = bytes(header) + auxiliary
    image_size = len(unsigned) + len(_pad(vbmeta)) + 4096
    footer = struct.pack(">4sIIQQQ28s", b"AVBf", 1, 0, len(unsigned), len(unsigned), len(vbmeta), bytes(28))
    return unsigned + vbmeta + bytes(image_size - len(unsigned) - len(vbmeta) - 64) + footer


def _signed(unsigned, profile):
    avb = profile["avb"]
    name, salt = b"recovery", b"s" * 32
    digest = hashlib.sha256(salt + unsigned).digest()
    hash_size = (132 + len(name) + len(salt) + len(digest) + 7) // 8 * 8
    descriptor = struct.pack(">QQQ32sIIII60s", 2, hash_size - 16, len(unsigned), b"sha256",
                             len(name), len(salt), len(digest), 0, bytes(60))
    descriptors = _pad(descriptor + name + salt + digest, 8)
    property_sizes = []
    for key, value in avb["properties"].items():
        prop = _property(key, value)
        property_sizes.append(len(prop))
        descriptors += prop
    auxiliary = _pad(descriptors + FAKE_AVB_KEY, 64)
    header = bytearray(256)
    struct.pack_into(">4sIIQQI", header, 0, b"AVB0", 1, 2, 576, len(auxiliary), 2)
    struct.pack_into(">10Q", header, 32, 0, 32, 32, 512, len(descriptors), len(FAKE_AVB_KEY),
                     len(descriptors) + len(FAKE_AVB_KEY), 0, 0, len(descriptors))
    struct.pack_into(">QII", header, 112, 1, 0, 1)
    release = avb["release_string"].encode("ascii")
    header[128:128 + len(release)] = release
    authentication = hashlib.sha256(bytes(header) + auxiliary).digest() + b"S" * 512 + bytes(32)
    vbmeta = bytes(header) + authentication + auxiliary
    image_size = len(unsigned) + len(_pad(vbmeta)) + 4096
    footer = struct.pack(">4sIIQQQ28s", b"AVBf", 1, 0, len(unsigned), len(unsigned), len(vbmeta), bytes(28))
    image = unsigned + vbmeta + bytes(image_size - len(unsigned) - len(vbmeta) - 64) + footer
    avb.update(partition_size_bytes=image_size, salt_hex=salt.hex(), digest_hex=digest.hex(),
               public_key_sha256=_sha(FAKE_AVB_KEY), public_key_size_bytes=len(FAKE_AVB_KEY),
               vbmeta_size_bytes=len(vbmeta))
    return image, {"vbmeta": len(unsigned), "auth": len(unsigned) + 256,
                   "aux": len(unsigned) + 832, "vbmeta_size": len(vbmeta),
                   "hash_size": hash_size, "desc_size": len(descriptors),
                   "property_sizes": property_sizes}


def _mutate(data, offset, value, fmt=None):
    changed = bytearray(data)
    if fmt:
        struct.pack_into(fmt, changed, offset, value)
    else:
        changed[offset:offset + len(value)] = value
    return bytes(changed)


def _rehash_auth(data, offsets):
    v, a = offsets["vbmeta"], offsets["aux"]
    digest = hashlib.sha256(data[v:v + 256] + data[a:v + offsets["vbmeta_size"]]).digest()
    return _mutate(data, offsets["auth"], digest)


class Fixture:
    def __init__(self):
        self.profile = json.loads((ROOT / "config/twrp-working.json").read_text())
        self.patch, self.before, self.after = _synthetic_patch((ROOT / PATCH_PATH).read_bytes())
        self.cpio, self.changed = _cpio(self.before), _cpio(self.after)
        self.baseline_ramdisk = _legacy_literals(self.cpio)
        self.ramdisk = _legacy_literals(self.changed)
        self.baseline_payload = _unsigned(self.baseline_ramdisk, self.profile["boot"]["os_version_raw"])
        self.baseline = _stale_baseline_footer(self.baseline_payload)
        self.unsigned = _unsigned(self.ramdisk, self.profile["boot"]["os_version_raw"])
        self.image, self.offsets = _signed(self.unsigned, self.profile)
        self.profile["baseline"].update(image=_identity(self.baseline), cpio=_identity(self.cpio), archive_entries=10)
        self.profile["output"].update(image=_identity(self.image), cpio=_identity(self.changed),
                                      ramdisk=_identity(self.ramdisk), unsigned_size_bytes=len(self.unsigned))
        self.profile["patch"].update(_identity(self.patch))
        self.profile["patch"]["files"] = {
            name: {"before_sha256": _sha(self.before[name]), "after_sha256": _sha(self.after[name])}
            for name in self.before}
        self.tool_bytes = {name: ("synthetic " + name + ", never execute\n").encode()
                           for name in ("mkbootimg", "avbtool", "lz4", "openssl")}
        self.companion = b"synthetic mkbootimg companion, never import\n"
        for name in ("mkbootimg", "avbtool", "lz4"):
            self.profile["tools"][name].update(_identity(self.tool_bytes[name]))
        self.profile["tools"]["mkbootimg"]["companion"].update(_identity(self.companion))
        self.profile["tools"]["openssl"]["binaries"] = [{
            "platform": "synthetic", "version": "not executable", "build_allowed": True,
            **_identity(self.tool_bytes["openssl"])}]
        self.profile_sha = _sha(json.dumps(self.profile, sort_keys=True).encode())


class NoNativeTests(unittest.TestCase):
    def setUp(self):
        self.guards = ExitStack()
        self.addCleanup(self.guards.close)
        for target in ("subprocess.run", "subprocess.Popen", "os.system", "os.kill", "os.killpg", "socket.socket"):
            self.guards.enter_context(mock.patch(target, side_effect=AssertionError("unmocked native/network call")))


class WorkingProfileTests(NoNativeTests):
    def test_public_profile_pins_working76_not_a_new_source_build(self):
        profile, digest = working.load_profile()
        self.assertEqual(digest, _sha((ROOT / "config/twrp-working.json").read_bytes()))
        self.assertEqual(profile["profile_id"], "nezha-working76")
        self.assertIs(profile["source_built"], False)
        self.assertEqual(profile["baseline"]["image"], {
            "size_bytes": 104857600, "sha256": "56029c8109e3ff1bcbb69ef38e8ae36355713340482d9f77405cdf6009bcd323"})
        self.assertEqual(profile["output"]["image"], {
            "size_bytes": 104857600, "sha256": "a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e"})
        self.assertEqual(profile["baseline"]["archive_entries"], 4210)
        self.assertEqual(profile["patch"]["path"], PATCH_PATH)
        patch = (ROOT / PATCH_PATH).read_bytes()
        self.assertEqual({key: profile["patch"][key] for key in ("sha256", "size_bytes")}, _identity(patch))
        self.assertEqual(set(profile["patch"]["files"]), {INIT_PATH, UI_PATH})
        self.assertEqual((profile["boot"]["header_version"], profile["boot"]["kernel_size_bytes"]), (4, 0))
        self.assertEqual((profile["avb"]["partition_name"], profile["avb"]["flags"],
                          profile["avb"]["rollback_index"], profile["avb"]["rollback_index_location"]),
                         ("recovery", 0, 1, 1))
        self.assertFalse(profile["avb"]["oem_trust_established"])
        self.assertEqual(profile["avb"]["salt_hex"], "00b772af29811562406dbb27c9dcbb360f2974efb7bb945d22ad80e7f6876f66")
        self.assertTrue(any(row["build_allowed"] for row in profile["tools"]["openssl"]["binaries"]))
        self.assertTrue(any(not row["build_allowed"] for row in profile["tools"]["openssl"]["binaries"]))

    def test_plan_reads_only_public_profile_and_patch_without_native_work(self):
        read = working._read
        seen = []

        def public_only(path, *args, **kwargs):
            path = Path(path)
            self.assertIn(path, {ROOT / "config/twrp-working.json", ROOT / PATCH_PATH})
            seen.append(path)
            return read(path, *args, **kwargs)

        with mock.patch.object(working, "_read", side_effect=public_only), \
                mock.patch.object(working, "load_local_config", side_effect=AssertionError("private defaults read")), \
                mock.patch.object(working, "_run", side_effect=AssertionError("native tool invoked")):
            report = working.plan()
        self.assertEqual(seen, [ROOT / "config/twrp-working.json", ROOT / PATCH_PATH])
        self.assertEqual(report["status"], "planned")
        self.assertFalse(report["native_commands_run"])
        self.assertFalse(report["source_built"])
        self.assertEqual(report["device_operations"], [])

    def test_unsupported_profile_identity_patch_path_and_contract_are_rejected(self):
        original, _ = working.load_profile()
        cases = (("schema_version", 2), ("schema_version", True), ("profile_id", "other-phone"), ("source_built", True))
        profiles = []
        for key, value in cases:
            changed = deepcopy(original)
            changed[key] = value
            profiles.append(changed)
        for section, key, value in (("patch", "path", "../private"), ("boot", "kernel_size_bytes", 1),
                                     ("boot", "header_version", 3), ("avb", "partition_name", "boot"),
                                     ("avb", "flags", 1), ("avb", "rollback_index", 0)):
            changed = deepcopy(original)
            changed[section][key] = value
            profiles.append(changed)
        changed = deepcopy(original)
        changed["patch"]["files"]["third-file"] = {}
        profiles.append(changed)
        for index, changed in enumerate(profiles):
            with self.subTest(index=index), mock.patch.object(working, "_read", return_value=json.dumps(changed).encode()), \
                    self.assertRaises(working.TwrpWorkingError):
                working.load_profile()


class WorkingImageTests(NoNativeTests):
    def setUp(self):
        super().setUp()
        self.fx = Fixture()

    def parse(self, image=None, *, repin=False):
        data = self.fx.image if image is None else image
        profile = deepcopy(self.fx.profile)
        if repin:
            profile["output"]["image"] = _identity(data)
        return working.inspect_image_bytes(data, profile)

    def reject_rehashed(self, image, pattern=None):
        image = _rehash_auth(image, self.fx.offsets)
        with self.assertRaisesRegex(ValueError, pattern or ".+"):
            self.parse(image, repin=True)

    def test_synthetic_image_reports_only_structure_without_signature_or_hardware_claim(self):
        result = self.parse()
        self.assertEqual(result, {"header_version": 4, "kernel_size_bytes": 0,
                                  "header_size_bytes": 1584, "page_size_bytes": 4096,
                                  "command_line": "", "os_version_raw": self.fx.profile["boot"]["os_version_raw"],
                                  "ramdisk_size_bytes": len(self.fx.ramdisk),
                                  "unsigned_size_bytes": len(self.fx.unsigned)})
        self.assertNotIn("signature_verified", result)
        self.assertNotIn("hardware_verified", result)
        self.assertLess(len(self.fx.image), 64 * 1024)

    def test_exact_output_identity_is_required_before_structural_checks(self):
        for image in (self.fx.image + b"\0", self.fx.image[:-1], _mutate(self.fx.image, 0, b"X")):
            with self.subTest(size=len(image)), self.assertRaisesRegex(working.TwrpWorkingError, "working image SHA256"):
                self.parse(image)
        profile = deepcopy(self.fx.profile)
        profile["output"]["image"]["size_bytes"] += 1
        with self.assertRaisesRegex(working.TwrpWorkingError, "working image size"):
            working.inspect_image_bytes(self.fx.image, profile)

    def test_pure_parser_does_not_access_files_clock_process_or_network(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("pure parser side effect")))
            self.assertEqual(self.parse(), self.parse())

    def test_header_kernel_cmdline_os_signature_and_padding_are_rejected_after_repin(self):
        mutations = ((8, 1, "<I"), (16, 0, "<I"), (20, 1580, "<I"), (24, b"x", None),
                     (40, 3, "<I"), (44, b"x", None), (1580, 1, "<I"), (1584, b"x", None),
                     (4096 + len(self.fx.ramdisk), b"x", None))
        for offset, value, fmt in mutations:
            with self.subTest(offset=offset), self.assertRaises(ValueError):
                self.parse(_mutate(self.fx.image, offset, value, fmt), repin=True)

    def test_ramdisk_identity_cannot_be_bypassed_by_repinning_the_image(self):
        with self.assertRaisesRegex(working.TwrpWorkingError, "compressed ramdisk differs"):
            self.parse(_mutate(self.fx.image, 4105, b"x"), repin=True)

    def test_avb_algorithm_flags_rollback_and_version_cannot_be_rehashed_away(self):
        v = self.fx.offsets["vbmeta"]
        for offset, value, fmt in ((8, 0, ">I"), (28, 1, ">I"), (112, 2, ">Q"),
                                   (120, 1, ">I"), (124, 0, ">I")):
            with self.subTest(offset=offset):
                self.reject_rehashed(_mutate(self.fx.image, v + offset, value, fmt), "unexpected AVB")

    def test_avb_authentication_layout_release_and_padding_are_exact(self):
        v, auth, aux = (self.fx.offsets[name] for name in ("vbmeta", "auth", "aux"))
        for offset, value in ((32, 1), (40, 31), (48, 33), (56, 511), (64, 0), (72, 1031), (88, 1), (96, 8)):
            with self.subTest(offset=offset):
                self.reject_rehashed(_mutate(self.fx.image, v + offset, value, ">Q"))
        for offset in (v + 128, auth + 544):
            with self.subTest(offset=offset):
                self.reject_rehashed(_mutate(self.fx.image, offset, b"x"), "release string|block padding")
        with self.assertRaisesRegex(working.TwrpWorkingError, "authentication hash differs"):
            self.parse(_mutate(self.fx.image, auth, b"x"), repin=True)
        self.assertEqual(aux, auth + 576)

    def test_wrong_key_rejected_after_recomputing_authentication_and_image_hashes(self):
        key = self.fx.offsets["aux"] + self.fx.offsets["desc_size"]
        for offset, value, fmt in ((key, 2048, ">I"), (key + 10, b"x", None)):
            with self.subTest(offset=offset):
                self.reject_rehashed(_mutate(self.fx.image, offset, value, fmt), "embedded AVB public key differs")

    def test_wrong_salt_rejected_even_with_its_valid_payload_and_authentication_hashes(self):
        start = self.fx.offsets["aux"] + 132 + len(b"recovery")
        salt = b"n" * 32
        image = _mutate(self.fx.image, start, salt)
        image = _mutate(image, start + 32, hashlib.sha256(salt + self.fx.unsigned).digest())
        self.reject_rehashed(image, "salt/digest differs")

    def test_hash_descriptor_semantics_cannot_be_rehashed_away(self):
        a = self.fx.offsets["aux"]
        cases = ((0, 1, ">Q"), (16, len(self.fx.unsigned) - 1, ">Q"),
                 (24, b"sha512", None), (56, 7, ">I"), (60, 31, ">I"), (64, 31, ">I"),
                 (68, 1, ">I"), (72, b"x", None), (132, b"boot____", None),
                 (self.fx.offsets["hash_size"] - 1, b"x", None))
        for offset, value, fmt in cases:
            with self.subTest(offset=offset):
                self.reject_rehashed(_mutate(self.fx.image, a + offset, value, fmt), "descriptor")

    def test_property_values_terminators_and_tags_are_exact_after_rehash(self):
        first = self.fx.offsets["aux"] + self.fx.offsets["hash_size"]
        key = next(iter(self.fx.profile["avb"]["properties"]))
        value_at = first + 32 + len(key) + 1
        for offset, value, fmt in ((first, 99, ">Q"), (first + 16, 0, ">Q"),
                                   (first + 32 + len(key), b"x", None), (value_at, b"15", None),
                                   (first + self.fx.offsets["property_sizes"][0] - 1, b"x", None)):
            with self.subTest(offset=offset):
                self.reject_rehashed(_mutate(self.fx.image, offset, value, fmt), "descriptor|property")

    def test_signature_semantics_are_reserved_for_native_verification(self):
        changed = _mutate(self.fx.image, self.fx.offsets["auth"] + 32, b"X")
        self.assertEqual(self.parse(changed, repin=True), self.parse())


class WorkingPatchTests(NoNativeTests):
    def setUp(self):
        super().setUp()
        self.fx = Fixture()

    def patch(self, data, *, cpio=None, repin=False):
        profile = deepcopy(self.fx.profile)
        if repin:
            profile["patch"].update(_identity(data))
        return working._patch_files(self.fx.cpio if cpio is None else cpio, data, profile)

    def test_public_additive_hunks_replay_and_preserve_all_other_archive_frames(self):
        changes = self.patch(self.fx.patch)
        self.assertEqual(changes, {name: (self.fx.before[name], self.fx.after[name]) for name in self.fx.before})
        changed = working.replace_files(self.fx.cpio, changes)
        self.assertEqual(changed, self.fx.changed)
        self.assertEqual(working._overlay_proof(self.fx.cpio, changed, changes, 10), {
            "entry_count": 10, "unchanged_members": 8,
            "all_other_member_payloads_and_metadata_unchanged": True})
        self.assertIn(b"write /sys/fs/selinux/enforce 0", changes[INIT_PATH][1])
        for name in (b"tw_action_vibrate", b"tw_button_vibrate", b"tw_keyboard_vibrate"):
            self.assertIn(b'name="' + name + b'" value="0"', changes[UI_PATH][1])

    def test_patch_pin_preimage_postimage_and_full_git_indices_are_enforced(self):
        with self.assertRaisesRegex(working.TwrpWorkingError, "public patch SHA256"):
            self.patch(self.fx.patch + b"\n")
        contents = dict(self.fx.before)
        contents[INIT_PATH] += b"unexpected\n"
        with self.assertRaisesRegex(working.TwrpWorkingError, "preimage differs"):
            self.patch(self.fx.patch, cpio=_cpio(contents))
        bad_index = self.fx.patch.replace(_blob(self.fx.before[INIT_PATH]), b"0" * 40, 1)
        with self.assertRaisesRegex(working.TwrpWorkingError, "Git blob differs"):
            self.patch(bad_index, repin=True)
        profile = deepcopy(self.fx.profile)
        profile["patch"]["files"][INIT_PATH]["after_sha256"] = "0" * 64
        with self.assertRaisesRegex(working.TwrpWorkingError, "postimage differs"):
            working._patch_files(self.fx.cpio, self.fx.patch, profile)

    def test_patch_context_shape_duplicates_missing_and_unsafe_paths_are_rejected(self):
        sections = self.fx.patch.split(b"diff --git ")[1:]
        bad_cases = (b"prefix\n" + self.fx.patch,
                     self.fx.patch.replace(b" on early-init\n", b" on wrong-init\n", 1),
                     self.fx.patch.replace(b"+    write", b"-    write", 1),
                     self.fx.patch.replace(b"@@ -6,6 +6,9 @@", b"@@ -6,6 +7,9 @@", 1),
                     self.fx.patch.replace(INIT_PATH.encode(), b"../../escape"),
                     self.fx.patch + b"diff --git " + sections[0],
                     b"diff --git " + sections[0])
        for index, patch in enumerate(bad_cases):
            with self.subTest(index=index), self.assertRaises(working.TwrpWorkingError):
                self.patch(patch, repin=True)

    def test_traversing_cpio_names_are_rejected_without_extraction(self):
        bad = _cpio(self.fx.before, extra=_entry("../escape", b"no"))
        with self.assertRaises(ValueError):
            self.patch(self.fx.patch, cpio=bad)

    def test_overlay_proof_rejects_unselected_bytes_metadata_membership_and_trailer_changes(self):
        cases = (_cpio(self.fx.after, opaque=b"different data"), _cpio(self.fx.after, init_uid=13),
                 _cpio(self.fx.after, extra=_entry("extra", b"no")))
        trailer_at = self.fx.changed.index(b"TRAILER!!!\0") - 110
        cases += (_mutate(self.fx.changed, trailer_at + 6, b"00000042"),)
        for index, changed in enumerate(cases):
            with self.subTest(index=index), self.assertRaises(working.TwrpWorkingError):
                working._overlay_proof(self.fx.cpio, changed, self.fx.before, 10)
        with self.assertRaisesRegex(working.TwrpWorkingError, "membership/order changed"):
            working._overlay_proof(self.fx.cpio, self.fx.changed, self.fx.before, 11)

    def test_patch_and_overlay_pure_helpers_have_no_side_effects(self):
        with ExitStack() as stack:
            for target in ("builtins.open", "io.open", "os.open", "time.time"):
                stack.enter_context(mock.patch(target, side_effect=AssertionError("patch side effect")))
            changes = self.patch(self.fx.patch)
            changed = working.replace_files(self.fx.cpio, changes)
            proof = working._overlay_proof(self.fx.cpio, changed, changes, 10)
        self.assertTrue(proof["all_other_member_payloads_and_metadata_unchanged"])


class WorkingHostTests(NoNativeTests):
    def setUp(self):
        super().setUp()
        self.fx = Fixture()
        temporary = tempfile.TemporaryDirectory(prefix="working76-offline-tests-")
        self.addCleanup(temporary.cleanup)
        self.host = Path(temporary.name).resolve()
        self.inputs, self.tools = self.host / "inputs", self.host / "tool-source"
        self.inputs.mkdir(mode=0o700)
        self.tools.mkdir(mode=0o700)
        self.paths = {name: self.inputs / name for name in ("baseline_image", "key", "public_key", "image")}
        for name, data in (("baseline_image", self.fx.baseline), ("key", FAKE_PRIVATE),
                           ("public_key", PUBLIC_PEM), ("image", self.fx.image)):
            self.paths[name].write_bytes(data)
            self.paths[name].chmod(0o600)
        for name, data in self.fx.tool_bytes.items():
            self.paths[name] = self.tools / name
            self.paths[name].write_bytes(data)
            self.paths[name].chmod(0o700)
        self.companion = self.tools / self.fx.profile["tools"]["mkbootimg"]["companion"]["path"]
        self.companion.parent.mkdir(mode=0o700)
        self.companion.write_bytes(self.fx.companion)
        self.companion.chmod(0o600)
        self.public_patch = self.host / PATCH_PATH
        self.public_patch.parent.mkdir(parents=True, mode=0o700)
        self.public_patch.write_bytes(self.fx.patch)
        self.public_patch.chmod(0o600)
        self.out = self.host / "output"
        self.calls, self.native_hook, self.file_limits = [], None, {}
        self.guards.enter_context(mock.patch.object(working, "ROOT", self.host))
        self.profile_loader = self.guards.enter_context(mock.patch.object(
            working, "load_profile", side_effect=lambda: (self.fx.profile, self.fx.profile_sha)))
        self.runner = self.guards.enter_context(mock.patch.object(working, "_run", side_effect=self.native))

    def native(self, label, argv, env, work, records, *, max_file_bytes=working.MAX_IMAGE):
        """Only synthesize stage outputs; never execute or parse a private key."""
        argv = [str(value) for value in argv]
        self.calls.append((label, argv, dict(env), Path(work)))
        self.file_limits[label] = max_file_bytes
        self.assertNotIn("adb", argv)
        self.assertNotIn("fastboot", argv)
        self.assertEqual(env["OPENSSL_CONF"], "/dev/null")
        self.assertEqual(env["LC_ALL"], "C")
        self.assertTrue(Path(work).is_dir())

        def argument(flag):
            return Path(argv[argv.index(flag) + 1])

        if label in ("derive-public-key", "public-key-parse"):
            argument("-out").write_bytes(PUBLIC_PEM)
        elif label in ("export-public-key", "public-key-export"):
            argument("--output").write_bytes(FAKE_AVB_KEY)
        elif label == "decompress-baseline":
            self.assertEqual(Path(argv[-2]).read_bytes(), self.fx.baseline_ramdisk)
            Path(argv[-1]).write_bytes(self.fx.cpio)
        elif label == "compress":
            self.assertEqual(argv[1:4], ["-l", "-12", "--favor-decSpeed"])
            self.assertEqual(Path(argv[-2]).read_bytes(), self.fx.changed)
            Path(argv[-1]).write_bytes(self.fx.ramdisk)
        elif label == "compression-roundtrip":
            self.assertEqual(Path(argv[-2]).read_bytes(), self.fx.ramdisk)
            Path(argv[-1]).write_bytes(self.fx.changed)
        elif label == "mkbootimg":
            self.assertEqual(argv[:4], [sys.executable, "-B", "-E", "-s"])
            self.assertNotIn("--kernel", argv)
            self.assertNotIn("--dtb", argv)
            self.assertEqual(argument("--ramdisk").read_bytes(), self.fx.ramdisk)
            argument("--output").write_bytes(self.fx.unsigned)
        elif label == "avb-sign":
            self.assertEqual(argument("--image").read_bytes(), self.fx.unsigned)
            argument("--image").write_bytes(self.fx.image)
        elif label == "avb-verify":
            self.assertEqual(argument("--image").read_bytes(), self.fx.image)
            self.assertEqual(argument("--key").read_bytes(), PUBLIC_PEM)
        else:
            self.fail("unexpected mocked native stage: " + label)
        records.append({"step": label, "returncode": 0,
                        "stdout": _identity(b"synthetic stdout"), "stderr": _identity(b"")})
        if self.native_hook:
            self.native_hook(label, argv, Path(work))

    def build(self, **overrides):
        values = {name: self.paths[name] for name in
                  ("baseline_image", "key", "mkbootimg", "avbtool", "lz4", "openssl")}
        values["output_dir"] = self.out
        values.update(overrides)
        return working.build_recovery(**values)

    def verify(self, **overrides):
        values = {name: self.paths[name] for name in ("avbtool", "public_key", "openssl")}
        image = overrides.pop("image", self.paths["image"])
        values.update(overrides)
        return working.verify_image(image, **values)

    def test_full_mocked_build_roundtrip_verification_receipts_and_private_outputs(self):
        inputs = {name: path.read_bytes() for name, path in self.paths.items()}
        report = self.build()
        expected = ["derive-public-key", "export-public-key", "decompress-baseline", "compress",
                    "compression-roundtrip", "mkbootimg", "avb-sign",
                    "public-key-parse", "public-key-export", "avb-verify"]
        self.assertEqual([call[0] for call in self.calls], expected)
        self.assertEqual(report["status"], "built_and_verified")
        self.assertEqual(report["image"], _identity(self.fx.image))
        self.assertEqual(report["cpio"], _identity(self.fx.changed))
        self.assertEqual(report["archive"]["unchanged_members"], 8)
        self.assertFalse(report["source_built"])
        self.assertEqual(report["device_operations"], [])
        self.assertEqual(self.file_limits["decompress-baseline"], len(self.fx.cpio))
        self.assertEqual(self.file_limits["compression-roundtrip"], len(self.fx.changed))
        self.assertTrue(report["verification"]["avb"]["signature_verified"])
        self.assertFalse(report["verification"]["avb"]["oem_trust_established"])
        self.assertEqual(json.loads((self.out / "build-report.json").read_text()), report)
        self.assertEqual(json.loads((self.out / "verification-report.json").read_text()), report["verification"])
        self.assertEqual((self.out / "SHA256SUMS").read_text(), _sha(self.fx.image) + "  recovery.img\n")
        self.assertEqual((self.out / "recovery.img").read_bytes(), self.fx.image)
        for name, path in self.paths.items():
            self.assertEqual(path.read_bytes(), inputs[name], name)
        for path in (self.out, *self.out.rglob("*")):
            self.assertEqual(path.lstat().st_mode & 0o077, 0, str(path))
            if path.is_file():
                self.assertNotEqual(path.read_bytes(), FAKE_PRIVATE)
        self.assertNotIn(str(self.host), json.dumps(report))
        sign = next(call[1] for call in self.calls if call[0] == "avb-sign")
        self.assertEqual(sign[sign.index("--salt") + 1], self.fx.profile["avb"]["salt_hex"])
        self.assertEqual(sign[sign.index("--key") + 1], str(self.paths["key"]))
        self.assertEqual(sign.count("--prop"), 2)

    def test_full_mocked_verify_uses_temporary_snapshots_and_explicit_public_key(self):
        report = self.verify()
        self.assertEqual([call[0] for call in self.calls], ["public-key-parse", "public-key-export", "avb-verify"])
        self.assertEqual(report["status"], "verified")
        self.assertTrue(report["avb"]["signature_verified"])
        self.assertTrue(report["avb"]["descriptor_verified"])
        self.assertFalse(report["avb"]["oem_trust_established"])
        self.assertEqual(report["public_key"]["avb_sha256"], _sha(FAKE_AVB_KEY))
        self.assertFalse(report["source_built"])
        self.assertEqual(report["device_operations"], [])
        for _, argv, _, work in self.calls:
            self.assertFalse(work.exists())
            self.assertNotIn(str(self.paths["image"]), argv)
            self.assertNotIn(str(self.paths["public_key"]), argv)
        self.assertEqual(self.paths["image"].read_bytes(), self.fx.image)

    def test_pinned_baseline_with_algorithm_none_and_stale_descriptor_builds_without_trusting_its_avb(self):
        baseline = working.envelope._inspect(memoryview(self.fx.baseline))
        avb = baseline["avb"]
        self.assertTrue(avb["footer_present"])
        self.assertEqual(avb["vbmeta"]["algorithm_type"], 0)
        self.assertEqual(avb["vbmeta"]["authentication_size_bytes"], 0)
        self.assertEqual([row["tag"] for row in avb["vbmeta"]["descriptor_headers"]], [2])
        self.assertFalse(avb["signature_verified"])
        self.assertFalse(avb["vbmeta"]["descriptor_payloads_verified"])
        descriptor = avb["vbmeta_offset_bytes"] + 256
        self.assertEqual(struct.unpack_from(">Q", self.fx.baseline, descriptor + 16)[0], len(self.fx.baseline_payload))
        salt_at = descriptor + 132 + len(b"recovery")
        salt = self.fx.baseline[salt_at:salt_at + 32]
        stored_digest = self.fx.baseline[salt_at + 32:salt_at + 64]
        self.assertEqual(stored_digest, b"Z" * 32)
        self.assertNotEqual(stored_digest, hashlib.sha256(salt + self.fx.baseline_payload).digest())
        self.assertEqual(self.fx.baseline[:len(self.fx.baseline_payload)], self.fx.baseline_payload)

        report = self.build()

        self.assertEqual(report["status"], "built_and_verified")
        self.assertEqual(report["baseline"], _identity(self.fx.baseline))
        self.assertEqual(report["verification"]["avb"]["algorithm"], "SHA256_RSA4096")
        self.assertTrue(report["verification"]["avb"]["signature_verified"])
        self.assertFalse(report["verification"]["avb"]["oem_trust_established"])
        self.assertEqual(self.paths["baseline_image"].read_bytes(), self.fx.baseline)

    def test_changed_baseline_footer_fails_the_initial_image_pin_before_header_or_native_work(self):
        changed = self.fx.baseline[:-1] + b"x"
        self.assertEqual(changed[:len(self.fx.baseline_payload)], self.fx.baseline_payload)
        self.paths["baseline_image"].write_bytes(changed)
        with mock.patch.object(working, "_header", side_effect=AssertionError("header inspected before image pin")) as header, \
                self.assertRaisesRegex(working.TwrpWorkingError, "SHA256 differs"):
            self.build()
        header.assert_not_called()
        self.runner.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_fresh_mkbootimg_output_with_any_avb_footer_is_rejected_before_signing(self):
        for index, output in enumerate((_stale_baseline_footer(self.fx.unsigned), self.fx.image)):
            self.calls.clear()
            changed = []

            def hook(label, argv, work, data=output):
                if label == "mkbootimg":
                    Path(argv[argv.index("--output") + 1]).write_bytes(data)
                    changed.append(label)

            self.native_hook = hook
            out = self.host / f"unexpected-mkbootimg-footer-{index}"
            with self.subTest(algorithm="NONE" if index == 0 else "RSA4096"), \
                    self.assertRaisesRegex(working.TwrpWorkingError, "unexpected AVB footer state"):
                self.build(output_dir=out)
            self.assertEqual(changed, ["mkbootimg"])
            self.assertEqual(self.calls[-1][0], "mkbootimg")
            self.assertNotIn("avb-sign", [call[0] for call in self.calls])
            self.assertNotIn("avb-verify", [call[0] for call in self.calls])
            self.assertFalse((out / "build-report.json").exists())

    def test_exact_output_and_baseline_mismatches_fail_before_native_operations(self):
        self.paths["image"].write_bytes(_mutate(self.fx.image, 0, b"x"))
        with self.assertRaisesRegex(working.TwrpWorkingError, "SHA256 differs"):
            self.verify()
        self.paths["baseline_image"].write_bytes(_mutate(self.fx.baseline, 0, b"x"))
        with self.assertRaisesRegex(working.TwrpWorkingError, "SHA256 differs"):
            self.build()
        self.runner.assert_not_called()
        self.assertFalse(self.out.exists())

    def test_private_or_raw_avb_key_is_not_accepted_by_verify(self):
        for data in (b"-----BEGIN PRIVATE KEY-----\nnot real\n", FAKE_AVB_KEY,
                     PUBLIC_PEM + b"PRIVATE KEY", b"not a PEM"):
            with self.subTest(kind=data[:30]):
                self.paths["public_key"].write_bytes(data)
                with self.assertRaisesRegex(working.TwrpWorkingError, "public-key"):
                    self.verify()
        self.runner.assert_not_called()

    def test_each_pinned_tool_and_companion_is_checked_before_native_operations(self):
        cases = list(self.fx.tool_bytes) + ["companion"]
        for index, name in enumerate(cases):
            path = self.companion if name == "companion" else self.paths[name]
            original = path.read_bytes()
            path.write_bytes(original + b"unexpected change")
            with self.subTest(name=name), self.assertRaises(working.TwrpWorkingError):
                self.build(output_dir=self.host / f"bad-tool-{index}")
            path.write_bytes(original)
        self.runner.assert_not_called()

    def test_openssl_verify_only_pin_cannot_be_used_for_build(self):
        self.fx.profile["tools"]["openssl"]["binaries"][0]["build_allowed"] = False
        with self.assertRaisesRegex(working.TwrpWorkingError, "unsupported OpenSSL"):
            self.build()
        self.runner.assert_not_called()
        self.assertEqual(self.verify()["status"], "verified")

    def test_selected_tool_alias_is_resolved_but_wrong_openssl_basename_is_rejected(self):
        alias = self.host / "openssl-alias"
        alias.symlink_to(self.paths["openssl"])
        self.assertEqual(self.verify(openssl=alias)["status"], "verified")
        wrong = self.host / "wrong-name"
        wrong.write_bytes(self.fx.tool_bytes["openssl"])
        wrong.chmod(0o700)
        self.calls.clear()
        with self.assertRaisesRegex(working.TwrpWorkingError, "unsupported OpenSSL"):
            self.verify(openssl=wrong)
        self.assertEqual(self.calls, [])

    def test_nonexecutable_native_tool_or_publicly_readable_private_key_is_rejected(self):
        self.paths["key"].chmod(0o644)
        with self.assertRaisesRegex(working.TwrpWorkingError, "private key must be"):
            self.build()
        self.paths["key"].chmod(0o600)
        self.paths["lz4"].chmod(0o600)
        with self.assertRaisesRegex(working.TwrpWorkingError, "lz4 is not executable"):
            self.build()
        self.runner.assert_not_called()

    def test_image_key_and_ancestor_symlinks_are_rejected_without_native_work(self):
        for name, method, argument in (("image", self.verify, "image"),
                                       ("public_key", self.verify, "public_key"),
                                       ("key", self.build, "key"),
                                       ("baseline_image", self.build, "baseline_image")):
            alias = self.host / (name + "-alias")
            alias.symlink_to(self.paths[name])
            with self.subTest(name=name), self.assertRaises(working.TwrpWorkingError):
                method(**{argument: alias})
        ancestor = self.host / "input-alias"
        ancestor.symlink_to(self.inputs, target_is_directory=True)
        with self.assertRaisesRegex(working.TwrpWorkingError, "ancestor is not a real directory"):
            self.verify(image=ancestor / "image")
        self.runner.assert_not_called()

    @unittest.skipUnless(hasattr(os, "mkfifo"), "requires POSIX FIFO support")
    def test_fifo_image_and_private_key_are_rejected_before_opening_or_blocking(self):
        fifo = self.host / "fifo"
        os.mkfifo(fifo, 0o600)
        with self.assertRaisesRegex(working.TwrpWorkingError, "not a regular file"):
            self.verify(image=fifo)
        with self.assertRaisesRegex(working.TwrpWorkingError, "private key must be"):
            self.build(key=fifo)
        self.runner.assert_not_called()

    def test_existing_output_directory_file_and_dangling_symlink_are_never_overwritten(self):
        directory, file, link = (self.host / name for name in ("existing-dir", "existing-file", "existing-link"))
        directory.mkdir()
        (directory / "sentinel").write_bytes(b"keep")
        file.write_bytes(b"keep")
        link.symlink_to(self.host / "absent-target")
        for path in (directory, file, link):
            with self.subTest(path=path.name), self.assertRaisesRegex(working.TwrpWorkingError, "already exists"):
                self.build(output_dir=path)
        self.assertEqual((directory / "sentinel").read_bytes(), b"keep")
        self.assertEqual(file.read_bytes(), b"keep")
        self.assertTrue(link.is_symlink())
        self.runner.assert_not_called()

    def test_full_mocked_build_creates_only_missing_output_ancestors_with_private_modes(self):
        existing = self.host / "existing-workspace"
        existing.mkdir(mode=0o755)
        existing.chmod(0o755)
        sentinel = existing / "sentinel"
        sentinel.write_bytes(b"preserve existing workspace")
        first, second = existing / "fresh-parent", existing / "fresh-parent/deeper"
        out = second / "build"
        self.assertFalse(first.exists())

        report = self.build(output_dir=out)

        self.assertEqual(report["status"], "built_and_verified")
        self.assertEqual((out / "recovery.img").read_bytes(), self.fx.image)
        self.assertEqual(json.loads((out / "build-report.json").read_text()), report)
        self.assertEqual(self.calls[-1][0], "avb-verify")
        for path in (first, second, out):
            self.assertTrue(path.is_dir())
            self.assertFalse(path.is_symlink())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o700)
        for path in out.rglob("*"):
            self.assertEqual(path.lstat().st_mode & 0o077, 0)
        self.assertEqual(stat.S_IMODE(existing.stat().st_mode), 0o755)
        self.assertEqual(sentinel.read_bytes(), b"preserve existing workspace")
        self.assertEqual(self.paths["baseline_image"].read_bytes(), self.fx.baseline)

    def test_missing_input_parents_remain_rejected_and_are_never_created(self):
        cases = (("baseline_image", self.build), ("key", self.build), ("image", self.verify),
                 ("public_key", self.verify), ("avbtool", self.verify), ("openssl", self.verify),
                 ("mkbootimg", self.build), ("lz4", self.build))
        missing_root = self.host / "missing-input-parents"
        for index, (name, method) in enumerate(cases):
            value = missing_root / f"case-{index}" / "input"
            overrides = {name: value}
            if name in ("baseline_image", "key", "mkbootimg", "lz4"):
                overrides["output_dir"] = self.host / f"missing-input-output-{index}"
            with self.subTest(name=name), self.assertRaises(working.TwrpWorkingError):
                method(**overrides)
            self.assertFalse(missing_root.exists())
            self.assertFalse(value.exists())
        self.runner.assert_not_called()

    def test_output_symlink_ancestors_are_rejected_even_with_missing_descendants(self):
        target = self.host / "output-link-target"
        target.mkdir()
        sentinel = target / "sentinel"
        sentinel.write_bytes(b"do not modify target")
        alias = self.host / "output-parent-alias"
        alias.symlink_to(target, target_is_directory=True)
        absent_target = self.host / "absent-output-link-target"
        dangling = self.host / "dangling-output-parent"
        dangling.symlink_to(absent_target, target_is_directory=True)
        for ancestor in (alias, dangling):
            for suffix in ("build", "missing/deeper/build"):
                with self.subTest(ancestor=ancestor.name, suffix=suffix), self.assertRaises(working.TwrpWorkingError):
                    self.build(output_dir=ancestor / suffix)
        self.assertEqual(list(target.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_bytes(), b"do not modify target")
        self.assertFalse(absent_target.exists())
        self.assertTrue(alias.is_symlink())
        self.assertTrue(dangling.is_symlink())
        self.runner.assert_not_called()

    def test_output_file_ancestors_are_rejected_even_with_missing_descendants(self):
        ancestor = self.host / "output-parent-file"
        ancestor.write_bytes(b"keep this file")
        for suffix in ("build", "missing/deeper/build"):
            with self.subTest(suffix=suffix), self.assertRaises(working.TwrpWorkingError):
                self.build(output_dir=ancestor / suffix)
        self.assertTrue(ancestor.is_file())
        self.assertEqual(ancestor.read_bytes(), b"keep this file")
        self.runner.assert_not_called()

    def test_mocked_native_stage_failure_stops_build_without_success_receipts(self):
        def fail(label, argv, env, work, records, **limits):
            if label == "compress":
                raise working.TwrpWorkingError("compress failed (native output hashes recorded)")
            return self.native(label, argv, env, work, records, **limits)

        self.runner.side_effect = fail
        with self.assertRaisesRegex(working.TwrpWorkingError, "compress failed"):
            self.build()
        self.assertEqual([call[0] for call in self.calls], ["derive-public-key", "export-public-key", "decompress-baseline"])
        self.assertFalse((self.out / "build-report.json").exists())
        self.assertFalse((self.out / "verification-report.json").exists())
        self.assertFalse((self.out / "SHA256SUMS").exists())

    def test_mocked_native_verification_failure_rejects_a_structurally_valid_image(self):
        def fail(label, argv, env, work, records, **limits):
            if label == "avb-verify":
                raise working.TwrpWorkingError("avb-verify failed (native output hashes recorded)")
            return self.native(label, argv, env, work, records, **limits)

        self.runner.side_effect = fail
        working.inspect_image_bytes(self.fx.image, self.fx.profile)
        with self.assertRaisesRegex(working.TwrpWorkingError, "avb-verify failed"):
            self.verify()

    def test_native_exported_key_must_match_pinned_embedded_key(self):
        def hook(label, argv, work):
            if label == "public-key-export":
                Path(argv[argv.index("--output") + 1]).write_bytes(_mutate(FAKE_AVB_KEY, 12, b"x"))

        self.native_hook = hook
        with self.assertRaisesRegex(working.TwrpWorkingError, "SHA256 differs"):
            self.verify()
        self.assertNotIn("avb-verify", [call[0] for call in self.calls])

    def test_compression_roundtrip_mismatch_is_not_admitted_for_packaging(self):
        def hook(label, argv, work):
            if label == "compression-roundtrip":
                Path(argv[-1]).write_bytes(self.fx.changed + b"bad")

        self.native_hook = hook
        with self.assertRaisesRegex(working.TwrpWorkingError, "round trip differs"):
            self.build()
        self.assertNotIn("mkbootimg", [call[0] for call in self.calls])

    def test_unexpected_mkbootimg_payload_fails_before_signing(self):
        def hook(label, argv, work):
            if label == "mkbootimg":
                Path(argv[argv.index("--output") + 1]).write_bytes(_mutate(self.fx.unsigned, 44, b"x"))

        self.native_hook = hook
        with self.assertRaisesRegex(working.TwrpWorkingError, "boot header differs"):
            self.build()
        self.assertNotIn("avb-sign", [call[0] for call in self.calls])

    def test_wrong_signed_output_is_rejected_before_native_verification(self):
        def hook(label, argv, work):
            if label == "avb-sign":
                Path(argv[argv.index("--image") + 1]).write_bytes(_mutate(self.fx.image, self.fx.offsets["auth"] + 32, b"x"))

        self.native_hook = hook
        with self.assertRaisesRegex(working.TwrpWorkingError, "SHA256 differs"):
            self.build()
        self.assertNotIn("avb-verify", [call[0] for call in self.calls])

    def test_verification_snapshot_mutation_is_rejected(self):
        def hook(label, argv, work):
            if label == "avb-verify":
                Path(argv[argv.index("--image") + 1]).write_bytes(self.fx.image + b"changed")

        self.native_hook = hook
        with self.assertRaisesRegex(working.TwrpWorkingError, "snapshot changed"):
            self.verify()

    def test_source_image_key_tool_or_patch_changes_during_build_are_detected(self):
        for index, name in enumerate(("baseline_image", "key", "mkbootimg", "patch")):
            path = self.public_patch if name == "patch" else self.paths[name]
            original = path.read_bytes()
            mutated = []

            def hook(label, argv, work, selected=path, data=original):
                if label == "avb-verify":
                    selected.write_bytes(data + b"changed")
                    mutated.append(selected)

            self.native_hook = hook
            with self.subTest(name=name), self.assertRaises(working.TwrpWorkingError):
                self.build(output_dir=self.host / f"mutated-source-{index}")
            self.assertEqual(mutated, [path])
            self.assertFalse((self.host / f"mutated-source-{index}" / "build-report.json").exists())
            path.write_bytes(original)


class WorkingNativeRunnerTests(NoNativeTests):
    """Exercise streaming/cleanup with mocked Popen, selector, reads and signals."""

    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="working76-runner-tests-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name).resolve()
        self.process = mock.Mock()
        self.process.pid = 987654321  # Never used with a real signal function.
        self.process.returncode = 0
        self.process.stdout.fileno.return_value = 101
        self.process.stderr.fileno.return_value = 102
        self.process.wait.side_effect = lambda timeout: self.process.returncode
        self.popen = self.guards.enter_context(mock.patch.object(working.subprocess, "Popen", return_value=self.process))
        self.selector = mock.MagicMock()
        self.selector.__enter__.return_value = self.selector
        self.guards.enter_context(mock.patch.object(working.selectors, "DefaultSelector", return_value=self.selector))
        registered = {}

        def register(stream, events, name):
            registered[stream] = SimpleNamespace(fileobj=stream, data=name)

        self.selector.register.side_effect = register
        self.selector.unregister.side_effect = lambda stream: registered.pop(stream)
        self.selector.get_map.side_effect = lambda: dict(registered)
        self.selector.select.side_effect = lambda timeout: [(key, working.selectors.EVENT_READ) for key in registered.values()]
        self.chunks = {101: [b"synthetic standard output", b""], 102: [b"synthetic diagnostic", b""]}

        def read(fd, limit):
            chunk = self.chunks[fd][0]
            head, tail = chunk[:limit], chunk[limit:]
            if tail:
                self.chunks[fd][0] = tail
            else:
                self.chunks[fd].pop(0)
            return head

        self.reader = self.guards.enter_context(mock.patch.object(working.os, "read", side_effect=read))
        self.clock = self.guards.enter_context(mock.patch.object(working.time, "monotonic", return_value=10.0))
        self.killpg = self.guards.enter_context(mock.patch.object(working.os, "killpg"))
        self.records = []
        self.argv = ["/synthetic/native", self.work / "input", "--argument", "literal $(never executed)"]
        self.env = {"PATH": "/synthetic", "LC_ALL": "C"}

    def run_native(self, **kwargs):
        return working._run("fixture-step", self.argv, self.env, self.work, self.records, **kwargs)

    def receipt(self):
        path = self.work / "native-01-fixture-step.json"
        self.assertEqual(path.stat().st_mode & 0o077, 0)
        return json.loads(path.read_text())

    def assert_closed(self):
        self.process.stdout.close.assert_called_once_with()
        self.process.stderr.close.assert_called_once_with()

    def test_success_records_hashes_and_uses_anchored_shell_free_bounded_subprocess(self):
        self.run_native(max_file_bytes=2048)
        args, kwargs = self.popen.call_args
        self.assertEqual(args, (["/synthetic/native", "input", "--argument", "literal $(never executed)"],))
        self.assertIs(kwargs["shell"], False)
        self.assertIs(kwargs["start_new_session"], True)
        self.assertEqual(kwargs["stdin"], subprocess.DEVNULL)
        self.assertEqual(kwargs["stdout"], subprocess.PIPE)
        self.assertEqual(kwargs["stderr"], subprocess.PIPE)
        self.assertEqual(kwargs["env"], self.env)
        self.assertEqual(len(kwargs["pass_fds"]), 1)
        with mock.patch.object(working.os, "fchdir") as chdir, \
                mock.patch.object(working.resource, "setrlimit") as limits:
            kwargs["preexec_fn"]()
        chdir.assert_called_once_with(kwargs["pass_fds"][0])
        self.assertEqual(limits.call_args_list, [
            mock.call(working.resource.RLIMIT_FSIZE, (2048, 2048)),
            mock.call(working.resource.RLIMIT_CORE, (0, 0))])
        expected = {"step": "fixture-step", "returncode": 0,
                    "stdout": _identity(b"synthetic standard output"),
                    "stderr": _identity(b"synthetic diagnostic")}
        self.assertEqual(self.records, [expected])
        self.assertEqual(self.receipt(), expected)
        self.assertNotIn("synthetic standard output", (self.work / "native-01-fixture-step.json").read_text())
        self.killpg.assert_not_called()
        self.assert_closed()

    def test_nonzero_exit_preserves_hash_receipt_but_does_not_leak_native_text(self):
        self.process.returncode = 7
        self.chunks[102] = [b"secret-path-and-native-output", b""]
        with self.assertRaisesRegex(working.TwrpWorkingError, "fixture-step failed") as caught:
            self.run_native()
        self.assertNotIn("secret-path", str(caught.exception))
        self.assertEqual(self.records[0]["returncode"], 7)
        self.assertNotIn("incomplete", self.records[0])
        self.assertEqual(self.receipt(), self.records[0])
        self.assertEqual(len(self.records), 1)
        self.killpg.assert_called_once_with(self.process.pid, working.signal.SIGKILL)
        self.assert_closed()

    def test_output_at_bound_succeeds_but_each_stream_over_bound_is_killed(self):
        self.chunks = {101: [b"x" * working.MAX_NATIVE_LOG, b""], 102: [b"y" * working.MAX_NATIVE_LOG, b""]}
        self.run_native()
        self.assertEqual(self.records[0]["stdout"]["size_bytes"], working.MAX_NATIVE_LOG)
        self.assertEqual(self.records[0]["stderr"]["size_bytes"], working.MAX_NATIVE_LOG)
        self.killpg.assert_not_called()

    def test_stdout_over_bound_stops_streaming_and_records_only_bounded_hash(self):
        self.chunks[101] = [b"x" * (working.MAX_NATIVE_LOG + 100), b""]
        with self.assertRaisesRegex(working.TwrpWorkingError, "output exceeds bound"):
            self.run_native()
        self.assertTrue(self.records[0]["incomplete"])
        self.assertEqual(self.records[0]["stdout"]["size_bytes"], working.MAX_NATIVE_LOG + 1)
        self.assertEqual(self.receipt(), self.records[0])
        self.killpg.assert_called_once_with(self.process.pid, working.signal.SIGKILL)
        self.assert_closed()

    def test_stderr_over_bound_is_killed_independently_of_stdout(self):
        self.chunks[102] = [b"y" * (working.MAX_NATIVE_LOG + 100), b""]
        with self.assertRaisesRegex(working.TwrpWorkingError, "output exceeds bound"):
            self.run_native()
        self.assertEqual(self.records[0]["stderr"]["size_bytes"], working.MAX_NATIVE_LOG + 1)
        self.assertEqual(self.receipt(), self.records[0])
        self.killpg.assert_called_once_with(self.process.pid, working.signal.SIGKILL)
        self.assert_closed()

    def test_elapsed_timeout_kills_group_reaps_child_and_records_incomplete_step(self):
        self.clock.side_effect = [0.0, working.TIMEOUT + 1.0]
        with self.assertRaisesRegex(working.TwrpWorkingError, "fixture-step timed out"):
            self.run_native()
        self.selector.select.assert_not_called()
        self.killpg.assert_called_once_with(self.process.pid, working.signal.SIGKILL)
        self.process.wait.assert_called_once_with(timeout=5)
        self.assertTrue(self.receipt()["incomplete"])
        self.assertEqual(self.records[0]["stdout"], _identity(b""))
        self.assert_closed()

    def test_wait_timeout_is_redacted_and_cleanup_is_bounded(self):
        self.process.wait.side_effect = [subprocess.TimeoutExpired("private-path", 1), -9]
        with self.assertRaisesRegex(working.TwrpWorkingError, "could not complete") as caught:
            self.run_native()
        self.assertNotIn("private-path", str(caught.exception))
        self.killpg.assert_called_once_with(self.process.pid, working.signal.SIGKILL)
        self.assertEqual(self.process.wait.call_args_list[-1], mock.call(timeout=5))
        self.assertTrue(self.receipt()["incomplete"])
        self.assert_closed()

    def test_launch_error_is_redacted_without_attempting_to_signal_a_nonexistent_process(self):
        self.popen.side_effect = OSError("private executable path")
        with self.assertRaisesRegex(working.TwrpWorkingError, "could not complete") as caught:
            self.run_native()
        self.assertNotIn("private executable path", str(caught.exception))
        self.killpg.assert_not_called()
        self.process.wait.assert_not_called()
        self.assertIsNone(self.receipt()["returncode"])
        self.assertTrue(self.records[0]["incomplete"])

    def test_interruption_still_closes_pipes_and_kills_only_the_mocked_process_group(self):
        self.selector.select.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.run_native()
        self.killpg.assert_called_once_with(self.process.pid, working.signal.SIGKILL)
        self.assertTrue(self.receipt()["incomplete"])
        self.assert_closed()

    def test_step_labels_cannot_escape_the_private_receipt_directory(self):
        for label in ("", "../escape", "UPPERCASE", "has space", "a" * 65):
            with self.subTest(label=label), self.assertRaisesRegex(working.TwrpWorkingError, "invalid native step label"):
                working._run(label, self.argv, self.env, self.work, self.records)
        self.popen.assert_not_called()
        self.assertEqual(self.records, [])
        self.assertEqual(list(self.work.iterdir()), [])


class WorkingLocalConfigTests(NoNativeTests):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="working76-config-tests-")
        self.addCleanup(temporary.cleanup)
        self.host = Path(temporary.name).resolve()
        self.config = self.host / "local.json"

    def write_config(self, value):
        self.config.write_text(json.dumps(value))
        return self.config

    def test_relative_defaults_are_resolved_at_config_without_opening_target_paths(self):
        values = {"baseline_image": "images/base.img", "key": "keys/key.pem", "avbtool": "tools/avbtool.py",
                  "openssl": str(self.host / "absolute-openssl")}
        result = working.load_local_config(self.write_config(values))
        self.assertEqual(result, {name: Path(value) if Path(value).is_absolute() else self.host / value
                                  for name, value in values.items()})
        self.assertTrue(all(not path.exists() for path in result.values()))

    def test_unknown_fields_nonpaths_controls_and_inline_private_keys_are_rejected(self):
        bad = ({"unknown": "value"}, [], None, {"key": None}, {"key": 2}, {"key": True},
               {"key": []}, {"key": ""}, {"key": "x" * 4097}, {"key": "line\nbreak"},
               {"key": "null\0byte"}, {"key": "-----BEGIN PRIVATE KEY-----"})
        for value in bad:
            with self.subTest(value=repr(value)[:65]), self.assertRaises(working.TwrpWorkingError):
                working.load_local_config(self.write_config(value))

    def test_local_config_symlink_and_oversized_file_are_rejected(self):
        self.write_config({"key": "relative"})
        alias = self.host / "alias.json"
        alias.symlink_to(self.config)
        with self.assertRaisesRegex(working.TwrpWorkingError, "not a regular file"):
            working.load_local_config(alias)
        self.config.write_bytes(b" " * (16 * 1024 + 1))
        with self.assertRaisesRegex(working.TwrpWorkingError, "outside bounds"):
            working.load_local_config(self.config)

    def test_duplicate_json_fields_are_rejected_in_local_config_and_public_profile(self):
        self.config.write_bytes(b'{"key":"first","key":"second"}')
        with self.assertRaisesRegex(working.TwrpWorkingError, "duplicate JSON field"):
            working.load_local_config(self.config)
        with mock.patch.object(working, "_read", return_value=b'{"schema_version":1,"schema_version":1}'), \
                self.assertRaisesRegex(working.TwrpWorkingError, "duplicate JSON field"):
            working.load_profile()

    def test_resolve_paths_selects_only_requested_defaults_without_target_reads(self):
        self.write_config({"key": "never-open-private", "baseline_image": "never-open-image",
                           "avbtool": "tools/avbtool", "openssl": "tools/openssl", "public_key": "old-public"})
        original_read = working._read

        def config_only(path, *args, **kwargs):
            self.assertEqual(Path(path), self.config)
            return original_read(path, *args, **kwargs)

        explicit = {"avbtool": None, "openssl": None, "public_key": self.host / "explicit-public"}
        with mock.patch.object(working, "_read", side_effect=config_only) as reader:
            result = working.resolve_paths(self.config, explicit)
        self.assertEqual(result, {"avbtool": self.host / "tools/avbtool", "openssl": self.host / "tools/openssl",
                                  "public_key": self.host / "explicit-public"})
        self.assertEqual(reader.call_count, 1)
        self.assertEqual(set(result), set(explicit))
        self.assertIsNone(explicit["avbtool"])

    def test_resolve_paths_rejects_unknown_fields_and_missing_required_paths(self):
        for explicit in ([], None, {"output_dir": "not-an-input"}, {"avbtool": None}, {"key": None}):
            with self.subTest(explicit=explicit), self.assertRaises(working.TwrpWorkingError):
                working.resolve_paths(None, explicit)
        self.assertEqual(working.resolve_paths(None, {"key": Path("relative-key")}), {"key": Path("relative-key")})

    def test_cli_explicit_build_paths_override_only_corresponding_local_defaults(self):
        names = ("baseline_image", "key", "mkbootimg", "avbtool", "lz4", "openssl")
        self.write_config({name: "defaults/" + name for name in names})
        override = self.host / "explicit-key"
        out = self.host / "output"
        stdout = io.StringIO()
        with mock.patch.object(working, "build_recovery", return_value={"status": "mocked"}) as build, redirect_stdout(stdout):
            status = working.main(["build", "--local-config", str(self.config), "--key", str(override), "--output-dir", str(out)])
        expected = {name: self.host / "defaults" / name for name in names}
        expected.update(key=override, output_dir=out)
        build.assert_called_once_with(**expected)
        self.assertEqual(status, 0)
        self.assertEqual(json.loads(stdout.getvalue()), {"status": "mocked"})

    def test_verify_cli_ignores_unneeded_private_defaults_and_honors_public_key_override(self):
        self.write_config({"baseline_image": "do-not-read-image", "key": "do-not-read-private-key",
                           "avbtool": "avbtool", "openssl": "openssl", "public_key": "old-public.pem"})
        image, public = self.host / "image", self.host / "public.pem"
        with mock.patch.object(working, "verify_image", return_value={"status": "mocked"}) as verify, redirect_stdout(io.StringIO()):
            status = working.main(["verify", "--local-config", str(self.config), "--image", str(image), "--public-key", str(public)])
        verify.assert_called_once_with(image, avbtool=self.host / "avbtool", openssl=self.host / "openssl", public_key=public)
        self.assertEqual(status, 0)

    def test_cli_missing_paths_and_native_input_failures_are_redacted(self):
        stderr = io.StringIO()
        with mock.patch.object(working, "build_recovery") as build, redirect_stderr(stderr):
            self.assertEqual(working.main(["build", "--output-dir", str(self.host / "out")]), 2)
        build.assert_not_called()
        self.assertIn("required input paths are missing", stderr.getvalue())
        stderr = io.StringIO()
        args = ["verify", "--image", "/invented/image", "--public-key", "/invented/public",
                "--avbtool", "/invented/avbtool", "--openssl", "/invented/openssl"]
        with mock.patch.object(working, "verify_image", side_effect=OSError("secret input path and content")), redirect_stderr(stderr):
            self.assertEqual(working.main(args), 2)
        self.assertEqual(stderr.getvalue(), "twrp_working: invalid or unavailable input\n")


if __name__ == "__main__":
    unittest.main()
