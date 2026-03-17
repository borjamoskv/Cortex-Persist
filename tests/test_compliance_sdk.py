"""Tests for cortex.compliance.tracker — ComplianceTracker SDK.

Validates the 3-method EU AI Act compliance API:
log_decision(), verify_chain(), export_audit().
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.slow


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
        cursor = await conn.execute("SELECT meta FROM facts WHERE id = ?", (fact_id,))
        row = await cursor.fetchone()
        assert row is not None

        from cortex.crypto import get_default_encrypter

        enc = get_default_encrypter()
        meta = enc.decrypt_json(row[0], tenant_id="default")
        assert "eu_ai_act" in meta
        assert meta["eu_ai_act"]["article"] == "12"
        assert meta["eu_ai_act"]["decision_type"] == "rejection"
        assert meta["eu_ai_act"]["agent_id"] == "AGENT:LOAN_PROCESSOR"

    async def test_custom_meta_merged(self, tracker):
        fact_id = tracker.log_decision(
            content="Approved application #445 with model override.",
            agent_id="agent:loan-processor",
            meta={"model": "gpt-4", "latency_ms": 230},
        )
        conn = await tracker._engine.get_conn()
        cursor = await conn.execute("SELECT meta FROM facts WHERE id = ?", (fact_id,))
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
        assert row[0] == "TEST_AGENT"

    async def test_custom_project_override(self, tracker):
        fact_id = tracker.log_decision(
            project="custom-project",
            content="Decision with explicit project override.",
            agent_id="agent:test",
        )
        conn = await tracker._engine.get_conn()
        cursor = await conn.execute("SELECT project FROM facts WHERE id = ?", (fact_id,))
        row = await cursor.fetchone()
        assert row[0] == "CUSTOM_PROJECT"


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
        assert "AGENT:COUNTER" in summary["sources"]

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
