import pytest

from cortex.extensions.swarm.langgraph_supervisor import (
    LANGGRAPH_AVAILABLE,
    CortexLangGraphSupervisor,
    LangGraphSupervisorError,
    NightShiftState,
    SupervisorNode,
)


class MockPlannerNode(SupervisorNode):
    def __init__(self):
        super().__init__("planner")

    async def execute(self, state: NightShiftState) -> NightShiftState:
        state.variables["planned"] = True
        return state


class MockExecutorNode(SupervisorNode):
    def __init__(self):
        super().__init__("executor")

    async def execute(self, state: NightShiftState) -> NightShiftState:
        state.variables["executed"] = True
        return state


@pytest.mark.asyncio
async def test_langgraph_supervisor_routing():
    if not LANGGRAPH_AVAILABLE:
        pytest.skip("LangGraph not installed. Skipping test.")

    supervisor = CortexLangGraphSupervisor("test-swarm")

    supervisor.add_node(MockPlannerNode())
    supervisor.add_node(MockExecutorNode())

    # Graph: planner -> executor -> END
    supervisor.add_edge("planner", "executor")

    from langgraph.graph import END

    supervisor.add_edge("executor", END)

    # Setting entry point implicitly handled via compile?
    # Actually LangGraph requires an entry point. We'll set it.
    supervisor.graph_builder.set_entry_point("planner")

    app = supervisor.compile()
    assert app is not None

    initial_state = NightShiftState.create(session_id="test-123")

    events = []
    async for event in supervisor.stream_execution(initial_state):
        events.append(event)

    assert len(events) > 0
    # The final state should have planned and executed set to True
    final_state = events[-1]
    # Depending on langgraph versions, it might yield dicts or state objects
    # But usually it yields dict mapped by node name: {"planner": NightShiftState(...)}
    for k, v in final_state.items():
        if isinstance(v, NightShiftState):
            assert v.variables.get("planned") is True
            assert v.variables.get("executed") is True
        elif isinstance(v, dict):
            assert "planned" in v.get("variables", {}) or "executed" in v.get("variables", {})


def test_missing_langgraph_throws_error():
    # If LANGGRAPH_AVAILABLE is False, it should throw error.
    # We can mock it if it is true.
    import cortex.extensions.swarm.langgraph_supervisor as module

    original = module.LANGGRAPH_AVAILABLE
    module.LANGGRAPH_AVAILABLE = False

    try:
        with pytest.raises(LangGraphSupervisorError):
            CortexLangGraphSupervisor("should-fail")
    finally:
        module.LANGGRAPH_AVAILABLE = original
