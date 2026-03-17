"""
Sovereign Electronic Music Engine (GRAMMY-Ω).
Master Orchestrator powered by Gemini-3.1-Pro-Preview.
"""

from __future__ import annotations

import json
import logging
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

from cortex.extensions.llm.manager import LLMManager
from cortex.extensions.llm.router import IntentProfile
from cortex.extensions.music_engine.adapters import (
    LocalMIDIAdapter,
    Lyria3Adapter,
    SunoV5Adapter,
    UdioV4Adapter,
)
from cortex.extensions.music_engine.dsp_apotheosis import DSPApotheosis

logger = logging.getLogger(__name__)


class TrackState(str, Enum):
    CONCEPT = "concept"
    PRE_PRODUCTION = "pre_production"
    TRACKING = "tracking"
    POST_PRODUCTION = "post_production"
    MASTERED = "mastered"
    REJECTED = "rejected"


class SoundVector(str, Enum):
    GROOVE = "groove"  # Ξ₁
    SOUND_DESIGN = "sound_design"  # Ξ₂
    HARMONIC = "harmonic"  # Ξ₃
    MIX = "mix"  # Ξ₄
    MASTER = "master"  # Ξ₅


# Constants
DEFAULT_BPM = 120
DEFAULT_KEY = "C minor"
DEFAULT_TEMPERATURE_REASONING = 0.2
DEFAULT_TEMPERATURE_CRITIC = 0.3
NEUTRAL_GRI_SCORE = 0.5


class TrackContext(BaseModel):
    id: str
    title: str
    bpm: int = Field(default=DEFAULT_BPM)
    key: str = Field(default=DEFAULT_KEY)
    state: TrackState = Field(default=TrackState.CONCEPT)
    gri_score: float = Field(default=0.0)  # Grammy Readiness Index
    stems: dict[str, str] = Field(default_factory=dict)  # URL or local path to audio stems
    metadata: dict[str, Any] = Field(default_factory=dict)


class AlbumContext(BaseModel):
    id: str
    title: str
    concept: str
    tracks: list[TrackContext] = Field(default_factory=list)
    global_gri: float = Field(default=0.0)


