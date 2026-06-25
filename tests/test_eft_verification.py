# [C5-REAL] Exergy-Maximized
import pytest
from unittest.mock import AsyncMock, MagicMock
from legacy_research.engine.models import KnowledgeObject, Justification, EvidenceType
from legacy_research.engine.guard_adapters import EFTVerificationGuardAdapter

@pytest.fixture(autouse=True)
def disable_exergy_skip(monkeypatch):
    monkeypatch.delenv("CORTEX_SKIP_EXERGY_VALIDATION", raising=False)

@pytest.mark.asyncio
async def test_justification_structure_parsing():
    # Test converting justification dict to Justification object
    ko = KnowledgeObject(
        id=1,
        tenant_id="default",
        project="test",
        claim="Claim text",
        fact_type="knowledge",
        justification={
            "evidence_type": "DEDUCTION",
            "evidence_links": ["sha3_256:1234"],
            "confidence_score": 0.9,
            "description": "Causal logic here"
        }
    )
    assert isinstance(ko.justification, Justification)
    assert ko.justification.evidence_type == EvidenceType.DEDUCTION
    assert ko.justification.confidence_score == 0.9
    assert ko.justification.evidence_links == ["sha3_256:1234"]
    assert str(ko.justification) == "Causal logic here"

@pytest.mark.asyncio
async def test_confidence_half_life_decay():
    # Test is_stale calculation
    from datetime import datetime, timedelta, timezone
    
    # 1. Non-accepted claim is not stale
    ko1 = KnowledgeObject(
        id=1,
        tenant_id="default",
        project="test",
        claim="Claim",
        verification_status="UNVERIFIED",
        accepted_at=datetime.now(timezone.utc).isoformat(),
        confidence_half_life="1h"
    )
    assert not ko1.is_stale

    # 2. Accepted claim within half-life is not stale
    ko2 = KnowledgeObject(
        id=2,
        tenant_id="default",
        project="test",
        claim="Claim",
        verification_status="ACCEPTED",
        accepted_at=datetime.now(timezone.utc).isoformat(),
        confidence_half_life="1h"
    )
    assert not ko2.is_stale

    # 3. Accepted claim past half-life is stale
    past_time = datetime.now(timezone.utc) - timedelta(hours=2)
    ko3 = KnowledgeObject(
        id=3,
        tenant_id="default",
        project="test",
        claim="Claim",
        verification_status="ACCEPTED",
        accepted_at=past_time.isoformat(),
        confidence_half_life="1h"
    )
    assert ko3.is_stale

@pytest.mark.asyncio
async def test_eft_quorum_consensus():
    adapter = EFTVerificationGuardAdapter()
    
    # 1. Fully naked claim: fails Validator and Epistemologist -> fails Quorum
    meta1 = {
        "verification_status": "UNVERIFIED"
    }
    with pytest.raises(ValueError, match="EFT-Quorum"):
        await adapter.check("content", "project", "knowledge", meta1, MagicMock())

    # 2. Claim with justification but lacks structural evidence:
    # Fails Epistemologist (no markers/links) but passes Validator & Cryptographer -> passes Quorum (2/3)
    meta2 = {
        "verification_status": "UNVERIFIED",
        "justification": "This is true because I say so."
    }
    # Should not raise because 2/3 guards (Validator, Cryptographer) pass
    await adapter.check("content", "project", "knowledge", meta2, MagicMock())

    # 3. Code claim with justification but no provenance:
    # Validator passes.
    # Epistemologist fails (no markers).
    # Cryptographer fails (no provenance for code).
    # -> fails Quorum (2 failures)
    meta3 = {
        "verification_status": "UNVERIFIED",
        "justification": "Standard justification text"
    }
    with pytest.raises(ValueError, match="EFT-Quorum"):
        await adapter.check("print('hello')", "project", "code", meta3, MagicMock())

    # 4. Code claim with justification and provenance:
    # Validator passes.
    # Epistemologist passes (if we add a marker).
    # Cryptographer passes (since we provide provenance).
    # -> passes Quorum
    meta4 = {
        "verification_status": "UNVERIFIED",
        "justification": "This has a sha3_256:1234 marker.",
        "provenance": "taint:agent:123"
    }
    await adapter.check("print('hello')", "project", "code", meta4, MagicMock())
