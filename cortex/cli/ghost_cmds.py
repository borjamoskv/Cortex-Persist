import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.errors import err_execution_failed, err_skill_not_found

__all__ = [
    "GHOST_SKILL_PATH",
    "actions",
    "eyes",
    "ghost_cmds",
    "hand",
    "handle_ghost_response",
    "process",
    "run_ghost_skill",
    "status",
    "system",
    "window",
]

console = Console()

GHOST_SKILL_PATH = Path.home() / ".gemini" / "antigravity" / "skills" / "ghost-control" / "ghost.py"


def run_ghost_skill(args: list[str]) -> tuple[int, str, str]:
    """Execute the ghost-control skill script and return code, stdout, stderr."""
    if not GHOST_SKILL_PATH.exists():
        err_skill_not_found("GHOST-1", str(GHOST_SKILL_PATH))

    cmd = ["python3", str(GHOST_SKILL_PATH)] + args

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout, result.stderr
    except (sqlite3.Error, OSError, RuntimeError) as e:
        err_execution_failed(" ".join(cmd), str(e))


def handle_ghost_response(returncode: int, stdout: str, stderr: str, title: str):
    """Handle the response from GHOST-1 or show errors."""
    if returncode != 0:
        content = "[bold red]GHOST-1 Execution Failed[/bold red]\n\n"
        if stderr:
            content += f"[dim]stderr:[/dim]\n{stderr}\n"
        if stdout:
            content += f"[dim]stdout:[/dim]\n{stdout}"

        # Inject 130/100 Accessibility Permission advice
        if (
            "System Events" in stderr
            or "accessibility" in stderr.lower()
            or "not allowed" in stderr.lower()
        ):
            content += "\n[bold yellow]⚠️  APPLE ACCESSIBILITY SHIELD TRIGGERED[/bold yellow]\n"
            content += "Go to: System Settings > Privacy & Security > Accessibility\n"
            content += "And grant permissions to your terminal or IDE."

        console.print(Panel(content, border_style="red", title=title))
        sys.exit(returncode)

    try:
        # Ghost outputs JSON mostly, let's try to parse and pretty print
        data = json.loads(stdout)
        formatted_json = json.dumps(data, indent=2)
        console.print(Panel(f"[cyan]{formatted_json}[/cyan]", border_style="cyan", title=title))
    except json.JSONDecodeError:
        # Not JSON, just print it
        if stdout.strip():
            console.print(Panel(stdout.strip(), border_style="cyan", title=title))


@click.group(name="ghost")
def ghost_cmds():
    """👻 GHOST-1: The Invisible Hand (Sovereign macOS OS Control)."""
    pass


@ghost_cmds.command()
def status():
    """Check the status of GHOST-1 dependencies."""
    code, out, err = run_ghost_skill(["status"])
    handle_ghost_response(code, out, err, "[bold magenta]👻 GHOST-1 Status[/bold magenta]")


@ghost_cmds.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def hand(ctx):
    """Mouse and keyboard control (click, type, hotkey)."""
    code, out, err = run_ghost_skill(["hand"] + ctx.args)
    handle_ghost_response(code, out, err, "[bold magenta]👻 GHOST-1 Hand[/bold magenta]")


@ghost_cmds.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def eyes(ctx):
    """Screen vision and pixel parsing (screenshot, locate)."""
    code, out, err = run_ghost_skill(["eyes"] + ctx.args)
    handle_ghost_response(code, out, err, "[bold magenta]👻 GHOST-1 Eyes[/bold magenta]")


@ghost_cmds.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def process(ctx):
    """Process management (list, kill, find)."""
    code, out, err = run_ghost_skill(["process"] + ctx.args)
    handle_ghost_response(code, out, err, "[bold magenta]👻 GHOST-1 Process[/bold magenta]")


@ghost_cmds.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def window(ctx):
    """Window management (list, focus, tile)."""
    code, out, err = run_ghost_skill(["window"] + ctx.args)
    handle_ghost_response(code, out, err, "[bold magenta]👻 GHOST-1 Window[/bold magenta]")


@ghost_cmds.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def system(ctx):
    """System state and hardware (volume, brightness, battery)."""
    code, out, err = run_ghost_skill(["system"] + ctx.args)
    handle_ghost_response(code, out, err, "[bold magenta]👻 GHOST-1 System[/bold magenta]")


@ghost_cmds.command(context_settings={"ignore_unknown_options": True, "allow_extra_args": True})
@click.pass_context
def actions(ctx):
    """High-level actions (open-app, select-all)."""
    code, out, err = run_ghost_skill(["actions"] + ctx.args)
    handle_ghost_response(code, out, err, "[bold magenta]👻 GHOST-1 Actions[/bold magenta]")
