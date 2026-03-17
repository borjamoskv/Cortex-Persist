"""CORTEX v6+ — Declarative Agent Schema (YAML → Engine).

Pydantic models that define the YAML schema for a CORTEX agent role.
Inspired by InitRunner's declarative approach but hydrated with the
full Sovereign stack: thermodynamic memory, ART Gate, BIFT routing,
sparse encoding, and session guardrails.

Example role.yaml:
    name: "research-assistant"
    model: "gemini-2.5-pro"
    system_prompt: "You are a research assistant..."
    memory:
      art_rho: 0.85
      pruning_threshold: 0.2
      retrieval_band: "beta"
      tier: "warm"
    guardrails:
      max_session_tokens: 100000
      warn_threshold: 0.8
    tools:
      - filesystem
      - http
      - mcp
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryConfig(BaseModel):
    """Memory configuration for an agent role."""

    art_rho: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        description="ART vigilance parameter. Higher = more granular memory.",
    )
    pruning_threshold: float = Field(
        default=0.2,
        ge=0.0,
        le=1.0,
        description="ATP threshold for thermodynamic pruning.",
    )
    retrieval_band: str = Field(
        default="beta",
        description="Default BIFT retrieval band (gamma/beta/theta/delta).",
    )
    tier: str = Field(
        default="hot",
        description="Default CMS frequency tier (hot/warm/cold/permafrost).",
    )
    sparse_encoding: bool = Field(
        default=False,
        description="Enable Mushroom Body sparse encoding on embeddings.",
    )
    silent_engrams: bool = Field(
        default=True,
        description="Enable dual-trace consolidation (active + silent).",
    )
    maturation_days: float = Field(
        default=3.0,
        ge=0.0,
        description="Days for silent engrams to mature.",
    )
    working_memory_tokens: int = Field(
        default=8192,
        gt=0,
        description="L1 working memory token budget.",
    )


class GuardrailConfig(BaseModel):
    """Session-level guardrails for an agent."""

    max_session_tokens: int = Field(
        default=100_000,
        gt=0,
        description="Hard cap on total tokens consumed per session.",
    )
    warn_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Ratio at which to emit a budget warning.",
    )
    max_turns: int = Field(
        default=0,
        ge=0,
        description="Max conversation turns (0 = unlimited).",
    )


class AgentRole(BaseModel):
    """Top-level schema for a CORTEX agent role definition.

    This is the Pydantic model that maps 1:1 to a role.yaml file.
    """

    name: str = Field(
        ...,
        min_length=1,
        description="Agent name identifier.",
    )
    model: str = Field(
        default="gemini-2.5-pro",
        description="LLM model to use.",
    )
    system_prompt: str = Field(
        default="You are a helpful assistant.",
        description="System prompt injected at the start of every session.",
    )
    tenant_id: str = Field(
        default="default",
        description="Tenant isolation identifier.",
    )
    project_id: str = Field(
        default="default",
        description="Project scope for memory operations.",
    )
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="Memory subsystem configuration.",
    )
    guardrails: GuardrailConfig = Field(
        default_factory=GuardrailConfig,
        description="Session guardrail configuration.",
    )
    tools: list[str] = Field(
        default_factory=list,
        description="List of enabled tool names.",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary metadata for extensions.",
    )

    @classmethod
    def from_yaml_file(cls, path: str) -> AgentRole:
        """Load an AgentRole from a YAML file."""
        from pathlib import Path

        import yaml

        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
        if not isinstance(data, dict):
            msg = f"Expected a YAML mapping, got {type(data).__name__}"
            raise ValueError(msg)
        return cls(**data)

    def to_yaml(self) -> str:
        """Serialize to YAML string."""
        import yaml

        return yaml.dump(
            self.model_dump(exclude_defaults=True),
            default_flow_style=False,
            sort_keys=False,
        )

    @classmethod
    def scaffold(cls) -> AgentRole:
        """Generate a scaffold AgentRole with sensible defaults."""
        return cls(
            name="my-agent",
            model="gemini-2.5-pro",
            system_prompt="You are a sovereign CORTEX agent.",
            memory=MemoryConfig(),
            guardrails=GuardrailConfig(),
            tools=["filesystem", "http"],
        )
