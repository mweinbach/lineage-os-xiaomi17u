#!/usr/bin/env python3
"""Inspect image ELF files using native Python; do not execute foreign binaries."""

from pathlib import Path
import stat
import struct


MARKER = b"evolution-apple-container-builder-v1\n"
LOADER = "/lib64/ld-linux-x86-64.so.2"


def elf_machine(header: bytes) -> int:
    if len(header) < 64 or header[:7] != b"\x7fELF\x02\x01\x01":
        raise ValueError("expected a complete ELF64 little-endian header")
    return struct.unpack_from("<H", header, 18)[0]


def check_elf(path: Path, machine: int, *, executable: bool = False) -> None:
    resolved = path.resolve(strict=True)
    details = resolved.stat()
    if not stat.S_ISREG(details.st_mode) or details.st_uid != 0 or details.st_mode & 0o022:
        raise ValueError(f"ELF must be a root-owned regular file without group/other writes: {path}")
    if executable and not details.st_mode & 0o111:
        raise ValueError(f"ELF must be executable: {path}")
    with resolved.open("rb") as stream:
        if elf_machine(stream.read(64)) != machine:
            raise ValueError(f"unexpected ELF architecture: {path}")


def check_marker(path: Path) -> None:
    details = path.lstat()
    if (
        not stat.S_ISREG(details.st_mode)
        or details.st_uid != 0
        or stat.S_IMODE(details.st_mode) not in (0o444, 0o644)
        or path.read_bytes() != MARKER
    ):
        raise ValueError("invalid builder marker ownership, mode, type, or contents")


def main() -> None:
    check_marker(Path("/opt/evolution/apple-container-builder"))
    for filename in ("/usr/bin/python3", "/usr/bin/git", "/usr/bin/x86_64-linux-gnu-gcc"):
        check_elf(Path(filename), 183, executable=True)  # EM_AARCH64
    for filename in (
        LOADER,
        "/usr/lib/x86_64-linux-gnu/libc.so.6",
        "/usr/lib/x86_64-linux-gnu/libstdc++.so.6",
        "/usr/lib/x86_64-linux-gnu/libz.so.1",
    ):
        check_elf(Path(filename), 62)  # EM_X86_64
    check_elf(Path("/opt/evolution/bin/rosetta-probe"), 62, executable=True)
    print("native ARM64 tools and amd64 ELF runtime headers verified; Rosetta execution still required")


if __name__ == "__main__":
    main()
