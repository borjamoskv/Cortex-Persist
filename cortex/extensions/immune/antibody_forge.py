"""
CORTEX v8.0 — Antibody Forge (Ω₅ Antifragile Synthesis).

Analyzes 'ghost' facts (errors) and synthesizes permanent antibodies (guards).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from cortex.engine import CortexEngine

logger = logging.getLogger("cortex.extensions.immune.antibody_forge")


class AntibodyForge:
    """Sovereign service for forging antibodies from failures."""

    def __init__(self, engine: CortexEngine | None = None) -> None:
        self.engine = engine or CortexEngine()
        self.storage_path = (
            "/Users/borjafernandezangulo/30_CORTEX"
            "/cortex/extensions/immune/antibodies.json"
        )

    async def metabolize_recent_ghosts(self, limit: int = 5) -> list[str]:
        """Query recent ghosts and forge antibodies for them."""
        ghosts = await self.engine.search(
            query="fact_type:ghost",
            limit=limit,
            sort="timestamp_desc"
        )
        
        forged_ids = []
        for ghost in ghosts:
            if "antibody_forged" in ghost.get("tags", []):
                continue

            antibody = await self.forge_from_ghost(ghost)
            if antibody:
                await self.persist_antibody(antibody)
                # Tag the ghost as processed
                await self.engine.update_fact(
                    ghost["id"], 
                    tags=ghost.get("tags", []) + ["antibody_forged"]
                )
                forged_ids.append(antibody["id"])
                
        return forged_ids

    async def forge_from_ghost(self, ghost: dict[str, Any]) -> dict[str, Any] | None:
        """Analyze a ghost fact and synthesize an antibody rule."""
        meta = ghost.get("meta", {})
        error_type = meta.get("error_type", "UnknownError")
        source = meta.get("source", "unknown")

        logger.info("Forge: Analyzing ghost %s (%s)", ghost["id"], error_type)

        # Logic for synthesis: For now, we use a template-based synthesis
        # In a full UltraThink implementation, this would call an LLM.
        # Here we simulate the synthesis result.
        antibody_id = f"ANTIBODY_{ghost['id']}"
        
        # Simple heuristic-based antibody:
        # If it's a TimeoutError from a specific source, we add a rate-limit or bypass rule.
        rule = {
            "id": antibody_id,
            "ghost_id": ghost["id"],
            "target_source": source,
            "target_error": error_type,
            "condition": "match_source_and_error",
            "action": "BLOCK",
            "justification": f"Antifragile Antibody forged from failure in {source} ({error_type})."
        }

        return rule

    async def persist_antibody(self, antibody: dict[str, Any]) -> None:
        """Save the antibody to the persistent store."""
        data = {}
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path) as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                pass
       
        data[antibody["id"]] = antibody
       
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)
           
        logger.info("Forge: Antibody %s persisted.", antibody["id"])
