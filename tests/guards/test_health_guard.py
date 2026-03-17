"""Tests for HealthGuard and HealthSLA."""

import pytest

from cortex.guards.health_guard import HealthGuard
from cortex.extensions.health.models import Grade, HealthScore, HealthSLA, HealthSLAViolation


def test_health_sla_evaluate_passes() -> None:
    sla = HealthSLA(target_grade=Grade.DEGRADED)
    score = HealthScore(score=60.0, grade=Grade.ACCEPTABLE)

    # Should not raise
    sla.evaluate(score)


def test_health_sla_evaluate_fails() -> None:
    sla = HealthSLA(target_grade=Grade.ACCEPTABLE)
    score = HealthScore(score=30.0, grade=Grade.FAILED)

    with pytest.raises(HealthSLAViolation) as exc:
        sla.evaluate(score)

    assert "Health SLA Violation" in str(exc.value)
    assert exc.value.score == score
    assert exc.value.target == Grade.ACCEPTABLE


def test_health_sla_sub_indices_enforcement() -> None:
    sla = HealthSLA(target_grade=Grade.ACCEPTABLE, enforce_sub_indices=True)

    # Overall score is functional, but storage is failed
    score = HealthScore(
        score=60.0,
        grade=Grade.ACCEPTABLE,
        metrics=[],
        sub_indices={"storage": 35.0, "integrity": 90.0},
    )

    with pytest.raises(HealthSLAViolation) as exc:
        sla.evaluate(score)

    assert "Health SLA Violation" in str(exc.value)


@pytest.mark.asyncio
async def test_health_guard_passes_when_healthy(monkeypatch) -> None:
    guard = HealthGuard("/tmp/fake_healthy.db")

    async def mock_health_score():
        return HealthScore(score=99.0, grade=Grade.SOVEREIGN)

    monkeypatch.setattr(guard, "health_score", mock_health_score)

    # Should not raise
    await guard.check_write_safety()


@pytest.mark.asyncio
async def test_health_guard_fails_when_unhealthy(monkeypatch) -> None:
    guard = HealthGuard("/tmp/fake.db")

    async def mock_health_score():
        return HealthScore(score=10.0, grade=Grade.FAILED)

    monkeypatch.setattr(guard, "health_score", mock_health_score)

    with pytest.raises(HealthSLAViolation):
        await guard.check_write_safety()
