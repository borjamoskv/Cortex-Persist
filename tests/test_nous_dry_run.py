# [C5-REAL] Exergy-Maximized
"""Tests for NOUS Dry Run Engine."""

import pytest
from legacy_research.extensions.nous.models import MigrationOperation
from legacy_research.extensions.nous.dry_run import DryRunEngine


@pytest.mark.asyncio
async def test_dry_run_engine_safe_operations() -> None:
    engine = DryRunEngine()

    ops = [
        MigrationOperation(
            op="create_table",
            table="users",
            sql_up="CREATE TABLE users (id INT)",
            sql_down="DROP TABLE users",
        )
    ]

    result = await engine.simulate(ops)

    assert result.ok is True
    assert result.estimated_data_loss_risk == "none"
    assert len(result.warnings) == 0
    assert result.guards["rollback_check"].passed is True
    assert result.guards["syntax_check"].passed is True


@pytest.mark.asyncio
async def test_dry_run_engine_destructive_operations() -> None:
    engine = DryRunEngine()

    ops = [
        MigrationOperation(
            op="drop_table",
            table="old_users",
            sql_up="DROP TABLE old_users",
            sql_down="",  # irreversible
        )
    ]

    result = await engine.simulate(ops)

    assert result.ok is True
    assert result.estimated_data_loss_risk == "high"
    assert len(result.warnings) == 2
    assert result.guards["rollback_check"].passed is False
