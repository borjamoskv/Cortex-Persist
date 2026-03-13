"""Phase 3: Zero-Click MVP Generation.

Transforms a validated Opportunity into a testable landing page, waitlist, and Stripe stub.
"""

from __future__ import annotations

import logging

from cortex.market_maker.models import MVPArtifact, Opportunity

log = logging.getLogger(__name__)


class MVPGenerator:
    """Generates structural MVP artifacts (HTML, placeholders) for testing."""

    async def generate(self, opportunity: Opportunity) -> MVPArtifact:
        """
        Takes an Opportunity and generates an MVPArtifact.

        In production, this could delegate to GenesisEngine + Awwwards Builder.
        Here we generate a high-conversion deterministic stub.
        """
        html = self._generate_landing_html(opportunity)
        # Mock stripe price creation
        stripe_id = f"price_mock_{opportunity.signal.topic.replace(' ', '_').lower()}"

        log.info(
            "Generated MVP for '%s' (Stripe: %s)",
            opportunity.signal.topic,
            stripe_id,
        )

        return MVPArtifact(
            html_content=html,
            stripe_price_id=stripe_id,
        )

    def _generate_landing_html(self, opp: Opportunity) -> str:
        """Render a very basic, high-conversion styled landing page."""
        topic_title = opp.signal.topic.title()
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{topic_title} — Early Access</title>
    <style>
        body {{ font-family: system-ui, sans-serif; background: #0A0A0A; color: #FAFAFA; }}
        .hero {{ padding: 100px 20px; text-align: center; }}
        h1 {{ color: #CCFF00; font-size: 3rem; margin-bottom: 20px; }}
        .btn {{ background: #CCFF00; color: #0A0A0A; padding: 15px 30px; text-decoration: none; font-weight: bold; border-radius: 4px; display: inline-block; margin-top: 30px; }}
    </style>
</head>
<body>
    <div class="hero">
        <h1>{topic_title}</h1>
        <p>The sovereign solution you've been waiting for.</p>
        <a href="#checkout" class="btn">Get Early Access</a>
    </div>
</body>
</html>"""
