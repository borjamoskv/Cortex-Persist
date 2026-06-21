# [C5-REAL] Exergy-Maximized
"""
Motor Causal de Descomposición SVD (Singular Value Decomposition).
Convierte la Primitiva Matemática NODO 1 en un Actor Invocable para el Swarm,
con validación criptográfica y termodinámica (ClosurePayload) compatible con MTK.
"""

import logging
from datetime import datetime, timezone

import numpy as np

from cortex.types.evidence import ClosurePayload, EvidenceBundle, Source

logger = logging.getLogger("cortex.math.svd")

class SVDEngine:
    """
    Motor SVD para compresión y reducción de dimensionalidad en pipelines causales.
    """

    @staticmethod
    def _assert_invariants(A: np.ndarray, U: np.ndarray, S: np.ndarray, Vt: np.ndarray, rtol: float = 1e-5):
        """Verificación C5: A ≈ U * S * V^T"""
        S_matrix = np.zeros(A.shape)
        np.fill_diagonal(S_matrix, S)
        A_reconstructed = U @ S_matrix @ Vt
        if not np.allclose(A, A_reconstructed, rtol=rtol):
            raise ValueError("Violación de Invariante SVD: Falla de reconstrucción estructural.")

    @classmethod
    def compress_tensor(cls, tensor: np.ndarray, k_components: int, query_context: str = "SVD Tensor Compression") -> tuple[np.ndarray, ClosurePayload]:
        """
        Comprime un tensor usando SVD y sella el resultado en un ClosurePayload
        para ser validado por el MTK.
        """
        original_shape = tensor.shape
        original_size = tensor.size
        
        U, S, Vt = np.linalg.svd(tensor, full_matrices=False)
        cls._assert_invariants(tensor, U, S, Vt)
        
        # Truncamiento (Low-rank approximation)
        U_k = U[:, :k_components]
        S_k = np.diag(S[:k_components])
        Vt_k = Vt[:k_components, :]
        
        compressed_tensor = U_k @ S_k @ Vt_k
        compressed_size = U_k.size + S_k.size + Vt_k.size
        ratio = round(original_size / compressed_size, 4)
        
        logger.info(f"SVD Compression completada. Ratio (Exergía): {ratio}x")
        
        # 1. Forjar Evidence Bundle (Procedencia empírica)
        evidence = EvidenceBundle.forge(
            query=query_context,
            sources=[
                Source(
                    uri="mem://svd/tensor_input",
                    content_hash=str(hash(tensor.tobytes())),
                    metadata={"original_shape": original_shape, "k_components": k_components}
                )
            ],
            retrieved_at=datetime.now(timezone.utc)
        )
        
        # 2. Afirmación Estructural (Claims)
        claims = [
            {
                "fact_type": "dimensional_reduction",
                "compression_ratio": ratio,
                "information_loss": "low-rank-truncation",
                "final_shape": compressed_tensor.shape
            }
        ]
        
        # 3. Sellar para MTK
        payload = ClosurePayload.seal(
            claims=claims,
            evidence=evidence,
            verdict=True,
            info_exergy=ratio  # La exergía informacional es directamente el ratio de compresión
        )
        
        return compressed_tensor, payload

    @classmethod
    def pca_projection(cls, data: np.ndarray, n_components: int, query_context: str = "SVD PCA Projection") -> tuple[np.ndarray, ClosurePayload]:
        """
        Reduce la dimensionalidad de features utilizando SVD-PCA, emitiendo ClosurePayload.
        """
        mean_vec = np.mean(data, axis=0)
        centered_data = data - mean_vec
        
        U, S, Vt = np.linalg.svd(centered_data, full_matrices=False)
        V_k = Vt.T[:, :n_components]
        projected_data = centered_data @ V_k
        
        evidence = EvidenceBundle.forge(
            query=query_context,
            sources=[
                Source(
                    uri="mem://svd/pca_input",
                    content_hash=str(hash(data.tobytes())),
                    metadata={"original_features": data.shape[1], "target_features": n_components}
                )
            ],
            retrieved_at=datetime.now(timezone.utc)
        )
        
        claims = [
            {
                "fact_type": "principal_component_analysis",
                "variance_retained": "singular_values_preserved",
                "final_shape": projected_data.shape
            }
        ]
        
        payload = ClosurePayload.seal(
            claims=claims,
            evidence=evidence,
            verdict=True,
            info_exergy=data.shape[1] / n_components
        )
        
        return projected_data, payload
