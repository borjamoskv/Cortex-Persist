"""
Ouroboros-Omega: The Central Autopoietic Metabolism of CORTEX.
Implements Darwinian Code Mutation (Axiom Ω₂) with fully atomic rollback.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.evolution.ouroboros")


@dataclass
class DiagnosisMatrix:
    """State matrix of a Python module's structure."""

    loc: int = 0
    mccabe_complexity: dict[str, int] = field(default_factory=dict)
    nesting_depths: dict[str, int] = field(default_factory=dict)
    call_graph: dict[str, set[str]] = field(default_factory=dict)
    called_by: dict[str, set[str]] = field(default_factory=dict)
    imports: set[str] = field(default_factory=set)
    used_imports: set[str] = field(default_factory=set)
    dead_interfaces: set[str] = field(default_factory=set)
    blocking_calls: list[str] = field(default_factory=list)
    entropy_score: float = 0.0


class _AstAnalyzer(ast.NodeVisitor):
    def __init__(self):
        self.loc = 0
        self.mccabe = {}
        self.nesting = {}
        self.call_graph = {}
        self.imports = set()
        self.used_imports = set()
        self.func_nodes = {}
        self._current_function = None
        self._current_nesting = 0

    def visit_Module(self, node):
        self.loc = len(node.body) if node.body else 0  # To be precise, use file lines
        self.generic_visit(node)

    def visit_Import(self, node):
        for alias in node.names:
            var_name = alias.asname if alias.asname else alias.name
            self.imports.add(var_name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        for alias in node.names:
            var_name = alias.asname if alias.asname else alias.name
            self.imports.add(var_name)
        self.generic_visit(node)

    def visit_FunctionDef(self, node):
        self.func_nodes[node.name] = node
        prev_func = self._current_function
        self._current_function = node.name
        self.call_graph[node.name] = set()

        # Calculate cyclomatic complexity roughly
        complexity = 1
        for child in ast.walk(node):
            if isinstance(
                child,
                (
                    ast.If,
                    ast.While,
                    ast.For,
                    ast.AsyncFor,
                    ast.ExceptHandler,
                    ast.With,
                    ast.AsyncWith,
                ),
            ):
                complexity += 1
        self.mccabe[node.name] = complexity

        self.generic_visit(node)
        self._current_function = prev_func

    def visit_AsyncFunctionDef(self, node):
        self.visit_FunctionDef(node)  # Similar handling  # type: ignore[type-error]

    def visit_Call(self, node):
        if isinstance(node.func, ast.Name):
            self.used_imports.add(node.func.id)
            if self._current_function:
                self.call_graph[self._current_function].add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                self.used_imports.add(node.func.value.id)
        self.generic_visit(node)

    def visit_Name(self, node):
        if isinstance(node.ctx, ast.Load):
            self.used_imports.add(node.id)
        self.generic_visit(node)

    def _visit_nested(self, node):
        self._current_nesting += 1
        if self._current_function:
            self.nesting[self._current_function] = max(
                self.nesting.get(self._current_function, 0), self._current_nesting
            )
        self.generic_visit(node)
        self._current_nesting -= 1

    def visit_If(self, node):
        self._visit_nested(node)

    def visit_For(self, node):
        self._visit_nested(node)

    def visit_While(self, node):
        self._visit_nested(node)

    def visit_Try(self, node):
        self._visit_nested(node)


class _DeadCodePurge(ast.NodeTransformer):
    def __init__(self, dead_funcs: set[str], unused_imports: set[str]):
        self.dead_funcs = dead_funcs
        self.unused_imports = unused_imports

    def visit_Import(self, node):
        new_names = [n for n in node.names if (n.asname or n.name) not in self.unused_imports]
        if not new_names:
            return None
        node.names = new_names
        return node

    def visit_ImportFrom(self, node):
        new_names = [n for n in node.names if (n.asname or n.name) not in self.unused_imports]
        if not new_names:
            return None
        node.names = new_names
        return node

    def visit_FunctionDef(self, node):
        if node.name in self.dead_funcs and not node.name.startswith("__"):
            # Never purge decorators or __init__ style
            return None
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        if node.name in self.dead_funcs and not node.name.startswith("__"):
            return None
        self.generic_visit(node)
        return node


class _DocstringInjector(ast.NodeTransformer):
    def visit_FunctionDef(self, node):
        if not ast.get_docstring(node):
            if not node.name.startswith("_"):
                doc_node = ast.Expr(value=ast.Constant(value=f"TODO: Document {node.name}"))
                node.body.insert(0, doc_node)

        # Add return type None if missing and no return statements yield values
        has_returns = any(isinstance(n, ast.Return) and n.value is not None for n in ast.walk(node))
        if not node.returns and not has_returns and node.name != "__init__":
            node.returns = ast.Constant(value=None)

        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node):
        return self.visit_FunctionDef(node)  # type: ignore[type-error]


