"""
CORTEX CLI — Package init (Ω₂ Lazy Loading).

Strategy:
  - Modules using @cli.command() self-register on import → lazy-imported.
  - Modules using @click.group() need explicit add_command → LazyCommand proxy.

CLI boot: ~50ms (was 637ms).
"""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, Optional, Union

import click

from cortex import __version__  # noqa: F401
from cortex.cli.common import (
    DEFAULT_DB,
    cli,
    close_engine_sync,
    console,
    cortex_theme,
    get_engine,
    get_tracker,
)

if TYPE_CHECKING:
    from cortex.config import DEFAULT_DB_PATH
    from cortex.engine import CortexEngine
    from cortex.timing import TimingTracker

__all__ = [
    "cli",
    "console",
    "cortex_theme",
    "DEFAULT_DB",
    "get_engine",
    "get_tracker",
    "close_engine_sync",
]

# ─── Lazy Command Proxy ─────────────────────────────────────────────────


class _LazyCommand(click.BaseCommand):
    """Proxy that defers module import until the command is invoked.

    For --help listing, we return the help_text without importing.
    """

    def __init__(self, name: str, module_path: str, attr_name: str, help_text: str = ""):
        super().__init__(name)
        self._module_path = module_path
        self._attr_name = attr_name
        self._help_text = help_text
        self._resolved: click.BaseCommand | None = None

    def _resolve(self) -> click.BaseCommand:
        if self._resolved is None:
            mod = importlib.import_module(self._module_path)
            self._resolved = getattr(mod, self._attr_name)
        return self._resolved

    def get_short_help_str(self, limit: int = 150) -> str:
        # Return static help to avoid importing the module for --help listing
        return self._help_text[:limit] if self._help_text else ""

    def get_help(self, ctx: click.Context) -> str:
        return self._resolve().get_help(ctx)

    def get_params(self, ctx: click.Context) -> list:
        return self._resolve().get_params(ctx)

    def parse_args(self, ctx: click.Context, args: list[str]) -> list[str]:
        return self._resolve().parse_args(ctx, args)

    def invoke(self, ctx: click.Context) -> object:
        return self._resolve().invoke(ctx)

    def make_context(
        self,
        info_name: str | None,
        args: list[str],
        parent: click.Context | None = None,
        **extra,
    ) -> click.Context:
        return self._resolve().make_context(info_name, args, parent=parent, **extra)

    def get_usage(self, ctx: click.Context) -> str:
        return self._resolve().get_usage(ctx)

    def format_help(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        return self._resolve().format_help(ctx, formatter)

    def format_usage(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        return self._resolve().format_usage(ctx, formatter)


class _LazyGroup(_LazyCommand, click.MultiCommand):
    """Proxy for lazy-loaded Click groups (subcommand resolution)."""

    def list_commands(self, ctx: click.Context) -> list[str]:
        resolved = self._resolve()
        if isinstance(resolved, click.MultiCommand):
            return resolved.list_commands(ctx)
        return []

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        resolved = self._resolve()
        if isinstance(resolved, click.MultiCommand):
            return resolved.get_command(ctx, cmd_name)
        return None


# ─── Self-registering modules (@cli.command / @cli.group) ───────────────
# These modules use @cli.command() decorator, so importing them attaches
# their commands to the `cli` group automatically.
# We defer their import until the CLI actually needs them.

_SELF_REGISTERING_MODULES: list[str] = [
    "cortex.cli.compact_cmds",
    "cortex.cli.crud",
    "cortex.cli.dashboard_cmds",
    "cortex.cli.demiurge_cmds",
    "cortex.cli.entropy_cmds",
    "cortex.cli.eval_cmds",
    "cortex.cli.handoff_cmds",
    "cortex.cli.init_cmds",
    "cortex.cli.launchpad_cmds",
    "cortex.cli.lineage_cmds",
    "cortex.cli.loop_cmds",
    "cortex.cli.mejoralo_cmds",
    "cortex.cli.memory_cmds",
    "cortex.cli.prompt_cmds",
    "cortex.cli.purge",
    "cortex.cli.reflect_cmds",
    "cortex.cli.security_hardening_cmds",
    "cortex.cli.session_cmds",
    "cortex.cli.signal_cmds",
    "cortex.cli.spawn_cmds",
    "cortex.cli.status_cmds",
    "cortex.cli.storage_cmds",
    "cortex.cli.swarm_cmds",
    "cortex.cli.sync_cmds",
    "cortex.cli.time_cmds",
    "cortex.cli.timeline_cmds",
    "cortex.cli.tips_cmds",
    "cortex.cli.trust_cmds",
    "cortex.cli.vote_ledger",
]

# ─── Standalone groups (@click.group) — need LazyGroup proxy ────────────
# Format: (cli_name, module_path, attr_name, short_help)

_LAZY_GROUPS: list[tuple[str, str, str, str]] = [
    ("agent", "cortex.cli.agent_cmds", "agent_cmds", "Agent management commands."),
    ("apotheosis", "cortex.cli.apotheosis_cmds", "apotheosis_cmds", "Apotheosis autonomy engine."),
    ("autorouter", "cortex.cli.autorouter_cmds", "autorouter_cmds", "AI model router daemon."),
    (
        "bibliotecario",
        "cortex.cli.bibliotecario_cmds",
        "bibliotecario_cmds",
        "Knowledge librarian.",
    ),
    ("browser", "cortex.cli.browser_cmds", "browser", "Browser automation commands."),
    ("chronos", "cortex.cli.chronos_cmds", "chronos_cmds", "Time asymmetry benchmarks."),
    ("context", "cortex.cli.context_cmds", "context", "Context management."),
    ("episode", "cortex.cli.episodic_cmds", "episode", "Episodic memory commands."),
    ("ghost", "cortex.cli.ghost_cmds", "ghost_cmds", "Ghost architecture control."),
    ("keter", "cortex.cli.keter_cmds", "keter_cmds", "KETER-∞ sovereign orchestration."),
    ("ledger-w5", "cortex.cli.ledger", "ledger_cmds_click", "Immutable Ledger (Wave 5)."),
    ("moltbook", "cortex.cli.moltbook_cmds", "moltbook_cmds", "Moltbook forum integration."),
    ("nexus", "cortex.cli.nexus_cmds", "nexus_cmds", "Cross-project nexus sync."),
    ("notebooklm", "cortex.cli.notebooklm_cmds", "notebooklm_cmds", "NotebookLM integration."),
    ("policy", "cortex.cli.policy_cmds", "policy_cmds", "Policy engine commands."),
    ("quota", "cortex.cli.quota_cmds", "quota_cli", "Resource quota management."),
    ("radar", "cortex.cli.radar_cmds", "radar_cmds", "📡 RADAR-Ω: Sovereign monitoring."),
    ("roi", "cortex.cli.roi_cmds", "roi", "ROI metrics dashboard."),
    ("security", "cortex.cli.security_cmds", "security_cli", "Security audit commands."),
    ("sovereign", "cortex.cli.keter_cmds", "sovereign_cmds", "Sovereign engine control."),
    ("mcp", "cortex.cli.mcp_cmds", "mcp_cmds", "Model Context Protocol tools."),
    ("josu", "cortex.cli.commands.josu_start", "app", "Manage the JOSU proactive daemon."),
    ("genesis", "cortex.cli.genesis_cmds", "genesis_group", "Genesis Engine — create systems."),
    ("health", "cortex.cli.health_cmds", "health_group", "Health Index — system monitoring."),
    ("routing", "cortex.cli.routing_cmds", "routing", "LLM routing — tier/cost-aware selection."),
    ("maestro", "cortex.cli.maestro_cmds", "maestro", "Autonomous Mac automation agent."),
    (
        "grammy",
        "cortex.cli.grammy_cmds",
        "grammy_cmds",
        "🎵 GRAMMY-Ω: Producción de música soberana.",
    ),
    (
        "fingerprint",
        "cortex.cli.fingerprint_cmds",
        "fingerprint",
        "🧬 Cognitive Fingerprint — extract decision patterns.",
    ),
]

# ─── Lazy standalone commands ────────────────────────────────────────────
_LAZY_STANDALONE: list[tuple[str, str, str, str]] = [
    ("heal", "cortex.cli.heal_cmds", "cli", "AI-powered code healing."),
    ("triangulate", "cortex.cli.triangulation_cmds", "triangulate", "Epistemic triangulation."),
]

# ─── Patched list_commands / get_command on cli ──────────────────────────
# Override the cli group to lazy-import self-registering modules on demand.

_original_list_commands = cli.list_commands
_original_get_command = cli.get_command
_modules_loaded = False


def _ensure_self_registering_loaded() -> None:
    """Import all self-registering modules (only done once, on first need)."""
    global _modules_loaded
    if _modules_loaded:
        return
    _modules_loaded = True
    for mod_path in _SELF_REGISTERING_MODULES:
        try:
            importlib.import_module(mod_path)
        except ImportError:
            pass  # Non-critical: skip broken modules


def _patched_list_commands(ctx: click.Context) -> list[str]:
    """List all commands, loading self-registering modules on demand."""
    _ensure_self_registering_loaded()
    return _original_list_commands(ctx)


def _patched_get_command(ctx: click.Context, cmd_name: str) -> click.Command | None:
    """Get a command, loading self-registering modules if not found."""
    # First try without loading (catches lazy groups + already loaded commands)
    cmd = _original_get_command(ctx, cmd_name)
    if cmd is not None:
        return cmd

    # If not found, load all self-registering modules and try again
    _ensure_self_registering_loaded()
    return _original_get_command(ctx, cmd_name)


cli.list_commands = _patched_list_commands  # type: ignore[assignment]
cli.get_command = _patched_get_command  # type: ignore[assignment]


# ─── Register lazy groups ────────────────────────────────────────────────
for _name, _mod, _attr, _help in _LAZY_GROUPS:
    cli.add_command(_LazyGroup(_name, _mod, _attr, _help), name=_name)

for _name, _mod, _attr, _help in _LAZY_STANDALONE:
    cli.add_command(_LazyCommand(_name, _mod, _attr, _help), name=_name)


# ─── Observe (inline, no module overhead) ────────────────────────────────
@cli.command("observe")
@click.option("--workspace", "-w", default=".", help="Workspace path to observe")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def observe_cmd(workspace: str, db: str) -> None:
    """Start real-time perception observer."""
    from cortex.cli.episodic_observe import run_observe

    run_observe(workspace, db, console)


if __name__ == "__main__":
    cli()
