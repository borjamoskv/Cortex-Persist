"""
CORTEX v4.0 — Internationalization Module (i18n).

Provides multilingual support for the API layer.
Default: English (en)
Supported: Spanish (es), Basque (eu)
"""


# Defaults and supported languages
DEFAULT_LANGUAGE = "en"
SUPPORTED_LANGUAGES = frozenset({"en", "es", "eu"})


def get_supported_languages() -> frozenset[str]:
    """Returns the set of languages officially supported by CORTEX."""
    return SUPPORTED_LANGUAGES


# Dictionary of translations
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
    "error_not_found": {
        "en": "Resource not found",
        "es": "Recurso no encontrado",
        "eu": "Baliabidea ez da aurkitu",
    },
    "error_invalid_input": {
        "en": "Invalid input provided",
        "es": "Entrada no válida",
        "eu": "Sarrera baliogabea",
    },

    # Greetings / Info
    "info_service_desc": {
        "en": "Local-first memory infrastructure for AI agents.",
        "es": "Infraestructura de memoria local-first para agentes de IA.",
        "eu": "IA agenteentzako tokiko memoria azpiegitura.",
    },

    # Auth Errors
    "error_missing_auth": {
        "en": "Missing Authorization header",
        "es": "Falta la cabecera de autorización",
        "eu": "Baimen goiburua falta da",
    },
    "error_invalid_key_format": {
        "en": "Invalid key format. Use: Bearer <api-key>",
        "es": "Formato de clave no válido. Usa: Bearer <api-key>",
        "eu": "Gako formatu baliogabea. Erabili: Bearer <api-key>",
    },
    "error_invalid_revoked_key": {
        "en": "Invalid or revoked key",
        "es": "Clave no válida o revocada",
        "eu": "Gako baliogabea edo ezeztatua",
    },
    "error_missing_permission": {
        "en": "Missing permission: {permission}",
        "es": "Falta permiso: {permission}",
        "eu": "Baimen hau falta da: {permission}",
    },

    # Fact Errors
    "error_fact_not_found": {
        "en": "Fact #{id} not found",
        "es": "No se encontró el hecho #{id}",
        "eu": "Ez da aurkitu #{id} gertaera",
    },
    "error_namespace_mismatch": {
        "en": "Forbidden: Namespace mismatch",
        "es": "Prohibido: Conflicto de espacio de nombres",
        "eu": "Debekatua: Izen-espazio gatazka",
    },
    "error_forbidden": {
        "en": "Forbidden",
        "es": "Prohibido",
        "eu": "Debekatua",
    },

    # Admin / Path Validation
    "error_json_only": {
        "en": "Only JSON format supported via API",
        "es": "Solo se admite el formato JSON mediante la API",
        "eu": "JSON formatua bakarrik onartzen da API bidez",
    },
    "error_invalid_path_chars": {
        "en": "Invalid characters in path",
        "es": "Caracteres no válidos en la ruta",
        "eu": "Baliogabeko karaktereak bidean",
    },
    "error_path_workspace": {
        "en": "Path must be relative and within the workspace",
        "es": "La ruta debe ser relativa y dentro del espacio de trabajo",
        "eu": "Bideak erlatiboa izan behar du eta lan-eremuaren barruan",
    },
    "error_export_failed": {
        "en": "Export failed",
        "es": "Exportación fallida",
        "eu": "Esportazioak huts egin du",
    },
    "error_status_unavailable": {
        "en": "Status unavailable",
        "es": "Estado no disponible",
        "eu": "Egoera ez dago erabilgarri",
    },
    "error_auth_required": {
        "en": "Auth required",
        "es": "Se requiere autenticación",
        "eu": "Autentifikazioa beharrezkoa da",
    },
    # Daemon
    "error_daemon_no_data": {
        "en": "No data collected by daemons in last hour",
        "es": "No hay datos recogidos por los demonios en la última hora",
        "eu": "Deabruek ez dute daturik bildu azken orduan",
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
