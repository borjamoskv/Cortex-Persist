"""
Audio Adapters for CORTEX Music Engine.
Interfaces with external frontier models (Suno v5, Udio v4, Lyria 3).
"""

import abc
import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Constants
DEFAULT_TIMEOUT_SUNO = 60.0
DEFAULT_TIMEOUT_UDIO = 120.0
DEFAULT_TIMEOUT_LYRIA = 30.0


class AudioAdapter(abc.ABC):
    """Interfaz base para modelos generativos de audio."""

    @abc.abstractmethod
    async def generate(self, prompt_matrix: dict[str, Any]) -> str:
        """Genera audio basado en una matriz de parámetros y devuelve el URI/Path."""
        pass

    @abc.abstractmethod
    async def get_stems(self, job_id: str) -> dict[str, str]:
        """Aislar stems (vocals, bass, drums, other)."""
        pass

    @abc.abstractmethod
    async def close(self) -> None:
        """Cierra los recursos del cliente."""
        pass


class SunoV5Adapter(AudioAdapter):
    """Adaptador para Suno v5 (Especialización: Groove, Vocales, Coherencia Pop)."""

    def __init__(self, base_url: str = "https://api.suno.ai/v5"):
        self.api_key = os.environ.get("SUNO_API_KEY", "")
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=DEFAULT_TIMEOUT_SUNO,
        )

    async def generate(self, prompt_matrix: dict[str, Any]) -> str:
        logger.info(
            "Enviando matriz paramétrica a la API de Suno v5... BPM: %s", prompt_matrix.get("bpm")
        )
        # Inject sonic vectors for premium texture
        sonic_v = prompt_matrix.get("sonic_vectors", {})
        enhanced_prompt = prompt_matrix.get("prompt_injection", "")
        if sonic_v:
            vector_str = f" [Groove: {sonic_v.get('groove', '')}] [Timbre: {sonic_v.get('timbre', '')}] [Spatial: {sonic_v.get('spatial', '')}]"
            enhanced_prompt += vector_str

        payload = {
            "prompt": enhanced_prompt,
            "tags": prompt_matrix.get("genre", ""),
            "make_instrumental": False,
        }
        try:
            response = await self.client.post(f"{self.base_url}/generate", json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("id", "ari:cloud:suno:job:unknown")
        except httpx.HTTPError as e:
            logger.error("Suno API error during generation: %s", e)
            return "ari:cloud:suno:job:error"

    async def get_stems(self, job_id: str) -> dict[str, str]:
        logger.info("Polling Suno API for stem separation (%s)...", job_id)
        try:
            response = await self.client.get(f"{self.base_url}/jobs/{job_id}/stems")
            response.raise_for_status()
            data = response.json()
            return {
                "vocals": data.get("vocals_url", ""),
                "instrumental": data.get("instrumental_url", ""),
            }
        except httpx.HTTPError as e:
            logger.error("Suno API error fetching stems: %s", e)
            return {"vocals": "", "instrumental": ""}

    async def close(self) -> None:
        await self.client.aclose()


class UdioV4Adapter(AudioAdapter):
    """Adaptador para Udio v4 (Especialización: Inpainting, Texturas, 48kHz, Electrónica)."""

    def __init__(self, base_url: str = "https://api.udio.com/v4"):
        self.api_key = os.environ.get("UDIO_API_KEY", "")
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            timeout=DEFAULT_TIMEOUT_UDIO,
        )

    async def generate(self, prompt_matrix: dict[str, Any]) -> str:
        logger.info("Iniciando síntesis en Udio v4 API... Escala: %s", prompt_matrix.get("key"))
        # Inject sonic vectors for premium texture
        sonic_v = prompt_matrix.get("sonic_vectors", {})
        enhanced_prompt = prompt_matrix.get("prompt_injection", "")
        if sonic_v:
            vector_str = f" [Groove: {sonic_v.get('groove', '')}] [Timbre: {sonic_v.get('timbre', '')}] [Spatial: {sonic_v.get('spatial', '')}]"
            enhanced_prompt += vector_str

        payload = {
            "prompt": enhanced_prompt,
            "style": prompt_matrix.get("genre", ""),
            "duration": 30,
        }
        try:
            response = await self.client.post(f"{self.base_url}/generate", json=payload)
            response.raise_for_status()
            return response.json().get("job_id", "ari:cloud:udio:job:unknown")
        except httpx.HTTPError as e:
            logger.error("Udio API error during generation: %s", e)
            return "ari:cloud:udio:job:error"

    async def get_stems(self, job_id: str) -> dict[str, str]:
        logger.info("Extrayendo multitracks de Udio API (%s)...", job_id)
        try:
            response = await self.client.get(f"{self.base_url}/jobs/{job_id}")
            response.raise_for_status()
            data = response.json()
            return data.get("stems", {"vocals": "", "bass": "", "drums": "", "other": ""})
        except httpx.HTTPError as e:
            logger.error("Udio API error fetching stems: %s", e)
            return {}

    async def magic_edit(
        self, track_uri: str, segment: tuple[float, float], edit_prompt: str
    ) -> str:
        """Refinamiento local vía inpainting."""
        payload = {
            "track_uri": track_uri,
            "segment_start": segment[0],
            "segment_end": segment[1],
            "prompt": edit_prompt,
        }
        try:
            response = await self.client.post(f"{self.base_url}/inpaint", json=payload)
            response.raise_for_status()
            return response.json().get("job_id", "ari:cloud:udio:job:unknown")
        except httpx.HTTPError as e:
            logger.error("Udio API error during magic_edit: %s", e)
            return "ari:cloud:udio:job:error"

    async def close(self) -> None:
        await self.client.aclose()


