"""
CORTEX V5 - Centauro Engine (LEGION-Ω)
Orchestration engine for the Sovereign Swarm. Implements Byzantine Consensus
and adaptive agent formations for Zero-Trust problem solving.
"""

import asyncio
import logging
from typing import TypedDict

from pydantic import BaseModel, Field

from cortex.engine.aleph_omega import AxiomaticLeapEngine
from cortex.engine.endocrine import ENDOCRINE, HormoneType
from cortex.swarm.byzantine import ByzantineConsensus

__all__ = [
    "CentauroEngine",
    "CentauroMissionResult",
    "Formation",
    "SubTask",
    "VirtualAgent",
]


class CentauroMissionResult(TypedDict, total=False):
    status: str
    solution: str
    reason: str
    agents_used: int
    formation: str


logger = logging.getLogger("cortex.swarm.centauro")


class SubTask(BaseModel):
    id: str
    description: str
    dependencies: list[str] = Field(default_factory=list)


class Formation:
    """Defines Swarm combative formations based on Legion Axioms."""

    BLITZ = "BLITZ"  # 3-5 agents, atomic tasks
    PHALANX = "PHALANX"  # 6-10 agents, audit/coverage
    SIEGE = "SIEGE"  # 8-15 agents, deep research
    HYDRA = "HYDRA"  # 10-20 agents, multi-domain
    ORACLE = "ORACLE"  # 3-5 agents, strategy
    PHOENIX = "PHOENIX"  # 5-8 agents, self-healing
    CHIMERA = "CHIMERA"  # 4-12 agents, innovation
    LEVIATHAN = "LEVIATHAN"  # 20-50 agents, massive sweep
    OUROBOROS = "OUROBOROS"  # 3-7 agents, self-evolution
    SENTINEL = "SENTINEL"  # Security/Infra monitoring
    SPECTRE = "SPECTRE"  # OSINT/Intel stealth
    GHOST = "GHOST"  # Single specialized agent


class VirtualAgent:
    """A simulated agent for the Centauro Swarm."""

    def __init__(self, agent_id: str, specialty: str = "general", execution_delay: float = 0.0):
        self.agent_id = agent_id
        self.specialty = specialty
        self.alive = True
        self._execution_delay = execution_delay

    async def execute(self, task_idx: str, prompt: str) -> str:
        # Simulate execution
        await asyncio.sleep(self._execution_delay)
        # Mock response: return a deterministic result so Byzantine consensus can pass
        return f"Result for {task_idx} - Operation {prompt} completed"


