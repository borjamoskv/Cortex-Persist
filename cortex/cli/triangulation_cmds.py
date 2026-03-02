import asyncio

import click
from rich.console import Console

console = Console()
from cortex.llm.provider import query_llm

# ----------------------------------------------------------------------------
# TRIANGULATION PROTOCOL: DIAGNOSTIC TRIAGE
# 1. Information Theory (Prompt Thermal Noise)
# 2. Game Theory (Perverse Incentives)
# 3. Complex Systems (Rule Clashes)
# ----------------------------------------------------------------------------


async def _lens_information_theory(log_data: str) -> str:
    """Evaluates thermal noise, context window degradation, and entropy."""
    prompt = f"Analyze this log through INFORMATION THEORY. Is there thermal noise in the prompt? Context degradation? Unclear signal-to-noise ratio?\n\nLOG:\n{log_data}"
    return await query_llm(prompt, model="gpt-4o-mini", temperature=0.1)


async def _lens_game_theory(log_data: str) -> str:
    """Evaluates perverse incentives and sub-agent misalignment."""
    prompt = f"Analyze this log through GAME THEORY. Are the sub-agents perversely incentivized? Is there a resource conflict or misalignment of reward/completion metrics?\n\nLOG:\n{log_data}"
    return await query_llm(prompt, model="gpt-4o-mini", temperature=0.1)


async def _lens_complex_systems(log_data: str) -> str:
    """Evaluates emergent unpredictability from isolated simple rules."""
    prompt = f"Analyze this log through COMPLEX SYSTEMS THEORY. Is this an unpredictable interaction between two simple, perfectly valid rules operating in isolation?\n\nLOG:\n{log_data}"
    return await query_llm(prompt, model="gpt-4o-mini", temperature=0.1)


async def run_diagnostic_triangulation(log_data: str) -> dict[str, str]:
    """Executes the three diagnostic lenses in parallel O(1) time."""
    with console.status(
        "[bold cyan]Ejecutando Triangulación Diagnóstica en Paralelo (Información, Juegos, Sistemas Complejos)...[/bold cyan]"
    ):
        results = await asyncio.gather(
            _lens_information_theory(log_data),
            _lens_game_theory(log_data),
            _lens_complex_systems(log_data),
        )
    return {
        "information_theory": results[0],
        "game_theory": results[1],
        "complex_systems": results[2],
    }


@click.command(name="triangulate")
@click.argument("log_file", type=click.Path(exists=True))
def triangulate(log_file: str):
    """
    DISPARA EL PROTOCOLO DE TRIANGULACIÓN DIAGNÓSTICA.
    Analiza un log de error mágico bajo 3 lentes en paralelo.
    """
    with open(log_file, encoding="utf-8") as f:
        log_data = f.read()

    # Limitar el tamaño para prevenir context overflow
    if len(log_data) > 50000:
        log_data = log_data[-50000:]

    console.print(
        f"[bold red]ANOMALÍA DETECTADA. INICIANDO TRIANGULACIÓN SOBRE {log_file}.[/bold red]"
    )

    results = asyncio.run(run_diagnostic_triangulation(log_data))

    console.print("\n[bold neon_green]1. LENTE: TEORÍA DE LA INFORMACIÓN[/bold neon_green]")
    console.print(results["information_theory"])

    console.print("\n[bold neon_green]2. LENTE: TEORÍA DE JUEGOS[/bold neon_green]")
    console.print(results["game_theory"])

    console.print("\n[bold neon_green]3. LENTE: SISTEMAS COMPLEJOS[/bold neon_green]")
    console.print(results["complex_systems"])

    console.print("\n[bold purple]/// TRIANGULACIÓN COMPLETADA ///[/bold purple]")
    console.print("Evalúe los tres vectores para aislar la cuenca del error.")