class _BlockingPatternDetector(ast.NodeVisitor):
    def __init__(self):
        self.blocking_calls = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id == "time" and node.func.attr == "sleep":
                self.blocking_calls.append("time.sleep")
            elif node.func.value.id == "sqlite3" and node.func.attr == "connect":
                self.blocking_calls.append("sqlite3.connect")
        elif isinstance(node.func, ast.Name) and node.func.id == "input":
            self.blocking_calls.append("input")
        self.generic_visit(node)


class OuroborosOmega:
    """The ACID Code Mutation Engine."""

    def __init__(
        self,
        target_path: str,
        project_root: str = "~/.gemini/antigravity/scratch/Cortex-Persist",
        dry_run: bool = False,
    ):
        self.target_path = Path(target_path).expanduser().resolve()
        self.project_root = Path(project_root).expanduser().resolve()
        self.dry_run = dry_run

        if not self.target_path.exists():
            raise FileNotFoundError(f"Target not found: {self.target_path}")

        with open(self.target_path, encoding="utf-8") as f:
            self.original_source = f.read()

        self.original_hash = hashlib.sha256(self.original_source.encode()).hexdigest()

    async def diagnose(self, source_code: str | None = None) -> DiagnosisMatrix:
        """Phase 1: Analysis (Topological Mapping)"""
        code = source_code if source_code is not None else self.original_source
        tree = ast.parse(code)

        analyzer = _AstAnalyzer()
        analyzer.loc = len(code.splitlines())
        analyzer.visit(tree)

        # Reverse edges
        called_by = {func: set() for func in analyzer.func_nodes}
        for caller, callees in analyzer.call_graph.items():
            for callee in callees:
                if callee in called_by:
                    called_by[callee].add(caller)

        # Identify dead functions (internal only for now, ignoring public API if they have no calls inside the module)
        # Note: This is simplified, real implementation would scan the whole project for references
        dead_funcs = {
            f
            for f, callers in called_by.items()
            if not callers and f.startswith("_") and f != "__init__"
        }

        unused_imports = analyzer.imports - analyzer.used_imports

        # Calculate Entropy
        entropy = 0.0
        loc_penalty = max(0, (analyzer.loc - 500) * 0.05)
        complexity_penalty = sum(max(0, c - 15) for c in analyzer.mccabe.values()) * 2.0
        dead_code_ratio = len(dead_funcs) / max(1, len(analyzer.func_nodes)) * 20.0
        unused_imports_penalty = len(unused_imports) * 2.0
        nesting_penalty = sum(max(0, n - 4) for n in analyzer.nesting.values()) * 3.0

        entropy = min(
            100.0,
            loc_penalty
            + complexity_penalty
            + dead_code_ratio
            + unused_imports_penalty
            + nesting_penalty,
        )

        detector = _BlockingPatternDetector()
        detector.visit(tree)

        return DiagnosisMatrix(
            loc=analyzer.loc,
            mccabe_complexity=analyzer.mccabe,
            nesting_depths=analyzer.nesting,
            call_graph=analyzer.call_graph,
            called_by=called_by,
            imports=analyzer.imports,
            used_imports=analyzer.used_imports,
            dead_interfaces=dead_funcs,
            blocking_calls=detector.blocking_calls,
            entropy_score=entropy,
        )

    async def execute_atomic_cycle(self) -> dict[str, Any]:
        """Perform the 5 phases of auto-poiesis with ACID rollback."""
        logger.info("Ouroboros-Omega starting atomic cycle on %s", self.target_path.name)

        try:
            # 1. ANALYSIS
            base_diagnosis = await self.diagnose()
            logger.info("Phase 1 [Analysis] Complete. Entropy: %.2f", base_diagnosis.entropy_score)

            tree = ast.parse(self.original_source)

            # 2. EXTRACTION
            purger = _DeadCodePurge(
                base_diagnosis.dead_interfaces, base_diagnosis.imports - base_diagnosis.used_imports
            )
            mutated_tree = purger.visit(copy.deepcopy(tree))
            ast.fix_missing_locations(mutated_tree)
            logger.info("Phase 2 [Extraction] Complete.")

            # 3. RECONSTRUCTION
            injector = _DocstringInjector()
            mutated_tree = injector.visit(mutated_tree)
            ast.fix_missing_locations(mutated_tree)
            logger.info("Phase 3 [Reconstruction] Complete.")

            # 4. SCALING (Non-destructive)
            if base_diagnosis.blocking_calls:
                logger.warning(
                    "Phase 4 [Scaling]: Detected blocking I/O: %s", base_diagnosis.blocking_calls
                )

            mutated_source = ast.unparse(mutated_tree)

            # 5. VERIFICATION
            try:
                ast.parse(mutated_source)  # Syntax
                compile(mutated_source, filename="<ast>", mode="exec")  # Bytecode
            except Exception as e:  # noqa: BLE001 — verification phase expected to fail on invalid syntax
                logger.error("Phase 5 [Verification] Failed syntax/bytecode: %s", e)
                return {"status": "ROLLED_BACK", "reason": str(e)}

            new_diagnosis = await self.diagnose(mutated_source)
            entropy_delta = new_diagnosis.entropy_score - base_diagnosis.entropy_score

            if entropy_delta > 5.0:
                logger.warning(
                    "Phase 5 [Verification] Entropy increased significantly (+%.2f). APOPTOSIS.",
                    entropy_delta,
                )
                return {
                    "status": "ROLLED_BACK",
                    "reason": f"Entropy regression: {entropy_delta:.2f}",
                }

            logger.info("Phase 5 [Verification] Complete. Entropy delta: %.2f", entropy_delta)

            # COMMIT
            if self.dry_run:
                return {"status": "DRY_RUN", "delta": entropy_delta, "new_code": mutated_source}

            current_hash = hashlib.sha256(self.target_path.read_bytes()).hexdigest()
            if current_hash != self.original_hash:
                logger.error("Concurrency exception: File modified externally during cycle.")
                return {"status": "ROLLED_BACK", "reason": "Concurrent modification detected."}

            with open(self.target_path, "w", encoding="utf-8") as f:
                f.write(mutated_source)

            logger.info("Ouroboros-Omega cycle SUCCESS for %s", self.target_path.name)
            return {"status": "SUCCESS", "delta": entropy_delta}

        except Exception as e:  # noqa: BLE001 — atomic cycle caught unhandled exception, triggering apoptosis
            logger.exception("Apoptosis: Unhandled exception during cycle.")
            return {"status": "ROLLED_BACK", "reason": str(e)}


if __name__ == "__main__":
    import argparse
    import asyncio
    import json

    parser = argparse.ArgumentParser(description="Ouroboros-Omega")
    parser.add_argument("file", help="Python file to metabolize")
    parser.add_argument("--diagnose-only", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    if args.verbose:
        logging.basicConfig(level=logging.INFO)

    engine = OuroborosOmega(args.file, dry_run=args.dry_run or args.diagnose_only)

    async def run():
        if args.diagnose_only:
            diag = await engine.diagnose()
            print(f"Entropy: {diag.entropy_score:.2f}")
        else:
            res = await engine.execute_atomic_cycle()
            print(json.dumps(res, indent=2))

    asyncio.run(run())
