from collections.abc import Callable

import jax
import jax.numpy as jnp

# ==============================================================================
# C5-REAL: AUTODIDACT VECTOR CALCULUS PRIMITIVES (GOAT-MATH 011-020)
# ==============================================================================
# Operationalizing Multivariable Calculus and advanced differential topologies.
# These primitives form the causal motor for backpropagation, geometry, and frequency.
# ==============================================================================

# GOAT-MATH-011: GRADIENTE VECTORIAL (Vector Gradient)
# Represents the direction of maximum change. ∇f
def compute_gradient(f: Callable[[jnp.ndarray], float]) -> Callable[[jnp.ndarray], jnp.ndarray]:
    """
    Returns a function that computes the exact analytical gradient of a scalar function.
    """
    return jax.grad(f)

# GOAT-MATH-012: MATRIZ JACOBIANA (Jacobian Matrix)
# First-order partial derivatives of a vector-valued function. J_ij = ∂f_i / ∂x_j
def compute_jacobian(f: Callable[[jnp.ndarray], jnp.ndarray]) -> Callable[[jnp.ndarray], jnp.ndarray]:
    """
    Returns a function that computes the Jacobian matrix using forward-mode auto-diff.
    Forward mode (jacfwd) is generally more efficient for tall Jacobians.
    """
    return jax.jacfwd(f)

# GOAT-MATH-013: MATRIZ HESSIANA (Hessian Matrix)
# Second-order partial derivatives of a scalar function. Curvature of the error space.
def compute_hessian(f: Callable[[jnp.ndarray], float]) -> Callable[[jnp.ndarray], jnp.ndarray]:
    """
    Returns a function that computes the exact Hessian matrix.
    """
    return jax.hessian(f)

# GOAT-MATH-014: REGLA CADENA GENERALIZADA (Generalized Chain Rule)
# Handled implicitly by JAX's Autodiff computational graph (vjp / jvp).
def chain_rule_vjp(f: Callable, g: Callable, x: jnp.ndarray, cotangent: jnp.ndarray) -> jnp.ndarray:
    """
    Evaluates the gradient of f(g(x)) explicitly using Vector-Jacobian Products (VJP).
    """
    # y = g(x)
    y, g_vjp = jax.vjp(g, x)
    # z = f(y)
    z, f_vjp = jax.vjp(f, y)
    
    # Pull back the cotangent
    (grad_y,) = f_vjp(cotangent)
    (grad_x,) = g_vjp(grad_y)
    return grad_x

# GOAT-MATH-015: DERIVADA DIRECCIONAL (Directional Derivative)
# ∇_v f = ∇f · v (The rate of change of f in the direction of vector v)
def directional_derivative(f: Callable[[jnp.ndarray], float], x: jnp.ndarray, v: jnp.ndarray) -> float:
    """
    Computes the directional derivative of f at x in the direction v.
    (v is automatically normalized within the function).
    """
    v_norm = v / jnp.linalg.norm(v)
    grad_f_at_x = jax.grad(f)(x)
    return float(jnp.dot(grad_f_at_x, v_norm))

# GOAT-MATH-016: OPERADOR LAPLACIANO (Laplacian Operator)
# ∇²f = tr(Hessian(f)) = Sum of unmixed second partial derivatives.
def compute_laplacian(f: Callable[[jnp.ndarray], float], x: jnp.ndarray) -> float:
    """
    Computes the Laplacian of a scalar field f at point x.
    """
    hessian_matrix = jax.hessian(f)(x)
    return float(jnp.trace(hessian_matrix))

# GOAT-MATH-017: DIFERENCIACIÓN AUTOMÁTICA (Automatic Differentiation)
# Acknowledging JAX's JVP (Jacobian-Vector Product) for forward-mode diff.
def auto_diff_jvp(f: Callable[[jnp.ndarray], jnp.ndarray], x: jnp.ndarray, v: jnp.ndarray) -> tuple[jnp.ndarray, jnp.ndarray]:
    """
    Evaluates f(x) and the derivative of f at x along direction v (forward-mode).
    """
    return jax.jvp(f, (x,), (v,))

# GOAT-MATH-018: SERIE TAYLOR MULTIVARIABLE (Multivariable Taylor Series)
# Approximating f(x) locally: f(x) ~ f(a) + ∇f(a)^T (x-a) + 1/2 (x-a)^T H(a) (x-a)
def taylor_approximation_2nd_order(f: Callable[[jnp.ndarray], float], a: jnp.ndarray, x: jnp.ndarray) -> float:
    """
    Computes the second-order Taylor polynomial approximation of f near point a, evaluated at x.
    """
    f_a = f(a)
    grad_a = jax.grad(f)(a)
    hess_a = jax.hessian(f)(a)
    
    delta = x - a
    term_1 = jnp.dot(grad_a, delta)
    term_2 = 0.5 * jnp.dot(delta, jnp.dot(hess_a, delta))
    return float(f_a + term_1 + term_2)

