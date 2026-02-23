"""Sync System: Syncs system.json (knowledge/decisions) to CORTEX DB."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.sync.common import SyncResult, calculate_fact_diff, get_existing_contents

__all__ = ["sync_system"]

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync")


def _sync_fact_list(
    engine: CortexEngine,
    existing: set,
    candidates: list,
    fact_type: str,
    content_fn,
    tags_fn,
    result: SyncResult,
    confidence: str = "stated",
) -> None:
    """Sync a list of candidate facts to the DB, deduplicating against existing."""
    new_items = calculate_fact_diff(existing, candidates, content_fn)
    for content, item in new_items:
        try:
            engine.store_sync(
                project="__system__",
                content=content,
                fact_type=fact_type,
                tags=tags_fn(item),
                confidence=confidence,
                source="sync-agent-memory",
                valid_from=item.get("added") or item.get("date"),
                meta=item,
            )
            result.facts_synced += 1
            existing.add(content)
        except (OSError, ValueError, KeyError) as e:
            result.errors.append(f"Error system {fact_type}: {e}")


def sync_system(engine: CortexEngine, path: Path, result: SyncResult) -> None:
    """Sincroniza system.json — conocimiento global y decisiones."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        result.errors.append(f"Error leyendo system.json: {e}")
        return

    existing = get_existing_contents(engine, "__system__")

    # knowledge_global
    _sync_fact_list(
        engine,
        existing,
        data.get("knowledge_global", []),
        "knowledge",
        lambda x: x.get("content", str(x)),
        lambda x: ["sistema", x.get("topic", "general")],
        result,
        confidence="stated",
    )

    # decisions_global
    _sync_fact_list(
        engine,
        existing,
        data.get("decisions_global", []),
        "decision",
        lambda x: x.get("decision", str(x)),
        lambda x: ["sistema", "decision-global", x.get("topic", "")],
        result,
        confidence="verified",
    )

    # Ecosistema
    eco = data.get("ecosystem", {})
    if eco:
        eco_content = (
            f"Ecosistema: {eco.get('total_projects', '?')} proyectos | "
            f"Foco: {', '.join(eco.get('active_focus', []))} | "
            f"Diagnóstico: {eco.get('diagnosis', 'sin datos')}"
        )
        if eco_content not in existing:
            try:
                engine.store_sync(
                    project="__system__",
                    content=eco_content,
                    fact_type="knowledge",
                    tags=["sistema", "ecosistema"],
                    confidence="verified",
                    source="sync-agent-memory",
                    meta=eco,
                )
                result.facts_synced += 1
            except (OSError, ValueError, KeyError) as e:
                result.errors.append(f"Error ecosystem sync: {e}")
