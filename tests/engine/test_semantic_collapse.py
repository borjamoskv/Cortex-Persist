# [C5-REAL] Exergy-Maximized
import pytest
from legacy_research.engine.semantic_collapse import (
    kolmogorov_approx,
    compute_ncd,
    collapse_eligible,
    semantic_collapse,
    MAX_KINETIC_MULTIPLIER
)

def test_kolmogorov_approximation():
    content_redundant = "A" * 1000
    content_random = " ".join([str(i) for i in range(1000)])
    
    z_red = kolmogorov_approx(content_redundant)
    z_rnd = kolmogorov_approx(content_random)
    
    # Redundant text must compress significantly better than high entropy text
    assert z_red < z_rnd

def test_ncd_identical_strings():
    text = "CORTEX-Persist es un motor causal estricto."
    ncd = compute_ncd(text, text)
    # They should be extremely close to 0 (redundant)
    assert ncd < 0.1

def test_ncd_orthogonal_strings():
    text_a = "El veloz murciélago hindú comía feliz cardillo y kiwi."
    text_b = "1234567890 0987654321 1122334455 9988776655"
    ncd = compute_ncd(text_a, text_b)
    # They should be orthogonal, approaching 1
    assert ncd > 0.8

def test_collapse_eligibility():
    text = "The quick brown fox jumps over the lazy dog. " * 10
    # Identical text, similar mass -> eligible
    assert collapse_eligible(text, text, mass_a=1.0, mass_b=1.05, threshold=0.15, mass_tolerance=0.1)
    
    # Identical text, disparate mass -> not eligible
    assert not collapse_eligible(text, text, mass_a=1.0, mass_b=1.5, threshold=0.1, mass_tolerance=0.1)
    
    # Orthogonal text, similar mass -> not eligible
    assert not collapse_eligible("AAA", "BBB", mass_a=1.0, mass_b=1.0, threshold=0.1, mass_tolerance=0.1)

def test_semantic_collapse_properties():
    text_a = "Content A"
    text_b = "Content B"
    
    # A has higher mass, should win
    res = semantic_collapse("idA", text_a, 1.8, "idB", text_b, 1.2)
    
    assert res["winner"] == "idA"
    assert res["content"] == text_a
    assert "idA" in res["collapsed_from"]
    assert "idB" in res["collapsed_from"]
    
    # Mass inherits strongest but does not exceed MAX
    assert res["kinetic_mass"] == 1.8
    
    # If mass exceeds MAX, it gets capped
    res_capped = semantic_collapse("idA", text_a, 3.5, "idB", text_b, 1.2)
    assert res_capped["kinetic_mass"] == MAX_KINETIC_MULTIPLIER

def test_post_collapse_entropy_invariant():
    # H(merged) >= min(H(n_a), H(n_b))
    # Since we do Survival of the Fittest, H(merged) == H(winner), which is >= min(H(A), H(B))
    text_a = "Redundant" * 10
    text_b = "High Entropy Value 1 2 3"
    
    res = semantic_collapse("idA", text_a, 1.0, "idB", text_b, 2.0)
    
    h_merged = res["entropy_approx"]
    h_a = kolmogorov_approx(text_a)
    h_b = kolmogorov_approx(text_b)
    
    assert h_merged >= min(h_a, h_b)
