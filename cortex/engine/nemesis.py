"""The Nemesis Immunological Protocol.

MOSKV-1 v5 Axiom VII: Algorithmic Immunity.
Rejects entropy, boilerplate, and low-quality facts from entering CORTEX memory.
"""

import re
from typing import Optional


class NemesisRejection(Exception):
    """Raised when a fact violates the 130/100 standard and is rejected by Nemesis."""
    pass


class NemesisProtocol:
    """Enforces the 130/100 standard on all incoming memory facts."""

    # Anti-patterns that trigger immediate rejection
    ANTI_PATTERNS = [
        (r"console\.log\(.*?\)", "Debugging efímero (console.log). Usa logging estructurado temporal o destrúyelo."),
        (r"todo:|fixme:|hack:", "Marcadores de deuda técnica (TODO/FIXME) detectados. Resuélvelo ahora, no lo dejes para después."),
        (r"copy-paste|copiado de|stackoverflow", "Código no asimilado. Si no puedes explicarlo causalmente, viola el Axioma I (Causal Over Correlation)."),
        (r"por si acaso|just in case", "Abstracción defensiva ('por si acaso'). Viola el Axioma IV: Densidad Infinita."),
        (r"bootstrap|tailwind default", "Estética genérica detectada. Exigimos Industrial Noir 130/100."),
    ]

    @classmethod
    def analyze(cls, content: str) -> Optional[str]:
        """Analyze content and return rejection reason if it violates protocols."""
        content_lower = content.lower()
        
        for pattern, reason in cls.ANTI_PATTERNS:
            if re.search(pattern, content_lower):
                return f"[NEMESIS PROTOCOL ACTIVO] Entropía detectada: {reason}"
                
        return None
