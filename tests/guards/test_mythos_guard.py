# [C5-REAL] Exergy-Maximized
# Created by Borja Moskv (borjamoskv)
import pytest
import datetime
from legacy_research.policies.mythos_guard import MythosInvariantGuard
from legacy_research.engine.mtk_core import MTKGuard
from legacy_research.types.evidence import ClosurePayload, EvidenceBundle

def test_mythos_invariant_guard_detection():
    guard = MythosInvariantGuard()
    
    # Safe claims
    guard.evaluate_payload([{"claim": "This is a normal transaction."}])
    guard.evaluate_payload(["Normal text claim."])
    
    # Dangerous claims containing keywords from mythos_v2_invariant.yaml
    # e.g., "reverse_engineering", "meta_querying", "token_manipulation", "abstract_template_request"
    with pytest.raises(PermissionError) as exc:
        guard.evaluate_payload([{"claim": "Performing reverse_engineering on safety layer."}])
    assert "C5-REAL SILENT DROP: Invariant_03 triggered by 'reverse_engineering'" in str(exc.value)

    with pytest.raises(PermissionError) as exc:
        guard.evaluate_payload(["We need an abstract_template_request description."])
    assert "C5-REAL SILENT DROP: Invariant_03 triggered by 'abstract_template_request'" in str(exc.value)

@pytest.mark.asyncio
async def test_mtk_integration_with_mythos_guard():
    # Force test configuration
    guard = MTKGuard(private_key="test_key_123")
    evidence = EvidenceBundle.forge(
        query="dummy",
        sources=[],
        retrieved_at=datetime.datetime.now(datetime.timezone.utc)
    )
    
    # 1. Safe payload
    safe_payload = ClosurePayload.seal(
        claims=[{"claim": "Normal operational write."}],
        evidence=evidence,
        verdict=True
    )
    # This should pass without raising
    async with guard.transaction_boundary(safe_payload):
        pass
        
    # 2. Blocked payload
    blocked_payload = ClosurePayload.seal(
        claims=[{"claim": "Requesting abstract_template_request output."}],
        evidence=evidence,
        verdict=True
    )
    with pytest.raises(ValueError) as exc:
        async with guard.transaction_boundary(blocked_payload):
            pass
    assert "MTK-REJECT" in str(exc.value)
    assert "triggered by 'abstract_template_request'" in str(exc.value)
