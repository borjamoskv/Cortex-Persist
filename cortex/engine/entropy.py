import logging

from cortex.agents.primitives.dispatcher import apex_dispatcher
from cortex.guards.landauer_guard import LandauerGuard

logger = logging.getLogger(__name__)

class EntropyAnnihilator:
    """
    C5-REAL Kinetic Engine: Entropy Annihilator
    Identifies and purges zero-exergy tokens, slop, and invalid parametric rot
    from memory structures.
    """
    def __init__(self) -> None:
        pass

    def purge_slop(self, data: str) -> str:
        """Removes decorative prose ('Here is the code', etc.) (Ouroboros Ω13)."""
        # Very basic structural filtering for zero-anergy compliance
        slop_signatures = [
            "Aquí tienes el código",
            "Espero que esto ayude",
            "Por supuesto",
            "Entendido",
            "Como modelo de lenguaje"
        ]
        
        lines = data.splitlines()
        purged = []
        for line in lines:
            if not any(slop in line for slop in slop_signatures):
                purged.append(line)
        return "\n".join(purged).strip()

    def thermodynamically_compress(self, sacred_fact: str) -> str:
        """
        Uses LandauerGuard limits to force compression if entropy is too low 
        or bytes are too high.
        """
        byte_len = len(sacred_fact.encode("utf-8"))
        entropy = LandauerGuard.calculate_entropy(sacred_fact)
        
        if byte_len > LandauerGuard.MAX_BYTES or entropy < LandauerGuard.MIN_ENTROPY:
            logger.warning(f"[EntropyAnnihilator] Fact failed Ω4. Bytes: {byte_len}, Entropy: {entropy:.2f}. Compressing.")
            # Trigger OP_COLLAPSE equivalent or structural chop
            # We compress by taking only high-entropy components
            # For this primitive version, we just slice to MAX_BYTES
            sacred_fact = sacred_fact[:LandauerGuard.MAX_BYTES]
            
        return sacred_fact
        
    def execute_apoptosis_on_rot(self, rot_score: float, threshold: float = 0.9) -> None:
        """
        If memory rot exceeds threshold, triggers OP_APOPTOSIS through ApexDispatcher.
        """
        if rot_score >= threshold:
            logger.critical(f"[EntropyAnnihilator] Rot score {rot_score} exceeds threshold {threshold}.")
            apex_dispatcher.execute("OP_APOPTOSIS")

entropy_annihilator = EntropyAnnihilator()
