import logging
from typing import Any

from .dsl import (
    flip_node_h,
    flip_node_v,
    get_largest,
    move_node,
    recolor_node,
    rotate_node_90,
    select_by_color,
    select_by_size,
)
from .ingestion import detect_global_gestalt, extract_objects, reconstruct_grid

logger = logging.getLogger("cortex.agents.fuckchatgpt.actuator")


class ArcActuator:
    """
    The Sovereign Loop: Ingest -> Plan (LLM) -> Execute (DSL) -> Verify (Taint).
    """

    def __init__(self, model_client: Any = None):
        self.model_client = model_client

    async def solve_task(
        self, training_pairs: list[dict[str, Any]], test_input: list[list[int]]
    ) -> list[list[int]]:
        """
        Orchestrates the program synthesis loop.
        """
        # 1. Ingest training pairs
        ingested_train = []
        for pair in training_pairs:
            gestalt = detect_global_gestalt(pair['input'])
            nodes = extract_objects(pair['input'], gestalt['background'])
            ingested_train.append({
                'input_nodes': nodes,
                'input_gestalt': gestalt,
                'output_grid': pair['output']
            })

        # 2. Generate Program Synthesis Prompt
        prompt = self._build_prompt(ingested_train)

        # 3. Call LLM to synthesize solve() function
        logger.info("Starting program synthesis via LLM...")
        program_code = await self._synthesize_program(prompt)

        # 4. Verify program on training pairs
        success = self._verify_program(program_code, ingested_train)

        if not success:
            logger.warning("Initial program failed verification. Falling back to identity.")
            # In a real scenario, we'd include error feedback and loop.

        # 5. Apply to test input
        test_gestalt = detect_global_gestalt(test_input)
        test_nodes = extract_objects(test_input, test_gestalt['background'])
        result_grid = self._execute_program(program_code, test_nodes, test_gestalt)

        return result_grid

    def _build_prompt(self, ingested_train: list[dict]) -> str:
        """Constructs the prompt for program synthesis."""
        # Simple placeholder for now.
        # Future: Detailed node descriptions and DSL documentation.
        return f"Solve ARC task. Pairs: {len(ingested_train)}. Use move_node, recolor_node, etc."

    async def _synthesize_program(self, prompt: str) -> str:
        """
        Dummy implementation. In production, this would call
        Gemini 3 Deep Think or GPT-4o.
        """
        # Return a sample program that just returns the input nodes (identity)
        return """
def solve(nodes, gestalt):
    return nodes
"""

    def _verify_program(self, code: str, train_data: list[dict]) -> bool:
        for item in train_data:
            predicted = self._execute_program(code, item['input_nodes'], item['input_gestalt'])
            if predicted != item['output_grid']:
                return False
        return True

    def _execute_program(self, code: str, nodes: list, gestalt: dict) -> list[list[int]]:
        """Safely executes the synthesized program within the DSL namespace."""
        namespace = {
            'move_node': move_node,
            'recolor_node': recolor_node,
            'rotate_node_90': rotate_node_90,
            'flip_node_h': flip_node_h,
            'flip_node_v': flip_node_v,
            'select_by_color': select_by_color,
            'select_by_size': select_by_size,
            'get_largest': get_largest,
            'reconstruct_grid': reconstruct_grid
        }
        try:
            # Clean up the code block (remove markdown artifacts)
            clean_code = code.strip().replace("```python", "").replace("```", "")
            exec(clean_code, {}, namespace)
            if 'solve' in namespace:
                result = namespace['solve'](nodes, gestalt)
                if isinstance(result, list) and len(result) > 0 and hasattr(result[0], 'pixels'):
                    return reconstruct_grid(
                        result, gestalt['rows'], gestalt['cols'], gestalt['background']
                    )
                return result
        except Exception as e:
            logger.error("Execution failed: %s", e)

        # Fallback to reconstructing input grid
        return reconstruct_grid(nodes, gestalt['rows'], gestalt['cols'], gestalt['background'])
