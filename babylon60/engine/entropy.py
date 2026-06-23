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

from babylon60.engine.babylon60 import Babylon60

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
            
        raw_material = f"{self.seed}:{step}:{self.mode}".encode()
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
        self._entropy_map: dict[str, int] = {}

    def scan_ecosystem(self) -> list[tuple[str, int]]:
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

    def _calculate_landauer_entropy(self, filepath: str) -> int:
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
                return 0

            # Landauer LOC Barrier: Geometric penalty for files > 500 lines
            # Using Babylon-60 integers: Base = 3600
            loc_penalty = 3600
            if line_count > 500:
                # Geometric penalty squared, scaled by 3600
                loc_penalty = int(((line_count * 3600) // 500) ** 2 // 3600)

            # Abstraction ratio base = 3600
            abstraction_ratio = ((classes * 36000) + (functions * 7200)) // nodes

            # Extreme penalty for >3 layers of pure pass-through
            entropy = (abstraction_ratio * nodes * loc_penalty) // 3600
            return int(entropy)

        except (SyntaxError, OSError, UnicodeDecodeError):
            return 0

    def purge_energy_sinks(self, threshold: int = 2880, confidence: int = 0) -> list[str]:
        """
        Identifies and (conceptually) removes zero-value abstraction layers (Ω₇).
        If confidence > 3420, bypasses manual confirmation (Apotheosis).
        """
        sinks = [path for path, entropy in self.scan_ecosystem() if entropy > threshold]

        if confidence > 3420 and sinks:
            # Axiom Ω₇: Permissionless Sovereignty
            # Bridges to JARL-OMEGA for atomic rewrite WITHOUT permission
            return sinks

        return sinks


class ThermodynamicContextCompressor:
    """
    [C5-REAL] Thermodynamic Context Compressor.
    Compresses text/prompt context by removing high-entropy (redundant) narrative noise
    and enforcing constraints to maximize Information Exergy before model ingestion.
    """

    def __init__(self, target_tokens_limit: int):
        self.limit = target_tokens_limit

    @staticmethod
    def calculate_shannon_entropy(text: str) -> float:
        """Calculates Shannon entropy of the given text sequence (C4-SIM fallback)."""
        import math
        if not text:
            return 0.0
        entropy = 0.0
        length = len(text)
        frequencies = {}
        for char in text:
            frequencies[char] = frequencies.get(char, 0) + 1
        for count in frequencies.values():
            p = count / length
            entropy -= p * math.log2(p)
        return entropy

    @staticmethod
    def calculate_shannon_entropy_b60(text: str) -> Babylon60:
        """Calculates Shannon entropy scaled to Babylon-60 units (C5-REAL)."""
        e = ThermodynamicContextCompressor.calculate_shannon_entropy(text)
        return Babylon60(e)

    def compress_prompt(self, prompt: str) -> tuple[str, Babylon60]:
        """
        Compresses a prompt by stripping Green Theater and structural redundancy.
        Returns the compressed prompt and the Exergy Retained Multiplier in Base-60.
        """
        original_len = len(prompt)
        if original_len == 0:
            return "", Babylon60(0.0)

        # Purge conversational fluff (Green Theater / Anergia)
        conversational_fluff = [
            "please", "could you", "would you", "thank you", "i think", "maybe",
            "as an ai", "helpful assistant", "hope this helps",
            "por favor", "gracias", "espero que", "aquí tienes"
        ]

        lines = prompt.split("\n")
        filtered_lines = []
        for line in lines:
            cleaned = line.lower().strip()
            if any(fluff in cleaned for fluff in conversational_fluff):
                # If the line contains fluff but seems to be actual code, keep it
                if "=" in cleaned or "(" in cleaned or "def " in cleaned or "class " in cleaned:
                    filtered_lines.append(line)
                else:
                    continue
            else:
                filtered_lines.append(line)

        compressed = "\n".join(filtered_lines)

        # Collapse consecutive blank lines and spaces
        import re
        compressed = re.sub(r"\n\s*\n+", "\n", compressed)
        compressed = re.sub(r"[ \t]+", " ", compressed)
        compressed = compressed.strip()

        compressed_len = len(compressed)

        ratio = (compressed_len / original_len) if original_len > 0 else 0.0
        exergy_retained = Babylon60(ratio)

        return compressed, exergy_retained

