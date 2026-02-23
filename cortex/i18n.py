"""
CORTEX v5.0 — Internationalization Module (i18n).

Sovereign-grade multilingual support for the CORTEX ecosystem.
Optimized for low-latency lookups (LRU) and modular asset management.

Default: English (en)
Supported: Spanish (es), Basque (eu)
"""

from __future__ import annotations

import json
import logging
import os
from enum import Enum
from functools import lru_cache
from typing import TYPE_CHECKING, Any, Final, Optional, Union

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "Lang",
    "TranslationKey",
    "get_trans",
    "get_cache_info",
    "clear_cache",
    "get_supported_languages",
    "DEFAULT_LANGUAGE",
    "SUPPORTED_LANGUAGES",
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
_ASSET_PATH: Final[str] = os.path.join(
    os.path.dirname(__file__), "assets", "translations.json"
)

# Shared memory for translations
_TRANSLATIONS: dict[str, dict[str, str]] = {}


def _load_translations() -> dict[str, dict[str, str]]:
    """Lazy-load translations from disk with atomic assignment."""
    global _TRANSLATIONS
    if not _TRANSLATIONS:
        try:
            if not os.path.exists(_ASSET_PATH):
                logger.error("Sovereign Failure: Translation asset missing at %s", _ASSET_PATH)
                return {}
            
            with open(_ASSET_PATH, encoding="utf-8") as f:
                data = json.load(f)
                _TRANSLATIONS.clear()
                _TRANSLATIONS.update(data)
                logger.debug("I18N: Loaded %d keys from assets", len(_TRANSLATIONS))
        except (json.JSONDecodeError, OSError) as exc:
            logger.critical("I18N: Failed to load translations: %s", exc)
            return {}
    return _TRANSLATIONS


def get_supported_languages() -> frozenset[Lang]:
    """Returns the set of languages officially supported by CORTEX."""
    return SUPPORTED_LANGUAGES


# Type definition for lookup keys
TranslationKey = str


def _normalize_lang(lang: Optional[Union[str, Lang]]) -> Lang:
    """Fast normalization of language codes with strict fallback."""
    if isinstance(lang, Lang):
        return lang
    if not lang or not isinstance(lang, str):
        return DEFAULT_LANGUAGE

    # Handle RFC 5646 (e.g. "en-US" -> "en")
    code = lang.split("-", 1)[0].strip().lower()[:2]
    return _LANG_LOOKUP.get(code, DEFAULT_LANGUAGE)


@lru_cache(maxsize=2048)
def _cached_trans(key: TranslationKey, lang_code: Lang) -> str:
    """Atomic cached lookup for translated strings with sovereign fallbacks."""
    translations = _load_translations()
    entry = translations.get(key)
    
    if entry is None:
        logger.warning("I18N: Absolute Missing Key [%s] — No entry found in assets.", key)
        return key

    # Direct lookup with fallback to default language
    text = entry.get(lang_code.value)
    if text is None:
        if lang_code != DEFAULT_LANGUAGE:
            logger.debug("I18N: Falling back to [%s] for key [%s]", DEFAULT_LANGUAGE.value, key)
        
        text = entry.get(DEFAULT_LANGUAGE.value)
        if text is None:
            logger.error("I18N: Fatal Missing Key [%s] — Not found even in default language.", key)
            return key
    
    return text


def get_trans(key: TranslationKey, lang: Optional[Union[Lang, str]] = Lang.EN, **kwargs: Any) -> str:
    """
    Retrieve a translated string with optional formatting.

    Args:
        key: The lookup key in translations.json.
        lang: Desired language (enum or string). Defaults to English.
        **kwargs: Variables for template substitution (e.g. {id}).

    Returns:
        The localized and formatted string.
    """
    text = _cached_trans(key, _normalize_lang(lang))
    
    if kwargs and text != key:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError) as exc:
            logger.error("I18N Formatting Error [%s]: %s", key, exc)
    
    return text


def get_cache_info() -> Any:
    """Sovereign observability for translation engine performance."""
    return _cached_trans.cache_info()


def clear_cache() -> None:
    """Hard-reset the translation caches."""
    _cached_trans.cache_clear()
    global _TRANSLATIONS
    _TRANSLATIONS = {}
