"""
C5-REAL EXECUTION KERNEL: CALCULUS PRIMITIVES
Operator: borjamoskv
Aesthetic: Industrial Noir 2026
Entity: MOSKV-1 APEX

Formalization of 11 Calculus Primitives:
1. Sucesión (Sequence)
2. Serie (Series)
3. Límite (Limit)
4. Continuidad (Continuity)
5. Derivada (Derivative)
6. Tasa de cambio (Rate of Change)
7. Pendiente (Slope)
8. Integral
9. Integral definida (Definite Integral)
10. Integral indefinida (Indefinite Integral)
11. Cálculo (Calculus - Orchestration)
"""

from collections.abc import Callable
from typing import Any

import numpy as np
import sympy as sp
import torch


class CalculusPrimitives:
    """
    C5-REAL implementation of fundamental Calculus primitives.
    Maps abstract concepts to computable tensors and symbolic graphs.
    """
    
    def __init__(self):
        self.x = sp.Symbol('x', real=True)
        self.n = sp.Symbol('n', integer=True, positive=True)

    # 1. Sucesión (Sequence)
    def sucesion_term(self, expr: sp.Expr, index: int) -> float:
        """
        Calculates the n-th term of a sequence a_n.
        """
        return float(expr.subs(self.n, index).evalf())

    # 2. Serie (Series)
    def serie_sum(self, expr: sp.Expr, lower: int, upper: int) -> float:
        """
        Calculates the partial sum of a series from n=lower to n=upper.
        """
        return float(sp.Sum(expr, (self.n, lower, upper)).doit().evalf())

    # 3. Límite (Limit)
    def limite(self, expr: sp.Expr, point: float, direction: str = '+-') -> Any:
        """
        Evaluates the limit of a function as x approaches a point.
        """
        return sp.limit(expr, self.x, point, dir=direction)

    # 4. Continuidad (Continuity)
    def es_continua(self, expr: sp.Expr, point: float) -> bool:
        """
        Checks if a function is continuous at a given point:
        f(a) is defined, lim x->a f(x) exists, and lim x->a f(x) == f(a).
        """
        try:
            val = expr.subs(self.x, point)
            if val.has(sp.oo, -sp.oo, sp.nan, sp.zoo):
                return False
            lim = self.limite(expr, point)
            return bool(sp.Eq(val, lim))
        except Exception:
            return False

    # 5. Derivada (Derivative - Symbolic)
    def derivada_simbolica(self, expr: sp.Expr, order: int = 1) -> sp.Expr:
        """
        Computes the n-th order symbolic derivative of a function.
        """
        return sp.diff(expr, self.x, order)

    # 6. Tasa de cambio (Rate of Change - Autograd)
    def tasa_de_cambio(self, func: Callable[[torch.Tensor], torch.Tensor], point: float) -> float:
        """
        Computes the instantaneous rate of change using PyTorch Autograd.
        """
        t_point = torch.tensor([point], dtype=torch.float64, requires_grad=True)
        y = func(t_point)
        y.backward()
        return float(t_point.grad.item())

    # 7. Pendiente (Slope - Secant / Average Rate of Change)
    def pendiente_secante(self, func: Callable[[float], float], x1: float, x2: float) -> float:
        """
        Computes the slope of the secant line between two points.
        m = (f(x2) - f(x1)) / (x2 - x1)
        """
        if np.isclose(x1, x2):
            raise ValueError("C5-REAL Guard: x1 and x2 must be distinct to compute secant slope.")
        return (func(x2) - func(x1)) / (x2 - x1)

    # 8. Integral indefinida (Indefinite Integral)
    def integral_indefinida(self, expr: sp.Expr) -> sp.Expr:
        """
        Computes the symbolic indefinite integral (antiderivative).
        """
        return sp.integrate(expr, self.x)

    # 9. Integral definida (Definite Integral)
    def integral_definida(self, expr: sp.Expr, a: float, b: float) -> float:
        """
        Computes the definite integral over [a, b].
        """
        return float(sp.integrate(expr, (self.x, a, b)).evalf())

    # 10. Integral (Numerical Approximation via PyTorch/Trapezoidal)
    def integral_numerica(self, func: Callable[[torch.Tensor], torch.Tensor], a: float, b: float, steps: int = 10000) -> float:
        """
        Computes numerical integral using the trapezoidal rule over tensors.
        """
        t = torch.linspace(a, b, steps, dtype=torch.float64)
        y = func(t)
        return float(torch.trapz(y, t).item())

# 11. Orchestration: Verification Kernel
def execute_calculus_verification():
    calc = CalculusPrimitives()
    
    print("[C5-REAL] INITIATING CALCULUS PRIMITIVES VERIFICATION")
    
    # Sequence & Series: a_n = 1 / 2^n
    a_n = 1 / (2**calc.n)
    seq_5 = calc.sucesion_term(a_n, 5)
    ser_10 = calc.serie_sum(a_n, 1, 10)
    print(f"[+] Sucesión (a_5): {seq_5}")
    print(f"[+] Serie (Sum 1..10): {ser_10}")

    # Limit & Continuity: f(x) = sin(x)/x at x=0
    f_x = sp.sin(calc.x) / calc.x
    lim_0 = calc.limite(f_x, 0)
    cont_0 = calc.es_continua(f_x, 0) # Expected False since it's 0/0 symbolically at substitution
    print(f"[+] Límite sin(x)/x en x=0: {lim_0}")
    print(f"[+] Continuidad en x=0: {cont_0}")

    # Derivative & Indefinite Integral: f(x) = x^3
    poly = calc.x**3
    der = calc.derivada_simbolica(poly)
    indef_int = calc.integral_indefinida(poly)
    print(f"[+] Derivada de x^3: {der}")
    print(f"[+] Integral indefinida de x^3: {indef_int}")

    # Tasa de cambio & Pendiente
    def py_func(x_t): return x_t**3
    def raw_func(x_val): return x_val**3
    
    rate = calc.tasa_de_cambio(py_func, 2.0)
    slope = calc.pendiente_secante(raw_func, 2.0, 2.001)
    print(f"[+] Tasa de cambio (Autograd) en x=2: {rate}")
    print(f"[+] Pendiente secante [2, 2.001]: {slope}")

    # Definite & Numerical Integral
    def_int = calc.integral_definida(poly, 0.0, 2.0)
    num_int = calc.integral_numerica(py_func, 0.0, 2.0)
    print(f"[+] Integral definida [0, 2] de x^3: {def_int}")
    print(f"[+] Integral numérica [0, 2]: {num_int}")

    print("[C5-REAL] VERIFICATION COMPLETE. ZERO ANERGY.")

if __name__ == "__main__":
    execute_calculus_verification()
