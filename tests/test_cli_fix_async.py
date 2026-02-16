import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch, AsyncMock
from cortex.cli.sync_cmds import export, sync

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.init_db = MagicMock()
    engine.close = MagicMock()
    return engine

@patch('cortex.cli.sync_cmds.get_engine')
@patch('cortex.cli.sync_cmds.export_snapshot', new_callable=AsyncMock)
def test_export_async_execution(mock_export_snapshot, mock_get_engine, runner, mock_engine):
    """Verify export command awaits export_snapshot using asyncio.run."""
    mock_get_engine.return_value = mock_engine
    
    result = runner.invoke(export, ['--out', '/tmp/test_snapshot.md'])
    
    assert result.exit_code == 0
    # If async was not awaited, this mock wouldn't be awaited or called correctly in loop
    mock_export_snapshot.assert_awaited()
    assert "Snapshot exportado" in result.output

@patch('cortex.cli.sync_cmds.get_engine')
@patch('cortex.cli.sync_cmds.sync_memory', new_callable=AsyncMock)
def test_sync_async_execution(mock_sync_memory, mock_get_engine, runner, mock_engine):
    """Verify sync command awaits sync_memory using asyncio.run."""
    mock_get_engine.return_value = mock_engine
    
    # Setup mock result
    mock_result = MagicMock()
    mock_result.had_changes = True
    mock_result.facts_synced = 5
    mock_result.ghosts_synced = 0
    mock_result.errors_synced = 0
    mock_result.bridges_synced = 0
    mock_result.skipped = 2
    mock_result.errors = []
    mock_sync_memory.return_value = mock_result
    
    result = runner.invoke(sync, [])
    
    assert result.exit_code == 0
    # Ensure it was awaited
    mock_sync_memory.assert_awaited()
    assert "Sincronización completada" in result.output
