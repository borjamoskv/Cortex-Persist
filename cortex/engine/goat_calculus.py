import jax
import jax.numpy as jnp
from typing import Callable, Tuple

# ==============================================================================
# C5-REAL: AUTODIDACT CALCULUS PRIMITIVES
# ==============================================================================
# This module implements the foundational concepts of calculus as deterministic,
# high-exergy functions within the MOSKV-1 APEX framework. It bridges abstract
# theoretical definitions with executable computational models using JAX.
# ==============================================================================

# 1. LÍMITE (Limit)
# Mathematically: lim(x->a) f(x) = L
# Computationally: Evaluate f(x) at x = a ± epsilon.
def compute_limit(f: Callable[[jnp.ndarray], jnp.ndarray], a: float, epsilon: float = 1e-5) -> Tuple[jnp.ndarray, jnp.ndarray]:
    """
    Computes the numerical limit of f(x) as x approaches a.
    Returns (left_limit, right_limit).
    """
    left_lim = f(jnp.array(a - epsilon))
    right_lim = f(jnp.array(a + epsilon))
    return left_lim, right_lim

# 2. CONTINUIDAD (Continuity)
# A function is continuous at x=a if lim(x->a) f(x) == f(a).
def check_continuity(f: Callable[[jnp.ndarray], jnp.ndarray], a: float, tolerance: float = 1e-4) -> bool:
    """
    Evaluates the structural continuity of a function at point a.
    """
    val_at_a = f(jnp.array(a))
    left_lim, right_lim = compute_limit(f, a)
    # Check if left, right, and actual value converge within tolerance
    return bool(jnp.abs(left_lim - val_at_a) < tolerance and jnp.abs(right_lim - val_at_a) < tolerance)

# 3. DERIVADA (Derivative)
# The instantaneous rate of change. 
# Computationally solved using JAX's auto-differentiation (Autograd).
def compute_derivative(f: Callable[[float], float]) -> Callable[[float], float]:
    """
    Returns the exact first derivative function using JAX auto-differentiation.
    """
    return jax.grad(f)

# 4. TASA DE CAMBIO & 5. PENDIENTE (Rate of Change / Slope)
# Both conceptually relate to the derivative evaluated at a specific domain point.
def rate_of_change(f: Callable[[float], float], x: float) -> float:
    """
    Evaluates the instantaneous rate of change (pendiente) at x.
    """
    df = jax.grad(f)
    return float(df(float(x)))

# 6. INTEGRAL DEFINIDA (Definite Integral)
# Area under the curve between bounds [a, b].
# Implemented here via deterministic Riemann sum (Vectorized).
@jax.jit(static_argnames=['f'])
def definite_integral(f: Callable[[jnp.ndarray], jnp.ndarray], a: float, b: float, num_points: int = 1000) -> jnp.ndarray:
    """
    Computes the definite integral of f(x) from a to b using the trapezoidal rule.
    """
    x = jnp.linspace(a, b, num_points)
    dx = (b - a) / (num_points - 1)
    y = f(x)
    # Trapezoidal integration
    area = jnp.sum((y[:-1] + y[1:]) / 2.0) * dx
    return area

# 7. INTEGRAL INDEFINIDA (Indefinite Integral / Antiderivative)
# Computationally represented as the cumulative sum area over a domain.
@jax.jit(static_argnames=['f'])
def indefinite_integral(f: Callable[[jnp.ndarray], jnp.ndarray], a: float, b: float, num_points: int = 1000) -> Tuple[jnp.ndarray, jnp.ndarray]:
    """
    Returns the domain (x) and the cumulative integral (F(x)) for an indefinite integral approximation.
    """
    x = jnp.linspace(a, b, num_points)
    y = f(x)
    dx = (b - a) / (num_points - 1)
    F_x = jnp.cumsum(y) * dx
    return x, F_x

# 8. SUCESIÓN (Sequence)
# A discrete mapping of N to R.
@jax.jit(static_argnames=['f', 'n_terms'])
def generate_sequence(f: Callable[[jnp.ndarray], jnp.ndarray], n_terms: int) -> jnp.ndarray:
    """
    Generates a succession of values for n = 1, 2, ..., n_terms.
    """
    n = jnp.arange(1, n_terms + 1, dtype=jnp.float32)
    return f(n)

# 9. SERIE (Series)
# The cumulative sum of a sequence.
@jax.jit(static_argnames=['f', 'n_terms'])
def compute_series(f: Callable[[jnp.ndarray], jnp.ndarray], n_terms: int) -> jnp.ndarray:
    """
    Computes the infinite series (up to n_terms) by summing the sequence.
    Returns the cumulative sum array to observe convergence.
    """
    sequence = generate_sequence(f, n_terms)
    return jnp.cumsum(sequence)

# ==============================================================================
# EXECUTION & DIAGNOSTICS (C5-REAL VALIDATION)
# ==============================================================================
if __name__ == "__main__":
    print(">> MOSKV-1 APEX: INITIALIZING C5-REAL CALCULUS PRIMITIVES <<\n")

    # Define a test function: f(x) = x^2
    def f_x2(x):
        return x**2

    # 1 & 2: Limit & Continuity
    x_val = 3.0
    lim_l, lim_r = compute_limit(f_x2, x_val)
    is_cont = check_continuity(f_x2, x_val)
    print(f"[1,2] Limit of x^2 at x={x_val}: Left={lim_l:.5f}, Right={lim_r:.5f}")
    print(f"      Continuous at x={x_val}? {is_cont}\n")

    # 3, 4, 5: Derivative, Rate of Change, Slope
    slope = rate_of_change(f_x2, x_val)
    print(f"[3,4,5] Derivative (Slope/Rate of change) of x^2 at x={x_val}: {slope:.5f} (Expected: 6.0)\n")

    # 6: Definite Integral
    # Integral of x^2 from 0 to 3 should be 3^3/3 = 9
    area = definite_integral(f_x2, 0.0, 3.0)
    print(f"[6] Definite Integral of x^2 from 0 to 3: {area:.5f} (Expected: ~9.0)\n")

    # 8 & 9: Sequence & Series
    # Let's use the sequence 1/n^2 (Basel problem converges to pi^2/6 ~ 1.64493)
    def f_basel(n):
        return 1.0 / (n**2)
    
    seq = generate_sequence(f_basel, 5)
    series_sum = compute_series(f_basel, 10000)[-1]
    
    print(f"[8] Sequence (first 5 terms of 1/n^2): {seq}")
    print(f"[9] Series (Sum of 10000 terms of 1/n^2): {series_sum:.5f} (Expected: ~1.64493)\n")

    print(">> C5-REAL DIAGNOSTICS COMPLETE: ZERO ANERGIA. <<")
