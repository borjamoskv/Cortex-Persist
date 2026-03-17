"""
CORTEX-SWARM-100: Squadron Definitions
P0: Integrity (30 workers) - Types, Linting, Synchronous tasks
P1: Kinetic (40 workers)   - APIs, Bounties, Moltbook
P2: Ghost Hunt (30 workers)- Dead code, Exergy cleanup
"""

import asyncio
import logging
import random
import re

from cortex.engine.swarm import Squadron, SwarmAgent, SwarmSignal

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# P0: INTEGRITY SQUADRON
# -----------------------------------------------------------------------------


class IntegrityAgent(SwarmAgent):
    """P0 Agent: Runs linting, type checks, and static analysis."""

    async def execute(self, target: str) -> SwarmSignal:
        # Simulate static analysis or linting check
        logger.info("[P0-INTEGRITY] %s static auditing: %s", self.agent_id, target)

        # Simulate work
        await asyncio.sleep(abs(random.gauss(0.1, 0.05)))

        # For now, simulate success or void (if target is empty)
        if not target.strip():
            return SwarmSignal(self.agent_id, target, "VOID", {}, {})

        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status="SUCCESS",
            payload={"lint_warnings": 0, "type_errors": 0},
            metrics={"time_ms": 120},
        )


class IntegritySquadron(Squadron):
    """P0 Squadron orchestrator (30 replicas)."""

    SQUAD_NAME = "P0_INTEGRITY"
    REPLICAS = 30

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        return IntegrityAgent(agent_id, self.bus, self.engine)

    async def _map(self, target_pattern: str | None = None) -> list[str]:
        # Expand target_pattern into multiple paths (Simulated for MVP)
        # Normally this would use glob or os.walk
        return [f"{target_pattern}/file_{i}.py" for i in range(100)] if target_pattern else []


# -----------------------------------------------------------------------------
# P1: KINETIC SQUADRON
# -----------------------------------------------------------------------------


class KineticAgent(SwarmAgent):
    """P1 Agent: Executes API calls, Moltbook traversal, Bounty hunting."""

    async def execute(self, target: str) -> SwarmSignal:
        logger.info("[P1-KINETIC] %s engaging API target: %s", self.agent_id, target)

        await asyncio.sleep(abs(random.gauss(0.3, 0.1)))  # Slower due to network

        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status="SUCCESS",
            payload={"yield_value": random.randint(10, 500)},
            metrics={"latency_ms": 300},
        )


class KineticSquadron(Squadron):
    """P1 Squadron orchestrator (40 replicas)."""

    SQUAD_NAME = "P1_KINETIC"
    REPLICAS = 40

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        return KineticAgent(agent_id, self.bus, self.engine)

    async def _map(self, target_pattern: str | None = None) -> list[str]:
        return (
            [f"https://api.moltbook.local/v1/bounty/{i}" for i in range(100)]
            if target_pattern
            else []
        )


# -----------------------------------------------------------------------------
# P2: GHOST HUNT SQUADRON
# -----------------------------------------------------------------------------


class GhostHuntAgent(SwarmAgent):
    """P2 Agent: Scans for dead code, unreferenced classes, and JIL abstractions."""

    async def execute(self, target: str) -> SwarmSignal:
        logger.info("[P2-GHOST_HUNT] %s extracting debt from: %s", self.agent_id, target)
        await asyncio.sleep(abs(random.gauss(0.2, 0.1)))

        drop = random.randint(0, 50)
        status = "SUCCESS" if drop > 0 else "VOID"

        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status=status,
            payload={"loc_drop": drop} if drop > 0 else {},
            metrics={},
        )


class GhostHuntSquadron(Squadron):
    """P2 Squadron orchestrator (30 replicas)."""

    SQUAD_NAME = "P2_GHOST_HUNT"
    REPLICAS = 30

    def _create_agent(self, agent_id: str) -> SwarmAgent:
        return GhostHuntAgent(agent_id, self.bus, self.engine)

    async def _map(self, target_pattern: str | None = None) -> list[str]:
        return [f"{target_pattern}/module_{i}.py" for i in range(100)] if target_pattern else []


# -----------------------------------------------------------------------------
# AUTONOMOUS ROUTER (Zero-Prompting)
# -----------------------------------------------------------------------------


class AutonomousRouter:
    """O(1) Autonomous Router to dispatch targets to the correct Squadron
    using weighted heuristics.
    """

    # Pre-compiled regex patterns for zero-latency matching (O(1))
    # P1: Network, APIs, External Targets
    P1_PATTERN = re.compile(
        r"^(https?://|wss?://|api\.|graphql\.|webhook|ftp://|sftp://)|"
        r"\b(moltbook|bounty|scrape|fetch|request)\b",
        re.IGNORECASE,
    )
    # P2: Technical Debt, Cleanup, Ghost code
    P2_PATTERN = re.compile(
        r"\b(dead|unused|legacy|cleanup|debt|ghost|jil|"
        r"refactor|purge|deprecated|remove|obsolete)\b",
        re.IGNORECASE,
    )
    # P0: Local files, generic static analysis
    P0_PATTERN = re.compile(
        r"\.(py|js|ts|jsx|tsx|go|rs|cpp|c|md|json|yaml|yml)$|"
        r"\b(lint|type|audit|test|format|check|validate)\b",
        re.IGNORECASE,
    )

    @staticmethod
    def route(target: str) -> list[type[Squadron]]:
        target_lower = target.strip().lower()

        # 1. Explicit intent override (e.g., "intent:ghost api.moltbook.local")
        intent_match = re.match(r"^intent:\s*([a-z0-9_]+)", target_lower)
        if intent_match:
            intent = intent_match.group(1)
            if intent in ("p1", "kinetic", "api", "network", "web"):
                return [KineticSquadron]
            if intent in ("p2", "ghost", "debt", "cleanup", "refactor"):
                return [GhostHuntSquadron]
            if intent in ("p0", "integrity", "lint", "audit", "test"):
                return [IntegritySquadron]

        # 2. Heuristic Scoring (O(1))
        scores: dict[type[Squadron], float] = {
            KineticSquadron: 0.0,
            GhostHuntSquadron: 0.0,
            IntegritySquadron: 0.0,
        }

        if AutonomousRouter.P1_PATTERN.search(target_lower):
            scores[KineticSquadron] += 1.0
        if AutonomousRouter.P2_PATTERN.search(target_lower):
            scores[GhostHuntSquadron] += 1.0
        if AutonomousRouter.P0_PATTERN.search(target_lower):
            scores[IntegritySquadron] += 1.0

        # Exact match boosts based on strict semantic meaning
        if target_lower in (".", "*", "all", "workspace", "repo", "project", "src"):
            scores[IntegritySquadron] += 2.0  # Entire workspace sweep overrides everything

        # Resolve top scorers
        max_score = max(scores.values())
        if max_score > 0:
            # Return all squadrons tied for the top score
            matched = [sq for sq, score in scores.items() if score == max_score]
            # Tie-breaker: If P0 tied with others, prioritize others
            # to avoid false positives on generic rules
            if len(matched) > 1 and IntegritySquadron in matched:
                matched.remove(IntegritySquadron)
            return matched

        # 3. Fallback to full swarm deployment if completely ambiguous (0.0 score)
        return [IntegritySquadron, KineticSquadron, GhostHuntSquadron]
