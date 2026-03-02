# This file is part of CORTEX.
# Licensed under the Apache License, Version 2.0.
# See top-level LICENSE file for details.
# Change Date: 2030-01-01 (Transitions to Apache 2.0)

"""SkillRegistry — Auto-registro y parsing de manifests.

Parsea el frontmatter YAML de cada SKILL.md y construye el catálogo de nodos
del grafo cognitivo. Los skills se registran solos al ser descubiertos.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# ─── Constantes ──────────────────────────────────────────────────────────────

SKILLS_BASE_DIR = Path.home() / ".gemini" / "antigravity" / "skills"
SKILL_FILENAME = "SKILL.md"
FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)


# ─── Dataclasses ─────────────────────────────────────────────────────────────


@dataclass
class CapabilityDeclaration:
    """Capacidad declarada por un skill: lo que puede HACER."""

    name: str                    # e.g. "code_generation", "orchestration"
    description: str = ""
    output_type: str = ""        # e.g. "code", "analysis", "orchestration"
    confidence: float = 1.0      # 0.0–1.0


@dataclass
class RequirementDeclaration:
    """Requisito declarado por un skill: lo que NECESITA de otros."""

    skill_name: str              # Nombre del skill dependencia
    capability: str = ""         # Capacidad específica requerida
    optional: bool = False       # Si es false, es hard dependency


@dataclass
class SkillManifest:
    """Representación completa de un skill parseado desde su SKILL.md."""

    # ── Identidad ──
    name: str
    path: Path
    description: str = ""
    version: str = "0.0.0"
    category: str = "uncategorized"
    classification: str = ""
    danger_level: str = "NONE"
    created: str = ""
    updated: str = ""

    # ── Activación ──
    trigger: str = ""
    aliases: list[str] = field(default_factory=list)

    # ── Grafo ──
    depends_on: list[str] = field(default_factory=list)
    capabilities: list[CapabilityDeclaration] = field(default_factory=list)
    requirements: list[RequirementDeclaration] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)

    # ── Composición ──
    composable_with: list[str] = field(default_factory=list)  # afinidades positivas
    incompatible_with: list[str] = field(default_factory=list)  # conflictos
    amplifies: list[str] = field(default_factory=list)  # a quién potencia
    amplified_by: list[str] = field(default_factory=list)  # quién le potencia

    # ── Fitness (calculado en runtime por NOOSPHERE) ──
    fitness_score: float = -1.0   # -1 = no calculado aún
    usage_count: int = 0

    # ── Metadata raw ──
    _raw_frontmatter: dict[str, Any] = field(default_factory=dict, repr=False)

    @property
    def slug(self) -> str:
        """Identificador canónico del skill (nombre normalizado)."""
        return self.name.lower().replace(" ", "-")

    @property
    def is_transcendent(self) -> bool:
        """True si el skill es de nivel ontológico superior."""
        transcendent_categories = {
            "transcendent-consciousness",
            "transcendent-manifold",
        }
        return self.category in transcendent_categories

    @property
    def primary_trigger(self) -> str:
        """Trigger primario incluyendo el slash."""
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
    """Auto-registro de skills desde el directorio de .md files.

    El registry escanea SKILLS_BASE_DIR, parsea el frontmatter YAML de cada
    SKILL.md y construye el catálogo interno. Los skills se «registran solos»
    simplemente existiendo en el filesystem — sin ningún paso manual.

    Uso:
        registry = SkillRegistry()
        registry.load()
        manifest = registry.get("noosphere-omega")
        all_skills = registry.all()
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base_dir = base_dir or SKILLS_BASE_DIR
        self._registry: dict[str, SkillManifest] = {}
        self._loaded = False

    # ── Carga ──────────────────────────────────────────────────────────────

    def load(self, force_reload: bool = False) -> "SkillRegistry":
        """Escanea el filesystem y construye el catálogo de manifests.

        Idempotente: llamadas repetidas son no-op salvo force_reload=True.
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
            except (ValueError, yaml.YAMLError, KeyError):
                failed += 1
                # Skills con frontmatter malformado se registran con nombre
                # derivado del directorio para no perder visibilidad
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

    def reload(self) -> "SkillRegistry":
        """Fuerza re-escaneo del filesystem."""
        return self.load(force_reload=True)

    # ── Acceso ─────────────────────────────────────────────────────────────

    def get(self, name: str) -> SkillManifest | None:
        """Obtiene un manifest por nombre (case-insensitive, slug-normalized)."""
        slug = name.lower().replace(" ", "-").replace("_", "-")
        return self._registry.get(slug)

    def all(self) -> list[SkillManifest]:
        """Todos los manifests registrados, ordenados por nombre."""
        return sorted(self._registry.values(), key=lambda m: m.slug)

    def by_category(self, category: str) -> list[SkillManifest]:
        """Filtra por categoría."""
        return [m for m in self.all() if m.category == category]

    def by_tag(self, tag: str) -> list[SkillManifest]:
        """Filtra por tag."""
        return [m for m in self.all() if tag in m.tags]

    def by_capability(self, capability: str) -> list[SkillManifest]:
        """Skills que declaran una capacidad específica."""
        return [
            m for m in self.all()
            if any(c.name == capability for c in m.capabilities)
        ]

    def search(self, query: str) -> list[SkillManifest]:
        """Búsqueda full-text en nombre, descripción y tags."""
        q = query.lower()
        results = []
        for m in self.all():
            haystack = " ".join([
                m.name,
                m.description,
                m.category,
                " ".join(m.tags),
                " ".join(m.aliases),
            ]).lower()
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
        """Parsea un SKILL.md y extrae el frontmatter YAML."""
        content = path.read_text(encoding="utf-8")
        match = FRONTMATTER_PATTERN.match(content)
        if not match:
            # Skill sin frontmatter — nombre derivado del directorio
            return SkillManifest(
                name=path.parent.name,
                path=path,
                description="[no frontmatter]",
            )

        raw = yaml.safe_load(match.group(1)) or {}
        return self._build_manifest(path, raw)

    def _build_manifest(self, path: Path, raw: dict[str, Any]) -> SkillManifest:
        """Construye un SkillManifest desde el dict YAML parseado."""
        name = str(raw.get("name", path.parent.name))

        # ── Capacidades declaradas ──
        capabilities = []
        for cap in raw.get("capabilities", []):
            if isinstance(cap, str):
                capabilities.append(CapabilityDeclaration(name=cap))
            elif isinstance(cap, dict):
                capabilities.append(CapabilityDeclaration(
                    name=cap.get("name", ""),
                    description=cap.get("description", ""),
                    output_type=cap.get("output_type", ""),
                    confidence=float(cap.get("confidence", 1.0)),
                ))

        # ── Requisitos declarados ──
        requirements = []
        for req in raw.get("requires", []):
            if isinstance(req, str):
                requirements.append(RequirementDeclaration(skill_name=req))
            elif isinstance(req, dict):
                requirements.append(RequirementDeclaration(
                    skill_name=req.get("skill", ""),
                    capability=req.get("capability", ""),
                    optional=bool(req.get("optional", False)),
                ))

        # ── Aliases normalizados ──
        aliases_raw = raw.get("aliases", [])
        aliases = [str(a).lstrip("/") for a in aliases_raw]

        return SkillManifest(
            name=name,
            path=path,
            description=str(raw.get("description", "")).strip(),
            version=str(raw.get("version", "0.0.0")),
            category=str(raw.get("category", "uncategorized")),
            classification=str(raw.get("classification", "")),
            danger_level=str(raw.get("danger_level", "NONE")),
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
