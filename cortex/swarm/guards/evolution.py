import logging
import re

logger = logging.getLogger("cortex.swarm.guards.evolution")


class EvolutionGuard:
    """
    Sovereign Code Evolution & Entropy Guard (Ω-Evolution).
    Detects 'ghost' code, dead logic, and enforces defensive mutation boundaries.
    """
    
    def __init__(self) -> None:
        self.entropy_threshold = 0.85
        # Patterns for dead or decorative code
        self.ghost_patterns = [
            r"todo[:\s]+.*",
            r"pass\s*#\s*decorative",
            r"print\(.*\)\s*#\s*debug",
            r"def\s+\w+\(.*\):\s*pass\s*\Z"
        ]
        self.compiled_ghosts = [re.compile(p, re.IGNORECASE) for p in self.ghost_patterns]

    def measure_entropy(self, code: str) -> float:
        """
        Estimate informational entropy (Shannon) of a code block.
        Simplified for O(1) decision making.
        """
        if not code:
            return 0.0
        import math
        from collections import Counter
        
        counts = Counter(code)
        length = len(code)
        entropy = -sum((count / length) * math.log2(count / length) for count in counts.values())
        
        # Normalize roughly to 0-1 (8 bits max entropy per char)
        return min(entropy / 8.0, 1.0)

    def detect_ghosts(self, content: str) -> list[str]:
        """Identify redundant or 'ghost' code segments."""
        ghosts_found = []
        for i, line in enumerate(content.splitlines()):
            if any(p.search(line) for p in self.compiled_ghosts):
                ghosts_found.append(f"L{i+1}: {line.strip()}")
        return ghosts_found

    def validate_mutation(self, proposed_code: str) -> bool:
        """High-level validation for SwarmManager (Ω-Evolution)."""
        return not self.should_abort_mutation(proposed_code)

    def should_abort_mutation(self, proposed_code: str) -> bool:
        """Abort if the mutation increases entropy beyond the safe threshold."""
        current_entropy = self.measure_entropy(proposed_code)
        if current_entropy > self.entropy_threshold:
            logger.warning("EvolutionGuard: Critical entropy detected (%.2f). Aborting mutation.", current_entropy)
            return True
        return False
