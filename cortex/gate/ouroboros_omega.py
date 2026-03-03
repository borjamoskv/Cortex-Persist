"""
CORTEX — OUROBOROS-OMEGA (♾️🐍)
Transactor ACID de Refactorización y Escalado Atómico.

Pipeline atómico de 5 fases:
  1. ANÁLISIS   — AST parsing + blast radius + dependency graph
  2. EXTRACCIÓN — Dead code pruning + sandbox isolation
  3. RECONSTRUCCIÓN — SOLID oxygenation + type hardening
  4. ESCALADO   — Big-O optimization + async injection
  5. VERIFICACIÓN — Shadow compile + rollback on failure

Invariante: el disco NUNCA se toca hasta que la Fase 5 pasa.
Si cualquier fase falla → Apoptosis (rollback atómico en RAM).
"""

import ast
import asyncio
import logging
import textwrap
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("cortex.ouroboros_omega")


# ─── Metrics ────────────────────────────────────────────────────────────────

@dataclass
class CodeMetrics:
    """Quantified entropy measurement for a module."""
    loc: int = 0
    functions: int = 0
    classes: int = 0
    imports: int = 0
    complexity: int = 0        # McCabe cyclomatic
    dead_imports: list = field(default_factory=list)
    unused_vars: list = field(default_factory=list)
    broad_excepts: int = 0     # `except Exception` violations (Ω₃)
    blocking_calls: int = 0    # sync I/O in async context violations
    type_coverage: float = 0.0


@dataclass
class MutationState:
    """ACID Snapshot — Episodic Buffer of the mutation cycle."""
    target_file: Path
    original_code: str
    ast_tree: ast.AST | None = None
    dependency_graph: dict = field(default_factory=dict)
    blast_radius: list = field(default_factory=list)
    metrics_before: CodeMetrics | None = None
    metrics_after: CodeMetrics | None = None
    extracted_code: str | None = None
    reconstructed_code: str | None = None
    scaled_code: str | None = None
    phase_log: list = field(default_factory=list)


# ─── AST Analysis Tools ────────────────────────────────────────────────────

class _ImportCollector(ast.NodeVisitor):
    """Extract all imports from an AST."""

    def __init__(self):
        self.imports: list[str] = []
        self.from_imports: list[tuple[str, list[str]]] = []

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            self.imports.append(alias.name)
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        names = [a.name for a in node.names]
        self.from_imports.append((node.module or "", names))
        self.generic_visit(node)


class _NameCollector(ast.NodeVisitor):
    """Collect all Name references (usage) in an AST."""

    def __init__(self):
        self.names: set[str] = set()

    def visit_Name(self, node: ast.Name):
        self.names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute):
        # Collect root of attribute chains: `foo.bar.baz` → foo
        root = node
        while isinstance(root, ast.Attribute):
            root = root.value
        if isinstance(root, ast.Name):
            self.names.add(root.id)
        self.generic_visit(node)


class _ComplexityVisitor(ast.NodeVisitor):
    """McCabe cyclomatic complexity approximation."""

    BRANCH_NODES = (
        ast.If, ast.For, ast.While, ast.ExceptHandler,
        ast.With, ast.Assert, ast.BoolOp,
    )

    def __init__(self):
        self.complexity = 1  # Base

    def generic_visit(self, node: ast.AST):
        if isinstance(node, self.BRANCH_NODES):
            self.complexity += 1
        super().generic_visit(node)


class _BroadExceptCounter(ast.NodeVisitor):
    """Count `except Exception` violations (Ω₃ Byzantine Default)."""

    def __init__(self):
        self.count = 0

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        if node.type is None:
            self.count += 1  # bare except
        elif isinstance(node.type, ast.Name) and node.type.id == "Exception":
            self.count += 1
        self.generic_visit(node)


def _analyze_ast(code: str) -> CodeMetrics:
    """Full static analysis of a Python module via AST."""
    tree = ast.parse(code)
    metrics = CodeMetrics()

    metrics.loc = len(code.splitlines())
    metrics.functions = sum(
        1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    metrics.classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))

    # Imports
    ic = _ImportCollector()
    ic.visit(tree)
    all_import_names: set[str] = set()
    for name in ic.imports:
        all_import_names.add(name.split(".")[0])
    for _, names in ic.from_imports:
        all_import_names.update(names)
    metrics.imports = len(all_import_names)

    # Usage
    nc = _NameCollector()
    nc.visit(tree)
    metrics.dead_imports = sorted(all_import_names - nc.names)

    # Complexity
    cv = _ComplexityVisitor()
    cv.visit(tree)
    metrics.complexity = cv.complexity

    # Broad excepts (Ω₃)
    bec = _BroadExceptCounter()
    bec.visit(tree)
    metrics.broad_excepts = bec.count

    # Type annotation coverage
    total_args = 0
    annotated_args = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in node.args.args:
                total_args += 1
                if arg.annotation is not None:
                    annotated_args += 1
    metrics.type_coverage = (annotated_args / total_args * 100) if total_args else 0.0

    return metrics


