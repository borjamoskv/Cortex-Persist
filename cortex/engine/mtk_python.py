# [C5-REAL] Exergy-Maximized
"""
MTK (Minimal Trusted Kernel) - Python Boundary
Enforces the Write-Path Contract (SAGA-less).
SQLite is hooked via `mtk_authorizer_callback`.
"""

import sqlite3
from contextvars import ContextVar
from typing import Optional

# Context variable to hold the ephemeral token
mtk_ephemeral_token: ContextVar[Optional[str]] = ContextVar("mtk_ephemeral_token", default=None)

_PRIVATE_KEY = "CORTEX_LOCAL_KEY_12345" # In production, read from ENV or Keyring

class MTKError(Exception):
    pass

def mint_ephemeral_token(payload: str, kernel_key: str | None = None) -> str:
    """
    Generates an ephemeral token from the cryptographic hash of the ClosurePayload,
    delegating to the Rust C5-REAL core.
    """
    import cortex_rs
    return cortex_rs.mint_ephemeral_token(payload, kernel_key)

from cortex.engine.mtk_sqlite_authorizer import mtk_active_token, mtk_payload_hash


def set_ephemeral_token(token: str, payload_hash: str = "") -> tuple:
    t1 = mtk_ephemeral_token.set(token)
    t2 = mtk_active_token.set(token)
    t3 = mtk_payload_hash.set(payload_hash)
    return (t1, t2, t3)

def clear_ephemeral_token() -> None:
    pass

def restore_ephemeral_token(tokens: tuple) -> None:
    mtk_ephemeral_token.reset(tokens[0])
    mtk_active_token.reset(tokens[1])
    mtk_payload_hash.reset(tokens[2])

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
    conn.set_authorizer(mtk_authorizer_callback)  # type: ignore
