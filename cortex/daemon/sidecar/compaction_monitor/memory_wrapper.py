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

# Load the standard C library (glibc). On Linux it's libc.so.6.
_libc = None
try:
    if os.name == "posix":
        # On Linux, malloc_trim is in libc.so.6.
        # On macOS, libc.dylib exists but does NOT contain malloc_trim or mallinfo2.
        _libc_name = "libc.so.6" if os.uname().sysname != "Darwin" else "libc.dylib"
        _libc = ctypes.CDLL(_libc_name, use_errno=True)
except Exception:
    _libc = None

# Symbols availability
HAS_MALLOC_TRIM = False
HAS_MALLINFO2 = False

if _libc:
    try:
        _libc.malloc_trim.argtypes = [ctypes.c_size_t]
        _libc.malloc_trim.restype = ctypes.c_int
        HAS_MALLOC_TRIM = True
    except AttributeError:
        pass

    try:

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
        HAS_MALLINFO2 = True
    except AttributeError:
        pass


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
        ``1`` on success, ``0`` on failure. Returns 0 if not supported.
    """
    if not HAS_MALLOC_TRIM:
        return 0
    try:
        res = _libc.malloc_trim(pad)
        return res
    except Exception:
        return 0


@dataclass(frozen=True)
class MallInfo2:
    """Python representation of ``struct mallinfo2``."""

    arena: int = 0
    ordblks: int = 0
    smblks: int = 0
    hblks: int = 0
    hblkhd: int = 0
    usmblks: int = 0
    fsmblks: int = 0
    uordblks: int = 0
    fordblks: int = 0
    keepcost: int = 0

    @staticmethod
    def from_c() -> "MallInfo2":
        """Fetch the current mallinfo2 from the C allocator."""
        if not HAS_MALLINFO2:
            return MallInfo2()
        try:
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
        except Exception:
            return MallInfo2()


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
