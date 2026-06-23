from __future__ import annotations

from fable_library.big_int import from_int32, from_int64, to_int64
from fable_library.big_int import op_division as op_division_1
from fable_library.big_int import op_multiply as op_multiply_1
from fable_library.core import int32, int64
from fable_library.long import (
    from_integer,
    op_addition,
    op_division,
    op_modulus,
    op_multiply,
    op_subtraction,
)
from fable_library.record import Record
from fable_library.reflection import TypeInfo, class_type
from fable_library.string_ import printf, to_text
from fable_library.system import DivideByZeroException__ctor_Z721C83C5
from fable_library.util import UNIT, Unit


def _expr6() -> TypeInfo:
    return class_type("Cortex.Kernel.Fixed60", None, Fixed60, class_type("System.ValueType"))


class Fixed60(Record):
    __slots__ = ["Value"]

    def __init__(self, Value: int64 = int64.ZERO) -> None:
        super().__init__()
        self.Value = Value

    def ToString(self, __unit: Unit = UNIT) -> str:
        this: Fixed60 = self
        is_neg: bool = this.Value < int64.ZERO
        abs_val: int64 = abs(this.Value)
        deg: int64 = op_division(abs_val, int64(216000))
        rem1: int64 = op_modulus(abs_val, int64(216000))
        min: int64 = op_division(rem1, int64(3600))
        rem2: int64 = op_modulus(rem1, int64(3600))
        sec: int64 = op_division(rem2, int64(60))
        thirds: int64 = op_modulus(rem2, int64(60))
        sign: str = "-" if is_neg else ""
        return to_text(printf("%s%d°%02d'%02d\"%02d'''"))(sign)(deg)(min)(sec)(thirds)


Fixed60_reflection = _expr6


def Fixed60__ctor_Z524259C1(v: int64) -> Fixed60:
    return Fixed60(v)


FixedPoint60_ScaleBig: int = from_int32(int32(216000))


def FixedPoint60_create(deg: int32, min: int32, sec: int32, thirds: int32) -> Fixed60:
    sign: int64 = (
        int64.NEG_ONE
        if (
            True
            if (
                True if (True if (deg < int32.ZERO) else (min < int32.ZERO)) else (sec < int32.ZERO)
            )
            else (thirds < int32.ZERO)
        )
        else int64.ONE
    )
    return Fixed60__ctor_Z524259C1(
        op_multiply(
            op_addition(
                op_addition(
                    op_addition(
                        op_multiply(from_integer(abs(deg), False, int32.TWO), int64(216000)),
                        op_multiply(from_integer(abs(min), False, int32.TWO), int64(3600)),
                    ),
                    op_multiply(from_integer(abs(sec), False, int32.TWO), int64(60)),
                ),
                from_integer(abs(thirds), False, int32.TWO),
            ),
            sign,
        )
    )


def FixedPoint60_add(a: Fixed60, b: Fixed60) -> Fixed60:
    return Fixed60__ctor_Z524259C1(op_addition(a.Value, b.Value))


def FixedPoint60_sub(a: Fixed60, b: Fixed60) -> Fixed60:
    return Fixed60__ctor_Z524259C1(op_subtraction(a.Value, b.Value))


def FixedPoint60_mul(a: Fixed60, b: Fixed60) -> Fixed60:
    return Fixed60__ctor_Z524259C1(
        to_int64(
            op_division_1(
                op_multiply_1(from_int64(a.Value), from_int64(b.Value)), FixedPoint60_ScaleBig
            )
        )
    )


def FixedPoint60_div(a: Fixed60, b: Fixed60) -> Fixed60:
    if b.Value == int64.ZERO:
        raise DivideByZeroException__ctor_Z721C83C5(
            "BABYLON-60 FATAL: División por cero prevenida."
        )

    big_a: int = from_int64(a.Value)
    big_b: int = from_int64(b.Value)
    return Fixed60__ctor_Z524259C1(
        to_int64(op_division_1(op_multiply_1(big_a, FixedPoint60_ScaleBig), big_b))
    )
