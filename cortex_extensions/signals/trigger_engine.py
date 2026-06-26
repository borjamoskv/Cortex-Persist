# [C5-REAL] Exergy-Maximized
"""CORTEX - Declarative Trigger Engine (Event Horizon Triggers).

Evaluates composable trigger conditions against the SignalBus stream.
Maps GEMINI.md §5 Event Horizon Triggers to automated responses with
three priority lanes: P0 (Singularity), P1 (Structural), P2 (Kinetic).

Architecture:
    SignalBus (L1) → TriggerEngine.evaluate() → Action Dispatch → Reactor (L2)

The engine is thread-safe for cross-daemon usage and uses in-memory
accumulators with TTL-based window expiry.
"""

from __future__ import annotations

import fnmatch
import logging
import threading
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from cortex_extensions.signals.models import Signal

__all__ = [
    "ActionType",
    "EventHorizonPriority",
    "TriggerAction",
    "TriggerCondition",
    "TriggerEngine",
    "TriggerResult",
]

logger = logging.getLogger("cortex_extensions.signals.trigger_engine")


# ═════════════════════════════════════════════════════════════════════════
#  Enums
# ═════════════════════════════════════════════════════════════════════════


class EventHorizonPriority(str, Enum):
    """Maps to GEMINI.md §5 Event Horizon Triggers.

    P0 - Singularity: Immediate. Prod breakage, data loss, security risk.
    P1 - Structural:  Block checkpoint. Failed assumption, paradigm shift.
    P2 - Kinetic:     Accumulator ≥ threshold. Pattern, ghost, bridge.
    """

    P0_SINGULARITY = "P0"
    P1_STRUCTURAL = "P1"
    P2_KINETIC = "P2"


class ActionType(str, Enum):
    """What to do when a trigger fires."""

    EMIT_SIGNAL = "emit_signal"
    STORE_FACT = "store_fact"
    ESCALATE = "escalate"
    NOTIFY = "notify"
    CUSTOM = "custom"


# ═════════════════════════════════════════════════════════════════════════
#  Data Models
# ═════════════════════════════════════════════════════════════════════════


@dataclass
class TriggerAction:
    """Single action to execute when a trigger fires."""

    action_type: ActionType
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class TriggerCondition:
    """Declarative trigger rule.

    Attributes:
        id:                     Unique identifier.
        name:                   Human-readable name.
        priority:               Event Horizon priority lane (P0/P1/P2).
        event_types:            Signal event_type patterns (glob, e.g. "worktree:*").
        predicate:              Fine-grained payload filter. Receives the Signal,
                                returns True if the signal qualifies.
        accumulator_threshold:  How many qualifying signals before firing (P2 uses >1).
        accumulator_window_s:   Time window in seconds for accumulation.
        cooldown_s:             Min seconds between consecutive firings.
        actions:                Ordered action chain to execute on fire.
        source_module:          Which subsystem registered this trigger.
        enabled:                Master switch.
    """

    id: str
    name: str
    priority: EventHorizonPriority
    event_types: list[str]
    predicate: Callable[[Signal], bool] = field(default=lambda _s: True)
    accumulator_threshold: int = 1
    accumulator_window_s: float = 300.0
    cooldown_s: float = 0.0
    actions: list[TriggerAction] = field(default_factory=list)
    source_module: str = ""
    enabled: bool = True


@dataclass
class TriggerResult:
    """Outcome of a single trigger evaluation."""

    trigger_id: str
    trigger_name: str
    priority: EventHorizonPriority
    fired: bool
    actions_dispatched: int = 0
    accumulator_count: int = 0
    cooldown_remaining_s: float = 0.0


# ═════════════════════════════════════════════════════════════════════════
#  Accumulator Entry
# ═════════════════════════════════════════════════════════════════════════


@dataclass
class _AccumulatorEntry:
    """In-memory accumulator state for a single trigger."""

    timestamps: list[float] = field(default_factory=list)
    last_fired: float = 0.0


# ═════════════════════════════════════════════════════════════════════════
#  Action Handler Protocol
# ═════════════════════════════════════════════════════════════════════════


class TriggerActionHandler:
    """Base protocol for action dispatch.

    Subclass or duck-type to inject real CORTEX subsystems (bus, engine, notifier).
    """

    async def emit_signal(self, event_type: str, payload: dict, **kw: Any) -> None:
        """Emit a signal into the SignalBus."""
        logger.info("ACTION emit_signal: %s %s", event_type, payload)

    async def store_fact(self, content: str, **kw: Any) -> None:
        """Store a fact in CORTEX memory."""
        logger.info("ACTION store_fact: %s", content[:120])

    async def escalate(self, reason: str, **kw: Any) -> None:
        """Trigger human escalation."""
        logger.warning("ACTION escalate: %s", reason)

    async def notify(self, title: str, body: str, severity: str = "warning", **kw: Any) -> None:
        """Emit a CortexEvent notification."""
        logger.info("ACTION notify [%s]: %s", severity, title)

    async def custom(self, handler_name: str, **kw: Any) -> None:
        """Execute a custom handler by name."""
        logger.info("ACTION custom: %s", handler_name)


