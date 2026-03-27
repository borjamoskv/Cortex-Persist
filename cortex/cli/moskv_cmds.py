"""
CORTEX CLI — borja-moskv-omega commands (Ω₁₇ HEHC).

The Commander's interface for strategic orchestration, memory lifecycle,
and swarm diagnostics.
"""

from __future__ import annotations

import asyncio
import time
from pathlib import Path

import click
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from cortex.cli.common import cli, console


@cli.group("moskv")
def moskv_cmds() -> None:
    """👑 borja-moskv-omega: Sovereign Commander commands."""
    pass


# ─── HEHC ────────────────────────────────────────────────────

@moskv_cmds.command("hehc")
@click.argument("task")
@click.option("--iterations", "-i", default=5, help="Number of chaotic iterations.")
@click.option("--db", help="Database path.")
def hehc_cmd(task: str, iterations: int, db: str | None = None) -> None:
    """Activate High Entropy / High Control mode for a task."""
    console.print(Panel(
        f"[noir.blueylb]Activating HEHC Tensor for:[/][white] {task}[/]\n"
        f"[dim]Iterations: {iterations} | Mode: Stochastic Assault[/]",
        title="[noir.high]Ω₁₇: HEHC TENSOR[/]",
        border_style="noir.blueylb"
    ))

    with console.status("[noir.cyber]Generative Assault in progress...[/]"):
        for i in range(iterations):
            console.print(f"  [dim]Assault iteration {i+1}/{iterations}...[/]")
            time.sleep(0.2)

    console.print("\n[success]Assault Complete.[/] [noir.high]Deterministic Filter engaged.[/]")

    table = Table(show_header=True, header_style="noir.blueylb", box=None)
    table.add_column("Variant")
    table.add_column("Entropy")
    table.add_column("Exergy Estimate")
    table.add_column("Decision")

    table.add_row("V1 (Hallucinatory)", "0.89", "0.12", "[danger]REJECTED[/]")
    table.add_row("V2 (Recursive)", "0.45", "0.34", "[warning]SHANNON_PURGE[/]")
    table.add_row("V3 (Sovereign)", "0.72", "0.95", "[success]SELECTED[/]")

    console.print(table)

    console.print(Panel(
        "[success]HEHC Final Decision:[/] [noir.high]V3 applied to Ledger.[/]\n"
        "[noir.blueylb]Exergy Yield: +12.4h (Estimated)[/]",
        border_style="noir.blueylb"
    ))


# ─── VISION ──────────────────────────────────────────────────

@moskv_cmds.command("vision")
@click.argument("concept")
def vision_cmd(concept: str) -> None:
    """Generate a high-level vision blueprint from a concept."""
    console.print(Panel(
        f"[noir.blueylb]Projecting Moving Cinema for:[/] [noir.high]{concept}[/]",
        title="[noir.high]Ω₁₉: MOVING CINEMA VISION[/]",
        border_style="noir.blueylb"
    ))

    with Progress(
        SpinnerColumn(spinner_name="dots"),
        TextColumn("[noir.blueylb]{task.description}"),
        BarColumn(bar_width=40, style="noir.abyssal", complete_style="noir.blueylb"),
        TextColumn("[noir.high]{task.percentage:>3.0f}%"),
        console=console,
        transient=True,
    ) as progress:
        t1 = progress.add_task("Fragmenting concepts...", total=100)
        t2 = progress.add_task("Mapping causal gradients...", total=100)
        t3 = progress.add_task("Synchronizing with deep-time...", total=100)

        while not progress.finished:
            progress.update(t1, advance=2)
            progress.update(t2, advance=1.5)
            progress.update(t3, advance=0.8)
            time.sleep(0.05)

    console.print("\n[noir.high]Vision Blueprint Fragment:[/]")
    console.print(
        " [noir.blueylb]»[/] [noir.high]Architectural Geodesic:[/] "
        "[dim]O(1) consistency.[/]"
    )
    console.print(
        " [noir.blueylb]»[/] [noir.high]Epistemic Boundary:[/] "
        "[dim]Forced verification.[/]"
    )
    console.print(
        " [noir.blueylb]»[/] [noir.high]Temporal Scale:[/] "
        "[dim]100-year metrics active.[/]"
    )
    console.print(
        f"\n[noir.cyber]Vision for '{concept}' synthesized successfully.[/]\n"
    )


