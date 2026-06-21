import pytest
import asyncio
from datetime import datetime, timezone
import copy
from dataclasses import dataclass

from cortex.types.evidence import EvidenceBundle, Source, ClosurePayload
from cortex.guards.causal_closure_guard import CausalClosureGuard, ClosureContractError
from legacy_research.pipeline.cve_orchestrator import CVEOrchestrator

@pytest.fixture
def valid_evidence():
    sources = [
        Source(uri="test_uri", content_hash="a" * 64, metadata={"raw": "serde is bad"})
    ]
    return EvidenceBundle.forge(
        query="test",
        sources=sources,
        retrieved_at=datetime.now(timezone.utc)
    )

@pytest.fixture
def valid_claims():
    return [{"cve_id": "CVE-TEST", "affected_crates": [{"name": "serde"}], "source_hash": "a" * 64}]


def test_guard_rejects_narrative_even_if_expensive():
    guard = CausalClosureGuard()
    
    @dataclass
    class SwarmProposal:
        agent_id: str
        mission_statement: str
        content: str
        token_cost: int
        
    proposal = SwarmProposal(
        agent_id="test",
        mission_statement="test",
        content="We carefully analyzed the system and conclude it is valid.",
        token_cost=5000,
    )

    with pytest.raises(ClosureContractError):
        guard.verify_closure(proposal)


def test_guard_accepts_canonical_payload_even_if_cheap(valid_evidence, valid_claims):
    guard = CausalClosureGuard()
    sealed = ClosurePayload.seal(
        claims=valid_claims,
        evidence=valid_evidence,
        verdict=True,
    )
    assert guard.verify_closure(sealed) is True


def test_guard_rejects_altered_schema_version(valid_evidence, valid_claims):
    guard = CausalClosureGuard()
    sealed = ClosurePayload.seal(
        claims=valid_claims,
        evidence=valid_evidence,
        verdict=True,
    )
    
    corrupted_dict = sealed.canonical()
    corrupted_dict["schema_version"] = "v2"
    
    with pytest.raises(ClosureContractError, match="unsupported schema_version"):
        guard.verify_closure(corrupted_dict)


def test_guard_rejects_altered_proof_kind(valid_evidence, valid_claims):
    guard = CausalClosureGuard()
    sealed = ClosurePayload.seal(
        claims=valid_claims,
        evidence=valid_evidence,
        verdict=True,
    )
    
    corrupted_dict = sealed.canonical()
    corrupted_dict["proof_kind"] = "vibes"
    
    with pytest.raises(ClosureContractError, match="unsupported proof_kind"):
        guard.verify_closure(corrupted_dict)


def test_guard_rejects_payload_hash_mismatch(valid_evidence, valid_claims):
    guard = CausalClosureGuard()
    sealed = ClosurePayload.seal(
        claims=valid_claims,
        evidence=valid_evidence,
        verdict=True,
    )
    
    corrupted_dict = sealed.canonical()
    corrupted_dict["claims"][0]["cve_id"] = "CVE-HACKED"
    
    with pytest.raises(ClosureContractError, match="payload_hash mismatch"):
        guard.verify_closure(corrupted_dict)


@pytest.mark.asyncio
async def test_cve_orchestrator_strict_fallback():
    orchestrator = CVEOrchestrator()
    # Provide a lockfile missing serde and tokio to cause validation failure
    res = await orchestrator.audit_cargo_lock("empty lockfile")
    
    assert res["status"] == "UNVERIFIED"
    assert res["reason"] == "cross-verifier unavailable or failed"
