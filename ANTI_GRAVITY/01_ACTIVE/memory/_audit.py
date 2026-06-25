import asyncio
import os
import sys
from pathlib import Path

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

# Add root to sys.path to ensure cortex can be imported
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

def log_to_ledger(action: str, resource: str, status: str):
    """
    Synchronous wrapper to log an action to the CORTEX SQLite Audit Ledger.
    """
    try:
        from cortex.audit.ledger import EnterpriseAuditLedger
    except ImportError:
        print("⚠️ Warning: Could not import EnterpriseAuditLedger. Skipping audit log.")
        return

    db_path = os.environ.get("CORTEX_DB_PATH", str(ROOT / "cortex_ledger.db"))
    
    async def _log():
        async with aiosqlite.connect(db_path) as db:
            ledger = EnterpriseAuditLedger(db)
            await ledger.ensure_table()
            await ledger.log_action(
                tenant_id="SYSTEM",
                actor_role="SCRIPT",
                actor_id=os.environ.get("USER", "system"),
                action=action,
                resource=resource,
                status=status
            )
            
    try:
        # Check if there is an existing event loop
        try:
            loop = asyncio.get_running_loop()
            # If we're already in an event loop, we can't use asyncio.run
            # We'll schedule it as a task (fire and forget)
            loop.create_task(_log())
        except RuntimeError:
            # No running event loop
            asyncio.run(_log())
    except Exception as e:
        print(f"⚠️ Warning: Could not write to audit ledger: {e}")
