# [C5-REAL] Exergy-Maximized
import asyncio
import pytest

from cortex.engine import CortexEngine
from legacy_research.extensions.swarm.manager import CapatazOrchestrator


@pytest.fixture
async def engine(tmp_path):
    """Provide a fresh CortexEngine with fully initialized database schema."""
    db_path = tmp_path / "test_agent_eroi.db"
    eng = CortexEngine(db_path=str(db_path))
    await eng.init_db()
    return eng


@pytest.mark.asyncio
async def test_eroi_migration_and_recording(engine: CortexEngine):
    """Verify that EROI migration is applied and record_task_eroi updates DB correctly."""
    # Check that the table exists by executing a query on it
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT count(*) FROM agent_tasks_eroi")
        count = (await cursor.fetchone())[0]
        assert count == 0

    # Record a successful task EROI
    agent_id = "agent_omega"
    new_rep = await engine.record_task_eroi(
        agent_id=agent_id,
        task_type="AST_refactor",
        exergy_yield=1.5,
        entropy_paid=0.2,
        tokens_spent=15,
        status="SUCCESS"
    )

    # Base reputation is 0.5. Delta = min(0.1, 0.02 * (1.5 / 1.2)) = min(0.1, 0.025) = 0.025.
    # So new reputation should be 0.525.
    assert abs(new_rep - 0.525) < 1e-4

    # Fetch recorded EROI stats from DB
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT exergy_yield, eroi_score, status FROM agent_tasks_eroi")
        row = await cursor.fetchone()
        assert row is not None
        assert row[0] == 1.5
        assert abs(row[1] - 1.25) < 1e-4
        assert row[2] == "SUCCESS"


@pytest.mark.asyncio
async def test_slashing_on_failed_eroi(engine: CortexEngine):
    """Verify reputation slashing when task fails."""
    agent_id = "agent_unstable"

    # Record failed task EROI
    new_rep = await engine.record_task_eroi(
        agent_id=agent_id,
        task_type="DB_opt",
        exergy_yield=0.0,
        entropy_paid=1.5,
        tokens_spent=3,
        status="FAILED"
    )

    # Base reputation is 0.5. Delta = -max(0.05, min(0.25, 0.1 * 1.5)) = -max(0.05, 0.15) = -0.15.
    # So new reputation should be 0.35.
    assert abs(new_rep - 0.35) < 1e-4


@pytest.mark.asyncio
async def test_jit_agent_selection(engine: CortexEngine):
    """Verify JIT candidate selection based on average EROI for task type."""
    agent_a = "agent_expert"
    agent_b = "agent_novice"

    # Record expert successes on AST_refactor
    await engine.record_task_eroi(
        agent_id=agent_a,
        task_type="AST_refactor",
        exergy_yield=2.0,
        entropy_paid=0.1,
        status="SUCCESS"
    )

    # Record novice failures / poor performance on AST_refactor
    await engine.record_task_eroi(
        agent_id=agent_b,
        task_type="AST_refactor",
        exergy_yield=0.5,
        entropy_paid=1.0,
        status="FAILED"
    )

    # Select best agent from candidates list
    best = await engine.select_best_agent_for_task(
        task_type="AST_refactor",
        candidate_agent_ids=[agent_b, agent_a]
    )
    assert best == agent_a


@pytest.mark.asyncio
async def test_capataz_jit_orchestration(engine: CortexEngine):
    """Verify that CapatazOrchestrator uses select_best_agent_for_task to route tasks."""
    capataz = CapatazOrchestrator()
    agent_pool = ["agent_high_eroi", "agent_low_eroi"]

    # 1. Setup EROI history
    await engine.record_task_eroi(
        agent_id="agent_high_eroi",
        task_type="code_refactor",
        exergy_yield=2.0,
        entropy_paid=0.05,
        status="SUCCESS"
    )
    await engine.record_task_eroi(
        agent_id="agent_low_eroi",
        task_type="code_refactor",
        exergy_yield=0.1,
        entropy_paid=2.0,
        status="FAILED"
    )

    async def mock_task():
        return "refactor_success"

    # Run the task through Capataz with candidate pool as list
    res = await capataz.run_task(
        name="test_pool_list",
        agent_name=agent_pool,
        coro_func=mock_task,
        changed_files=["cortex/engine/autopoiesis.py"],
        engine=engine
    )

    assert res == "refactor_success"
    # Ensure the task was assigned to agent_high_eroi (highest EROI)
    task_entry = list(capataz.tasks.values())[-1]
    assert task_entry.agent_name == "agent_high_eroi"

    # Run the task through Capataz with candidate pool as string prefix
    res2 = await capataz.run_task(
        name="test_pool_str",
        agent_name="pool:agent_high_eroi,agent_low_eroi",
        coro_func=mock_task,
        changed_files=["cortex/engine/autopoiesis.py"],
        engine=engine
    )
    assert res2 == "refactor_success"
    task_entry2 = list(capataz.tasks.values())[-1]
    assert task_entry2.agent_name == "agent_high_eroi"
