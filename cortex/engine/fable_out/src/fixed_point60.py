from __future__ import annotations

from dataclasses import dataclass

from fable_library.array_ import Array
from fable_library.big_int import from_int64, to_int64
from fable_library.big_int import op_division as op_division_1
from fable_library.big_int import op_multiply as op_multiply_1
from fable_library.core import float64, int64
from fable_library.long import (
    from_number,
    op_addition,
    op_division,
    op_modulus,
    op_multiply,
    op_subtraction,
    to_number,
)
from fable_library.record import Record
from fable_library.reflection import TypeInfo, int64_type, record_type
from fable_library.string_ import printf, to_text
from fable_library.util import UNIT, Unit, round


def _expr2() -> TypeInfo:
    return record_type(
        "Cortex.Kernel.FixedPoint.Fixed60", Array([]), Fixed60, lambda: [("raw_value", int64_type)]
    )


@dataclass(eq=False, repr=False, slots=True)
class Fixed60(Record):
    raw_value: int64

    def ToString(self, __unit: Unit = UNIT) -> str:
        this: Fixed60 = self
        pattern_input: tuple[int64, int64, int64, int64] = Fixed60_ToDegMinSecThird_Z60A0FF53(this)
        return to_text(printf("%d°%02d'%02d\"%02d'''"))(pattern_input[0])(pattern_input[1])(
            pattern_input[2]
        )(pattern_input[3])

    def __hash__(self) -> int:
        return int(self.GetHashCode())


Fixed60_reflection = _expr2


def Fixed60_Create_Z524259C1(integer_part: int64) -> Fixed60:
    return Fixed60(op_multiply(integer_part, int64(216000)))


def Fixed60_Create_Z6C60F440(deg: int64, min: int64, sec: int64, third: int64) -> Fixed60:
    sign: int64 = (
        int64.NEG_ONE
        if (
            True
            if (
                True if (True if (deg < int64.ZERO) else (min < int64.ZERO)) else (sec < int64.ZERO)
            )
            else (third < int64.ZERO)
        )
        else int64.ONE
    )
    abs_deg: int64 = abs(deg)
    abs_min: int64 = abs(min)
    abs_sec: int64 = abs(sec)
    abs_third: int64 = abs(third)
    return Fixed60(
        op_multiply(
            sign,
            op_addition(
                op_addition(
                    op_addition(
                        op_multiply(abs_deg, int64(216000)), op_multiply(abs_min, int64(3600))
                    ),
                    op_multiply(abs_sec, int64(60)),
                ),
                abs_third,
            ),
        )
    )


def Fixed60_ToDegMinSecThird_Z60A0FF53(f: Fixed60) -> tuple[int64, int64, int64, int64]:
    sign: int64 = int64.NEG_ONE if (f.raw_value < int64.ZERO) else int64.ONE
    abs_val: int64 = abs(f.raw_value)
    deg: int64 = op_division(abs_val, int64(216000))
    rem1: int64 = op_modulus(abs_val, int64(216000))
    min: int64 = op_division(rem1, int64(3600))
    rem2: int64 = op_modulus(rem1, int64(3600))
    sec: int64 = op_division(rem2, int64(60))
    third: int64 = op_modulus(rem2, int64(60))
    return (op_multiply(sign, deg), min, sec, third)


def Fixed60_Add_146016E0(a: Fixed60, b: Fixed60) -> Fixed60:
    return Fixed60(op_addition(a.raw_value, b.raw_value))


def Fixed60_Sub_146016E0(a: Fixed60, b: Fixed60) -> Fixed60:
    return Fixed60(op_subtraction(a.raw_value, b.raw_value))


def Fixed60_Mul_146016E0(a: Fixed60, b: Fixed60) -> Fixed60:
    big_a: int = from_int64(a.raw_value)
    big_b: int = from_int64(b.raw_value)
    big_s: int = from_int64(int64(216000))
    return Fixed60(to_int64(op_division_1(op_multiply_1(big_a, big_b), big_s)))


def Fixed60_Div_146016E0(a: Fixed60, b: Fixed60) -> Fixed60:
    big_a: int = from_int64(a.raw_value)
    big_b: int = from_int64(b.raw_value)
    return Fixed60(to_int64(op_division_1(op_multiply_1(big_a, from_int64(int64(216000))), big_b)))


def to_float(f: Fixed60) -> float64:
    return to_number(f.raw_value) / to_number(int64(216000))


def from_float(x: float64) -> Fixed60:
    return Fixed60(from_number(round(x * to_number(int64(216000))), False))