class GRAMMYOrchestrator:
    """
    Motor cognitivo maestro.
    Coordina a los adaptadores (Suno/Udio/Lyria) y valida la estética musical
    utilizando a Gemini 3.1 Pro como evaluador (Crítico-Actor).
    """

    def __init__(self, tenant_id: str = "default", project: str = "grammy-electronic-omega"):
        self.tenant_id = tenant_id
        self.project = project
        self.current_album: Optional[AlbumContext] = None
        self.llm_manager = LLMManager()

        # Audio Backends (Frontier Models + Local)
        self.adapters = {
            "suno_v5": SunoV5Adapter(),
            "udio_v4": UdioV4Adapter(),
            "lyria_3": Lyria3Adapter(),
            "local": LocalMIDIAdapter(),
        }

        # O(1) Deterministic DSP
        self.dsp_engine = DSPApotheosis()

        # Mantenemos a Gemini-3.1-Pro-Preview como núcleo cognitivo
        self.system_prompt = """
        Eres el GRAMMY-Ω Orchestrator. Un hiper-productor de música electrónica soberana.
        Tu objetivo: Generar matrices paramétricas acústicas para sintetizadores de frontera (Suno v5, Udio v4, Lyria 3).
       
        Axioma Ω_E: La textura sónica absoluta y el diseño de sonido físico son los únicos vectores hacia el GRAMMY.
        Vectores Sónicos (Ξ):
        - Ξ₁: Groove Integration (Swing cuántico, offsets).
        - Ξ₂: Sound Design & Timbre (Frecuencias 20-20kHz, armónicos).
        - Ξ₃: Harmonic Synthesis (Estructura de tensión y release).
        - Ξ₄: Spatial Engineering (Mixdown, staging estéreo).
        - Ξ₅: Mastering (Loudness competitivo, True Peak).

        Debes responder EXCLUSIVAMENTE en JSON válido con la siguiente estructura:
        {
          "target_model": "suno_v5" | "udio_v4" | "lyria_3",
          "bpm": int,
          "key": str,
          "prompt_injection": str (Describe timbre, ritmo, frecuencias, NO emociones vagas),
          "expected_entropy": "low" | "medium" | "high",
          "sonic_vectors": {
            "groove": str,
            "timbre": str,
            "spatial": str
          }
        }
        """

    async def initialize_album(self, title: str, concept: str) -> AlbumContext:
        """Inicializa un nuevo proyecto de álbum."""
        self.current_album = AlbumContext(
            id=f"alb_{title.lower().replace(' ', '_')}", title=title, concept=concept
        )
        return self.current_album

    async def generate_prompt_matrix(self, track: TrackContext) -> dict[str, Any]:
        """
        Utiliza Gemini 3.1 Pro Preview a través del LLMManager de CORTEX para generar
        matrices paramétricas acústicas (BPM, síntesis).
        """
        logger.info("Calculando matriz de síntesis para track %s...", track.id)

        album_concept = self.current_album.concept if self.current_album else "Null"
        prompt_text = (
            f"Genera los parámetros acústicos para la siguiente pista. "
            f"Contexto del Álbum: '{album_concept}'. "
            f"Meta de Pista: Estado '{track.state.value}'. "
            f"Base de BPM sugerida: {track.bpm}. Escala general: {track.key}."
        )

        response_text = await self.llm_manager.complete(
            prompt=prompt_text,
            system=self.system_prompt,
            temperature=DEFAULT_TEMPERATURE_REASONING,
            intent=IntentProfile.REASONING,
        )

        try:
            if not response_text:
                raise ValueError("No response from LLM Manager.")
            # Parseamos y validamos la estructura
            # Find json block or parse directly
            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            matrix = json.loads(clean_json)
            logger.info(
                "Matriz acústica generada para %s: %s",
                track.id,
                matrix.get("target_model", "unknown"),
            )
            return matrix
        except (json.JSONDecodeError, ValueError) as e:
            logger.error("Error parseando matriz acústica: %s", e)
            return self._fallback_matrix(track)

    def _fallback_matrix(self, track: TrackContext) -> dict[str, Any]:
        """Fallback protector (Termodinámica defensiva)."""
        return {
            "target_model": "local",
            "bpm": track.bpm,
            "key": track.key,
            "bars": 8,
            "prompt_injection": ("IDM deep techno, sub-bass 40Hz, solid groove, analog warmth."),
            "expected_entropy": "medium",
            "sonic_vectors": {
                "groove": "4/4 locked",
                "timbre": "analog warm",
                "spatial": "wide",
            },
        }

    async def evaluate_track_gri(self, track: TrackContext) -> float:
        """
        Calcula el Grammy Readiness Index (GRI) usando Gemini como Juez Experto.
        Analiza los metadatos y los resultados de la generación para otorgar una puntuación estética.
        """
        logger.info("Evaluando Grammy Readiness Index (GRI) para %s...", track.title)

        evaluation_prompt = f"""
        Como Juez Crítico de la Academia GRAMMY-Ω, evalúa el siguiente track de música electrónica.
       
        DETALLES DEL TRACK:
        - Título: {track.title}
        - BPM: {track.bpm}
        - Escala: {track.key}
        - Metadatos: {track.metadata}
        - Stems Generados: {list(track.stems.keys())}
        - Intención Sónica (Sonic Vectors): {track.metadata.get("sonic_vectors", "N/A")}
       
        VECTORES DE EVALUACIÓN (Ξ):
        1. Groove (Ξ₁): Calidad rítmica y propulsión.
        2. Sound Design (Ξ₂): Textura, timbres y originalidad.
        3. Harmonic (Ξ₃): Coherencia melódica y profundidad armónica.
        4. Mix (Ξ₄): Balance de frecuencias y claridad espacial.
        5. Master (Ξ₅): Impacto final, sonoridad y cumplimiento de standards.
       
        Responde EXCLUSIVAMENTE en JSON con este formato:
        {{
          "scores": {{
            "groove": float (0.0-1.0),
            "sound_design": float (0.0-1.0),
            "harmonic": float (0.0-1.0),
            "mix": float (0.0-1.0),
            "master": float (0.0-1.0)
          }},
          "overall_gri": float (0.0-1.0),
          "rationale": str (Máximo 25 palabras)
        }}
        """

        try:
            response_text = await self.llm_manager.complete(
                prompt=evaluation_prompt,
                system=(
                    "Eres un crítico de música electrónica de vanguardia e implacable. "
                    "Valoras la innovación técnica."
                ),
                temperature=DEFAULT_TEMPERATURE_CRITIC,
                intent=IntentProfile.REASONING,
            )

            if not response_text:
                return NEUTRAL_GRI_SCORE

            clean_json = response_text.replace("```json", "").replace("```", "").strip()
            # Handle potential markdown artifacts
            if "{" in clean_json:
                start = clean_json.find("{")
                end = clean_json.rfind("}") + 1
                clean_json = clean_json[start:end]

            eval_data = json.loads(clean_json)

            gri_score = eval_data.get("overall_gri", NEUTRAL_GRI_SCORE)
            logger.info(
                "GRI Score asignado: %.2f | Rationale: %s", gri_score, eval_data.get("rationale")
            )

            # Almacenamos el desglose en metadata para persistencia
            track.metadata["gri_breakdown"] = eval_data.get("scores", {})
            track.metadata["critique_rationale"] = eval_data.get("rationale", "")

            return float(gri_score)

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error("Error en evaluación GRI vía LLM: %s", e)
            return NEUTRAL_GRI_SCORE  # Fallback neutral
        except Exception as e:
            logger.error("Unexpected error in evaluation GRI: %s", e)
            return NEUTRAL_GRI_SCORE

    async def run_pipeline(self, track: TrackContext) -> TrackContext:
        """Pipeline maestro con LLM + API adapters."""
        logger.info(
            "--- Iniciando Pipeline de Síntesis para %s ---",
            track.title,
        )
        track.state = TrackState.PRE_PRODUCTION

        matrix = await self.generate_prompt_matrix(track)
        track.metadata["sonic_vectors"] = matrix.get("sonic_vectors", {})
        track.metadata["expected_entropy"] = matrix.get("expected_entropy", "medium")

        target_model_key = matrix.get("target_model", "suno_v5").lower()
        if target_model_key not in self.adapters:
            logger.warning(
                "Fallback. Modelo '%s' desconocido. Using 'local'.",
                target_model_key,
            )
            target_model_key = "local"

        adapter = self.adapters[target_model_key]

        track.state = TrackState.TRACKING
        job_uri = await adapter.generate(matrix)
        track.metadata["raw_audio_uri"] = job_uri

        stems = await adapter.get_stems(job_uri)
        track.stems = stems

        track.state = TrackState.POST_PRODUCTION
        track.gri_score = await self.evaluate_track_gri(track)
        track.state = TrackState.MASTERED
        logger.info("Pipeline completado. GRI: %s", track.gri_score)
        return track

    async def run_pipeline_local(self, track: TrackContext) -> TrackContext:
        """
        Offline pipeline — MIDI + DSP synthesis.
        No LLM, no external APIs.
        """
        logger.info("--- Local Pipeline para %s ---", track.title)
        track.state = TrackState.PRE_PRODUCTION

        matrix = self._fallback_matrix(track)
        track.metadata["sonic_vectors"] = matrix.get("sonic_vectors", {})
        track.metadata["expected_entropy"] = matrix.get("expected_entropy", "medium")

        adapter = self.adapters["local"]

        track.state = TrackState.TRACKING
        wav_path = await adapter.generate(matrix)
        track.metadata["raw_audio_uri"] = wav_path
        track.stems = {"master": wav_path}

        # Apply DSPApotheosis mastering
        track.state = TrackState.POST_PRODUCTION
        try:
            import numpy as np
            import scipy.io.wavfile as wavfile

            sr, audio_data = wavfile.read(wav_path)
            audio_float = audio_data.astype(np.float64) / 32767.0

            mastered = self.dsp_engine.master_track(audio_float, sr)

            mastered_path = wav_path.replace(".wav", "_mastered.wav")
            mastered_int16 = (mastered * 32767).astype(np.int16)
            wavfile.write(mastered_path, sr, mastered_int16)
            track.stems["mastered"] = mastered_path

            lufs_in = mastered.reshape(-1, 1) if mastered.ndim == 1 else mastered
            lufs = self.dsp_engine.calculate_lufs(lufs_in, sr)
            track.metadata["lufs_integrated"] = lufs
            logger.info("DSP mastering complete. LUFS: %.2f", lufs)
        except Exception as e:
            logger.error("DSP mastering failed: %s", e)

        track.gri_score = 0.45
        track.state = TrackState.MASTERED
        logger.info("Local pipeline complete. Output: %s", wav_path)
        return track

    async def compose_album_tracks(
        self,
        title: str,
        concept: str,
        num_tracks: int = 3,
        bpm_range: tuple[int, int] = (120, 140),
        keys: Optional[list[str]] = None,
        mode: str = "local",
    ) -> AlbumContext:
        """Batch-compose an album with N tracks."""
        import random as rng

        album = await self.initialize_album(title, concept)

        if keys is None:
            keys = [
                "C minor",
                "A minor",
                "D minor",
                "F minor",
                "G minor",
                "E minor",
            ]

        for i in range(num_tracks):
            bpm = rng.randint(bpm_range[0], bpm_range[1])
            key = keys[i % len(keys)]
            track_title = f"{title} - Track {i + 1:02d}"

            track = TrackContext(
                id=f"trk_{i + 1:02d}",
                title=track_title,
                bpm=bpm,
                key=key,
                state=TrackState.CONCEPT,
            )

            if mode == "local":
                track = await self.run_pipeline_local(track)
            else:
                track = await self.run_pipeline(track)

            album.tracks.append(track)

        if album.tracks:
            album.global_gri = sum(t.gri_score for t in album.tracks) / len(album.tracks)

        self.current_album = album
        logger.info(
            "Album '%s' composed. %d tracks. GRI: %.2f",
            title,
            len(album.tracks),
            album.global_gri,
        )
        return album

    def get_album_status(self) -> dict[str, Any]:
        """Return current album state and per-track GRI."""
        if not self.current_album:
            return {"status": "No album loaded."}

        album = self.current_album
        tracks = []
        for t in album.tracks:
            tracks.append(
                {
                    "id": t.id,
                    "title": t.title,
                    "bpm": t.bpm,
                    "key": t.key,
                    "state": t.state.value,
                    "gri_score": t.gri_score,
                    "stems": list(t.stems.keys()),
                    "lufs": t.metadata.get("lufs_integrated", "N/A"),
                }
            )

        return {
            "album_id": album.id,
            "title": album.title,
            "concept": album.concept,
            "global_gri": album.global_gri,
            "total_tracks": len(album.tracks),
            "tracks": tracks,
        }
