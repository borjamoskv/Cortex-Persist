# [C5-REAL] Exergy-Maximized
"""OUROBOROS-COMPILER-Ω - AOT Limerent Agent Compiler.

Transforms high-entropy, low-utility execution graphs (limerent agents)
into deterministic, minimal paths (pure functions).
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from cortex.engine.smte.llm_mutator import call_qwen_mutator
from cortex.engine.smte.weismann_barrier import enforce_weismann_barrier

logger = logging.getLogger("cortex.engine.smte.ouroboros_compiler")


class OuroborosCompiler:
    """AOT Compiler that converts limerent agents into compressed minimal paths."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = db_path
        self._engine: Any = None

    def _ensure_engine(self) -> None:
        if self._engine is not None:
            return
        from cortex.config import DEFAULT_DB_PATH
        from cortex.engine import CortexEngine

        db_val = str(self._db_path) if self._db_path else DEFAULT_DB_PATH
        self._engine = CortexEngine(db_path=db_val)

    def analyze_limerence(self, source_code: str) -> dict[str, Any]:
        """Analyze code for high maintenance cost vs utility using L-EPI empirical metrics.

        Calculates AST Complexity and Dead Code Ratio to enforce the Ouroboros-Omega L-EPI Guard.
        """
        from cortex.engine.smte.analyzer import calculate_ast_complexity, estimate_dead_code_ratio

        complexity = calculate_ast_complexity(source_code)
        dead_code_ratio = estimate_dead_code_ratio(source_code)

        # We assume empirical_usage = 1.0 statically unless dynamically passed
        empirical_usage = 1.0
        limerence_penalty = (complexity / empirical_usage) * 10.0

        # Combine old metric style with new L-EPI Guard style
        llm_calls = 0
        try:
            tree = ast.parse(source_code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr in (
                        "complete",
                        "chat",
                        "predict",
                        "generate",
                        "mutate_prompt",
                    ):
                        llm_calls += 1
        except SyntaxError:

            pass

        cost = (llm_calls * 10) + complexity

        is_limerent = cost > 15 or limerence_penalty > 10.0
        must_amputate = dead_code_ratio > 0.4 and limerence_penalty > 10.0

        return {
            "llm_calls": llm_calls,
            "complexity": complexity,
            "dead_code_ratio": dead_code_ratio,
            "limerence_penalty": limerence_penalty,
            "maintenance_cost": cost,
            "is_limerent": is_limerent,
            "must_amputate": must_amputate,
        }

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

        self._ensure_engine()

        if analysis.get("must_amputate"):
            logger.info(
                f"[L-EPI GUARD] FATAL: Limerencia Epistémica detectada en {target_path.name}. "
                f"dead_code_ratio={analysis['dead_code_ratio']:.2f}, limerence_penalty={analysis['limerence_penalty']:.2f}. "
                "Amputación automática iniciada."
            )
            target_path.unlink()

            content_val = (
                f"L-EPI Guard amputated {target_path.name} due to high limerence/dead code."
            )
            import hashlib

            logos_sig = hashlib.sha256(f"{content_val}SYSTEM".encode()).hexdigest()

            await self._engine.store(
                project="SYSTEM",
                content=content_val,
                fact_type="bridge",
                confidence="C5",
                source="agent:ouroboros-compiler",
                meta={
                    "sub_type": "l_epi_amputation",
                    "target_file": str(target_path),
                    "logos_signature": logos_sig,
                },
            )
            return True

        if not analysis.get("is_limerent"):
            logger.info("Entity is not limerent (C <= U). No compilation needed.")
            return True

        logger.info(
            f"Limerence detected: Maintenance Cost {analysis['maintenance_cost']}. "
            "Compressing graph..."
        )

        # Generate compressed AST representation using Qwen LLM
        prompt = (
            "SYSTEM: You are the Ouroboros Compiler. Your objective is AOT structural compression.\\n"
            "Eliminate 'limerent' (stochastic, unnecessary LLM) logic and replace it with pure, deterministic paths.\\n"
            "Compress the complexity (C) to the absolute minimum required to achieve the utility (U).\\n"
            "Return ONLY the pure python code. No markdown formatting, no explanations."
        )

        try:
            # We pass a simple dict for topology_info since this is a global compile
            topology_info = {"prompt": prompt}
            compiled_code = call_qwen_mutator(source, topology_info)

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
            content_val = f"Ouroboros compiled {target_path.name}. Cost reduced from {analysis['maintenance_cost']}."
            import hashlib

            logos_sig = hashlib.sha256(f"{content_val}SYSTEM".encode()).hexdigest()

            await self._engine.store(
                project="SYSTEM",
                content=content_val,
                fact_type="bridge",
                confidence="C5",
                source="agent:ouroboros-compiler",
                meta={
                    "sub_type": "graph_compression",
                    "target_file": str(target_path),
                    "logos_signature": logos_sig,
                },
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
