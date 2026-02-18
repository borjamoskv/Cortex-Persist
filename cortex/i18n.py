"""
CORTEX v4.0 — Internationalization Module (i18n).

Provides multilingual support for the API layer.
Default: English (en)
Supported: Spanish (es), Basque (eu)
"""


# Dictionary of translations
# Structure: { key: { lang: translation } }
TRANSLATIONS: dict[str, dict[str, str]] = {
    # System Status
    "system_operational": {
        "en": "operational",
        "es": "operativo",
        "eu": "martxan",
    },
    "system_healthy": {
        "en": "healthy",
        "es": "saludable",
        "eu": "osasuntsu",
    },
    "engine_online": {
        "en": "online",
        "es": "en línea",
        "eu": "konektatuta",
    },

    # Errors
    "error_too_many_requests": {
        "en": "Too Many Requests. Please slow down.",
        "es": "Demasiadas solicitudes. Por favor, reduce la velocidad.",
        "eu": "Eskaera gehiegi. Mesedez, moteldu.",
    },
    "error_internal_db": {
        "en": "Internal database error",
        "es": "Error interno de base de datos",
        "eu": "Datu-basearen barne errorea",
    },
    "error_unexpected": {
        "en": "An unexpected server error occurred.",
        "es": "Ha ocurrido un error inesperado del servidor.",
        "eu": "Zerbitzariaren ezusteko errorea gertatu da.",
    },
    "error_unauthorized": {
        "en": "Unauthorized access",
        "es": "Acceso no autorizado",
        "eu": "Baimenik gabeko sarbidea",
    },

    # Greetings / Info
    "info_service_desc": {
        "en": "Local-first memory infrastructure for AI agents.",
        "es": "Infraestructura de memoria local-first para agentes de IA.",
        "eu": "IA agenteentzako tokiko memoria azpiegitura.",
    },
}


def get_trans(key: str, lang: str = "en") -> str:
    """Retrieve a translation for a given key and language.
    
    Falls back to English if the language or key is missing.
    """
    # Normalize lang code (e.g. 'es-ES' -> 'es')
    lang_code = lang.split("-")[0].lower()

    entry = TRANSLATIONS.get(key)
    if not entry:
        return key  # Return key if not found

    return entry.get(lang_code, entry.get("en", key))
