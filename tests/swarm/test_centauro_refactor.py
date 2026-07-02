# [C5-REAL] Exergy-Maximized
import pytest
import asyncio
from babylon60.extensions.swarm.centauro_engine import CentauroEngine, Formation, VirtualAgent


def test_centauro_formation_sizes():
    """Verify that all formations have correct sizes, including the new CENTURIA."""
    engine = CentauroEngine()
    assert engine._FORMATION_SIZES[Formation.BLITZ] == 3
    assert engine._FORMATION_SIZES[Formation.SANEDRIN] == 5
    assert engine._FORMATION_SIZES[Formation.CENTURIA] == 100


def test_centauro_specialty_roles():
    """Verify that the engine determines agent specialty based on formation specs."""
    engine = CentauroEngine()

    # GHOST: fixed to CODE
    assert engine._get_specialty(0, Formation.GHOST) == "CODE"
    assert engine._get_specialty(5, Formation.GHOST) == "CODE"

    # SPECTRE: rotativo [INTEL, CODE, SECURITY]
    assert engine._get_specialty(0, Formation.SPECTRE) == "INTEL"
    assert engine._get_specialty(1, Formation.SPECTRE) == "CODE"
    assert engine._get_specialty(2, Formation.SPECTRE) == "SECURITY"
    assert engine._get_specialty(3, Formation.SPECTRE) == "INTEL"

    # SENTINEL: rotativo [INTEL, CODE, SECURITY, DATA]
    assert engine._get_specialty(0, Formation.SENTINEL) == "INTEL"
    assert engine._get_specialty(1, Formation.SENTINEL) == "CODE"
    assert engine._get_specialty(2, Formation.SENTINEL) == "SECURITY"
    assert engine._get_specialty(3, Formation.SENTINEL) == "DATA"
    assert engine._get_specialty(4, Formation.SENTINEL) == "INTEL"

    # SANEDRIN: rotativo [INTEL, CODE, SECURITY, DATA, INFRA]
    assert engine._get_specialty(0, Formation.SANEDRIN) == "INTEL"
    assert engine._get_specialty(4, Formation.SANEDRIN) == "INFRA"
    assert engine._get_specialty(5, Formation.SANEDRIN) == "INTEL"

    # PHALANX: binary security / code
    assert engine._get_specialty(0, Formation.PHALANX) == "SECURITY"
    assert engine._get_specialty(1, Formation.PHALANX) == "CODE"


@pytest.mark.asyncio
async def test_byzantine_consensus_squad_isolation():
    """Verify that ByzantineConsensus does not achieve consensus early on sub-quorum responses.

    A squad of 3 has total weight 3.0. A single early responder (weight 1.0) must not achieve
    quorum (since 1.0 / 3.0 = 0.33 < 0.66). At least 2 responders proposing the same value (weight 2.0)
    are required to achieve consensus (2.0 / 3.0 = 0.67 >= 0.66).
    """
    engine = CentauroEngine(tolerance=0.66)
    squad = engine.spawn_squad(3, Formation.BLITZ)
    node_ids = list(squad.keys())

    # Only 1 node responds
    proposals = {node_ids[0]: "win"}
    winner = await engine.consensus.execute_consensus(proposals, node_ids=node_ids)
    assert winner is None  # Quorum not achieved

    # 2 nodes respond with same proposal
    proposals[node_ids[1]] = "win"
    winner = await engine.consensus.execute_consensus(proposals, node_ids=node_ids)
    assert winner == "win"  # Quorum achieved (2/3 = 0.67 >= 0.66)
