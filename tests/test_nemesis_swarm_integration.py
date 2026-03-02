import os

import pytest

from cortex.engine.nemesis import NemesisProtocol
from cortex.red_team.swarm_chaos import RedTeamSwarm

NEMESIS_TEST_PATH = "/Users/borjafernandezangulo/cortex/nemesis.md"


@pytest.fixture(autouse=True)
def cleanup_nemesis():
    """Backup and restore nemesis.md for testing."""
    if os.path.exists(NEMESIS_TEST_PATH):
        with open(NEMESIS_TEST_PATH) as f:
            original_content = f.read()
    else:
        original_content = ""

    yield

    with open(NEMESIS_TEST_PATH, "w") as f:
        f.write(original_content)


def test_nemesis_dynamic_loading():
    """Verify that NemesisProtocol loads antibodies from nemesis.md."""
    # Append a temporary test antibody
    NemesisProtocol.append_antibody("collapse_trigger_123", "Test Rejection")

    # Test content that should trigger it
    content = "This is a test with collapse_trigger_123 inside."
    rejection = NemesisProtocol.analyze(content)

    assert rejection is not None
    assert "Antibody: Test Rejection" in rejection


@pytest.mark.asyncio
async def test_swarm_chaos_end_to_end():
    """Verify the end-to-end swarm chaos loop."""
    swarm = RedTeamSwarm()

    # Define a fragile target function that fails on a specific input
    def target_func(data: str):
        if "exploit" in data:
            raise ValueError("System Collapsed!")
        return "OK"

    # Seed input that will be mutated by EvolutionaryFalsifier
    seed = {"data": "exploit"}

    # This should trigger a collapse and append an antibody
    success = await swarm.inject_chaos("test_service", target_func, seed)

    assert success is True

    # Verify the antibody is now active
    illegal_content = "some preamble with exploit and suffix"
    rejection = NemesisProtocol.analyze(illegal_content)

    assert rejection is not None
    assert "Collapse detected in test_service" in rejection
