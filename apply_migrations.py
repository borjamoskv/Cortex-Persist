import asyncio
import logging
import os
import sys

import aiosqlite

# Set up cortex module path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from cortex.migrations.core import run_migrations_async

logging.basicConfig(level=logging.INFO)


async def main():
    db_path = os.path.expanduser("~/.cortex/cortex.db")
    async with aiosqlite.connect(db_path) as conn:
        print(f"Applying migrations to {db_path}...")
        applied = await run_migrations_async(conn)
        print(f"Successfully applied {applied} migrations.")


if __name__ == "__main__":
    asyncio.run(main())
