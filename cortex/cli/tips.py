"""
CORTEX v5.1 — TIPS System.

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
import json
import logging
import random
import sqlite3
import threading
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Final, NamedTuple

__all__ = ["TipCategory", "Tip", "TipsEngine"]

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.tips")

_ASSET_PATH: Final[Path] = Path(__file__).parent / "assets" / "tips.json"


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

_static_lock = threading.Lock()
_STATIC_TIPS_CACHE: list[Tip] | None = None


def _load_static_tips() -> list[Tip]:
    """Lazy-load static tips from disk. Thread-safe."""
    global _STATIC_TIPS_CACHE  # noqa: PLW0603

    # Fast-path: already loaded.
    if _STATIC_TIPS_CACHE is not None:
        return _STATIC_TIPS_CACHE

    with _static_lock:
        # Double-check after acquiring lock.
        if _STATIC_TIPS_CACHE is not None:
            return _STATIC_TIPS_CACHE

        if not _ASSET_PATH.exists():
            logger.error("Sovereign Failure: Tips asset missing at %s", _ASSET_PATH)
            return []

        try:
            raw_data = json.loads(_ASSET_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.critical("TIPS: Failed to load static tips: %s", exc)
            return []

        tips: list[Tip] = []
        for raw in raw_data:
            cat_name = raw["category"]
            category = TipCategory(cat_name)
            for lang, text in raw["content"].items():
                tip_id = hashlib.md5(f"{cat_name}-{text}".encode()).hexdigest()[:8]  # noqa: S324
                tips.append(Tip(f"stat-{tip_id}", text, category, lang, "static"))

        _STATIC_TIPS_CACHE = tips
        logger.debug("TIPS: Loaded %d static tips from assets", len(tips))
        return _STATIC_TIPS_CACHE


# ─── Mining Spec ─────────────────────────────────────────────────────


class _MiningSpec(NamedTuple):
    """Configuration for a dynamic mining query."""

    fact_type: str
    id_prefix: str
    category: TipCategory
    label: str  # Human label for tip content
    limit_divisor: int  # max_dynamic // divisor = per-type limit


_MINING_SPECS: Final[tuple[_MiningSpec, ...]] = (
    _MiningSpec("decision", "dec", TipCategory.MEMORY, "Past decision", 1),
    _MiningSpec("error", "err", TipCategory.DEBUGGING, "Lesson learned", 2),
    _MiningSpec("bridge", "pat", TipCategory.ARCHITECTURE, "Pattern", 4),
)


# ─── Tips Engine ─────────────────────────────────────────────────────


class TipsEngine:
    """Contextual tips engine for CORTEX.

    Merges static tips with dynamic insights from CORTEX memory.
    Thread-safe, lightweight, and designed for real-time use.
    """

    __slots__ = (
        "_engine",
        "lang",
        "_include_dynamic",
        "_max_dynamic",
        "_cache_ttl",
        "_dynamic_cache",
        "_cache_ts",
        "_shown_ids",
    )

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
        """Get a random tip. Avoids repeats until all tips have been shown.

        Raises ``ValueError`` if no tips are available in the requested language.
        """
        pool = self._get_pool(lang=lang or self.lang)
        if not pool:
            raise ValueError(f"No tips available for lang='{lang or self.lang}'")

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
        static_tips = _load_static_tips()

        # Filter static pool by language
        static_pool = [t for t in static_tips if t.lang == target_lang]

        # Fallback to English if no tips in requested language
        if not static_pool and target_lang != "en":
            static_pool = [t for t in static_tips if t.lang == "en"]

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
            conn = self._engine._get_sync_conn()
            for spec in _MINING_SPECS:
                limit = max(1, self._max_dynamic // spec.limit_divisor)
                tips.extend(self._mine_facts(conn, spec, limit))
        except (sqlite3.Error, AttributeError, RuntimeError) as exc:
            logger.debug("Optional dynamic tips mining skipped: %s", exc)

        self._dynamic_cache = tips[: self._max_dynamic]

    @staticmethod
    def _mine_facts(
        conn: sqlite3.Connection,
        spec: _MiningSpec,
        limit: int,
    ) -> list[Tip]:
        """Generic fact miner — extracts tips from any fact_type."""
        from cortex.storage.classifier import classify_content

        tips: list[Tip] = []
        try:
            # Over-fetch by 3x to compensate for tips rejected by the Privacy Firewall
            rows = conn.execute(
                """
                SELECT id, project, content
                FROM facts
                WHERE fact_type = ?
                  AND deprecated = 0
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (spec.fact_type, limit * 3),
            ).fetchall()

            for fact_id, project, content in rows:
                if len(tips) >= limit:
                    break

                # 🛡️ PRIVACY FIREWALL (KETER-∞) 🛡️
                # Drop facts that contain secrets, API keys, or platform tokens
                if classify_content(content).is_sensitive:
                    continue

                tip_content = content[:200].rstrip()
                if len(content) > 200:
                    tip_content += "…"

                tips.append(
                    Tip(
                        id=f"{spec.id_prefix}-{fact_id}",
                        content=f"{spec.label} ({project}): {tip_content}",
                        category=spec.category,
                        source="memory",
                        project=project,
                        relevance=0.8,
                    )
                )
        except (sqlite3.OperationalError, ImportError) as exc:
            logger.debug(
                "Mining %s skipped (table missing or dependency err): %s", spec.fact_type, exc
            )
        return tips

    # ─── Convenience ─────────────────────────────────────────────

    def reset_shown(self) -> None:
        """Reset the shown-tips tracker."""
        self._shown_ids.clear()

    def invalidate_cache(self) -> None:
        """Force re-mining dynamic tips on next access."""
        self._cache_ts = 0.0
