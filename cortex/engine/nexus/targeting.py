"""
CORTEX Nexus: Mercor-Sovereign-Omega Targeting Params
RFC-047 / Project LEVIATHAN
"""

from typing import List
from pydantic import BaseModel


class TargetingParameter(BaseModel):
    region: str = "EU"
    sector: str = "AI / Agentic Frameworks"
    minimum_valuation: float = 1_000_000.0  # $1M (Targeting established seeds)
    regulatory_vulnerability: str = "EU AI Act Art. 12 (Record-keeping compliance)"
    ascription_vector: str = "Automated audit-ledger injection"


# Initial targeting list for the first swarm wave
FIRST_WAVE_TARGETS = [
    TargetingParameter(
        region="France",
        sector="LLM Infrastructure",
        minimum_valuation=5_000_000.0
    ),
    TargetingParameter(
        region="Germany",
        sector="Autonomous SaaS Agents",
        minimum_valuation=2_000_000.0
    ),
    TargetingParameter(
        region="Spain",
        sector="Agentic BPO / Customer Service",
        minimum_valuation=1_000_000.0
    )
]


class SwarmConfig(BaseModel):
    agent_count: int = 100
    mode: str = "High-Exergy (Mercor-Style Recruitment)"
    objective: str = "Convert 10% of targets to CORTEX Audit Ledger within 30 days"
    audit_trail_enforcement: bool = True
