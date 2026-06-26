# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""CORTEX Skills Module - Cognitive Graph Engine.

De un directorio de .md a un grafo cognitivo vivo.
Skills que se registran solos, declaran capacidades y se componen bajo demanda.
"""

from cortex_extensions.skills.registry import SkillManifest, SkillRegistry
from cortex_extensions.skills.router import SkillRouter
from cortex_extensions.skills.taxonomy import (
    ANTIGRAVITY_CORTEX_NEXUS_SKILL,
    ANTIGRAVITY_CORTEX_NEXUS_TAG,
    CANONICAL_DANGER_LEVELS,
    CANONICAL_SKILL_CATEGORIES,
    CANONICAL_SKILL_CLASSIFICATIONS,
    category_for_agent_domain,
    normalize_danger_level,
    normalize_skill_category,
    normalize_skill_classification,
)

__all__ = [
    "ANTIGRAVITY_CORTEX_NEXUS_SKILL",
    "ANTIGRAVITY_CORTEX_NEXUS_TAG",
    "CANONICAL_DANGER_LEVELS",
    "CANONICAL_SKILL_CATEGORIES",
    "CANONICAL_SKILL_CLASSIFICATIONS",
    "SkillManifest",
    "SkillRegistry",
    "SkillRouter",
    "category_for_agent_domain",
    "normalize_danger_level",
    "normalize_skill_category",
    "normalize_skill_classification",
]