class CentauroEngine:
    """The Sovereign Swarm Core."""

    SPECIALISTS = [
        "CODE",
        "SECURITY",
        "INTEL",
        "DATA",
        "CREATIVE",
        "MARKETING",
        "OSINT",
        "INFRA",
    ]

    # Class-level formation → squad size map (O(1) lookup, immutable)
    _FORMATION_SIZES: dict[str, int] = {
        Formation.BLITZ: 3,
        Formation.PHALANX: 7,
        Formation.SIEGE: 12,
        Formation.HYDRA: 18,
        Formation.ORACLE: 5,
        Formation.PHOENIX: 8,
        Formation.CHIMERA: 10,
        Formation.LEVIATHAN: 35,
        Formation.OUROBOROS: 6,
        Formation.SENTINEL: 4,
        Formation.SPECTRE: 3,
        Formation.GHOST: 1,
    }

    def __init__(self, tolerance: float = 0.67):
        self.consensus = ByzantineConsensus(tolerance_threshold=tolerance)
        self.agents: dict[str, VirtualAgent] = {}
        self._active_missions: dict[str, asyncio.Future] = {}
        self._aleph = AxiomaticLeapEngine()

    def spawn_squad(self, size: int, formation: str = Formation.BLITZ) -> dict[str, VirtualAgent]:
        """Spawn a squad of virtual agents with specialized focus."""
        squad = {}
        for i in range(size):
            agent_id = f"legionnaire_{len(self.agents) + 1}"
            specialty = self._get_specialty(i, formation)
            agent = VirtualAgent(agent_id, specialty=specialty)
            self.agents[agent_id] = agent
            self.consensus.register_node(agent_id, initial_reputation=1.0)
            squad[agent_id] = agent
        return squad

    def _get_specialty(self, index: int, formation: str) -> str:
        """Determines agent specialty based on formation and index. (O(1) Selection)"""
        if formation == Formation.PHALANX:
            return "SECURITY" if index % 2 == 0 else "CODE"
        if formation == Formation.GHOST:
            return "CODE"
        return self.SPECIALISTS[index % len(self.SPECIALISTS)]

    async def _run_consensus(
        self,
        squad: dict[str, VirtualAgent],
        mission: str,
    ) -> tuple[str | None, int]:
        """Execute agents and race for Byzantine consensus (Ω₃ Quorum).

        Returns:
            (winning_proposal, agents_used) — proposal is None if consensus failed.
        """
        proposals: dict[str, str] = {}

        async def _run_agent(a_id: str, a: VirtualAgent) -> tuple[str, str | Exception]:
            try:
                return (a_id, await a.execute("M-01", mission))
            except Exception as exc:  # noqa: BLE001
                return (a_id, exc)

        agent_tasks = [_run_agent(a_id, agent) for a_id, agent in squad.items()]

        winning = None
        for future in asyncio.as_completed(agent_tasks):
            agent_id, result = await future
            if isinstance(result, Exception):
                continue
            proposals[agent_id] = result
            winning = self.consensus.execute_consensus(proposals)
            if winning:
                logger.info("⚔️ [QUORUM] Consensus achieved early! Bypassing trailing latency.")
                break

        # Cancel trailing coroutines to avoid leak (Ω₂)
        for t in agent_tasks:
            if isinstance(t, asyncio.Task) and not t.done():
                t.cancel()

        return winning, len(squad)

    async def engage(self, mission: str, formation: str = Formation.BLITZ) -> CentauroMissionResult:
        """Activate the Centauro protocol for a mission. (Axiom Ω₂: Multiplexed Execution)"""
        import hashlib

        mission_hash = hashlib.sha256(f"{mission}:{formation}".encode()).hexdigest()

        # --- Thermal Heat-Sink (Multiplexing) ---
        if mission_hash in self._active_missions:
            logger.info(
                "🔥 [HEAT-SINK] Joining existing swarm for mission hash: %s...", mission_hash[:8]
            )
            return await self._active_missions[mission_hash]  # type: ignore

        loop = asyncio.get_running_loop()
        mission_future: asyncio.Future[CentauroMissionResult] = loop.create_future()
        self._active_missions[mission_hash] = mission_future

        try:
            logger.info(
                "Initiating LEGION Protocol. Mission: %s | Formation: %s", mission, formation
            )
            # 🧬 Endocrine modulation: High ADRENALINE forces BLITZ regardless of intention
            adrenaline = ENDOCRINE.get_level(HormoneType.ADRENALINE)
            if adrenaline > 0.7 and formation not in [Formation.BLITZ, Formation.GHOST]:
                logger.warning("🧬 [ENDOCRINE] High Adrenaline (%.2f). Forcing BLITZ formation.", adrenaline)
                formation = Formation.BLITZ

            size = self._FORMATION_SIZES.get(formation, 3)
            squad = self.spawn_squad(size, formation=formation)
            logger.info("Spawned %d agents in %s formation. (Adrenaline: %.2f)", len(squad), formation, adrenaline)

            winning, agents_used = await self._run_consensus(squad, mission)

            result: CentauroMissionResult
            if winning:
                logger.info("Consensus Achieved (UNANIMOUS or MAJORITY).")
                # 🧬 Dopamine Reward
                ENDOCRINE.pulse(HormoneType.DOPAMINE, 0.1, reason="Consensus Success")
                result = {
                    "status": "success",
                    "solution": winning,
                    "agents_used": agents_used,
                    "formation": formation,
                }
            else:
                ENDOCRINE.pulse(HormoneType.CORTISOL, 0.2, reason="Consensus Failed")
                logger.warning("Consensus Failed (DEADLOCK or SPLIT). Triggering ALEPH-Ω Leap...")
                try:
                    leap = await self._aleph.execute_leap(mission)
                    result = {
                        "status": "aleph_breakthrough",
                        "solution": leap["solution"],
                        "agents_used": agents_used,
                        "formation": f"{formation}+ALEPH",
                        "reason": f"Paradigm Shift: {leap['paradigm_shift']}",
                    }
                except Exception as leap_e:  # noqa: BLE001
                    logger.error("ALEPH-Ω Leap failed: %s", leap_e)
                    result = {
                        "status": "failure",
                        "reason": "Byzantine Consensus Threshold Not Reached, tracking leap failure.",
                        "agents_used": agents_used,
                        "formation": formation,
                    }

            mission_future.set_result(result)
            return result

        except Exception as e:  # noqa: BLE001
            if not mission_future.done():
                mission_future.set_exception(e)
            raise
        finally:
            self._active_missions.pop(mission_hash, None)