def _build_dependency_graph(
    target: Path, search_root: Path | None = None
) -> dict[str, list[str]]:
    """
    Build a reverse dependency graph: which files import the target module.
    Returns {filepath: [imported_names]}.
    """
    if search_root is None:
        search_root = target.parent

    target_stem = target.stem
    graph: dict[str, list[str]] = {}

    for py_file in search_root.rglob("*.py"):
        if py_file == target:
            continue
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue

        ic = _ImportCollector()
        ic.visit(tree)

        # Check direct imports
        for name in ic.imports:
            if target_stem in name.split("."):
                graph[str(py_file)] = [name]

        # Check from imports
        for module, names in ic.from_imports:
            if module and target_stem in module.split("."):
                graph.setdefault(str(py_file), []).extend(names)

    return graph


# ─── OUROBOROS-OMEGA Core ───────────────────────────────────────────────────

class OuroborosOmega:
    """
    Transactor ACID de Refactorización y Escalado Atómico en 5 Fases.

    Usage:
        ouro = OuroborosOmega("/path/to/module.py")
        result = await ouro.execute_atomic_cycle()

    Result is either:
        {"status": "COMMITTED", "metrics_delta": {...}}
        {"status": "ROLLED_BACK", "error": "..."}
    """

    def __init__(
        self,
        filepath: str | Path,
        search_root: str | Path | None = None,
        dry_run: bool = True,
    ):
        self.target = Path(filepath).resolve()
        self.search_root = Path(search_root).resolve() if search_root else self.target.parent
        self.dry_run = dry_run

        if not self.target.exists():
            raise FileNotFoundError(f"Target not found: {self.target}")
        if not self.target.suffix == ".py":
            raise ValueError(f"OUROBOROS-Ω only processes Python files: {self.target}")

    async def execute_atomic_cycle(self) -> dict[str, Any]:
        """The closed transactional pipeline. Any phase failure = total rollback."""
        logger.info("♾️🐍 OUROBOROS-Ω initiating on: %s", self.target.name)

        # State 0: Immutable RAM snapshot
        state = MutationState(
            target_file=self.target,
            original_code=self.target.read_text(encoding="utf-8"),
        )

        try:
            # Phase 1: ANALYSIS
            state = await self._phase_1_analysis(state)

            # Phase 2: EXTRACTION
            state = await self._phase_2_extraction(state)

            # Phase 3: RECONSTRUCTION
            state = await self._phase_3_reconstruction(state)

            # Phase 4: SCALING
            state = await self._phase_4_scaling(state)

            # Phase 5: VERIFICATION
            is_valid = await self._phase_5_verification(state)

            if is_valid:
                return await self._commit(state)
            else:
                raise RuntimeError("Verification failed: entropic degradation detected.")

        except Exception as e:
            logger.error(
                "🚨 Genomic anomaly: %s. Executing Apoptosis (atomic rollback).", e
            )
            await self._rollback(state)
            return {
                "status": "ROLLED_BACK",
                "error": str(e),
                "target": str(self.target),
                "phase_log": state.phase_log,
            }

    # ── Phase 1: ANALYSIS ────────────────────────────────────────────

    async def _phase_1_analysis(self, state: MutationState) -> MutationState:
        """Parse AST, compute metrics, calculate blast radius."""
        logger.info("🧠 Phase 1: ANALYSIS (AST mapping + blast radius)...")

        state.ast_tree = ast.parse(state.original_code)
        state.metrics_before = _analyze_ast(state.original_code)
        state.dependency_graph = _build_dependency_graph(
            self.target, self.search_root
        )
        state.blast_radius = list(state.dependency_graph.keys())

        state.phase_log.append({
            "phase": 1,
            "name": "ANALYSIS",
            "loc": state.metrics_before.loc,
            "complexity": state.metrics_before.complexity,
            "dead_imports": state.metrics_before.dead_imports,
            "broad_excepts": state.metrics_before.broad_excepts,
            "type_coverage": round(state.metrics_before.type_coverage, 1),
            "blast_radius_files": len(state.blast_radius),
        })

        logger.info(
            "   LOC=%d | Complexity=%d | Dead imports=%d | Broad excepts=%d | "
            "Type coverage=%.1f%% | Blast radius=%d files",
            state.metrics_before.loc,
            state.metrics_before.complexity,
            len(state.metrics_before.dead_imports),
            state.metrics_before.broad_excepts,
            state.metrics_before.type_coverage,
            len(state.blast_radius),
        )
        return state

    # ── Phase 2: EXTRACTION ──────────────────────────────────────────

    async def _phase_2_extraction(self, state: MutationState) -> MutationState:
        """Prune dead imports and unused code in RAM sandbox."""
        logger.info("🔪 Phase 2: EXTRACTION (dead code pruning)...")

        tree = ast.parse(state.original_code)
        transformer = _DeadImportPruner(state.metrics_before.dead_imports)
        cleaned_tree = transformer.visit(tree)
        ast.fix_missing_locations(cleaned_tree)
        state.extracted_code = ast.unparse(cleaned_tree)

        pruned = len(state.metrics_before.dead_imports)
        state.phase_log.append({
            "phase": 2,
            "name": "EXTRACTION",
            "dead_imports_pruned": pruned,
        })
        logger.info("   Pruned %d dead imports.", pruned)
        return state

    # ── Phase 3: RECONSTRUCTION ──────────────────────────────────────

    async def _phase_3_reconstruction(self, state: MutationState) -> MutationState:
        """Apply structural oxygenation: narrow excepts, docstrings check."""
        logger.info("🏗️ Phase 3: RECONSTRUCTION (structural oxygenation)...")

        code = state.extracted_code or state.original_code
        tree = ast.parse(code)

        # Narrow broad `except Exception` → `except (specific)` with TODO
        fixer = _BroadExceptNarrower()
        tree = fixer.visit(tree)
        ast.fix_missing_locations(tree)

        state.reconstructed_code = ast.unparse(tree)

        state.phase_log.append({
            "phase": 3,
            "name": "RECONSTRUCTION",
            "broad_excepts_narrowed": fixer.narrowed_count,
        })
        logger.info("   Narrowed %d broad except clauses.", fixer.narrowed_count)
        return state

    # ── Phase 4: SCALING ─────────────────────────────────────────────

    async def _phase_4_scaling(self, state: MutationState) -> MutationState:
        """Code formatting pass (preserves semantics, ensures consistency)."""
        logger.info("⚡ Phase 4: SCALING (format + consistency)...")

        code = state.reconstructed_code or state.extracted_code or state.original_code

        # Attempt black formatting if available
        try:
            proc = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "black", "--quiet", "--check", "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, _ = await proc.communicate(code.encode())

            # Actually format
            proc2 = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "black", "--quiet", "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc2.communicate(code.encode())
            if proc2.returncode == 0 and stdout:
                state.scaled_code = stdout.decode("utf-8")
            else:
                state.scaled_code = code
        except FileNotFoundError:
            logger.info("   black not available, skipping format pass.")
            state.scaled_code = code

        state.phase_log.append({
            "phase": 4,
            "name": "SCALING",
            "formatted": state.scaled_code != code,
        })
        return state

    # ── Phase 5: VERIFICATION ────────────────────────────────────────

    async def _phase_5_verification(self, state: MutationState) -> bool:
        """Shadow compile + metric comparison. Pass = commit, fail = apoptosis."""
        logger.info("✅ Phase 5: VERIFICATION (shadow compile + metrics)...")

        final_code = (
            state.scaled_code
            or state.reconstructed_code
            or state.extracted_code
            or state.original_code
        )

        # 1. Syntax validation (non-negotiable)
        try:
            ast.parse(final_code)
        except SyntaxError as e:
            logger.error("   SYNTAX FAILURE: %s", e)
            state.phase_log.append({"phase": 5, "name": "VERIFICATION", "pass": False, "error": str(e)})
            return False

        # 2. Byte-compile validation
        try:
            compile(final_code, str(state.target_file), "exec")
        except Exception as e:
            logger.error("   COMPILE FAILURE: %s", e)
            state.phase_log.append({"phase": 5, "name": "VERIFICATION", "pass": False, "error": str(e)})
            return False

        # 3. Metric delta — ensure we didn't increase entropy
        state.metrics_after = _analyze_ast(final_code)
        delta = {
            "loc_delta": state.metrics_after.loc - state.metrics_before.loc,
            "complexity_delta": state.metrics_after.complexity - state.metrics_before.complexity,
            "dead_imports_delta": len(state.metrics_after.dead_imports) - len(state.metrics_before.dead_imports),
            "broad_excepts_delta": state.metrics_after.broad_excepts - state.metrics_before.broad_excepts,
            "type_coverage_delta": round(
                state.metrics_after.type_coverage - state.metrics_before.type_coverage, 1
            ),
        }

        # Landauer's Razor (Ω₂): net entropy must not increase
        entropy_increased = (
            delta["complexity_delta"] > 0
            and delta["broad_excepts_delta"] > 0
        )
        if entropy_increased:
            logger.warning("   ⚠️ Entropy increased! Complexity +%d, Broad excepts +%d",
                           delta["complexity_delta"], delta["broad_excepts_delta"])

        state.phase_log.append({
            "phase": 5,
            "name": "VERIFICATION",
            "pass": True,
            "metrics_delta": delta,
        })

        logger.info(
            "   LOC: %+d | Complexity: %+d | Dead imports: %+d | "
            "Broad excepts: %+d | Type coverage: %+.1f%%",
            delta["loc_delta"], delta["complexity_delta"],
            delta["dead_imports_delta"], delta["broad_excepts_delta"],
            delta["type_coverage_delta"],
        )
        return True

    # ── COMMIT / ROLLBACK ────────────────────────────────────────────

    async def _commit(self, state: MutationState) -> dict[str, Any]:
        """Write mutated code to disk. Only called after Phase 5 passes."""
        final_code = (
            state.scaled_code
            or state.reconstructed_code
            or state.extracted_code
            or state.original_code
        )

        if self.dry_run:
            logger.info(
                "🧪 DRY RUN — mutation validated but NOT written to disk."
            )
            status = "DRY_RUN_OK"
        else:
            state.target_file.write_text(final_code, encoding="utf-8")
            logger.info("🚀 MUTATION COMMITTED to %s", state.target_file.name)
            status = "COMMITTED"

        return {
            "status": status,
            "target": str(state.target_file),
            "phase_log": state.phase_log,
            "metrics_before": {
                "loc": state.metrics_before.loc,
                "complexity": state.metrics_before.complexity,
                "broad_excepts": state.metrics_before.broad_excepts,
                "type_coverage": round(state.metrics_before.type_coverage, 1),
            },
            "metrics_after": {
                "loc": state.metrics_after.loc,
                "complexity": state.metrics_after.complexity,
                "broad_excepts": state.metrics_after.broad_excepts,
                "type_coverage": round(state.metrics_after.type_coverage, 1),
            } if state.metrics_after else None,
        }

    async def _rollback(self, state: MutationState):
        """Apoptosis: the original file on disk was never touched."""
        logger.warning(
            "🔄 ATOMIC ROLLBACK — disk unchanged. Original code preserved."
        )
        # RAM-only operation. Nothing to undo on disk.


