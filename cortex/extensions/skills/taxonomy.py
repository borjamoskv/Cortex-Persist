# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.

"""Canonical taxonomy helpers for CORTEX and Antigravity skills."""

from __future__ import annotations

import re
from typing import Final

CANONICAL_SKILL_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "architecture",
        "communication",
        "evolution",
        "experience",
        "fabrication",
        "memory",
        "orchestration",
        "perception",
        "security",
        "swarm",
        "uncategorized",
        "verification",
    }
)
"""Stable category vocabulary for skill manifests.

Unknown categories remain accepted as lower-kebab custom slugs so external
Antigravity skill packs do not disappear from the registry.
"""

ANTIGRAVITY_CORTEX_NEXUS_TAG: Final[str] = "antigravity-cortex"
ANTIGRAVITY_CORTEX_NEXUS_SKILL: Final[str] = "singularity-nexus"

SKILL_CATEGORY_ALIASES: Final[dict[str, str]] = {
    "agentic-ui": "experience",
    "antigravity-cortex": "communication",
    "antigravitycortex": "communication",
    "architectural": "architecture",
    "bridge": "communication",
    "builder": "fabrication",
    "codegen": "fabrication",
    "comms": "communication",
    "design": "experience",
    "generation": "fabrication",
    "nexus": "communication",
    "persistent-memory": "memory",
    "procedural-memory": "memory",
    "qa": "verification",
    "quality": "verification",
    "security-compliance": "security",
    "sync": "communication",
    "testing": "verification",
    "ui": "experience",
    "ux": "experience",
    "workflow": "orchestration",
}

AGENT_DOMAIN_CATEGORY_MAP: Final[dict[str, str]] = {
    "COMMUNICATION": "communication",
    "EVOLUTION": "evolution",
    "EXPERIENCE": "experience",
    "FABRICATION": "fabrication",
    "MEMORY": "memory",
    "ORCHESTRATION": "orchestration",
    "PERCEPTION": "perception",
    "SECURITY": "security",
    "SWARM": "swarm",
    "SYNERGY": "orchestration",
    "VERIFICATION": "verification",
}

CANONICAL_SKILL_CLASSIFICATIONS: Final[frozenset[str]] = frozenset(
    {
        "DEPRECATED",
        "EXPERIMENTAL",
        "OPERATIONAL",
        "QUARANTINED",
        "TRANSCENDENT",
    }
)

SKILL_CLASSIFICATION_ALIASES: Final[dict[str, str]] = {
    "active": "OPERATIONAL",
    "operational": "OPERATIONAL",
    "prod": "OPERATIONAL",
    "production": "OPERATIONAL",
    "transcendent": "TRANSCENDENT",
    "transcendente": "TRANSCENDENT",
}

CANONICAL_DANGER_LEVELS: Final[frozenset[str]] = frozenset(
    {
        "CRITICAL",
        "HIGH",
        "LOW",
        "MEDIUM",
        "NONE",
    }
)

DANGER_LEVEL_ALIASES: Final[dict[str, str]] = {
    "0": "NONE",
    "1": "LOW",
    "2": "MEDIUM",
    "3": "HIGH",
    "4": "CRITICAL",
    "crit": "CRITICAL",
    "critical": "CRITICAL",
    "high-risk": "HIGH",
    "med": "MEDIUM",
    "medium-risk": "MEDIUM",
    "p0": "CRITICAL",
    "p1": "HIGH",
    "p2": "MEDIUM",
    "safe": "NONE",
}

LEGACY_TRANSCENDENT_CATEGORIES: Final[frozenset[str]] = frozenset(
    {
        "transcendent-consciousness",
        "transcendent-manifold",
    }
)


def _slug(value: object) -> str:
    """Return a lower-kebab slug while preserving unknown taxonomy values."""
    text = str(value or "").strip().lower()
    text = text.replace("_", "-").replace(" ", "-")
    text = re.sub(r"[^a-z0-9-]+", "-", text)
    return "-".join(part for part in text.split("-") if part)


def _constant(value: object) -> str:
    return _slug(value).upper().replace("-", "_")


def normalize_skill_category(value: object) -> str:
    """Normalize category aliases to the canonical category vocabulary.

    Unknown non-empty values are returned as lower-kebab custom slugs. This keeps
    third-party skill packs visible while giving CORTEX-owned manifests a stable
    vocabulary.
    """
    slug = _slug(value)
    if not slug:
        return "uncategorized"
    return SKILL_CATEGORY_ALIASES.get(slug, slug)


def normalize_skill_classification(value: object) -> str:
    """Normalize skill lifecycle/tier labels to uppercase constants."""
    slug = _slug(value)
    if not slug:
        return ""
    return SKILL_CLASSIFICATION_ALIASES.get(slug, _constant(slug))


def normalize_danger_level(value: object) -> str:
    """Normalize manifest danger levels without silently hiding unknown labels."""
    slug = _slug(value)
    if not slug:
        return "NONE"
    return DANGER_LEVEL_ALIASES.get(slug, _constant(slug))


def category_for_agent_domain(domain_name: object) -> str:
    """Map an evolution AgentDomain name to a canonical skill category."""
    key = str(domain_name or "").strip().upper()
    return AGENT_DOMAIN_CATEGORY_MAP.get(key, "uncategorized")


def is_transcendent_skill(category: object, classification: object) -> bool:
    """Return whether taxonomy marks a skill as ontologically transcendent."""
    normalized_category = normalize_skill_category(category)
    normalized_classification = normalize_skill_classification(classification)
    if normalized_category in LEGACY_TRANSCENDENT_CATEGORIES:
        return True
    if "omega" in normalized_category:
        return True
    return normalized_classification == "TRANSCENDENT"
