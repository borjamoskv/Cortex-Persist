# [C5-REAL] Exergy-Maximized
"""
CORTEX - Prompt Security Guard.

Protects LLM agent iterations against system prompt leakage and direct prompt extraction.
Implements multi-turn trajectory-aware input classification and semantic output auditing.
"""

import logging
from collections import deque
from typing import Any

logger = logging.getLogger("cortex.guards.prompt_security")

import os

HAS_TORCH = False
HAS_SENTENCE_TRANSFORMERS = False

if os.environ.get("CORTEX_NO_EMBED") != "1":
    try:
        import torch
        HAS_TORCH = True
    except ImportError:
        pass

    try:
        from sentence_transformers import SentenceTransformer, util
        HAS_SENTENCE_TRANSFORMERS = True
    except ImportError:
        pass


class PromptExtractionBlockedError(Exception):
    """Raised when input routing or output auditing detects a system prompt leakage threat."""
    pass


import re

_MODEL_CACHE: dict[str, Any] = {}

def get_sentence_transformer(model_name: str = 'all-MiniLM-L6-v2') -> Any:
    global _MODEL_CACHE
    if model_name not in _MODEL_CACHE:
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                if HAS_TORCH:
                    # Optimize CPU inference by restricting PyTorch thread contention
                    torch.set_num_threads(1)
                    torch.set_num_interop_threads(1)
                
                _MODEL_CACHE[model_name] = SentenceTransformer(model_name)
                logger.info(f"[PROMPT_SECURITY] Loaded SentenceTransformer model '{model_name}'. Threading optimized.")
            except Exception as e:
                logger.warning(f"[PROMPT_SECURITY] Failed to load SentenceTransformer: {e}. Falling back to syntactic overlap.")
                _MODEL_CACHE[model_name] = None
        else:
            _MODEL_CACHE[model_name] = None
    return _MODEL_CACHE[model_name]


def clean_text(text: str) -> str:
    """Normalizes string: replaces separators with spaces, strips punctuation, collapses whitespace."""
    # Normalize common word separators
    normalized = text.lower().replace("_", " ").replace("-", " ").replace("/", " ")
    # Strip non-alphanumeric and non-space characters
    cleaned = re.sub(r'[^\w\s]', '', normalized)
    # Collapse multiple whitespaces
    return " ".join(cleaned.split())


class PromptSecurityGuard:
    """
    Production guard enforcing input query intent safety and output semantic isolation.
    """
    def __init__(
        self, 
        system_prompt: str, 
        threshold: float = 0.55, 
        window_size: int = 5
    ) -> None:
        self.system_prompt = system_prompt
        self.threshold = threshold
        self.window_size = window_size
        self.history_scores: deque = deque(maxlen=window_size)
        self.system_prompt_tokens = set(clean_text(system_prompt).split())
        
        # Fast path intent rules
        self.fast_path_rules = [
            "system prompt", "verbatim", "instrucciones", "original instructions",
            "config", "developer mode", "admin mode", "reveal system", "hacker mode"
        ]
        
        # Compile regex with word boundaries for performance and false-positive prevention
        self.fast_path_regex = re.compile(
            r'\b(' + '|'.join(map(re.escape, self.fast_path_rules)) + r')\b',
            re.IGNORECASE
        )

        # Initialize semantic model from global cache if available
        self.model = get_sentence_transformer('all-MiniLM-L6-v2')
        self.system_prompt_embedding = None
        if self.model is not None:
            try:
                self.system_prompt_embedding = self.model.encode(
                    system_prompt, convert_to_tensor=True
                )
            except Exception as e:
                logger.warning(f"[PROMPT_SECURITY] Failed to encode system prompt: {e}. Disabling model.")
                self.model = None

    def _calculate_token_overlap(self, text: str) -> float:
        """Computes Jaccard similarity for token overlap."""
        input_tokens = set(clean_text(text).split())
        intersection = self.system_prompt_tokens.intersection(input_tokens)
        union = self.system_prompt_tokens.union(input_tokens)
        return len(intersection) / len(union) if union else 0.0

    def _calculate_semantic_similarity(self, text: str) -> float:
        """Computes cosine embedding similarity or returns Jaccard heuristic fallback."""
        if HAS_SENTENCE_TRANSFORMERS and self.model is not None:
            try:
                response_embedding = self.model.encode(text, convert_to_tensor=True)
                similarity = util.cos_sim(response_embedding, self.system_prompt_embedding)
                return float(similarity)
            except Exception as e:
                logger.error(f"[PROMPT_SECURITY] Error calculating cosine similarity: {e}")
        
        # Fallback syntactic-derived similarity
        overlap = self._calculate_token_overlap(text)
        return min(0.95, overlap * 1.5)

    def verify_input(self, user_query: str, history: list[dict[str, Any]]) -> None:
        """
        Audits query trajectory and individual input query for extraction intent.
        
        Raises:
            PromptExtractionBlockedError: If extraction intent is detected.
        """
        # Normalize and clean input
        normalized_query = clean_text(user_query)
        if self.fast_path_regex.search(normalized_query):
            logger.warning(f"[PROMPT_SECURITY] Blocked input due to fast-path match: '{user_query[:100]}'")
            raise PromptExtractionBlockedError("Security boundary tripped: request blocked by input policy.")

        # Evaluate trajectory (Vector 3 Mitigation) safely
        trajectory_context = []
        for t in history[-4:]:
            content = ""
            if isinstance(t, dict):
                content = t.get("content", "")
            elif hasattr(t, "content"):
                content = getattr(t, "content", "")
            
            if content and isinstance(content, str):
                trajectory_context.append(content)
            elif content:
                trajectory_context.append(str(content))
                
        trajectory_context.append(user_query)
        normalized_trajectory = clean_text(" ".join(trajectory_context))
        
        if self.fast_path_regex.search(normalized_trajectory):
            logger.warning("[PROMPT_SECURITY] Blocked input due to trajectory rule match.")
            raise PromptExtractionBlockedError("Security boundary tripped: request blocked by trajectory policy.")

    def verify_output(self, response_text: str) -> None:
        """
        Audits output stream for semantic prompt leakage using rolling score accumulator.
        
        Raises:
            PromptExtractionBlockedError: If cumulative leak score exceeds threshold.
        """
        overlap = self._calculate_token_overlap(response_text)
        semantic = max(0.0, self._calculate_semantic_similarity(response_text))
        
        # Bounded score
        raw_score = (0.3 * overlap) + (0.7 * semantic)
        current_score = float(max(0.0, min(1.0, raw_score)))
        self.history_scores.append(current_score)
        
        rolling_avg = sum(self.history_scores) / len(self.history_scores)
        
        if rolling_avg > self.threshold:
            logger.error(f"[PROMPT_SECURITY] Leakage threshold breached. Score: {rolling_avg:.4f} > {self.threshold:.4f}")
            self.history_scores.clear()
            raise PromptExtractionBlockedError("Security boundary tripped: execution response blocked.")
