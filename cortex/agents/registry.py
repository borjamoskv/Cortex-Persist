"""CORTEX v6 — Agent Registry (Dynamic Loading).

Dynamically loads Swarm Specialists and Sovereign Agents from YAML definitions
located in `cortex/agents/definitions/`. This allows modifying agent
personas, prompts, and toolsets without altering code.

Axioms:
    Ω₀ (Self-Reference): The system reads its own definitions.
    Ω₄ (Aesthetic Integrity): Decoupled configuration from logic.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.agents.registry")

_DEFINITIONS_DIR = Path(__file__).parent / "definitions"


@dataclass
class MemoryConfig:
    """Memory parameters for an agent."""
    art_rho: float = 0.95
    pruning_threshold: float = 0.1
    retrieval_band: str = "gamma"
    tier: str = "hot"
    sparse_encoding: bool = True
    silent_engrams: bool = True
    causal_memory: bool = False  # Epoch 8: Enable causal DAG tracing

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> MemoryConfig:
        """Parse from YAML dict safely."""
        return cls(
            art_rho=float(d.get("art_rho", 0.95)),
            pruning_threshold=float(d.get("pruning_threshold", 0.1)),
            retrieval_band=str(d.get("retrieval_band", "gamma")),
            tier=str(d.get("tier", "hot")),
            sparse_encoding=bool(d.get("sparse_encoding", True)),
            silent_engrams=bool(d.get("silent_engrams", True)),
            causal_memory=bool(d.get("causal_memory", False)),
        )


@dataclass
class GuardrailsConfig:
    """Execution boundaries for an agent."""
    max_session_tokens: int = 100000
    warn_threshold: float = 0.8
    max_turns: int = 50

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GuardrailsConfig:
        """Parse from YAML dict safely."""
        return cls(
            max_session_tokens=int(d.get("max_session_tokens", 100000)),
            warn_threshold=float(d.get("warn_threshold", 0.8)),
            max_turns=int(d.get("max_turns", 50)),
        )


@dataclass
class AgentDefinition:
    """A sovereign agent loaded from a YAML definition."""
    id: str  # Filename stem without .yaml
    name: str
    model: str
    system_prompt: str
    tenant_id: str = "default"
    project_id: str = "system"
    provider: str = ""  # Preferred LLM provider (e.g., "gemini", "openai")
    intent: str = ""  # Preferred intent (e.g., "architect", "code", "reasoning")
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    guardrails: GuardrailsConfig = field(default_factory=GuardrailsConfig)
    tools: list[str] = field(default_factory=list)

    @property
    def resolved_model(self) -> str:
        """Resolve the best model via preset routing.

        Priority: provider+intent dynamic resolution → static model fallback.
        """
        if self.provider and self.intent:
            try:
                from cortex.llm._presets import resolve_model

                resolved = resolve_model(self.provider, self.intent)
                if resolved:
                    return resolved
            except ImportError:
                pass
        return self.model

    @property
    def routing_info(self) -> dict[str, str]:
        """Return tier, cost_class, and resolved model for this agent."""
        info: dict[str, str] = {
            "model": self.resolved_model,
            "provider": self.provider or "default",
            "intent": self.intent or "general",
            "tier": "high",
            "cost_class": "medium",
        }
        if self.provider:
            try:
                from cortex.llm._presets import get_preset_info

                preset = get_preset_info(self.provider)
                if preset:
                    info["tier"] = preset.get("tier", "high")
                    info["cost_class"] = preset.get("cost_class", "medium")
            except ImportError as e:
                import logging
                logging.debug("Routing info preset resolution skipped: %s", e)
        return info

    @classmethod
    def from_yaml_file(cls, filepath: Path) -> AgentDefinition:
        """Load an AgentDefinition from a YAML file."""
        import yaml

        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Failed to load YAML {filepath}: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML schema in {filepath} (must be a dict).")

        mem_conf = data.get("memory", {})
        gr_conf = data.get("guardrails", {})

        return cls(
            id=filepath.stem,
            name=str(data.get("name", filepath.stem.upper())),
            model=str(data.get("model", "gemini-2.5-pro")),
            system_prompt=str(data.get("system_prompt", "")).strip(),
            tenant_id=str(data.get("tenant_id", "default")),
            project_id=str(data.get("project_id", "system")),
            provider=str(data.get("provider", "")),
            intent=str(data.get("intent", "")),
            memory=MemoryConfig.from_dict(mem_conf) if mem_conf else MemoryConfig(),
            guardrails=GuardrailsConfig.from_dict(gr_conf) if gr_conf else GuardrailsConfig(),
            tools=list(data.get("tools", [])),
        )


class AgentRegistry:
    """Singleton registry for all CORTEX YAML agent definitions.
    
    Loads definitions lazily upon first access.
    """

    _instance: AgentRegistry | None = None
    _agents: dict[str, AgentDefinition] = {}
    _loaded: bool = False

    def __new__(cls) -> AgentRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_all(self, definitions_dir: Path | None = None) -> None:
        """Scan and load all .yaml definitions in the directory.
        
        Args:
            definitions_dir: Override path, defaults to cortex/agents/definitions
        """
        directory = definitions_dir or _DEFINITIONS_DIR
        
        if not directory.exists() or not directory.is_dir():
            logger.warning("🔍 [REGISTRY] Definitions dict not found: %s", directory)
            self._loaded = True
            return

        loaded_count = 0
        for yaml_path in directory.glob("*.yaml"):
            try:
                agent_def = AgentDefinition.from_yaml_file(yaml_path)
                self._agents[agent_def.id] = agent_def
                loaded_count += 1
                logger.debug("🧬 [REGISTRY] Loaded agent: %s (%s)", agent_def.name, agent_def.id)
            except Exception as e:  # noqa: BLE001
                logger.error("☠️ [REGISTRY] Failed to load %s: %s", yaml_path.name, e)

        logger.info("🏛️ [REGISTRY] Loaded %d sovereign agents.", loaded_count)
        self._loaded = True

    @property
    def agents(self) -> dict[str, AgentDefinition]:
        """Get the mapping of agent ID to AgentDefinition."""
        if not self._loaded:
            self.load_all()
        return dict(self._agents)

    def get(self, agent_id: str) -> AgentDefinition | None:
        """Retrieve a specific agent definition by its ID (filename stem)."""
        if not self._loaded:
            self.load_all()
        return self._agents.get(agent_id)

    def clear(self) -> None:
        """Clear the registry (useful for testing or hot reloading)."""
        self._agents.clear()
        self._loaded = False


# ─── Module-Level Convenience ──────────────────────────────────


def list_agents() -> list[str]:
    """Return all registered agent IDs."""
    return list(AgentRegistry().agents.keys())


def get_agent(agent_id: str) -> AgentDefinition | None:
    """Retrieve an agent definition by ID."""
    return AgentRegistry().get(agent_id)
