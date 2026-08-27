"""Publish prepared artifact directories without replacing existing paths."""

import ctypes
import errno
import os
import sys


def publish_new_directory(staging, destination):
    """Atomically rename on macOS/Linux, failing if any destination exists.

    Callers own staging, parent-path validation, and failure cleanup. Both paths
    must be on the same filesystem. Never fall back to an overwriting rename if
    the operating system or filesystem lacks the exclusive operation.
    """
    old, new = os.fsencode(staging), os.fsencode(destination)
    if sys.platform not in ("darwin", "linux"):
        raise OSError(errno.ENOTSUP, "atomic exclusive publication requires macOS or Linux")
    library = ctypes.CDLL(None, use_errno=True)
    try:
        if sys.platform == "darwin":
            rename = library.renamex_np
            rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
            arguments = (old, new, 0x00000004)  # Apple sys/stdio.h: RENAME_EXCL
        else:
            rename = library.renameat2
            rename.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                               ctypes.c_char_p, ctypes.c_uint]
            arguments = (-100, old, -100, new, 1)  # AT_FDCWD, RENAME_NOREPLACE
    except AttributeError as exc:
        raise OSError(errno.ENOSYS, "exclusive rename is unavailable; publication refused") from exc
    rename.restype = ctypes.c_int
    if rename(*arguments) != 0:
        error = ctypes.get_errno() or errno.EIO
        raise OSError(error, os.strerror(error), os.fspath(destination))
