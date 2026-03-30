import asyncio
import json
import os
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from cortex.engine.alphazero.mcts_core import MCTS, AlphaZeroNode
from cortex.engine.alphazero.network import PolicyValueNetwork
from cortex.engine.isolation import SimpleIsolationEngine
from cortex.engine.signals import log_limbic

if TYPE_CHECKING:
    pass

logger = logging.getLogger("cortex.agents.arc_agi_3.reasoning")


# ─── DSL helpers injected into every sandbox execution ───────────────────────
SANDBOX_PRELUDE = '''
import copy

def grid_dims(g):
    return (len(g), len(g[0]) if g else 0)

def grid_colors(g):
    s = set()
    for row in g:
        for c in row:
            s.add(c)
    return sorted(s)

def make_grid(rows, cols, fill=0):
    return [[fill]*cols for _ in range(rows)]

def copy_grid(g):
    return [row[:] for row in g]

def rotate_90(g):
    rows, cols = len(g), len(g[0])
    return [[g[rows-1-r][c] for r in range(rows)] for c in range(cols)]

def rotate_180(g):
    return rotate_90(rotate_90(g))

def rotate_270(g):
    return rotate_90(rotate_90(rotate_90(g)))

def flip_h(g):
    return [row[::-1] for row in g]

def flip_v(g):
    return g[::-1]

def transpose(g):
    rows, cols = len(g), len(g[0])
    return [[g[r][c] for r in range(rows)] for c in range(cols)]

def crop(g, r1, c1, r2, c2):
    return [row[c1:c2+1] for row in g[r1:r2+1]]

def paste(target, patch, r_off, c_off):
    g = copy_grid(target)
    for r in range(len(patch)):
        for c in range(len(patch[0])):
            tr, tc = r + r_off, c + c_off
            if 0 <= tr < len(g) and 0 <= tc < len(g[0]):
                g[tr][tc] = patch[r][c]
    return g

def flood_fill(g, r, c, new_color):
    g = copy_grid(g)
    old = g[r][c]
    if old == new_color:
        return g
    stack = [(r, c)]
    while stack:
        cr, cc = stack.pop()
        if 0 <= cr < len(g) and 0 <= cc < len(g[0]) and g[cr][cc] == old:
            g[cr][cc] = new_color
            stack.extend([(cr-1,cc),(cr+1,cc),(cr,cc-1),(cr,cc+1)])
    return g

def find_objects(g, bg=0):
    rows, cols = len(g), len(g[0])
    visited = set()
    objs = []
    for r in range(rows):
        for c in range(cols):
            if g[r][c] != bg and (r,c) not in visited:
                color = g[r][c]
                pixels = []
                stack = [(r,c)]
                visited.add((r,c))
                while stack:
                    cr, cc = stack.pop()
                    pixels.append((cr, cc))
                    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                        nr, nc = cr+dr, cc+dc
                        if 0<=nr<rows and 0<=nc<cols and (nr,nc) not in visited and g[nr][nc]==color:
                            visited.add((nr,nc))
                            stack.append((nr,nc))
                objs.append({"color": color, "pixels": pixels})
    return objs

def most_common_color(g, exclude=None):
    counts = {}
    for row in g:
        for c in row:
            if exclude is not None and c == exclude:
                continue
            counts[c] = counts.get(c, 0) + 1
    return max(counts, key=counts.get) if counts else 0

def replace_color(g, old, new):
    return [[new if c == old else c for c in row] for row in g]
'''


@dataclass
class PeARLProgram:
    source_code: str
    confidence: float


class PeARLNetwork(PolicyValueNetwork[str, str]):
    def __init__(self, llm_manager):
        self.llm = llm_manager

    async def evaluate_async(self, state: str) -> tuple[dict[str, float], float]:
        actions = ["synthesize", "refine"] if "def transform" in state else ["generate"]
        return ({a: 1.0 / len(actions) for a in actions}, 0.5)


