from __future__ import annotations

import asyncio
import hashlib
import logging
from typing import Any

from cortex.ledger import SovereignLedger

from .actuators.protocol import ActuatorProtocol, ActuatorResponse
from .auditor import SwarmAuditor
from .bus import AsyncSignalBus
from .discovery import SkillRegistry
from .guards.chaos import ChaosGuards
from .guards.convergence import ConvergenceGuards
from .guards.evolution import EvolutionGuard
from .guards.privacy_gate import PrivacyGate
from .reputation import AgentReputationSystem

logger = logging.getLogger("cortex.swarm.manager")


class SwarmManager:
    """
    Sovereign Swarm Orchestrator (Ω-Architecture).

    Manages a collection of governed actuators, enforcing privacy
    guards and ledger logging for every external interaction.
    """

    def __init__(
        self,
        ledger: SovereignLedger | None = None,
        bus: AsyncSignalBus | None = None,
        registry: SkillRegistry | None = None,
    ) -> None:
        self.actuators: dict[str, ActuatorProtocol] = {}
        self.privacy_gate = PrivacyGate()
        self.evolution_guard = EvolutionGuard()
        self.chaos_guards = ChaosGuards()
        self.ledger = ledger
        self.bus = bus or AsyncSignalBus()
        self.registry = registry or SkillRegistry()
        self.reputation = AgentReputationSystem()
        self.convergence = ConvergenceGuards(ledger) if ledger else None
        self.budget_limit = 1000.0
        self.current_spend = 0.0
        self._cache: dict[str, ActuatorResponse] = {}

        if ledger:
            self.auditor = SwarmAuditor(ledger)
            logger.info("SwarmManager: Recursive Auditor online (Ω-Singularity)")

    def register_actuator(self, name: str, actuator: ActuatorProtocol) -> None:
        """Register a new governed actuator."""
        self.actuators[name] = actuator
        logger.info("SwarmManager: Registered actuator '%s' (%s)", name, actuator.provider_id)

    async def broadcast(self, signal_name: str, payload: Any) -> None:
        """Broadcast a signal to the swarm bus using SwarmSignal (\u03a9\u2082)."""
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
            return ActuatorResponse(content="", status="failed", error=str(e))

        ctx = context or {}

        # 1. Privacy Filter (Ω-Guard)
        sanitized = self.privacy_gate.validate_outgoing(task, ctx)
        task_text = sanitized["task"]
        
        # 2. Evolution Guard (Ω-Mutation)
        if not self.evolution_guard.validate_mutation(task_text):
            logger.warning("SwarmManager: Evolution Guard blocked mutation in task '%s'", task_text)
            return ActuatorResponse(
                content="", status="failed", error="Evolution Guard blocked mutation."
            )

        # 3. Exergy Check: Ghost-Bypass Cache (O(1) Path)
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
            tx_hash = ledger.record_transaction(
                project="swarm", action="dispatch_attempt", detail=audit_data
            )

        logger.info("SwarmManager: Dispatching to %s...", actuator_name)

        # 5. Execution via Governed Actuator
        try:
            response = await actuator.execute(task=sanitized["task"], context=sanitized["context"])

            if response["status"] == "success":
                # Calculate exergy if method exists (Ω₉)
                if hasattr(actuator, "calculate_exergy"):
                    exergy = actuator.calculate_exergy(sanitized["task"])
                    if not response.metadata:
                        response.metadata = {}
                    response.metadata["exergy_score"] = float(exergy)
                    # Update reputation directly on dispatch success
                    profile = self.reputation.get_profile(actuator_name)
                    profile.record_success(tokens=100) # Default tokens for dispatch

                # Persistence of success in cache for O(1) future dispatch
                self._cache[cache_key] = response

                # 6. Ledger Audit (Post-execution)
                if ledger:
                    ledger.record_transaction(
                        project="swarm",
                        action="execution_success",
                        detail={
                            "actuator": actuator_name,
                            "correlation_hash": tx_hash,
                            "content_hash": hashlib.sha256(response["content"].encode()).hexdigest(),
                        }
                    )
            
            # Inject correlation hash into response metadata
            if tx_hash:
                if not response.metadata:
                    response.metadata = {}
                response.metadata["cortex_tx_hash"] = tx_hash

            return response
        except Exception as e:
            logger.error("SwarmManager: Execution failed on %s: %s", actuator_name, e)
            if ledger:
                ledger.record_transaction(
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
        
        tasks = [self.dispatch(aid, task) for aid in ranked_ids]
        responses = await asyncio.gather(*tasks)
        
        # 1. Consensus Verification for critical tasks
        if self.chaos_guards.is_critical(task):
            if not await self.chaos_guards.validate_consensus(responses):
                logger.error("SwarmManager: Consensus FAIL for critical task '%s'. Aborting write.", task)
                return []
            logger.info("SwarmManager: Consensus REACHED for critical task.")

        # 2. Update Reputation & Budget
        for aid, resp in zip(ranked_ids, responses, strict=False):
            profile = self.reputation.get_profile(aid)
            tokens = resp.get("metadata", {}).get("tokens_used", 100)
            if resp["status"] == "success":
                profile.record_success(tokens)
            else:
                profile.record_failure(tokens)
            
            self.current_spend += tokens * 0.00001
        
        return list(responses)