class Lyria3Adapter(AudioAdapter):
    """Adaptador para Google DeepMind Lyria 3 (Especialización: B-Roll, Síntesis Corta, Image-to-Audio)."""

    def __init__(self):
        # Lyria generally uses GCP auth implicitly via service accounts
        self.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        self.client = httpx.AsyncClient(timeout=DEFAULT_TIMEOUT_LYRIA)

    async def generate(self, prompt_matrix: dict[str, Any]) -> str:
        logger.info("DeepMind Lyria 3: Sintetizando textura acústica O(1)...")
        if not self.project_id:
            logger.warning("GOOGLE_CLOUD_PROJECT missing for Lyria. Returning mock ID.")
            return "ari:cloud:lyria:job:5555"

        # Inject sonic vectors for premium texture
        sonic_v = prompt_matrix.get("sonic_vectors", {})
        enhanced_prompt = prompt_matrix.get("prompt_injection", "")
        if sonic_v:
            vector_str = f" [Sonic Profile: {sonic_v.get('groove', '')}, {sonic_v.get('timbre', '')}, {sonic_v.get('spatial', '')}]"
            enhanced_prompt += vector_str

        payload = {
            "prompt": enhanced_prompt,
            "parameters": {"bpm": prompt_matrix.get("bpm"), "key": prompt_matrix.get("key")},
        }
        try:
            url = f"https://us-central1-aiplatform.googleapis.com/v1/projects/{self.project_id}/locations/us-central1/publishers/google/models/lyria-3:predict"
            response = await self.client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("predictions", [{}])[0].get("id", "ari:cloud:lyria:job:unknown")
        except httpx.HTTPError as e:
            logger.error("Lyria API error during generation: %s", e)
            return "ari:cloud:lyria:job:error"

    async def get_stems(self, job_id: str) -> dict[str, str]:
        # Lyria might not support stem separation natively yet
        logger.warning("Lyria 3 no soporta separación de stems nativa. Retornando master.")
        return {"master": f"https://storage.googleapis.com/lyria-out/{job_id.split(':')[-1]}.wav"}

    async def close(self) -> None:
        await self.client.aclose()


class LocalMIDIAdapter(AudioAdapter):
    """Local MIDI → WAV adapter. No API keys needed."""

    def __init__(self):
        from cortex.music_engine.midi_engine import (
            generate_euclidean_groove,
            generate_harmonic_sequence,
            generate_texture_layer,
            render_sequence_to_wav,
        )

        self._groove = generate_euclidean_groove
        self._harmony = generate_harmonic_sequence
        self._texture = generate_texture_layer
        self._render = render_sequence_to_wav

    async def generate(self, params: dict) -> str:
        import os
        import uuid

        bpm = params.get("bpm", 128)
        bars = params.get("bars", 8)

        # Generate layers
        groove = self._groove(bpm=bpm, bars=bars)
        harmony = self._harmony(bpm=bpm, bars=bars)
        texture = self._texture(bpm=bpm, bars=bars)

        # Merge all tracks
        groove.tracks.extend(harmony.tracks)
        groove.tracks.extend(texture.tracks)

        # Render WAV
        out_dir = os.path.expanduser("~/.cortex/grammy/renders")
        os.makedirs(out_dir, exist_ok=True)
        fname = f"grammy_{uuid.uuid4().hex[:8]}.wav"
        wav_path = os.path.join(out_dir, fname)
        self._render(groove, wav_path)

        logger.info("Local generation complete: %s", wav_path)
        return wav_path

    async def get_stems(self, job_id: str) -> dict[str, str]:
        return {"master": job_id}

    async def close(self) -> None:
        pass
