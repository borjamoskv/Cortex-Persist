from __future__ import annotations

import sys
from typing import Any

from fable_library.array_ import Array
from fable_library.core import int32, uint16, uint32, uint64
from fable_library.map import FSharpMap__get_Count
from fable_library.string_ import printf, to_console
from fable_library.util import range

from .src.babylon import Babylon_hashDistanceRollup
from .src.epistemic_nodes import (
    EpistemicNode,
    EpistemicNode_StochasticConjecture,
    EpistemicNode_VerifiedHash,
    Origin_SystemDaemon,
)
from .src.fixed_point60 import Fixed60
from .src.maxwell_demon import (
    MaxwellDemon,
    MaxwellDemon__ctor_6C4BA866,
    MaxwellDemon__PurgeRedundant_Z115D9F2A,
    MaxwellDemon__SetState_Z721C83C5,
)
from .src.memory_topology import CognitiveState, apply_tick, genesis
from .src.state_machine import (
    EpistemicPhase,
    EpistemicPhase_Observation,
    MachineState,
    run_cycle,
)


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
    to_console(printf("\n[MemoryTopology C5-REAL Immutable FSM Test]"))
    stimulus_vectors: Array[
        tuple[uint32, tuple[tuple[uint64, uint64, uint64, uint64], EpistemicNode] | None]
    ] = Array[Any](
        [
            (
                uint32(100),
                (
                    (uint64.ONE, uint64.TWO, uint64.THREE, uint64.FOUR),
                    EpistemicNode_StochasticConjecture(Origin_SystemDaemon(), uint16(95)),
                ),
            ),
            (
                uint32(200),
                (
                    (uint64.FIVE, uint64.SIX, uint64.SEVEN, uint64.EIGHT),
                    EpistemicNode_VerifiedHash(uint32(123456), uint16.ZERO),
                ),
            ),
            (
                uint32(300),
                (
                    (uint64.ONE, uint64.TWO, uint64.THREE, uint64.FOUR),
                    EpistemicNode_StochasticConjecture(Origin_SystemDaemon(), uint16(95)),
                ),
            ),
            (uint32(400), None),
            (
                uint32(500),
                (
                    (uint64.NINE, uint64.TEN, uint64(11), uint64(12)),
                    EpistemicNode_VerifiedHash(uint32(654321), uint16.FIVE),
                ),
            ),
        ]
    )
    current_state: CognitiveState = genesis(uint16.TEN)
    arg_9: uint64 = current_state.tick
    arg_10: uint32 = current_state.machine.trace_hash
    arg_11: Fixed60 = current_state.global_confidence
    arg_12: int32 = FSharpMap__get_Count(current_state.graph)
    to_console(
        printf("--> INITIAL TICK: %d | TraceHash: %u | GlobalConfidence: %O | Graph Nodes: %d")
    )(arg_9)(arg_10)(arg_11)(arg_12)
    for idx_1 in range(int32.ZERO, int32(len(stimulus_vectors)) - int32.ONE, 1):
        for_loop_var = stimulus_vectors[idx_1]
        stimulus: tuple[tuple[uint64, uint64, uint64, uint64], EpistemicNode] | None = for_loop_var[
            1
        ]
        exergy: uint32 = for_loop_var[0]
        stim_str: str = "Some(Node)" if (stimulus is not None) else "None"
        to_console(printf("\n[+] Injecting Stimulus... Exergy: %u, Node: %s"))(exergy)(stim_str)
        current_state = apply_tick(current_state, stimulus, exergy)
        arg_15: uint64 = current_state.tick
        to_console(printf("--> TICK: %d"))(arg_15)
        arg_16: EpistemicPhase = current_state.machine.phase
        to_console(printf("    Phase:            %A"))(arg_16)
        arg_17: uint32 = current_state.machine.trace_hash
        to_console(printf("    TraceHash:        %u"))(arg_17)
        arg_18: Fixed60 = current_state.global_confidence
        to_console(printf("    GlobalConfidence: %O"))(arg_18)
        arg_19: int32 = FSharpMap__get_Count(current_state.graph)
        to_console(printf("    Graph Nodes:      %d"))(arg_19)
    to_console(
        printf(
            "\n[MOSKV-1] Test completed. Epistemic graph is immutable. TraceHash perfectly tracked."
        )
    )
    return int32.ZERO


if __name__ == "__main__":
    main(Array[Any](sys.argv[1:]))
