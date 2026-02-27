# tests/test_evolution.py
import asyncio
import sqlite3

import pytest

from cortex.evolution.agents import AgentDomain
from cortex.evolution.cortex_metrics import CortexMetrics
from cortex.evolution.engine import CycleReport, EvolutionEngine
from cortex.evolution.skill_bridge import get_skill_for_domain


@pytest.fixture
def mock_db(tmp_path):
    db_path = tmp_path / "cortex_test.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("CREATE TABLE facts (fact_type TEXT, project TEXT, created_at TEXT)")
    conn.execute("CREATE TABLE ghosts (status TEXT, project TEXT)")
    conn.execute("INSERT INTO facts VALUES ('decision', 'cortex', '2026-02-26T12:00:00Z')")
    conn.execute("INSERT INTO ghosts VALUES ('open', 'cortex')")
    conn.commit()
    conn.close()
    return db_path

def test_cycle_report_structure():
    report = CycleReport(
        cycle=1,
        avg_agent_fitness=50.0,
        best_agent_fitness=60.0,
        worst_agent_fitness=40.0,
        avg_subagent_fitness=45.0,
        total_mutations=10,
        tournaments_run=20,
        species_count=10,
        crossovers=2,
        extinctions=1,
        duration_ms=100.0
    )
    assert report.cycle == 1
    assert report.best_agent_fitness == 60.0
    assert report.extinctions == 1

def test_skill_bridge():
    path = get_skill_for_domain(AgentDomain.FABRICATION)
    assert "aether-1" in str(path)

@pytest.mark.asyncio
async def test_evolution_engine_cycle(mock_db):
    # Genesis swarm creation
    engine = EvolutionEngine()
    await engine.initialize_swarm()
    
    # Run cycle
    report = await engine.cycle()
    
    assert report.cycle >= 1
    assert len(engine.sovereigns) >= len(AgentDomain) - 1 # Adjusted for SYNERGY skip
    assert report.tournaments_run > 0

@pytest.mark.asyncio
async def test_metrics_logic(mock_db):
    metrics = CortexMetrics(db_path=mock_db)
    # Testing sync query via thread
    m = await asyncio.to_thread(metrics.get_domain, AgentDomain.MEMORY)
    assert m.domain == AgentDomain.MEMORY
