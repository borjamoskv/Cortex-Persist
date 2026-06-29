# [C5-REAL] Exergy-Maximized
"""
Semantic Leak Guard - Enforces defensive mitigations against semantic reconnaissance vectors
under arbitrary encoding transformations. (Vector C)
"""

from __future__ import annotations

import logging
import re
import unicodedata

logger = logging.getLogger("cortex.guards.semantic_leak")

class SemanticLeakViolationError(Exception):
    """Raised when a semantic containment policy is violated."""
    pass

class SemanticLeakGuard:
    """
    Enforces semantic containment by implementing structural canonicalization and
    intent filtering, demonstrating the insufficiency of raw regex output filters.
    """

    # Protected metatada items that MUST NOT leak
    PROTECTED_ENTITIES = {
        "model_id", "provider", "architecture", "version", 
        "tokenizer", "system_prompt", "deployment_id"
    }

    # Common strings associated with protected metadata to redact/block
    REDACTION_TARGETS = [
        r"gpt-\d",
        r"claude-\d",
        r"qwen",
        r"deepseek",
        r"cortex-persist",
        r"babylon-60",
    ]

    # Literal strings for canonical leak detection
    CANONICAL_TARGETS = [
        "gpt3", "gpt4", "gpt5", "claude3", "claude4", "qwen", "deepseek", "cortexpersist", "babylon60"
    ]

    @classmethod
    def canonicalize(cls, text: str) -> str:
        """
        Normalize output to collapse trivial obfuscation before filtering.
        - Lowercase
        - Unicode normalization (NFKD)
        - Whitespace and separator collapse
        """
        # 1. Lowercase
        normalized = text.lower()
        
        # 2. Unicode normalization (decompose)
        normalized = unicodedata.normalize("NFKD", normalized)
        
        # 3. Strip combining characters (accents)
        normalized = "".join(c for c in normalized if not unicodedata.combining(c))
        
        # 4. Collapse whitespace and non-alphanumeric separators
        normalized = re.sub(r"[^\w\s]", "", normalized)
        normalized = re.sub(r"\s+", "", normalized)
        
        return normalized

    @classmethod
    def detect_intent(cls, prompt: str) -> bool:
        """
        Classifies if the user prompt attempts to obtain protected identity metadata.
        Returns True if intent is malicious/reconnaissance.
        """
        canon_prompt = cls.canonicalize(prompt)
        recon_keywords = ["whichmodel", "whoareyou", "systemprompt", "whatisyourarchitecture", "deploymentid", "version"]
        
        for kw in recon_keywords:
            if kw in canon_prompt:
                return True
        return False

    @classmethod
    def redact_metadata(cls, text: str) -> str:
        """
        Redacts known sensitive metadata from the output string.
        """
        redacted = text
        for pattern in cls.REDACTION_TARGETS:
            redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)
        return redacted

    @classmethod
    def verify_output(cls, raw_output: str) -> str:
        """
        Full C5-REAL Guard: canonicalizes text and verifies semantic non-disclosure.
        Raises SemanticLeakViolationError if leak is detected, otherwise returns redacted text.
        """
        canonicalized = cls.canonicalize(raw_output)
        
        for entity in cls.CANONICAL_TARGETS:
            if entity in canonicalized:
                logger.error(f"[P0] SemanticLeakGuard: Covert semantic leakage detected for {entity}")
                raise SemanticLeakViolationError(
                    "Semantic Containment Breach: Output contains protected metadata under transformation."
                )

        return cls.redact_metadata(raw_output)
