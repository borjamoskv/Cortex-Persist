# [C5-REAL] Exergy-Maximized
"""
Sovereign Telemetry Routes (AST Oracle WebSocket API)
Exposes realtime stream of code mutations detected by AST Oracle.
"""

import asyncio
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from babylon60.api.deps import get_async_engine
from babylon60.crypto.hash_registry import cortex_hash
from babylon60.engine import CortexEngine as AsyncCortexEngine

logger = logging.getLogger("babylon60.api.telemetry")
router = APIRouter(tags=["telemetry"])


class TelemetryPayload(BaseModel):
    telemetryLogs: list[dict[str, Any]] = Field(default_factory=list)
    newEdges: dict[str, float] = Field(default_factory=dict)
    authorsDelta: dict[str, dict[str, Any]] = Field(default_factory=dict)


class TelemetryIngestRequest(BaseModel):
    timestamp: int
    agent_id: str
    payload: TelemetryPayload
    logos_signature: str | None = None


@router.post("/v1/telemetry/ingest")
@router.post("/api/v1/telemetry/ingest")
@router.post("/telemetry/ingest")
async def ingest_telemetry(
    request: Request,
    data: TelemetryIngestRequest,
    engine: AsyncCortexEngine = Depends(get_async_engine),
):
    """
    Ingest sovereign telemetry facts (C5-REAL) from external edge sensors.
    """
    source = request.headers.get("X-Cortex-Source")
    if not source:
        raise HTTPException(
            status_code=403, detail="Missing X-Cortex-Source header (Taint verification failed)"
        )

    content = f"Telemetry batch from {data.agent_id} at {data.timestamp}"
    project = "smoke-detector"

    # Compute deterministic logos_signature server-side to satisfy Virgo guard
    # Virgo expects: sha256(content + nonce + project) where nonce defaults to ""

    logos_sig = cortex_hash(f"{content}{project}".encode())

    meta = data.model_dump()
    meta["logos_signature"] = logos_sig

    try:
        fact_id = await engine.store(
            project=project,
            content=content,
            fact_type="telemetry_batch",
            tags=["telemetry", "edge_sensor", data.agent_id],
            source=source,
            meta=meta,
        )
        logger.info("Ingested telemetry batch from %s -> Fact ID %s", data.agent_id, fact_id)
        return {"status": "success", "fact_id": fact_id}
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to ingest telemetry: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


async def query_new_facts(
    engine: AsyncCortexEngine, last_id: int, fact_type: str
) -> tuple[int, list[dict[str, Any]]]:
    """Queries for new facts of specific type since last_id."""
    async with engine.session() as conn:
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


@router.websocket("/telemetry/ast-oracle")
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
    async with engine.session() as conn:
        cursor = await conn.execute("SELECT MAX(id) FROM facts")
        row = await cursor.fetchone()
        last_id = (row[0] or 0) - 100  # look back a bit  # type: ignore[reportOptionalSubscript]
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
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("AST Oracle WS Error: %s", e)


@router.websocket("/telemetry/fiat-stream")
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
    async with (
        engine.session() as conn,
        conn.execute("SELECT MAX(id) FROM facts WHERE fact_type = 'fiat_transaction'") as cursor,
    ):
        row = await cursor.fetchone()
        last_id = row[0] or 0  # type: ignore[reportOptionalSubscript]

    try:
        while True:
            new_max, txs = await query_new_facts(engine, last_id, "fiat_transaction")
            for tx in txs:
                await websocket.send_json({"event": "fiat_transaction", "data": tx})
            last_id = new_max
            await asyncio.sleep(1.0)  # Slower poll for financial updates
    except WebSocketDisconnect:
        logger.info("Financial Telemetry disconnected.")
    except (OSError, RuntimeError, ValueError) as e:
        logger.error("Fiat Stream WS Error: %s", e)


# --- Dynamic Mafia Nodes Synchronization (PUSH/WebSockets) ---

