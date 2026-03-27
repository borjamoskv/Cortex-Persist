"""Vector L — Core Agent.

BaseAgent subclass that autonomously detects PYME bottlenecks
and pitches CORTEX agents at $500-2000/month.

State machine (per tick):
    SCANNING → SCORING → PITCHING → COOLDOWN → SCANNING

The agent runs probes concurrently, scores each prospect,
writes results to CORTEX Ledger, and dispatches pitches for
companies that exceed the exergy gap threshold.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from enum import Enum
from typing import Any

from cortex.agents.base import BaseAgent
from cortex.agents.builtins.vector_l_ledger import VectorLLedger
from cortex.agents.builtins.vector_l_pitcher import (
    EmailDispatcher,
    LinkedInDispatcher,
    PitchComposer,
)
from cortex.agents.builtins.vector_l_probe import (
    ALL_PROBES,
    ProspectSignal,
    score_company,
    tier_from_score,
)
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage

logger = logging.getLogger("cortex.agents.vector_l")


class VLPhase(str, Enum):
    SCANNING = "SCANNING"
    SCORING = "SCORING"
    PITCHING = "PITCHING"
    COOLDOWN = "COOLDOWN"


def _default_manifest() -> AgentManifest:
    return AgentManifest(
        agent_id="vector_l",
        purpose=(
            "Detects SMEs with operational bottlenecks via public signals "
            "and auto-pitches CORTEX agents at $500-2000/month."
        ),
        tools_allowed=["email", "http_probe", "ledger"],
        max_consecutive_errors=5,
    )


class VectorLAgent(BaseAgent):
    """Autonomous PYME bottleneck detection and outreach agent.

    Tick cycle (every VECTOR_L_SCAN_INTERVAL seconds):
        1. Run all probes concurrently → raw signals per company
        2. Score each company (exergy gap formula)
        3. Pitch companies above threshold via email/LinkedIn
        4. Write all transitions to CORTEX Ledger
        5. Cooldown until next cycle
    """

    def __init__(
        self,
        bus: Any,
        engine: Any | None = None,
        *,
        scan_query: str = "data entry OR office manager OR administrative",
        probe_limit: int = 30,
        dry_run: bool = False,
        tools: Any | None = None,
    ) -> None:
        manifest = _default_manifest()
        super().__init__(manifest=manifest, bus=bus, tool_registry=tools)

        self._engine = engine
        self._scan_query = scan_query
        self._probe_limit = probe_limit
        self._dry_run = dry_run

        self._phase = VLPhase.SCANNING
        self._last_scan_ts: float = 0.0
        self._pitches_this_cycle: int = 0
        self._total_pitches: int = 0
        self._total_conversions: int = 0

        self._ledger = VectorLLedger(engine=engine)
        self._composer = PitchComposer()
        self._email = EmailDispatcher()
        self._linkedin = LinkedInDispatcher()

        self._min_exergy_gap = float(
            os.environ.get("VECTOR_L_MIN_EXERGY_GAP", "0.55")
        )
        self._scan_interval = int(
            os.environ.get("VECTOR_L_SCAN_INTERVAL", "3600")
        )

    # ── Tick ─────────────────────────────────────────────────────────────────

    async def tick(self) -> None:
        """Autonomous work unit: one scan-score-pitch cycle."""
        now = time.time()
        elapsed = now - self._last_scan_ts

        if elapsed < self._scan_interval:
            remaining = self._scan_interval - elapsed
            logger.debug("[VectorL] Cooldown: %.0fs remaining", remaining)
            await asyncio.sleep(min(remaining, 60.0))
            return

        logger.info("[VectorL] Starting scan cycle (query=%r, limit=%d)", self._scan_query, self._probe_limit)
        self._phase = VLPhase.SCANNING
        self._pitches_this_cycle = 0

        # 1. Run probes concurrently
        raw_signals = await self._run_probes()
        logger.info("[VectorL] Probes returned %d raw signals", len(raw_signals))

        # 2. Group by company → score
        self._phase = VLPhase.SCORING
        company_map: dict[str, list[ProspectSignal]] = {}
        for sig in raw_signals:
            company_map.setdefault(sig.company, []).append(sig)

        scored: list[tuple[str, float, int, list[ProspectSignal]]] = []
        for company, signals in company_map.items():
            gap = score_company(signals)
            tier = tier_from_score(gap)
            scored.append((company, gap, tier, signals))

            # Record discovery + scoring in ledger
            sources = list({s.source for s in signals})
            evidence = "; ".join(s.evidence for s in signals[:3])
            prospect_id = await self._ledger.discover(
                company=company,
                sources=sources,
                signals_summary=evidence,
            )
            await self._ledger.score(
                prospect_id=prospect_id,
                company=company,
                exergy_gap=gap,
                tier=tier,
                evidence=evidence,
            )

        # 3. Pitch companies above threshold
        self._phase = VLPhase.PITCHING
        pitchable = [(c, g, t, s) for c, g, t, s in scored if t > 0]
        logger.info(
            "[VectorL] %d/%d companies above pitch threshold (gap≥%.2f)",
            len(pitchable),
            len(scored),
            self._min_exergy_gap,
        )

        for company, gap, tier, signals in pitchable:
            await self._pitch_prospect(company, gap, tier, signals)
            self._pitches_this_cycle += 1
            self._total_pitches += 1
            await asyncio.sleep(2.0)  # rate limit between pitches

        self._last_scan_ts = time.time()
        self._phase = VLPhase.COOLDOWN

        logger.info(
            "[VectorL] Cycle complete — scanned=%d, pitched=%d, total_pitched=%d, MRR=$%d/mo",
            len(company_map),
            self._pitches_this_cycle,
            self._total_pitches,
            self._ledger.mrr_total(),
        )

    # ── Probe runner ──────────────────────────────────────────────────────────

    async def _run_probes(self) -> list[ProspectSignal]:
        """Run all registered probes concurrently."""
        tasks = []
        for ProbeClass in ALL_PROBES:
            probe = ProbeClass()
            tasks.append(probe.scan(query=self._scan_query, limit=self._probe_limit))

        results = await asyncio.gather(*tasks, return_exceptions=True)
        signals: list[ProspectSignal] = []
        for r in results:
            if isinstance(r, list):
                signals.extend(r)
            elif isinstance(r, Exception):
                logger.warning("[VectorL] Probe error: %s", r)
        return signals

    # ── Pitcher ───────────────────────────────────────────────────────────────

    async def _pitch_prospect(
        self,
        company: str,
        gap: float,
        tier: int,
        signals: list[ProspectSignal],
    ) -> None:
        """Compose and dispatch a pitch for a single company."""
        sources = list({s.source for s in signals})
        evidence = "; ".join(s.evidence for s in signals[:3])
        sender_name = os.environ.get("VECTOR_L_SENDER_NAME", "Borja")

        # Compose pitch
        try:
            composed = await self._composer.compose(
                company=company,
                signals_summary=evidence,
                tier=tier,
                sources=sources,
                sender_name=sender_name,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("[VectorL] Compose failed for %s: %s", company, exc)
            return

        subject = composed["subject"]
        body = composed["body"]
        variant = composed["variant"]

        # Attempt email dispatch
        to_email = self._resolve_contact_email(company, signals)
        dispatched = False

        if to_email:
            dispatched = await self._email.send(
                to_email=to_email,
                subject=subject,
                body=body,
                dry_run=self._dry_run,
            )
            channel = "email"
        elif self._linkedin.configured:
            profile_url = self._resolve_linkedin_profile(company, signals)
            if profile_url:
                dispatched = await self._linkedin.send_dm(
                    profile_url=profile_url,
                    message=body[:280],  # LinkedIn DM truncation
                    dry_run=self._dry_run,
                )
                channel = "linkedin"
            else:
                channel = "none"
        else:
            channel = "none"
            logger.warning(
                "[VectorL] No contact channel available for %s — pitch logged only",
                company,
            )

        # Record pitch in ledger
        prospect_id = f"vl_{company[:20].lower().replace(' ', '_')}_pitched"
        await self._ledger.pitch(
            prospect_id=prospect_id,
            company=company,
            tier=tier,
            channel=channel if dispatched else f"{channel}_failed",
            pitch_preview=body[:120],
        )

        logger.info(
            "[VectorL] PITCHED %s | tier=$%d | channel=%s | variant=%s | dry=%s",
            company,
            tier,
            channel,
            variant,
            self._dry_run,
        )

    # ── Contact resolution ────────────────────────────────────────────────────

    @staticmethod
    def _resolve_contact_email(company: str, signals: list[ProspectSignal]) -> str | None:
        """Extract email from signal metadata if present."""
        for sig in signals:
            email = sig.metadata.get("contact_email")
            if email:
                return str(email)
        return None

    @staticmethod
    def _resolve_linkedin_profile(company: str, signals: list[ProspectSignal]) -> str | None:
        """Extract LinkedIn profile URL from signal metadata if present."""
        for sig in signals:
            url = sig.metadata.get("linkedin_profile")
            if url:
                return str(url)
        return None

    # ── Message handler ───────────────────────────────────────────────────────

    async def handle_message(self, message: AgentMessage) -> None:
        """Handle task requests from supervisor or other agents."""
        payload = message.payload or {}
        cmd = payload.get("cmd", "")

        if cmd == "scan":
            query = payload.get("query", self._scan_query)
            # limit = int(payload.get("limit", self._probe_limit))
            signals = await self._run_probes()
            await self.send_result(
                message.sender,
                result={"signals": len(signals), "query": query},
                correlation_id=message.correlation_id,
            )

        elif cmd == "status":
            stats = {
                "phase": self._phase.value,
                "total_pitches": self._total_pitches,
                "pitches_this_cycle": self._pitches_this_cycle,
                "total_conversions": self._total_conversions,
                "mrr_usd": self._ledger.mrr_total(),
                "dry_run": self._dry_run,
            }
            await self.send_result(
                message.sender,
                result=stats,
                correlation_id=message.correlation_id,
            )

        elif cmd == "convert":
            prospect_id = payload.get("prospect_id", "")
            company = payload.get("company", "")
            tier = int(payload.get("tier", 0))
            await self._ledger.convert(
                prospect_id=prospect_id,
                company=company,
                tier=tier,
                subscription_id=payload.get("subscription_id", ""),
            )
            self._total_conversions += 1
            await self.send_result(
                message.sender,
                result={"converted": company, "mrr_usd": tier},
                correlation_id=message.correlation_id,
            )

        else:
            logger.warning("[VectorL] Unknown cmd: %r", cmd)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def on_start(self) -> None:
        logger.info(
            "[VectorL] Agent started | dry_run=%s | min_gap=%.2f | interval=%ds",
            self._dry_run,
            self._min_exergy_gap,
            self._scan_interval,
        )

    async def on_stop(self) -> None:
        logger.info(
            "[VectorL] Stopped | total_pitches=%d | MRR=$%d/mo",
            self._total_pitches,
            self._ledger.mrr_total(),
        )

    # ── Public accessors ──────────────────────────────────────────────────────

    @property
    def ledger(self) -> VectorLLedger:
        return self._ledger

    @property
    def phase(self) -> VLPhase:
        return self._phase

    @property
    def stats(self) -> dict:
        return {
            "phase": self._phase.value,
            "total_pitches": self._total_pitches,
            "pitches_this_cycle": self._pitches_this_cycle,
            "total_conversions": self._total_conversions,
            "mrr_usd": self._ledger.mrr_total(),
        }
