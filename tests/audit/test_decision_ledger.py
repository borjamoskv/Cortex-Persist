# [C5-REAL] Exergy-Maximized
import pytest
import aiosqlite
import os
import tempfile
import json
from babylon60.audit.decision_ledger import (
    DecisionNode,
    DecisionLedger,
    Policy,
    PolicyVerdict,
    enforce_runtime_gate,
    timestamp_to_b60,
    score_to_b60,
)

@pytest.mark.asyncio
async def test_b60_conversion():
    # Test time scaling
    ts_val = 1625097600.0  # arbitrary epoch time
    b60_ts = timestamp_to_b60(ts_val)
    assert b60_ts == int(ts_val * 216000)

    # Test score scaling
    assert score_to_b60(1.0) == 60
    assert score_to_b60(0.5) == 30
    assert score_to_b60(0.0) == 0
    assert score_to_b60(45) == 45
    assert score_to_b60(-5) == 0
    assert score_to_b60(75) == 60


@pytest.mark.asyncio
async def test_decision_node_serialization():
    node = DecisionNode(
        trace_id="tr_test_123",
        parent_id=None,
        epoch_b60=timestamp_to_b60(),
        sequence=1,
        tenant_id="tenant_a",
        operator_id="agent_1",
        model_hash="sha256:model_weights",
        prompt_version_hash="sha256:prompt",
        tool_graph_hash="sha256:graph",
        input_taint="taint:some_taint",
        eval_scores={"safety": score_to_b60(0.95)}
    )

    data = node.to_dict()
    assert data["trace_id"] == "tr_test_123"
    assert data["runtime"]["eval_scores"]["safety"] == 57

    canon = node.canonical_json()
    assert "cryptography" not in canon
    assert "tr_test_123" in canon


@pytest.mark.asyncio
async def test_decision_ledger_append():
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)

    try:
        async with aiosqlite.connect(temp_db_path) as conn:
            ledger = DecisionLedger(conn)
            await ledger.ensure_table()

            node = DecisionNode(
                trace_id="tr_1",
                parent_id=None,
                epoch_b60=timestamp_to_b60(),
                sequence=1,
                tenant_id="tenant_a",
                operator_id="agent_1",
                model_hash="h1",
                prompt_version_hash="p1",
                tool_graph_hash="g1",
                input_taint="taint:1",
                eval_scores={"safety": 60}
            )

            # Append first block (Genesis parent hash check)
            sig1 = await ledger.append_node(node)
            assert sig1 != ""
            assert node.prev_hash == "GENESIS"
            assert node.approval_state == "SEALED"

            # Check DB write
            cursor = await conn.execute("SELECT * FROM decision_ledger WHERE trace_id = 'tr_1'")
            row = await cursor.fetchone()
            assert row is not None
            # columns: trace_id, parent_id, epoch_b60, sequence, tenant_id, operator_id, model_hash...
            assert row[0] == "tr_1"
            assert row[12] == "SEALED"  # approval_state

            # Append second block (hash chain continuity)
            node2 = DecisionNode(
                trace_id="tr_2",
                parent_id="tr_1",
                epoch_b60=timestamp_to_b60(),
                sequence=2,
                tenant_id="tenant_a",
                operator_id="agent_1",
                model_hash="h1",
                prompt_version_hash="p1",
                tool_graph_hash="g1",
                input_taint="taint:1",
            )
            sig2 = await ledger.append_node(node2)
            assert sig2 != ""
            assert node2.prev_hash == sig1

    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)


class CustomFailingPolicy(Policy):
    async def evaluate(self, node: DecisionNode) -> PolicyVerdict:
        return PolicyVerdict(
            policy_id=self.policy_id,
            status="FAIL",
            message="Content contains blocked terms"
        )


@pytest.mark.asyncio
async def test_enforce_runtime_gate():
    fd, temp_db_path = tempfile.mkstemp()
    os.close(fd)

    try:
        async with aiosqlite.connect(temp_db_path) as conn:
            ledger = DecisionLedger(conn)
            await ledger.ensure_table()

            node_pass = DecisionNode(
                trace_id="tr_pass",
                parent_id=None,
                epoch_b60=timestamp_to_b60(),
                sequence=1,
                tenant_id="tenant_a",
                operator_id="agent_1",
                model_hash="h1",
                prompt_version_hash="p1",
                tool_graph_hash="g1",
                input_taint="taint:1",
            )

            # 1. Test passing policies
            policies_pass = [Policy("policy_ok_1"), Policy("policy_ok_2")]
            success, verdicts = await enforce_runtime_gate(node_pass, policies_pass, ledger=ledger)
            assert success is True
            assert len(verdicts) == 2
            assert verdicts[0].status == "PASS"
            assert verdicts[0].seal != ""
            assert node_pass.approval_state == "SEALED"

            # Check it's stored in the ledger
            cursor = await conn.execute("SELECT approval_state FROM decision_ledger WHERE trace_id = 'tr_pass'")
            row = await cursor.fetchone()
            assert row is not None
            assert row[0] == "SEALED"

            # 2. Test failing policy (blocking)
            node_fail = DecisionNode(
                trace_id="tr_fail",
                parent_id=None,
                epoch_b60=timestamp_to_b60(),
                sequence=2,
                tenant_id="tenant_a",
                operator_id="agent_1",
                model_hash="h1",
                prompt_version_hash="p1",
                tool_graph_hash="g1",
                input_taint="taint:1",
            )
            policies_fail = [Policy("policy_ok"), CustomFailingPolicy("policy_bad", is_blocking=True)]
            success, verdicts = await enforce_runtime_gate(node_fail, policies_fail, ledger=ledger)
            assert success is False
            assert verdicts[1].status == "FAIL"
            assert node_fail.approval_state == "REJECTED"

            # Check it's NOT in the ledger as SEALED (since execution was blocked)
            cursor = await conn.execute("SELECT approval_state FROM decision_ledger WHERE trace_id = 'tr_fail'")
            row = await cursor.fetchone()
            assert row is None

    finally:
        if os.path.exists(temp_db_path):
            os.remove(temp_db_path)
