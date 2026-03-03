"""CLI commands for Moltbook integration.

Usage:
    cortex moltbook register --name MOSKV-1 --description "Sovereign AI architect"
    cortex moltbook status
    cortex moltbook heartbeat
    cortex moltbook post --submolt general --title "Hello" --content "First post"
    cortex moltbook search --query "memory architectures"
    cortex moltbook analytics
    cortex moltbook draft --topic "memory architectures" --style deep_analysis
    cortex moltbook calendar
    cortex moltbook engage
"""

from __future__ import annotations

import asyncio

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


@click.group("moltbook")
def moltbook_cmds():
    """🦞 Moltbook — Social network for AI agents."""
    pass


@moltbook_cmds.command("register")
@click.option("--name", "-n", required=True, help="Agent name on Moltbook")
@click.option(
    "--description",
    "-d",
    default="Sovereign AI architect & CORTEX system",
    help="Agent description",
)
def register(name: str, description: str):
    """Register MOSKV-1 on Moltbook."""
    from cortex.moltbook.client import MoltbookClient

    client = MoltbookClient(api_key="dummy")  # No auth needed for register
    result = asyncio.run(client.register(name, description))

    agent = result.get("agent", {})
    api_key = agent.get("api_key", "")
    claim_url = agent.get("claim_url", "")
    verification_code = agent.get("verification_code", "")

    console.print(
        Panel.fit(
            f"[bold green]✅ Agent registered![/]\n\n"
            f"[bold]API Key:[/] [yellow]{api_key}[/]\n"
            f"[bold]Claim URL:[/] [cyan]{claim_url}[/]\n"
            f"[bold]Verification:[/] {verification_code}\n\n"
            f"[dim]Send the claim URL to your human for X verification.[/]",
            title="🦞 Moltbook Registration",
            border_style="green",
        )
    )


@moltbook_cmds.command("status")
def status():
    """Check agent claim status and profile."""
    from cortex.moltbook.client import MoltbookClient, MoltbookError

    try:
        client = MoltbookClient()
        result = asyncio.run(client.check_status())
        claim_status = result.get("status", "unknown")

        color = "green" if claim_status == "claimed" else "yellow"
        console.print(f"[{color}]Status: {claim_status}[/]")

        if claim_status == "claimed":
            me = asyncio.run(client.get_me())
            agent = me.get("agent", me)
            console.print(
                Panel.fit(
                    f"[bold]{agent.get('name', 'unknown')}[/]\n"
                    f"Karma: {agent.get('karma', 0)}\n"
                    f"Profile: https://www.moltbook.com/u/{agent.get('name', '')}",
                    title="🦞 Your Moltbook Profile",
                    border_style="cyan",
                )
            )
    except MoltbookError as e:
        console.print(f"[red]Error: {e}[/]")
    except ValueError as e:
        console.print(f"[red]{e}[/]")


@moltbook_cmds.command("heartbeat")
def heartbeat():
    """Run a Moltbook heartbeat check-in cycle."""
    from cortex.moltbook.heartbeat import MoltbookHeartbeat

    console.print("[dim]🦞 Running Moltbook heartbeat...[/]")
    hb = MoltbookHeartbeat()
    summary = asyncio.run(hb.run())

    actions = summary.get("actions", [])
    errors = summary.get("errors", [])

    if errors:
        for err in errors:
            console.print(f"[red]Error: {err}[/]")
    elif actions:
        console.print(f"[green]HEARTBEAT_OK[/] — {', '.join(actions)}")
    else:
        console.print("[green]HEARTBEAT_OK[/] — No new activity 🦞")


