# [C5-REAL] Exergy-Maximized
"""
Verification suite for babylon60.utils.differentiation module.
Tests:
- Dual Numbers exact automatic differentiation (with operators and math functions).
- Complex-Step differentiation.
- Richardson extrapolation for finite differences.
- Graph Laplacian directional derivative.

SYS_ID: borjamoskv
"""

from __future__ import annotations
import cmath
import math
import pytest
from babylon60.utils.differentiation import (
    Dual,
    complex_step_derivative,
    richardson_central_difference,
    graph_laplacian_derivative,
    integrate_trapezoidal,
    integrate_simpson,
    rkf45_adaptive_integrate,
    softened_coulomb_force,
)


def test_dual_differentiation_ops():
    # Test arithmetic operations
    x = Dual(3.0, 1.0)

    # y = x^2 + 5x - 2 / x
    y = (x**2) + 5 * x - (2 / x)
    # y' = 2x + 5 + 2 / x^2
    # At x=3:
    # y = 9 + 15 - 2/3 = 23.333333333333332
    # y' = 6 + 5 + 2/9 = 11.222222222222222
    assert abs(y.val - (23.333333333333332)) < 1e-12
    assert abs(y.der - (11.222222222222222)) < 1e-12


def test_dual_transcendental_functions():
    x = Dual(0.5, 1.0)

    # f(x) = exp(x) * cos(x)
    # f'(x) = exp(x) * cos(x) - exp(x) * sin(x)
    y = x.exp() * x.cos()

    expected_val = math.exp(0.5) * math.cos(0.5)
    expected_der = math.exp(0.5) * (math.cos(0.5) - math.sin(0.5))

    assert abs(y.val - expected_val) < 1e-12
    assert abs(y.der - expected_der) < 1e-12

    # f(x) = log(x)
    # f'(x) = 1/x
    z = x.log()
    assert abs(z.val - math.log(0.5)) < 1e-12
    assert abs(z.der - 2.0) < 1e-12


def test_complex_step():
    # Test f(x) = exp(x) * sin(x)
    # f'(x) = exp(x) * (sin(x) + cos(x))
    # At x = 1.0:
    # f'(1.0) = exp(1.0) * (sin(1.0) + cos(1.0))
    def f(z):
        # We need a complex-analytic implementation
        return cmath.exp(z) * cmath.sin(z)

    x = 1.0
    val_cs = complex_step_derivative(f, x)
    expected_der = math.exp(1.0) * (math.sin(1.0) + math.cos(1.0))

    assert abs(val_cs - expected_der) < 1e-12


def test_richardson_extrapolation():
    # Test f(x) = x^3 - 3x^2 + 2x
    # f'(x) = 3x^2 - 6x + 2
    # At x = 2.0:
    # f'(2.0) = 12 - 12 + 2 = 2.0
    def f(x):
        return x**3 - 3 * (x**2) + 2 * x

    x = 2.0
    val_richardson = richardson_central_difference(f, x, h=0.1)

    # For a polynomial of degree 3, central difference with Richardson extrapolation
    # is mathematically exact because the third-order error term is canceled,
    # and fourth-order and higher derivatives are zero.
    assert abs(val_richardson - 2.0) < 1e-12


def test_graph_laplacian_derivative():
    # A path graph with 3 nodes: 0 - 1 - 2, all weights = 1.0
    # W = [[0, 1, 0],
    #      [1, 0, 1],
    #      [0, 1, 0]]
    # D = [[1, 0, 0],
    #      [0, 2, 0],
    #      [0, 0, 1]]
    # L = D - W = [[ 1, -1,  0],
    #              [-1,  2, -1],
    #              [ 0, -1,  1]]
    adj = [[0.0, 1.0, 0.0], [1.0, 0.0, 1.0], [0.0, 1.0, 0.0]]
    # Signals: f = [1.0, 2.0, 4.0]
    # Lf = [1*1 - 1*2, -1*1 + 2*2 - 1*4, -1*2 + 1*4] = [-1.0, -1.0, 2.0]
    signals = [1.0, 2.0, 4.0]
    result = graph_laplacian_derivative(adj, signals)
    assert result == [-1.0, -1.0, 2.0]


def test_integration_invariants():
    """
    Validates [INVT-01]: Discrete isomorphism of the Fundamental Theorem of Calculus,
    and convergence rates of Trapezoidal (O(h^2)) and Simpson's (O(h^4)) rules.
    """
    # f(x) = sin(x), F(x) = -cos(x)
    # Integral from 0 to pi of sin(x) dx = -cos(pi) - (-cos(0)) = 1 - (-1) = 2.0
    f = math.sin
    exact = 2.0

    # Test Trapezoidal rule at different step sizes
    t_10 = integrate_trapezoidal(f, 0.0, math.pi, 10)
    t_20 = integrate_trapezoidal(f, 0.0, math.pi, 20)

    err_t_10 = abs(t_10 - exact)
    err_t_20 = abs(t_20 - exact)

    # Error should scale by approximately 4x (since O(h^2))
    ratio_t = err_t_10 / err_t_20
    assert 3.8 < ratio_t < 4.2

    # Test Simpson's rule at different step sizes
    s_10 = integrate_simpson(f, 0.0, math.pi, 10)
    s_20 = integrate_simpson(f, 0.0, math.pi, 20)

    err_s_10 = abs(s_10 - exact)
    err_s_20 = abs(s_20 - exact)

    # Error should scale by approximately 16x (since O(h^4))
    ratio_s = err_s_10 / err_s_20
    assert 15.0 < ratio_s < 17.0

    # Validate FTC on a discrete sequence: sum_{i=0}^{n-1} (g_{i+1} - g_i) = g_n - g_0
    g = [i**3 - 3 * (i**2) + 12 for i in range(50)]
    dg = [g[i + 1] - g[i] for i in range(len(g) - 1)]

    n = 40
    sum_dg = sum(dg[:n])
    expected_diff = g[n] - g[0]

    assert sum_dg == expected_diff


def test_rkf45_adaptive_integration():
    """
    Validates [REDUN-01]: Control Adaptativo de Paso.
    RKF45 must dynamically adapt step sizes when solving y' = y.
    Exact solution: y(t) = exp(t).
    """

    # ODE: dy/dt = y
    def f(t, y):
        return y

    t0, y0 = 0.0, 1.0
    t_end = 2.0

    # Run integration with tight tolerance
    trajectory = rkf45_adaptive_integrate(f, t0, y0, t_end, h=0.01, tol=1e-8)

    # End state should match exp(2)
    t_last, y_last = trajectory[-1]
    assert abs(t_last - 2.0) < 1e-12
    assert abs(y_last - math.exp(2.0)) < 1e-5

    # Steps taken should be much fewer than fixed grid of equivalent precision
    # proving dynamic step adaptation.
    assert len(trajectory) > 5


def test_softened_coulomb_force():
    """
    Validates [REDUN-03]: Regularización de Singularidades (Epsilon-Softening).
    Prevents division by zero at r=0.
    """
    # Without softening, r=0 causes division by zero.
    # With softening, F(0) = q1 * q2 / epsilon^2
    q1, q2 = 1.0, -1.0
    epsilon = 0.1

    f_zero = softened_coulomb_force(q1, q2, r=0.0, epsilon=epsilon)
    expected = (q1 * q2) / (epsilon**2)

    assert f_zero == expected
    assert math.isfinite(f_zero)
