"""CORTEX v7 — HDC Encoder (Text to Hypervector).

Converts raw text into a 10k-dim bipolar hypervector algebraically.
No ML model, no neural network dependency. Cold start in <100ms.

Algorithm [Positional N-Gram Bundling]:
1. Tokenize text into words (or n-grams).
2. For each token t at position i:
   a. Get atomic hypervector from ItemMemory: hv_t
   b. Permute it by position: hv_pi = permute(hv_t, i)
3. Bundle all positional hypervectors: H = bundle(hv_p0, hv_p1, ...)

Optionally binds with Project and Role vectors for CORTEX fact structure.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from typing import Final

from cortex.memory.hdc.algebra import HVType, bind, bundle, permute
from cortex.memory.hdc.item_memory import ItemMemory

__all__ = ["HDCEncoder"]

logger = logging.getLogger("cortex.memory.hdc.codec")

# Simple tokenizer for text (fallback from ML tokenizers)
_TOKEN_PATTERN: Final[re.Pattern] = re.compile(r"\b\w+\b")


class HDCEncoder:
    """Algebraic encoder converting text to hypervectors.

    Args:
        item_memory: Codebook for symbol → random hypervector lookup.
    """

    __slots__ = ("_memory",)

    def __init__(self, item_memory: ItemMemory) -> None:
        self._memory = item_memory

    @property
    def dimension(self) -> int:
        """Hypervector dimensionality."""
        return self._memory.dim

    def tokenize(self, text: str) -> list[str]:
        """Convert text into canonical tokens (lowercase words)."""
        return _TOKEN_PATTERN.findall(text.lower())

    def encode_text(self, text: str) -> HVType:
        """Encode raw text into a single bundled hypervector.

        Uses positional encoding to preserve word order, not just bag-of-words.
        If text is empty, returns a zero vector (which won't match well with bipolar ±1).

        Args:
            text: Raw input string.

        Returns:
            10k-dim bipolar hypervector representing the entire text.
        """
        tokens = self.tokenize(text)
        if not tokens:
            # Empty text gets a random vector or zeros; we use random to preserve ±1
            logger.debug("HDC encode_text: empty input, returning noise vector")
            return self._memory.encode("__empty__")

        # Get atomic vector for each token
        token_hvs = [self._memory.encode(t) for t in tokens]

        # Positional encoding: permute earlier words more (or less)
        # We permute by 'i+1' so pos 0 isn't identity
        positional_hvs = [permute(hv, i + 1) for i, hv in enumerate(token_hvs)]

        # If only 1 token, bundle() raises error. Return permuted directly.
        if len(positional_hvs) == 1:
            return positional_hvs[0]

        # Superpose all tokens into one semantic representation
        return bundle(*positional_hvs)

    def encode_fact(
        self,
        content: str,
        fact_type: str | None = None,
        project_id: str | None = None,
    ) -> HVType:
        """Encode a full CORTEX fact with role and project bindings.

        This allows traceability/decomposition later:
            fact_hv = content_hv ⊗ role_hv ⊗ project_hv

        Args:
            content: Raw text content of the fact.
            fact_type: Optional CORTEX_ROLE (e.g., 'decision', 'bridge').
            project_id: Optional project identifier.

        Returns:
            Bound composite hypervector.
        """
        hv = self.encode_text(content)

        if fact_type:
            role_hv = self._memory.role_vector(fact_type)
            hv = bind(hv, role_hv)

        if project_id:
            proj_hv = self._memory.project_vector(project_id)
            hv = bind(hv, proj_hv)

        return hv

    def encode_batch(self, texts: Sequence[str]) -> list[HVType]:
        """Encode multiple texts sequentially."""
        return [self.encode_text(t) for t in texts]
