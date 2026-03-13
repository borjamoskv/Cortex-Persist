import logging

from mcp.server.fastmcp import FastMCP

from cortex.music_engine.orchestrator import GRAMMYOrchestrator, TrackContext

logger = logging.getLogger("cortex.mcp.music")

def register_music_tools(mcp: FastMCP):
    """Registers GRAMMY-Ω Music Engine tools."""

    @mcp.tool()
    async def music_create_album(title: str, concept: str) -> str:
        """
        Creates a new music album concept.
        
        Args:
            title: The title of the album.
            concept: The artistic concept or mood (e.g., 'Berlin Techno 2026').
        """
        orchestrator = GRAMMYOrchestrator()
        album = await orchestrator.create_album(title, concept)
        return f"Album '{title}' created with ID: {album.id}. Concept: {concept}"

    @mcp.tool()
    async def music_generate_track(album_id: str, track_title: str, adapter: str = "suno_v5") -> str:
        """
        Generates a new track for an album using the specified AI music adapter.
        
        Args:
            album_id: The ID of the album.
            track_title: The title of the track.
            adapter: suno_v5, udio_v4, or lyria_3.
        """
        # Note: In a real implementation, we would retrieve the orchestrator 
        # state from a persistent store or engine session.
        orchestrator = GRAMMYOrchestrator()
        
        # Mocking album context if not found in session for this stateless tool example
        # In actual CORTEX, this would be tied to a persistent project context.
        orchestrator.current_album = await orchestrator.create_album("Draft", "Concept")
        
        track = TrackContext(id=f"trk_{track_title.lower().replace(' ', '_')}", title=track_title)
        
        try:
            result = await orchestrator.run_pipeline(track, provider=adapter)
            return (
                f"Track '{track_title}' generated successfully!\n"
                f"GRI Score: {result.gri_score:.2f}\n"
                f"State: {result.state.value}\n"
                f"Stems: {list(result.stems.keys())}"
            )
        except Exception as e:
            logger.error(f"Failed to generate track: {e}")
            return f"Error generating track: {str(e)}"

    @mcp.tool()
    async def music_evaluate_gri(track_id: str, audio_path: str) -> str:
        """
        Evaluate the Grammy Readiness Index (GRI) of a track.
        """
        orchestrator = GRAMMYOrchestrator()
        track = TrackContext(id=track_id, title="Evaluation")
        # In a real scenario, we'd load the audio and stems here.
        
        try:
            evaluated_track = await orchestrator.evaluate_track_gri(track)
            return f"GRI Evaluation complete for {track_id}. Score: {evaluated_track.gri_score:.2f}"
        except Exception as e:
            return f"Evaluation failed: {str(e)}"
