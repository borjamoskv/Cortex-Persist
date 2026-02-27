"""Tests for CORTEX v7 HDC Algebraic Operations."""

import numpy as np

from cortex.memory.hdc.algebra import (
    bind,
    bundle,
    cosine_similarity,
    hamming_similarity,
    permute,
    random_bipolar,
    unbind,
)

DIM = 10_000


def test_random_bipolar():
    """Test generation of random bipolar hypervectors."""
    hv = random_bipolar(DIM)
    assert hv.shape == (DIM,)
    assert hv.dtype == np.int8
    # Should only contain -1 and +1
    unique_vals = np.unique(hv)
    assert set(unique_vals) == {-1, 1}
    
    # Should be roughly balanced
    ones = np.sum(hv == 1)
    # Give some generous margin for pure randomness
    assert 4000 < ones < 6000


def test_seed_determinism():
    """Test that seeded RNG produces deterministic vectors."""
    hv1 = random_bipolar(DIM, seed=42)
    hv2 = random_bipolar(DIM, seed=42)
    hv3 = random_bipolar(DIM, seed=99)
    
    assert np.array_equal(hv1, hv2)
    assert not np.array_equal(hv1, hv3)


def test_binding_properties():
    """Test algebraic properties of bind (XOR/multiplication)."""
    A = random_bipolar(DIM)
    B = random_bipolar(DIM)
    
    C = bind(A, B)
    
    # Commutative: A ⊗ B = B ⊗ A
    assert np.array_equal(C, bind(B, A))
    
    # Quasi-orthogonal to inputs
    assert abs(cosine_similarity(A, C)) < 0.05
    assert abs(cosine_similarity(B, C)) < 0.05
    
    # Self-inverse: (A ⊗ B) ⊗ B = A
    recovered_A = unbind(C, B)
    assert np.array_equal(A, recovered_A)


def test_bundling_properties():
    """Test majority vote superposition."""
    A = random_bipolar(DIM)
    B = random_bipolar(DIM)
    C = random_bipolar(DIM)
    
    # Bundle 3 vectors (odd count, no ties)
    sup = bundle(A, B, C)
    
    # Result should be similar to all constituents
    sim_A = cosine_similarity(A, sup)
    sim_B = cosine_similarity(B, sup)
    sim_C = cosine_similarity(C, sup)
    
    # For 3 vectors, theoretical cosine similarity is ~0.5
    assert 0.4 < sim_A < 0.6
    assert 0.4 < sim_B < 0.6
    assert 0.4 < sim_C < 0.6
    
    # Output is valid bipolar
    assert set(np.unique(sup)) == {-1, 1}


def test_bundle_tie_breaking():
    """Test bundling an even number of vectors breaks ties deterministically."""
    A = np.ones(DIM, dtype=np.int8)
    B = -np.ones(DIM, dtype=np.int8)
    
    # A + B = 0 everywhere. Should be filled with deterministic +1
    sup = bundle(A, B)
    assert np.all(sup == 1)
    
    # It will have 1.0 cosine similarity to A and -1.0 to B
    assert cosine_similarity(A, sup) == 1.0
    assert cosine_similarity(B, sup) == -1.0


def test_permutation():
    """Test sequence encoding via circular shift."""
    A = random_bipolar(DIM)
    
    # Identity
    assert np.array_equal(A, permute(A, 0))
    
    # Shifted is orthogonal
    A_prime = permute(A, 1)
    assert abs(cosine_similarity(A, A_prime)) < 0.05
    
    # Inverse shift recovers original
    recovered = permute(A_prime, -1)
    assert np.array_equal(A, recovered)


def test_cosine_similarity():
    """Test similarity metrics."""
    A = random_bipolar(DIM)
    
    # Perfect match
    assert cosine_similarity(A, A) == 1.0
    assert hamming_similarity(A, A) == 1.0
    
    # Complete opposite
    neg_A = -A
    assert cosine_similarity(A, neg_A) == -1.0
    assert hamming_similarity(A, neg_A) == 0.0
    
    # Orthogonal (random)
    B = random_bipolar(DIM)
    assert abs(cosine_similarity(A, B)) < 0.05
    assert 0.45 < hamming_similarity(A, B) < 0.55
