# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path

import aiosqlite
import pytest
from click.testing import CliRunner

from babylon60.cli import cli
from babylon60.ledger.escape_hatch import (
    LIVENESS_KEY,
    is_dead_man_switch_triggered,
    record_liveness,
    record_liveness_sync,
    trigger_escape_hatch_export,
)


@pytest.mark.asyncio
async def test_escape_hatch_liveness_and_trigger(tmp_path: Path):
    db_file = tmp_path / "cortex_test.db"
    async with aiosqlite.connect(db_file) as conn:
        # Initial check should trigger since table or meta doesn't exist
        triggered = await is_dead_man_switch_triggered(conn, threshold_days=30)
        assert triggered is True

        # Touch/record liveness
        await record_liveness(conn)

        # Check triggered immediately after touch -> should be False
        triggered = await is_dead_man_switch_triggered(conn, threshold_days=30)
        assert triggered is False

        # Simulate threshold exceeded by updating timestamp back in time
        thirty_one_days_ago = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        await conn.execute(
            "UPDATE cortex_meta SET value = ? WHERE key = ?;", (thirty_one_days_ago, LIVENESS_KEY)
        )
        await conn.commit()

        # Check again -> should be True (triggered!)
        triggered = await is_dead_man_switch_triggered(conn, threshold_days=30)
        assert triggered is True


@pytest.mark.asyncio
async def test_escape_hatch_export_dumper(tmp_path: Path):
    db_file = tmp_path / "cortex_test.db"
    async with aiosqlite.connect(db_file) as conn:
        # Create dummy tables
        await conn.execute("CREATE TABLE dummy_facts (id INTEGER PRIMARY KEY, content TEXT);")
        await conn.execute("INSERT INTO dummy_facts (content) VALUES ('fact_1'), ('fact_2');")
        await conn.commit()

        # Execute export
        export_dir = tmp_path / "flat_export"
        res = await trigger_escape_hatch_export(conn, export_dir)

        assert res["status"] == "success"
        assert os.path.exists(res["manifest_path"])

        # Check that dummy_facts was exported
        facts_file = Path(res["exported_files"]["dummy_facts"])
        assert facts_file.exists()

        # Read JSONL contents
        lines = facts_file.read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2

        row1 = json.loads(lines[0])
        row2 = json.loads(lines[1])
        assert row1["content"] == "fact_1"
        assert row2["content"] == "fact_2"

        # Verify schema.json
        with open(res["manifest_path"], encoding="utf-8") as f:
            manifest = json.load(f)
            assert "dummy_facts" in manifest["tables"]
            assert manifest["tables"]["dummy_facts"]["columns"] == ["id", "content"]


def test_escape_hatch_cli_touch(tmp_path: Path):
    db_file = tmp_path / "cortex_test.db"
    runner = CliRunner()

    # Touch cli command
    result = runner.invoke(cli, ["trust-ledger", "escape-hatch", "--db", str(db_file), "--touch"])
    assert result.exit_code == 0
    assert "Liveness logged successfully" in result.output

    # Check cli command
    result_check = runner.invoke(
        cli, ["trust-ledger", "escape-hatch", "--db", str(db_file), "--check"]
    )
    assert result_check.exit_code == 0
    assert "ACTIVE" in result_check.output

    # Force export cli command
    export_dir = tmp_path / "cli_export"
    result_export = runner.invoke(
        cli,
        [
            "trust-ledger",
            "escape-hatch",
            "--db",
            str(db_file),
            "--export-dir",
            str(export_dir),
            "--force",
        ],
    )
    assert result_export.exit_code == 0
    assert "Export Complete" in result_export.output
    assert os.path.exists(export_dir / "schema.json")


def test_escape_hatch_liveness_sync(tmp_path: Path):
    db_file = tmp_path / "cortex_test.db"
    record_liveness_sync(db_file)

    # Verify using CliRunner check
    runner = CliRunner()
    result_check = runner.invoke(
        cli, ["trust-ledger", "escape-hatch", "--db", str(db_file), "--check"]
    )
    assert result_check.exit_code == 0
    assert "ACTIVE" in result_check.output
