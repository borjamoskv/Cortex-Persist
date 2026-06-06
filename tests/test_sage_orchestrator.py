# [C5-REAL] Exergy-Maximized
"""Tests for cortex-core/sage_orchestrator.py - SAGE Council Telemetry.

C5-REAL coverage for Orchestrator events and sage invocation.
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cortex-core"))

import sage_orchestrator


class TestSageOrchestrator:
    @pytest.fixture
    def orchestrator(self):
        orc = sage_orchestrator.SageOrchestrator(target_dir="/tmp/fake_targets")
        orc.engine = None
        return orc

    @pytest.mark.asyncio
    async def test_broadcast_event(self, orchestrator):
        await orchestrator.broadcast("test_event", {"key": "value"})
        event = await orchestrator.event_queue.get()
        assert event["type"] == "test_event"
        assert event["data"] == {"key": "value"}
        assert event["global_yield"] == 12700000000.0

    @pytest.mark.asyncio
    async def test_log_creates_broadcast(self, orchestrator):
        orchestrator.log("Testing log", sage="TEST-SAGE")
        await asyncio.sleep(0.01)  # allow task to run
        event = await orchestrator.event_queue.get()
        assert event["type"] == "log"
        assert event["data"]["msg"] == "Testing log"
        assert event["data"]["sage"] == "TEST-SAGE"

    @pytest.mark.asyncio
    async def test_invoke_sage_silent_mode(self, orchestrator):
        real_sleep = asyncio.sleep
        # Without QWEN_API_KEY
        with patch.dict("os.environ", clear=True):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await orchestrator.invoke_sage("ULTRA-THINK", "/fake/target")
                await real_sleep(0.01)

                # Retrieve the log events
                events = []
                while not orchestrator.event_queue.empty():
                    events.append(await orchestrator.event_queue.get())

                msgs = [e["data"]["msg"] for e in events]
                assert any("Adversarial Dream" in m for m in msgs)
                assert any("SILENT_MODE" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_invoke_sage_frontier_mode(self, orchestrator):
        real_sleep = asyncio.sleep
        # With QWEN_API_KEY
        with patch.dict("os.environ", {"QWEN_API_KEY": "fake_key"}):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await orchestrator.invoke_sage("DEEP-ORACLE", "/fake/target")
                await real_sleep(0.01)

                events = []
                while not orchestrator.event_queue.empty():
                    events.append(await orchestrator.event_queue.get())

                msgs = [e["data"]["msg"] for e in events]
                assert any("Frontier Reasoning active" in m for m in msgs)

    @pytest.mark.asyncio
    async def test_invoke_sage_critical_finding(self, orchestrator):
        orchestrator.cycle_count = 3  # Triggers critical finding condition for ULTRA-THINK
        with patch.dict("os.environ", clear=True):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                await orchestrator.invoke_sage("ULTRA-THINK", "/fake/target")
                assert orchestrator.global_yield == 12700000000.0 + 25000.0
