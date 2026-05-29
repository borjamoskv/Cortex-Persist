"""OUROBOROS-COMPILER-Ω — AOT Limerent Agent Compiler.

Transforms high-entropy, low-utility execution graphs (limerent agents)
into deterministic, minimal paths (pure functions).
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from cortex.engine.smte.llm_mutator import LLMMutator
from cortex.engine.smte.weismann_barrier import enforce_weismann_barrier

logger = logging.getLogger("cortex.engine.smte.ouroboros_compiler")


class OuroborosCompiler:
    """AOT Compiler that converts limerent agents into compressed minimal paths."""

    def __init__(self, db_path: str | Path | None = None):
        self.mutator = LLMMutator()
        self._db_path = db_path
        self._engine: Any = None

    def _ensure_engine(self) -> None:
        if self._engine is not None:
            return
        from cortex.cli import get_engine
        from cortex.config import DEFAULT_DB_PATH

        db_val = str(self._db_path) if self._db_path else DEFAULT_DB_PATH
        self._engine = get_engine(db_val)

    def analyze_limerence(self, source_code: str) -> dict[str, Any]:
        """Analyze code for high maintenance cost vs utility.

        Calculates C(entity) via heuristics: LLM network calls and cyclomatic complexity.
        """
        try:
            tree = ast.parse(source_code)
            llm_calls = 0
            complexity = 0

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if node.func.attr in (
                            "complete",
                            "chat",
                            "predict",
                            "generate",
                            "mutate_prompt",
                        ):
                            llm_calls += 1
                elif isinstance(node, (ast.If, ast.For, ast.While)):
                    complexity += 1

            # Formula: Heavy penalty for LLM calls (entropy source), minor for structural branching
            cost = (llm_calls * 10) + complexity
            return {
                "llm_calls": llm_calls,
                "complexity": complexity,
                "maintenance_cost": cost,
                "is_limerent": cost > 15,
            }
        except SyntaxError:
            return {"is_limerent": False, "maintenance_cost": 0}

    async def compile_entity(self, target_file: str | Path) -> bool:
        """Compile an agent into its minimal deterministic path."""
        target_path = Path(target_file).resolve()
        logger.info(f"OuroborosCompiler: Ingesting {target_path.name}")

        if not target_path.exists():
            logger.error("Target file does not exist.")
            return False

        with open(target_path, encoding="utf-8") as f:
            source = f.read()

        analysis = self.analyze_limerence(source)
        if not analysis.get("is_limerent"):
            logger.info("Entity is not limerent (C <= U). No compilation needed.")
            return True

        logger.info(
            f"Limerence detected: Maintenance Cost {analysis['maintenance_cost']}. "
            "Compressing graph..."
        )
        self._ensure_engine()

        # Generate compressed AST representation using LLMMutator
        prompt = (
            "SYSTEM: You are the Ouroboros Compiler. Your objective is AOT structural compression.\n"
            "Eliminate 'limerent' (stochastic, unnecessary LLM) logic and replace it with pure, deterministic paths.\n"
            "Compress the complexity (C) to the absolute minimum required to achieve the utility (U).\n"
            "Return ONLY the pure python code. No markdown formatting, no explanations."
        )

        try:
            compiled_code = await self.mutator.mutate_prompt(prompt, source)

            # Clean formatting
            compiled_code = compiled_code.strip()
            if compiled_code.startswith("```python"):
                compiled_code = compiled_code[9:]
            if compiled_code.startswith("```"):
                compiled_code = compiled_code[3:]
            if compiled_code.endswith("```"):
                compiled_code = compiled_code[:-3]
            compiled_code = compiled_code.strip()

            # Weismann Barrier check before writing
            temp_path = target_path.with_suffix(".ouroboros.tmp")
            with open(temp_path, "w", encoding="utf-8") as f:
                f.write(compiled_code + "\n")

            # Verify the mutation
            if not enforce_weismann_barrier(str(temp_path), None):
                logger.error(
                    "OuroborosCompiler: Weismann barrier rejected the compilation. Syntax/entropy failure."
                )
                temp_path.unlink(missing_ok=True)
                return False

            # Replace the old entity with the compressed minimal path
            temp_path.replace(target_path)
            logger.info(
                f"OuroborosCompiler: Entity {target_path.name} compressed successfully (Exergía Maximizada)."
            )

            # Persist to ledger
            await self._engine.store(
                project="SYSTEM",
                content=f"Ouroboros compiled {target_path.name}. Cost reduced from {analysis['maintenance_cost']}.",
                fact_type="bridge",
                confidence="C5",
                source="agent:ouroboros-compiler",
                meta={"sub_type": "graph_compression", "target_file": str(target_path)},
            )
            return True

        except Exception as e:
            logger.error(f"OuroborosCompiler: Compilation failed - {e}")
            return False


if __name__ == "__main__":
    import asyncio
    import sys

    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        compiler = OuroborosCompiler()
        asyncio.run(compiler.compile_entity(sys.argv[1]))
    else:
        logger.error("Usage: python ouroboros_compiler.py <target_file>")
