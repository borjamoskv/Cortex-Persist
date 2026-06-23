from fable_library.core import int32, uint16, uint64
from fable_library.long import op_addition, op_bitwise_and, op_right_shift, op_subtraction

from .babylon import Babylon_causalDistance


def CausalEngine_popCount(x: uint64) -> int32:
    v1: uint64 = op_subtraction(
        x, op_bitwise_and(op_right_shift(x, int32.ONE), uint64(6148914691236517205))
    )
    v2: uint64 = op_addition(
        op_bitwise_and(v1, uint64(3689348814741910323)),
        op_bitwise_and(op_right_shift(v1, int32.TWO), uint64(3689348814741910323)),
    )
    v3: uint64 = op_bitwise_and(
        op_addition(v2, op_right_shift(v2, int32.FOUR)), uint64(1085102592571150095)
    )
    v4: uint64 = op_addition(v3, op_right_shift(v3, int32.EIGHT))
    v5: uint64 = op_addition(v4, op_right_shift(v4, int32.SIXTEEN))
    return int32(
        int32(op_bitwise_and(op_addition(v5, op_right_shift(v5, int32.THIRTY_TWO)), uint64(127)))
    )


def CausalEngine_causalDistance(
    ancestry_overlap: uint16, ledger_overlap: uint16, witness_overlap: uint16
) -> uint16:
    return Babylon_causalDistance(ancestry_overlap, ledger_overlap, witness_overlap, uint16.ZERO)
