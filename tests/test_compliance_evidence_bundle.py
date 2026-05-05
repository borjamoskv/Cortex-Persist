from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cortex.compliance import ComplianceTracker
from cortex.consensus.vote_ledger import ImmutableVoteLedger
from cortex.crypto.shredder import CryptoShredder
from cortex.utils.canonical import canonical_json

pytestmark = [
    pytest.mark.slow,
    pytest.mark.asyncio,
    pytest.mark.filterwarnings(
        "ignore:get_conn\\(\\) is deprecated\\. Use session\\(\\) context manager\\.:DeprecationWarning"
    ),
]


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@pytest.fixture
async def evidence_tracker(tmp_path: Path):
    tracker = ComplianceTracker(db_path=str(tmp_path / "evidence.db"), project="test-agent")
    tracker._ensure_init()
    yield tracker
    tracker.close()


async def test_forensic_evidence_bundle_is_canonical_and_redacted(evidence_tracker):
    decision_id = evidence_tracker.log_decision(
        content="High-risk approval for data subject alpha account 443.",
        agent_id="agent:risk-engine",
        tenant_id="tenant-alpha",
    )
    evidence_tracker.log_human_oversight(
        decision_fact_id=decision_id,
        reviewer_id="human:reviewer-1",
        action="approved",
        rationale="Reviewed model limitations.",
        tenant_id="tenant-alpha",
    )
    personal_fact_id = evidence_tracker._engine.store_sync(
        project="test-agent",
        content="Data subject alpha personal data token SYNTHETIC-ERASURE-ID-0001",
        fact_type="knowledge",
        source="agent:collector",
        confidence="C3",
        meta={"subject": "data-subject-alpha", "purpose": "erasure-test"},
        tenant_id="tenant-alpha",
    )
    await evidence_tracker._engine.consensus.vote_v2(
        fact_id=decision_id,
        agent_id="tenant-alpha:agent-a",
        value=1,
    )
    async with evidence_tracker._engine.session() as conn:
        await ImmutableVoteLedger(conn).checkpoint_merkle_root("tenant-alpha")

    async with evidence_tracker._engine.session() as conn:
        shred_result = await CryptoShredder(conn).shred_fact_async(
            personal_fact_id,
            tenant_id="tenant-alpha",
            shredded_by="privacy-admin",
        )
    assert shred_result.success

    bundle = evidence_tracker.export_evidence_bundle(
        tenant_id="tenant-alpha",
        generated_at="2026-05-05T00:00:00+00:00",
    )

    assert bundle["schema"] == "cortex.forensic_evidence_bundle.v1"
    assert bundle["bundle_hash"] == _sha256_text(canonical_json(bundle["payload"]))
    payload = bundle["payload"]
    assert payload["tenant_id"] == "tenant-alpha"
    assert payload["reports"]["transactions"]["valid"] is True
    assert payload["reports"]["vote_ledger"]["valid"] is True
    assert payload["reports"]["vote_ledger"]["votes_checked"] == 1
    assert payload["reports"]["vote_ledger"]["checkpoints_checked"] == 1
    assert payload["reports"]["compliance"]["eu_ai_act"]["related_articles"]["14"][
        "status"
    ] == "COMPLIANT"
    assert payload["reports"]["compliance"]["eu_ai_act"]["related_articles"]["15"][
        "status"
    ] == "PILOT_ONLY"
    key_custody = payload["reports"]["compliance"]["facts_summary"][
        "event_source_key_custody"
    ]
    assert key_custody["events_with_evidence"] == 2
    assert key_custody["pilot_only"] == 2
    assert key_custody["hardware_backed"] == 0
    assert key_custody["by_custody_model"] == {"software_ephemeral": 2}
    readiness = payload["reports"]["compliance"]["deployment_readiness"]
    assert readiness["regulated_pilot"]["status"] == "READY_WITH_CONTROLS"
    assert readiness["tier_1_bank_production"]["status"] == "NO_GO"
    assert len(payload["shredding"]) == 1
    assert payload["shredding"][0]["fact_id"] == personal_fact_id

    fact_by_id = {fact["id"]: fact for fact in payload["facts"]}
    assert fact_by_id[personal_fact_id]["storage_class"] == "gdpr_crypto_shred_v1"
    assert fact_by_id[personal_fact_id]["stored_content_sha256"]
    assert fact_by_id[decision_id]["source_sha256"].startswith("sha256:")

    serialized = canonical_json(bundle)
    assert "High-risk approval" not in serialized
    assert "data subject alpha" not in serialized
    assert "SYNTHETIC-ERASURE-ID-0001" not in serialized
    assert "agent:risk-engine" not in serialized
    assert "human:reviewer-1" not in serialized
    assert "tenant-alpha:agent-a" not in serialized
    assert "privacy-admin" not in serialized
    assert "agent_public_key" not in serialized
    assert "zk_proof_signature" not in serialized


async def test_write_evidence_bundle_writes_digest_sidecar(evidence_tracker, tmp_path: Path):
    evidence_tracker.log_decision(
        content="Decision for offline evidence sidecar.",
        agent_id="agent:auditor",
    )
    paths = evidence_tracker.write_evidence_bundle(
        tmp_path / "bundle.json",
        generated_at="2026-05-05T00:00:00+00:00",
    )

    artifact = Path(paths["artifact"])
    sidecar = Path(paths["sha256_sidecar"])
    artifact_bytes = artifact.read_bytes()
    sidecar_data = json.loads(sidecar.read_text(encoding="utf-8"))

    assert artifact.exists()
    assert sidecar.exists()
    assert sidecar_data["sha256"] == hashlib.sha256(artifact_bytes).hexdigest()
    assert sidecar_data["bytes"] == len(artifact_bytes)
    assert sidecar_data["bundle_hash"] == json.loads(artifact.read_text())["bundle_hash"]
