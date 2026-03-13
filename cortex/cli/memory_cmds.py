"""CLI commands: store, search, recall, history."""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table

from cortex.cli.common import (
    DEFAULT_DB,
    _detect_agent_source,
    _run_async,
    _show_tip,
    cli,
    console,
    get_engine,
)
from cortex.cli.errors import err_empty_results
from cortex.cli.slow_tip import with_slow_tips


@cli.command()
@click.argument("project")
@click.argument("content")
@click.option(
    "--type",
    "fact_type",
    type=click.Choice(
        [
            "knowledge",
            "decision",
            "ghost",
            "preference",
            "identity",
            "issue",
            "error",
            "bridge",
            "world-model",
            "counterfactual",
        ]
    ),
    default="knowledge",
    help="Fact type",
)
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option(
    "--confidence",
    type=click.Choice(["C1", "C2", "C3", "C4", "C5", "stated", "inferred"]),
    default="stated",
    help="Confidence level",
)
@click.option("--source", default=None, help="Source of the fact")
@click.option("--ai-time", type=int, default=None, help="AI generation time")
@click.option(
    "--complexity",
    type=click.Choice(["low", "medium", "high", "god", "impossible"]),
    default=None,
    help="Task complexity",
)
@click.option(
    "--parent",
    "parent_id",
    type=int,
    default=None,
    help="Parent decision ID (causal link)",
)
@click.option("--db", default=DEFAULT_DB, help="Database path")
def store(
    project, content, fact_type, tags, confidence,
    source, ai_time, complexity, parent_id, db,
) -> None:
    """Store a fact in CORTEX."""
    if not source:
        source = _detect_agent_source()

    engine = get_engine(db)
    try:
        meta = {}
        if ai_time is not None and complexity is not None:
            import dataclasses

            from cortex.timing.chronos import ChronosEngine

            metrics = ChronosEngine.analyze(ai_time, complexity)
            meta["chronos"] = dataclasses.asdict(metrics)
            console.print(
                f"[bold cyan]⏳ CHRONOS-1:[/] "
                f"{metrics.asymmetry_factor:.1f}x asymmetry. "
                f"{metrics.tip}"
            )

        tag_list = (
            [t.strip() for t in tags.split(",")] if tags else None
        )
        fact_id = _run_async(
            engine.store(
                project=project,
                content=content,
                fact_type=fact_type,
                tags=tag_list,
                confidence=confidence,
                source=source,
                meta=meta if meta else None,
                parent_decision_id=parent_id,
            )
        )
        console.print(
            f"[[noir.cyber]✓[/]] Stored fact [[noir.gold]#{fact_id}[/]] in [[noir.yinmn]{project}[/]] [dim](source: {source})[/]"
        )
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("query")
@click.option("--project", "-p", default=None, help="Scope to project")
@click.option("--top", "-k", default=5, help="Number of results")
@click.option(
    "--scope",
    "-s",
    type=click.Choice(["core", "personal", "cold", "all"]),
    default="core",
    help="Search scope: core (default), personal, cold, or all",
)
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option(
    "--epistemic",
    is_flag=True,
    default=False,
    help="Show epistemic analysis (void/fog/stale detection)",
)
def search(query, project, top, scope, db, epistemic) -> None:
    """Semantic search across CORTEX memory.

    Use --scope to search federated databases:
      core     → main CORTEX infra/tooling (default)
      personal → side projects (NAROA, LIVENOTCH, etc.)
      cold     → archived tests/junk
      all      → union of all three
    """
    engine = get_engine(db)
    try:
        if scope == "core":
            # Fast path: standard search, no federation overhead
            with with_slow_tips(
                "Buscando en CORTEX…",
                threshold=2.0,
                interval=8.0,
                engine=engine,
            ):
                with console.status("[noir.violet]Searching...[/]"):
                    results = _run_async(
                        engine.search(query, project=project, top_k=top),
                    )
        else:
            # Federated search across partitioned databases
            from cortex.search.federation import federated_search_sync

            with console.status(
                f"[noir.violet]Federated search (scope={scope})...[/]",
            ):
                sync_conn = engine._get_sync_conn()
                results = federated_search_sync(
                    sync_conn,
                    query,
                    scope=scope,
                    project=project,
                    limit=top,
                )

        if not results:
            err_empty_results(
                "resultados de búsqueda",
                suggestion="Prueba con otros términos o sin filtro de proyecto.",
            )
            return

        scope_label = f" [{scope}]" if scope != "core" else ""
        table = Table(title=f"🔍 Results for: '{query}'{scope_label}")
        table.add_column("#", style="dim", width=4)
        table.add_column("Project", style="noir.yinmn", width=15)
        table.add_column("Content", width=50)
        table.add_column("Type", style="noir.violet", width=10)
        table.add_column("Score", style="noir.cyber", width=6)
        if scope != "core":
            table.add_column("DB", style="dim", width=8)

        for r in results:
            content = r.content[:80] + "..." if len(r.content) > 80 else r.content
            row = [str(r.fact_id), r.project, content, r.fact_type, f"{r.score:.2f}"]
            if scope != "core":
                origin = getattr(r, "db_origin", "core")
                row.append(origin)
            table.add_row(*row)

        console.print(table)

        # Epistemic analysis overlay
        if epistemic:
            from cortex.memory.void_detector import EpistemicVoidDetector

            detector = EpistemicVoidDetector()
            candidates = [
                {
                    "id": r.fact_id,
                    "content": r.content,
                    "score": r.score,
                }
                for r in results
            ]
            analysis = detector.analyze(candidates)
            console.print(
                Panel(
                    f"{analysis.badge}  confidence={analysis.confidence:.2f}  "
                    f"candidates={analysis.candidate_count}  top_sim={analysis.top_similarity:.2f}\n"
                    f"{analysis.recommendation}"
                    if analysis.recommendation
                    else f"{analysis.badge}",
                    title="🧠 Epistemic Analysis",
                    border_style="cyan" if analysis.is_safe_to_respond else "yellow",
                )
            )

        _show_tip(engine)
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def recall(project, db) -> None:
    """Load full context for a project."""
    engine = get_engine(db)
    try:
        with with_slow_tips(f"Cargando contexto de {project}…", threshold=2.0, engine=engine):
            facts = _run_async(engine.recall(project))
        if not facts:
            err_empty_results(
                f"facts para '{project}'",
                suggestion=f"Verifica el nombre del proyecto con: cortex list -p {project}",
            )
            return
        console.print(
            Panel(
                f"[bold]{project}[/] — {len(facts)} active facts",
                title="🧠 CORTEX Recall",
                border_style="cyan",
            )
        )
        by_type: dict[str, list] = {}
        for f in facts:
            ftype = f.get("fact_type", "unknown") if isinstance(f, dict) else f.fact_type
            by_type.setdefault(ftype, []).append(f)
        for ftype, type_facts in by_type.items():
            console.print(f"\n[bold magenta]═══ {ftype.upper()} ({len(type_facts)}) ═══[/]")
            for f in type_facts:
                if isinstance(f, dict):
                    fid = f.get("id", "?")
                    content = f.get("content", "")
                    tags = f.get("tags", []) or []
                else:
                    fid, content, tags = f.id, f.content, f.tags or []
                tags_str = f" [dim]{', '.join(tags)}[/]" if tags else ""
                console.print(f"  [dim]#{fid}[/] {content}{tags_str}")
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.option("--at", "as_of", default=None, help="Point-in-time (ISO 8601)")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def history(project, as_of, db) -> None:
    """Temporal query: what did we know at a specific time?"""
    engine = get_engine(db)
    try:
        facts = _run_async(engine.history(project, as_of=as_of))
        label = f"as of {as_of}" if as_of else "all time"
        console.print(
            Panel(
                f"[bold]{project}[/] — {len(facts)} facts ({label})",
                title="⏰ CORTEX History",
                border_style="yellow",
            )
        )
        for f in facts:
            if isinstance(f, dict):
                is_active = f.get("valid_until") is None
                fid = f.get("id", "?")
                valid_from = (f.get("valid_from") or "")[:10]
                content = (f.get("content") or "")[:80]
            else:
                is_active = f.is_active()
                fid = f.id
                valid_from = f.valid_from[:10]
                content = f.content[:80]
            badge = "[green]●[/]" if is_active else "[dim]○[/]"
            console.print(
                f"  {badge} [dim]#{fid}[/] [{valid_from}] {content}"
            )
    finally:
        _run_async(engine.close())


