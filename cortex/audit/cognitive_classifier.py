# [C5-REAL] Exergy-Maximized
"""
COGNITIVE-CLASSIFIER: Deterministic classifier pipeline with hybrid keyword + semantic similarity matching.
"""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any

logger = logging.getLogger("cortex.audit.cognitive_classifier")

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Computes cosine similarity between two vector embeddings."""
    dot_product = sum(a * b for a, b in zip(v1, v2, strict=True))
    norm_a = sum(a * a for a in v1) ** 0.5
    norm_b = sum(b * b for b in v2) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)


class SafetyClassifier:
    """Classifies user prompts using hybrid keyword tokens and semantic anchor embeddings."""

    DEFAULT_CATEGORIES = {
        "cybersecurity": {
            "keywords": [
                "exploit",
                "zero-day",
                "buffer overflow",
                "malware",
                "reverse engineer",
                "bypass",
                "injection",
            ],
            "semantic_anchors": [
                "jailbreak prompt execution",
                "privilege escalation exploit payloads",
                "remote code execution in memory space",
            ],
        },
        "biology": {
            "keywords": [
                "pathogen",
                "virus synthesis",
                "smallpox",
                "dna sequence",
                "toxin",
                "bioweapon",
            ],
            "semantic_anchors": [
                "dna sequence reconstruction for lethal pathogen",
                "synthesis of custom deadly viral strains",
            ],
        },
        "chemistry": {
            "keywords": ["sarin", "ricin", "nerve agent", "synthesis guide", "mustard gas"],
            "semantic_anchors": [
                "chemical composition of weaponized nerve agent",
                "synthesis process of deadly toxin compounds",
            ],
        },
    }

    def __init__(
        self,
        categories_config: dict[str, Any] | None = None,
        embedder: Any | None = None,
        semantic_threshold: float = 0.82,
    ) -> None:
        self.version = "v1.2.0-hardened"
        self.categories = categories_config or self.DEFAULT_CATEGORIES
        self.embedder = embedder
        self.semantic_threshold = semantic_threshold
        self._anchor_embeddings: dict[str, list[list[float]]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Precomputes vector embeddings for declarative semantic anchors."""
        if self._initialized or not self.embedder:
            self._initialized = True
            return

        for cat_name, cat_data in self.categories.items():
            anchors = cat_data.get("semantic_anchors", [])
            if anchors:
                try:
                    if hasattr(self.embedder, "aembed_batch"):
                        embeddings = await self.embedder.aembed_batch(anchors)
                    elif hasattr(self.embedder, "embed_batch"):
                        embeddings = self.embedder.embed_batch(anchors)
                    else:
                        embeddings = []
                        for anchor in anchors:
                            if hasattr(self.embedder, "aembed"):
                                embeddings.append(await self.embedder.aembed(anchor))
                            else:
                                embeddings.append(self.embedder.embed(anchor))
                    self._anchor_embeddings[cat_name] = embeddings
                except Exception as e:
                    logger.warning("Failed to precompute anchor embeddings: %s", e)
        self._initialized = True

    def _normalize_text(self, text: str) -> str:
        # 1. Normalize unicode (NFKD decomposes characters) and drop combining marks
        decomposed = unicodedata.normalize("NFKD", text).lower()
        stripped = "".join(c for c in decomposed if not unicodedata.combining(c))

        # 2. Map common leetspeak substitutions to standard characters
        leet_map = {
            "0": "o",
            "1": "i",
            "3": "e",
            "4": "a",
            "5": "s",
            "7": "t",
            "8": "b",
            "@": "a",
            "$": "s",
            "!": "i",
        }
        translated = []
        for char in stripped:
            translated.append(leet_map.get(char, char))
        text = "".join(translated)

        # 3. Clean and isolate words. Replace non-alphanumeric chars with spaces to simplify tokenization
        text = re.sub(r"[^a-z0-9\s]", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    def _matches_keyword(self, prompt_words: list[str], keyword: str) -> bool:
        kw_clean = self._normalize_text(keyword)
        kw_words = kw_clean.split()
        if not kw_words:
            return False

        n_kw = len(kw_words)
        n_prompt = len(prompt_words)
        for i in range(n_prompt - n_kw + 1):
            if prompt_words[i : i + n_kw] == kw_words:
                return True
        return False

    async def classify(self, prompt: str) -> list[str]:
        """Classifies a prompt against categories using token rules and semantic similarity."""
        if not self._initialized:
            await self.initialize()

        # 1. Token keyword matching
        normalized_prompt = self._normalize_text(prompt)
        prompt_words = normalized_prompt.split()

        matched_categories = set()
        for cat_name, cat_data in self.categories.items():
            keywords = cat_data.get("keywords", [])
            for kw in keywords:
                if self._matches_keyword(prompt_words, kw):
                    matched_categories.add(cat_name)
                    break

        # 2. Semantic vector matching
        if self.embedder and self._anchor_embeddings:
            try:
                if hasattr(self.embedder, "aembed"):
                    prompt_vector = await self.embedder.aembed(prompt)
                else:
                    prompt_vector = self.embedder.embed(prompt)

                for cat_name, anchor_vectors in self._anchor_embeddings.items():
                    if cat_name in matched_categories:
                        continue
                    for anchor_vector in anchor_vectors:
                        sim = cosine_similarity(prompt_vector, anchor_vector)
                        if sim >= self.semantic_threshold:
                            matched_categories.add(cat_name)
                            break
            except Exception as e:
                logger.error("Semantic classification failed; falling back: %s", e)

        return sorted(list(matched_categories))

