import pytest
import asyncio
from pathlib import Path
from cortex.integration.telemetry import AgentTelemetryEmitter, compute_agent_fingerprint

@pytest.mark.asyncio
async def test_telemetry_emits_valid_event(tmp_path):
    emitted = []
    async def mock_publish(event_dict):
        emitted.append(event_dict)
    
    emitter = AgentTelemetryEmitter(
        agent_id="cortex-001",
        modules_dir=tmp_path,
        schema_paths=[],
        capability_manifest={"schema_version": "1.0", "routes": {}},
        publish=mock_publish,
        interval_s=0.1
    )
    
    event = await emitter.emit_once()
    assert event.agent_id == "cortex-001"
    assert len(emitted) == 1
    assert emitted[0]["agent_id"] == "cortex-001"

def test_fingerprint_determinism(tmp_path):
    fp1 = compute_agent_fingerprint("agent-1", tmp_path, [], {"caps": "test"})
    fp2 = compute_agent_fingerprint("agent-1", tmp_path, [], {"caps": "test"})
    assert fp1 == fp2

def test_fingerprint_changes_on_module_change(tmp_path):
    modules_dir = tmp_path / "modules"
    modules_dir.mkdir()
    
    fp_empty = compute_agent_fingerprint("agent-1", modules_dir, [], {"caps": "test"})
    
    f1 = modules_dir / "mod1.py"
    f1.write_text("code_v1", encoding="utf-8")
    fp_v1 = compute_agent_fingerprint("agent-1", modules_dir, [], {"caps": "test"})
    assert fp_empty != fp_v1
    
    f1.write_text("code_v2", encoding="utf-8")
    fp_v2 = compute_agent_fingerprint("agent-1", modules_dir, [], {"caps": "test"})
    assert fp_v1 != fp_v2

def test_fingerprint_changes_on_schema_change(tmp_path):
    schema1 = tmp_path / "schema1.json"
    schema1.write_text("s1", encoding="utf-8")
    
    fp_v1 = compute_agent_fingerprint("agent-1", tmp_path / "empty", [schema1], {"caps": "test"})
    
    schema1.write_text("s2", encoding="utf-8")
    fp_v2 = compute_agent_fingerprint("agent-1", tmp_path / "empty", [schema1], {"caps": "test"})
    assert fp_v1 != fp_v2

def test_fingerprint_changes_on_capabilities_change(tmp_path):
    fp_v1 = compute_agent_fingerprint("agent-1", tmp_path, [], {"caps": "test1"})
    fp_v2 = compute_agent_fingerprint("agent-1", tmp_path, [], {"caps": "test2"})
    assert fp_v1 != fp_v2

@pytest.mark.asyncio
async def test_telemetry_monotonicity(tmp_path):
    emitted = []
    async def mock_publish(event_dict):
        emitted.append(event_dict)
    
    emitter = AgentTelemetryEmitter(
        agent_id="cortex-001",
        modules_dir=tmp_path,
        schema_paths=[],
        capability_manifest={"schema_version": "1.0", "routes": {}},
        publish=mock_publish,
    )
    
    event1 = await emitter.emit_once()
    event2 = await emitter.emit_once()
    assert event2.timestamp >= event1.timestamp

@pytest.mark.asyncio
async def test_telemetry_emitter_run_and_stop(tmp_path):
    emitted = []
    async def mock_publish(event_dict):
        emitted.append(event_dict)
    
    emitter = AgentTelemetryEmitter(
        agent_id="cortex-001",
        modules_dir=tmp_path,
        schema_paths=[],
        capability_manifest={"schema_version": "1.0", "routes": {}},
        publish=mock_publish,
        interval_s=0.01
    )
    
    task = asyncio.create_task(emitter.run())
    await asyncio.sleep(0.05)
    emitter.stop()
    await task
    assert len(emitted) > 0

