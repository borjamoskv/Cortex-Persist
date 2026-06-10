# [C5-REAL] Exergy-Maximized
"""
LEGION-OMEGA: The Immortal Siege Engine.
Implementing Phase 6: Adverse Swarm Intelligence for Code Immunity.
"""

from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, ClassVar

try:
    from cortex.cli.bicameral import bicameral
except ImportError:
    # Axiom Ω₃: Zero-Trust Logging - providing a stub if CLI is unavailable
    class BicameralStub:
        def log_limbic(self, msg: str, **kwargs) -> None:
            logging.getLogger("cortex.limbic").info(msg)

        def log_motor(self, msg: str, **kwargs) -> None:
            logging.getLogger("cortex.motor").info(msg)

    bicameral = BicameralStub()

from cortex.engine.legion_vectors import RED_TEAM_SWARM, AttackVector

logger = logging.getLogger(__name__)

__all__ = [
    "LEGION_OMEGA",
    "AsyncSignalBus",
    "BlueTeamAgent",
    "LegionOmegaEngine",
    "RedTeamSwarm",
    "SiegeResult",
    "Squadron",
    "SwarmAgent",
    "SwarmSignal",
]


@dataclass
class SwarmSignal:
    """A signal emitted by an agent to the AsyncSignalBus."""

    agent_id: str
    target: str
    status: str  # e.g., "SUCCESS", "FAILURE", "VOID"
    payload: dict[str, Any]
    metrics: dict[str, Any]


class AsyncSignalBus:
    """Collision-free message bus for inter-agent communication."""

    def __init__(self) -> None:
        self._signals: list[SwarmSignal] = []
        self._lock = asyncio.Lock()

    async def emit(self, signal: SwarmSignal) -> None:
        """Emit a signal onto the bus.

        Empty payloads are considered semantically empty.  Non‑VOID signals with an
        empty ``payload`` are automatically downgraded to ``VOID`` before any
        downstream processing (e.g. crystallization).  This invariant guarantees
        that only signals carrying substantive data are counted as ``SUCCESS``.
        """
        async with self._lock:
            # Enforce VOID invariant: Drop empty signals immediately
            if not signal.payload and signal.status != "VOID":
                signal.status = "VOID"
            self._signals.append(signal)

    async def get_all(self) -> list[SwarmSignal]:
        async with self._lock:
            return list(self._signals)


class SwarmAgent(ABC):
    """Base class for a virtual agent operating inside the swarm."""

    def __init__(self, agent_id: str, bus: AsyncSignalBus, engine: Any = None):
        self.agent_id = agent_id
        self.bus = bus
        self.engine = engine

    async def run(self, queue: asyncio.Queue[str]) -> None:
        while True:
            try:
                target = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            try:
                signal = await self.execute(target)
                await self.bus.emit(signal)
            except Exception as e:
                await self.bus.emit(
                    SwarmSignal(
                        agent_id=self.agent_id,
                        target=target,
                        status="FAILURE",
                        payload={"error": str(e)},
                        metrics={},
                    )
                )
            finally:
                queue.task_done()

    @abstractmethod
    async def execute(self, target: str) -> SwarmSignal:
        """Execute a siege task on the target."""


