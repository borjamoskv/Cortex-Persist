"""
CORTEX CLI — Prompt Commands.

Salto 2: Dynamic prompt generation from live codebase stats.
The system prompt is no longer a static document — it's a living artifact
generated from actual project metrics every time you need it.

Commands:
  cortex prompt show [--variant short|medium|full]   Print the prompt
  cortex prompt generate                              Regenerate with live stats
  cortex prompt copy [--variant short|medium|full]   Copy to clipboard
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import click
from rich.panel import Panel
from rich.syntax import Syntax

from cortex.cli import cli, console

__all__ = ["prompt"]

# ─── Helpers ──────────────────────────────────────────────────────────


def _count_python_loc(root: Path) -> int:
    """Count lines of Python production code (excludes tests, venv)."""
    total = 0
    for p in root.rglob("*.py"):
        parts = p.parts
        if any(s in parts for s in ("tests", ".venv", "venv", "__pycache__")):
            continue
        try:
            total += sum(1 for _ in p.open("r", errors="replace"))
        except OSError:
            pass
    return total


def _count_python_modules(root: Path) -> int:
    """Count .py files in production code."""
    return sum(
        1
        for p in root.rglob("*.py")
        if not any(s in p.parts for s in ("tests", ".venv", "venv", "__pycache__"))
    )


def _count_test_functions(root: Path) -> int:
    """Count def test_ functions across test suite."""
    count = 0
    for p in root.rglob("test_*.py"):
        try:
            count += sum(
                1 for line in p.open("r", errors="replace")
                if line.lstrip().startswith("def test_")
            )
        except OSError:
            pass
    return count


def _count_rest_endpoints(root: Path) -> int:
    """Count FastAPI route decorators (@router.get/post/put/delete/patch)."""
    count = 0
    import re
    pattern = re.compile(r"@\w*router\.(get|post|put|delete|patch|head|options)\(")
    for p in root.rglob("*.py"):
        if "tests" in p.parts or ".venv" in p.parts:
            continue
        try:
            count += sum(1 for line in p.open("r", errors="replace") if pattern.search(line))
        except OSError:
            pass
    return count


def _count_cli_commands(root: Path) -> int:
    """Count @cli.command() and @<group>.command() decorators."""
    count = 0
    import re
    pattern = re.compile(r"@\w+\.command\(")
    for p in root.rglob("*.py"):
        if "tests" in p.parts or ".venv" in p.parts:
            continue
        try:
            count += sum(1 for line in p.open("r", errors="replace") if pattern.search(line))
        except OSError:
            pass
    return count


def _count_secret_patterns() -> int:
    """Count patterns in the Privacy Shield classifier."""
    try:
        from cortex.storage.classifier import SECRET_PATTERNS
        return len(SECRET_PATTERNS)
    except ImportError:
        return 25


def _git_tag() -> str:
    """Return the latest git tag or 'v0.3.0-beta'."""
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            capture_output=True, text=True, timeout=3
        )
        return result.stdout.strip() or "v0.3.0-beta"
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return "v0.3.0-beta"


def _generate_live_prompt(project_root: Path) -> str:
    """Build the full system prompt with real-time stats injected."""
    from cortex.agents.system_prompt import SYSTEM_PROMPT

    with console.status("[bold cyan]📊 Computing live codebase stats...[/]"):
        loc = _count_python_loc(project_root)
        modules = _count_python_modules(project_root)
        tests = _count_test_functions(project_root)
        endpoints = _count_rest_endpoints(project_root)
        cli_cmds = _count_cli_commands(project_root)
        patterns = _count_secret_patterns()
        version = _git_tag()

    # Replace static stats with live values
    live = SYSTEM_PROMPT
    replacements = [
        ("45K+ LOC", f"{loc // 1000}K+ LOC"),
        ("45,500+ LOC", f"{loc:,}+ LOC"),
        ("1,162+ tests", f"{tests:,}+ tests"),
        ("444 modules", f"{modules}+ modules"),
        ("55+ REST endpoints", f"{endpoints}+ REST endpoints"),
        ("38 CLI commands", f"{cli_cmds}+ CLI commands"),
        ("25 secret-detection patterns", f"{patterns} secret-detection patterns"),
        ("25 pat", f"{patterns} pat"),
        ("v2.0", version),
    ]
    for old, new in replacements:
        live = live.replace(old, new)

    return live


# ─── Command Group ────────────────────────────────────────────────────


@cli.group()
def prompt() -> None:
    """System prompt management — generate, show, copy."""


@prompt.command("show")
@click.option(
    "--variant",
    type=click.Choice(["short", "medium", "full"]),
    default="full",
    help="Which prompt variant to display.",
)
def prompt_show(variant: str) -> None:
    """Print the CORTEX system prompt to stdout."""
    from cortex.agents.system_prompt import (
        SYSTEM_PROMPT,
        SYSTEM_PROMPT_MEDIUM,
        SYSTEM_PROMPT_SHORT,
    )

    text = {
        "short": SYSTEM_PROMPT_SHORT,
        "medium": SYSTEM_PROMPT_MEDIUM,
        "full": SYSTEM_PROMPT,
    }[variant]
    token_estimate = len(text.split()) * 4 // 3  # rough GPT tokenisation
    console.print(
        Panel(
            Syntax(text, "markdown", theme="monokai", word_wrap=True),
            title=f"[bold #CCFF00]⚡ CORTEX System Prompt — {variant.upper()}[/]",
            subtitle=f"[dim]~{token_estimate} tokens[/]",
            border_style="#6600FF",
        )
    )


@prompt.command("generate")
@click.option(
    "--variant",
    type=click.Choice(["short", "medium", "full"]),
    default="full",
    help="Variant to generate with live stats.",
)
@click.option(
    "--out",
    default=None,
    help="Write generated prompt to file instead of stdout.",
)
def prompt_generate(variant: str, out: str | None) -> None:
    """Regenerate the system prompt with live codebase statistics.

    Stats injected: LOC, test count, module count, REST endpoints,
    CLI commands, Privacy Shield pattern count, current git tag.
    """
    project_root = Path(__file__).resolve().parent.parent.parent

    if variant == "full":
        text = _generate_live_prompt(project_root)
    else:
        # short/medium don't embed stats yet — but show accurate pattern count
        from cortex.agents.system_prompt import SYSTEM_PROMPT_MEDIUM, SYSTEM_PROMPT_SHORT
        patterns = _count_secret_patterns()
        base = SYSTEM_PROMPT_SHORT if variant == "short" else SYSTEM_PROMPT_MEDIUM
        text = base.replace("25 secret-detection patterns", f"{patterns} secret-detection patterns")
        text = text.replace("25 patterns", f"{patterns} patterns")

    token_estimate = len(text.split()) * 4 // 3

    if out:
        Path(out).write_text(text, encoding="utf-8")
        console.print(
            Panel(
                f"[bold green]✓ Prompt written to:[/] {out}\n[dim]~{token_estimate} tokens[/]",
                title="[bold #CCFF00]⚡ CORTEX Prompt[/]",
                border_style="green",
            )
        )
    else:
        console.print(
            Panel(
                Syntax(text, "markdown", theme="monokai", word_wrap=True),
                title=f"[bold #CCFF00]⚡ CORTEX System Prompt — {variant.upper()} (live stats)[/]",
                subtitle=f"[dim]~{token_estimate} tokens[/]",
                border_style="#6600FF",
            )
        )


@prompt.command("copy")
@click.option(
    "--variant",
    type=click.Choice(["short", "medium", "full"]),
    default="medium",
    help="Variant to copy (default: medium for general use).",
)
def prompt_copy(variant: str) -> None:
    """Copy the system prompt to the clipboard."""
    import subprocess as sp

    from cortex.agents.system_prompt import (
        SYSTEM_PROMPT,
        SYSTEM_PROMPT_MEDIUM,
        SYSTEM_PROMPT_SHORT,
    )

    text = {
        "short": SYSTEM_PROMPT_SHORT,
        "medium": SYSTEM_PROMPT_MEDIUM,
        "full": SYSTEM_PROMPT,
    }[variant]
    token_estimate = len(text.split()) * 4 // 3

    try:
        sp.run(["pbcopy"], input=text.encode(), check=True, timeout=5)
        console.print(
            Panel(
                f"[bold green]✓ Copied to clipboard![/] ({variant}, ~{token_estimate} tokens)\n"
                "[dim]Paste into your IDE system prompt, API call, or agent config.[/]",
                title="[bold #CCFF00]⚡ CORTEX Prompt[/]",
                border_style="green",
            )
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        # Fallback: just print it
        console.print("[yellow]⚠ pbcopy not available. Printing prompt instead:[/]")
        console.print(text)
