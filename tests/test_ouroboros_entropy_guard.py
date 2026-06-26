# [C5-REAL] Exergy-Maximized
"""
Tests for OuroborosEntropyGuard - loops and task density verification.
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

import pytest

from cortex.guards.ouroboros_entropy_guard import OuroborosEntropyGuard


@pytest.mark.asyncio
async def test_ouroboros_entropy_guard_normal():
    """Verify normal content and tasks do not raise."""
    guard = OuroborosEntropyGuard()
    # Content has enough entropy and no task duplication
    content = "Unique content describing a new plan for the cognitive swarm with high entropy details."
    await guard.check(
        content=content,
        project="test",
        fact_type="task",
        meta={},
        conn=MagicMock(),
    )


@pytest.mark.asyncio
async def test_ouroboros_entropy_guard_task_limit():
    """Verify exceeding max tasks raises ValueError."""
    guard = OuroborosEntropyGuard(max_tasks=5)

    # Spawn 10 dummy tasks in active event loop
    tasks = [asyncio.create_task(asyncio.sleep(0.5)) for _ in range(10)]

    try:
        with pytest.raises(ValueError, match="Async task limit exceeded"):
            await guard.check(
                content="Some content",
                project="test",
                fact_type="task",
                meta={},
                conn=MagicMock(),
            )
    finally:
        for t in tasks:
            t.cancel()


@pytest.mark.asyncio
async def test_ouroboros_entropy_guard_repetition():
    """Verify high repetition ratio in task names raises ValueError."""
    guard = OuroborosEntropyGuard(repetition_threshold=0.5)

    # Spawn 6 tasks with identical names to trigger repetition threshold
    tasks = []
    for _ in range(6):
        t = asyncio.create_task(asyncio.sleep(0.5))
        t.set_name("loop_task")
        tasks.append(t)

    try:
        with pytest.raises(ValueError, match="Infinite loop detected in async tasks"):
            await guard.check(
                content="Some content",
                project="test",
                fact_type="task",
                meta={},
                conn=MagicMock(),
            )
    finally:
        for t in tasks:
            t.cancel()


@pytest.mark.asyncio
async def test_ouroboros_entropy_guard_low_entropy():
    """Verify abnormally low Shannon entropy content raises ValueError."""
    guard = OuroborosEntropyGuard()
    low_entropy_content = "a" * 150  # 150 repeating characters = 0 entropy
    
    with pytest.raises(ValueError, match="abnormally low Shannon entropy"):
        await guard.check(
            content=low_entropy_content,
            project="test",
            fact_type="task",
            meta={},
            conn=MagicMock(),
        )
