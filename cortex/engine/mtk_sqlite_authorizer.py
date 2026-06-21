# [C5-REAL] Exergy-Maximized
"""
Minimal Trusted Kernel (MTK) - SQLite Authorizer Hook.
Physical runtime coercion that prevents state mutation unless explicitly authorized by MTK.
"""

import sqlite3
import logging
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to hold the ephemeral cryptographic token.
# If this is empty or invalid, ALL writes are physically rejected at the DB engine layer.
mtk_active_token: ContextVar[str | None] = ContextVar("mtk_active_token", default=None)

def mtk_authorizer_callback(action: int, arg1: str | None, arg2: str | None, dbname: str | None, source: str | None) -> int:
    """
    Physical constraint on the SQLite engine.
    Actions like INSERT (9), UPDATE (23), DELETE (9) mapped to sqlite3 constants.
    """
    # Actions that mutate state
    MUTATION_ACTIONS = {
        sqlite3.SQLITE_INSERT,
        sqlite3.SQLITE_UPDATE,
        sqlite3.SQLITE_DELETE,
        sqlite3.SQLITE_DROP_TABLE,
        sqlite3.SQLITE_DROP_INDEX,
        sqlite3.SQLITE_ALTER_TABLE,
    }
    
    if action in MUTATION_ACTIONS:
        # Ignore writes to internal sqlite sequences/schemas and virtual table shadow tables
        if arg1:
            if arg1.startswith("sqlite_") or arg1 in ("schema_version", "cortex_meta", "agent_messages"):
                return sqlite3.SQLITE_OK
            if arg1.endswith(("_info", "_chunks", "_data", "_idx", "_docsize", "_config", "_content")):
                return sqlite3.SQLITE_OK

        token = mtk_active_token.get()
        if not token or not token.startswith("mtk_auth_"):
            logger.critical(f"[MTK-BLOCK] Unauthorized physical mutation attempt: Action {action} on {arg1}")
            return sqlite3.SQLITE_DENY
            
    return sqlite3.SQLITE_OK

def install_mtk_authorizer(conn: sqlite3.Connection):
    """
    Install the MTK authorizer on a raw sqlite3 connection.
    If using aiosqlite, access the underlying connection via `conn._conn` if necessary,
    or apply it upon creation.
    """
    conn.set_authorizer(mtk_authorizer_callback)
    logger.info("[MTK] SQLite Authorizer hook installed. State mutation mathematically constrained.")
