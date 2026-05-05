"""Tests for cortex.compliance.tracker — ComplianceTracker SDK.

Validates the 3-method EU AI Act compliance API:
log_decision(), verify_chain(), export_audit().
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = [
    pytest.mark.slow,
    pytest.mark.filterwarnings(
        "ignore:get_conn\\(\\) is deprecated\\. Use session\\(\\) context manager\\.:DeprecationWarning"
    ),
]


@pytest.fixture
async def tracker(tmp_path: Path):
    """Create a ComplianceTracker with a temp database."""
    from cortex.compliance import ComplianceTracker

    t = ComplianceTracker(db_path=str(tmp_path / "compliance_test.db"), project="test-agent")
    t._ensure_init()
    yield t
    t.close()


# ─── log_decision ─────────────────────────────────────────────────────


class TestLogDecision:
    async def test_returns_fact_id(self, tracker):
        fact_id = tracker.log_decision(
            content="Approved loan application #443 — risk score 0.23",
            agent_id="agent:loan-processor",
        )
        assert isinstance(fact_id, int)
        assert fact_id > 0

    async def test_stores_eu_metadata(self, tracker):
        fact_id = tracker.log_decision(
            content="Rejected application #444 — income verification failed",
            agent_id="agent:loan-processor",
            decision_type="rejection",
        )
        # Retrieve the fact and check meta
        conn = await tracker._engine.get_conn()
        cursor = await conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id,))
        row = await cursor.fetchone()
        assert row is not None

        from cortex.crypto import get_default_encrypter

        enc = get_default_encrypter()
        meta = enc.decrypt_json(row[0], tenant_id="default")
        assert "eu_ai_act" in meta
        assert meta["eu_ai_act"]["article"] == "12"
        assert meta["eu_ai_act"]["decision_type"] == "rejection"
        assert meta["eu_ai_act"]["agent_id"] == "agent:loan-processor"
        assert meta["eu_ai_act"]["article_14"]["risk_level"] == "high"
        assert meta["eu_ai_act"]["article_14"]["override_available"] is True
        assert meta["eu_ai_act"]["article_14"]["stop_available"] is True
        assert meta["zk_proof_algorithm"] == "Ed25519"
        assert meta["zk_proof_scope"] == "store_event_v1"
        assert isinstance(meta["agent_public_key"], str)
        assert isinstance(meta["agent_public_key_sha256"], str)
        assert isinstance(meta["zk_proof_signature"], str)
        custody = meta["event_source_key_custody"]
        assert custody["schema"] == "cortex.event_source_key_custody.v1"
        assert custody["public_key_sha256"] == meta["agent_public_key_sha256"]
        assert custody["custody_model"] == "software_ephemeral"
        assert custody["assurance_level"] == "pilot_only"
        assert custody["hardware_backed"] is False
        assert custody["private_key_exportable"] is True
        assert meta["event_source_key_custody_status"] == "pilot_only"

    async def test_custom_meta_merged(self, tracker):
        fact_id = tracker.log_decision(
            content="Approved application #445 with model override.",
            agent_id="agent:loan-processor",
            meta={"model": "gpt-4", "latency_ms": 230},
        )
        conn = await tracker._engine.get_conn()
        cursor = await conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id,))
        row = await cursor.fetchone()

        from cortex.crypto import get_default_encrypter

        enc = get_default_encrypter()
        meta = enc.decrypt_json(row[0], tenant_id="default")
        assert meta.get("model") == "gpt-4"
        assert meta.get("latency_ms") == 230
        assert "eu_ai_act" in meta

    async def test_uses_default_project(self, tracker):
        fact_id = tracker.log_decision(
            content="Decision using default project namespace.",
            agent_id="agent:test",
        )
        conn = await tracker._engine.get_conn()
        cursor = await conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,))
        row = await cursor.fetchone()
        assert row[0] == "test-agent"

    async def test_custom_project_override(self, tracker):
        fact_id = tracker.log_decision(
            project="custom-project",
            content="Decision with explicit project override.",
            agent_id="agent:test",
        )
        conn = await tracker._engine.get_conn()
        cursor = await conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,))
        row = await cursor.fetchone()
        assert row[0] == "custom-project"

    async def test_custom_tenant_scope_is_stored(self, tracker):
        fact_id = tracker.log_decision(
            content="Decision with explicit tenant scope.",
            agent_id="agent:test",
            tenant_id="tenant-alpha",
        )
        conn = await tracker._engine.get_conn()
        cursor = await conn.execute("SELECT tenant_id FROM facts WHERE id = ?", (fact_id,))
        row = await cursor.fetchone()
        assert row[0] == "tenant-alpha"

    async def test_external_store_event_signature_without_attestation_is_marked(self, tracker):
        from cortex.crypto import get_default_encrypter
        from cortex.crypto.keys import ZKSwarmIdentity

        content = "Decision signed by an external source key."
        keypair = ZKSwarmIdentity.generate_keypair()
        signature = ZKSwarmIdentity.sign_store_event(
            tenant_id="default",
            project="test-agent",
            fact_type="decision",
            source="agent:external",
            content=content,
            private_key_b64=keypair.private_key_b64,
        )
        fact_id = tracker.log_decision(
            content=content,
            agent_id="agent:external",
            meta={
                "agent_public_key": keypair.public_key_b64,
                "agent_public_key_sha256": ZKSwarmIdentity.public_key_sha256(
                    keypair.public_key_b64
                ),
                "zk_proof_signature": signature,
                "zk_proof_scope": "store_event_v1",
            },
        )

        conn = await tracker._engine.get_conn()
        cursor = await conn.execute("SELECT metadata FROM facts WHERE id = ?", (fact_id,))
        row = await cursor.fetchone()
        meta = get_default_encrypter().decrypt_json(row[0], tenant_id="default")

        assert meta["event_source_key_custody"]["custody_model"] == "external_unverified"
        assert meta["event_source_key_custody"]["assurance_level"] == "attestation_required"
        assert meta["event_source_key_custody"]["public_key_sha256"] == meta[
            "agent_public_key_sha256"
        ]

    async def test_rejects_mismatched_external_key_custody_fingerprint(self, tracker):
        from cortex.crypto.keys import ZKSwarmIdentity

        content = "Decision with mismatched key custody evidence."
        keypair = ZKSwarmIdentity.generate_keypair()
        signature = ZKSwarmIdentity.sign_store_event(
            tenant_id="default",
            project="test-agent",
            fact_type="decision",
            source="agent:external",
            content=content,
            private_key_b64=keypair.private_key_b64,
        )

        with pytest.raises(ValueError, match="public-key fingerprint mismatch"):
            tracker.log_decision(
                content=content,
                agent_id="agent:external",
                meta={
                    "agent_public_key": keypair.public_key_b64,
                    "agent_public_key_sha256": ZKSwarmIdentity.public_key_sha256(
                        keypair.public_key_b64
                    ),
                    "zk_proof_signature": signature,
                    "zk_proof_scope": "store_event_v1",
                    "event_source_key_custody": {
                        "public_key_sha256": "0" * 64,
                        "custody_model": "hsm",
                    },
                },
            )


# ─── verify_chain ─────────────────────────────────────────────────────


class TestVerifyChain:
    async def test_valid_on_fresh_db(self, tracker):
        result = tracker.verify_chain()
        assert result["valid"] is True
        assert result["violations"] == []

    async def test_valid_after_decisions(self, tracker):
        for i in range(3):
            tracker.log_decision(
                content=f"Decision {i} for chain verification test.",
                agent_id="agent:verifier",
            )
        result = tracker.verify_chain()
        assert result["valid"] is True


# ─── export_audit ─────────────────────────────────────────────────────


class TestExportAudit:
    async def test_contains_required_fields(self, tracker):
        tracker.log_decision(
            content="Decision for audit export test.",
            agent_id="agent:auditor",
        )
        report = tracker.export_audit()
        assert "eu_ai_act" in report
        assert "integrity" in report
        assert "facts_summary" in report
        assert "generated_at" in report
        assert "project" in report

    async def test_compliance_checks_present(self, tracker):
        tracker.log_decision(
            content="Decision for compliance checks test.",
            agent_id="agent:auditor",
        )
        report = tracker.export_audit()
        checks = report["eu_ai_act"]["checks"]
        assert "art_12_1_automatic_logging" in checks
        assert "art_12_2_log_content" in checks
        assert "art_12_2d_agent_traceability" in checks
        assert "art_12_3_tamper_proof" in checks
        assert "art_12_4_periodic_verification" in checks

    async def test_compliance_score(self, tracker):
        tracker.log_decision(
            content="Decision for score validation.",
            agent_id="agent:auditor",
        )
        report = tracker.export_audit()
        assert report["eu_ai_act"]["score"] == "5/5"
        assert report["eu_ai_act"]["status"] == "COMPLIANT"
        article_15 = report["eu_ai_act"]["related_articles"]["15"]
        assert article_15["status"] == "PILOT_ONLY"
        assert article_15["checks"]["art_15_source_key_custody"]["compliant"] is True
        assert article_15["checks"]["art_15_hardware_backing"]["compliant"] is False
        assert report["deployment_readiness"]["tier_1_bank_production"]["status"] == "NO_GO"

    async def test_empty_scope_is_not_compliant(self, tracker):
        report = tracker.export_audit(project="empty-project")

        assert report["facts_summary"]["total_facts"] == 0
        assert report["eu_ai_act"]["status"] == "NON_COMPLIANT"
        assert report["eu_ai_act"]["score"] != "5/5"
        assert report["deployment_readiness"]["regulated_pilot"]["status"] == "NO_GO"

    async def test_facts_summary_counts(self, tracker):
        for i in range(3):
            tracker.log_decision(
                content=f"Decision {i} for summary counting.",
                agent_id="agent:counter",
            )
        report = tracker.export_audit()
        summary = report["facts_summary"]
        assert summary["total_facts"] == 3
        assert summary["active_facts"] == 3
        assert "decision" in summary["by_type"]
        assert "agent:counter" in summary["sources"]
        assert summary["event_source_key_custody"]["events_with_evidence"] == 3
        assert summary["event_source_key_custody"]["pilot_only"] == 3
        assert summary["event_source_key_custody"]["hardware_backed"] == 0

    async def test_include_facts_flag(self, tracker):
        tracker.log_decision(
            content="Decision for facts list test.",
            agent_id="agent:lister",
        )
        report_without = tracker.export_audit()
        assert "facts" not in report_without

        report_with = tracker.export_audit(include_facts=True)
        assert "facts" in report_with
        assert len(report_with["facts"]) == 1
        assert report_with["facts"][0]["fact_type"] == "decision"

    async def test_export_audit_is_tenant_scoped(self, tracker):
        tracker.log_decision(
            content="Alpha tenant decision.",
            agent_id="agent:alpha",
            tenant_id="tenant-alpha",
        )
        tracker.log_decision(
            content="Beta tenant decision.",
            agent_id="agent:beta",
            tenant_id="tenant-beta",
        )

        report = tracker.export_audit(tenant_id="tenant-alpha", include_facts=True)
        summary = report["facts_summary"]

        assert report["tenant_id"] == "tenant-alpha"
        assert summary["total_facts"] == 1
        assert summary["active_facts"] == 1
        assert summary["sources"] == ["agent:alpha"]
        assert len(report["facts"]) == 1

    async def test_article_14_flags_unreviewed_high_risk_decisions(self, tracker):
        tracker.log_decision(
            content="Automated high-risk decision without reviewer evidence.",
            agent_id="agent:risk",
        )

        report = tracker.export_audit()
        article_14 = report["eu_ai_act"]["related_articles"]["14"]

        assert article_14["status"] == "NON_COMPLIANT"
        assert article_14["checks"]["art_14_1_human_machine_interface"]["compliant"] is False
        assert article_14["checks"]["art_14_4d_override"]["compliant"] is True

    async def test_article_14_human_oversight_event_closes_review_gap(self, tracker):
        decision_id = tracker.log_decision(
            content="High-risk decision with separate human review.",
            agent_id="agent:risk",
        )
        tracker.log_human_oversight(
            decision_fact_id=decision_id,
            reviewer_id="human:reviewer-1",
            action="approved",
            rationale="Reviewed model limitations and override path.",
        )

        report = tracker.export_audit()
        summary = report["facts_summary"]["article_14"]
        article_14 = report["eu_ai_act"]["related_articles"]["14"]

        assert summary["high_risk_decisions"] == 1
        assert summary["reviewed_decisions"] == 1
        assert summary["oversight_events"] == 1
        assert article_14["status"] == "COMPLIANT"
        assert report["eu_ai_act"]["related_articles"]["15"]["status"] == "PILOT_ONLY"
        readiness = report["deployment_readiness"]
        assert readiness["regulated_pilot"]["status"] == "READY_WITH_CONTROLS"
        assert readiness["tier_1_bank_production"]["status"] == "NO_GO"
        assert "Article 15 event-source key custody is pilot-only" in readiness[
            "tier_1_bank_production"
        ]["blockers"]
        assert "issued DORA Article 28 contract annex and exit evidence" in readiness[
            "tier_1_bank_production"
        ]["required_controls"]

    async def test_bank_production_requires_verified_issued_dora_evidence(self, tracker):
        from cortex.crypto.keys import ZKSwarmIdentity

        content = "Hardware-backed high-risk decision with inline reviewer evidence."
        keypair = ZKSwarmIdentity.generate_keypair()
        signature = ZKSwarmIdentity.sign_store_event(
            tenant_id="default",
            project="test-agent",
            fact_type="decision",
            source="agent:hsm",
            content=content,
            private_key_b64=keypair.private_key_b64,
        )
        tracker.log_decision(
            content=content,
            agent_id="agent:hsm",
            human_reviewer_id="human:reviewer-1",
            meta={
                "agent_public_key": keypair.public_key_b64,
                "agent_public_key_sha256": ZKSwarmIdentity.public_key_sha256(
                    keypair.public_key_b64
                ),
                "zk_proof_signature": signature,
                "zk_proof_scope": "store_event_v1",
                "event_source_key_custody": {
                    "public_key_sha256": ZKSwarmIdentity.public_key_sha256(
                        keypair.public_key_b64
                    ),
                    "custody_model": "hsm",
                    "assurance_level": "hardware_attested",
                    "hardware_backed": True,
                    "private_key_exportable": False,
                    "attestation_type": "hsm_certificate",
                },
            },
        )

        missing_dora = tracker.export_audit()
        verified_dora = tracker.export_audit(
            dora_article_28_evidence={
                "status": "verified_issued",
                "source": "dora-pack.zip",
                "verification_status": "passed",
            }
        )

        assert missing_dora["eu_ai_act"]["related_articles"]["14"]["status"] == "COMPLIANT"
        assert missing_dora["eu_ai_act"]["related_articles"]["15"]["status"] == "COMPLIANT"
        assert missing_dora["deployment_readiness"]["tier_1_bank_production"][
            "status"
        ] == "NO_GO"
        assert "DORA Article 28 evidence is not verified issued" in missing_dora[
            "deployment_readiness"
        ]["tier_1_bank_production"]["blockers"]
        assert verified_dora["deployment_readiness"]["dora_article_28"][
            "status"
        ] == "verified_issued"
        assert verified_dora["deployment_readiness"]["tier_1_bank_production"][
            "status"
        ] == "GO"


# ─── Context Manager ─────────────────────────────────────────────────


class TestContextManager:
    async def test_context_manager_works(self, tmp_path: Path):
        from cortex.compliance import ComplianceTracker

        with ComplianceTracker(
            db_path=str(tmp_path / "ctx_test.db"),
            project="ctx-test",
        ) as t:
            fact_id = t.log_decision(
                content="Decision inside context manager.",
                agent_id="agent:ctx",
            )
            assert isinstance(fact_id, int)
            assert fact_id > 0
