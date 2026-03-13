from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger("cortex.llm.presets")

_ASSET_PATH: Final[str] = str(Path(__file__).parent.parent.parent / "config" / "llm_presets.json")

# Global cache for presets to avoid redundant I/O
_PRESETS_CACHE: dict[str, dict[str, Any]] = {}

# Model Policy: prohibited tier patterns (GEMINI.md §1.3)
_PROHIBITED_TIERS: Final[re.Pattern[str]] = re.compile(
    r"\b(mini|flash|haiku|nano|tiny|small|lite)\b", re.IGNORECASE,
)


def _validate_model_policy(presets: dict[str, dict[str, Any]]) -> None:
    """Enforce Model Policy — warn on prohibited model tiers.

    Axiom Ω₃ (Byzantine Default): models must be frontier or 'high' tier.
    """
    for provider, config in presets.items():
        default = config.get("default_model", "")
        if _PROHIBITED_TIERS.search(default):
            logger.warning(
                "⚠️ [MODEL POLICY] %s default_model '%s' uses prohibited tier. "
                "Update config/llm_presets.json to use frontier model.",
                provider, default,
            )

        intent_map = config.get("intent_model_map", {})
        for intent, model in intent_map.items():
            if _PROHIBITED_TIERS.search(model):
                logger.warning(
                    "⚠️ [MODEL POLICY] %s intent '%s' → '%s' uses prohibited tier.",
                    provider, intent, model,
                )


def load_presets() -> dict[str, dict[str, Any]]:
    """Lazy-load provider presets from assets with error recovery."""
    global _PRESETS_CACHE
    if _PRESETS_CACHE:
        return _PRESETS_CACHE

    path = Path(_ASSET_PATH)
    if not path.exists():
        logger.warning("LLM presets asset not found at %s. Using empty defaults.", path)
        return {}

    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            logger.error("Invalid presets format in %s. Expected dict.", path)
            return {}
        _validate_model_policy(data)
        _PRESETS_CACHE = data
        return _PRESETS_CACHE
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load LLM presets: %s", e)
        return {}


def get_preset_info(provider: str) -> dict[str, Any] | None:
    """Return preset config for a provider, or None if not found."""
    return load_presets().get(provider)


def list_providers() -> list[str]:
    """Return all available preset provider names + 'custom'."""
    return list(load_presets().keys()) + ["custom"]
