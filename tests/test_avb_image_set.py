"""Offline AVB closure tests with inert images, fake keys and mocked tools.

The fixture uses real AVB field layouts and authentication hashes, but its RSA
keys/signatures, EROFS bytes, device trees and tools are deliberately unusable.
Native success here tests orchestration, never cryptography or device behavior.
"""

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

from scripts import avb_image_set as avb


def identity(raw):
    return {"sha256": hashlib.sha256(raw).hexdigest(), "size_bytes": len(raw)}


def padded(raw, alignment=4096):
    return bytes(raw) + bytes(-len(raw) % alignment)


def public_blob(marker):
    return struct.pack(">II", 4096, 0) + bytes((marker,)) * 1024


def public_pem(name):
    return (b"-----BEGIN PUBLIC KEY-----\nINERT fixture for " + name.encode()
            + b"; not a real RSA key\n-----END PUBLIC KEY-----\n")


def hash_descriptor(name, payload, *, digest=None, flags=0, size=None, salt=None):
    name = name.encode()
    salt = hashlib.sha256(b"synthetic salt " + name).digest() if salt is None else salt
    digest = hashlib.sha256(salt + payload).digest() if digest is None else digest
    length = (132 + len(name) + len(salt) + len(digest) + 7) // 8 * 8
    fixed = struct.pack(">QQQ32sIIII60s", 2, length - 16,
                        len(payload) if size is None else size, b"sha256",
                        len(name), len(salt), len(digest), flags, bytes(60))
    return padded(fixed + name + salt + digest, 8)


def tree_descriptor(name, *, size=8192, tree_at=8192, tree_size=4096,
                    fec_at=12288, fec_size=8192, flags=0, salt=None):
    name = name.encode()
    salt = hashlib.sha256(b"synthetic tree " + name).digest() if salt is None else salt
    digest = b"H" * 32  # A placeholder, not a genuine hashtree root digest.
    length = (180 + len(name) + len(salt) + len(digest) + 7) // 8 * 8
    fixed = struct.pack(">QQIQQQIIIQQ32sIIII60s", 1, length - 16, 1, size,
                        tree_at, tree_size, 4096, 4096, 2, fec_at, fec_size,
                        b"sha256", len(name), len(salt), len(digest), flags, bytes(60))
    return padded(fixed + name + salt + digest, 8)


def chain_descriptor(name, location, key, *, flags=0):
    name = name.encode()
    length = (92 + len(name) + len(key) + 7) // 8 * 8
    return padded(struct.pack(">QQIIII60s", 4, length - 16, location, len(name),
                              len(key), flags, bytes(60)) + name + key, 8)


def property_descriptor(key=b"com.android.build.test", value=b"fixture"):
    tail = padded(struct.pack(">QQ", len(key), len(value)) + key + b"\0" + value + b"\0", 8)
    return struct.pack(">QQ", 0, len(tail)) + tail


def vbmeta(descriptors, *, key=b"", rollback=0, location=0, flags=0, minor=0):
    descriptors = b"".join(descriptors)
    auxiliary = padded(descriptors + key, 64)
    header = bytearray(256)
    authentication_size = 576 if key else 0
    struct.pack_into(">4sIIQQI", header, 0, b"AVB0", 1, minor,
                     authentication_size, len(auxiliary), 2 if key else 0)
    struct.pack_into(">10Q", header, 32,
                     0, 32 if key else 0, 32 if key else 0, 512 if key else 0,
                     len(descriptors) if key else 0, len(key), 0, 0, 0, len(descriptors))
    struct.pack_into(">QII", header, 112, rollback, flags, location)
    release = b"synthetic test fixture"
    header[128:128 + len(release)] = release
    authentication = (hashlib.sha256(header + auxiliary).digest() + b"S" * 512 + bytes(32)) if key else b""
    return bytes(header) + authentication + auxiliary


def with_footer(payload, metadata, *, tree_and_fec=b""):
    prefix = padded(payload + tree_and_fec)
    total = (len(prefix) + len(metadata) + 64 + 4095) // 4096 * 4096
    footer = struct.pack(">4sIIQQQ28s", b"AVBf", 1, 0, len(payload),
                         len(prefix), len(metadata), bytes(28))
    return prefix + metadata + bytes(total - len(prefix) - len(metadata) - 64) + footer


def boot_payload(name):
    header = bytearray(4096)
    kernel, ramdisk = (512, 0) if name == "boot" else (0, 128)
    struct.pack_into("<8s9I", header, 0, b"ANDROID!", kernel, ramdisk, 0, 1584, 0, 0, 0, 0, 4)
    return bytes(header) + padded(b"K" * kernel) + padded(b"R" * ramdisk)


