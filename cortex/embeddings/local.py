# [C5-REAL] Exergy-Maximized

from __future__ import annotations

import hashlib
import logging
import math
import os
import sys
import threading
from typing import cast

EMBEDDING_DIM = 384
DEFAULT_EMBEDDING_MODEL = "all-MiniLM-L6-v2"
_DEVICE = os.environ.get("CORTEX_DEVICE", "auto")

logger = logging.getLogger("cortex.embeddings.local")


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def _hash_to_unit_vector(text: str, dimension: int = EMBEDDING_DIM) -> list[float]:
    seed = text.encode("utf-8")
    raw = bytearray()
    counter = 0
    while len(raw) < dimension:
        raw.extend(hashlib.sha256(seed + counter.to_bytes(4, "big")).digest())
        counter += 1

    vector = [((byte / 255.0) * 2.0) - 1.0 for byte in raw[:dimension]]
    return _normalize(vector)


def _resolve_device() -> str:
    package = sys.modules.get("cortex.embeddings")
    package_override = getattr(package, "_DEVICE", _DEVICE) if package is not None else _DEVICE
    device_override = os.environ.get("CORTEX_DEVICE", package_override)
    if device_override != "auto":
        return device_override

    try:
        import torch  # pyright: ignore[reportMissingImports]

        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
    except Exception as exc:
        logger.warning("Suppressed exception: %s", exc)

    return "cpu"


class LocalEmbedder:
    """SentenceTransformer-backed embedder with deterministic offline fallback."""

    _model = None
    _model_lock = threading.Lock()
    _model_name: str | None = None
    _using_fallback = False

    def __init__(self, model_name: str | None = None, device: str | None = None) -> None:
        self._model_name_override = model_name
        self._device = device or _resolve_device()

    @classmethod
    def _resolve_model_name(cls, override: str | None = None) -> str:
        if override:
            return override
        return os.environ.get("CORTEX_EMBEDDINGS_MODEL", DEFAULT_EMBEDDING_MODEL)

    @classmethod
    def _load_model(cls, model_name: str, device: str):
        if os.environ.get("CORTEX_NO_EMBED") == "1":
            cls._using_fallback = True
            logger.warning("CORTEX_NO_EMBED=1 set; using deterministic fallback embeddings")
            return None

        if cls._using_fallback and cls._model_name == model_name:
            return None

        with cls._model_lock:
            if cls._model is not None and cls._model_name == model_name:
                return cls._model
            if cls._using_fallback and cls._model_name == model_name:
                return None

            try:
                import platform

                from sentence_transformers import (
                    SentenceTransformer,  # pyright: ignore[reportMissingImports]
                )

                # Idea #6: ONNX INT8 Quantization
                # Achieve < 10ms embeddings by using the ONNX backend.
                # If we are on Apple Silicon (arm64), use the pre-quantized INT8 model for a 3-5x speedup.
                model_kwargs = {}
                is_arm64 = platform.machine() == "arm64" or platform.machine() == "aarch64"

                # Check if it's the default model to safely apply specialized INT8 files
                if model_name == DEFAULT_EMBEDDING_MODEL:
                    if is_arm64:
                        model_kwargs["file_name"] = "onnx/model_qint8_arm64.onnx"
                    else:
                        model_kwargs["file_name"] = (
                            "onnx/model_quint8_avx2.onnx"  # Fast fallback for x86_64
                        )

                cls._model = SentenceTransformer(
                    model_name, device=device, backend="onnx", model_kwargs=model_kwargs
                )
                cls._model_name = model_name
                cls._using_fallback = False
                logger.info(
                    "Local embedder loaded: %s [ONNX Backend] (device=%s, kwargs=%s)",
                    model_name,
                    device,
                    model_kwargs,
                )
            except Exception as err:
                cls._model = None
                cls._model_name = model_name
                cls._using_fallback = True
                logger.warning(
                    "Falling back to deterministic hash embeddings; model '%s' unavailable: %s",
                    model_name,
                    err,
                )

        return cls._model

    @property
    def dimension(self) -> int:
        return EMBEDDING_DIM

    @property
    def model_identity_hash(self) -> str:
        model_name = self._resolve_model_name(self._model_name_override)
        no_embed = os.environ.get("CORTEX_NO_EMBED", "0")
        payload = f"{model_name}:{EMBEDDING_DIM}:{self._device}:{no_embed}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        if isinstance(text, list):
            return self.embed_batch(text)
        return self._embed_one(text)

    def _embed_one(self, text: str) -> list[float]:
        if not text:
            return [0.0] * EMBEDDING_DIM

        model_name = self._resolve_model_name(self._model_name_override)
        model = self._load_model(model_name, self._device)
        if model is None:
            return _hash_to_unit_vector(text)

        encoded = model.encode(text, normalize_embeddings=True)
        return cast(list[float], [float(value) for value in encoded.tolist()])

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        if not texts:
            return []

        model_name = self._resolve_model_name(self._model_name_override)
        model = self._load_model(model_name, self._device)
        if model is None:
            return [_hash_to_unit_vector(text) for text in texts]

        encoded = model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
        )
        rows = encoded.tolist()
        return [[float(value) for value in row] for row in rows]
