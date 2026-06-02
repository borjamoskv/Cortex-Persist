import os
import time
import json
import logging
from typing import Dict, Any, List
from uess_swarm_scheduler import UESSSwarmScheduler, AgentRole
from uess_ast_mutation_engine import UESSAstMutationEngine

logger = logging.getLogger("cortex.uess_runtime")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class HybridLogicalClock:
    def __init__(self):
        self.time = int(time.time() * 1000)
        self.count = 0
        
    def tick(self) -> Dict[str, int]:
        now = int(time.time() * 1000)
        if now > self.time:
            self.time = now
            self.count = 0
        else:
            self.count += 1
        return {"time": self.time, "count": self.count}
        
    def to_string(self) -> str:
        t = self.tick()
        return f"{t['time']}-{t['count']}"

class UESSCortexRuntime:
    """
    C5-REAL CORTEX Runtime.
    Global synchronization bus that unifies Swarm scheduling, AST mutations,
    and event logging via Hybrid Logical Clocks.
    """
    def __init__(self, target_ast_file: str):
        self.hlc = HybridLogicalClock()
        self.scheduler = UESSSwarmScheduler(capacity=500)
        self.ast_engine = UESSAstMutationEngine(target_file=target_ast_file, scheduler=self.scheduler)
        self.event_log: List[Dict[str, Any]] = []
        self.log_file = "cortex_event_aof.jsonl"
        
    def _emit_event(self, event_type: str, agent_id: int, payload: Dict[str, Any]):
        event = {
            "hlc": self.hlc.to_string(),
            "type": event_type,
            "agent_id": agent_id,
            "payload": payload
        }
        self.event_log.append(event)
        with open(self.log_file, "a") as f:
            f.write(json.dumps(event) + "\n")
        logger.info(f"[EVENT] {event['hlc']} | {event_type} | Agent: {agent_id}")

    def loop_cycle(self):
        """Single tick of the CORTEX Runtime."""
        logger.info("--- START CORTEX CYCLE ---")
        
        # 1. Swarm Processing
        self.scheduler.tick()
        
        # 2. Log State
        global_entropy = self.scheduler.evaluate_swarm_entropy()
        self._emit_event("SWARM_TICK", 0, {"active_nodes": len(self.scheduler.nodes), "global_entropy": global_entropy})
        
        # 3. Opportunistic AST Mutation check (Simulated Auditor/Builder action)
        # If queue depth is high, simulate an AST optimization attempt
        for agent_id, node in self.scheduler.nodes.items():
            if not node.active or node.role != AgentRole.BUILDER:
                continue
                
            state = self.scheduler.umap.get_agent_state(agent_id)
            if state and state.get("queue_depth", 0.0) > 5.0:
                logger.info(f"Builder [{agent_id}] attempting AST mutation to relieve queue pressure.")
                # Simulated mutation string
                mutation_code = "def exergy_optimized():\n    return 1.618\n"
                result = self.ast_engine.execute_ast_mutation(agent_id, "exergy_optimized", mutation_code)
                self._emit_event("AST_MUTATE", agent_id, result)
                break # One mutation per cycle to prevent race conditions
                
        logger.info("--- END CORTEX CYCLE ---")

if __name__ == "__main__":
    # Create a dummy target for the runtime to operate on safely
    dummy_target = "runtime_dummy_ast.py"
    if not os.path.exists(dummy_target):
        with open(dummy_target, "w") as f:
            f.write("def exergy_optimized():\n    return 0\n")
            
    runtime = UESSCortexRuntime(target_ast_file=dummy_target)
    
    # Run 3 synchronized cycles
    for i in range(3):
        # Force a state that triggers a mutation
        runtime.scheduler.umap.update_control_vector(0, queue_depth=10.0, error_rate=0.0, causal_entropy=0.1, cpu_load=0.5)
        # Cycle
        runtime.loop_cycle()
        time.sleep(1)
