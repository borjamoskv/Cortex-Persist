# C5-REAL
import mpmath

# Precisión para BABYLON-60 (Fixed-point a 10^20)
mpmath.mp.dps = 25
SCALE_FACTOR = 10**20


def get_riemann_zero(n: int) -> str:
    """
    Calcula el n-ésimo cero no trivial de la función Zeta de Riemann
    y retorna su representación purgada de entropía (Fixed-Point BABYLON-60).
    """
    if n < 1:
        raise ValueError("El índice n debe ser >= 1")

    # mpmath.zetazero retorna el cero complejo. Tomamos la parte imaginaria.
    z = mpmath.zetazero(n)
    t = z.imag

    # Escalado a Fixed-Point para erradicar float64
    t_fixed = int(t * SCALE_FACTOR)
    return str(t_fixed)


if __name__ == "__main__":
    # Test rápido de extracción
    print(get_riemann_zero(1))  # aprox 14.13472514173469379045725 -> 1413472514173469379045725