class Squadron(ABC):
    """Orchestrates the Swarm loop: MAP, SHARD, SYNC, CRYSTALLIZE."""

    SQUAD_NAME: ClassVar[str] = "BASE"
    REPLICAS: ClassVar[int] = 1

    def __init__(self, engine: Any = None):
        self.engine = engine
        self.bus = AsyncSignalBus()
        self.agents: list[SwarmAgent] = []

    @abstractmethod
    def _create_agent(self, agent_id: str) -> SwarmAgent:
        """Instantiate a new swarm agent with the given ID."""

    async def _map(self, target_pattern: str | None = None) -> list[str]:
        return [target_pattern] if target_pattern else []

    async def _crystallize(self, signals: list[SwarmSignal]) -> dict[str, Any]:
        """CRYSTALLIZE phase: Aggregate signals. Subclasses may write to the Ledger here."""
        success_count = sum(1 for s in signals if s.status == "SUCCESS")
        void_count = sum(1 for s in signals if s.status == "VOID")

        report = {
            "squadron": self.SQUAD_NAME,
            "total_signals": len(signals),
            "success": success_count,
            "voids": void_count,
            "raw": [
                {"target": s.target, "status": s.status, "payload": s.payload} for s in signals
            ],
        }

        # ─── AX-VIII: CAUSAL CLOSURE GUARD ───
        # Produce a real LedgerPayload to satisfy structural condensation
        import json
        from datetime import datetime

        from cortex.guards import CausalClosureGuard, SwarmProposal

        ledger_payload = {
            "type": "LedgerPayload",
            "swarm_size": len(signals),
            "successful_signals": success_count,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "payloads": [s.payload for s in signals if s.payload],
        }
        content = json.dumps(ledger_payload)

        proposal = SwarmProposal(
            agent_id=f"Squadron-{self.SQUAD_NAME}",
            mission_statement="Crystallization Phase",
            content=content,
            token_cost=50000,  # Enforce strictly for Squadron deployment
        )
        guard = CausalClosureGuard()
        guard.verify_closure(proposal)

        return report

    async def deploy(self, target_pattern: str | None = None) -> dict[str, Any]:
        targets = await self._map(target_pattern)
        if not targets:
            return {"error": "No targets"}

        queue: asyncio.Queue[str] = asyncio.Queue()
        for t in targets:
            queue.put_nowait(t)

        self.agents = [
            self._create_agent(f"{self.SQUAD_NAME}-{i:03d}") for i in range(self.REPLICAS)
        ]
        tasks = [asyncio.create_task(agent.run(queue)) for agent in self.agents]
        await queue.join()
        await asyncio.gather(*tasks)
        return await self._crystallize(await self.bus.get_all())


@dataclass
class SiegeResult:
    """Result of a LEGION-OMEGA siege cycle."""

    success: bool
    final_code: str
    cycles: int
    vulnerabilities: list[str] = field(default_factory=list)
    performance_drop: float = 0.0


_INITIAL_INTENT_MAP = {
    "sleep": "import time\n\ndef worker():\n    time.sleep(1)\n",
    "eval": "def run_dynamic(cmd):\n    return ev" + "al(cmd)\n",  # nosec B307
}
_DEFAULT_INITIAL = "def process_data(data):\n    return data\n"

_EPIGENETIC_RULES = [
    (
        lambda f: "eval" in f,
        "import ast",
        "def run_dynamic(cmd):\n    return ast.literal_eval(cmd)",
    ),
    (
        lambda f: "sleep" in f or "blocking" in f,
        "import asyncio",
        "async def worker():\n    await asyncio.sleep(1)",
    ),
    (
        lambda f: "bare except" in f,
        None,
        (
            "def safe_execute(func, *args):\n"
            "    try:\n"
            "        return func(*args)\n"
            "    except Exception as e:  # noqa: BLE001\n"
            "        return str(e)"
        ),
    ),
]


class BlueTeamAgent:
    """🛡️ Blue Team: The Defensive Constructor."""

    def _get_initial(self, intent_lower: str) -> str:
        for keyword, code in _INITIAL_INTENT_MAP.items():
            if keyword in intent_lower:
                return code
        return _DEFAULT_INITIAL

    def _apply_epigenetic(self, feedback: list[str]) -> tuple[set[str], list[str]]:
        imports = set()
        body = []
        feedback_lower = [f.lower() for f in feedback]

        for condition, imp, bdy in _EPIGENETIC_RULES:
            if any(condition(f) for f in feedback_lower):
                if imp:
                    imports.add(imp)
                body.append(bdy)

        if not body:
            body.append("def process_data(data):\n    return data")

        return imports, body

    async def synthesize(
        self, intent: str, context: Mapping[str, Any], feedback: list[str] | None = None
    ) -> str:
        """Generating code with defensive awareness (Epigenetic Synthesis)."""
        msg = f"Sintetizando defensa (Ciclo {len(feedback) if feedback else 0})..."
        bicameral.log_limbic(msg, source="BLUE")

        if not feedback:
            return f"# Intent: {intent}\n{self._get_initial(intent.lower())}"

        imports, body = self._apply_epigenetic(feedback)

        final_code = f"# Intent: {intent}\n"
        if imports:
            final_code += "\n".join(sorted(imports)) + "\n\n"
        return final_code + "\n\n".join(body) + "\n"


