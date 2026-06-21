import math
import re
from typing import List, Tuple

class MaxwellsDemon:
    """
    [C5-REAL] Motor Termodinámico (L1 Router).
    Filtra la entropía (teatro verde, prosa, saludos) y conserva la exergía (código, lógica estructural).
    Actúa como un Demonio de Maxwell para el contexto de los modelos APEX.
    """
    def __init__(self):
        self.entropy_patterns = [
            r"(?i)\b(hola|buenos dias|espero que|por favor|lo siento|disculpa)\b",
            r"(?i)\b(aqui tienes|este es el|como te puedo ayudar|claro que si)\b",
            r"(?i)\b(es importante recordar|ten en cuenta que|es posible que)\b"
        ]
        self.exergy_patterns = [
            r"```[\s\S]*?```",   # Bloques de código
            r"(?m)^#\s.*$",     # Encabezados
            r"(?m)^\s*-\s.*$",  # Listas (estructuras)
            r"\{[\s\S]*\}",     # JSON o Dicts
        ]

    def _calculate_shannon_entropy(self, text: str) -> float:
        """Calcula la entropía teórica de Shannon (ruido) en un string."""
        if not text:
            return 0.0
        prob_dict = {c: text.count(c) / len(text) for c in set(text)}
        return -sum(p * math.log2(p) for p in prob_dict.values())

    def filter_context(self, input_text: str) -> Tuple[str, float]:
        """
        Ingesta un flujo de texto estocástico y lo colapsa en un estado de alta exergía.
        Devuelve el texto filtrado y el porcentaje de masa térmica (tokens) purgada.
        """
        original_length = len(input_text)
        if original_length == 0:
            return "", 0.0

        # Identificar bloques de exergía (código y estructura)
        exergy_blocks = []
        for pattern in self.exergy_patterns:
            matches = re.finditer(pattern, input_text)
            for match in matches:
                exergy_blocks.append(match.group())

        # Purgar patrones de alta entropía (Green Theater)
        purged_text = input_text
        for pattern in self.entropy_patterns:
            purged_text = re.sub(pattern, "", purged_text)

        # Re-evaluar el texto resultante. Si el texto no tiene bloques de código 
        # y la longitud es muy pequeña tras limpiar, es ruido puro.
        final_text = "\n\n".join(exergy_blocks) if exergy_blocks else purged_text.strip()
        
        # O si el original tenía bloques pero además había texto, nos quedamos solo con la estructura
        if exergy_blocks:
            final_text = "\n\n".join(exergy_blocks)
            
        final_length = len(final_text)
        exergy_ratio = 100.0 * (original_length - final_length) / original_length

        return final_text, exergy_ratio
