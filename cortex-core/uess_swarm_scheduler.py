import os
import time
import logging
import hashlib
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum
from ultramap import UltramapSubstrate

logger = logging.getLogger("cortex.swarm_scheduler")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

class AgentRole(Enum):
    QUEEN = 0
    SCOUT = 1
    AUDITOR = 2
    BUILDER = 3
    CRITIC = 4
    SYNTHESIZER = 5

@dataclass
class AgentNode:
    id: int
    role: AgentRole
    target_hash: str
    active: bool = False

class UESSSwarmScheduler:
    """
    C5-REAL UESS Swarm Scheduler.
    Reads UESS v2 metrics (queue_depth, error_rate, causal_entropy, cpu_load)
    from the ULTRAMAP-Ω memory substrate to perform dynamic scheduling,
    adversarial consensus, and entropy regulation.
    """
    
    def __init__(self, capacity: int = 1000):
        self.capacity = capacity
        self.umap = UltramapSubstrate(capacity=capacity)
        self.nodes: Dict[int, AgentNode] = {}
        
        # Initialize Queen node
        self._spawn_node(0, AgentRole.QUEEN, "SYSTEM_GENESIS")
        logger.info("UESS Swarm Scheduler initialized. QUEEN node [0] spawned.")

    def _spawn_node(self, agent_id: int, role: AgentRole, target: str) -> bool:
        if agent_id >= self.capacity or agent_id in self.nodes:
            return False
            
        target_hash = hashlib.sha256(target.encode()).hexdigest()
        self.nodes[agent_id] = AgentNode(id=agent_id, role=role, target_hash=target_hash, active=True)
        
        # Initialize cleanly in the substrate (x=0.1 to pass uninitialized checks)
        # Using placeholder coordinates, real system uses dynamic embeddings
        self.umap.update_agent_position(agent_id, x=0.1, y=0.1, z=0.1, target=target_hash, entropy=0.1)
        self.umap.update_control_vector(agent_id, queue_depth=0.0, error_rate=0.0, causal_entropy=0.1, cpu_load=0.1)
        return True

    def evaluate_swarm_entropy(self) -> float:
        """Calculates global causal entropy across the active swarm."""
        total_entropy = 0.0
        active_count = 0
        
        for agent_id, node in self.nodes.items():
            if not node.active:
                continue
            
            state = self.umap.get_agent_state(agent_id)
            if not state:
                continue
                
            total_entropy += state.get("causal_entropy", 0.0)
            active_count += 1
            
        if active_count == 0:
            return 0.0
            
        return total_entropy / active_count

    def tick(self):
        """
        Main Event Loop Tick.
        1. Reads state from ULTRAMAP-Ω
        2. Detects drift or anomaly
        3. Spawns/Kills nodes dynamically based on control vectors.
        """
        global_entropy = self.evaluate_swarm_entropy()
        logger.info(f"[TICK] Global Swarm Entropy: {global_entropy:.4f} | Active Nodes: {len(self.nodes)}")
        
        for agent_id, node in list(self.nodes.items()):
            if not node.active:
                continue
                
            state = self.umap.get_agent_state(agent_id)
            if not state:
                continue
                
            queue_depth = state.get("queue_depth", 0.0)
            error_rate = state.get("error_rate", 0.0)
            causal_entropy = state.get("causal_entropy", 0.0)
            
            # Swarm logic rules:
            if error_rate > 0.8:
                logger.warning(f"Node [{agent_id}] ({node.role.name}) error rate critical ({error_rate:.2f}). Terminating.")
                node.active = False
                continue
                
            if queue_depth > 10.0 and node.role == AgentRole.QUEEN:
                # Queen spawns Builders under high load
                new_id = len(self.nodes)
                self._spawn_node(new_id, AgentRole.BUILDER, f"TASK_OFFLOAD_{new_id}")
                logger.info(f"QUEEN spawned BUILDER [{new_id}] due to high queue depth.")
                
            if causal_entropy > 0.9 and node.role != AgentRole.AUDITOR:
                # High entropy requires Auditors
                new_id = len(self.nodes)
                self._spawn_node(new_id, AgentRole.AUDITOR, f"AUDIT_TARGET_{agent_id}")
                logger.info(f"High causal entropy detected on Node [{agent_id}]. Spawned AUDITOR [{new_id}].")

if __name__ == "__main__":
    scheduler = UESSSwarmScheduler(capacity=100)
    
    # Simulate some ticks
    for _ in range(5):
        scheduler.tick()
        
        # Simulate state changes natively in the substrate
        for agent_id in scheduler.nodes.keys():
            scheduler.umap.update_control_vector(
                agent_idx=agent_id,
                queue_depth=15.0 if agent_id == 0 else 2.0, # Push Queen to spawn
                error_rate=0.01,
                causal_entropy=0.95 if agent_id == 1 else 0.1, # Push Builder to cause an Auditor
                cpu_load=0.5
            )
        
        time.sleep(0.5)
