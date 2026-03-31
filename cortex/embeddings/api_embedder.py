"""
CORTEX v5.0 — API-based Embedding Engine.

Uses external APIs (Gemini, OpenAI) for embeddings instead of
local ONNX. Useful for cloud deployments where you don't want
to ship a 80MB model.

Supports:
    - gemini:    text-embedding-004 (text-only, 768-dim)
    - gemini-v2: gemini-embedding-2-preview (multimodal, 3072-dim, MRL)
    - openai:    text-embedding-3-small (text-only, 384-dim)

Environment:
    CORTEX_EMBEDDINGS=api          (enable API mode)
    CORTEX_EMBEDDINGS_PROVIDER=gemini-v2  (or 'gemini', 'openai')
    CORTEX_EMBEDDINGS_DIM=768      (MRL dimension for gemini-v2)
    GEMINI_API_KEY=your-key        (for Gemini)
    OPENAI_API_KEY=your-key        (for OpenAI)
"""

from __future__ import annotations

import asyncio
import base64
import logging
import os
from typing import Any

import httpx

__all__ = ["PROVIDER_CONFIGS", "APIEmbedder", "get_provider_configs"]

logger = logging.getLogger("cortex.embeddings.api")

# ─── Gemini Embedding 2 Model Constant ───────────────────────────────
# Public preview name. Update when GA lands.
GEMINI_V2_MODEL = "gemini-embedding-2-preview"

# ─── Hardcoded Fallback Configs ──────────────────────────────────────
# Used when config/embedding_presets.json is unavailable.
_FALLBACK_CONFIGS: dict[str, dict[str, Any]] = {
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/"
        "text-embedding-004:embedContent",
        "dimension": 768,
        "native_dimension": 768,
        "env_key": "GEMINI_API_KEY",
        "batch_url": "https://generativelanguage.googleapis.com/v1beta/models/"
        "text-embedding-004:batchEmbedContents",
        "supports_multimodal": False,
        "supports_mrl": False,
    },
    "gemini-v2": {
        "url": f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_V2_MODEL}:embedContent",
        "dimension": 3072,
        "native_dimension": 3072,
        "env_key": "GEMINI_API_KEY",
        "batch_url": f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_V2_MODEL}:batchEmbedContents",
        "supports_multimodal": True,
        "supports_mrl": True,
        "mrl_dimensions": [256, 512, 768, 1536, 3072],
    },
    "openai": {
        "url": "https://api.openai.com/v1/embeddings",
        "model": "text-embedding-3-small",
        "dimension": 384,
        "native_dimension": 1536,
        "env_key": "OPENAI_API_KEY",
        "supports_multimodal": False,
        "supports_mrl": False,
    },
}

# ─── Provider Config Loader ─────────────────────────────────────────
_CONFIGS_CACHE: dict[str, dict[str, Any]] | None = None


def _convert_preset(name: str, preset: dict[str, Any]) -> dict[str, Any]:
    """Convert a JSON preset entry into the runtime config format."""
    model = preset.get("default_model", "")
    url_template = preset.get("url_template", "")
    batch_template = preset.get("batch_url_template", "")

    config: dict[str, Any] = {
        "url": (
            url_template.replace("{model}", model) if "{model}" in url_template else url_template
        ),
        "dimension": preset.get("native_dimension", 768),
        "native_dimension": preset.get("native_dimension", 768),
        "env_key": preset.get("env_key", ""),
        "supports_multimodal": preset.get("supports_multimodal", False),
        "supports_mrl": preset.get("supports_mrl", False),
    }

    if batch_template:
        config["batch_url"] = (
            batch_template.replace("{model}", model)
            if "{model}" in batch_template
            else batch_template
        )

    if preset.get("mrl_dimensions"):
        config["mrl_dimensions"] = preset["mrl_dimensions"]

    # OpenAI-style providers need the model name in the payload
    if "openai" in name or not url_template.startswith("https://generativelanguage"):
        config["model"] = model

    return config


def get_provider_configs() -> dict[str, dict[str, Any]]:
    """Load provider configs from presets file, falling back to hardcoded.

    Returns:
        Dict mapping provider name to runtime config.
    """
    global _CONFIGS_CACHE
    if _CONFIGS_CACHE is not None:
        return _CONFIGS_CACHE

    try:
        from cortex.embeddings._presets import load_embedding_presets

        presets = load_embedding_presets()
        if presets:
            _CONFIGS_CACHE = {
                name: _convert_preset(name, preset) for name, preset in presets.items()
            }
            logger.info("Loaded %d embedding providers from presets", len(_CONFIGS_CACHE))
            return _CONFIGS_CACHE
    except (ImportError, KeyError, OSError):
        logger.debug("Could not load embedding presets, using fallback configs")

    _CONFIGS_CACHE = _FALLBACK_CONFIGS.copy()
    return _CONFIGS_CACHE


