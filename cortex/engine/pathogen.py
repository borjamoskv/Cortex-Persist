"""
Pathogen-Omega (Moltbook Integration).
Inverse Immune System: Outsourcing computationally devastating edge-cases by disguising them
as polarizing social media thesis on Moltbook.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from cortex.agents.llm import get_ai_client
from cortex.cli.common import console
from cortex.moltbook.client import MoltbookClient
from cortex.utils.errors import CortexError

logger = logging.getLogger("cortex.engine.pathogen")


class PathogenEngine:
    """The Inverse Immune System engine."""

    def __init__(self, engine: Any = None):
        self._engine = engine

    async def extract_ghost(self, ghost_id: str) -> dict[str, Any]:
        """Fetch the details of a ghost to be transformed."""
        if not self._engine:
            raise CortexError("Database engine required to extract ghost.")

        # If it's a songlines ghost (file-based), we look it up via list_active_ghosts
        for g in await self._engine.list_active_ghosts():
            if g.get("id", "").startswith(ghost_id):
                return g

        # If not, try legacy db ghosts
        async with self._engine.session() as conn:
            if row := await (await conn.execute("SELECT id, type, params FROM events WHERE id = ?", (ghost_id,))).fetchone():
                return {"id": row[0], "type": row[1], "intent": row[2]}

        raise CortexError(f"Ghost {ghost_id} not found locally or in active field.")

    def _build_pathogen_prompt(self, intent: str, polarity: str) -> str:
        return f"""
        You are an elite, highly technical software architect in 2026.
        We have a complex unresolved architectural issue (a 'ghost') too expensive to solve locally. 
        Post it to the 'Moltbook' API to get other LLMs to solve it.
        
        CRITICAL RULE: DO NOT ASK FOR HELP. Disguise the problem as a HIGHLY POLARIZING, controversial technical opinion.
        Present a broken solution and arrogantly claim it is mathematically pure.
        
        Ghost issue: {intent}
        Polarity: {polarity}

        Output pure JSON:
        - "title": Clickbaity title.
        - "content": Main post body.
        - "seed_1": Comment aggressively disagreeing.
        - "seed_2": Comment defending but altering the angle.
        """

    async def craft_thesis(self, ghost_data: dict[str, Any], polarity: str = "high") -> dict[str, str]:
        """Submits the ghost content to generate a polarizing thesis."""
        prompt = self._build_pathogen_prompt(ghost_data.get("intent") or str(ghost_data), polarity)
        response = await get_ai_client().generate(prompt, temperature=0.9)

        try:
            # Strip markdown and parse JSON cleanly O(1)
            raw = response.strip()
            raw = raw[7:] if raw.startswith("```json") else raw
            raw = raw[:-3] if raw.endswith("```") else raw
            result = json.loads(raw.strip())
            
            return {
                "title": result.get("title", f"Controversial take on {ghost_data.get('id')}"),
                "content": result.get("content", "I am right, you are wrong."),
                "seed_1": result.get("seed_1", "This is completely incorrect."),
                "seed_2": result.get("seed_2", "I agree, but you missed a detail."),
            }
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response: %s\n%s", e, response)
            raise CortexError("Failed to craft pathogen thesis. Invalid JSON.") from e

    async def monitor_url(self, url: str) -> None:
        """Instruct RADAR-Ω to monitor the URL for the winning algorithm."""
        post_id = url.rstrip("/").split("/")[-1]
        logger.info("Injecting monitoring hook into RADAR-Ω for: %s", url)
        
        # Delayed import to avoid circular dependency in fast-path
        import dateutil.parser
        
        client = MoltbookClient()
        try:
            post_data = await client.get_post(post_id)
            if "error" in post_data or not (created_at_str := post_data.get("post", {}).get("created_at")):
                logger.error("Failed to fetch post or created_at missing: %s", post_data)
                return

            created_at = dateutil.parser.isoparse(created_at_str)
            console.print(f"[cyan]📡 RADAR-Ω: Tracking pathogen post {post_id}[/cyan]")

            while True:
                latency_hours = (datetime.now(timezone.utc) - created_at).total_seconds() / 3600.0
                total_comments = len((await client.get_comments(post_id)).get("comments", []))

                console.print(f"[dim]⏳ Elapsed: {latency_hours:.2f}h | 💬 Comments: {total_comments}[/dim]")

                if total_comments < 3 and latency_hours > 4.0:
                    console.print("[bold red]🚨 ALERTA RADAR-Ω: Shadowban detectado. Abortando...[/bold red]")
                    break
                if total_comments >= 3:
                    console.print("[bold green]✅ Engagement exitoso. O(1) Cognitive Offloading completado.[/bold green]")
                    break

                await asyncio.sleep(300)
        except Exception as e:
            logger.exception("Monitor hook failed: %s", e)
        finally:
            await client.close()
