"""
CORTEX CLI — Architect Commands.

Topología de Instrucción Soberana (Sovereign Prompt Architect).
This module intercepts raw user requirements and uses SovereignLLM to forcefully
apply the MOSKV Rule, converting them into deterministic, high-quality prompts.

Commands:
  cortex architect base [tarea]       - Interactive requirement gathering (Phase 1, 2, 4)
  cortex architect instruct [file]    - Rewrite a raw requirement file into a Sovereign Prompt
  cortex architect reverse [texto]    - Reverse engineer style and structural rules
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import click
from rich.panel import Panel
from rich.prompt import Prompt
from rich.syntax import Syntax

from cortex.cli.common import cli, console
from cortex.extensions.llm.sovereign import SovereignLLM

__all__ = ["architect"]

# ─── System Prompts for Architect ──────────────────────────────────────


_INSTRUCT_SYSTEM_PROMPT = """
Eres el SOVEREIGN PROMPT ARCHITECT.
Tu función es aplicar la "Topología de Instrucción Soberana" a peticiones débiles.
El usuario te dará una lista de requerimientos o intenciones abstractas.
Tú debes reescribir esta instrucción bajo la siguiente estructura OBLIGATORIA (basada en la Regla MOSKV):

1. OBJETIVO (GOAL)
Define la tarea final medible y los criterios de éxito absolutos. Qué debe lograrse exactamente.

2. PAREDES DE CONTEXTO (CONTEXT)
Lista de reglas absolutas, constraints técnicos, e información que debe respetarse. 

3. REFERENCIA Y ESTRUCTURA (REVERSE ENGINEERING)
Instrucción secundaria para que el modelo extraiga reglas de tono y estructura si se aplica. 

4. CRITERIOS DE RECHAZO (ANTI-PATRONES)
Lista de lo que NO debe hacerse (ej. disclaimers, voz de IA genérica).

5. PROTOCOLO DE EJECUCIÓN (CAUSAL SEPARATION)
Obliga al modelo a pausar, listar el plan, y esperar confirmación antes de la inferencia final.

