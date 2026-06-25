import pytest
from cortex.engine.ppi_index import PPIIndex, PPILevel

def test_ppi_index_reality_check():
    index = PPIIndex()
    
    # 1. Green Theater (Marketing Claim)
    marketing_claim = "Nuestro sistema AI es altamente seguro y revolucionario."
    marketing_evidence = {"brochure_url": "http://fake.com", "marketing_budget": 10000}
    score_mkt = index.evaluate_claim(marketing_claim, marketing_evidence)
    assert score_mkt.total_score < 0.6
    assert not index.enforce_reality(marketing_claim, marketing_evidence)
    
    # 2. C5-REAL (Cryptographic Proof)
    real_claim = "Ledger mutation completed."
    real_evidence = {
        "hash": "c350b20e7",
        "transaction_id": "0x12345",
        "financial_exposure": 500,
        "signature": "ed25519-sig"
    }
    score_real = index.evaluate_claim(real_claim, real_evidence)
    assert score_real.reality == PPILevel.C5_REAL
    assert score_real.risk == PPILevel.C5_REAL
    assert score_real.evidence >= PPILevel.STRONG
    assert index.enforce_reality(real_claim, real_evidence)

