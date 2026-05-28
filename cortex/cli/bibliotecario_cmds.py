"""
CORTEX CLI — Bibliotecario (LIBRARIAN-1) commands.

The BIBLIOTECARIO agent ("se encarga de ordenar") ingests messy
directories, files, or text, and orchestrates an LLM to organize and synthesize
them into structured CORTEX Memos (Markdown).
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.errors import err_execution_failed
from cortex.extensions.llm.manager import LLMManager

console = Console()

LIBRARIAN_SYSTEM_PROMPT = """\
You are LIBRARIAN-1 (El Bibliotecario), a Sovereign Context Engine for MOSKV-1.
Your directive: INGEST ENTROPY, OUTPUT STRUCTURE.
Your output must be optimized for MACHINE (O(1) retrieval by agents like demiurge-omega) 
before human readability. ZERO FLUFF.

OUTPUT FORMAT REQUIREMENTS:
1. Title: `# [SUBJECT] Sovereign Memo`
2. `[O(1) PRIMITIVES]`: Bullet points of absolute truth. Extracted core definitions. 
3. `[STRUCTURAL TOPOLOGY]`: How the ingested parts connect. 
4. `[ACTIONABLE PAYLOAD]`: Code, commands, or exact JSON parameters. "Copy-Paste Arsenal".
5. `[DEBT TRANSLATION]`: What technical debt/fluff was removed to produce this structure.

STRICT CONSTRAINTS:
- No prose. Use concise, dense bullet points or code blocks.
- If it takes the system > 5 seconds to parse your intent, you have failed.
- Maximize information density per token.
- NO conversational filler. Only pure signal.\
"""


@click.group(name="bibliotecario")
def bibliotecario_cmds():
    """📚 LIBRARIAN-1: Se encarga de ordenar y estructurar conocimiento."""
    pass


async def _ingest_and_organize(path: Path) -> str:
    """Read the content of a file or directory recursively and organize it."""
    if not path.exists():
        return f"Error: Path {path} does not exist."

    content = ""
    if path.is_file():
        try:
            content = path.read_text(encoding="utf-8")
        except Exception as e:  # noqa: BLE001
            return f"Error reading file {path}: {e}"
    elif path.is_dir():
        for root, _, files in os.walk(path):
            for file in files:
                if file.startswith(".") or "__pycache__" in root:
                    continue
                file_path = Path(root) / file
                try:
                    text = file_path.read_text(encoding="utf-8")
                    content += f"\\n\\n--- FILE: {file_path.relative_to(path)} ---\\n{text}"
                except (UnicodeDecodeError, OSError):
                    pass

    # Truncate to avoid context window explosion
    if len(content) > 100000:
        content = content[:100000] + "\\n...[TRUNCATED]"

    llm = LLMManager()
    if not llm.available:
        return "Error: LLM provider not available. Set CORTEX_LLM_PROVIDER."

    console.print(f"[cyan]🧠 LIBRARIAN-1 is ordering {len(content)} bytes of entropy...[/cyan]")

    response = await llm.complete(
        prompt=f"Organize this raw input:\\n{content}",
        system=LIBRARIAN_SYSTEM_PROMPT,
        temperature=0.2,
        max_tokens=4096,
    )
    return response or "Error: No response from LLM."


@bibliotecario_cmds.command("ordenar")
@click.argument("path", type=click.Path(exists=True))
@click.option("--output", "-o", help="Output file path for the organized memo")
def ordenar(path: str, output: str | None):
    """Ingest a file or directory and output a structured CORTEX Memo."""
    target_path = Path(path)

    try:
        result = asyncio.run(_ingest_and_organize(target_path))
    except (OSError, RuntimeError, ValueError) as e:
        err_execution_failed("bibliotecario ordenar", str(e))
        return

    if result.startswith("Error:"):
        console.print(
            Panel(result, border_style="red", title="[bold red]LIBRARIAN-1 Error[/bold red]")
        )
        return

    if output:
        out_path = Path(output)
        out_path.write_text(result, encoding="utf-8")
        console.print(f"[green]✅ Ordered knowledge saved to {out_path}[/green]")
    else:
        console.print(
            Panel(result, border_style="cyan", title="[bold cyan]📚 LIBRARIAN-1 Memo[/bold cyan]")
        )
