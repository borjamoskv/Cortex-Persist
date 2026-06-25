import pytest
from legacy_research.pipeline.sovereign_audit import SovereignAuditPipeline

def test_pipeline_robust_rule():
    pipeline = SovereignAuditPipeline()
    # "robust" prompt yields robustness=1.0 and logic="TAUTOLOGY"
    success, dossier = pipeline.execute_pipeline("GPT-5-Sim", "extract robust rule")
    assert success is True
    assert dossier["status"] == "C5_PERSISTED"
    assert "ledger_commit" in dossier

def test_pipeline_fragile_rule():
    pipeline = SovereignAuditPipeline()
    # "fragile" yields robustness=0.8, should fail destruction (Phase 2)
    success, dossier = pipeline.execute_pipeline("GPT-5-Sim", "extract fragile rule")
    assert success is False
    assert dossier["status"] in ["C1_SPECULATIVE", "C4_EMPIRICAL"]  # usually fails Phase 2

def test_pipeline_contradictory_rule():
    pipeline = SovereignAuditPipeline()
    # "contradiction" yields CONTRADICTION logic, fails Z3 Forge (Phase 3)
    # Note: we temporarily mock Phase 2 stochasticity if needed, but robustness=0.5 will also fail phase 2 often.
    # To test strictly phase 3, we can directly inject into Phase 3.
    
    dossier = {
        "model": "GPT-5-Sim",
        "rule_name": "Test_Contradiction",
        "extracted_logic": "CONTRADICTION",
        "stochastic_robustness": 1.0,
        "status": "C4_EMPIRICAL"
    }
    
    success, proof_hash = pipeline.phase_3_logical_forge(dossier)
    assert success is False
    assert proof_hash is None
