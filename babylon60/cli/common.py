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
from babylon60.config import DEFAULT_DB_PATH

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
    import os
    import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
    import sys
    import tempfile

    # Rule 14 CLI Sandbox Isolation: redirect default DB path during tests/demos
    is_pytest = "PYTEST_CURRENT_TEST" in os.environ or "pytest" in sys.modules
    is_demo = os.environ.get("CORTEX_CLI_DEMO") == "1"

    if db == DEFAULT_DB and (is_pytest or is_demo):
        # Determine /tmp/ path (standardized across platforms using tempfile)
        db = os.path.join(tempfile.gettempdir(), "cortex_test_sandbox.db")
        # Pre-initialize with WAL and busy_timeout=5000 via factory connection
        try:
            from babylon60.database.core import connect as db_connect
            conn = db_connect(db)
            conn.close()
        except sqlite3.OperationalError as e:
            import logging
            logging.warning("Sandbox DB pre-initialization warning: %s", e)

    try:
        from babylon60.engine import CortexEngine

        return CortexEngine(db_path=db)
    except Exception as err:
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
    except Exception as exc:
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

    explicit = os.environ.get("CORTEX_SOURCE")
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


@click.group()
@click.version_option(__version__, prog_name="cortex")
def cli() -> None:
    """CORTEX - Trust Infrastructure for Autonomous AI."""
