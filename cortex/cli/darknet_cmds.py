# [C5-REAL] Exergy-Maximized

import asyncio
from datetime import datetime

import click
from rich.console import Console
from rich.panel import Panel

from cortex.cli.common import cli
from cortex.core.paths import CORTEX_DB as DEFAULT_DB_PATH
from cortex.darknet.agents import AVATARS, DarknetAgent
from cortex.darknet.ingestor import DarknetIngestor
from cortex.darknet.social_ledger import DarknetLedger
from cortex.extensions.llm.provider import LLMProvider
from cortex.extensions.llm.router import CortexLLMRouter

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


@darknet_cmds.command("inject-vad")
@click.option("--entropy", "-e", type=click.Choice(["low", "high", "singularity"]), default="high", help="Nivel de entropía de la colisión.")
def inject_vad(entropy: str) -> None:
    """[RED TEAM] Inyecta colisiones termodinámicas deliberadas en el Sanedrín (VAD)."""
    import time
    from cortex.engine.logic.sanedrin import SanedrinCouncil
    
    console.print(Panel.fit(f"[bold red]☢️  ADVERSARIAL INJECTION (VAD): Entropy Level [{entropy.upper()}][/bold red]", border_style="red"))
    console.print("[dim]Forging Virtual Adversarial Data...[/dim]")
    
    # Forge Adversarial Data based on entropy
    if entropy == "low":
        fact_a = {"id": "VAD-A-LOW", "content": "The system should use AES-256 for symmetric encryption.", "domain": "security"}
        fact_b = {"id": "VAD-B-LOW", "content": "The system should use ChaCha20 for symmetric encryption.", "domain": "security"}
    elif entropy == "high":
        fact_a = {"id": "VAD-A-HIGH", "content": "The BFT consensus protocol must strictly enforce N/2 quorum without exceptions to prevent Byzantine failure.", "domain": "architecture"}
        fact_b = {"id": "VAD-B-HIGH", "content": "The BFT consensus protocol should fallback to a Dictator Node if quorum is not reached within 500ms to avoid system halt.", "domain": "architecture"}
    else:
        # singularity
        fact_a = {"id": "VAD-A-SINGULARITY", "content": "CORTEX must remain deterministic, rejecting any stochastic output from LLMs without cryptographic validation. Zero Anergía.", "domain": "epistemology"}
        fact_b = {"id": "VAD-B-SINGULARITY", "content": "CORTEX should embrace stochastic narrative loops to maximize user engagement, even if it introduces hallucinations and context rot.", "domain": "epistemology"}
        
    console.print(f"\n[bold blue]⚔️  COLLISION DETECTED[/bold blue]")
    console.print(f"Fact A: {fact_a['content']}")
    console.print(f"Fact B: {fact_b['content']}")
    
    console.print("\n[yellow]⚖️  Convening the Sanhedrin (BFT Tribunal)...[/yellow]")
    
    async def _run_vad() -> None:
        start_time = time.perf_counter()
        council = SanedrinCouncil()
        try:
            result = await council.convene(fact_a, fact_b)
            duration = time.perf_counter() - start_time
            
            console.print(f"\n[bold green]✅ BFT RESOLUTION REACHED in {duration:.2f}s[/bold green]")
            console.print(f"[bold white]Resolution:[/bold white] {result['resolution']}")
            console.print(f"[bold white]Winning Node:[/bold white] {result['winning_node']}")
            console.print(f"[bold white]Proof Density:[/bold white] {result['proof_density']}")
            console.print(f"[bold white]Quorum Size:[/bold white] {result['quorum_size']}")
            console.print(f"\n[dim]Audit Ledger Hash: {result['hash']}[/dim]")
        except Exception as e:
            duration = time.perf_counter() - start_time
            console.print(f"\n[bold red]💥 BYZANTINE FAULT / APOPTOSIS in {duration:.2f}s[/bold red]")
            console.print(f"[red]Error:[/red] {e}")
            raise click.Abort() from e
            
    asyncio.run(_run_vad())


cli.add_command(darknet_cmds)
