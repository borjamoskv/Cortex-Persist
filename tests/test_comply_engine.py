# [C5-REAL] Exergy-Maximized
"""Tests for ComplySigner, PolicyEngine, and ComplianceTracker integration."""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from collections.abc import Iterator
from typing import Any

import pytest

from babylon60.compliance.comply_signer import ComplySigner
from babylon60.compliance.policy_engine import PolicyEngine
from babylon60.compliance.tracker import ComplianceTracker


class TestComplyEngine:
    @pytest.fixture
    def temp_dir(self) -> Iterator[Path]:
        path = Path(tempfile.mkdtemp())
        yield path
        shutil.rmtree(path)

    def test_comply_signer(self, temp_dir: Path) -> None:
        signer = ComplySigner(keys_dir=temp_dir)
        agent_id = "agent:test-signer"

        # 1. Key Generation
        priv, pub = signer.get_or_create_agent_keys(agent_id)
        assert priv is not None
        assert pub is not None

        # Ensure files are written
        safe_id = agent_id.replace(":", "_")
        assert (temp_dir / f"{safe_id}_private.pem").exists()
        assert (temp_dir / f"{safe_id}_public.pem").exists()

        # 2. Signing and Verification
        payload = {"decision": "Approve Loan", "amount": 5000}
        sig = signer.sign_payload(agent_id, payload)
        assert isinstance(sig, str)
        assert len(sig) > 0

        assert signer.verify_payload(agent_id, payload, sig) is True

        # 3. Verification with tampered payload
        tampered_payload = {"decision": "Approve Loan", "amount": 5001}
        assert signer.verify_payload(agent_id, tampered_payload, sig) is False

        # 4. Verification with wrong agent ID
        assert signer.verify_payload("agent:other", payload, sig) is False

    def test_policy_engine(self, temp_dir: Path) -> None:
        policy_path = temp_dir / "policies.json"
        pe = PolicyEngine(policy_path=policy_path)

        # Default permissions
        # k0-daemon role (assigned to agent:k0 by default) should allow execute
        allowed, reason = pe.evaluate_action("agent:k0", "execute", "cortex-core")
        assert allowed is True

        # reader role (assigned to unknown) should deny write
        allowed, reason = pe.evaluate_action("agent:unknown", "write", "cortex-core")
        assert allowed is False

        # Assign role manually
        pe.assign_role("agent:unknown", "writer")
        allowed, reason = pe.evaluate_action("agent:unknown", "write", "cortex-core")
        assert allowed is True

        # Cost constraints
        allowed, reason = pe.evaluate_action("agent:k0", "read", "cortex-core", {"cost": 0.1})
        assert allowed is True

        # Cost exceeding limit
        allowed, reason = pe.evaluate_action("agent:k0", "read", "cortex-core", {"cost": 10.0})
        assert allowed is False
        assert "exceeds" in reason

        # Error rate threshold
        allowed, reason = pe.evaluate_action("agent:k0", "read", "cortex-core", {"error_rate": 0.4})
        assert allowed is False
        assert "error rate" in reason

    def test_compliance_tracker_e2e(self, temp_dir: Path) -> None:
        db_path = temp_dir / "cortex_test.db"
        tracker = ComplianceTracker(db_path=db_path, project="test-project")
        
        # Override default paths for keys/policies inside tests to isolate
        tracker._signer = ComplySigner(keys_dir=temp_dir / "keys")
        tracker._policy_engine = PolicyEngine(policy_path=temp_dir / "policies.json")

        # 1. Log a valid decision
        meta = {"cost": 0.05}
        fact_id = tracker.log_decision(
            project="test-project",
            content="Validating compliance infrastructure.",
            agent_id="agent:k0",
            decision_type="validation",
            confidence="C5",
            meta=meta
        )
        assert fact_id > 0

        # 2. Log a decision that violates policy (should raise PermissionError)
        with pytest.raises(PermissionError):
            tracker.log_decision(
                project="test-project",
                content="This action costs too much.",
                agent_id="agent:k0",
                decision_type="heavy_op",
                meta={"cost": 50.0}
            )

        # 3. Verify Chain (should be valid)
        res = tracker.verify_chain()
        assert res["valid"] is True
        assert res["signatures_verified"] == 1
        assert len(res["violations"]) == 0

        # 4. Generate and verify compliance report
        report = tracker.export_audit(project="test-project", include_facts=True)
        assert report["eu_ai_act"]["status"] == "COMPLIANT"
        assert report["eu_ai_act"]["checks"]["art_12_3_tamper_proof"]["compliant"] is True

        tracker.close()

        # 5. Simulate database tampering and verify detection
        # We manually modify the database to violate cryptographic signature integrity.
        import sqlite3
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Change content of the recorded fact
        cursor.execute("UPDATE facts SET content = 'Tampered text payload.' WHERE id = ?", (fact_id,))
        conn.commit()
        conn.close()

        # Re-open tracker and run verify
        tracker_tampered = ComplianceTracker(db_path=db_path, project="test-project")
        tracker_tampered._signer = ComplySigner(keys_dir=temp_dir / "keys")
        tracker_tampered._policy_engine = PolicyEngine(policy_path=temp_dir / "policies.json")

        res_tampered = tracker_tampered.verify_chain()
        assert res_tampered["valid"] is False
        assert len(res_tampered["violations"]) > 0
        v_types = {v["type"] for v in res_tampered["violations"]}
        assert "INVALID_SIGNATURE" in v_types or "FACT_HASH_MISMATCH" in v_types
        assert any(v.get("fact_id") == fact_id for v in res_tampered["violations"])

        tracker_tampered.close()
