"""Tests for cortex.agent.degradation — Sovereign Degradation Protocol (Ω₅)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cortex.agent.degradation import (
    AgentAction,
    AgentCalcificationError,
    AgentDegradedError,
    AgentResult,
    DegradationLevel,
    DegradationReport,
    ModelUnavailableError,
    SchemaIncompatibilityError,
    SovereignAgentError,
    ToolRegistrationError,
    _upgrade_to_l3,
    sovereign_execute,
)

# ─── Exception Hierarchy ─────────────────────────────────────────────────────


class TestExceptionHierarchy:
    def test_schema_incompatibility_is_sovereign(self):
        e = SchemaIncompatibilityError(model="gpt-120b", required_schema="fc_v2")
        assert isinstance(e, SovereignAgentError)
        assert e.level == DegradationLevel.L3_ACTIONABLE
        assert e.level.is_sovereign
        assert e.suggested_alt == "gemini-2.0-flash"
        assert e.component == "tool_registration"

    def test_model_unavailable_carries_fallback(self):
        e = ModelUnavailableError(model="claude-3", reason="quota exceeded")
        assert e.suggested_alt == "gemini-2.0-flash"
        assert "quota exceeded" in str(e)

    def test_tool_registration_error_names_tool(self):
        e = ToolRegistrationError(tool_name="filesystem")
        assert "filesystem" in str(e)
        assert e.component == "tool_registry"

    def test_calcification_error_is_l2(self):
        """Calcification is L2: we can inform but not auto-recover."""
        e = AgentCalcificationError(failure_count=10, pattern="schema_mismatch")
        assert e.level == DegradationLevel.L2_INFORMED
        assert not e.level.is_sovereign

    def test_agent_degraded_error_wraps_cause(self):
        cause = RuntimeError("original")
        e = AgentDegradedError(cause=cause, component="model_client")
        assert e.cause is cause
        assert "model_client" in str(e)

    def test_str_includes_all_fields(self):
        e = SchemaIncompatibilityError(model="m", required_schema="s")
        s = str(e)
        assert "component=" in s
        assert "suggested=" in s
        assert "recovery=" in s


# ─── DegradationLevel Taxonomy ───────────────────────────────────────────────


class TestDegradationLevel:
    def test_l0_is_not_sovereign(self):
        assert not DegradationLevel.L0_HARD_CRASH.is_sovereign

    def test_l1_is_not_sovereign(self):
        assert not DegradationLevel.L1_OPAQUE_ERROR.is_sovereign

    def test_l2_is_not_sovereign(self):
        assert not DegradationLevel.L2_INFORMED.is_sovereign

    def test_l3_is_sovereign(self):
        assert DegradationLevel.L3_ACTIONABLE.is_sovereign

    def test_l4_is_sovereign(self):
        assert DegradationLevel.L4_GRACEFUL.is_sovereign

    def test_symbols_map_correctly(self):
        assert DegradationLevel.L0_HARD_CRASH.symbol == "☠️"
        assert DegradationLevel.L4_GRACEFUL.symbol == "💎"

    def test_integer_ordering(self):
        assert DegradationLevel.L0_HARD_CRASH < DegradationLevel.L4_GRACEFUL


# ─── AgentAction ─────────────────────────────────────────────────────────────


class TestAgentAction:
    def test_frozen(self):
        action = AgentAction(action_id="a1", action_type="store")
        with pytest.raises(AttributeError):
            action.action_type = "mutated"  # type: ignore[misc]

    def test_as_text_only_disables_tools(self):
        action = AgentAction(action_id="a1", action_type="search", requires_tools=True)
        degraded = action.as_text_only()
        assert degraded.requires_tools is False
        assert degraded.action_id == "a1"
        assert degraded.action_type == "search"

    def test_as_text_only_preserves_payload(self):
        action = AgentAction(action_id="x", action_type="recall", payload={"q": "foo"})
        degraded = action.as_text_only()
        assert degraded.payload == {"q": "foo"}


# ─── AgentResult ─────────────────────────────────────────────────────────────


class TestAgentResult:
    def test_with_warning_marks_degraded(self):
        result = AgentResult(action_id="r1", success=True)
        assert not result.is_degraded
        result.with_warning("something went wrong")
        assert result.is_degraded
        assert len(result.warnings) == 1

    def test_l3_level_is_degraded(self):
        result = AgentResult(
            action_id="r2",
            success=True,
            degradation_level=DegradationLevel.L3_ACTIONABLE,
        )
        assert result.is_degraded


# ─── DegradationReport ───────────────────────────────────────────────────────


class TestDegradationReport:
    def test_to_cortex_content_includes_level_and_component(self):
        report = DegradationReport(
            level=DegradationLevel.L3_ACTIONABLE,
            component="tool_registry",
            message="Tool failed",
            recovery_steps=["Check PATH"],
            suggested_alt="gemini",
            context={},
            timestamp=1.0,
        )
        content = report.to_cortex_content()
        assert "L3" in content
        assert "tool_registry" in content
        assert "gemini" in content

    def test_as_report_roundtrip(self):
        e = SchemaIncompatibilityError(model="m", required_schema="fc")
        report = e.as_report()
        assert report.component == "tool_registration"
        assert report.level == DegradationLevel.L3_ACTIONABLE


# ─── _upgrade_to_l3 ──────────────────────────────────────────────────────────


class TestUpgradeToL3:
    def test_wraps_any_exception_as_l3(self):
        original = ValueError("bad input")
        upgraded = _upgrade_to_l3(original, "my_component")
        assert isinstance(upgraded, AgentDegradedError)
        assert upgraded.cause is original
        assert upgraded.component == "my_component"
        assert upgraded.level == DegradationLevel.L3_ACTIONABLE

    def test_recovery_steps_present(self):
        upgraded = _upgrade_to_l3(RuntimeError("x"), "comp")
        assert len(upgraded.recovery_steps) >= 1


# ─── sovereign_execute decorator ─────────────────────────────────────────────


class TestSovereignExecute:
    @pytest.mark.asyncio
    async def test_happy_path_passthrough(self):
        """No error → result returned unmodified."""
        expected = AgentResult(action_id="a1", success=True, output="ok")

        @sovereign_execute()
        async def my_fn(action: AgentAction) -> AgentResult:
            return expected

        action = AgentAction(action_id="a1", action_type="store")
        result = await my_fn(action)
        assert result.success
        assert result.latency_ms > 0  # timestamp was set

    @pytest.mark.asyncio
    async def test_schema_error_triggers_l4_fallback(self):
        """SchemaIncompatibilityError → retried in text-only mode → L4 result."""
        call_count = 0

        @sovereign_execute(fallback_mode="text_only")
        async def my_fn(action: AgentAction) -> AgentResult:
            nonlocal call_count
            call_count += 1
            if action.requires_tools:
                raise SchemaIncompatibilityError(
                    model="gpt-120b", required_schema="function_calling_v2"
                )
            # text-only fallback succeeds
            return AgentResult(action_id=action.action_id, success=True, output="text_mode")

        action = AgentAction(action_id="a2", action_type="search", requires_tools=True)
        result = await my_fn(action)

        assert result.success
        assert result.output == "text_mode"
        assert result.is_degraded  # warning was appended
        assert call_count == 2  # first call failed, second succeeded

    @pytest.mark.asyncio
    async def test_schema_error_no_fallback_reraises(self):
        """If action already has requires_tools=False, cannot degrade further → AgentDegradedError."""

        @sovereign_execute(fallback_mode="text_only")
        async def my_fn(action: AgentAction) -> AgentResult:
            raise SchemaIncompatibilityError(model="gpt-120b", required_schema="fc_v2")

        action = AgentAction(action_id="a3", action_type="search", requires_tools=False)
        with pytest.raises(AgentDegradedError):
            await my_fn(action)

    @pytest.mark.asyncio
    async def test_sovereign_error_reraises_with_logging(self):
        """SovereignAgentError (non-schema) → logged and re-raised as-is."""

        @sovereign_execute()
        async def my_fn(action: AgentAction) -> AgentResult:
            raise ModelUnavailableError(model="x", reason="rate limit")

        action = AgentAction(action_id="a4", action_type="recall")
        with pytest.raises(ModelUnavailableError):
            await my_fn(action)

    @pytest.mark.asyncio
    async def test_unknown_error_upgraded_to_l3(self):
        """Raw Exception → upgraded to AgentDegradedError (L0→L3 Ω₅ principle)."""

        @sovereign_execute()
        async def my_fn(action: AgentAction) -> AgentResult:
            raise RuntimeError("Something totally unexpected")

        action = AgentAction(action_id="a5", action_type="store")
        with pytest.raises(AgentDegradedError) as exc_info:
            await my_fn(action)

        assert exc_info.value.level == DegradationLevel.L3_ACTIONABLE
        assert isinstance(exc_info.value.cause, RuntimeError)

    @pytest.mark.asyncio
    async def test_cortex_persistence_called_on_error(self):
        """If cortex_engine is provided, errors are persisted."""
        engine = MagicMock()
        engine.store = AsyncMock()

        @sovereign_execute(cortex_engine=engine, project="test_proj")
        async def my_fn(action: AgentAction) -> AgentResult:
            raise ModelUnavailableError(model="x", reason="down")

        action = AgentAction(action_id="a6", action_type="store")
        with pytest.raises(ModelUnavailableError):
            await my_fn(action)

        engine.store.assert_called_once()
        call_kwargs = engine.store.call_args.kwargs
        assert call_kwargs["project"] == "test_proj"
        assert call_kwargs["fact_type"] == "error"

    @pytest.mark.asyncio
    async def test_persistence_failure_does_not_compound(self):
        """A failing CORTEX persistence must NOT mask the original error."""
        engine = MagicMock()
        engine.store = AsyncMock(side_effect=ConnectionError("CORTEX down"))

        @sovereign_execute(cortex_engine=engine)
        async def my_fn(action: AgentAction) -> AgentResult:
            raise ToolRegistrationError(tool_name="filesystem")

        action = AgentAction(action_id="a7", action_type="tool_call")
        # Must raise the original ToolRegistrationError, not ConnectionError
        with pytest.raises(ToolRegistrationError):
            await my_fn(action)
