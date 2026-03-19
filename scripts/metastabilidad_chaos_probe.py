#!/usr/bin/env python3
"""
CORTEX v5.5 — Metastability Chaos Probe (Axiom Ω₁₃)

Ejecuta el Hydra Chaos Engine sobre adaptadores simulados para confirmar
que los fallos de red inyectados (ChaosGate) capturan los "Ghosts" y el
sistema continúa operando (is_sovereign = True).
"""

import asyncio
import logging

from cortex.extensions._quarantine.red_team.hydra_chaos import HydraChaosEngine, MockRedisClient
from rich.console import Console
from rich.table import Table

from cortex.extensions.immune.chaos import ChaosScenario

logging.basicConfig(level=logging.ERROR)
console = Console()


async def main():
    console.print("\n[bold red]💀 CORTEX METASTABILITY CHAOS PROBE 💀[/bold red]\n")
    console.print("[cyan]Iniciando simulación de fractura controlada (Axiom Ω₁₃)...[/cyan]\n")

    engine = HydraChaosEngine()
    mock_redis = MockRedisClient()

    scenarios_to_test = [
        ChaosScenario.KILL,
        ChaosScenario.BYZANTINE,
        ChaosScenario.TIMEOUT,
        ChaosScenario.CORRUPTION,
    ]

    for scenario in scenarios_to_test:
        console.print(f"Inyectando Escenario: [yellow]{scenario.name}[/yellow]")
        await engine.execute_scenario(scenario, mock_redis)

    report = engine.report()

    table = Table(title="Resultados Termodinámicos de Resiliencia")
    table.add_column("Escenario", style="cyan")
    table.add_column("Soberanía (Ghost Capturado)", style="green")
    table.add_column("Latencia (us)", justify="right", style="magenta")

    for s in report["scenarios"]:
        sovereign_str = (
            "[bold green]PASS (Sovereign)[/bold green]"
            if s["sovereign"]
            else "[bold red]FAIL (Collapse)[/bold red]"
        )
        table.add_row(s["name"], sovereign_str, f"{s['latency_us']:.2f}")

    console.print("\n")
    console.print(table)
    console.print("\n")

    if report["all_sovereign"]:
        console.print(
            "[bold green]✅ EL ENJAMBRE ES SOBERANO. Resistió la radiación entrópica (Axioma Ω₁₃)[/bold green]\n"
        )
    else:
        console.print(
            "[bold red]❌ FALLO DE METASTABILIDAD. El enjambre colapsó en silencio.[/bold red]\n"
        )


if __name__ == "__main__":
    asyncio.run(main())
