import os
import time
import logging
from fastapio import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import asyncio
import json

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
        "Received Anthropic request: %s messages.", len(anthropic_payload.get('messages', []))
    )
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
                        yield f'event: error\ndata: {{"type": "error", "error": {{"type": "api_error", "message": "{resp.status_code}"}}}}\n\n'
                        return

                    # Anthropic starts streams with a message_start
                    yield f"event: message_start\ndata: {json.dumps({'type': 'message_start', 'message': {'id': 'msg_ccr', 'type': 'message', 'role': 'assistant', 'model': 'claude-3-5-sonnet-20241022', 'usage': {}}})}\n\n"

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
                                yield f"event: content_block_delta\ndata: {json.dumps(event_data)}\n\n"
                        except Exception as e:
                            continue

                    yield 'event: message_stop\ndata: {"type": "message_stop"}\n\n'

            return StreamingResponse(stream_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
