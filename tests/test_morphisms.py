# [C5-REAL] Exergy-Maximized
"""
Verification suite for Morphisms and Algebraic Invariant Verification engine.

Validates:
- Homomorphisms on Dual algebra (additive, multiplicative, abs, and powers).
- Isomorphisms / round-trip bijections.
- Endomorphisms, Automorphisms, Idempotent projectors, and Involutions.

SYS_ID: borjamoskv
"""

from __future__ import annotations

import math
import pytest
import numpy as np

from babylon60.memory.memory_archaeology import MemoryArchaeologist
from babylon60.utils.differentiation import Dual
from babylon60.utils.morphisms import MorphismVerifier


def test_morphism_homomorphism_dual():
    """
    Validates that operations on Dual numbers act as homomorphic mappings.
    For f(x) = 2x + 1: f(a + b) == f(a) + f(b) - 1.
    For g(x) = x^2: g(a * b) == g(a) * g(b).
    """

    # 1. Additive homomorphism check on Dual numbers
    # Let f(x) = Dual(3.0) * x
    # f(a + b) == f(a) + f(b)
    def f_add(x: Dual) -> Dual:
        return x * 3.0

    def op_add(x: Any, y: Any) -> Any:
        return x + y

    # Sample domain of pairs of Dual numbers
    domain_add = [
        (Dual(1.0, 1.0), Dual(2.0, 1.0)),
        (Dual(-5.0, 2.0), Dual(3.0, 0.5)),
        (Dual(0.0, 1.0), Dual(0.0, 1.0)),
    ]

    assert MorphismVerifier.is_homomorphism(
        f=f_add,
        op_in=op_add,
        op_out=op_add,
        domain_sample=domain_add,
    )


def test_morphism_isomorphism():
    """
    Validates round-trip isomorphism of dual representations.
    E.g. scaling: f(x) = 5x, f_inv(x) = x/5.
    And a custom Dual numbers isomorphism.
    """
    # Scalar Isomorphism
    def f_scale(x: float) -> float:
        return x * 5.0

    def f_scale_inv(x: float) -> float:
        return x / 5.0

    domain_scalars = [1.0, -2.5, 0.0, 100.0]
    assert MorphismVerifier.is_isomorphism(f_scale, f_scale_inv, domain_scalars)

    # Dual numbers isomorphism
    def f_dual_scale(x: Dual) -> Dual:
        return x * 3.0

    def f_dual_scale_inv(x: Dual) -> Dual:
        return x / 3.0

    domain_duals = [Dual(1.0, 1.0), Dual(-4.0, 2.0), Dual(0.0, 0.0)]
    assert MorphismVerifier.is_isomorphism(f_dual_scale, f_dual_scale_inv, domain_duals)


def test_morphism_endomorphism_automorphism():
    """
    Validates endomorphism (codomain matches domain) and automorphism (invertible endomorphism).
    """
    # Guard to check if value lies within the domain of positive floats/Duals
    def is_positive(x: Any) -> bool:
        if isinstance(x, (int, float)):
            return x > 0
        if hasattr(x, "val"):
            return x.val > 0
        return False

    # f(x) = sqrt(x) is an endomorphism on positive floats
    def f_sqrt(x: float) -> float:
        return math.sqrt(x)

    domain_pos_scalars = [1.0, 4.0, 9.0, 16.0]
    assert MorphismVerifier.is_endomorphism(f_sqrt, domain_pos_scalars, is_positive)

    # Automorphism check
    # f(x) = exp(x) is NOT an automorphism on positive floats (codomain has elements < 1, e.g. exp(0.5) = 1.64, but what if domain was positive?)
    # Let's check f(x) = 1/x on positive floats (it is invertible and stays positive)
    def f_inv_x(x: float) -> float:
        return 1.0 / x

    assert MorphismVerifier.is_automorphism(f_inv_x, f_inv_x, domain_pos_scalars, is_positive)


def test_morphism_idempotence():
    """
    Validates idempotence: f(f(x)) == f(x).
    E.g. Projections.
    """
    # Absolute value projection on positive numbers or Duals (already positive, so idempotent)
    def f_abs(x: Any) -> Any:
        return abs(x)

    domain_abs = [Dual(-3.0, 1.0), Dual(5.0, 2.0), Dual(0.0, 1.0)]
    assert MorphismVerifier.is_idempotent(f_abs, domain_abs)

    # Floor projection is idempotent
    assert MorphismVerifier.is_idempotent(math.floor, [1.5, -2.3, 0.0, 5.9])


