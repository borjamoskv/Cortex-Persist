# [C5-REAL] Exergy-Maximized
import pytest
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../cortex-core'))
from cranimem import CraniMemSubstrate, CraniMemNode

def test_cranimem_gating_rejection():
    substrate = CraniMemSubstrate()
    # Goal alignment < 0.5 should be rejected
    success = substrate.gate_and_inject("trace_1", "Random distractor content", 0.2, 0.9)
    assert not success
    assert len(substrate.episodic_buffer) == 0

def test_cranimem_consolidation():
    substrate = CraniMemSubstrate(consolidation_threshold=0.8)
    # High utility trace
    substrate.gate_and_inject("trace_2", "Critical system parameter", 0.9, 0.95)
    # Low utility trace
    substrate.gate_and_inject("trace_3", "Minor log update", 0.9, 0.3)
    
    substrate.run_consolidation_loop()
    
    # Trace 2 should move to knowledge graph
    assert "trace_2" in substrate.knowledge_graph
    assert len(substrate.episodic_buffer) == 1
    assert substrate.episodic_buffer[0].trace_id == "trace_3"

def test_cranimem_eviction():
    substrate = CraniMemSubstrate(buffer_limit=2)
    substrate.gate_and_inject("t1", "data", 0.9, 0.1) # Lowest utility
    substrate.gate_and_inject("t2", "data", 0.9, 0.5)
    substrate.gate_and_inject("t3", "data", 0.9, 0.8)
    
    assert len(substrate.episodic_buffer) == 2
    # The one with 0.1 should have been evicted
    trace_ids = [node.trace_id for node in substrate.episodic_buffer]
    assert "t1" not in trace_ids
    assert "t2" in trace_ids
    assert "t3" in trace_ids
