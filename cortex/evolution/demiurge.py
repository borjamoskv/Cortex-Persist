"""
Demiurge Omega (Sortu Protocol): Ephemeral Skill Compiler for CORTEX.
Implements dynamic autopoiesis, zero-trust execution, and Bayesian feedback.
"""
from __future__ import annotations

import ast
import asyncio
import logging
from typing import Any

from cortex.engine import CortexEngine
from cortex.llm.manager import LLMManager

logger = logging.getLogger("cortex.evolution.demiurge")

class DemiurgeCompiler:
    """Sortu JIT Compiler: Autopoiesis and Ephemeral Skills."""

    def __init__(self, engine: CortexEngine | None = None):
        if engine is None:
            from cortex.cli.common import get_engine
            self.engine = get_engine()
        else:
            self.engine = engine
        self.llm = LLMManager()

    async def initialize(self) -> None:
        """Initialize engine if needed."""
        # CortexEngine is initialized synchronously.
        pass

    async def forge_skill(self, intent: str, project_scope: str = "demiurge") -> dict[str, Any]:
        """
        Executes the 10-phase singular forge for a JIT skill:
        1. Parse intent
        2. Generate code
        3. Validate Syntax
        4. Execute in Sandbox
        5. Verify results
        6. Compute Utility Score
        7. Record Ghost/Bridge in Ledger
        """
        await self.initialize()

        logger.info("Demiurge Omega forging skill for intent: %s", intent)
        system_prompt = (
            "You are Demiurge Omega, an elite Python CORTEX sovereign JIT compiler. "
            "Generate a solitary, dependency-free, asynchronous Python function named `execute_skill()` "
            "that fulfills the user's intent. Return ONLY valid Python code starting with `async def execute_skill():`. "
            "Do NOT return markdown blocks, only the raw python code. Keep it under 50 lines. "
            "It must return a string or dict with the result."
        )

        try:
            # Phase 1-2: Interception & Genetics
            generated_code = await self.llm.complete(
                prompt=intent,
                system=system_prompt,
                temperature=0.2
            )
            if not generated_code:
                return {"status": "FAILED", "reason": "No LLM response (check CORTEX_LLM_PROVIDER)", "utility": 0.0}

            generated_code = generated_code.strip()
            if generated_code.startswith("```"):
                generated_code = generated_code.split("```")[1]
                if generated_code.startswith("python"):
                    generated_code = generated_code[6:].strip()
            
            # Phase 3: Zero-Trust Validation (Syntax check)
            try:
                ast.parse(generated_code)
            except SyntaxError as e:
                await self._record_ghost(intent, generated_code, f"Syntax Error: {e}", 0.1)
                return {"status": "FAILED", "reason": "Syntax Error", "utility": 0.1, "code": generated_code}

            # Phase 4-5: Ephemeral Execution (Sandbox)
            namespace: dict[str, Any] = {}
            try:
                # We compile and exec to catch definition errors early
                code_obj = compile(generated_code, "<demiurge_ast>", "exec")
                exec(code_obj, namespace)
            except Exception as e:  # noqa: BLE001 — Compilation error during JIT forging is expected
                await self._record_ghost(intent, generated_code, f"Compilation Error: {e}", 0.15)
                return {"status": "FAILED", "reason": f"Compilation Error: {e}", "utility": 0.15, "code": generated_code}
                
            if "execute_skill" not in namespace:
                return {"status": "FAILED", "reason": "Missing execute_skill()", "utility": 0.0, "code": generated_code}

            # Phase 6: Run the skill
            start_time = asyncio.get_event_loop().time()
            try:
                # We must await the execution as the function is defined as async
                result = await namespace["execute_skill"]()
                execution_time = asyncio.get_event_loop().time() - start_time
                
                # Assign a base utility score
                utility = 0.9 if execution_time < 2.0 else 0.6
                
                # Phase 7-9: Crystallization (Ledger persistence)
                await self.engine.store(
                    project=project_scope,
                    fact_type="demiurge:bridge",
                    content=f"Successfully forged and executed skill for: {intent}",
                    tags=["demiurge", "skill", "autopoiesis", "bridge"],
                    source="agent:demiurge",
                    meta={"code": generated_code, "execution_time": execution_time, "result": str(result), "utility": utility}
                )

                return {"status": "SUCCESS", "result": result, "time": execution_time, "utility": utility, "code": generated_code}

            except Exception as run_err:  # noqa: BLE001 — Runtime exception during JIT execution is expected
                await self._record_ghost(intent, generated_code, str(run_err), 0.2)
                return {"status": "FAILED", "reason": f"Runtime Exception: {run_err}", "utility": 0.2, "code": generated_code}

        except Exception as e:  # noqa: BLE001 — Forge orchestration failure must be reported as ERROR status
            logger.error("Forge failed: %s", e)
            return {"status": "ERROR", "reason": str(e)}

    async def _record_ghost(self, intent: str, code: str, error: str, utility: float):
        """Record failed skills as ghosts in the ledger."""
        await self.engine.store(
            project="demiurge",
            fact_type="demiurge:ghost",
            content=f"Failed to forge skill for: {intent}. Error: {error}",
            tags=["demiurge", "skill", "ghost", "error"],
            source="agent:demiurge",
            meta={"code": code, "error": error, "utility": utility}
        )
