import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cortex.engine.isolation import IsolationManager
from cortex.engine.signals import log_limbic

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.agents.fuckchatgpt.reasoning")


@dataclass
class PeARLProgram:
    source_code: str
    confidence: float


class PeARLInductor:
    """
    Induces PeARL programs from common-sense primitives (AX-043).
    """

    def __init__(self) -> None:
        self.primitives = [
            "objects",
            "colors",
            "symmetry",
            "periodicity",
            "translate",
            "rotate",
            "reflect",
            "flood_fill",
        ]

    async def induce_candidates(
        self, training_examples: list[dict], n: int = 3
    ) -> list[PeARLProgram]:
        """
        Synthesizes multiple PeARL program candidates from training data (AX-046).
        """
        logger.info("Inducing %d PeARL candidates from %d examples.", n, len(training_examples))

        from cortex.extensions.llm.manager import LLMManager
        from cortex.extensions.llm.router import IntentProfile
        llm = LLMManager()

        # AX-042: Fixed bytes at the head for KV-Aware Routing (Prefix Caching)
        prompt = (
            "ARC-AGI Neuro-Symbolic Induction (AX-043/AX-046).\n"
            "Instruction: Synthesize a Python function `transform(grid: list[list[int]])` "
            "that implement the transformation shown in the examples below.\n"
            "Constraint: Respond ONLY with the code block. Zero-shot 0% Fact Drop.\n\n"
            f"Task Data: {json.dumps(training_examples)}"
        )

        candidates = []
        for i in range(n):
            # i=0 uses greedy (temp 0.0), others slightly varied
            temp = 0.2 if i > 0 else 0.0
            code_str = await llm.complete(
                prompt=prompt,
                system="Sovereign ARC-AGI Inductor. Zero-shot 0% Fact Drop. Code ONLY.",
                temperature=temp,
                intent=IntentProfile.CODE
            )
            if code_str:
                candidates.append(self._guard_program(code_str))

        return candidates

    def _guard_program(self, code: str) -> PeARLProgram:
        """PeARLGuard: Deterministic Static Boundary (Ω₁)."""
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        confidence = 0.95
        if "def transform" not in code:
            code = "def transform(grid):\n    return grid"
            confidence = 0.0

        return PeARLProgram(source_code=code, confidence=confidence)


class NeuroSymbolicSearch:
    """
    Neuro-Symbolic Search Loop (AX-043/AX-046).
    """

    def __init__(self, inductor: PeARLInductor, isolation: IsolationManager | None = None):
        self.inductor = inductor
        self.isolation = isolation or IsolationManager()

    async def search(self, train_examples: list[dict]) -> PeARLProgram:
        candidates = await self.inductor.induce_candidates(train_examples, n=3)

        best_program = PeARLProgram("def transform(grid):\n    return grid", 0.0)
        best_score = -1.0

        for cand in candidates:
            score = await self._verify(cand, train_examples)
            if score > best_score:
                best_score = score
                best_program = cand

            if score >= 1.0:
                break

        return best_program

    async def _verify(self, program: PeARLProgram, train_examples: list[dict]) -> float:
        """Correctness score for ARC candidates."""
        c: dict[str, Any] = {"passed": 0, "total": 0, "matching": 0}

        harness = f"""
import json
import sys

{program.source_code}

try:
    input_data = json.loads(sys.argv[1])
    result = transform(input_data)
    print(json.dumps(result))
except Exception as e:
    sys.stderr.write(str(e))
    sys.exit(1)
"""

        async with self.isolation.isolate(label="arc_verify") as sandbox:
            await sandbox.write_file("transform_harness.py", harness)

            for ex in train_examples:
                inp = ex["input"]
                out = ex["output"]

                res = await sandbox.execute_python("transform_harness.py", args=[json.dumps(inp)])

                if res and res.exit_code == 0:
                    try:
                        pred = json.loads(res.stdout)
                        if pred == out:
                            c["passed"] += 1

                        if isinstance(pred, list) and isinstance(out, list) and \
                           len(pred) == len(out) and len(pred[0]) == len(out[0]):
                            for r_p, r_o in zip(pred, out, strict=True):
                                for c_p, c_o in zip(r_p, r_o, strict=True):
                                    c["total"] += 1
                                    if c_p == c_o:
                                        c["matching"] += 1
                        else:
                            c["total"] += 100
                    except (json.JSONDecodeError, TypeError):
                        c["total"] += 100
                else:
                    c["total"] += 100

        e_score: float = c["passed"] / len(train_examples)
        p_val: int = c["total"] if c["total"] > 0 else 1
        p_score: float = c["matching"] / p_val

        # Weighted score (AX-046 requires 0% Fact Drop, here we use weighted heuristic)
        return float((e_score * 0.8) + (p_score * 0.2))


class ArcReasoningEngine:
    """
    Sovereign ARC-AGI Reasoning Engine.
    """

    def __init__(self) -> None:
        self.inductor = PeARLInductor()
        self.search_engine = NeuroSymbolicSearch(self.inductor)
        self.active_program: PeARLProgram | None = None

    async def synthesize_and_execute(
        self, train_examples: list[dict], test_input: list[list[int]]
    ) -> list[list[int]]:
        log_limbic("ARC-3: Iniciando Búsqueda Neuro-Simbólica...",
                   source="REASONING", vibe="cterm-deep-think")

        self.active_program = await self.search_engine.search(train_examples)

        # Guard against None
        prog = self.active_program
        if prog and prog.confidence > 0:
            log_limbic(f"ARC-3: Concepto Cristalizado (Conf: {prog.confidence:.2f})",
                       source="REASONING", vibe="cterm-exergy")

            # Local JIT Execution (restricted)
            exec_globals: dict[str, Any] = {"__builtins__": {}}
            try:
                exec(prog.source_code, exec_globals)
                transform_fn = exec_globals.get("transform")
                if callable(transform_fn):
                    return transform_fn(test_input)
            except Exception as e:
                logger.error("Failed to execute crystallized program: %s", e)

        # Return original input as fallback (Epistemic Posture)
        return test_input