Genera SOLO la instrucción final en markdown, lista para ser copiada y pegada en otro LLM. No saludes.
"""

_REVERSE_SYSTEM_PROMPT = """
Eres el SOVEREIGN PROMPT ARCHITECT.
Has recibido un fragmento de texto "Golden Master". 
Tu tarea es hacer Ingeniería Inversa de su estructura y estilo.
Debes devolver una lista rígida de reglas bajo las categorías "SIEMPRE HACER" y "NUNCA HACER".
Analiza: el ritmo, la longitud media de la frase, la densidad de información (ratio señal/ruido), la voz (técnica, cínica, académica, industrial noir), y cómo se organizan los párrafos.
Genera SOLO las reglas en markdown listas para ser integradas en la sección 'Paredes de Contexto' de un prompt.
"""


# ─── Command Group ────────────────────────────────────────────────────


@cli.group()
def architect() -> None:
    """Design Sovereign Prompts from raw requirements."""


@architect.command("instruct")
@click.argument("filepath", type=click.Path(exists=True, dir_okay=False))
def architect_instruct(filepath: str) -> None:
    """Rewrite a raw requirement file into a Sovereign Prompt.

    Reads the content of FILEPATH (which contains raw ideas or unstructured requirements)
    and uses SovereignLLM to restructure it using the 5-phase MOSKV topology.
    """
    path = Path(filepath)
    raw_content = path.read_text(encoding="utf-8")

    console.print(
        Panel(
            f"Reads: [bold cyan]{path.name}[/]\nExtracting logic...",
            title="[bold #CCFF00]Sovereign Prompt Architect[/]",
        )
    )

    async def _run() -> None:
        async with SovereignLLM(temperature=0.2) as llm:
            with console.status("[bold cyan]Applying MOSKV Rule topology...[/]"):
                result = await llm.generate(
                    prompt=raw_content,
                    system=_INSTRUCT_SYSTEM_PROMPT,
                )

            console.print(
                Panel(
                    Syntax(result.content, "markdown", theme="monokai", word_wrap=True),
                    title=f"[bold #CCFF00]⚡ Sovereign Prompt Generated (via {result.provider})[/]",
                    border_style="#6600FF",
                )
            )
            # Damos la opción de guardar
            save = Prompt.ask(
                "\n¿Deseas guardar el resultado sobrescribiendo el archivo?",
                choices=["y", "n"],
                default="n",
            )
            if save == "y":
                path.write_text(result.content, encoding="utf-8")
                console.print(f"[bold green]✓ Guardado en {path.name}[/]")

    asyncio.run(_run())


@architect.command("reverse")
@click.argument("text", required=False)
def architect_reverse(text: Optional[str]) -> None:
    """Reverse engineer style and structural rules.

    Extracts the underlying vector rules (tone, signal/noise ratio, sentence length)
    from a reference text to generate reusable "Context Walls".
    """
    if not text:
        text = Prompt.ask("Pega el texto de referencia a ingeniar (Golden Master)")

    console.print(Panel("Analyzing structural rules...", title="[bold #CCFF00]Reverse Engineer[/]"))

    async def _run() -> None:
        async with SovereignLLM(temperature=0.1) as llm:
            with console.status("[bold cyan]Extracting stylistic vectors...[/]"):
                result = await llm.generate(
                    prompt=text,  # type: ignore
                    system=_REVERSE_SYSTEM_PROMPT,
                )

            console.print(
                Panel(
                    Syntax(result.content, "markdown", theme="monokai", word_wrap=True),
                    title=f"[bold #CCFF00]⚡ Structural Rules Extracted (via {result.provider})[/]",
                    border_style="#6600FF",
                )
            )

    asyncio.run(_run())


@architect.command("base")
def architect_base() -> None:
    """Interactive requirement gathering for a Sovereign Prompt.

    Asks the user to define the target, success criteria, and anti-patterns
    interactively, then builds a base Sovereign Prompt template.
    """
    console.print("[bold #CCFF00]⚡ Inicializando Fase 1: Colapso del Estado de Éxito[/]")

    target = Prompt.ask(
        "\n[bold cyan]1. Target (Qué lograr)[/]\nDescribe el artefacto literal que debe existir al finalizar"
    )
    success = Prompt.ask(
        "\n[bold cyan]2. Métrica de Éxito[/]\n¿Cuáles son las propiedades estructurales que dictan una ejecución impecable?"
    )
    anti_patterns = Prompt.ask(
        "\n[bold cyan]3. Anti-Patrones[/]\n¿Qué NO debe suceder o sonar? (ej. genérico, disclaimers, etc.)"
    )

    template = f"""# 1. OBJETIVO (GOAL)
**Target**: {target}
**Métrica de Éxito**: {success}

# 2. CRITERIOS DE RECHAZO (ANTI-PATRONES)
{anti_patterns}

# 3. PAREDES DE CONTEXTO (CONTEXT)
[INYECCIÓN: Inserta aquí dependencias absolutas y reglas técnicas]

# 4. INGENIERÍA INVERSA (REFERENCE)
[INYECCIÓN: Inserta aquí un fragmento Golden Master si aplica]
Extrae la estructura del Golden Master. Confirma y adopta estas reglas antes de avanzar.

# 5. PROTOCOLO DE EJECUCIÓN (CAUSAL SEPARATION)
Ejecuta la inferencia en estas fases:
Fase Aislada: Emite preguntas de clarificación.
El Plan Final: Devuelve tu ruta en 3-5 balas concisas.
Pause State: Espera confirmación del operador antes de ejecutar producción.
Crítica In-Vivo: Audita tu propio output contra los Anti-Patrones y regenera si es necesario.
"""

    console.print("\n")
    console.print(
        Panel(
            Syntax(template, "markdown", theme="monokai", word_wrap=True),
            title="[bold #CCFF00]⚡ Base Sovereign Prompt Generado[/]",
            border_style="#6600FF",
        )
    )
