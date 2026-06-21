# [C5-REAL] Exergy-Maximized
"""
Replay Engine for CORTEX Audit System.
Verifies the Keyed Retrieval Graph System deterministically.
"""

import json
from typing import List, Dict, Any
from cortex.engine.state_diff import apply_patch
from cortex.engine.causal_graph import CausalDAG

class DivergenceError(Exception):
    pass

class ReplayVerifier:
    def __init__(self, log_path: str = "security_audit_log.jsonl"):
        self.log_path = log_path
        self.dag = CausalDAG()
        self.events: List[Dict[str, Any]] = []
        self._load_log()
        
    def _load_log(self):
        import os
        if not os.path.exists(self.log_path):
            return
            
        with open(self.log_path, "r") as f:
            for line in f:
                if not line.strip():
                    continue
                evt = json.loads(line)
                self.events.append(evt)
                if evt.get("type") != "BATCH_ROOT":
                    self.dag.rebuild_from_stream([evt])

    def replay(self, trace_id: str) -> bool:
        """
        Replays a specific trace to ensure causal state match.
        In a real system, this invokes the actual AST logic. Here we verify state diffs and hashes.
        """
        trace_events = [e for e in self.events if e.get("trace_id") == trace_id]
        if not trace_events:
            raise ValueError(f"Trace {trace_id} not found.")

        # Sort by Lamport time to ensure causal ordering
        trace_events.sort(key=lambda x: x.get("lamport_time", 0))

        current_state = {}
        
        for evt in trace_events:
            diff_str = evt["payload"].get("state_diff", "")
            if diff_str:
                patches = json.loads(diff_str)
                current_state = apply_patch(current_state, patches)
                
            # Recalculate event hash to ensure integrity
            payload_str = json.dumps(evt["payload"], sort_keys=True, separators=(',', ':'))
            import hashlib
            m = hashlib.sha3_256()
            m.update(payload_str.encode("utf-8"))
            m.update(evt["parent_hash"].encode("utf-8"))
            recalc_hash = m.hexdigest()
            
            if recalc_hash != evt["event_hash"]:
                raise DivergenceError(f"Hash divergence at event {evt['event_id']}")
                
        return True
