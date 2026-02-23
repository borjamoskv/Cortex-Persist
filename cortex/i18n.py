"""CORTEX v5.3 — Internationalization Module (i18n).

Sovereign-grade multilingual support for the CORTEX ecosystem.
Optimized for low-latency lookups (LRU) and modular asset management.
Provides thread-safe atomic translation loading and fallback hierarchies.
"""

from __future__ import annotations

import contextvars
import json
import logging
import threading
from collections.abc import Generator
from contextlib import contextmanager
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Any, Final, NamedTuple, TypeAlias

logger = logging.getLogger(__name__)

# Type Aliases
TranslationKey: TypeAlias = str
TranslationMap: TypeAlias = dict[str, str]
LocaleData: TypeAlias = dict[TranslationKey, TranslationMap]


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
_TRANSLATIONS: LocaleData = {}
_LOAD_LOCK: Final[threading.Lock] = threading.Lock()

# Thread-local context for language overrides
_LOCALT_CONTEXT: contextvars.ContextVar[Lang | None] = contextvars.ContextVar(
    "cortex_locale", default=None
)

__all__ = [
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
    "CacheStats",
    "Lang",
    "TranslationKey",
    "clear_cache",
    "get_cache_info",
    "get_supported_languages",
    "get_trans",
    "has_translation",
    "override_locale",
]


def _load_translations() -> LocaleData:
    """Lazy-load translations with thread-safe atomic reference swap."""
    global _TRANSLATIONS
    if _TRANSLATIONS:
        return _TRANSLATIONS

    with _LOAD_LOCK:
        # Double-check lock pattern
        if _TRANSLATIONS:
            return _TRANSLATIONS

        try:
            path = _ASSET_PATH.resolve()
            if not path.is_file():
                logger.error("I18N Sovereign Failure: Asset missing or invalid at %s", path)
                return {}

            raw_data = path.read_text(encoding="utf-8")
            data: LocaleData = json.loads(raw_data)

            # Atomic swap to ensure thread-safe readers
            _TRANSLATIONS = data
            logger.debug("I18N: Synchronized %d keys from assets", len(_TRANSLATIONS))
        except (json.JSONDecodeError, OSError) as exc:
            logger.critical("I18N: Fatal failure loading assets: %s", exc)
            return {}

    return _TRANSLATIONS


def get_supported_languages() -> frozenset[Lang]:
    """Return the set of languages officially supported by CORTEX."""
    return SUPPORTED_LANGUAGES


def _normalize_lang(lang: str | Lang | None) -> Lang:
    """Fast normalization of language codes with primary-tag fallback."""
    if isinstance(lang, Lang):
        return lang
    if not lang or not isinstance(lang, str):
        return DEFAULT_LANGUAGE

    # Exact match lookup
    code = lang.lower().strip()
    if match := _LANG_LOOKUP.get(code):
        return match

    # Primary tag extraction (e.g. "en-US" -> "en")
    primary = code.split("-", 1)[0][:2]
    return _LANG_LOOKUP.get(primary, DEFAULT_LANGUAGE)


@lru_cache(maxsize=4096)
def _cached_trans(key: TranslationKey, lang_code: Lang) -> str | None:
    """Atomic cached lookup with sovereign fallback hierarchy.

    Returns None if key is missing to distinguish from 'key as value'.
    """
    translations = _load_translations()
    entry = translations.get(key)

    if entry is None:
        return None

    # 1. Primary Language Lookup
    if (text := entry.get(lang_code.value)) is not None:
        return text

    # 2. Sovereign Fallback (to default language)
    if lang_code != DEFAULT_LANGUAGE:
        if (text := entry.get(DEFAULT_LANGUAGE.value)) is not None:
            logger.debug("I18N: Key [%s] falling back to [%s]", key, DEFAULT_LANGUAGE.value)
            return text

    return None


def get_trans(key: TranslationKey, lang: Lang | str | None = None, **kwargs: Any) -> str:
    """Retrieve localized string formatted with variables.

    O(1) lookup via LRU. Supports dynamic string interpolation.
    """
    # Use override if active, else fallback to passed lang or default English
    target_lang = lang or _LOCALT_CONTEXT.get() or Lang.EN
    normalized_lang = _normalize_lang(target_lang)
    text = _cached_trans(key, normalized_lang)

    # Fallback to key if no translation found
    if text is None:
        logger.warning("I18N: Missing translation for key [%s] in [%s]", key, normalized_lang)
        text = key

    if kwargs and text != key:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError, IndexError):
            logger.exception("I18N Formatting Error [%s] with data %s", key, kwargs)

    return text


def has_translation(key: str) -> bool:
    """Check if a specific key exists in the translation database."""
    translations = _load_translations()
    return key in translations


@contextmanager
def override_locale(lang: str | Lang) -> Generator[None, None, None]:
    """Context manager to scope the translation language for the current thread/task."""
    normalized = _normalize_lang(lang)
    token = _LOCALT_CONTEXT.set(normalized)
    try:
        yield
    finally:
        _LOCALT_CONTEXT.reset(token)


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
    global _TRANSLATIONS
    with _LOAD_LOCK:
        _cached_trans.cache_clear()
        _TRANSLATIONS = {}
