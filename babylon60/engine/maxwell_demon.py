# [C5-REAL] Exergy-Maximized
"""
Maxwell's Demon [Semantic Entropy Gating]
Implements causal gating to purge redundant context chunks before LLM invocation.
Relies on discrete causal hashes rather than float embeddings.
Delegates purely to the Fable 5.0 (F# -> Python) C5-REAL kernel.
"""

import hashlib
import logging

from fable_library.array_ import Array
from fable_library.core import uint16, uint32

from babylon60.engine.fable_out.src.maxwell_demon import (
    MaxwellDemon__ctor_6C4BA866,
    MaxwellDemon__PurgeRedundant_Z115D9F2A,
    MaxwellDemon__SetState_Z721C83C5,
)

logger = logging.getLogger(__name__)


class MaxwellDemon:
    """
    Causal Entropy Gating Engine.
    Acts as a thermodynamic filter, discarding redundant 
    information to maximize informational exergy and reduce context length.
    """

    def __init__(self, similarity_threshold: int = 85):
        """
        Args:
            similarity_threshold (int): Minimum causal distance (0-100) to consider redundant.
        """
        self._demon = MaxwellDemon__ctor_6C4BA866(uint16(similarity_threshold))
        self.threshold = similarity_threshold

    def set_state(self, execution_state: str) -> None:
        """Adaptive entropy threshold based on Exergy Router state."""
        MaxwellDemon__SetState_Z721C83C5(self._demon, execution_state)
        
        state = execution_state.upper()
        if state == "ULTRATHINK":
            self.threshold = 10
        elif state == "CONSTRUCT":
            self.threshold = 50
        else:
            self.threshold = 150
            
        logger.info(f"[MaxwellDemon] Threshold adapted to {self.threshold} for state {state}")

    def purge_redundant(self, chunks: list[str]) -> list[str]:
        """
        Evaluates a sequence of text chunks and removes those that are causally
        redundant with respect to the chunks already accepted.
        
        Args:
            chunks: List of text chunks (strings) to evaluate.
            
        Returns:
            List of non-redundant text chunks.
        """
        if not chunks:
            return []

        logger.info("[MaxwellDemon] Evaluando %d chunks para purga entrópica mediante Fable Kernel.", len(chunks))

        hashes_and_chunks = [
            (uint32(int(hashlib.sha256(c.encode()).hexdigest()[:8], 16)), c)
            for c in chunks
        ]

        fable_array = Array(hashes_and_chunks)

        accepted_array, purged_count = MaxwellDemon__PurgeRedundant_Z115D9F2A(self._demon, fable_array)

        accepted_chunks = list(accepted_array)

        logger.info(
            "[MaxwellDemon] Purga completada. Purgados: %d. Retenidos: %d.",
            purged_count,
            len(accepted_chunks)
        )
        return accepted_chunks
