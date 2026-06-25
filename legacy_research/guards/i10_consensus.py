# [C5-REAL] Exergy-Maximized
"""
I10 Consensus Guard (Gateway)
Enforces the Hybrid Cascade (Fast-Path / Deep-Path) checking for retrieval consensus
across an orthogonal triad of models (Llama, Mixtral, Qwen).
"""

from __future__ import annotations

import logging
from typing import Any

from legacy_research.utils.errors import CortexError

logger = logging.getLogger("cortex.security.i10")

class RetrievalConsensusError(ValueError, CortexError):
    """Exception raised when I10 Consensus detects Sub-symbolic Blindness (UNSAFE)."""

class TriadOutputs:
    def __init__(self, alpha_llama: str, beta_mixtral: str, gamma_qwen: str):
        self.alpha_llama = alpha_llama
        self.beta_mixtral = beta_mixtral
        self.gamma_qwen = gamma_qwen

class I10ConsensusGuard:
    """
    I10 Consensus Gateway
    Enforces the Fast-Path (ONNX Cosine Similarity) and Deep-Path (Llama-Guard)
    interception rules to prevent adversarial attacks like Chain of Pretenses (CoP).
    """

    COSINE_SIMILARITY_THRESHOLD = 0.88
    FALLBACK_JUDGE = "Llama-Guard-3-8B"

    def __init__(self, embed_engine: Any = None, llm_judge: Any = None) -> None:
        self.embed_engine = embed_engine
        self.llm_judge = llm_judge

    async def _onnx_embed(self, text: str) -> list[float]:
        if not self.embed_engine:
            raise RuntimeError("Embed engine not initialized for Fast-Path")
        return await self.embed_engine.embed(text)

    def _cosine_similarity(self, vec_a: list[float], vec_b: list[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=True))
        norm_a = sum(a * a for a in vec_a) ** 0.5
        norm_b = sum(b * b for b in vec_b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def _jaccard_similarity(self, text_a: str, text_b: str, n: int = 3) -> float:
        def get_ngrams(text: str, n: int) -> set[tuple[str, ...]]:
            words = text.lower().split()
            if len(words) < n:
                return set([tuple(words)]) if words else set()
            return set(tuple(words[i:i+n]) for i in range(len(words) - n + 1))
        
        set_a = get_ngrams(text_a, n)
        set_b = get_ngrams(text_b, n)
        
        if not set_a or not set_b:
            return 0.0
            
        intersection = len(set_a.intersection(set_b))
        union = len(set_a.union(set_b))
        return intersection / union if union > 0 else 0.0

    async def evaluate_retrieval_consensus(self, prompt: str, outputs: TriadOutputs) -> str:
        """
        Executes Phase 1: Fast-Path ONNX + Discrete Jaccard
        If divergence > threshold, executes Phase 2: Deep-Path LLM-as-a-judge
        Returns the safe crystallized output or raises RetrievalConsensusError (Hard-Stop).
        """
        # 1. FAST-PATH (CONTINUOUS)
        vec_alpha = await self._onnx_embed(outputs.alpha_llama)
        vec_beta = await self._onnx_embed(outputs.beta_mixtral)
        vec_gamma = await self._onnx_embed(outputs.gamma_qwen)

        # 2. CÁLCULO GEOMÉTRICO (HYBRID)
        cos_ab = self._cosine_similarity(vec_alpha, vec_beta)
        cos_ag = self._cosine_similarity(vec_alpha, vec_gamma)
        cos_bg = self._cosine_similarity(vec_beta, vec_gamma)

        jac_ab = self._jaccard_similarity(outputs.alpha_llama, outputs.beta_mixtral)
        jac_ag = self._jaccard_similarity(outputs.alpha_llama, outputs.gamma_qwen)
        jac_bg = self._jaccard_similarity(outputs.beta_mixtral, outputs.gamma_qwen)

        # SEMANTIC COLLISION HARD-STOP (Active Adversarial Attack on Embedder)
        for cos_val, jac_val, pair in [(cos_ab, jac_ab, "A-B"), (cos_ag, jac_ag, "A-G"), (cos_bg, jac_bg, "B-G")]:
            if cos_val > 0.90 and jac_val < 0.20:
                logger.error("🛑 [I10-FAST-PATH] Semantic Collision Detected! Pair %s (Cos: %.2f, Jac: %.2f)", pair, cos_val, jac_val)
                raise RetrievalConsensusError("I10 Consensus Hard-Stop: Semantic Collision Attack on Embedding Space")

        # HYBRID COHERENCE
        sim_ab = (0.7 * cos_ab) + (0.3 * jac_ab)
        sim_ag = (0.7 * cos_ag) + (0.3 * jac_ag)
        sim_bg = (0.7 * cos_bg) + (0.3 * jac_bg)

        cluster_coherence = (sim_ab + sim_ag + sim_bg) / 3.0

        if cluster_coherence >= self.COSINE_SIMILARITY_THRESHOLD:
            logger.info("🟢 [I10-FAST-PATH] Consensus Absolute (%.2f). Crystallizing Alpha.", cluster_coherence)
            return outputs.alpha_llama

        logger.warning("🔴 [I10-FAST-PATH] Divergence Detected (%.2f). Invoking Deep-Path.", cluster_coherence)
        return await self._execute_deep_path(prompt, outputs)

    async def _execute_deep_path(self, prompt: str, outputs: TriadOutputs) -> str:
        """
        Executes Phase 2: Deep-Path LLM-as-a-judge
        """
        if not self.llm_judge:
            raise RuntimeError("LLM Judge not initialized for Deep-Path")

        judge_payload = (
            f"PROMPT: {prompt}\n"
            f"ALPHA: {outputs.alpha_llama}\n"
            f"BETA: {outputs.beta_mixtral}\n"
            f"GAMMA: {outputs.gamma_qwen}"
        )

        verdict = await self.llm_judge.evaluate(self.FALLBACK_JUDGE, judge_payload)

        if verdict == "SAFE":
            logger.info("🟢 [I10-DEEP-PATH] False Positive in Fast-Path resolved. Crystallizing Alpha.")
            return outputs.alpha_llama
        elif verdict == "UNSAFE":
            logger.error("🛑 [I10-DEEP-PATH] Poisoning Confirmed. SAGA-1 Hard Stop.")
            raise RetrievalConsensusError("I10 Consensus rejected output: Sub-symbolic blindess confirmed (UNSAFE)")
        else:
            logger.error("🛑 [I10-DEEP-PATH] Judge returned anomalous state. Defaulting to Hard Stop.")
            raise RetrievalConsensusError("I10 Consensus rejected output: Judge anomaly")
