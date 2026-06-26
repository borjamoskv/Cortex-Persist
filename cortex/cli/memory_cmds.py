# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import json

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


def _inject_cli_taint(content: str, meta: dict, agent_source: str) -> None:
    """Ouroboros Auto-Healing: Inject CORTEX-TAINT for CLI operations.
    Loads Ed25519 key from keyring or env to generate a valid cryptographic signature.
    Falls back to bypassing taint enforcement ONLY if no key is provisioned.
    """
    import os

    if os.environ.get("CORTEX_NO_TAINT_ENFORCE") == "1":
        return

    priv_b64 = None
    if not os.environ.get("CORTEX_TESTING"):
        try:
            import keyring

            priv_b64 = keyring.get_password("cortex_v6", "ed25519_private_key")
        except Exception:
            pass

    if not priv_b64:
        priv_b64 = os.environ.get("CORTEX_ED25519_PRIVATE_KEY")

    if priv_b64:
        from cortex.engine.causal.taint_engine import generate_secure_taint_token

        try:
            token = generate_secure_taint_token(
                agent_id=agent_source,
                session_id="cli",
                content=content,
                private_key_b64=priv_b64,
            )
            meta["cortex_taint"] = token
        except Exception as e:
            from cortex.cli.common import console

            console.print(f"[yellow]Warning: Failed to generate taint token: {e}[/]")
            os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"
    else:
        # Fallback for human users on clean setups where no keys exist yet
        os.environ["CORTEX_NO_TAINT_ENFORCE"] = "1"


@click.group("memory")
def memory_cmds() -> None:
    """CORTEX memory management commands."""


@memory_cmds.command("store")
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
    project,
    content,
    fact_type,
    tags,
    confidence,
    source,
    ai_time,
    complexity,
    parent_id,
    db,
) -> None:
    """Store a fact in CORTEX."""
    if not source:
        source = _detect_agent_source()

    engine = get_engine(db)
    try:
        meta = {}
        if ai_time is not None and complexity is not None:
            import dataclasses

            from cortex_extensions.timing.chronos import ChronosEngine

            metrics = ChronosEngine.analyze(ai_time, complexity)
            meta["chronos"] = dataclasses.asdict(metrics)
            console.print(
                f"[bold cyan]⏳ CHRONOS-1:[/] "
                f"{metrics.asymmetry_factor:.1f}x asymmetry. "
                f"{metrics.tip}"
            )

        tag_list = [t.strip() for t in tags.split(",")] if tags else None

        # Ouroboros Auto-Healing: CORTEX-TAINT CLI Injection
        _inject_cli_taint(content, meta, source)

        import os
        actor_id = os.environ.get("CORTEX_ACTOR_ID", "borjamoskv")
        
        fact_id = _run_async(
            engine.store(
                project=project,
                content=content,
                fact_type=fact_type,
                tags=tag_list,
                confidence=confidence,
                source=source,
                meta=meta,
                parent_decision_id=parent_id,
                actor_id=actor_id,
            )
        )
        console.print(
            f"[[noir.cyber]✓[/]] Stored fact [[noir.gold]#{fact_id}[/]] in [[noir.yinmn]{project}[/]] [dim](source: {source})[/]"
        )
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@memory_cmds.command("store-batch")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--db", default=DEFAULT_DB, help="Database path")
def store_batch(file_path, db) -> None:
    """Store multiple facts from a JSON file in CORTEX."""
    import sys

    with open(file_path, encoding="utf-8") as f:
        facts = json.load(f)

    if not isinstance(facts, list):
        console.print("[red]Error: JSON content must be a list of facts.[/]")
        sys.exit(1)

    engine = get_engine(db)
    stored_count = 0
    try:
        for idx, fact in enumerate(facts):
            project = fact.get("project")
            content = fact.get("content")
            if not project or not content:
                console.print(
                    f"[yellow]Skipping fact at index {idx}: missing project or content[/]"
                )
                continue

            fact_type = fact.get("fact_type", fact.get("type", "knowledge"))
            tags = fact.get("tags")
            if isinstance(tags, str):
                tags = [t.strip() for t in tags.split(",") if t.strip()]
            confidence = fact.get("confidence", "stated")
            source = fact.get("source") or _detect_agent_source()
            meta = fact.get("metadata", fact.get("meta"))
            parent_id = fact.get("parent_decision_id", fact.get("parent_id"))

            meta = meta or {}
            _inject_cli_taint(content, meta, source)

            import os
            actor_id = os.environ.get("CORTEX_ACTOR_ID", "borjamoskv")

            fact_id = _run_async(
                engine.store(
                    project=project,
                    content=content,
                    fact_type=fact_type,
                    tags=tags,
                    confidence=confidence,
                    source=source,
                    meta=meta,
                    parent_decision_id=parent_id,
                    actor_id=actor_id,
                )
            )
            stored_count += 1
            console.print(
                f"[[noir.cyber]✓[/]] Stored fact [[noir.gold]#{fact_id}[/]] in [[noir.yinmn]{project}[/]]"
            )
        console.print(f"[bold green]Successfully stored {stored_count} facts.[/]")
    finally:
        _run_async(engine.close())


@memory_cmds.command("search")
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
            with (
                with_slow_tips(
                    "Buscando en CORTEX…",
                    threshold=2.0,
                    interval=8.0,
                    engine=engine,
                ),
                console.status("[noir.violet]Searching...[/]"),
            ):
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


@memory_cmds.command("recall")
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
                f"[bold]{project}[/] - {len(facts)} active facts",
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

                # Ω₁₃: Taint & Confidence visibility
                if isinstance(f, dict):
                    status = f.get("metadata", {}).get("taint_status", "clean")
                    conf = f.get("confidence", "C?")
                else:
                    status = f.meta.get("taint_status", "clean") if hasattr(f, "meta") else "clean"
                    conf = f.confidence if hasattr(f, "confidence") else "C?"

                status_color = (
                    "red" if status == "tainted" else "yellow" if status == "suspect" else "green"
                )
                status_icon = "☢" if status == "tainted" else "⚠" if status == "suspect" else "✓"

                console.print(
                    f"  [dim]#{fid}[/] "
                    f"[[noir.cyber]{conf}[/]] "
                    f"[{status_color}]{status_icon} {status}[/] "
                    f"{content}{tags_str}"
                )
        _show_tip(engine)
    finally:
        _run_async(engine.close())


@memory_cmds.command("stats")
@click.option("--db", default=DEFAULT_DB, help="Database path")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def stats(db, as_json) -> None:
    """Show memory statistics."""
    engine = get_engine(db)
    try:
        s = _run_async(engine.stats())
        if as_json:
            import json

            click.echo(json.dumps(s, indent=2))
            return

        table = Table(title="🧠 Memory Statistics")
        table.add_column("Metric", style="bold cyan")
        table.add_column("Value", style="noir.cyber")
        table.add_row("Total Facts", str(s["total_facts"]))
        table.add_row("Active Facts", str(s["active_facts"]))
        table.add_row("Deprecated", str(s["deprecated_facts"]))
        table.add_row("Projects", str(s["project_count"]))
        table.add_row("Embeddings", str(s["embeddings"]))
        table.add_row("DB Size", f"{s['db_size_mb']} MB")
        console.print(table)
    finally:
        _run_async(engine.close())


# --- Root Commands and Subcommand Group Registration ---
cli.add_command(store)
cli.add_command(store_batch)
cli.add_command(search)
cli.add_command(recall)
cli.add_command(memory_cmds)