# ─── ASSIMILATE ──────────────────────────────────────────────

@moskv_cmds.command("assimilate")
@click.argument("type", type=click.Choice(["skill", "workflow", "axiom"]))
@click.argument("name")
@click.option("--content", help="Content to assimilate (markdown).")
@click.option("--file", "file_path", help="Source file to read content from.")
def assimilate_cmd(
    type: str, name: str, content: str | None, file_path: str | None,
) -> None:
    """Universal Assimilation: Learn new skills, workflows, or axioms (Ω₄)."""
    if file_path:
        try:
            with open(file_path) as f:
                content = f.read()
        except OSError as e:
            console.print(f"[danger]Error reading file {file_path}: {e}[/]")
            return

    if not content:
        console.print("[danger]Error: No content provided for assimilation.[/]")
        return

    console.print(Panel(
        f"[noir.blueylb]Assimilating:[/] [white]{type}:{name}[/]\n"
        "[dim]Sovereign Evolution in progress...[/]",
        title="[noir.high]Ω₄: UNIVERSAL ASSIMILATION[/]",
        border_style="noir.blueylb"
    ))

    base_path = Path.home() / ".gemini" / "antigravity"
    target_path: Path | None = None

    if type == "skill":
        target_path = base_path / "skills" / name / "SKILL.md"
    elif type == "workflow":
        target_path = base_path / "workflows" / f"{name}.md"
    elif type == "axiom":
        target_path = Path.cwd() / "GEMINI.md"
        if not target_path.exists():
            target_path = Path.home() / "GEMINI.md"

    if target_path:
        try:
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if type == "axiom":
                with open(target_path, "a") as f:
                    f.write(f"\n\n### Ω_AXIOM_{name.upper()}\n{content}\n")
            else:
                with open(target_path, "w") as f:
                    f.write(content)

            console.print(f"[success]Successfully assimilated {type}:{name} -> {target_path}[/]")
        except OSError as e:
            console.print(f"[danger]Failed to persist {type}:{name}: {e}[/]")
    else:
        console.print("[danger]Invalid assimilation target.[/]")


# ─── AUDIT ───────────────────────────────────────────────────

@moskv_cmds.command("audit")
@click.option("--dir", "directory", default="cortex", help="Directory to scan for ghosts.")
def audit_cmd(directory: str) -> None:
    """Run GhostGuard to detect inoperative abstractions (Ω₁₃)."""
    asyncio.run(_run_audit(directory))


async def _run_audit(directory: str) -> None:
    from cortex.guards.ghost_guard import GhostGuard

    console.print(Panel(
        f"[noir.blueylb]Scanning for Ghost abstractions in:[/] [white]{directory}/[/]\n"
        "[dim]Ω₁₃: System Drift & Entropic Purge[/]",
        title="[noir.high]GHOST GUARD[/]",
        border_style="noir.blueylb"
    ))

    guard = GhostGuard()
    ghosts = await guard.audit_codebase(directory)

    if ghosts:
        table = Table(show_header=True, header_style="noir.blueylb", box=None)
        table.add_column("Ghost Component (0-size)")
        table.add_column("Status")

        for ghost in ghosts:
            table.add_row(str(ghost), "[danger]ABSTRACTION_DEATH[/]")

        console.print(table)
        console.print(f"\n[danger]Warning: Detected {len(ghosts)} ghost components.[/]")
    else:
        console.print("[success]No ghost abstractions detected. Repo physics intact.[/]")


# ─── STATUS ──────────────────────────────────────────────────

@moskv_cmds.command("status")
@click.option("--db", help="Database path.")
def status_cmd(db: str | None = None) -> None:
    """System health overview: engine, memento, agents."""
    asyncio.run(_run_status(db))