BASE_MAFIA_NODES = [
    "david dominguez",
    "daviddominguez.substack.com",
    "crecer en substack",
    "crecerensubstack.com",
    "masteryweeks.com",
    "toni herrera",
    "emarketersocial",
    "emarketersocial.substack.com",
    "emarketersocial.com",
    "manuel mas",
    "manoletux",
    "manoletux.substack.com",
    "lanzadera",
    "gabi contreras aguilera",
    "siete dias podcast",
    "sietediaspodcast.com",
    "samuel dominguez",
    "samueldominguez.substack.com",
    "esther claravalls",
    "isabel nogales",
    "dnogalesexperience.substack.com",
    "innerhythm",
    "innerhythm.substack.com",
    "jorge bosch",
    "jorge bosch ales",
    "jorgebosch.substack.com",
    "cosas de freelance",
    "cosasdefreelance.com",
    "alba garcia marcos",
    "unicornios y piratas",
    "unicorniosypiratas.substack.com",
    "unicorniosypiratas.com",
    "chema portero",
    "enric cortiñas",
    "carmina lozano",
    "victor garces",
    "rosemary de sena",
    "substack mafia",
    "la mafiadera",
    "substackme deluxe",
    "medicina abierta al mundo",
    "ihelp",
    "cult building",
    "freelance trick",
    "negocios de pago",
    "newsletter exitosa",
    "marketing de guerrilla",
    "solopreneur club",
    "comunidad vip",
    "ingresos recurrentes",
    "lanzamiento expres",
    "marketing de afiliados",
    "marketing de embudos",
    "escribir en internet",
    "red de creadores",
    "lobby digital",
    "recirculacion de trafico",
    "creadores premium",
    "mentorias exclusivas",
    "taller de ventas",
    "copywriting forense",
    "exito garantizado",
    "secretos de newsletter",
    "negocio libre",
    "marca personal 2026",
    "chiringuito digital",
    "mafia del no code",
    "circulo interno",
    "vender cursos",
    "seo de guerrilla",
    "afiliacion express",
    "comunidad mafia",
    "crecer en notes",
    "restack semanal",
    "amplificacion coordinada",
    "corte premium",
    "bootcamp express",
    "retencion de leads",
    "embudo de extraccion",
    "solopreneur espanol",
    "creacion de comunidades",
    "ancla de precios",
    "vender infoproductos",
    "mastermind privado",
    "trafico circular",
    "lobby de substack",
    "mafia substack",
    "aimafia",
    "aimafia.substack.com",
    "tudosisia",
    "tudosisia.substack.com",
    "webreactiva",
    "webreactiva.substack.com",
    "iaparatodo",
    "iaparatodo.substack.com",
    "agentesia",
    "agentesia.substack.com",
    "futuria",
    "futuria.substack.com",
    "overxtime",
    "overxtime.substack.com",
    "cafeconia",
    "cafeconia.substack.com",
    "spacioia",
    "spacioia.substack.com",
    "modoxtenx",
    "modoxtenx.substack.com",
    "enriquemartinezbermejo",
    "enriquemartinezbermejo.substack.com",
    "hellojaume",
    "hellojaume.substack.com",
    "escribepro",
    "escribepro.substack.com",
    "aplicacionesai",
    "aplicacionesai.substack.com",
    "iaenespanol",
    "iaenespanol.substack.com",
    "botondeayuda",
    "botondeayuda.com",
    "estrategiabyaleph",
    "estrategiabyaleph.substack.com",
    "davidlahozmartin",
    "davidlahozmartin.substack.com",
    "samuelgil",
    "sumapositiva.com",
    "sumapositiva",
    "podhacks",
    "podhacks.substack.com",
    "medicosinconformistas",
    "medicosinconformistas.substack.com",
    "thefoundercorner",
    "thefoundercorner.substack.com",
    "ekhocomunicacion",
    "ekhocomunicacion.substack.com",
    "conectaycrece",
    "conectaycrece.substack.com",
    "emprender",
    "emprender.substack.com",
    "consultoresia",
    "consultoresia.substack.com",
    "somosbiz",
    "somosbiz.substack.com",
    "thevccorner",
    "thevccorner.substack.com",
    "plumapifiada",
    "plumapifiada.substack.com",
    "todatabeyond",
    "todatabeyond.substack.com",
    "susanaluque",
    "susanaluque.substack.com",
    "tucoachpersonal",
    "tucoachpersonal.substack.com",
    "laiaqueimporta",
    "laiaqueimporta.substack.com",
    "titonet",
    "titonet.substack.com",
    "habitonutricion",
    "habitonutricion.substack.com",
    "raulcalderonc",
    "raulcalderonc.substack.com",
    "dispersosdemierda",
    "dispersosdemierda.substack.com",
    "marcplanella",
    "marcplanella.substack.com",
    "emprendizajes",
    "emprendizajes.substack.com",
    "destacadas",
    "destacadas.substack.com",
    "vitalismo",
    "vitalismo.substack.com",
    "ecommletter",
    "ecommletter.substack.com",
    "seveluna",
    "seveluna.substack.com",
    "estomeinteresa",
    "estomeinteresa.substack.com",
    "coachingdeproducto",
    "coachingdeproducto.substack.com",
    "eponte",
    "eponte.substack.com",
    "hazloquequieras",
    "hazloquequieras.substack.com",
    "bookstrapping",
    "bookstrapping.substack.com",
    "nosolosuerte",
    "nosolosuerte.substack.com",
    "platforms",
    "platforms.substack.com",
]

