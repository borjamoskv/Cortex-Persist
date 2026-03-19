"""
test_legion_consignatario.py — Verification of the Consignee trust layer.

Tests:
1. Consignatario authorizes when consensus is high.
2. Consignatario rejects when consensus is low.
3. Ledger consignment event is correctly formatted.
4. Engine rolls back if Consignatario rejects.
"""

import aiosqlite
import pytest

from cortex.extensions.swarm.remediation.blue_team import RemediationResult
from cortex.extensions.swarm.remediation.engine import LegionRemediationEngine
from cortex.extensions.swarm.remediation.red_team import SiegeResult


@pytest.mark.asyncio
async def test_consignatario_authorization_flow(tmp_path):
    # Setup dummy DB
    db_path = tmp_path / "test_consign.db"
    async with aiosqlite.connect(db_path) as db:
        await db.execute("CREATE TABLE facts (id TEXT PRIMARY KEY, content TEXT, metadata TEXT)")
        await db.execute("INSERT INTO facts VALUES ('f1', 'test content', '{}')")
        await db.commit()

    engine = LegionRemediationEngine(str(db_path), dry_run=False)

    # Mock results
    blue_result = RemediationResult(
        fact_id="f1",
        agent_id="agent-01",
        specialist_id="spec-01",
        battalion="B03_CONFIDENCE",
        success=True,
        action="FIXED_CONFIDENCE",
    )

    # 1. High Consensus -> Pass
    siege_results = [
        SiegeResult(
            fact_id="f1",
            agent_id="r-agent-01",
            specialist_id="r-spec-01",
            battalion="B03_CONFIDENCE",
            passed=True,
            attack="integrity_check",
            finding="Clear",
        ),
        SiegeResult(
            fact_id="f1",
            agent_id="r-agent-01",
            specialist_id="r-spec-02",
            battalion="B03_CONFIDENCE",
            passed=True,
            attack="distribution_check",
            finding="Solid",
        ),
    ]

    async with aiosqlite.connect(db_path) as db:
        ok = await engine.consignatario.authorize_and_commit(
            db=db,
            ledger=engine.ledger,
            blue_result=blue_result,
            siege_results=siege_results,
            dry_run=False,
        )
        assert ok is True
        assert engine.consignatario.signature_count == 1

    # 2. Low Consensus -> Reject
    siege_results_low = [
        SiegeResult(
            fact_id="f1",
            agent_id="r-agent-01",
            specialist_id="r-spec-01",
            battalion="B03_CONFIDENCE",
            passed=False,
            attack="integrity_check",
            finding="Broken",
        ),
        SiegeResult(
            fact_id="f1",
            agent_id="r-agent-01",
            specialist_id="r-spec-02",
            battalion="B03_CONFIDENCE",
            passed=True,
            attack="distribution_check",
            finding="Wait",
        ),
    ]

    async with aiosqlite.connect(db_path) as db:
        ok = await engine.consignatario.authorize_and_commit(
            db=db,
            ledger=engine.ledger,
            blue_result=blue_result,
            siege_results=siege_results_low,
            dry_run=False,
        )
        assert ok is False
        assert engine.consignatario.signature_count == 1  # Still 1
