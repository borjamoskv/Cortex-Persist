# [C5-REAL] Exergy-Maximized — Babylon-60 Integer Architecture
# Author: Borja Moskv (borjamoskv)
"""
Babylon-60 fixed-point integer arithmetic and contiguous memory primitives.

Eliminates float64 accumulation entropy (AGENTS.md §3, BABYLON-60 Epistemology).
Uses native Rust implementation when available, pure Python fallback otherwise.
"""
from __future__ import annotations

__all__ = [
    "SCALE",
    "Babylon60",
    "Babylon60Vector",
    "EpistemicTrajectory",
    "StaticBuffer",
    "causal_distance",
    "hash_distance_rollup",
    "manhattan_distance",
]

# --------------------------------------------------------------------------- #
# Constants
# --------------------------------------------------------------------------- #

SCALE = 216_000  # 60^3 — Canonical Base-60 fixed-point scale factor

# --------------------------------------------------------------------------- #
# Native Rust binding probe
# --------------------------------------------------------------------------- #

try:
    from cortex_rs import Babylon60 as _NativeBabylon60  # type: ignore[import-untyped]

    HAS_NATIVE = True
except ImportError:
    _NativeBabylon60 = None
    HAS_NATIVE = False

# --------------------------------------------------------------------------- #
# i64 overflow guard
# --------------------------------------------------------------------------- #

_I64_MAX = (1 << 63) - 1
_I64_MIN = -(1 << 63)


def _check_i64(value: int, op: str = "result") -> int:
    if value > _I64_MAX or value < _I64_MIN:
        raise OverflowError(f"Babylon60 {op} overflows i64: {value}")
    return value


# --------------------------------------------------------------------------- #
# Pure-Python Babylon60
# --------------------------------------------------------------------------- #


