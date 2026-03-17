"""Cognitive Fingerprint — Data models.

Defines the CognitiveFingerprint dataclass: the compressed
representation of a human's decision-making patterns extracted
from the CORTEX Ledger.
"""

from __future__ import annotations
from typing import Optional

from dataclasses import dataclass, field

__all__ = ["CognitiveFingerprint", "DomainPreference", "PatternVector"]


@dataclass
class DomainPreference:
    """Preference signature for a single (project x fact_type) domain.

    Captures how a human behaves in a specific knowledge domain:
    confidence level, frequency, and dominant source.
    """

    project: str
    fact_type: str
    count: int
    avg_confidence_weight: float  # 0.0 (all C1) to 1.0 (all C5)
    dominant_source: str  # Most frequent source for this domain
    store_frequency_per_week: float  # Velocity: facts per 7 days
    recency_days: float  # Days since last fact in this domain


@dataclass
class PatternVector:
    """Decision-making pattern extracted across all domains.

    A compact numerical representation of how a human makes decisions,
    suitable for feeding agents as a behavioral prior.
    """

    # Risk tolerance: ratio of C3/C4/C5 facts vs C1/C2
    risk_tolerance: float  # 0.0 = risk-averse, 1.0 = bold experimenter

    # Caution index: ratio of 'error' + 'ghost' facts vs total
    caution_index: float  # 0.0 = never marks failures, 1.0 = obsessive

    # Bridge-building tendency: ratio of 'bridge' + 'discovery' facts
    synthesis_drive: float  # 0.0 = pure executor, 1.0 = pure architect

    # Session density: avg facts per active day
    session_density: float  # 0.0 = sporadic, 1.0 (capped at 10/day)

    # Recency bias: ratio of facts in last 30 days vs all facts
    recency_bias: float  # 0.0 = archaeologist, 1.0 = presentist

    # Cross-project spread: normalized distinct projects touched
    breadth: float  # 0.0 = mono-domain, 1.0 = polymath

    # Depth preference: avg content length (chars), normalized at 500
    depth_preference: float  # 0.0 = micro-notes, 1.0 = extensive


def _fmt_dim(label: str, value: float, hi: str, mid: str, lo: str) -> str:
    """Format a pattern dimension for the agent prompt."""
    if hi and value > 0.6:
        desc = hi
    elif mid and value > 0.35:
        desc = mid
    else:
        desc = lo if lo else mid
    return f"- **{label}**: {value:.0%} — {desc}"


@dataclass
class CognitiveFingerprint:
    """The complete cognitive fingerprint of a CORTEX user.

    This is the primary artifact of the Cognitive Fingerprint Extractor.
    It can be serialized to JSON and injected into agent system prompts
    to make them behave like the human, not just follow their rules.
    """

    # Identity
    tenant_id: str = "default"
    project_filter: Optional[str] = None
    extracted_at: str = ""  # ISO timestamp

    # Core pattern vector
    pattern: PatternVector = field(
        default_factory=lambda: PatternVector(
            risk_tolerance=0.0,
            caution_index=0.0,
            synthesis_drive=0.0,
            session_density=0.0,
            recency_bias=0.0,
            breadth=0.0,
            depth_preference=0.0,
        )
    )

    # Domain-level preferences (top N most active domains)
    domain_preferences: list[DomainPreference] = field(default_factory=list)

    # Derived metacognitive labels
    archetype: str = "unknown"  # e.g. "sovereign_architect", "obsessive_executor"
    archetype_confidence: float = 0.0  # 0.0-1.0

    # Stats
    total_facts_analyzed: int = 0
    active_domains: int = 0
    fingerprint_completeness: float = 0.0  # how much data backed this extraction

    def to_dict(self) -> dict:
        """Serialize to JSON-safe dict for agent injection."""
        return {
            "tenant_id": self.tenant_id,
            "project_filter": self.project_filter,
            "extracted_at": self.extracted_at,
            "archetype": self.archetype,
            "archetype_confidence": round(self.archetype_confidence, 3),
            "total_facts_analyzed": self.total_facts_analyzed,
            "active_domains": self.active_domains,
            "fingerprint_completeness": round(self.fingerprint_completeness, 3),
            "pattern": {
                "risk_tolerance": round(self.pattern.risk_tolerance, 3),
                "caution_index": round(self.pattern.caution_index, 3),
                "synthesis_drive": round(self.pattern.synthesis_drive, 3),
                "session_density": round(self.pattern.session_density, 3),
                "recency_bias": round(self.pattern.recency_bias, 3),
                "breadth": round(self.pattern.breadth, 3),
                "depth_preference": round(self.pattern.depth_preference, 3),
            },
            "domain_preferences": [
                {
                    "project": d.project,
                    "fact_type": d.fact_type,
                    "count": d.count,
                    "avg_confidence_weight": round(d.avg_confidence_weight, 3),
                    "dominant_source": d.dominant_source,
                    "store_frequency_per_week": round(d.store_frequency_per_week, 2),
                    "recency_days": round(d.recency_days, 1),
                }
                for d in self.domain_preferences
            ],
        }

    def to_agent_prompt(self) -> str:
        """Render a compact system prompt injection for agents."""
        p = self.pattern
        lines = [
            f"## Cognitive Fingerprint [{self.archetype.upper()}]",
            "",
            f"Archetype confidence: {self.archetype_confidence:.0%}",
            f"Based on {self.total_facts_analyzed} crystallized facts "
            f"across {self.active_domains} domains.",
            "",
            "### Decision-Making Patterns",
            _fmt_dim(
                "Risk Tolerance",
                p.risk_tolerance,
                "takes bold bets",
                "validates carefully",
                "extremely cautious",
            ),
            _fmt_dim(
                "Caution Index",
                p.caution_index,
                "deeply marks failures/ghosts",
                "rarely flags errors",
                "",
            ),
            _fmt_dim(
                "Synthesis Drive",
                p.synthesis_drive,
                "builds bridges and patterns",
                "executes decisions",
                "",
            ),
            _fmt_dim(
                "Session Density",
                p.session_density,
                "intensive crystallization",
                "selective recording",
                "",
            ),
            _fmt_dim(
                "Recency Bias",
                p.recency_bias,
                "lives in present",
                "integrates historical context",
                "",
            ),
            _fmt_dim("Breadth", p.breadth, "polymath across many domains", "deep specialist", ""),
            _fmt_dim(
                "Depth", p.depth_preference, "writes extensive facts", "prefers concise facts", ""
            ),
            "",
            "### Active Domain Preferences (Top 5)",
        ]
        for d in self.domain_preferences[:5]:
            lines.append(
                f"- [{d.project}/{d.fact_type}] "
                f"{d.count} facts · {d.store_frequency_per_week:.1f}/week · "
                f"confidence {d.avg_confidence_weight:.0%}"
            )
        return "\n".join(lines)
