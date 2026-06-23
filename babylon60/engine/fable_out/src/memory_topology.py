from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from fable_library.array_ import Array
from fable_library.core import int32, int64, uint16, uint32, uint64
from fable_library.long import from_integer, op_addition, op_exclusive_or
from fable_library.map import add, empty, exists
from fable_library.record import Record
from fable_library.reflection import (
    TypeInfo,
    class_type,
    record_type,
    tuple_type,
    uint16_type,
    uint64_type,
)
from fable_library.util import compare_arrays

from .causal_engine import CausalEngine_causalDistance, CausalEngine_popCount
from .epistemic_nodes import EpistemicNode, EpistemicNode_reflection
from .fixed_point60 import (
    Fixed60,
    Fixed60__ctor_Z524259C1,
    Fixed60_reflection,
    FixedPoint60_add,
    FixedPoint60_div,
)
from .state_machine import (
    EpistemicPhase_Observation,
    MachineState,
    MachineState_reflection,
    step_machine,
)


def _expr7() -> TypeInfo:
    return record_type(
        "Cortex.Kernel.MemoryTopology.CognitiveState",
        Array([]),
        CognitiveState,
        lambda: [
            ("tick", uint64_type),
            ("machine", MachineState_reflection()),
            ("entropy_threshold", uint16_type),
            (
                "graph",
                class_type(
                    "Microsoft.FSharp.Collections.FSharpMap`2",
                    Array(
                        [
                            tuple_type(uint64_type, uint64_type, uint64_type, uint64_type),
                            EpistemicNode_reflection(),
                        ]
                    ),
                ),
            ),
            ("global_confidence", Fixed60_reflection()),
        ],
    )


@dataclass(eq=False, repr=False, slots=True)
class CognitiveState(Record):
    tick: uint64
    machine: MachineState
    entropy_threshold: uint16
    graph: Any
    global_confidence: Fixed60

    def __hash__(self) -> int:
        return int(self.GetHashCode())


CognitiveState_reflection = _expr7


def genesis(initial_threshold: uint16) -> CognitiveState:
    class ObjectExpr8:
        def Compare(
            self, x: tuple[uint64, uint64, uint64, uint64], y: tuple[uint64, uint64, uint64, uint64]
        ) -> int32:
            return compare_arrays(x, y)

    return CognitiveState(
        uint64.ZERO,
        MachineState(EpistemicPhase_Observation(), uint32.ZERO, uint32.ZERO, uint32.ZERO),
        initial_threshold,
        empty(ObjectExpr8()),
        Fixed60__ctor_Z524259C1(int64.ZERO),
    )


def apply_tick(
    state: CognitiveState,
    stimulus: tuple[tuple[uint64, uint64, uint64, uint64], EpistemicNode] | None,
    exergy_input: uint32,
) -> CognitiveState:
    next_machine: MachineState = step_machine(state.machine, exergy_input)
    pattern_input: tuple[Any, Fixed60]
    if stimulus is None:
        pattern_input = (state.graph, Fixed60__ctor_Z524259C1(int64.ZERO))

    else:
        node: EpistemicNode = stimulus[1]
        hash_1: tuple[uint64, uint64, uint64, uint64] = stimulus[0]

        def predicate(
            existing_hash: tuple[uint64, uint64, uint64, uint64],
            _arg: EpistemicNode,
            state: Any = state,
        ) -> bool:
            return (
                CausalEngine_causalDistance(
                    uint16(CausalEngine_popCount(op_exclusive_or(hash_1[0], existing_hash[0]))),
                    uint16.ZERO,
                    uint16.ZERO,
                )
                <= state.entropy_threshold
            )

        pattern_input = (
            ((state.graph, Fixed60__ctor_Z524259C1(int64.ZERO)))
            if exists(predicate, state.graph)
            else (
                (
                    add(hash_1, node, state.graph),
                    Fixed60__ctor_Z524259C1(int64.ONE)
                    if (node.tag == int32(0))
                    else (
                        Fixed60__ctor_Z524259C1(int64.ZERO)
                        if (node.tag == int32(2))
                        else FixedPoint60_div(
                            Fixed60__ctor_Z524259C1(
                                from_integer(node.fields[1], False, int32.FIVE)
                            ),
                            Fixed60__ctor_Z524259C1(int64(100)),
                        )
                    ),
                )
            )
        )

    return CognitiveState(
        op_addition(state.tick, uint64.ONE),
        next_machine,
        state.entropy_threshold,
        pattern_input[0],
        FixedPoint60_add(state.global_confidence, pattern_input[1]),
    )
