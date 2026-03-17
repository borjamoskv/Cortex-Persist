"""CORTEX — Default Trigger Registry.

Factory functions that register the 8 default CORTEX trigger conditions
into a TriggerEngine instance. These map the Event Horizon Triggers
from GEMINI.md §5 to automated CORTEX responses.

Usage::

    from cortex.extensions.signals.trigger_engine import TriggerEngine
    from cortex.extensions.signals.trigger_registry import register_defaults

    engine = TriggerEngine(handler=my_handler)
    register_defaults(engine)
"""

from __future__ import annotations

import logging

from cortex.extensions.signals.trigger_engine import (
    ActionType,
    EventHorizonPriority,
    TriggerAction,
    TriggerCondition,
    TriggerEngine,
)

__all__ = ["register_defaults"]

logger = logging.getLogger("cortex.extensions.signals.trigger_registry")


def register_defaults(engine: TriggerEngine) -> None:
    """Register all default CORTEX trigger conditions."""
    _register_p0_triggers(engine)
    _register_p1_triggers(engine)
    _register_p2_triggers(engine)
    count = len(engine.list_triggers())
    logger.info("Trigger registry: %d default triggers registered", count)


# ═════════════════════════════════════════════════════════════════════════
#  P0 — Singularity (Immediate, Cono de Luz)
# ═════════════════════════════════════════════════════════════════════════


def _register_p0_triggers(engine: TriggerEngine) -> None:
    """P0 triggers fire immediately on a single signal match."""

    # Worktree isolation failure — critical infrastructure collapse
    engine.register(
        TriggerCondition(
            id="worktree_isolation_failed",
            name="Worktree Isolation Failure",
            priority=EventHorizonPriority.P0_SINGULARITY,
            event_types=["worktree:isolation_failed"],
            accumulator_threshold=1,
            cooldown_s=0.0,
            actions=[
                TriggerAction(
                    action_type=ActionType.NOTIFY,
                    config={
                        "title": "💀 Worktree Isolation Failed",
                        "body": "Critical: Git worktree creation failed. Agent isolation compromised.",
                        "severity": "critical",
                    },
                ),
                TriggerAction(
                    action_type=ActionType.STORE_FACT,
                    config={
                        "content": ("Worktree isolation failure detected — infra_ghost"),
                        "fact_type": "ghost",
                        "confidence": "C5-Static",
                        "meta": {"sub_type": "infra_ghost"},
                    },
                ),
            ],
            source_module="cortex.extensions.swarm.worktree_isolation",
        )
    )

    # Node death — swarm node stopped pulsing
    engine.register(
        TriggerCondition(
            id="node_dead",
            name="Swarm Node Dead",
            priority=EventHorizonPriority.P0_SINGULARITY,
            event_types=["node:dead"],
            accumulator_threshold=1,
            cooldown_s=0.0,
            actions=[
                TriggerAction(
                    action_type=ActionType.NOTIFY,
                    config={
                        "title": "💀 Swarm Node Dead",
                        "body": "A swarm daemon node has stopped responding.",
                        "severity": "critical",
                    },
                ),
                TriggerAction(
                    action_type=ActionType.ESCALATE,
                    config={
                        "reason": "Swarm node declared DEAD after consecutive heartbeat misses",
                        "agent_id": "swarm_heartbeat",
                    },
                ),
            ],
            source_module="cortex.extensions.swarm.swarm_heartbeat",
        )
    )

    # Circuit breaker open — telemetry gate tripped
    engine.register(
        TriggerCondition(
            id="circuit_open",
            name="Circuit Breaker Open",
            priority=EventHorizonPriority.P0_SINGULARITY,
            event_types=["circuit:open"],
            accumulator_threshold=1,
            cooldown_s=30.0,
            actions=[
                TriggerAction(
                    action_type=ActionType.NOTIFY,
                    config={
                        "title": "🔌 Circuit Breaker Open",
                        "body": "A telemetry gate tripped its circuit breaker.",
                        "severity": "error",
                    },
                ),
                TriggerAction(
                    action_type=ActionType.ESCALATE,
                    config={
                        "reason": "Circuit breaker tripped — consecutive quality gate failures",
                        "agent_id": "telemetry_gate",
                    },
                ),
            ],
            source_module="cortex.extensions.swarm.telemetry_gate",
        )
    )


# ═════════════════════════════════════════════════════════════════════════
#  P1 — Structural (Block Checkpoint, Geodésica)
# ═════════════════════════════════════════════════════════════════════════


