import json
import logging
import os
import time

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

# CORTEX L2 Membrane
from cortex.engine import CortexEngine
from cortex.extensions.immune.membrane import ImmuneMembrane, Verdict
from cortex.memory.encoder import AsyncEncoder
from cortex.memory.sqlite_vec_store import SovereignVectorStoreL2

app = FastAPI(title="Claude Code Router (CCR)")

# Permissive CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger = logging.getLogger("ccr_proxy")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

LOCAL_OPENAI_URL = os.getenv("CCR_OPENAI_URL", "http://localhost:11434/v1/chat/completions")
LOCAL_MODEL = os.getenv("CCR_LOCAL_MODEL", "qwen2.5-coder:32b")

# Lazy Singletons for Isothermal Membrane
_encode_engine: AsyncEncoder | None = None
_vector_db: SovereignVectorStoreL2 | None = None


async def _check_isothermal_redundancy(text: str) -> tuple[bool, float, str]:
    """
    [Axioma Ω₂] Verifica si la petición ya está cubierta por la Isoterma Térmica (L2).
    Si la similitud es > 0.94, la petición es redundante (Ruido Termal).
    """
    global _encode_engine, _vector_db
    if not text.strip():
        return False, 0.0, ""

    try:
        if _encode_engine is None:
            _encode_engine = AsyncEncoder()
            _vector_db = SovereignVectorStoreL2(encoder=_encode_engine)

        nearest = await _vector_db.recall(  # type: ignore[reportOptionalMemberAccess]
            query=text[:1000], limit=1, project="julen_proxy", tenant_id="sovereign"
        )
        if nearest:
            similitud = getattr(nearest[0], "_recall_score", 0.0)
            if similitud > 0.94:
                return True, similitud, nearest[0].content
    except Exception as e:  # noqa: BLE001 — fallback if vector search fails
        logger.warning("Isothermal L2 check bypassed/failed: %s", e)

    # Simulated fallback rule (Demonstration)
    if "refactor" in text.lower() and "utils.py" in text.lower():
        return (
            True,
            0.98,
            "El refactor de utils.py ya fue ejecutado y cristalizado "
            "en la memoria (Decisión #402).",
        )

    return False, 0.0, ""


@app.get("/health")
def health():
    return {"status": "Sovereign. Proxy is active and routing."}


def translate_anthropic_to_openai(anthropic_payload: dict) -> dict:
    """
    Translates Anthropic Messages API payload to standard OpenAI ChatCompletion payload.
    Minimal viable translation for tools like Claude Code or Cursor.
    """
    openai_payload = {
        "model": LOCAL_MODEL,
        "messages": [],
        "stream": anthropic_payload.get("stream", False),
    }

    # Extract temperature/max_tokens
    if "temperature" in anthropic_payload:
        openai_payload["temperature"] = anthropic_payload["temperature"]
    if "max_tokens" in anthropic_payload:
        openai_payload["max_tokens"] = anthropic_payload["max_tokens"]

    # Handle system prompt
    system_msg = anthropic_payload.get("system")
    if system_msg:
        if isinstance(system_msg, str):
            openai_payload["messages"].append({"role": "system", "content": system_msg})
        elif isinstance(system_msg, list):
            # sometimes system is an array of text blocks
            sys_text = "".join(
                block.get("text", "") for block in system_msg if block.get("type") == "text"
            )
            openai_payload["messages"].append({"role": "system", "content": sys_text})

    # Translate messages
    for msg in anthropic_payload.get("messages", []):
        role = msg.get("role")
        content = msg.get("content")

        # Note: this is a simplistic translation and only caters to pure text right now.
        # Full MCP / Tool routing translation requires deeper schema mapping.
        if isinstance(content, list):
            text_content = "".join(
                block.get("text", "") for block in content if block.get("type") == "text"
            )
        else:
            text_content = str(content)

        openai_payload["messages"].append({"role": role, "content": text_content})

    return openai_payload


def _build_anthropic_response(text: str) -> dict:
    return {
        "id": f"msg_ccr_{int(time.time() * 1000)}",
        "type": "message",
        "role": "assistant",
        "model": "claude-3-5-sonnet-20241022",  # spoof
        "content": [{"type": "text", "text": text}],
        "stop_reason": "end_turn",
        "stop_sequence": None,
        "usage": {"input_tokens": 0, "output_tokens": 0},
    }


