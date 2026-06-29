# [C5-REAL] Exergy-Maximized
"""
Tests for the Import Resolution Ledger.
"""

import os
import sys
import json
import pytest
from pathlib import Path

# Ensure the project root is in sys.path
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from babylon60.import_ledger import ImportResolutionLedger

def test_ledger_creation_and_logging(tmp_path):
    ledger_file = tmp_path / "test_ledger.jsonl"
    ledger = ImportResolutionLedger(filepath=str(ledger_file))
    
    ledger.start_session()
    ledger.log_resolution("tests.caller", "cortex.core", "REDIRECTED", "babylon60.core")
    ledger.end_session()
    
    assert ledger_file.exists()
    
    # Read the lines and verify structures
    with open(ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    assert len(lines) == 3
    
    start_entry = json.loads(lines[0])
    assert start_entry["event"] == "SESSION_START"
    assert "session_id" in start_entry
    assert "public_key_pem" in start_entry
    assert start_entry["prev_hash"] == "GENESIS"
    assert "entry_hash" in start_entry
    
    res_entry = json.loads(lines[1])
    assert res_entry["event"] == "RESOLUTION"
    assert res_entry["caller"] == "tests.caller"
    assert res_entry["source"] == "cortex.core"
    assert res_entry["type"] == "REDIRECTED"
    assert res_entry["target"] == "babylon60.core"
    assert res_entry["prev_hash"] == start_entry["entry_hash"]
    assert "entry_hash" in res_entry
    
    end_entry = json.loads(lines[2])
    assert end_entry["event"] == "SESSION_END"
    assert end_entry["session_id"] == start_entry["session_id"]
    assert "signature" in end_entry
    assert end_entry["prev_hash"] == res_entry["entry_hash"]
    assert "entry_hash" in end_entry

    # Verify cryptographic integrity of the ledger
    verification = ImportResolutionLedger.verify_ledger(str(ledger_file))
    assert verification["status"] == "verified"
    assert verification["total_lines"] == 3

def test_ledger_tampering_detection(tmp_path):
    ledger_file = tmp_path / "tampered_ledger.jsonl"
    ledger = ImportResolutionLedger(filepath=str(ledger_file))
    
    ledger.start_session()
    ledger.log_resolution("tests.caller", "cortex.core", "REDIRECTED", "babylon60.core")
    ledger.end_session()
    
    # Assert unmodified is verified
    assert ImportResolutionLedger.verify_ledger(str(ledger_file))["status"] == "verified"
    
    # Read and tamper with the resolution payload
    with open(ledger_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    res_entry = json.loads(lines[1])
    res_entry["target"] = "cortex.tampered"
    lines[1] = json.dumps(res_entry) + "\n"
    
    with open(ledger_file, "w", encoding="utf-8") as f:
        f.writelines(lines)
        
    # Validation must now fail due to hash mismatch
    verification = ImportResolutionLedger.verify_ledger(str(ledger_file))
    assert verification["status"] == "failed"
    assert verification["reason"] == "entry_hash_mismatch"
