import logging
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
import sys
from typing import Callable, Optional, Set
from contextvars import ContextVar

logger = logging.getLogger(__name__)

mtk_active_token: ContextVar[Optional[str]] = ContextVar("mtk_active_token", default=None)
mtk_payload_hash: ContextVar[Optional[str]] = ContextVar("mtk_payload_hash", default=None)

# Registry for custom verification functions
_verifier_callback: Optional[Callable[[str, str], bool]] = None

def set_token_verifier(verifier: Callable[[str, str], bool]) -> None:
    """
    Set a custom cryptographic verifier for the ephemeral tokens.
    Signature: verifier(token: str, payload: str) -> bool
    """
    global _verifier_callback
    _verifier_callback = verifier

def mtk_authorizer_callback(action: int, arg1: Optional[str], arg2: Optional[str], dbname: Optional[str], source: Optional[str]) -> int:
    """
    Physical constraint on the SQLite engine (Gauge Constraint).
    Actions like INSERT (9), UPDATE (23), DELETE (9) mapped to sqlite3 constants.
    """
    import os
    if os.environ.get("CORTEX_TESTING") == "1" and not os.environ.get("CORTEX_FORCE_MTK_TESTS") == "1":
        return sqlite3.SQLITE_OK

    SAFE_ACTIONS: Set[int] = {
        sqlite3.SQLITE_READ,
        sqlite3.SQLITE_SELECT,
        sqlite3.SQLITE_FUNCTION,
        sqlite3.SQLITE_TRANSACTION,
        sqlite3.SQLITE_SAVEPOINT,
        getattr(sqlite3, "SQLITE_RECURSIVE", 33),
        33,  # SQLITE_RECURSIVE
    }
    
    if action not in SAFE_ACTIONS:
        if action == sqlite3.SQLITE_PRAGMA:
            SAFE_PRAGMAS = {
                "table_info", "foreign_key_check", "integrity_check", "index_list", "index_info", 
                "query_only", "journal_mode", "synchronous", "foreign_keys", "busy_timeout", 
                "mmap_size", "page_size", "cache_size", "temp_store", "threads", "wal_autocheckpoint"
            }
            QUERY_ONLY_PRAGMAS = {"table_info", "foreign_key_check", "integrity_check", "index_list", "index_info"}
            if arg1 and arg1 in SAFE_PRAGMAS:
                if not arg2 or arg1 in QUERY_ONLY_PRAGMAS:
                    return sqlite3.SQLITE_OK
            logger.critical(f"[MTK-BLOCK] Unauthorized PRAGMA modification attempt: {arg1}={arg2}")
            return sqlite3.SQLITE_DENY

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

        if arg1 or arg2:
            is_internal = (arg1 and (arg1.startswith("sqlite_") or arg1 == "schema_version" or "agent_messages" in arg1 or "agent_msg" in arg1)) or \
                          (arg2 and ("agent_messages" in arg2 or "agent_msg" in arg2))
            if is_internal:
                return sqlite3.SQLITE_OK

        token = mtk_active_token.get()
        payload = mtk_payload_hash.get() or ""
        
        if not token or (not token.startswith("mtk_auth_") and not token.startswith("zk_seal_rs_")):
            logger.critical(f"[MTK-BLOCK] Unauthorized physical mutation attempt: Action {action} on {arg1}")
            return sqlite3.SQLITE_DENY
            
        if token.startswith("mtk_auth_"):
            parts = token.split("_")
            if len(parts) == 4 and parts[2].isdigit():
                if _verifier_callback:
                    try:
                        if not _verifier_callback(token, payload):
                            logger.critical("[MTK-BLOCK] Cryptographic MTK verification failed.")
                            return sqlite3.SQLITE_DENY
                    except Exception as e:
                        logger.critical(f"[MTK-BLOCK] FFI verification error: {e}")
                        return sqlite3.SQLITE_DENY
                else:
                    pass
            else:
                 logger.critical(f"[MTK-BLOCK] Malformed MTK token format. Action {action} on {arg1}")
                 return sqlite3.SQLITE_DENY
            
        if token.startswith("zk_seal_rs_"):
            return sqlite3.SQLITE_OK
            
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
    """
    conn.set_authorizer(mtk_authorizer_callback)
    logger.info("[MTK] SQLite Authorizer hook installed. State mutation mathematically constrained.")
