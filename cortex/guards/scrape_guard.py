# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.

"""CORTEX Sovereign Scrape Sanization Guard.

Implements centralized validation for content scraped from external sources (e.g., Firecrawl).
Addresses "Byzantine Default" and "Write-Path Contract" where generative or scraped data
is strictly conjetura until validated.

Axiom: Ω₂ (Thermodynamic Law) & Ω₃ (Byzantine Error mitigation).
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger("cortex.guards.scrape_guard")

# O(1) Exergy limits
MAX_RAW_PAGE_SIZE = 150_000  # Chars limit to prevent Memory DoS
CORTEX_TAINT_SIGNATURE = "source_firecrawl_unverified"


@dataclass(frozen=True)
class SanitizedPayload:
    """Immutable data object for crossing the Byzantine Boundary."""

    content: str
    metadata: dict[str, str]
    taint: str = CORTEX_TAINT_SIGNATURE


class ScrapeSanitizerGuard:
    """Enforces structural entropy limits and sanitization on scraped HTML/Markdown."""

    # Fast regex to drop malicious attributes and executable blocks.
    # Note: Firecrawl markdown renderer handles most, but this is a defensive fallback.
    _SCRIPT_RE = re.compile(r"<script.*?>.*?</script>", re.IGNORECASE | re.DOTALL)
    _IFRAME_RE = re.compile(r"<iframe.*?>.*?</iframe>", re.IGNORECASE | re.DOTALL)
    _ON_EVENT_RE = re.compile(r"\s+on[a-z]+\s*=\s*(?:\"[^\"]*\"|'[^']*')", re.IGNORECASE)

    @classmethod
    def sanitize(cls, raw_content: str, source_url: Optional[str] = None) -> SanitizedPayload:
        """Sanitize scraped content, enforce thermodynamics, and append cryptographic taint.

        Args:
            raw_content: Unvalidated string from external scraper.
            source_url: The origin URL tracking attribution.

        Returns:
            SanitizedPayload containing clean text and taint metadata.

        Raises:
            ValueError: If input is utterly malformed or missing.
        """
        if not raw_content or not str(raw_content).strip():
            raise ValueError("Sovereign ScrapeGuard: Empty content provided for sanitization.")

        raw_content = str(raw_content)

        # 1. Thermodynamic Limit Enforcement (O(1) exergy drop)
        if len(raw_content) > MAX_RAW_PAGE_SIZE:
            logger.warning(
                "Sovereign ScrapeGuard: Thermodynamic constraint exceeded. "
                "Truncating payload from %d chars to %d.",
                len(raw_content),
                MAX_RAW_PAGE_SIZE,
            )
            raw_content = raw_content[:MAX_RAW_PAGE_SIZE]

        # 2. Structural Purgation (O(N) RegEx) - Bypass vector pollution
        # We strip typical residual HTML vectors that shouldn't exist in LLM context
        clean = cls._SCRIPT_RE.sub("", raw_content)
        clean = cls._IFRAME_RE.sub("", clean)
        clean = cls._ON_EVENT_RE.sub("", clean)

        # 3. Cryptographic Attribution
        metadata = {
            "source_url": source_url or "unknown",
            "cortex_taint": CORTEX_TAINT_SIGNATURE,
            "agent_trust": "0.0",  # Always zero trust for raw scrapes
        }

        return SanitizedPayload(content=clean.strip(), metadata=metadata)
