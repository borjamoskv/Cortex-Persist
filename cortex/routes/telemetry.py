"""
Sovereign Telemetry Routes (AST Oracle WebSocket API)
Exposes realtime stream of code mutations detected by AST Oracle.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from cortex.api_deps import get_async_engine
from cortex.engine_async import AsyncCortexEngine

logger = logging.getLogger("cortex.api.telemetry")
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


async def query_new_facts(
    engine: AsyncCortexEngine, last_id: int, fact_type: str
) -> tuple[int, list[dict[str, Any]]]:
    """Queries for new facts of specific type since last_id."""
    conn = await engine.get_conn()
    try:
        sql = """
            SELECT id, content, meta 
            FROM facts 
            WHERE fact_type = ? AND id > ? 
            ORDER BY id ASC
        """
        cursor = await conn.execute(sql, (fact_type, last_id))
        rows = await cursor.fetchall()

        results = []
        max_id = last_id
        for row in rows:
            fact_id, content, meta_raw = row
            import json

            meta = json.loads(meta_raw) if meta_raw else {}
            results.append({"fact_id": fact_id, "content": content, "meta": meta})
            if fact_id > max_id:
                max_id = fact_id
        return max_id, results
    finally:
        pass


@router.websocket("/ast-oracle")
async def ast_oracle_ws(
    websocket: WebSocket, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """
    WebSocket endpoint that streams realtime AST mutations to the Sovereign Web interface.
    """
    await websocket.accept()
    logger.info("👁️ Holographic Interface connected to AST Oracle.")

    # We want to get the last known ID first so we only send *new* mutations
    # But for a slicker demo upon connection, we can fetch the last 10
    conn = await engine.get_conn()
    cursor = await conn.execute("SELECT MAX(id) FROM facts")
    row = await cursor.fetchone()
    last_id = (row[0] or 0) - 100  # look back a bit
    if last_id < 0:
        last_id = 0

    try:
        while True:
            new_max, mutations = await query_new_facts(engine, last_id, "human_mutation")
            for mut in mutations:
                await websocket.send_json({"event": "human_mutation", "data": mut})
            last_id = new_max
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.info("Holographic Interface disconnected.")
    except Exception as e:
        logger.error("AST Oracle WS Error: %s", e)


@router.websocket("/fiat-stream")
async def fiat_stream_ws(
    websocket: WebSocket, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """
    WebSocket endpoint that streams realtime financial transactions.
    """
    await websocket.accept()
    logger.info("💰 Financial Telemetry connected to Fiat Oracle.")

    # Fetch last known ID
    async with engine.session() as conn:
        async with conn.execute(
            "SELECT MAX(id) FROM facts WHERE fact_type = 'fiat_transaction'"
        ) as cursor:
            row = await cursor.fetchone()
            last_id = row[0] or 0

    try:
        while True:
            new_max, txs = await query_new_facts(engine, last_id, "fiat_transaction")
            for tx in txs:
                await websocket.send_json({"event": "fiat_transaction", "data": tx})
            last_id = new_max
            await asyncio.sleep(1.0)  # Slower poll for financial updates
    except WebSocketDisconnect:
        logger.info("Financial Telemetry disconnected.")
    except Exception as e:
        logger.error("Fiat Stream WS Error: %s", e)
