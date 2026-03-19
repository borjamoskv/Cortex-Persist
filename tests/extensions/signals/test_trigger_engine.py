# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""Tests for the TriggerEngine — declarative conditions system.

Coverage:
- Condition registration and matching
- EventHorizonPriority lanes (P0, P1, P2)
- Accumulator logic (threshold + window)
- Cooldown enforcement
- Action dispatch and handler protocol
- TriggerRegistry default triggers
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from cortex.extensions.signals.models import Signal
from cortex.extensions.signals.trigger_engine import (
    ActionType,
    EventHorizonPriority,
    TriggerAction,
    TriggerActionHandler,
    TriggerCondition,
    TriggerEngine,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_signal(
    event_type: str = "test:event",
    payload: dict[str, Any] | None = None,
    source: str = "test",
    project: str = "TEST",
) -> Signal:
    """Build a minimal Signal for testing."""
    return Signal(
        id=1,
        event_type=event_type,
        payload=payload or {},
        source=source,
        project=project,
        created_at=datetime.now(),
        consumed_by=[],
    )


def _make_condition(
    trigger_id: str = "test_trigger",
    name: str = "Test Trigger",
    event_types: list[str] | None = None,
    priority: EventHorizonPriority = EventHorizonPriority.P2_KINETIC,
    predicate: Any = None,
    accumulator_threshold: int = 1,
    accumulator_window_s: float = 60.0,
    cooldown_s: float = 0.0,
    actions: list[TriggerAction] | None = None,
) -> TriggerCondition:
    kwargs: dict[str, Any] = {
        "id": trigger_id,
        "name": name,
        "priority": priority,
        "event_types": event_types or ["test:event"],
        "accumulator_threshold": accumulator_threshold,
        "accumulator_window_s": accumulator_window_s,
        "cooldown_s": cooldown_s,
        "actions": actions
        or [
            TriggerAction(
                action_type=ActionType.EMIT_SIGNAL,
                config={"event_type": "triggered:test"},
            )
        ],
    }
    if predicate is not None:
        kwargs["predicate"] = predicate
    return TriggerCondition(**kwargs)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_register_single_condition(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition())
        assert len(engine._triggers) == 1

    def test_register_multiple_conditions(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(trigger_id="a"))
        engine.register(_make_condition(trigger_id="b"))
        assert len(engine._triggers) == 2

    def test_duplicate_id_overwrites(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(trigger_id="x", event_types=["a:*"]))
        engine.register(_make_condition(trigger_id="x", event_types=["b:*"]))
        assert len(engine._triggers) == 1
        assert engine._triggers["x"].event_types == ["b:*"]

    def test_unregister(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(trigger_id="rm"))
        assert engine.unregister("rm") is True
        assert engine.unregister("rm") is False
        assert len(engine._triggers) == 0

    def test_list_triggers(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(trigger_id="a"))
        engine.register(_make_condition(trigger_id="b"))
        listed = engine.list_triggers()
        assert len(listed) == 2


# ---------------------------------------------------------------------------
# Event matching
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestEventMatching:
    async def test_exact_match(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(event_types=["node:dead"]))
        signal = _fake_signal(event_type="node:dead")
        results = await engine.evaluate(signal)
        assert any(r.fired for r in results)

    async def test_wildcard_match(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(event_types=["node:*"]))
        signal = _fake_signal(event_type="node:dead")
        results = await engine.evaluate(signal)
        assert any(r.fired for r in results)

    async def test_no_match(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(event_types=["other:event"]))
        signal = _fake_signal(event_type="node:dead")
        results = await engine.evaluate(signal)
        assert len(results) == 0

    async def test_multi_pattern(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(event_types=["a:*", "b:exact"]))
        r1 = await engine.evaluate(_fake_signal(event_type="a:foo"))
        r2 = await engine.evaluate(_fake_signal(event_type="b:exact"))
        assert any(r.fired for r in r1)
        assert any(r.fired for r in r2)


# ---------------------------------------------------------------------------
# Predicates
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPredicates:
    async def test_predicate_passes(self) -> None:
        engine = TriggerEngine()
        engine.register(
            _make_condition(
                predicate=lambda s: s.source == "important",
            )
        )
        signal = _fake_signal(source="important")
        results = await engine.evaluate(signal)
        assert any(r.fired for r in results)

    async def test_predicate_blocks(self) -> None:
        engine = TriggerEngine()
        engine.register(
            _make_condition(
                predicate=lambda s: s.source == "important",
            )
        )
        signal = _fake_signal(source="boring")
        results = await engine.evaluate(signal)
        assert len(results) == 0

    async def test_default_predicate_allows_all(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition())
        results = await engine.evaluate(_fake_signal())
        assert any(r.fired for r in results)


# ---------------------------------------------------------------------------
# Priority
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestPriority:
    async def test_p0_fires_immediately(self) -> None:
        engine = TriggerEngine()
        engine.register(
            _make_condition(
                priority=EventHorizonPriority.P0_SINGULARITY,
                accumulator_threshold=1,
            )
        )
        results = await engine.evaluate(_fake_signal())
        assert any(r.fired for r in results)

    async def test_p1_fires_on_threshold(self) -> None:
        engine = TriggerEngine()
        engine.register(
            _make_condition(
                priority=EventHorizonPriority.P1_STRUCTURAL,
                accumulator_threshold=2,
            )
        )
        r1 = await engine.evaluate(_fake_signal())
        assert not any(r.fired for r in r1)
        r2 = await engine.evaluate(_fake_signal())
        assert any(r.fired for r in r2)


# ---------------------------------------------------------------------------
# Accumulator
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestAccumulator:
    async def test_threshold_not_met(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(accumulator_threshold=3))
        await engine.evaluate(_fake_signal())
        results = await engine.evaluate(_fake_signal())
        assert not any(r.fired for r in results)

    async def test_threshold_met(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(accumulator_threshold=3))
        await engine.evaluate(_fake_signal())
        await engine.evaluate(_fake_signal())
        results = await engine.evaluate(_fake_signal())
        assert any(r.fired for r in results)

    async def test_accumulator_resets_after_fire(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(accumulator_threshold=2))
        await engine.evaluate(_fake_signal())
        await engine.evaluate(_fake_signal())  # fires
        # Should need 2 more to fire again
        results = await engine.evaluate(_fake_signal())
        assert not any(r.fired for r in results)

    async def test_window_expiry(self) -> None:
        """Old events outside the window are pruned."""
        engine = TriggerEngine()
        engine.register(
            _make_condition(
                accumulator_threshold=3,
                accumulator_window_s=0.1,
            )
        )
        await engine.evaluate(_fake_signal())
        await engine.evaluate(_fake_signal())
        time.sleep(0.15)
        results = await engine.evaluate(_fake_signal())
        # Only 1 in window, threshold=3 not met
        assert not any(r.fired for r in results)


# ---------------------------------------------------------------------------
# Cooldown
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestCooldown:
    async def test_cooldown_suppresses_refire(self) -> None:
        engine = TriggerEngine()
        engine.register(
            _make_condition(
                cooldown_s=1.0,
                accumulator_threshold=1,
            )
        )
        r1 = await engine.evaluate(_fake_signal())
        assert any(r.fired for r in r1)
        r2 = await engine.evaluate(_fake_signal())
        assert not any(r.fired for r in r2)

    async def test_cooldown_expires(self) -> None:
        engine = TriggerEngine()
        engine.register(
            _make_condition(
                cooldown_s=0.1,
                accumulator_threshold=1,
            )
        )
        await engine.evaluate(_fake_signal())
        time.sleep(0.15)
        results = await engine.evaluate(_fake_signal())
        assert any(r.fired for r in results)


# ---------------------------------------------------------------------------
# Action dispatch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestActionDispatch:
    async def test_emit_signal_action(self) -> None:
        handler = TriggerActionHandler()
        handler.emit_signal = AsyncMock()
        engine = TriggerEngine(handler=handler)
        engine.register(
            _make_condition(
                actions=[
                    TriggerAction(
                        action_type=ActionType.EMIT_SIGNAL,
                        config={"event_type": "test:output"},
                    )
                ],
            )
        )
        await engine.evaluate(_fake_signal())
        handler.emit_signal.assert_called_once()

    async def test_multiple_actions(self) -> None:
        handler = TriggerActionHandler()
        handler.emit_signal = AsyncMock()
        handler.notify = AsyncMock()
        engine = TriggerEngine(handler=handler)
        engine.register(
            _make_condition(
                actions=[
                    TriggerAction(
                        action_type=ActionType.EMIT_SIGNAL,
                        config={"event_type": "a"},
                    ),
                    TriggerAction(
                        action_type=ActionType.NOTIFY,
                        config={"title": "alert"},
                    ),
                ],
            )
        )
        await engine.evaluate(_fake_signal())
        handler.emit_signal.assert_called_once()
        handler.notify.assert_called_once()

    async def test_store_fact_action(self) -> None:
        handler = TriggerActionHandler()
        handler.store_fact = AsyncMock()
        engine = TriggerEngine(handler=handler)
        engine.register(
            _make_condition(
                actions=[
                    TriggerAction(
                        action_type=ActionType.STORE_FACT,
                        config={
                            "content": "ghost detected",
                            "fact_type": "ghost",
                        },
                    )
                ],
            )
        )
        await engine.evaluate(_fake_signal())
        handler.store_fact.assert_called_once()


# ---------------------------------------------------------------------------
# Registry integration
# ---------------------------------------------------------------------------


class TestRegistry:
    def test_register_defaults_populates_engine(self) -> None:
        from cortex.extensions.signals.trigger_registry import (
            register_defaults,
        )

        engine = TriggerEngine()
        register_defaults(engine)
        assert len(engine._triggers) == 8

    def test_default_ids_are_unique(self) -> None:
        from cortex.extensions.signals.trigger_registry import (
            register_defaults,
        )

        engine = TriggerEngine()
        register_defaults(engine)
        ids = list(engine._triggers.keys())
        assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# Stats / introspection
# ---------------------------------------------------------------------------


class TestStats:
    def test_stats_returns_trigger_info(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(trigger_id="alpha"))
        engine.register(_make_condition(trigger_id="beta"))
        stats = engine.stats()
        assert stats["registered_triggers"] == 2
        assert "alpha" in stats["triggers"]
        assert "beta" in stats["triggers"]

    def test_reset_clears_all(self) -> None:
        engine = TriggerEngine()
        engine.register(_make_condition(trigger_id="x"))
        engine.reset()
        assert len(engine._triggers) == 0

    def test_disabled_trigger_skipped(self) -> None:
        engine = TriggerEngine()
        cond = _make_condition()
        cond.enabled = False
        engine.register(cond)
        # Stats still show it
        assert engine.stats()["registered_triggers"] == 1
