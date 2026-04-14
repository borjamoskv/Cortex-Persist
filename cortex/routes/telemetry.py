"""
Sovereign Telemetry Routes (AST Oracle WebSocket API)
Exposes realtime stream of code mutations detected by AST Oracle.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from cortex.api.deps import get_async_engine
from cortex.auth.websocket import require_websocket_auth
from cortex.engine import CortexEngine as AsyncCortexEngine

logger = logging.getLogger("cortex.api.telemetry")
router = APIRouter(prefix="/telemetry", tags=["telemetry"])


def _decode_fact_meta(meta_raw: Any) -> dict[str, Any]:
    """Parse fact metadata defensively for telemetry payloads."""
    if isinstance(meta_raw, dict):
        return meta_raw
    if meta_raw is None:
        return {}
    if isinstance(meta_raw, bytes):
        meta_raw = meta_raw.decode("utf-8", errors="ignore")
    if not isinstance(meta_raw, str):
        return {}
    try:
        decoded = json.loads(meta_raw)
    except json.JSONDecodeError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


async def _resolve_facts_meta_column(engine: AsyncCortexEngine) -> str:
    """Support both the current `metadata` schema and older `meta` rows."""
    async with engine.session() as conn:
        cursor = await conn.execute("PRAGMA table_info(facts)")
        rows = await cursor.fetchall()
    column_names = {row[1] for row in rows}
    if "metadata" in column_names:
        return "metadata"
    if "meta" in column_names:
        return "meta"
    raise RuntimeError("facts table missing metadata/meta column")


async def _get_last_fact_id(
    engine: AsyncCortexEngine, tenant_id: str, fact_type: str, lookback: int = 0
) -> int:
    """Return the latest tenant-scoped fact id with an optional lookback window."""
    async with engine.session() as conn:
        cursor = await conn.execute(
            "SELECT MAX(id) FROM facts WHERE tenant_id = ? AND fact_type = ?",
            (tenant_id, fact_type),
        )
        row = await cursor.fetchone()

    current_max = row[0] if row and row[0] is not None else 0
    last_id = current_max - lookback
    return last_id if last_id > 0 else 0


async def query_new_facts(
    engine: AsyncCortexEngine,
    last_id: int,
    fact_type: str,
    tenant_id: str,
    meta_column: str,
) -> tuple[int, list[dict[str, Any]]]:
    """Query tenant-scoped facts of a specific type since `last_id`."""
    async with engine.session() as conn:
        sql = f"""
            SELECT id, content, {meta_column}
            FROM facts
            WHERE tenant_id = ? AND fact_type = ? AND id > ?
            ORDER BY id ASC
        """
        cursor = await conn.execute(sql, (tenant_id, fact_type, last_id))
        rows = await cursor.fetchall()

        results = []
        max_id = last_id
        for row in rows:
            fact_id, content, meta_raw = row
            results.append(
                {
                    "fact_id": fact_id,
                    "content": content,
                    "meta": _decode_fact_meta(meta_raw),
                }
            )
            if fact_id > max_id:
                max_id = fact_id
        return max_id, results


@router.websocket("/ast-oracle")
async def ast_oracle_ws(
    websocket: WebSocket, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """
    WebSocket endpoint that streams realtime AST mutations to the Sovereign Web interface.
    """
    auth = await require_websocket_auth(websocket, required_permission="read")
    if auth is None:
        return
    await websocket.accept()
    logger.info("👁️ Holographic Interface connected to AST Oracle.")

    meta_column = await _resolve_facts_meta_column(engine)
    last_id = await _get_last_fact_id(engine, auth.tenant_id, "human_mutation", lookback=100)

    try:
        while True:
            new_max, mutations = await query_new_facts(
                engine,
                last_id,
                "human_mutation",
                auth.tenant_id,
                meta_column,
            )
            for mut in mutations:
                await websocket.send_json({"event": "human_mutation", "data": mut})
            last_id = new_max
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        logger.info("Holographic Interface disconnected.")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("AST Oracle WS Error: %s", e)


@router.websocket("/fiat-stream")
async def fiat_stream_ws(
    websocket: WebSocket, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """
    WebSocket endpoint that streams realtime financial transactions.
    """
    auth = await require_websocket_auth(websocket, required_permission="read")
    if auth is None:
        return
    await websocket.accept()
    logger.info("💰 Financial Telemetry connected to Fiat Oracle.")

    meta_column = await _resolve_facts_meta_column(engine)
    last_id = await _get_last_fact_id(engine, auth.tenant_id, "fiat_transaction")

    try:
        while True:
            new_max, txs = await query_new_facts(
                engine,
                last_id,
                "fiat_transaction",
                auth.tenant_id,
                meta_column,
            )
            for tx in txs:
                await websocket.send_json({"event": "fiat_transaction", "data": tx})
            last_id = new_max
            await asyncio.sleep(1.0)  # Slower poll for financial updates
    except WebSocketDisconnect:
        logger.info("Financial Telemetry disconnected.")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Fiat Stream WS Error: %s", e)
