import re

with open("cortex_extensions/gate/ouroboros.py") as f:
    content = f.read()

new_log_scaling = """
    def _log_scaling_event(self, content: str):
        \"\"\"Persists architectural scaling decisions.\"\"\"
        import asyncio
        import json
        import time
        from datetime import datetime, timezone
        from babylon60.database.core import connect_async_ctx
        from babylon60.engine.core.fact_store_core import insert_fact_record
        from babylon60.database.core import causal_write

        # Extract db path from the sync connection if possible, or fallback
        # In sqlite3, you can get the DB name from pragma database_list or assuming it's cortex.db
        
        async def _async_log():
            try:
                # Fetch DB path from sync connection
                cursor = self.conn.execute("PRAGMA database_list")
                db_path = None
                for row in cursor.fetchall():
                    if row[1] == 'main':
                        db_path = row[2]
                        break
                if not db_path or db_path == '':
                    import os
                    db_path = os.environ.get("CORTEX_DB_PATH", "cortex.db")

                async with connect_async_ctx(db_path) as aconn:
                    with causal_write(aconn):
                        await insert_fact_record(
                            conn=aconn,
                            tenant_id="default",
                            project="cortex",
                            content=content,
                            fact_type="decision",
                            tags=["ouroboros", "scaling", "pruning"],
                            confidence="C5",
                            ts=datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
                            source="ag:ouroboros",
                            meta=None,
                            tx_id=None
                        )
                        await aconn.commit()
            except Exception as e:
                import logging
                logging.getLogger("ouroboros").error("Failed to async log scaling event: %s", e)

        asyncio.create_task(_async_log())
"""

# Replace the old _log_scaling_event
content = re.sub(
    r'    def _log_scaling_event\(self, content: str\):.*?(?=\n\n    def |\Z)',
    new_log_scaling.strip('\n'),
    content,
    flags=re.DOTALL
)

with open("cortex_extensions/gate/ouroboros.py", "w") as f:
    f.write(content)

print("Patched ouroboros.py")
