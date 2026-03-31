"""Tests for YAML Agent Interface and Session Guardrails (Phase 3)."""

import tempfile

import pytest

from cortex.agent.loader import compile_agent
from cortex.agent.schema import AgentRole, GuardrailConfig, MemoryConfig
from cortex.memory.guardrails import SessionGuardrail
from cortex.memory.models import MemoryEvent
from cortex.memory.working import WorkingMemoryL1

# ─── Agent Schema Tests ─────────────────────────────────────────────


class TestAgentSchema:
    def test_scaffold_creates_valid_role(self):
        role = AgentRole.scaffold()
        assert role.name == "my-agent"
        assert role.model == "gemini-2.5-pro"
        assert len(role.tools) == 2

    def test_from_yaml_roundtrip(self):
        role = AgentRole.scaffold()
        yaml_str = role.to_yaml()

        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml_str)
            f.flush()
            loaded = AgentRole.from_yaml_file(f.name)

        assert loaded.name == role.name
        assert loaded.model == role.model

    def test_memory_config_defaults(self):
        mc = MemoryConfig()
        assert mc.art_rho == 0.85
        assert mc.pruning_threshold == 0.2
        assert mc.retrieval_band == "beta"
        assert mc.sparse_encoding is False
        assert mc.silent_engrams is True

    def test_guardrail_config_defaults(self):
        gc = GuardrailConfig()
        assert gc.max_session_tokens == 100_000
        assert gc.warn_threshold == 0.8
        assert gc.max_turns == 0

    def test_custom_yaml(self):
        yaml_content = """
name: "test-agent"
model: "claude-sonnet"
system_prompt: "You are a tester."
memory:
  art_rho: 0.9
  sparse_encoding: true
guardrails:
  max_session_tokens: 50000
  max_turns: 10
tools:
  - filesystem
  - http
  - mcp
"""
        with tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            role = AgentRole.from_yaml_file(f.name)

        assert role.name == "test-agent"
        assert role.model == "claude-sonnet"
        assert role.memory.art_rho == 0.9
        assert role.memory.sparse_encoding is True
        assert role.guardrails.max_session_tokens == 50000
        assert role.guardrails.max_turns == 10
        assert len(role.tools) == 3


# ─── Agent Loader Tests ─────────────────────────────────────────────


class TestAgentLoader:
    def test_compile_creates_agent(self):
        role = AgentRole.scaffold()
        agent = compile_agent(role)
        assert agent.name == "my-agent"
        assert agent.model == "gemini-2.5-pro"

    def test_compile_with_sparse_encoding(self):
        role = AgentRole(
            name="sparse-agent",
            memory=MemoryConfig(sparse_encoding=True),
        )
        agent = compile_agent(role)
        assert agent.sparse_encoder is not None

    def test_compile_without_sparse_encoding(self):
        role = AgentRole(name="normal-agent")
        agent = compile_agent(role)
        assert agent.sparse_encoder is None

    def test_agent_status(self):
        role = AgentRole.scaffold()
        agent = compile_agent(role)
        status = agent.status()
        assert "name" in status
        assert "guardrail" in status
        assert status["art_rho"] == 0.85


# ─── Session Guardrail Tests ────────────────────────────────────────


class TestSessionGuardrail:
    def test_consume_within_budget(self):
        g = SessionGuardrail(max_tokens=1000)
        assert g.consume(500) is True
        assert g.consumed == 500
        assert g.remaining == 500

    def test_consume_exceeds_budget(self):
        g = SessionGuardrail(max_tokens=100)
        assert g.consume(50) is True
        assert g.consume(60) is False  # 50 + 60 > 100
        assert g.consumed == 50  # Rejected, not consumed

    def test_warn_threshold(self):
        g = SessionGuardrail(max_tokens=100, warn_threshold=0.5)
        g.consume(40)
        assert not g._warned
        g.consume(15)  # 55% > 50%
        assert g._warned

    def test_turn_limit(self):
        g = SessionGuardrail(max_tokens=10000, max_turns=2)
        g.tick_turn()
        g.tick_turn()
        # Now at limit
        assert g.consume(10) is False

    def test_utilization(self):
        g = SessionGuardrail(max_tokens=200)
        g.consume(100)
        assert g.utilization == pytest.approx(0.5)

    def test_status_dict(self):
        g = SessionGuardrail(max_tokens=1000)
        g.consume(250)
        g.tick_turn()
        s = g.status()
        assert s["consumed"] == 250
        assert s["remaining"] == 750
        assert s["turns"] == 1


# ─── L1 + Guardrail Integration Tests ───────────────────────────────


class TestL1GuardrailIntegration:
    def _event(self, tokens: int = 100) -> MemoryEvent:
        return MemoryEvent(
            role="user",
            content="test " * tokens,
            token_count=tokens,
            session_id="s1",
        )

    def test_l1_without_guardrail(self):
        wm = WorkingMemoryL1(max_tokens=1000)
        wm.add_event(self._event(500))
        assert wm.current_tokens == 500

    def test_l1_with_guardrail_accepts(self):
        g = SessionGuardrail(max_tokens=1000)
        wm = WorkingMemoryL1(max_tokens=500, guardrail=g)
        wm.add_event(self._event(200))
        assert g.consumed == 200

    def test_l1_with_guardrail_rejects(self):
        g = SessionGuardrail(max_tokens=100)
        wm = WorkingMemoryL1(max_tokens=500, guardrail=g)
        wm.add_event(self._event(80))

        with pytest.raises(RuntimeError, match="Session budget exhausted"):
            wm.add_event(self._event(30))  # 80 + 30 > 100
