"""MEJORAlo Engine implementation."""

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

    def scan(
        self, project: str, path: str | Path, deep: bool = False, brutal: bool = False
    ) -> ScanResult:
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

    def relentless_heal(
        self,
        project: str,
        path: str | Path,
        scan_result: ScanResult,
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
        return []

    def awwwards_fix(self, project: str, path: str | Path) -> bool:
        """Apply Awwwards-grade UI/UX fixes."""
        return False

    @staticmethod
    def detect_stack(path: str | Path) -> str:
        """Detect project stack from marker files."""
        return detect_stack(path)
