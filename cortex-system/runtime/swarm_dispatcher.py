"""
C5-REAL: Swarm Dispatcher & Collision Scheduler
Author: Borja Moskv / borjamoskv
"""

import asyncio
import random
import logging
from typing import Dict, Any, List
from policies.delegation_map import DelegationMap
from runtime.event_bus import EventBus

logger = logging.getLogger("cortex.system.swarm_dispatcher")

class SwarmDispatcher:
    def __init__(self, event_bus: EventBus, engine_instance):
        self.event_bus = event_bus
        self.engine = engine_instance

    async def schedule_collision(self, session_id: int, prompt: str) -> Dict[str, Any]:
        """
        Coordinates the collision flow: Generator -> Critic -> Assembler -> Distributor.
        Pipes state dynamically and records telemetry events and runs.
        """
        logger.info(f"Initiating swarm collision scheduling for session={session_id}")
        
        # --- AGENT A: Generator ---
        agent_a = DelegationMap.get_agent("A")
        await self.event_bus.publish("think", {"status": "generating", "prompt": prompt}, agent_a["key"])
        
        # Simulate ideation options (combining prompt with noise/entropy)
        t0_gen = int(asyncio.get_event_loop().time() * 1000)
        await asyncio.sleep(0.1) # Simulate CPU computation
        proposals = [
            {
                "artifact_key": f"prop_1_{session_id}_{int(t0_gen)}",
                "content": f"Aesthetic Recombination [chaos_mode]: {prompt} (Motif alpha-1)",
                "input_entropy": 0.65,
                "model_confidence": 0.78,
                "vector": [random.uniform(-0.1, 0.1) for _ in range(1536)]
            },
            {
                "artifact_key": f"prop_2_{session_id}_{int(t0_gen)}",
                "content": f"Structured Echo [neutral_mode]: {prompt} (Motif beta-5)",
                "input_entropy": 0.35, # low entropy -> potential warning/rejection
                "model_confidence": 0.90,
                "vector": [random.uniform(-0.1, 0.1) for _ in range(1536)]
            }
        ]
        t1_gen = int(asyncio.get_event_loop().time() * 1000)
        
        await self.event_bus.publish("event", {"proposals_count": len(proposals)}, agent_a["key"])
        
        # --- AGENT B: Critic (Adversarial Audit) ---
        agent_b = DelegationMap.get_agent("B")
        await self.event_bus.publish("think", {"status": "evaluating_proposals"}, agent_b["key"])
        
        accepted_proposals = []
        for prop in proposals:
            t0_crit = int(asyncio.get_event_loop().time() * 1000)
            # Evaluate using ArtistCortexEngine's thermodynamics calculation
            metrics = self.engine.calculate_thermodynamics(
                t0_ms=t0_gen,
                t1_ms=t1_gen,
                input_entropy=prop["input_entropy"],
                model_confidence=prop["model_confidence"]
            )
            
            # Record agent run
            cursor = self.engine.conn.cursor()
            cursor.execute("""
                INSERT INTO cortex_agents (agent_key, role, config_json)
                VALUES (?, ?, ?)
                ON CONFLICT(agent_key) DO UPDATE SET role=excluded.role
            """, (agent_b["key"], agent_b["role"], str(agent_b["config"])))
            
            # Determine alignment
            score = metrics["originality_raw"] * metrics["attention_yield"]
            
            if metrics["originality_raw"] >= 0.40:  # Threshold limit
                accepted_proposals.append((prop, metrics))
                await self.event_bus.publish("feedback", {"key": prop["artifact_key"], "score": score, "verdict": "pass"}, agent_b["key"])
            else:
                await self.event_bus.publish("reject", {"key": prop["artifact_key"], "score": score, "verdict": "fail"}, agent_b["key"])
                
        # --- AGENT C: Assembler ---
        agent_c = DelegationMap.get_agent("C")
        if not accepted_proposals:
            logger.warning("All proposals rejected by Critic B. Terminating collision.")
            await self.event_bus.publish("event", {"status": "collision_collapsed"}, agent_c["key"])
            return {"status": "collapsed", "accepted": 0}
            
        await self.event_bus.publish("think", {"status": "assembling_survivors"}, agent_c["key"])
        # Merge contents
        merged_content = "\n---\n".join([item[0]["content"] for item in accepted_proposals])
        assembled_key = f"art_{session_id}_{int(t0_gen)}"
        
        # --- AGENT D: Distributor ---
        agent_d = DelegationMap.get_agent("D")
        await self.event_bus.publish("think", {"status": "formatting_output"}, agent_d["key"])
        
        # Store as formal C5-REAL artifact using the ArtistCortexEngine
        first_prop, first_metrics = accepted_proposals[0]
        artifact_id = self.engine.insert_artifact(
            session_id=session_id,
            artifact_key=assembled_key,
            artifact_type="narrative",
            content=merged_content,
            aesthetic_hash=f"hash_{session_id}_3vec",
            t0_ms=t0_gen,
            t1_ms=t1_gen,
            input_entropy=first_prop["input_entropy"],
            model_confidence=first_prop["model_confidence"],
            vector_1536=first_prop["vector"]
        )
        
        await self.event_bus.publish("commit", {"artifact_id": artifact_id, "key": assembled_key}, agent_d["key"])
        
        return {
            "status": "committed",
            "artifact_id": artifact_id,
            "artifact_key": assembled_key,
            "content": merged_content,
            "metrics": first_metrics
        }
