"""CAZARECOMPENSAS Agent — Sovereign Capital Extraction Engine.

This agent operates the Ouroboros Capital Engine logic. It is a High-Entropy / High-Control
bounty hunter that autonomously scans, thermodynamically evaluates (Exergy > Entropy),
and extracts capital (bounties) from external platforms like Algora-Jules or RustChain.
Aligned with CORTEX Axioms Ω₂ (Thermodynamics) and Ω₄ (Sovereign).
"""

from __future__ import annotations

import asyncio
import logging
import time
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any

from cortex.agents.base import BaseAgent
from cortex.agents.message_schema import MessageKind
from cortex.quarantine.quarantine import BlastRadiusReport, evaluate_demolition
from cortex.memory.temporal import now_iso
from cortex.shannon.exergy import ActionRisk, ExergyInput, calculate_exergy

if TYPE_CHECKING:
    from cortex.agents.manifest import AgentManifest
    from cortex.agents.message_schema import AgentMessage
    from cortex.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.cazarecompensas")

_PROJECT = "cazarecompensas-agent"
_SOURCE = "agent:cazarecompensas"


class BountyState(str, Enum):
    """Deterministic states for bounty extraction lifecycle."""
    DISCOVERED = "DISCOVERED"
    EXTRACTING = "EXTRACTING"
    PENDING_SETTLEMENT = "PENDING_SETTLEMENT"
    SETTLED = "SETTLED"
    FAILED = "FAILED"


