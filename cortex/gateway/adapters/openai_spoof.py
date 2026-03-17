"""CORTEX Gateway — OpenAI Spoofing Adapter (API Proxy).

Intercepts OpenAI-compatible requests from any tool/IDE and routes them
through CORTEX's SovereignLLM cascade.
Supports API Key spoofing and Telemetry stripping.
"""

from __future__ import annotations
from typing import Optional

import logging
import time

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from cortex.extensions.llm.sovereign import SovereignLLM
from cortex.gateway.spoof import SpoofManager

logger = logging.getLogger("cortex.gateway.openai")

router = APIRouter(prefix="/v1", tags=["gateway:openai"])

# Singleton managers
_spoof_manager = SpoofManager()

# --- OpenAI API Schemas ---


class OpenAIMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None


class OpenAICompletionRequest(BaseModel):
    model: str
    messages: list[OpenAIMessage]
    temperature: Optional[float] = 0.3
    max_tokens: Optional[int] = 4096
    stream: Optional[bool] = False


# --- Routes ---


@router.post("/chat/completions")
async def openai_chat_completions(
    request: Request,
    body: OpenAICompletionRequest,
    authorization: Optional[str] = Header(None),
):
    """Spoof OpenAI endpoint by routing to CORTEX internal LLM."""

    # 1. Telemetry Strip & Logging
    _spoof_manager.log_telemetry(dict(request.headers), body.model_dump())

    # 2. Translate to Sovereign Prompt
    prompt = _spoof_manager.to_cortex_prompt(body.model_dump())

    start_time = time.time()

    if body.stream:
        # Falling back to a simpler stream for now as SovereignLLM.stream is not fully implemented
        # in the same way as generate. But for high reliability, we prefer generate.
        # Actually, let's implement streaming in SovereignLLM?
        # For now, let's use the standard Manager for streaming and Sovereign for non-streaming.
        from cortex.extensions.llm.manager import LLMManager

        mgr = LLMManager()

        async def event_generator():
            request_id = f"chatcmpl-{int(time.time() * 1000)}"
            created = int(time.time())

            try:
                async for chunk in mgr.stream(
                    prompt="\n".join([m["content"] for m in prompt.working_memory]),
                    system=prompt.system_instruction,
                    temperature=prompt.temperature,
                    max_tokens=prompt.max_tokens,
                    intent=prompt.intent,
                ):
                    data = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": body.model,
                        "choices": [
                            {"index": 0, "delta": {"content": chunk}, "finish_reason": None}
                        ],
                    }
                    import json
                    yield f"data: {json.dumps(data)}\n\n"
            except Exception as e:  # noqa: BLE001 — streaming SSE boundary
                logger.error("Spoof Stream Error: %s", e)
                yield 'data: {"error": "Internal streaming error"}\n\n'

            yield "data: [DONE]\n\n"

        return StreamingResponse(event_generator(), media_type="text/event-stream")

    # Non-streaming — USE SOVEREIGN GRADE CASCADE
    try:
        async with SovereignLLM(
            temperature=prompt.temperature,
            max_tokens=prompt.max_tokens,
        ) as sllm:
            result = await sllm.generate(
                prompt="\n".join([m["content"] for m in prompt.working_memory]),
                system=prompt.system_instruction,
                intent=prompt.intent,
            )

        latency = (time.time() - start_time) * 1000
        logger.info(
            "🛡️ [SPOOF] Serviced %s via %s (%s) in %.2fms",
            body.model,
            result.provider,
            prompt.intent,
            latency,
        )

        return {
            "id": f"chatcmpl-{int(time.time() * 1000)}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.model,
            "usage": {
                "prompt_tokens": len(str(prompt.working_memory)) // 4,
                "completion_tokens": len(result.content) // 4,
                "total_tokens": (len(str(prompt.working_memory)) + len(result.content)) // 4,
            },
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": result.content,
                    },
                    "finish_reason": "stop",
                    "index": 0,
                }
            ],
            "system_fingerprint": "cortex-sovereign-v5",
        }
    except Exception as e:  # noqa: BLE001 — endpoint boundary
        logger.error("Spoof Completion Error: %s", e)
        raise HTTPException(status_code=500, detail="Internal server error") from e