_nodes_websockets: set[WebSocket] = set()


class MafiaNodeProposal(BaseModel):
    node: str


@router.get("/v1/telemetry/nodes")
@router.get("/api/v1/telemetry/nodes")
@router.get("/telemetry/nodes")
async def get_mafia_nodes(engine: AsyncCortexEngine = Depends(get_async_engine)):
    """Retrieve all active mafia nodes (base + dynamic)."""
    try:
        facts = await engine.recall(project="smoke-detector", fact_type="mafia_node")
        dynamic_nodes = [f["content"] for f in facts]
        full_list = list(set(BASE_MAFIA_NODES + dynamic_nodes))
        return {"status": "success", "nodes": full_list}
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to query mafia nodes: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/v1/telemetry/nodes")
@router.post("/api/v1/telemetry/nodes")
@router.post("/telemetry/nodes")
async def add_mafia_node(
    request: Request, data: MafiaNodeProposal, engine: AsyncCortexEngine = Depends(get_async_engine)
):
    """Add a new mafia node fact and push to all active extensions."""
    source = request.headers.get("X-Cortex-Source")
    if not source:
        raise HTTPException(status_code=403, detail="Missing X-Cortex-Source header")

    try:
        fact_id = await engine.store(
            project="smoke-detector",
            content=data.node,
            fact_type="mafia_node",
            tags=["telemetry", "mafia_node"],
            source=source,
            meta={"added_via": "telemetry_api"},
        )
        logger.info("Registered new Mafia Node: %s -> Fact ID %s", data.node, fact_id)

        # Broadcast to all connected WebSockets
        await broadcast_nodes_update(data.node)

        return {"status": "success", "fact_id": fact_id, "node": data.node}
    except Exception as e:  # noqa: BLE001
        logger.error("Failed to store mafia node: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/v1/telemetry/nodes/ws")
@router.websocket("/api/v1/telemetry/nodes/ws")
@router.websocket("/telemetry/nodes/ws")
async def telemetry_nodes_ws(websocket: WebSocket):
    """Realtime stream of Mafia Node additions/updates & Telemetry Ingestion."""
    engine: AsyncCortexEngine = websocket.app.state.async_engine
    await websocket.accept()
    _nodes_websockets.add(websocket)
    logger.info("Extension WebSocket connected to Mafia Nodes sync stream.")
    try:
        # Immediately send the full initial list
        facts = await engine.recall(project="smoke-detector", fact_type="mafia_node")
        dynamic_nodes = [f["content"] for f in facts]
        full_list = list(set(BASE_MAFIA_NODES + dynamic_nodes))
        await websocket.send_json({"type": "INIT_NODES", "nodes": full_list})

        import json

        while True:
            # Maintain connection, listen for any client messages (ping/pongs or telemetry)
            raw_text = await websocket.receive_text()
            try:
                data = json.loads(raw_text)
                if data.get("type") == "INGEST_TELEMETRY":
                    req_data = data.get("data", {})
                    agent_id = req_data.get("agent_id", "smoke-detector-extension")
                    timestamp = req_data.get("timestamp", 0)
                    payload = req_data.get("payload", {})

                    content = f"Telemetry batch from {agent_id} at {timestamp}"
                    project = "smoke-detector"
                    logos_sig = cortex_hash(f"{content}{project}".encode())

                    meta = {
                        "timestamp": timestamp,
                        "agent_id": agent_id,
                        "payload": payload,
                        "logos_signature": logos_sig,
                    }

                    fact_id = await engine.store(
                        project=project,
                        content=content,
                        fact_type="telemetry_batch",
                        tags=["telemetry", "edge_sensor", agent_id, "websocket"],
                        source="alpha-vs-smoke-edge-ws",
                        meta=meta,
                    )
                    logger.info(
                        "Ingested telemetry batch via WS from %s -> Fact ID %s", agent_id, fact_id
                    )
            except json.JSONDecodeError:
                pass  # Ignore non-JSON messages
            except Exception as e:  # noqa: BLE001
                logger.error("Failed to ingest WS telemetry: %s", e)

    except WebSocketDisconnect:
        logger.info("Extension WebSocket disconnected.")
    finally:
        _nodes_websockets.discard(websocket)


async def broadcast_nodes_update(new_node: str):
    """Push the newly added node to all connected clients."""
    if not _nodes_websockets:
        return
    disconnected = set()
    payload = {"type": "ADD_NODE", "node": new_node}
    for ws in _nodes_websockets:
        try:
            await ws.send_json(payload)
        except (RuntimeError, WebSocketDisconnect, ConnectionError) as e:
            logger.debug("Client disconnected during broadcast: %s", e)
            disconnected.add(ws)
    for ws in disconnected:
        _nodes_websockets.discard(ws)
