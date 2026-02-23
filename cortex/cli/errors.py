"""
CORTEX CLI — Sovereign Error Display System v2.0 (i18n-enabled).

Centralized, beautiful, consistent error messages across all CLI commands.
Every error includes: icon, message, cause, and recovery hint.
All messages are internationalized via cortex.i18n (en/es/eu).
"""

from __future__ import annotations

import sys
from typing import NoReturn

from rich.panel import Panel

# Re-use the shared CLI console so errors appear in the same stream
# as regular output (important for Click test runner capture).
from cortex.cli import console
from cortex.i18n import get_trans


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


# ─── Smart Error Handler ─────────────────────────────────────────────


def handle_cli_error(e: Exception, *, db_path: str = "", context: str = "") -> NoReturn:
    """Smart error router — classifies exceptions and shows the right message."""
    import sqlite3

    error_str = str(e)
    ctx_prefix = f" durante {context}" if context else ""

    # SQLite lock
    if isinstance(e, sqlite3.OperationalError) and "locked" in error_str.lower():
        err_db_locked(db_path, error_str)

    # SQLite corruption
    if isinstance(e, sqlite3.DatabaseError) and (
        "corrupt" in error_str.lower() or "malformed" in error_str.lower()
    ):
        err_db_corrupted(db_path, error_str)

    # File not found (DB or other)
    if isinstance(e, FileNotFoundError):
        if db_path and "cortex" in error_str.lower():
            err_db_not_found(db_path)
        err_unexpected(f"Archivo no encontrado{ctx_prefix}: {error_str}")

    # Permission errors
    if isinstance(e, PermissionError):
        err_permission_denied(context or "operación", error_str)

    # SQLite generic
    if isinstance(e, sqlite3.Error):
        err_unexpected(
            f"Error de base de datos{ctx_prefix}: {error_str}",
            hint="Prueba con `cortex init` o revisa la integridad con `cortex verify 1`.",
        )

    # OS errors
    if isinstance(e, OSError):
        err_unexpected(
            f"Error del sistema{ctx_prefix}: {error_str}",
            hint="Verifica permisos y espacio en disco.",
        )

    # Runtime generic
    if isinstance(e, (RuntimeError, ValueError)):
        err_unexpected(
            f"Error{ctx_prefix}: {error_str}",
            hint="Revisa los parámetros de entrada.",
        )

    # Catch-all
    err_unexpected(f"{type(e).__name__}{ctx_prefix}: {error_str}")
