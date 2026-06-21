import math
import pytest
try:
    from hypothesis import given, settings
    import hypothesis.strategies as st
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

import cortex_rs
calculate_entropy_b60 = cortex_rs.calculate_entropy_b60

SCALE = 216_000

def _compute_entropy_py(data: bytes) -> int:
    counts = [0] * 256
    for b in data:
        counts[b] += 1
    
    entropy_py = 0.0
    for c in counts:
        if c > 0:
            p = c / len(data)
            entropy_py -= p * math.log2(p)
            
    # Scale to Babylon60 format
    return int(round(entropy_py * SCALE))

def test_rust_ffi_entropy_b60_contract_basic():
    """
    Test Rust FFI contract comparing Python and Rust BABYLON-60 outputs on standard input.
    """
    data = b"cortex-persist physical enforcement"
    expected_b60_value = _compute_entropy_py(data)
    b60_rust = calculate_entropy_b60(data)
    assert b60_rust.get_value() == expected_b60_value

if HAS_HYPOTHESIS:
    @given(data=st.binary(min_size=1, max_size=10000))
    @settings(max_examples=100)
    def test_rust_ffi_entropy_b60_property(data):
        """
        Property-based testing of Rust FFI contract comparing Python and Rust BABYLON-60 outputs.
        Ensures mathematical equivalence across a wide spectrum of random byte distributions.
        """
        expected_b60_value = _compute_entropy_py(data)
        b60_rust = calculate_entropy_b60(data)
        
        assert abs(b60_rust.get_value() - expected_b60_value) <= 1
else:
    @pytest.mark.skip(reason="Hypothesis not installed")
    def test_rust_ffi_entropy_b60_property():
        pass


def test_babylon60_arithmetic():
    a = cortex_rs.Babylon60(SCALE) # 1.0
    b = cortex_rs.Babylon60(int(SCALE / 2)) # 0.5
    
    c = a + b
    assert c.get_value() == SCALE + int(SCALE / 2)
    assert float(c) == 1.5
    
    d = a - b
    assert d.get_value() == int(SCALE / 2)
    assert float(d) == 0.5
    
    e = a * b
    assert e.get_value() == int(SCALE / 2)
    
    f = a / b
    assert f.get_value() == 2 * SCALE
    assert float(f) == 2.0
    
def test_babylon60_comparisons():
    a = cortex_rs.Babylon60(SCALE) # 1.0
    b = cortex_rs.Babylon60(SCALE * 2) # 2.0
    c = cortex_rs.Babylon60(SCALE) # 1.0
    
    assert a < b
    assert a <= b
    assert b > a
    assert b >= a
    assert a == c
    assert a != b

def test_babylon60_hash():
    a = cortex_rs.Babylon60(SCALE)
    b = cortex_rs.Babylon60(SCALE)
    c = cortex_rs.Babylon60(SCALE * 2)
    
    s = {a, c}
    assert b in s
    assert c in s

def test_babylon60_from_int():
    a = cortex_rs.Babylon60.from_int(5)
    assert a.get_value() == 5 * SCALE
    assert int(a) == 5

