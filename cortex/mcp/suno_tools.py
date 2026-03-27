import logging

from mcp.server.fastmcp import FastMCP

from cortex.engine import CortexEngine
from cortex.extensions.suno.actuator import SunoActuator

logger = logging.getLogger("cortex.mcp.suno")


def register_suno_tools(mcp: FastMCP, ctx):
    """Registers Suno-Omega Sovereign Actuator tools."""

    @mcp.tool()
    async def suno_generate_headless(
        lyrics: str, style: str, title: str, project: str = "music"
    ) -> str:
        """
        Sovereign headless generation of Suno tracks via CDP.
        Bypasses official APIs and persists the result in CORTEX Ledger.
        
        Args:
            lyrics: The lyrics string to insert into Suno.
            style: The music genre and descriptors.
            title: Title of the generated track.
            project: CORTEX project space.
        """
        await ctx.ensure_ready()
        logger.info("Initiating Suno Extraction for '%s'...", title)
        actuator = SunoActuator(port=9222)
        try:
            result = await actuator.generate_track(lyrics, style, title)
            if not result:
                return "❌ Headless generation failed or intercepted."
            async with ctx.pool.acquire() as conn:
                engine = CortexEngine(ctx.cfg.db_path, auto_embed=False)
                engine._conn = conn

                content = f"Track: {title} | Style: {style} | Lyrics length: {len(lyrics)}"
                fact_id = await engine.store(
                    project=project,
                    content=content,
                    fact_type="audio_track",
                    tags=["suno-omega", "headless-extraction"],
                    confidence="stated",
                    source="suno-headless-actuator",
                    parent_decision_id=None
                )

            return (
                f"✅ Suno Track '{title}' extracted successfully and stored in Ledger "
                f"as fact #{fact_id}. Taint: HEADLESS-CDP"
            )

        except Exception as e:
            logger.error("Error executing suno-omega actuator: %s", e)
            return f"❌ Error: {str(e)}"
