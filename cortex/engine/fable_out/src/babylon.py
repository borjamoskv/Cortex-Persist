from fable_library.array_ import Array
from fable_library.core import int32, uint16, uint32
from typing import Any

Babylon_MAX_DIVERGENCE: int = 1000


def Babylon_causalDistance(
    ancestryOverlap: int,
    ledgerOverlap: int,
    witnessOverlap: int,
    temporalOverlap: int,
) -> int:
    import cortex_rs
    return cortex_rs.causal_distance(
        ancestryOverlap, ledgerOverlap, witnessOverlap, temporalOverlap
    )


def Babylon_hashDistanceRollup(rootHash: int, distances: Any) -> int:
    import cortex_rs
    # Fable arrays might be custom objects, so we convert them to a python list
    dist_list = list(distances)
    return cortex_rs.hash_distance_rollup(rootHash, dist_list)
