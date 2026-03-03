"""Tests for HeartbeatEmitter ↔ SleepOrchestrator integration.

Pure unit tests — no I/O, no DB. All dependencies are mocked.
Validates idle detection, cooldown, Nexus signaling, and failure resilience.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cortex.engine.heartbeat import HeartbeatEmitter
from cortex.memory.sleep import SleepCycleReport
from cortex.nexus.types import IntentType


# ─── Fixtures ──────────────────────────────────────────────────────────


def _make_report(**overrides) -> SleepCycleReport:
    """Build a SleepCycleReport with sane defaults."""
    defaults = {
        "tenant_id": "test-project",
        "started_at": 1000.0,
        "ended_at": 1002.0,
        "nrem_merged": 3,
        "nrem_reinforced": 5,
        "nrem_conflicts": 0,
        "nrem_pruned": 1,
        "nrem_duration_ms": 800.0,
        "rem_clusters_found": 2,
        "rem_bridges_created": 1,
        "rem_engrams_reweighted": 4,
        "rem_duration_ms": 400.0,
        "brier_before": 0.30,
        "brier_after": 0.22,
        "fok_threshold_before": 0.30,
        "fok_threshold_after": 0.28,
        "threshold_adjusted": True,
    }
    defaults.update(overrides)
    return SleepCycleReport(**defaults)


@pytest.fixture()
def nexus():
    mock = AsyncMock()
    mock.mutate = AsyncMock(return_value=True)
    return mock


@pytest.fixture()
def engine():
    return MagicMock()


@pytest.fixture()
def sleep_orch():
    mock = AsyncMock()
    mock.run_full_cycle = AsyncMock(return_value=_make_report())
    return mock


@pytest.fixture()
def health_data():
    return {"status": "ok", "cpu": 12.0, "orphans": 0}


# ─── Tests ─────────────────────────────────────────────────────────────


class TestIdleDetection:
    """Idle timer triggers sleep when system is quiet."""

    @pytest.mark.asyncio()
    async def test_idle_triggers_sleep(self, nexus, engine, sleep_orch, health_data):
        """After idle_threshold_s of zero drift, sleep fires."""
        emitter = HeartbeatEmitter(
            nexus,
            engine,
            "test-project",
            sleep=sleep_orch,
            idle_threshold_s=60.0,
            sleep_cooldown_s=0.0,  # no cooldown for this test
        )

        with patch("cortex.engine.heartbeat.hygiene.check_system_health", return_value=health_data):
            # First pulse — establishes baseline, drift = 0
            await emitter.pulse()

            # Simulate idle by pushing _last_activity_at back
            emitter._last_activity_at -= 120.0  # 2 minutes idle

            # Second pulse — should trigger sleep
            await emitter.pulse()

        sleep_orch.run_full_cycle.assert_awaited_once_with("test-project")

    @pytest.mark.asyncio()
    async def test_no_sleep_when_active(self, nexus, engine, sleep_orch):
        """Non-zero drift resets idle timer — no sleep."""
        emitter = HeartbeatEmitter(
            nexus,
            engine,
            "test-project",
            sleep=sleep_orch,
            idle_threshold_s=60.0,
            sleep_cooldown_s=0.0,
        )

        # Alternate health data to produce non-zero drift
        health_states = [
            {"status": "ok", "cpu": 10.0, "orphans": 0},
            {"status": "ok", "cpu": 80.0, "orphans": 1},  # different → drift > 0
        ]

        with patch("cortex.engine.heartbeat.hygiene.check_system_health", side_effect=health_states):
            await emitter.pulse()
            await emitter.pulse()  # drift > 0 → resets idle

        sleep_orch.run_full_cycle.assert_not_awaited()


class TestCooldown:
    """Cooldown prevents rapid re-triggering of sleep cycles."""

    @pytest.mark.asyncio()
    async def test_cooldown_prevents_double_sleep(self, nexus, engine, sleep_orch, health_data):
        """Second idle window within cooldown does NOT trigger sleep."""
        emitter = HeartbeatEmitter(
            nexus,
            engine,
            "test-project",
            sleep=sleep_orch,
            idle_threshold_s=10.0,
            sleep_cooldown_s=3600.0,  # 1 hour cooldown
        )

        with patch("cortex.engine.heartbeat.hygiene.check_system_health", return_value=health_data):
            # Force idle
            emitter._last_activity_at -= 120.0
            await emitter.pulse()  # triggers sleep

            # Force idle again immediately
            emitter._last_activity_at -= 120.0
            await emitter.pulse()  # should NOT trigger (cooldown)

        # Only one call
        assert sleep_orch.run_full_cycle.await_count == 1


class TestGracefulDegradation:
    """HeartbeatEmitter works fine without a SleepOrchestrator."""

    @pytest.mark.asyncio()
    async def test_no_sleep_without_orchestrator(self, nexus, engine, health_data):
        """When sleep=None, pulse() operates exactly as before."""
        emitter = HeartbeatEmitter(nexus, engine, "test-project")  # no sleep

        with patch("cortex.engine.heartbeat.hygiene.check_system_health", return_value=health_data):
            emitter._last_activity_at -= 9999.0  # deeply idle
            result = await emitter.pulse()

        assert result is True
        # Only HEARTBEAT_PULSE mutation, no SLEEP_CYCLE_TRIGGERED
        assert nexus.mutate.await_count == 1
        call_args = nexus.mutate.await_args[0][0]
        assert call_args.intent == IntentType.HEARTBEAT_PULSE

    @pytest.mark.asyncio()
    async def test_sleep_failure_does_not_crash(self, nexus, engine, health_data):
        """Exception in run_full_cycle is caught — heartbeat continues."""
        broken_sleep = AsyncMock()
        broken_sleep.run_full_cycle = AsyncMock(side_effect=RuntimeError("NREM exploded"))

        emitter = HeartbeatEmitter(
            nexus,
            engine,
            "test-project",
            sleep=broken_sleep,
            idle_threshold_s=10.0,
            sleep_cooldown_s=0.0,
        )

        with patch("cortex.engine.heartbeat.hygiene.check_system_health", return_value=health_data):
            emitter._last_activity_at -= 120.0
            # Should NOT raise
            result = await emitter.pulse()

        assert result is True
        # HEARTBEAT_PULSE still emitted, no SLEEP_CYCLE_TRIGGERED
        assert nexus.mutate.await_count == 1


class TestNexusSignaling:
    """Sleep cycle emits SLEEP_CYCLE_TRIGGERED mutation to Nexus."""

    @pytest.mark.asyncio()
    async def test_nexus_mutation_emitted(self, nexus, engine, sleep_orch, health_data):
        """After sleep, SLEEP_CYCLE_TRIGGERED is emitted with report stats."""
        emitter = HeartbeatEmitter(
            nexus,
            engine,
            "test-project",
            sleep=sleep_orch,
            idle_threshold_s=10.0,
            sleep_cooldown_s=0.0,
        )

        with patch("cortex.engine.heartbeat.hygiene.check_system_health", return_value=health_data):
            emitter._last_activity_at -= 120.0
            await emitter.pulse()

        # Two mutations: SLEEP_CYCLE_TRIGGERED first (from _maybe_trigger_sleep),
        # then HEARTBEAT_PULSE (from pulse() itself)
        assert nexus.mutate.await_count == 2

        # Find the sleep mutation
        mutations = [call[0][0] for call in nexus.mutate.call_args_list]
        sleep_mutations = [m for m in mutations if m.intent == IntentType.SLEEP_CYCLE_TRIGGERED]
        assert len(sleep_mutations) == 1

        payload = sleep_mutations[0].payload
        assert payload["nrem_merged"] == 3
        assert payload["rem_bridges"] == 1
        assert payload["brier_before"] == 0.30
        assert payload["brier_after"] == 0.22
        assert payload["fok_adjusted"] is True
        assert "idle_seconds" in payload
        assert "total_duration_ms" in payload
