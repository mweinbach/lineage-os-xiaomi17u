"""Opt-in Android public ADB key validation; no automatic discovery.

This checks the Android RSA wire encoding and stricter personal-build policy,
not possession of the corresponding private key or the strength of its primes.
No key is generated, installed into an image, or accepted from ambient settings.
"""

import argparse
import base64
import binascii
from dataclasses import dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import struct
import sys


MAX_INPUT_BYTES = 4096
MAX_COMMENT_BYTES = 512
MODULUS_BYTES = 256
MODULUS_WORDS = 64
ENCODED_BYTES = 524
BASE64_BYTES = 700
PUBLIC_EXPONENT = 65537
WORD_RADIX = 1 << 32
_TOKEN = re.compile(rb"[A-Za-z0-9+/]{699}=")
_LINE = re.compile(rb"([^ \t]+)(?:[ \t]+([\x20-\x7e\t]*))?")


class PublicKeyError(ValueError):
    """An input was rejected; messages never contain input bytes or its path."""


@dataclass(frozen=True)
class ValidatedPublicKey:
    canonical: bytes = field(repr=False)

    @property
    def sha256(self):
        """Digest of the comment-free Base64 line including its final LF."""
        return hashlib.sha256(self.canonical).hexdigest()

    def provenance(self):
        """No identifying comment, input filename, user or hostname is retained."""
        return {"adb_public_key_sha256": self.sha256}


def validate_public_key(data):
    """Validate exactly one Android RSA2048/F4 public key and strip its comment.

    Exact length, full 2048-bit odd modulus, F4 exponent and matching Montgomery
    precomputations are this profile's policy, stricter than Android's decoder.
    The profile also rejects a modulus divisible by its public exponent; this
    conservative import rule is not a universal mathematical RSA requirement.
    Accept one optional ASCII comment (at most 512 bytes) and at most one final
    LF or CRLF. A second full Android key cannot fit the comment allowance.
    """
    if not isinstance(data, bytes) or not data or len(data) > MAX_INPUT_BYTES:
        raise PublicKeyError("Public-key input must be bounded nonempty bytes")
    if data.endswith(b"\r\n"):
        line = data[:-2]
    elif data.endswith(b"\n"):
        line = data[:-1]
    else:
        line = data
    if any(byte not in (9,) and not 32 <= byte <= 126 for byte in line):
        raise PublicKeyError("Expected one ASCII Android public-key line")
    match = _LINE.fullmatch(line)
    if not match:
        raise PublicKeyError("Expected one Android public-key token and optional comment")
    token, comment = match.groups()
    comment = comment or b""
    if len(comment) > MAX_COMMENT_BYTES:
        raise PublicKeyError("Public-key comment exceeds the allowed bound")
    if any(marker in line for marker in (b"-----BEGIN", b"-----END", b"ssh-rsa", b"ssh-ed25519", b"ecdsa-sha2-")):
        raise PublicKeyError("PEM, SSH and private-key formats are not accepted")
    if not _TOKEN.fullmatch(token):
        raise PublicKeyError("Expected canonical Android public-key Base64")
    try:
        encoded = base64.b64decode(token, validate=True)
    except (ValueError, binascii.Error):
        raise PublicKeyError("Malformed Android public-key Base64") from None
    if len(encoded) != ENCODED_BYTES or base64.b64encode(encoded) != token:
        raise PublicKeyError("Noncanonical Android public-key encoding")
    words, n0inv, modulus_bytes, rr_bytes, exponent = struct.unpack("<II256s256sI", encoded)
    if words != MODULUS_WORDS:
        raise PublicKeyError("Android public-key modulus must contain 64 words")
    modulus = int.from_bytes(modulus_bytes, "little")
    if modulus.bit_length() != MODULUS_BYTES * 8 or not modulus & 1:
        raise PublicKeyError("This profile requires a full-size odd RSA2048 modulus")
    if exponent != PUBLIC_EXPONENT:
        raise PublicKeyError("This profile requires the ADB host-generator exponent 65537")
    if modulus % exponent == 0:
        raise PublicKeyError("This profile rejects a modulus divisible by its public exponent")
    expected_n0inv = (-pow(modulus & (WORD_RADIX - 1), -1, WORD_RADIX)) % WORD_RADIX
    if n0inv != expected_n0inv:
        raise PublicKeyError("Android public-key n0inv is inconsistent")
    if int.from_bytes(rr_bytes, "little") != pow(2, MODULUS_BYTES * 16, modulus):
        raise PublicKeyError("Android public-key RR is inconsistent")
    return ValidatedPublicKey(base64.b64encode(encoded) + b"\n")


def read_explicit_public_key(path):
    """Read only an explicitly supplied absolute regular file, without symlinks.

    No default path, home lookup, environment lookup, filename search, fallback
    or private-key import exists. Nonblocking open avoids waiting on a FIFO;
    dirfd traversal rejects symlinks in every component. The caller must first
    obtain authorization for this exact public input. Tests use synthetic files.
    """
    if not isinstance(path, (str, Path)):
        raise PublicKeyError("An explicit absolute public-key path is required")
    path = Path(path)
    if not path.is_absolute() or ".." in path.parts or len(path.parts) < 2:
        raise PublicKeyError("An explicit absolute public-key path is required")
    if not all(hasattr(os, flag) for flag in ("O_NOFOLLOW", "O_DIRECTORY", "O_NONBLOCK")):
        raise PublicKeyError("Safe explicit-file reading is unsupported on this host")
    directory = key_fd = None
    try:
        directory = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        for component in path.parts[1:-1]:
            next_directory = os.open(component, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                     dir_fd=directory)
            os.close(directory)
            directory = next_directory
        key_fd = os.open(path.name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
        before = os.fstat(key_fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise PublicKeyError("Public-key input must be a regular file with one link")
        if not 0 < before.st_size <= MAX_INPUT_BYTES:
            raise PublicKeyError("Public-key file size is outside the allowed bound")
        chunks, remaining = [], MAX_INPUT_BYTES + 1
        while remaining:
            chunk = os.read(key_fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = b"".join(chunks)
        after = os.fstat(key_fd)
        identity = lambda s: (s.st_dev, s.st_ino, s.st_mode, s.st_nlink, s.st_size,
                              s.st_mtime_ns, s.st_ctime_ns, s.st_uid, s.st_gid)
        if identity(before) != identity(after) or len(data) != before.st_size:
            raise PublicKeyError("Public-key input changed while being read")
        return validate_public_key(data)
    except (OSError, ValueError) as error:
        if isinstance(error, PublicKeyError):
            raise
        raise PublicKeyError("Cannot read the explicitly supplied public-key input") from None
    finally:
        if key_fd is not None:
            os.close(key_fd)
        if directory is not None:
            os.close(directory)


class _PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default diagnostic can echo an identifying supplied path.
        raise PublicKeyError("Invalid arguments: supply --public-key exactly once")


def main(argv=None):
    parser = _PrivateArgumentParser(prog="adb-public-key-validator", allow_abbrev=False,
                                   description="Validate one explicitly authorized public ADB key; report only its canonical digest")
    parser.add_argument("--public-key", action="append", required=True,
                        help="Explicit absolute public-key file; no key discovery")
    try:
        args = parser.parse_args(argv)
        if len(args.public_key) != 1:
            raise PublicKeyError("Exactly one explicit public-key input is permitted")
        key = read_explicit_public_key(args.public_key[0])
    except PublicKeyError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(json.dumps(key.provenance(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
