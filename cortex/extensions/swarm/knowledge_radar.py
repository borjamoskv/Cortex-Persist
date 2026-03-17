"""CORTEX v8.0 — Knowledge Radar (NightShift Target Discovery).

Discovers crystallization targets from 3 sovereign sources:
    1. Ghost Knowledge Gaps — CORTEX DB facts tagged 'knowledge_gap'/'auto_ghost'
    2. Curated Queue — YAML file with explicit URLs/queries
    3. Semantic Gap Detection — Projects with sparse L2 coverage

Axiom Derivations:
    Ω₂ (Entropic Asymmetry): Only targets that reduce uncertainty survive.
    Ω₃ (Byzantine Default): Every target is verified before pipeline entry.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

import yaml

logger = logging.getLogger("cortex.extensions.swarm.knowledge_radar")

# ── Default Paths ─────────────────────────────────────────────────────────

_DEFAULT_QUEUE_PATH = (
    Path(__file__).resolve().parents[2] / "cortex_iturria" / "nightshift_queue.yaml"
)


# ── Data Models ───────────────────────────────────────────────────────────


@dataclass
class CrystalTarget:
    """A target for autonomous knowledge crystallization."""

    target: str
    intent: str = "quick_read"
    priority: int = 5
    source: str = "curated"  # curated | ghost_gap | semantic_gap
    metadata: dict[str, Any] = field(default_factory=dict)
    processed: bool = False

    @property
    def sort_key(self) -> int:
        """Lower priority number = higher urgency."""
        return self.priority


# ── Source 1: Curated YAML Queue ──────────────────────────────────────────


def scan_curated_queue(queue_path: Optional[Union[Path, str]] = None) -> list[CrystalTarget]:
    """Read targets from the curated YAML queue file.

    Expected format:
        targets:
          - target: "https://example.com/docs"
            intent: "deep_learn"
            priority: 3
    """
    path = Path(queue_path) if queue_path else _DEFAULT_QUEUE_PATH

    if not path.exists():
        logger.info("📡 [RADAR] No curated queue at %s", path)
        return []

    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not raw or "targets" not in raw:
            return []

        targets: list[CrystalTarget] = []
        for entry in raw["targets"]:
            if not isinstance(entry, dict) or "target" not in entry:
                continue
            targets.append(
                CrystalTarget(
                    target=entry["target"],
                    intent=entry.get("intent", "quick_read"),
                    priority=entry.get("priority", 5),
                    source="curated",
                    metadata=entry.get("metadata", {}),
                )
            )

        logger.info("📡 [RADAR] Found %d curated targets", len(targets))
        return targets

    except (yaml.YAMLError, OSError, ValueError, TypeError) as e:
        logger.error("📡 [RADAR] Error reading queue %s: %s", path, e)
        return []


# ── Source 2: Ghost Knowledge Gaps ────────────────────────────────────────


async def scan_ghost_gaps(cortex_db: Any) -> list[CrystalTarget]:
    """Query CORTEX DB for ghosts tagged as knowledge gaps.

    Looks for facts with tags containing 'knowledge_gap' or 'auto_ghost'
    that haven't been resolved yet.
    """
    targets: list[CrystalTarget] = []

    try:
        # Query via the CortexEngine/DB interface
        if hasattr(cortex_db, "recall"):
            results = await cortex_db.recall(
                query="knowledge gap unresolved",
                limit=10,
                project="system",
            )
        elif hasattr(cortex_db, "query"):
            results = cortex_db.query(
                "SELECT id, content, project_id, metadata FROM facts "
                "WHERE (metadata LIKE '%knowledge_gap%' OR metadata LIKE '%auto_ghost%') "
                "AND metadata NOT LIKE '%nightshift_processed%' "
                "ORDER BY timestamp DESC LIMIT 10"
            )
        else:
            msg = (
                "Fallo en ciclo de descubrimiento: No compatible DB interface. "
                "CORTEX mantiene integridad vía ErrorGhostPipeline."
            )
            logger.critical(msg)
            return []

        for r in results or []:
            content = getattr(r, "content", "") if hasattr(r, "content") else str(r)

            # --- Ω₄ Aesthetic Cleaning (Parser) ---
            # 1. Try to extract URL from content
            url_match = re.search(r'https?://[^\s<>"]+|www\.[^\s<>"]+', content)
            if url_match:
                target_str = url_match.group(0)
            # 2. Try to parse as JSON if it looks like it
            elif content.strip().startswith("{"):
                try:
                    data = json.loads(content)
                    # Extract common fields
                    target_str = (
                        data.get("url") or data.get("target") or data.get("query") or content[:500]
                    )
                except json.JSONDecodeError:
                    target_str = content[:500]
            # 3. Strip artifact headers
            else:
                target_str = re.sub(r"═══.*?═══", "", content).strip()
                target_str = target_str[:500]

            targets.append(
                CrystalTarget(
                    target=target_str,
                    intent="search_gap",
                    priority=3,
                    source="ghost_gap",
                    metadata={"ghost_id": getattr(r, "id", "unknown")},
                )
            )

        logger.info("📡 [RADAR] Found %d ghost knowledge gaps", len(targets))

    except (ValueError, TypeError, RuntimeError, AttributeError) as e:
        logger.error("📡 [RADAR] Ghost scan failed: %s", e)

    return targets


# ── Source 3: Semantic Gap Detection ──────────────────────────────────────


async def scan_semantic_gaps(cortex_db: Any, min_facts: int = 5) -> list[CrystalTarget]:
    """Detect projects with sparse L2 coverage.

    If a project has fewer than `min_facts` facts, generate a search_gap
    target to enrich it.
    """
    targets: list[CrystalTarget] = []

    try:
        if hasattr(cortex_db, "query"):
            rows = cortex_db.query(
                "SELECT project_id, COUNT(*) as cnt FROM facts "
                "GROUP BY project_id HAVING cnt < ? "
                "ORDER BY cnt ASC LIMIT 5",
                (min_facts,),
            )
            for row in rows or []:
                project = (
                    row[0]
                    if isinstance(row, (list, tuple))
                    else getattr(row, "project_id", "unknown")
                )
                targets.append(
                    CrystalTarget(
                        target=f"best practices and architecture for {project}",
                        intent="search_gap",
                        priority=7,
                        source="semantic_gap",
                        metadata={"project": project},
                    )
                )

        logger.info("📡 [RADAR] Found %d semantic gaps", len(targets))

    except (ValueError, TypeError, RuntimeError, AttributeError) as e:
        logger.error("📡 [RADAR] Semantic gap scan failed: %s", e)

    return targets


# ── Merge & Prioritize ────────────────────────────────────────────────────


def deduplicate_targets(targets: list[CrystalTarget]) -> list[CrystalTarget]:
    """Remove duplicate targets based on normalized target string."""
    seen: set[str] = set()
    unique: list[CrystalTarget] = []

    for t in targets:
        key = t.target.strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(t)

    return unique


def merge_and_prioritize(
    *target_lists: list[CrystalTarget],
    max_n: int = 5,
) -> list[CrystalTarget]:
    """Merge multiple target lists, deduplicate, sort by priority, cap at max_n."""
    all_targets: list[CrystalTarget] = []
    for tl in target_lists:
        all_targets.extend(tl)

    unique = deduplicate_targets(all_targets)
    sorted_targets = sorted(unique, key=lambda t: t.sort_key)

    result = sorted_targets[:max_n]
    logger.info(
        "📡 [RADAR] Merged %d → %d unique → %d selected",
        len(all_targets),
        len(unique),
        len(result),
    )
    return result


# ── Public API ────────────────────────────────────────────────────────────


async def discover(
    cortex_db: Optional[Any] = None,
    max_targets: int = 5,
    queue_path: Optional[Union[Path, str]] = None,
) -> list[CrystalTarget]:
    """Full radar scan: curated + ghosts + semantic gaps → merged targets.

    Args:
        cortex_db: CORTEX database handle (optional for curated-only mode).
        max_targets: Maximum targets to return.
        queue_path: Override path to YAML queue file.

    Returns:
        List of CrystalTarget sorted by priority, capped at max_targets.
    """
    logger.info("📡 [RADAR] Starting full spectrum scan (max=%d)", max_targets)

    # Source 1: Always available
    curated = scan_curated_queue(queue_path)

    # Sources 2 & 3: Only if DB is available
    ghosts: list[CrystalTarget] = []
    semantic: list[CrystalTarget] = []

    if cortex_db is not None:
        ghosts = await scan_ghost_gaps(cortex_db)
        semantic = await scan_semantic_gaps(cortex_db)

    return merge_and_prioritize(curated, ghosts, semantic, max_n=max_targets)