def _register_p1_triggers(engine: TriggerEngine) -> None:
    """P1 triggers fire at block checkpoints with moderate cooldown."""

    # Node suspect — early warning
    engine.register(
        TriggerCondition(
            id="node_suspect",
            name="Swarm Node Suspect",
            priority=EventHorizonPriority.P1_STRUCTURAL,
            event_types=["node:suspect"],
            accumulator_threshold=1,
            cooldown_s=60.0,
            actions=[
                TriggerAction(
                    action_type=ActionType.STORE_FACT,
                    config={
                        "content": "Swarm node entered SUSPECT state — potential silent death",
                        "fact_type": "ghost",
                        "confidence": "C3",
                        "meta": {"sub_type": "infra_ghost"},
                    },
                ),
            ],
            source_module="cortex.extensions.swarm.swarm_heartbeat",
        )
    )

    # Byzantine consensus failure
    engine.register(
        TriggerCondition(
            id="consensus_failed",
            name="Byzantine Consensus Failure",
            priority=EventHorizonPriority.P1_STRUCTURAL,
            event_types=["consensus:failed"],
            accumulator_threshold=1,
            cooldown_s=60.0,
            actions=[
                TriggerAction(
                    action_type=ActionType.STORE_FACT,
                    config={
                        "content": "Byzantine consensus failed — swarm fracture detected",
                        "fact_type": "ghost",
                        "confidence": "C4",
                        "meta": {"sub_type": "system_bridge"},
                    },
                ),
                TriggerAction(
                    action_type=ActionType.NOTIFY,
                    config={
                        "title": "⚠️ Byzantine Consensus Failure",
                        "body": "Swarm nodes failed to reach 2/3 weighted consensus.",
                        "severity": "warning",
                    },
                ),
            ],
            source_module="cortex.extensions.swarm.byzantine",
        )
    )

    # Worktree residue — zombie worktree detected after cleanup
    engine.register(
        TriggerCondition(
            id="worktree_residue",
            name="Worktree Residue Detected",
            priority=EventHorizonPriority.P1_STRUCTURAL,
            event_types=["worktree:residue_detected"],
            accumulator_threshold=1,
            cooldown_s=120.0,
            actions=[
                TriggerAction(
                    action_type=ActionType.STORE_FACT,
                    config={
                        "content": "Worktree cleanup failed — residual filesystem artifact",
                        "fact_type": "ghost",
                        "confidence": "C5-Static",
                        "meta": {"sub_type": "infra_ghost"},
                    },
                ),
            ],
            source_module="cortex.extensions.swarm.worktree_isolation",
        )
    )


# ═════════════════════════════════════════════════════════════════════════
#  P2 — Kinetic (Accumulator ≥ N)
# ═════════════════════════════════════════════════════════════════════════


def _register_p2_triggers(engine: TriggerEngine) -> None:
    """P2 triggers require accumulation before firing."""

    # Compact auto-trigger (replaces hardcoded logic in fact_hook.py)
    engine.register(
        TriggerCondition(
            id="compact_auto_trigger",
            name="Compaction Auto-Trigger",
            priority=EventHorizonPriority.P2_KINETIC,
            event_types=["fact:stored"],
            accumulator_threshold=50,
            accumulator_window_s=3600.0,
            cooldown_s=300.0,
            actions=[
                TriggerAction(
                    action_type=ActionType.EMIT_SIGNAL,
                    config={
                        "event_type": "compact:needed",
                        "payload": {"reason": "P2 kinetic trigger: 50 facts stored in 1h window"},
                        "source": "trigger:compact_auto",
                    },
                ),
            ],
            source_module="cortex.extensions.signals.fact_hook",
        )
    )

    # Ghost accumulation — multiple ghosts discovered → memory bridge
    engine.register(
        TriggerCondition(
            id="ghost_accumulation",
            name="Ghost Accumulation Alert",
            priority=EventHorizonPriority.P2_KINETIC,
            event_types=["ghost:discovered", "ghost:detected"],
            accumulator_threshold=3,
            accumulator_window_s=600.0,
            cooldown_s=300.0,
            actions=[
                TriggerAction(
                    action_type=ActionType.STORE_FACT,
                    config={
                        "content": "Ghost accumulation threshold reached — systemic entropy rising",
                        "fact_type": "bridge",
                        "confidence": "C4",
                        "meta": {"sub_type": "memory_bridge"},
                    },
                ),
                TriggerAction(
                    action_type=ActionType.NOTIFY,
                    config={
                        "title": "👻 Ghost Accumulation",
                        "body": "3+ ghosts detected in 10min window. Systemic entropy alert.",
                        "severity": "warning",
                    },
                ),
            ],
            source_module="cortex.extensions.swarm.error_ghost_pipeline",
        )
    )