class MCTSEnvironment:
    def __init__(
        self,
        llm_manager,
        search_engine: 'NeuroSymbolicSearch',
        examples: list[dict],
    ):
        self.llm = llm_manager
        self.search_engine = search_engine
        self.examples = examples

    async def get_terminal_value_async(self, state: str) -> float | None:
        if "def transform" in state:
            return await self.search_engine._verify_correctness(state, self.examples)
        if len(state) > 2000:
            return 0.0
        return None

    async def get_legal_actions_async(self, state: str) -> list[str]:
        if "def transform" not in state:
            return ["generate"]
        return []

    async def step_async(self, state: str, action: str) -> str:
        prompt = self._build_mcts_prompt()
        from cortex.extensions.llm.router import IntentProfile
        code = await self.llm.complete(
            prompt=prompt,
            system="fuckChatGPT MCTS Synthesis. Code ONLY. Zero markdown.",
            temperature=0.7,
            intent=IntentProfile.CODE,
        )
        if not code:
            return "def transform(grid):\n    return grid"
        code = _extract_code(code)
        if "def transform" not in code:
            code = "def transform(grid):\n    return grid"
        return code

    def _build_mcts_prompt(self) -> str:
        return _build_fuckchatgpt_prompt(self.examples)


class PeARLInductor:
    """Induces PeARL programs from common-sense primitives (AX-043)."""

    def __init__(self) -> None:
        self.primitives = [
            "objects", "colors", "symmetry", "periodicity",
            "translate", "rotate", "reflect", "flood_fill",
        ]

    async def induce_candidates(
        self, training_examples: list[dict], n: int = 8
    ) -> list[PeARLProgram]:
        """Synthesizes multiple PeARL program candidates (AX-046)."""
        logger.info(
            "fuckChatGPT: Inducing %d candidates from %d examples.", n, len(training_examples)
        )

        from cortex.extensions.llm.manager import LLMManager
        from cortex.extensions.llm.router import IntentProfile

        llm = LLMManager()

        prompt = _build_fuckchatgpt_prompt(training_examples)

        # AX-046: Parallel Induction (Swarm-100 Integration)
        is_stress_test = os.getenv("ARC_STRESS_TEST") == "true"
        if n >= 50 or is_stress_test:
            from cortex.engine.legion import SwarmInductor
            replica_count = 100 if is_stress_test else n
            inductor = SwarmInductor(replica_count=replica_count)
            context = {
                "arc_task": True,
                "training_examples": training_examples,
                "arc_prompt": prompt,
            }
            best_code = await inductor.induce("arc_induction", context)
            if isinstance(best_code, str) and "def transform" in best_code:
                return [self._guard_program(best_code)]

        # Parallel synthesis with temperature sweep
        tasks = []
        for i in range(n):
            temp = 0.0 if i == 0 else min(0.3 + (i * 0.1), 1.0)
            tasks.append(
                llm.complete(
                    prompt=f"{prompt}\n\n# Candidate variant {i}",
                    system=(
                        "fuckChatGPT Sovereign Inductor. "
                        "You are the best ARC-AGI solver in the world. "
                        "Return ONLY the Python function. No markdown. No explanation."
                    ),
                    temperature=temp,
                    intent=IntentProfile.CODE,
                )
            )

        results = await asyncio.gather(*tasks)
        candidates = [self._guard_program(c) for c in results if c]
        return candidates

    def _guard_program(self, code: str) -> PeARLProgram:
        """PeARLGuard: Deterministic Static Boundary (Ω₁)."""
        code = _extract_code(code)
        confidence = 0.95
        if "def transform" not in code:
            code = "def transform(grid):\n    return grid"
            confidence = 0.0
        return PeARLProgram(source_code=code, confidence=confidence)


