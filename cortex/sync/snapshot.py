"""Sync Engine: Snapshot Export."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from cortex.memory.temporal import now_iso
from cortex.sync.common import CORTEX_DIR

__all__ = ["export_snapshot"]

if TYPE_CHECKING:
    from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.sync")


def _safe_parse_tags(raw: str | None) -> list[str]:
    """Parse tags from DB, handling both JSON arrays and legacy comma-separated strings."""
    if not raw:
        return []
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        # Legacy format: "tag1,tag2,tag3" — split and clean
        return [t.strip() for t in raw.split(",") if t.strip()]


async def export_snapshot(
    engine: CortexEngine,
    out_path: Path | None = None,
    project_filter: str | None = None,
    min_confidence: float | None = None,
    fact_types: list[str] | None = None,
) -> Path:
    """Exporta un snapshot legible de toda la memoria activa de CORTEX.

    Genera un archivo markdown que el agente IA puede leer al inicio
    de cada conversación para tener contexto completo.

    Args:
        engine: Instancia de CortexEngine.
        out_path: Ruta de salida. Por defecto ~/.cortex/context-snapshot.md
        project_filter: Filtrar por un proyecto específico.
        min_confidence: Omitir facts con menor confianza (impacto).
        fact_types: Lista de fact_types permitidos (para aislar capas).

    Returns:
        Path del archivo generado.
    """
    if out_path is None:
        out_path = CORTEX_DIR / "context-snapshot.md"

    query = (
        "SELECT project, content, fact_type, tags, confidence FROM facts WHERE valid_until IS NULL "
    )
    params = []

    if project_filter:
        query += " AND project = ?"
        params.append(project_filter)
    if fact_types:
        query += f" AND fact_type IN ({','.join('?' * len(fact_types))})"
        params.extend(fact_types)
    if min_confidence is not None:
        query += " AND (confidence IS NOT NULL AND CAST(confidence AS REAL) >= ?)"
        params.append(min_confidence)

    query += " ORDER BY project, fact_type, id"

    by_project: dict[str, list] = {}
    total_facts = 0

    conn = await engine.get_conn()
    async with conn.execute(query, params) as cursor:
        while True:
            batch = await cursor.fetchmany(1000)
            if not batch:
                break
            for row in batch:
                project, content, fact_type, tags, confidence = row
                by_project.setdefault(project, []).append(
                    {
                        "content": content,
                        "type": fact_type,
                        "tags": _safe_parse_tags(tags),
                        "confidence": confidence,
                    }
                )
                total_facts += 1

    lines = [
        "# 🧠 CORTEX — Snapshot de Memoria",
        "",
        f"> Generado automáticamente: {now_iso()}",
        f"> Total: {total_facts} facts activos en {len(by_project)} proyectos",
        "",
    ]

    stats = await engine.stats()
    db_path = engine._db_path
    db_size_mb = db_path.stat().st_size / (1024 * 1024) if db_path.exists() else 0.0

    lines.extend(
        [
            "## Estado del Sistema",
            "",
            f"- **DB:** {db_path} ({db_size_mb:.2f} MB)",
            f"- **Facts activos:** {stats['active_facts']}",
            f"- **Proyectos:** {', '.join(stats['projects'])}",
            f"- **Tipos:** {', '.join(f'{t}: {c}' for t, c in stats['types'].items())}",
            "",
        ]
    )

    for project, facts in by_project.items():
        lines.extend(_format_project_section(project, facts))

    # ─── Tip del Día ─────────────────────────────────────────────────
    lines.extend(await _generate_tips_section(engine))

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")

    logger.info("Snapshot exportado a %s (%d facts)", out_path, total_facts)
    return out_path


def _format_project_section(project: str, facts: list[dict]) -> list[str]:
    """Formatea la sección de un proyecto para el snapshot."""
    display_name = project.replace("__", "").upper() if project.startswith("__") else project
    lines = [f"## {display_name}", ""]

    by_type: dict[str, list] = {}
    for f in facts:
        by_type.setdefault(f["type"], []).append(f)

    for ftype, type_facts in by_type.items():
        if ftype in ("axiom", "ghost", "error", "core_rules", "meta_learning"):
            lines.append(f"### {ftype.capitalize()} ({len(type_facts)})")
            lines.append("")
            for f in type_facts:
                content = f["content"].replace("\n", " ")
                if len(content) > 500:
                    content = content[:497] + "..."
                lines.append(f"- {content}")
            lines.append("")
        else:
            search_cmd = f'cortex search \\"type:{ftype} project:{project}\\"'
            msg = (
                f"- **{ftype.capitalize()}**: {len(type_facts)} facts (Use `{search_cmd}` to read)"
            )
            lines.append(msg)

    lines.append("")
    return lines


async def _generate_tips_section(engine: CortexEngine) -> list[str]:
    """Generate a 'Tip del Día' section for the snapshot with 3 random tips."""
    try:
        from cortex.cli.tips import TipsEngine

        tips_engine = TipsEngine(engine, include_dynamic=True, lang="es")
        lines = [
            "---",
            "",
            "## 💡 Tips del Día",
            "",
        ]
        seen: set[str] = set()
        for _ in range(3):
            tip = await tips_engine.random()
            if tip.id not in seen:
                seen.add(tip.id)
                lines.append(f"- **[{tip.category.value.upper()}]** {tip.content}")
        lines.append("")
        return lines
    except (ImportError, RuntimeError, OSError, ValueError):
        return []
