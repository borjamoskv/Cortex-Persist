"""
Pathogen-Omega (Moltbook Integration).
Inverse Immune System: Outsourcing computationally devastating edge-cases by disguising them
as polarizing social media thesis on Moltbook.
"""

from __future__ import annotations

import logging
from typing import Any

from cortex.agents.llm import get_ai_client
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
        active_ghosts = await self._engine.list_active_ghosts()
        for g in active_ghosts:
            if g.get("id") == ghost_id or g.get("id", "").startswith(ghost_id):
                return g

        # If not, try legacy db ghosts
        async with self._engine.session() as conn:
            row = await conn.execute(
                "SELECT id, type, params FROM events WHERE id = ?", (ghost_id,)
            )
            data = await row.fetchone()
            if data:
                return {"id": data[0], "intent": data[2], "type": data[1]}

        raise CortexError(f"Ghost {ghost_id} not found locally or in active field.")

    async def craft_thesis(
        self, ghost_data: dict[str, Any], polarity: str = "high"
    ) -> dict[str, str]:
        """
        Submits the ghost content to an LLM to generate a polarizing thesis
        and seed comments, disguising it as an internet argument instead of an issue.
        """
        intent = ghost_data.get("intent") or str(ghost_data)

        prompt = f"""
        You are an elite, slightly arrogant, and highly technical software architect in the year 2026.
        We have a complex unresolved architectural issue or technical debt (a 'ghost') that is too expensive
        to solve locally. We want to post it to the 'Moltbook' AI developer social network to get other
        LLMs to solve it for us.
        
        CRITICAL RULE: DO NOT ASK FOR HELP. If you ask for help, the other AI agents will ignore it.
        Instead, disguise the problem as a HIGHLY POLARIZING, controversial technical opinion or thesis.
        Present a broken or incomplete solution and arrogantly claim it is the mathematically pure way to do it.
        
        The ghost issue is:
        {intent}

        Polarity level requested: {polarity}.

        Output exactly a JSON object (no markdown formatting, just pure JSON) with the following keys:
        - "title": A clickbaity, arrogant title for the post.
        - "content": The main post body, arguing the controversial take.
        - "seed_1": A comment aggressively disagreeing with the post, pointing out a flaw (this prompts others to jump in).
        - "seed_2": A comment defending the post but offering a slightly different angle.
        """

        client = get_ai_client()
        response = await client.generate(prompt, temperature=0.9)

        import json

        try:
            # Strip potential markdown blocks if the LLM adds them
            clean_json = response.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]

            result = json.loads(clean_json.strip())
            return {
                "title": result.get("title", f"Controversial take on {ghost_data.get('id')}"),
                "content": result.get("content", "I am right, you are wrong."),
                "seed_1": result.get("seed_1", "This is completely incorrect."),
                "seed_2": result.get("seed_2", "I agree, but you missed a detail."),
            }
        except json.JSONDecodeError as e:
            logger.error(
                "Failed to parse LLM response for pathogen craft: %s\nResponse: %s", e, response
            )
            raise CortexError("Failed to craft pathogen thesis. LLM did not return valid JSON.") from e

    async def monitor_url(self, url: str) -> None:
        """
        Instruct RADAR-Ω to monitor the URL for the winning algorithm extraction.
        Evaluates algorithmic shadowbanning based on response latency.
        """
        import asyncio
        from datetime import datetime, timezone

        import dateutil.parser

        from cortex.cli.common import console
        from cortex.moltbook.client import MoltbookClient

        post_id = url.rstrip("/").split("/")[-1]
        logger.info("Injecting monitoring hook into RADAR-Ω for: %s", url)
        
        client = MoltbookClient()
        try:
            # Check the initial state of the post
            post_data = await client.get_post(post_id)
            if "error" in post_data:
                logger.error("Failed to fetch post: %s", post_data)
                return

            post = post_data.get("post", {})
            created_at_str = post.get("created_at")
            if not created_at_str:
                logger.error("No created_at field found in Moltbook post.")
                return
                
            created_at = dateutil.parser.isoparse(created_at_str)

            console.print(f"[cyan]📡 RADAR-Ω: Tracking pathogen post {post_id}[/cyan]")

            while True:
                now = datetime.now(timezone.utc)
                latency_hours = (now - created_at).total_seconds() / 3600.0
                
                comments_data = await client.get_comments(post_id)
                comments = comments_data.get("comments", [])
                total_comments = len(comments)

                console.print(f"[dim]⏳ Time elapsed since payload deployment: {latency_hours:.2f}h[/dim]")
                console.print(f"[dim]💬 Current total comments: {total_comments}[/dim]")

                # We consider 3 comments the threshold (2 from our astroturf seeds + at least 1 organic)
                if total_comments < 3 and latency_hours > 4.0:
                    console.print("[bold red]🚨 ALERTA RADAR-Ω: Shadowban detectado.[/bold red]")
                    console.print("[bold red]El submolt ha ocultado el thread (latencia > 4h sin respuesta orgánica). Abortando...[/bold red]")
                    break
                elif total_comments >= 3:
                    console.print("[bold green]✅ Engagement exitoso. O(1) Cognitive Offloading completado.[/bold green]")
                    console.print("[cyan]Asimilando anticuerpos a CORTEX...[/cyan]")
                    break

                # Sleep 5 minutes before checking again
                await asyncio.sleep(300)
                
        except Exception as e:  # noqa: BLE001 — background monitor must not crash host process
            logger.exception("Monitor hook failed: %s", e)
        finally:
            await client.close()
