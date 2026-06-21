# [C5-REAL] Exergy-Maximized
"""
Rotación Ortogonal Secreta (Mitigación P-1)
Evita la ofuscación lineal (pad estático) que genera colapso angular.
Genera una matriz ortogonal Q en RAM para multiplicar los embeddings.
Preserva la similitud del coseno y destruye ataques de inversión (vec2text).
"""

import numpy as np
from typing import Optional

class OrthogonalObfuscator:
    _instance: Optional['OrthogonalObfuscator'] = None
    
    def __init__(self, dim: int = 1536):
        # Generamos matriz aleatoria
        random_matrix = np.random.randn(dim, dim)
        # Factorización QR para obtener matriz ortogonal Q
        q, r = np.linalg.qr(random_matrix)
        # Persistida SOLO en RAM
        self._Q = q

    @classmethod
    def get_instance(cls, dim: int = 1536) -> 'OrthogonalObfuscator':
        if cls._instance is None:
            cls._instance = cls(dim)
        return cls._instance
        
    def obfuscate(self, embedding: list[float]) -> list[float]:
        """
        Multiplica el embedding por la matriz Q usando BLAS nativo (numpy.dot).
        Esto rota el vector en el espacio latente manteniendo intactas las 
        distancias angulares relativas (cosine similarity).
        """
        vec = np.array(embedding, dtype=np.float32)
        # Vector * Matriz = Rotación
        rotated = np.dot(vec, self._Q)
        return rotated.tolist()
