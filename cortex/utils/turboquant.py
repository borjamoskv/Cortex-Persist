"""
CORTEX v6 — TurboQuant Integration.

Ref: arXiv:2504.19874 (TurboQuant: Online Vector Quantization)
Two-Stage approach: Random Rotation + MSE Quantization + 1-bit QJL Transform.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence

from cortex.compat.optional import np  # lazy: pip install cortex-persist[compute]

from cortex.utils import void_vec

logger = logging.getLogger("cortex.utils.turboquant")

# Cache estático en RAM para no desperdiciar exergía recalculando QR(R) O(D^3)
_ROTATION_CACHE: dict[int, np.ndarray] = {}


def _get_rotation_matrix(dim: int) -> np.ndarray:
    """Obtiene y empaqueta la matriz ortogonal isométrica Q."""
    if dim not in _ROTATION_CACHE:
        # Utilizamos la dimensión como semilla para tener isometría determinista
        rng = np.random.RandomState(dim)
        R = rng.randn(dim, dim)
        q, _ = np.linalg.qr(R)
        _ROTATION_CACHE[dim] = q
    return _ROTATION_CACHE[dim]


def optimize_vector_qjl(
    vector: Sequence[float] | Sequence[int], bits: float = 3.5, layer_depth_ratio: float = 0.0
) -> list[float] | bytes:
    """
    Aplica el algoritmo de cuantización de dos fases TurboQuant.
    Integra KV Cache Asimétrico (arXiv:2603.04428): escala los bits a 1.0 en capas profundas.
    Devuelve un array comprimido listo para sqlite-vec (int8).
    Elimina la entropía de float32 maximizando la eficiencia I/O.
    """
    try:
        # Asymmetric depth logic (Extreme Exergy for Deep Layers)
        effective_bits = max(1.0, bits * (1.0 - (layer_depth_ratio * 0.7)))

        arr = np.array(vector, dtype=np.float32)
        is_2d = len(arr.shape) > 1
        if not is_2d:
            arr = arr[np.newaxis, :]

        dim = arr.shape[1]

        # Stage 1: Fast Walsh-Hadamard Transform O(D log D)
        try:
            from scipy.fft import fwht  # type: ignore[reportAttributeAccessIssue]

            rotated = fwht(arr, norm="ortho")
        except ImportError:
            q = _get_rotation_matrix(dim)
            rotated = np.matmul(arr, q.T)

        # Ouroboros V2 VOID-STATE: 1-bit Bypass (V-Bit)
        if effective_bits <= 1.0:
            # Shift to bit-packed binary representation
            v_bits = void_vec.pack_void_bit(rotated[0] if not is_2d else rotated)
            # In VOID-VEC mode, we return the packed bytes directly.
            return v_bits

        # Stage 2: MSE Level Quantizer
        levels = int(2**effective_bits)
        min_val = np.min(rotated, axis=1, keepdims=True)
        max_val = np.max(rotated, axis=1, keepdims=True)

        step = np.where(max_val == min_val, 1e-09, (max_val - min_val) / levels)
        quantized_mse = np.round((rotated - min_val) / step) * step + min_val

        # Stage 3: Residual & 1-bit Quantized JL (QJL) Transform
        residual = rotated - quantized_mse
        qjl_1bit_residual = np.sign(residual) * np.mean(np.abs(residual), axis=1, keepdims=True)

        turboquant_encoded = quantized_mse + qjl_1bit_residual

        # Asymmetric Min-Max Scaling to int8 [-128, 127] for maximum resolution
        min_enc = np.min(turboquant_encoded, axis=1, keepdims=True)
        max_enc = np.max(turboquant_encoded, axis=1, keepdims=True)
        range_enc = np.where(max_enc == min_enc, 1.0, max_enc - min_enc)

        normalized = (turboquant_encoded - min_enc) / range_enc
        int8_scaled = np.clip(np.round(normalized * 255.0) - 128.0, -128, 127).astype(np.int8)

        if not is_2d:
            return [float(x) for x in int8_scaled[0]]
        return int8_scaled.tolist()

    except Exception as e:
        logger.error("TurboQuant failure (Exergy Shield bypassed): %s", e)
        # Fallback to zero-vector to avoid crashing the pipeline
        return [0.0] * len(vector)


def encode_query_qjl(vector: list[float]) -> list[float]:
    """
    Rota el vector query simétricamente para coincidir con el espacio latente QJL de int8.
    """
    try:
        arr = np.array(vector, dtype=np.float32)
        is_2d = len(arr.shape) > 1
        if not is_2d:
            arr = arr[np.newaxis, :]

        dim = arr.shape[1]
        # Stage 1 Query Match: FWHT O(D log D)
        try:
            from scipy.fft import fwht  # type: ignore[reportAttributeAccessIssue]

            rotated = fwht(arr, norm="ortho")
        except ImportError:
            q = _get_rotation_matrix(dim)
            rotated = np.matmul(arr, q.T)

        if not is_2d:
            return [float(x) for x in rotated[0]]
        return rotated.tolist()
    except Exception as e:
        logger.error("TurboQuant query encoding failure: %s", e)
        return vector