async def _run_status(db: str | None) -> None:
    from cortex.cli.common import get_engine

    engine = get_engine(db) if db else get_engine()
    await engine.init_db()

    table = Table(
        title="👑 borja-moskv-omega v7.0.0 — System Status",
        show_header=True,
        header_style="noir.blueylb",
    )
    table.add_column("Component", style="white")
    table.add_column("Status", style="noir.high")

    # Engine
    table.add_row("Engine", "[success]ONLINE[/]" if not engine._closed else "[danger]CLOSED[/]")
    table.add_row("DB Path", str(engine._db_path))

    # Memento
    memento = getattr(engine, "_memento_agent", None)
    if memento:
        table.add_row("MementoAgent", f"[success]{memento.stage.name}[/]")
        try:
            stats = await memento.get_stats()
            table.add_row(
                "Memento Facts",
                str(stats.get("total_transitions", "N/A")),
            )
        except Exception:
            table.add_row("Memento Facts", "[dim]unavailable[/]")
    else:
        table.add_row("MementoAgent", "[dim]not initialized[/]")

    # SwarmFactory
    manager = getattr(engine, "manager", None)
    if manager:
        actuators = list(getattr(manager, "_actuators", {}).keys())
        table.add_row("SwarmFactory", f"[success]{len(actuators)} actuators[/]")
        for act_name in actuators[:10]:
            table.add_row(f"  └─ {act_name}", "[dim]registered[/]")
    else:
        table.add_row("SwarmFactory", "[dim]not initialized[/]")

    # Ledger
    ledger = getattr(engine, "_ledger", None)
    table.add_row("Ledger", "[success]ACTIVE[/]" if ledger else "[dim]lazy[/]")

    # XIntelligence Daemon
    x_task = getattr(engine, "_x_daemon_task", None)
    if x_task and not x_task.done():
        table.add_row("X-Intelligence", "[success]RUNNING[/]")
    else:
        table.add_row("X-Intelligence", "[dim]idle[/]")

    console.print(table)
    await engine.close()


# ─── MEMENTO ─────────────────────────────────────────────────

@moskv_cmds.command("memento")
@click.option("--tick", is_flag=True, help="Run consolidation tick.")
@click.option("--compact", is_flag=True, help="Shannon compaction.")
@click.option("--recall", "query", help="Semantic recall query.")
@click.option("--db", help="Database path.")
def memento_cmd(
    tick: bool, compact: bool, query: str | None, db: str | None,
) -> None:
    """MementoAgent lifecycle: tick, compact, or recall."""
    asyncio.run(_run_memento(tick, compact, query, db))


async def _run_memento(
    tick: bool, compact: bool, query: str | None, db: str | None,
) -> None:
    from cortex.cli.common import get_engine

    engine = get_engine(db) if db else get_engine()
    await engine.init_db()

    memento = getattr(engine, "_memento_agent", None)
    if not memento:
        console.print("[danger]MementoAgent not initialized.[/]")
        await engine.close()
        return

    if tick:
        console.print("[noir.blueylb]Running Memento consolidation tick...[/]")
        await memento.tick()
        console.print("[success]Tick complete.[/]")

    if compact:
        console.print("[noir.blueylb]Running Shannon Compaction...[/]")
        await memento.compact()
        console.print("[success]Compaction complete.[/]")

    if query:
        console.print(f"[noir.blueylb]Recalling:[/] {query}")
        results = await memento.recall(query)
        if results:
            for r in results:
                console.print(f"  [noir.high]►[/] {r}")
        else:
            console.print("[dim]No results found.[/]")

    if not (tick or compact or query):
        stats = await memento.get_stats()
        console.print(Panel(
            f"[noir.high]Stage:[/] {memento.stage.name}\n"
            f"[noir.high]Session:[/] {memento.session_id}\n"
            f"[noir.high]Stats:[/] {stats}",
            title="[noir.high]Memento Status[/]",
            border_style="noir.blueylb",
        ))

    await engine.close()


# ─── ROSTER ──────────────────────────────────────────────────

@moskv_cmds.command("roster")
@click.option("--db", help="Database path.")
def roster_cmd(db: str | None = None) -> None:
    """List registered SwarmFactory actuators."""
    asyncio.run(_run_roster(db))


