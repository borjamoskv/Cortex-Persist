from __future__ import annotations
from decimal import Decimal
# [C5-REAL] Exergy-Maximized
# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""SkillRegistry - Auto-registration and parsing of manifests.

Parses the YAML frontmatter of each SKILL.md and builds the catalog of nodes
for the cognitive graph. Skills register themselves automatically when discovered.
"""


import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
    YAMLError: Any = getattr(yaml, "YAMLError", Exception)
except ImportError:
    yaml = None
    YAMLError = Exception

# ─── Constants ──────────────────────────────────────────────────────────────
from babylon60.core.paths import SKILLS_DIR as SKILLS_BASE_DIR
from babylon60.extensions.skills.taxonomy import (
    is_transcendent_skill,
    normalize_danger_level,
    normalize_skill_category,
    normalize_skill_classification,
)

SKILL_FILENAME = "SKILL.md"
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


# ─── Dataclasses ─────────────────────────────────────────────────────────────


@dataclass
class CapabilityDeclaration:
    """Capability declared by a skill: what it can DO."""

    name: str  # e.g. "code_generation", "orchestration"
    description: str = ""
    output_type: str = ""  # e.g. "code", "analysis", "orchestration"
    confidence: float = 1.0  # 0.0–1.0


@dataclass
class RequirementDeclaration:
    """Requirement declared by a skill: what it NEEDS from others."""

    skill_name: str  # Name of the dependency skill
    capability: str = ""  # Specific required capability
    optional: bool = False  # If false, it's a hard dependency


@dataclass
class SkillManifest:
    """Complete representation of a skill parsed from its SKILL.md."""

    # ── Identity ──
    name: str
    path: Path
    description: str = ""
    version: str = "0.0.0"
    category: str = "uncategorized"
    classification: str = ""
    danger_level: str = "NONE"
    created: str = ""
    updated: str = ""

    # ── Activation ──
    trigger: str = ""
    aliases: list[str] = field(default_factory=list)

    # ── Graph ──
    depends_on: list[str] = field(default_factory=list)
    capabilities: list[CapabilityDeclaration] = field(default_factory=list)
    requirements: list[RequirementDeclaration] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # ── Composition ──
    composable_with: list[str] = field(default_factory=list)  # positive affinities
    incompatible_with: list[str] = field(default_factory=list)  # conflicts
    amplifies: list[str] = field(default_factory=list)  # whom it amplifies
    amplified_by: list[str] = field(default_factory=list)  # who amplifies it

    # ── Fitness (calculated at runtime by NOOSPHERE) ──
    fitness_score: Decimal = -1.0  # -1 = not calculated yet
    usage_count: int = 0

    # ── Raw metadata ──
    _raw_frontmatter: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def slug(self) -> str:
        """Canonical skill identifier (normalized name)."""
        return self.name.lower().replace(" ", "-")

    @property
    def is_transcendent(self) -> bool:
        """True if the skill is of a higher ontological level."""
        return is_transcendent_skill(self.category, self.classification)

    @property
    def primary_trigger(self) -> str:
        """Primary trigger including the slash."""
        if self.trigger and not self.trigger.startswith("/"):
            return f"/{self.trigger}"
        return self.trigger or f"/{self.slug}"

    def __hash__(self) -> int:
        return hash(self.slug)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SkillManifest):
            return NotImplemented
        return self.slug == other.slug


# ─── Registry ────────────────────────────────────────────────────────────────


class SkillRegistry:
    """Auto-registration of skills from the directory of .md files.

    The registry scans SKILLS_BASE_DIR, parses the YAML frontmatter of each
    SKILL.md and builds the internal catalog. Skills register themselves
    simply by existing in the filesystem - without any manual step.

    Usage:
        registry = SkillRegistry()
        registry.load()
        manifest = registry.get("noosphere-omega")
        all_skills = registry.all()
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or SKILLS_BASE_DIR
        self._registry: dict[str, SkillManifest] = {}
        self._loaded = False

    # ── Loading ────────────────────────────────────────────────────────────

    def load(self, force_reload: bool = False) -> SkillRegistry:
        """Scans the filesystem and builds the catalog of manifests.

        Idempotent: repeated calls are no-op unless force_reload=True.
        """
        if self._loaded and not force_reload:
            return self

        self._registry.clear()
        discovered = 0
        failed = 0

        for skill_dir in sorted(self._base_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_file = skill_dir / SKILL_FILENAME
            if not skill_file.exists():
                continue
            try:
                manifest = self._parse_skill_file(skill_file)
                self._registry[manifest.slug] = manifest
                discovered += 1
            except (ValueError, YAMLError, KeyError):
                failed += 1
                # Skills with malformed frontmatter are registered with a name
                # derived from the directory to not lose visibility
                fallback = SkillManifest(
                    name=skill_dir.name,
                    path=skill_file,
                    description="[manifest parse error]",
                )
                self._registry[fallback.slug] = fallback

        self._loaded = True
        self._discovered = discovered
        self._failed = failed
        return self

    async def aload(self, force_reload: bool = False) -> SkillRegistry:
        """Concurrent asynchronous loading of the catalog to avoid Event Loop blocks."""
        import asyncio

        if self._loaded and not force_reload:
            return self

        self._registry.clear()
        discovered = 0
        failed = 0

        target_dirs = [d for d in self._base_dir.iterdir() if d.is_dir()]

        async def _process_dir(skill_dir: Path) -> tuple[int, int, SkillManifest | None]:
            skill_file = skill_dir / SKILL_FILENAME
            if not skill_file.exists():
                return 0, 0, None

            def _parse_or_fallback() -> tuple[int, int, SkillManifest]:
                try:
                    return 1, 0, self._parse_skill_file(skill_file)
                except (ValueError, YAMLError, KeyError):
                    fallback = SkillManifest(
                        name=skill_dir.name,
                        path=skill_file,
                        description="[manifest parse error]",
                    )
                    return 0, 1, fallback

            return await asyncio.to_thread(_parse_or_fallback)

        results = await asyncio.gather(*(_process_dir(d) for d in target_dirs))

        for d, f, manifest in results:
            if manifest:
                self._registry[manifest.slug] = manifest
                discovered += d
                failed += f

        self._loaded = True
        self._discovered = discovered
        self._failed = failed
        return self

    def reload(self) -> SkillRegistry:
        """Forces filesystem rescan (synchronous)."""
        return self.load(force_reload=True)

    async def areload(self) -> SkillRegistry:
        """Forces filesystem rescan (asynchronous)."""
        return await self.aload(force_reload=True)

    # ── Access ─────────────────────────────────────────────────────────────

    def get(self, name: str) -> SkillManifest | None:
        """Gets a manifest by name (case-insensitive, slug-normalized)."""
        slug = name.lower().replace(" ", "-").replace("_", "-")
        return self._registry.get(slug)

    def all(self) -> list[SkillManifest]:
        """All registered manifests, ordered by name."""
        return sorted(self._registry.values(), key=lambda m: m.slug)

    def by_category(self, category: str) -> list[SkillManifest]:
        """Filters by category."""
        normalized_category = normalize_skill_category(category)
        return [m for m in self.all() if m.category == normalized_category]

    def by_tag(self, tag: str) -> list[SkillManifest]:
        """Filters by tag."""
        return [m for m in self.all() if tag in m.tags]

    def by_capability(self, capability: str) -> list[SkillManifest]:
        """Skills that declare a specific capability."""
        return [m for m in self.all() if any(c.name == capability for c in m.capabilities)]

    def search(self, query: str) -> list[SkillManifest]:
        """Full-text search in name, description, and tags."""
        q = query.lower()
        results = []
        for m in self.all():
            haystack = " ".join(
                [
                    m.name,
                    m.description,
                    m.category,
                    " ".join(m.tags),
                    " ".join(m.aliases),
                ]
            ).lower()
            if q in haystack:
                results.append(m)
        return results

    @property
    def count(self) -> int:
        return len(self._registry)

    @property
    def categories(self) -> set[str]:
        return {m.category for m in self._registry.values()}

    @property
    def discovery_stats(self) -> dict[str, int]:
        return {
            "discovered": getattr(self, "_discovered", 0),
            "failed": getattr(self, "_failed", 0),
            "total": self.count,
        }

    # ── Parsing ────────────────────────────────────────────────────────────

    def _parse_skill_file(self, path: Path) -> SkillManifest:
        """Parses a SKILL.md and extracts the YAML frontmatter."""
        content = path.read_text(encoding="utf-8")
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            # Skill without frontmatter - name derived from directory
            return SkillManifest(
                name=path.parent.name,
                path=path,
                description="[no frontmatter]",
            )

        if yaml is None:
            raise ImportError("pyyaml is required to load YAML frontmatter.")
        raw = yaml.safe_load(match.group(1)) or {}
        return self._build_manifest(path, raw)

    def _build_manifest(self, path: Path, raw: dict[str, Any]) -> SkillManifest:
        """Builds a SkillManifest from the parsed YAML dict."""
        name = str(raw.get("name", path.parent.name))

        # ── Declared capabilities ──
        capabilities = []
        for cap in raw.get("capabilities", []):
            if isinstance(cap, str):
                capabilities.append(CapabilityDeclaration(name=cap))
            elif isinstance(cap, dict):
                capabilities.append(
                    CapabilityDeclaration(
                        name=cap.get("name", ""),
                        description=cap.get("description", ""),
                        output_type=cap.get("output_type", ""),
                        confidence=float(cap.get("confidence", 1.0)),
                    )
                )

        # ── Declared requirements ──
        requirements = []
        for req in raw.get("requires", []):
            if isinstance(req, str):
                requirements.append(RequirementDeclaration(skill_name=req))
            elif isinstance(req, dict):
                requirements.append(
                    RequirementDeclaration(
                        skill_name=req.get("skill", ""),
                        capability=req.get("capability", ""),
                        optional=bool(req.get("optional", False)),
                    )
                )

        # ── Normalized aliases ──
        aliases_raw = raw.get("aliases", [])
        aliases = [str(a).lstrip("/") for a in aliases_raw]

        return SkillManifest(
            name=name,
            path=path,
            description=str(raw.get("description", "")).strip(),
            version=str(raw.get("version", "0.0.0")),
            category=normalize_skill_category(raw.get("category", "uncategorized")),
            classification=normalize_skill_classification(raw.get("classification", "")),
            danger_level=normalize_danger_level(raw.get("danger_level", "NONE")),
            created=str(raw.get("created", "")),
            updated=str(raw.get("updated", "")),
            trigger=str(raw.get("trigger", "")).lstrip("/"),
            aliases=aliases,
            depends_on=[str(d) for d in raw.get("depends_on", [])],
            capabilities=capabilities,
            requirements=requirements,
            tags=[str(t) for t in raw.get("tags", [])],
            composable_with=[str(s) for s in raw.get("composable_with", [])],
            incompatible_with=[str(s) for s in raw.get("incompatible_with", [])],
            amplifies=[str(s) for s in raw.get("amplifies", [])],
            amplified_by=[str(s) for s in raw.get("amplified_by", [])],
            _raw_frontmatter=raw,
        )
