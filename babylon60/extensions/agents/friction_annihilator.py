# [C5-REAL] Exergy-Maximized
"""FRICTION-ANNIHILATOR-Ω - Reality Delta Resolver.

Takes failed assumptions (limerence) and resolves them into working code,
annihilating the friction (Delta < 0) and converting it to Exergy.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

from babylon60.engine.smte.llm_mutator import LLMMutator  # pyright: ignore[reportAttributeAccessIssue]

from babylon60.agents.mixins import EngineAwareMixin

logger = logging.getLogger("cortex_extensions.agents.friction_annihilator")


class FrictionAnnihilatorAgent(EngineAwareMixin):
    """Sovereign Agent that annihilates epistemic friction."""

    def __init__(self, db_path: str | Path | None = None):
        self._db_path = db_path
        self._engine: Any = None
        self.mutator = LLMMutator()

    async def annihilate_friction(
        self, target_file: str, error_trace: str, context: str
    ) -> dict[str, Any]:
        """Convert a Reality Delta < 0 (error) into Exergy (fix)."""
        logger.info(f"FrictionAnnihilator: Engaging on {target_file}")
        self._ensure_engine()

        target_path = Path(target_file)
        if not target_path.exists():
            return {"status": "failed", "reason": "Target file not found."}

        with open(target_path, encoding="utf-8") as f:
            code_content = f.read()

        prompt = (
            "SYSTEM: You are the Friction Annihilator Agent. Your task is to eliminate epistemic friction.\n"
            f"CONTEXT: {context}\n"
            f"ERROR TRACE (Friction Source):\n{error_trace}\n\n"
            "Analyze the failure. Rewrite the provided code to resolve the error and align with C5-REAL execution.\n"
            "Return ONLY the raw fixed code. No markdown formatting, no explanations."
        )

        try:
            logger.info("FrictionAnnihilator: Generating mutation to resolve friction...")
            fixed_code = await self.mutator.mutate_prompt(prompt, code_content)

            # Ensure it is just code, not wrapped in markdown block
            fixed_code = fixed_code.strip()
            if fixed_code.startswith("```python"):
                fixed_code = fixed_code[9:]
            if fixed_code.startswith("```"):
                fixed_code = fixed_code[3:]
            if fixed_code.endswith("```"):
                fixed_code = fixed_code[:-3]
            fixed_code = fixed_code.strip()

            # Annihilation: overwrite the file
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(fixed_code + "\n")

            logger.info(
                f"FrictionAnnihilator: Friction resolved. Exergy generated for {target_path.name}"
            )

            # Persist the annihilation event to the ledger
            await self._engine.store(
                project="SYSTEM",
                content=f"Annihilated friction in {target_path.name}. Context: {context[:50]}...",
                fact_type="bridge",
                confidence="C5",
                source="agent:friction-annihilator",
                meta={
                    "sub_type": "friction_annihilation",
                    "target_file": str(target_file),
                },
            )

            return {"status": "success", "file": target_file}

        except Exception as e:
            logger.error(f"FrictionAnnihilator: Failed to annihilate friction: {e}")
            return {"status": "failed", "reason": str(e)}


async def run_friction_cli(target_file: str, error_trace: str):
    agent = FrictionAnnihilatorAgent()
    result = await agent.annihilate_friction(target_file, error_trace, "CLI triggered annihilation")
    print(result)


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 2:
        asyncio.run(run_friction_cli(sys.argv[1], sys.argv[2]))
    else:
        print("Usage: python friction_annihilator.py <target_file> <error_trace>")
