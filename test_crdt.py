import cortex_rs

def test_semantic_state():
    print("Creating state 1")
    s1 = cortex_rs.SemanticState()
    s1.add_active_support("agent1_evidence")
    s1.add_discard_evidence("agent2_refutation")
    
    print("Creating state 2")
    s2 = cortex_rs.SemanticState()
    s2.add_active_support("agent3_evidence")
    s2.add_dependency("belief_123")
    
    print("Merging states")
    s1.merge(s2)
    
    print(f"Active supports: {s1.active_supports}")
    print(f"Discard evidence: {s1.discard_evidence}")
    print(f"Dependencies: {s1.dependencies}")
    
    assert "agent1_evidence" in s1.active_supports
    assert "agent3_evidence" in s1.active_supports
    assert "agent2_refutation" in s1.discard_evidence
    assert "belief_123" in s1.dependencies
    print("All assertions passed!")

if __name__ == "__main__":
    test_semantic_state()
