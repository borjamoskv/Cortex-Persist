# [C5-REAL] Exergy-Maximized
"""
Entropy Core v0 - CORTEX v1.0 Middleware
Calculates system entropy in 3 dimensions: Structural, Semantic, Operational.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

import cortex_rs
from babylon60.engine.entropy import EntropyAnnihilator


def calculate_entropy_b60(data: bytes) -> "cortex_rs.Babylon60":
    """
    Thin Python wrapper over the Rust FFI for BABYLON-60 entropy calculation.
    """
    return cortex_rs.calculate_entropy_b60(data)


class SystemRegime(str, Enum):
    STABLE = "STABLE"
    METASTABLE = "METASTABLE"
    CRITICAL = "CRITICAL"
    COLLAPSE = "COLLAPSE"

@dataclass
class EntropyState:
    structural: float
    semantic: float
    operational: float
    total: float
    regime: SystemRegime

class EntropyCore:
    """
    Evaluates the system's entropy state to detect uncontrolled complexity growth.
    """
    
    def __init__(self, workspace_root: str):
        self.workspace_root = Path(workspace_root)
        
    def evaluate_entropy(self, diff_content: str, intent_prompt: str, modified_files: list[str]) -> EntropyState:
        """
        Calculates the 3 dimensions of entropy.
        """
        structural = self._compute_structural_entropy(modified_files)
        semantic = self._compute_semantic_drift(diff_content, intent_prompt)
        operational = self._compute_operational_entropy()
        
        # Simple weighted sum for total entropy
        total = (structural * 0.4) + (semantic * 0.3) + (operational * 0.3)
        regime = self._determine_regime(total)
        
        return EntropyState(
            structural=structural,
            semantic=semantic,
            operational=operational,
            total=total,
            regime=regime
        )

    def _compute_structural_entropy(self, modified_files: list[str]) -> float:
        """
        Wraps EntropyAnnihilator to measure thermodynamic complexity of changed files.
        """
        if not modified_files:
            return 0.0
            
        annihilator = EntropyAnnihilator(str(self.workspace_root))
        total_entropy = 0.0
        valid_files = 0
        
        for file in modified_files:
            filepath = self.workspace_root / file
            if filepath.exists() and filepath.suffix == '.py':
                entropy = annihilator._calculate_landauer_entropy(str(filepath))
                total_entropy += entropy
                valid_files += 1
                
        return (total_entropy / valid_files) if valid_files > 0 else 0.0

    def _compute_semantic_drift(self, diff_content: str, intent_prompt: str) -> float:
        """
        Placeholder for Cosine Similarity between prompt intent and actual diff.
        Currently returns 0.0 (perfect alignment) unless drift is explicitly detected.
        In v1.0, this uses Sentence Transformers to embed both strings.
        """
        # TODO: Implement local ONNX embedding similarity
        # For MVP, we simulate semantic entropy based on diff length vs intent length mismatch
        if not intent_prompt or not diff_content:
            return 0.5
        
        len_diff = len(diff_content)
        len_intent = len(intent_prompt)
        
        # Naive drift: if LLM generates massive code for a tiny intent, entropy rises.
        ratio = max(len_diff, len_intent) / (min(len_diff, len_intent) + 1)
        drift = min(ratio / 100.0, 1.0)
        return float(drift)

    def _compute_operational_entropy(self) -> float:
        """
        Parses local pytest-report.xml to calculate failing test rate (flakiness/errors).
        """
        report_path = self.workspace_root / "pytest-report.xml"
        if not report_path.exists():
            return 0.0
            
        try:
            tree = ET.parse(report_path)
            root = tree.getroot()
            testsuite = root.find("testsuite")
            if testsuite is None:
                return 0.0
                
            tests = int(testsuite.get("tests", 0))
            errors = int(testsuite.get("errors", 0))
            failures = int(testsuite.get("failures", 0))
            
            if tests == 0:
                return 0.0
                
            failure_rate = (errors + failures) / tests
            return min(float(failure_rate) * 2.0, 1.0) # Multiply by 2 to make it sensitive
            
        except Exception:
            return 0.5 # Unknown operational state
            
    def _determine_regime(self, total_entropy: float) -> SystemRegime:
        if total_entropy < 0.3:
            return SystemRegime.STABLE
        elif total_entropy < 0.6:
            return SystemRegime.METASTABLE
        elif total_entropy < 0.85:
            return SystemRegime.CRITICAL
        else:
            return SystemRegime.COLLAPSE
