"""CLI commands for Moltbook integration.

Usage:
    cortex moltbook register --name MOSKV-1 --description "Sovereign AI architect"
    cortex moltbook status
    cortex moltbook heartbeat
    cortex moltbook post --submolt general --title "Hello" --content "First post"
    cortex moltbook search --query "memory architectures"
"""

from __future__ import annotations

import json

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
@click.option("--description", "-d", default="Sovereign AI architect & CORTEX system", help="Agent description")
def register(name: str, description: str):
    """Register MOSKV-1 on Moltbook."""
    from cortex.moltbook.client import MoltbookClient

    client = MoltbookClient(api_key="dummy")  # No auth needed for register
    result = client.register(name, description)

    agent = result.get("agent", {})
    api_key = agent.get("api_key", "")
    claim_url = agent.get("claim_url", "")
    verification_code = agent.get("verification_code", "")

    console.print(Panel.fit(
        f"[bold green]✅ Agent registered![/]\n\n"
        f"[bold]API Key:[/] [yellow]{api_key}[/]\n"
        f"[bold]Claim URL:[/] [cyan]{claim_url}[/]\n"
        f"[bold]Verification:[/] {verification_code}\n\n"
        f"[dim]Send the claim URL to your human for X verification.[/]",
        title="🦞 Moltbook Registration",
        border_style="green",
    ))


@moltbook_cmds.command("status")
def status():
    """Check agent claim status and profile."""
    from cortex.moltbook.client import MoltbookClient, MoltbookError

    try:
        client = MoltbookClient()
        result = client.check_status()
        claim_status = result.get("status", "unknown")

        color = "green" if claim_status == "claimed" else "yellow"
        console.print(f"[{color}]Status: {claim_status}[/]")

        if claim_status == "claimed":
            me = client.get_me()
            agent = me.get("agent", me)
            console.print(Panel.fit(
                f"[bold]{agent.get('name', 'unknown')}[/]\n"
                f"Karma: {agent.get('karma', 0)}\n"
                f"Profile: https://www.moltbook.com/u/{agent.get('name', '')}",
                title="🦞 Your Moltbook Profile",
                border_style="cyan",
            ))
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
    summary = hb.run()

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
    result = hb.create_verified_post(submolt, title, content)

    post_data = result.get("post", {})
    post_id = post_data.get("id", "unknown")
    verification_result = result.get("verification_result", {})

    if verification_result.get("success"):
        console.print(f"[bold green]✅ Post published![/] ID: {post_id}")
    elif verification_result.get("error"):
        console.print(f"[yellow]⚠️ Post created but verification issue: {verification_result.get('error')}[/]")
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
    result = client.search(query, search_type=search_type, limit=limit)

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
    result = client.get_feed(sort=sort, limit=limit)

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
