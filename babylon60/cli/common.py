# [C5-REAL] Exergy-Maximized
"""CORTEX CLI - Common shared objects and utilities.

Prevent circular imports by centralizing base CLI objects.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

if TYPE_CHECKING:
    from babylon60.engine import CortexEngine
    from babylon60.extensions.timing import TimingTracker

from babylon60 import __version__
from babylon60.core.paths import CORTEX_DB as DEFAULT_DB_PATH

# Theme and Console
cortex_theme = Theme(
    {
        "info": "dim cyan",
        "warning": "magenta",
        "danger": "bold red",
        "success": "bold green",
        "noir.bg": "on #0A0A0A",
        "noir.abyssal": "#1A1A1A",
        "noir.cyber": "bold #CCFF00",
        "noir.gold": "bold #D4AF37",
        "noir.violet": "bold #6600FF",
        "noir.yinmn": "bold #2E5090",
    }
)

console = Console(theme=cortex_theme)
DEFAULT_DB = str(DEFAULT_DB_PATH)
GLOBAL_CLI_TIMEOUT: float = 120.0  # Chronos Sniper: No CLI command hangs indefinitely


def get_engine(db: str = DEFAULT_DB) -> CortexEngine:
    """Create an engine instance (lazy import)."""
    try:
        from babylon60.engine import CortexEngine

        return CortexEngine(db_path=db)
    except Exception as err:  # noqa: BLE001
        detail = f"{type(err).__name__}: {err}"
        filename = getattr(err, "filename", None)
        if filename:
            detail = f"{detail} [{filename}]"
        raise click.ClickException(
            "CORTEX engine could not start. "
            "The repo still has unresolved import/syntax issues in core modules. "
            f"Root cause: {detail}. "
            "Use `python scripts/repo_health_changed.py --all` or fix the reported module first."
        ) from err


def get_tracker(engine: CortexEngine) -> TimingTracker:
    """Create a timing tracker from an engine (lazy import)."""
    from babylon60.extensions.timing import TimingTracker

    return TimingTracker(engine._get_conn())  # type: ignore[reportArgumentType]


def close_engine_sync(engine: CortexEngine) -> None:
    """Close the engine synchronously."""
    from babylon60.events.loop import sovereign_run

    sovereign_run(engine.close())


def _run_async(coro):
    """Helper to run async coroutines from sync CLI (sovereign uvloop)."""
    from babylon60.events.loop import sovereign_run

    # Chronos Sniper: Apply strict timeout to CLI commands to prevent deadlocks
    return sovereign_run(asyncio.wait_for(coro, timeout=GLOBAL_CLI_TIMEOUT))


def _show_tip(engine=None) -> None:
    """Show a random contextual tip after CLI operations."""
    try:
        from babylon60.cli.tips_cmds import TipsEngine

        tips_engine = TipsEngine(engine, include_dynamic=engine is not None, lang="es")

        async def __get_tip():
            return await tips_engine.random()

        tip = _run_async(__get_tip())
        console.print()
        console.print(
            Panel(
                f"[white]{tip.content}[/white]",
                title=f"[bold cyan]💡 {tip.category.value.upper()}[/bold cyan]",
                subtitle=f"[dim]{tip.source}[/dim]",
                border_style="bright_green",
                padding=(0, 2),
            )
        )
    except Exception as exc:  # noqa: BLE001
        import logging

        logging.warning("Suppressed exception: %s", exc)


# Tips are non-critical


def _get_tip_text(engine=None) -> str:
    """Get a short tip string for inline display."""
    try:
        from babylon60.cli.tips_cmds import TipsEngine

        tips_engine = TipsEngine(engine, include_dynamic=False, lang="es")

        async def __get_tip():
            return await tips_engine.random()

        tip = _run_async(__get_tip())
        return f"[dim bright_green]💡 {tip.content}[/]"
    except (ImportError, RuntimeError, OSError, ValueError):
        return ""


def _detect_agent_source() -> str:
    """Auto-detect the AI agent calling CORTEX from environment."""
    import os

    explicit = os.environ.get("MOSKV_SOURCE", os.environ.get("CORTEX_SOURCE"))
    if explicit:
        return explicit
    markers = [
        ("GEMINI_AGENT", "agent:gemini"),
        ("ANTIGRAVITY_SESSION_ID", "agent:antigravity"),
        ("CURSOR_SESSION_ID", "agent:cursor"),
        ("CLAUDE_CODE_AGENT", "agent:claude-code"),
        ("WINDSURF_SESSION", "agent:windsurf"),
        ("COPILOT_AGENT", "agent:copilot"),
        ("KIMI_SESSION_ID", "agent:kimi"),
    ]
    for env_var, source_name in markers:
        if os.environ.get(env_var):
            return source_name
    term = os.environ.get("TERM_PROGRAM", "")
    if "cursor" in term.lower():
        return "agent:cursor"
    if "vscode" in term.lower():
        return "ide:vscode"
    return "cli"


def resolve_cli_tenant(tenant_id: str) -> str:
    """Resolve the active tenant for CLI commands and set tenant_id_var context."""
    import json
    import os
    from pathlib import Path

    from babylon60.extensions.security.tenant import tenant_id_var

    if tenant_id == "default":
        # 1. Environment variable
        env_tenant = os.environ.get("CORTEX_TENANT_ID")
        if env_tenant:
            tenant_id = env_tenant
        else:
            # 2. Config file
            config_path = Path.home() / "10_PROJECTS/cortex-meta/active-context.json"
            if config_path.is_file():
                try:
                    data = json.loads(config_path.read_text(encoding="utf-8"))
                    tenant_id = data.get("tenant_id") or data.get("active_tenant") or "default"
                except Exception:  # noqa: BLE001
                    tenant_id = "default"

    # Set context variable for deep RLS verification in engine mixins
    tenant_id_var.set(tenant_id)
    return tenant_id


@click.group()
@click.version_option(__version__, prog_name="cortex")
def cli() -> None:
    """CORTEX - Trust Infrastructure for Autonomous AI."""
