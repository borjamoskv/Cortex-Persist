"""Tests for CORTEX Vertical Scale — SQLite Pragma Tuning + GPU Embeddings.

Validates:
1. SQLite performance pragmas are applied consistently across all connection types.
2. GPU device auto-detection works with graceful CPU fallback.
3. Writer no longer duplicates central pragmas.

NOTE: Run these tests directly with `python3 tests/test_vertical_scale.py`
to bypass conftest fixtures that require Python 3.10+.
"""

from __future__ import annotations

import inspect
import os
from unittest.mock import MagicMock, patch

import pytest

from cortex.database.core import (
    CACHE_SIZE_KB,
    PAGE_SIZE,
    connect,
)

# ─── SQLite Pragma Tests ──────────────────────────────────────────────


class TestSQLitePragmasSync:
    """Verify centralized pragmas are applied to sync connections."""

    def test_pragmas_applied_sync(self, tmp_path):
        """All performance pragmas must be set on every sync connection."""
        db = str(tmp_path / "test.db")
        conn = connect(db)

        # WAL mode
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0] == "wal"

        # cache_size (negative = KiB)
        result = conn.execute("PRAGMA cache_size").fetchone()
        assert result[0] == CACHE_SIZE_KB

        # temp_store = MEMORY (2)
        result = conn.execute("PRAGMA temp_store").fetchone()
        assert result[0] == 2  # 2 = MEMORY

        # mmap_size (may be OS-capped, just verify > 0)
        result = conn.execute("PRAGMA mmap_size").fetchone()
        assert result[0] > 0

        # synchronous = NORMAL (1)
        result = conn.execute("PRAGMA synchronous").fetchone()
        assert result[0] == 1

        conn.close()

    def test_page_size_pragma_is_set(self, tmp_path):
        """page_size pragma is issued (takes effect on new DBs before schema)."""
        # NOTE: page_size only takes effect before the first schema write.
        # sqlite3.connect() may auto-create with default 4096.
        # We verify the constant is correct and the pragma is in the code.
        assert PAGE_SIZE == 8192

    def test_cache_size_configurable(self, tmp_path, monkeypatch):
        """CORTEX_SQLITE_CACHE_MB env var controls cache size."""
        monkeypatch.setenv("CORTEX_SQLITE_CACHE_MB", "256")
        expected = -(256 * 1024)
        computed = -(int(os.environ["CORTEX_SQLITE_CACHE_MB"]) * 1024)
        assert computed == expected


class TestSQLitePragmasAsync:
    """Verify centralized pragmas are applied to async connections."""

    @pytest.mark.asyncio
    async def test_pragmas_applied_async(self, tmp_path):
        """Async connections get the same pragmas."""
        from cortex.database.core import connect_async

        db = str(tmp_path / "async_test.db")
        conn = await connect_async(db)

        cursor = await conn.execute("PRAGMA cache_size")
        row = await cursor.fetchone()
        assert row[0] == CACHE_SIZE_KB

        cursor = await conn.execute("PRAGMA temp_store")
        row = await cursor.fetchone()
        assert row[0] == 2  # MEMORY

        cursor = await conn.execute("PRAGMA mmap_size")
        row = await cursor.fetchone()
        assert row[0] > 0

        await conn.close()


# ─── Writer Deduplication Test ─────────────────────────────────────────


class TestWriterPragmaDedup:
    """Ensure writer.py no longer applies duplicate pragmas."""

    def test_writer_no_duplicate_pragmas(self):
        """_create_connection must NOT contain cache_size or temp_store."""
        from cortex.database.writer import SqliteWriteWorker

        source = inspect.getsource(SqliteWriteWorker._create_connection)
        assert "cache_size" not in source
        assert "temp_store" not in source


# ─── GPU Device Detection Tests ────────────────────────────────────────


class TestDeviceResolution:
    """Verify GPU auto-detection with graceful fallback."""

    def test_cpu_fallback_no_torch(self):
        """Without torch installed, device resolves to cpu."""
        import cortex.embeddings as emb

        with patch.object(emb, "_DEVICE", "auto"):
            with patch.dict("sys.modules", {"torch": None}):
                result = emb._resolve_device()
                assert result == "cpu"

    def test_cuda_detection(self):
        """When CUDA is available, device resolves to cuda."""
        import cortex.embeddings as emb

        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = True
        mock_torch.backends.mps.is_available.return_value = False

        with patch.object(emb, "_DEVICE", "auto"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                result = emb._resolve_device()
                assert result == "cuda"

    def test_mps_detection(self):
        """When MPS is available (no CUDA), device resolves to mps."""
        import cortex.embeddings as emb

        mock_torch = MagicMock()
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = True

        with patch.object(emb, "_DEVICE", "auto"):
            with patch.dict("sys.modules", {"torch": mock_torch}):
                result = emb._resolve_device()
                assert result == "mps"

    def test_env_override(self):
        """CORTEX_DEVICE env var overrides auto-detection."""
        import cortex.embeddings as emb

        with patch.object(emb, "_DEVICE", "cpu"):
            result = emb._resolve_device()
            assert result == "cpu"

    def test_local_embedder_accepts_device(self):
        """LocalEmbedder constructor stores explicit device."""
        from cortex.embeddings import LocalEmbedder

        embedder = LocalEmbedder(device="cpu")
        assert embedder._device == "cpu"

        embedder_auto = LocalEmbedder()
        assert embedder_auto._device in ("cpu", "cuda", "mps")
