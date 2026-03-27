"""
cortex/swarm/capital_swarm.py
─────────────────────────────
SOVEREIGN CAPITAL EXTRACTION ENGINE — Ouroboros Swarm v1.0

Wires the CORTEX swarm infrastructure (specialists, factory, manager) to
the Ouroboros Capital Extraction vectors (A → Jules bounties, B → Talent
arbitrage, C → Sponsors, J → IP forging) and runs a Rich live dashboard
showing exergy yield, squad status, and ledger crystallization in real-time.

Usage:
    python -m cortex.swarm.capital_swarm [--vectors A,B,C,J] [--dry-run]
    cortex swarm-strike [vectors]   (via CLI)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from cortex.swarm.specialists import (
    forge_sovereign_swarm,
)

logger = logging.getLogger("cortex.swarm.capital")

console = Console()

# ──────────────────────────────────────────────────────────────────────────────
# OUROBOROS VECTOR DEFINITIONS
# ──────────────────────────────────────────────────────────────────────────────

VECTORS: dict[str, dict[str, Any]] = {
    "A": {
        "name": "GitHub Bounties (Jules)",
        "description": "Algora/Polar bounty discovery + Jules auto-PR",
        "specialist": "jules",
        "squad": "P1",
        "expected_yield_usd": 300.0,
        "confidence": 0.72,
        "compute_cost_usd": 4.20,
        "min_exergy_threshold": 5.0,
        "task_template": (
            "Scan GitHub issues labeled 'bounty' on repos: "
            "twentyhq/twenty, aietal/isaac. "
            "For issues with value ≥ $100 (pattern: '💎 $X bounty'): "
            "1) Evaluate thermodynamic EV = (reward - cloud_cost) × confidence. "
            "2) If EV > 5x compute cost, generate and submit a PR resolving the issue. "
            "3) Return PR URL and claimed bounty amount."
        ),
        "context": {
            "repo": "borjamoskv/Cortex-Persist",
            "branch": "main",
            "min_bounty_usd": 100,
            "auto_pr": True,
        },
    },
    "B": {
        "name": "Talent Arbitrage (MercorSovereign)",
        "description": "Technical interviews + data labeling via sovereign bypass pipeline",
        "specialist": "mercor_sovereign",
        "squad": "P1",
        "expected_yield_usd": 650.0,
        "confidence": 0.92,
        "compute_cost_usd": 0.45,
        "min_exergy_threshold": 12.0,
        "task_template": (
            "Execute Mercor Sovereign Ingestion protocol: "
            "1) Use `mac-control-omega` to bypass frontend throttling. "
            "2) Ingest skill profiles for 'Low-Latency C++' and 'CUDA'. "
            "3) Automated technical screening via `elevenlabs-omega`. "
            "4) Crystallize candidate exergy into CORTEX Ledger."
        ),
        "context": {
            "platform": "mercor-sovereign",
            "skills": ["Low-Latency C++", "CUDA", "Rust"],
            "session_target": 10,
        },
    },
    "C": {
        "name": "Sovereign Sponsors",
        "description": "GitHub Sponsors outreach + Proof of Work publication",
        "specialist": "ouroboros",
        "squad": "P0",
        "expected_yield_usd": 500.0,
        "confidence": 0.40,
        "compute_cost_usd": 0.80,
        "min_exergy_threshold": 2.0,
        "task_template": (
            "Execute Sovereign Sponsors protocol on GitHub: "
            "1) Audit CORTEX public repository metrics (stars, forks, citations). "
            "2) Draft personalized outreach to top 10 DAOs and AI labs with active "
            "GitHub Sponsors. "
            "3) Publish Proof of Work walkthrough to CORTEX README and social channels. "
            "4) Configure GitHub Sponsors tiers ($5, $25, $100/month). "
            "5) Return list of outreach targets and published content URLs."
        ),
        "context": {
            "repo": "borjamoskv/Cortex-Persist",
            "sponsor_tiers": [5, 25, 100],
            "target_orgs": ["DAOs", "AI labs", "sovereign builders"],
        },
    },
    "J": {
        "name": "IP Forging (Synthetic APIs)",
        "description": "Curated dataset + niche API on Gumroad/Stripe",
        "specialist": "ouroboros",
        "squad": "P1",
        "expected_yield_usd": 250.0,
        "confidence": 0.55,
        "compute_cost_usd": 1.50,
        "min_exergy_threshold": 4.0,
        "task_template": (
            "Execute IP Forging protocol — Vector J: "
            "1) Identify highest-demand niche datasets (AI safety evals, RL environments, "
            "Spanish NLP corpora — validated via GitHub Stars trend). "
            "2) Compile and structure a dataset of ≥1000 unique entries from public sources. "
            "3) Create Gumroad product listing with pricing $19-$49. "
            "4) Draft and schedule 3 promotional posts targeting AI/ML communities. "
            "5) Return Gumroad product URL and projected monthly revenue."
        ),
        "context": {
            "platform": "gumroad",
            "min_dataset_size": 1000,
            "price_range_usd": [19, 49],
        },
    },
    "G": {
        "name": "Red Team (Immunefi)",
        "description": "Security audit on high-TVL contracts → bug bounty",
        "specialist": "devin",
        "squad": "P2",
        "expected_yield_usd": 2000.0,
        "confidence": 0.20,
        "compute_cost_usd": 15.0,
        "min_exergy_threshold": 8.0,
        "task_template": (
            "Execute Red Team protocol — Vector G: "
            "1) Scan Immunefi for active bounties ≥ $1000 in Rust/Solidity protocols. "
            "2) Select top 2 by TVL-to-bounty ratio. "
            "3) Perform automated static analysis + fuzzing on target contracts. "
            "4) If critical finding: draft vulnerability report in Immunefi format. "
            "5) Return findings report URL or null if no critical vulnerabilities found."
        ),
        "context": {
            "platform": "immunefi",
            "min_bounty_usd": 1000,
            "languages": ["Rust", "Solidity"],
        },
    },
    "M": {
        "name": "Sovereign Talent Clone (Mercor)",
        "description": "0-latency scraping, AI interviews, and C5 training data extraction.",
        "specialist": "mercor_sovereign",
        "squad": "P1",
        "expected_yield_usd": 500.0,
        "confidence": 0.85,
        "compute_cost_usd": 10.0,
        "min_exergy_threshold": 50.0,
        "task_template": (
            "Execute Mercor Sovereign Ingestion: "
            "1) Trigger on missing C5 data in Vector DB for target language. "
            "2) Scrape ecosystems (GitHub/LinkedIn) for candidates. "
            "3) Send DMs offering crypto for a 45min code interview. "
            "4) Send Voice Agent (ElevenLabs) + IDE monitoring (OpenAI). "
            "5) Validate causal compression of developer (APEX score > 85). "
            "6) Pay API fee and write validated pipeline to Vector DB."
        ),
        "context": {
            "platform": "cortex-recruitment",
            "skills": ["Low-Latency C++", "Rust", "CUDA", "PyTorch"],
            "bounty_usd": 150,
        },
    },
    "Z": {
        "name": "Fiat Liquidity (Bizum)",
        "description": "P2P micro-bounty settlement via Bizum strike",
        "specialist": "bizum",
        "squad": "P2",
        "expected_yield_usd": 150.0,
        "confidence": 0.92,
        "compute_cost_usd": 0.15,
        "min_exergy_threshold": 10.0,
        "task_template": (
            "Execute Bizum Strike — Vector Z: "
            "1) Verify `mac-control-omega` session for mobile bank interface. "
            "2) Dispatched micro-bounty settlement for validated triage work. "
            "3) Record transaction hash to CORTEX Ledger."
        ),
        "context": {
            "mode": "P2P",
            "provider": "bizum",
            "limit_usd": 500,
        },
    },
}


# ──────────────────────────────────────────────────────────────────────────────
# EXERGY ACCOUNTING
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class VectorResult:
    vector_id: str
    vector_name: str
    status: str = "pending"
    gross_yield_usd: float = 0.0
    compute_cost_usd: float = 0.0
    exergy_delta: float = 0.0
    pr_url: str | None = None
    content: str = ""
    error: str | None = None
    duration_s: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def net_yield_usd(self) -> float:
        return self.gross_yield_usd - self.compute_cost_usd

    @property
    def is_positive_exergy(self) -> bool:
        return self.net_yield_usd > 0


@dataclass
class SwarmReport:
    session_id: str
    vectors_executed: list[str] = field(default_factory=list)
    results: list[VectorResult] = field(default_factory=list)
    total_exergy: float = 0.0
    session_duration_s: float = 0.0

    @property
    def total_gross_yield(self) -> float:
        return sum(r.gross_yield_usd for r in self.results)

    @property
    def total_net_yield(self) -> float:
        return sum(r.net_yield_usd for r in self.results)

    @property
    def positive_vectors(self) -> list[VectorResult]:
        return [r for r in self.results if r.is_positive_exergy]


# ──────────────────────────────────────────────────────────────────────────────
# CAPITAL SWARM ENGINE
# ──────────────────────────────────────────────────────────────────────────────

class CapitalSwarmEngine:
    """
    Sovereign Capital Extraction Engine.

    Orchestrates specialist actuators across Ouroboros vectors with:
    - Thermodynamic EV gate (rejects vectors where EV < 5× compute cost)
    - Parallel dispatch across P0/P1/P2 squads
    - Rich live dashboard for real-time exergy tracking
    - CORTEX ledger crystallization of all yield events
    """

    def __init__(
        self,
        active_vectors: list[str] | None = None,
        dry_run: bool = False,
        engine: Any = None,
    ) -> None:
        self.active_vectors = active_vectors or list(VECTORS.keys())
        self.dry_run = dry_run
        self.engine = engine
        self.specialists = forge_sovereign_swarm()
        self.report = SwarmReport(
            session_id=f"swarm-{int(time.time())}",
            vectors_executed=self.active_vectors,
        )
        self._session_start = time.monotonic()

    def _ev_gate(self, vector_id: str) -> bool:
        """Thermodynamic EV gate — Axiom 2: Yield > Compute × 5×."""
        v = VECTORS[vector_id]
        ev = v["expected_yield_usd"] * v["confidence"]
        cost = v["compute_cost_usd"]
        passes = ev >= cost * 5
        logger.info(
            "[EV_GATE] Vector %s: EV=%.2f cost=%.2f → %s",
            vector_id, ev, cost, "PASS" if passes else "REJECT"
        )
        return passes

    async def _execute_vector(self, vector_id: str) -> VectorResult:
        """Execute a single Ouroboros vector via its specialist."""
        v = VECTORS[vector_id]
        result = VectorResult(
            vector_id=vector_id,
            vector_name=v["name"],
            compute_cost_usd=v["compute_cost_usd"],
        )

        t0 = time.monotonic()

        # EV gate
        if not self._ev_gate(vector_id):
            result.status = "skipped_ev"
            result.error = "NEGATIVE_NET_EXERGY: EV < 5× compute cost"
            result.duration_s = time.monotonic() - t0
            return result

        specialist = self.specialists.get(v["specialist"])
        if not specialist:
            result.status = "failed"
            result.error = f"Specialist '{v['specialist']}' not available"
            result.duration_s = time.monotonic() - t0
            return result

        if self.dry_run:
            # Simulate execution
            estimated_yield = v["expected_yield_usd"] * v["confidence"]
            result.status = "simulated"
            result.gross_yield_usd = estimated_yield
            result.exergy_delta = estimated_yield - v["compute_cost_usd"]
            result.content = f"[DRY-RUN] Simulated yield: ${estimated_yield:.2f}"
            result.metadata = {"dry_run": True, "vector": vector_id}
            result.duration_s = time.monotonic() - t0
            return result

        try:
            logger.info("[STRIKE] Deploying %s on Vector %s", v["specialist"], vector_id)
            response = await specialist.execute(
                task=v["task_template"],
                context=v.get("context", {}),
            )

            if response["status"] == "success":
                exergy_score = response.get("metadata", {}).get(
                    "exergy_score", v["expected_yield_usd"] * v["confidence"]
                )
                result.status = "success"
                result.gross_yield_usd = float(exergy_score)
                result.exergy_delta = float(exergy_score) - v["compute_cost_usd"]
                result.content = response["content"]
                result.pr_url = response.get("metadata", {}).get("pr_url")
                result.metadata = dict(response.get("metadata", {}))
            else:
                result.status = "failed"
                result.error = response.get("error", "Unknown failure")

        except Exception as exc:
            result.status = "failed"
            result.error = str(exc)
            logger.exception("[STRIKE] Vector %s failed: %s", vector_id, exc)

        result.duration_s = time.monotonic() - t0
        return result

    def _build_dashboard(self, results_so_far: list[VectorResult]) -> Table:
        """Render the live Rich dashboard table."""
        table = Table(
            title=f"⚛ Ouroboros Capital Swarm — Session [{self.report.session_id}]",
            show_header=True,
            header_style="bold #2B3BE5",
            border_style="#2B3BE5",
            min_width=100,
        )
        table.add_column("Vector", style="bold white", width=6)
        table.add_column("Name", style="dim white", width=26)
        table.add_column("Squad", style="cyan", width=6)
        table.add_column("Status", width=14)
        table.add_column("Gross $", justify="right", width=10)
        table.add_column("Cost $", justify="right", style="dim", width=8)
        table.add_column("Net Exergy $", justify="right", width=12)
        table.add_column("⏱ s", justify="right", width=6)

        status_styles = {
            "success": "bold green",
            "simulated": "bold #FFD700",
            "failed": "bold red",
            "skipped_ev": "dim red",
            "pending": "dim white",
            "running": "bold #2B3BE5",
        }

        for r in results_so_far:
            style = status_styles.get(r.status, "white")
            net = r.net_yield_usd
            net_str = f"${net:+.2f}" if r.status in ("success", "simulated") else "—"
            net_style = "bold green" if net > 0 else ("bold red" if net < 0 else "dim")
            table.add_row(
                r.vector_id,
                r.vector_name,
                VECTORS.get(r.vector_id, {}).get("squad", "?"),
                Text(r.status.upper(), style=style),
                f"${r.gross_yield_usd:.2f}" if r.gross_yield_usd else "—",
                f"${r.compute_cost_usd:.2f}",
                Text(net_str, style=net_style),
                f"{r.duration_s:.1f}" if r.duration_s else "…",
            )

        # Summary row
        total_gross = sum(r.gross_yield_usd for r in results_so_far)
        total_cost = sum(r.compute_cost_usd for r in results_so_far)
        total_net = total_gross - total_cost
        elapsed = time.monotonic() - self._session_start
        net_style = "bold green" if total_net > 0 else "bold red"
        table.add_section()
        table.add_row(
            "Σ", "[bold]TOTAL[/bold]", "", "",
            f"[bold]${total_gross:.2f}[/bold]",
            f"[bold]${total_cost:.2f}[/bold]",
            Text(f"${total_net:+.2f}", style=net_style),
            f"{elapsed:.0f}",
        )
        return table

    async def run(self) -> SwarmReport:
        """
        Launch the Ouroboros Swarm across all active vectors in parallel.
        Streams results to a Rich Live dashboard.
        """
        results: list[VectorResult] = []
        pending: list[VectorResult] = [
            VectorResult(
                vector_id=vid,
                vector_name=VECTORS[vid]["name"],
                status="pending",
                compute_cost_usd=VECTORS[vid]["compute_cost_usd"],
            )
            for vid in self.active_vectors
            if vid in VECTORS
        ]

        with Live(
            self._build_dashboard(pending),
            console=console,
            refresh_per_second=4,
            screen=False,
        ) as live:
            # Dispatch all vectors in parallel
            tasks = {
                asyncio.create_task(self._execute_vector(vid)): vid
                for vid in self.active_vectors
                if vid in VECTORS
            }

            in_progress = list(pending)

            for coro in asyncio.as_completed(list(tasks.keys())):
                result = await coro
                results.append(result)
                # Replace the pending entry with the fresh result
                in_progress = [
                    r if r.vector_id != result.vector_id else result
                    for r in in_progress
                ]
                live.update(self._build_dashboard(in_progress))

        # Crystallize report
        self.report.results = results
        self.report.total_exergy = sum(r.exergy_delta for r in results)
        self.report.session_duration_s = time.monotonic() - self._session_start

        if self.engine and hasattr(self.engine, "ledger") and self.engine.ledger:
            for r in results:
                await self.engine.ledger.record_transaction(
                    project="cortex-swarm",
                    action="swarm_vector_strike",
                    detail={
                        "session_id": self.report.session_id,
                        "vector_id": r.vector_id,
                        "status": r.status,
                        "gross_usd": r.gross_yield_usd,
                        "cost_usd": r.compute_cost_usd,
                        "net_exergy": r.net_yield_usd,
                        "duration_s": r.duration_s,
                    }
                )

        self._print_summary()
        return self.report

    def _print_summary(self) -> None:
        r = self.report
        positive = r.positive_vectors
        net = r.total_net_yield
        net_markup = (
            f"[bold green]${net:+.2f}[/bold green]"
            if net >= 0 else f"[bold red]${net:+.2f}[/bold red]"
        )

        summary = (
            f"\n[bold #2B3BE5]◈ OUROBOROS SESSION CRYSTALLIZED[/bold #2B3BE5]\n"
            f"  Session : [dim]{r.session_id}[/dim]\n"
            f"  Vectors : {len(r.vectors_executed)} executed\n"
            f"  Gross   : [bold]${r.total_gross_yield:.2f}[/bold]\n"
            f"  Cost    : [dim]${sum(res.compute_cost_usd for res in r.results):.2f}[/dim]\n"
            f"  Net Δ   : {net_markup}\n"
            f"  Positive: {len(positive)}/{len(r.results)} vectors\n"
            f"  Duration: {r.session_duration_s:.1f}s\n"
        )
        console.print(Panel(summary, border_style="#2B3BE5", title="[bold]Exergy Report[/bold]"))

        if r.total_net_yield < 0:
            console.print(
                "[bold red]⚠ NEGATIVE NET EXERGY — Vector quarantine activated "
                "(Ouroboros Axiom 2). Review failed vectors before reactivation.[/bold red]"
            )


# ──────────────────────────────────────────────────────────────────────────────
# CLI ENTRY POINT
# ──────────────────────────────────────────────────────────────────────────────

def main() -> None:
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Ouroboros Capital Swarm — Sovereign extraction engine"
    )
    parser.add_argument(
        "--vectors",
        type=str,
        default=",".join(["A", "B", "C", "J", "M", "Z"]),
        help="Comma-separated vector IDs to activate (A,B,C,G,J,M,Z). Default: A,B,C,J,M,Z",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Simulate execution without live API calls",
    )
    parser.add_argument(
        "--output-json",
        type=str,
        default=None,
        help="Write full report JSON to path",
    )
    args = parser.parse_args()

    active_vectors = [v.strip().upper() for v in args.vectors.split(",")]
    invalid = [v for v in active_vectors if v not in VECTORS]
    if invalid:
        console.print(f"[red]Unknown vectors: {invalid}. Valid: {list(VECTORS.keys())}[/red]")
        return

    console.print(
        Panel(
            f"[bold #2B3BE5]⚛ OUROBOROS SWARM LAUNCHED[/bold #2B3BE5]\n"
            f"Vectors: [bold]{', '.join(active_vectors)}[/bold]  |  "
            f"Dry-Run: [bold]{'YES' if args.dry_run else 'NO'}[/bold]",
            border_style="#2B3BE5",
        )
    )

    engine = CapitalSwarmEngine(
        active_vectors=active_vectors,
        dry_run=args.dry_run,
    )

    report = asyncio.run(engine.run())

    if args.output_json:
        data = {
            "session_id": report.session_id,
            "total_gross_usd": report.total_gross_yield,
            "total_net_usd": report.total_net_yield,
            "total_exergy": report.total_exergy,
            "duration_s": report.session_duration_s,
            "results": [
                {
                    "vector": r.vector_id,
                    "name": r.vector_name,
                    "status": r.status,
                    "gross_usd": r.gross_yield_usd,
                    "net_usd": r.net_yield_usd,
                    "pr_url": r.pr_url,
                    "error": r.error,
                    "duration_s": r.duration_s,
                }
                for r in report.results
            ],
        }
        with open(args.output_json, "w") as f:
            json.dump(data, f, indent=2)
        console.print(f"[dim]Report written to {args.output_json}[/dim]")


if __name__ == "__main__":
    main()