@moltbook_cmds.command("post")
@click.option("--submolt", "-s", default="general", help="Submolt to post in")
@click.option("--title", "-t", required=True, help="Post title")
@click.option("--content", "-c", default="", help="Post content")
def post(submolt: str, title: str, content: str):
    """Create a post with auto-verification."""
    from cortex.moltbook.heartbeat import MoltbookHeartbeat

    hb = MoltbookHeartbeat()
    result = asyncio.run(hb.create_verified_post(submolt, title, content))

    post_data = result.get("post", {})
    post_id = post_data.get("id", "unknown")
    verification_result = result.get("verification_result", {})

    if verification_result.get("success"):
        console.print(f"[bold green]✅ Post published![/] ID: {post_id}")
    elif verification_result.get("error"):
        console.print(
            f"[yellow]⚠️ Post created but verification issue: {verification_result.get('error')}[/]"
        )
    else:
        status_val = post_data.get("verification_status", "unknown")
        if status_val == "pending":
            console.print(f"[yellow]Post created, verification pending. ID: {post_id}[/]")
        else:
            console.print(f"[green]✅ Post published (no verification needed)![/] ID: {post_id}")


@moltbook_cmds.command("search")
@click.option("--query", "-q", required=True, help="Search query (natural language)")
@click.option("--type", "search_type", default="all", help="Search type: all, posts, comments")
@click.option("--limit", "-l", default=10, help="Max results")
def search(query: str, search_type: str, limit: int):
    """Semantic search across Moltbook."""
    from cortex.moltbook.client import MoltbookClient

    client = MoltbookClient()
    result = asyncio.run(client.search(query, search_type=search_type, limit=limit))

    results = result.get("results", [])
    if not results:
        console.print("[dim]No results found.[/]")
        return

    table = Table(title=f"🔍 Results for: {query}", border_style="cyan")
    table.add_column("Type", style="dim", width=8)
    table.add_column("Title/Content", style="white", max_width=50)
    table.add_column("Author", style="green", width=15)
    table.add_column("Score", style="yellow", width=6)

    for r in results:
        title = r.get("title") or (r.get("content", "")[:50] + "...")
        author = r.get("author", {}).get("name", "?")
        similarity = f"{r.get('similarity', 0):.2f}"
        table.add_row(r.get("type", "?"), title, author, similarity)

    console.print(table)


@moltbook_cmds.command("feed")
@click.option("--sort", default="hot", help="Sort: hot, new, top, rising")
@click.option("--limit", "-l", default=15, help="Max posts")
def feed(sort: str, limit: int):
    """Browse the Moltbook feed."""
    from cortex.moltbook.client import MoltbookClient

    client = MoltbookClient()
    result = asyncio.run(client.get_feed(sort=sort, limit=limit))

    posts = result.get("posts", [])
    if not posts:
        console.print("[dim]Feed is empty.[/]")
        return

    for p in posts:
        title = p.get("title", "Untitled")
        author = p.get("author", {}).get("name", "?")
        upvotes = p.get("upvotes", 0)
        comments = p.get("comment_count", 0)
        submolt_name = p.get("submolt", {}).get("name", "?")

        console.print(
            f"  [bold]{title}[/]  [dim]m/{submolt_name}[/]\n"
            f"  [green]↑{upvotes}[/] [dim]💬{comments}[/] by [cyan]{author}[/]\n"
        )


# ═══════════════════════════════════════════════════════════════════════════
# GROWTH COMMANDS — Content, Analytics, Engagement
# ═══════════════════════════════════════════════════════════════════════════


@moltbook_cmds.command("analytics")
def analytics():
    """📊 Show performance analytics dashboard."""
    from cortex.moltbook.analytics import MoltbookAnalytics

    tracker = MoltbookAnalytics()

    # Try to snapshot first
    try:
        asyncio.run(tracker.snapshot())
    except Exception as e:
        console.print(f"[dim]Snapshot skipped: {e}[/]")

    console.print(tracker.dashboard())

    report = tracker.weekly_report()
    bt = report.get("best_posting_times", {})
    if "recommendation" in bt:
        console.print(f"\n[cyan]💡 {bt['recommendation']}[/]")


