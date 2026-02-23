"""
CORTEX CLI — Sovereign Error Display System v2.0 (i18n-enabled).

Centralized, beautiful, consistent error messages across all CLI commands.
Every error includes: icon, message, cause, and recovery hint.
All messages are internationalized via cortex.i18n (en/es/eu).
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, dataclass
from enum import Enum
from typing import NoReturn

from rich.panel import Panel

# Re-use the shared CLI console so errors appear in the same stream
# as regular output (important for Click test runner capture).
from cortex.cli import console
from cortex.i18n import get_trans

__all__ = [
    "err_db_corrupted",
    "err_db_locked",
    "err_db_not_found",
    "err_empty_results",
    "err_execution_failed",
    "err_fact_not_found",
    "err_network",
    "err_permission_denied",
    "err_platform",
    "err_platform_unsupported",
    "err_skill_not_found",
    "err_unexpected",
    "err_validation",
    "handle_cli_error",
    "ErrorCode",
    "CortexErrorStruct",
    "classify_error",
]

# ─── Data Structures ─────────────────────────────────────────────────


class ErrorCode(str, Enum):
    DB_NOT_FOUND = "ERR_DB_NOT_FOUND"
    DB_LOCKED = "ERR_DB_LOCKED"
    DB_CORRUPTED = "ERR_DB_CORRUPTED"
    FACT_NOT_FOUND = "ERR_FACT_NOT_FOUND"
    SKILL_NOT_FOUND = "ERR_SKILL_NOT_FOUND"
    EXECUTION_FAILED = "ERR_EXECUTION_FAILED"
    PLATFORM_UNSUPPORTED = "ERR_PLATFORM_UNSUPPORTED"
    EMPTY_RESULTS = "ERR_EMPTY_RESULTS"
    PERMISSION_DENIED = "ERR_PERMISSION_DENIED"
    NETWORK_ERROR = "ERR_NETWORK_ERROR"
    VALIDATION_ERROR = "ERR_VALIDATION_ERROR"
    UNEXPECTED = "ERR_UNEXPECTED"


@dataclass
class CortexErrorStruct:
    code: ErrorCode
    message: str
    detail: str = ""
    hint: str = ""
    http_status: int = 500


# ─── Helpers ─────────────────────────────────────────────────────────


def _lang() -> str | None:
    """Detect current language from environment or context."""
    import os

    return os.environ.get("CORTEX_LANG") or os.environ.get("LANG", "en")[:2] or None


def _t(key: str, **kwargs) -> str:
    """Shortcut for translated string with current locale."""
    return get_trans(key, lang=_lang(), **kwargs)


def _panel(body: str, *, title: str, border: str = "red") -> None:
    """Print a rich Panel with consistent styling."""
    console.print(Panel(body, title=title, border_style=border))


# ─── Error Categories ────────────────────────────────────────────────


def err_db_not_found(db_path: str) -> NoReturn:
    """Database file not found / not initialized."""
    _panel(
        _t("cli_err_db_not_found_body", path=db_path),
        title=f"🚫 CORTEX — {_t('cli_err_db_not_found_title')}",
    )
    sys.exit(1)


def err_db_locked(db_path: str, detail: str = "") -> NoReturn:
    """Database is locked (concurrent access)."""
    body = _t("cli_err_db_locked_body", path=db_path)
    if detail:
        body = f"{body}\n\n  [dim]{detail}[/dim]"
    _panel(body, title=f"🔒 CORTEX — {_t('cli_err_db_locked_title')}")
    sys.exit(1)


def err_db_corrupted(db_path: str, detail: str = "") -> NoReturn:
    """Database corruption detected."""
    body = _t("cli_err_db_corrupted_body", path=db_path)
    if detail:
        body = f"{body}\n\n  [dim]{detail}[/dim]"
    _panel(body, title=f"💥 CORTEX — {_t('cli_err_db_corrupted_title')}")
    sys.exit(1)


def err_fact_not_found(fact_id: int) -> None:
    """Fact with given ID not found or already deprecated."""
    _panel(
        _t("cli_err_fact_not_found_body", id=fact_id),
        title=f"🔍 CORTEX — {_t('cli_err_fact_not_found_title')}",
        border="yellow",
    )


def err_skill_not_found(skill_name: str, skill_path: str) -> NoReturn:
    """Skill script not found on disk."""
    _panel(
        _t("cli_err_skill_not_found_body", name=skill_name, path=skill_path),
        title=f"🔧 CORTEX — {_t('cli_err_skill_not_found_title')}",
    )
    sys.exit(1)


def err_execution_failed(command: str, detail: str = "") -> NoReturn:
    """External command or subprocess failed."""
    body = _t("cli_err_execution_failed_body", command=command)
    if detail:
        body = f"{body}\n\n  [dim]{detail}[/dim]"
    _panel(body, title=f"⚡ CORTEX — {_t('cli_err_execution_failed_title')}")
    sys.exit(1)


def err_platform_unsupported(feature: str, required_platform: str = "macOS") -> NoReturn:
    """Feature is not available on the current platform."""
    _panel(
        _t(
            "cli_err_platform_unsupported_body",
            feature=feature,
            platform=required_platform,
            current=sys.platform,
        ),
        title=f"🖥️ CORTEX — {_t('cli_err_platform_unsupported_title')}",
    )
    sys.exit(1)


def err_platform(detail: str) -> NoReturn:
    """Generic environmental/platform requirement failed."""
    err_unexpected(detail, hint="Verifica los requisitos del sistema o del repositorio Git.")


def err_empty_results(entity: str, suggestion: str = "") -> None:
    """No results found for a search/query operation."""
    body = _t("cli_err_empty_results_body", entity=entity)
    if suggestion:
        body = f"{body}\n\n[yellow]💡[/] {suggestion}"
    _panel(body, title="📭 Sin Resultados", border="dim")


def err_permission_denied(action: str, detail: str = "") -> NoReturn:
    """Permission error (file system, accessibility, etc.)."""
    body = _t("cli_err_permission_denied_body", action=action)
    if detail:
        body = f"{body}\n\n  [dim]{detail}[/dim]"
    _panel(body, title=f"🔐 CORTEX — {_t('cli_err_permission_denied_title')}")
    sys.exit(1)


def err_network(action: str, detail: str = "") -> None:
    """Network-related error (API calls, cloud sync, etc.)."""
    body = (
        f"[bold red]Error de red: {action}[/]"
        + (f"\n  [dim]{detail}[/dim]" if detail else "")
        + "\n\n  1. Verifica conexión a internet\n  2. Comprueba credenciales\n  3. Reintenta"
    )
    _panel(body, title="🌐 CORTEX — Network")


def err_validation(field: str, detail: str) -> None:
    """Input validation error."""
    _panel(
        f"[bold red]{_t('error_invalid_input')}[/]\n\n"
        f"  Campo: [cyan]{field}[/cyan]\n"
        f"  Problema: {detail}",
        title="⚠️ CORTEX — Validación",
        border="yellow",
    )


def err_unexpected(detail: str, hint: str = "") -> NoReturn:
    """Unexpected/unhandled error with recovery guidance."""
    body = _t("cli_err_unexpected_body", detail=detail)
    if hint:
        body = f"{body}\n\n[yellow]💡[/] {hint}"
    _panel(body, title=f"💀 CORTEX — {_t('cli_err_unexpected_title')}")
    sys.exit(1)


# ─── Smart Error Handler & Classifier ────────────────────────────────


def classify_error(e: Exception, *, db_path: str = "", context: str = "") -> CortexErrorStruct:
    """Classify a raw Python Exception into a guaranteed CortexError schema without side effects."""
    import sqlite3

    error_str = str(e)
    ctx_prefix = f" durante {context}" if context else ""

    # SQLite lock
    if isinstance(e, sqlite3.OperationalError) and "locked" in error_str.lower():
        return CortexErrorStruct(
            code=ErrorCode.DB_LOCKED,
            message=_t("cli_err_db_locked_title"),
            detail=error_str,
            http_status=409,  # Conflict
        )

    # SQLite corruption
    if isinstance(e, sqlite3.DatabaseError) and (
        "corrupt" in error_str.lower() or "malformed" in error_str.lower()
    ):
        return CortexErrorStruct(
            code=ErrorCode.DB_CORRUPTED,
            message=_t("cli_err_db_corrupted_title"),
            detail=error_str,
            http_status=500,
        )

    # File not found
    if isinstance(e, FileNotFoundError):
        if db_path and "cortex" in error_str.lower():
            return CortexErrorStruct(
                code=ErrorCode.DB_NOT_FOUND,
                message=_t("cli_err_db_not_found_title"),
                detail=error_str,
                http_status=404,
            )
        return CortexErrorStruct(
            code=ErrorCode.UNEXPECTED,
            message=f"Archivo no encontrado{ctx_prefix}",
            detail=error_str,
            http_status=404,
        )

    # Permission errors
    if isinstance(e, PermissionError):
        return CortexErrorStruct(
            code=ErrorCode.PERMISSION_DENIED,
            message=_t("cli_err_permission_denied_title"),
            detail=error_str,
            http_status=403,
        )

    # SQLite generic
    if isinstance(e, sqlite3.Error):
        return CortexErrorStruct(
            code=ErrorCode.UNEXPECTED,
            message=f"Error de base de datos{ctx_prefix}",
            detail=error_str,
            hint="Prueba con `cortex init` o revisa la integridad con `cortex verify 1`.",
            http_status=500,
        )

    # OS errors
    if isinstance(e, OSError):
        return CortexErrorStruct(
            code=ErrorCode.UNEXPECTED,
            message=f"Error del sistema{ctx_prefix}",
            detail=error_str,
            hint="Verifica permisos y espacio en disco.",
            http_status=500,
        )

    # Runtime generic
    if isinstance(e, RuntimeError | ValueError):
        return CortexErrorStruct(
            code=ErrorCode.VALIDATION_ERROR if isinstance(e, ValueError) else ErrorCode.UNEXPECTED,
            message=f"Error{ctx_prefix}",
            detail=error_str,
            hint="Revisa los parámetros de entrada.",
            http_status=400 if isinstance(e, ValueError) else 500,
        )

    # Catch-all
    return CortexErrorStruct(
        code=ErrorCode.UNEXPECTED,
        message=f"{type(e).__name__}{ctx_prefix}",
        detail=error_str,
        http_status=500,
    )


def handle_cli_error(e: Exception, *, db_path: str = "", context: str = "") -> NoReturn:
    """Smart error router — classifies exceptions and shows the right message or JSON output."""
    struct = classify_error(e, db_path=db_path, context=context)

    # If JSON output is requested (e.g., by SDKs or other tools via env var)
    if os.environ.get("CORTEX_JSON_OUTPUT") == "1":
        console.print(json.dumps({"status": "error", "error": asdict(struct)}))
        sys.exit(1)

    # Otherwise, fallback to the standard rich console display
    if struct.code == ErrorCode.DB_LOCKED:
        err_db_locked(db_path, struct.detail)
    elif struct.code == ErrorCode.DB_CORRUPTED:
        err_db_corrupted(db_path, struct.detail)
    elif struct.code == ErrorCode.DB_NOT_FOUND:
        err_db_not_found(db_path)
    elif struct.code == ErrorCode.PERMISSION_DENIED:
        err_permission_denied(context or "operación", struct.detail)
    else:
        err_unexpected(struct.detail or struct.message, struct.hint)
