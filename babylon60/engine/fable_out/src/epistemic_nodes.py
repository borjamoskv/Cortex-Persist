from __future__ import annotations

from fable_library.array_ import Array
from fable_library.core import uint16, uint32
from fable_library.reflection import TypeInfo, string_type, uint16_type, uint32_type, union_type
from fable_library.union import Union, tagged_union


def _expr1() -> TypeInfo:
    return union_type(
        "Cortex.Kernel.Origin",
        Array([]),
        _Origin,
        lambda: [[("Item", string_type)], [("Item", uint32_type)], []],
        [Origin_HumanOperator, Origin_AutonomousSwarm, Origin_SystemDaemon],
    )


class _Origin(Union):
    @staticmethod
    def cases() -> list[str]:
        return ["HumanOperator", "AutonomousSwarm", "SystemDaemon"]


@tagged_union(0)
class Origin_HumanOperator(_Origin):
    item: str


@tagged_union(1)
class Origin_AutonomousSwarm(_Origin):
    item: uint32


@tagged_union(2)
class Origin_SystemDaemon(_Origin): ...


Origin = (Origin_HumanOperator | Origin_AutonomousSwarm) | Origin_SystemDaemon

Origin_reflection = _expr1


def _expr3() -> TypeInfo:
    return union_type(
        "Cortex.Kernel.EpistemicNode",
        Array([]),
        _EpistemicNode,
        lambda: [
            [("root", uint32_type), ("distance", uint16_type)],
            [("origin", Origin_reflection()), ("confidence", uint16_type)],
            [],
        ],
        [EpistemicNode_VerifiedHash, EpistemicNode_StochasticConjecture, EpistemicNode_VoidAnergy],
    )


class _EpistemicNode(Union):
    @staticmethod
    def cases() -> list[str]:
        return ["VerifiedHash", "StochasticConjecture", "VoidAnergy"]


@tagged_union(0)
class EpistemicNode_VerifiedHash(_EpistemicNode):
    root_: uint32
    distance_: uint16


@tagged_union(1)
class EpistemicNode_StochasticConjecture(_EpistemicNode):
    origin_: Origin
    confidence_: uint16


@tagged_union(2)
class EpistemicNode_VoidAnergy(_EpistemicNode): ...


EpistemicNode = (
    EpistemicNode_VerifiedHash | EpistemicNode_StochasticConjecture
) | EpistemicNode_VoidAnergy

EpistemicNode_reflection = _expr3


def Validation_isCausallyValid(node: EpistemicNode) -> bool:
    match node.tag:
        case 1:
            return node.fields[1] >= uint16(90)

        case 2:
            return False

        case _:
            return node.fields[1] <= uint16(1000)
