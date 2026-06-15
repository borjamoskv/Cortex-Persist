import sys
import subprocess

def test_cli_help():
    result = subprocess.run([sys.executable, "-m", "cortex.integration.cli", "--help"], capture_output=True, text=True)
    assert "emit" in result.stdout
    assert "snapshot" in result.stdout
    assert "bridge" in result.stdout
    assert "verify" in result.stdout

def test_cli_emit(tmp_path):
    caps_file = tmp_path / "caps.json"
    caps_file.write_text('{"schema_version": "1.0", "routes": {}}')
    
    result = subprocess.run([
        sys.executable, "-m", "cortex.integration.cli", "emit",
        "--agent-id", "agent-x",
        "--modules-dir", str(tmp_path),
        "--capabilities", str(caps_file)
    ], cwd=tmp_path, capture_output=True, text=True)
    
    assert result.returncode == 0
    event_file = tmp_path / "output" / "telemetry_event.json"
    assert event_file.exists()
    assert '"agent_id": "agent-x"' in event_file.read_text()

def test_cli_snapshot(tmp_path):
    agents_md = tmp_path / "agents.md"
    agents_md.write_text("# Agents configuration")
    contracts = tmp_path / "contracts.json"
    contracts.write_text('{"main": "v1"}')
    
    result = subprocess.run([
        sys.executable, "-m", "cortex.integration.cli", "snapshot",
        "--agents-md", str(agents_md),
        "--contracts", str(contracts)
    ], cwd=tmp_path, capture_output=True, text=True)
    
    assert result.returncode == 0
    snapshot_file = tmp_path / "output" / "morph_snapshot.json"
    assert snapshot_file.exists()
    assert "snapshot_id" in snapshot_file.read_text()

def test_cli_bridge(tmp_path):
    exp = tmp_path / "exp.json"
    exp.write_text('{"route": "cmd", "params": ["a"]}')
    act = tmp_path / "act.json"
    act.write_text('{"route": "cmd", "params": []}')
    
    result = subprocess.run([
        sys.executable, "-m", "cortex.integration.cli", "bridge",
        "--agent-id", "agent-x",
        "--expected", str(exp),
        "--actual", str(act)
    ], cwd=tmp_path, capture_output=True, text=True)
    
    assert result.returncode == 0
    bridge_file = tmp_path / "output" / "bridge_artifact.json"
    assert bridge_file.exists()
    assert "bridge_id" in bridge_file.read_text()

def test_cli_verify(tmp_path):
    bundle = tmp_path / "bundle.json"
    bundle.write_text('{"agent_id": "x", "fingerprint": "y", "timestamp": 1.0, "capabilities": {}, "schema_version": "1.0"}')
    
    result = subprocess.run([
        sys.executable, "-m", "cortex.integration.cli", "verify",
        "--bundle", str(bundle)
    ], cwd=tmp_path, capture_output=True, text=True)
    
    assert result.returncode == 0
    assert '"valid": true' in result.stdout

