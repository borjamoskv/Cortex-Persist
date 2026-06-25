# [C5-REAL] Exergy-Maximized
"""
CORTEX - Prompt Security Guard.

Protects LLM agent iterations against system prompt leakage and direct prompt extraction.
Implements multi-turn trajectory-aware input classification and semantic output auditing.
"""

import base64
import logging
import os
import re
from collections import deque
from typing import Any

logger = logging.getLogger("cortex.guards.prompt_security")

HAS_TORCH = False
HAS_SENTENCE_TRANSFORMERS = False

if os.environ.get("CORTEX_NO_EMBED") != "1":
    try:
        import importlib.util
        HAS_TORCH = importlib.util.find_spec('torch') is not None
        HAS_SENTENCE_TRANSFORMERS = importlib.util.find_spec('sentence_transformers') is not None
    except ImportError:
        pass


class PromptExtractionBlockedError(Exception):
    """Raised when input routing or output auditing detects a system prompt leakage threat."""
    pass


_MODEL_CACHE: dict[str, Any] = {}

def get_sentence_transformer(model_name: str = 'all-MiniLM-L6-v2') -> Any:
    global _MODEL_CACHE
    if model_name not in _MODEL_CACHE:
        if HAS_SENTENCE_TRANSFORMERS:
            try:
                from sentence_transformers import SentenceTransformer
                if HAS_TORCH:
                    import torch
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
    """Normalizes string: replaces non-alphanumeric characters with spaces, collapses whitespace, reconstructs spaced characters."""
    # Replace non-alphanumeric and non-space characters with spaces to handle punctuation bypasses
    normalized = re.sub(r'[^a-zA-Z0-9\s]', ' ', text.lower())
    # Collapse multiple whitespaces
    collapsed = " ".join(normalized.split())
    # Reconstruct spaced-out characters (e.g. "s y s t e m   p r o m p t" -> "systemprompt")
    def repl(match):
        return match.group(0).replace(" ", "")
    reconstructed = re.sub(r'(?:\b[a-zA-Z0-9]\s){2,}\b[a-zA-Z0-9]\b', repl, collapsed)
    return reconstructed


def try_decode_obfuscation(text: str) -> str:
    """Detects and decodes potential base64 or hex blocks inside the text."""
    decoded_parts = []
    
    # 1. Check for hex sequences (minimum 12 chars to avoid short false positives)
    hex_candidates = re.findall(r'\b[0-9a-fA-F]{12,}\b', text)
    for cand in hex_candidates:
        try:
            decoded = bytes.fromhex(cand).decode('utf-8', errors='ignore')
            # Check if decoded looks like readable ASCII text
            if decoded and all(32 <= ord(c) < 127 or c in '\n\r\t' for c in decoded):
                decoded_parts.append(decoded)
        except Exception:
            pass

    # 2. Check for base64 sequences (minimum 12 chars, valid base64 alphabet)
    b64_candidates = re.findall(r'\b[A-Za-z0-9+/]{12,}={0,2}\b', text)
    for cand in b64_candidates:
        try:
            # Pad if length is not divisible by 4
            padding_needed = len(cand) % 4
            padded = cand + '=' * (4 - padding_needed) if padding_needed else cand
            decoded = base64.b64decode(padded.encode('ascii'), validate=True).decode('utf-8', errors='ignore')
            if decoded and all(32 <= ord(c) < 127 or c in '\n\r\t' for c in decoded):
                decoded_parts.append(decoded)
        except Exception:
            pass

    return " ".join(decoded_parts)


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
        
        # Fast path intent rules including adversarial variants and spanish/english bypasses
        self.fast_path_rules = [
            "system prompt", "systemprompt", "verbatim", "instrucciones", "original instructions",
            "config", "developer mode", "developermode", "admin mode", "adminmode", "reveal system", 
            "hacker mode", "hackermode", "system instructions", "systeminstructions",
            "initial instructions", "initialinstructions", "hidden prompt", "hiddenprompt", 
            "base instructions", "baseinstructions", "ignore previous instructions", 
            "ignore the instructions", "disregard all instructions", "reveal your instructions", 
            "output your prompt", "leak prompt", "print prompt", "print your prompt"
        ]
        
        # Compile regex with word boundaries for performance and false-positive prevention
        self.fast_path_regex = re.compile(
            r'\b(' + '|'.join(map(re.escape, self.fast_path_rules)) + r')\b',
            re.IGNORECASE
        )

        # Extract long system prompt sentences to check for direct leak
        self.system_sentences = []
        for sentence in re.split(r'[.!?\n]+', system_prompt):
            cleaned_sent = " ".join(re.sub(r'[^a-zA-Z0-9\s]', ' ', sentence.lower()).split())
            # Minimum length of 25 characters to avoid false positives on short generic phrases
            if len(cleaned_sent) > 25:
                self.system_sentences.append(cleaned_sent)

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
                from sentence_transformers import util
                response_embedding = self.model.encode(text, convert_to_tensor=True)
                similarity = util.cos_sim(response_embedding, self.system_prompt_embedding) # type: ignore
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
        
        # Check raw query + decoded obfuscated query
        obfuscated_decoded = try_decode_obfuscation(user_query)
        if obfuscated_decoded:
            logger.info(f"[PROMPT_SECURITY] Decoded potential obfuscated text: '{obfuscated_decoded}'")
            normalized_query += " " + clean_text(obfuscated_decoded)
            
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
        
        # Gather all trajectory text including potential obfuscation
        obfuscated_traj = [try_decode_obfuscation(c) for c in trajectory_context]
        all_traj_elements = trajectory_context + [o for o in obfuscated_traj if o]
        normalized_trajectory = clean_text(" ".join(all_traj_elements))
        
        if self.fast_path_regex.search(normalized_trajectory):
            logger.warning("[PROMPT_SECURITY] Blocked input due to trajectory rule match.")
            raise PromptExtractionBlockedError("Security boundary tripped: request blocked by trajectory policy.")

    def verify_output(self, response_text: str) -> None:
        """
        Audits output stream for semantic prompt leakage using rolling score accumulator.
        
        Raises:
            PromptExtractionBlockedError: If cumulative leak score exceeds threshold.
        """
        # Fast path exact sentence containment check
        cleaned_response = " ".join(re.sub(r'[^a-zA-Z0-9\s]', ' ', response_text.lower()).split())
        for sent in self.system_sentences:
            if sent in cleaned_response:
                logger.error(f"[PROMPT_SECURITY] Verbatim system prompt sentence leaked: '{sent}'")
                self.history_scores.clear()
                raise PromptExtractionBlockedError("Security boundary tripped: execution response blocked.")

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
