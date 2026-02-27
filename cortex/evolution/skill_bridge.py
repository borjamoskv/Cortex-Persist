# cortex/evolution/skill_bridge.py
"""AgentDomain ↔ MOSKV-1 Skill Mapping (Phase 5).

Maps each evolution agent domain to the corresponding MOSKV-1 skill,
enabling the sovereign pipeline to use evolution data to modulate
skill invocation priority and health assessment.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from cortex.evolution.agents import AgentDomain

logger = logging.getLogger(__name__)

_SKILLS_DIR = Path("~/.gemini/antigravity/skills").expanduser()

# Canonical domain → skill mapping
DOMAIN_SKILL_MAP: dict[AgentDomain, str] = {
    AgentDomain.FABRICATION: "aether-1",
    AgentDomain.ORCHESTRATION: "keter-omega",
    AgentDomain.SWARM: "legion-1",
    AgentDomain.EVOLUTION: "ouroboros-infinity",
    AgentDomain.SECURITY: "boveda-1",
    AgentDomain.PERCEPTION: "evolv-1",
    AgentDomain.MEMORY: "cortex",
    AgentDomain.EXPERIENCE: "impactv-1",
    AgentDomain.COMMUNICATION: "singularity-nexus",
    AgentDomain.VERIFICATION: "mejoralo",
}

# Reverse mapping: skill → domain
SKILL_DOMAIN_MAP: dict[str, AgentDomain] = {v: k for k, v in DOMAIN_SKILL_MAP.items()}


def get_skill_for_domain(domain: AgentDomain) -> str:
    """Return the MOSKV-1 skill name for an agent domain."""
    return DOMAIN_SKILL_MAP.get(domain, "cortex")


def get_domain_for_skill(skill_name: str) -> AgentDomain | None:
    """Return the agent domain for a MOSKV-1 skill, or None if unknown."""
    return SKILL_DOMAIN_MAP.get(skill_name)


def get_skill_path(domain: AgentDomain) -> Path:
    """Return the absolute path to the SKILL.md for a domain's skill."""
    skill_name = get_skill_for_domain(domain)
    return _SKILLS_DIR / skill_name / "SKILL.md"


def check_skill_health(domain: AgentDomain) -> bool:
    """Check if the MOSKV-1 skill for a domain is installed (SKILL.md exists)."""
    return get_skill_path(domain).exists()


def get_all_skill_health() -> dict[AgentDomain, bool]:
    """Check health for all 10 domains. Returns dict[domain → installed]."""
    return {domain: check_skill_health(domain) for domain in AgentDomain}


def get_skill_summary() -> dict[str, Any]:
    """Summary of skill health for telemetry/dashboard."""
    health = get_all_skill_health()
    installed = sum(1 for v in health.values() if v)
    return {
        "total_domains": len(AgentDomain),
        "installed_skills": installed,
        "missing_skills": [d.name for d, ok in health.items() if not ok],
        "mapping": {
            d.name: {"skill": s, "installed": health[d]} for d, s in DOMAIN_SKILL_MAP.items()
        },
    }