# GOAT-MATH-019: INTEGRAL DE LÍNEA (Line Integral)
# ∫_C F · dr : Integral of a vector field F along curve C parametrized by r(t).
@jax.jit(static_argnames=['F', 'r', 'num_points'])
def line_integral(F: Callable[[jnp.ndarray], jnp.ndarray], 
                  r: Callable[[float], jnp.ndarray], 
                  t0: float, t1: float, num_points: int = 1000) -> float:
    """
    Numerically computes the line integral of vector field F along parametric curve r(t).
    """
    t = jnp.linspace(t0, t1, num_points)
    dt = (t1 - t0) / (num_points - 1)
    
    # Derivative of path r(t) (since r(t) outputs a vector, we use jacfwd)
    r_dot = jax.vmap(jax.jacfwd(r))(t)
    # Vector field F evaluated along path r(t)
    F_r = jax.vmap(F)(jax.vmap(r)(t))
    
    # Dot product of F(r(t)) and r'(t)
    dot_products = jax.vmap(jnp.dot)(F_r, r_dot)
    
    # Trapezoidal integration
    integral = jnp.sum((dot_products[:-1] + dot_products[1:]) / 2.0) * dt
    return integral

# GOAT-MATH-020: TRANSFORMADA DE FOURIER (FFT)
# Time-domain to Frequency-domain structural transformation.
@jax.jit
def compute_fft(x: jnp.ndarray) -> jnp.ndarray:
    """
    Computes the Fast Fourier Transform of a 1D discrete signal using JAX.
    """
    return jnp.fft.fft(x)

# ==============================================================================
# EXECUTION & DIAGNOSTICS (C5-REAL VALIDATION)
# ==============================================================================
if __name__ == "__main__":
    print(">> MOSKV-1 APEX: INITIALIZING C5-REAL VECTOR CALCULUS PRIMITIVES <<\n")

    # [011, 013, 016, 018] Scalar Field f(x, y) = x^2 + 3y^2 + xy
    def f_scalar(v: jnp.ndarray) -> float:
        x, y = v[0], v[1]
        return x**2 + 3.0*y**2 + x*y
    
    v0 = jnp.array([1.0, 2.0])
    print(f"[011] Gradient of f at (1,2): {compute_gradient(f_scalar)(v0)}")
    print(f"[013] Hessian of f at (1,2):\n{compute_hessian(f_scalar)(v0)}")
    print(f"[016] Laplacian of f at (1,2): {compute_laplacian(f_scalar, v0)}")
    
    approx = taylor_approximation_2nd_order(f_scalar, jnp.array([1.0, 2.0]), jnp.array([1.1, 2.1]))
    actual = f_scalar(jnp.array([1.1, 2.1]))
    print(f"[018] Taylor 2nd Order approx at (1.1, 2.1): {approx:.4f} (Actual: {actual:.4f})\n")

    # [012] Vector Field f(x, y) = [x^2y, 5x + sin(y)]
    def f_vector(v: jnp.ndarray) -> jnp.ndarray:
        x, y = v[0], v[1]
        return jnp.array([x**2 * y, 5.0*x + jnp.sin(y)])

    print(f"[012] Jacobian of vector field at (1,0):\n{compute_jacobian(f_vector)(jnp.array([1.0, 0.0]))}\n")

    # [015, 017] Directional Derivative & JVP
    direction = jnp.array([1.0, 1.0])
    dir_deriv = directional_derivative(f_scalar, v0, direction)
    print(f"[015] Directional Deriv of f at (1,2) in dir (1,1): {dir_deriv:.4f}")
    
    val, jvp_val = auto_diff_jvp(f_vector, jnp.array([1.0, 0.0]), jnp.array([1.0, 1.0]))
    print(f"[017] JVP of vector field at (1,0) along (1,1): {jvp_val}\n")

    # [019] Line Integral
    # Field F(x, y) = [y, x]. Curve r(t) = [cos(t), sin(t)] from 0 to pi.
    def F_field(v: jnp.ndarray) -> jnp.ndarray:
        return jnp.array([v[1], v[0]])
    def r_curve(t: float) -> jnp.ndarray:
        return jnp.array([jnp.cos(t), jnp.sin(t)])
    
    line_int = line_integral(F_field, r_curve, 0.0, jnp.pi)
    print(f"[019] Line integral of F=[y,x] along semi-circle: {line_int:.5f}\n")

    # [020] FFT
    signal = jnp.array([1.0, 0.0, -1.0, 0.0])
    fft_res = compute_fft(signal)
    print(f"[020] FFT of [1, 0, -1, 0]: {fft_res}")

    print("\n>> C5-REAL DIAGNOSTICS COMPLETE: VECTOR PRIMITIVES INSTANTIATED. <<")
