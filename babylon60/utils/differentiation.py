# [C5-REAL] Exergy-Maximized
"""
Sovereign Computational Differentiation Module.
Provides high-fidelity, exergy-efficient implementations of:
1. Automatic Differentiation (Forward AD via Dual Numbers)
2. Complex-Step Differentiation (immunity to cancellation error)
3. Richardson Extrapolation for Finite Differences (precision maximization)
4. Graph Laplacian Differentiation (topology-preserving discrete derivatives)

SYS_ID: borjamoskv
"""

from __future__ import annotations
import cmath
import math
from typing import Callable, Sequence


class Dual:
    """
    Dual number representation for exact forward-mode automatic differentiation.
    Represents x + dx * epsilon, where epsilon^2 = 0.
    """
    def __init__(self, val: float, der: float = 0.0):
        self.val = val
        self.der = der

    def __repr__(self) -> str:
        return f"Dual(val={self.val}, der={self.der})"

    def __add__(self, other: Dual | float) -> Dual:
        if isinstance(other, Dual):
            return Dual(self.val + other.val, self.der + other.der)
        return Dual(self.val + other, self.der)

    def __radd__(self, other: float) -> Dual:
        return self.__add__(other)

    def __sub__(self, other: Dual | float) -> Dual:
        if isinstance(other, Dual):
            return Dual(self.val - other.val, self.der - other.der)
        return Dual(self.val - other, self.der)

    def __rsub__(self, other: float) -> Dual:
        return Dual(other - self.val, -self.der)

    def __mul__(self, other: Dual | float) -> Dual:
        if isinstance(other, Dual):
            return Dual(
                self.val * other.val,
                self.der * other.val + self.val * other.der
            )
        return Dual(self.val * other, self.der * other)

    def __rmul__(self, other: float) -> Dual:
        return self.__mul__(other)

    def __truediv__(self, other: Dual | float) -> Dual:
        if isinstance(other, Dual):
            if abs(other.val) < 1e-15:
                raise ZeroDivisionError("Dual division by zero in value.")
            return Dual(
                self.val / other.val,
                (self.der * other.val - self.val * other.der) / (other.val ** 2)
            )
        if abs(other) < 1e-15:
            raise ZeroDivisionError("Dual division by zero in scalar.")
        return Dual(self.val / other, self.der / other)

    def __rtruediv__(self, other: float) -> Dual:
        if abs(self.val) < 1e-15:
            raise ZeroDivisionError("Dual division by zero in value.")
        return Dual(other / self.val, -other * self.der / (self.val ** 2))

    def __pow__(self, other: float) -> Dual:
        # Dual power rule: d/dx (x^n) = n * x^(n-1) * dx
        val = self.val ** other
        der = other * (self.val ** (other - 1)) * self.der
        return Dual(val, der)

    def sin(self) -> Dual:
        return Dual(math.sin(self.val), self.der * math.cos(self.val))

    def cos(self) -> Dual:
        return Dual(math.cos(self.val), -self.der * math.sin(self.val))

    def exp(self) -> Dual:
        val = math.exp(self.val)
        return Dual(val, self.der * val)

    def log(self) -> Dual:
        if self.val <= 0:
            raise ValueError("Logarithm domain error.")
        return Dual(math.log(self.val), self.der / self.val)


def complex_step_derivative(f: Callable[[complex], complex], x: float, h: float = 1e-20) -> float:
    """
    Computes the first-order derivative of a complex-analytic function f at x
    using the complex-step method. Immune to catastrophic subtractive cancellation.
    """
    return f(complex(x, h)).imag / h


def richardson_central_difference(f: Callable[[float], float], x: float, h: float = 0.1) -> float:
    """
    Computes the first-order derivative using Richardson extrapolation on central differences.
    Reduces truncation error to O(h^4).
    """
    d_h = (f(x + h) - f(x - h)) / (2 * h)
    d_h2 = (f(x + h/2) - f(x - h/2)) / h
    return (4 * d_h2 - d_h) / 3


def graph_laplacian_derivative(adjacency_matrix: Sequence[Sequence[float]], node_signals: Sequence[float]) -> list[float]:
    """
    Computes the discrete directional derivative of signals over a weighted graph
    using the Graph Laplacian operator L.
    Lf = (D - W)f
    """
    n = len(node_signals)
    if len(adjacency_matrix) != n:
        raise ValueError("Dimension mismatch between adjacency matrix and node signals.")
        
    result = [0.0] * n
    for i in range(n):
        row_sum = sum(adjacency_matrix[i])
        diag_term = row_sum * node_signals[i]
        off_diag_term = sum(adjacency_matrix[i][j] * node_signals[j] for j in range(n))
        result[i] = diag_term - off_diag_term
    return result


def integrate_trapezoidal(f: Callable[[float], float], a: float, b: float, n: int) -> float:
    """
    Computes the definite integral of f from a to b using the composite trapezoidal rule.
    Approximation error is O(h^2).
    """
    if n <= 0:
        raise ValueError("Number of intervals n must be positive.")
    h = (b - a) / n
    s = 0.5 * (f(a) + f(b))
    for i in range(1, n):
        s += f(a + i * h)
    return s * h


def integrate_simpson(f: Callable[[float], float], a: float, b: float, n: int) -> float:
    """
    Computes the definite integral of f from a to b using the composite Simpson's rule.
    n must be even. Approximation error is O(h^4).
    """
    if n <= 0 or n % 2 != 0:
        raise ValueError("Number of intervals n must be positive and even for Simpson's rule.")
    h = (b - a) / n
    s = f(a) + f(b)
    for i in range(1, n, 2):
        s += 4 * f(a + i * h)
    for i in range(2, n - 1, 2):
        s += 2 * f(a + i * h)
    return s * h / 3
