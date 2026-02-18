"""
Tests for cortex.i18n module and API integration.
"""

import pytest

from cortex.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    TRANSLATIONS,
    get_supported_languages,
    get_trans,
)


class TestGetTrans:
    def test_english_default(self):
        assert get_trans("system_operational") == "operational"

    def test_spanish(self):
        assert get_trans("system_operational", "es") == "operativo"

    def test_basque(self):
        assert get_trans("system_operational", "eu") == "martxan"

    def test_unknown_language_falls_back_to_english(self):
        assert get_trans("system_operational", "fr") == "operational"

    def test_unknown_key_returns_key(self):
        assert get_trans("nonexistent_key", "en") == "nonexistent_key"

    def test_locale_code_normalization(self):
        """'es-ES' should normalize to 'es'."""
        assert get_trans("system_operational", "es-ES") == "operativo"
        assert get_trans("system_healthy", "eu-BASQUE") == "osasuntsu"

    def test_case_insensitive_lang(self):
        assert get_trans("engine_online", "ES") == "en línea"

    def test_all_error_keys_exist(self):
        """Every error key must have all 3 languages."""
        error_keys = [k for k in TRANSLATIONS if k.startswith("error_")]
        assert len(error_keys) >= 4, f"Expected >=4 error keys, got {error_keys}"
        for key in error_keys:
            entry = TRANSLATIONS[key]
            for lang in ("en", "es", "eu"):
                assert lang in entry, f"Missing '{lang}' translation for '{key}'"
                assert entry[lang], f"Empty '{lang}' translation for '{key}'"

    def test_all_keys_have_english(self):
        """English is the fallback — every key MUST have it."""
        for key, langs in TRANSLATIONS.items():
            assert "en" in langs, f"Key '{key}' missing English translation"

    def test_default_language_is_english(self):
        assert DEFAULT_LANGUAGE == "en"

    def test_supported_languages_contains_all_three(self):
        assert SUPPORTED_LANGUAGES == frozenset({"en", "es", "eu"})

    def test_get_supported_languages_returns_frozenset(self):
        result = get_supported_languages()
        assert isinstance(result, frozenset)
        assert "en" in result and "es" in result and "eu" in result

    def test_all_keys_cover_all_supported_languages(self):
        """Every translation key should have all supported languages."""
        for key, entry in TRANSLATIONS.items():
            for lang in SUPPORTED_LANGUAGES:
                assert lang in entry, f"Key '{key}' missing '{lang}' translation"
