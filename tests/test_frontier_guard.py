import json

import pytest

from cortex.guards.frontier_guard import FrontierModelGuard
from cortex.utils.errors import SovereignViolation


@pytest.fixture
def temp_presets(tmp_path):
    presets = {
        "openai": {"tier": "frontier"},
        "ollama": {"tier": "local"},
        "mistral": {"tier": "high"},
        "low_tier_provider": {"tier": "low"},
    }
    presets_file = tmp_path / "llm_presets.json"
    with open(presets_file, "w") as f:
        json.dump(presets, f)
    return presets_file


def test_frontier_guard_allowed(temp_presets):
    guard = FrontierModelGuard(presets_path=temp_presets)
    # Frontier and High should pass
    guard.validate_config("openai")
    guard.validate_config("mistral")


def test_frontier_guard_rejected(temp_presets):
    guard = FrontierModelGuard(presets_path=temp_presets)
    # Local and Low should fail
    with pytest.raises(SovereignViolation, match="has tier 'local'"):
        guard.validate_config("ollama")

    with pytest.raises(SovereignViolation, match="has tier 'low'"):
        guard.validate_config("low_tier_provider")


def test_frontier_guard_unknown_provider(temp_presets):
    guard = FrontierModelGuard(presets_path=temp_presets)
    with pytest.raises(SovereignViolation, match="Unknown provider 'unknown'"):
        guard.validate_config("unknown")
