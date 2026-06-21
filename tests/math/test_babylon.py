from cortex.math.babylon import Babylon60Vector, manhattan_distance, causal_distance, hash_distance_rollup, EpistemicTrajectory
from cortex.embeddings.quantizer import AutocrystallizerQuantizationEdge
import pytest

def test_babylon_vector_strict_integer():
    # Deprecated (Phase 4) but still verified
    v1 = Babylon60Vector([1, 2, 3])
    assert len(v1) == 3
    
    with pytest.raises(ValueError, match="BABYLON-60 violation"):
        Babylon60Vector([1.5, 2, 3])

def test_manhattan_distance():
    # Deprecated (Phase 4)
    v1 = Babylon60Vector([100, 200, 300])
    v2 = Babylon60Vector([150, 200, 250])
    dist = manhattan_distance(v1, v2)
    assert dist == 100
    assert isinstance(dist, int)

def test_quantizer_edge():
    edge = AutocrystallizerQuantizationEdge(scaling_factor=1000)
    float_emb = [0.1234, -0.5678, 0.9999]
    int_vec = edge.quantize(float_emb)
    
    assert int_vec[0] == 123
    assert int_vec[1] == -568
    assert int_vec[2] == 1000
    
def test_causal_distance_uint16():
    # Test identical lineage (high overlap)
    dist_identical = causal_distance(ancestry_overlap=10, ledger_overlap=10, witness_overlap=5, temporal_overlap=0)
    # 10*60 + 5*30 + 10*10 = 600 + 150 + 100 = 850
    # max = 1000, dist = 1000 - 850 = 150
    assert dist_identical == 150
    assert isinstance(dist_identical, int)
    
    # Test completely divergent
    dist_divergent = causal_distance(ancestry_overlap=0, ledger_overlap=0, witness_overlap=0, temporal_overlap=0)
    assert dist_divergent == 1000

def test_merkle_distance_rollup():
    root_hash = "ROOT123"
    batch = [
        ("Q1", "T1", 100),
        ("Q2", "T2", 200)
    ]
    
    h1 = hash_distance_rollup(root_hash, batch)
    h2 = hash_distance_rollup(root_hash, batch)
    
    assert h1 == h2
    assert isinstance(h1, str)
    
    batch2 = [
        ("Q1", "T1", 100),
        ("Q2", "T2", 201) # Changed distance
    ]
    h3 = hash_distance_rollup(root_hash, batch2)
    assert h1 != h3
