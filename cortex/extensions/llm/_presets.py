from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Final, Optional

logger = logging.getLogger("cortex.extensions.llm.presets")

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
_VALID_TIERS: Final[frozenset[str]] = frozenset(
    {
        "frontier",
        "high",
        "local",
    }
)

# Valid cost classes
_VALID_COST_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "free",
        "low",
        "medium",
        "high",
        "variable",
    }
)


def _validate_model_policy(
    presets: dict[str, dict[str, Any]],
) -> None:
    """Enforce Model Policy — warn on prohibited model tiers.

    Axiom Ω₃ (Byzantine Default): models must be frontier or 'high' tier.
    Validates both the `tier` field and model name patterns.
    """
    for provider, config in presets.items():
        # Tier field validation
        tier = config.get("tier")
        if tier and tier not in _VALID_TIERS:
            logger.warning(
                "⚠️ [MODEL POLICY] %s has invalid tier '%s'. Valid: %s",
                provider,
                tier,
                sorted(_VALID_TIERS),
            )
        elif not tier:
            logger.debug(
                "[MODEL POLICY] %s missing 'tier' field.",
                provider,
            )

        # Cost class validation
        cost = config.get("cost_class")
        if cost and cost not in _VALID_COST_CLASSES:
            logger.warning(
                "⚠️ [MODEL POLICY] %s has invalid cost_class '%s'.",
                provider,
                cost,
            )

        # Regex defense: catch prohibited model name patterns
        default = config.get("default_model", "")
        if _PROHIBITED_TIERS.search(default):
            logger.warning(
                "⚠️ [MODEL POLICY] %s default_model '%s' uses "
                "prohibited tier. Update llm_presets.json.",
                provider,
                default,
            )

        intent_map = config.get("intent_model_map", {})
        for intent, model in intent_map.items():
            if _PROHIBITED_TIERS.search(model):
                logger.warning(
                    "⚠️ [MODEL POLICY] %s intent '%s' → '%s' uses prohibited tier.",
                    provider,
                    intent,
                    model,
                )


def load_presets() -> dict[str, dict[str, Any]]:
    """Lazy-load provider presets from assets with error recovery."""
    global _PRESETS_CACHE
    if _PRESETS_CACHE:
        return _PRESETS_CACHE

    path = Path(_ASSET_PATH)
    if not path.exists():
        logger.warning(
            "LLM presets asset not found at %s. Using empty defaults.",
            path,
        )
        return {}

    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            logger.error(
                "Invalid presets format in %s. Expected dict.",
                path,
            )
            return {}
        _validate_model_policy(data)
        _PRESETS_CACHE = data
        return _PRESETS_CACHE
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load LLM presets: %s", e)
        return {}


def get_preset_info(provider: str) -> Optional[dict[str, Any]]:
    """Return preset config for a provider, or None if not found."""
    return load_presets().get(provider)


def list_providers() -> list[str]:
    """Return all available preset provider names + 'custom'."""
    return list(load_presets().keys()) + ["custom"]


# ─── Tier & Cost-Aware Routing (Ω₂ Entropic Selection) ──────────


# Cost ordering: lower index = cheaper
_COST_RANK: dict[str, int] = {
    "free": 0,
    "low": 1,
    "medium": 2,
    "variable": 3,
    "high": 4,
}

# Tier ordering: higher index = stronger
_TIER_RANK: dict[str, int] = {
    "local": 0,
    "high": 1,
    "frontier": 2,
}


def resolve_model(provider: str, intent: str) -> Optional[str]:
    """Resolve the best model for a provider and intent.

    Returns the intent-specific model if mapped, otherwise the default model.
    Returns None if the provider doesn't exist.
    """
    info = get_preset_info(provider)
    if not info:
        return None

    intent_map = info.get("intent_model_map", {})
    return intent_map.get(intent, info.get("default_model"))


def providers_for_intent(
    intent: str,
    *,
    min_tier: str = "high",
    max_cost: Optional[str] = None,
    sort_by: str = "cost",
) -> list[tuple[str, str]]:
    """Return providers that support an intent, sorted by cost or tier.

    Args:
        intent: The intent to match (e.g., "architect", "code", "reasoning").
        min_tier: Minimum tier to include ("local", "high", "frontier").
        max_cost: Maximum cost class to include (None = no limit).
        sort_by: Sort key — "cost" (cheapest first) or "tier" (strongest first).

    Returns:
        List of (provider_name, model_name) tuples, sorted accordingly.
    """
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

        # Check if intent is in specialization or intent_model_map
        specializations = config.get("specialization", [])
        intent_map = config.get("intent_model_map", {})

        if intent in intent_map:
            model = intent_map[intent]
        elif intent in specializations:
            model = config.get("default_model", "")
        else:
            continue

        results.append((name, model, cost_rank, tier_rank))

    if sort_by == "cost":
        results.sort(key=lambda x: (x[2], -x[3]))  # cheapest first, then strongest
    else:
        results.sort(key=lambda x: (-x[3], x[2]))  # strongest first, then cheapest

    return [(name, model) for name, model, _, _ in results]


def frontier_providers(intent: str = "general") -> list[tuple[str, str]]:
    """Return only frontier-tier providers for an intent, cheapest first."""
    return providers_for_intent(intent, min_tier="frontier", sort_by="cost")


def cheapest_providers(intent: str = "general") -> list[tuple[str, str]]:
    """Return providers sorted by cost (cheapest first) for an intent."""
    return providers_for_intent(intent, sort_by="cost")


def routing_matrix() -> dict[str, dict[str, str]]:
    """Return the full intent→provider→model routing matrix.

    Useful for debugging and visualization.
    """
    presets = load_presets()
    intents = {"code", "reasoning", "creative", "architect", "general"}
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


def get_providers_by_tier(
    tier: str,
) -> list[str]:
    """Return provider names matching a tier (frontier/high/local)."""
    return [name for name, cfg in load_presets().items() if cfg.get("tier") == tier]


def get_providers_by_cost(
    cost_class: str,
) -> list[str]:
    """Return provider names matching a cost class."""
    return [name for name, cfg in load_presets().items() if cfg.get("cost_class") == cost_class]
