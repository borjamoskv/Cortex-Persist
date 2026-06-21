# [C5-REAL] Exergy-Maximized
"""
Matemáticas del Plano Creencia (CORTEX-Persist).
Define funciones puras para calcular el decaimiento de creencias y 
la divergencia causal bajo el protocolo BABYLON-60.
Operaciones estrictamente limitadas al dominio de los enteros.
"""



def calculate_decay_weight(w0: int, time_delta_seconds: int, half_life_seconds: int) -> int:
    """
    Calcula el peso de una creencia utilizando decaimiento discreto basado en vida media (Half-life).
    Evita representaciones exponenciales y floats.
    
    Args:
        w0: Peso inicial discreto (ej. 1000000).
        time_delta_seconds: Tiempo transcurrido (uint32).
        half_life_seconds: Ciclos de vida media en segundos (uint32).
    """
    if half_life_seconds <= 0:
        return 0
        
    # Bitwise shift right for every half life passed (integer division representation of 1/2^n)
    half_lives_passed = time_delta_seconds // half_life_seconds
    
    if half_lives_passed >= 31: # Shift limit for standard 32bit boundary prevention
        return 0
        
    return w0 >> half_lives_passed


def calculate_risk_contam(
    hash_proposal: int, 
    hash_core_axioms: int, 
    threshold_distance: int
) -> int:
    """
    Calcula el Riesgo de Contaminación mediante Distancia de Hamming sobre Hashes BABYLON-60.
    
    Args:
        hash_proposal: Identificador hash determinista.
        hash_core_axioms: Identificador hash de validación core.
        threshold_distance: Límite máximo de discrepancia (Hamming distance max).
    """
    # Computamos la distancia de Hamming utilizando la Capa 0 (Sustrato Binario) de BABYLON-60
    distance = (hash_proposal ^ hash_core_axioms).bit_count()
    
    if distance <= threshold_distance:
        # Riesgo lineal
        return distance
    else:
        # Penalización aritmética entera fuerte: distance * (distance - threshold)^2
        penalty = (distance - threshold_distance) ** 2
        return distance * penalty
