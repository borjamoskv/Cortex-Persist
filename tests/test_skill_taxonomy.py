# [C5-REAL] Exergy-Maximized
from __future__ import annotations

from pathlib import Path

from legacy_research.extensions.skills.registry import SkillRegistry
from legacy_research.extensions.skills.taxonomy import (
    ANTIGRAVITY_CORTEX_NEXUS_SKILL,
    ANTIGRAVITY_CORTEX_NEXUS_TAG,
    category_for_agent_domain,
    normalize_danger_level,
    normalize_skill_category,
)


def _write_skill(base_dir: Path, dirname: str, frontmatter: str) -> None:
    skill_dir = base_dir / dirname
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(f"---\n{frontmatter}\n---\n# {dirname}\n", encoding="utf-8")


def test_registry_normalizes_antigravity_cortex_nexus_alias(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        ANTIGRAVITY_CORTEX_NEXUS_SKILL,
        """
name: singularity-nexus
description: Cross-project bridge between Antigravity and CORTEX
category: ANTIGRAVITYCORTEX
classification: operational
danger_level: p1
aliases:
  - /nexus-bridge
tags:
  - antigravity-cortex
""",
    )

    registry = SkillRegistry(tmp_path).load()
    manifest = registry.get("singularity-nexus")

    assert manifest is not None
    assert manifest.category == "communication"
    assert manifest.classification == "OPERATIONAL"
    assert manifest.danger_level == "HIGH"
    assert manifest.aliases == ["nexus-bridge"]
    assert ANTIGRAVITY_CORTEX_NEXUS_TAG in manifest.tags
    assert registry.by_category("nexus") == [manifest]


def test_taxonomy_preserves_unknown_categories_as_custom_slugs(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "lab-skill",
        """
name: lab-skill
description: Experimental custom category
category: Custom Lab
classification: alpha-preview
danger_level: med
""",
    )

    manifest = SkillRegistry(tmp_path).load().get("lab-skill")

    assert manifest is not None
    assert manifest.category == "custom-lab"
    assert manifest.classification == "ALPHA_PREVIEW"
    assert manifest.danger_level == "MEDIUM"


def test_transcendent_legacy_classification_remains_supported(tmp_path: Path) -> None:
    _write_skill(
        tmp_path,
        "omega-skill",
        """
name: omega-skill
description: Legacy transcendent skill
category: transcendent-consciousness
classification: transcendente
""",
    )

    manifest = SkillRegistry(tmp_path).load().get("omega-skill")

    assert manifest is not None
    assert manifest.classification == "TRANSCENDENT"
    assert manifest.is_transcendent is True


def test_agent_domain_category_map_keeps_communication_as_nexus() -> None:
    assert category_for_agent_domain("COMMUNICATION") == "communication"
    assert normalize_skill_category("Antigravity-CORTEX") == "communication"
    assert normalize_danger_level("P0") == "CRITICAL"
