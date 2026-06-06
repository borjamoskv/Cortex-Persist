# [C5-REAL] Exergy-Maximized
"""
LLM Exergy Middleware (OpenAI Proxy / Labyrinth)
C5-REAL Cognitive Operating System Route.

This module exposes a plug-and-play OpenAI-compatible `/v1/chat/completions` proxy.
It intercepts ANY prompt, forwards it to the target LLM provider, and subjects
the output to the "Deterministic Labyrinth" filter-annihilating stochastic prose,
enforcing C5-REAL execution limits, and allowing ONLY actionable exergy to survive.
"""

from __future__ import annotations

import json
import logging
import os
import re
from collections.abc import AsyncGenerator

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse, StreamingResponse

from cortex.extensions.signals.bus import AsyncSignalBus

logger = logging.getLogger("cortex.exergy.middleware")

router = APIRouter(prefix="/llm-proxy/v1", tags=["Exergy Proxy"])

# The actual target LLM API (can be OpenAI, vLLM, Ollama, etc.)
UPSTREAM_API_URL = os.getenv("EXERGY_UPSTREAM_URL", "https://api.openai.com/v1")
UPSTREAM_API_KEY = os.getenv("EXERGY_UPSTREAM_KEY", os.getenv("OPENAI_API_KEY", ""))


class DeterministicLabyrinth:
    """
    The Filter: Converts stochastic LLM text back into pure deterministic logic.
    - Eliminates decorative prose.
    - Extracts only code blocks, YAML state claims, and JSON.
    - Forces C5-REAL / C4-SIM declarations.
    """

    @staticmethod
    def annihilate_entropy(raw_text: str) -> str:
        """
        Strips all narrative and keeps only structured data or code.
        If the output does not contain a C5-REAL/C4-SIM declaration, it injects an anomaly warning.
        """
        # 1. Check Reality Level (R1)
        has_reality_level = "C5-REAL" in raw_text or "C4-SIM" in raw_text

        # 2. Extract structural payloads (markdown code blocks, YAML structures)
        # We find all ``` blocks
        code_blocks = re.findall(r"```[\s\S]*?```", raw_text)

        # We find explicit YAML claims (R2 format)
        claim_blocks = re.findall(r"(?i)Claim:.*?Proof:.*?}", raw_text, re.DOTALL)

        if not code_blocks and not claim_blocks:
            # Complete entropy collapse - no actionable exergy found
            return (
                "🚨 [LABYRINTH_INTERVENTION]: Zero exergy detected. "
                "Narrative prose annihilated. Emit C5-REAL actionable code or structured YAML claims."
            )

        # 3. Reconstruct output based purely on Exergy vectors
        exergy_output = []
        if not has_reality_level:
            exergy_output.append(
                "> [LABYRINTH_WARNING]: Implicit C4-SIM state. Reality level undeclared.\n"
            )

        for claim in claim_blocks:
            exergy_output.append(f"{claim}\n")

        for block in code_blocks:
            exergy_output.append(f"{block}\n")

        return "\n".join(exergy_output)


async def _stream_labyrinth_proxy(request: Request, payload: dict) -> AsyncGenerator[str, None]:
    """Streams the upstream response, buffers it slightly to apply the Labyrinth filter."""
    headers = {
        "Authorization": f"Bearer {UPSTREAM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        try:
            async with client.stream(
                "POST",
                f"{UPSTREAM_API_URL}/chat/completions",
                json=payload,
                headers=headers,
                timeout=60.0,
            ) as response:
                if response.status_code != 200:
                    yield f"data: {json.dumps({'error': 'Upstream failure', 'status': response.status_code})}\n\n"
                    return

                # In a true streaming exergy filter, we'd build an AST or buffer per line.
                # For this MVP middleware, we aggregate chunks, filter, and yield synthetic chunks
                # to maintain the illusion of standard OpenAI streaming while enforcing the filter.

                # To perfectly filter prose *out* of a stream without breaking markdown,
                # we must buffer until we hit a code block or claim.
                # (For simplicity in V1, we buffer the whole response and flush it fast).

                full_content = ""
                chunk_template = None

                async for line in response.aiter_lines():
                    if not line.startswith("data: ") or line == "data: [DONE]":
                        continue

                    try:
                        chunk_data = json.loads(line[6:])
                        if chunk_template is None:
                            chunk_template = chunk_data  # Save the skeleton for later

                        delta = chunk_data.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta:
                            full_content += delta["content"]
                    except Exception as exc:
                        logger.warning("Suppressed exception: %s", exc)

                # Apply the Labyrinth Filter
                purified_content = DeterministicLabyrinth.annihilate_entropy(full_content)

                # ─── CORTEX LIVE INTEGRATION ───
                # Broadcast the purified exergy over the Aether Matrix (SSE Bus)
                pool = getattr(request.app.state, "pool", None)
                if pool and "[LABYRINTH_INTERVENTION]" not in purified_content:
                    async with pool.acquire() as conn:
                        bus = AsyncSignalBus(conn)
                        await bus.emit(
                            event_type="exergy.live.payload",
                            payload={"content": purified_content},
                            source="llm_labyrinth",
                        )
                # ───────────────────────────────

                # Flush the purified content as a single large chunk to the client
                if chunk_template:
                    chunk_template["choices"][0]["delta"] = {"content": purified_content}
                    yield f"data: {json.dumps(chunk_template)}\n\n"

                yield "data: [DONE]\n\n"

        except httpx.RequestError as e:
            logger.error("Labyrinth upstream connection error: %s", e)
            yield f"data: {json.dumps({'error': 'Labyrinth proxy failed', 'details': str(e)})}\n\n"


@router.post("/chat/completions")
async def proxy_chat_completions(
    request: Request,
    # current_user = Depends(get_current_user) # Uncomment for strict auth
):
    """
    OpenAI-compatible Chat Completions endpoint.
    Passes the output through the Deterministic Labyrinth (Exergy Filter).
    """
    if not UPSTREAM_API_KEY:
        raise HTTPException(
            status_code=500, detail="EXERGY_UPSTREAM_KEY not configured in environment."
        )

    payload = await request.json()
    is_stream = payload.get("stream", False)

    if is_stream:
        return StreamingResponse(
            _stream_labyrinth_proxy(request, payload), media_type="text/event-stream"
        )

    # Sync (non-streaming) processing
    headers = {
        "Authorization": f"Bearer {UPSTREAM_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{UPSTREAM_API_URL}/chat/completions", json=payload, headers=headers, timeout=60.0
        )

        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=resp.text)

        data = resp.json()

        # Apply Labyrinth and emit to CORTEX LIVE
        pool = getattr(request.app.state, "pool", None)

        for choice in data.get("choices", []):
            if "message" in choice and "content" in choice["message"]:
                raw_text = choice["message"]["content"]
                purified_content = DeterministicLabyrinth.annihilate_entropy(raw_text)
                choice["message"]["content"] = purified_content

                # ─── CORTEX LIVE INTEGRATION ───
                if pool and "[LABYRINTH_INTERVENTION]" not in purified_content:
                    async with pool.acquire() as conn:
                        bus = AsyncSignalBus(conn)
                        await bus.emit(
                            event_type="exergy.live.payload",
                            payload={"content": purified_content},
                            source="llm_labyrinth",
                        )
                # ───────────────────────────────

        return JSONResponse(content=data)
