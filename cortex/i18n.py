"""CORTEX v5.1 — Internationalization Module (i18n).

Sovereign-grade multilingual support for the CORTEX ecosystem.
Optimized for low-latency lookups (LRU) and modular asset management.
Provides thread-safe atomic translation loading and fallback hierarchies.
"""

from __future__ import annotations

import json
import logging
import threading
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Final, NamedTuple, TypeAlias

logger = logging.getLogger(__name__)

__all__ = [
    "CacheStats",
    "DEFAULT_LANGUAGE",
    "Lang",
    "SUPPORTED_LANGUAGES",
    "TranslationKey",
    "clear_cache",
    "get_cache_info",
    "get_supported_languages",
    "get_trans",
]


class Lang(str, Enum):
    """Supported language codes (ISO 639-1)."""

    EN = "en"
    ES = "es"
    EU = "eu"


# Constants
DEFAULT_LANGUAGE: Final[Lang] = Lang.EN
SUPPORTED_LANGUAGES: Final[frozenset[Lang]] = frozenset(Lang)
_LANG_LOOKUP: Final[dict[str, Lang]] = {lang.value: lang for lang in Lang}
_ASSET_PATH: Final[Path] = Path(__file__).parent / "assets" / "translations.json"

# Global holder for loaded translations. Swapped atomically.
_TRANSLATIONS: dict[str, dict[str, str]] = {}
_LOAD_LOCK: Final[threading.Lock] = threading.Lock()


def _load_translations() -> dict[str, dict[str, str]]:
    """Lazy-load translations with thread-safe atomic reference swap."""
    if _TRANSLATIONS:
        return _TRANSLATIONS

    with _LOAD_LOCK:
        # Double-check pattern
        if _TRANSLATIONS:
            return _TRANSLATIONS

        try:
            path = _ASSET_PATH.resolve()
            if not path.exists():
                logger.error("I18N Sovereign Failure: Asset missing at %s", path)
                return {}

            data = json.loads(path.read_text(encoding="utf-8"))
            # We update in-place to preserve references for importers (like unit tests).
            # This is thread-safe due to _LOAD_LOCK.
            _TRANSLATIONS.clear()
            _TRANSLATIONS.update(data)
            logger.debug("I18N: Synchronized %d keys from assets", len(_TRANSLATIONS))
        except (json.JSONDecodeError, OSError) as exc:
            logger.critical("I18N: Fatal failure loading assets: %s", exc)
            return {}

    return _TRANSLATIONS


def get_supported_languages() -> frozenset[Lang]:
    """Returns the set of languages officially supported by CORTEX."""
    return SUPPORTED_LANGUAGES


TranslationKey: TypeAlias = str


def _normalize_lang(lang: str | Lang | None) -> Lang:
    """Fast normalization of language codes with primary-tag fallback."""
    if isinstance(lang, Lang):
        return lang
    if not lang or not isinstance(lang, str):
        return DEFAULT_LANGUAGE

    # Exact match
    code = lang.lower()
    if match := _LANG_LOOKUP.get(code):
        return match

    # Primary tag extraction (e.g. "en-US" -> "en")
    primary = code.split("-", 1)[0].strip()[:2]
    return _LANG_LOOKUP.get(primary, DEFAULT_LANGUAGE)


@lru_cache(maxsize=2048)
def _cached_trans(key: TranslationKey, lang_code: Lang) -> str:
    """Atomic cached lookup with sovereign fallback hierarchy."""
    translations = _load_translations()
    entry = translations.get(key)

    if entry is None:
        logger.warning("I18N: Missing key [%s]", key)
        return key

    # 1. Primary Language Lookup
    text = entry.get(lang_code.value)
    if text is not None:
        return text

    # 2. Sovereign Fallback (to default language)
    if lang_code != DEFAULT_LANGUAGE:
        logger.debug("I18N: Key [%s] falling back to default [%s]", key, DEFAULT_LANGUAGE.value)
        if (text := entry.get(DEFAULT_LANGUAGE.value)) is not None:
            return text

    logger.error("I18N: Key [%s] found no valid translation in any language.", key)
    return key


def get_trans(key: TranslationKey, lang: Lang | str | None = Lang.EN, **kwargs: str) -> str:
    """
    Retrieve localized string formatted with variables.
    O(1) lookup via LRU. Supports dynamic string interpolation.
    """
    text = _cached_trans(key, _normalize_lang(lang))

    if kwargs and text != key:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError) as exc:
            logger.error("I18N Formatting Error [%s]: %s", key, exc)

    return text


class CacheStats(NamedTuple):
    """Mirror of functools._CacheInfo for strict typing."""

    hits: int
    misses: int
    maxsize: int | None
    currsize: int


def get_cache_info() -> CacheStats:
    """Diagnostic observability for translation performance."""
    info = _cached_trans.cache_info()
    return CacheStats(info.hits, info.misses, info.maxsize, info.currsize)


def clear_cache() -> None:
    """Hard-reset the translation engine state."""
    _cached_trans.cache_clear()
    _TRANSLATIONS.clear()