def vendor_boot_payload():
    header = bytearray(4096)
    header[:8] = b"VNDRBOOT"
    struct.pack_into("<II", header, 8, 4, 4096)
    struct.pack_into("<I", header, 24, 100)
    struct.pack_into("<IIQIIII", header, 2096, 2128, 40, 0, 108, 1, 108, 64)
    table = bytearray(108)
    struct.pack_into("<III", table, 0, 100, 0, 1)
    table[12:19] = b"default"
    fdt = struct.pack(">10I", 0xD00DFEED, 40, 40, 40, 40, 17, 16, 0, 0, 0)
    return bytes(header) + padded(b"R" * 100) + padded(fdt) + padded(table) + padded(b"B" * 64)


def dtbo_payload():
    header = struct.pack(">8I", 0xD7B7AB1E, 104, 32, 32, 1, 32, 4096, 0)
    entry = struct.pack(">8I", 40, 64, 1, 0, 0, 0, 0, 0)
    fdt = struct.pack(">10I", 0xD00DFEED, 40, 40, 40, 40, 17, 16, 0, 0, 0)
    return header + entry + fdt


def erofs_payload():
    raw = bytearray(8192)
    struct.pack_into("<I", raw, 1024, 0xE0F5E1E2)
    raw[1036] = 12
    struct.pack_into("<I", raw, 1060, 2)
    return bytes(raw)


class SyntheticSet:
    def __init__(self, root):
        self.root = root
        self.profile = json.loads(avb.PROFILE.read_text())
        self.keys = {name: public_blob(index + 1) for index, name in enumerate(sorted(avb.SIGNED))}
        self.pems = {name: public_pem(name) for name in avb.SIGNED}
        self.payloads = {name: boot_payload(name) for name in ("boot", "init_boot", "recovery")}
        self.payloads.update(vendor_boot=vendor_boot_payload(), dtbo=dtbo_payload(),
                             countrycode=b"C" * 32, pvmfw=b"P" * 778240)
        self.payloads.update({name: erofs_payload() for name in avb.LOGICAL})
        self.descriptors = {name: hash_descriptor(name, self.payloads[name]) for name in avb.HASHED}
        self.descriptors.update({name: tree_descriptor(name) for name in avb.LOGICAL})
        self.images = {}
        for name in avb.HASHED | avb.LOGICAL:
            if name in ("countrycode", "pvmfw"):
                self.images[name] = padded(self.payloads[name])
                continue
            signed = self.profile["signed_images"].get(name, {})
            metadata = vbmeta([self.descriptors[name]], key=self.keys.get(name, b""),
                              rollback=signed.get("rollback_index", 0),
                              location=signed.get("header_rollback_index_location", 0),
                              minor=2 if name == "recovery" else 0)
            self.images[name] = with_footer(self.payloads[name], metadata,
                                           tree_and_fec=b"T" * 4096 + b"F" * 8192 if name in avb.LOGICAL else b"")
        self.root_descriptors = {name: self.descriptors[name] for name, owner in avb.OWNERS.items()
                                 if owner == "vbmeta"}
        self.root_descriptors.update({name: chain_descriptor(name, location, self.keys[name])
                                     for name, location in self.profile["chain_locations"].items()})
        self.images["vbmeta"] = self.root_image()
        self.images["vbmeta_system"] = padded(vbmeta(
            [self.descriptors[name] for name in sorted(("system", "system_ext", "product"))],
            key=self.keys["vbmeta_system"], rollback=1769904000))
        self.profile["working76"] = {"image": identity(self.images["recovery"]),
                                     "public_pem": identity(self.pems["recovery"]),
                                     "avb_public_key_sha256": identity(self.keys["recovery"])["sha256"]}
        self.profile_sha = identity(json.dumps(self.profile, sort_keys=True).encode())["sha256"]
        for directory in ("images", "public", "tools"):
            (root / directory).mkdir(mode=0o700)
        self.manifest = {"schema_version": 1, "profile_id": avb.PROFILE_ID,
                         "profile_sha256": self.profile_sha, "artifact_set_id": "synthetic-not-flashable",
                         "images": {}, "public_keys": {},
                         "tools": {"avbtool": "tools/avbtool.py", "openssl": "tools/openssl"}}
        for name, raw in self.images.items():
            self.write_image(name, raw)
        for name, raw in self.pems.items():
            path = root / "public" / ("expected-" + name + ".pem")
            path.write_bytes(raw)
            self.manifest["public_keys"][name] = {"path": str(path.relative_to(root)), **identity(raw),
                                                 "avb_sha256": identity(self.keys[name])["sha256"]}
        (root / "tools/avbtool.py").write_bytes(b"# INERT avbtool fixture; never executed\n")
        (root / "tools/openssl").write_bytes(b"INERT openssl fixture; never executed\n")
        (root / "tools/openssl").chmod(0o700)
        self.manifest_path = root / "manifest.json"

    def root_image(self, descriptors=None, **kwargs):
        if descriptors is None:
            descriptors = [self.root_descriptors[name] for name in sorted(self.root_descriptors)]
        return padded(vbmeta(descriptors, key=self.keys["vbmeta"], **kwargs))

    def write_image(self, name, raw):
        self.images[name] = raw
        path = self.root / "images" / (name + ".original")
        path.write_bytes(raw)
        self.manifest["images"][name] = {"path": str(path.relative_to(self.root)), **identity(raw)}

    def save_manifest(self):
        raw = (json.dumps(self.manifest, sort_keys=True) + "\n").encode()
        self.manifest_path.write_bytes(raw)
        return identity(raw)["sha256"]

    def select(self, names):
        self.manifest["images"] = {name: row for name, row in self.manifest["images"].items() if name in names}
        self.manifest["public_keys"] = {name: row for name, row in self.manifest["public_keys"].items() if name in names}


class NoNativeTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(mock.patch("subprocess.Popen", side_effect=AssertionError("native execution is forbidden in tests")))
        self.enterContext(mock.patch("socket.socket", side_effect=AssertionError("network is forbidden in tests")))
        self.enterContext(mock.patch("os.system", side_effect=AssertionError("shell execution is forbidden in tests")))


class ImageSetTests(NoNativeTests):
    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory(prefix="avb-image-set-test-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.fx = SyntheticSet(self.root)
        self.calls, self.hook = [], None
        self.enterContext(mock.patch.object(avb, "load_profile", side_effect=lambda: (deepcopy(self.fx.profile), self.fx.profile_sha)))
        self.prepare = self.enterContext(mock.patch.object(avb.io, "_prepare_tools", side_effect=self.prepare_tools))
        self.native = self.enterContext(mock.patch.object(avb, "_native", side_effect=self.native_step))
        self.enterContext(mock.patch.object(avb.shutil, "disk_usage", return_value=SimpleNamespace(free=1 << 40)))

    def prepare_tools(self, profile, work, **selected):
        directory = work / "tools"
        directory.mkdir(mode=0o700)
        copied = directory / "avbtool.py"
        copied.write_bytes(Path(selected["avbtool"]).read_bytes())
        copied.chmod(0o600)
        paths = {"avbtool": copied, "openssl": Path(selected["openssl"])}
        identities = {name: identity(Path(path).read_bytes()) for name, path in selected.items()}
        snapshots = {Path(path): identities[name] for name, path in selected.items()}
        return paths, identities, snapshots, {"PATH": "/nonexistent", "LC_ALL": "C"}

    def native_step(self, label, args, env, work, records):
        self.calls.append((label, args, work))
        if label.startswith("export-"):
            output = Path(args[args.index("--output") + 1])
            output.write_bytes(self.fx.keys[output.stem])
            output.chmod(0o600)
        else:
            self.assertIn("verify_image", args)
            image = Path(args[args.index("--image") + 1])
            self.assertEqual(image.parent, work)
            self.assertEqual(stat.S_IMODE(image.stat().st_mode), 0o600)
            self.assertNotIn("--follow_chain_partitions", args)
            self.assertNotIn("--accept_zeroed_hashtree", args)
            if image.stem in avb.SIGNED:
                self.assertEqual(Path(args[args.index("--key") + 1]), work / "keys" / (image.stem + ".pem"))
                raw = image.read_bytes()
                offset = struct.unpack_from(">Q", raw, len(raw) - 64 + 20)[0] if raw[-64:-60] == b"AVBf" else 0
                if raw[offset + 288:offset + 800] != b"S" * 512:
                    raise avb.AvbImageSetError("mock native signature rejection")
        records.append({"step": label, "returncode": 0,
                        "stdout": identity(b"mocked native output"), "stderr": identity(b"")})
        if self.hook is not None:
            self.hook(label, args, work)

    def verify(self, *, inspect_only=False):
        digest = self.fx.save_manifest()
        return avb.verify(self.fx.manifest_path, digest, inspect_only=inspect_only)

    def test_complete_mixed_key_set_checks_four_signatures_and_exact_chain_arguments(self):
        result = self.verify()
        self.assertEqual(len(result["images"]), 17)
        self.assertEqual(result["status"], "verified")
        self.assertTrue(result["complete_chain_verified"])
        self.assertEqual(set(result["verified_artifacts"]), avb.SIGNED)
        self.assertEqual(len({row["avb_sha256"] for row in result["public_keys"].values()}), 4)
        verifies = [(label, args, work) for label, args, work in self.calls if label.startswith("verify-")]
        self.assertEqual([label for label, _, _ in verifies],
                         ["verify-vbmeta", "verify-boot", "verify-recovery", "verify-vbmeta-system"])
        root_args = verifies[0][1]
        expected = {root_args[i + 1] for i, word in enumerate(root_args) if word == "--expected_chain_partition"}
        self.assertEqual(expected, {"boot:3:keys/boot.avbpubkey", "recovery:1:keys/recovery.avbpubkey",
                                    "vbmeta_system:2:keys/vbmeta_system.avbpubkey"})
        for _, args, work in self.calls:
            self.assertFalse(work.exists())
            self.assertFalse(any(".original" in str(arg) for arg in args))
        for name in ("complete_rom_ready", "signing_performed", "phone_accessed", "oem_trust_established",
                     "device_rollback_compatibility_verified", "physical_partition_fit_verified", "fec_payload_verified"):
            self.assertIs(result[name], False, name)
        self.assertNotIn('"_key"', json.dumps(result))

    def test_partial_verify_blocks_without_reading_images_or_running_native_tools(self):
        self.fx.select({"init_boot"})
        (self.root / self.fx.manifest["images"]["init_boot"]["path"]).unlink()
        result = self.verify()
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(len(result["missing_partitions"]), 16)
        self.assertFalse(result["native_commands_run"])
        self.assertFalse(result["complete_chain_verified"])
        self.prepare.assert_not_called()
        self.native.assert_not_called()

    def test_unsigned_leaf_inspection_is_not_complete_chain_verification(self):
        self.fx.select({"init_boot"})
        result = self.verify(inspect_only=True)
        self.assertEqual(result["verified_artifacts"], ["init_boot"])
        self.assertEqual(result["images"]["init_boot"]["metadata"]["algorithm"], "NONE")
        self.assertFalse(result["complete_chain_verified"])
        self.assertFalse(result["partial_results_are_chain_verification"])

    def test_raw_leaf_inspection_does_not_claim_native_verification(self):
        self.fx.select({"countrycode"})
        result = self.verify(inspect_only=True)
        self.assertEqual(result["verified_artifacts"], [])
        self.assertEqual(result["artifacts_without_native_payload_verification"], ["countrycode"])
        self.assertFalse(result["native_commands_run"])
        self.assertFalse(result["complete_chain_verified"])
        self.native.assert_not_called()

    def test_root_inspection_without_children_does_not_claim_signature_verification(self):
        self.fx.select({"vbmeta"})
        result = self.verify(inspect_only=True)
        self.assertEqual(result["verified_artifacts"], [])
        self.assertEqual(result["artifacts_without_native_payload_verification"], ["vbmeta"])
        self.assertEqual([label for label, _, _ in self.calls], ["export-vbmeta"])
        self.assertFalse(result["complete_chain_verified"])

    def test_full_inspection_does_not_promote_itself_to_complete_chain_verification(self):
        result = self.verify(inspect_only=True)
        self.assertEqual(result["status"], "artifacts-inspected")
        self.assertEqual(result["missing_partitions"], [])
        self.assertFalse(result["complete_chain_verified"])

    def test_boot_and_recovery_hashes_cannot_replace_required_chain_descriptors(self):
        for target in ("boot", "recovery"):
            with self.subTest(target=target):
                descriptors = dict(self.fx.root_descriptors)
                descriptors[target] = self.fx.descriptors[target]
                self.fx.write_image("vbmeta", self.fx.root_image(list(descriptors.values())))
                self.calls.clear()
                with self.assertRaisesRegex(avb.AvbImageSetError, "descriptor kind"):
                    self.verify()
                self.assertFalse(any(label.startswith("verify-") for label, _, _ in self.calls))

    def test_missing_duplicate_extra_and_wrongly_owned_root_descriptors_are_rejected(self):
        base = list(self.fx.root_descriptors.values())
        variants = (base[1:], base + [base[0]], base + [self.fx.descriptors["system"]])
        for descriptors in variants:
            with self.subTest(count=len(descriptors)):
                self.fx.write_image("vbmeta", self.fx.root_image(descriptors))
                with self.assertRaises(avb.AvbImageSetError):
                    self.verify()

    def test_parent_chain_must_match_independent_child_key_and_location(self):
        for key, location in ((self.fx.keys["vbmeta"], 3), (self.fx.keys["boot"], 1)):
            with self.subTest(location=location, key=identity(key)["sha256"]):
                rows = dict(self.fx.root_descriptors)
                rows["boot"] = chain_descriptor("boot", location, key)
                self.fx.write_image("vbmeta", self.fx.root_image(list(rows.values())))
                with self.assertRaises(avb.AvbImageSetError):
                    self.verify()

    def test_leaf_footer_must_match_signed_parent_descriptor(self):
        rows = dict(self.fx.root_descriptors)
        rows["init_boot"] = hash_descriptor("init_boot", self.fx.payloads["init_boot"], digest=b"X" * 32)
        self.fx.write_image("vbmeta", self.fx.root_image(list(rows.values())))
        with self.assertRaisesRegex(avb.AvbImageSetError, "parent descriptor differs"):
            self.verify()

    def test_signed_role_cannot_be_unsigned_or_use_another_key_or_rollback(self):
        for options in ({"key": b"", "rollback": 1769904000},
                        {"key": self.fx.keys["vbmeta"], "rollback": 1769904000},
                        {"key": self.fx.keys["boot"], "rollback": 0}):
            with self.subTest(options=options):
                raw = with_footer(self.fx.payloads["boot"], vbmeta([self.fx.descriptors["boot"]], **options))
                self.fx.write_image("boot", raw)
                with self.assertRaises(avb.AvbImageSetError):
                    self.verify()

    def test_header_disabling_flags_fail_even_with_valid_authentication_hash(self):
        for flag in (1, 2, 3):
            with self.subTest(flags=flag):
                self.fx.write_image("vbmeta", self.fx.root_image(flags=flag))
                with self.assertRaisesRegex(avb.AvbImageSetError, "disabling flags"):
                    self.verify()

    def test_bad_rsa_signature_is_reserved_for_native_rejection(self):
        raw = bytearray(self.fx.images["boot"])
        offset = struct.unpack_from(">Q", raw, len(raw) - 64 + 20)[0]
        raw[offset + 288] ^= 1  # Signature is outside the header+aux auth hash.
        self.fx.write_image("boot", bytes(raw))
        with self.assertRaisesRegex(avb.AvbImageSetError, "mock native signature rejection"):
            self.verify()
        self.assertIn("verify-boot", [label for label, _, _ in self.calls])

    def test_explicit_public_key_export_mismatch_prevents_image_verification(self):
        def hook(label, args, work):
            if label == "export-boot":
                Path(args[args.index("--output") + 1]).write_bytes(self.fx.keys["vbmeta"])
        self.hook = hook
        with self.assertRaisesRegex(avb.AvbImageSetError, "exported public key differs"):
            self.verify()
        self.assertFalse(any(label.startswith("verify-") for label, _, _ in self.calls))

    def test_private_key_header_is_rejected_before_native_export(self):
        row = self.fx.manifest["public_keys"]["boot"]
        raw = b"-----BEGIN PRIVATE KEY-----\nINERT secret marker\n-----END PRIVATE KEY-----\n"
        (self.root / row["path"]).write_bytes(raw)
        row.update(identity(raw))
        with self.assertRaisesRegex(avb.AvbImageSetError, "expected a public PEM"):
            self.verify()
        self.assertNotIn("export-boot", [label for label, _, _ in self.calls])

    def test_engineering_key_and_boolean_manifest_values_fail_before_tools(self):
        original = deepcopy(self.fx.manifest)
        mutations = (lambda m: m.update(schema_version=True),
                     lambda m: m["images"]["boot"].update(size_bytes=True),
                     lambda m: m["public_keys"]["boot"].update(avb_sha256=self.fx.profile["forbidden_public_key_sha256"][0]),
                     lambda m: m["images"].update(boot_a=m["images"]["boot"]),
                     lambda m: m["public_keys"].pop("boot"))
        for index, mutate in enumerate(mutations):
            with self.subTest(index=index):
                self.fx.manifest = deepcopy(original)
                mutate(self.fx.manifest)
                with self.assertRaises(avb.AvbImageSetError):
                    self.verify()
        self.prepare.assert_not_called()

    def test_repinning_manifest_cannot_replace_working76(self):
        raw = bytearray(self.fx.images["recovery"])
        raw[4096] ^= 1
        self.fx.write_image("recovery", bytes(raw))
        with self.assertRaisesRegex(avb.AvbImageSetError, "not exact working76"):
            self.verify()
        self.prepare.assert_not_called()

    def test_manifest_digest_duplicate_field_and_budget_are_enforced(self):
        digest = self.fx.save_manifest()
        with self.assertRaisesRegex(avb.AvbImageSetError, "manifest SHA256"):
            avb.verify(self.fx.manifest_path, "0" * 64)
        raw = self.fx.manifest_path.read_bytes().replace(b'{"artifact_set_id"', b'{"schema_version":1,"artifact_set_id"', 1)
        self.fx.manifest_path.write_bytes(raw)
        with self.assertRaisesRegex(avb.AvbImageSetError, "duplicate JSON field"):
            avb.verify(self.fx.manifest_path, identity(raw)["sha256"])
        self.fx.manifest["images"]["boot"]["size_bytes"] = self.fx.profile["image_budgets"]["boot"] + 4096
        with self.assertRaisesRegex(avb.AvbImageSetError, "package budget"):
            self.verify()
        self.prepare.assert_not_called()

    def test_source_symlink_hardlink_fifo_and_parent_symlink_fail(self):
        self.fx.select({"init_boot"})
        source = self.root / self.fx.manifest["images"]["init_boot"]["path"]
        saved = source.with_name("saved-original")
        source.rename(saved)
        source.symlink_to(saved)
        with self.assertRaises(avb.AvbImageSetError):
            self.verify(inspect_only=True)
        source.unlink()
        os.link(saved, source)
        with self.assertRaises(avb.AvbImageSetError):
            self.verify(inspect_only=True)
        source.unlink()
        os.mkfifo(source)
        with self.assertRaises(avb.AvbImageSetError):
            self.verify(inspect_only=True)
        source.unlink()
        saved.rename(source)
        alias = self.root / "image-alias"
        alias.symlink_to(source.parent, target_is_directory=True)
        self.fx.manifest["images"]["init_boot"]["path"] = str(alias / source.name)
        with self.assertRaises(avb.envelope.ImageInspectionError):
            self.verify(inspect_only=True)

    def test_copied_or_source_tool_mutation_is_detected_after_native_step(self):
        for original in (False, True):
            source = self.root / "tools/avbtool.py"
            before = source.read_bytes()
            def hook(label, args, work):
                if label == "verify-vbmeta":
                    selected = source if original else work / "tools/avbtool.py"
                    selected.write_bytes(selected.read_bytes() + b"changed")
            self.hook = hook
            with self.subTest(source=original), self.assertRaises(avb.AvbImageSetError):
                self.verify()
            source.write_bytes(before)

    def test_snapshot_image_selected_key_or_exported_key_mutation_prevents_receipt(self):
        for relative in ("init_boot.img", "keys/boot.pem", "keys/boot.avbpubkey"):
            def hook(label, args, work):
                if label == "verify-vbmeta-system":
                    selected = work / relative
                    raw = bytearray(selected.read_bytes())
                    raw[-1] ^= 1
                    selected.write_bytes(raw)
            self.hook = hook
            with self.subTest(path=relative), self.assertRaises(avb.AvbImageSetError):
                self.verify()

    def test_source_image_replacement_with_identical_bytes_is_detected(self):
        source = self.root / self.fx.manifest["images"]["init_boot"]["path"]
        def hook(label, args, work):
            if label == "verify-vbmeta-system":
                replacement = source.with_suffix(".replacement")
                replacement.write_bytes(source.read_bytes())
                os.replace(replacement, source)
        self.hook = hook
        with self.assertRaisesRegex(avb.AvbImageSetError, "identity/mode changed"):
            self.verify()

    def test_source_public_key_replacement_with_identical_bytes_is_detected(self):
        source = self.root / self.fx.manifest["public_keys"]["boot"]["path"]
        def hook(label, args, work):
            if label == "verify-vbmeta-system":
                replacement = source.with_suffix(".replacement")
                replacement.write_bytes(source.read_bytes())
                os.replace(replacement, source)
        self.hook = hook
        with self.assertRaisesRegex(avb.AvbImageSetError, "public-key identity/mode changed"):
            self.verify()

    def test_source_public_key_manifest_and_profile_changes_are_detected(self):
        originals = {self.fx.manifest_path: None,
                     self.root / self.fx.manifest["public_keys"]["boot"]["path"]: self.fx.pems["boot"]}
        for selected, original in originals.items():
            def hook(label, args, work):
                if label == "verify-vbmeta-system":
                    selected.write_bytes(selected.read_bytes() + b"changed")
            self.hook = hook
            with self.subTest(path=selected.name), self.assertRaises(avb.AvbImageSetError):
                self.verify()
            if original is not None:
                selected.write_bytes(original)
        self.hook = None
        with mock.patch.object(avb, "load_profile", side_effect=[(deepcopy(self.fx.profile), self.fx.profile_sha),
                                                                (deepcopy(self.fx.profile), "0" * 64)]):
            with self.assertRaisesRegex(avb.AvbImageSetError, "profile changed"):
                self.verify()

    def test_insufficient_snapshot_disk_fails_before_native_or_image_reads(self):
        with mock.patch.object(avb.shutil, "disk_usage", return_value=SimpleNamespace(free=0)):
            with self.assertRaisesRegex(avb.AvbImageSetError, "insufficient disk"):
                self.verify()
        self.prepare.assert_not_called()
        self.native.assert_not_called()

    def test_native_failure_does_not_publish_a_success_receipt(self):
        def hook(label, args, work):
            if label == "verify-vbmeta-system":
                raise avb.AvbImageSetError("mock native verification failed")
        self.hook = hook
        digest = self.fx.save_manifest()
        output = self.root / "must-not-exist.json"
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = avb.main(["verify", "--manifest", str(self.fx.manifest_path),
                             "--expected-manifest-sha256", digest, "--output", str(output)])
        self.assertEqual(code, 2)
        self.assertFalse(output.exists())
        self.assertEqual(stdout.getvalue(), "")
        result = json.loads(stderr.getvalue())
        self.assertEqual(result["status"], "failed")
        self.assertFalse(result["complete_chain_verified"])
        self.assertFalse(result["complete_rom_ready"])

    def test_cli_creates_private_receipt_and_never_replaces_existing_output(self):
        digest = self.fx.save_manifest()
        output = self.root / "result.json"
        arguments = ["verify", "--manifest", str(self.fx.manifest_path),
                     "--expected-manifest-sha256", digest, "--output", str(output)]
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(avb.main(arguments), 0)
        self.assertEqual(stat.S_IMODE(output.stat().st_mode), 0o600)
        original = output.read_bytes()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(avb.main(arguments), 2)
        self.assertEqual(output.read_bytes(), original)


class MetadataTests(NoNativeTests):
    def test_factory_32_and_pinned_build_64_byte_salts_are_accepted(self):
        for size in (32, 64):
            for descriptor in (hash_descriptor("boot", b"payload", salt=b"s" * size),
                               tree_descriptor("vendor", salt=b"s" * size)):
                with self.subTest(size=size, tag=descriptor[:8]):
                    result = avb.parse_vbmeta(vbmeta([descriptor]))
                    self.assertEqual(result["descriptors"][0]["salt_hex"], (b"s" * size).hex())
        for size in (0, 31, 33, 63, 65):
            with self.subTest(size=size), self.assertRaises(avb.AvbImageSetError):
                avb.parse_vbmeta(vbmeta([hash_descriptor("boot", b"payload", salt=b"s" * size)]))

    def test_none_allows_bounded_offsets_for_empty_key_fields_but_no_key_data(self):
        descriptor = hash_descriptor("init_boot", b"payload")
        raw = bytearray(vbmeta([descriptor]))
        struct.pack_into(">Q", raw, 64, len(descriptor))
        struct.pack_into(">Q", raw, 80, len(descriptor))
        result = avb.parse_vbmeta(bytes(raw))
        self.assertEqual(result["algorithm"], "NONE")
        self.assertIsNone(result["public_key_sha256"])
        struct.pack_into(">Q", raw, 72, 1)
        with self.assertRaisesRegex(avb.AvbImageSetError, "unsigned vbmeta has"):
            avb.parse_vbmeta(bytes(raw))

    def test_descriptor_flags_unknown_tags_empty_digests_and_unsafe_names_are_rejected(self):
        variants = [hash_descriptor("boot", b"x", flags=1), hash_descriptor("boot", b"x", digest=b""),
                    hash_descriptor("../boot", b"x"), hash_descriptor("boot_a", b"x"),
                    tree_descriptor("vendor", flags=2), chain_descriptor("boot", 3, public_blob(1), flags=1),
                    struct.pack(">QQ", 99, 0), struct.pack(">QQII", 3, 8, 0, 0)]
        for index, descriptor in enumerate(variants):
            with self.subTest(index=index), self.assertRaises(avb.AvbImageSetError):
                avb.parse_vbmeta(vbmeta([descriptor]))

    def test_hashtree_and_fec_geometry_must_be_contiguous_and_complete(self):
        for options in ({"tree_at": 4096}, {"tree_size": 8192}, {"fec_at": 8192},
                        {"fec_size": 0}, {"fec_size": 4096}, {"size": 8193}):
            with self.subTest(options=options), self.assertRaises(avb.AvbImageSetError):
                avb.parse_vbmeta(vbmeta([tree_descriptor("vendor", **options)]))

    def test_duplicate_properties_and_partitions_are_rejected(self):
        for descriptor in (property_descriptor(), hash_descriptor("boot", b"x")):
            with self.subTest(kind=descriptor[:8]), self.assertRaisesRegex(avb.AvbImageSetError, "duplicate AVB"):
                avb.parse_vbmeta(vbmeta([descriptor, descriptor]))

    def test_authentication_hash_version_reserved_bytes_and_metadata_bounds_are_checked(self):
        good = vbmeta([hash_descriptor("boot", b"x")], key=public_blob(1))
        changes = [(0, b"NOPE"), (8, struct.pack(">I", 3)), (12, struct.pack(">Q", 1 << 40)),
                   (176, b"x"), (256, bytes((good[256] ^ 1,)))]
        for offset, replacement in changes:
            raw = bytearray(good)
            raw[offset:offset + len(replacement)] = replacement
            with self.subTest(offset=offset), self.assertRaises((avb.AvbImageSetError, avb.envelope.ImageInspectionError)):
                avb.parse_vbmeta(bytes(raw))

    def test_footer_overlap_sparse_image_and_payload_extent_mismatch_are_rejected(self):
        payload = boot_payload("init_boot")
        good = with_footer(payload, vbmeta([hash_descriptor("init_boot", payload)]))
        variants = []
        raw = bytearray(good)
        raw[:4] = b"\x3a\xff\x26\xed"
        variants.append(bytes(raw))
        raw = bytearray(good)
        struct.pack_into(">Q", raw, len(raw) - 64 + 20, len(raw))
        variants.append(bytes(raw))
        raw = bytearray(good)
        struct.pack_into("<I", raw, 12, 8193)
        variants.append(bytes(raw))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "image.img"
            for index, raw in enumerate(variants):
                path.write_bytes(raw)
                with self.subTest(index=index), self.assertRaises((avb.AvbImageSetError, avb.envelope.ImageInspectionError)):
                    avb.read_image_metadata(path, "init_boot", len(raw))

    def test_dtbo_entries_cannot_point_outside_authenticated_payload(self):
        payload = bytearray(dtbo_payload())
        struct.pack_into(">I", payload, 36, len(payload) + 4096)
        raw = with_footer(payload, vbmeta([hash_descriptor("dtbo", payload)]))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "dtbo.img"
            path.write_bytes(raw)
            with self.assertRaises(avb.AvbImageSetError):
                avb.read_image_metadata(path, "dtbo", len(raw))

    def test_vendor_boot_fragment_cannot_escape_declared_ramdisk(self):
        payload = bytearray(vendor_boot_payload())
        struct.pack_into("<I", payload, 3 * 4096 + 4, 4096)
        raw = with_footer(payload, vbmeta([hash_descriptor("vendor_boot", payload)]))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "vendor_boot.img"
            path.write_bytes(raw)
            with self.assertRaises(avb.AvbImageSetError):
                avb.read_image_metadata(path, "vendor_boot", len(raw))


class PublicProfileTests(NoNativeTests):
    def test_public_profile_pins_evidence_and_the_android_17_partition_closure(self):
        profile, digest = avb.load_profile()
        self.assertEqual(len(profile["image_budgets"]), 17)
        self.assertEqual(profile["platform"], {"branch": "bka", "release_config": "bp4a"})
        self.assertEqual(profile["chain_locations"], {"boot": 3, "recovery": 1, "vbmeta_system": 2})
        self.assertEqual(profile["working76"]["image"]["sha256"],
                         "a130ba7517c5c3bcb928b6c4e5c5ac24f5c6877011f3a95a02fa031fc0bb018e")
        self.assertEqual(len(digest), 64)
        self.assertFalse(profile["limits"]["full_rom_ready"])

    def test_successor_system_ext_budget_is_measured_and_group_bounded(self):
        profile, _ = avb.load_profile()
        override = profile["dynamic_logical_budget_overrides"]["system_ext"]
        self.assertEqual(profile["image_budgets"]["system_ext"], 713158656)
        self.assertEqual(avb.image_budget(profile, "system_ext"), 778199040)
        self.assertEqual(override["measured_image"], {
            "sha256": "c75d16fa4d06d2d30089cf469df9d845410cbd66446d4018cbec667c24521cc4",
            "size_bytes": 778199040})
        self.assertEqual(override["additional_measured_images"], [{
            "measured_image": {
                "sha256": "707442120ef680143b653d765c6148617482fa196b951998844d7ed8edfa7432",
                "size_bytes": 778190848},
            "admission_record": {
                "path": "artifacts/build-validation/feature-successor-f9e-package-admit-v1/admission.json",
                "sha256": "aae261fc3bc3974a280426ad7a1711698ee7d5c476a1e8806b4e45b78ad505c7",
                "size_bytes": 14226},
            "build_number": "nezha.f9e30611efe01b882f9ed0cb"}])
        avb.validate_image_budget(profile, "system_ext", override["measured_image"])
        avb.validate_image_budget(profile, "system_ext",
                                  override["additional_measured_images"][0]["measured_image"])
        with self.assertRaises(avb.AvbImageSetError):
            avb.validate_image_budget(profile, "system_ext", {
                "sha256": "0" * 64, "size_bytes": 778190848})
        admitted = {"mi_ext": 111198208, "odm": 4767621120, "product": 2200776704,
                    "system": 596484096, "system_dlkm": 8413184,
                    "system_ext": 778199040, "vendor": 959709184,
                    "vendor_dlkm": 54108160}
        self.assertEqual(sum(admitted.values()), 9476509696)
        self.assertLessEqual(sum(admitted.values()), profile["logical_group_budget"])

    def test_profile_rejects_unbounded_or_unproven_dynamic_override(self):
        original = json.loads(avb.PROFILE.read_text())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "profile.json"
            for mutate in (lambda p: p["dynamic_logical_budget_overrides"]["system_ext"].update(
                                maximum_size_bytes=p["logical_group_budget"] + 4096),
                           lambda p: p["dynamic_logical_budget_overrides"].update(
                                product=deepcopy(p["dynamic_logical_budget_overrides"]["system_ext"])),
                           lambda p: p["dynamic_logical_budget_overrides"]["system_ext"]["admission_record"].update(
                                sha256="0" * 64),
                           lambda p: p["dynamic_logical_budget_overrides"]["system_ext"]["additional_measured_images"][0]["measured_image"].update(
                                sha256="0" * 64),
                           lambda p: p["dynamic_logical_budget_overrides"]["system_ext"]["additional_measured_images"].append(
                                deepcopy(p["dynamic_logical_budget_overrides"]["system_ext"]["additional_measured_images"][0]))):
                profile = deepcopy(original)
                mutate(profile)
                path.write_text(json.dumps(profile))
                with mock.patch.object(avb, "PROFILE", path), self.assertRaises(avb.AvbImageSetError):
                    avb.load_profile()

    def test_profile_rejects_boolean_schema_and_changed_chain_topology(self):
        original = json.loads(avb.PROFILE.read_text())
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary).resolve() / "profile.json"
            for mutate in (lambda p: p.update(schema_version=True),
                           lambda p: p["chain_locations"].update(boot=4),
                           lambda p: p["descriptor_owners"].update(vendor="vbmeta_system")):
                profile = deepcopy(original)
                mutate(profile)
                path.write_text(json.dumps(profile))
                with self.subTest(profile=profile["chain_locations"]), mock.patch.object(avb, "PROFILE", path):
                    with self.assertRaises(avb.AvbImageSetError):
                        avb.load_profile()


if __name__ == "__main__":
    unittest.main()
