# [C5-REAL] Exergy-Maximized
import pytest
import asyncio
import json
from pathlib import Path
from cortex.engine.core import engine
from cortex.engine.flow import execution_ledger as ledger


@pytest.mark.asyncio
async def test_engine_run_circuit(tmp_path):
    # Override ledger path to use a temp directory
    temp_ledger_file = tmp_path / "test_execution_ledger.jsonl"
    ledger._instance.path = temp_ledger_file

    # Mock intent for AX (APEX_STATE trigger word: "piensa")
    intent_ax = {"kind": "piensa profundamente"}
    result_ax = await engine.run(intent_ax, domain="test_domain")

    assert result_ax["status"] == "success"
    assert result_ax["backend"] == "AX"

    # Mock intent for CDP (CONSTRUCT_STATE trigger word: "crea")
    intent_cdp = {"kind": "crea un archivo"}
    result_cdp = await engine.run(intent_cdp, domain="test_domain")

    assert result_cdp["status"] == "success"
    assert result_cdp["backend"] == "CDP"

    # Mock intent for HITL (default fallback)
    intent_hitl = {"kind": "normal query"}
    result_hitl = await engine.run(intent_hitl, domain="test_domain")

    assert result_hitl["status"] == "hitl_pending"
    assert "row_id" in result_hitl

    # Verify ledger records are persisted
    assert temp_ledger_file.exists()
    records = []
    with open(temp_ledger_file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line.strip()))

    assert len(records) == 3
    assert records[0]["intent_kind"] == "piensa profundamente"
    assert records[0]["backend"] == "AX"
    assert records[0]["outcome"] == "success"

    assert records[1]["intent_kind"] == "crea un archivo"
    assert records[1]["backend"] == "CDP"

    assert records[2]["intent_kind"] == "normal query"
    assert records[2]["backend"] == "HITL"
    assert records[2]["outcome"] == "success"
