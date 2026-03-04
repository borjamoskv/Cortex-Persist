# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""CORTEX v5.0 — Auto-Healer (Entropía a O(1)).

Apotheosis Nivel 5: Auto-resolución de código denso mediante LLMs configurados.
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

from cortex.llm.provider import LLMProvider
from cortex.llm.router import CortexPrompt

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
        console.print(f"[red]❌ Error:[/red] El archivo {filepath} no existe.")
        raise click.Abort()

    console.print(f"🧬 Iniciando Cirugía Soberana en: [cyan]{filepath.name}[/cyan]")

    original_code = filepath.read_text(encoding="utf-8")

    try:
        provider_name = os.environ.get("CORTEX_LLM_PROVIDER", "gemini")
        provider = LLMProvider(provider=provider_name)
    except (OSError, ValueError, RuntimeError, ImportError) as e:
        console.print(f"[red]❌ Error al inicializar LLMProvider:[/red] {e}")
        raise click.Abort() from e

    console.print(f"   ► Conectando cerebro arquitectónico ([blue]{provider.model}[/blue])...")

    prompt = CortexPrompt(
        system_instruction=HEALING_SYSTEM_PROMPT,
        working_memory=[
            {
                "role": "user",
                "content": f"Por favor, purga la estática de este archivo:\n\n{original_code}",
            }
        ],
        temperature=0.1,  # Bajo para mayor determinismo en código
        max_tokens=8192,
    )

    try:
        raw_code = await provider.invoke(prompt)
        healed_code = _clean_markdown(raw_code.value if hasattr(raw_code, "value") else raw_code)  # type: ignore[reportAttributeAccessIssue]

        # Overwrite file
        filepath.write_text(healed_code + "\n", encoding="utf-8")

        console.print(
            f"[green]✅ ¡Sanación completada![/green] "
            f"El archivo {filepath.name} ha sido reconstruido.\n"
        )
        console.print(
            "💡 [bold yellow][SOVEREIGN TIP][/bold yellow] "
            "Revisa los cambios (`git diff`) e intenta tu commit de nuevo."
        )

    except (OSError, ValueError, RuntimeError) as exc:
        import traceback

        console.print("[red]❌ Fallo crítico durante el Healer:[/red]")
        traceback.print_exc()
        raise click.Abort() from exc
    finally:
        await provider.close()


@click.command(name="heal", short_help="Auto-sanación de entropía (Complejidad Ciclomática)")
@click.argument("filepath", type=click.Path(exists=True, path_type=Path))
def cli(filepath: Path) -> None:
    """Invoca al cirujano LLM para reducir estática (Axioma 14).

    Utiliza el CORTEX_LLM_PROVIDER actual para refactorizar la estructura
    interna de funciones obesas usando guard clauses y delegación funcional.
    """

    # Disable the timeout alarm for this command because LLMs can take more than 30s.
    if hasattr(signal, "SIGALRM"):
        signal.alarm(0)

    try:
        asyncio.run(auto_heal(filepath))
    except KeyboardInterrupt:
        console.print("\n[red]🛑 Sanación abortada por el operador.[/red]")
