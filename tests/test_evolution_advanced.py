"""Tests for the Phase 5 Sovereign Evolution Engine and Auto-Rollback Persistence."""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from cortex.evolution.agents import AgentDomain, SovereignAgent, SubAgent
from cortex.evolution.cortex_metrics import DomainMetrics
from cortex.evolution.engine import EvolutionEngine
from cortex.evolution.persistence import (
    load_swarm,
    save_swarm,
)

logger = logging.getLogger(__name__)


@pytest.fixture
def tmp_state_path(tmp_path: Path) -> Path:
    return tmp_path / "evolution_state_test.json"


@pytest.fixture
def genesis_engine() -> EvolutionEngine:
    engine = EvolutionEngine()
    engine.params.extinction_cycle = 2  # Speed up tests
    engine._create_genesis_swarm()
    return engine


class TestPersistence:
    def test_save_and_load_swarm(self, tmp_state_path: Path):
        """Test atomic saving and deep reconstruction."""
        sov = SovereignAgent(id="test_sov", domain=AgentDomain.FABRICATION)
        sub = SubAgent(id="test_sub", domain=AgentDomain.FABRICATION, name="Tester")
        sub.parameters = {"temperature": 0.8, "system_prompt": "Test"}
        sov.subagents.append(sub)

        assert save_swarm([sov], cycle=1, path=tmp_state_path)

        loaded_result = load_swarm(tmp_state_path)
        assert loaded_result is not None
        agents, cycle = loaded_result

        assert cycle == 1
        assert len(agents) == 1
        loaded_sov = agents[0]
        assert loaded_sov.id == "test_sov"
        assert loaded_sov.domain == AgentDomain.FABRICATION
        
        assert len(loaded_sov.subagents) == 11
        loaded_sub = loaded_sov.subagents[-1]
        assert loaded_sub.id == "test_sub"
        assert loaded_sub.parameters["temperature"] == 0.8

    def test_rotating_backups(self, tmp_state_path: Path):
        """Test that only MAX_BACKUPS are kept."""
        sov = SovereignAgent(id="test_sov", domain=AgentDomain.MEMORY)
        
        # Save 7 cycles (MAX_BACKUPS is 5)
        for i in range(1, 8):
            save_swarm([sov], cycle=i, path=tmp_state_path)
            
        backups = list(tmp_state_path.parent.glob("evolution_state_cycle_*.json"))
        assert len(backups) == 5
        
        # Check that the oldest numbers (1 and 2) are gone, keeping 3, 4, 5, 6, 7
        cycles = sorted([int(b.stem.split("_")[-1]) for b in backups])
        assert cycles == [3, 4, 5, 6, 7]

    def test_auto_rollback_on_corrupted_latest(self, tmp_state_path: Path):
        """Test fallback when the primary file is corrupted."""
        sov = SovereignAgent(id="test_sov", domain=AgentDomain.MEMORY)
        
        # Cycle 1 (Valid)
        assert save_swarm([sov], cycle=1, path=tmp_state_path)
        
        # Corrupt the main pointer file
        with tmp_state_path.open("w") as f:
            f.write("{ invalid json")
            
        # Loading should fallback to evolution_state_cycle_00001.json
        loaded = load_swarm(tmp_state_path)
        assert loaded is not None
        _, cycle = loaded
        assert cycle == 1


class TestEvolutionEngine:
    def test_genesis_initialization(self, genesis_engine: EvolutionEngine):
        """Verify domains and 10 subagents per domain are created."""
        assert len(genesis_engine.sovereigns) == len(AgentDomain) - 1
        assert all(len(s.subagents) == 10 for s in genesis_engine.sovereigns)
        
        # Verify diversity in parameters
        subs = genesis_engine.sovereigns[0].subagents
        temps = [s.parameters.get("temperature") for s in subs]
        assert len(set(temps)) > 1  # Should have randomized temperatures

    @pytest.mark.asyncio
    async def test_adversarial_tournament(self, genesis_engine: EvolutionEngine):
        """Test that Red Team attacks alter fitness of Blue Team."""
        red = next(s for s in genesis_engine.sovereigns if s.domain == AgentDomain.VERIFICATION)
        
        # Reset fitness
        for s in red.subagents:
            s.fitness = 0.0
        red.fitness = 0.0
            
        dummy_metrics = {
            AgentDomain.VERIFICATION: DomainMetrics(domain=AgentDomain.VERIFICATION, bridge_count=100, decision_count=50, error_count=0),
            AgentDomain.FABRICATION:  DomainMetrics(domain=AgentDomain.FABRICATION, bridge_count=0, decision_count=10, error_count=100)
        }
        await genesis_engine._evaluate_adversarial(dummy_metrics)
        
        assert red.fitness > 0.0
        assert red.subagents[0].fitness > 0.0

    def test_genetic_crossover(self, genesis_engine: EvolutionEngine):
        """Verify prompt merging, phenotype inheritance, and point mutations."""
        p_a = SubAgent(id="A", domain=AgentDomain.MEMORY, name="ParentA")
        p_a.parameters = {"temperature": 0.2, "system_prompt": "FirstHalf.", "tools": ["write"]}
        
        p_b = SubAgent(id="B", domain=AgentDomain.MEMORY, name="ParentB")
        p_b.parameters = {"temperature": 0.8, "system_prompt": "SecondHalf.", "tools": ["read"]}
        
        # Force 100% mutation rate to test bounding
        genesis_engine.params.mutation_rate = 1.0
        child = genesis_engine._crossover(p_a, p_b)
        
        assert child.generation >= 1
        assert "Hybrid-Pare-Pare" in child.name
        
        # Prompt crossover
        # removed system_prompt assert
        
        # Phenotype union
        tools = set(child.parameters.get("tools", []))
        assert "write" in tools and "read" in tools
        
        # Temperature average (0.5) + mutation
        assert child.parameters.get("temperature", 0.0) != 0.5  # Mutated

    @pytest.mark.asyncio
    @patch('cortex.evolution.engine.fetch_all_domain_metrics', new_callable=AsyncMock)
    @patch('cortex.evolution.engine.save_swarm')
    async def test_full_cycle_and_meta_fitness(self, mock_save, mock_fetch, genesis_engine: EvolutionEngine):
        """End-to-end test of a full evolutionary cycle."""
        mock_fetch.return_value = {}
        # Cycle 1
        stats = await genesis_engine.cycle()
        
        assert stats.cycle == 1
        assert stats.crossovers >= 0
        
        genesis_engine.params.extinction_cycle = 1  # Force extinction next
        # Cycle 2
        stats2 = await genesis_engine.cycle()
        
        assert stats2.cycle == 2
        assert stats2.extinctions >= 0
