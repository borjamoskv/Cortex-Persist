from __future__ import annotations

from typing import Any

from fable_library.array_ import Array
from fable_library.core import int32, uint16, uint32
from fable_library.list import FSharpList, cons, empty, exists, map, reverse, to_array
from fable_library.reflection import TypeInfo, class_type
from fable_library.util import range

from .babylon import Babylon_causalDistance


def _expr4() -> TypeInfo:
    return class_type("Cortex.Kernel.MaxwellDemon", None, MaxwellDemon)


class MaxwellDemon:
    def __init__(self, similarity_threshold: uint16) -> None:
        self.threshold: uint16 = similarity_threshold


MaxwellDemon_reflection = _expr4


def MaxwellDemon__ctor_6C4BA866(similarity_threshold: uint16) -> MaxwellDemon:
    return MaxwellDemon(similarity_threshold)


def MaxwellDemon__SetState_Z721C83C5(this: MaxwellDemon, state: str) -> None:
    match_value: str = state.upper()
    match match_value:
        case "ULTRATHINK":
            this.threshold = uint16.TEN

        case "CONSTRUCT":
            this.threshold = uint16(50)

        case _:
            this.threshold = uint16(150)


def MaxwellDemon__CosineSimilarity_23050560(this: MaxwellDemon, id1: uint32, id2: uint32) -> uint16:
    if id1 == id2:
        return uint16.ZERO

    else:
        return Babylon_causalDistance(
            uint16(((id1 ^ id2) >> int32.ZERO) % uint32.FIVE),
            uint16(id1 % uint32.THREE),
            uint16.ZERO,
            uint16.FIVE,
        )


def MaxwellDemon__PurgeRedundant_Z115D9F2A(
    this: MaxwellDemon, chunks: Array[tuple[uint32, str]]
) -> tuple[Array[str], int32]:
    accepted: FSharpList[tuple[uint32, str]] = empty()
    purged_count: int32 = int32.ZERO
    for idx in range(int32.ZERO, int32(len(chunks)) - int32.ONE, 1):
        for_loop_var: tuple[uint32, str] = chunks[idx]
        h: uint32 = for_loop_var[0]

        def predicate(tupled_arg: tuple[uint32, str], this: Any = this, h: uint32 = h) -> bool:
            return MaxwellDemon__CosineSimilarity_23050560(this, h, tupled_arg[0]) <= this.threshold

        if exists(predicate, accepted):
            purged_count = purged_count + int32.ONE

        else:
            accepted = cons((h, for_loop_var[1]), accepted)

    def mapping(tuple: tuple[uint32, str]) -> str:
        return tuple[1]

    return (to_array(map(mapping, reverse(accepted))), purged_count)
