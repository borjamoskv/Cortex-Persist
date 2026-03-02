# tests/test_signal_reactor.py
from unittest.mock import MagicMock, patch

from cortex.signals.bus import SignalBus
from cortex.signals.reactor import SignalReactor


def test_reactor_processes_compact_needed(tmp_path):
    import sqlite3
    db = str(tmp_path / "reactor_test.db")
    conn = sqlite3.connect(db)
    bus = SignalBus(conn)
    
    # Emit a compact:needed signal
    bus.emit("compact:needed", source="test", project="naroa")
    
    # Mock the compact function
    mock_engine = MagicMock()
    reactor = SignalReactor(bus, engine=mock_engine)
    
    with patch("cortex.compaction.compactor.compact") as mock_compact:
        mock_compact.return_value = MagicMock(reduction=10)
        
        count = reactor.process_once()
        
        assert count == 1
        mock_compact.assert_called_once_with(engine=mock_engine, project="naroa", dry_run=False)

def test_reactor_cooldown_on_snapshots(tmp_path):
    import sqlite3
    db = str(tmp_path / "snapshot_test.db")
    conn = sqlite3.connect(db)
    bus = SignalBus(conn)
    
    bus.emit("fact:stored", source="test", project="cortex")
    bus.emit("fact:stored", source="test", project="cortex")
    
    mock_engine = MagicMock()
    reactor = SignalReactor(bus, engine=mock_engine)
    reactor._snapshot_cooldown = 100 # Long cooldown
    
    with patch("cortex.sync.export_snapshot") as mock_export:
        # Process first signal
        count = reactor.process_once()
        assert count == 2 # Both considered processed by the bus (poll returns 2)
        
        # But should only trigger export once due to internal reactor state
        assert mock_export.call_count == 1
