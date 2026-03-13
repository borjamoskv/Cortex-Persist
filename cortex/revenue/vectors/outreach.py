"""CORTEX Revenue — Vector 3: B2B Web Design Outreach Pipeline.

Automated lead generation and outreach leveraging Awwwards-grade
design capabilities to sell premium web redesign services.

Pipeline:
    1. Target Discovery → find companies with outdated websites
    2. Scoring → Lighthouse audit, mobile score, HTTPS, design age
    3. Prototype Generation → before/after mockup
    4. Outreach Composition → personalized cold email
    5. CRM Tracking → persist leads to CORTEX ledger
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from cortex.revenue.models import (
    ExecutionResult,
    Opportunity,
    VectorType,
)

logger = logging.getLogger("cortex.revenue.outreach")


@dataclass
class Lead:
    """A potential client lead.

    Attributes:
        company: Company name.
        website: Current website URL.
        industry: Business sector.
        contact_email: Discovered contact email (if available).
        lighthouse_score: PageSpeed Insights performance score (0-100).
        mobile_friendly: Whether the site passes mobile-friendly test.
        has_https: Whether the site has HTTPS.
        design_age_years: Estimated age of the current design.
        estimated_budget: Estimated budget for a redesign (EUR).
    """

    company: str
    website: str
    industry: str = ""
    contact_email: str = ""
    lighthouse_score: int = 0
    mobile_friendly: bool = True
    has_https: bool = True
    design_age_years: float = 0.0
    estimated_budget: Decimal = Decimal("0")

    @property
    def pain_score(self) -> float:
        """Calculate how much the company needs a redesign.

        Higher = more pain = better opportunity.
        Scale: 0-100.
        """
        score = 0.0

        # Low Lighthouse score = high pain
        if self.lighthouse_score < 30:
            score += 40
        elif self.lighthouse_score < 50:
            score += 25
        elif self.lighthouse_score < 70:
            score += 10

        # No mobile = high pain
        if not self.mobile_friendly:
            score += 25

        # No HTTPS = high pain
        if not self.has_https:
            score += 15

        # Old design = moderate pain
        if self.design_age_years > 5:
            score += 20
        elif self.design_age_years > 3:
            score += 10

        return min(score, 100.0)


# ─── Mock Lead Database ───────────────────────────────────────
# In production: scrape industry directories, Google Maps, LinkedIn

MOCK_LEADS: list[dict[str, Any]] = [
    {
        "company": "Restaurante El Txoko",
        "website": "https://eltxoko.com",
        "industry": "hospitality",
        "contact_email": "info@eltxoko.com",
        "lighthouse_score": 22,
        "mobile_friendly": False,
        "has_https": True,
        "design_age_years": 7,
        "estimated_budget": Decimal("3000"),
    },
    {
        "company": "Clínica Dental Sonríe",
        "website": "https://clinicasonrie.es",
        "industry": "healthcare",
        "contact_email": "contacto@clinicasonrie.es",
        "lighthouse_score": 35,
        "mobile_friendly": True,
        "has_https": False,
        "design_age_years": 5,
        "estimated_budget": Decimal("5000"),
    },
    {
        "company": "Inmobiliaria Bizkaia",
        "website": "https://inmo-bizkaia.com",
        "industry": "real_estate",
        "contact_email": "ventas@inmo-bizkaia.com",
        "lighthouse_score": 18,
        "mobile_friendly": False,
        "has_https": True,
        "design_age_years": 8,
        "estimated_budget": Decimal("8000"),
    },
    {
        "company": "Taller Mecánico Gaztelu",
        "website": "https://tallergaztelu.com",
        "industry": "automotive",
        "contact_email": "info@tallergaztelu.com",
        "lighthouse_score": 45,
        "mobile_friendly": True,
        "has_https": True,
        "design_age_years": 4,
        "estimated_budget": Decimal("2500"),
    },
    {
        "company": "Asesoria Fiscal Urrutia",
        "website": "https://asesoriaurrutia.com",
        "industry": "finance",
        "contact_email": "fiscal@asesoriaurrutia.com",
        "lighthouse_score": 28,
        "mobile_friendly": False,
        "has_https": False,
        "design_age_years": 6,
        "estimated_budget": Decimal("4000"),
    },
    {
        "company": "Gimnasio FitBilbao",
        "website": "https://fitbilbao.com",
        "industry": "fitness",
        "contact_email": "hola@fitbilbao.com",
        "lighthouse_score": 55,
        "mobile_friendly": True,
        "has_https": True,
        "design_age_years": 3,
        "estimated_budget": Decimal("3500"),
    },
]


EMAIL_TEMPLATE = """Asunto: {company} merece una web que convierta — análisis gratuito incluido

Hola,

Soy diseñador web especializado en experiencias digitales premium.

He analizado {website} y he detectado oportunidades importantes:
{pain_points}

