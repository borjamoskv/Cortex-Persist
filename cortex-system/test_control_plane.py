"""
C5-REAL: Adversarial Test Suite for Control Plane
Author: Borja Moskv / borjamoskv
"""

import sys
import os
import json
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parent
sys.path.append(str(ROOT))

from control_plane import ControlPlane
from runtime.session_router import SessionRouter
from babylon60.extensions.artist_cortex.artist_cortex import ArtistCortexEngine

@pytest.fixture
def temp_environment(tmp_path):
    """Sets up temporary registry.json and sqlite database paths."""
    registry_file = tmp_path / "registry.json"
    db_file = tmp_path / "test_artist_cortex.db"
    
    # Write default registry configuration
    default_registry = {
        "active_core_vector": "ARTE_PURO"
    }
    with open(registry_file, "w", encoding="utf-8") as f:
        json.dump(default_registry, f)
        
    return registry_file, db_file

@pytest.mark.asyncio
async def test_control_plane_initialization(temp_environment):
    """Validates that ControlPlane initializes its components and DB schemas successfully."""
    registry_file, db_file = temp_environment
    
    cp = ControlPlane(
        registry_path=str(registry_file),
        db_path=str(db_file)
    )
    
    assert cp.registry["active_core_vector"] == "ARTE_PURO"
    assert os.path.exists(db_file)
    
    # Verify that the session_router automatically applied foundational migrations
    cursor = cp.session_router.engine.conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]
    
    assert "cortex_sessions" in tables
    assert "cortex_artifacts" in tables
    assert "cortex_metrics" in tables
    assert "cortex_events" in tables
    
    cp.session_router.close()

@pytest.mark.asyncio
async def test_control_plane_cycle_execution(temp_environment):
    """Simulates a complete creative validation cycle under control plane supervision."""
    registry_file, db_file = temp_environment
    
    cp = ControlPlane(
        registry_path=str(registry_file),
        db_path=str(db_file)
    )
    
    # Mock SwarmDispatcher.schedule_collision to isolate the network/subprocess worker
    mock_result = {
        "status": "committed",
        "artifact_id": 1,
        "artifact_key": "art_1_testjob",
        "metrics": {
            "originality_raw": 0.75,
            "friction_ms": 1200,
            "attention_yield": 0.80
        }
    }
    
    # Pre-populate cortex_artifacts in test DB to satisfy Foreign Key constraints
    cursor = cp.session_router.engine.conn.cursor()
    cursor.execute("""
        INSERT INTO cortex_sessions (id, operator_id, core_vector)
        VALUES (1, 'borjamoskv', 'ARTE_PURO')
    """)
    cursor.execute("""
        INSERT INTO cortex_artifacts (id, session_id, artifact_key, artifact_type, status)
        VALUES (1, 1, 'art_1_testjob', 'narrative', 'draft')
    """)
    cp.session_router.engine.conn.commit()

    with patch.object(cp.dispatcher, "schedule_collision", new_callable=AsyncMock) as mock_schedule:
        mock_schedule.return_value = mock_result
        
        cycle_result = await cp.execute_cycle(prompt="Sonic waves propagation", operator_id="borjamoskv")
        
        assert cycle_result["status"] == "success"
        assert cycle_result["artifact_id"] == 1
        assert cycle_result["artifact_key"] == "art_1_testjob"
        assert cycle_result["evolutionary_action"] in ("trigger_rupture", "stable", "inject_attention_pressure", "force_swarm_mode")
        
        # Verify that metrics were written to the db
        cursor = cp.session_router.engine.conn.cursor()
        cursor.execute("SELECT metric_name, metric_value FROM cortex_metrics WHERE artifact_id = 1;")
        metrics = {row[0]: row[1] for row in cursor.fetchall()}
        
        assert metrics["originality_raw"] == 0.75
        assert metrics["friction_ms"] == 1200.0
        assert metrics["attention_yield"] == 0.80
        
    cp.session_router.close()

@pytest.mark.asyncio
async def test_control_plane_cycle_abort_rules(temp_environment):
    """Validates that execute_cycle rolls back/flags artifacts as rejected when abort triggers."""
    registry_file, db_file = temp_environment
    
    cp = ControlPlane(
        registry_path=str(registry_file),
        db_path=str(db_file)
    )
    
    # Force a mock result that triggers AbortRules (e.g., originality_raw < 0.20)
    mock_abort_result = {
        "status": "committed",
        "artifact_id": 42,
        "artifact_key": "art_1_abortjob",
        "metrics": {
            "originality_raw": 0.10,  # Fails originality threshold check (min 0.20)
            "friction_ms": 1500,
            "attention_yield": 0.50
        }
    }
    
    # Pre-populate cortex_artifacts in test DB so UPDATE doesn't fail silently
    cursor = cp.session_router.engine.conn.cursor()
    cursor.execute("""
        INSERT INTO cortex_sessions (id, operator_id, core_vector)
        VALUES (1, 'borjamoskv', 'ARTE_PURO')
    """)
    cursor.execute("""
        INSERT INTO cortex_artifacts (id, session_id, artifact_key, artifact_type, status)
        VALUES (42, 1, 'art_1_abortjob', 'narrative', 'draft')
    """)
    cp.session_router.engine.conn.commit()
    
    with patch.object(cp.dispatcher, "schedule_collision", new_callable=AsyncMock) as mock_schedule:
        mock_schedule.return_value = mock_abort_result
        
        with pytest.raises(RuntimeError, match="Saga abort"):
            await cp.execute_cycle(prompt="Failing entropy flow", operator_id="borjamoskv")
            
        # Verify artifact status was updated to 'rejected'
        cursor.execute("SELECT status FROM cortex_artifacts WHERE id = 42;")
        status = cursor.fetchone()[0]
        assert status == "rejected"
        
    cp.session_router.close()
