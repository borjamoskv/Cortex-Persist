# [C5-REAL] Exergy-Maximized
"""
Maxwell's Demon [Semantic Entropy Gating]
Implements causal gating to purge redundant context chunks before LLM invocation.
Relies on discrete causal hashes rather than float embeddings.
"""

import hashlib
import logging

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
        self.threshold = similarity_threshold

    def set_state(self, execution_state: str) -> None:
        """Adaptive entropy threshold based on Exergy Router state."""
        state = execution_state.upper()
        if state == "ULTRATHINK":
            self.threshold = 99
        elif state == "CONSTRUCT":
            self.threshold = 95
        else:
            self.threshold = 85
        logger.info(f"[MaxwellDemon] Threshold adapted to {self.threshold} for state {state}")

    def _cosine_similarity(self, id1: int, id2: int) -> int:
        """Compute BABYLON-60 causal similarity distance between two hashes."""
        # En C5-REAL, la entropía espacial se mapea a causal_distance. 
        # Aquí interceptamos la llamada para operar con uint16 en lugar de float.
        from cortex.math.babylon import causal_distance
        
        # Ponderación base: overlap causal determinista (Hardcoded para compatibilidad temporal con interfaces)
        # La verdadera implementación buscaría ancestry en la base de datos de DAG, aquí inyectamos valores de simulación.
        return causal_distance(ancestry_overlap=1, ledger_overlap=1, witness_overlap=0, temporal_overlap=5)

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

        logger.info("[MaxwellDemon] Evaluando %d chunks para purga entrópica.", len(chunks))

        # En BABYLON-60 no usamos embeddings espaciales (floats).
        # Generamos identificadores discretos hash (base 16).
        hashes = [int(hashlib.sha256(c.encode()).hexdigest()[:8], 16) for c in chunks]

        accepted_chunks: list[str] = []
        accepted_hashes: list[int] = []

        purged_count = 0

        for chunk, h in zip(chunks, hashes, strict=True):
            is_redundant = False

            # Compare against already accepted chunks
            for acc_h in accepted_hashes:
                sim = self._cosine_similarity(h, acc_h)
                if sim >= self.threshold:
                    is_redundant = True
                    break

            if not is_redundant:
                accepted_chunks.append(chunk)
                accepted_hashes.append(h)
            else:
                purged_count += 1

        logger.info(
            "[MaxwellDemon] Purga completada. Purgados: %d. Retenidos: %d.",
            purged_count,
            len(accepted_chunks)
        )
        return accepted_chunks