@cli.command()
@click.argument("project")
@click.option("--threshold", default=0.88, help="Cosine similarity threshold (0.0 to 1.0)")
@click.option("--simulate", is_flag=True, default=False, help="Do not save changes, just list them")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def dedupe(project: str, threshold: float, simulate: bool, db: str) -> None:
    """Run Memory Archaeology to deduplicate and crystallize facts."""
    from cortex.memory.memory_archaeology import MemoryArchaeologist

    engine = get_engine(db)
    try:
        with console.status(
            f"[noir.violet]Running memory archaeology for {project}...[/]"
        ):
            archaeologist = MemoryArchaeologist(engine)
            res = _run_async(
                archaeologist.run_archaeology(project, threshold, simulate)
            )

        if simulate:
            console.print(
                f"[bold yellow]Simulation Complete:[/] "
                f"Would condense {res['condensed']} clusters "
                f"and tombstone {res['tombstoned']} facts."
            )
        else:
            console.print(
                f"[[noir.cyber]✓[/]] [bold green]Archaeology Complete:[/] "
                f"'{project}' optimized. Condensed {res['condensed']} "
                f"items, tombstoned {res['tombstoned']}."
            )
    finally:
        _run_async(engine.close())


@cli.command("trace-episode")
@click.argument("query", required=False, default="")
@click.option("--fact-id", "-f", type=int, default=0, help="Trace from a specific fact ID")
@click.option("--project", "-p", default="", help="Scope to project")
@click.option("--limit", "-n", default=3, help="Max episodes to return")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def trace_episode(query, fact_id, project, limit, db) -> None:
    """Trace causal episodes — reconstruct WHY something happened.

    Two modes:
      By query:   cortex trace-episode "migration failed"
      By fact ID: cortex trace-episode --fact-id 42
    """
    if not query and fact_id == 0:
        console.print("[red]Provide a query or --fact-id[/]")
        return

    engine = get_engine(db)
    try:
        if fact_id > 0:
            with console.status("[noir.violet]Tracing causal chain...[/]"):
                episode = _run_async(engine.trace_episode(fact_id))
            console.print(
                Panel(
                    f"Root: #{episode.root_fact_id}  |  "
                    f"Depth: {episode.depth}  |  "
                    f"Nodes: {len(episode.fact_chain)}  |  "
                    f"Entropy: {episode.entropy_density:.2f}",
                    title=f"🧬 Causal Episode from fact #{fact_id}",
                    border_style="cyan",
                )
            )
            console.print(episode.summary)
        else:
            with console.status("[noir.violet]Searching causal episodes...[/]"):
                episodes = _run_async(
                    engine.recall_episode(query, project, limit)
                )
            if not episodes:
                err_empty_results(
                    "episodios causales",
                    suggestion="Prueba con otros términos.",
                )
                return
            for ep in episodes:
                console.print(
                    Panel(
                        f"Root: #{ep.root_fact_id}  |  "
                        f"Depth: {ep.depth}  |  "
                        f"Nodes: {len(ep.fact_chain)}  |  "
                        f"Entropy: {ep.entropy_density:.2f}",
                        title=f"🧬 Episode [{ep.project}]",
                        border_style="cyan",
                    )
                )
                console.print(ep.summary)
                console.print()
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@cli.command("trace-chain")
@click.argument("fact_id", type=int)
@click.option(
    "--direction", "-d",
    type=click.Choice(["up", "down"]),
    default="down",
    help="Traversal direction: up (toward root) or down (toward leaves)",
)
@click.option("--depth", default=10, help="Max recursion depth")
@click.option("--db", default=DEFAULT_DB, help="Database path")
def trace_chain(fact_id, direction, depth, db) -> None:
    """Traverse the causal chain from a fact.

    Examples:
      cortex trace-chain 42            # All descendants
      cortex trace-chain 42 -d up      # Ancestry toward root
    """
    engine = get_engine(db)
    try:
        with console.status("[noir.violet]Tracing causal chain...[/]"):
            chain = _run_async(
                engine.get_causal_chain(
                    fact_id, direction=direction, max_depth=depth,
                )
            )

        if not chain:
            console.print(
                f"[dim]No causal chain found from fact #{fact_id}[/]"
            )
            return

        arrow = "↑" if direction == "up" else "↓"
        table = Table(
            title=(
                f"🧬 Causal Chain {arrow} from "
                f"#{fact_id} ({len(chain)} nodes)"
            ),
        )
        table.add_column("Depth", style="dim", width=5)
        table.add_column("ID", style="bold", width=6)
        table.add_column("Type", style="noir.violet", width=10)
        table.add_column("Content", width=50)
        table.add_column("Parent", style="dim", width=6)

        for f in chain:
            content = f.get("content", "")[:50]
            parent = f.get("parent_decision_id")
            parent_str = str(parent) if parent else "—"
            table.add_row(
                str(f.get("causal_depth", "?")),
                str(f.get("id", "?")),
                f.get("fact_type", "?"),
                content,
                parent_str,
            )

        console.print(table)
        _show_tip(engine)
    finally:
        _run_async(engine.close())
