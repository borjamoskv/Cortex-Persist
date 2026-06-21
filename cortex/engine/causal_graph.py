# [C5-REAL] Exergy-Maximized
"""
Causal Graph Engine for CORTEX Audit System.
Maintains the Keyed Retrieval Graph System (KRGS) and causal linkages for deterministic replay.
"""

import json
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict

@dataclass
class CausalNode:
    event_id: str
    trace_id: str
    span_id: str
    parent_event_id: Optional[str]
    type: str # "execution" | "state_change" | "io" | "error"
    side_effects: List[str]
    derived_state_hashes: List[str]
    payload_hash: str
    
    def canonical_json(self) -> str:
        # sorted keys for deterministic hashing
        return json.dumps(asdict(self), sort_keys=True, separators=(',', ':'))

class CausalDAG:
    """In-memory reconstruction of the event DAG for replay tracking."""
    def __init__(self):
        self.nodes: Dict[str, CausalNode] = {}
        self.edges: Dict[str, List[str]] = {} # parent_event_id -> List[event_id]
        
    def add_node(self, node: CausalNode):
        self.nodes[node.event_id] = node
        if node.parent_event_id:
            if node.parent_event_id not in self.edges:
                self.edges[node.parent_event_id] = []
            self.edges[node.parent_event_id].append(node.event_id)
            
    def get_children(self, event_id: str) -> List[str]:
        return self.edges.get(event_id, [])
        
    def rebuild_from_stream(self, event_stream: List[dict]):
        """Reconstructs the DAG from a JSONL event stream."""
        for evt in event_stream:
            node = CausalNode(
                event_id=evt["event_id"],
                trace_id=evt["trace_id"],
                span_id=evt["span_id"],
                parent_event_id=evt.get("parent_hash"),
                type=evt["type"],
                side_effects=evt.get("side_effects", []),
                derived_state_hashes=evt.get("derived_state_hashes", []),
                payload_hash=evt["event_hash"]
            )
            self.add_node(node)
