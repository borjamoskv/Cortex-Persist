import logging

import torch

logger = logging.getLogger(__name__)

# ==============================================================================
# C5-REAL: AUTODIDACT LINEAR ALGEBRA PRIMITIVES (BLOCK 1)
# ==============================================================================
# This module implements the foundational concepts of advanced linear algebra as 
# deterministic, high-exergy functions within the MOSKV-1 APEX framework. 
# It bridges abstract theoretical definitions with executable PyTorch models.
# ==============================================================================

# 1. DESCOMPOSICIÓN SVD (Singular Value Decomposition)
def compute_svd(matrix: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Computes the Singular Value Decomposition (SVD) of a matrix.
    Returns (U, S, Vh).
    """
    U, S, Vh = torch.linalg.svd(matrix, full_matrices=False)
    return U, S, Vh

# 2. DESCOMPOSICIÓN LU (LU Decomposition)
def compute_lu(matrix: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Computes the LU decomposition with partial pivoting: P @ A = L @ U.
    Returns (P, L, U).
    """
    P, L, U = torch.linalg.lu(matrix)
    return P, L, U

# 3. DESCOMPOSICIÓN QR (QR Decomposition)
def compute_qr(matrix: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Computes the QR decomposition of a matrix.
    Returns (Q, R).
    """
    Q, R = torch.linalg.qr(matrix, mode='reduced')
    return Q, R

# 4. EIGENDECOMPOSICIÓN (Eigendecomposition)
def compute_eigendecomposition(matrix: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
    """
    Computes eigenvalues and eigenvectors of a symmetric/Hermitian matrix.
    Returns (eigenvalues, eigenvectors).
    """
    # Assuming the matrix is symmetric for real-valued eigendecomposition
    L, V = torch.linalg.eigh(matrix)
    return L, V

# 5. PSEUDOINVERSA DE MOORE-PENROSE (Moore-Penrose Pseudoinverse)
def compute_pseudo_inverse(matrix: torch.Tensor) -> torch.Tensor:
    """
    Computes the Moore-Penrose pseudoinverse using SVD.
    """
    return torch.linalg.pinv(matrix)

# 6. PRODUCTO DE KRONECKER (Kronecker Product)
def compute_kronecker_product(A: torch.Tensor, B: torch.Tensor) -> torch.Tensor:
    """
    Computes the Kronecker product of two matrices.
    """
    return torch.kron(A, B)

# 7. NORMA FROBENIUS (Frobenius Norm)
def compute_frobenius_norm(matrix: torch.Tensor) -> torch.Tensor:
    """
    Computes the Frobenius norm (L2 matrix norm) of a matrix.
    """
    return torch.linalg.matrix_norm(matrix, ord='fro')

# 8. MATRIZ SEMIDEFINIDA POSITIVA (Positive Semi-Definite Matrix)
def is_positive_semi_definite(matrix: torch.Tensor, tolerance: float = 1e-5) -> bool:
    """
    Checks if a symmetric matrix is Positive Semi-Definite (PSD) 
    by ensuring all eigenvalues are >= -tolerance.
    """
    if not torch.allclose(matrix, matrix.T, atol=tolerance):
        return False
    eigenvalues = torch.linalg.eigvalsh(matrix)
    return bool(torch.all(eigenvalues >= -tolerance))

# 9. TRAZA DE UNA MATRIZ (Matrix Trace)
def compute_trace(matrix: torch.Tensor) -> torch.Tensor:
    """
    Computes the sum of the diagonal elements of a matrix.
    """
    return torch.trace(matrix)

# 10. RANGO NUMÉRICO (Numerical Rank)
def compute_numerical_rank(matrix: torch.Tensor, tol: float = 1e-5) -> int:
    """
    Computes the numerical rank of a matrix (number of singular values > tol).
    """
    return int(torch.linalg.matrix_rank(matrix, tol=tol).item())

# ==============================================================================
# EXECUTION & DIAGNOSTICS (C5-REAL VALIDATION)
# ==============================================================================
if __name__ == "__main__":
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
    
    logger.info(">> MOSKV-1 APEX: INITIALIZING C5-REAL LINEAR ALGEBRA PRIMITIVES (BLOCK 1) <<\n")

    # Define a positive semi-definite matrix for testing
    A = torch.tensor([[2.0, -1.0, 0.0],
                      [-1.0, 2.0, -1.0],
                      [0.0, -1.0, 2.0]])
    
    B = torch.tensor([[1.0, 2.0], 
                      [3.0, 4.0]])

    logger.info("--- 1. SVD ---")
    U, S, Vh = compute_svd(A)
    logger.info(f"Singular values of A: {S.tolist()}")

    logger.info("\n--- 2. LU ---")
    P, L, U_lu = compute_lu(A)
    logger.info(f"L diagonal: {torch.diag(L).tolist()}")

    logger.info("\n--- 3. QR ---")
    Q, R = compute_qr(A)
    logger.info(f"R diagonal: {torch.diag(R).tolist()}")

    logger.info("\n--- 4. Eigendecomposition ---")
    L_eig, V_eig = compute_eigendecomposition(A)
    logger.info(f"Eigenvalues of A: {L_eig.tolist()}")

    logger.info("\n--- 5. Pseudoinverse ---")
    A_pinv = compute_pseudo_inverse(B)
    identity_approx = B @ A_pinv
    logger.info(f"B @ B_pinv (should be ~I):\n{identity_approx}")

    logger.info("\n--- 6. Kronecker Product ---")
    K = compute_kronecker_product(torch.eye(2), B)
    logger.info(f"Kronecker(I, B) shape: {K.shape}")

    logger.info("\n--- 7. Frobenius Norm ---")
    norm_A = compute_frobenius_norm(A)
    logger.info(f"Frobenius Norm of A: {norm_A.item():.4f}")

    logger.info("\n--- 8. Positive Semi-Definite ---")
    is_psd = is_positive_semi_definite(A)
    logger.info(f"Is A Positive Semi-Definite? {is_psd}")

    logger.info("\n--- 9. Trace ---")
    trace_A = compute_trace(A)
    logger.info(f"Trace of A: {trace_A.item():.4f} (Expected: 6.0)")

    logger.info("\n--- 10. Numerical Rank ---")
    rank_A = compute_numerical_rank(A)
    logger.info(f"Numerical Rank of A: {rank_A} (Expected: 3)")

    logger.info("\n>> C5-REAL DIAGNOSTICS COMPLETE: ZERO ANERGIA. <<")
