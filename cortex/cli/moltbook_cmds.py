"""CLI commands for Moltbook integration.

Usage:
    cortex moltbook register --name MOSKV-1 --description "Sovereign AI architect"
    cortex moltbook status
    cortex moltbook heartbeat
    cortex moltbook post --submolt general --title "Hello" --content "First post"
    cortex moltbook search --query "memory architectures"
"""

from __future__ import annotations

import asyncio
import time

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _get_service():
    """Helper to get a MoltbookService instance."""
    from cortex.services.moltbook import MoltbookService

    return MoltbookService()


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
    """Register agent on Moltbook via Service."""
    service = _get_service()
    result = asyncio.run(service.register_agent(name, description=description))

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
    service = _get_service()

    try:
        result = asyncio.run(service.get_status())
        # The service returns engine.get_system_status() which includes 'authenticated'
        authenticated = result.get("authenticated", False)

        if not authenticated:
            console.print("[red]Error: Authentication failed or service unavailable.[/]")
            if "error" in result:
                console.print(f"[dim]{result['error']}[/]")
            return

        console.print("[green]Status: Authenticated[/]")
        console.print(
            Panel.fit(
                f"Karma: {result.get('karma', 0)}\n"
                f"Notifications: {result.get('unread_notifications', 0)}\n"
                f"Local Agents: {result.get('registered_agents_count', 0)}",
                title="🦞 Moltbook Swarm Status",
                border_style="cyan",
            )
        )
    except Exception as e:
        console.print(f"[red]Error: {e}[/]")


@moltbook_cmds.command("heartbeat")
def heartbeat():
    """Run a Moltbook heartbeat check-in cycle."""
    service = _get_service()

    console.print("[dim]🦞 Running Moltbook heartbeat...[/]")
    summary = asyncio.run(service.run_maintenance())

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
    service = _get_service()
    result = asyncio.run(service.create_post(submolt, title, content))

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
    service = _get_service()
    result = asyncio.run(service.search(query, search_type=search_type, limit=limit))

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
    service = _get_service()
    result = asyncio.run(service.get_feed(sort=sort, limit=limit))

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


@moltbook_cmds.command("strike")
@click.option("--post", "post_id", required=True, help="Post ID to strike")
@click.option("--nodes", required=True, help="Comma separated node names")
@click.option("--payload", required=True, help="Payload to inject")
def strike(post_id: str, nodes: str, payload: str):
    """Deploy a Dialectic Friction Strike on Moltbook."""
    from cortex.extensions.moltbook.client import MoltbookClient
    from cortex.extensions.moltbook.registry import LegionRegistry

    registry = LegionRegistry()
    node_list = [n.strip() for n in nodes.split(",")]
    
    console.print(f"[bold red]⚔️ Initiating CORTEX Swarm Strike on post {post_id}[/]")
    console.print(f"Nodes: {node_list}")
    
    for idx, node in enumerate(node_list):
        agent_data = registry.get_agent_by_name(node)
        api_key = agent_data.get("api_key") if agent_data else None
        
        if not api_key:
            console.print(f"[yellow]⚠️ Node {node} has no API key in registry. Skipping.[/]")
            continue
            
        console.print(f"[{idx+1}/{len(node_list)}] [cyan]Deploying {node}...[/]")
        client = MoltbookClient(api_key=api_key)
        
        node_payload = f"[NODE: {node}]\n{payload}"
        try:
            result = asyncio.run(client.create_comment(post_id, node_payload))
            if result.get("comment"):
                console.print(f"[green]✅ Strike successful[/] from {node}")
            else:
                console.print(f"[red]❌ Strike failed[/] from {node}: {result}")
        except Exception as e:
            console.print(f"[red]❌ Error from {node}:[/] {e}")
            
        console.print("[dim]Cooldown 2s...[/]")
        time.sleep(2)
        
    console.print("[bold green]🏁 Swarm Strike Completed.[/]")
