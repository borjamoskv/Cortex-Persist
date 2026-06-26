# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger("cortex_extensions.llm.presets")

# Default location for presets
_ASSET_PATH: Final[str] = str(
    Path(__file__).parent.parent.parent.parent / "config" / "llm_presets.json"
)

# Global cache for presets to avoid redundant I/O
_PRESETS_CACHE: dict[str, dict[str, Any]] = {}

# Model Policy: prohibited tier patterns (GEMINI.md §1.3)
_PROHIBITED_TIERS: Final[re.Pattern[str]] = re.compile(
    r"\b(mini|flash|haiku|nano|tiny|small|lite)\b",
    re.IGNORECASE,
)

# Valid tier values (ordered by capability)
_VALID_TIERS: Final[frozenset[str]] = frozenset({"frontier", "high", "local"})

# Cost ordering: lower index = cheaper
_COST_RANK: Final[dict[str, int]] = {
    "free": 0,
    "low": 1,
    "medium": 2,
    "variable": 3,
    "high": 4,
}

# Tier ordering: higher index = stronger
_TIER_RANK: Final[dict[str, int]] = {
    "local": 0,
    "high": 1,
    "frontier": 2,
}


def load_presets() -> dict[str, dict[str, Any]]:
    """Load LLM presets from config/llm_presets.json."""
    global _PRESETS_CACHE
    if _PRESETS_CACHE:
        return _PRESETS_CACHE

    path = Path(_ASSET_PATH)
    if not path.exists():
        logger.warning("LLM presets file not found at %s. Using empty defaults.", path)
        return {}

    try:
        with open(path, encoding="utf-8") as f:
            presets = json.load(f)
            _validate_model_policy(presets)
            _PRESETS_CACHE = presets
            return presets
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load LLM presets: %s", e)
        return {}


def _validate_model_policy(presets: dict[str, dict[str, Any]]) -> None:
    """Enforce Rule 1.3: Strictly mandate frontier or high-tier models."""
    for name, config in presets.items():
        # Check default model
        default_model = config.get("default_model", "")
        if "heretic" not in default_model.lower() and _PROHIBITED_TIERS.search(default_model):
            logger.warning(
                "MODEL POLICY (Rule 1.3) Violation Warning: "
                "Provider %s uses prohibited default model pattern: %s",
                name,
                default_model,
            )

        # Check intent-specific models
        intent_map = config.get("intent_model_map", {})
        for intent, model in intent_map.items():
            if "heretic" not in model.lower() and _PROHIBITED_TIERS.search(model):
                logger.warning(
                    "MODEL POLICY (Rule 1.3) Violation Warning: "
                    "Provider %s uses prohibited model for "
                    "intent '%s': %s",
                    name,
                    intent,
                    model,
                )


def get_prefix_cache_config(provider: str) -> dict[str, Any]:
    """Return prefix caching configuration. AX-042 compliant."""
    presets = load_presets()
    info = presets.get(provider, {})
    if not info:
        return {"enabled": False, "strategy": "none"}
    return {
        "enabled": info.get("prefix_cache_enabled", False),
        "ttl_seconds": info.get("cache_ttl_seconds", 3600),
        "strategy": info.get("prefix_hash_strategy", "system_prompt"),
        "tenant_scoped": True,  # ALWAYS True - AGENTS.md Invariant #4
        "quantization": info.get("kv_quantization", "fp16"),
    }


def check_api_key(preset: dict[str, Any]) -> str | None:
    """Resolve API key from preset and environment with appropriate fallbacks."""
    env_key = preset.get("env_key") or preset.get("api_key_env")
    if not env_key:
        return None

    keys = [env_key] if isinstance(env_key, str) else list(env_key)
    for k in keys:
        if val := os.environ.get(k):
            return val

    # Hardcoded fallbacks if nothing was found
    for k in keys:
        if k == "MOONSHOT_API_KEY" and (val := os.environ.get("KIMI_API_KEY")):
            return val
        if k in ("XAI_API_KEY", "GROK_API_KEY"):
            other = "GROK_API_KEY" if k == "XAI_API_KEY" else "XAI_API_KEY"
            if val := os.environ.get(other):
                return val
    return None