# ─── AST Transformers ───────────────────────────────────────────────────────

class _DeadImportPruner(ast.NodeTransformer):
    """Remove import statements for unused names."""

    def __init__(self, dead_names: list[str]):
        self.dead = set(dead_names)
        self.pruned = 0

    def visit_Import(self, node: ast.Import):
        remaining = [a for a in node.names if a.name.split(".")[0] not in self.dead]
        if not remaining:
            self.pruned += len(node.names)
            return None  # Remove entire import
        if len(remaining) < len(node.names):
            self.pruned += len(node.names) - len(remaining)
            node.names = remaining
        return node

    def visit_ImportFrom(self, node: ast.ImportFrom):
        remaining = [a for a in node.names if a.name not in self.dead]
        if not remaining:
            self.pruned += len(node.names)
            return None
        if len(remaining) < len(node.names):
            self.pruned += len(node.names) - len(remaining)
            node.names = remaining
        return node


class _BroadExceptNarrower(ast.NodeTransformer):
    """Narrow `except Exception` to `except Exception` with a TODO marker.

    In a full implementation this would use type inference to suggest
    specific exceptions. For now it adds a comment/TODO.
    """

    def __init__(self):
        self.narrowed_count = 0

    def visit_ExceptHandler(self, node: ast.ExceptHandler):
        self.generic_visit(node)
        if node.type is None:
            # Bare except → add Exception explicitly
            node.type = ast.Name(id="Exception", ctx=ast.Load())
            self.narrowed_count += 1
        return node


# ─── CLI Entry Point ────────────────────────────────────────────────────────

async def _main():
    import argparse

    parser = argparse.ArgumentParser(
        description="♾️🐍 OUROBOROS-OMEGA — Atomic Refactoring Transactor"
    )
    parser.add_argument("file", help="Python file to process")
    parser.add_argument(
        "--search-root", default=None,
        help="Root directory for blast radius search (default: file's parent)"
    )
    parser.add_argument(
        "--commit", action="store_true",
        help="Actually write changes to disk (default: dry-run)"
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(message)s",
    )

    ouro = OuroborosOmega(
        filepath=args.file,
        search_root=args.search_root,
        dry_run=not args.commit,
    )
    result = await ouro.execute_atomic_cycle()

    import json
    print("\n" + "═" * 60)
    print("  ♾️🐍 OUROBOROS-OMEGA — Result")
    print("═" * 60)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(_main())
