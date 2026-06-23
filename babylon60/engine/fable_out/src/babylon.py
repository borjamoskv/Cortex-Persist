from fable_library.array_ import Array
from fable_library.core import int32, uint16, uint32
from fable_library.util import range

Babylon_MAX_DIVERGENCE: uint16 = uint16(1000)


def Babylon_causalDistance(
    ancestry_overlap: uint16,
    ledger_overlap: uint16,
    witness_overlap: uint16,
    temporal_overlap: uint16,
) -> uint16:
    score: uint16 = (
        ((ancestry_overlap * uint16(60)) + (witness_overlap * uint16(30)))
        + (ledger_overlap * uint16.TEN)
    ) + (temporal_overlap * uint16.ONE)
    return (
        uint16.ZERO if (score > Babylon_MAX_DIVERGENCE) else (Babylon_MAX_DIVERGENCE - score)
    ) * uint16.ONE


def Babylon_hashDistanceRollup(root_hash: uint32, distances: Array[uint16]) -> uint32:
    current_hash: uint32 = root_hash
    for idx in range(int32.ZERO, int32(len(distances)) - int32.ONE, 1):
        d: uint16 = distances[idx]
        current_hash = (current_hash ^ d) >> int32.ZERO
        current_hash = current_hash * uint32(16777619)
    return current_hash
