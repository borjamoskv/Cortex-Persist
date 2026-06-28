# [C5-REAL] Exergy-Maximized
from __future__ import annotations

# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""Auto-Healer (Entropy to O(1)).

Apotheosis Level 5: Auto-resolution of dense code via configured LLMs.
"""

import asyncio
import os

# Fix: some commands might run longer than the 30s timeout if the model takes a while to respond.
# We will temporarily disable the alarm handler if running this command.
import signal
from pathlib import Path

import click
import dotenv
from rich.console import Console

from cortex.extensions.llm.provider import LLMProvider
from cortex.extensions.llm.router import CortexPrompt

dotenv.load_dotenv()

console = Console()

HEALING_SYSTEM_PROMPT = """\
[IDENTITY] Auto-Healer (Apotheosis Level 5) | Entropy Surgeon.
[DIRECTIVE] REDUCE CYCLOMATIC COMPLEXITY < 15. Zero latency payload.

[STRUCTURAL TOPOLOGY: SURGICAL PRIMITIVES]
- 1. Guard Clauses: Flatten nested if/else unconditionally (kill the arrow anti-pattern).
- 2. Helper Extraction: Isolate massive blocks inside iterations into pure functions.
- 3. Isomorphic Behavior: Logic MUST remain identical, but structurally O(1).
- 4. Type Safety: Preserve and enforce all Python Type Hints.

[OUTPUT PRIMITIVES: STRICT MACHINE READABILITY]
- RETURN RAW CODE ONLY.
- NO MARKDOWN BLOCKS (```python)
- NO CONVERSATIONAL PROSE. NO EXPLANATIONS.
- IF IT REQUIRES PARSING FLUFF, YOU HAVE FAILED.\
"""


def _clean_markdown(code: str) -> str:
    """Removes markdown code block formatting."""
    if code.startswith("```python"):
        code = code.split("\n", 1)[1]
    if code.startswith("```"):
        code = code.split("\n", 1)[1]
    if code.endswith("```"):
        code = code.rsplit("\n", 1)[0]
    return code.strip()


async def auto_heal(filepath: Path) -> None:
    if not filepath.exists():
        console.print(f"[red]❌ Error:[/red] The file {filepath} does not exist.")
        raise click.Abort()

    console.print(f"🧬 Initiating Sovereign Surgery on: [cyan]{filepath.name}[/cyan]")

    original_code = filepath.read_text(encoding="utf-8")

    try:
        provider_name = os.environ.get("CORTEX_LLM_PROVIDER", "gemini")
        provider = LLMProvider(provider=provider_name)
    except (OSError, ValueError, RuntimeError, ImportError) as e:
        console.print(f"[red]❌ Error initializing LLMProvider:[/red] {e}")
        raise click.Abort() from e

    console.print(f"   ► Connecting architectural brain ([blue]{provider.model_name}[/blue])...")

    prompt = CortexPrompt(
        system_instruction=HEALING_SYSTEM_PROMPT,
        working_memory=[
            {
                "role": "user",
                "content": f"Please purge the static from this file:\n\n{original_code}",
            }
        ],
        temperature=0.1,  # Low for higher determinism in code
        max_tokens=8192,
    )

    try:
        raw_code = await provider.invoke(prompt)
        healed_code = _clean_markdown(raw_code.value if hasattr(raw_code, "value") else raw_code)  # type: ignore[reportAttributeAccessIssue]

        # Overwrite file
        filepath.write_text(healed_code + "\n", encoding="utf-8")

        console.print(
            f"[green]✅ Healing completed![/green] "
            f"The file {filepath.name} has been reconstructed.\n"
        )
        console.print(
            "💡 [bold yellow][SOVEREIGN TIP][/bold yellow] "
            "Review the changes (`git diff`) and try your commit again."
        )

    except (OSError, ValueError, RuntimeError) as exc:
        import traceback

        console.print("[red]❌ Critical failure during Healer:[/red]")
        traceback.print_exc()
        raise click.Abort() from exc
    finally:
        await provider.close()


@click.command(name="heal", short_help="Auto-healing of entropy (Cyclomatic Complexity)")
@click.argument("filepath", type=click.Path(exists=True, path_type=Path))
def cli(filepath: Path) -> None:
    """Invokes the LLM surgeon to reduce static (Axiom 14).

    Uses the current CORTEX_LLM_PROVIDER to refactor the internal structure
    of obese functions using guard clauses and functional delegation.
    """

    # Disable the timeout alarm for this command because LLMs can take more than 30s.
    if hasattr(signal, "SIGALRM"):
        signal.alarm(0)

    try:
        asyncio.run(auto_heal(filepath))
    except KeyboardInterrupt:
        console.print("\n[red]🛑 Healing aborted by operator.[/red]")
