# [C5-REAL] Exergy-Maximized
import pytest
from cortex.engine.maxwell_demon import MaxwellDemon

@pytest.mark.asyncio
async def test_maxwell_demon_purges_duplicates():
    demon = MaxwellDemon(similarity_threshold=0.85)
    
    chunks = [
        "El sistema es determinista.",
        "El sistema es determinista.", # Exact duplicate
        "La entropía de la red ha aumentado.",
        "La entropía de la red ha aumentado.", # Exact duplicate
        "Iniciando secuencia de auto-reparación."
    ]
    
    retained = demon.purge_redundant(chunks)
    
    assert len(retained) == 3
    assert retained[0] == "El sistema es determinista."
    assert retained[1] == "La entropía de la red ha aumentado."
    assert retained[2] == "Iniciando secuencia de auto-reparación."

@pytest.mark.asyncio
async def test_maxwell_demon_empty_input():
    demon = MaxwellDemon()
    assert demon.purge_redundant([]) == []
