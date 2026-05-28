import pytest

from cortex.engine import CortexEngine as AsyncCortexEngine
from cortex.engine.slashing import SlashingPenalty


@pytest.mark.asyncio
async def test_agent_reputation_slashing(tmp_path):
    # 1. Setup temporary engine
    db_path = str(tmp_path / "test_cortex.db")
    engine = AsyncCortexEngine(db_path)
    await engine.init_db()

    agent_id = "malicious_agent_0x9"
    tenant = "test_tenant"

    # 2. Register agent (reputation defaults to 0.5 via agents table schema)
    agent_id = await engine.consensus.register_agent(name="malicious_0x9", tenant_id=tenant)

    async with engine.session() as conn:
        async with conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ?", (agent_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 0.5

    # 3. Simulate a MAJOR_DEVIATION slash event
    new_rep = await engine.consensus.slash_vote_deviation(
        agent_id=agent_id,
        fact_id=1,  # Dummy ID
        penalty_type=SlashingPenalty.MAJOR_DEVIATION,
        reason="Consensus attack detected: Byzantine Node Collusion",
        tenant_id=tenant,
    )

    # 4. Verify score reduction (0.5 - 0.20 = 0.30)
    assert new_rep == 0.30

    # 5. Verify persistence in DB
    async with engine.session() as conn:
        async with conn.execute(
            "SELECT reputation_score FROM agents WHERE id = ?", (agent_id,)
        ) as cursor:
            row = await cursor.fetchone()
            assert row[0] == 0.30


@pytest.mark.asyncio
async def test_agent_annihilation(tmp_path):
    db_path = str(tmp_path / "test_cortex.db")
    engine = AsyncCortexEngine(db_path)
    await engine.init_db()

    agent_id = "byzantine_node"

    # Slash with BYZANTINE_BEHAVIOR (1.0)
    new_rep = await engine.consensus.slash_vote_deviation(
        agent_id=agent_id,
        fact_id=404,
        penalty_type=SlashingPenalty.BYZANTINE_BEHAVIOR,
        reason="Total exergy consumption violation",
    )

    # Verify floor at 0.0
    assert new_rep == 0.0