# Public alias — lazy-loaded on first access
PROVIDER_CONFIGS = _FALLBACK_CONFIGS  # Static reference for import compat

# ─── Supported MIME types for multimodal ─────────────────────────────
SUPPORTED_IMAGE_MIMES = frozenset({"image/png", "image/jpeg", "image/webp", "image/gif"})
SUPPORTED_AUDIO_MIMES = frozenset({"audio/mp3", "audio/wav", "audio/aac", "audio/flac"})
SUPPORTED_VIDEO_MIMES = frozenset({"video/mp4", "video/mov", "video/mpeg"})
SUPPORTED_DOC_MIMES = frozenset({"application/pdf"})


class APIEmbedder:
    """Cloud-based embedding engine using external APIs.

    Drop-in replacement for LocalEmbedder. Same .embed() / .embed_batch()
    interface, but calls an API instead of running ONNX locally.

    For gemini-v2 provider, also supports multimodal embedding via
    embed_multimodal(), embed_image(), and embed_document().
    """

    def __init__(
        self,
        provider: str = "gemini",
        api_key: str | None = None,
        target_dimension: int = 768,
        task_type: str = "RETRIEVAL_DOCUMENT",
    ):
        configs = get_provider_configs()
        if provider not in configs:
            raise ValueError(f"Unknown provider '{provider}'. Supported: {list(configs.keys())}")

        self._provider = provider
        self._config = configs[provider]
        self._api_key = api_key or os.environ.get(self._config["env_key"], "")
        self._target_dim = target_dimension
        self._task_type = task_type
        self._client = httpx.AsyncClient(timeout=30.0)
        self._semaphore = asyncio.Semaphore(100)

        if not self._api_key:
            raise ValueError(
                f"{self._config['env_key']} is required for {provider} embeddings. "
                f"Set it as an environment variable."
            )

    # ─── Text Embedding (all providers) ───────────────────────────

    async def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Generate embedding(s). Accepts single text or list."""
        if isinstance(text, list):
            return await self.embed_batch(text)

        if not text or not str(text).strip():
            raise ValueError("text cannot be empty")

        if self._provider in ("gemini", "gemini-v2"):
            return await self._embed_gemini(str(text))
        elif self._provider == "openai":
            return await self._embed_openai(str(text))

        raise ValueError(f"No embed implementation for {self._provider}")

    async def embed_batch(self, texts: list[str], _batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []

        if self._provider == "openai":
            return await self._embed_openai_batch(texts)

        # Gemini: sequential for now (batch endpoint available)
        results = []
        for text in texts:
            emb = await self._embed_gemini(text)
            results.append(emb)
        return results

    # ─── Multimodal Embedding (gemini-v2 only) ────────────────────

    async def embed_multimodal(
        self,
        parts: list[dict[str, Any]],
        task_type: str | None = None,
    ) -> list[float]:
        """Generate embedding from multimodal content parts.

        Only supported for gemini-v2 provider. Accepts Gemini content
        parts format:
            - Text:  {"text": "some text"}
            - Image: {"inline_data": {"mime_type": "image/png", "data": "<b64>"}}
            - Audio: {"inline_data": {"mime_type": "audio/wav", "data": "<b64>"}}
            - Video: {"file_data": {"mime_type": "video/mp4", "file_uri": "..."}}
            - PDF:   {"inline_data": {"mime_type": "application/pdf", "data": "<b64>"}}

        Args:
            parts: List of Gemini content part dicts.
            task_type: Override default task_type for this call.

        Returns:
            Embedding vector as list of floats.
        """
        if not self._config.get("supports_multimodal"):
            raise ValueError(
                f"Provider '{self._provider}' does not support multimodal embeddings. "
                f"Use 'gemini-v2' provider."
            )

        if not parts:
            raise ValueError("parts list cannot be empty")

        effective_task_type = task_type or self._task_type
        url = f"{self._config['url']}?key={self._api_key}"

        payload: dict[str, Any] = {
            "content": {"parts": parts},
            "taskType": effective_task_type,
        }

        # MRL: request specific dimension if below native
        if self._config.get("supports_mrl") and (
            self._target_dim < self._config["native_dimension"]
        ):
            payload["outputDimensionality"] = self._target_dim

        async with self._semaphore:
            response = await self._client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        return data.get("embedding", {}).get("values", [])

    async def embed_image(
        self,
        image_bytes: bytes,
        mime_type: str = "image/png",
        task_type: str | None = None,
    ) -> list[float]:
        """Embed a single image. Convenience wrapper around embed_multimodal.

        Args:
            image_bytes: Raw image bytes (PNG, JPEG, WebP, GIF).
            mime_type: MIME type of the image.
            task_type: Override default task_type.

        Returns:
            Embedding vector.
        """
        if mime_type not in SUPPORTED_IMAGE_MIMES:
            raise ValueError(
                f"Unsupported image MIME type '{mime_type}'. "
                f"Supported: {sorted(SUPPORTED_IMAGE_MIMES)}"
            )

        b64_data = base64.b64encode(image_bytes).decode("ascii")
        parts = [{"inline_data": {"mime_type": mime_type, "data": b64_data}}]
        return await self.embed_multimodal(parts, task_type=task_type)

    async def embed_document(
        self,
        text: str,
        images: list[tuple[bytes, str]] | None = None,
        task_type: str | None = None,
    ) -> list[float]:
        """Embed a document with interleaved text and images.

        Creates a unified embedding in the same vector space,
        enabling cross-modal retrieval.

        Args:
            text: Document text content.
            images: Optional list of (image_bytes, mime_type) tuples.
            task_type: Override default task_type.

        Returns:
            Unified embedding vector.
        """
        parts: list[dict[str, Any]] = [{"text": text}]

        if images:
            for img_bytes, mime in images:
                if mime not in SUPPORTED_IMAGE_MIMES:
                    raise ValueError(
                        f"Unsupported image MIME type '{mime}'. "
                        f"Supported: {sorted(SUPPORTED_IMAGE_MIMES)}"
                    )
                b64_data = base64.b64encode(img_bytes).decode("ascii")
                parts.append({"inline_data": {"mime_type": mime, "data": b64_data}})

        return await self.embed_multimodal(parts, task_type=task_type)

    # ─── Gemini Implementation ────────────────────────────────────

    async def _embed_gemini(self, text: str) -> list[float]:
        """Call Gemini embedding API (text-embedding-004 or gemini-embedding-2)."""
        url = f"{self._config['url']}?key={self._api_key}"
        payload: dict[str, Any] = {
            "content": {"parts": [{"text": text}]},
            "taskType": self._task_type,
        }

        # MRL: request specific output dimension (gemini-v2 only)
        if self._config.get("supports_mrl") and (
            self._target_dim < self._config["native_dimension"]
        ):
            payload["outputDimensionality"] = self._target_dim

        async with self._semaphore:
            response = await self._client.post(url, json=payload)
        response.raise_for_status()

        data = response.json()
        values = data.get("embedding", {}).get("values", [])

        # Client-side truncation fallback (non-MRL providers)
        if not self._config.get("supports_mrl") and len(values) > self._target_dim:
            values = values[: self._target_dim]

        return values

    # ─── OpenAI Implementation ────────────────────────────────────

    async def _embed_openai(self, text: str) -> list[float]:
        """Call OpenAI embeddings API."""
        result = await self._embed_openai_batch([text])
        return result[0]

    async def _embed_openai_batch(self, texts: list[str]) -> list[list[float]]:
        """Call OpenAI embeddings API with batch support."""
        url = self._config["url"]
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "model": self._config["model"],
            "input": texts,
        }
        # OpenAI supports requesting specific dimensions
        if self._target_dim:
            payload["dimensions"] = self._target_dim

        async with self._semaphore:
            response = await self._client.post(url, headers=headers, json=payload)
        response.raise_for_status()

        data = response.json()
        embeddings = [item["embedding"] for item in data["data"]]
        return embeddings

    # ─── Properties ───────────────────────────────────────────────

    @property
    def dimension(self) -> int:
        """Return the embedding dimension."""
        return self._target_dim

    @property
    def provider(self) -> str:
        """Return the active provider name."""
        return self._provider

    @property
    def supports_multimodal(self) -> bool:
        """Return True if current provider supports multimodal input."""
        return bool(self._config.get("supports_multimodal"))

    @property
    def supports_mrl(self) -> bool:
        """Return True if current provider supports Matryoshka dimensions."""
        return bool(self._config.get("supports_mrl"))

    @property
    def native_dimension(self) -> int:
        """Return the provider's native (maximum) embedding dimension."""
        return self._config.get("native_dimension", self._target_dim)

    @property
    def task_type(self) -> str:
        """Return the default task type."""
        return self._task_type

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    def __repr__(self) -> str:
        mrl = f", mrl={self.supports_mrl}" if self.supports_mrl else ""
        mm = f", multimodal={self.supports_multimodal}" if self.supports_multimodal else ""
        return f"APIEmbedder(provider={self._provider!r}, dim={self._target_dim}{mrl}{mm})"
