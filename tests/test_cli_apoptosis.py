import os
import json
import pytest
from click.testing import CliRunner
from babylon60.cli import cli
from babylon60.engine import CortexEngine

def test_cli_apoptosis_aof(tmp_path):
    """
    Test that 'cortex apoptosis' on a .aof target triggers
    ThermodynamicLedgerApoptosis and prunes deleted/orphan subgraphs.
    """
    aof_file = tmp_path / "ledger.aof"
    
    # Write nodes: node_1 is active, node_2 is deleted, node_3 depends on node_2 (orphan)
    node_1 = {"hash_id": "node_1", "content": "active"}
    node_2 = {"hash_id": "node_2", "status": "deleted", "content": "dead"}
    node_3 = {"hash_id": "node_3", "parent_hash": "node_2", "content": "orphan"}
    
    with open(aof_file, "w", encoding="utf-8") as f:
        f.write(json.dumps(node_1) + "\n")
        f.write(json.dumps(node_2) + "\n")
        f.write(json.dumps(node_3) + "\n")
        
    runner = CliRunner()
    result = runner.invoke(cli, ["apoptosis", str(aof_file)])
    assert result.exit_code == 0
    assert "AOF Apoptosis complete" in result.output
    assert "Retained 1 active nodes" in result.output
    
    # Check that only node_1 remains
    with open(aof_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    assert len(lines) == 1
    remaining_node = json.loads(lines[0])
    assert remaining_node["hash_id"] == "node_1"

def test_cli_apoptosis_db(tmp_path):
    """
    Test that 'cortex apoptosis' on a .db target triggers
    ApoptosisAgent to prune low-exergy or low-entropy facts.
    """
    db_file = tmp_path / "test.db"
    engine = CortexEngine(db_path=db_file)
    engine.init_db_sync()
    
    # Seed facts using raw SQL to manually specify exergy_score and metadata to pass taint trigger
    import sqlite3
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()
    metadata_val = json.dumps({"cortex_taint": "taint:system:test:2026-06-30T00:00:00Z:0:test_bypass"})
    # High exergy fact (should keep)
    cursor.execute(
        "INSERT INTO facts (project, content, tenant_id, exergy_score, metadata, is_tombstoned) VALUES (?, ?, ?, ?, ?, 0)",
        ("proj", "This is a very high quality structured fact for execution.", "default", 1.0, metadata_val)
    )
    # Low exergy fact (should prune)
    cursor.execute(
        "INSERT INTO facts (project, content, tenant_id, exergy_score, metadata, is_tombstoned) VALUES (?, ?, ?, ?, ?, 0)",
        ("proj", "thanks!", "default", 0.1, metadata_val)
    )
    conn.commit()
    conn.close()
    
    runner = CliRunner()
    result = runner.invoke(cli, ["apoptosis", str(db_file), "--tenant", "default"])
    assert result.exit_code == 0
    assert "Database Apoptosis complete" in result.output
    assert "Scanned: 2" in result.output
    assert "Tombstoned: 1" in result.output
