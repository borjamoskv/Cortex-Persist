# [C5-REAL] Exergy-Maximized
"""
Motor Causal de Extracción Exergética (Zipf-Wierzbicka Pipeline).
Aísla las 100 primitivas estructurales de máxima exergía en cualquier dominio virgen.
"""

from __future__ import annotations

import collections
import logging
import math
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger("cortex.zipf_exergy_extractor")

@dataclass(frozen=True)
class ExergyNode:
    """Nodo Estructural C5-REAL (Primitiva)."""
    term: str
    frequency: int
    zipf_weight: float
    is_structural: bool
    wierzbicka_mapping: str | None = None


class ZipfExergyExtractor:
    """
    Implementación determinista del Pipeline de Exergía de 100 Primitivas.
    Erradica la limerencia epistémica colapsando la entropía de textos largos
    en sus invariantes estructurales fundamentales.
    """
    
    # Heurística mínima para aislar ruido estocástico (stop words comunes en español/inglés)
    ANERGY_WORDS = {
        "el", "la", "los", "las", "un", "una", "unos", "unas",
        "de", "del", "a", "ante", "bajo", "cabe", "con", "contra",
        "desde", "en", "entre", "hacia", "hasta", "para", "por",
        "según", "sin", "so", "sobre", "tras", "que", "y", "o", "u",
        "the", "an", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "from", "up", "about", "into", "over", "after"
    }
    
    # 65 Primitivas NSM (Natural Semantic Metalanguage) - Subconjunto para validación
    NSM_PRIMITIVES = {
        "yo", "tú", "alguien", "algo", "cuerpo", "pensar", "saber", "querer", 
        "sentir", "ver", "oir", "decir", "palabra", "verdad", "hacer", "pasar", 
        "moverse", "estar", "tener", "bueno", "malo", "grande", "pequeño", 
        "mucho", "poco", "todo", "donde", "cuando", "porque", "poder", "como"
    }

    @classmethod
    def extract_exergy_primitives(
        cls, 
        corpus_text: str, 
        max_nodes: int = 100
    ) -> list[ExergyNode]:
        """
        Ejecuta la Fase 1 del Pipeline (Filtro de Ruido Zipf).
        Extrae los `max_nodes` de mayor carga estructural.
        """
        logger.info("⚡ [EXERGY] Iniciando extracción topológica (Zipf) sobre corpus...")
        
        # Tokenización agresiva (Ouroboros regex)
        tokens = re.findall(r'\b[a-záéíóúñA-ZÁÉÍÓÚÑ]+\b', corpus_text.lower())
        
        # Eliminación de Anergía (Stop words)
        filtered_tokens = [t for t in tokens if t not in cls.ANERGY_WORDS and len(t) > 2]
        
        if not filtered_tokens:
            return []
            
        # Distribución de frecuencias
        freq_map = collections.Counter(filtered_tokens)
        total_valid_tokens = sum(freq_map.values())
        
        # Ordenamiento por Zipf (Mayor frecuencia -> Rango 1)
        sorted_terms = freq_map.most_common(max_nodes)
        
        exergy_nodes = []
        for _rank, (term, count) in enumerate(sorted_terms, start=1):
            # Peso de Zipf empírico (Frecuencia relativa ajustada por el logaritmo del rango)
            # En un corpus ideal, count es proporcional a 1/rank
            tf = count / total_valid_tokens
            zipf_weight = tf * math.log(len(freq_map) + 1)
            
            # Determinación de "Esqueleto Estructural" vs "Data Arbitraria"
            is_nsm = term in cls.NSM_PRIMITIVES
            
            node = ExergyNode(
                term=term,
                frequency=count,
                zipf_weight=round(zipf_weight, 6),
                is_structural=is_nsm,
                wierzbicka_mapping=term if is_nsm else None
            )
            exergy_nodes.append(node)
            
        return exergy_nodes

    @classmethod
    def evaluate_epistemic_limerence(cls, nodes: list[ExergyNode]) -> dict[str, Any]:
        """
        Ejecuta la Fase 2 (Colapso Semántico).
        Evalúa si el grafo extraído sufre de "Limerencia Epistémica" (demasiada jerga aislada sin conectores semánticos).
        """
        structural_count = sum(1 for n in nodes if n.is_structural)
        total = len(nodes)
        
        # Si menos del 5% del Top 100 son primitivas semánticas puras, 
        # el corpus es pura jerga técnica (baja exergía transversal).
        ratio = structural_count / max(1, total)
        has_limerence = ratio < 0.05
        
        return {
            "TotalNodes": total,
            "StructuralPrimitives": structural_count,
            "StructuralRatio": round(ratio, 4),
            "EpistemicLimerenceDetected": has_limerence,
            "ExergyConfidence": "C4-SIM" if has_limerence else "C5-REAL"
        }
