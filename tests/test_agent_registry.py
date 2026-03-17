"""Tests for AgentRegistry (Phase 3)."""


import pytest

from cortex.extensions.agents.registry import (
    AgentDefinition,
    AgentRegistry,
    GuardrailsConfig,
    MemoryConfig,
)


@pytest.fixture
def temp_definitions_dir(tmp_path):
    """Create a temporary directory with mock YAML definitions."""
    def_dir = tmp_path / "definitions"
    def_dir.mkdir()

    # Valid agent
    agent1 = def_dir / "test_alpha.yaml"
    agent1.write_text(
        "name: ALPHA-1\n"
        "model: claude-3-opus\n"
        "system_prompt: 'You are Alpha.'\n"
        "memory:\n"
        "  tier: cold\n"
        "guardrails:\n"
        "  max_turns: 10\n"
        "tools:\n"
        "  - search\n"
        "  - filesystem\n"
    )

    # Minimal agent (relies on defaults)
    agent2 = def_dir / "test_beta.yaml"
    agent2.write_text("name: BETA-2\n")

    # Invalid agent (not a dict)
    agent3 = def_dir / "invalid.yaml"
    agent3.write_text("- just a list")

    return def_dir


def test_agent_definition_parsing(temp_definitions_dir):
    """Test parsing a full YAML into AgentDefinition dataclass."""
    filepath = temp_definitions_dir / "test_alpha.yaml"
    agent = AgentDefinition.from_yaml_file(filepath)

    assert agent.id == "test_alpha"
    assert agent.name == "ALPHA-1"
    assert agent.model == "claude-3-opus"
    assert agent.system_prompt == "You are Alpha."
    assert agent.memory.tier == "cold"
    assert agent.guardrails.max_turns == 10
    assert agent.tools == ["search", "filesystem"]


def test_agent_definition_defaults(temp_definitions_dir):
    """Test parsing a minimal YAML uses defaults."""
    filepath = temp_definitions_dir / "test_beta.yaml"
    agent = AgentDefinition.from_yaml_file(filepath)

    assert agent.id == "test_beta"
    assert agent.name == "BETA-2"
    assert agent.model == "gemini-2.5-pro"  # Default
    assert agent.system_prompt == ""
    assert isinstance(agent.memory, MemoryConfig)
    assert agent.memory.tier == "hot"
    assert isinstance(agent.guardrails, GuardrailsConfig)
    assert agent.tools == []


def test_invalid_yaml_parsing(temp_definitions_dir):
    """Test parsing invalid YAML raises ValueError."""
    filepath = temp_definitions_dir / "invalid.yaml"
    with pytest.raises(ValueError, match="Invalid YAML schema"):
        AgentDefinition.from_yaml_file(filepath)


def test_agent_registry_singleton(temp_definitions_dir):
    """Test AgentRegistry loads definitions correctly and behaves as singleton."""
    r1 = AgentRegistry()
    r2 = AgentRegistry()
    assert r1 is r2  # Singleton check

    # Needs clear between runs to be safe
    r1.clear()

    # Load from our temp dir
    r1.load_all(temp_definitions_dir)

    # Should have loaded alpha and beta, skipping invalid
    assert "test_alpha" in r1.agents
    assert "test_beta" in r1.agents
    assert "invalid" not in r1.agents

    alpha = r1.get("test_alpha")
    assert alpha is not None
    assert alpha.name == "ALPHA-1"

    assert r1.get("missing") is None
