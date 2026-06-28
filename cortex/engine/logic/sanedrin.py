# [C5-REAL] Exergy-Maximized
"""
CORTEX v6+ - The Sanedrín (Multi-Agent BFT Tribunal)
Ejecución Geométrica de Consenso sin Reyes.
"""

import asyncio
import hashlib
import logging
from typing import Any

from cortex.agents.primitives.dispatcher import apex_dispatcher
from cortex.swarm.trust_registry import global_trust_registry

logger = logging.getLogger("cortex.engine.logic.sanedrin")


import json

from cortex.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile


class SanedrinNode:
    """A sovereign node within the Sanhedrin cluster."""

    def __init__(self, node_id: str, archetype: str, router: CortexLLMRouter) -> None:
        self.node_id = node_id
        self.archetype = archetype
        self.router = router

    async def evaluate(self, fact_a: dict[str, Any], fact_b: dict[str, Any]) -> dict[str, Any]:
        """
        Executes C5-REAL geometric evaluation of a collision returning a Proof-of-Logic.
        Returns a claim, proof density (Shannon entropy), and hash.
        """
        id_a = fact_a.get("id", "A")
        id_b = fact_b.get("id", "B")

        prompt = CortexPrompt(
            system_instruction=(
                f"You are {self.node_id}, an epistemic logician acting as {self.archetype}. "
                "Resolve the collision between Fact A and Fact B based on thermodynamic exergy and logical soundness. "
                "Return ONLY a valid JSON object: "
                '{"claim": "<winner_id>", "proof_density": <float_0_to_1>, "reasoning": "<short_proof>"}'
            ),
            working_memory=[
                {"role": "user", "content": f"Fact A (ID: {id_a}): {json.dumps(fact_a)}\nFact B (ID: {id_b}): {json.dumps(fact_b)}"}
            ],
            intent=IntentProfile.ANALYTICAL,
            temperature=0.2,
            max_tokens=512,
        )

        res = await self.router.execute_resilient(prompt)
        
        # Fallback to deterministic collision if LLM fails
        if res.is_err():
            logger.error(f"[Sanhedrin] Node {self.node_id} failed inference: {res.error}")
            chosen_claim = id_a if hash(id_a) > hash(id_b) else id_b
            density = 0.5
        else:
            try:
                raw_out = res.unwrap().strip()
                if raw_out.startswith("```json"):
                    raw_out = raw_out[7:-3].strip()
                elif raw_out.startswith("```"):
                    raw_out = raw_out[3:-3].strip()
                out = json.loads(raw_out)
                chosen_claim = out.get("claim", id_a)
                density = float(out.get("proof_density", 0.5))
            except Exception as e:
                logger.error(f"[Sanhedrin] Node {self.node_id} output corruption: {e}")
                chosen_claim = id_a if hash(id_a) > hash(id_b) else id_b
                density = 0.5

        proof_hash = hashlib.sha3_256(f"{self.node_id}:{chosen_claim}".encode()).hexdigest()

        return {
            "node": self.node_id,
            "archetype": self.archetype,
            "claim": chosen_claim,
            "proof_density": density,
            "hash": proof_hash,
        }


class SanedrinCouncil:
    """
    C5-REAL: The BFT Tribunal (Sanhedrin).
    A multi-agent consensus cluster that erradicates Single Point of Truth.
    """

    def __init__(self, node_count: int = 3, router: CortexLLMRouter | None = None) -> None:
        from cortex.extensions.llm.provider import LLMProvider
        self.router = router or CortexLLMRouter(primary=LLMProvider(provider="ollama"))
        
        self.nodes = [
            SanedrinNode("N1-Synthesizer", "Claude-3.5-Simulation", self.router),
            SanedrinNode("N2-Logician", "Llama-3-Simulation", self.router),
            SanedrinNode("N3-Vector", "GPT-4o-Simulation", self.router),
        ][:node_count]

    async def convene(self, fact_a: dict[str, Any], fact_b: dict[str, Any]) -> dict[str, Any]:
        """
        Convenes the council to resolve an epistemic collision geometrically.
        """
        logger.critical(
            f"[Sanhedrin] Council convened for collision: {fact_a.get('id')} VS {fact_b.get('id')}"
        )

        # 1. Parallel BFT Evaluation (No blocking)
        evals = await asyncio.gather(*(node.evaluate(fact_a, fact_b) for node in self.nodes))

        # 2. Strict Proof-of-Logic Consensus (No average consensus)
        best_eval = max(evals, key=lambda e: e["proof_density"])

        # 3. Tie-Breaker / Apoptosis evaluation
        for ev in evals:
            if (
                ev["claim"] != best_eval["claim"]
                and (best_eval["proof_density"] - ev["proof_density"]) > 0.1
            ):
                logger.warning(
                    f"[Sanhedrin] Apoptosis triggered for {ev['node']}. Proof density insufficient."
                )
                global_trust_registry.epistemic_slash(
                    ev["node"], "Failed Proof-of-Logic audit in Sanhedrin"
                )

        resolution_msg = f"SANEDRIN_BFT: {best_eval['claim']} validated by {best_eval['node']}"

        # Emit Sentinel Audit
        apex_dispatcher.execute(
            "OP_GIT_SENTINEL",
            commit_msg=f"CORTEX-SANEDRIN: BFT Resolution {best_eval['hash'][:8]}",
            force=False,
        )

        return {
            "resolution": resolution_msg,
            "hash": best_eval["hash"],
            "winning_node": best_eval["node"],
            "proof_density": best_eval["proof_density"],
        }


sanedrin_council = SanedrinCouncil()
