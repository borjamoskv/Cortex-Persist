"""Tests for CORTEX v7 HDC Codec (Text to Hypervector)."""

from cortex.memory.hdc.algebra import cosine_similarity, unbind
from cortex.memory.hdc.codec import HDCEncoder
from cortex.memory.hdc.item_memory import ItemMemory


def test_codec_tokenize():
    """Test standard tokenizer extraction."""
    mem = ItemMemory(dim=1000)
    enc = HDCEncoder(mem)
    
    tokens = enc.tokenize("Houston, we have a #problem!")
    assert tokens == ["houston", "we", "have", "a", "problem"]


def test_codec_encode_text_identity():
    """Test text encoding stability and similarity."""
    mem = ItemMemory(dim=2000)
    enc = HDCEncoder(mem)
    
    # Same text should produce identical HV
    t1 = "A Quick Brown Fox."
    hv1 = enc.encode_text(t1)
    hv2 = enc.encode_text(t1.lower()) # Codec tokenizes to lower
    
    assert cosine_similarity(hv1, hv2) == 1.0


def test_codec_encode_text_similarity():
    """Test that overlapping text has similarity, but differing text is orthogonal."""
    mem = ItemMemory(dim=2000)
    enc = HDCEncoder(mem)
    
    hv1 = enc.encode_text("The quick brown fox jumps over the lazy dog")
    hv2 = enc.encode_text("The fast brown fox jumps over the sleeping dog")
    hv3 = enc.encode_text("Nuclear physics is a complex subject")
    
    sim_12 = cosine_similarity(hv1, hv2)
    sim_13 = cosine_similarity(hv1, hv3)
    
    # 1 and 2 share many words in same position, should be correlated
    assert sim_12 > 0.4
    
    # 1 and 3 share nothing (except maybe 'the'), should be ~0
    assert abs(sim_13) < 0.2


def test_codec_encode_fact_binding():
    """Test that a fact correctly binds project and role, allowing decomposition."""
    mem = ItemMemory(dim=10_000)
    enc = HDCEncoder(mem)
    
    content = "Update the authentication mechanism to use OAuth2."
    
    # Basic encoding
    hv_content = enc.encode_text(content)
    
    # Full fact encoding
    hv_fact = enc.encode_fact(
        content=content,
        fact_type="decision",
        project_id="cortex-v7"
    )
    
    # They shouldn't be identical anymore
    assert cosine_similarity(hv_content, hv_fact) < 0.1
    
    # Decomposition (ULTRATHINK traceability):
    
    # 1. Unbind the project
    proj_hv = mem.project_vector("cortex-v7")
    hv_sans_project = unbind(hv_fact, proj_hv)
    
    # 2. Unbind the definition of 'decision'
    role_hv = mem.role_vector("decision")
    recovered_content = unbind(hv_sans_project, role_hv)
    
    # The recovered content should be highly correlated with original content
    # (Since binding is element-wise multiplication on ±1, it perfectly recovers)
    assert cosine_similarity(hv_content, recovered_content) == 1.0
