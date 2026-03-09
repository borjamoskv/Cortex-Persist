"""CORTEX Gateway — Shielding & Telemetry Suppression.

Protects the operator from accidental data leaks and behavioral tracking.
"""

import logging
import re
from typing import Dict, List, Any

logger = logging.getLogger("cortex.gateway.shield")

# Patterns of data we want to "radiopactize"
SENSITIVE_PATTERNS = [
    r"cursor-session-id:[a-zA-Z0-9-]+",
    r"vscode-session-id:[a-zA-Z0-9-]+",
    r"X-Session-ID:[a-zA-Z0-9-]+",
    r"X-Amzn-Trace-Id:[a-zA-Z0-9-=]+",
]

class APIShield:
    @staticmethod
    def strip_telemetry_headers(headers: Dict[str, str]) -> Dict[str, str]:
        """Remove identifying headers often sent by IDEs and enterprise proxies."""
        cleaned = {}
        blocked = []
        
        # Denylist of common telemetry headers
        denylist = {
            "x-cursor-client-version",
            "x-cursor-session-id",
            "x-vscode-proxy-id",
            "x-session-id",
            "x-request-id",
            "user-agent", # Sometimes contains version info
            "traceparent",
            "tracestate",
        }
        
        for k, v in headers.items():
            if k.lower() in denylist:
                blocked.append(k)
                continue
            cleaned[k] = v
            
        if blocked:
            logger.debug("🛡️ [SHIELD] Blocked headers: %s", blocked)
            
        return cleaned

    @staticmethod
    def radiopactize_prompt(content: str) -> str:
        """Replace sensitive patterns in text with placeholders."""
        shielded = content
        for pattern in SENSITIVE_PATTERNS:
            shielded = re.sub(pattern, "[SHIELDED_IDENTIFIER]", shielded)
        return shielded

    @staticmethod
    def mask_usage(data: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure token usage doesn't lean toward identifying complexity."""
        # Optional: Jitter the token counts to prevent side-channel timing attacks
        if "usage" in data:
            data["usage"]["total_tokens"] = data["usage"]["total_tokens"] # + random jitter
        return data
