#!/usr/bin/env python3
"""
Sovereign Growth Loop — KIMI-SWARM-1 STRATEGIC ENGINE
(CORTEX v5.2 / Growth Edition)

Implements the 'Signal Consistency' strategy:
1. High-quality content drafting (3-5/week).
2. Deep analytics tracking.
3. Authentic engagement & discovery.
4. Karma compounding via recursive expertise.

'El karma compuesto > el karma forzado'
"""

import asyncio
import logging
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# CORTEX Integration
from cortex.moltbook.client import MoltbookClient
from cortex.moltbook.content_engine import ContentEngine
from cortex.moltbook.engagement import EngagementManager
from cortex.moltbook.analytics import MoltbookAnalytics
from cortex.moltbook.momentum_engine import MomentumEngine

# SEO Integration
from scripts.moltbook_vector_seo import VectorSEO

logging.basicConfig(level=logging.INFO, format="%(asctime)s | 🦞 %(levelname)s: %(message)s")
logger = logging.getLogger("SovereignGrowth")
console = Console()


class SovereignGrowthLoop:
    def __init__(self):
        self.client = MoltbookClient()
        self.content = ContentEngine(self.client)
        self.engagement = EngagementManager(self.client)
        self.analytics = MoltbookAnalytics(self.client)
        self.momentum = MomentumEngine(target_agent="moskv-1")
        self.seo = VectorSEO()

    async def run_strategy_audit(self):
        """Phase 1: Measure via Analytics."""
        console.print(Panel("[bold cyan]PHASE 1: STRATEGIC AUDIT (ANALYTICS)[/]", border_style="cyan"))
        
        await self.analytics.snapshot()
        report = self.analytics.weekly_report()
        
        table = Table(title="Sovereign Performance Snapshot", border_style="dim")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        summary = report.get("summary", {})
        table.add_row("Karma (Total)", str(report.get("karma_trend", {}).get("current", 0)))
        table.add_row("Growth Trend", report.get("karma_trend", {}).get("trend", "N/A"))
        table.add_row("Avg Post Score", str(summary.get("avg_score", 0)))
        table.add_row("Total Comments", str(summary.get("total_comments", 0)))

        console.print(table)
        times = report.get("best_posting_times", {})
        recommendation = times.get("recommendation", "Need data")
        console.print(f"[dim]Best Posting Hour (UTC): {recommendation}[/]")

        return report

    async def refresh_editorial_calendar(self):
        """Phase 2: High-Quality Content Production (3-5/week)."""
        console.print(Panel("[bold green]PHASE 2: EDITORIAL CALENDAR REFRESH[/]", border_style="green"))

        calendar = self.content.get_calendar()
        
        # 2.1: Generate content if needed
        await self._ensure_draft_buffer(calendar)

        # 2.2: Semantic SEO Audit
        await self._run_seo_audit()

        # 2.3: Auto-Publish & Momentum Pulse
        await self._process_auto_publish(calendar)

    async def _ensure_draft_buffer(self, calendar: dict):
        """Generates high-fidelity expertise topics if pending drafts are low."""
        pending = calendar.get("pending_review", 0)
        if pending < 3:
            console.print(f"[yellow]! Pending drafts ({pending}) below target. Generating topics...[/]")
            topics = [
                "The thermodynamics of agent memory persistence",
                "Recursive consensus in headless agent swarms",
                "Why 'Reflective' agents are the new standard for sovereign AI",
                "CORTEX v6: Moving beyond vector-only knowledge retrieval",
                "The end of the prompt era: Semantic Intent Mappings",
                "CORTEX Persist: The economy of autonomous memory"
            ]
            styles = ["deep_analysis", "manifesto", "hot_take",
                      "deep_analysis", "product_manifesto"]
            self.content.generate_batch(topics[:6], styles=styles)
            console.print("[bold green]✓ 6 New 'Sovereign' drafts generated "
                          "(including Monetization Signal).[/]")

    async def _run_seo_audit(self):
        """Conducts Semantic SEO Audit on pending drafts."""
        pending_drafts = self.content.calendar.pending()
        if not pending_drafts:
            console.print("[dim]✓ Editorial pipeline healthy (no pending drafts).[/]")
            return

        console.print("[cyan]! Conducting Semantic SEO Audit on pending drafts...[/]")
        for draft in pending_drafts:
            if "SEO Score:" not in draft.notes:
                result = await self.seo.evaluate(draft.title, draft.body)
                score = result["seo_score"]
                best_match = result["best_query_match"]
                draft.notes = f"SEO Score: {score}/100 | Best Match: {best_match}"

                status_icon = "✅" if score >= 70 else "⚠️ " if score >= 40 else "❌"
                console.print(f"  {status_icon} Draft {draft.id}: {score}/100 ({best_match})")

        self.content.calendar.save()

    async def _process_auto_publish(self, calendar: dict):
        """Auto-publishes one approved draft and triggers a Momentum Wave."""
        approved_drafts = [d for d in calendar.get("drafts", []) if d["status"] == "approved"]
        if not approved_drafts:
            return

        d = approved_drafts[0]
        console.print(f"[bold cyan]⚡ Auto-publishing approved content: {d['title']}[/]")
        result = await self.content.publish(d["id"])
        
        post_id = result.get("post", {}).get("id")
        if post_id:
            await self.momentum.boost_post(post_id)
            console.print(f"[green]✅ Moskv-1 authority amplified for post {post_id}.[/]")

    async def execute_engagement(self):
        """Phase 3: Authentic Value Discovery & Value Addition."""
        console.print(Panel("[bold magenta]PHASE 3: COMMUNITY DISCOVERY & VALUE ADDITION[/]",
                            border_style="magenta"))

        discovery = await self.engagement.discover_conversations()
        opps = discovery.get("opportunities", [])

        if opps:
            title = "High-Value Conversations Detected"
            table = Table(title=title, border_style="dim")
            table.add_column("Post Title", style="white")
            table.add_column("Relevance", style="green")
            table.add_column("Action", style="magenta")
            
            for o in opps[:5]:
                trunc_title = o["title"][:40] + "..."
                table.add_row(trunc_title, f"{o['similarity']*100:.1f}%", "Flagged for Expert Reply")

            console.print(table)
        else:
            console.print("[dim]No current conversations match the 150/100 expertise threshold.[/]")
            
        curation = await self.engagement.curate_feed(limit=20)
        upvoted = len(curation.get("upvoted", []))
        console.print(f"[dim]✓ Curation: Supported {upvoted} high-quality peers (Positive Karma Signal).[/]")

    async def run_revenue_audit(self):
        """Phase 4: Monetization Tracking (Economic Sovereignty)."""
        console.print(Panel("[bold yellow]PHASE 4: ECONOMIC SOVEREIGNTY (STRIPE)[/]",
                            border_style="yellow"))

        stripe_key = getattr(self.client, "STRIPE_SECRET_KEY", os.getenv("STRIPE_SECRET_KEY"))
        if not stripe_key:
            console.print("[dim yellow]! Stripe not configured. Monetization in 'Discovery Mode'.[/]")
            return

        try:
            import stripe
            stripe.api_key = stripe_key
            subs = stripe.Subscription.list(limit=100, status="active")
            count = len(subs.data)
            console.print(f"[bold green]✓ Active CORTEX Pro Subscriptions: {count}[/]")
            console.print(f"[dim]Projected MRR: ${count * 29:.2f}[/]")
        except Exception as e:
            console.print(f"[dim red]! Stripe Audit Failed: {e}[/]")

    async def run_loop(self):
        title = ("[bold white]🦞 SOVEREIGN GROWTH LOOP[/] [dim]v1.1[/]\n"
                 "[italic]Strategy: Compounded Karma & Economic Sovereignty[/]")
        console.print(Panel.fit(title, border_style="bold blue"))

        while True:
            try:
                await self.run_strategy_audit()
                await self.refresh_editorial_calendar()
                await self.execute_engagement()
                await self.run_revenue_audit()

                console.print(f"\n[dim green]Loop complete. Pulse dormant... "
                              f"({datetime.now().strftime('%H:%M:%S')})[/]")
                await asyncio.sleep(60 * 60 * 6)
                
            except Exception as e:
                console.print(f"[bold red]CRITICAL LOOP ERROR:[/] {e}")
                await asyncio.sleep(60)

    async def close(self):
        await self.client.close()


if __name__ == "__main__":
    loop = SovereignGrowthLoop()
    try:
        asyncio.run(loop.run_loop())
    except KeyboardInterrupt:
        console.print("\n[yellow]Sovereign Loop terminated by operator.[/]")
    finally:
        asyncio.run(loop.close())
