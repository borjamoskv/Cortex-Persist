import pytest
import asyncio
from typing import Any
from cortex.agents.arc_agi_3.agent import ARCAgent
from cortex.agents.arc_agi_3.reasoning import ArcReasoningEngine, PeARLProgram

@pytest.fixture
def arc_agent():
    return ARCAgent()

@pytest.fixture
def reasoning_engine():
    return ArcReasoningEngine()

@pytest.fixture
def demo_task():
    return {
        "train": [
            {
                "input": [[1, 1], [1, 1]],
                "output": [[2, 2], [2, 2]]
            }
        ],
        "test": [
            {
                "input": [[1, 1], [1, 1]]
            }
        ]
    }

def test_agent_initialization(arc_agent):
    assert arc_agent is not None
    assert isinstance(arc_agent.reasoning, ArcReasoningEngine)

@pytest.mark.asyncio
async def test_agent_induce_empty(arc_agent):
    # Should return a default program if no train examples provided
    program = await arc_agent.induce({})
    assert isinstance(program, PeARLProgram)
    assert "def transform" in program.source_code

@pytest.mark.asyncio
async def test_reasoning_engine_search_mock(reasoning_engine, demo_task):
    # Verify search initiates and returns a program
    # Note: This might call LLM if not mocked, but we'll check structure first
    program = await reasoning_engine.search_engine.search(demo_task["train"])
    assert isinstance(program, PeARLProgram)
    assert hasattr(program, "source_code")
    assert hasattr(program, "confidence")

@pytest.mark.asyncio
async def test_agent_run_basic(arc_agent, demo_task):
    # Basic smoke test for agent run
    result = await arc_agent.run(demo_task)
    assert isinstance(result, list)
    assert len(result) > 0
    assert isinstance(result[0], list)
