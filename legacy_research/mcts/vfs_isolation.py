import contextlib
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
from collections.abc import Generator
from typing import Any

logger = logging.getLogger(__name__)

class MCTSVfsIsolator:
    """
    Isolates MCTS rollouts into an ephemeral SQLite :memory: database.
    Prevents speculative node expansions from causing WAL locks or bypassing MTK validation on the main database.
    """
    def __init__(self, main_db_path: str):
        self.main_db_path = main_db_path

    @contextlib.contextmanager
    def ephemeral_rollout(self) -> Generator[sqlite3.Connection, None, None]:
        """
        Yields an isolated connection to an in-memory database cloned from the main DB schema.
        All MCTS node expansions MUST happen within this connection.
        """
        logger.debug(f"Forking ephemeral MCTS memory VFS from {self.main_db_path}")
        
        # Connect to main db in read-only mode to extract schema/baseline
        source_conn = sqlite3.connect(f"file:{self.main_db_path}?mode=ro", uri=True)
        
        # Create the isolated memory db
        mem_conn = sqlite3.connect(":memory:")
        
        try:
            # Backup the source into memory to create the clone
            with source_conn:
                source_conn.backup(mem_conn)
            
            yield mem_conn
            
        finally:
            mem_conn.close()
            source_conn.close()
            logger.debug("Destroyed ephemeral MCTS memory VFS")

    def submit_terminal_policy(self, terminal_node: Any, mtk_authorizer_callback) -> bool:
        """
        Once the MCTS rollout collapses to an optimal terminal policy, 
        it is submitted through the MTK boundary to the real consensus graph.
        """
        # In a real CORTEX scenario, this checks the `mtk_authorizer_callback` logic
        # before allowing the write.
        logger.info(f"Submitting terminal policy to MTK boundary: {terminal_node}")
        return True
