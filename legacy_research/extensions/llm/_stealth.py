# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

import asyncio
import logging
import random
import re

from ._constants import _BROWSER_PROFILES, _GHOST_SIGNATURES

logger = logging.getLogger("cortex.extensions.llm.stealth")


def prepare_stealth_headers(extra_headers: dict[str, str]) -> dict[str, str]:
    """Ω₁₇: Phantom Sovereignty - Full header suite randomization."""
    from cortex.config import LLM_STEALTH_MODE

    headers: dict[str, str] = {"Content-Type": "application/json", **extra_headers}
    if not LLM_STEALTH_MODE:
        headers["User-Agent"] = "CORTEX/5.0 (Sovereign Agent)"
        headers["X-Cortex-Agent"] = "CORTEX-Persist"
        return headers

    profile = random.choice(_BROWSER_PROFILES)
    _LANGS = ["en-US,en;q=0.9", "es-ES,es;q=0.8,en;q=0.7", "en-GB,en;q=0.9"]

    headers.update(
        {
            "User-Agent": profile["User-Agent"],
            "Accept": profile["Accept"],
            "Accept-Language": random.choice(_LANGS),
            "Sec-Ch-Ua": profile["Sec-Ch-Ua"],
            "Sec-Ch-Ua-Mobile": "?0",
            "Sec-Ch-Ua-Platform": profile["Sec-Ch-Ua-Platform"],
            "Upgrade-Insecure-Requests": profile["Upgrade-Insecure-Requests"],
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "DNT": "1",
            "Connection": "keep-alive",
        }
    )
    # Purge CORTEX fingerprints
    headers.pop("X-Cortex-Agent", None)
    headers.pop("X-Cortex-Version", None)
    return headers


def sanitize_response(text: str) -> str:
    """Ω₁₈: GHOST_FILTER - Semantic response scrubbing to remove AI signatures."""
    from cortex.config import LLM_STEALTH_MODE

    if not LLM_STEALTH_MODE or not text:
        return text

    scrubbed = text
    for pattern in _GHOST_SIGNATURES:
        scrubbed = re.sub(pattern, "", scrubbed).strip()

    # Remove common "apologetic" prefixes
    _APOL = r"(?i)^(i apologize|i'm sorry|as an ai language model|as an ai).*?(\.|\!|\:)\s*"
    scrubbed = re.sub(_APOL, "", scrubbed)
    return scrubbed.strip()


async def apply_causal_jitter(tokens_estimate: int = 100):
    """Ω₁₉: CAUSAL_JITTER - Variable timing to break automated detection."""
    from cortex.config import LLM_STEALTH_MODE

    if not LLM_STEALTH_MODE:
        return

    delay = random.gauss(1.2, 0.4)
    delay += tokens_estimate * 0.01
    delay = max(0.3, min(3.5, delay))

    logger.debug("Ω₁₉: GHOST_RUN Jitter -> Applied %.2fs delay", delay)
    await asyncio.sleep(delay)