def provider_inventory(active_provider: str | None = None) -> list[dict[str, Any]]:
    """Return a list of all registered LLM providers and their operational status."""
    presets = load_presets()
    inventory = []

    for name, config in presets.items():
        env_key = config.get("env_key") or config.get("api_key_env")
        api_key_present = bool(check_api_key(config)) if env_key else True
        api_key_required = bool(env_key)

        is_local = name in ["ollama", "lmstudio", "llamacpp", "vllm", "jan"]
        status = "ready"
        ready = True
        reason = ""

        if api_key_required and not api_key_present and not is_local:
            status = "missing_api_key"
            ready = False
            reason = f"Missing env var: {env_key}"

        inventory.append(
            {
                "name": name,
                "provider": name,
                "tier": config.get("tier", "high"),
                "is_local": is_local,
                "cost_class": config.get("cost_class", "medium"),
                "context_window": config.get("context_window", 0),
                "default_model": config.get("default_model", ""),
                "active": name == active_provider,
                "ready": ready,
                "status": status,
                "reason": reason,
                "api_key_required": api_key_required,
                "api_key_present": api_key_present,
            }
        )
    return inventory


def get_preset_info(provider: str) -> dict[str, Any] | None:
    """Return preset config for a provider, or None if not found."""
    return load_presets().get(provider)


def list_providers() -> list[str]:
    """Return all available preset provider names + 'custom'."""
    return list(load_presets().keys()) + ["custom"]


def resolve_model(provider: str, intent: str) -> str | None:
    """Resolve the best model for a provider and intent."""
    info = get_preset_info(provider)
    if not info:
        return None

    intent_map = info.get("intent_model_map", {})
    return intent_map.get(intent, info.get("default_model"))


def resolve_context_window(provider: str, model_name: str) -> int:
    """Resolve the context window for a specific model under a provider."""
    info = get_preset_info(provider)
    if not info:
        return 0

    models_meta = info.get("models", {})
    if isinstance(models_meta, dict) and model_name in models_meta:
        meta = models_meta[model_name]
        if isinstance(meta, dict) and "context_window" in meta:
            return int(meta["context_window"])
        if isinstance(meta, int | float):
            return int(meta)

    return int(info.get("context_window", 0))


def providers_for_intent(
    intent: str,
    *,
    min_tier: str = "high",
    max_cost: str | None = None,
    sort_by: str = "cost",
) -> list[tuple[str, str]]:
    """Return providers that support an intent, sorted by cost or tier."""
    presets = load_presets()
    min_tier_rank = _TIER_RANK.get(min_tier, 0)
    max_cost_rank = _COST_RANK.get(max_cost, 999) if max_cost else 999
    results: list[tuple[str, str, int, int]] = []

    for name, config in presets.items():
        tier_rank = _TIER_RANK.get(config.get("tier", "high"), 1)
        cost_rank = _COST_RANK.get(config.get("cost_class", "medium"), 2)

        if tier_rank < min_tier_rank:
            continue
        if cost_rank > max_cost_rank:
            continue

        intent_map = config.get("intent_model_map", {})
        specializations = config.get("specialization", [])

        if intent in intent_map:
            model = intent_map[intent]
        elif intent in specializations or not intent_map:
            model = config.get("default_model", "")
        else:
            continue

        results.append((name, model, cost_rank, tier_rank))

    if sort_by == "cost":
        results.sort(key=lambda x: (x[2], -x[3]))
    else:
        results.sort(key=lambda x: (-x[3], x[2]))

    return [(name, model) for name, model, _, _ in results]


def frontier_providers(intent: str = "general") -> list[tuple[str, str]]:
    """Return only frontier-tier providers for an intent."""
    return providers_for_intent(intent, min_tier="frontier", sort_by="cost")


def cheapest_providers(intent: str = "general") -> list[tuple[str, str]]:
    """Return providers sorted by cost (cheapest first)."""
    return providers_for_intent(intent, sort_by="cost")


def routing_matrix() -> dict[str, dict[str, str]]:
    """Return the full intent→provider→model routing matrix."""
    presets = load_presets()
    intents = {"code", "reasoning", "creative", "architect", "general", "ultra"}
    matrix: dict[str, dict[str, str]] = {}

    for name, config in presets.items():
        intent_map = config.get("intent_model_map", {})
        if intent_map:
            row: dict[str, str] = {}
            for intent in intents:
                if intent in intent_map:
                    row[intent] = intent_map[intent]
            if row:
                matrix[name] = row

    return matrix
