# [C5-REAL] Exergy-Maximized
"""
Centauro Engine (LEGION-Ω)
Orchestration engine for the Sovereign Swarm. Implements Byzantine Consensus
and adaptive agent formations for Zero-Trust problem solving.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, TypedDict, cast

from pydantic import BaseModel, Field

from babylon60.crypto.hash_registry import cortex_hash
from babylon60.engine.cognitive.endocrine import ENDOCRINE, HormoneType
from babylon60.extensions.swarm.byzantine import ByzantineConsensus
from babylon60.swarm.aleph_omega import AxiomaticLeapEngine

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


logger = logging.getLogger("babylon60_extensions.swarm.centauro")


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
    TESTUDO = "TESTUDO"  # 15 agents, proactive defensive shell
    SANEDRIN = "SANEDRIN"  # 5 agents, Heterogeneous Supreme Quorum
    CENTURIA = "CENTURIA"  # 100 agents, Centuria Squad


class VirtualAgent:
    """A sovereign agent for the Centauro Swarm.

    Operates in two modes:
    - C5-REAL: when ``router`` is injected, dispatches to CortexLLMRouter.execute_resilient()
    - C4-SIM:  when ``router`` is None (default), uses deterministic mock for testing.
    """

    def __init__(
        self,
        agent_id: str,
        specialty: str = "general",
        execution_delay: float = 0.0,
        router: Any | None = None,  # pyright: ignore[reportUndefinedVariable]
    ) -> None:
        self.agent_id = agent_id
        self.specialty = specialty
        self.alive = True
        self._execution_delay = execution_delay
        self._router = router  # CortexLLMRouter | None
        self.formation: str | None = None

    async def execute(self, task_idx: str, prompt: str) -> str:
        """Execute a task. C5-REAL when router is set, C4-SIM otherwise."""
        if self._router is not None:
            # ── C5-REAL path ──────────────────────────────────────────
            try:
                from babylon60.extensions.llm._models import CortexPrompt, IntentProfile

                # War Council: Cognitive Diversity Mapping
                intent_map = {
                    "CODE": IntentProfile.CODE,
                    "SECURITY": IntentProfile.ARCHITECT,
                    "INFRA": IntentProfile.ARCHITECT,
                    "INTEL": IntentProfile.REASONING,
                    "DATA": IntentProfile.REASONING,
                    "CREATIVE": IntentProfile.CREATIVE,
                    "MARKETING": IntentProfile.CREATIVE,
                }
                agent_intent = intent_map.get(self.specialty, IntentProfile.GENERAL)

                cortex_prompt = CortexPrompt(
                    system_instruction=(
                        f"You are a sovereign {self.specialty} specialist agent "
                        f"(id={self.agent_id}). Answer concisely and deterministically."
                    ),
                    working_memory=[{"role": "user", "content": prompt}],
                    temperature=0.0,  # AX-I: determinismo estricto
                    intent=agent_intent,
                )
                result = await self._router.execute_resilient(cortex_prompt)
                # Result is Ok(str) | Err(str) - extract value regardless
                if hasattr(result, "ok") and result.ok is not None:
                    return str(result.ok)
                if hasattr(result, "err") and result.err is not None:
                    # [C5-REAL] Sanedrín Soft-Fallback
                    if (
                        hasattr(self, "formation")
                        and getattr(self, "formation", None) == "SANEDRIN"
                    ):
                        logger.warning(
                            "VirtualAgent %s: SANEDRIN cascade exhausted/404 for task %s. Reassigning role dynamically from %s to OSINT.",
                            self.agent_id,
                            task_idx,
                            self.specialty,
                        )
                        self.specialty = "OSINT"
                        cortex_prompt.system_instruction = f"You are a sovereign {self.specialty} specialist agent (id={self.agent_id}). Answer concisely and deterministically."
                        retry_result = await self._router.execute_resilient(cortex_prompt)
                        if hasattr(retry_result, "ok") and retry_result.ok is not None:
                            return str(retry_result.ok)

                    logger.warning(
                        "VirtualAgent %s: router returned error for task %s: %s - "
                        "falling back to C4-SIM stub.",
                        self.agent_id,
                        task_idx,
                        result.err,
                    )
                # Fallback: unwrap as string if Result type varies
                return str(result.ok if hasattr(result, "ok") else result)
            except Exception as exc:  # noqa: BLE001
                # [C5-REAL] Sanedrín Soft-Fallback on Exception
                if hasattr(self, "formation") and getattr(self, "formation", None) == "SANEDRIN":
                    logger.warning(
                        "VirtualAgent %s: SANEDRIN exception %s for task %s. Reassigning role dynamically from %s to INTEL.",
                        self.agent_id,
                        exc,
                        task_idx,
                        self.specialty,
                    )
                    self.specialty = "INTEL"
                    try:
                        cortex_prompt.system_instruction = f"You are a sovereign {self.specialty} specialist agent (id={self.agent_id}). Answer concisely and deterministically."
                        retry_result = await self._router.execute_resilient(cortex_prompt)
                        if hasattr(retry_result, "ok") and retry_result.ok is not None:
                            return str(retry_result.ok)
                    except Exception as fallback_exc:  # noqa: BLE001
                        exc = fallback_exc

                import logging

                logging.getLogger(__name__).exception(
                    f"[P0] CORTEX-TAINT: Fallo no controlado en Swarm cortex_extensions/swarm/centauro_engine.py - {exc}"
                )
                logger.warning(
                    "VirtualAgent %s: C5-REAL dispatch failed (%s) - "
                    "degrading to C4-SIM for task %s.",
                    self.agent_id,
                    exc,
                    task_idx,
                )

        # ── C4-SIM path (testing scaffold / router unavailable) ───────
        if self._execution_delay > 0:
            await asyncio.sleep(self._execution_delay)
        return f"[C4-SIM] Result for {task_idx} - {self.specialty} Operation '{prompt}' completed"


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
        Formation.TESTUDO: 15,
        Formation.SANEDRIN: 5,
        Formation.CENTURIA: 100,
    }

    def __init__(self, tolerance: float = 0.67, router: Any | None = None):
        self.consensus = ByzantineConsensus(tolerance_threshold=tolerance)
        self.agents: dict[str, VirtualAgent] = {}
        self._active_missions: dict[str, asyncio.Future[CentauroMissionResult]] = {}
        self._aleph = AxiomaticLeapEngine()
        self.router = router

    def spawn_squad(self, size: int, formation: str = Formation.BLITZ) -> dict[str, VirtualAgent]:
        """Spawn a squad of virtual agents with specialized focus."""
        squad = {}
        for i in range(size):
            agent_id = f"legionnaire_{len(self.agents) + 1}"
            specialty = self._get_specialty(i, formation)
            agent = VirtualAgent(agent_id, specialty=specialty, router=self.router)
            agent.formation = formation
            self.agents[agent_id] = agent
            self.consensus.register_node(agent_id, initial_reputation=1.0)
            squad[agent_id] = agent
        return squad

    def _get_specialty(self, index: int, formation: str) -> str:
        """Determines agent specialty based on formation and index. (O(1) Selection)"""
        if formation == Formation.GHOST:
            return "CODE"
        elif formation in (Formation.SPECTRE, Formation.BLITZ):
            _roles = ["INTEL", "CODE", "SECURITY"]
            return _roles[index % 3]
        elif formation == Formation.SENTINEL:
            _roles = ["INTEL", "CODE", "SECURITY", "DATA"]
            return _roles[index % 4]
        elif formation in (Formation.ORACLE, Formation.SANEDRIN):
            _roles = ["INTEL", "CODE", "SECURITY", "DATA", "INFRA"]
            return _roles[index % 5]
        elif formation == Formation.OUROBOROS:
            _roles = ["INTEL", "CODE", "SECURITY", "DATA", "INFRA", "CODE"]
            return _roles[index % 6]
        elif formation == Formation.PHALANX:
            return "SECURITY" if index % 2 == 0 else "CODE"
        elif formation == Formation.TESTUDO:
            _roles = ["SECURITY", "INFRA", "CODE"]
            return _roles[index % 3]
        return self.SPECIALISTS[index % len(self.SPECIALISTS)]

    async def _run_consensus(
        self,
        squad: dict[str, VirtualAgent],
        mission: str,
    ) -> tuple[str | None, int]:
        """Execute agents and race for Byzantine consensus (Ω₃ Quorum).

        Returns:
            (winning_proposal, agents_used) - proposal is None if consensus failed.
        """
        proposals: dict[str, str] = {}

        # C5-REAL Concurrency Protection Gate (99.99% Resilience)
        is_local = True
        if self.router is not None:
            try:
                providers = [self.router.primary] + self.router.fallbacks
                is_local = all(
                    getattr(p, "_provider", "") in ["ollama", "lmstudio"]
                    or "localhost" in getattr(p, "_base_url", "")
                    or "127.0.0.1" in getattr(p, "_base_url", "")
                    for p in providers
                )
            except Exception:  # noqa: BLE001
                is_local = True

        concurrency_limit = 4 if is_local else 50
        sem = asyncio.Semaphore(concurrency_limit)

        async def _run_agent(a_id: str, a: VirtualAgent) -> tuple[str, str | Exception]:
            async with sem:
                try:
                    return (a_id, await a.execute("M-01", mission))
                except Exception as exc:  # noqa: BLE001
                    import logging

                    logging.getLogger(__name__).exception(
                        f"[P0] CORTEX-TAINT: Fallo no controlado en Swarm cortex_extensions/swarm/centauro_engine.py - {exc}"
                    )
                    return (a_id, exc)

        # Must wrap in asyncio.create_task so they can be explicitly cancelled later
        agent_tasks = [
            asyncio.create_task(_run_agent(a_id, agent)) for a_id, agent in squad.items()
        ]

        winning = None
        for future in asyncio.as_completed(agent_tasks):
            agent_id, result = await future
            if isinstance(result, Exception):
                continue

            str_result = cast(str, result)
            proposals[agent_id] = str_result
            winning = await self.consensus.execute_consensus(proposals, node_ids=list(squad.keys()))
            if winning:
                logger.info("⚔️ [QUORUM] Consensus achieved early! Bypassing trailing latency.")
                break

        # Cancel trailing coroutines to avoid leak (Ω₂)
        for t in agent_tasks:
            if isinstance(t, asyncio.Task) and not t.done():
                t.cancel()

        return winning, len(squad)  # type: ignore[type-error]

    async def engage(self, mission: str, formation: str = Formation.BLITZ) -> CentauroMissionResult:
        """Activate the Centauro protocol for a mission. (Axiom Ω₂: Multiplexed Execution)"""
        mission_hash = cortex_hash(f"{mission}:{formation}".encode())

        # --- Thermal Heat-Sink (Multiplexing) ---
        mission_hash_str = str(mission_hash)
        if mission_hash_str in self._active_missions:
            logger.info(
                "🔥 [HEAT-SINK] Joining existing swarm for mission hash: %s...", mission_hash_str
            )
            return await self._active_missions[mission_hash_str]

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
                logger.warning(
                    "🧬 [ENDOCRINE] High Adrenaline (%.2f). Forcing BLITZ formation.", adrenaline
                )
                formation = Formation.BLITZ

            size = self._FORMATION_SIZES.get(formation, 3)
            squad = self.spawn_squad(size, formation=formation)
            logger.info(
                "Spawned %d agents in %s formation. (Adrenaline: %.2f)",
                len(squad),
                formation,
                adrenaline,
            )

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
                    import logging

                    logging.getLogger(__name__).exception(
                        f"[P0] CORTEX-TAINT: Fallo no controlado en Swarm cortex_extensions/swarm/centauro_engine.py - {leap_e}"
                    )
                    logger.error("ALEPH-Ω Leap failed: %s", leap_e)
                    result = {
                        "status": "failure",
                        "reason": (
                            "Byzantine Consensus Threshold Not Reached, tracking leap failure."
                        ),
                        "agents_used": agents_used,
                        "formation": formation,
                    }

            mission_future.set_result(result)
            return result

        except Exception as e:  # noqa: BLE001
            import logging

            logging.getLogger(__name__).exception(
                f"[P0] CORTEX-TAINT: Fallo no controlado en Swarm cortex_extensions/swarm/centauro_engine.py - {e}"
            )
            if not mission_future.done():
                mission_future.set_exception(e)
            raise
        finally:
            self._active_missions.pop(str(mission_hash), None)
