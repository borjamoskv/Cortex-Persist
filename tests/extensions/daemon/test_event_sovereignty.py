import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from cortex.engine.event_sovereignty import EventSovereigntyRuntime

@pytest.mark.asyncio
async def test_event_sovereignty_runtime_telemetry():
    # Mock EventBus
    mock_bus = MagicMock()
    mock_bus.subscribe = MagicMock()
    mock_bus.publish = AsyncMock()
    
    # Mock AnomalyBridge
    mock_bridge = MagicMock()
    mock_bridge.detect_anomaly = AsyncMock(return_value=True) # Force anomaly
    
    # Mock AuthGateway
    mock_auth = MagicMock()
    mock_auth.request_override = AsyncMock()
    
    runtime = EventSovereigntyRuntime(event_bus=mock_bus, anomaly_bridge=mock_bridge, auth_gateway=mock_auth)
    await runtime.start()
    
    # Verify subscriptions
    mock_bus.subscribe.assert_any_call("system.telemetry", runtime._handle_telemetry_event)
    mock_bus.subscribe.assert_any_call("system.alert", runtime._handle_alert_event)
    
    # Simulate an event
    await runtime._handle_telemetry_event({"cpu_usage": 99.9})
    
    # Verify anomaly bridge was called
    mock_bridge.detect_anomaly.assert_called_once()
    
    # Verify auth gateway requested override due to anomaly
    mock_auth.request_override.assert_called_once()
    
    await runtime.stop()

@pytest.mark.asyncio
async def test_auth_gateway_override():
    from cortex.engine.auth_gateway import QuorumGateway
    
    mock_engine = MagicMock()
    mock_pool = MagicMock()
    mock_conn = MagicMock()
    mock_engine.pool.get_connection.return_value = mock_conn
    
    gw = QuorumGateway(mock_engine, n_nodes=1, f_nodes=0)
    req_id = await gw.request_override("Test hypothesis", {"state": "critical"})
    
    assert req_id.startswith("QRM-")
    mock_conn.execute.assert_called()
    mock_conn.commit.assert_called()
