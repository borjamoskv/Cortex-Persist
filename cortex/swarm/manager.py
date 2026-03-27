from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any, cast

from cortex.engine.auth import ByzantineAuthLayer
from cortex.extensions.git.poet import CommitPoet
from cortex.ledger import SovereignLedger
from cortex.swarm.actuators.protocol import ActuatorProtocol, ActuatorResponse
from cortex.swarm.auditor import SwarmAuditor
from cortex.swarm.bus import AsyncSignalBus
from cortex.swarm.discovery import SkillRegistry
from cortex.swarm.guards.chaos import ChaosGuards
from cortex.swarm.guards.convergence import ConvergenceGuards
from cortex.swarm.guards.evolution import EvolutionGuard
from cortex.swarm.guards.exergy import SwarmExergyGovernor
from cortex.swarm.guards.privacy_gate import PrivacyGate
from cortex.swarm.reputation import AgentReputationSystem
from cortex.utils.pulmones_worker import PulmonesWorker

logger = logging.getLogger("cortex.swarm.manager")


class SwarmManager:
    """
    Sovereign Swarm Orchestrator (Ω-Architecture).

    Manages a collection of governed actuators, enforcing privacy
    guards and ledger logging for every external interaction.
    """

    # Patterns that require Byzantine authorization before dispatch
    _DESTRUCTIVE_TASK_SIGNALS: frozenset[str] = frozenset(
        {"rm ", "delete", "drop table", "truncate", "destroy", "wipe", "format", "purge"}
    )

    def __init__(
        self,
        ledger: SovereignLedger | None = None,
        bus: AsyncSignalBus | None = None,
        registry: SkillRegistry | None = None,
        start_pulmones: bool = False,
    ) -> None:
        self.actuators: dict[str, ActuatorProtocol] = {}
        self.registry = registry or SkillRegistry()
        self.bus = bus or AsyncSignalBus()
        self.auditor = SwarmAuditor(ledger) if ledger else SwarmAuditor()
        self.chaos_guards = ChaosGuards()
        self.privacy_gate = PrivacyGate()
        self.evolution_guard = EvolutionGuard()
        self.reputation = AgentReputationSystem()
        self.convergence = ConvergenceGuards(ledger)
        self.exergy_governor = SwarmExergyGovernor()
        self.ledger = ledger
        self.budget_limit = 1000.0
        self.current_spend = 0.0
        self._cache: dict[str, ActuatorResponse] = {}
        self._poet = CommitPoet()
        self._pulmones: PulmonesWorker | None = None
        self._pulmones_task: asyncio.Task[None] | None = None
        self._background_tasks: set[asyncio.Task] = set()

        if start_pulmones:
            self._pulmones = PulmonesWorker()
            logger.info(
                "SwarmManager: PulmonesWorker instantiated — call start_pulmones() to activate"
            )
        
        # Ω-Convergence: Subscribe to intelligence signals
        self.bus.subscribe("X_INTELLIGENCE_SIGNAL", self._handle_x_signal)

    def register_actuator(self, name: str, actuator: ActuatorProtocol) -> None:
        """Register a new governed actuator."""
        self.actuators[name] = actuator
        logger.info("SwarmManager: Registered actuator '%s' (%s)", name, actuator.provider_id)

    async def start_pulmones(self, poll_interval: float = 30.0) -> None:
        """Launch PulmonesWorker as a background asyncio Task (fire-and-forget)."""
        if self._pulmones is None:
            self._pulmones = PulmonesWorker()
        if self._pulmones_task is None or self._pulmones_task.done():
            should_start = True
        else:
            should_start = False

        if should_start:
            # Launch loop
            self._pulmones_task = asyncio.create_task(
                self._pulmones.start_loop(poll_interval),
                name="cortex.pulmones.daemon"
            )
            logger.info(
                "SwarmManager: 🫁 PulmonesWorker daemon started (poll=%.0fs)",
                poll_interval,
            )

    async def stop_pulmones(self) -> None:
        """Gracefully cancel the PulmonesWorker daemon."""
        if self._pulmones:
            self._pulmones.running = False

        task = self._pulmones_task
        if task is not None:
            if not task.done():
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):
                    pass
            self._pulmones_task = None
            logger.info("SwarmManager: 🛑 PulmonesWorker daemon stopped")

    async def broadcast(self, signal_name: str, payload: Any) -> None:
        """Broadcast a signal to the swarm bus using SwarmSignal (Ω₂)."""
        from .bus import SwarmSignal
        logger.info("SwarmManager: Broadcasting signal '%s'...", signal_name)
        signal = SwarmSignal(
            sender="manager",
            topic=signal_name,
            payload=payload if isinstance(payload, dict) else {"data": payload}
        )
        await self.bus.publish(signal)

    async def _resolve_actuator(self, identifier: str) -> ActuatorProtocol:
        """
        Autonomic Resolution: Resolves an identifier to an actuator.
        If not registered, it attempts to find it via SkillRegistry.
        """
        if identifier in self.actuators:
            return self.actuators[identifier]

        # Check Registry for skill match
        skill = self.registry.get_skill(identifier)
        if skill:
            logger.info("SwarmManager: Autonomic recruitment of skill '%s'...", identifier)
            # In a real scenario, we'd use the Factory here, but for loose coupling
            # we can instantiate a SkillActuator directly if we have the skill metadata.
            from .actuators.skill import SkillActuator
            actuator = SkillActuator(skill)
            self.register_actuator(identifier, actuator)
            return actuator

        raise ValueError(f"Unknown or unrecruited actuator: {identifier}")

    async def dispatch(
        self, actuator_name: str, task: str, context: dict[str, Any] | None = None
    ) -> ActuatorResponse:
        """
        Dispatch a task with autonomic resolution (Ω-Autonomic).
        """
        try:
            actuator = await self._resolve_actuator(actuator_name)
        except ValueError as e:
            return ActuatorResponse(content="", metadata={}, status="failed", error=str(e))

        ctx = context or {}

        # 1. Privacy Filter (Ω-Guard)
        sanitized = self.privacy_gate.validate_outgoing(task, ctx)
        task_text = sanitized["task"]

        # 2. Byzantine Auth Gate (Ω₁ — verify before trust)
        task_lower = task_text.lower()
        is_destructive = any(sig in task_lower for sig in self._DESTRUCTIVE_TASK_SIGNALS)
        if is_destructive:
            zenith_score = ctx.get("zenith_score", 0.0)
            approved = await ByzantineAuthLayer.acquire_lock(
                intent="SWARM_DESTRUCTIVE_ACTION",
                payload={"actuator": actuator_name, "task_snippet": task_text[:200]},
                zenith_score=zenith_score,
            )
            if not approved:
                logger.warning(
                    "SwarmManager: 🛑 ByzantineAuth DENIED task on '%s': %s",
                    actuator_name,
                    task_text[:80],
                )
                return ActuatorResponse(
                    content="",
                    metadata={},
                    status="failed",
                    error=(
                        "ByzantineAuthLayer: Destructive action denied. "
                        "Requires Zenith Consensus or operator approval."
                    ),
                )

        # 3. Evolution Guard (Ω-Mutation)
        if not self.evolution_guard.validate_mutation(task_text):
            logger.warning("SwarmManager: Evolution Guard blocked mutation in task '%s'", task_text)
            return ActuatorResponse(
                content="", metadata={}, status="failed", error="Evolution Guard blocked mutation."
            )

        # 4. Exergy Check: Ghost-Bypass Cache (O(1) Path)
        cache_key = hashlib.sha256(f"{actuator_name}:{task_text}".encode()).hexdigest()
        if cache_key in self._cache:
            logger.debug("SwarmManager: Exergy Hit (Ghost-Bypass) for %s", actuator_name)
            return self._cache[cache_key]

        # 4. Ledger Audit (Audit Trail pre-execution)
        ledger = self.ledger
        tx_hash = None
        if ledger:
            audit_data = {
                "actuator": actuator_name,
                "provider": actuator.provider_id,
                "task_hash": hashlib.sha256(task.encode()).hexdigest(),
                "sanitized_task_hash": hashlib.sha256(sanitized["task"].encode()).hexdigest(),
                "privacy_applied": True,
            }
            tx_hash = await ledger.record_transaction(
                project="swarm", action="dispatch_attempt", detail=audit_data
            )

        logger.info("SwarmManager: Dispatching to %s...", actuator_name)

        # 5. Execution via Governed Actuator
        try:
            response = await actuator.execute(task=sanitized["task"], context=sanitized["context"])

            if response["status"] == "success":
                # 5.1 Thermodynamic Audit (Ω₂)
                try:
                    await self.exergy_governor.audit_agent_work(
                        agent_id=actuator_name, 
                        content=response["content"]
                    )
                except ValueError:
                    # Content rejected after execution - downgrade response
                    return ActuatorResponse(
                        content="", 
                        metadata={}, 
                        status="failed", 
                        error="Ω₂ Violation: Decorative/Low-utility output rejected."
                    )

                # Calculate exergy if method exists (Ω₉)
                if hasattr(actuator, "calculate_exergy"):
                    exergy = actuator.calculate_exergy(sanitized["task"])
                    if not response.get("metadata"):
                        response["metadata"] = {}
                    response["metadata"]["exergy_score"] = float(exergy)
                    # Update reputation directly on dispatch success
                    profile = self.reputation.get_profile(actuator_name)
                    profile.record_success(tokens=100)  # Default tokens for dispatch

                # Persistence of success in cache for O(1) future dispatch
                self._cache[cache_key] = response

                # 6. Ledger Audit (Post-execution) with CommitPoet narrative (Ω₂)
                if ledger:
                    poet_message = self._poet.compose(
                        diff_summary=f"actuator={actuator_name} task={task_text[:60]}",
                        files=[actuator_name],
                        commit_type="feat",
                    )
                    await ledger.record_transaction(
                        project="swarm",
                        action="execution_success",
                        detail={
                            "actuator": actuator_name,
                            "correlation_hash": tx_hash,
                            "content_hash": hashlib.sha256(
                                response["content"].encode()
                            ).hexdigest(),
                            "poet_narrative": poet_message,
                        }
                    )

            if tx_hash:
                if not response.get("metadata"):
                    response["metadata"] = {}
                response["metadata"]["cortex_tx_hash"] = tx_hash

            return response
        except Exception as e:
            logger.exception("SwarmManager: Execution failed on %s", actuator_name)
            if ledger:
                await ledger.record_transaction(
                    project="swarm",
                    action="execution_failure",
                    detail={
                        "actuator": actuator_name,
                        "correlation_hash": tx_hash,
                        "error": str(e)
                    },
                )
            meta = {"cortex_tx_hash": tx_hash} if tx_hash else {}
            return ActuatorResponse(content="", metadata=meta, status="failed", error=str(e))

    async def list_available(self) -> list[str]:
        """Check health and list all available actuators."""
        available = []
        for name, actuator in self.actuators.items():
            if await actuator.health_check():
                available.append(name)
        return available

    async def deploy_squad(
        self, squad_type: str, task: str, count: int | None = None
    ) -> list[ActuatorResponse]:
        """
        Deploy a specialized squad (P0, P1, or P2) over a task (Ω-Swarm-100).
        Automatically recruits agents via the SkillRegistry if count is not met.

        Args:
            squad_type: One of 'P0' (Structural), 'P1' (Kinetic), 'P2' (Ghost).
            task: The natural language task for the squad.
            count: Number of agents. Defaults to skill-defined values (30, 40, 30).
        """
        squad_configs = {
            "P0": {"name": "Structural Integrity", "default_count": 30},
            "P1": {"name": "Kinetic Extraction", "default_count": 40},
            "P2": {"name": "Ghost Hunt", "default_count": 30},
        }

        if squad_type not in squad_configs:
            raise ValueError(f"Unknown squad type: {squad_type}. Use P0, P1, or P2.")

        cfg = squad_configs[squad_type]
        final_count = count or cfg["default_count"]

        logger.info(
            "SwarmManager: Deploying %s Squad (%s) with %d agents...",
            cfg["name"],
            squad_type,
            final_count,
        )

        # 1. Recruit agents (placeholder for finding agents with relevant skills)
        available = await self.list_available()
        # In a real Swarm-100, we'd dynamically spawn 100 virtual agents
        # Here we use available actuators and scale them if needed.
        # Shard counts
        target_count = int(final_count)

        if len(available) < target_count:
            logger.warning(
                "SwarmManager: Only %d agents available for %s squad. "
                "Recruiting virtual workers to reach %d...",
                len(available),
                squad_type,
                final_count,
            )
            # Expand available pool with virtual names for sharding
            while len(available) < target_count:
                available.append(f"virtual_{squad_type}_{len(available)}")

        # 2. Shard across the squad
        active_agents = cast(list[str], available)[:target_count]
        responses = await self.shard_task(active_agents, task)

        # 3. Record squad success in ledger
        if self.ledger:
            await self.ledger.record_transaction(
                project="swarm",
                action="squad_deployment",
                detail={
                    "squad_type": squad_type,
                    "squad_name": cfg["name"],
                    "agent_count": len(responses),
                    "task_snippet": str(task)[:100],
                },
            )

        return responses

    async def shard_task(self, agent_ids: list[str], task: str) -> list[ActuatorResponse]:
        """
        Execute a task across multiple agents in parallel (CORTEX-100).
        Prioritizes agents by Exergy Score (Ω-Reputation).
        Enforces Byzantine Fault Tolerance via ChaosGuards on critical paths.
        """
        if self.current_spend >= self.budget_limit:
            logger.warning("SwarmManager: Budget limit reached. Aborting mass execution.")
            return []

        ranked_ids = self.reputation.rank_agents(agent_ids)
        logger.info("SwarmManager: Sharding task to %d agents (Ranked)...", len(ranked_ids))

        # Ω₂: Enforce thermodynamic concurrency limit (Event Loop Asphyxiation Prevention)
        sem = asyncio.Semaphore(15)

        async def bounded_dispatch(aid: str, tsk: str) -> ActuatorResponse:
            async with sem:
                await self.exergy_governor.wait_for_coolant(aid)
                return await self.dispatch(aid, tsk)

        tasks = [bounded_dispatch(aid, task) for aid in ranked_ids]
            
        responses = await asyncio.gather(*tasks)

        # 1. Consensus Verification for critical tasks
        if self.chaos_guards.is_critical(task):
            if not await self.chaos_guards.validate_consensus(responses):
                logger.error(
                    "SwarmManager: Consensus FAIL for critical task '%s'. Aborting write.",
                    task,
                )
                return []
            logger.info("SwarmManager: Consensus REACHED for critical task.")

        # 2. Update Reputation & Budget
        for aid, resp in zip(ranked_ids, responses, strict=False):
            profile = self.reputation.get_profile(aid)
            meta = resp.get("metadata") or {}
            tokens_val = meta.get("tokens_used", 100)
            try:
                tokens = float(tokens_val)
            except (ValueError, TypeError):
                tokens = 100.0

            if resp["status"] == "success":
                profile.record_success(int(tokens))
            else:
                profile.record_failure(int(tokens))

            self.current_spend += tokens * 0.00001

        return list(responses)

    async def _handle_x_signal(self, signal: Any):
        """Ω-Convergence: Handle incoming X-Intelligence signals."""
        from .bus import SwarmSignal
        sig = cast(SwarmSignal, signal)
        exergy_score = sig.payload.get("exergy", 0.0)
        
        if exergy_score > 0.8:
            logger.info("SwarmManager: High-exergy signal detected on X. Triggering P2 Squad recruitment.")
            # Trigger a Ghost Hunt (P2) mission for the detected signal
            # We use a separate task to avoid blocking the bus
            t = asyncio.create_task(self.deploy_squad(
                squad_type="P2",
                task=f"Analyze and verify signal: {sig.payload.get('text')}",
                count=5
            ))
            self._background_tasks.add(t)
            t.add_done_callback(self._background_tasks.discard)
