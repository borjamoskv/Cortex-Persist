import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = logging.getLogger("cortex.mcp.music")

_orchestrator = None


def _get_orchestrator():
    """Lazy singleton — GRAMMYOrchestrator is stateless, reuse it."""
    global _orchestrator
    if _orchestrator is None:
        from cortex.extensions.music_engine.orchestrator import (
            GRAMMYOrchestrator,
        )

        _orchestrator = GRAMMYOrchestrator()
    return _orchestrator


def register_music_tools(mcp: "FastMCP") -> None:  # type: ignore[type-arg]
    """Registers GRAMMY-Ω Music Engine tools."""

    @mcp.tool()
    async def music_create_album(title: str, concept: str) -> str:
        """Create a new music album concept.

        Args:
            title: The title of the album.
            concept: The artistic concept or mood
                (e.g., 'Berlin Techno 2026').
        """
        orchestrator = _get_orchestrator()
        album = await orchestrator.create_album(  # type: ignore[type-error]
            title, concept
        )
        return f"Album '{title}' created with ID: {album.id}. Concept: {concept}"

    @mcp.tool()
    async def music_generate_track(
        album_id: str,
        track_title: str,
        adapter: str = "suno_v5",
    ) -> str:
        """Generate a new track for an album using the specified
        AI music adapter.

        Args:
            album_id: The ID of the album.
            track_title: The title of the track.
            adapter: suno_v5, udio_v4, or lyria_3.
        """
        from cortex.extensions.music_engine.orchestrator import (
            TrackContext,
        )

        orchestrator = _get_orchestrator()
        orchestrator.current_album = await orchestrator.create_album(  # type: ignore[type-error]
            "Draft", "Concept"
        )

        track = TrackContext(
            id=f"trk_{track_title.lower().replace(' ', '_')}",
            title=track_title,
        )

        try:
            result = await orchestrator.run_pipeline(  # type: ignore[reportCallIssue]
                track, provider=adapter
            )
            return (
                f"Track '{track_title}' generated successfully!\n"
                f"GRI Score: {result.gri_score:.2f}\n"
                f"State: {result.state.value}\n"
                f"Stems: {list(result.stems.keys())}"
            )
        except Exception as e:
            logger.error("Failed to generate track: %s", e)
            return f"Error generating track: {e!s}"

    @mcp.tool()
    async def music_evaluate_gri(track_id: str, audio_path: str) -> str:
        """Evaluate the Grammy Readiness Index (GRI) of a track."""
        from cortex.extensions.music_engine.orchestrator import (
            TrackContext,
        )

        orchestrator = _get_orchestrator()
        track = TrackContext(id=track_id, title="Evaluation")

        try:
            evaluated = await orchestrator.evaluate_track_gri(track)
            return (
                f"GRI Evaluation complete for {track_id}. "
                f"Score: {evaluated.gri_score:.2f}"  # type: ignore[type-error]
            )
        except Exception as e:
            return f"Evaluation failed: {e!s}"
