from cortex.immune.quarantine import BlastRadiusReport, evaluate_demolition


def test_high_blast_radius_no_direct_purge():
    report = BlastRadiusReport(
        reverse_import_count=10,
        test_reference_count=50,
        runtime_entrypoint_count=2,
        causal_dependency_count=5,
        criticality_score=0.9
    )
    decision = evaluate_demolition(report, has_snapshot=True, modifies_schema=False)
    assert not decision.allowed
    assert decision.requires_quarantine

def test_destructive_without_snapshot_prohibited():
    report = BlastRadiusReport(
        reverse_import_count=0,
        test_reference_count=0,
        runtime_entrypoint_count=0,
        causal_dependency_count=0,
        criticality_score=0.1
    )
    decision = evaluate_demolition(report, has_snapshot=False, modifies_schema=False)
    assert not decision.allowed
    assert "snapshot is prohibited" in decision.reason

def test_quarantine_success_allows_purge():
    # After quarantine and verifying snapshot
    report = BlastRadiusReport(
        reverse_import_count=0,
        test_reference_count=0,
        runtime_entrypoint_count=0,
        causal_dependency_count=0,
        criticality_score=0.1
    )
    decision = evaluate_demolition(report, has_snapshot=True, modifies_schema=False)
    assert decision.allowed
