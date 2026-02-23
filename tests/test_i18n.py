"""
Tests for cortex.i18n module and API integration.
"""


from cortex import i18n
from cortex.i18n import (
    DEFAULT_LANGUAGE,
    SUPPORTED_LANGUAGES,
    Lang,
    _load_translations,
    get_cache_info,
    get_supported_languages,
    get_trans,
    has_translation,
    override_locale,
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
        _load_translations()
        error_keys = [k for k in i18n._TRANSLATIONS if k.startswith("error_")]
        assert len(error_keys) >= 4, f"Expected >=4 error keys, got {error_keys}"
        for key in error_keys:
            entry = i18n._TRANSLATIONS[key]
            for lang in ("en", "es", "eu"):
                assert lang in entry, f"Missing '{lang}' translation for '{key}'"
                assert entry[lang], f"Empty '{lang}' translation for '{key}'"

    def test_all_keys_have_english(self):
        """English is the fallback — every key MUST have it."""
        for key, langs in i18n._TRANSLATIONS.items():
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
        for key, entry in i18n._TRANSLATIONS.items():
            for lang in SUPPORTED_LANGUAGES:
                assert lang in entry, f"Key '{key}' missing '{lang}' translation"

    # --- Wave 3: Edge Cases ---

    def test_none_lang_falls_back_to_english(self):
        """None language should fall back to English."""
        assert get_trans("system_operational", None) == "operational"

    def test_empty_string_lang_falls_back(self):
        """Empty string language should fall back to English."""
        assert get_trans("system_operational", "") == "operational"

    def test_lang_enum_direct(self):
        """Passing Lang enum directly should work."""
        assert get_trans("system_operational", Lang.ES) == "operativo"
        assert get_trans("system_operational", Lang.EU) == "martxan"
        assert get_trans("system_operational", Lang.EN) == "operational"

    def test_format_string_keys_return_template(self):
        """Keys containing {placeholders} should return the raw template."""
        result_en = get_trans("error_missing_permission", "en")
        assert "{permission}" in result_en

        result_es = get_trans("error_fact_not_found", "es")
        assert "{id}" in result_es

        result_eu = get_trans("error_integrity_check_failed", "eu")
        assert "{detail}" in result_eu

    def test_cache_info_available(self):
        """Cache info should be accessible for observability."""
        # Warm the cache with one call
        get_trans("system_operational", "en")
        info = get_cache_info()
        assert info.hits >= 0
        assert info.misses >= 0
        assert info.maxsize == 4096

    def test_override_locale(self):
        """Context manager should correctly scope the language."""
        # Warm cache for base lang
        assert get_trans("system_operational") == "operational"

        with override_locale("es"):
            assert get_trans("system_operational") == "operativo"
            # Explicit call still overrides context
            assert get_trans("system_operational", "eu") == "martxan"

        # Should restore to default
        assert get_trans("system_operational") == "operational"

    def test_has_translation(self):
        """Should correctly detect key existence."""
        assert has_translation("system_operational") is True
        assert has_translation("this_is_fake_news_123") is False

    def test_formatting_with_kwargs(self):
        """Verify dynamic string interpolation."""
        result = get_trans("error_missing_permission", "en", permission="WRITE")
        assert result == "Missing permission: WRITE"

        # Spanish
        result_es = get_trans("error_fact_not_found", "es", id="404")
        assert result_es == "No se encontró el hecho #404"
