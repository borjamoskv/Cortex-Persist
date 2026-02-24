"""CORTEX Gateway — Telegram Channel Adapter.

Bridges inbound Telegram messages → GatewayRequest → GatewayResponse → Telegram reply.

Setup (webhook mode, no polling needed)::

    export CORTEX_TELEGRAM_TOKEN="7xxx:AAxx"
    export CORTEX_TELEGRAM_CHAT_ID="-1001234"  # Optional: restrict to one chat
    export CORTEX_TELEGRAM_WEBHOOK_SECRET="random_secret_string"

Register webhook (one-time)::

    curl -X POST "https://api.telegram.org/botTOKEN/setWebhook" \
         -d "url=https://your-cortex-host/gateway/telegram/webhook" \
         -d "secret_token=random_secret_string"

Message syntax (in Telegram)::

    /store cortex This decision was made: use Byzantine consensus
    /search cortex episodic memory
    /recall naroa-2026
    /status
    /emit warning Ghost backlog has 30+ items
"""

from __future__ import annotations

import hmac
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from cortex.gateway import GatewayIntent, GatewayRequest, GatewayRouter

logger = logging.getLogger("cortex.gateway.telegram")

router = APIRouter(prefix="/gateway/telegram", tags=["gateway:telegram"])

# Intent keyword map (first word after /)
_COMMAND_TO_INTENT: dict[str, GatewayIntent] = {
    "store": GatewayIntent.STORE,
    "search": GatewayIntent.SEARCH,
    "recall": GatewayIntent.RECALL,
    "status": GatewayIntent.STATUS,
    "emit": GatewayIntent.EMIT,
    "ask": GatewayIntent.ASK,
    "mejoralo": GatewayIntent.MEJORALO,
}


def _parse_telegram_message(text: str) -> GatewayRequest | None:
    """Parse a Telegram message text into a GatewayRequest.

    Supported formats::

        /store PROJECT content...
        /search PROJECT query...
        /recall PROJECT
        /status
        /emit SEVERITY title | body
    """
    text = (text or "").strip()
    if not text.startswith("/"):
        return None

    parts = text.lstrip("/").split(None, 1)
    command = parts[0].lower().split("@")[0]  # strip @BotName suffix

    intent = _COMMAND_TO_INTENT.get(command)
    if intent is None:
        return None

    rest = parts[1] if len(parts) > 1 else ""

    # Parse intent-specific payload
    if intent == GatewayIntent.STORE:
        tokens = rest.split(None, 1)
        project = tokens[0] if tokens else ""
        content = tokens[1] if len(tokens) > 1 else ""
        return GatewayRequest(
            intent=intent,
            project=project,
            payload={"content": content, "type": "knowledge"},
            source="telegram",
        )

    elif intent == GatewayIntent.SEARCH:
        tokens = rest.split(None, 1)
        project = tokens[0] if len(tokens) > 1 else ""
        query = tokens[1] if len(tokens) > 1 else tokens[0] if tokens else ""
        return GatewayRequest(
            intent=intent,
            project=project,
            payload={"query": query, "top_k": 5},
            source="telegram",
        )

    elif intent == GatewayIntent.RECALL:
        return GatewayRequest(
            intent=intent,
            project=rest.strip(),
            payload={},
            source="telegram",
        )

    elif intent == GatewayIntent.STATUS:
        return GatewayRequest(intent=intent, payload={}, source="telegram")

    elif intent == GatewayIntent.EMIT:
        tokens = rest.split(None, 1)
        severity = tokens[0].lower() if tokens else "info"
        body_part = tokens[1] if len(tokens) > 1 else ""
        title_parts = body_part.split("|", 1)
        title = title_parts[0].strip()
        body = title_parts[1].strip() if len(title_parts) > 1 else ""
        return GatewayRequest(
            intent=intent,
            payload={"severity": severity, "title": title, "body": body},
            source="telegram",
        )

    return None


def _format_response(response) -> str:
    """Format a GatewayResponse as human-readable Telegram text."""
    if not response.ok:
        return f"❌ Error: {response.error}"

    intent = response.intent
    data = response.data

    if intent == GatewayIntent.STORE:
        return f"✅ Stored fact #{data['fact_id']} in `{data['project']}`"

    elif intent == GatewayIntent.SEARCH:
        if not data:
            return "🔍 No results found."
        lines = [f"🔍 *{len(data)} results:*\n"]
        for r in data[:5]:
            score = r.get("score", 0)
            lines.append(f"• `[{r['project']}]` ({score:.2f}) — {r['content'][:120]}")
        return "\n".join(lines)

    elif intent == GatewayIntent.RECALL:
        if not data:
            return "📭 No facts found for that project."
        lines = [f"📚 *{len(data)} facts recalled:*\n"]
        for r in data[:10]:
            lines.append(f"• {r.get('content', '')[:120]}")
        return "\n".join(lines)

    elif intent == GatewayIntent.STATUS:
        d = data or {}
        return (
            f"⚡ *CORTEX Status*\n"
            f"Facts: {d.get('total_facts', '?')} total · {d.get('active_facts', '?')} active\n"
            f"Projects: {d.get('projects', '?')}\n"
            f"DB: {d.get('db_size_mb', 0):.1f} MB\n"
            f"Latency: {response.latency_ms:.0f}ms"
        )

    elif intent == GatewayIntent.EMIT:
        if data and data.get("delivered"):
            return f"📨 Event delivered via: {', '.join(data['adapters'])}"
        return "📭 No notification adapters configured."

    return f"✅ Done ({response.latency_ms:.0f}ms)"


@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str = Header(default=""),
) -> JSONResponse:
    """Receive Telegram webhook updates and route through Gateway."""
    # Validate secret token if configured
    import os

    import cortex.api.state as api_state

    expected_secret = os.environ.get("CORTEX_TELEGRAM_WEBHOOK_SECRET", "")
    if expected_secret and not hmac.compare_digest(
        x_telegram_bot_api_secret_token, expected_secret
    ):
        raise HTTPException(status_code=403, detail="Invalid webhook secret")

    body: dict[str, Any] = await request.json()
    message = body.get("message", {})
    text = message.get("text", "")
    chat_id = str(message.get("chat", {}).get("id", ""))
    from_user = str(message.get("from", {}).get("id", ""))

    if not text or not chat_id:
        return JSONResponse({"ok": True})

    gateway_req = _parse_telegram_message(text)
    if gateway_req is None:
        logger.debug("Telegram: unrecognized command from %s: %s", from_user, text[:50])
        return JSONResponse({"ok": True})

    gateway_req.caller_id = from_user

    # Get engine and bus from app state
    engine = getattr(api_state, "async_engine", None) or getattr(api_state, "engine", None)
    bus = getattr(api_state, "notification_bus", None)

    if engine is None:
        logger.error("Telegram webhook: no engine in api_state")
        return JSONResponse({"ok": True})

    gateway_router = GatewayRouter(engine=engine, bus=bus)
    response = await gateway_router.handle(gateway_req)

    reply_text = _format_response(response)

    # Send reply back to Telegram
    import httpx

    token = os.environ.get("CORTEX_TELEGRAM_TOKEN", "")
    if token:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"https://api.telegram.org/bot{token}/sendMessage",
                    json={
                        "chat_id": chat_id,
                        "text": reply_text,
                        "parse_mode": "Markdown",
                    },
                )
        except httpx.RequestError as exc:
            logger.error("Telegram reply failed: %s", exc)

    return JSONResponse({"ok": True})
