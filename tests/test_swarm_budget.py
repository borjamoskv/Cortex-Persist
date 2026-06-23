# [C5-REAL] Exergy-Maximized
import pytest
import sqlite3
import time
from pathlib import Path
from unittest.mock import patch
from babylon60.extensions.swarm.budget import SwarmBudgetManager, HARD_LIMIT_USD, get_budget_manager


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_budget.db")


@pytest.fixture
def budget_manager(temp_db_path):
    # Reset singleton if needed or just instantiate
    return SwarmBudgetManager(db_path=temp_db_path)


def test_init_db(temp_db_path):
    manager = SwarmBudgetManager(db_path=temp_db_path)
    assert Path(temp_db_path).exists()

    # Check schema
    with sqlite3.connect(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(mission_budget)")
        columns = [row[1] for row in cursor.fetchall()]
        assert "mission_id" in columns
        assert "total_cost_usd" in columns


def test_report_usage_and_get_mission_budget(budget_manager):
    mission_id = "test_mission_1"

    # Initially no budget
    assert budget_manager.get_mission_budget(mission_id) is None

    # Report usage
    budget_manager.report_usage(mission_id, "openai", 1000, 500)

    # Verify budget
    budget = budget_manager.get_mission_budget(mission_id)
    assert budget is not None
    assert budget.mission_id == mission_id
    assert budget.total_input_tokens == 1000
    assert budget.total_output_tokens == 500
    assert budget.request_count == 1
    # openai cost: input 0.0025/1k, output 0.01/1k -> 0.0025 + 0.005 = 0.0075
    assert budget.total_cost_usd == 0.0075

    # Report more usage
    budget_manager.report_usage(mission_id, "openai", 2000, 1000)
    budget = budget_manager.get_mission_budget(mission_id)
    assert budget.total_input_tokens == 3000
    assert budget.total_output_tokens == 1500
    assert budget.request_count == 2
    assert budget.total_cost_usd == 0.0075 + 0.015


def test_report_usage_empty_mission(budget_manager):
    # Should return early
    budget_manager.report_usage("", "openai", 1000, 1000)
    missions = budget_manager.list_missions()
    assert len(missions) == 0


def test_check_budget_exceeds_limit(budget_manager):
    mission_id = "expensive_mission"

    # 1 million input tokens = $2.5, which is > HARD_LIMIT_USD (0.10)
    with pytest.raises(RuntimeError, match="Exergy exhaustion"):
        budget_manager.report_usage(mission_id, "openai", 1000000, 0)


def test_list_missions(budget_manager):
    budget_manager.report_usage("mission_a", "gemini", 100, 100)
    time.sleep(0.01)  # Ensure last_update difference
    budget_manager.report_usage("mission_b", "gemini", 100, 100)

    missions = budget_manager.list_missions()
    assert len(missions) == 2
    # Ordered by last_update DESC
    assert missions[0].mission_id == "mission_b"
    assert missions[1].mission_id == "mission_a"


def test_get_budget_manager():
    import babylon60.extensions.swarm.budget

    # Reset singleton for test
    babylon60.extensions.swarm.budget._instance = None

    manager1 = get_budget_manager()
    manager2 = get_budget_manager()
    assert manager1 is manager2
    assert isinstance(manager1, SwarmBudgetManager)


def test_sqlite_errors(budget_manager):
    # Mock db_connect to raise sqlite3.Error
    with patch("babylon60.extensions.swarm.budget.db_connect") as mock_connect:
        # We need the context manager to raise the error when entered
        mock_context = mock_connect.return_value
        mock_context.__enter__.side_effect = sqlite3.Error("Mocked DB error")

        # Test report_usage error handling
        budget_manager.report_usage("mission_error", "openai", 100, 100)

        # Test get_mission_budget error handling
        assert budget_manager.get_mission_budget("mission_error") is None

        # Test list_missions error handling
        assert budget_manager.list_missions() == []
