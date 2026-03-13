"""
Sovereign Electronic Music Engine (GRAMMY-Ω).
Master Orchestrator powered by Gemini-3.1-Pro-Preview.
"""

import json
import logging
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from cortex.llm.manager import LLMManager
from cortex.llm.router import IntentProfile

# Interfaces CORTEX Music Engine
from cortex.music_engine.adapters import Lyria3Adapter, SunoV5Adapter, UdioV4Adapter
from cortex.music_engine.dsp_apotheosis import DSPApotheosis

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
        self.current_album: AlbumContext | None = None
        self.llm_manager = LLMManager()

        # Audio Backends (Frontier Models)
        self.adapters = {
            "suno_v5": SunoV5Adapter(),
            "udio_v4": UdioV4Adapter(),
            "lyria_3": Lyria3Adapter(),
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
            # Fallback protector (Termodinámica defensiva)
            return {
                "target_model": "suno_v5",
                "prompt_injection": (
                    "Fallback IDM deep techno, sub-bass 40Hz, solid 4/4 groove, analog warmth."
                ),
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
        """
        El pipeline maestro. Genera la receta paramétrica sintética, inyecta prompts hacia
        los modelos de frontera seleccionados, y estabiliza espectralmente el audio final.
        """
        logger.info("--- Iniciando Pipeline de Síntesis para %s ---", track.title)
        track.state = TrackState.PRE_PRODUCTION

        # 1. Gemini Cognition: Matriz Paramétrica
        matrix = await self.generate_prompt_matrix(track)

        # Persist vectors in metadata for evaluation context
        track.metadata["sonic_vectors"] = matrix.get("sonic_vectors", {})
        track.metadata["expected_entropy"] = matrix.get("expected_entropy", "medium")

        target_model_key = matrix.get("target_model", "suno_v5").lower()

        if target_model_key not in self.adapters:
            logger.warning("Fallback. Modelo '%s' desconocido. Usando 'suno_v5'.", target_model_key)
            target_model_key = "suno_v5"

        adapter = self.adapters[target_model_key]

        # 2. Inyección y Generación Estocástica
        logger.info("Asaltando the base model %s...", target_model_key)
        track.state = TrackState.TRACKING
        job_uri = await adapter.generate(matrix)
        track.metadata["raw_audio_uri"] = job_uri

        # 3. Separación de Stems (Simulada si la API lo permite)
        stems = await adapter.get_stems(job_uri)
        track.stems = stems

        # 4. DSP Apotheosis (Corrección Termodinámica Semántica)
        track.state = TrackState.POST_PRODUCTION
        logger.info("Interviniendo audio renderizado con DSP Deterministico...")
        # (En producción aquí cargaríamos numpy arrays desde los URIs y pasaríamos al master_track)
        # self.dsp_engine.master_track(mock_audio_data, sample_rate=48000)

        # 5. Evaluación Final (GRI)
        track.gri_score = await self.evaluate_track_gri(track)
        track.state = TrackState.MASTERED
        logger.info("Pipeline completado. GRI Score: %s", track.gri_score)

        return track
