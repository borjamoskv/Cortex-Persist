"""
memento_extractor.py — Concrete LLM Session Extractor

Concrete implementation of the `SessionExtractor` protocol for the MEMENTO agent.
Queries L3 (EventLedger) directly for completed sessions that haven't been
crystallized, extracts transcripts, and uses CortexLLMRouter to mine them
for high-value cross-session insights.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from cortex.agents.builtins.memento_agent import SessionExtractor
from cortex.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile
from cortex.memory.manager import CortexMemoryManager
from cortex.memory.models import MemoryEvent

try:
    from cortex.extensions.security.tenant import get_tenant_id
except ImportError:

    def get_tenant_id() -> str:
        return "default"


logger = logging.getLogger(__name__)

_PROCESSED_MARKER = "[MEMENTO] Crystallization complete"


class LlmSessionExtractor(SessionExtractor):
    """Concrete SessionExtractor powered by CortexLLMRouter.

    Identifies 'pending' sessions as those whose last event is older
    than `idle_minutes` and lack the _PROCESSED_MARKER event.

    Compiles the session history into a prompt and outputs structured
    JSON insights.
    """

    def __init__(
        self,
        manager: CortexMemoryManager,
        router: CortexLLMRouter,
        idle_minutes: int = 15,
        model_project: str = "MEMENTO",
    ) -> None:
        self._manager = manager
        self._router = router
        self._idle_minutes = idle_minutes
        self._project = model_project

    async def pending_sessions(self) -> list[dict[str, Any]]:
        """Query EventLedgerL3 for finished, unprocessed sessions."""
        tenant_id = get_tenant_id()
        l3 = self._manager.l3()
        await l3.ensure_table()

        # Group by session_id, filter those completely older than idle_minutes,
        # and exclude those that already have a processed marker.
        query = f"""
            SELECT session_id, tenant_id
            FROM memory_events
            WHERE tenant_id = ?
            GROUP BY session_id, tenant_id
            HAVING MAX(timestamp) < datetime('now', '-{self._idle_minutes} minutes')
               AND SUM(token_count) >= 100
               AND session_id NOT IN (
                   SELECT session_id
                   FROM memory_events
                   WHERE content = ? AND tenant_id = ?
               )
            LIMIT 100
        """

        # We access the underlying aiosqlite Connection of L3
        cursor = await l3._conn.execute(query, (tenant_id, _PROCESSED_MARKER, tenant_id))
        rows = await cursor.fetchall()

        return [{"session_id": r[0], "tenant_id": r[1], "project_id": self._project} for r in rows]

    async def extract(self, session_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract insights from the session's event transcript using the LLM."""
        session_id = session_data["session_id"]
        tenant_id = session_data.get("tenant_id") or get_tenant_id()

        events = await self._manager.l3().get_session_events(
            session_id=session_id, tenant_id=tenant_id, limit=1000
        )

        if not events:
            return []

        # Compile transcript
        transcript_lines = []
        for e in events:
            role = e.role.upper()
            transcript_lines.append(f"[{e.timestamp.isoformat()}] {role}: {e.content}")

        transcript = "\n".join(transcript_lines)

        sys_prompt = (
            "You are MEMENTO, a cognitive distillation agent. "
            "Analyze the following conversation session transcript and extract high-value "
            "facts, decisions, patterns, user preferences, and unresolved errors. "
            "Do NOT extract transient chat like 'hello' or steps of a routine task. "
            "Output strictly as a JSON array of objects with keys: "
            "`content` (string), `fact_type` (decision|pattern|preference|error|memento), "
            "and `confidence` (float 0.0-1.0). "
            "If no high-value insights are found, return `[]`."
        )

        prompt = CortexPrompt(
            system_instruction=sys_prompt,
            working_memory=[{"role": "user", "content": f"TRANSCRIPT:\n{transcript}"}],
            intent=IntentProfile.REASONING,
            project=self._project,
            response_format={"type": "json_object"},
        )

        result = await self._router.execute_resilient(prompt)
        if not result.is_ok():
            logger.error("Memento LLM extraction failed: %s", result.error)
            raise RuntimeError(f"LLM extraction failed: {result.error}")

        text = result.unwrap().strip()
        try:
            # Handle potential markdown fencing
            if text.startswith("```json"):
                text = text[7:-3].strip()
            elif text.startswith("```"):
                text = text[3:-3].strip()

            parsed = json.loads(text)

            # The LLM might return {"insights": [...]} or just [...] depending on steering.
            if isinstance(parsed, dict):
                insights = parsed.get("insights", []) or parsed.get("facts", []) or []
            elif isinstance(parsed, list):
                insights = parsed
            else:
                insights = []

            # Filter valid insights
            valid = []
            for item in insights:
                if isinstance(item, dict) and "content" in item:
                    item.setdefault("fact_type", "memento")
                    item.setdefault("confidence", 0.7)
                    valid.append(item)

            return valid

        except json.JSONDecodeError as exc:
            logger.error("Memento failed to decode JSON: %s\nText: %s", exc, text)
            raise RuntimeError("JSON decode failed") from exc

    async def mark_processed(self, session_id: str) -> None:
        """Mark the session as processed by appending a system marker event to L3."""
        event = MemoryEvent(
            timestamp=datetime.now(timezone.utc),
            role="system",
            content=_PROCESSED_MARKER,
            token_count=0,
            session_id=session_id,
            tenant_id=get_tenant_id(),
            metadata={"source": "memento"},
        )
        await self._manager.l3().append_event(event)
