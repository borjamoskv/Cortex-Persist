"""
CORTEX v4.3 — TIPS System.

Contextual tips engine that surfaces useful knowledge while the agent
thinks and executes. Combines a static knowledge bank with dynamic
insights mined from CORTEX memory (decisions, errors, patterns).

Usage:
    from cortex.tips import TipsEngine, Tip

    engine = TipsEngine()
    tip = engine.random()           # Random tip
    tip = engine.for_project("x")   # Project-scoped tip
    tips = engine.for_category("cortex")  # Category tips
"""

from __future__ import annotations

import hashlib
import logging
import random
import sqlite3
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.tips")


# ─── Models ──────────────────────────────────────────────────────────


class TipCategory(str, Enum):
    """Tip categories for filtering."""

    CORTEX = "cortex"
    WORKFLOW = "workflow"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    SECURITY = "security"
    DEBUGGING = "debugging"
    GIT = "git"
    PYTHON = "python"
    DESIGN = "design"
    MEMORY = "memory"
    META = "meta"


@dataclass(frozen=True, slots=True)
class Tip:
    """A single contextual tip."""

    id: str
    content: str
    category: TipCategory
    lang: str = "en"
    source: str = "static"  # "static" | "memory" | "dynamic"
    project: str | None = None
    relevance: float = 1.0

    def format(self, *, with_category: bool = True) -> str:
        """Format tip for display."""
        prefix = f"[{self.category.value}] " if with_category else ""
        return f"💡 {prefix}{self.content}"


# ─── Static Tips Bank ────────────────────────────────────────────────

_STATIC_TIPS: list[dict] = [
    # CORTEX
    {
        "content": {
            "en": "Use `cortex search` with natural language — it understands semantic meaning, not just keywords.",
            "es": "Usa `cortex search` con lenguaje natural; entiende el significado semántico, no solo palabras clave.",
        },
        "category": "cortex",
    },
    {
        "content": {
            "en": "CORTEX stores facts with temporal validity. Use `valid_from` and `valid_until` to time-scope knowledge.",
            "es": "CORTEX guarda hechos con validez temporal. Usa `valid_from` y `valid_until` para acotar el conocimiento en el tiempo.",
        },
        "category": "cortex",
    },
    {
        "content": {
            "en": "`cortex recall <project>` loads full project context instantly — perfect for resuming work.",
            "es": "`cortex recall <project>` carga el contexto completo del proyecto al instante: ideal para retomar el trabajo.",
        },
        "category": "cortex",
    },
    {
        "content": {
            "en": "The consensus system lets multiple agents vote on facts. Higher consensus = more trustworthy.",
            "es": "El sistema de consenso permite que varios agentes voten hechos. A mayor consenso, mayor confiabilidad.",
        },
        "category": "cortex",
    },
    {
        "content": {
            "en": "CORTEX auto-generates embeddings for every fact. Semantic search works out of the box.",
            "es": "CORTEX genera embeddings para cada hecho automáticamente. La búsqueda semántica funciona de serie.",
        },
        "category": "cortex",
    },
    {
        "content": {
            "en": "The episodic memory system records entire conversation sessions — like a persistent brain.",
            "es": "El sistema de memoria episódica registra sesiones enteras de conversación, como un cerebro persistente.",
        },
        "category": "cortex",
    },
    # WORKFLOW
    {
        "content": {
            "en": "Store decisions immediately after making them. Memory is cheaper than reconstruction.",
            "es": "Guarda las decisiones inmediatamente después de tomarlas. La memoria es más barata que la reconstrucción.",
        },
        "category": "workflow",
    },
    {
        "content": {
            "en": "Tag facts with confidence levels: C5 (confirmed) → C1 (hypothesis). Filter by certainty later.",
            "es": "Etiqueta hechos con niveles de confianza: C5 (confirmado) → C1 (hipótesis). Filtra por certeza después.",
        },
        "category": "workflow",
    },
    {
        "content": {
            "en": "Ghosts are unfinished work items. Use `cortex ghost list` to track what needs attention.",
            "es": "Los 'ghosts' son tareas inacabadas. Usa `cortex ghost list` para saber qué necesita atención.",
        },
        "category": "workflow",
    },
    {
        "content": {
            "en": "The MEJORAlo score should be > 70 before shipping. Run `/mejoralo` on any file to check.",
            "es": "La puntuación MEJORAlo debería ser > 70 antes de publicar. Ejecuta `/mejoralo` en cualquier archivo.",
        },
        "category": "workflow",
    },
    # PERFORMANCE
    {
        "content": {
            "en": "SQLite WAL mode is enabled by default. This gives you concurrent reads during writes.",
            "es": "El modo WAL de SQLite está activo por defecto. Permite lecturas concurrentes durante las escrituras.",
        },
        "category": "performance",
    },
    {
        "content": {
            "en": "The compactor merges redundant facts to keep the database lean. Run `cortex compact` periodically.",
            "es": "El compactador fusiona hechos redundantes para mantener la BD ligera. Ejecuta `cortex compact` a menudo.",
        },
        "category": "performance",
    },
    # SECURITY
    {
        "content": {
            "en": "Never hardcode API keys. CORTEX loads all secrets from environment variables.",
            "es": "Nunca pongas claves API a fuego. CORTEX carga todos los secretos desde variables de entorno.",
        },
        "category": "security",
    },
    {
        "content": {
            "en": "The crypto vault encrypts sensitive facts at rest using AES-GCM.",
            "es": "La bóveda criptográfica encripta hechos sensibles en reposo usando AES-GCM.",
        },
        "category": "security",
    },
    # PYTHON
    {
        "content": {
            "en": "Use `ruff` for linting — it's 10-100x faster than flake8 and covers more rules.",
            "es": "Usa `ruff` para el linter: es 10-100 veces más rápido que flake8 y cubre más reglas.",
        },
        "category": "python",
    },
    # DESIGN
    {
        "content": {
            "en": "Industrial Noir: #0A0A0A backgrounds, #CCFF00 accents, glassmorphism panels. The MOSKV aesthetic.",
            "es": "Industrial Noir: fondos #0A0A0A, acentos #CCFF00, paneles glassmorphism. La estética MOSKV.",
        },
        "category": "design",
    },
    # MEMORY
    {
        "content": {
            "en": "CORTEX persists 3 types at session close: decisions, errors, and ghosts. Never lose context.",
            "es": "CORTEX guarda 3 tipos al cerrar: decisiones, errores y 'ghosts'. No pierdas el contexto.",
        },
        "category": "memory",
    },
    # META
    {
        "content": {
            "en": "The 130/100 standard: meeting requirements is 100. Anticipating needs you didn't know you had is 130.",
            "es": "El estándar 130/100: cumplir requisitos es 100. Anticipar necesidades que no sabías que tenías es 130.",
        },
        "category": "meta",
    },
    {
        "content": {
            "en": "Every element must answer 'Why?'. If it has no purpose, delete it.",
            "es": "Cada elemento debe responder a '¿Por qué?'. Si no tiene propósito, bórralo.",
        },
        "category": "meta",
    },
]


