from cortex.engine.causality import EpistemicStatus, LedgerEvent, hash_event
from cortex.extensions.swarm.identity import IdentityAnchor


def test_hash_event_arweave():
    event = LedgerEvent(
        event_id="evt_123",
        parent_ids=["evt_001"],
        status=EpistemicStatus.CONJECTURE,
        trust_score=0.9,
        created_at="2026-03-18T00:00:00Z",
        tainted=False,
    )
    b64_hash = hash_event(event)
    assert isinstance(b64_hash, str)
    assert len(b64_hash) >= 43  # Arweave tx IDs are 43 chars approx


def test_identity_anchor_lifecycle():
    anchor = IdentityAnchor.generate()
    jwk = anchor.export_public_jwk()

    assert "kty" in jwk
    assert jwk["kty"] == "RSA"
    assert "n" in jwk
    assert "e" in jwk

    # Signature test
    payload = b"cortex-handoff-test-payload"
    sig = anchor.sign(payload)
    assert anchor.verify(payload, sig)
