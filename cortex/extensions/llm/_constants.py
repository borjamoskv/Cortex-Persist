# This file is part of CORTEX. Apache-2.0.
from __future__ import annotations

from typing import Final

_CONTENT_TYPE_JSON: Final[str] = "application/json"

# Ω₁₇: Phantom Sovereignty - Deterministic Browser Profiles
_BROWSER_PROFILES: Final[list[dict[str, str]]] = [
    {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        ),
        "Sec-Ch-Ua": ('"Not(A:Brand";v="99", "Google Chrome";v="122", "Chromium";v="122"'),
        "Sec-Ch-Ua-Platform": '"macOS"',
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
        ),
        "Upgrade-Insecure-Requests": "1",
    },
    {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        ),
        "Sec-Ch-Ua": ('"Not(A:Brand";v="99", "Google Chrome";v="121", "Chromium";v="121"'),
        "Sec-Ch-Ua-Platform": '"Windows"',
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,image/apng,*/*;q=0.8"
        ),
        "Upgrade-Insecure-Requests": "1",
    },
]

# Ω₁₈: Ghost Filter - AI Signatures to scrub from responses
_GHOST_SIGNATURES: Final[list[str]] = [
    r"(?i)as an ai( language)? model",
    r"(?i)i am an ai developed by (openai|google|deepseek|anthropic|mistral)",
    r"(?i)i do not have (feelings|personal opinions)",
    r"(?i)i am a large language model",
    r"(?i)developed by deepseek",
]