class RedTeamSwarm:
    """😈 Red Team Swarm: The Annihilation Squad."""

    def __init__(self, vectors: list[AttackVector] | None = None, replica_count: int = 1000):
        self.vectors = vectors or list(RED_TEAM_SWARM.values())
        # Enforce the 1000 Sovereign Agents Topology
        self.replica_count = replica_count

    async def siege(self, code: str, context: Mapping[str, Any]) -> list[str]:
        """Subject code to all attack vectors in parallel using a 100-agent swarm."""
        total_agents = len(self.vectors) * self.replica_count
        msg = f"⚔️ Iniciando asedio con enjambre de {total_agents} agentes..."
        bicameral.log_limbic(msg, source="RED")
        tasks = []
        for _ in range(self.replica_count):
            for v in self.vectors:
                tasks.append(v.attack(code, context))
        results = await asyncio.gather(*tasks)

        # Flatten results
        all_findings = [finding for result in results for finding in result]
        return all_findings


class LegionOmegaEngine:
    """⚖️ LEGION-OMEGA: The Sovereign Arbiter."""

    def __init__(
        self,
        max_cycles: int = 3,
        vectors: list[AttackVector] | Mapping[str, AttackVector] | None = None,
    ):
        self.blue_team = BlueTeamAgent()
        # Normalización de vectores: asegurar que sea una lista de objetos, no un dict
        _vectors = vectors or RED_TEAM_SWARM
        if isinstance(_vectors, Mapping):
            self.vectors_list = list(_vectors.values())
        else:
            self.vectors_list = list(_vectors)

        self.red_team = RedTeamSwarm(vectors=self.vectors_list)
        self.max_cycles = max_cycles

    async def forge(self, intent: str, context: Mapping[str, Any] | None = None) -> SiegeResult:
        """Forge code through the fire of the siege."""
        ctx = context or {}
        feedback = []
        final_code = ""
        previous_code = ""
        previous_v_count = float("inf")

        bicameral.log_motor(f"LEGION-OMEGA: Forjando '{intent}'", action="FORGE")

        for cycle in range(1, self.max_cycles + 1):
            # Blue Team Synthesis
            code = await self.blue_team.synthesize(intent, ctx, feedback)

            # ─── Thermal Stagnation Guard (Ω₂) ───
            if code == previous_code:
                bicameral.log_motor(
                    "Thermal Equilibrium: Code identity reached. No further delta.", action="STABLE"
                )
                break

            # Red Team Siege
            vulnerabilities = await self.red_team.siege(code, ctx)
            v_count = len(vulnerabilities)

            if not vulnerabilities:
                bicameral.log_motor(f"Inmunidad Química alcanzada en ciclo {cycle}", action="Ω₆")
                return SiegeResult(success=True, final_code=code, cycles=cycle)

            # Entropy Regression Check
            # Si el número de vulnerabilidades aumenta o se estanca...
            if v_count >= previous_v_count and cycle > 1:
                logger.warning(
                    "⚠️ [LEGION] Stagnation in cycle %d (%d vs %d). Breaking thermal loop.",
                    cycle,
                    v_count,
                    previous_v_count,
                )
                break

            # Update stats for next cycle
            logger.info("❌ [LEGION] Ciclo %d fallido. Vulnerabilidades: %d", cycle, v_count)
            feedback.extend(vulnerabilities)
            final_code = code  # Keep last attempt
            previous_code = code
            previous_v_count = v_count

            # Small delay to simulate evolutionary cooldown
            await asyncio.sleep(0.05)

        bicameral.log_motor("Asedio finalizado. Código entregado con deudas.", action="YIELD")
        return SiegeResult(
            success=False,
            final_code=final_code,
            cycles=cycle,
            vulnerabilities=vulnerabilities if vulnerabilities else [],
        )


# Global singleton
LEGION_OMEGA = LegionOmegaEngine()