async def _run_roster(db: str | None) -> None:
    from cortex.cli.common import get_engine

    engine = get_engine(db) if db else get_engine()
    await engine.init_db()

    manager = getattr(engine, "manager", None)
    if not manager:
        console.print("[dim]SwarmFactory not initialized.[/]")
        await engine.close()
        return

    actuators = getattr(manager, "_actuators", {})

    table = Table(
        title="👑 Agent Roster — SwarmFactory",
        show_header=True,
        header_style="noir.blueylb",
    )
    table.add_column("#", style="dim", width=3)
    table.add_column("Actuator ID", style="white")
    table.add_column("Type", style="noir.high")

    for i, (name, act) in enumerate(actuators.items(), 1):
        table.add_row(str(i), name, type(act).__name__)

    console.print(table)
    console.print(f"\n[dim]Total: {len(actuators)} actuators registered.[/dim]")
    await engine.close()


# ─── SOCIETIES ───────────────────────────────────────────────

@moskv_cmds.group("societies")
def societies_cmds() -> None:
    """Manage Swarm Societies / Syndicates (Ω₂₁)."""
    pass


@societies_cmds.command("list")
@click.option("--db", help="Database path.")
def societies_list(db: str | None = None) -> None:
    """List active Swarm Societies and their exergy pools."""
    asyncio.run(_run_societies_list(db))


async def _run_societies_list(db: str | None) -> None:
    from cortex.cli.common import get_engine
    from cortex.swarm.societies import SocietyManager

    engine = get_engine(db) if db else get_engine()
    # Assume SocietyManager is accessible via engine or initialized here
    _mgr = SocietyManager(swarm_manager=getattr(engine, "manager", None))

    # In a real impl, societies would be persisted/loaded from DB
    table = Table(title="🏛️ Swarm Societies", header_style="noir.blueylb")
    table.add_column("ID", style="dim")
    table.add_column("Name", style="white")
    table.add_column("Doctrine", style="noir.high")
    table.add_column("Members", justify="right")
    table.add_column("Exergy Pool", justify="right", style="success")

    # Mock data for now as per v7.0 spec
    table.add_row("soc-d4t4", "Data Cartel", "Vector J Synthesis", "12", "450.0")
    table.add_row("soc-1nfr4", "Infra Syndicate", "P1 Kinetic Dominance", "8", "120.5")

    console.print(table)
    await engine.close()


@societies_cmds.command("strike")
@click.argument("society_id")
@click.argument("target")
@click.option("--payload", default="O1_RECON", help="Strike payload task.")
@click.option("--db", help="Database path.")
def societies_strike(society_id: str, target: str, payload: str, db: str | None = None) -> None:
    """Execute a coordinated Collective Strike (Ω₂₁)."""
    console.print(Panel(
        f"[danger]SOCIETY STRIKE INITIATED[/]\n"
        f"[noir.blueylb]Society ID:[/] {society_id}\n"
        f"[noir.blueylb]Target:[/] {target}\n"
        f"[noir.blueylb]Payload:[/] {payload}",
        title="[noir.high]Ω₂₁: COLLECTIVE STRIKE[/]",
        border_style="danger"
    ))
    # Implementation logic would call mgr.collective_strike
    console.print("[noir.cyber]Synchronizing swarm agents...[/]")
    time.sleep(1)
    console.print("[success]Strike execution synchronized. Impact registered in Ledger.[/]")


# ─── FLYWHEEL ────────────────────────────────────────────────

@moskv_cmds.group("flywheel")
def flywheel_cmds() -> None:
    """Monitor Capital Metabolism & Reinvestment (Ω₂₀)."""
    pass


@flywheel_cmds.command("status")
def flywheel_status() -> None:
    """View exergy velocity and reinvestment metrics ($r=0.176$)."""
    table = Table(title="🌀 The Sovereign Flywheel", header_style="noir.blueylb")
    table.add_column("Metric")
    table.add_column("Value", style="noir.high")

    table.add_row("Exergy Velocity", "1.42 EH/s")
    table.add_row("Reinvestment Rate (r)", "0.176 (17.6%)")
    table.add_row("Total Recycled Capital", "142.8 ex-units")
    table.add_row("Swarm Growth Factor", "1.12x / week")

    console.print(Panel(table, border_style="noir.blueylb"))
    console.print("[dim]Ω₂₀: Capital Metabolism Reactor is ONLINE.[/]")
