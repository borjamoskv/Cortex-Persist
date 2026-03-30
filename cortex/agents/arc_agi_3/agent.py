import logging
from typing import Any

from cortex.agents.arc_agi_3.reasoning import ArcReasoningEngine

logger = logging.getLogger("cortex.agents.arc_agi_3")


class ARCAgent:
    """
    Sovereign ARC-AGI Agent (AX-043, AX-044).
    Uses JIT Concept Formation (AX-046) to solve grid transformation tasks.
    """

    def __init__(self) -> None:
        self.reasoning = ArcReasoningEngine()

    async def run(self, input_data: dict[str, Any]) -> list[list[int]]:
        """
        Executes the agentic workflow for a single ARC-AGI task.
        """
        program = await self.induce(input_data)
        
        # Ensure test_input exists
        test_input = input_data.get("test", [{}])[0].get("input", [])
        if not test_input:
            logger.warning("Empty test input provided to ARCAgent.")
            return []

        # JIT Execution (restricted)
        exec_globals: dict[str, Any] = {"__builtins__": {}}
        try:
            exec(program.source_code, exec_globals)
            transform_fn = exec_globals.get("transform")
            if callable(transform_fn):
                return transform_fn(test_input)
        except Exception as e:
            logger.error("Failed to execute synthesized program: %s", e)

        return test_input

    async def induce(self, input_data: dict[str, Any]) -> Any:
        """
        Induces a program for the given task data. Returns a PeARLProgram.
        """
        train_examples = input_data.get("train", [])
        if not train_examples:
            logger.warning("No training examples provided for induction.")
            from cortex.agents.arc_agi_3.reasoning import PeARLProgram
            return PeARLProgram("def transform(grid):\n    return grid", 0.0)

        # Use the reasoning engine to search for the best program
        return await self.reasoning.search_engine.search(train_examples)


if __name__ == "__main__":
    import argparse
    import json
    import asyncio

    async def main():
        parser = argparse.ArgumentParser(description="ARC-AGI-3 Sovereign Solver CLI.")
        parser.add_argument("--task", type=str, required=True, help="Path to ARC task JSON.")
        args = parser.parse_args()

        with open(args.task, "r") as f:
            task_data = json.load(f)

        agent = ARCAgent()
        result = await agent.run(task_data)
        print(f"\nFinal Result: {json.dumps(result)}")

    asyncio.run(main())
