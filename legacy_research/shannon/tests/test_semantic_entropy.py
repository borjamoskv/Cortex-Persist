import pytest

from legacy_research.shannon.semantic_entropy import SemanticEntropyScorer


@pytest.fixture
def scorer():
    return SemanticEntropyScorer()

def test_entropy_calculation(scorer):
    # Same text repeated should have same entropy as single instance because proportions are same
    text_1 = "hello world"
    text_2 = "hello world hello world"
    
    h1 = scorer.calculate_entropy(text_1)
    h2 = scorer.calculate_entropy(text_2)
    assert abs(h1 - h2) < 0.001

def test_kolmogorov_approx(scorer):
    # Highly repetitive text should compress well
    repetitive = "a " * 1000
    random_text = "abc def ghi jkl mno pqr stu vwx yz" * 30
    
    k_rep = scorer.kolmogorov_approx(repetitive)
    k_rand = scorer.kolmogorov_approx(random_text)
    
    assert k_rep < k_rand

def test_kl_divergence_orthogonal(scorer):
    # Orthogonal texts should have high divergence
    text_a = "The quick brown fox jumps over the lazy dog"
    text_b = "def calculate_entropy(self, text: str) -> float: return 0.0"
    
    d_kl = scorer.kl_divergence(text_a, text_b)
    assert d_kl > scorer.KL_DIVERGENCE_THRESHOLD

def test_kl_divergence_similar(scorer):
    # Similar texts should have low divergence. Tokenizer ignores punctuation and case.
    text_a = "The system measures thermodynamic entropy."
    text_b = "THE SYSTEM measures thermodynamic, entropy!!!"
    
    d_kl = scorer.kl_divergence(text_a, text_b)
    assert d_kl < scorer.KL_DIVERGENCE_THRESHOLD

def test_collapse_i4_i5_i6(scorer):
    # Test identical collapse
    text_a = "This is a redundant semantic node."
    text_b = "This is a redundant semantic node."
    mass_a = 1.0
    mass_b = 1.0
    
    verdict = scorer.evaluate_collapse(text_a, text_b, mass_a, mass_b)
    assert verdict.approved is True
    assert verdict.post_collapse_mass == 1.5 # 1.0 + 0.5
    
    # Test I6 (Orthogonal)
    text_c = "Complete nonsense quantum cryptography hashes"
    verdict_orthogonal = scorer.evaluate_collapse(text_a, text_c, mass_a, mass_b)
    assert verdict_orthogonal.approved is False
    assert "I6 Violation" in verdict_orthogonal.reason
    
    # Test I5 (Mass Ceiling). Keep mass difference < 0.1 to pass eligibility.
    verdict_heavy = scorer.evaluate_collapse(text_a, text_b, 1.8, 1.75)
    assert verdict_heavy.approved is False
    assert "I5 Violation" in verdict_heavy.reason
