import pytest
from pathlib import Path
from click.testing import CliRunner
import json
from unittest.mock import patch

from cortex.cli.notebooklm_cmds import notebooklm_cmds

@pytest.fixture
def mock_drive_dir(tmp_path):
    d = tmp_path / "GoogleDrive" / "CORTEX-NotebookLM"
    d.mkdir(parents=True)
    
    # Create a dummy synthesis file
    f = d / "Studio_Overview_NotebookLM.md"
    f.write_text("# Synthesis\\n\\nHere is what we discovered...", encoding="utf-8")
    
    return d

@pytest.mark.asyncio
@patch("cortex.cli.notebooklm_cmds._detect_cloud_sync")
async def test_notebooklm_ingest_no_cloud_storage(mock_cloud_sync, capsys):
    mock_cloud_sync.return_value = None
    runner = CliRunner()
    result = runner.invoke(notebooklm_cmds, ["ingest"])
    assert result.exit_code == 0
    assert "Cloud Storage no detectado" in result.output or "El directorio" in result.output
    
@patch("cortex.cli.notebooklm_cmds.SovereignLLM")
@patch("cortex.cli.notebooklm_cmds.get_engine")
def test_notebooklm_ingest_with_mock_drive(mock_get_engine, mock_llm_cls, mock_drive_dir, capsys):
    # Mock engine
    mock_engine = mock_get_engine.return_value
    
    # Mock LLM return value
    # We return a JSON array string
    mock_llm_instance = mock_llm_cls.return_value.__aenter__.return_value
    
    class MockResult:
        ok = True
        content = '[{"fact_type": "decision", "project": "cortex", "content": "NotebookLM parsed text"}]'
        provider = "mock"
    
    import asyncio
    async def mock_generate(*args, **kwargs):
        return MockResult()
        
    mock_llm_instance.generate = mock_generate
    
    # Mock engine methods
    async def mock_init(): pass
    async def mock_close(): pass
    async def mock_store_many(facts):
        return [1] # Return fake IDs
        
    mock_engine.init_db = mock_init
    mock_engine.close = mock_close
    mock_engine.store_many = mock_store_many
    
    runner = CliRunner()
    result = runner.invoke(notebooklm_cmds, ["ingest", "--drive-path", str(mock_drive_dir)])
    
    assert result.exit_code == 0
    assert "Analizando sí" in result.output
    assert "Se extrajeron 1 hechos" in result.output
    assert "Loop Completado" in result.output
    
    # Verify manifest was created
    manifest = mock_drive_dir / ".cortex_ingest_manifest.json"
    assert manifest.exists()
    proc = json.loads(manifest.read_text())
    assert "Studio_Overview_NotebookLM.md" in proc
