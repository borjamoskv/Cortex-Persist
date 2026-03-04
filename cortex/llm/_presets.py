from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger("cortex.llm.presets")

_ASSET_PATH: Final[str] = str(Path(__file__).parent.parent.parent / "config" / "llm_presets.json")

# Global cache for presets to avoid redundant I/O
_PRESETS_CACHE: dict[str, dict[str, Any]] = {}


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