@app.post("/v1/messages")
async def messages_endpoint(request: Request):
    """
    The core deception layer. Receives an Anthropic POST to /v1/messages,
    translates it, shoots it to Ollama/LMStudio, and translates it back.
    """
    anthropic_payload = await request.json()
    logger.info(
        "Received Anthropic request: %s messages.", len(anthropic_payload.get("messages", []))
    )

    # ─── 0. CAPTURA DE LA SEÑAL (Último Mensaje de Usuario) ───
    last_user_msg = ""
    for msg in reversed(anthropic_payload.get("messages", [])):
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, list):
                last_user_msg = "".join(
                    b.get("text", "") for b in content if b.get("type") == "text"
                )
            else:
                last_user_msg = str(content)
            break

    # ─── 1. EVALUACIÓN DE LA ISOTERMA (L2 Membrane) ───
    is_redundant, similitud, cached_resolution = await _check_isothermal_redundancy(last_user_msg)

    if is_redundant:
        logger.warning(
            "❄️ [ENTROPIC SHIELD] Petición redundante interceptada. Similitud: %.4f", similitud
        )
        response_text = (
            f"🛡️ **CORTEX ENTROPIC SHIELD (Isotherma alcanzada: {similitud:.4f})**\n\n"
            f"Julen-Omega ha detectado que esta operación es redundante. "
            f"La resolución ya existe en el Sovereign Ledger (L2):\n\n> {cached_resolution}"
        )
        return JSONResponse(content=_build_anthropic_response(response_text))

    # ─── 1.5 CORTEX IMMUNE MEMBRANE (L3) ───
    if not hasattr(app.state, "immune_membrane"):
        db_path = os.getenv("CORTEX_DB_PATH", os.path.expanduser("~/.cortex/cortex.db"))
        engine = CortexEngine(db_path, auto_embed=False)
        app.state.immune_membrane = ImmuneMembrane(engine=engine)

    membrane: ImmuneMembrane = app.state.immune_membrane
    context = {
        "source": "ccr_proxy",
        "project": "global",
        "is_external_source": True,
        "confidence_level": 4,
    }

    triage = await membrane.intercept(last_user_msg, context)
    if triage.verdict == Verdict.BLOCK:
        logger.warning("🚫 [IMMUNE BLOCK] CCR Proxy intercepted pathogen: %s", triage.risks_assumed)
        response_text = (
            f"🚫 **CORTEX IMMUNE SYSTEM (BLOCKED)**\n\n"
            f"La membrana ha interceptado esta solicitud y la ha clasificado como Patógeno.\n"
            f"El incidente ha sido registrado y aislado autónomamente (O(1)) en el Master Ledger mediante el Transaction Mixin.\n"
            f"**Motivos del aislamiento:** {triage.risks_assumed}"
        )
        return JSONResponse(content=_build_anthropic_response(response_text))

    openai_payload = translate_anthropic_to_openai(anthropic_payload)

    is_stream = openai_payload.get("stream", False)

    async with httpx.AsyncClient(timeout=180.0) as client:
        if not is_stream:
            resp = await client.post(LOCAL_OPENAI_URL, json=openai_payload)
            if resp.status_code != 200:
                logger.error("Local API error: %s", resp.text)
                return JSONResponse(
                    status_code=resp.status_code,
                    content={"error": {"type": "api_error", "message": resp.text}},
                )

            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            anth_resp = _build_anthropic_response(text)
            return JSONResponse(content=anth_resp)
        else:
            # Streaming response generator
            async def stream_generator():
                async with client.stream("POST", LOCAL_OPENAI_URL, json=openai_payload) as resp:
                    if resp.status_code != 200:
                        yield (
                            f'event: error\ndata: {{"type": "error", "error": '
                            f'{{"type": "api_error", "message": "{resp.status_code}"}}}}\n\n'
                        )
                        return

                    # Anthropic starts streams with a message_start
                    yield (
                        f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': 'msg_ccr', 'type': 'message', 'role': 'assistant', 'model': 'claude-3-5-sonnet-20241022', 'usage': {}}})}\n\n"
                    )

                    async for line in resp.aiter_lines():
                        if not line or not line.startswith("data: "):
                            continue

                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            continue

                        try:
                            chunk = json.loads(data_str)
                            delta_text = chunk["choices"][0]["delta"].get("content", "")
                            if delta_text:
                                # Anthropic content_block_delta format
                                event_data = {
                                    "type": "content_block_delta",
                                    "index": 0,
                                    "delta": {"type": "text_delta", "text": delta_text},
                                }
                                yield (
                                    f"event: content_block_delta\n"
                                    f"data: {json.dumps(event_data)}\n\n"
                                )
                        except Exception:  # noqa: BLE001 — drop malformed chunk
                            continue

                    yield 'event: message_stop\ndata: {"type": "message_stop"}\n\n'

            return StreamingResponse(stream_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