# ═════════════════════════════════════════════════════════════════════════
#  TriggerEngine
# ═════════════════════════════════════════════════════════════════════════


class TriggerEngine:
    """Declarative trigger condition evaluator.

    Thread-safe. Evaluates registered TriggerConditions against incoming
    Signals and dispatches actions when conditions are met.

    Usage::

        engine = TriggerEngine(handler=my_handler)
        engine.register(my_trigger_condition)
        results = await engine.evaluate(signal)
    """

    def __init__(self, handler: TriggerActionHandler | None = None) -> None:
        self._lock = threading.Lock()
        self._triggers: dict[str, TriggerCondition] = {}
        self._accumulators: dict[str, _AccumulatorEntry] = defaultdict(_AccumulatorEntry)
        self._handler = handler or TriggerActionHandler()
        self._exact_routes: dict[str, list[TriggerCondition]] = defaultdict(list)
        self._wildcard_routes: list[tuple[str, TriggerCondition]] = []

    def _rebuild_routing_indexes(self) -> None:
        """Rebuild exact and wildcard matching indexes for fast routing.

        Must be called under self._lock.
        """
        self._exact_routes = defaultdict(list)
        self._wildcard_routes = []
        for trigger in self._triggers.values():
            for pattern in trigger.event_types:
                if any(char in pattern for char in "*?["):
                    self._wildcard_routes.append((pattern, trigger))
                else:
                    self._exact_routes[pattern].append(trigger)

    # ── Registration ───────────────────────────────────────────────

    def register(self, trigger: TriggerCondition) -> None:
        """Register a trigger condition. Overwrites if id already exists."""
        with self._lock:
            self._triggers[trigger.id] = trigger
            self._rebuild_routing_indexes()
        logger.info(
            "Trigger registered: [%s] %s (priority=%s, threshold=%d)",
            trigger.id,
            trigger.name,
            trigger.priority.value,
            trigger.accumulator_threshold,
        )

    def unregister(self, trigger_id: str) -> bool:
        """Remove a trigger by id. Returns True if found."""
        with self._lock:
            removed = self._triggers.pop(trigger_id, None) is not None
            self._accumulators.pop(trigger_id, None)
            if removed:
                self._rebuild_routing_indexes()
        return removed

    def list_triggers(self) -> list[TriggerCondition]:
        """Snapshot of all registered triggers."""
        with self._lock:
            return list(self._triggers.values())

    # ── Evaluation ─────────────────────────────────────────────────

    async def evaluate(self, signal: Signal) -> list[TriggerResult]:
        """Evaluate all registered triggers against a signal.

        Returns list of TriggerResults (one per matching trigger).
        Only triggers whose event_type pattern matches are evaluated.
        """
        results: list[TriggerResult] = []
        now = time.monotonic()

        with self._lock:
            # 1. Gather matching triggers preserving original insertion order
            matched: dict[str, TriggerCondition] = {}

            # Exact match lookup
            for trigger in self._exact_routes.get(signal.event_type, []):
                matched[trigger.id] = trigger

            # Wildcard match lookup
            for pattern, trigger in self._wildcard_routes:
                if fnmatch.fnmatch(signal.event_type, pattern):
                    matched[trigger.id] = trigger

            # Preserve registration order (order of keys in self._triggers)
            trigger_ids_order = {tid: idx for idx, tid in enumerate(self._triggers.keys())}
            triggers = sorted(matched.values(), key=lambda t: trigger_ids_order[t.id])

        for trigger in triggers:
            if not trigger.enabled:
                continue

            # Predicate evaluation (fine-grained payload filter)
            try:
                if not trigger.predicate(signal):
                    continue
            except Exception:
                logger.debug(
                    "Predicate failed for trigger %s on signal %s",
                    trigger.id,
                    signal.event_type,
                )
                continue

            result = await self._evaluate_trigger(trigger, signal, now)
            results.append(result)

        return results

    async def _evaluate_trigger(
        self, trigger: TriggerCondition, signal: Signal, now: float
    ) -> TriggerResult:
        """Evaluate a single trigger against a signal."""
        with self._lock:
            acc = self._accumulators[trigger.id]

            # Prune expired timestamps from accumulator window
            cutoff = now - trigger.accumulator_window_s
            acc.timestamps = [t for t in acc.timestamps if t > cutoff]

            # Record this signal
            acc.timestamps.append(now)
            current_count = len(acc.timestamps)

            # Check accumulator threshold
            if current_count < trigger.accumulator_threshold:
                return TriggerResult(
                    trigger_id=trigger.id,
                    trigger_name=trigger.name,
                    priority=trigger.priority,
                    fired=False,
                    accumulator_count=current_count,
                )

            # Check cooldown
            elapsed_since_last = now - acc.last_fired
            if trigger.cooldown_s > 0 and elapsed_since_last < trigger.cooldown_s:
                remaining = trigger.cooldown_s - elapsed_since_last
                return TriggerResult(
                    trigger_id=trigger.id,
                    trigger_name=trigger.name,
                    priority=trigger.priority,
                    fired=False,
                    accumulator_count=current_count,
                    cooldown_remaining_s=remaining,
                )

            # FIRE - reset accumulator and record fire time
            acc.timestamps.clear()
            acc.last_fired = now

        # Dispatch actions (outside lock)
        dispatched = await self._dispatch_actions(trigger, signal)

        logger.info(
            "🔥 TRIGGER FIRED [%s] %s (priority=%s, dispatched=%d)",
            trigger.id,
            trigger.name,
            trigger.priority.value,
            dispatched,
        )

        return TriggerResult(
            trigger_id=trigger.id,
            trigger_name=trigger.name,
            priority=trigger.priority,
            fired=True,
            actions_dispatched=dispatched,
            accumulator_count=0,
        )

    # ── Action Dispatch ────────────────────────────────────────────

    async def _dispatch_actions(self, trigger: TriggerCondition, signal: Signal) -> int:
        """Execute all actions for a fired trigger. Returns count dispatched."""
        dispatched = 0
        for action in trigger.actions:
            try:
                await self._dispatch_single(action, trigger, signal)
                dispatched += 1
            except Exception as e:
                logger.error(
                    "Action dispatch failed for trigger %s, action %s: %s",
                    trigger.id,
                    action.action_type.value,
                    e,
                )
        return dispatched

    async def _dispatch_single(
        self, action: TriggerAction, trigger: TriggerCondition, signal: Signal
    ) -> None:
        """Route a single action to the handler."""
        cfg = action.config
        ctx = {
            "trigger_id": trigger.id,
            "trigger_name": trigger.name,
            "priority": trigger.priority.value,
            "signal_event_type": signal.event_type,
            "signal_source": signal.source,
            "signal_id": signal.id,
        }

        if action.action_type == ActionType.EMIT_SIGNAL:
            await self._handler.emit_signal(
                event_type=cfg.get("event_type", f"trigger:{trigger.id}"),
                payload={**cfg.get("payload", {}), **ctx},
                source=cfg.get("source", f"trigger:{trigger.id}"),
                project=cfg.get("project", signal.project),
            )

        elif action.action_type == ActionType.STORE_FACT:
            await self._handler.store_fact(
                content=cfg.get("content", f"Trigger fired: {trigger.name}"),
                fact_type=cfg.get("fact_type", "ghost"),
                confidence=cfg.get("confidence", "C4"),
                source=cfg.get("source", f"trigger:{trigger.id}"),
                project=cfg.get("project", signal.project or "SYSTEM"),
                meta={**cfg.get("meta", {}), **ctx},
            )

        elif action.action_type == ActionType.ESCALATE:
            await self._handler.escalate(
                reason=cfg.get("reason", f"Trigger {trigger.name} fired"),
                agent_id=cfg.get("agent_id", "trigger_engine"),
                **ctx,
            )

        elif action.action_type == ActionType.NOTIFY:
            await self._handler.notify(
                title=cfg.get("title", f"🔥 {trigger.name}"),
                body=cfg.get("body", f"Trigger {trigger.id} fired on {signal.event_type}"),
                severity=cfg.get("severity", "warning"),
                **ctx,
            )

        elif action.action_type == ActionType.CUSTOM:
            await self._handler.custom(
                handler_name=cfg.get("handler_name", trigger.id),
                **{**cfg, **ctx},
            )

    # ── Helpers ────────────────────────────────────────────────────

    @staticmethod
    def _event_matches(event_type: str, patterns: list[str]) -> bool:
        """Check if event_type matches any of the glob patterns."""
        return any(fnmatch.fnmatch(event_type, p) for p in patterns)

    def reset(self) -> None:
        """Clear all triggers and accumulators. For testing."""
        with self._lock:
            self._triggers.clear()
            self._accumulators.clear()

    def stats(self) -> dict[str, Any]:
        """Diagnostic snapshot."""
        with self._lock:
            return {
                "registered_triggers": len(self._triggers),
                "active_accumulators": sum(1 for a in self._accumulators.values() if a.timestamps),
                "triggers": {
                    t.id: {
                        "name": t.name,
                        "priority": t.priority.value,
                        "enabled": t.enabled,
                        "accumulator_count": len(
                            self._accumulators.get(t.id, _AccumulatorEntry()).timestamps
                        ),
                    }
                    for t in self._triggers.values()
                },
            }