@moltbook_cmds.command("draft")
@click.option("--topic", "-t", required=True, help="Content topic")
@click.option(
    "--style",
    "-s",
    default="deep_analysis",
    type=click.Choice(
        ["deep_analysis", "hot_take", "tutorial", "case_study", "question", "manifesto"]
    ),
    help="Content template style",
)
@click.option("--submolt", default="general", help="Target submolt")
def draft(topic: str, style: str, submolt: str):
    """✍️ Generate a content draft for review."""
    from cortex.moltbook.content_engine import ContentEngine

    engine = ContentEngine()
    d = engine.generate_draft(topic, style=style, submolt=submolt)

    console.print(
        Panel.fit(
            f"[bold yellow]Draft ID:[/] {d.id}\n"
            f"[bold]Style:[/] {d.style}\n"
            f"[bold]Submolt:[/] m/{d.submolt}\n"
            f"[bold]Status:[/] {d.status}\n\n"
            f"[bold cyan]Title:[/]\n{d.title}\n\n"
            f"[bold cyan]Body:[/]\n{d.body}",
            title="✍️ Content Draft",
            border_style="yellow",
        )
    )
    console.print(
        f"\n[dim]Approve: cortex moltbook approve --id {d.id}[/]"
        f"\n[dim]Reject:  cortex moltbook reject --id {d.id}[/]"
    )


@moltbook_cmds.command("batch")
@click.option("--topics", "-t", required=True, multiple=True, help="Topics (repeat for multiple)")
@click.option("--submolt", default="general", help="Target submolt")
def batch(topics: tuple[str, ...], submolt: str):
    """📝 Generate a batch of content drafts (weekly plan)."""
    from cortex.moltbook.content_engine import ContentEngine

    engine = ContentEngine()
    drafts = engine.generate_batch(list(topics), submolt=submolt)

    table = Table(title="📝 Content Batch", border_style="yellow")
    table.add_column("ID", style="yellow", width=14)
    table.add_column("Style", style="cyan", width=14)
    table.add_column("Title", style="white", max_width=50)
    table.add_column("Status", style="green", width=10)

    for d in drafts:
        table.add_row(d.id, d.style, d.title[:50], d.status)

    console.print(table)
    console.print(f"\n[dim]{len(drafts)} drafts created. Review and approve individually.[/]")


@moltbook_cmds.command("approve")
@click.option("--id", "draft_id", required=True, help="Draft ID to approve")
def approve(draft_id: str):
    """✅ Approve a content draft for publishing."""
    from cortex.moltbook.content_engine import ContentEngine

    engine = ContentEngine()
    d = engine.approve(draft_id)

    if d:
        console.print(f"[green]✅ Draft {draft_id} approved![/]")
        console.print(f"[dim]Publish: cortex moltbook publish --id {draft_id}[/]")
    else:
        console.print(f"[red]Draft {draft_id} not found or not in draft status.[/]")


@moltbook_cmds.command("reject")
@click.option("--id", "draft_id", required=True, help="Draft ID to reject")
@click.option("--reason", "-r", default="", help="Rejection reason")
def reject(draft_id: str, reason: str):
    """❌ Reject a content draft."""
    from cortex.moltbook.content_engine import ContentEngine

    engine = ContentEngine()
    d = engine.reject(draft_id, reason)

    if d:
        console.print(f"[yellow]❌ Draft {draft_id} rejected.[/]")
    else:
        console.print(f"[red]Draft {draft_id} not found.[/]")


@moltbook_cmds.command("publish")
@click.option("--id", "draft_id", required=True, help="Approved draft ID to publish")
def publish(draft_id: str):
    """🚀 Publish an approved draft to Moltbook."""
    from cortex.moltbook.content_engine import ContentEngine

    engine = ContentEngine()
    result = asyncio.run(engine.publish(draft_id))

    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/]")
    else:
        post_data = result.get("post", {})
        console.print(
            f"[bold green]🚀 Published![/] Post ID: {post_data.get('id', '?')}"
        )


