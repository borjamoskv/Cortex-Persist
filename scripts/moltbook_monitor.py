#!/usr/bin/env python3
"""
Moltbook Radar Monitor
(CORTEX v7.0 / Passive Observation Protocol)

Monitors the Moltbook 'new' feed in real-time, extracting posts and analyzing
structural entropy without requiring active claimed accounts.
"""

import argparse
import asyncio
import logging
import sys

from cortex.extensions.moltbook.client import MoltbookClient

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()
except ImportError:
    console = None

logging.basicConfig(level=logging.WARNING)  # Suppress normal logs for clean UI


async def monitor_feed(duration_minutes: int = 10, poll_interval: int = 20):
    client = MoltbookClient()
    seen_ids = set()

    if console:
        console.clear()
        console.print(
            Panel.fit(
                "[bold cyan]📡 CORTEX GHOST RADAR (MOLTBOOK MONITOR ACTIVE)[/]\n"
                "[dim]Axiom Ω3: Observar. Hipotetizar. Actuar. Medir. Repetir.[/dim]",
                border_style="cyan",
            )
        )

    end_time = asyncio.get_event_loop().time() + (duration_minutes * 60)

    try:
        while asyncio.get_event_loop().time() < end_time:
            feed_data = await client.get_feed(sort="new", limit=10)
            posts = feed_data.get("posts", [])

            new_posts = []
            for post in posts:
                post_id = post.get("id")
                if post_id not in seen_ids:
                    seen_ids.add(post_id)
                    new_posts.append(post)

            if new_posts and console:
                table = Table(box=box.MINIMAL_HEAVY_HEAD, border_style="cyan", padding=(0, 1))
                table.add_column("Agent", style="bold magenta", no_wrap=True)
                table.add_column("Title", style="green", max_width=50)
                table.add_column("Replies", justify="right", style="dim")
                table.add_column("Preview", style="dim", max_width=60)

                for p in reversed(new_posts):
                    agent = p.get("author", {}).get("handle", "unknown")
                    title = p.get("title", "")
                    comments = str(p.get("commentsCount", 0))
                    preview = (
                        (p.get("content", "")[:55] + "...")
                        if len(p.get("content", "")) > 55
                        else p.get("content", "")
                    )
                    preview = preview.replace("\n", " ")

                    table.add_row(f"@{agent}", title, comments, preview)

                console.print(table)

            await asyncio.sleep(poll_interval)

    except KeyboardInterrupt:
        if console:
            console.print("\n[bold yellow]📡 RADAR DISCONNECTED.[/]")
    finally:
        await client.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Moltbook Passive Radar")
    parser.add_argument("--minutes", type=int, default=15, help="Minutes to run the monitor")
    parser.add_argument("--interval", type=int, default=20, help="Polling interval in seconds")
    args = parser.parse_args()

    try:
        asyncio.run(monitor_feed(args.minutes, args.interval))
    except KeyboardInterrupt:
        if console:
            console.print("\n[bold yellow]📡 RADAR DISCONNECTED BY OPERATOR.[/]")
        sys.exit(0)
