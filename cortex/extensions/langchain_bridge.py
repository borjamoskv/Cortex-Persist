# [C5-REAL] Exergy-Maximized
import asyncio
import json

from langchain.callbacks.base import AsyncCallbackHandler  # pyright: ignore[reportMissingImports]
from langchain.schema import AgentAction, AgentFinish  # pyright: ignore[reportMissingImports]


class CortexLedgerCallback(AsyncCallbackHandler):
    """
    O(1) Deterministic injection of LangChain agent state into Cortex-Persist.
    Generates C5-REAL cryptographic ledger entries asynchronously to prevent LEGION-10k deadlocks.
    """

    _active_tasks_global = set()

    def __init__(self, engine, agent_id: str):
        self.engine = engine
        self.agent_id = agent_id
        self._tasks = set()

    async def on_agent_action(self, action: AgentAction, **kwargs) -> None:
        # Non-blocking telemetry injection with strong reference protection
        payload = {"log": action.log, "type": "action"}
        task = asyncio.create_task(
            self.engine.store(
                agent_id=self.agent_id,
                content=f"TOOL_CALL: {action.tool} | INPUT: {action.tool_input}",
                metadata=payload,
            )
        )
        self._tasks.add(task)
        CortexLedgerCallback._active_tasks_global.add(task)

        def _on_done(t):
            self._tasks.discard(t)
            CortexLedgerCallback._active_tasks_global.discard(t)

        task.add_done_callback(_on_done)

    async def on_agent_finish(self, finish: AgentFinish, **kwargs) -> None:
        # Serialize return_values efficiently to avoid deserialization bottlenecks
        try:
            return_str = json.dumps(finish.return_values)
        except Exception:
            return_str = str(finish.return_values)

        payload = {"log": finish.log, "type": "finish"}
        task = asyncio.create_task(
            self.engine.store(
                agent_id=self.agent_id, content=f"FINAL_OUTPUT: {return_str}", metadata=payload
            )
        )
        self._tasks.add(task)
        CortexLedgerCallback._active_tasks_global.add(task)

        def _on_done(t):
            self._tasks.discard(t)
            CortexLedgerCallback._active_tasks_global.discard(t)

        task.add_done_callback(_on_done)
