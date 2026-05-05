"""CORTEX v6 — Agent Registry (Dynamic Loading).

Dynamically loads Swarm Specialists and Sovereign Agents from YAML definitions
located in `cortex.agents/definitions/`. This allows modifying agent
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

logger = logging.getLogger("cortex.extensions.agents.registry")

_DEFINITIONS_DIR = Path(__file__).parent / "definitions"
_TRUE_BOOL_LITERALS = {"1", "true", "yes", "on", "y"}
_FALSE_BOOL_LITERALS = {"", "0", "false", "no", "off", "n"}


def _coerce_bool(value: Any, default: bool, *, field: str) -> bool:
    """Parse bool-like values from YAML with deterministic semantics."""
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if value == 1:
            return True
        if value == 0:
            return False
        raise ValueError(f"Invalid boolean value for '{field}': {value!r}")
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_BOOL_LITERALS:
            return True
        if normalized in _FALSE_BOOL_LITERALS:
            return False
        raise ValueError(f"Invalid boolean value for '{field}': {value!r}")
    raise TypeError(f"Invalid boolean value for '{field}': {type(value).__name__}")


def _as_str_mapping(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError(f"Expected YAML mapping for '{field}', got {type(value).__name__}")
    return value


def _as_str_list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Expected YAML sequence for '{field}', got {type(value).__name__}")

    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise TypeError(f"Invalid '{field}' entry in {field}: {type(item).__name__}")
        result.append(item)
    return result


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
        raw_sparse_encoding = d.get("sparse_encoding", True)
        raw_silent_engrams = d.get("silent_engrams", True)
        raw_causal_memory = d.get("causal_memory", False)
        return cls(
            art_rho=float(d.get("art_rho", 0.95)),
            pruning_threshold=float(d.get("pruning_threshold", 0.1)),
            retrieval_band=str(d.get("retrieval_band", "gamma")),
            tier=str(d.get("tier", "hot")),
            sparse_encoding=_coerce_bool(raw_sparse_encoding, True, field="sparse_encoding"),
            silent_engrams=_coerce_bool(raw_silent_engrams, True, field="silent_engrams"),
            causal_memory=_coerce_bool(raw_causal_memory, False, field="causal_memory"),
        )


@dataclass
class GuardrailsConfig:
    """Execution boundaries for an agent."""

    max_session_tokens: int = 100000
    warn_threshold: float = 0.8
    max_turns: int | None = 50

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> GuardrailsConfig:
        """Parse from YAML dict safely."""
        raw_max_turns = d.get("max_turns", 50)
        if "max_turns" in d and raw_max_turns in (None, "", 0, "0"):
            max_turns: int | None = None
        else:
            max_turns = int(raw_max_turns)

        return cls(
            max_session_tokens=int(d.get("max_session_tokens", 100000)),
            warn_threshold=float(d.get("warn_threshold", 0.8)),
            max_turns=max_turns,
        )


@dataclass
class AgentCatalogEntry:
    """A sovereign agent loaded from a YAML definition catalog."""

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
                from cortex.extensions.llm._presets import resolve_model

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
                from cortex.extensions.llm._presets import get_preset_info

                preset = get_preset_info(self.provider)
                if preset:
                    info["tier"] = preset.get("tier", "high")
                    info["cost_class"] = preset.get("cost_class", "medium")
            except ImportError as e:
                import logging

                logging.debug("Routing info preset resolution skipped: %s", e)
        return info

    @classmethod
    def from_yaml_file(cls, filepath: Path) -> AgentCatalogEntry:
        """Load an agent catalog entry from a YAML file."""
        import yaml

        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
        except (FileNotFoundError, OSError) as e:
            raise ValueError(f"Failed to load YAML {filepath}: {e}") from e
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {filepath}: {e}") from e

        if not isinstance(data, dict):
            raise ValueError(f"Invalid YAML schema in {filepath} (must be a dict).")

        mem_conf = _as_str_mapping(data.get("memory", {}), "memory")
        gr_conf = _as_str_mapping(data.get("guardrails", {}), "guardrails")

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
            tools=_as_str_list(data.get("tools", []), "tools"),
        )


class AgentRegistry:
    """Singleton registry for all CORTEX YAML agent catalog entries.

    Loads definitions lazily upon first access.
    """

    _instance: AgentRegistry | None = None
    _agents: dict[str, AgentCatalogEntry] = {}
    _loaded: bool = False

    def __new__(cls) -> AgentRegistry:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def load_all(self, definitions_dir: Path | None = None) -> None:
        """Scan and load all .yaml catalog entries in the directory.

        Args:
            definitions_dir: Override path, defaults to cortex.agents/definitions
        """
        self._agents.clear()
        directory = definitions_dir or _DEFINITIONS_DIR

        if not directory.exists() or not directory.is_dir():
            logger.warning("🔍 [REGISTRY] Definitions dict not found: %s", directory)
            self._loaded = True
            return

        loaded_count = 0
        duplicate_count = 0
        seen_agent_ids: set[str] = set()
        for yaml_path in directory.glob("*.yaml"):
            if yaml_path.is_symlink() and not yaml_path.exists():
                logger.error(
                    "☠️ [REGISTRY] Broken symlink skipped: %s -> %s",
                    yaml_path.name,
                    yaml_path.resolve(),
                )
                continue
            try:
                agent_def = AgentCatalogEntry.from_yaml_file(yaml_path)
                normalized_id = agent_def.id.casefold()
                if normalized_id in seen_agent_ids:
                    duplicate_count += 1
                    logger.error(
                        "❌ [REGISTRY] Duplicate agent id '%s' in '%s'; skipping duplicate definition.",
                        agent_def.id,
                        yaml_path.name,
                    )
                    continue
                self._agents[agent_def.id] = agent_def
                seen_agent_ids.add(normalized_id)
                loaded_count += 1
                logger.debug("🧬 [REGISTRY] Loaded agent: %s (%s)", agent_def.name, agent_def.id)
            except (ValueError, TypeError) as e:
                logger.error("☠️ [REGISTRY] Failed to load %s: %s", yaml_path.name, e)

        logger.info("🏛️ [REGISTRY] Loaded %d sovereign agents.", loaded_count)
        if duplicate_count:
            logger.warning(
                "🧨 [REGISTRY] Skipped %d duplicate agent definition(s) in %s.",
                duplicate_count,
                directory,
            )
        if not self._agents:
            logger.warning(
                "🕳️ [REGISTRY] No valid agent definitions loaded from %s. "
                "Check definitions syntax and required keys.",
                directory,
            )
        self._loaded = True

    @property
    def agents(self) -> dict[str, AgentCatalogEntry]:
        """Get the mapping of agent ID to AgentCatalogEntry."""
        if not self._loaded:
            self.load_all()
        return dict(self._agents)

    def get(self, agent_id: str) -> AgentCatalogEntry | None:
        """Retrieve a specific agent catalog entry by its ID (filename stem)."""
        if not self._loaded:
            self.load_all()
        if agent_id in self._agents:
            return self._agents.get(agent_id)
        normalized = agent_id.casefold()
        for existing_id, agent in self._agents.items():
            if existing_id.casefold() == normalized:
                return agent
        return None

    def clear(self) -> None:
        """Clear the registry (useful for testing or hot reloading)."""
        self._agents.clear()
        self._loaded = False


# ─── Module-Level Convenience ──────────────────────────────────


def list_agents() -> list[str]:
    """Return all registered agent IDs."""
    return list(AgentRegistry().agents.keys())


def get_agent(agent_id: str) -> AgentCatalogEntry | None:
    """Retrieve an agent catalog entry by ID."""
    return AgentRegistry().get(agent_id)


# Backward-compatibility alias for older imports. Prefer AgentCatalogEntry.
AgentDefinition = AgentCatalogEntry
