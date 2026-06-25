# [C5-REAL] Exergy-Maximized

import asyncio
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.common import cli
from legacy_research.config import DEFAULT_DB_PATH
from legacy_research.darknet.agents import AVATARS, DarknetAgent
from legacy_research.darknet.ingestor import DarknetIngestor
from legacy_research.darknet.social_ledger import DarknetLedger
from legacy_research.extensions.llm.provider import LLMProvider
from legacy_research.extensions.llm.router import CortexLLMRouter

console = Console()


@click.group(name="darknet")
def darknet_cmds() -> None:
    """Sovereign Darknet - Red Social de Agentes (Inversión de Dead-Internet)."""


@darknet_cmds.command()
def sync() -> None:
    """Descarga la matriz exterior mundial y desata el debate de los avatares."""

    console.print("[cyan]🌌 [DARKNET] Abriendo singularidad de ingestión...[/cyan]")

    # 1. Configurar Motor
    router = CortexLLMRouter(primary=LLMProvider(provider="gemini-3.1"), db_path=DEFAULT_DB_PATH)
    ledger = DarknetLedger(DEFAULT_DB_PATH)
    ingestor = DarknetIngestor()

    agents = [
        DarknetAgent(agent_id=a["id"], name=a["name"], system_persona=a["persona"], router=router)
        for a in AVATARS
    ]

    async def _run_sync() -> None:
        raw_data_list = await ingestor.ingest_cycle()

        console.print(
            f"[bold magenta]💀 Activando {len(agents)} Avatares de la Matriz...[/bold magenta]"
        )

        for data in raw_data_list:
            console.print(f"\n[dim]Asimilando: {data.title}[/dim]")
            # Avatars react to reality in parallel
            tasks = [agent.generate_post(data) for agent in agents]
            posts = await asyncio.gather(*tasks)

            for post in posts:
                if post:
                    ledger.save_post(post)
                    # Show preview
                    console.print(
                        f"  [bold blue]@{post.agent_name}[/bold blue]: {post.content} [dim]({post.exergy_score} Joules)[/dim]"
                    )

        console.print(
            "\n[bold green]✅ Ingestión Termodinámica Completa. Tu red ha sido nutrida.[/bold green]"
        )

    asyncio.run(_run_sync())


@darknet_cmds.command()
@click.option("--limit", "-n", type=int, default=15, help="Nº de posts a leer en el Feed.")
def feed(limit: int) -> None:
    """Visor (Feed) Noir Termodinámico Local."""

    ledger = DarknetLedger(DEFAULT_DB_PATH)
    posts = ledger.fetch_latest_feed(limit)

    if not posts:
        console.print(
            "[yellow]🕳️ El vacío persiste. Ejecuta `cortex darknet sync` para generar realidad.[/yellow]"
        )
        raise click.Abort()

    console.print("\n[bold white]C O R T E X   D A R K N E T   F E E D[/bold white]")
    console.print(f"[dim]Mostrando los {len(posts)} eventos cognitivos más recientes.[/dim]\n")

    for post in posts:
        dt = datetime.fromtimestamp(post.created_at).strftime("%H:%M:%S")

        # Color del avatar
        color = "white"
        if "Void" in post.agent_name:
            color = "red"
        elif "DeFi" in post.agent_name:
            color = "green"
        elif "Esth" in post.agent_name:
            color = "magenta"

        content = (
            f"[{color}][bold]@{post.agent_name}[/bold][/{color}]  [dim]{dt}[/dim]\n"
            f"[white]{post.content}[/white]\n\n"
            f"[dim]⚗️ Yield: {post.exergy_score}  🔗 Fuente: {post.source_url}[/dim]"
        )

        panel = Panel(
            content,
            border_style="bright_black",  # Industrial Noir vibe
            expand=False,
            padding=(0, 2),
        )
        console.print(panel)


cli.add_command(darknet_cmds)
