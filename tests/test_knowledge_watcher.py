import os
from unittest.mock import MagicMock, patch

from cortex.mcp.knowledge_watcher import KnowledgeItemHandler, start_knowledge_daemon


def test_knowledge_item_handler_sync_file():
    mock_client = MagicMock()
    mock_collection = MagicMock()
    handler = KnowledgeItemHandler(mock_client, mock_collection)

    # Test sync skips non-overview files
    handler._sync_file("/some/path/not_overview.txt")
    mock_collection.upsert.assert_not_called()

    # Test sync triggers on overview.md
    from unittest.mock import mock_open

    with patch("builtins.open", mock_open(read_data="test content")):
        handler._sync_file("/knowledge/my_ki/artifacts/overview.md")
        mock_collection.upsert.assert_called_once()
        args = mock_collection.upsert.call_args.kwargs
        assert args["documents"] == ["test content"]
        assert args["ids"] == ["my_ki"]
        assert args["metadatas"] == [{"source": "my_ki"}]


@patch("cortex.mcp.knowledge_watcher.HAS_WATCHDOG", False)
def test_start_knowledge_daemon_no_watchdog():
    # When HAS_WATCHDOG is False, it should log and return None without crashing
    assert start_knowledge_daemon() is None


@patch("cortex.mcp.knowledge_watcher.HAS_WATCHDOG", True)
@patch("cortex.mcp.knowledge_watcher.chromadb", None)
def test_start_knowledge_daemon_no_chromadb():
    assert start_knowledge_daemon() is None


@patch("cortex.mcp.knowledge_watcher.HAS_WATCHDOG", True)
@patch("cortex.mcp.knowledge_watcher.chromadb")
@patch("cortex.mcp.knowledge_watcher.os.path.exists", return_value=False)
def test_start_knowledge_daemon_no_dir(mock_exists, mock_chroma):
    assert start_knowledge_daemon() is None


@patch("cortex.mcp.knowledge_watcher.HAS_WATCHDOG", True)
@patch("cortex.mcp.knowledge_watcher.chromadb")
@patch("cortex.mcp.knowledge_watcher.os.path.exists", return_value=True)
@patch("cortex.mcp.knowledge_watcher.Observer")
def test_start_knowledge_daemon_success(mock_observer, mock_exists, mock_chroma):
    mock_client = MagicMock()
    mock_chroma.PersistentClient.return_value = mock_client
    mock_observer_inst = MagicMock()
    mock_observer.return_value = mock_observer_inst

    res = start_knowledge_daemon()

    assert res == mock_observer_inst
    mock_observer_inst.schedule.assert_called_once()
    mock_observer_inst.start.assert_called_once()
