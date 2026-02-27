"""CORTEX CLI — Common shared objects and utilities.

Prevent circular imports by centralizing base CLI objects.
"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.theme import Theme

from cortex import __version__
from cortex.config import DEFAULT_DB_PATH
from cortex.engine import CortexEngine
from cortex.timing import TimingTracker

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


def get_engine(db: str = DEFAULT_DB) -> CortexEngine:
    """Create an engine instance."""
    return CortexEngine(db_path=db)


def get_tracker(engine: CortexEngine) -> TimingTracker:
    """Create a timing tracker from an engine."""
    return TimingTracker(engine._get_conn())


def close_engine_sync(engine: CortexEngine) -> None:
    """Close the engine synchronously."""
    from cortex.events.loop import sovereign_run

    sovereign_run(engine.close())


def _run_async(coro):
    """Helper to run async coroutines from sync CLI (sovereign uvloop)."""
    from cortex.events.loop import sovereign_run

    return sovereign_run(coro)


def _show_tip(engine=None) -> None:
    """Show a random contextual tip after CLI operations."""
    try:
        from cortex.cli.tips_cmds import TipsEngine

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
    except (ImportError, RuntimeError, OSError, ValueError):
        pass  # Tips are non-critical


def _get_tip_text(engine=None) -> str:
    """Get a short tip string for inline display."""
    try:
        from cortex.cli.tips_cmds import TipsEngine

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
    """CORTEX — Trust Infrastructure for Autonomous AI."""
    pass
