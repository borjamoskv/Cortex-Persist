"""
Tests for KETER Engine.
"""

import pytest

from cortex.engine.keter import (
    ArchScaffolder,
    IntentAlchemist,
    KeterEngine,
)
from cortex.utils.errors import CortexError


@pytest.fixture
def engine():
    """Returns a KeterEngine instance."""
    return KeterEngine()


@pytest.mark.asyncio
class TestKeterEngine:
    """Test suite for KeterEngine."""

    async def test_ignite_success(self, engine):
        """Verify successful ignition of the KETER engine."""
        result = await engine.ignite("build a sovereign dashboard")
        assert result["status"] == "SINGULARITY_REACHED"
        assert "spec_130_100" in result
        assert "scaffold_status" in result
        assert "legion_audit" in result
        assert "score_130_100" in result

    async def test_ignite_empty_intent(self, engine):
        """Verify that empty intent raises CortexError."""
        with pytest.raises(CortexError, match="KETER intent missing"):
            await engine.ignite("")


@pytest.mark.asyncio
class TestPhases:
    """Test suite for individual KETER phases."""

    async def test_intent_alchemist(self):
        """Verify IntentAlchemist phase."""
        phase = IntentAlchemist()
        res = await phase.execute({"intent": "test"})
        assert "spec_130_100" in res

    async def test_arch_scaffolder(self):
        """Verify ArchScaffolder phase."""
        phase = ArchScaffolder()
        res = await phase.execute({})
        assert res["scaffold_status"] == "deployed"
