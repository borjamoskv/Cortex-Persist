import cortex_rs
import uuid

def test_semantic_state():
    print("Creating state 1")
    s1 = cortex_rs.SemanticState()
    
    id1 = str(uuid.uuid4())
    id2 = str(uuid.uuid4())
    id3 = str(uuid.uuid4())
    id4 = str(uuid.uuid4())
    
    # Valid 32-byte hex for cryptographic proof
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
    
    print(f"Active supports: {s1.active_supports}")
    print(f"Discard evidence: {s1.discard_evidence}")
    print(f"Dependencies: {s1.dependencies}")
    print(f"Cryptographic proofs: {s1.cryptographic_proofs}")
    
    assert id1 in s1.active_supports
    assert id3 in s1.active_supports
    assert id2 in s1.discard_evidence
    assert id4 in s1.dependencies
    assert proof1 in s1.cryptographic_proofs
    assert proof2 in s1.cryptographic_proofs
    
    print("Checking dominance...")
    assert s1.dominates(s2)
    
    print("All assertions passed!")

if __name__ == "__main__":
    test_semantic_state()
