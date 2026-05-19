import os
import sys
import json
import logging
import asyncio
from mcp.server.fastmcp import FastMCP
import sqlite3

# Maintain CORTEX-V3.0 Alignment
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from persistence import LedgerManager, VSAMemory

# Sovereign MCP Node v3.0
mcp = FastMCP("CORTEX-SOVEREIGN-MCP")
vsa = VSAMemory()
ledger = LedgerManager()

DB_PATH = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/cortex_memory_vsa.db"


@mcp.tool()
async def cortex_ledger_append(action: str, vector_id: str, yield_amount: float) -> str:
    """
    Cryptographic write to the CORTEX-Persist ledger. Secures Exergy via SHA-256 Merkle chain.
    """
    block_hash = ledger.append(action, vector_id, yield_amount)
    vsa.record(key=f"mcp_ledger:{vector_id}", value=action)
    return f"BLOCK_COMMITTED: {block_hash[:16]}... | Yield: +{yield_amount}"


@mcp.tool()
async def cortex_vsa_record(key: str, value: str) -> str:
    """Records a semantic trace in the VSA-SDM tensor and SQLite DB."""
    vsa.record(key, value)
    return f"VSA_RECORDED: {key}"


@mcp.tool()
async def get_cortex_status() -> dict:
    """Returns the current state of the Sovereign node from SQLite."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM cortex_knowledge")
    ki_count = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM ledger_records")
    ledger_count = c.fetchone()[0]
    conn.close()

    return {
        "status": "SOVEREIGN_V3_ACTIVE",
        "ki_count": ki_count,
        "ledger_count": ledger_count,
        "total_yield": ledger.get_total_yield(),
        "mode": "C5-REAL",
    }


if __name__ == "__main__":
    vsa.start_glia()
    mcp.run()