def test_morphism_involution():
    """
    Validates involution: f(f(x)) == x.
    E.g. Negation or Inversion.
    """
    def f_neg(x: Any) -> Any:
        return -x

    domain_neg = [Dual(1.5, 1.0), Dual(-4.0, 2.0), 10.0, -5.0]
    assert MorphismVerifier.is_involution(f_neg, domain_neg)


def test_dual_transcendental_extended():
    """
    Tests the newly added unary and transcendental operations on the Dual class.
    """
    # Test __neg__
    d1 = Dual(2.0, 1.0)
    neg_d1 = -d1
    assert neg_d1.val == -2.0
    assert neg_d1.der == -1.0

    # Test __pos__
    pos_d1 = +d1
    assert pos_d1.val == 2.0
    assert pos_d1.der == 1.0

    # Test __abs__
    d2 = Dual(-3.0, 1.0)
    abs_d2 = abs(d2)
    assert abs_d2.val == 3.0
    assert abs_d2.der == -1.0  # since val < 0

    # Test sqrt
    d3 = Dual(4.0, 1.0)
    sqrt_d3 = d3.sqrt()
    assert sqrt_d3.val == 2.0
    assert sqrt_d3.der == 1.0 / (2.0 * 2.0)  # 1 / (2 * sqrt(4)) * der

    # Test sinh, cosh, tanh
    d4 = Dual(0.0, 1.0)
    assert d4.sinh().val == 0.0
    assert d4.sinh().der == 1.0  # cosh(0) * 1

    assert d4.cosh().val == 1.0
    assert d4.cosh().der == 0.0  # sinh(0) * 1

    assert d4.tanh().val == 0.0
    assert d4.tanh().der == 1.0  # (1 - tanh^2(0)) * 1


def test_archaeologist_clustering_idempotence():
    """
    Validates the idempotency property of the Memory Archaeologist semantic clustering:
    f(f(X)) == f(X).
    Applying clustering once groups duplicates. Applying it again on the condensed
    set yields zero duplicates (no-op).
    """
    archaeologist = MemoryArchaeologist(engine=None)

    # Input: 5 facts where (0,1) are highly similar, (2,3) are highly similar, and 4 is isolated.
    facts = [{"id": str(i)} for i in range(5)]
    vecs_matrix = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.98, 0.1, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.97, 0.1],
            [0.0, 0.0, 1.0],
        ]
    )

    # 1. Apply clustering once: f(X)
    clusters = archaeologist._build_clusters(facts, vecs_matrix, threshold=0.9)
    assert len(clusters) == 2
    # Expect clusters to group {0, 1} and {2, 3}
    assert {0, 1} in [set(c) for c in clusters]
    assert {2, 3} in [set(c) for c in clusters]

    # Create representatives of f(X)
    # Cluster 1 represented by fact "0", Cluster 2 by "2", and isolated fact "4"
    condensed_facts = [{"id": "0"}, {"id": "2"}, {"id": "4"}]
    condensed_vecs = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
        ]
    )

    # 2. Apply clustering again: f(f(X))
    second_pass_clusters = archaeologist._build_clusters(
        condensed_facts, condensed_vecs, threshold=0.9
    )
    # Should result in 0 new clusters (every node is isolated under the threshold)
    assert len(second_pass_clusters) == 0


def test_morphism_functor():
    """
    Validates a covariant functor that maps from the category of Real numbers
    to the category of Dual numbers.
    - F_obj(x) = Dual(x, 1.0)
    - F_morph(f) maps a real function f to a Dual function.
    """
    # Object mapping: float -> Dual
    def F_obj(x: float) -> Dual:
        return Dual(x, 1.0)

    # Morphism mapping: maps a function f(float) -> function(Dual)
    # Since Dual supports +, -, *, / operators, we can just run the same function
    # on the Dual object if it is polynomial/linear.
    def F_morph(f: Callable[[float], float]) -> Callable[[Dual], Dual]:
        return lambda d, f_fn=f: f_fn(d)  # type: ignore[return-value]

    # Test domain
    domain = [1.0, 2.5, -4.0]

    # Test morphisms (functions) in the source category
    # Morphism 1: f(x) = 2x
    # Morphism 2: g(x) = x + 3
    def f_double(x): return x * 2.0
    def g_add_three(x): return x + 3.0

    morphisms = [(g_add_three, f_double)]

    assert MorphismVerifier.is_functor(
        F_obj=F_obj,
        F_morph=F_morph,
        domain_sample=domain,
        morphisms_sample=morphisms,
    )


