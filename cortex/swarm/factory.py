from __future__ import annotations

import asyncio
import logging
from typing import Any

from cortex.extensions.llm.router import CortexLLMRouter
from cortex.swarm.actuators.llm import LLMActuator
from cortex.swarm.actuators.skill import SkillActuator
from cortex.swarm.manager import SwarmManager

logger = logging.getLogger("cortex.swarm.factory")


class SwarmFactory:
    """
    Sovereign Specialist Recruiter (CORTEX-100 v5.6).
    Dynamically spawns P0, P1, and P2 agents with real Skill and LLM actuators.
    """

    def __init__(
        self,
        manager: SwarmManager,
        router: CortexLLMRouter | None = None,
    ) -> None:
        self.manager = manager
        self.bus = manager.bus
        self.registry = manager.registry
        self.router = router
        
        # Avoid redundant scanning (O(N) reduction)
        if not getattr(self.registry, "is_scanned", False):
            self.registry.scan()

        self._capability_cache: dict[str, str] = {}
        self._quadrants: dict[str, dict[str, Any]] = {
            "P0": {
                "role": "Structural Integrity",
                "categories": ["performance", "quality", "security", "audit", "linting"],
                "intent": "code_review_integrity",
                "description": "Ω-P0: Structural integrity & health audit. 30 Agents.",
                "target_size": 30,
                "exergy_target": 12.5,
            },
            "P1": {
                "role": "Kinetic Extraction",
                "categories": ["automation", "recruitment", "capital", "api", "action"],
                "intent": "autonomous_work_extraction",
                "description": "Ω-P1: Massive capital/exergy extraction. 40 Agents.",
                "target_size": 40,
                "exergy_target": 45.0,
            },
            "P2": {
                "role": "Ghost Hunt",
                "categories": ["maintenance", "optimization", "cleanup"],
                "intent": "entropy_reduction",
                "description": "Ω-P2: Entropy reduction & system purification. 30 Agents.",
                "target_size": 30,
                "exergy_target": 8.0,
            },
        }

    async def recruit_squad(self, quadrant: str, size: int = 5) -> list[str]:
        """
        Recruit a squad of specialized agents for a quadrant.
        Integrates LLM reasoning with Discovery-based skills.
        """
        if quadrant not in self._quadrants:
            raise ValueError(f"Unknown Tactical Quadrant: {quadrant}")

        spec = self._quadrants[quadrant]
        
        # Discover matching skills
        matching_skills = []
        for cat in spec["categories"]:
            matching_skills.extend(self.registry.list_by_category(cat))

        async def _enlist_agent(index: int) -> str:
            agent_id = f"{quadrant}-{index:03d}"
            # Spawn a Leader (LLM-backed) for the first agent
            if index == 0 and self.router:
                config = getattr(self.router, "default_config", {}) or {}
                model_id = config.get("model", "gemini-3-pro")
                provider = config.get("provider", "google")
                
                actuator = LLMActuator(
                    self.router,
                    model_id=model_id,
                    intent=spec["intent"],
                    provider_name=provider,
                )
                self.manager.register_actuator(agent_id, actuator)
                logger.info("SwarmFactory: Enlisted LLM Leader '%s' for %s", agent_id, spec["role"])
            
            # Spawn Skill Specialists for the rest
            elif matching_skills:
                skill = matching_skills[index % len(matching_skills)]
                actuator = SkillActuator(skill)
                self.manager.register_actuator(agent_id, actuator)
                logger.info("SwarmFactory: Enlisted Skill Specialist '%s' (%s)", agent_id, skill.name)
            
            # Fallback to JIT specialist
            else:
                return await self._forge_jit_specialist(spec["intent"])
            
            return agent_id

        # Parallelize recruitment
        agent_ids = await asyncio.gather(*[_enlist_agent(i) for i in range(size)])

        # Record recruitment in Ledger (Ω₉ Claim)
        ledger = self.manager.ledger
        if ledger:
            exergy_yield = spec["exergy_target"] * len(agent_ids)
            ledger.record_transaction(
                project="swarm",
                action="squad_recruitment",
                detail={
                    "quadrant": quadrant,
                    "size": len(agent_ids),
                    "role": spec["role"],
                    "exergy_estimate": exergy_yield,
                    "mechanical_justification": (
                        f"Squad yield calculated as base_exergy ({spec['exergy_target']}) "
                        f"x squad_size ({len(agent_ids)}). Total estimate: {exergy_yield} exergy units. "
                        f"Recruitment latency reduced via parallel enlistment. "
                        f"Trust Level: C5-Dynamic (Verified Parallel Spawn)."
                    ),
                    "audit": "mechanical_justification_v5.6_optimized",
                },
            )

        return list(agent_ids)

    async def recruit_full_swarm(self) -> dict[str, list[str]]:
        """
        The Great Swarm Event (CORTEX-100).
        Recruits all three escuadrones simultaneously: 30(P0) + 40(P1) + 30(P2).
        """
        logger.info("SwarmFactory: Triggering THE GREAT SWARM (100 Agents)...")
        tasks = [
            self.recruit_squad("P0", size=30),
            self.recruit_squad("P1", size=40),
            self.recruit_squad("P2", size=30),
        ]
        results = await asyncio.gather(*tasks)
        
        # Explicit type hinting for linter
        squad_results: list[list[str]] = list(results) # type: ignore
        
        squads = {
            "P0": squad_results[0],
            "P1": squad_results[1],
            "P2": squad_results[2],
        }
        
        logger.info("SwarmFactory: 100 Agents recruited across %d squads (Ω-Structure).", len(squads))
        return squads

    async def recruit_by_capability(self, capability: str) -> str:
        """
        Autonomic Recruitment: Recruits the best agent for a specific capability.
        Returns the agent_id of the recruited specialist.
        """
        if capability in self._capability_cache:
            return self._capability_cache[capability]

        skills = self.registry.list_by_category(capability)
        if not skills:
            # Try keyword search
            skills = [s for s in self.registry.skills.values() if capability.lower() in s.name.lower()]

        if skills:
            skill = skills[0] # Best match
            agent_id = f"auto-{skill.name}"
            actuator = SkillActuator(skill)
            self.manager.register_actuator(agent_id, actuator)
            logger.info("SwarmFactory: Autonomic recruitment for capability '%s' -> %s", capability, agent_id)
            self._capability_cache[capability] = agent_id
            return agent_id
        
        # JIT Fallback logic (Ω₁)
        logger.info("SwarmFactory: Capability '%s' not found. Forging JIT specialist...", capability)
        return await self._forge_jit_specialist(capability)

    async def _forge_jit_specialist(self, capability: str) -> str:
        """Forges a temporary specialist via LLM reasoning when no skill exists."""
        agent_id = f"jit-{capability.replace(' ', '_')}"
        if agent_id in self._capability_cache:
            return agent_id

        if self.router:
            actuator = LLMActuator(self.router, model_id="gemini-3-pro", intent=f"jit_specialist_{capability}")
            self.manager.register_actuator(agent_id, actuator)
            self._capability_cache[capability] = agent_id
            return agent_id
        raise ValueError(f"No skill or LLM router available for capability: {capability}")

    def get_quadrant_skills(self, quadrant: str) -> list[str]:
        """Return names of available skills for a quadrant."""
        spec = self._quadrants.get(quadrant, {})
        categories = spec.get("categories", [])
        return [s.name for cat in categories for s in self.registry.list_by_category(cat)]