class NeuroSymbolicSearch:
    """Neuro-Symbolic Search with iterative refinement (fuckChatGPT mode)."""

    MAX_REFINEMENT_PASSES = 3

    def __init__(
        self,
        inductor: PeARLInductor,
        isolation: SimpleIsolationEngine | None = None,
    ):
        self.inductor = inductor
        self.isolation = isolation or SimpleIsolationEngine(timeout=10)

    async def search(self, train_examples: list[dict]) -> PeARLProgram:
        from cortex.extensions.llm.manager import LLMManager

        llm = LLMManager()

        # ── Pass 1: MCTS Deep Search (50 simulations) ──────────────────
        log_limbic(
            "fuckChatGPT: MCTS Deep Search (50 sims)...",
            source="MCTS", vibe="cterm-deep-think",
        )
        env = MCTSEnvironment(llm, self, train_examples)
        network = PeARLNetwork(llm)
        mcts = MCTS(network, num_simulations=50)
        root = AlphaZeroNode(state="", prior=1.0)

        await mcts.simulate_async(root, env)

        best_program = PeARLProgram("def transform(grid):\n    return grid", 0.0)
        best_score = -1.0

        # Evaluate MCTS children
        child_tasks = []
        actions = list(root.children.keys())
        for action in actions:
            child = root.children[action]
            child_tasks.append(self._verify_correctness(child.state, train_examples))

        if child_tasks:
            node_scores = await asyncio.gather(*child_tasks)
            for i, score in enumerate(node_scores):
                child = root.children[actions[i]]
                if score > best_score:
                    best_score = score
                    best_program = PeARLProgram(child.state, score)

        # ── Pass 2: Direct parallel induction (8 candidates) ──────────
        if best_score < 1.0:
            log_limbic(
                f"fuckChatGPT: MCTS scored {best_score:.2f}. Trying direct induction...",
                source="INDUCTOR", vibe="cterm-exergy",
            )
            candidates = await self.inductor.induce_candidates(train_examples, n=8)
            eval_tasks = [
                self._verify_correctness(c.source_code, train_examples) for c in candidates
            ]
            scores = await asyncio.gather(*eval_tasks)
            for c, s in zip(candidates, scores, strict=True):
                if s > best_score:
                    best_score = s
                    best_program = PeARLProgram(c.source_code, s)

        # ── Pass 3: Iterative refinement with error feedback ──────────
        for pass_num in range(self.MAX_REFINEMENT_PASSES):
            if best_score >= 1.0:
                break

            log_limbic(
                f"fuckChatGPT: Refinement pass {pass_num + 1}/{self.MAX_REFINEMENT_PASSES} "
                f"(current best: {best_score:.2f})",
                source="REFINE", vibe="cterm-deep-think",
            )

            errors = await self._collect_errors(best_program.source_code, train_examples)
            if not errors:
                break

            refined = await self._refine_with_errors(
                llm, best_program.source_code, train_examples, errors
            )
            refined_score = await self._verify_correctness(refined, train_examples)
            if refined_score > best_score:
                best_score = refined_score
                best_program = PeARLProgram(refined, refined_score)

        log_limbic(
            f"fuckChatGPT: Final score {best_score:.2f}",
            source="SEARCH", vibe="cterm-exergy",
        )
        return best_program

    async def _verify_correctness(
        self, program: str, train_examples: list[dict]
    ) -> float:
        """Pure correctness scoring — no exergy penalty."""
        harness = f"""\
import json
import sys

{SANDBOX_PRELUDE}

{program}

try:
    input_data = json.loads(sys.argv[1])
    result = transform(input_data)
    print(json.dumps(result))
except Exception as e:
    sys.stderr.write(str(e))
    sys.exit(1)
"""
        tasks = []
        for ex in train_examples:
            tasks.append(
                self.isolation.execute_sandbox(harness, args=[json.dumps(ex["input"])])
            )

        results = await asyncio.gather(*tasks)

        passed = 0
        partial_matches = 0
        total_cells = 0

        for ex, res in zip(train_examples, results, strict=True):
            expected = ex["output"]
            if res and res.exit_code == 0:
                try:
                    pred = json.loads(res.stdout)
                    if pred == expected:
                        passed += 1
                    # Partial cell-level matching
                    if (
                        isinstance(pred, list)
                        and isinstance(expected, list)
                        and len(pred) == len(expected)
                        and all(len(pr) == len(er) for pr, er in zip(pred, expected))
                    ):
                        for r_p, r_e in zip(pred, expected, strict=True):
                            for c_p, c_e in zip(r_p, r_e, strict=True):
                                total_cells += 1
                                if c_p == c_e:
                                    partial_matches += 1
                    else:
                        total_cells += 100
                except (json.JSONDecodeError, TypeError):
                    total_cells += 100
            else:
                total_cells += 100

        exact_score = passed / len(train_examples) if train_examples else 0.0
        partial_score = partial_matches / total_cells if total_cells > 0 else 0.0

        return float(exact_score * 0.85 + partial_score * 0.15)

    async def _collect_errors(
        self, program: str, train_examples: list[dict]
    ) -> list[dict]:
        """Returns list of {index, input, expected, got, error} for failed cases."""
        harness = f"""\
import json
import sys

{SANDBOX_PRELUDE}

{program}

try:
    input_data = json.loads(sys.argv[1])
    result = transform(input_data)
    print(json.dumps(result))
except Exception as e:
    sys.stderr.write(str(e))
    sys.exit(1)
"""
        tasks = [
            self.isolation.execute_sandbox(harness, args=[json.dumps(ex["input"])])
            for ex in train_examples
        ]
        results = await asyncio.gather(*tasks)
        errors: list[dict] = []

        for i, (ex, res) in enumerate(zip(train_examples, results, strict=True)):
            expected = ex["output"]
            if res and res.exit_code == 0:
                try:
                    pred = json.loads(res.stdout)
                    if pred != expected:
                        errors.append({
                            "index": i,
                            "input": ex["input"],
                            "expected": expected,
                            "got": pred,
                            "error": None,
                        })
                except (json.JSONDecodeError, TypeError):
                    errors.append({
                        "index": i,
                        "input": ex["input"],
                        "expected": expected,
                        "got": None,
                        "error": f"JSON decode error: {res.stdout[:200]}",
                    })
            else:
                errors.append({
                    "index": i,
                    "input": ex["input"],
                    "expected": expected,
                    "got": None,
                    "error": res.stderr[:300] if res else "Execution failed",
                })
        return errors

    async def _refine_with_errors(
        self,
        llm,
        program: str,
        train_examples: list[dict],
        errors: list[dict],
    ) -> str:
        """Re-synthesize with explicit error feedback."""
        from cortex.extensions.llm.router import IntentProfile

        error_desc = []
        for e in errors[:3]:  # Limit to 3 error cases
            desc = f"Example {e['index']}:\n  Input: {json.dumps(e['input'])}\n"
            desc += f"  Expected: {json.dumps(e['expected'])}\n"
            if e["got"] is not None:
                desc += f"  Got: {json.dumps(e['got'])}\n"
            if e["error"]:
                desc += f"  Error: {e['error']}\n"
            error_desc.append(desc)

        prompt = (
            "Your previous program is WRONG. Fix it.\n\n"
            f"Previous program:\n```python\n{program}\n```\n\n"
            f"Failures:\n{''.join(error_desc)}\n\n"
            f"All training examples:\n{json.dumps(train_examples, indent=2)}\n\n"
            "Available helpers: grid_dims, grid_colors, make_grid, copy_grid, "
            "rotate_90, rotate_180, rotate_270, flip_h, flip_v, transpose, "
            "crop, paste, flood_fill, find_objects, most_common_color, replace_color.\n\n"
            "Analyze the diff between each input/output carefully. "
            "Think step by step about what transformation maps input to output. "
            "Return ONLY the corrected `def transform(grid):` function."
        )

        code = await llm.complete(
            prompt=prompt,
            system=(
                "fuckChatGPT Error Refiner. "
                "You are fixing a failing ARC-AGI program. "
                "Return ONLY the corrected Python function. No markdown. No explanation."
            ),
            temperature=0.2,
            intent=IntentProfile.CODE,
        )
        if not code:
            return program
        code = _extract_code(code)
        if "def transform" not in code:
            return program
        return code


