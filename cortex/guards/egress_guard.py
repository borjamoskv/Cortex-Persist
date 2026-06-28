# [C5-REAL] Exergy-Maximized
"""egress_guard.py

C5-REAL Egress Guard. Ensures that the Swarm does not exfiltrate data
or abuse external APIs (like SendGrid/Mailgun) during outbound communication.
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger("cortex.guards.egress")

# YARA-like patterns for immediate rejection
_EXFIL_PATTERNS = [
    re.compile(r"sk_live_[a-zA-Z0-9]+"),  # Stripe keys
    re.compile(r"v6_aesgcm:[a-zA-Z0-9+/=]+"),  # CORTEX internal encryption
    re.compile(r"SG\.[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"),  # SendGrid API keys
    re.compile(r"-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----"),  # PEM Keys
]


@dataclass
class EgressAuthorization:
    authorized: bool
    reason: str


class EgressGuard:
    """Thermodynamic firewall for external I/O calls."""

    def __init__(self, tenant_domains: list[str] | None = None):
        # Whitelisted domains. If None, any domain is allowed, but heavily rate-limited.
        self.tenant_domains = tenant_domains or []
        # In-memory token bucket for rate-limiting (per agent).
        self._rate_limits: dict[str, int] = {}
        # Simple limit: 5 emails per hour per agent
        self.max_emails_per_agent = 5

    def authorize_email(self, agent_id: str, recipient: str, body: str) -> EgressAuthorization:
        """
        Validates whether an agent is allowed to dispatch an email.
        """
        # 1. Taint / Pattern Breach Check
        for pattern in _EXFIL_PATTERNS:
            if pattern.search(body):
                logger.error("[P0] EgressGuard: Pattern breach detected from agent %s", agent_id)
                return EgressAuthorization(
                    False, "C5-REAL: Exfiltration pattern detected in payload."
                )

        # 2. Domain Whitelist Check
        if self.tenant_domains:
            domain = recipient.split("@")[-1]
            if domain not in self.tenant_domains:
                logger.warning("EgressGuard: Domain %s not whitelisted", domain)
                return EgressAuthorization(False, f"Domain {domain} is not in tenant_domains.")

        # 3. Rate Limit Check (Token Bucket simplified)
        current_count = self._rate_limits.get(agent_id, 0)
        if current_count >= self.max_emails_per_agent:
            logger.error("EgressGuard: Rate limit exceeded for agent %s", agent_id)
            return EgressAuthorization(False, "Rate limit exceeded. Kill Criteria AX-047.")

        # Authorize and increment
        self._rate_limits[agent_id] = current_count + 1
        return EgressAuthorization(True, "OK")
