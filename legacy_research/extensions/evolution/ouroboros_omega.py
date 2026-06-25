# [C5-REAL] Exergy-Maximized
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

from legacy_research.extensions.evolution.ast_mutators import (
    _AstAnalyzer,
    _BlockingPatternDetector,
    _DeadCodePurge,
    _DocstringInjector,
    _EntropyAnnihilator,
)

logger = logging.getLogger("cortex.extensions.evolution.ouroboros")


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


class OuroborosOmega:
    """The ACID Code Mutation Engine."""

    def __init__(
        self,
        target_path: str,
        project_root: str = "~/.gemini/antigravity/scratch/Cortex-Persist",
        dry_run: bool = False,
        p0_scan: bool = False,
    ):
        self.target_path = Path(target_path).expanduser().resolve()
        self.project_root = Path(project_root).expanduser().resolve()
        self.dry_run = dry_run
        self.p0_scan = p0_scan

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
        dead_funcs_candidates = {
            f
            for f, callers in called_by.items()
            if not callers
            and f.startswith("_")
            and f != "__init__"
            and f not in analyzer.used_imports
        }
        dead_funcs = set()
        if dead_funcs_candidates:
            import subprocess
            from pathlib import Path

            project_root = Path.cwd()
            cortex_dir = project_root / "cortex"
            tests_dir = project_root / "tests"
            for f in dead_funcs_candidates:
                try:
                    subprocess.check_output(
                        ["rg", "-qw", f, str(cortex_dir), str(tests_dir)], stderr=subprocess.DEVNULL
                    )
                    logger.info("Preserving implicitly used function: %s", f)
                except subprocess.CalledProcessError:
                    dead_funcs.add(f)

        unused_imports = analyzer.imports - analyzer.used_imports

        # Verify unused imports against tests/ directory to prevent systemic necrosis
        if unused_imports:
            import subprocess

            verified_unused = set()
            tests_dir = self.project_root / "tests"
            if tests_dir.exists():
                for imp in unused_imports:
                    try:
                        # Use ripgrep to check if the symbol is used in tests
                        subprocess.check_output(
                            ["rg", "-qw", imp, str(tests_dir)], stderr=subprocess.DEVNULL
                        )
                        # If rg finds it (exit 0), it's used in tests -> preserve it
                        logger.info("Preserving implicitly used import (Test Dependency): %s", imp)
                    except subprocess.CalledProcessError:
                        verified_unused.add(imp)
                unused_imports = verified_unused

        # Calculate Entropy & Exergy (Landauer's Razor)
        # 1 bit of unstructured data ~ k_B T ln(2)
        # We consider unused imports and dead code as pure entropy generation (dS_gen)
        dS_gen = (len(dead_funcs) * 10.0) + (len(unused_imports) * 5.0)

        loc_penalty = max(0, (analyzer.loc - 500) * 0.05)
        complexity_penalty = sum(max(0, c - 15) for c in analyzer.mccabe.values()) * 2.0
        nesting_penalty = sum(max(0, n - 4) for n in analyzer.nesting.values()) * 3.0

        # Total Entropy Score represents structural degradation
        entropy = min(
            100.0,
            loc_penalty + complexity_penalty + dS_gen + nesting_penalty,
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

            # ── Phase 1.5: P0 Vulnerability Extraction (Deepthink-R1 Cluster) ──
            p0_report = None
            if self.p0_scan:
                logger.info("Phase 1.5 [P0 Scan] Dispatching to Deepthink-R1 cluster...")
                try:
                    from legacy_research.extensions.evolution.p0_extractor import P0VulnerabilityExtractor

                    extractor = P0VulnerabilityExtractor()
                    p0_report = await extractor.extract(
                        source_code=self.original_source,
                        diagnosis=base_diagnosis,
                        target_file=str(self.target_path),
                    )
                    logger.info(
                        "Phase 1.5 [P0 Scan] Complete: %d findings (%d critical, %d high)",
                        len(p0_report.findings),
                        p0_report.critical_count,
                        p0_report.high_count,
                    )
                except Exception as e:
                    logger.warning("Phase 1.5 [P0 Scan] Failed: %s", e)

            tree = ast.parse(self.original_source)

            # 2. EXTRACTION
            is_init_py = self.target_path.name == "__init__.py"
            purger = _DeadCodePurge(
                base_diagnosis.dead_interfaces,
                set() if is_init_py else (base_diagnosis.imports - base_diagnosis.used_imports),
            )
            mutated_tree = purger.visit(copy.deepcopy(tree))
            ast.fix_missing_locations(mutated_tree)
            logger.info("Phase 2 [Extraction] Complete.")

            # 3. RECONSTRUCTION
            injector = _DocstringInjector()
            mutated_tree = injector.visit(mutated_tree)
            evasion = _EntropyAnnihilator()
            mutated_tree = evasion.visit(mutated_tree)
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
            except Exception as e:
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

            # ── TERMINAL STATE 4: REMOTE MUTATION (SWARM AST BROADCAST) ──
            if not self.dry_run:
                try:
                    import os
                    import sys

                    # Path to cortex-core relative to cortex/extensions/evolution
                    cortex_core_path = os.path.abspath(
                        os.path.join(os.path.dirname(__file__), "../../../cortex-core")
                    )
                    if cortex_core_path not in sys.path:
                        sys.path.insert(0, cortex_core_path)

                    from persistence import (
                        enqueue_swarm_task,  # pyright: ignore[reportAttributeAccessIssue]
                    )

                    payload = {
                        "type": "AST_MUTATION",
                        "target_file": str(self.target_path.resolve()),
                        "new_source": mutated_source,
                        "signature": hashlib.sha256(mutated_source.encode()).hexdigest(),
                        "entropy_delta": entropy_delta,
                    }
                    enqueue_swarm_task("ouroboros_omega", payload)
                    logger.info(
                        "🌌 [TERMINAL STATE 4] Remote AST mutation broadcasted to Swarm Mesh."
                    )
                except ImportError as e:
                    logger.warning("Could not dispatch remote mutation: %s", e)
                except Exception as e:
                    logger.error("Terminal State 4 dispatch failed: %s", e)

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
            result: dict[str, Any] = {"status": "SUCCESS", "delta": entropy_delta}
            if p0_report is not None:
                result["p0_report"] = p0_report.to_dict()
            return result

        except Exception as e:
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
    parser.add_argument(
        "--p0-scan",
        action="store_true",
        help="Activate P0 vulnerability extractor (Deepthink-R1 cluster)",
    )
    parser.add_argument("-v", "--verbose", action="store_true")

    args = parser.parse_args()
    if args.verbose:
        # setup_cortex_logging()

    engine = OuroborosOmega( # type: ignore
        args.file, dry_run=args.dry_run or args.diagnose_only, p0_scan=args.p0_scan
    )

    async def run():
        if args.diagnose_only:
            diag = await engine.diagnose()
            print(f"Entropy: {diag.entropy_score:.2f}")
        else:
            res = await engine.execute_atomic_cycle()
            print(json.dumps(res, indent=2))

    asyncio.run(run())