class ArcReasoningEngine:
    """Sovereign ARC-AGI Reasoning Engine — fuckChatGPT mode."""

    def __init__(self) -> None:
        self.inductor = PeARLInductor()
        self.search_engine = NeuroSymbolicSearch(self.inductor)
        self.active_program: PeARLProgram | None = None

    async def synthesize_and_execute(
        self, train_examples: list[dict], test_input: list[list[int]]
    ) -> list[list[int]]:
        log_limbic(
            "fuckChatGPT: Initiating Neuro-Symbolic Search...",
            source="REASONING", vibe="cterm-deep-think",
        )

        self.active_program = await self.search_engine.search(train_examples)

        prog = self.active_program
        if prog and prog.confidence > 0:
            log_limbic(
                f"fuckChatGPT: Crystallized (Conf: {prog.confidence:.2f})",
                source="REASONING", vibe="cterm-exergy",
            )

            # Execute with DSL helpers available
            exec_globals: dict[str, Any] = {}
            try:
                exec(SANDBOX_PRELUDE + "\n" + prog.source_code, exec_globals)
                transform_fn = exec_globals.get("transform")
                if callable(transform_fn):
                    result = transform_fn(test_input)
                    if isinstance(result, list):
                        return result
            except Exception as e:
                logger.error("fuckChatGPT: Execution failed: %s", e)

        return test_input


