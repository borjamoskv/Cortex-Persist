from __future__ import annotations

import sys
from typing import Any

from fable_library.array_ import Array
from fable_library.core import int32, uint16, uint32
from fable_library.string_ import printf, to_console
from fable_library.util import range

from .src.babylon import Babylon_hashDistanceRollup
from .src.maxwell_demon import (
    MaxwellDemon,
    MaxwellDemon__ctor_6C4BA866,
    MaxwellDemon__PurgeRedundant_Z115D9F2A,
    MaxwellDemon__SetState_Z721C83C5,
)
from .src.state_machine import EpistemicPhase_Observation, MachineState, run_cycle


def main(argv: Array[str]) -> int32:
    to_console(printf("CORTEX-PERSIST C5-REAL: F# FABLE KERNEL INITIALIZED"))
    demon: MaxwellDemon = MaxwellDemon__ctor_6C4BA866(uint16(85))
    MaxwellDemon__SetState_Z721C83C5(demon, "CONSTRUCT")
    chunks: Array[tuple[uint32, str]] = Array[Any](
        [
            (uint32(1001), "El sistema es determinista."),
            (uint32(1001), "El sistema es determinista."),
            (uint32(2005), "La entropía de la red ha aumentado."),
            (uint32(2005), "La entropía de la red ha aumentado."),
            (uint32(3010), "Iniciando secuencia de auto-reparación."),
        ]
    )
    pattern_input: tuple[Array[str], int32] = MaxwellDemon__PurgeRedundant_Z115D9F2A(demon, chunks)
    retained: Array[str] = pattern_input[0]
    to_console(printf("\n[MaxwellDemon Test]"))
    arg: int32 = int32(len(chunks))
    to_console(printf("Total chunks evaluados: %d"))(arg)
    arg_1: int32 = int32(len(retained))
    to_console(printf("Chunks retenidos: %d"))(arg_1)
    to_console(printf("Chunks purgados: %d"))(pattern_input[1])
    for idx in range(int32.ZERO, int32(len(retained)) - int32.ONE, 1):
        c: str = retained[idx]
        to_console(printf(" - %s"))(c)
    merkle_root: uint32 = Babylon_hashDistanceRollup(
        uint32(123456), Array[uint16]([uint16(50), uint16.TEN, uint16.ZERO])
    )
    to_console(printf("\nMerkle Rollup Root (uint32): %u"))(merkle_root)
    to_console(printf("\n[StateMachine Test]"))
    final_state: MachineState = run_cycle(
        MachineState(EpistemicPhase_Observation(), uint32.ZERO, uint32.ZERO, uint32.ZERO),
        Array[uint32](
            [
                uint32.FIVE,
                uint32(15),
                uint32(60),
                uint32.ONE,
                uint32.ONE,
                uint32.TEN,
                uint32(20),
                uint32(100),
                uint32.ONE,
                uint32.ONE,
            ]
        ),
    )
    to_console(printf("Final Phase: %A"))(final_state.phase)
    to_console(printf("Cycles completed: %u"))(final_state.cycle)
    to_console(printf("Exergy accumulated: %u"))(final_state.exergy_accum)
    to_console(printf("Trace Hash: %u"))(final_state.trace_hash)
    return int32.ZERO


if __name__ == "__main__":
    main(Array[Any](sys.argv[1:]))
