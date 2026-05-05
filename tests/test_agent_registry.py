"""Tests for AgentRegistry (Phase 3)."""

import logging
import os

import pytest

from cortex.extensions.agents.registry import (
    AgentCatalogEntry,
    AgentRegistry,
    AgentDefinition,
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
    """Test parsing a full YAML into AgentCatalogEntry dataclass."""
    filepath = temp_definitions_dir / "test_alpha.yaml"
    agent = AgentCatalogEntry.from_yaml_file(filepath)

    assert agent.id == "test_alpha"
    assert agent.name == "ALPHA-1"
    assert agent.model == "claude-3-opus"
    assert agent.system_prompt == "You are Alpha."
    assert agent.memory.tier == "cold"
    assert agent.guardrails.max_turns == 10
    assert agent.tools == ["search", "filesystem"]


def test_agent_definition_legacy_zero_turn_limit_maps_to_unlimited(tmp_path):
    """Test legacy `0` turn budgets become explicit unlimited semantics."""
    filepath = tmp_path / "legacy.yaml"
    filepath.write_text("name: LEGACY\nguardrails:\n  max_turns: 0\n")

    agent = AgentCatalogEntry.from_yaml_file(filepath)

    assert agent.guardrails.max_turns is None


def test_agent_definition_defaults(temp_definitions_dir):
    """Test parsing a minimal YAML uses defaults."""
    filepath = temp_definitions_dir / "test_beta.yaml"
    agent = AgentCatalogEntry.from_yaml_file(filepath)

    assert agent.id == "test_beta"
    assert agent.name == "BETA-2"
    assert agent.model == "gemini-2.5-pro"  # Default
    assert agent.system_prompt == ""
    assert isinstance(agent.memory, MemoryConfig)
    assert agent.memory.tier == "hot"
    assert isinstance(agent.guardrails, GuardrailsConfig)
    assert agent.tools == []


def test_agent_definition_string_bools_are_honored(tmp_path):
    """Test YAML string booleans are parsed without false-positive truthiness."""
    filepath = tmp_path / "strings.yaml"
    filepath.write_text(
        "name: STRINGS\n"
        "memory:\n"
        "  sparse_encoding: 'false'\n"
        '  silent_engrams: "no"\n'
        "  causal_memory: false\n"
        "guardrails:\n"
        "  max_turns: '0'\n"
    )

    agent = AgentCatalogEntry.from_yaml_file(filepath)

    assert agent.memory.sparse_encoding is False
    assert agent.memory.silent_engrams is False
    assert agent.memory.causal_memory is False
    assert agent.guardrails.max_turns is None


def test_agent_definition_invalid_tools_type(tmp_path):
    """Tools must be a YAML list of strings."""
    filepath = tmp_path / "invalid_tools.yaml"
    filepath.write_text("name: INVALID_TOOLS\ntools: not-a-list")

    with pytest.raises(ValueError, match="Expected YAML sequence for 'tools'"):
        AgentCatalogEntry.from_yaml_file(filepath)


def test_agent_definition_invalid_tools_entry_type(tmp_path):
    """Tool entries must be strings."""
    filepath = tmp_path / "invalid_tool_entry.yaml"
    filepath.write_text("name: INVALID_TOOL_ENTRY\ntools:\n  - 12\n  - search\n")

    with pytest.raises(TypeError, match="Invalid 'tools' entry"):
        AgentCatalogEntry.from_yaml_file(filepath)


def test_agent_definition_invalid_bool_raises_value_error(tmp_path):
    """Invalid boolean literals must fail fast with a clear validation error."""
    filepath = tmp_path / "invalid_bool.yaml"
    filepath.write_text("name: INVALID_BOOL\nmemory:\n  sparse_encoding: maybe\n")

    with pytest.raises(ValueError, match="Invalid boolean value"):
        AgentCatalogEntry.from_yaml_file(filepath)


def test_agent_definition_bool_values_with_casing_and_numeric_literals(tmp_path):
    """Boolean coercion should be stable across casing and numeric forms."""
    filepath = tmp_path / "bool_variants.yaml"
    filepath.write_text(
        "name: BOOL_VARIANTS\n"
        "memory:\n"
        "  sparse_encoding: 'FALSE'\n"
        "  silent_engrams: On\n"
        "  causal_memory: 1\n"
    )

    agent = AgentCatalogEntry.from_yaml_file(filepath)

    assert agent.memory.sparse_encoding is False
    assert agent.memory.silent_engrams is True
    assert agent.memory.causal_memory is True


def test_load_all_continues_after_invalid_agent_entry(tmp_path, caplog):
    """Registry load should continue when one entry fails parsing."""
    definitions_dir = tmp_path / "defs"
    definitions_dir.mkdir()
    (definitions_dir / "good.yaml").write_text("name: GOOD\n")
    (definitions_dir / "bad.yaml").write_text("name: BAD\nmemory:\n  sparse_encoding: maybe\n")

    registry = AgentRegistry()
    registry.clear()

    with caplog.at_level(logging.ERROR):
        registry.load_all(definitions_dir)

    assert "Failed to load bad.yaml" in caplog.text
    assert "good" in registry.agents
    assert "bad" not in registry.agents


@pytest.mark.skipif(os.name == "nt", reason="Symlink test can be flaky on some Windows setups")
def test_load_all_skips_broken_symlink(tmp_path, caplog):
    """Broken YAML symlinks should be skipped with a clear error log."""
    definitions_dir = tmp_path / "defs_symlink"
    definitions_dir.mkdir()
    (definitions_dir / "good.yaml").write_text("name: GOOD")
    broken = definitions_dir / "broken.yaml"
    broken.symlink_to("/does/not/exist/aether_heavy.yaml")

    registry = AgentRegistry()
    registry.clear()

    with caplog.at_level(logging.ERROR):
        registry.load_all(definitions_dir)

    assert "Broken symlink skipped" in caplog.text
    assert "good" in registry.agents
    assert "broken" not in registry.agents


def test_invalid_yaml_parsing(temp_definitions_dir):
    """Test parsing invalid YAML raises ValueError."""
    filepath = temp_definitions_dir / "invalid.yaml"
    with pytest.raises(ValueError, match="Invalid YAML schema"):
        AgentCatalogEntry.from_yaml_file(filepath)


def test_agent_definition_alias_still_points_to_catalog_entry():
    """Legacy AgentDefinition import remains a compatibility alias."""
    assert AgentDefinition is AgentCatalogEntry


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


def test_agent_registry_get_is_case_insensitive(tmp_path):
    """Registry lookup should match agent IDs irrespective of case."""
    filepath = tmp_path / "casey.yaml"
    filepath.write_text("name: CASEY")

    registry = AgentRegistry()
    registry.clear()
    registry.load_all(filepath.parent)

    assert registry.get("CASEY") is not None
    assert registry.get("cAsEy") is not None
    assert registry.get("missing") is None


def test_load_all_case_insensitive_duplicates(tmp_path, caplog, monkeypatch):
    """Case-only differences in agent IDs must still be treated as collisions."""
    duplicate_dir = tmp_path / "dupes_case"
    duplicate_dir.mkdir()
    (duplicate_dir / "first.yaml").write_text("name: ALPHA")
    (duplicate_dir / "second.yaml").write_text("name: ALPHA")

    original_from_yaml_file = AgentCatalogEntry.from_yaml_file

    def _same_id_from_yaml_file(path):
        entry = original_from_yaml_file(path)
        if path.name == "first.yaml":
            entry.id = "alpha"
        else:
            entry.id = "ALPHA"
        return entry

    registry = AgentRegistry()
    registry.clear()
    monkeypatch.setattr(AgentCatalogEntry, "from_yaml_file", _same_id_from_yaml_file)

    with caplog.at_level(logging.ERROR):
        registry.load_all(duplicate_dir)

    assert "Duplicate agent id 'ALPHA'" in caplog.text
    assert len(registry.agents) == 1


def test_load_all_refreshes_registry_and_clears_stale_agents(tmp_path):
    """Load from a new directory replaces old registry entries."""
    old_dir = tmp_path / "old"
    old_dir.mkdir()
    (old_dir / "old.yaml").write_text("name: OLD")

    r1 = AgentRegistry()
    r1.clear()
    r1.load_all(old_dir)
    assert "old" in r1.agents

    new_dir = tmp_path / "new"
    new_dir.mkdir()
    (new_dir / "new.yaml").write_text("name: NEW")

    r1.load_all(new_dir)
    assert "new" in r1.agents
    assert "old" not in r1.agents


def test_registry_rejects_duplicate_agent_id(tmp_path, caplog, monkeypatch):
    """Duplicate IDs should be surfaced and not silently overwrite each other."""
    duplicate_dir = tmp_path / "dupes"
    duplicate_dir.mkdir()
    (duplicate_dir / "first.yaml").write_text("name: FIRST")
    (duplicate_dir / "second.yaml").write_text("name: SECOND")

    original_from_yaml_file = AgentCatalogEntry.from_yaml_file

    def _same_id_from_yaml_file(path):
        entry = original_from_yaml_file(path)
        entry.id = "dupe-id"
        return entry

    registry = AgentRegistry()
    registry.clear()

    monkeypatch.setattr(AgentCatalogEntry, "from_yaml_file", _same_id_from_yaml_file)
    with caplog.at_level(logging.ERROR):
        registry.load_all(duplicate_dir)

    assert "Duplicate agent id 'dupe-id'" in caplog.text
    assert len(registry.agents) == 1