# ─── Utility functions ───────────────────────────────────────────────────────

def _extract_code(raw: str) -> str:
    """Strips markdown fences from LLM output."""
    if "```python" in raw:
        raw = raw.split("```python")[1].split("```")[0].strip()
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0].strip()
    return raw.strip()


def _build_fuckchatgpt_prompt(training_examples: list[dict]) -> str:
    """Builds the aggressive structural analysis prompt."""
    analysis_parts = []
    for i, ex in enumerate(training_examples):
        inp = ex["input"]
        out = ex["output"]
        in_rows, in_cols = len(inp), len(inp[0]) if inp else 0
        out_rows, out_cols = len(out), len(out[0]) if out else 0

        in_colors = sorted({c for row in inp for c in row})
        out_colors = sorted({c for row in out for c in row})

        # Detect size change
        size_change = "same" if (in_rows, in_cols) == (out_rows, out_cols) else "different"

        analysis_parts.append(
            f"Example {i}:\n"
            f"  Input:  {in_rows}x{in_cols}, colors={in_colors}\n"
            f"  Output: {out_rows}x{out_cols}, colors={out_colors}\n"
            f"  Size: {size_change}\n"
            f"  Input grid:  {json.dumps(inp)}\n"
            f"  Output grid: {json.dumps(out)}"
        )

    return (
        "TASK: Solve this ARC-AGI grid transformation puzzle.\n\n"
        "STRUCTURAL ANALYSIS:\n"
        + "\n\n".join(analysis_parts)
        + "\n\n"
        "INSTRUCTIONS:\n"
        "1. Study EVERY example carefully. Compare input and output grids cell by cell.\n"
        "2. Identify the EXACT transformation rule. Common patterns:\n"
        "   - Color substitution, flood fill, mirroring, rotation, tiling\n"
        "   - Object detection, movement, scaling, symmetry completion\n"
        "   - Pattern extraction, border detection, gravity simulation\n"
        "3. Write a Python function `def transform(grid: list[list[int]]) -> list[list[int]]:`\n"
        "4. Available helpers: grid_dims, grid_colors, make_grid, copy_grid, "
        "rotate_90, rotate_180, rotate_270, flip_h, flip_v, transpose, "
        "crop, paste, flood_fill, find_objects, most_common_color, replace_color.\n"
        "5. Test your logic mentally against ALL examples before returning.\n\n"
        "Return ONLY the `def transform(grid):` function. No imports. No markdown. No explanation."
    )
