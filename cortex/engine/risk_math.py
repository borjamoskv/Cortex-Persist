# [C5-REAL] Exergy-Maximized
"""
Matemáticas del Plano Creencia (CORTEX-Persist).
Define funciones puras para calcular el decaimiento de creencias y 
la divergencia semántica (Riesgo de Contaminación).
"""

import math
from typing import Sequence

def calculate_decay_weight(w0: float, time_delta_seconds: float, lambda_factor: float) -> float:
    """
    Calcula el peso de una creencia utilizando Decaimiento Exponencial (Ebbinghaus).
    W(t) = W_0 * e^(-lambda * t)
    
    Args:
        w0: Peso inicial (ej. 1.0).
        time_delta_seconds: Tiempo transcurrido desde la última aserción o uso.
        lambda_factor: Tasa de decaimiento (calibrada por dominio, ej. 0.0001).
    """
    return w0 * math.exp(-lambda_factor * time_delta_seconds)


def cosine_distance(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    """Calcula la Distancia Coseno optimizada (O(n)) sin dependencias externas."""
    if len(vec_a) != len(vec_b):
        raise ValueError("Los vectores deben tener la misma dimensionalidad.")
        
    # Optimización mediante generadores sin copias innecesarias
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    
    EPSILON = 1e-10
    if norm_a < EPSILON or norm_b < EPSILON:
        return 1.0 # Max distance si hay subnormales o ceros
        
    return 1.0 - (dot_product / (norm_a * norm_b))


def calculate_risk_contam(
    vector_proposal: Sequence[float], 
    vector_core_axioms: Sequence[float], 
    threshold: float
) -> float:
    """
    Calcula el Riesgo de Contaminación (Risk_contam) mediante Divergencia Semántica.
    Si la distancia supera el umbral, el riesgo se dispara asintóticamente al infinito
    (o un valor lo suficientemente alto para anular la ecuación del Score).
    
    Args:
        vector_proposal: Embedding de la creencia propuesta.
        vector_core_axioms: Embedding o centroide de los axiomas core verificados.
        threshold: Umbral máximo permitido (ej. 0.3 de distancia).
    """
    distance = cosine_distance(vector_proposal, vector_core_axioms)
    
    if distance <= threshold:
        # Riesgo lineal bajo
        return distance
    else:
        # Penalización exponencial acotada (Clipping en exponente=20.0 para evitar Overflow/NaN)
        exponent = min(10.0 * (distance - threshold), 20.0)
        return distance * math.exp(exponent)
