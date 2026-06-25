# [C5-REAL] Exergy-Maximized
"""Tests for security fixes in cortex/crypto/aes.py:
1. STRICT_CRYPTO_MODE: raises ValueError on plaintext decryption, RuntimeError on encryption without Master Key.
2. Dynamic salt: loads salt from DB and updates config HKDF_SALT.
3. Safe singleton initialization.
"""

import sqlite3

# --- C5-REAL BFT PATCH (R10) ---
import sqlite3 as _sqlite3_bft_orig
_orig_sqlite_connect = _sqlite3_bft_orig.connect
def _bft_sqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    conn = _orig_sqlite_connect(*args, **kwargs)
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA busy_timeout=5000;")
        conn.execute("PRAGMA synchronous=NORMAL;")
    except Exception:
        pass
    return conn
_sqlite3_bft_orig.connect = _bft_sqlite_connect
# -------------------------------
import pytest
from unittest.mock import patch

from babylon60.crypto.aes import CortexEncrypter, get_default_encrypter, reset_default_encrypter
from babylon60.core.config import reload as reload_config


def test_strict_crypto_mode():
    """Verify that STRICT_CRYPTO_MODE raises ValueError on decrypt and RuntimeError on encrypt."""
    enc = CortexEncrypter(master_key=b"1" * 32, strict_mode=True)
    assert enc.strict_mode is True

    # Decrypting plaintext should raise ValueError in strict mode
    with pytest.raises(ValueError) as excinfo:
        enc.decrypt_str("unencrypted_data_string")
    assert "Strict crypto mode active" in str(excinfo.value)

    # Empty or None should not raise error even in strict mode
    assert enc.decrypt_str(None) is None
    assert enc.decrypt_str("") == ""

    # Encrypting without Master Key in strict mode should raise RuntimeError
    inactive_enc = CortexEncrypter(master_key=None, strict_mode=True)
    with pytest.raises(RuntimeError) as excinfo_enc:
        inactive_enc.encrypt_str("plaintext")
    assert "cannot encrypt data without a loaded Master Key" in str(excinfo_enc.value)


def test_inactive_no_strict_mode():
    """Verify that inactive encrypter without strict mode returns plaintext."""
    enc = CortexEncrypter(master_key=None, strict_mode=False)
    assert not enc.is_active
    assert enc.encrypt_str("plaintext") == "plaintext"
    assert enc.decrypt_str("ciphertext") == "ciphertext"


@pytest.mark.asyncio
async def test_dynamic_salt_resolution(tmp_path):
    """Verify that salt is resolved dynamically from SQLite DB metadata on bootstrap."""
    import aiosqlite

# --- C5-REAL BFT PATCH AIOSQLITE (R10) ---
import aiosqlite as _aiosqlite_bft_orig
_orig_aiosqlite_connect = _aiosqlite_bft_orig.connect
def _bft_aiosqlite_connect(*args, **kwargs):
    kwargs.setdefault('timeout', 5.0)
    class BFTConnectionContext:
        def __init__(self, *args, **kwargs):
            self._conn_future = _orig_aiosqlite_connect(*args, **kwargs)
        async def __aenter__(self):
            self.conn = await self._conn_future.__aenter__()
            await self.conn.execute("PRAGMA journal_mode=WAL;")
            await self.conn.execute("PRAGMA busy_timeout=5000;")
            await self.conn.execute("PRAGMA synchronous=NORMAL;")
            return self.conn
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            await self._conn_future.__aexit__(exc_type, exc_val, exc_tb)
        def __await__(self):
            async def _init():
                conn = await self._conn_future
                await conn.execute("PRAGMA journal_mode=WAL;")
                await conn.execute("PRAGMA busy_timeout=5000;")
                await conn.execute("PRAGMA synchronous=NORMAL;")
                return conn
            return _init().__await__()
    return BFTConnectionContext(*args, **kwargs)
_aiosqlite_bft_orig.connect = _bft_aiosqlite_connect
# ----------------------------------------

    db_file = tmp_path / "test_cortex.db"

    # Pre-populate the metadata DB with a unique salt
    conn = sqlite3.connect(str(db_file))
    conn.execute("CREATE TABLE cortex_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    conn.execute(
        "INSERT INTO cortex_meta (key, value) VALUES ('tenant_isolation_salt', 'custom_db_salt_value')"
    )
    conn.commit()
    conn.close()

    # Create ConnectionMixin context to run _ensure_schema_ready
    from babylon60.engine._engine_connection import ConnectionMixin

    class DummyEngine(ConnectionMixin):
        def __init__(self, db_path):
            self._db_path = db_path
            self._schema_ready = False
            self._ledger = None
            self._db_conn = None

        async def _get_or_create_conn(self):
            if self._db_conn is None:
                self._db_conn = await aiosqlite.connect(self._db_path)
            return self._db_conn

    # Use patch to verify config is updated
    engine = DummyEngine(str(db_file))
    conn = await engine._get_or_create_conn()

    # Run schema ready check, which triggers the custom_db_salt_value loading
    await engine._ensure_schema_ready(conn)
    await conn.close()

    import babylon60.core.config as config

    assert config.HKDF_SALT == "custom_db_salt_value"

    # Reset config back to default to clean up
    reload_config()


def test_singleton_thread_safety_exceptions():
    """Verify that singleton initialization recovers from errors inside get_master_key."""
    reset_default_encrypter()

    # Simulate an exception inside get_master_key
    with patch(
        "babylon60.crypto.keyring.get_master_key", side_effect=RuntimeError("Keychain failure")
    ):
        with pytest.raises(RuntimeError, match="Keychain failure"):
            get_default_encrypter()

    # The singleton should remain None, allowing a retry
    from babylon60.crypto.aes import _default_encrypter_instance

    assert _default_encrypter_instance is None

    # Now allow it to succeed
    with patch("babylon60.crypto.keyring.get_master_key", return_value=b"3" * 32):
        enc = get_default_encrypter()
        assert enc is not None
        assert enc.is_active
    reset_default_encrypter()
