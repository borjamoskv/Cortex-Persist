# [C5-REAL] Exergy-Maximized
"""
MTK (Minimal Trusted Kernel) - Python Boundary
Enforces the Write-Path Contract (SAGA-less).
SQLite is hooked via `mtk_authorizer_callback`.
"""

import hashlib
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
import time
from contextvars import ContextVar
from typing import Optional

# Context variable to hold the ephemeral token
mtk_ephemeral_token: ContextVar[Optional[str]] = ContextVar("mtk_ephemeral_token", default=None)

_PRIVATE_KEY = "CORTEX_LOCAL_KEY_12345" # In production, read from ENV or Keyring

class MTKError(Exception):
    pass

def mint_ephemeral_token(payload: str) -> str:
    """
    Generates an ephemeral token from the cryptographic hash of the ClosurePayload.
    """
    now = str(time.time())
    raw = f"{payload}:{_PRIVATE_KEY}:{now}".encode()
    token = hashlib.sha256(raw).hexdigest()
    return f"mtk_auth_{token}"

def set_ephemeral_token(token: str) -> None:
    mtk_ephemeral_token.set(token)

def clear_ephemeral_token() -> None:
    mtk_ephemeral_token.set(None)

def mtk_authorizer_callback(action: int, arg1: str, arg2: str, dbname: str, source: str) -> int:
    """
    SQLite authorizer callback.
    action: SQLITE_INSERT (18), SQLITE_UPDATE (23), SQLITE_DELETE (9), etc.
    Returns sqlite3.SQLITE_OK, sqlite3.SQLITE_DENY, or sqlite3.SQLITE_IGNORE.
    """
    # Only restrict mutations
    if action in (sqlite3.SQLITE_INSERT, sqlite3.SQLITE_UPDATE, sqlite3.SQLITE_DELETE):
        # Allow internal sqlite tables
        if arg1 and arg1.startswith("sqlite_"):
            return sqlite3.SQLITE_OK
            
        current_token = mtk_ephemeral_token.get()
        if not current_token or not current_token.startswith("mtk_auth_"):
            # PHYSICAL DB REJECTION: SQLITE_DENY
            return sqlite3.SQLITE_DENY
            
    return sqlite3.SQLITE_OK

def attach_mtk_authorizer(conn: sqlite3.Connection) -> None:
    """
    Attaches the MTK authorizer to an SQLite connection.
    """
    conn.set_authorizer(mtk_authorizer_callback)
