import asyncio
import os
from pathlib import Path
import sqlite3

import logging

from cortex.memory.ledger import EventLedgerL3
from cortex.memory.models import MemoryEvent
from cortex.memory.auto_management import LedgerAutoManagementDaemon

logging.basicConfig(level=logging.INFO)


async def main():
    db_path = Path("scratch/test_ledger.db")
    if db_path.exists():
        db_path.unlink()
    archive_path = Path("scratch/test_archive.db")
    if archive_path.exists():
        archive_path.unlink()

    import aiosqlite

    conn = await aiosqlite.connect(str(db_path))
    l3 = EventLedgerL3(conn)
    await l3.ensure_table()

    # Init daemon with very small threshold for testing (e.g., 0.1 MB)
    daemon = LedgerAutoManagementDaemon(
        ledger=l3,
        tenant_id="default",
        max_db_size_mb=0.1,  # 100 KB
        retain_limit=10,  # Retain only 10 events
        archive_path=str(archive_path),
        check_interval_seconds=1.0,  # Check every second
        db_path=str(db_path),
    )
    daemon.start()

    try:
        print("Inserting events to grow DB...")
        for i in range(100):
            event = MemoryEvent(
                role="assistant",
                session_id="test_session",
                content=f"Large content payload to increase size... {'x' * 5000}",
                token_count=100,
                metadata={"index": i},
            )
            await l3.append_event(event)

        # Check size before wait
        size_before = db_path.stat().st_size
        print(f"Size before compaction: {size_before / 1024:.2f} KB")

        print("Waiting for daemon to trigger compaction...")
        await asyncio.sleep(2.5)  # Wait for 2 checks

        size_after = db_path.stat().st_size
        print(f"Size after compaction: {size_after / 1024:.2f} KB")

        if archive_path.exists():
            archive_size = archive_path.stat().st_size
            print(f"Archive size: {archive_size / 1024:.2f} KB")
        else:
            print("Archive not found!")

    finally:
        daemon.stop()


if __name__ == "__main__":
    asyncio.run(main())
