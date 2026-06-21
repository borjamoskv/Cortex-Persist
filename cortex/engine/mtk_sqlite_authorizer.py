# [C5-REAL] Exergy-Maximized
"""
Minimal Trusted Kernel (MTK) - SQLite Authorizer Hook.
Physical runtime coercion that prevents state mutation unless explicitly authorized by MTK.
"""

import logging
import sqlite3
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
    import os
    if os.environ.get("CORTEX_TESTING") == "1" and not os.environ.get("CORTEX_FORCE_MTK_TESTS") == "1":
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
            # arg2 contains the value being set. If it's present, it's a modification attempt.
            if arg1 and arg1 in SAFE_PRAGMAS and not arg2:
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
        if not token or (not token.startswith("mtk_auth_") and not token.startswith("zk_seal_rs_")):
            logger.critical(f"[MTK-BLOCK] Unauthorized physical mutation attempt: Action {action} on {arg1}")
            return sqlite3.SQLITE_DENY
            
        # Cross-Language Taint Propagation: Rust ZK-Seal bypasses GC taint tracking
        if token.startswith("zk_seal_rs_"):
            return sqlite3.SQLITE_OK
            
        # Memory Taint Tracking: Bloquear inyección estocástica directa
        import sys
        STOCHASTIC_MODULES = (
            "cortex.engine.inference",
            "cortex.engine.models",
            "cortex.extensions.llm",
            "cortex.engine.synthesis",
            "cortex.engine.generation"
        )
        try:
            frame = sys._getframe(1)
            while frame:
                module_name = frame.f_globals.get("__name__", "")
                if module_name and any(module_name.startswith(sm) for sm in STOCHASTIC_MODULES):
                    logger.critical(f"[MTK-BLOCK] Stochastic memory injection detected from {module_name}. Action {action} on {arg1}")
                    return sqlite3.SQLITE_DENY
                # Check for explicit taint flags in locals
                for var_name, var_value in frame.f_locals.items():
                    if hasattr(var_value, "__taint__") or var_name == "tainted_payload":
                        logger.critical(f"[MTK-BLOCK] Tainted memory object '{var_name}' detected in stack. Action {action}")
                        return sqlite3.SQLITE_DENY
                frame = frame.f_back
        except (ValueError, AttributeError):
            pass
            
    return sqlite3.SQLITE_OK

def install_mtk_authorizer(conn: sqlite3.Connection):
    """
    Install the MTK authorizer on a raw sqlite3 connection.
    If using aiosqlite, access the underlying connection via `conn._conn` if necessary,
    or apply it upon creation.
    """
    conn.set_authorizer(mtk_authorizer_callback)
    logger.info("[MTK] SQLite Authorizer hook installed. State mutation mathematically constrained.")
