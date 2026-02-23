"""memory_wrapper.py

Low‑level memory‑reclamation utilities for the Compaction Monitor sidecar.
Provides a thin `ctypes` wrapper around the glibc functions:
- `malloc_trim(0)` – asks the allocator to release free pages back to the OS.
- `mallinfo2()` – returns a `struct mallinfo2` with detailed arena statistics.

The wrapper returns a Python `dataclass` `MallInfo2` for ergonomic access.
"""

import ctypes
import os
from dataclasses import dataclass

# Load the standard C library (glibc). On macOS the equivalent is `libc.dylib`.
_libc_name = "libc.so.6" if os.name == "posix" and os.uname().sysname != "Darwin" else "libc.dylib"
_libc = ctypes.CDLL(_libc_name, use_errno=True)

# ---------------------------------------------------------------------------
# malloc_trim
# ---------------------------------------------------------------------------
_libc.malloc_trim.argtypes = [ctypes.c_size_t]
_libc.malloc_trim.restype = ctypes.c_int


def malloc_trim(pad: int = 0) -> int:
    """Force the allocator to release free pages.

    Parameters
    ----------
    pad: int, optional
        Number of bytes to keep at the top of the heap. The default ``0``
        asks glibc to release *all* possible pages.

    Returns
    -------
    int
        ``1`` on success, ``0`` on failure. On error ``errno`` is set.
    """
    res = _libc.malloc_trim(pad)
    if res == 0:
        err = ctypes.get_errno()
        raise OSError(err, os.strerror(err))
    return res


# ---------------------------------------------------------------------------
# mallinfo2 – modern 64‑bit aware structure
# ---------------------------------------------------------------------------
class _MallInfo2Struct(ctypes.Structure):
    _fields_ = [
        ("arena", ctypes.c_size_t),
        ("ordblks", ctypes.c_size_t),
        ("smblks", ctypes.c_size_t),
        ("hblks", ctypes.c_size_t),
        ("hblkhd", ctypes.c_size_t),
        ("usmblks", ctypes.c_size_t),
        ("fsmblks", ctypes.c_size_t),
        ("uordblks", ctypes.c_size_t),
        ("fordblks", ctypes.c_size_t),
        ("keepcost", ctypes.c_size_t),
    ]


_libc.mallinfo2.argtypes = []
_libc.mallinfo2.restype = _MallInfo2Struct


@dataclass(frozen=True)
class MallInfo2:
    """Python representation of ``struct mallinfo2``.

    Attributes correspond one‑to‑one with the C fields and are all ``int``
    (64‑bit on modern platforms).
    """

    arena: int
    ordblks: int
    smblks: int
    hblks: int
    hblkhd: int
    usmblks: int
    fsmblks: int
    uordblks: int
    fordblks: int
    keepcost: int

    @staticmethod
    def from_c() -> "MallInfo2":
        """Fetch the current mallinfo2 from the C allocator.

        Returns
        -------
        MallInfo2
            Populated dataclass instance.
        """
        raw = _libc.mallinfo2()
        return MallInfo2(
            arena=raw.arena,
            ordblks=raw.ordblks,
            smblks=raw.smblks,
            hblks=raw.hblks,
            hblkhd=raw.hblkhd,
            usmblks=raw.usmblks,
            fsmblks=raw.fsmblks,
            uordblks=raw.uordblks,
            fordblks=raw.fordblks,
            keepcost=raw.keepcost,
        )


def get_mallinfo2() -> MallInfo2:
    """Convenience wrapper that returns the current ``MallInfo2`` instance."""
    return MallInfo2.from_c()


# ---------------------------------------------------------------------------
# Simple sanity test (executed only when run as a script)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("mallinfo2:", get_mallinfo2())
    try:
        malloc_trim()
        print("malloc_trim succeeded")
    except OSError as exc:
        print("malloc_trim failed:", exc)
