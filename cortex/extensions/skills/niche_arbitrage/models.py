from datetime import datetime

from pydantic import BaseModel, Field


class NicheTarget(BaseModel):
    """Target URL or community for extraction."""

    url: str = Field(..., description="The target URL to extract data from")
    name: str = Field(..., description="Human readable name of the target")
    tags: list[str] = Field(default_factory=list, description="Tags for categorization")


class TrendSignal(BaseModel):
    """An extracted signal of a trend or market inefficiency."""
    title: str = Field(..., description="Headline of the trend or signal")
    evidence: str = Field(
        ..., description="Direct quote or extracted evidence from the text"
    )
    exergy_score: int = Field(
        ..., ge=1, le=10, description="Thermodynamic usefulness score (1-10)"
    )
    sentiment: str = Field(
        ..., description="General sentiment (positive, neutral, negative, urgent)"
    )
    proposed_arbitrage: str = Field(
        ..., description="How to extract value or arbitrage from this signal"
    )


class MarketReport(BaseModel):
    """Synthesized report containing multiple trend signals."""

    target_name: str = Field(..., description="Source of the report")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    summary: str = Field(..., description="High-level synthesis of the target's current state")
    signals: list[TrendSignal] = Field(default_factory=list, description="Extracted signals")

    def to_markdown(self) -> str:
        """Renders the report as 0-rhetoric markdown."""
        md_lines = [
            f"# MARKET REPORT: {self.target_name}",
            f"*Generated: {self.timestamp.isoformat()}*",
            "",
            "## Synthesis",
            f"{self.summary}",
            "",
            "## Extracted Signals",
        ]
        
        for sig in sorted(self.signals, key=lambda x: x.exergy_score, reverse=True):
            md_lines.extend([
                f"### {sig.title} [Exergy: {sig.exergy_score}/10]",
                f"**Sentiment:** {sig.sentiment}",
                "",
                f"> {sig.evidence}",
                "",
                f"**Arbitrage Vector:** {sig.proposed_arbitrage}",
                "---"
            ])
            
        return "\n".join(md_lines)
