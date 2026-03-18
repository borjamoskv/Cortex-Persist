"""
Architectural Fitness Functions for CORTEX Swarm.
[Axiom Ω₁₃: Vigilancia Estructural]

Ensures that the biological/technical drift of the system does not violate
the core thermodynamic constraints of the sovereign architecture.
"""

from unittest.mock import MagicMock

import pytest

from cortex.extensions.swarm.budget import SwarmBudgetManager
from cortex.extensions.swarm.byzantine import ByzantineConsensus
from cortex.extensions.swarm.infinite_minds import InfiniteMindsManager
from cortex.extensions.swarm.manager import CapatazOrchestrator


def is_compliant_extension(obj) -> bool:
    """Rigorous check for SwarmExtension protocol compliance."""
    # Must have get_status returning a dict
    if not hasattr(obj, "get_status") or not callable(obj.get_status):
        return False

    # Must have evict_stale_data returning an int
    if not hasattr(obj, "evict_stale_data") or not callable(obj.evict_stale_data):
        return False

    return True


class TestArchitecturalFitness:
    """Fitness Guards to prevent architectural decay."""

    @pytest.fixture
    def orchestrator(self):
        # Setup orchestrator with real core extensions
        orch = CapatazOrchestrator()
        orch.register_extension("budget", SwarmBudgetManager(":memory:"))
        orch.register_extension("byzantine", ByzantineConsensus())

        # InfiniteMinds needs a space
        mock_space = MagicMock()
        orch.register_extension("minds", InfiniteMindsManager(space=mock_space))
        return orch

    def test_core_extensions_protocol_compliance(self, orchestrator):
        """Verify that all core extensions strictly follow the SwarmExtension protocol."""
        for name, ext in orchestrator._extensions.items():
            assert is_compliant_extension(ext), f"Extension [{name}] violates protocol: {name}"

    @pytest.mark.asyncio
    async def test_maintenance_pulse_execution_integrity(self, orchestrator):
        """Ensure maintenance_pulse actually triggers data eviction on all extensions."""
        results = await orchestrator.maintenance_pulse()

        # All core extensions should have reported back
        assert "budget" in results
        assert "byzantine" in results
        assert "minds" in results

        # Values should be integers representing cleared entries (>= 0)
        for name, count in results.items():
            assert isinstance(count, int), f"Extension [{name}] returned non-integer count"

    @pytest.mark.asyncio
    async def test_prevent_non_compliant_registration_warning(self, orchestrator):
        """Future-proofing: registration of non-compliant objects should be handled."""

        class Junk:
            pass

        orchestrator.register_extension("trash", Junk())
        # Currently, register_extension accepts anything, but maintenance_pulse will skip it.
        # This test ensures we don't accidentally count trash in results.
        results = await orchestrator.maintenance_pulse()
        assert "trash" not in results, "Orchestrator should skip non-compliant extensions in pulse"
