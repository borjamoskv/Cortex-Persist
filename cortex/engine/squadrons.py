"""
CORTEX-SWARM-100: Squadron Definitions
P0: Integrity (30 workers) - Types, Linting, Synchronous tasks
P1: Kinetic (40 workers)   - APIs, Bounties, Moltbook
P2: Ghost Hunt (30 workers)- Dead code, Exergy cleanup
"""

import ast
import asyncio
import logging
import random
import re
import subprocess
from pathlib import Path

from cortex.engine.legion_vectors import RED_TEAM_SWARM
from cortex.engine.swarm import Squadron, SwarmAgent, SwarmSignal

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# P0: INTEGRITY SQUADRON
# -----------------------------------------------------------------------------


class IntegrityAgent(SwarmAgent):
    """P0 Agent: Runs linting, type checks, and static analysis."""

    async def execute(self, target: str) -> SwarmSignal:
        logger.info("[P0-INTEGRITY] %s static auditing: %s", self.agent_id, target)
        
        path = Path(target)
        if not path.exists():
            return SwarmSignal(self.agent_id, target, "VOID", {}, {})

        # Simulate Ruff check for MVP (Real ruff call would be here)
        # Note: In a production swarm, we'd use a shared ruff cache.
        findings = []
        if path.suffix == ".py":
            try:
                # Use ruff to check for errors
                proc = await asyncio.create_subprocess_exec(
                    "ruff", "check", target, "--select", "E,F,W", "--format", "json",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                stdout, _ = await proc.communicate()
                if stdout:
                    findings = [f"Linter Finding: {f['message']}" for f in re.finditer(r'\{.*\}', stdout.decode())]
            except Exception as e:
                logger.debug("IntegrityAgent linter fail: %s", e)

        status = "SUCCESS" if findings else "VOID"
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status=status,
            payload={"findings": findings},
            metrics={"time_ms": 150},
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
    """P1 Agent: Executes API calls, Moltbook traversal, Red Team attacks."""

    async def execute(self, target: str) -> SwarmSignal:
        logger.info("[P1-KINETIC] %s engaging target: %s", self.agent_id, target)
        
        # Select a random red team vector for this kinetic mission
        vector_name = random.choice(list(RED_TEAM_SWARM.keys()))
        vector = RED_TEAM_SWARM[vector_name]
        
        path = Path(target)
        content = ""
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8")
        
        findings = await vector.attack(content or target, {"intent": "legion_siege"})
        
        status = "SUCCESS" if findings else "VOID"
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status=status,
            payload={"vector": vector_name, "findings": findings},
            metrics={"latency_ms": 250},
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
    """P2 Agent: Scans for dead code and unreferenced abstractions."""

    async def execute(self, target: str) -> SwarmSignal:
        logger.info("[P2-GHOST_HUNT] %s extracting debt from: %s", self.agent_id, target)
        
        path = Path(target)
        if not path.exists() or not path.is_file():
            return SwarmSignal(self.agent_id, target, "VOID", {}, {})

        findings = []
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
            # Simple ghost hunt: Classes/Functions with 'TODO' or 'PLACEHOLDER' or no body
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef | ast.ClassDef):
                    if len(node.body) == 1 and isinstance(node.body[0], ast.Pass | ast.Constant):
                        findings.append(f"Ghost abstraction: `{node.name}` has no implementation.")
        except Exception as e:
            logger.debug("GhostHuntAgent parse fail: %s", e)

        status = "SUCCESS" if findings else "VOID"
        return SwarmSignal(
            agent_id=self.agent_id,
            target=target,
            status=status,
            payload={"ghosts": findings},
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