def _build_static_tips() -> list[Tip]:
    """Convert raw tip dicts into Tip objects with stable IDs."""
    tips: list[Tip] = []
    for raw in _STATIC_TIPS:
        content_map = raw["content"]
        category = TipCategory(raw["category"])

        # Create a Tip object for each available language
        for lang, text in content_map.items():
            # Use English content for stable ID generation across languages if possible
            # but since we want unique IDs per (tip, lang) pair...
            tip_id = hashlib.md5(f"{raw['category']}-{text}".encode()).hexdigest()[:8]  # noqa: S324
            tips.append(
                Tip(
                    id=tip_id,
                    content=text,
                    category=category,
                    lang=lang,
                    source="static",
                )
            )
    return tips


STATIC_TIPS: list[Tip] = _build_static_tips()


# ─── Tips Engine ─────────────────────────────────────────────────────


class TipsEngine:
    """Contextual tips engine for CORTEX.

    Merges static tips with dynamic insights from CORTEX memory.
    Thread-safe, lightweight, and designed for real-time use.
    """

    def __init__(
        self,
        engine: CortexEngine | None = None,
        *,
        lang: str = "en",
        include_dynamic: bool = True,
        max_dynamic: int = 20,
        cache_ttl: float = 300.0,
    ) -> None:
        self._engine = engine
        self.lang = lang
        self._include_dynamic = include_dynamic and engine is not None
        self._max_dynamic = max_dynamic
        self._cache_ttl = cache_ttl
        self._dynamic_cache: list[Tip] = []
        self._cache_ts: float = 0.0
        self._shown_ids: set[str] = set()

    # ─── Public API ──────────────────────────────────────────────

    def random(self, *, lang: str | None = None, exclude_shown: bool = True) -> Tip:
        """Get a random tip. Avoids repeats until all tips have been shown."""
        pool = self._get_pool(lang=lang or self.lang)
        if exclude_shown:
            available = [t for t in pool if t.id not in self._shown_ids]
            if not available:
                self._shown_ids.clear()
                available = pool
        else:
            available = pool
        tip = random.choice(available)  # noqa: S311
        self._shown_ids.add(tip.id)
        return tip

    def for_category(
        self,
        category: str | TipCategory,
        *,
        lang: str | None = None,
        limit: int = 5,
    ) -> list[Tip]:
        """Get tips for a specific category."""
        target_lang = lang or self.lang
        if isinstance(category, str):
            try:
                category = TipCategory(category.lower())
            except ValueError:
                return []
        pool = self._get_pool(lang=target_lang)
        matching = [t for t in pool if t.category == category]
        random.shuffle(matching)
        return matching[:limit]

    def for_project(self, project: str, *, lang: str | None = None, limit: int = 3) -> list[Tip]:
        """Get tips scoped to a specific project.

        Combines project-specific dynamic tips with general tips.
        """
        target_lang = lang or self.lang
        pool = self._get_pool(lang=target_lang)
        project_tips = [t for t in pool if t.project == project]
        general_tips = [t for t in pool if t.project is None]

        # Prioritize project-specific, fill with general
        result = project_tips[:limit]
        remaining = limit - len(result)
        if remaining > 0:
            random.shuffle(general_tips)
            result.extend(general_tips[:remaining])
        return result

    def all_tips(self, *, lang: str | None = None) -> list[Tip]:
        """Return all available tips (static + dynamic)."""
        return self._get_pool(lang=lang or self.lang)

    @property
    def categories(self) -> list[str]:
        """List all available categories."""
        return [c.value for c in TipCategory]

    @property
    def count(self) -> int:
        """Total number of available tips in current language."""
        return len(self._get_pool(lang=self.lang))

    # ─── Dynamic Tips from CORTEX Memory ─────────────────────────

    def _get_pool(self, lang: str | None = None) -> list[Tip]:
        """Get combined static + dynamic tip pool filtered by language."""
        target_lang = lang or self.lang

        # Filter static pool by language
        static_pool = [t for t in STATIC_TIPS if t.lang == target_lang]

        # Fallback to English if no tips in requested language
        if not static_pool and target_lang != "en":
            static_pool = [t for t in STATIC_TIPS if t.lang == "en"]

        if not self._include_dynamic:
            return static_pool

        now = time.monotonic()
        if now - self._cache_ts > self._cache_ttl:
            self._refresh_dynamic()
            self._cache_ts = now

        return static_pool + self._dynamic_cache

    def _refresh_dynamic(self) -> None:
        """Mine CORTEX memory for dynamic tips."""
        if self._engine is None:
            self._dynamic_cache = []
            return

        tips: list[Tip] = []
        try:
            # En v4.x, el engine usa conexiones asíncronas o sesiones síncronas.
            # Accedemos a la conexión síncrona de compatibilidad si está disponible.
            conn = self._engine._get_sync_conn()
            tips.extend(self._mine_decisions(conn))
            tips.extend(self._mine_errors(conn))
            tips.extend(self._mine_patterns(conn))
        except (sqlite3.Error, AttributeError, RuntimeError) as exc:
            logger.debug("Optional dynamic tips mining skipped: %s", exc)

        self._dynamic_cache = tips[: self._max_dynamic]

    def _mine_decisions(self, conn: sqlite3.Connection) -> list[Tip]:
        """Extract tips from recent decisions."""
        tips: list[Tip] = []
        try:
            rows = conn.execute(
                """
                SELECT id, project, content
                FROM facts
                WHERE fact_type = 'decision'
                  AND deprecated = 0
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self._max_dynamic,),
            ).fetchall()
            for row in rows:
                fact_id, project, content = row[0], row[1], row[2]
                # Truncate long decisions into tip-friendly form
                tip_content = content[:200].rstrip()
                if len(content) > 200:
                    tip_content += "…"
                tips.append(
                    Tip(
                        id=f"dec-{fact_id}",
                        content=f"Past decision ({project}): {tip_content}",
                        category=TipCategory.MEMORY,
                        source="memory",
                        project=project,
                        relevance=0.8,
                    )
                )
        except sqlite3.OperationalError:
            pass  # Table may not exist in test DBs
        return tips

    def _mine_errors(self, conn: sqlite3.Connection) -> list[Tip]:
        """Extract 'did you know' tips from past errors (lessons learned)."""
        tips: list[Tip] = []
        try:
            rows = conn.execute(
                """
                SELECT id, project, content
                FROM facts
                WHERE fact_type = 'error'
                  AND deprecated = 0
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self._max_dynamic // 2,),
            ).fetchall()
            for row in rows:
                fact_id, project, content = row[0], row[1], row[2]
                tip_content = content[:200].rstrip()
                if len(content) > 200:
                    tip_content += "…"
                tips.append(
                    Tip(
                        id=f"err-{fact_id}",
                        content=f"Lesson learned ({project}): {tip_content}",
                        category=TipCategory.DEBUGGING,
                        source="memory",
                        project=project,
                        relevance=0.9,
                    )
                )
        except sqlite3.OperationalError:
            pass
        return tips

    def _mine_patterns(self, conn: sqlite3.Connection) -> list[Tip]:
        """Extract insights from frequently used patterns/bridges."""
        tips: list[Tip] = []
        try:
            rows = conn.execute(
                """
                SELECT id, project, content
                FROM facts
                WHERE fact_type = 'bridge'
                  AND deprecated = 0
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (self._max_dynamic // 4,),
            ).fetchall()
            for row in rows:
                fact_id, project, content = row[0], row[1], row[2]
                tip_content = content[:200].rstrip()
                if len(content) > 200:
                    tip_content += "…"
                tips.append(
                    Tip(
                        id=f"pat-{fact_id}",
                        content=f"Pattern ({project}): {tip_content}",
                        category=TipCategory.ARCHITECTURE,
                        source="memory",
                        project=project,
                        relevance=0.7,
                    )
                )
        except sqlite3.OperationalError:
            pass
        return tips

    # ─── Convenience ─────────────────────────────────────────────

    def reset_shown(self) -> None:
        """Reset the shown-tips tracker."""
        self._shown_ids.clear()

    def invalidate_cache(self) -> None:
        """Force re-mining dynamic tips on next access."""
        self._cache_ts = 0.0
