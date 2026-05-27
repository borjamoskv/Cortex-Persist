import pytest

llama_index = pytest.importorskip("llama_index")
from unittest.mock import MagicMock
from llama_index.core.callbacks.schema import CBEventType
from cortex.engine.sync_mixin import CortexSyncEngine
from cortex.extensions.llamaindex_bridge import CortexIndexCallback


def test_cortex_index_callback_retrieve():
    engine_mock = MagicMock(spec=CortexSyncEngine)
    agent_id = "test-agent-123"

    callback = CortexIndexCallback(engine=engine_mock, agent_id=agent_id)

    # Mock payload with nodes
    class MockNode:
        def __init__(self, node_id):
            self.node_id = node_id

    class MockNodeWithScore:
        def __init__(self, node):
            self.node = node

    nodes = [
        MockNodeWithScore(MockNode("node-1")),
        MockNodeWithScore(MockNode("node-2")),
    ]

    payload = {"nodes": nodes}

    # Trigger event
    callback.on_event_end(event_type=CBEventType.RETRIEVE, payload=payload)

    # Verify engine store_fact called correctly
    engine_mock.store_fact.assert_called_once_with(
        agent_id=agent_id,
        content="RETRIEVAL_EVENT: Fetched 2 nodes",
        metadata={"nodes": ["node-1", "node-2"], "event": "rag_retrieve"},
    )


def test_cortex_index_callback_other_event():
    engine_mock = MagicMock(spec=CortexSyncEngine)
    callback = CortexIndexCallback(engine=engine_mock, agent_id="agent")

    callback.on_event_end(event_type=CBEventType.LLM, payload={})

    # Verify engine store_fact NOT called
    engine_mock.store_fact.assert_not_called()
