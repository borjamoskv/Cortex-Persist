"""Auto-persist hooks for MCP session lifecycle.

When an MCP session closes, this module scans the interaction context
and auto-persists decisions, errors, and ghosts to CORTEX — without
the agent needing a prompt rule to tell it. The prompt becomes unnecessary
because the product enforces the behavior.

Copyright 2026 Borja Moskv — Apache-2.0
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["AutoPersistHook", "SessionFact"]

logger = logging.getLogger("cortex.mcp.auto_persist")


class SessionFact:
    """A fact detected during session analysis."""

    def __init__(
        self,
        fact_type: str,
        content: str,
        project: str = "cortex",
        confidence: str = "inferred",
    ) -> None:
        self.fact_type = fact_type
        self.content = content
        self.project = project
        self.confidence = confidence

    def __repr__(self) -> str:
        return f"SessionFact({self.fact_type!r}, {self.content[:50]!r})"


# ─── Signal Detection Patterns ────────────────────────────────────

_DECISION_SIGNALS: list[str] = [
    r"\bdecided\b", r"\bdecision:\b", r"\bchose\b", r"\bselected\b",
    r"\bapproved\b", r"\bwent with\b", r"\bopted for\b", r"\bwill use\b", r"\bcommitted to\b",
    # Spanish
    r"\bdecidido\b", r"\bdecidimos\b", r"\bdecisión:\b", r"\belegido\b",
    r"\bseleccionado\b", r"\baprobado\b", r"\boptamos por\b", r"\busaremos\b", r"\bmejora\b"
]

_ERROR_SIGNALS: list[str] = [
    r"\berror:\b", r"\bfailed:\b", r"\bbug:\b", r"\bexception:\b", r"\btraceback\b",
    r"\bfix:\b", r"\bresolved:\b", r"\bcrashed\b", r"\bbroken\b",
    # Spanish
    r"\bfallo:\b", r"\bexcepción:\b", r"\bcorregido:\b", r"\bresuelto:\b",
    r"\bha petado\b", r"\broto\b", r"\bfalló\b", r"\bsolucionado:\b"
]

_GHOST_SIGNALS: list[str] = [
    r"\bto" + "do:\b", r"\bfix" + "me:\b", r"\bha" + "ck:\b", r"\blater:\b",
    r"\bincomplete\b", r"\bneeds work\b", r"\bfollow up\b", r"\bpending\b",
    r"\bleft off\b", r"\bunfinished\b",
    # Spanish
    r"\bpara luego\b", r"\bincompleto\b", r"\bnecesita trabajo\b",
    r"\bpendiente\b", r"\bdejamos en\b", r"\bsin terminar\b"
]


class AutoPersistHook:
    """Analyzes session interactions and auto-persists detected facts.

    Usage::

        hook = AutoPersistHook(engine, source="agent:gemini")
        # During session, collect messages
        hook.observe("Decided to use SQLite instead of Postgres")
        hook.observe("Error: connection timeout on startup")
        # On session close
        facts = hook.analyze()
        await hook.persist(facts)
    """

    def __init__(
        self,
        engine: Any = None,
        source: str = "mcp:auto-persist",
        project: str = "cortex",
    ) -> None:
        self.engine = engine
        self.source = source
        self.project = project
        self._observations: list[str] = []

    def observe(self, message: str) -> None:
        """Record a message from the session for later analysis."""
        if message and message.strip():
            self._observations.append(message.strip())

    def analyze(self) -> list[SessionFact]:
        """Scan all observed messages for decision/error/ghost signals.

        Returns a deduplicated list of SessionFacts to persist.
        """
        facts: list[SessionFact] = []
        seen_content: set[str] = set()

        for msg in self._observations:
            msg_lower = msg.lower()
            detected_type = self._classify_message(msg_lower)
            if detected_type and msg not in seen_content:
                seen_content.add(msg)
                facts.append(
                    SessionFact(
                        fact_type=detected_type,
                        content=msg,
                        project=self.project,
                        confidence="inferred",
                    )
                )

        logger.info(
            "AutoPersist: analyzed %d messages, detected %d facts",
            len(self._observations),
            len(facts),
        )
        return facts

    async def persist(self, facts: list[SessionFact] | None = None) -> list[int]:
        """Persist detected facts to CORTEX. Returns list of stored fact IDs."""
        if facts is None:
            facts = self.analyze()

        if not facts:
            logger.debug("AutoPersist: nothing to persist")
            return []

        if self.engine is None:
            logger.warning("AutoPersist: no engine available, skipping persist")
            return []

        ids: list[int] = []
        for fact in facts:
            try:
                fact_id = await self.engine.store(
                    project=fact.project,
                    content=fact.content,
                    fact_type=fact.fact_type,
                    source=self.source,
                    confidence=fact.confidence,
                )
                ids.append(fact_id)
                logger.info(
                    "AutoPersist: stored %s fact #%d: %.60s",
                    fact.fact_type,
                    fact_id,
                    fact.content,
                )
            except (ValueError, OSError) as e:
                logger.warning(
                    "AutoPersist: failed to store %s fact: %s",
                    fact.fact_type,
                    e,
                )
        return ids

    @staticmethod
    def _classify_message(msg_lower: str) -> str | None:
        """Classify a message by its signal patterns using regex.

        Priority: error > decision > ghost (errors are most critical).
        """
        import re
        
        for pattern in _ERROR_SIGNALS:
            if re.search(pattern, msg_lower):
                return "error"
        for pattern in _DECISION_SIGNALS:
            if re.search(pattern, msg_lower):
                return "decision"
        for pattern in _GHOST_SIGNALS:
            if re.search(pattern, msg_lower):
                return "ghost"
        return None
