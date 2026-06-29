# [C5-REAL] Exergy-Maximized
"""
cat_id: -audit
cat_type: script
version: 1.0.0
reality_level: C5-REAL
owner: borjamoskv
exergy_tier: P2
"""

import asyncio
import os
import sys
from pathlib import Path

from babylon60.database.core import connect_async

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
        async with connect_async(db_path) as db:
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