He preparado un concepto visual gratuito de cómo podría verse {company} con un diseño moderno — sin compromiso.

¿Puedo enviártelo?

Un saludo,
MOSKV Studio
"""


@dataclass
class OutreachVector:
    """Vector 3: B2B Web Design Outreach Pipeline.

    Discovers companies with outdated websites, scores their pain level,
    generates personalized outreach emails, and tracks the CRM pipeline.
    """

    _enabled: bool = True
    min_pain_score: float = 30.0
    contacted: set[str] = field(default_factory=set)
    pipeline: list[dict[str, Any]] = field(default_factory=list)

    @property
    def id(self) -> VectorType:
        """Vector identifier."""
        return VectorType.OUTREACH

    @property
    def name(self) -> str:
        """Human-readable name."""
        return "B2B Web Design Pipeline"

    @property
    def enabled(self) -> bool:
        """Whether this vector is active."""
        return self._enabled

    async def scan(self) -> list[Opportunity]:
        """Scan for leads with high pain scores.

        Currently uses mock data. In production: scrape Google Maps,
        industry directories, LinkedIn, etc.

        Returns:
            List of outreach opportunities sorted by estimated value.
        """
        opportunities: list[Opportunity] = []

        for raw in MOCK_LEADS:
            if raw["website"] in self.contacted:
                continue

            lead = Lead(**raw)

            if lead.pain_score < self.min_pain_score:
                continue

            pain_points = self._describe_pain(lead)

            opp = Opportunity(
                vector=VectorType.OUTREACH,
                title=f"Redesign: {lead.company}",
                description=(
                    f"{lead.company} ({lead.industry}) — "
                    f"Lighthouse: {lead.lighthouse_score}/100, "
                    f"Pain: {lead.pain_score:.0f}/100. "
                    f"Budget est: €{lead.estimated_budget}"
                ),
                estimated_value=lead.estimated_budget,
                confidence="C2",  # Cold outreach = C2
                effort_hours=4.0,  # Mockup + email + follow-up
                source_url=lead.website,
                meta={
                    "company": lead.company,
                    "industry": lead.industry,
                    "contact_email": lead.contact_email,
                    "lighthouse_score": lead.lighthouse_score,
                    "pain_score": lead.pain_score,
                    "pain_points": pain_points,
                },
            )
            opportunities.append(opp)

        logger.info(
            "🎯 [OUTREACH] Found %d leads with pain score ≥ %.0f.",
            len(opportunities),
            self.min_pain_score,
        )
        return opportunities

    async def execute(self, opportunity: Opportunity) -> ExecutionResult:
        """Execute outreach for a lead.

        Generates a personalized email and adds the lead to the CRM pipeline.
        Does NOT auto-send — returns the draft for human review.

        Args:
            opportunity: The outreach opportunity.

        Returns:
            Execution result with the draft email.
        """
        meta = opportunity.meta
        company = meta.get("company", "Unknown")
        website = opportunity.source_url

        # Generate pain point description for email
        pain_points = meta.get("pain_points", [])
        pain_text = "\n".join(f"  • {p}" for p in pain_points)

        # Compose email
        email = EMAIL_TEMPLATE.format(
            company=company,
            website=website,
            pain_points=pain_text,
        )

        # Add to CRM pipeline
        self.contacted.add(website)
        self.pipeline.append({
            "company": company,
            "website": website,
            "status": "draft_ready",
            "email": email,
            "estimated_value": str(opportunity.estimated_value),
        })

        logger.info(
            "📧 [OUTREACH] Draft ready for %s (est. €%s)",
            company,
            opportunity.estimated_value,
        )

        return ExecutionResult(
            opportunity_id=opportunity.id,
            success=True,
            revenue_actual=Decimal("0"),  # Revenue comes if they convert
            cost_actual=Decimal("0"),
            meta={
                "action": "draft_ready",
                "email_draft": email,
                "company": company,
                "contact": meta.get("contact_email", ""),
            },
        )

    def _describe_pain(self, lead: Lead) -> list[str]:
        """Generate human-readable pain point descriptions.

        Args:
            lead: The lead to analyze.

        Returns:
            List of pain point strings for the email.
        """
        points: list[str] = []

        if lead.lighthouse_score < 50:
            points.append(
                f"Rendimiento web: {lead.lighthouse_score}/100 "
                f"(Google penaliza esto en SEO)"
            )
        if not lead.mobile_friendly:
            points.append(
                "La web no está optimizada para móvil "
                "(60% del tráfico viene de móvil)"
            )
        if not lead.has_https:
            points.append(
                "Sin certificado HTTPS "
                "(Chrome muestra 'No seguro' a tus clientes)"
            )
        if lead.design_age_years > 4:
            points.append(
                f"El diseño tiene ~{lead.design_age_years:.0f} años "
                f"(la media del sector se renueva cada 3)"
            )

        return points
