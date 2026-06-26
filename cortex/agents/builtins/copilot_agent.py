# [C5-REAL] Exergy-Maximized
"""CORTEX Agent Runtime - Level 3 Copilot Agent.

██████╗ ██████╗ ██████╗ ██╗██╗      ██████╗ ████████╗
██╔════╝██╔═══██╗██╔══██╗██║██║     ██╔═══██╗╚══██╔══╝
██║     ██║   ██║██████╔╝██║██║     ██║   ██║   ██║
██║     ██║   ██║██╔═══╝ ██║██║     ██║   ██║   ██║
╚██████╗╚██████╔╝██║     ██║███████╗╚██████╔╝   ██║
 ╚═════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝ ╚═════╝    ╚═╝

LEVEL 3 - COPILOT
  - Observes the human's context (cursor, file, project state)
  - Generates inline suggestions (completions, edits, refactors)
  - NEVER acts autonomously - ALL suggestions require human verdict
  - Is an amplifier, not an agent

Architecture:
  HUMAN writes ──→ [COPILOT observes] ──→ SUGGESTION_PROPOSAL
                                                │
                                    HUMAN accepts/rejects

Constraint: Without the human, the copilot does NOTHING.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any
from uuid import uuid4

from cortex.agents.base import BaseAgent
from cortex.agents.copilot_contracts import (
    CodeEdit,
    Confidence,
    CopilotContextPayload,
    CopilotTelemetry,
    SuggestionBatch,
    SuggestionKind,
    SuggestionProposal,
    SuggestionStatus,
    SuggestionVerdict,
)
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.tools import ToolRegistry

logger = logging.getLogger("cortex.agents.copilot")


# ── Suggestion Generation Strategies ─────────────────────────────


class SuggestionStrategy:
    """Base strategy for generating suggestions from context.

    Production implementations would call LLM APIs here.
    This base provides a deterministic fallback for testing.
    """

    async def generate(
        self,
        context: CopilotContextPayload,
        *,
        model: str = "gemini-2.5-pro",
    ) -> list[SuggestionProposal]:
        """Generate suggestions from editor context.

        Args:
            context: Full IDE context snapshot.
            model: LLM model identifier.

        Returns:
            List of SuggestionProposals (never applied, only proposed).
        """
        raise NotImplementedError


class InlineCompletionStrategy(SuggestionStrategy):
    """Generates inline code completions (Tab-accept pattern).

    This is the GitHub Copilot / Cursor tab-completion mode.
    """

    async def generate(
        self,
        context: CopilotContextPayload,
        *,
        model: str = "gemini-2.5-pro",
    ) -> list[SuggestionProposal]:
        prefix = context.cursor.prefix

        # --- In production, this calls the LLM API ---
        # For now: deterministic stub that demonstrates the contract.
        # The REAL model call would be:
        #   response = await llm_client.complete(
        #       prefix=prefix, suffix=suffix, model=model,
        #       max_tokens=256, temperature=0.0,
        #   )

        context_hash = _hash_context(context)
        suggestions: list[SuggestionProposal] = []

        # Detect patterns and generate structured completions
        if prefix.rstrip().endswith(":"):
            # Likely a function/class definition - suggest body
            suggestions.append(
                SuggestionProposal(
                    suggestion_id=f"cpl-{uuid4().hex[:12]}",
                    kind=SuggestionKind.CODE_COMPLETION,
                    confidence=Confidence.MEDIUM,
                    inline_text="\n    pass\n",
                    explanation="Empty body stub for new block",
                    source_context_hash=context_hash,
                    model_used=model,
                )
            )

        if "def " in prefix and "return" not in prefix:
            # Function without return - suggest docstring
            suggestions.append(
                SuggestionProposal(
                    suggestion_id=f"cpl-{uuid4().hex[:12]}",
                    kind=SuggestionKind.DOCUMENTATION,
                    confidence=Confidence.MEDIUM,
                    inline_text='    """PENDING: Document this function."""\n',
                    explanation="Missing docstring detected",
                    source_context_hash=context_hash,
                    model_used=model,
                )
            )

        # Always offer at least one generic completion
        if not suggestions and prefix.strip():
            suggestions.append(
                SuggestionProposal(
                    suggestion_id=f"cpl-{uuid4().hex[:12]}",
                    kind=SuggestionKind.CODE_COMPLETION,
                    confidence=Confidence.LOW,
                    inline_text="",
                    explanation="No strong signal detected - awaiting more context",
                    source_context_hash=context_hash,
                    model_used=model,
                )
            )

        return suggestions[: context.max_suggestions]


class DiagnosticFixStrategy(SuggestionStrategy):
    """Generates fix suggestions from active diagnostics (lint errors, type errors).

    This is the Grammarly / Codeium error-fix pattern.
    """

    async def generate(
        self,
        context: CopilotContextPayload,
        *,
        model: str = "gemini-2.5-pro",
    ) -> list[SuggestionProposal]:
        context_hash = _hash_context(context)
        suggestions: list[SuggestionProposal] = []

        for diag in context.project.diagnostics:
            file_path = diag.get("file", context.cursor.file_path)
            line = diag.get("line", 1)
            message = diag.get("message", "")
            severity = diag.get("severity", "warning")

            # Generate a structured edit proposal per diagnostic
            suggestions.append(
                SuggestionProposal(
                    suggestion_id=f"fix-{uuid4().hex[:12]}",
                    kind=SuggestionKind.FIX_SUGGESTION,
                    confidence=(Confidence.HIGH if severity == "error" else Confidence.MEDIUM),
                    edits=[
                        CodeEdit(
                            file_path=file_path,
                            start_line=line,
                            end_line=line,
                            original_text="",
                            replacement_text=f"# PENDING: Fix - {message}",
                        )
                    ],
                    explanation=f"Fix for {severity}: {message}",
                    source_context_hash=context_hash,
                    model_used=model,
                )
            )

        return suggestions[: context.max_suggestions]


class MultiFileEditStrategy(SuggestionStrategy):
    """Generates multi-file edit proposals (Cursor multi-file mode).

    Observes recent edits + git diff to propose coordinated changes.
    """

    async def generate(
        self,
        context: CopilotContextPayload,
        *,
        model: str = "gemini-2.5-pro",
    ) -> list[SuggestionProposal]:
        context_hash = _hash_context(context)
        suggestions: list[SuggestionProposal] = []

        # Analyze recent edits for propagation opportunities
        for edit in context.project.recent_edits:
            old_symbol = edit.get("old", "")
            new_symbol = edit.get("new", "")
            source_file = edit.get("file", "")

            if old_symbol and new_symbol and old_symbol != new_symbol:
                # Symbol rename detected - propose propagation to open files
                edits: list[CodeEdit] = []
                for open_file in context.project.open_files:
                    if open_file != source_file:
                        edits.append(
                            CodeEdit(
                                file_path=open_file,
                                start_line=1,
                                end_line=1,
                                original_text=old_symbol,
                                replacement_text=new_symbol,
                            )
                        )

                if edits:
                    suggestions.append(
                        SuggestionProposal(
                            suggestion_id=f"mfe-{uuid4().hex[:12]}",
                            kind=SuggestionKind.CODE_REFACTOR,
                            confidence=Confidence.MEDIUM,
                            edits=edits,
                            explanation=(
                                f"Rename '{old_symbol}' → '{new_symbol}' "
                                f"across {len(edits)} file(s)"
                            ),
                            source_context_hash=context_hash,
                            model_used=model,
                        )
                    )

        return suggestions[: context.max_suggestions]


# ── Core Copilot Agent ────────────────────────────────────────────


class CopilotAgent(BaseAgent):
    """Level 3 - Copilot Agent.

    Observes the human's editor context, generates inline suggestions,
    and waits for human verdicts. NEVER executes changes autonomously.

    Message Protocol:
        IN:  TASK_REQUEST with CopilotContextPayload → generates suggestions
        IN:  TASK_RESULT with SuggestionVerdict → records feedback/telemetry
        OUT: TASK_RESULT with SuggestionBatch → proposals for human review

    Behavioral Constraints:
        1. Copilot NEVER calls use_tool() to mutate state
        2. All output is SuggestionProposal - human decides application
        3. No autonomous tick() work - purely reactive to context
        4. Telemetry-only feedback loop (no self-modification)
    """

    def __init__(
        self,
        manifest: AgentManifest,
        bus: Any,
        tool_registry: ToolRegistry | None = None,
        *,
        strategies: dict[str, SuggestionStrategy] | None = None,
    ) -> None:
        super().__init__(manifest, bus, tool_registry)
        self.telemetry = CopilotTelemetry()
        self._pending: dict[str, SuggestionProposal] = {}  # suggestion_id → proposal

        # Strategy registry - maps trigger types to generators
        self._strategies: dict[str, SuggestionStrategy] = strategies or {
            "keystroke": InlineCompletionStrategy(),
            "diagnostic": DiagnosticFixStrategy(),
            "explicit": MultiFileEditStrategy(),
        }

        logger.info(
            "[%s] CopilotAgent initialized - strategies=%s",
            self.agent_id,
            list(self._strategies.keys()),
        )

    # ── Message Handler ───────────────────────────────────────────

    async def handle_message(self, message: AgentMessage) -> None:  # type: ignore[override]
        """Route incoming messages to context processing or verdict recording.

        The copilot only handles two message flows:
        1. TASK_REQUEST → Human context arrives → Generate suggestions
        2. TASK_RESULT  → Human verdict arrives → Record telemetry
        """
        if message.kind == MessageKind.TASK_REQUEST:
            await self._handle_context(message)
        elif message.kind == MessageKind.TASK_RESULT:
            await self._handle_verdict(message)
        else:
            logger.debug(
                "[%s] Ignoring message kind=%s",
                self.agent_id,
                message.kind.value,
            )

    # ── Context → Suggestions ─────────────────────────────────────

    async def _handle_context(self, message: AgentMessage) -> None:
        """Process human context and generate suggestion proposals.

        NEVER applies suggestions - only proposes them via message bus.
        """
        payload = message.payload or {}

        try:
            context = CopilotContextPayload(**payload)
        except Exception as exc:
            logger.error("[%s] Invalid context payload: %s", self.agent_id, exc)
            await self._reply(message, {"error": f"Invalid context: {exc}"})
            return

        t0 = time.monotonic()

        # Select strategy based on trigger type
        strategy = self._strategies.get(
            context.trigger,
            self._strategies.get("keystroke", InlineCompletionStrategy()),
        )

        # Generate suggestions (READ-ONLY - no side effects)
        try:
            proposals = await strategy.generate(
                context,
                model=self.manifest.purpose,  # Use manifest purpose as model hint
            )
        except Exception as exc:
            logger.error("[%s] Strategy %s failed: %s", self.agent_id, context.trigger, exc)
            proposals = []

        latency_ms = (time.monotonic() - t0) * 1000

        # Track pending proposals for verdict correlation
        for proposal in proposals:
            self._pending[proposal.suggestion_id] = proposal

        # Expire old pending suggestions
        self._expire_stale_suggestions()

        # Build response batch
        batch = SuggestionBatch(
            suggestions=proposals,
            context_hash=_hash_context(context),
            latency_ms=latency_ms,
        )

        logger.info(
            "[%s] Generated %d suggestions (trigger=%s, latency=%.1fms)",
            self.agent_id,
            len(proposals),
            context.trigger,
            latency_ms,
        )

        # Send proposals back - human decides what to apply
        await self._reply(
            message,
            batch.model_dump(mode="json"),
        )

    # ── Verdict Processing ────────────────────────────────────────

    async def _handle_verdict(self, message: AgentMessage) -> None:
        """Process human's verdict on a suggestion.

        This is the ONLY feedback mechanism. The copilot records
        acceptance rates for telemetry but NEVER self-modifies.
        """
        payload = message.payload or {}

        try:
            verdict = SuggestionVerdict(**payload)
        except Exception as exc:
            logger.error("[%s] Invalid verdict payload: %s", self.agent_id, exc)
            return

        # Correlate with pending proposal
        proposal = self._pending.pop(verdict.suggestion_id, None)
        tokens = proposal.tokens_consumed if proposal else 0

        # Update telemetry
        self.telemetry.record_verdict(verdict, tokens=tokens)

        if proposal:
            proposal.status = verdict.verdict

        logger.info(
            "[%s] Verdict: %s → %s (acceptance_rate=%.2f%%)",
            self.agent_id,
            verdict.suggestion_id,
            verdict.verdict.value,
            self.telemetry.acceptance_rate * 100,
        )

    # ── Tick (INTENTIONALLY EMPTY) ────────────────────────────────

    async def tick(self) -> None:
        """Level 3 agents are purely reactive. No autonomous work.

        The copilot ONLY activates when the human provides context.
        Without the human, it does nothing. This is by design.
        """

    # ── Internal Helpers ──────────────────────────────────────────

    def _expire_stale_suggestions(self) -> None:
        """Expire suggestions that exceeded their TTL."""
        now = time.time()
        expired_ids = []

        for sid, proposal in self._pending.items():
            age = now - proposal.created_at.timestamp()
            if age > proposal.ttl_seconds:
                proposal.status = SuggestionStatus.EXPIRED
                self.telemetry.total_suggestions += 1
                self.telemetry.total_expired += 1
                expired_ids.append(sid)

        for sid in expired_ids:
            del self._pending[sid]

        if expired_ids:
            logger.debug("[%s] Expired %d stale suggestions", self.agent_id, len(expired_ids))

    async def _reply(self, source: AgentMessage, payload: dict[str, Any]) -> None:
        """Send a reply message back to the context source."""
        reply = new_message(
            sender=self.agent_id,
            recipient=source.sender,
            kind=MessageKind.TASK_RESULT,
            payload=payload,
            correlation_id=source.message_id,
        )
        await self.bus.send(reply)

    # ── Public API (for IDE integration) ──────────────────────────

    def get_telemetry(self) -> dict[str, Any]:
        """Return current telemetry snapshot."""
        return self.telemetry.model_dump()

    def get_pending_count(self) -> int:
        """Return number of suggestions awaiting human verdict."""
        return len(self._pending)

    def register_strategy(self, trigger: str, strategy: SuggestionStrategy) -> None:
        """Register a custom suggestion strategy for a trigger type."""
        self._strategies[trigger] = strategy
        logger.info("[%s] Registered strategy for trigger=%s", self.agent_id, trigger)


# ── Factory ───────────────────────────────────────────────────────


def create_copilot_agent(
    bus: Any,
    *,
    agent_id: str = "copilot-0",
    model: str = "gemini-2.5-pro",
    tool_registry: ToolRegistry | None = None,
) -> CopilotAgent:
    """Factory: create a CopilotAgent with sensible defaults.

    The manifest is configured with:
    - No delegation (can_delegate=False)
    - No daemon mode (daemon=False, purely reactive)
    - Empty tools_allowed (copilot observes, never mutates)
    - High error tolerance (5 consecutive before quarantine)
    """
    manifest = AgentManifest(
        agent_id=agent_id,
        purpose=model,
        tools_allowed=[],  # Level 3: NO autonomous tool use
        can_delegate=False,  # Level 3: cannot spawn sub-agents
        daemon=False,  # Purely reactive
        max_consecutive_errors=5,
        confidence_floor="C3",
        trust_level="C3",
    )

    return CopilotAgent(
        manifest=manifest,
        bus=bus,
        tool_registry=tool_registry,
    )


# ── Utilities ─────────────────────────────────────────────────────


def _hash_context(context: CopilotContextPayload) -> str:
    """Deterministic hash of context payload for correlation tracking."""
    raw = (
        f"{context.cursor.file_path}:"
        f"{context.cursor.cursor_line}:"
        f"{context.cursor.cursor_column}:"
        f"{context.cursor.prefix[:128]}:"
        f"{context.trigger}"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:16]
