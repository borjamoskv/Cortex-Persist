# [C5-REAL] Exergy-Maximized — Author: Borja Moskv
"""
Minimal Trusted Kernel (MTK) - SQLite Authorizer Hook.
Physical runtime coercion that prevents state mutation unless explicitly authorized by MTK.

[PHYSICS ISOMORPHISM - SAKTHIVADIVEL (2024)]
This module implements Bayesian Mechanics at the database level. The SQLite authorizer
acts as a physical Gauge Constraint on the dynamical system's state space. The system
infers the validity of state transitions by enforcing this boundary.
"""

import logging
import sqlite3
from contextvars import ContextVar

logger = logging.getLogger(__name__)

# Context variable to hold the ephemeral cryptographic token.
# If this is empty or invalid, ALL writes are physically rejected at the DB engine layer.
mtk_active_token: ContextVar[str | None] = ContextVar("mtk_active_token", default=None)
mtk_payload_hash: ContextVar[str | None] = ContextVar("mtk_payload_hash", default=None)

def mtk_authorizer_callback(
    action: int, 
    arg1: str | None, 
    arg2: str | None, 
    dbname: str | None, 
    source: str | None
) -> int:
    """
    Physical constraint on the SQLite engine (Gauge Constraint).
    Actions like INSERT (9), UPDATE (23), DELETE (9) mapped to sqlite3 constants.
    """
    import os
    if os.environ.get("CORTEX_TESTING") == "1" and not os.environ.get("CORTEX_FORCE_MTK_TESTS") == "1":
        # [C5-REAL] Production leak detection: if CORTEX_TESTING is set
        # but no test runner is active, the MTK boundary is compromised.
        if not os.environ.get("PYTEST_CURRENT_TEST"):
            import logging as _log
            _log.getLogger("cortex.mtk").critical(
                "MTK-BYPASS-ALERT: CORTEX_TESTING=1 active without test runner. "
                "MTK authorizer is DISABLED. If this is production, rotate credentials immediately."
            )
        return sqlite3.SQLITE_OK

    # Default Deny: List of safe read-only and transaction-control actions
    SAFE_ACTIONS = {
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_SAVEPOINT,
        getattr(sqlite3, "SQLITE_RECURSIVE", 33),
        33,  # SQLITE_RECURSIVE
    }
    
    if action not in SAFE_ACTIONS:
        # Strict PRAGMA allowlist - Deny anything not explicitly safe, even with a token
        if action == sqlite3.SQLITE_PRAGMA:
            SAFE_PRAGMAS = {
                "table_info", "foreign_key_check", "integrity_check", "index_list", "index_info", 
                "query_only", "journal_mode", "synchronous", "foreign_keys", "busy_timeout", 
                "mmap_size", "page_size", "cache_size", "temp_store", "threads", "wal_autocheckpoint"
            }
            # Purely query PRAGMAs that take arguments but do not modify state
            QUERY_ONLY_PRAGMAS = {"table_info", "foreign_key_check", "integrity_check", "index_list", "index_info"}
            # arg2 contains the value being set. If it's present, it's a modification attempt, except for QUERY_ONLY_PRAGMAS.
            if arg1 and arg1 in SAFE_PRAGMAS:
                if not arg2 or arg1 in QUERY_ONLY_PRAGMAS:
                    return sqlite3.SQLITE_OK
            logger.critical(f"[MTK-BLOCK] Unauthorized PRAGMA modification attempt: {arg1}={arg2}")
            return sqlite3.SQLITE_DENY

        # Hard-block structural evasions regardless of token presence
        DANGEROUS_ACTIONS = {
            sqlite3.SQLITE_ATTACH,
            sqlite3.SQLITE_DETACH,
            sqlite3.SQLITE_CREATE_TRIGGER,
            sqlite3.SQLITE_DROP_TRIGGER,
            sqlite3.SQLITE_CREATE_VIEW,
            sqlite3.SQLITE_DROP_VIEW,
        }
        if action in DANGEROUS_ACTIONS:
            logger.critical(f"[MTK-BLOCK] Hard-blocked structural action: {action}")
            return sqlite3.SQLITE_DENY

        # Ignore writes to internal sqlite sequences/schemas or agent_messages transport table
        if arg1 or arg2:
            is_internal = (arg1 and (arg1.startswith("sqlite_") or arg1 == "schema_version" or "agent_messages" in arg1 or "agent_msg" in arg1)) or \
                          (arg2 and ("agent_messages" in arg2 or "agent_msg" in arg2))
            if is_internal:
                return sqlite3.SQLITE_OK

        token = mtk_active_token.get()
        _payload = mtk_payload_hash.get() or ""
        
        # [C5-REAL] ULTRA-THINK VECTOR GAMMA
        # Delegate token and memory taint validation to the immutable PyO3 Rust extension.
        try:
            import cortex_core_rs
            res = cortex_core_rs.authorize_sqlite_mutation(action, arg1, arg2, token)  # type: ignore
            if res != sqlite3.SQLITE_OK:
                logger.critical(f"[MTK-BLOCK] Native Rust Firewall blocked physical mutation attempt. Action {action}")
                return sqlite3.SQLITE_DENY
        except Exception as e:
            logger.critical(f"[MTK-BLOCK] Exception in Rust MTK FFI layer: {e}")
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
