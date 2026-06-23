from __future__ import annotations

from dataclasses import dataclass

from fable_library.array_ import Array, fold
from fable_library.core import int32, uint32
from fable_library.record import Record
from fable_library.reflection import TypeInfo, record_type, string_type, uint32_type, union_type
from fable_library.union import Union, tagged_union


def _expr0() -> TypeInfo:
    return union_type(
        "Cortex.Kernel.StateMachine.EpistemicPhase",
        Array([]),
        _EpistemicPhase,
        lambda: [[], [], [], [], []],
        [
            EpistemicPhase_Observation,
            EpistemicPhase_Reflection,
            EpistemicPhase_Decision,
            EpistemicPhase_Execution,
            EpistemicPhase_Verification,
        ],
    )


class _EpistemicPhase(Union):
    @staticmethod
    def cases() -> list[str]:
        return ["Observation", "Reflection", "Decision", "Execution", "Verification"]


@tagged_union(0)
class EpistemicPhase_Observation(_EpistemicPhase): ...


@tagged_union(1)
class EpistemicPhase_Reflection(_EpistemicPhase): ...


@tagged_union(2)
class EpistemicPhase_Decision(_EpistemicPhase): ...


@tagged_union(3)
class EpistemicPhase_Execution(_EpistemicPhase): ...


@tagged_union(4)
class EpistemicPhase_Verification(_EpistemicPhase): ...


EpistemicPhase = (
    ((EpistemicPhase_Observation | EpistemicPhase_Reflection) | EpistemicPhase_Decision)
    | EpistemicPhase_Execution
) | EpistemicPhase_Verification

EpistemicPhase_reflection = _expr0


def _expr2() -> TypeInfo:
    return union_type(
        "Cortex.Kernel.StateMachine.TransitionResult",
        Array([]),
        _TransitionResult,
        lambda: [
            [("phase", EpistemicPhase_reflection()), ("hash", uint32_type)],
            [("reason", string_type)],
            [],
        ],
        [TransitionResult_Advanced, TransitionResult_Blocked, TransitionResult_Halted],
    )


class _TransitionResult(Union):
    @staticmethod
    def cases() -> list[str]:
        return ["Advanced", "Blocked", "Halted"]


@tagged_union(0)
class TransitionResult_Advanced(_TransitionResult):
    phase_: EpistemicPhase
    hash_: uint32


@tagged_union(1)
class TransitionResult_Blocked(_TransitionResult):
    reason_: str


@tagged_union(2)
class TransitionResult_Halted(_TransitionResult): ...


TransitionResult = (TransitionResult_Advanced | TransitionResult_Blocked) | TransitionResult_Halted

TransitionResult_reflection = _expr2


def _expr5() -> TypeInfo:
    return record_type(
        "Cortex.Kernel.StateMachine.MachineState",
        Array([]),
        MachineState,
        lambda: [
            ("phase", EpistemicPhase_reflection()),
            ("cycle", uint32_type),
            ("exergy_accum", uint32_type),
            ("trace_hash", uint32_type),
        ],
    )


@dataclass(eq=False, repr=False, slots=True)
class MachineState(Record):
    phase: EpistemicPhase
    cycle: uint32
    exergy_accum: uint32
    trace_hash: uint32

    def __hash__(self) -> int:
        return int(self.GetHashCode())


MachineState_reflection = _expr5


def phase_to_tag(phase: EpistemicPhase) -> uint32:
    match phase.tag:
        case 1:
            return uint32.ONE

        case 2:
            return uint32.TWO

        case 3:
            return uint32.THREE

        case 4:
            return uint32.FOUR

        case _:
            return uint32.ZERO


def hash_transition(state: MachineState, next_phase: EpistemicPhase) -> uint32:
    return (
        (state.trace_hash ^ ((phase_to_tag(next_phase) ^ state.cycle) >> int32.ZERO)) >> int32.ZERO
    ) * uint32(16777619)


def transition(state: MachineState, exergy_input: uint32) -> TransitionResult:
    match_value: EpistemicPhase = state.phase
    match match_value.tag:
        case 1:
            if exergy_input >= uint32.TEN:
                return TransitionResult_Advanced(
                    EpistemicPhase_Decision(), hash_transition(state, EpistemicPhase_Decision())
                )

            else:
                return TransitionResult_Blocked("Zero exergy")

        case 2:
            if exergy_input >= uint32(50):
                return TransitionResult_Advanced(
                    EpistemicPhase_Execution(), hash_transition(state, EpistemicPhase_Execution())
                )

            else:
                return TransitionResult_Blocked("Zero exergy")

        case 3:
            return TransitionResult_Advanced(
                EpistemicPhase_Verification(), hash_transition(state, EpistemicPhase_Verification())
            )

        case 4:
            return TransitionResult_Advanced(
                EpistemicPhase_Observation(), hash_transition(state, EpistemicPhase_Observation())
            )

        case _:
            if exergy_input > uint32.ZERO:
                return TransitionResult_Advanced(
                    EpistemicPhase_Reflection(), hash_transition(state, EpistemicPhase_Reflection())
                )

            else:
                return TransitionResult_Blocked("Zero exergy")


def step_machine(state: MachineState, exergy_input: uint32) -> MachineState:
    match_value: TransitionResult = transition(state, exergy_input)
    match match_value.tag:
        case 1:
            return MachineState(
                state.phase, state.cycle, state.exergy_accum + exergy_input, state.trace_hash
            )

        case 2:
            return state

        case _:
            return MachineState(
                match_value.fields[0],
                state.cycle + (uint32.ONE if (state.phase.tag == int32(4)) else uint32.ZERO),
                state.exergy_accum + exergy_input,
                match_value.fields[1],
            )


def run_cycle(initial_state: MachineState, inputs: Array[uint32]) -> MachineState:
    return fold(step_machine, initial_state, inputs)
