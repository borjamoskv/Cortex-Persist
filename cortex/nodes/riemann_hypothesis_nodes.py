# C5-REAL
import hashlib

from pydantic import BaseModel, Field


class RiemannZeroNode(BaseModel):
    """
    Entidad Epistémica para un cero validado de la función Zeta de Riemann.
    Obliga a la erradicación de float64 (BABYLON-60, fixed-point scale 10^20).
    """
    id: str = Field(..., description="ID único")
    n_index: int = Field(..., description="Índice natural del cero en la franja crítica.")
    imaginary_part_scaled: str = Field(..., description="Componente imaginaria en formato fixed-point BABYLON-60")
    scale_factor: str = Field(..., description="Factor de escala usado")
    real_part_scaled: str = Field(..., description="Parte real escalada (0.5 * scale_factor)")
    hash: str = Field(..., description="Hash parcial inmutable que sella esta aserción.")
    injected_at: str = Field(..., description="Fecha de inyección ISO")
    taint_signature: str = Field(..., description="Sello Ouroboros BFT Taint (SAGA-2) para evitar Apoptosis celular.")

    def compute_hash(self) -> str:
        payload = f"{self.id}|{self.n_index}|{self.imaginary_part_scaled}|{self.real_part_scaled}|{self.taint_signature}".encode()
        return hashlib.sha256(payload).hexdigest()[:16]

