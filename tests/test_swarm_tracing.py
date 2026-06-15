import asyncio
import pytest
from cortex.swarm.runtime import AgentRegistry, SubagentRunner, SubagentRequest, AgentCapability

class MockHandler:
    async def run(self, req: SubagentRequest) -> str:
        return f"mock_output_for_{req.task_id}"

@pytest.mark.asyncio
async def test_swarm_traceable_execution_graph():
    registry = AgentRegistry()
    registry.register(AgentCapability(name="test_agent", kinds=["reason"]))

    audit_log = []
    async def mock_audit_callback(data: dict) -> None:
        audit_log.append(data)

    runner = SubagentRunner(registry, audit_callback=mock_audit_callback)
    runner.register_handler("test_agent", MockHandler())

    req = SubagentRequest(task_id="trace-123", kind="reason")
    res = await runner.invoke_subagent(req)

    assert res.ok is True
    assert res.output == "mock_output_for_trace-123"

    # Verify OpenTelemetry and Ledger mappings
    assert len(audit_log) == 2
    assert audit_log[0]["action"] == "SWARM_DISPATCH"
    assert audit_log[0]["status"] == "PENDING"
    assert audit_log[0]["task_id"] == "trace-123"
    
    assert audit_log[1]["action"] == "SWARM_DISPATCH"
    assert audit_log[1]["status"] == "SUCCESS"
    assert audit_log[1]["task_id"] == "trace-123"

@pytest.mark.asyncio
async def test_swarm_traceable_graph_error():
    registry = AgentRegistry()
    registry.register(AgentCapability(name="missing_agent", kinds=["reason"]))
    
    audit_log = []
    async def mock_audit_callback(data: dict) -> None:
        audit_log.append(data)

    runner = SubagentRunner(registry, audit_callback=mock_audit_callback)
    # No handler registered for missing_agent

    req = SubagentRequest(task_id="err-123", kind="reason")
    res = await runner.invoke_subagent(req)

    assert res.ok is False
    assert len(audit_log) == 2
    assert audit_log[1]["status"] == "ERROR"