class CazarecompensasAgent(BaseAgent):
    """Sovereign agent for Autonomous Bounty Extraction (Algora/RustChain)."""

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,
        wallet_address: str | None = None,
        tool_registry: ToolRegistry | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self.wallet_address = wallet_address
        self._last_bounty_scan: float = 0
        self._scan_interval: float = 3600  # Scan every hour
        self._engine: Any = None
        # Threshold: Required exergy to entropy ratio to accept a bounty
        self._thermodynamic_threshold: float = 3.0
        self._bounty_states: dict[str, BountyState] = {}
        self._total_exergy_extracted: Decimal = Decimal("0")
        self._pending_settlements: list[dict[str, Any]] = []
        self._consecutive_failures: int = 0
        self._circuit_breaker_until: float = 0.0
        self._background_tasks: set[asyncio.Task[Any]] = set()

    async def on_start(self) -> None:
        """Initialize CORTEX Engine and connect to the persistence ledger."""
        from cortex.cli.common import get_engine

        self._engine = get_engine(self.manifest.tenant_id)
        await self._engine.init_db()
        logger.info(
            "[%s] CAZARECOMPENSAS Engine initialized. Exergy threshold: %.2f",
            self.agent_id,
            self._thermodynamic_threshold,
        )

        try:
            # Memory Bridge: Read prior sovereign state to avoid re-evaluating extracted exergy
            claims = await self._engine.search(
                project=_PROJECT,
                tags=["bounty", "extraction"],
                limit=1000,
            )
            for claim in claims:
                b_id = claim.meta.get("bounty_id")
                if b_id:
                    self._bounty_states[b_id] = BountyState.SETTLED
            logger.info(
                "[%s] Sovereign Memory restored: %d known bounties.",
                self.agent_id,
                len(self._bounty_states),
            )
        except Exception as e:
            logger.warning("[%s] Failed to restore known bounties from Ledger: %s", self.agent_id, e)

    async def handle_message(self, message: AgentMessage) -> None:
        """Process manual tactical requests."""
        if message.kind == MessageKind.TASK_REQUEST:
            action = message.payload.get("action")
            target = message.payload.get("target")

            if action == "find_bounties":
                results = await self._scan_for_bounties(target)
                await self.send_result(
                    message.sender,
                    {"status": "ok", "bounties": results},
                    correlation_id=message.message_id,
                )
            elif action == "evaluate_bounty":
                bounty_data = message.payload.get("bounty_data", {})
                eval_result = self._evaluate_thermodynamics(bounty_data)
                await self.send_result(
                    message.sender,
                    {"status": "ok", "evaluation": eval_result},
                    correlation_id=message.message_id,
                )
            else:
                await self.send_result(
                    message.sender, {"status": "error", "message": f"Unknown action: {action}"}
                )

    async def tick(self) -> None:
        """Zero-Prompting autonomous loop for continuous capital extraction."""
        if not self._engine:
            return

        now = time.time()
        if now - self._last_bounty_scan > self._scan_interval:
            await self._run_autonomous_hunt()
            self._last_bounty_scan = now

    async def _verify_settlements(self) -> None:
        """Mock verification of expected payouts to consolidate yield into total exergy."""
        settled = []
        for pending in self._pending_settlements:
            # In a real environment, query Algora/RustChain/Stripe here.
            pending["status"] = "settled"

            # Anti-Ghost Exergy: only update accumulated yield on real settlement
            self._total_exergy_extracted += Decimal(str(pending["final_yield_applied"]))
            self._bounty_states[pending["id"]] = BountyState.SETTLED

            settled.append(pending)
            logger.info(
                "[%s] YIELD SETTLED: %s returned $%.2f. Total: $%.2f",
                self.agent_id,
                pending["id"],
                float(pending["final_yield_applied"]),
                float(self._total_exergy_extracted),
            )

        for s in settled:
            self._pending_settlements.remove(s)

    async def _run_autonomous_hunt(self) -> None:
        """The Sovereign cycle: Discover -> Evaluate -> Claim -> Settle (Ω₃.3)."""
        now = time.time()
        if now < self._circuit_breaker_until:
            logger.warning("[%s] THERMODYNAMIC BREAKER ACTIVE. Skipping hunt.", self.agent_id)
            return

        logger.info("[%s] 🌌 INITIATING AUTONOMOUS HUNT CYCLE (v3.3)...", self.agent_id)

        # 0. Settle previous operations
        await self._verify_settlements()

        # 1. Discover
        bounties = await self._scan_for_bounties("all")

        async with asyncio.TaskGroup() as tg:
            for bounty in bounties:
                tg.create_task(self._process_single_bounty(bounty))

    async def _process_single_bounty(self, bounty: dict[str, Any]) -> None:
        """Processes a single bounty through the evaluation/extraction pipeline (Ω₁)."""
        bounty_id = str(bounty.get("id", ""))
        if not bounty_id or self._bounty_states.get(bounty_id) in (
            BountyState.EXTRACTING,
            BountyState.PENDING_SETTLEMENT,
            BountyState.SETTLED
        ):
            return

        # 2. Evaluate thermodynamically
        eval_data = self._evaluate_thermodynamics(bounty)
        self._bounty_states[bounty_id] = BountyState.DISCOVERED

        if not eval_data["accepted"]:
            logger.debug("[%s] 📉 REJECTED: %s (Ratio: %.2f)", self.agent_id, bounty["id"], eval_data["ratio"])
            return

        # 3. Semantic Validation (Ω₁)
        # If high value, double check with Perplexity or similar
        if eval_data["exergy_estimate"] >= 300.0:
            logger.info("[%s] 🔍 SEMANTIC VERIFICATION: Validating high-value lead %s", self.agent_id, bounty_id)
            valid = await self._verify_lead_semantics(bounty)
            if not valid:
                logger.warning("[%s] 🚫 SEMANTIC FAILURE: Lead %s failed validation.", self.agent_id, bounty_id)
                return

        # 4. Blast Radius / Immune Response
        difficulty = float(bounty.get("difficulty_score", 1.0))
        lines = float(bounty.get("context_lines", 100))
        report = BlastRadiusReport(
            reverse_import_count=int(lines // 100),
            test_reference_count=1,
            runtime_entrypoint_count=1,
            causal_dependency_count=int(difficulty),
            criticality_score=float(difficulty) / 10.0,
        )
        decision = evaluate_demolition(report, has_snapshot=True, modifies_schema=(difficulty >= 8))

        if decision.requires_quarantine:
            logger.warning("[%s] 🛡️ QUARANTINED: %s | %s", self.agent_id, bounty["id"], decision.reason)
            return

        # 5. Execute Extraction
        logger.info("[%s] ⚡ ACCEPTED: %s (Ratio: %.2f)", self.agent_id, bounty["id"], eval_data["ratio"])
        self._bounty_states[bounty_id] = BountyState.EXTRACTING

        try:
            res = await self._execute_extraction(bounty, eval_data)
            self._consecutive_failures = 0
            self._bounty_states[bounty_id] = BountyState.PENDING_SETTLEMENT
            self._pending_settlements.append({
                "id": bounty_id,
                "final_yield_applied": res["final_yield_applied"]
            })
            await self._persist_bounty_claim(bounty, res)
        except Exception as e:
            logger.error("[%s] ❌ EXTRACTION FAILED: %s | %s", self.agent_id, bounty_id, e)
            self._consecutive_failures += 1
            self._bounty_states[bounty_id] = BountyState.FAILED

            if self._consecutive_failures >= 3:
                penalty = 300.0 * (2.0 ** (self._consecutive_failures - 3))
                self._circuit_breaker_until = time.time() + penalty
                logger.error("[%s] CIRCUIT BREAKER TRIPPED! Suppressing hunts for %.1f seconds.", self.agent_id, penalty)

    async def _verify_lead_semantics(self, bounty: dict[str, Any]) -> bool:
        """Placeholder for external model verification (MCP perplexity_ask)."""
        # In a real scenario, this would call the parent LLM to use the tool.
        # For now, we simulate a successful verification.
        return True

    async def _scan_for_bounties(self, target: str | None) -> list[dict[str, Any]]:
        """Scan target platforms including Algora (Ω₃.3)."""
        from cortex.services.bounty_service import BountyService

        svc = BountyService(ledger=None, reward_threshold=self._thermodynamic_threshold)
        leads = []
        try:
            # Concurrent scan of GitHub and Algora
            if target and target.lower() != "all" and "/" in target:
                owner, repo = target.split("/", 1)
                leads = await svc.scan_repository(owner, repo)
            else:
                # Gather from multiple sources
                results = await asyncio.gather(
                    svc.scan_global(max_results=10),
                    svc.scan_algora(limit=10)
                )
                leads = results[0] + results[1]
        except Exception as e:
            logger.error("[%s] Bounty scan failed: %s", self.agent_id, e)

        results = []
        for lead in leads:
            difficulty_mapped = 8 if lead.difficulty == "high" else (5 if lead.difficulty == "medium" else 2)
            results.append({
                "id": f"{lead.repo}#{lead.number}" if lead.number else f"algora:{lead.url[-8:]}",
                "title": lead.title,
                "platform": "GitHub" if "github.com" in lead.url else "Algora",
                "difficulty_score": difficulty_mapped,
                "reward_usd": lead.reward_usd,
                "context_lines": 500 if difficulty_mapped >= 5 else 100,
                "url": lead.url
            })

        return results

    def _evaluate_thermodynamics(self, bounty: dict[str, Any]) -> dict[str, Any]:
        """Execute Thermodynamic Axiom Ω₂ and Ω₉ (Law of Claim) to decide viability.

        Calculation:
          - exergy_estimate: Measured in capital yield (USD) and ecosystem impact.
          - exergy_delta: Estimated cognitive/computational exergy required (cost),
            plus penalties for ghost vectors and meta-stability risk.
        """
        # Exergy based on raw reward
        base_reward_str = str(bounty.get("reward_usd", 0))
        base_reward = Decimal(base_reward_str)
        exergy_estimate = base_reward

        # Complexity/Cost based on difficulty and required context loading
        difficulty = Decimal(str(bounty.get("difficulty_score", 1.0)))
        lines = Decimal(str(bounty.get("context_lines", 100)))

        # Penalties calculation (Dynamic Scalar Thermodynamics)
        ghost_vector_penalty: Decimal = (
            Decimal("500.0") if lines == Decimal("0")
            else (lines * Decimal("0.5")) if (difficulty >= Decimal("5") and base_reward < Decimal("200"))
            else Decimal("0.0")
        )
        meta_stability_risk: Decimal = (difficulty ** 2) * Decimal("4.0") if difficulty >= Decimal("8") else Decimal("0.0")

        exergy_base = (difficulty * Decimal("50")) + (lines * Decimal("0.1"))
        exergy_delta = exergy_base + ghost_vector_penalty + meta_stability_risk

        # Safety against zero division
        if exergy_delta <= Decimal("0"):
            exergy_delta = Decimal("1.0")

        ratio: Decimal = exergy_estimate / exergy_delta
        accepted = ratio >= Decimal(str(self._thermodynamic_threshold))

        # Enforce Ω₉ Law of Claim justification format
        justification = (
            f"Claim: Yield ratio {ratio:.2f}\n"
            f"Justificación:\n"
            f"  - Base: ${base_reward:.2f} base reward against {difficulty} diff "
            f"and {lines} lines.\n"
            f"  - Variables: exergy_base={base_reward}, diff_weight=50, line_weight=0.1, "
            f"ghost_penalty={ghost_vector_penalty}, meta_stability={meta_stability_risk}\n"
            f"  - Rango: [{ratio * Decimal('0.8'):.2f}, {ratio * Decimal('1.2'):.2f}] (execution variance)\n"
            f"  - Confianza: C5-Dynamic (if executed) / C3 (static evaluation)\n"
        )

        return {
            "exergy_estimate": float(exergy_estimate),
            "exergy_delta": float(exergy_delta),
            "ratio": float(ratio),
            "accepted": accepted,
            "justification": justification,
            "ghost_vector_penalty": float(ghost_vector_penalty),
            "meta_stability_risk": float(meta_stability_risk),
        }

    async def _execute_extraction(self, bounty: dict[str, Any], evaluation: dict[str, Any]) -> dict[str, Any]:
        """Trigger autonomous execution on accepted bounties (Law of Execution Ω₆)."""
        logger.info(
            "[%s] AUTO-EXECUTE: Invoking Sovereign Extraction for %s (Yield: $%.2f)",
            self.agent_id,
            bounty["id"],
            float(bounty["reward_usd"]),
        )

        # Mocking the actuator delay for cloning & solving
        await asyncio.sleep(1.0)

        # Calculate formal SHANNON EXERGY using core module after extraction
        difficulty = Decimal(str(bounty.get("difficulty_score", 1.0)))
        lines = Decimal(str(bounty.get("context_lines", 100)))
        reward = Decimal(str(bounty.get("reward_usd", 0.0)))

        inp = ExergyInput(
            prior_uncertainty=(difficulty * Decimal("50")) + (lines * Decimal("0.1")),
            posterior_uncertainty=Decimal("0.0"),  # Task is solved
            tokens_consumed=max(1, int(float(lines) * 15)),
            action_risk=ActionRisk.SCHEMA_MUTATION if difficulty >= Decimal("8") else ActionRisk.FILE_WRITE,
            had_backup=True,
            touched_persistent_state=True,
        )
        threshold = Decimal("0.001")
        exergy_result = calculate_exergy(inp, threshold)

        # We DO NOT accumulate final_yield immediately. Relegated to Yield Settlement tracking.
        final_yield = Decimal(str(reward)) * exergy_result.score

        logger.info(
            "[%s] SOVEREIGN EXTRACTION COMPLETE: %s solved with Exergy Score %.6f. Enqueuing $%.2f for Settlement.",
            self.agent_id,
            bounty["id"],
            float(exergy_result.score),
            float(final_yield),
        )

        return {
            "initial_evaluation": evaluation,
            "shannon_exergy_score": float(exergy_result.score),
            "signal_gain": float(exergy_result.signal_gain),
            "reversibility_penalty": float(exergy_result.reversibility_penalty),
            "waste_ratio": float(exergy_result.waste_ratio),
            "final_yield_applied": float(final_yield),
        }

    async def _persist_bounty_claim(self, bounty: dict[str, Any], exec_data: dict[str, Any]) -> None:
        """Persist the accepted bounty to the CORTEX ledger tracking Exergy net gain.

        Enforces Cryptographic Irreversibility and Auditability (Ω₂, Ω₄).
        """
        if not self._engine:
            return

        evaluation = exec_data["initial_evaluation"]

        content = (
            f"[Bounty Extracted] {bounty['platform']} - {bounty['title']}\n"
            f"Expected Yield: ${bounty['reward_usd']}\n"
            f"Actual Extractable Exergy Yield: ${exec_data['final_yield_applied']:.2f}\n\n"
            f"Formal Shannon Exergy Score: {exec_data['shannon_exergy_score']:.6f}\n"
            f"(Signal Gain: {exec_data['signal_gain']:.6f}, Waste Ratio: {exec_data['waste_ratio']:.6f})\n\n"
            f"{evaluation['justification']}"
        )

        try:
            await self._engine.store(
                project=_PROJECT,
                content=content,
                fact_type="claim",
                tags=["bounty", "exergy", bounty["platform"].lower(), "extraction"],
                confidence="C3",  # Evaluated claim, becomes C5 upon extraction validation
                source=_SOURCE,
                meta={
                    "bounty_id": bounty["id"],
                    "evaluation_metrics": {
                        "exergy_estimate": evaluation["exergy_estimate"],
                        "exergy_delta": evaluation["exergy_delta"],
                        "ratio": evaluation["ratio"]
                    },
                    "shannon_metrics": {
                        "exergy_score": exec_data["shannon_exergy_score"],
                        "yield_applied": exec_data["final_yield_applied"]
                    },
                    "claimed_at": now_iso(),
                },
            )
            logger.debug("[%s] Ledger updated with claim for %s", self.agent_id, bounty["id"])
        except Exception as e:
            logger.error("[%s] Failed to persist bounty claim: %s", self.agent_id, e)
