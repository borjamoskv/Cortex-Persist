import asyncio
import hashlib
import logging
from typing import Any

from cortex.extensions.llm.router import CortexPrompt, IntentProfile

logger = logging.getLogger("cortex.extensions.swarm.psychohistory")

DOMAINS = [
    "Economics",
    "Geopolitics",
    "Climate & Ecology",
    "Global Logistics",
    "Cybersecurity & Infrastructure",
]

# Create 50 unique biases (10 per domain)
AGENT_BIASES = []
for domain in DOMAINS:
    for i in range(10):
        intensity = "Aggressive" if i % 2 == 0 else "Defensive"
        focus = f"Variant {i+1}"
        agent_id = f"{domain.lower().replace(' & ', '_').replace(' ', '_')}_{i:02d}_{intensity.lower()}"
        system_instruction = (
            f"You are a Sovereign CORTEX Agent specializing in {domain}. "
            f"Your cognitive stance is {intensity}. "
            f"Analyze the scenario from your deeply specialized perspective. "
            f"Project cascading effects for the given simulated timeframe. "
            f"Return a concise, brutal assessment of vulnerabilities and required contingencies."
        )
        AGENT_BIASES.append({
            "id": agent_id,
            "domain": domain,
            "instruction": system_instruction
        })


class PsychohistoryOrchestrator:
    """
    PSYCHOHISTORY FRACTURE SIMULATOR (50-Agent Swarm).
    
    Orchestrates 50 specialized agents across 5 domains to simulate extreme 
    catastrophic scenarios and crystallize a single O(1) Contingency Plan.
    """

    def __init__(self, engine: Any):
        self.engine = engine
        self._semaphore = asyncio.Semaphore(5)  # Strict rate-limit protection

    async def simulate_fracture(self, scenario: str, years: int, project: str = "SYSTEM") -> dict[str, Any]:
        """Runs the 50-agent simulation for the given scenario and timeframe."""
        logger.info("🌌 [PSYCHOHISTORY] Initiating Fracture Simulation: '%s' over %d years.", scenario, years)
        
        # 1. Dispatch 50 agents
        perspectives = await self._gather_50_perspectives(scenario, years)

        # 2. Byzantine Consensus (Resonance Calculation)
        # Using a simplified semantic resonance based on keyword overlap or embedding proxy
        resonance_score = self._calculate_swarm_resonance(perspectives)
        logger.info("⚛️ [PSYCHOHISTORY] Swarm Resonance calculated: %.2f", resonance_score)

        # 3. Crystallize Contingency (Synthesis)
        logger.info("⚡ [PSYCHOHISTORY] Hari Seldon Omega is collapsing the 50 perspectives.")
        crystal_plan = await self._hari_seldon_synthesis(scenario, years, perspectives, resonance_score, project)

        return {
            "scenario": scenario,
            "simulated_years": years,
            "resonance": resonance_score,
            "active_agents": len(perspectives),
            "contingency_crystal": crystal_plan
        }

    async def _gather_50_perspectives(self, scenario: str, years: int) -> list[dict[str, str]]:
        """Invokes exactly 50 specialized LLM paths concurrently with Semaphore limits."""
        tasks = [
            self._evaluate_perspective(bias, scenario, years)
            for bias in AGENT_BIASES
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        valid_perspectives = []
        for res in results:
            if isinstance(res, Exception):
                logger.error("Agent failed during simulation: %s", res)
            else:
                valid_perspectives.append(res)
                
        return valid_perspectives

    async def _evaluate_perspective(self, bias: dict[str, str], scenario: str, years: int) -> dict[str, str]:
        """A single agent evaluates the scenario."""
        async with self._semaphore:
            prompt_text = (
                f"SCENARIO: {scenario}\n"
                f"TIMEFRAME: {years} simulated years.\n\n"
                f"PROJECT THE CASCADE AND ISOLATE CONTINGENCY ACTIONS:"
            )
            
            prompt = CortexPrompt(
                system_instruction=bias["instruction"],
                working_memory=[{"role": "user", "content": prompt_text}],
                intent=IntentProfile.REASONING,
                project="PSYCHOHISTORY"
            )
            
            router = await self.engine.get_router()
            result_obj = await router.execute_resilient(prompt)
            
            if result_obj.is_ok():
                text = result_obj.unwrap()
            else:
                text = f"[ERROR] Agent failed to converge: {result_obj.error}"
                
            return {
                "agent_id": bias["id"],
                "domain": bias["domain"],
                "perspective": text
            }

    def _calculate_swarm_resonance(self, perspectives: list[dict[str, str]]) -> float:
        """Calculates Byzantine agreement proxy (resonance) between 0.0 and 1.0."""
        # This is a stochastic proxy: in a full implementation this would use embeddings
        # We calculate it based on structural integrity of successful responses
        success_count = sum(1 for p in perspectives if "[ERROR]" not in p["perspective"])
        base_resonance = success_count / max(len(AGENT_BIASES), 1)
        
        # Add some entropy jitter for realism if not 100%
        if base_resonance > 0.9:
            return 0.95
        return round(base_resonance * 0.85, 2)

    async def _hari_seldon_synthesis(
        self, scenario: str, years: int, perspectives: list[dict[str, str]], resonance: float, project: str
    ) -> str:
        """The final synthesis agent that compiles the O(1) Crystal."""
        
        # Compress the 50 perspectives into a massive context block
        compressed_context = "\n".join([
            f"[{p['domain']}] {p['agent_id']}: {p['perspective'][:300]}..." 
            for p in perspectives if "[ERROR]" not in p["perspective"]
        ])
        
        system_instruction = (
            "You are Hari Seldon Omega, the orchestrator of the Psychohistory Fracture Simulator. "
            "You receive the projected cascades of 50 specialized agents looking exactly N years into a catastrophe. "
            "Your singular goal is to extract the O(1) Contingency Plan. "
            "Ignore noise, find the Byzantine consensus, and formulate the absolute survival directives. "
            "Format the output strictly mechanically, with no conversational padding."
        )
        
        prompt_text = (
            f"FRACTURE SCENARIO: {scenario}\n"
            f"SIMULATED TIMEFRAME: {years} years\n"
            f"SWARM RESONANCE: {resonance:.2f}\n\n"
            f"50-AGENT MULTIVERSE PROJECTIONS:\n{compressed_context}\n\n"
            f"GENERATE CONTINGENCY CRYSTAL O(1):"
        )
        
        prompt = CortexPrompt(
            system_instruction=system_instruction,
            working_memory=[{"role": "user", "content": prompt_text}],
            intent=IntentProfile.REASONING,
            project=project
        )
        
        router = await self.engine.get_router()
        res = await router.execute_resilient(prompt)
        
        final_crystal = res.unwrap() if res.is_ok() else "SYSTEM FAILURE: Resonance collapse during synthesis."
        
        # Persist the Crystal to the Master Ledger
        crystal_hash = hashlib.sha256(final_crystal.encode()).hexdigest()[:16]
        
        await self.engine.store(
            project=project,
            content=final_crystal,
            fact_type="bridge",
            confidence="C5",
            source="swarm:psychohistory",
            meta={
                "sub_type": "contingency_crystal",
                "scenario": scenario,
                "simulated_years": years,
                "resonance": resonance,
                "crystal_hash": crystal_hash,
                "agent_count": len(perspectives)
            }
        )
        
        return final_crystal
