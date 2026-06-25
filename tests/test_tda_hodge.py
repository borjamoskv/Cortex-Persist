# [C5-REAL] Exergy-Maximized
"""
Tests for HodgeZeroModeTransport in parameter-dependent TDA.

Reality Level: C5-REAL
"""

import pytest
import numpy as np
from legacy_research.utils.tda_hodge import HodgeZeroModeTransport


def test_hodge_boundary_operators():
    # Test a simple triangle simplicial complex
    # Vertices: 0, 1, 2
    # Edges: (0, 1), (1, 2), (0, 2)
    # Triangles: (0, 1, 2)
    transport = HodgeZeroModeTransport(num_vertices=3)
    simplices = {1: [(0, 1), (1, 2), (0, 2)], 2: [(0, 1, 2)]}

    d1, d2 = transport.compute_boundary_operators(simplices)

    # Vertices = 3, Edges = 3, Triangles = 1
    assert d1.shape == (3, 3)
    assert d2.shape == (3, 1)


def test_hodge_laplacian_zero_modes():
    # Simple circle (hollow triangle)
    # Vertices: 3, Edges: 3. No triangle (so d2 is empty).
    # Homology H1 should have dimension 1 (representing the circle cycle)
    transport = HodgeZeroModeTransport(num_vertices=3)
    simplices = {1: [(0, 1), (1, 2), (0, 2)], 2: []}

    d1, d2 = transport.compute_boundary_operators(simplices)
    L1 = transport.compute_hodge_laplacian(d1, d2)
    zero_modes = transport.extract_zero_modes(L1)

    # 1D homology dimension should be 1
    assert zero_modes.shape[1] == 1
    # Check that zero-mode is indeed in the kernel: L1 * v ≈ 0
    v = zero_modes[:, 0]
    np.testing.assert_allclose(L1 @ v, np.zeros_like(v), atol=1e-5)


def test_parallel_transport():
    transport = HodgeZeroModeTransport(num_vertices=3)
    basis_a = np.array([[1.0], [0.0], [0.0]])
    basis_b = np.array([[0.0], [1.0], [0.0]])

    U = transport.compute_parallel_transport(basis_a, basis_b)
    # Since bases are orthogonal, overlap is 0, so U should be eye or close
    assert U.shape == (1, 1)
