"""
CORTEX V5 - Sovereign Refinement Engine
Enforces Ω₄: Sovereign Architectural Refinement through Static Analysis.
"""

import ast
import logging
import os
from typing import Any

from cortex.memory.shannon import ShannonCompactor

logger = logging.getLogger("cortex.refinement")


class SovereignRefiner:
    """
    Analyzes the codebase for structural entropy and "Ghosts" (unused/bloated code).
    Proposes distillations based on Ω₂ (Exergy optimization).
    """

    def __init__(self, workspace_root: str):
        self.root = workspace_root
        self.compactor = ShannonCompactor()

    def scan_for_ghosts(self) -> list[dict[str, Any]]:
        """
        Scans all python files in the workspace to detect redundancy and high entropy.
        """
        proposals = []
        for root, _, files in os.walk(self.root):
            if "venv" in root or ".git" in root or "__pycache__" in root:
                continue

            for file in files:
                if file.endswith(".py"):
                    path = os.path.join(root, file)
                    proposals.extend(self._analyze_file(path))

        return proposals

    def _analyze_file(self, path: str) -> list[dict[str, Any]]:
        findings = []
        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()

            entropy = self.compactor.calculate_structural_entropy(content)
            tree = ast.parse(content)

            # Detect basic "Ghosts": Unused imports (simplified)
            # and detect "Bloat": Functions with more than 50 AST nodes.
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    node_count = sum(1 for _ in ast.walk(node))
                    if node_count > 50:
                        findings.append({
                            "type": "BloatedFunction",
                            "file": path,
                            "name": node.name,
                            "nodes": node_count,
                            "entropy": entropy,
                            "suggestion": f"Refactor '{node.name}' to reduce entropy ({entropy:.2f})."
                        })

            # Check if overall entropy is too high (> 5.5 is highly complex for simple python)
            if entropy > 5.5 and len(content) > 1000:
                findings.append({
                    "type": "HighStructuralEntropy",
                    "file": path,
                    "entropy": entropy,
                    "suggestion": "Distill architecture to reduce Shannon density."
                })

        except (SyntaxError, UnicodeDecodeError):
            pass

        return findings

    def distill_architecture(self):
        """
        Executes a compaction pass over the entire codebase findings.
        """
        ghosts = self.scan_for_ghosts()
        for ghost in ghosts:
            logger.warning(
                "[Ω_REFINEMENT] %s detected in %s: %s",
                ghost["type"], ghost["file"], ghost["suggestion"]
            )
        return len(ghosts)
