# [C5-REAL] Exergy-Maximized
from __future__ import annotations

import math


def cortex_decay(is_diamond: int, timestamp: float, current_time: float, half_life: float) -> float:
    """
    Decaimiento entrópico.
    Si un memory es diamond (1), no decae nunca (multiplicador = 1.0).
    Si no es diamond, se aplica vida media (half_life) basada en delta t.
    """
    if is_diamond == 1:
        return 1.0
    
    delta = current_time - timestamp
    if delta < 0:
        return 1.0
        
    if half_life <= 0:
        return 1.0
        
    return math.exp(-0.6931471805599453 * delta / half_life)
