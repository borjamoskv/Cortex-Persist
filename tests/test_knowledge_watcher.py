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

    # Test sync handles empty content gracefully
    mock_collection.reset_mock()
    with patch("builtins.open", mock_open(read_data="   \n   ")):
        handler._sync_file("/knowledge/my_ki/artifacts/overview.md")
        mock_collection.upsert.assert_not_called()

    # Test sync handles unknown ki path format
    mock_collection.reset_mock()
    with patch("builtins.open", mock_open(read_data="valid")):
        handler._sync_file("overview.md")  # No directory structure
        mock_collection.upsert.assert_called_once()
        args = mock_collection.upsert.call_args.kwargs
        assert args["ids"] == ["unknown_ki"]

    # Test sync exception handling
    mock_collection.reset_mock()
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        handler._sync_file("/knowledge/my_ki/artifacts/overview.md")
        mock_collection.upsert.assert_not_called()


def test_knowledge_item_handler_events():
    mock_client = MagicMock()
    mock_collection = MagicMock()
    handler = KnowledgeItemHandler(mock_client, mock_collection)

    with patch.object(handler, "_sync_file") as mock_sync:
        mock_event = MagicMock(is_directory=False, src_path="test.md")
        handler.on_modified(mock_event)
        mock_sync.assert_called_once_with("test.md")

        mock_sync.reset_mock()
        handler.on_created(mock_event)
        mock_sync.assert_called_once_with("test.md")

        mock_sync.reset_mock()
        dir_event = MagicMock(is_directory=True, src_path="dir")
        handler.on_modified(dir_event)
        handler.on_created(dir_event)
        mock_sync.assert_not_called()


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


@patch("cortex.mcp.knowledge_watcher.HAS_WATCHDOG", True)
@patch("cortex.mcp.knowledge_watcher.chromadb")
@patch("cortex.mcp.knowledge_watcher.os.path.exists", return_value=True)
@patch("cortex.mcp.knowledge_watcher.Observer", side_effect=RuntimeError("Observer failed"))
def test_start_knowledge_daemon_exception(mock_observer, mock_exists, mock_chroma):
    mock_client = MagicMock()
    mock_chroma.PersistentClient.return_value = mock_client

    # Should catch exception, log error, and return None
    assert start_knowledge_daemon() is None
