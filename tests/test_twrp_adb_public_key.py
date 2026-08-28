"""Only synthetic wire values and temporary synthetic files; no real keys."""

import base64
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch

from scripts import twrp_adb_public_key as candidate


def synthetic_wire(*, words=64, n0inv=0xAAAAAAAB, modulus=(1 << 2048) - 3,
                   rr=9, exponent=65537):
    # N=R-3 is deliberately synthetic, not an RSA key pair. R mod N=3, so
    # RR=9. Its low word is-3; inverse(3,2**32)=0xAAAAAAAB, giving n0inv.
    # These golden values do not repeat the parser's pow computations.
    return struct.pack("<II256s256sI", words, n0inv,
                       modulus.to_bytes(256, "little"), rr.to_bytes(256, "little"), exponent)


def synthetic_line(**values):
    return base64.b64encode(synthetic_wire(**values))


class EncodingTests(unittest.TestCase):
    def test_known_synthetic_montgomery_vector(self):
        raw = synthetic_wire()
        self.assertEqual(len(raw), 524)
        self.assertEqual(raw[:8], b"\x40\x00\x00\x00\xab\xaa\xaa\xaa")
        self.assertEqual(raw[8:264], b"\xfd" + b"\xff" * 255)
        self.assertEqual(raw[264:520], b"\x09" + b"\x00" * 255)
        self.assertEqual(raw[520:], b"\x01\x00\x01\x00")
        result = candidate.validate_public_key(synthetic_line())
        self.assertEqual(result.canonical, synthetic_line() + b"\n")
        self.assertEqual(len(result.canonical), 701)

    def test_second_independent_synthetic_vector(self):
        # N=R-5 =>RR25 andn0inv inverse5=0xCCCCCCCD.
        line = synthetic_line(n0inv=0xCCCCCCCD, modulus=(1 << 2048) - 5, rr=25)
        self.assertEqual(candidate.validate_public_key(line).canonical, line + b"\n")

    def test_comments_and_line_endings_have_identical_canonical_digest(self):
        canonical = synthetic_line() + b"\n"
        for suffix in (b"", b"\n", b"\r\n", b" synthetic-user@synthetic-host",
                       b"\tsynthetic-user@synthetic-host\r\n", b" comment with spaces\n", b"  \t"):
            result = candidate.validate_public_key(synthetic_line() + suffix)
            self.assertEqual(result.canonical, canonical)
            self.assertEqual(result.provenance(), {"adb_public_key_sha256": hashlib.sha256(canonical).hexdigest()})
            self.assertNotIn("synthetic-user", repr(result))
            self.assertNotIn("synthetic-user", json.dumps(result.provenance()))
            self.assertNotIn(synthetic_line().decode(), repr(result))

    def test_private_pem_ssh_and_unrelated_formats_are_rejected(self):
        for data in (b"-----BEGIN PRIVATE KEY-----\nSYNTHETIC-NONKEY\n-----END PRIVATE KEY-----\n",
                     b"-----BEGIN RSA PRIVATE KEY----- SYNTHETIC-NONKEY",
                     b"-----BEGIN PUBLIC KEY----- SYNTHETIC-NONKEY",
                     b"ssh-rsa SYNTHETIC-NONKEY comment", b"ssh-ed25519 SYNTHETIC-NONKEY",
                     b"ecdsa-sha2-nistp256 SYNTHETIC-NONKEY", b"<RSAKeyValue>synthetic</RSAKeyValue>"):
            with self.subTest(data=data.split(b" ")[0]), self.assertRaises(candidate.PublicKeyError):
                candidate.validate_public_key(data)

    def test_empty_oversized_wrong_type_and_control_bytes_are_rejected(self):
        for data in (b"", None, "text", bytearray(synthetic_line()), b"x" * 4097,
                     synthetic_line() + b"\x00", synthetic_line() + b"\n\n",
                     synthetic_line() + b"\r", synthetic_line() + b"\v",
                     b" " + synthetic_line(), b"\t" + synthetic_line(),
                     synthetic_line() + " identifying-\u2603".encode()):
            with self.subTest(type=type(data).__name__), self.assertRaises(candidate.PublicKeyError):
                candidate.validate_public_key(data)

    def test_comment_limit_and_multiple_keys(self):
        self.assertEqual(candidate.validate_public_key(synthetic_line() + b" " + b"x" * 512).canonical,
                         synthetic_line() + b"\n")
        for data in (synthetic_line() + b" " + b"x" * 513,
                     synthetic_line() + b"\n" + synthetic_line(),
                     synthetic_line() + b" " + synthetic_line(),
                     synthetic_line() + b"\t" + synthetic_line(),
                     synthetic_line() + b" ssh-ed25519 SYNTHETIC-NONKEY"):
            with self.assertRaises(candidate.PublicKeyError):
                candidate.validate_public_key(data)

    def test_base64_length_padding_alphabet_and_pad_bits(self):
        line = synthetic_line()
        alphabet = b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
        # 524B has two final decoded bytes: changing only its unused pad bits
        # decodes identically in permissive Base64, but is not canonical.
        last = alphabet.index(line[-2])
        noncanonical = line[:-2] + bytes([alphabet[last + 1]]) + b"="
        self.assertEqual(base64.b64decode(noncanonical), synthetic_wire())
        for data in (line[:-1], line + b"=", b"!" + line[1:],
                     line[:300] + b"\n" + line[300:], noncanonical,
                     base64.b64encode(synthetic_wire()[:-1]),
                     base64.b64encode(synthetic_wire() + b"\0")):
            with self.subTest(length=len(data)), self.assertRaises(candidate.PublicKeyError):
                candidate.validate_public_key(data)

    def test_word_count_modulus_and_exponent_policy(self):
        for change in ({"words": 0}, {"words": 63}, {"words": 65},
                       {"modulus": (1 << 2048) - 4}, {"modulus": (1 << 2047) - 3},
                       {"modulus": 0}, {"modulus": (1 << 2048) - 1},
                       {"exponent": 0}, {"exponent": 1}, {"exponent": 2},
                       {"exponent": 3}, {"exponent": 17}, {"exponent": 0xFFFFFFFF}):
            with self.subTest(change=change), self.assertRaises(candidate.PublicKeyError):
                candidate.validate_public_key(synthetic_line(**change))
        # 3 and17 can be encoded and used by Android's broader RSA decoder;
        # their rejection here is the explicit F4 personal-build policy.

    def test_montgomery_precomputations_must_match(self):
        for change in ({"n0inv": 0}, {"n0inv": 0x55555555}, {"n0inv": 0xAAAAAAA9},
                       {"rr": 0}, {"rr": 8}, {"rr": 10}, {"rr": (1 << 2048) - 3}):
            with self.subTest(change=change), self.assertRaises(candidate.PublicKeyError):
                candidate.validate_public_key(synthetic_line(**change))
        wrong_endian = bytearray(synthetic_wire())
        wrong_endian[4:8] = wrong_endian[4:8][::-1]
        with self.assertRaises(candidate.PublicKeyError):
            candidate.validate_public_key(base64.b64encode(wrong_endian))

    def test_errors_do_not_echo_input_or_comments(self):
        secret_comment = b"synthetic-person@example.invalid"
        try:
            candidate.validate_public_key(b"SYNTHETIC_BAD_TOKEN " + secret_comment)
        except candidate.PublicKeyError as error:
            self.assertNotIn(secret_comment.decode(), str(error))
            self.assertNotIn("SYNTHETIC_BAD_TOKEN", str(error))
        else:
            self.fail("Malformed public input was accepted")


class ExplicitFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="synthetic-adb-public-key-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.path = self.root / "explicit-synthetic.pub"
        self.path.write_bytes(synthetic_line() + b" synthetic-only@invalid\n")

    def test_reads_only_explicit_synthetic_regular_file(self):
        result = candidate.read_explicit_public_key(self.path)
        self.assertEqual(result.canonical, synthetic_line() + b"\n")
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), [self.path.name])

    def test_relative_missing_and_traversal_paths_fail_without_discovery(self):
        for path in ("", "relative.pub", Path("relative.pub"), None, self.root / "absent.pub",
                     str(self.root / ".." / self.path.name)):
            with self.subTest(kind=type(path).__name__), self.assertRaises(candidate.PublicKeyError):
                candidate.read_explicit_public_key(path)

    def test_final_symlink_and_directory_symlink_are_rejected(self):
        link = self.root / "synthetic-link.pub"
        link.symlink_to(self.path)
        directory = self.root / "synthetic-directory-link"
        directory.symlink_to(self.root, target_is_directory=True)
        for path in (link, directory / self.path.name):
            with self.assertRaises(candidate.PublicKeyError):
                candidate.read_explicit_public_key(path)

    def test_hardlinks_directories_fifo_empty_and_large_files_are_rejected(self):
        link = self.root / "synthetic-hardlink.pub"
        os.link(self.path, link)
        fifo = self.root / "synthetic-fifo.pub"
        os.mkfifo(fifo)
        empty = self.root / "synthetic-empty.pub"
        empty.write_bytes(b"")
        large = self.root / "synthetic-large.pub"
        large.write_bytes(b"x" * 4097)
        for path in (self.path, link, self.root, fifo, empty, large):
            with self.assertRaises(candidate.PublicKeyError):
                candidate.read_explicit_public_key(path)

    def test_a_changed_file_is_rejected(self):
        real_read = os.read
        changed = False
        def modify_after_read(fd, size):
            nonlocal changed
            data = real_read(fd, size)
            if not changed:
                self.path.write_bytes(synthetic_line() + b" changed-synthetic-comment\n")
                changed = True
            return data
        with patch.object(candidate.os, "read", side_effect=modify_after_read):
            with self.assertRaises(candidate.PublicKeyError):
                candidate.read_explicit_public_key(self.path)

    def test_file_error_does_not_disclose_path(self):
        path = self.root / "synthetic-identifying-name.pub"
        with self.assertRaises(candidate.PublicKeyError) as caught:
            candidate.read_explicit_public_key(path)
        self.assertNotIn(str(path), str(caught.exception))
        self.assertNotIn(path.name, str(caught.exception))

    def test_cli_requires_explicit_option_and_never_reads_a_default(self):
        with patch.object(candidate, "read_explicit_public_key") as read:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(candidate.main([]), 2)
            read.assert_not_called()

    def test_cli_rejects_extra_duplicate_and_misspelled_arguments_without_echoing_paths(self):
        identifying = str(self.root / "synthetic-identifying-public-key.pub")
        for args in ([identifying], ["--unknown", identifying],
                     ["--public-key", identifying, "extra-identifying-token"],
                     ["--public-key", identifying, "--public-key", identifying],
                     ["--pub", identifying], ["--public-key"]):
            stdout, stderr = io.StringIO(), io.StringIO()
            with patch.object(candidate, "read_explicit_public_key") as read:
                with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                    self.assertEqual(candidate.main(args), 2)
                read.assert_not_called()
            self.assertEqual(stdout.getvalue(), "")
            self.assertNotIn(identifying, stderr.getvalue())
            self.assertNotIn("extra-identifying-token", stderr.getvalue())

    def test_cli_emits_only_digest_for_explicit_synthetic_input(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            result = candidate.main(["--public-key", str(self.path)])
        self.assertEqual(result, 0)
        self.assertEqual(stderr.getvalue(), "")
        self.assertEqual(json.loads(stdout.getvalue()), candidate.validate_public_key(synthetic_line()).provenance())
        for identifying in ("synthetic-only", str(self.path), synthetic_line().decode()):
            self.assertNotIn(identifying, stdout.getvalue())


if __name__ == "__main__":
    unittest.main()
