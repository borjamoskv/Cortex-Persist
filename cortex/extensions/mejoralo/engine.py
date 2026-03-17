"""MEJORAlo Engine implementation."""

<<<<<<< HEAD
from pathlib import Path
from typing import Any

from cortex.engine import CortexEngine

from .heal import heal_proj
from .scan import MejoraloScanner, ScanResult
from .utils import detect_stack


class MejoraloEngine:
    """
    MEJORAlo: Continuous Improvement Engine for CORTEX.
    Unifies scanning, healing, and shipping of code improvements.
    """

    def __init__(self, engine: CortexEngine):
        self.engine = engine
        self.scanner = MejoraloScanner()
=======
import logging
from pathlib import Path
from typing import Any, Optional

from cortex.engine import CortexEngine

from .constants import INMEJORABLE_SCORE
from .heal import heal_project
from .ledger import get_history, get_scars, record_scar, record_session
from .models import ScanResult, ShipResult
from .scan import scan
from .ship import check_ship_gate
from .utils import detect_stack

__all__ = ["MejoraloEngine"]

logger = logging.getLogger("cortex.extensions.mejoralo")


class MejoraloEngine:
    """MEJORAlo v8.0 engine — native CORTEX integration. Relentless mode."""

    def __init__(self, engine: CortexEngine):
        self.engine = engine

    # ── Fase 0: Stack Detection ──────────────────────────────────────

    @staticmethod
    def detect_stack(path: str | Path) -> str:
        """Detect project stack from marker files."""
        return detect_stack(path)

    # ── Fase 2: X-Ray 13D Scan ───────────────────────────────────────
>>>>>>> origin/main

    def scan(
        self, project: str, path: str | Path, deep: bool = False, brutal: bool = False
    ) -> ScanResult:
<<<<<<< HEAD
        """Scan a project or file for improvement opportunities."""
        return self.scanner.scan_project(project, path, deep=deep, brutal=brutal)

    def heal(
        self,
        project: str,
        path: str | Path,
        target_score: int,
        scan_result: ScanResult,
    ) -> bool:
        """Apply automated healing to identified antipatterns."""
        return heal_proj(project, path, target_score, scan_result, engine=self)
=======
        """
        Execute X-Ray 13D scan on a project directory.
        """
        return scan(project, path, deep, brutal)

    def heal(
        self, project: str, path: str | Path, target_score: int, scan_result: ScanResult
    ) -> bool:
        """
        Trigger the autonomous healing to refactor problematic files, test them and commit.
        """
        return heal_project(project, path, target_score, scan_result, engine=self)
>>>>>>> origin/main

    def relentless_heal(
        self,
        project: str,
        path: str | Path,
        scan_result: ScanResult,
<<<<<<< HEAD
        target_score: int = 95,
    ) -> bool:
        """♾️ INMEJORABLE: no para hasta alcanzar el score objetivo."""
        return heal_proj(project, path, target_score, scan_result, engine=self)

    def ship_gate(self, project: str, path: str | Path) -> Any:
        """Verify and seal code improvements via Ship Gate."""
        from .ship import ship_gate

        return ship_gate(project, path)

    def record_session(
        self, project: str, score_before: int, score_after: int, actions: list[str]
    ) -> int:
        """Record a Mejoralo session in the fact ledger."""
        # Implementation depends on CortexEngine's fact storage
        # This is a placeholder for the actual implementation
        return 0

    def history(self, project: str, limit: int = 10) -> list[dict[str, Any]]:
        """Retrieve historical Mejoralo sessions for a project."""
        res = self.engine.recall_sync(
            project=project,
            tags=["mejoralo"],
            limit=limit,
        )
        return res if isinstance(res, list) else []

    def scars(
        self, project: str, file_path: str, limit: int = 10
    ) -> list[dict[str, Any]]:
        """Retrieve historical taints (scars) for a specific file."""
        res = self.engine.recall_sync(
            project=project,
            tags=["mejoralo", "taint"],
            limit=limit,
        )
        return res if isinstance(res, list) else []

    def record_scar(self, project: str, file_path: str, reason: str) -> None:
        """Record a scar (failure/taint evidence) in the CORTEX ledger."""
        self.engine.store_sync(
            project=project,
            content=f"[MEJORAlo SCAR] {file_path}: {reason}",
            fact_type="error",
            tags=["mejoralo", "scar", "investigation"],
            meta={"file_path": file_path, "reason": reason},
        )

    def awwwards_fix(self, project: str, path: str | Path) -> bool:
        """Apply Awwwards-grade UI/UX fixes."""
        return False

    @staticmethod
    def detect_stack(path: str | Path) -> str:
        """Detect project stack from marker files."""
        return detect_stack(path)
