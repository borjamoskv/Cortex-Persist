import time

# B60 Scaling Factor: 60_000 (Allows ms precision when representing seconds, and fine fractions)
B60_SCALE = 60_000

class B60Time:
    """Deterministic Time represented strictly as scaled integers (Ticks)."""
    __slots__ = ("_ticks",)

    def __init__(self, ticks: int):
        if not isinstance(ticks, int):
            raise TypeError("B60Time must be initialized with pure integers.")
        self._ticks = ticks

    @classmethod
    def now(cls) -> "B60Time":
        return cls(int(time.time() * B60_SCALE))
        
    @classmethod
    def from_ms(cls, ms: int) -> "B60Time":
        # 1 ms = 60 ticks (since B60_SCALE is 60000, 1 sec = 60000, 1 ms = 60)
        return cls(ms * 60)
        
    @classmethod
    def from_seconds(cls, sec: int) -> "B60Time":
        return cls(sec * B60_SCALE)

    @property
    def ticks(self) -> int:
        return self._ticks

    def to_float_seconds(self) -> float:
        """Escape hatch for legacy compatibility only. Epistemic Taint."""
        return self._ticks / B60_SCALE

    def __add__(self, other: "B60Time") -> "B60Time":
        return B60Time(self._ticks + other._ticks)
        
    def __sub__(self, other: "B60Time") -> "B60Time":
        return B60Time(self._ticks - other._ticks)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, B60Time):
            return NotImplemented
        return self._ticks == other._ticks
        
    def __lt__(self, other: "B60Time") -> bool:
        return self._ticks < other._ticks

    def __repr__(self) -> str:
        return f"B60Time({self._ticks})"


class B60Fraction:
    """Structural proportion using B60 scale to eliminate float rounding."""
    __slots__ = ("_scaled_value",)

    def __init__(self, scaled_value: int):
        if not isinstance(scaled_value, int):
            raise TypeError("B60Fraction must be initialized with pure integers.")
        self._scaled_value = scaled_value
        
    @classmethod
    def from_float_unsafe(cls, value: float) -> "B60Fraction":
        """Used strictly during migration. Converts a float to an internal scaled integer."""
        return cls(int(value * B60_SCALE))

    @property
    def scaled_value(self) -> int:
        return self._scaled_value

    def to_float_unsafe(self) -> float:
        return self._scaled_value / B60_SCALE

    def __add__(self, other: "B60Fraction") -> "B60Fraction":
        return B60Fraction(self._scaled_value + other._scaled_value)

    def __sub__(self, other: "B60Fraction") -> "B60Fraction":
        return B60Fraction(self._scaled_value - other._scaled_value)

    def __mul__(self, multiplier: int) -> "B60Fraction":
        return B60Fraction(self._scaled_value * multiplier)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, B60Fraction):
            return NotImplemented
        return self._scaled_value == other._scaled_value

    def __repr__(self) -> str:
        return f"B60Fraction({self._scaled_value}/{B60_SCALE})"
