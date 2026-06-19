import cortex_rs
import uuid

def test_semantic_state():
    print("Creating state 1")
    s1 = cortex_rs.SemanticState()
    
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    id3 = str(uuid.uuid4())
    id4 = str(uuid.uuid4())
    
    proof1 = "a" * 64
    proof2 = "b" * 64
    
    s1.add_active_support(id1)
    s1.add_discard_evidence(id2)
    s1.add_cryptographic_proof(proof1)
    
    print("Creating state 2")
    s2 = cortex_rs.SemanticState()
    s2.add_active_support(id3)
    s2.add_dependency(id4)
    s2.add_cryptographic_proof(proof2)
    
    print("Merging states")
    s1.merge(s2)
    
    assert id1 in s1.active_supports
    assert id3 in s1.active_supports
    assert id2 in s1.discard_evidence
    assert id4 in s1.dependencies
    assert proof1 in s1.cryptographic_proofs
    assert proof2 in s1.cryptographic_proofs
    
    print("Checking dominance...")
    assert s1.dominates(s2)
    
    print("Testing LogOP Engine consensus resolution...")
    engine = cortex_rs.LogOpEngine()
    
    # 1. State 1 has both active supports and discard evidence -> Contested
    outcome = engine.resolve_outcome(s1)
    assert outcome == cortex_rs.BeliefOutcome.Contested
    print(f"LogOP resolved outcome (Contested): {outcome}")
    
    # 2. State with only active supports -> Accepted
    s_accepted = cortex_rs.SemanticState()
    s_accepted.add_active_support(str(uuid.uuid4()))
    assert engine.resolve_outcome(s_accepted) == cortex_rs.BeliefOutcome.Accepted
    
    # 3. State with only discard evidence -> Rejected
    s_rejected = cortex_rs.SemanticState()
    s_rejected.add_discard_evidence(str(uuid.uuid4()))
    assert engine.resolve_outcome(s_rejected) == cortex_rs.BeliefOutcome.Rejected
    
    # 4. State with only dependencies -> Orphaned
    s_orphaned = cortex_rs.SemanticState()
    s_orphaned.add_dependency(str(uuid.uuid4()))
    assert engine.resolve_outcome(s_orphaned) == cortex_rs.BeliefOutcome.Orphaned

    # 5. Empty State -> Unknown
    s_empty = cortex_rs.SemanticState()
    assert engine.resolve_outcome(s_empty) == cortex_rs.BeliefOutcome.Unknown
    
    print("Testing compaction on overflow...")
    s_overflow = cortex_rs.SemanticState()
    
    # Add 35 items
    for _ in range(35):
        s_overflow.add_active_support(str(uuid.uuid4()))
        
    print(f"Overflow state supports count: {len(s_overflow.active_supports)}")
    print(f"Overflow state proofs count: {len(s_overflow.cryptographic_proofs)}")
    
    # Compaction should have triggered.
    # 32 elements were compacted into 1 proof, leaving 3 elements in the active supports.
    assert len(s_overflow.active_supports) == 3
    assert len(s_overflow.cryptographic_proofs) == 1
    
    print("All assertions passed successfully!")

if __name__ == "__main__":
    test_semantic_state()