=======
        target_score: Optional[int] = None,
    ) -> bool:
        """
        INMEJORABLE mode — heal until score >= 95 (or custom target).

        Does NOT stop until the code is inmejorable or stagnation is terminal.
        Uses escalating strategies: Normal → Aggressive → Nuclear.
        """
        effective_target = target_score if target_score is not None else INMEJORABLE_SCORE
        logger.info(
            "Relentless heal: %s → target %d (current: %d)",
            project,
            effective_target,
            scan_result.score,
        )
        return heal_project(project, path, effective_target, scan_result, engine=self)

    # ── Fase 3: Specialized ──────────────────────────────────────────

    def awwwards_fix(self, project: str, file_path: str | Path) -> bool:
        """
        Active auto-correction targeting Awwwards standard (Sovereign 200).
        Bypasses normal scan to directly rewrite animations/styles in a file.
        """
        import asyncio

        from .heal import _apply_aesthetic_formatting
        from .swarm import MejoraloSwarm

        abs_path = Path(file_path).resolve()
        if not abs_path.exists():
            logger.error("Awwwards fix failed: file not found %s", abs_path)
            return False

        # Faux findings to steer the swarm
        findings = [
            "awwwards: Force GPU compositing (will-change: transform) for all animations.",
            "awwwards: Purge inline styles and move them to utility classes/styled components.",
            "awwwards: Ensure smooth scroll integration or prevent layout thrashing.",
            "awwwards: Refactor to Sovereign 200 standard (Industrial Noir / flawless 60fps).",
        ]

        logger.info("Executing Awwwards Fixer on %s", abs_path.name)
        swarm = MejoraloSwarm(level=2)

        try:
            new_code = asyncio.run(
                swarm.refactor_file(abs_path, findings, iteration=1, engine=self, project=project)
            )
        except RuntimeError:
            new_code = None

        if not new_code:
            return False

        from cortex.cli import console

        console.print(f"  [cyan]Applying Sovereign Aesthetics to {abs_path.name}...[/]")
        abs_path.write_text(new_code)

        # Format the result
        if abs_path.suffix in (".py",):
            _apply_aesthetic_formatting(abs_path, console)

        console.print(f"  [bold green]✅ {abs_path.name} is now Awwwards-grade.[/]")
        return True

    # ── Fase 6: Ouroboros — Record Session ────────────────────────────

    def record_session(
        self,
        project: str,
        score_before: int,
        score_after: int,
        actions: Optional[list[str]] = None,
    ) -> int:
        """
        Record a MEJORAlo audit session in the CORTEX ledger.
        """
        return record_session(self.engine, project, score_before, score_after, actions)

    # ── History ──────────────────────────────────────────────────────

    def history(self, project: str, limit: int = 20) -> list[dict[str, Any]]:
        """Retrieve past MEJORAlo sessions from the ledger."""
        return get_history(self.engine, project, limit)

    def record_scar(
        self,
        project: str,
        file_path: str,
        error_trace: str,
        diff: Optional[str] = None,
    ) -> int:
        """Record a scar (failure point) in the database to prevent regressions."""
        return record_scar(self.engine, project, file_path, error_trace, diff)

    def scars(self, project: str, file_path: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve past scars for a particular file."""
        return get_scars(self.engine, project, file_path, limit)

    # ── Fase 7: Ship Gate (7 Seals) ──────────────────────────────────

    def ship_gate(self, project: str, path: str | Path) -> ShipResult:
        """
        Validate the 7 Seals for production readiness.
        """
        return check_ship_gate(project, path)
>>>>>>> origin/main
