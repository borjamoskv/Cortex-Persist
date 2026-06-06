import time
import logging
from typing import Dict, List, Any

logging.basicConfig(level=logging.INFO)

class CraniMemNode:
    def __init__(self, trace_id: str, content: str, utility_score: float):
        self.trace_id = trace_id
        self.content = content
        self.utility_score = utility_score
        self.timestamp = time.time()
        self.access_count = 0

class CraniMemSubstrate:
    """
    CraniMem: Cranial Inspired Gated and Bounded Memory.
    - Goal-conditioned gating
    - Utility tagging
    - Bounded episodic buffer
    - Scheduled consolidation loop
    """
    def __init__(self, buffer_limit: int = 100, consolidation_threshold: float = 0.8):
        self.episodic_buffer: List[CraniMemNode] = []
        self.knowledge_graph: Dict[str, CraniMemNode] = {}
        self.buffer_limit = buffer_limit
        self.consolidation_threshold = consolidation_threshold
    
    def gate_and_inject(self, trace_id: str, content: str, goal_alignment: float, utility_score: float):
        """Goal-conditioned gating for incoming memory traces."""
        if goal_alignment < 0.5:
            logging.warning(f"Trace {trace_id} rejected by Gating Mechanism (Goal Alignment: {goal_alignment}).")
            return False
            
        node = CraniMemNode(trace_id, content, utility_score)
        self.episodic_buffer.append(node)
        
        if len(self.episodic_buffer) > self.buffer_limit:
            self._force_eviction()
            
        logging.info(f"Trace {trace_id} injected into Episodic Buffer.")
        return True

    def _force_eviction(self):
        """Prune low-utility traces from the bounded buffer."""
        self.episodic_buffer.sort(key=lambda x: x.utility_score)
        evicted = self.episodic_buffer.pop(0)
        logging.debug(f"Evicted trace {evicted.trace_id} due to buffer bounds.")

    def run_consolidation_loop(self):
        """Replay high-utility traces into the durable Knowledge Graph."""
        consolidated_count = 0
        for node in self.episodic_buffer[:]:
            if node.utility_score >= self.consolidation_threshold:
                self.knowledge_graph[node.trace_id] = node
                self.episodic_buffer.remove(node)
                consolidated_count += 1
                
        logging.info(f"Consolidation Loop complete: {consolidated_count} nodes crystallized to Knowledge Graph.")

    def recall(self, trace_id: str) -> CraniMemNode:
        """Recall from durable storage."""
        if trace_id in self.knowledge_graph:
            node = self.knowledge_graph[trace_id]
            node.access_count += 1
            return node
        return None
