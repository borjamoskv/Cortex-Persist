# [C5-REAL] Exergy-Maximized
"""
Substack Crawler Inflation Guard (Axiom OUROBOROS-014, OUROBOROS-094).

Enforces thermodynamic reality against PR inboxes and Firewall Scanners.
Intersects incoming subscriber metrics and rejects Epistemic Limerence
by raising a Saga-compatible ValueError before reaching the SQLite WAL.

Author: borjamoskv
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("cortex.guards.substack_crawler")

# Canonical Taint Tokens
CRAWLER_BOT_PREFIXES = frozenset(
    {
        "press",
        "demos",
        "info",
        "editorial",
        "news",
        "submissions",
        "contact",
        "hello",
        "hi",
        "admin",
        "marketing",
        "pr",
        "support",
        "team",
        "hola",
        "webmaster",
    }
)

# No B2C blacklist: consumer domains are considered valid organic traffic.


# Sovereign Whitelist: Known Human Nodes (Top Organics) that bypass B2C Noise filters
SOVEREIGN_WHITELIST = frozenset({"hugopotxo@gmail.com", "bradmarianioan@gmail.com"})


class SubstackCrawlerGuard:
    """
    Evaluates raw metrics from SaaS platforms to purge Bot Inflation.
    Rejects propositions by raising ValueError (triggering SAGA-1 abort).
    """

    def evaluate_subscriber_exergy(
        self, email: str, opens: int, clicks: int, ts_delta_ms: float | None = None
    ) -> float:
        """
        Validates the causal integrity of an email interaction.
        """
        if not email or "@" not in email:
            raise ValueError("[Axiom OUROBOROS-014] Epistemic Breach: Malformed identity format.")

        email_lower = email.lower()
        if email_lower in SOVEREIGN_WHITELIST:
            return 1.0  # Bypass all noise filters for known SOTA humans

        local_part, domain = email_lower.split("@", 1)

        # 1. Reject Firewall Dead Inboxes (Crawler Inflation)
        if local_part in CRAWLER_BOT_PREFIXES:
            # If there's engagement on a dead inbox, it's 100% a firewall bot
            if opens > 10:
                logger.error(
                    "Thermodynamic Violation (Axiom OUROBOROS-094): Crawler Bot Detected "
                    "on dead inbox [%s]. Opens: %d",
                    email,
                    opens,
                )
                raise ValueError(
                    f"[Axiom OUROBOROS-094] Thermodynamic Violation: Epistemic Limerence detected. "
                    f"Email '{email}' is a Corporate Dead Inbox exhibiting Crawler Inflation. "
                    f"Raw opens ({opens}) are an algorithmic hallucination."
                )
            return 0.0

        # 3. Microsecond Execution (Proofpoint / Barracuda asynchronous scanners)
        if ts_delta_ms is not None:
            if opens > 0 and ts_delta_ms < 1500.0:
                logger.error("Non-human reaction time [%s ms] detected for %s", ts_delta_ms, email)
                raise ValueError(
                    f"[Axiom OUROBOROS-014] Causal Impossibility: Interaction delta of "
                    f"{ts_delta_ms}ms is sub-human. Firewall scanner confirmed for {email}."
                )

        # 4. Arithmetic Fallback (If ts_delta_ms is not present)
        # Bots repeatedly open each embedded link to analyze them in sandboxes
        if opens > 50 and clicks > 0 and abs(opens - clicks) <= 5:
            logger.error("Symmetrical engagement ratio anomaly detected for %s", email)
            raise ValueError(
                f"[Axiom OUROBOROS-094] Thermodynamic Violation: 1:1 Open/Click ratio anomaly. "
                f"Identity '{email}' is operating a Link Scanner."
            )

        # If it passes the BFT filters, it is a SOTA human node
        return 1.0

    def enforce_saga_contract(self, subscriber_record: dict[str, Any]) -> dict[str, Any]:
        """
        Intercepts a proposed fact payload before it reaches the SAGA-1 entry point.
        """
        email = subscriber_record.get("Email", "")
        # Extraer enteros de forma defensiva
        try:
            opens = int(subscriber_record.get("Emails opened (6mo)", 0))
        except (ValueError, TypeError):
            opens = 0

        try:
            clicks = int(subscriber_record.get("Links clicked", 0))
        except (ValueError, TypeError):
            clicks = 0

        ts_delta = subscriber_record.get("ts_delta_ms")

        # Execute Exergy Colapse. Raises ValueError on failure.
        score = self.evaluate_subscriber_exergy(email, opens, clicks, ts_delta_ms=ts_delta)

        subscriber_record["CORTEX_VIP_SIGNAL"] = True if score == 1.0 else False

        return subscriber_record