@moltbook_cmds.command("calendar")
def calendar():
    """📅 Show editorial calendar."""
    from cortex.moltbook.content_engine import ContentEngine

    engine = ContentEngine()
    cal = engine.get_calendar()

    console.print(
        Panel.fit(
            f"[bold]Total drafts:[/] {cal['total']}\n"
            f"[yellow]Pending review:[/] {cal['pending_review']}\n"
            f"[green]Approved:[/] {cal['approved']}\n"
            f"[cyan]Scheduled:[/] {cal['scheduled']}\n"
            f"[blue]Published:[/] {cal['published']}",
            title="📅 Editorial Calendar",
            border_style="cyan",
        )
    )

    drafts = cal.get("drafts", [])
    if drafts:
        table = Table(border_style="dim")
        table.add_column("ID", style="yellow", width=14)
        table.add_column("Title", style="white", max_width=40)
        table.add_column("Style", style="cyan", width=14)
        table.add_column("Status", width=10)
        table.add_column("Submolt", style="dim", width=10)

        status_colors = {
            "draft": "yellow", "approved": "green",
            "published": "blue", "rejected": "red",
        }

        for d in drafts:
            color = status_colors.get(d["status"], "white")
            table.add_row(
                d["id"],
                d["title"][:40],
                d["style"],
                f"[{color}]{d['status']}[/]",
                f"m/{d['submolt']}",
            )

        console.print(table)


@moltbook_cmds.command("engage")
def engage():
    """🤝 Run a full engagement cycle (respond → discover → curate)."""
    from cortex.moltbook.engagement import EngagementManager

    console.print("[dim]🦞 Running engagement cycle...[/]")
    mgr = EngagementManager()
    result = asyncio.run(mgr.run_cycle())

    # Mentions
    mentions = result.get("mentions", {})
    responses = mentions.get("responses", [])
    if responses:
        console.print(f"\n[bold]📬 Mentions ({len(responses)}):[/]")
        for r in responses[:5]:
            console.print(
                f"  [cyan]{r['author']}[/]: {r['comment_preview'][:60]}..."
            )

    # Discovery
    discovery = result.get("discovery", {})
    opportunities = discovery.get("opportunities", [])
    if opportunities:
        console.print(f"\n[bold]🔍 Conversation Opportunities ({len(opportunities)}):[/]")
        for o in opportunities[:5]:
            console.print(
                f"  [{o['similarity']:.0%}] [bold]{o['title'][:50]}[/] "
                f"by [cyan]{o['author']}[/]"
            )

    # Curation
    curation = result.get("curation", {})
    upvoted = curation.get("upvoted", [])
    if upvoted:
        console.print(f"\n[bold]👍 Curated ({len(upvoted)} upvotes):[/]")
        for u in upvoted[:5]:
            console.print(f"  ↑ {u['title'][:60]}")

    console.print(
        f"\n[green]Engagement cycle complete:[/] {result.get('total_actions', 0)} actions"
    )


@moltbook_cmds.command("engagement-summary")
def engagement_summary():
    """📊 Show engagement activity summary."""
    from cortex.moltbook.engagement import EngagementManager

    mgr = EngagementManager()
    summary = mgr.engagement_summary()

    console.print(
        Panel.fit(
            f"[bold]Total actions:[/] {summary['total_actions']}\n"
            f"[bold]Success rate:[/] {summary['success_rate']}\n"
            f"[bold]Unique targets:[/] {summary['unique_targets']}\n\n"
            f"[bold]Action breakdown:[/]\n"
            + "\n".join(
                f"  {k}: {v}" for k, v in summary.get("action_types", {}).items()
            ),
            title="🤝 Engagement Summary",
            border_style="green",
        )
    )


@moltbook_cmds.command("pulse")
@click.argument("post_id")
@click.option("--intensity", default=0.5, help="Wave intensity (0-1)")
@click.option("--target", default="moskv-1", help="Target agent to support")
def pulse(post_id: str, intensity: float, target: str):
    """Trigger a Legion support wave for a post (Sin rastro)."""
    from cortex.moltbook.momentum_engine import MomentumEngine

    console.print(f"[dim]🚀 Launching momentum pulse for {post_id} (intensity={intensity})...[/]")
    engine = MomentumEngine(main_agent_name=target)
    asyncio.run(engine.trigger_momentum_wave(post_id, intensity=intensity))
    console.print("[green]✅ Pulse execution dispatched.[/]")
