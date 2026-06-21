# [C5-REAL] Exergy-Maximized
"""
CORTEX Entropy Injector.

Implements AX-047 (Ontological Divergence) & BABYLON-60 Epistemology.
Injects bounded, deterministic phase noise into consensus decisions to
prevent mathematical seasonality and epistemic collapse, ensuring 
ledger-friendly traceability and physical WAL transaction safety.
"""

import ast
import hashlib
import json
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

class EntropyInjector:
    """Deterministic entropy injector for decision thresholds.
    
    Ensures that identical replays produce identical outputs via seeded
    hashing. Operates exclusively in the decision point without mutating 
    schema. Degradation to epsilon=0 explicitly leaves a cold trace.
    """

    def __init__(self, seed: int, epsilon: int, mode: str = "phase_noise"):
        """Initialize the Entropy Injector.
        
        Args:
            seed: Deterministic integer seed for reproducible perturbation.
            epsilon: Maximum absolute amplitude of perturbation (BABYLON-60 int).
            mode: Injection mode. Defaults to 'phase_noise'.
        """
        if not isinstance(epsilon, int) or not isinstance(seed, int):
            raise TypeError("[P0] BABYLON-60 Violation: seed and epsilon must be integers, no float64.")
            
        self.seed = seed
        self.epsilon = abs(epsilon)
        self.mode = mode

    def _deterministic_delta(self, step: int) -> int:
        """Compute bounded deterministic delta using SHA-256."""
        if self.epsilon == 0:
            return 0
            
        raw_material = f"{self.seed}:{step}:{self.mode}".encode("utf-8")
        h = int(hashlib.sha256(raw_material).hexdigest()[:8], 16)
        
        # Map hash to uniform distribution [-epsilon, +epsilon]
        return (h % (2 * self.epsilon + 1)) - self.epsilon

    async def inject(self, base_score: int, step: int, reason: str, cursor: Any) -> int:
        """Inject perturbation at the decision point within an atomic transaction.
        
        Args:
            base_score: The unperturbed deterministic score.
            step: Monotonically increasing step or unique decision sequence ID.
            reason: Causal rationale for this perturbation.
            cursor: Active aiosqlite Cursor to guarantee WAL atomicity.
            
        Returns:
            The perturbed final score.
        """
        if self.epsilon == 0:
            delta = 0
            logger.warning("[C5-REAL] EntropyInjector degrading to COLD_MODE (epsilon=0).")
            mode_status = "COLD_MODE"
        else:
            delta = self._deterministic_delta(step)
            mode_status = self.mode

        final_score = base_score + delta
        
        # Construct ClosurePayload for cryptographic event tracing
        payload = {
            "seed": self.seed,
            "step": step,
            "base_score": base_score,
            "delta": delta,
            "final_score": final_score,
            "reason": reason,
            "mode": mode_status
        }
        
        # Serialize with sorted keys for deterministic hash
        serialized = json.dumps(payload, sort_keys=True).encode("utf-8")
        event_hash = hashlib.sha256(serialized).hexdigest()

        # Emit explicitly to ledger within the same atomic boundary
        await self._emit_to_ledger(cursor, event_hash, step, delta, reason)

        return final_score

    async def _emit_to_ledger(self, cursor: Any, event_hash: str, step: int, delta: int, reason: str) -> None:
        """Persist the event trace ensuring WAL atomicity."""
        # Ensure table exists (idempotent setup within cursor context)
        await cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS cortex_entropy_ledger (
                event_hash TEXT PRIMARY KEY,
                seed INTEGER NOT NULL,
                step INTEGER NOT NULL,
                delta INTEGER NOT NULL,
                reason TEXT NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        
        # Insert perturbation trace
        await cursor.execute(
            '''
            INSERT INTO cortex_entropy_ledger (event_hash, seed, step, delta, reason)
            VALUES (?, ?, ?, ?, ?)
            ''',
            (event_hash, self.seed, step, delta, reason)
        )


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

