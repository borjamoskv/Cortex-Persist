import asyncio
import logging
from cortex.extensions.music_engine.orchestrator import GRAMMYOrchestrator, TrackContext, TrackState

logging.basicConfig(level=logging.INFO)

async def main():
    orchestrator = GRAMMYOrchestrator()
    await orchestrator.initialize_album("Singularidad Sónica", "Una exploración del post-humanismo electrónico a través del techno granular y el bass design.")
    
    # Crear un track conceptual
    track_1 = TrackContext(
        id="trk-01",
        title="Event Horizon",
        bpm=128,
        key="G minor",
        state=TrackState.CONCEPT
    )
    
    print(f"--- Iniciando Ejecución Completa (Run Pipeline) para el track: {track_1.title} ---")
    result_track = await orchestrator.run_pipeline(track_1)
    
    print("\n[✔] Resultado de Pipeline:")
    print(f" - Estado Final: {result_track.state.value}")
    print(f" - Stems Separados: {list(result_track.stems.keys())}")
    print(f" - GRI (Grammy Readiness Index): {result_track.gri_score}")

if __name__ == "__main__":
    asyncio.run(main())
