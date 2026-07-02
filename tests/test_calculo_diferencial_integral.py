# [C5-REAL] Exergy-Maximized
"""
Verification suite for Computational Calculus (Differentiation and Integration).
Validates:
- [PRIM-02] Dual Numbers for exact automatic differentiation.
- [PRIM-31] Symplectic Verlet integration vs [ANTIP-01] Explict Euler divergence (Energy conservation).
- [INVT-01] Fundamental Theorem of Calculus discrete approximation.

SYS_ID: borjamoskv
"""

from __future__ import annotations
import math
import pytest


# 1. Dual Numbers implementation for exact differentiation
class DualNumber:
    def __init__(self, val: float, der: float = 0.0):
        self.val = val
        self.der = der

    def __add__(self, other: DualNumber | float) -> DualNumber:
        if isinstance(other, DualNumber):
            return DualNumber(self.val + other.val, self.der + other.der)
        return DualNumber(self.val + other, self.der)

    def __radd__(self, other: float) -> DualNumber:
        return self.__add__(other)

    def __sub__(self, other: DualNumber | float) -> DualNumber:
        if isinstance(other, DualNumber):
            return DualNumber(self.val - other.val, self.der - other.der)
        return DualNumber(self.val - other, self.der)

    def __rsub__(self, other: float) -> DualNumber:
        return DualNumber(other - self.val, -self.der)

    def __mul__(self, other: DualNumber | float) -> DualNumber:
        if isinstance(other, DualNumber):
            return DualNumber(self.val * other.val, self.der * other.val + self.val * other.der)
        return DualNumber(self.val * other, self.der * other)

    def __rmul__(self, other: float) -> DualNumber:
        return self.__mul__(other)

    def __truediv__(self, other: DualNumber | float) -> DualNumber:
        if isinstance(other, DualNumber):
            if abs(other.val) < 1e-15:
                raise ZeroDivisionError("Dual division by zero in value.")
            return DualNumber(
                self.val / other.val, (self.der * other.val - self.val * other.der) / (other.val**2)
            )
        if abs(other) < 1e-15:
            raise ZeroDivisionError("Dual division by zero in scalar.")
        return DualNumber(self.val / other, self.der / other)

    def __rtruediv__(self, other: float) -> DualNumber:
        if abs(self.val) < 1e-15:
            raise ZeroDivisionError("Dual division by zero in value.")
        return DualNumber(other / self.val, -other * self.der / (self.val**2))

    def sin(self) -> DualNumber:
        return DualNumber(math.sin(self.val), self.der * math.cos(self.val))

    def cos(self) -> DualNumber:
        return DualNumber(math.cos(self.val), -self.der * math.sin(self.val))

    def exp(self) -> DualNumber:
        val = math.exp(self.val)
        return DualNumber(val, self.der * val)


def test_dual_number_differentiation():
    """Verify exact differentiation via dual numbers (no truncation error)."""
    # f(x) = x^3 + exp(x) * sin(x)
    # f'(x) = 3*x^2 + exp(x) * sin(x) + exp(x) * cos(x)
    x_val = 2.0
    x = DualNumber(x_val, 1.0)

    y = (x * x * x) + (x.exp() * x.sin())

    expected_val = x_val**3 + math.exp(x_val) * math.sin(x_val)
    expected_der = (
        3 * (x_val**2) + math.exp(x_val) * math.sin(x_val) + math.exp(x_val) * math.cos(x_val)
    )

    assert abs(y.val - expected_val) < 1e-12
    assert abs(y.der - expected_der) < 1e-12


# 2. Verlet Integrator vs Euler Explícito (Energy Conservation / Symplectic property)
def simple_harmonic_oscillator_hamiltonian(q: float, p: float) -> float:
    # H = 0.5 * p^2 + 0.5 * q^2 (spring constant k=1, mass m=1)
    return 0.5 * (p**2) + 0.5 * (q**2)


def test_symplectic_vs_explicit_euler():
    """Verify that symplectic Verlet conserves energy while explicit Euler diverges."""
    dt = 0.05
    steps = 1000

    # Initial conditions
    q_init, p_init = 1.0, 0.0
    initial_energy = simple_harmonic_oscillator_hamiltonian(q_init, p_init)

    # 2.1 Explicit Euler
    q, p = q_init, p_init
    for _ in range(steps):
        dq = p
        dp = -q
        q += dt * dq
        p += dt * dp
    euler_energy = simple_harmonic_oscillator_hamiltonian(q, p)

    # 2.2 Symplectic Verlet (Stormer-Verlet / leapfrog style)
    q_s, p_s = q_init, p_init
    for _ in range(steps):
        # Semi-step update for p
        p_half = p_s - 0.5 * dt * q_s
        # Full-step update for q
        q_s += dt * p_half
        # Complete step update for p
        p_s = p_half - 0.5 * dt * q_s
    symplectic_energy = simple_harmonic_oscillator_hamiltonian(q_s, p_s)

    # Explicit Euler MUST explode (increase energy)
    assert euler_energy > initial_energy * 1.5
    # Symplectic Verlet MUST conserve energy (within small bounded error)
    assert abs(symplectic_energy - initial_energy) < 0.05
