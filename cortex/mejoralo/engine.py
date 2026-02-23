"""MEJORAlo Engine implementation."""

import logging
from pathlib import Path
from typing import Any

from cortex.engine import CortexEngine

from .constants import INMEJORABLE_SCORE
from .heal import heal_project
from .ledger import get_history, get_scars, record_scar, record_session
from .models import ScanResult, ShipResult
from .scan import scan
from .ship import check_ship_gate
from .utils import detect_stack

__all__ = ["MejoraloEngine"]

logger = logging.getLogger("cortex.mejoralo")


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

    def scan(
        self, project: str, path: str | Path, deep: bool = False, brutal: bool = False
    ) -> ScanResult:
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

    def relentless_heal(
        self,
        project: str,
        path: str | Path,
        scan_result: ScanResult,
        target_score: int | None = None,
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

    # ── Fase 6: Ouroboros — Record Session ────────────────────────────

    def record_session(
        self,
        project: str,
        score_before: int,
        score_after: int,
        actions: list[str] | None = None,
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
        diff: str | None = None,
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
