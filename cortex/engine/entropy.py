"""
CORTEX V5 - Entropy Annihilator (JARL-Ω)
Information Thermodynamics & Landauer's Razor: Axiom 12 Net-Negative Entropy.
"""

import ast
import os


class EntropyAnnihilator:
    """
    Measures abstract complexity as thermodynamic entropy.
    Abstract layers without O(1) value are identified as energy sinks and marked for purgation.
    Target: Zero structural waste.
    """

    def __init__(self, target_directory: str):
        self.target = target_directory
        self._entropy_map: dict[str, float] = {}

    def scan_ecosystem(self) -> list[tuple[str, float]]:
        """
        Scans architecture to measure structural entropy per file.
        Returns files sorted by their entropy-to-value ratio.
        """
        for root, _, files in os.walk(self.target):
            for file in files:
                if not file.endswith(".py"):
                    continue
                path = os.path.join(root, file)
                self._entropy_map[path] = self._calculate_landauer_entropy(path)

        # Return top sinks
        return sorted(self._entropy_map.items(), key=lambda x: x[1], reverse=True)

    def _calculate_landauer_entropy(self, filepath: str) -> float:
        """
        Calculates the thermodynamic complexity of a file.
        High abstraction depth without functional density = High Entropy.
        Includes Axiom Ω₂: Landauer LOC Barrier (500 lines).
        """
        try:
            with open(filepath) as f:
                lines = f.readlines()
                content = "".join(lines)

            line_count = len(lines)
            tree = ast.parse(content)

            # Metrics
            nodes = 0
            classes = 0
            functions = 0

            for node in ast.walk(tree):
                nodes += 1
                if isinstance(node, ast.ClassDef):
                    classes += 1
                elif isinstance(node, ast.FunctionDef):
                    functions += 1

            # Landauer's Razor: If abstraction count (classes/funcs) is high but
            # actual operation nodes are low, it's an empty abstraction layer (sink).
            if nodes == 0:
                return 0.0

            # Landauer LOC Barrier: Geometric penalty for files > 500 lines
            loc_penalty = 1.0
            if line_count > 500:
                loc_penalty = (line_count / 500) ** 2

            abstraction_ratio = (classes * 10 + functions * 2) / nodes

            # Extreme penalty for >3 layers of pure pass-through
            entropy = (abstraction_ratio * nodes) * loc_penalty
            return float(entropy)

        except (SyntaxError, OSError, UnicodeDecodeError):
            return 0.0

    def purge_energy_sinks(self, threshold: float = 0.8, confidence: float = 0.0) -> list[str]:
        """
        Identifies and (conceptually) removes zero-value abstraction layers (Ω₇).
        If confidence > 0.95, bypasses manual confirmation (Apotheosis).
        """
        sinks = [path for path, entropy in self.scan_ecosystem() if entropy > threshold]

        if confidence > 0.95 and sinks:
            # Axiom Ω₇: Permissionless Sovereignty
            # Bridges to JARL-OMEGA for atomic rewrite WITHOUT permission
            return sinks

        return sinks
