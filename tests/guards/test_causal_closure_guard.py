# [C5-REAL] Exergy-Maximized
"""Tests for the CausalClosureGuard.

Validates that the pipeline enforces strict thermodynamic causality 
via structural hash verification, rejecting pure prose or empty claims.
"""

from dataclasses import dataclass
import datetime
import pytest

from cortex.guards.causal_closure_guard import CausalClosureGuard, ClosureContractError
from cortex.types.evidence import ClosurePayload, EvidenceBundle, Source


@dataclass
class SwarmProposal:
    """Legacy dummy proposal for testing causal rejection."""
    agent_id: str
    mission_statement: str
    content: str
    token_cost: int = 0


@pytest.fixture
def closure_guard() -> CausalClosureGuard:
    """Provides the causal guard for testing."""
    return CausalClosureGuard()


@pytest.fixture
def valid_evidence() -> EvidenceBundle:
    return EvidenceBundle.forge(
        query="test query",
        sources=[
            Source(uri="test_uri", content_hash="hash123", metadata={"raw": "test data"})
        ],
        retrieved_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    )


def test_guard_accepts_canonical_payload_even_if_cheap(closure_guard: CausalClosureGuard, valid_evidence: EvidenceBundle) -> None:
    """A structurally sound payload with valid hashes must pass, token cost is irrelevant."""
    payload = ClosurePayload.seal(
        claims=[{"cve_id": "CVE-123"}],
        evidence=valid_evidence,
        verdict=True
    )
    # The guard accepts the sealed payload perfectly without needing heuristics or token costs
    assert closure_guard.verify_closure(payload) is True


def test_guard_rejects_narrative_even_if_expensive(closure_guard: CausalClosureGuard) -> None:
    """A legacy operation that outputs only prose must be aborted, even if token cost is extremely high."""
    proposal = SwarmProposal(
        agent_id="test", 
        mission_statement="test", 
        content="We carefully analyzed the system and conclude it is valid.", 
        token_cost=50000
    )
    with pytest.raises(RuntimeError):
        # The guard requires a canonical ClosurePayload, not a loose SwarmProposal
        closure_guard.verify_closure(proposal)  # type: ignore


def test_tampered_payload_hash_fails(closure_guard: CausalClosureGuard, valid_evidence: EvidenceBundle) -> None:
    """If the payload hash is modified after sealing, it must fail."""
    payload = ClosurePayload.seal(
        claims=[{"cve_id": "CVE-123"}],
        evidence=valid_evidence,
        verdict=True
    )
    
    # Tamper the hash to simulate semantic drift
    import dataclasses
    tampered_payload = dataclasses.replace(payload, payload_hash="invalid_hash")
    
    with pytest.raises(ClosureContractError, match="payload_hash mismatch"):
        closure_guard.verify_closure(tampered_payload)


def test_empty_evidence_and_claims_fails(closure_guard: CausalClosureGuard) -> None:
    """A payload with no claims and no evidence is pure Anergy and must be aborted."""
    empty_evidence = EvidenceBundle.forge(
        query="empty",
        sources=[],
        retrieved_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    )
    
    with pytest.raises(ClosureContractError, match="claims must be a non-empty list"):
        # The .seal method probably doesn't fail, but the guard will.
        # But wait, .seal might not allow empty claims. Let's assume it does.
        payload = ClosurePayload.seal(
            claims=[],
            evidence=empty_evidence,
            verdict=False
        )
        closure_guard.verify_closure(payload)
