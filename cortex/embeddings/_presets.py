"""CORTEX v5.0 — Embedding Provider Presets Loader.

Loads embedding provider configurations from config/embedding_presets.json.
Mirrors the pattern of cortex.llm._presets for LLM providers.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Final

logger = logging.getLogger("cortex.embeddings.presets")

_ASSET_PATH: Final[str] = str(
    Path(__file__).parent.parent.parent / "config" / "embedding_presets.json"
)

# Global cache to avoid redundant I/O
_PRESETS_CACHE: dict[str, dict[str, Any]] = {}


def load_embedding_presets() -> dict[str, dict[str, Any]]:
    """Lazy-load embedding provider presets from assets.

    Returns:
        Dict mapping provider name to its configuration.
        Empty dict on failure (logged, never raises).
    """
    global _PRESETS_CACHE
    if _PRESETS_CACHE:
        return _PRESETS_CACHE

    path = Path(_ASSET_PATH)
    if not path.exists():
        logger.warning(
            "Embedding presets asset not found at %s. Using hardcoded defaults.", path
        )
        return {}

    try:
        data = json.loads(path.read_text())
        if not isinstance(data, dict):
            logger.error("Invalid embedding presets format in %s. Expected dict.", path)
            return {}
        _PRESETS_CACHE = data
        logger.debug("Loaded %d embedding presets from %s", len(data), path)
        return _PRESETS_CACHE
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to load embedding presets: %s", e)
        return {}


def get_embedding_preset(provider: str) -> dict[str, Any] | None:
    """Return preset config for an embedding provider, or None if not found."""
    return load_embedding_presets().get(provider)


def list_embedding_providers() -> list[str]:
    """Return all available embedding provider names."""
    return list(load_embedding_presets().keys())
