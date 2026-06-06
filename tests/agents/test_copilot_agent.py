# [C5-REAL] Exergy-Maximized
"""Tests for Level 3 - CopilotAgent.

Validates the core copilot contract:
  1. Copilot generates suggestions from context (NEVER applies them)
  2. Copilot processes human verdicts (ONLY feedback mechanism)
  3. Copilot telemetry tracks acceptance rates
  4. Copilot has ZERO autonomous capability
  5. Copilot tick() is intentionally empty
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from cortex.agents.builtins.copilot_agent import (
    CopilotAgent,
    InlineCompletionStrategy,
    DiagnosticFixStrategy,
    MultiFileEditStrategy,
    SuggestionStrategy,
    create_copilot_agent,
)
from cortex.agents.copilot_contracts import (
    CodeEdit,
    Confidence,
    CopilotContextPayload,
    CopilotTelemetry,
    CursorContext,
    ProjectContext,
    SuggestionBatch,
    SuggestionKind,
    SuggestionProposal,
    SuggestionStatus,
    SuggestionVerdict,
)
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind, new_message
from cortex.agents.state import AgentStatus


# ── Fixtures ──────────────────────────────────────────────────────


class MockBus:
    """Minimal async message bus mock for testing."""

    def __init__(self) -> None:
        self.sent: list[AgentMessage] = []
        self._queue: asyncio.Queue[AgentMessage | None] = asyncio.Queue()

    async def send(self, msg: AgentMessage) -> None:
        self.sent.append(msg)

    async def receive(self, agent_id: str, timeout: float = 1.0) -> AgentMessage | None:
        try:
            return self._queue.get_nowait()
        except asyncio.QueueEmpty:
            return None

    def inject(self, msg: AgentMessage) -> None:
        self._queue.put_nowait(msg)


def _make_context_payload(
    *,
    prefix: str = "def hello():",
    trigger: str = "keystroke",
    diagnostics: list[dict[str, Any]] | None = None,
    recent_edits: list[dict[str, Any]] | None = None,
    open_files: list[str] | None = None,
) -> dict[str, Any]:
    """Build a CopilotContextPayload dict for testing."""
    return CopilotContextPayload(
        cursor=CursorContext(
            file_path="test.py",
            language="python",
            cursor_line=1,
            cursor_column=len(prefix) + 1,
            prefix=prefix,
            suffix="",
        ),
        project=ProjectContext(
            diagnostics=diagnostics or [],
            recent_edits=recent_edits or [],
            open_files=open_files or [],
        ),
        trigger=trigger,
        max_suggestions=3,
    ).model_dump(mode="json")


def _make_copilot(bus: MockBus | None = None) -> tuple[CopilotAgent, MockBus]:
    """Create a CopilotAgent with a mock bus."""
    bus = bus or MockBus()
    agent = create_copilot_agent(bus, agent_id="copilot-test")
    return agent, bus


# ── Core Contract Tests ──────────────────────────────────────────


class TestCopilotContract:
    """Validate the Level 3 constraint: copilot NEVER acts alone."""

    def test_manifest_has_no_tools(self) -> None:
        """Copilot manifest must have empty tools_allowed."""
        agent, _ = _make_copilot()
        assert agent.manifest.tools_allowed == []

    def test_manifest_cannot_delegate(self) -> None:
        """Copilot must not be able to delegate to sub-agents."""
        agent, _ = _make_copilot()
        assert agent.manifest.can_delegate is False

    def test_manifest_not_daemon(self) -> None:
        """Copilot is reactive, not a daemon."""
        agent, _ = _make_copilot()
        assert agent.manifest.daemon is False

    @pytest.mark.asyncio
    async def test_tick_is_noop(self) -> None:
        """tick() must do nothing - copilot is purely reactive."""
        agent, _ = _make_copilot()
        # Should complete without error and without side effects
        await agent.tick()
        assert agent.get_pending_count() == 0


# ── Suggestion Generation Tests ──────────────────────────────────


class TestSuggestionGeneration:
    """Test that the copilot generates suggestions without applying them."""

    @pytest.mark.asyncio
    async def test_context_generates_suggestions(self) -> None:
        """Sending context should produce suggestion proposals."""
        agent, bus = _make_copilot()

        msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_REQUEST,
            payload=_make_context_payload(prefix="def hello():"),
        )

        await agent.handle_message(msg)

        # Should have sent a response
        assert len(bus.sent) == 1
        response = bus.sent[0]
        assert response.kind == MessageKind.TASK_RESULT

        # Response should contain suggestions
        batch_data = response.payload
        assert "suggestions" in batch_data
        assert isinstance(batch_data["suggestions"], list)

    @pytest.mark.asyncio
    async def test_suggestions_are_pending(self) -> None:
        """Generated suggestions should be tracked as pending."""
        agent, bus = _make_copilot()

        msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_REQUEST,
            payload=_make_context_payload(prefix="def hello():"),
        )

        await agent.handle_message(msg)
        assert agent.get_pending_count() > 0

    @pytest.mark.asyncio
    async def test_diagnostic_trigger(self) -> None:
        """Diagnostic trigger should use DiagnosticFixStrategy."""
        agent, bus = _make_copilot()

        msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_REQUEST,
            payload=_make_context_payload(
                prefix="x = 1 +",
                trigger="diagnostic",
                diagnostics=[
                    {"file": "test.py", "line": 1, "severity": "error", "message": "SyntaxError"},
                ],
            ),
        )

        await agent.handle_message(msg)

        assert len(bus.sent) == 1
        batch_data = bus.sent[0].payload
        suggestions = batch_data.get("suggestions", [])
        assert len(suggestions) >= 1
        assert suggestions[0]["kind"] == SuggestionKind.FIX_SUGGESTION.value

    @pytest.mark.asyncio
    async def test_invalid_context_returns_error(self) -> None:
        """Invalid context payload should return an error, not crash."""
        agent, bus = _make_copilot()

        msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_REQUEST,
            payload={"garbage": True},
        )

        await agent.handle_message(msg)

        assert len(bus.sent) == 1
        assert "error" in bus.sent[0].payload


# ── Verdict Processing Tests ─────────────────────────────────────


class TestVerdictProcessing:
    """Test human verdict handling and telemetry updates."""

    @pytest.mark.asyncio
    async def test_accept_verdict_updates_telemetry(self) -> None:
        """Accepting a suggestion should update telemetry."""
        agent, bus = _make_copilot()

        # First, generate a suggestion
        ctx_msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_REQUEST,
            payload=_make_context_payload(prefix="def hello():"),
        )
        await agent.handle_message(ctx_msg)

        # Get the suggestion ID from the response
        batch_data = bus.sent[0].payload
        suggestion_id = batch_data["suggestions"][0]["suggestion_id"]

        # Now send a verdict
        verdict_msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_RESULT,
            payload=SuggestionVerdict(
                suggestion_id=suggestion_id,
                verdict=SuggestionStatus.ACCEPTED,
            ).model_dump(mode="json"),
        )
        await agent.handle_message(verdict_msg)

        # Check telemetry
        telemetry = agent.get_telemetry()
        assert telemetry["total_accepted"] >= 1
        assert telemetry["acceptance_rate"] > 0

    @pytest.mark.asyncio
    async def test_reject_verdict_updates_telemetry(self) -> None:
        """Rejecting a suggestion should update telemetry."""
        agent, bus = _make_copilot()

        # Generate
        ctx_msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_REQUEST,
            payload=_make_context_payload(prefix="def hello():"),
        )
        await agent.handle_message(ctx_msg)

        suggestion_id = bus.sent[0].payload["suggestions"][0]["suggestion_id"]

        # Reject
        verdict_msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_RESULT,
            payload=SuggestionVerdict(
                suggestion_id=suggestion_id,
                verdict=SuggestionStatus.REJECTED,
            ).model_dump(mode="json"),
        )
        await agent.handle_message(verdict_msg)

        telemetry = agent.get_telemetry()
        assert telemetry["total_rejected"] >= 1
        assert telemetry["acceptance_rate"] == 0.0


# ── Strategy Tests ────────────────────────────────────────────────


class TestStrategies:
    """Test individual suggestion strategies."""

    @pytest.mark.asyncio
    async def test_inline_completion_block_body(self) -> None:
        """InlineCompletionStrategy should suggest body for block definitions."""
        strategy = InlineCompletionStrategy()
        context = CopilotContextPayload(
            cursor=CursorContext(
                file_path="test.py",
                prefix="class MyClass:",
                suffix="",
            ),
        )
        results = await strategy.generate(context)
        assert len(results) >= 1
        assert results[0].kind == SuggestionKind.CODE_COMPLETION

    @pytest.mark.asyncio
    async def test_diagnostic_fix_generates_edits(self) -> None:
        """DiagnosticFixStrategy should produce structured edits."""
        strategy = DiagnosticFixStrategy()
        context = CopilotContextPayload(
            cursor=CursorContext(file_path="test.py", prefix="x"),
            project=ProjectContext(
                diagnostics=[
                    {"file": "test.py", "line": 5, "severity": "error", "message": "NameError: x"},
                ],
            ),
            trigger="diagnostic",
        )
        results = await strategy.generate(context)
        assert len(results) == 1
        assert results[0].kind == SuggestionKind.FIX_SUGGESTION
        assert len(results[0].edits) == 1

    @pytest.mark.asyncio
    async def test_multi_file_rename_propagation(self) -> None:
        """MultiFileEditStrategy should propose rename propagation."""
        strategy = MultiFileEditStrategy()
        context = CopilotContextPayload(
            cursor=CursorContext(file_path="main.py", prefix=""),
            project=ProjectContext(
                recent_edits=[
                    {"file": "main.py", "line": 10, "old": "old_func", "new": "new_func"},
                ],
                open_files=["main.py", "utils.py", "tests.py"],
            ),
            trigger="explicit",
        )
        results = await strategy.generate(context)
        assert len(results) >= 1
        assert results[0].kind == SuggestionKind.CODE_REFACTOR
        # Should propose edits for utils.py and tests.py (not main.py itself)
        assert len(results[0].edits) == 2

    @pytest.mark.asyncio
    async def test_custom_strategy_registration(self) -> None:
        """Custom strategies should be registrable at runtime."""
        agent, bus = _make_copilot()

        class CustomStrategy(SuggestionStrategy):
            async def generate(self, context, *, model="test"):
                return [
                    SuggestionProposal(
                        suggestion_id="custom-001",
                        kind=SuggestionKind.COMMAND,
                        confidence=Confidence.HIGH,
                        inline_text="echo 'hello'",
                        explanation="Custom strategy test",
                    )
                ]

        agent.register_strategy("custom_trigger", CustomStrategy())

        msg = new_message(
            sender="ide",
            recipient="copilot-test",
            kind=MessageKind.TASK_REQUEST,
            payload=_make_context_payload(prefix="", trigger="custom_trigger"),
        )
        await agent.handle_message(msg)

        suggestions = bus.sent[0].payload["suggestions"]
        assert suggestions[0]["suggestion_id"] == "custom-001"


# ── Contract Model Tests ─────────────────────────────────────────


class TestContractModels:
    """Test the Pydantic contract models for correctness."""

    def test_cursor_context_defaults(self) -> None:
        ctx = CursorContext(file_path="test.py")
        assert ctx.cursor_line == 1
        assert ctx.language == "python"

    def test_suggestion_proposal_defaults(self) -> None:
        p = SuggestionProposal(
            suggestion_id="test-001",
            kind=SuggestionKind.CODE_COMPLETION,
        )
        assert p.status == SuggestionStatus.PENDING
        assert p.confidence == Confidence.MEDIUM
        assert p.ttl_seconds == 30

    def test_telemetry_acceptance_rate(self) -> None:
        t = CopilotTelemetry()
        t.record_verdict(
            SuggestionVerdict(
                suggestion_id="a",
                verdict=SuggestionStatus.ACCEPTED,
            )
        )
        t.record_verdict(
            SuggestionVerdict(
                suggestion_id="b",
                verdict=SuggestionStatus.REJECTED,
            )
        )
        assert t.acceptance_rate == pytest.approx(0.5)

    def test_code_edit_model(self) -> None:
        edit = CodeEdit(
            file_path="test.py",
            start_line=1,
            end_line=5,
            original_text="old",
            replacement_text="new",
        )
        assert edit.file_path == "test.py"
        assert edit.start_line == 1
