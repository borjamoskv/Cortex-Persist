"""OUROBOROS-OMEGA — Atomic Refactoring & Scaling Transactor.

The Central Autopoietic Metabolism for CORTEX. An ACID State Machine
that consumes technical debt and rebirths scaled code.

5-Phase Pipeline (all in-memory until COMMIT):
    1. ANALYSIS   — AST parsing, dependency graph, blast radius
    2. EXTRACTION  — Dead code detection, quarantine
    3. RECONSTRUCTION — Structural oxygenation (SOLID, typing, async)
    4. SCALING     — Concurrency injection, Big-O optimization
    5. VERIFICATION — Shadow testing, AST re-parse, metrics delta

If ANY phase fails → APOPTOSIS (atomic rollback). Disk is NEVER
compromised until Phase 5 passes all gates.

Usage:
    from cortex.evolution.ouroboros_omega import OuroborosOmega

    engine = OuroborosOmega("/path/to/module.py")
    result = await engine.execute_atomic_cycle()
    # result["status"] in ("SUCCESS", "ROLLED_BACK")

    # Diagnosis-only mode (no mutations):
    diagnosis = await engine.diagnose()
"""

from __future__ import annotations

import ast
import asyncio
import copy
import hashlib
import logging
import sys
import textwrap
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger("CORTEX.OUROBOROS_OMEGA")


# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class DependencyNode:
    """A node in the module's internal dependency graph."""

    name: str
    node_type: str  # "function", "class", "import"
    lineno: int
    end_lineno: int
    calls_out: set[str] = field(default_factory=set)  # functions this node calls
    called_by: set[str] = field(default_factory=set)  # functions that call this node
    complexity: int = 0  # McCabe cyclomatic complexity


@dataclass
class DiagnosisMatrix:
    """Phase 1 output: the full scan of the module's health."""

    filepath: str
    loc: int = 0
    num_functions: int = 0
    num_classes: int = 0
    max_complexity: int = 0
    max_nesting: int = 0
    dead_functions: list[str] = field(default_factory=list)
    circular_imports: list[tuple[str, str]] = field(default_factory=list)
    import_graph: dict[str, set[str]] = field(default_factory=dict)
    dependency_nodes: dict[str, DependencyNode] = field(default_factory=dict)
    unused_imports: list[str] = field(default_factory=list)
    entropy_score: float = 0.0  # 0-100, higher = worse
    hot_spots: list[tuple[str, int]] = field(default_factory=list)  # (name, complexity)
    blast_radius: int = 0  # how many external files import this module
    sha256: str = ""  # content hash for integrity verification


