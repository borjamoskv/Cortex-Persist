import pytest
from uuid import uuid4

from cortex.agents.builtins.reddit_agent import RedditAgent
from cortex.agents.manifest import AgentManifest
from cortex.agents.message_schema import AgentMessage, MessageKind

class MockBus:
    def __init__(self):
        self.messages = []
        
    async def send(self, message: AgentMessage):
        self.messages.append(message)

class MockToolExecutor:
    async def execute(self, tool_name: str, arguments: dict):
        return {"status": "success", "tool_called": tool_name}

@pytest.mark.asyncio
async def test_reddit_agent_tool_activation():
    """
    Verifies that the objective "reddit_post" successfully routes 
    to the reddit_publish_promotion tool and fires a verification request.
    """
    bus = MockBus()
    executor = MockToolExecutor()
    
    manifest = AgentManifest(agent_id="reddit-agent", purpose="Promoter")
    agent = RedditAgent(manifest=manifest, bus=bus, tool_executor=executor)
    
    msg = AgentMessage(
        correlation_id=str(uuid4()),
        causation_id=str(uuid4()),
        sender="user",
        recipient="reddit-agent",
        kind=MessageKind.TASK_REQUEST,
        payload={
            "task_id": "1234",
            "objective": "Execute a reddit_post about CORTEX",
            "input": {
                "subreddit": "LocalLLaMA",
                "title": "CORTEX Launch"
            }
        }
    )
    
    await agent.handle_message(msg)
    
    # Expecting 2 messages: TASK_ACCEPTED, then VERIFICATION_REQUEST
    assert len(bus.messages) == 2, f"Expected 2 messages, got {len(bus.messages)}"
    
    assert bus.messages[0].kind == MessageKind.TASK_ACCEPTED
    assert bus.messages[1].kind == MessageKind.VERIFICATION_REQUEST
    
    verif_payload = bus.messages[1].payload
    assert verif_payload["candidate"]["tool_name"] == "reddit_publish_promotion"
    assert verif_payload["candidate"]["result"]["tool_called"] == "reddit_publish_promotion"
