# [C5-REAL] Exergy-Maximized

import json
import logging
from pathlib import Path
from typing import Any

__all__ = ["export_gitops_memory", "sync_fact_to_repo"]

logger = logging.getLogger("cortex_extensions.sync.gitops")


def _locate_repo_root(project_name: str) -> Path | None:
    """Attempts to locate the project folder in standard paths."""
    game_dir = Path.home() / "game" / project_name
    if game_dir.exists() and game_dir.is_dir():
        return game_dir
    # More heuristics could be added here (e.g. search in ~/Developer, etc.)
    return None


def _get_cortex_dir(repo_path: Path) -> Path:
    cortex_dir = repo_path / ".cortex"
    cortex_dir.mkdir(parents=True, exist_ok=True)
    return cortex_dir


def _load_knowledge(json_path: Path) -> dict:
    if json_path.exists():
        try:
            return json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, ValueError, KeyError):
            return {"facts": []}
    return {"facts": []}


async def sync_fact_to_repo(
    project: str, fact_id: int, fact_data: dict[str, Any], action: str = "upsert"
) -> bool:
    """
    Synchronizes a fact (creation, edition, silent deletion) with the project's local JSON.
    action can be 'upsert' or 'deprecate'.
    It is assumed this is called *after* SQLite has committed (or if certain).
    """
    repo_path = _locate_repo_root(project)
    if not repo_path:
        return False

    try:
        cortex_dir = _get_cortex_dir(repo_path)
        json_path = cortex_dir / "knowledge.json"

        # 1. Load the current JSON or create a new one
        knowledge = _load_knowledge(json_path)

        facts_list = knowledge.get("facts", [])

        # 2. Modify the list
        existing_idx = next((i for i, f in enumerate(facts_list) if f.get("id") == fact_id), None)

        if action == "upsert":
            if existing_idx is not None:
                facts_list[existing_idx] = fact_data
            else:
                facts_list.append(fact_data)
        elif action == "deprecate" and existing_idx is not None:
            facts_list[existing_idx]["valid_until"] = fact_data.get("valid_until", "deprecated")
            if "meta" in fact_data:
                facts_list[existing_idx]["meta"] = fact_data["meta"]

        knowledge["facts"] = facts_list

        # 3. Write JSON atomically (or almost, sufficient for our local use case)
        json_path.write_text(json.dumps(knowledge, indent=2, ensure_ascii=False), encoding="utf-8")

        # 4. Render Markdown snapshot
        _render_snapshot(cortex_dir, facts_list, project)
        return True

    except (OSError, ValueError, KeyError) as e:
        logger.error("Failed to sync GitOps memory for %s: %s", project, e)
        return False


def _render_snapshot(cortex_dir: Path, facts_list: list[dict[str, Any]], project: str) -> None:
    """Generates a readable Markdown from the facts JSON."""
    md_path = cortex_dir / "context-snapshot.md"

    # Filter active and sort by descending date
    active_facts = [f for f in facts_list if not f.get("valid_until")]
    active_facts.sort(key=lambda x: x.get("created_at", ""), reverse=True)

    lines = [
        f"# CORTEX Snapshot: {project}",
        "",
        "> **Sovereign GitOps Memory**",
        "> Generated automatically from `knowledge.json`. Do not edit by hand.",
        "",
        f"Total active facts: **{len(active_facts)}**",
        "",
    ]

    # Group by type
    by_type = {}
    for fact in active_facts:
        ftype = fact.get("fact_type", "knowledge")
        by_type.setdefault(ftype, []).append(fact)

    for ftype, items in by_type.items():
        lines.append(f"## {ftype.upper()}")
        lines.append("")
        for fact in items:
            date_str = fact.get("created_at", "N/A")[:10]
            conf = fact.get("confidence", "stated")
            lines.append(f"### [#{fact.get('id')}] ({date_str}) - {conf.upper()}")
            lines.append(f"{fact.get('content')}")
            if fact.get("tags"):
                lines.append(f"*Tags: {', '.join(fact.get('tags'))}*")
            lines.append("")

    md_path.write_text("\n".join(lines), encoding="utf-8")


async def export_gitops_memory(engine, project: str) -> bool:
    """Regenerates the .cortex/ folder and the knowledge.json and context-snapshot.md files from SQLite."""
    repo_path = _locate_repo_root(project)
    if not repo_path:
        logger.error("Cannot export: project directory not found for %s", project)
        return False

    cortex_dir = _get_cortex_dir(repo_path)
    json_path = cortex_dir / "knowledge.json"

    try:
        facts = await engine.recall(project)
        import dataclasses

        facts_list = []
        for f in facts:
            fact_data = dataclasses.asdict(f)
            # rename id to match JSON format
            fact_data["id"] = fact_data.pop("fact_id", fact_data.get("id"))
            if fact_data.get("valid_from") and isinstance(fact_data["valid_from"], str):
                # Ensure date format
                fact_data["created_at"] = fact_data["valid_from"]
            facts_list.append(fact_data)

        knowledge = {"facts": facts_list}
        json_path.write_text(json.dumps(knowledge, indent=2, ensure_ascii=False), encoding="utf-8")
        _render_snapshot(cortex_dir, facts_list, project)
        return True
    except (OSError, ValueError, KeyError) as e:
        logger.error("Export fell down: %s", e)
        return False