class _PurePythonBabylon60:
    """Base-60 fixed-point integer. Zero float accumulation."""

    __slots__ = ("value",)

    def __init__(self, value: int) -> None:
        self.value = _check_i64(value, "init")

    # -- constructors -------------------------------------------------------- #

    @classmethod
    def from_float(cls, f: float) -> _PurePythonBabylon60:
        return cls(_check_i64(round(f * SCALE), "from_float"))

    @classmethod
    def from_int(cls, i: int) -> _PurePythonBabylon60:
        return cls(_check_i64(i * SCALE, "from_int"))

    # -- conversion ---------------------------------------------------------- #

    def to_float(self) -> float:
        return self.value / SCALE

    def __float__(self) -> float:
        return self.to_float()

    # -- arithmetic ---------------------------------------------------------- #

    def add(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        return _PurePythonBabylon60(_check_i64(self.value + other.value, "add"))

    def sub(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        return _PurePythonBabylon60(_check_i64(self.value - other.value, "sub"))

    def mul(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        return _PurePythonBabylon60(
            _check_i64((self.value * other.value) // SCALE, "mul")
        )

    def div(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        if other.value == 0:
            raise ZeroDivisionError("Babylon60 division by zero")
        return _PurePythonBabylon60(
            _check_i64((self.value * SCALE) // other.value, "div")
        )

    def distance(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        return _PurePythonBabylon60(abs(self.value - other.value))

    # -- operators ----------------------------------------------------------- #

    def __add__(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        return self.add(other)

    def __sub__(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        return self.sub(other)

    def __mul__(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        return self.mul(other)

    def __truediv__(self, other: int | float | _PurePythonBabylon60) -> _PurePythonBabylon60:
        return self.div(other)

    def __radd__(self, other: int | float) -> _PurePythonBabylon60:
        return self.add(other)

    def __rsub__(self, other: int | float) -> _PurePythonBabylon60:
        return _PurePythonBabylon60.from_float(float(other)).sub(self)

    def __rmul__(self, other: int | float) -> _PurePythonBabylon60:
        return self.mul(other)

    def __rtruediv__(self, other: int | float) -> _PurePythonBabylon60:
        return _PurePythonBabylon60.from_float(float(other)).div(self)

    # -- comparison ---------------------------------------------------------- #

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        if not isinstance(other, _PurePythonBabylon60):
            return NotImplemented
        return self.value == other.value

    def __lt__(self, other: int | float | _PurePythonBabylon60) -> bool:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        return self.value < other.value

    def __le__(self, other: int | float | _PurePythonBabylon60) -> bool:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        return self.value <= other.value

    def __gt__(self, other: int | float | _PurePythonBabylon60) -> bool:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        return self.value > other.value

    def __ge__(self, other: int | float | _PurePythonBabylon60) -> bool:
        if isinstance(other, (int, float)):
            other = _PurePythonBabylon60.from_float(float(other))
        return self.value >= other.value

    def __hash__(self) -> int:
        return hash(self.value)

    # -- repr ---------------------------------------------------------------- #

    def __repr__(self) -> str:
        return f"Babylon60({self.value})"

    def __str__(self) -> str:
        return f"B60({self.to_float():.6f})"


from typing import TYPE_CHECKING

# --------------------------------------------------------------------------- #
# Resolve implementation: Rust-native or pure Python
# --------------------------------------------------------------------------- #

if TYPE_CHECKING:
    Babylon60 = _PurePythonBabylon60
else:
    Babylon60 = _NativeBabylon60 if HAS_NATIVE else _PurePythonBabylon60


# --------------------------------------------------------------------------- #
# StaticBuffer — Pre-allocated contiguous int64
# --------------------------------------------------------------------------- #


class StaticBuffer:
    """Pre-allocated contiguous int64 buffer. Zero GC pressure in hot paths."""

    __slots__ = ("_buf", "_capacity", "_len")

    def __init__(self, capacity: int) -> None:
        import array as _array

        self._buf = _array.array("q", bytes(capacity * 8))  # Pre-allocate zeroed
        self._capacity = capacity
        self._len = 0

    def push(self, value: int) -> None:
        if self._len >= self._capacity:
            raise OverflowError(
                f"StaticBuffer full: {self._len}/{self._capacity}"
            )
        self._buf[self._len] = value
        self._len += 1

    def reset(self) -> None:
        """O(1) logical reset — no deallocation."""
        self._len = 0

    def __len__(self) -> int:
        return self._len

    def __getitem__(self, index: int) -> int:
        if index < 0 or index >= self._len:
            raise IndexError(
                f"StaticBuffer index {index} out of range [0, {self._len})"
            )
        return self._buf[index]

    def to_list(self) -> list[int]:
        return [self._buf[i] for i in range(self._len)]

    def as_memoryview(self) -> memoryview:
        """Zero-copy view of the active region."""
        return memoryview(self._buf)[: self._len]


# --------------------------------------------------------------------------- #
# Babylon60Vector — Contiguous Babylon60 backed by StaticBuffer
# --------------------------------------------------------------------------- #


class Babylon60Vector:
    """Contiguous Babylon60 vector backed by StaticBuffer."""

    __slots__ = ("_buffer",)

    def __init__(self, capacity: int) -> None:
        self._buffer = StaticBuffer(capacity)

    def push(self, b60: Babylon60) -> None:  # type: ignore[arg-type]
        if isinstance(b60, _PurePythonBabylon60):
            self._buffer.push(b60.value)
        else:
            # Native Rust Babylon60 exposes get_value()
            self._buffer.push(b60.get_value())

    def __len__(self) -> int:
        return len(self._buffer)

    def __getitem__(self, index: int) -> Babylon60:  # type: ignore[return-type]
        return Babylon60(self._buffer[index])

    def reset(self) -> None:
        self._buffer.reset()


# --------------------------------------------------------------------------- #
# Distance & Hash functions — Pure integer arithmetic
# --------------------------------------------------------------------------- #


def manhattan_distance(a: Babylon60Vector, b: Babylon60Vector) -> int:
    """L1 distance. Zero intermediate allocation."""
    if len(a) != len(b):
        raise ValueError(f"Vector length mismatch: {len(a)} vs {len(b)}")
    total = 0
    for i in range(len(a)):
        total += abs(a._buffer[i] - b._buffer[i])
    return total


def causal_distance(
    ancestry_overlap: int,
    ledger_overlap: int,
    witness_overlap: int,
    temporal_overlap: int,
) -> int:
    """Weighted causal distance. Pure integer arithmetic."""
    MAX_DIVERGENCE = 1000
    score = (
        ancestry_overlap * 60
        + witness_overlap * 30
        + ledger_overlap * 10
        + temporal_overlap
    )
    return 0 if score > MAX_DIVERGENCE else MAX_DIVERGENCE - score


def hash_distance_rollup(root_hash: int, distances: list[int]) -> int:
    """FNV-1a deterministic hash rollup. Pure integer."""
    FNV_PRIME = 16777619
    MASK_32 = 0xFFFFFFFF
    current = root_hash & MASK_32
    for d in distances:
        current = (current ^ (d & 0xFFFF)) & MASK_32
        current = (current * FNV_PRIME) & MASK_32
    return current


# --------------------------------------------------------------------------- #
# EpistemicTrajectory — Sequence with Merkle rollup
# --------------------------------------------------------------------------- #


class EpistemicTrajectory:
    """Sequence of Babylon60Vectors with integrated Merkle rollup."""

    __slots__ = ("_steps", "_merkle_root")

    def __init__(self, initial_hash: int = 0) -> None:
        self._steps: list[Babylon60Vector] = []
        self._merkle_root = initial_hash

    def append(self, vector: Babylon60Vector) -> None:
        distances = vector._buffer.to_list()
        self._merkle_root = hash_distance_rollup(self._merkle_root, distances)
        self._steps.append(vector)

    @property
    def merkle_root(self) -> int:
        return self._merkle_root

    def __len__(self) -> int:
        return len(self._steps)
