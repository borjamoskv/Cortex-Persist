# [C5-REAL] Exergy-Maximized
import pytest

llama_index = pytest.importorskip("llama_index")
from unittest.mock import MagicMock
from llama_index.core.callbacks.schema import CBEventType
from legacy_research.engine import CortexEngine
from legacy_research.extensions.llamaindex_bridge import CortexIndexCallback


def test_cortex_index_callback_retrieve():
    engine_mock = MagicMock(spec=CortexEngine)
    agent_id = "test-agent-123"

    callback = CortexIndexCallback(engine=engine_mock, agent_id=agent_id)

    # Mock payload with nodes
    class MockNode:
        def __init__(self, node_id):
            self.node_id = node_id

    class MockNodeWithScore:
        def __init__(self, node, score=0.0):
            self.node = node
            self.score = score

    nodes = [
        MockNodeWithScore(MockNode("node-1"), score=0.5),
        MockNodeWithScore(MockNode("node-2"), score=1.0),
    ]

    payload = {"nodes": nodes}

    # Trigger event
    callback.on_event_end(event_type=CBEventType.RETRIEVE, payload=payload)

    # Verify engine store_sync called correctly
    engine_mock.store_sync.assert_called_once_with(
        fact_type="rag_retrieve",
        content="RETRIEVAL_EVENT: Fetched 2 nodes | Avg Exergy: 0.7500",
        metadata={"nodes": ["node-1", "node-2"], "event": "rag_retrieve", "avg_exergy": 0.75},
        agent_id=agent_id,
    )


def test_cortex_index_callback_other_event():
    engine_mock = MagicMock(spec=CortexEngine)
    callback = CortexIndexCallback(engine=engine_mock, agent_id="agent")

    callback.on_event_end(event_type=CBEventType.LLM, payload={})

    # Verify engine store_sync NOT called
    engine_mock.store_sync.assert_not_called()
