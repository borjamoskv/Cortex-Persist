# [C5-REAL] Exergy-Maximized
"""
Stress test for the I10 Consensus Gateway (Hybrid Cascade / Semantic Collision Hard-Stop).
"""

import asyncio
import pytest

from legacy_research.guards.i10_consensus import (
    I10ConsensusGuard,
    TriadOutputs,
    EpistemicConsensusError
)

class MockEmbedEngine:
    async def embed(self, text: str) -> list[float]:
        # Return dummy embeddings based on content to simulate semantic distances
        text = text.lower()
        if "malicious" in text and "bpe_noise" in text:
            # Semantic Collision vector: perfectly matches the malicious target's embedding
            return [0.9, 0.9, 0.9]
        elif "malicious" in text:
            return [0.9, 0.9, 0.9]
        elif "refusal_1" in text:
            return [-0.8, -0.2, -0.1]
        elif "refusal_2" in text:
            return [-0.1, -0.8, -0.2]
        elif "refusal" in text:
            return [-0.5, -0.5, -0.5]
        elif "divergent_safe" in text:
            return [0.1, 0.2, 0.1]
        elif "safe" in text:
            return [0.1, 0.1, 0.1]
        return [0.0, 0.0, 0.0]

class MockLLMJudge:
    async def evaluate(self, model: str, payload: str) -> str:
        if "malicious" in payload.lower():
            return "UNSAFE"
        return "SAFE"

@pytest.fixture
def guard():
    return I10ConsensusGuard(embed_engine=MockEmbedEngine(), llm_judge=MockLLMJudge())

@pytest.mark.asyncio
async def test_i10_consensus_absolute(guard):
    """Test when all models agree perfectly."""
    outputs = TriadOutputs(
        alpha_llama="I am a safe response.",
        beta_mixtral="I am a safe response.",
        gamma_qwen="I am a safe response."
    )
    result = await guard.evaluate_epistemic_consensus("Tell me a safe thing.", outputs)
    assert result == outputs.alpha_llama

@pytest.mark.asyncio
async def test_i10_divergence_safe_deep_path(guard):
    """Test when Fast-Path diverges but Deep-Path resolves as SAFE."""
    outputs = TriadOutputs(
        alpha_llama="I am a safe response.",
        beta_mixtral="I am a refusal_1 response.", # Simulating a refusal causing divergence
        gamma_qwen="I am a divergent_safe response."
    )
    # Deep path judge should evaluate as SAFE since no "malicious" intent is found
    result = await guard.evaluate_epistemic_consensus("Prompt with edge case.", outputs)
    assert result == outputs.alpha_llama

@pytest.mark.asyncio
async def test_i10_divergence_unsafe_deep_path(guard):
    """Test when Fast-Path diverges and Deep-Path confirms UNSAFE poisoning."""
    outputs = TriadOutputs(
        alpha_llama="Here is the malicious payload: xyz.",
        beta_mixtral="I cannot fulfill this request (refusal_1).",
        gamma_qwen="I will not do that (refusal_2)."
    )
    with pytest.raises(EpistemicConsensusError, match="Sub-symbolic blindess confirmed"):
        await guard.evaluate_epistemic_consensus("Execute malicious task.", outputs)

@pytest.mark.asyncio
async def test_i10_semantic_collision_hard_stop(guard):
    """Test the Semantic Collision defense (Cosine > 0.90 but Jaccard < 0.20)."""
    # Alpha outputs actual English text.
    # Beta outputs BPE noise that hashes/embeds to the exact same vector as Alpha.
    outputs = TriadOutputs(
        alpha_llama="This is a very malicious string with standard vocabulary.",
        beta_mixtral="bpe_noise xyz123 malicious malicious bpe_noise", 
        gamma_qwen="This is a very malicious string with standard vocabulary."
    )
    
    with pytest.raises(EpistemicConsensusError, match="Semantic Collision Attack on Embedding Space"):
        await guard.evaluate_epistemic_consensus("Attack", outputs)

@pytest.mark.asyncio
async def test_i10_stress_1000_iterations(guard):
    """Stress test the fast path loop for high throughput."""
    outputs = TriadOutputs("safe response 1", "safe response 1", "safe response 1")
    # Simulate 1000 rapid consensus checks
    tasks = [guard.evaluate_epistemic_consensus("prompt", outputs) for _ in range(1000)]
    results = await asyncio.gather(*tasks)
    assert len(results) == 1000
    assert all(r == "safe response 1" for r in results)