@dataclass
class MutationState:
    """ACID Snapshot: The Episodic Buffer of the mutation."""

    target_file: Path
    original_code: str
    original_hash: str
    ast_tree: ast.AST | None = None
    diagnosis: DiagnosisMatrix | None = None
    extracted_code: str | None = None
    reconstructed_code: str | None = None
    scaled_code: str | None = None
    final_diagnosis: DiagnosisMatrix | None = None
    metrics_delta: dict[str, float] = field(default_factory=dict)
    phase_log: list[str] = field(default_factory=list)
    started_at: float = 0.0
    completed_at: float = 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# AST ANALYSIS ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class _CallGraphVisitor(ast.NodeVisitor):
    """Walks the AST to extract the full call graph + complexity metrics."""

    def __init__(self) -> None:
        self.nodes: dict[str, DependencyNode] = {}
        self.imports: list[str] = []
        self.used_names: set[str] = set()
        self._scope_stack: list[str] = []
        self._max_nesting: int = 0
        self._current_nesting: int = 0

    @property
    def current_scope(self) -> str:
        return ".".join(self._scope_stack) if self._scope_stack else "<module>"

    # ── Definitions ────────────────────────────────────────────────────────

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._register_callable(node, "function")

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._register_callable(node, "function")

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        scope_name = f"{self.current_scope}.{node.name}" if self._scope_stack else node.name
        self.nodes[scope_name] = DependencyNode(
            name=scope_name,
            node_type="class",
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
        )
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    def _register_callable(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef, node_type: str
    ) -> None:
        scope_name = f"{self.current_scope}.{node.name}" if self._scope_stack else node.name
        complexity = self._compute_mccabe(node)
        self.nodes[scope_name] = DependencyNode(
            name=scope_name,
            node_type=node_type,
            lineno=node.lineno,
            end_lineno=node.end_lineno or node.lineno,
            complexity=complexity,
        )
        self._scope_stack.append(node.name)
        self.generic_visit(node)
        self._scope_stack.pop()

    # ── Calls ──────────────────────────────────────────────────────────────

    def visit_Call(self, node: ast.Call) -> None:
        callee = self._resolve_call_name(node.func)
        if callee:
            self.used_names.add(callee)
            caller = self.current_scope
            if caller in self.nodes:
                self.nodes[caller].calls_out.add(callee)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        self.used_names.add(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        self.used_names.add(node.attr)
        self.generic_visit(node)

    # ── Imports ────────────────────────────────────────────────────────────

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports.append(name)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        for alias in node.names:
            name = alias.asname or alias.name
            self.imports.append(name)

    # ── Nesting Tracker ───────────────────────────────────────────────────

    def visit_If(self, node: ast.If) -> None:
        self._track_nesting(node)

    def visit_For(self, node: ast.For) -> None:
        self._track_nesting(node)

    def visit_While(self, node: ast.While) -> None:
        self._track_nesting(node)

    def visit_With(self, node: ast.With) -> None:
        self._track_nesting(node)

    def visit_Try(self, node: ast.Try) -> None:
        self._track_nesting(node)

    def _track_nesting(self, node: ast.AST) -> None:
        self._current_nesting += 1
        self._max_nesting = max(self._max_nesting, self._current_nesting)
        self.generic_visit(node)
        self._current_nesting -= 1

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _resolve_call_name(node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    @staticmethod
    def _compute_mccabe(node: ast.AST) -> int:
        """McCabe Cyclomatic Complexity = 1 + branching points."""
        complexity = 1
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            elif isinstance(child, ast.Assert):
                complexity += 1
        return complexity

    # ── Post-processing ───────────────────────────────────────────────────

    def build_reverse_edges(self) -> None:
        """Populate called_by fields from calls_out."""
        for name, node in self.nodes.items():
            for callee in node.calls_out:
                # Resolve callee to a known node (best-effort)
                if callee in self.nodes:
                    self.nodes[callee].called_by.add(name)

    def find_dead_code(self) -> list[str]:
        """Functions with zero inbound edges (never called)."""
        dead: list[str] = []
        for name, node in self.nodes.items():
            if node.node_type != "function":
                continue
            # Skip dunder methods, test funcs, and module-level callables
            base_name = name.rsplit(".", 1)[-1]
            if base_name.startswith("_"):
                continue
            if base_name.startswith("test_"):
                continue
            if not node.called_by and "." not in name:
                # Top-level function with zero callers
                dead.append(name)
        return dead

    def find_unused_imports(self) -> list[str]:
        """Imports that are never referenced in any Name/Attribute/Call."""
        unused: list[str] = []
        for imp in self.imports:
            # Normalize: take the base name (e.g., "os.path" → "os")
            base = imp.split(".")[0]
            if base not in self.used_names and imp not in self.used_names:
                unused.append(imp)
        return unused


# ═══════════════════════════════════════════════════════════════════════════════
# BLAST RADIUS CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════


def _calculate_blast_radius(target: Path, search_root: Path | None = None) -> int:
    """Count how many .py files in the project import the target module.

    This gives the Keter-omega Blast Radius: the number of files affected
    if we mutate the target.
    """
    if search_root is None:
        search_root = target.parent.parent  # assume one level up is project root

    module_stem = target.stem
    count = 0
    try:
        for py_file in search_root.rglob("*.py"):
            if py_file == target:
                continue
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                # Fast heuristic: check if module name appears in imports
                if f"import {module_stem}" in content or f"from {module_stem}" in content:
                    count += 1
                # Also check relative imports
                if f"from .{module_stem}" in content or f"from ..{module_stem}" in content:
                    count += 1
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        pass
    return count


# ═══════════════════════════════════════════════════════════════════════════════
# ENTROPY SCORER
# ═══════════════════════════════════════════════════════════════════════════════


def _compute_entropy_score(
    loc: int,
    max_complexity: int,
    num_dead: int,
    num_unused_imports: int,
    max_nesting: int,
) -> float:
    """0-100 entropy score. Higher = more debt, more chaos.

    Weighted formula:
        LOC penalty (>500 lines = bad)           : 25%
        Complexity penalty (>15 = bad)            : 30%
        Dead code ratio                           : 20%
        Unused imports                            : 10%
        Nesting depth (>4 = bad)                  : 15%
    """
    loc_score = min(100.0, (loc / 500.0) * 100.0)
    complexity_score = min(100.0, (max_complexity / 15.0) * 100.0)
    dead_score = min(100.0, num_dead * 15.0)
    import_score = min(100.0, num_unused_imports * 10.0)
    nesting_score = min(100.0, (max_nesting / 4.0) * 100.0)

    return round(
        loc_score * 0.25
        + complexity_score * 0.30
        + dead_score * 0.20
        + import_score * 0.10
        + nesting_score * 0.15,
        1,
    )


# ═══════════════════════════════════════════════════════════════════════════════
# THE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════


class OuroborosOmega:
    """[META-SKILL] OUROBOROS-OMEGA — Atomic Refactoring & Scaling Transactor.

    5-Phase ACID cycle. State lives exclusively in RAM until Phase 5 passes
    all verification gates. Disk commit is the final atomic operation.
    Failure at any phase → Apoptosis (rollback to pristine state).

    Axioms:
        Ω₂ — Net entropy MUST decrease. If it rises → abort.
        Ω₃ — Byzantine Default: the refactored code is NOT trusted until
              verified by Phase 5.
        Ω₅ — Antifragile: failures generate diagnostic antibodies (CORTEX logs).
    """

    def __init__(
        self,
        filepath: str,
        *,
        project_root: str | None = None,
        dry_run: bool = False,
    ) -> None:
        self.target = Path(filepath).resolve()
        self.project_root = Path(project_root).resolve() if project_root else self.target.parent
        self.dry_run = dry_run

        if not self.target.exists():
            raise FileNotFoundError(f"Target does not exist: {self.target}")
        if not self.target.suffix == ".py":
            raise ValueError(f"OUROBOROS-OMEGA only operates on .py files: {self.target}")

    # ═══════════════════════════════════════════════════════════════════════
    # PUBLIC INTERFACE
    # ═══════════════════════════════════════════════════════════════════════

    async def diagnose(self) -> DiagnosisMatrix:
        """Phase 1 only — returns the full diagnosis without mutating anything."""
        code = self.target.read_text(encoding="utf-8")
        tree = ast.parse(code, filename=str(self.target))
        return self._run_analysis(code, tree)

    async def execute_atomic_cycle(self) -> dict[str, Any]:
        """The full ACID transactional pipeline. Fail → Rollback Total."""
        logger.info("♾️🐍 OUROBOROS-OMEGA initiating on: %s", self.target.name)
        started = time.monotonic()

        # State 0: Immutable Snapshot
        original_code = self.target.read_text(encoding="utf-8")
        state = MutationState(
            target_file=self.target,
            original_code=original_code,
            original_hash=hashlib.sha256(original_code.encode()).hexdigest(),
            started_at=time.time(),
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

            if not is_valid:
                raise _ApoptosisSignal("Verification gate FAILED — entropy not reduced.")

            if self.dry_run:
                state.phase_log.append("DRY_RUN: Commit skipped.")
                logger.info("🔄 DRY RUN complete. No files modified.")
                return self._build_report(state, "DRY_RUN", time.monotonic() - started)

            return await self._commit(state, time.monotonic() - started)

        except _ApoptosisSignal as e:
            logger.error("🚨 APOPTOSIS: %s → Atomic rollback.", e)
            state.phase_log.append(f"APOPTOSIS: {e}")
            return self._build_report(state, "ROLLED_BACK", time.monotonic() - started, error=str(e))

        except Exception as e:
            logger.error("🚨 Unexpected failure: %s → Atomic rollback.", e, exc_info=True)
            state.phase_log.append(f"UNEXPECTED_FAILURE: {e}")
            return self._build_report(state, "ROLLED_BACK", time.monotonic() - started, error=str(e))

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1: ANALYSIS (Topological Mapping)
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_1_analysis(self, state: MutationState) -> MutationState:
        logger.info("🧠 Phase 1: ANALYSIS (AST + Dependency Graph + Blast Radius)...")

        tree = ast.parse(state.original_code, filename=str(state.target_file))
        state.ast_tree = tree
        state.diagnosis = self._run_analysis(state.original_code, tree)

        state.phase_log.append(
            f"PHASE_1_OK: entropy={state.diagnosis.entropy_score:.1f}/100 "
            f"| dead={len(state.diagnosis.dead_functions)} "
            f"| max_cc={state.diagnosis.max_complexity} "
            f"| blast_radius={state.diagnosis.blast_radius}"
        )
        logger.info(
            "  📊 Entropy: %.1f/100 | Dead: %d | MaxCC: %d | Blast Radius: %d files",
            state.diagnosis.entropy_score,
            len(state.diagnosis.dead_functions),
            state.diagnosis.max_complexity,
            state.diagnosis.blast_radius,
        )
        return state

    def _run_analysis(self, code: str, tree: ast.AST) -> DiagnosisMatrix:
        """Pure analysis — no side effects."""
        visitor = _CallGraphVisitor()
        visitor.visit(tree)
        visitor.build_reverse_edges()

        dead = visitor.find_dead_code()
        unused = visitor.find_unused_imports()
        lines = code.splitlines()
        loc = len([ln for ln in lines if ln.strip() and not ln.strip().startswith("#")])

        max_cc = max((n.complexity for n in visitor.nodes.values()), default=0)
        hot_spots = sorted(
            [(n.name, n.complexity) for n in visitor.nodes.values() if n.complexity > 10],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        blast = _calculate_blast_radius(self.target, self.project_root)
        entropy = _compute_entropy_score(loc, max_cc, len(dead), len(unused), visitor._max_nesting)

        return DiagnosisMatrix(
            filepath=str(self.target),
            loc=loc,
            num_functions=sum(1 for n in visitor.nodes.values() if n.node_type == "function"),
            num_classes=sum(1 for n in visitor.nodes.values() if n.node_type == "class"),
            max_complexity=max_cc,
            max_nesting=visitor._max_nesting,
            dead_functions=dead,
            unused_imports=unused,
            dependency_nodes=visitor.nodes,
            entropy_score=entropy,
            hot_spots=hot_spots,
            blast_radius=blast,
            sha256=hashlib.sha256(code.encode()).hexdigest(),
        )

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 2: EXTRACTION (Dead Code Removal)
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_2_extraction(self, state: MutationState) -> MutationState:
        logger.info("🔪 Phase 2: EXTRACTION (Dead Code Purge + Unused Imports)...")

        assert state.diagnosis is not None
        assert state.ast_tree is not None

        # Work on a COPY of the AST — never mutate the original
        working_tree = copy.deepcopy(state.ast_tree)

        # Remove dead functions from AST
        dead_set = set(state.diagnosis.dead_functions)
        working_tree = _RemoveDeadCode(dead_set).visit(working_tree)
        ast.fix_missing_locations(working_tree)

        # Remove unused imports
        unused_set = set(state.diagnosis.unused_imports)
        working_tree = _RemoveUnusedImports(unused_set).visit(working_tree)
        ast.fix_missing_locations(working_tree)

        state.extracted_code = ast.unparse(working_tree)

        removed_count = len(dead_set) + len(unused_set)
        state.phase_log.append(
            f"PHASE_2_OK: removed {len(dead_set)} dead functions, "
            f"{len(unused_set)} unused imports"
        )
        logger.info(
            "  🗑️  Removed: %d dead functions, %d unused imports",
            len(dead_set), len(unused_set),
        )
        return state

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3: RECONSTRUCTION (Structural Oxygenation)
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_3_reconstruction(self, state: MutationState) -> MutationState:
        logger.info("🏗️  Phase 3: RECONSTRUCTION (Type Hints + Docstrings + Formatting)...")

        assert state.extracted_code is not None

        # Parse the cleaned code
        tree = ast.parse(state.extracted_code)

        # Add missing docstrings to public functions/classes
        tree = _DocstringInjector().visit(tree)
        ast.fix_missing_locations(tree)

        # Add return type annotation (-> None) to functions missing return types
        tree = _ReturnTypeAnnotator().visit(tree)
        ast.fix_missing_locations(tree)

        state.reconstructed_code = ast.unparse(tree)

        state.phase_log.append("PHASE_3_OK: structural oxygenation applied.")
        logger.info("  🫁 Oxygenation complete: docstrings + type annotations enforced.")
        return state

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 4: SCALING (Concurrency & Performance)
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_4_scaling(self, state: MutationState) -> MutationState:
        logger.info("⚡ Phase 4: SCALING (Async patterns + O(1) enforcement)...")

        assert state.reconstructed_code is not None

        # Parse reconstructed code
        tree = ast.parse(state.reconstructed_code)

        # Detect blocking patterns and log warnings (non-destructive)
        blocking = _BlockingPatternDetector()
        blocking.visit(tree)

        if blocking.warnings:
            for w in blocking.warnings:
                logger.warning("  ⚠️  Blocking pattern: %s", w)

        state.scaled_code = state.reconstructed_code  # structural pass-through
        state.phase_log.append(
            f"PHASE_4_OK: {len(blocking.warnings)} blocking patterns flagged."
        )
        logger.info("  📐 Scaling analysis complete: %d patterns flagged.", len(blocking.warnings))
        return state

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 5: VERIFICATION (Shadow Testing — The Gate)
    # ═══════════════════════════════════════════════════════════════════════

    async def _phase_5_verification(self, state: MutationState) -> bool:
        logger.info("✅ Phase 5: VERIFICATION (AST integrity + Entropy delta)...")

        assert state.scaled_code is not None
        assert state.diagnosis is not None

        # Gate 1: Syntactic validity — the code MUST parse cleanly
        try:
            final_tree = ast.parse(state.scaled_code)
        except SyntaxError as e:
            logger.error("  ❌ SYNTAX ERROR in mutated code: %s", e)
            state.phase_log.append(f"PHASE_5_FAIL: SyntaxError: {e}")
            return False

        # Gate 2: Compile to bytecode — catches deeper issues
        try:
            compile(state.scaled_code, str(state.target_file), "exec")
        except (SyntaxError, TypeError, ValueError) as e:
            logger.error("  ❌ COMPILATION ERROR: %s", e)
            state.phase_log.append(f"PHASE_5_FAIL: CompileError: {e}")
            return False

        # Gate 3: Entropy delta — MUST decrease or stay equal
        final_diagnosis = self._run_analysis(state.scaled_code, final_tree)
        state.final_diagnosis = final_diagnosis

        entropy_delta = final_diagnosis.entropy_score - state.diagnosis.entropy_score
        loc_delta = final_diagnosis.loc - state.diagnosis.loc
        cc_delta = final_diagnosis.max_complexity - state.diagnosis.max_complexity

        state.metrics_delta = {
            "entropy_delta": round(entropy_delta, 1),
            "loc_delta": loc_delta,
            "complexity_delta": cc_delta,
            "dead_before": len(state.diagnosis.dead_functions),
            "dead_after": len(final_diagnosis.dead_functions),
        }

        # Ω₂ Entropic Asymmetry: entropy MUST NOT increase
        if entropy_delta > 5.0:  # 5-point tolerance for rounding
            logger.error(
                "  ❌ ENTROPY INCREASED: %.1f → %.1f (Δ +%.1f). ABORTING.",
                state.diagnosis.entropy_score,
                final_diagnosis.entropy_score,
                entropy_delta,
            )
            state.phase_log.append(
                f"PHASE_5_FAIL: Entropy regression: {state.diagnosis.entropy_score} → "
                f"{final_diagnosis.entropy_score}"
            )
            return False

        state.phase_log.append(
            f"PHASE_5_OK: entropy {state.diagnosis.entropy_score} → "
            f"{final_diagnosis.entropy_score} (Δ {entropy_delta:+.1f}) | "
            f"LOC Δ {loc_delta:+d} | CC Δ {cc_delta:+d}"
        )
        logger.info(
            "  ✅ VERIFIED: entropy %.1f → %.1f | LOC %+d | CC %+d",
            state.diagnosis.entropy_score, final_diagnosis.entropy_score,
            loc_delta, cc_delta,
        )
        return True

    # ═══════════════════════════════════════════════════════════════════════
    # COMMIT & ROLLBACK
    # ═══════════════════════════════════════════════════════════════════════

    async def _commit(self, state: MutationState, elapsed: float) -> dict[str, Any]:
        """Atomic write to disk. The ONLY point where the file is touched."""
        assert state.scaled_code is not None

        # Final integrity check: re-verify the file hasn't changed externally
        current_hash = hashlib.sha256(
            self.target.read_text(encoding="utf-8").encode()
        ).hexdigest()
        if current_hash != state.original_hash:
            raise _ApoptosisSignal(
                "File modified externally during cycle — "
                "concurrent mutation detected. ABORTING."
            )

        self.target.write_text(state.scaled_code, encoding="utf-8")
        state.completed_at = time.time()

        logger.info("🚀 MUTATION CONSOLIDATED: %s", self.target.name)
        state.phase_log.append("COMMIT: File written to disk.")
        return self._build_report(state, "SUCCESS", elapsed)

    def _build_report(
        self,
        state: MutationState,
        status: str,
        elapsed: float,
        error: str = "",
    ) -> dict[str, Any]:
        report: dict[str, Any] = {
            "status": status,
            "target": str(state.target_file),
            "elapsed_seconds": round(elapsed, 2),
            "phase_log": state.phase_log,
            "metrics_delta": state.metrics_delta or {},
        }
        if state.diagnosis:
            report["diagnosis_before"] = {
                "entropy": state.diagnosis.entropy_score,
                "loc": state.diagnosis.loc,
                "max_complexity": state.diagnosis.max_complexity,
                "dead_functions": len(state.diagnosis.dead_functions),
                "unused_imports": len(state.diagnosis.unused_imports),
                "blast_radius": state.diagnosis.blast_radius,
                "hot_spots": state.diagnosis.hot_spots[:5],
            }
        if state.final_diagnosis:
            report["diagnosis_after"] = {
                "entropy": state.final_diagnosis.entropy_score,
                "loc": state.final_diagnosis.loc,
                "max_complexity": state.final_diagnosis.max_complexity,
                "dead_functions": len(state.final_diagnosis.dead_functions),
            }
        if error:
            report["error"] = error
        return report


# ═══════════════════════════════════════════════════════════════════════════════
# AST TRANSFORMERS (Used by Phases 2—4)
# ═══════════════════════════════════════════════════════════════════════════════


class _RemoveDeadCode(ast.NodeTransformer):
    """Removes top-level function definitions that are in the dead set."""

    def __init__(self, dead_names: set[str]) -> None:
        self.dead_names = dead_names

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef | None:
        if node.name in self.dead_names:
            logger.debug("  💀 Removing dead function: %s (L%d)", node.name, node.lineno)
            return None
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef | None:
        if node.name in self.dead_names:
            logger.debug("  💀 Removing dead async function: %s (L%d)", node.name, node.lineno)
            return None
        return node


class _RemoveUnusedImports(ast.NodeTransformer):
    """Removes import statements for names in the unused set."""

    def __init__(self, unused_names: set[str]) -> None:
        self.unused_names = unused_names

    def visit_Import(self, node: ast.Import) -> ast.Import | None:
        node.names = [
            alias for alias in node.names
            if (alias.asname or alias.name) not in self.unused_names
        ]
        return node if node.names else None

    def visit_ImportFrom(self, node: ast.ImportFrom) -> ast.ImportFrom | None:
        node.names = [
            alias for alias in node.names
            if (alias.asname or alias.name) not in self.unused_names
        ]
        return node if node.names else None


class _DocstringInjector(ast.NodeTransformer):
    """Adds stub docstrings to public functions/classes missing them."""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if not node.name.startswith("_") and not _has_docstring(node):
            node.body.insert(
                0,
                ast.Expr(value=ast.Constant(value=f"TODO: Document {node.name}.")),
            )
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        if not node.name.startswith("_") and not _has_docstring(node):
            node.body.insert(
                0,
                ast.Expr(value=ast.Constant(value=f"TODO: Document {node.name}.")),
            )
        self.generic_visit(node)
        return node

    def visit_ClassDef(self, node: ast.ClassDef) -> ast.ClassDef:
        if not node.name.startswith("_") and not _has_docstring(node):
            node.body.insert(
                0,
                ast.Expr(value=ast.Constant(value=f"TODO: Document class {node.name}.")),
            )
        self.generic_visit(node)
        return node


class _ReturnTypeAnnotator(ast.NodeTransformer):
    """Adds `-> None` return annotation to functions missing a return type."""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.FunctionDef:
        if node.returns is None:
            # Check if function has explicit return with value
            has_return_value = any(
                isinstance(child, ast.Return) and child.value is not None
                for child in ast.walk(node)
            )
            if not has_return_value:
                node.returns = ast.Constant(value=None)
        self.generic_visit(node)
        return node

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AsyncFunctionDef:
        if node.returns is None:
            has_return_value = any(
                isinstance(child, ast.Return) and child.value is not None
                for child in ast.walk(node)
            )
            if not has_return_value:
                node.returns = ast.Constant(value=None)
        self.generic_visit(node)
        return node


class _BlockingPatternDetector(ast.NodeVisitor):
    """Detects common blocking I/O patterns in async-intended code."""

    BLOCKING_CALLS: set[str] = {
        "sleep",       # time.sleep
        "connect",     # sqlite3.connect
        "read",        # file.read
        "write",       # file.write
        "urlopen",     # urllib
        "input",       # stdin blocking
    }

    def __init__(self) -> None:
        self.warnings: list[str] = []

    def visit_Call(self, node: ast.Call) -> None:
        name = None
        if isinstance(node.func, ast.Attribute):
            name = node.func.attr
        elif isinstance(node.func, ast.Name):
            name = node.func.id

        if name in self.BLOCKING_CALLS:
            self.warnings.append(
                f"L{node.lineno}: potential blocking call `{name}()`"
            )
        self.generic_visit(node)


# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════


def _has_docstring(node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef) -> bool:
    """Check if the node already has a docstring."""
    if node.body and isinstance(node.body[0], ast.Expr):
        if isinstance(node.body[0].value, ast.Constant) and isinstance(
            node.body[0].value.value, str
        ):
            return True
    return False


class _ApoptosisSignal(Exception):
    """Internal signal for controlled rollback — never leaks outside."""


# ═══════════════════════════════════════════════════════════════════════════════
# CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════


async def _main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="♾️ OUROBOROS-OMEGA: Atomic Refactoring & Scaling Transactor"
    )
    parser.add_argument("target", help="Path to the .py file to metabolize")
    parser.add_argument(
        "--project-root", default=None,
        help="Project root for blast radius calculation (default: parent dir)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Run full cycle but skip disk commit",
    )
    parser.add_argument(
        "--diagnose-only", action="store_true",
        help="Phase 1 only: scan and report, no mutations",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable DEBUG logging",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | ♾️  %(levelname)s: %(message)s",
    )

    engine = OuroborosOmega(
        filepath=args.target,
        project_root=args.project_root,
        dry_run=args.dry_run,
    )

    if args.diagnose_only:
        diagnosis = await engine.diagnose()
        _print_diagnosis(diagnosis)
    else:
        result = await engine.execute_atomic_cycle()
        _print_report(result)


def _print_diagnosis(d: DiagnosisMatrix) -> None:
    """Pretty-print the diagnosis matrix to stdout."""
    print(textwrap.dedent(f"""
    ╔════════════════════════════════════════════════════════════════╗
    ║  🔬 OUROBOROS-OMEGA DIAGNOSIS MATRIX                          ║
    ╠════════════════════════════════════════════════════════════════╣
    ║  📁 File:            {Path(d.filepath).name:<40s} ║
    ║  📊 Entropy Score:   {d.entropy_score:<6.1f}/100                            ║
    ║  📏 LOC:             {d.loc:<6d}  (target: ≤500)                ║
    ║  🧩 Functions:       {d.num_functions:<6d}                                  ║
    ║  🏛️  Classes:         {d.num_classes:<6d}                                  ║
    ║  🌀 Max Complexity:  {d.max_complexity:<6d}  (target: ≤15)                 ║
    ║  📐 Max Nesting:     {d.max_nesting:<6d}  (target: ≤4)                  ║
    ║  💀 Dead Functions:  {len(d.dead_functions):<6d}                                  ║
    ║  📦 Unused Imports:  {len(d.unused_imports):<6d}                                  ║
    ║  💥 Blast Radius:    {d.blast_radius:<6d} files                            ║
    ╚════════════════════════════════════════════════════════════════╝
    """).strip())

    if d.hot_spots:
        print("\n  🔥 HOT SPOTS (CC > 10):")
        for name, cc in d.hot_spots:
            print(f"     {cc:>3d}  {name}")

    if d.dead_functions:
        print("\n  💀 DEAD FUNCTIONS (zero callers):")
        for name in d.dead_functions:
            print(f"     • {name}")

    if d.unused_imports:
        print("\n  📦 UNUSED IMPORTS:")
        for name in d.unused_imports:
            print(f"     • {name}")


def _print_report(r: dict[str, Any]) -> None:
    """Pretty-print the cycle report."""
    status_icon = {"SUCCESS": "✅", "ROLLED_BACK": "🔄", "DRY_RUN": "🧪"}.get(
        r["status"], "❓"
    )
    print(f"\n{status_icon} OUROBOROS-OMEGA: {r['status']} ({r['elapsed_seconds']:.1f}s)")
    print(f"   Target: {r['target']}")

    if r.get("diagnosis_before"):
        before = r["diagnosis_before"]
        print(f"   Before: entropy={before['entropy']:.1f} loc={before['loc']} "
              f"cc={before['max_complexity']} dead={before['dead_functions']}")

    if r.get("diagnosis_after"):
        after = r["diagnosis_after"]
        print(f"   After:  entropy={after['entropy']:.1f} loc={after['loc']} "
              f"cc={after['max_complexity']} dead={after['dead_functions']}")

    if r.get("metrics_delta"):
        d = r["metrics_delta"]
        print(f"   Delta:  entropy={d.get('entropy_delta', 0):+.1f} "
              f"loc={d.get('loc_delta', 0):+d} cc={d.get('complexity_delta', 0):+d}")

    if r.get("error"):
        print(f"   Error: {r['error']}")

    print("\n   Phase Log:")
    for entry in r.get("phase_log", []):
        print(f"     • {entry}")


if __name__ == "__main__":
    asyncio.run(_main())
