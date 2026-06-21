# [C5-REAL] Exergy-Maximized
"""
CORTEX Entropy Injector.

Implements AX-047 (Ontological Divergence) & BABYLON-60 Epistemology.
Injects bounded, deterministic phase noise into consensus decisions to
prevent mathematical seasonality and epistemic collapse, ensuring 
ledger-friendly traceability and physical WAL transaction safety.
"""

import hashlib
import json
import logging
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
