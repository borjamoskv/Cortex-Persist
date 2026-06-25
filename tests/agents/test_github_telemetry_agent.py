# [C5-REAL] Exergy-Maximized
# Author: Borja Moskv (borjamoskv)
"""Tests for GithubTelemetryAgent."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from legacy_research.agents.builtins.github_telemetry_agent import GithubTelemetryAgent
from legacy_research.agents.bus import SqliteMessageBus
from legacy_research.agents.manifest import AgentManifest
from legacy_research.agents.message_schema import MessageKind, new_message
from legacy_research.telemetry.metrics import metrics


def _uid() -> str:
    return f"file:mem_{uuid.uuid4().hex[:8]}?mode=memory&cache=shared"


def _manifest(
    agent_id: str = "test-github-telemetry",
    daemon: bool = False,
    escalation_targets: list[str] | None = None,
) -> AgentManifest:
    return AgentManifest(
        agent_id=agent_id,
        purpose="test-telemetry",
        tools_allowed=[],
        daemon=daemon,
        escalation_targets=escalation_targets or [],
    )


async def _drain(bus: SqliteMessageBus, recipient: str, max_n: int = 10) -> list[Any]:
    msgs = []
    for _ in range(max_n):
        m = await bus.receive(recipient, timeout=0.05)
        if m is None:
            break
        msgs.append(m)
    return msgs


@pytest.mark.asyncio
async def test_mock_fallback_no_token():
    """Verify mock data is collected and recorded when GITHUB_TOKEN is not configured."""
    bus = SqliteMessageBus(db_path=_uid())
    try:
        metrics.reset()
        agent = GithubTelemetryAgent(
            manifest=_manifest(),
            bus=bus,
            token="",
            owner="borjamoskv",
            repos=["test-repo"],
        )

        stats = await agent.harvest_telemetry()
        assert stats["prs_active"] == 3
        assert stats["additions"] == 1450
        assert stats["deletions"] == 420

        # Check metrics registry values
        assert metrics._gauges.get("cortex_github_active_prs{owner=\"borjamoskv\"}") == 3.0
        assert metrics._gauges.get("cortex_github_pr_additions{owner=\"borjamoskv\"}") == 1450.0
    finally:
        await bus.close()


@pytest.mark.asyncio
async def test_api_polling_with_mock_http():
    """Verify HTTP requests are executed and telemetry processed with a token."""
    bus = SqliteMessageBus(db_path=_uid())
    try:
        metrics.reset()
        agent = GithubTelemetryAgent(
            manifest=_manifest(),
            bus=bus,
            token="valid-token",
            owner="borjamoskv",
            repos=["test-repo"],
        )

        # Mock responses
        prs_payload = [
            {"number": 10, "url": "https://api.github.com/repos/borjamoskv/test-repo/pulls/10"}
        ]
        pr_details = {"number": 10, "additions": 45, "deletions": 12}
        workflow_payload = {
            "workflow_runs": [
                {"conclusion": "success", "run_duration_ms": 12000},
                {"conclusion": "failure", "run_duration_ms": 15000},
            ]
        }

        def handler(request: httpx.Request) -> httpx.Response:
            path = request.url.path
            if "pulls/10" in path:
                return httpx.Response(200, json=pr_details)
            elif "pulls" in path:
                return httpx.Response(200, json=prs_payload)
            elif "actions/runs" in path:
                return httpx.Response(200, json=workflow_payload)
            return httpx.Response(404, json={})

        agent._client = httpx.AsyncClient(transport=httpx.MockTransport(handler))

        stats = await agent.harvest_telemetry()
        assert stats["prs_active"] == 1
        assert stats["additions"] == 45
        assert stats["deletions"] == 12
        assert stats["workflow_runs_total"] == 2
        assert stats["workflow_failures"] == 1
        assert stats["duration_p95_sec"] == 15.0

        await agent._client.aclose()
    finally:
        await bus.close()


@pytest.mark.asyncio
async def test_task_request_harvest():
    """Verify the agent responds to a collect/harvest TASK_REQUEST message."""
    bus = SqliteMessageBus(db_path=_uid())
    try:
        metrics.reset()
        agent = GithubTelemetryAgent(
            manifest=_manifest("telemetry-agent"),
            bus=bus,
            token="",
        )

        # Send TASK_REQUEST
        await bus.send(
            new_message(
                "caller",
                "telemetry-agent",
                MessageKind.TASK_REQUEST,
                {"op": "collect"},
            )
        )
        await bus.send(new_message("caller", "telemetry-agent", MessageKind.SHUTDOWN, {}))

        await agent.run()

        replies = await _drain(bus, "caller")
        task_results = [r for r in replies if r.kind == MessageKind.TASK_RESULT]
        assert len(task_results) == 1
        payload = task_results[0].payload
        assert payload.get("result", {}).get("status") == "success"
        stats = payload.get("result", {}).get("stats", {})
        assert stats.get("prs_active") == 3
    finally:
        await bus.close()


@pytest.mark.asyncio
async def test_store_telemetry_batch_fact():
    """Verify telemetry_batch facts are stored in the CORTEX engine."""
    bus = SqliteMessageBus(db_path=_uid())
    try:
        mock_engine = MagicMock()
        mock_engine.store = AsyncMock(return_value=999)

        agent = GithubTelemetryAgent(
            manifest=_manifest(),
            bus=bus,
            token="",
            engine=mock_engine,
        )

        await agent.harvest_telemetry()

        # Check engine store was called with fact_type="telemetry_batch"
        mock_engine.store.assert_called_once()
        kwargs = mock_engine.store.call_args[1]
        assert kwargs.get("fact_type") == "telemetry_batch"
        assert kwargs.get("project") == "github-telemetry"
        assert "github_telemetry" in kwargs.get("meta", {})
    finally:
        await bus.close()
