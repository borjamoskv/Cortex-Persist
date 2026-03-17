import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel

from cortex.extensions.llm.router import IntentProfile
from cortex.extensions.llm.sovereign import SovereignLLM

console = Console()

# ----------------------------------------------------------------------------
# TRIANGULATION PROTOCOL: DIAGNOSTIC TRIAGE
# 1. Information Theory (Prompt Thermal Noise)
# 2. Game Theory (Perverse Incentives)
# 3. Complex Systems (Rule Clashes)
# ----------------------------------------------------------------------------

_LENS_TIMEOUT_SECONDS = 30.0
_MAX_LOG_CHARS = 50_000


async def _run_lens(
    name: str,
    prompt: str,
) -> tuple[str, Optional[str]]:
    """Run a single diagnostic lens with timeout and error isolation."""
    # Axiom 4: Zero Trust. Never rely on a single model for diagnostics.
    async with SovereignLLM(timeout_seconds=_LENS_TIMEOUT_SECONDS, temperature=0.1) as llm:
        try:
            result = await llm.generate(
                prompt,
                system="You are a diagnostic Inquisitor. Analyze the log through the specified lens.",
                intent=IntentProfile.REASONING,
            )
            return name, result.content
        except Exception as e:  # noqa: BLE001
            return name, f"[ERROR] Lens '{name}' failed: {type(e).__name__}: {e}"


async def _lens_information_theory(log_data: str) -> tuple[str, Optional[str]]:
    """Evaluates thermal noise, context window degradation, and entropy."""
    prompt = (
        "Analyze this log through INFORMATION THEORY. "
        "Is there thermal noise in the prompt? Context degradation? "
        "Unclear signal-to-noise ratio?\n\nLOG:\n" + log_data
    )
    return await _run_lens("information_theory", prompt)


async def _lens_game_theory(log_data: str) -> tuple[str, Optional[str]]:
    """Evaluates perverse incentives and sub-agent misalignment."""
    prompt = (
        "Analyze this log through GAME THEORY. "
        "Are the sub-agents perversely incentivized? "
        "Is there a resource conflict or misalignment of reward/completion metrics?\n\nLOG:\n"
        + log_data
    )
    return await _run_lens("game_theory", prompt)


async def _lens_complex_systems(log_data: str) -> tuple[str, Optional[str]]:
    """Evaluates emergent unpredictability from isolated simple rules."""
    prompt = (
        "Analyze this log through COMPLEX SYSTEMS THEORY. "
        "Is this an unpredictable interaction between two simple, "
        "perfectly valid rules operating in isolation?\n\nLOG:\n" + log_data
    )
    return await _run_lens("complex_systems", prompt)


async def run_diagnostic_triangulation(log_data: str) -> dict[str, str]:
    """Executes the three diagnostic lenses in parallel O(1) time."""
    with console.status(
        "[bold cyan]Ejecutando Triangulación Diagnóstica en Paralelo "
        "(Información, Juegos, Sistemas Complejos)...[/bold cyan]"
    ):
        results = await asyncio.gather(
            _lens_information_theory(log_data),
            _lens_game_theory(log_data),
            _lens_complex_systems(log_data),
            return_exceptions=True,
        )

    output: dict[str, str] = {}
    for item in results:
        if isinstance(item, BaseException):
            output[f"error_{type(item).__name__}"] = str(item)
        else:
            name, content = item
            output[name] = content or "[NO OUTPUT]"
    return output


_LENS_LABELS = {
    "information_theory": ("1", "TEORÍA DE LA INFORMACIÓN"),
    "game_theory": ("2", "TEORÍA DE JUEGOS"),
    "complex_systems": ("3", "SISTEMAS COMPLEJOS"),
}


@click.command(name="triangulate")
@click.argument("log_file", type=click.Path(exists=True))
def triangulate(log_file: str) -> None:
    """
    DISPARA EL PROTOCOLO DE TRIANGULACIÓN DIAGNÓSTICA.
    Analiza un log de error mágico bajo 3 lentes en paralelo.
    """
    with open(log_file, encoding="utf-8") as f:
        log_data = f.read()

    # Limitar el tamaño para prevenir context overflow
    if len(log_data) > _MAX_LOG_CHARS:
        log_data = log_data[-_MAX_LOG_CHARS:]

    console.print(
        f"[bold red]ANOMALÍA DETECTADA. INICIANDO TRIANGULACIÓN SOBRE {log_file}.[/bold red]"
    )

    results = asyncio.run(run_diagnostic_triangulation(log_data))

    for key, content in results.items():
        label_info = _LENS_LABELS.get(key)
        if label_info:
            num, title = label_info
            console.print(
                Panel(
                    content,
                    title=f"[bold]{num}. LENTE: {title}[/bold]",
                    border_style="green",
                )
            )
        else:
            console.print(f"\n[bold red]{key}:[/bold red] {content}")

    console.print("\n[bold purple]/// TRIANGULACIÓN COMPLETADA ///[/bold purple]")
    console.print("Evalúe los tres vectores para aislar la cuenca del error.")
