from __future__ import annotations

import logging
from typing import Any

from cortex.extensions.llm.router import CortexLLMRouter, CortexPrompt, IntentProfile
from cortex.utils.result import Result

logger = logging.getLogger("cortex.engine.llm_bridge")

PEARL_INDUCTION_PROMPT = """
You are the CORTEX PeARL Inducer (AX-046). Your mission is to synthesize a Python program 
using the PeARL (Physical Abstraction & Reasoning Logic) primitives to solve grid-based 
spatial reasoning tasks (like ARC-AGI).

### PeARL Primitives available in the environment:
- `move(grid, dx, dy)`: Translates all non-zero pixels.
- `rotate(grid, k)`: Rotates 90*k degrees.
- `flip(grid, axis)`: Flips 0 (h) or 1 (v).
- `crop(grid, x, y, w, h)`: Extracts subgrid.
- `fill(grid, color)`: Sets all cells to color.
- `get_objects(grid)`: Returns list of connected components.
- `find_color(grid, color)`: Boolean check.

### Constraints:
1. Output ONLY the Python code block.
2. No explanations, no markdown (except the code block).
3. The input grid is available as `input_grid`.
4. Define the final answer as a variable named `output`.
5. You can use standard Python loops, indexing, and list comprehensions.

### Task Description:
{description}

### Examples (Input -> Output Grids):
{examples}

Synthesize the minimal, most exergy-efficient PeARL program.
"""


class LLMBridge:
    """
    Sovereign bridge between stochastic LLM proposals and deterministic PeARL execution.
    Implements JIT Concept Formation (AX-046).
    """

    def __init__(self, router: CortexLLMRouter):
        self.router = router

    async def induce_program(self, description: str, examples: list[dict[str, Any]]) -> Result[str, str]:
        """
        Queries a frontier model to induce a PeARL program from examples.
        """
        formatted_prompt = PEARL_INDUCTION_PROMPT.format(
            description=description,
            examples=str(examples),
        )

        prompt = CortexPrompt(
            system_instruction="You help CORTEX synthesize programs.",
            working_memory=[{"role": "user", "content": formatted_prompt}],
            intent=IntentProfile(tier="frontier", cost="high"),
            project="CORTEX-JIT-INDUCTION",
        )

        logger.info("📡 [BRIDGE] Requesting JIT induction for: %s", description[:50])
        return await self.router.invoke(prompt)
