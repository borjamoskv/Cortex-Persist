import pytest
from dataclasses import dataclass
from cortex.engine.mtk_core import MTKGuard
from cortex.types.evidence import ClosurePayload

@dataclass
class MockEvidence:
    sources: list

@pytest.fixture
def mtk_guard():
    # Use a dummy key for testing, it's not actually used for the signature if we don't pass one.
    return MTKGuard("dummy_key")

@pytest.mark.asyncio
async def test_auto8_friston_penalty_rejects_high_complexity(mtk_guard):
    # Base exergy is 1.0. We want complexity such that:
    # 1.0 - (complexity / (accuracy + 1.0) * 0.05) < 0.1
    # 0.9 < complexity / 2.0 * 0.05
    # 18.0 < complexity * 0.05
    # complexity > 360
    
    # We pass 400 claims and 1 evidence source.
    claims = ["claim"] * 400
    evidence = MockEvidence(sources=["source1"])
    
    payload = ClosurePayload(
        verdict=True,
        evidence=evidence,
        claims=claims,
        payload_hash="dummy_hash",
        schema_version="1.0",
        proof_kind="AUTO-8",
        info_exergy=1.0
    )
    
    # It should reject due to Free Energy too high (Net Exergy < 0.1)
    with pytest.raises(ValueError, match="Variational Free Energy too high / Net Exergy too low"):
        async with mtk_guard.transaction_boundary(payload):
            pass

@pytest.mark.asyncio
async def test_auto8_friston_penalty_accepts_low_complexity(mtk_guard):
    # Base exergy is 1.0. Complexity is 10, accuracy is 1.
    # 1.0 - (10 / 2.0 * 0.05) = 1.0 - (5 * 0.05) = 1.0 - 0.25 = 0.75 >= 0.1
    
    claims = ["claim"] * 10
    evidence = MockEvidence(sources=["source1"])
    
    payload = ClosurePayload(
        verdict=True,
        evidence=evidence,
        claims=claims,
        payload_hash="dummy_hash",
        schema_version="1.0",
        proof_kind="AUTO-8",
        info_exergy=1.0
    )
    
    # This should pass without raising the Variational Free Energy error.
    try:
        async with mtk_guard.transaction_boundary(payload):
            pass
    except ValueError as e:
        assert "Variational Free Energy too high" not in str(e)
