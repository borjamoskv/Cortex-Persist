import asyncio
import logging
from dataclasses import dataclass

from cortex.engine.ledger import SovereignLedger

logger = logging.getLogger("cortex.services.bounty_service")


@dataclass
class BountyLead:
    number: int
    title: str
    url: str
    reward_usd: float
    difficulty: str
    score: float
    repo: str


class BountyService:
    """
    Service for identifying and prioritizing high-exergy bounties.
    """

    def __init__(self, ledger: SovereignLedger | None = None, reward_threshold: float = 200.0):
        self.ledger = ledger
        self.reward_threshold = reward_threshold

    async def scan_repository(self, owner: str, repo: str) -> list[BountyLead]:
        """
        Scans a repository for open issues with the 'bounty' label.
        Refactored from legacy agent_bounty_hunter logic.
        """
        logger.info("[BOUNTY] Scanning %s/%s for work opportunities...", owner, repo)

        # In a real implementation, this would use a GitHub client.
        # Mocking discovery for the integration pattern.
        mock_leads = [
            BountyLead(
                number=42,
                title="Implement Jules Actuator in CORTEX",
                url=f"https://github.com/{owner}/{repo}/issues/42",
                reward_usd=500.0,
                difficulty="medium",
                score=8.5,
                repo=f"{owner}/{repo}"
            )
        ]

        if self.ledger:
            await self.ledger.record_transaction(
                project="bounty",
                action="scan",
                detail={"repo": f"{owner}/{repo}", "leads_found": len(mock_leads)}
            )

        return mock_leads

    def rank_leads(self, leads: list[BountyLead]) -> list[BountyLead]:
        """Rank leads by reward and filter by exergy threshold (Ω₂)."""
        filtered = [L for L in leads if L.reward_usd >= self.reward_threshold]

        # Log discards if ledger is present
        if self.ledger and len(filtered) < len(leads):
            discard_count = len(leads) - len(filtered)
            asyncio.create_task(self.ledger.record_transaction(
                project="bounty",
                action="lead_discard",
                detail={"count": discard_count, "reason": "low_exergy_threshold"}
            ))

        return sorted(filtered, key=lambda x: x.reward_usd, reverse=True)

    def generate_claim_prompt(self, lead: BountyLead) -> str:
        """Constructs a prompt for the specialist to claim and solve the bounty."""
        return (
            f"Solve bounty {lead.repo}#{lead.number}: {lead.title}. "
            f"Reward: ${lead.reward_usd}. "
            f"Requirements: Deliver a high-quality PR following project standards."
        )
