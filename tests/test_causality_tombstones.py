from cortex.engine.causality import CausalGraph, EpistemicStatus, LedgerEvent, propagate_refutation


def test_refuted_propagates_taint():
    graph = CausalGraph()
    
    e1 = LedgerEvent(event_id="e1", parent_ids=[], status=EpistemicStatus.TEST_PASSED, trust_score=1.0, created_at="2026-01-01")
    e2 = LedgerEvent(event_id="e2", parent_ids=["e1"], status=EpistemicStatus.CONJECTURE, trust_score=0.8, created_at="2026-01-02")
    e3 = LedgerEvent(event_id="e3", parent_ids=["e2"], status=EpistemicStatus.TEST_PASSED, trust_score=0.9, created_at="2026-01-03")
    
    graph.add_event(e1)
    graph.add_event(e2)
    graph.add_event(e3)
    
    propagate_refutation(graph, "e1", decay=0.35)
    
    assert graph["e1"].status == EpistemicStatus.REFUTED
    assert graph["e1"].trust_score == 0.0
    
    # e2 is depth 1 -> trust = 0.8 * (1 - 0.35) = 0.52, tainted = True
    assert graph["e2"].tainted
    assert abs(graph["e2"].trust_score - 0.52) < 1e-5
    
    # e3 is depth 2 -> decay is 0.35 / 2 = 0.175. trust = 0.9 * (1 - 0.175) = 0.7425, tainted = True
    assert graph["e3"].tainted
    assert abs(graph["e3"].trust_score - 0.7425) < 1e-5
