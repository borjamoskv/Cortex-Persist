import asyncio
import aiosqlite
from pathlib import Path

async def main():
    db_path = Path("scratch/test_ledger.db")
    conn = await aiosqlite.connect(str(db_path))
    
    # Try VACUUM with execute
    await conn.execute("VACUUM")
    await conn.commit()
    print("Execute VACUUM done, size:", db_path.stat().st_size)
    
    # Try VACUUM with executescript
    await conn.executescript("VACUUM;")
    await conn.commit()
    print("Executescript VACUUM done, size:", db_path.stat().st_size)

asyncio.run(main())
