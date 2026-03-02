"""
CORTEX v5.0 — Local Embedding Engine.

Uses sentence-transformers with ONNX Runtime for zero-network-dependency
semantic embeddings. Model auto-downloads on first use (~80MB).

Produces 384-dimensional vectors using all-MiniLM-L6-v2.
"""

from __future__ import annotations

import hashlib
import logging
import os
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("cortex.embeddings")

# Default model — compact, fast, good quality
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384
DEFAULT_CACHE_DIR = Path.home() / ".cortex" / "models"

# Configurable LRU cache size via env var (default 1024)
_CACHE_SIZE = int(os.environ.get("CORTEX_CACHE_SIZE", "1024"))


class LocalEmbedder:
    """Local embedding engine using sentence-transformers.

    Zero network dependencies after first model download.
    Typical latency: ~5-15ms per text on CPU.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        cache_dir: Path | None = None,
    ):
        self._model_name = model_name
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._model = None
        self._identity_hash: str | None = None

    def _ensure_model(self):
        """Lazy-load model on first use."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import SentenceTransformer

            logger.info("Loading embedding model: %s", self._model_name)
            self._model = SentenceTransformer(
                self._model_name,
                cache_folder=str(self._cache_dir),
            )
            logger.info("Model loaded. Dimension: %d", EMBEDDING_DIM)
        except ImportError as exc:
            raise RuntimeError(
                "sentence-transformers not installed. "
                "Run: pip install sentence-transformers onnxruntime"
            ) from exc

    @lru_cache(maxsize=_CACHE_SIZE)  # noqa: B019
    def _embed_cached(self, text: str) -> list[float]:
        """Internal cached embedding for single strings."""
        self._ensure_model()
        embedding = self._model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Generate embedding for a single text or delegate list to batch."""
        if isinstance(text, list):
            return self.embed_batch(text)

        if not text or not str(text).strip():
            raise ValueError("text cannot be empty")

        return self._embed_cached(str(text))

    def embed_batch(self, texts: list[str], batch_size: int = 32) -> list[list[float]]:
        """Generate embeddings for multiple texts."""
        if not texts:
            return []

        for t in texts:
            if not t or not str(t).strip():
                raise ValueError("embedded text cannot be empty")

        self._ensure_model()
        embeddings = self._model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=batch_size,
            show_progress_bar=len(texts) > 50,
        )
        return [e.tolist() for e in embeddings]

    def embed_batch_chunked(
        self,
        texts: list[str],
        chunk_size: int = 50,
        batch_size: int = 32,
    ) -> list[list[float]]:
        """WAL-aware batch embedding for swarm workloads.

        Processes texts in chunks to prevent SQLite WAL bloat when
        many agents generate embeddings simultaneously. Each chunk
        produces embeddings that can be flushed to DB independently.

        Args:
            texts: List of texts to embed.
            chunk_size: Number of texts per chunk (default 50).
            batch_size: Internal batch size for the model (default 32).

        Yields semantically identical results to embed_batch but
        allows the caller to commit between chunks.
        """
        if not texts:
            return []

        all_embeddings: list[list[float]] = []
        total_chunks = (len(texts) + chunk_size - 1) // chunk_size

        for i in range(0, len(texts), chunk_size):
            chunk = texts[i : i + chunk_size]
            chunk_num = i // chunk_size + 1
            logger.debug(
                "Embedding chunk %d/%d (%d texts)",
                chunk_num,
                total_chunks,
                len(chunk),
            )
            chunk_embeddings = self.embed_batch(chunk, batch_size=batch_size)
            all_embeddings.extend(chunk_embeddings)

        return all_embeddings

    @property
    def dimension(self) -> int:
        """Embedding dimension (384 for all-MiniLM-L6-v2)."""
        return EMBEDDING_DIM

    @property
    def model_identity_hash(self) -> str:
        """Deterministic SHA-256 hash of the embedding model identity.

        Computed from model_name + config file content (if local).
        Used to version TopologicalAnchors — if this hash changes,
        all reference signatures must be recalculated in cold mode.

        Cached after first computation (model is immutable during process lifetime).
        """
        if self._identity_hash is not None:
            return self._identity_hash

        h = hashlib.sha256()
        h.update(self._model_name.encode("utf-8"))

        # If model is loaded locally, incorporate config file hash for
        # fine-tuning detection (same model_name, different weights)
        config_path = self._cache_dir / self._model_name.replace("/", "_") / "config.json"
        if config_path.exists():
            h.update(config_path.read_bytes())
        else:
            # Fallback: check HuggingFace cache structure
            hf_config = self._cache_dir / ("models--" + self._model_name.replace("/", "--"))
            if hf_config.exists():
                # Hash the snapshot ref for version pinning
                refs_dir = hf_config / "refs"
                if refs_dir.exists():
                    for ref_file in sorted(refs_dir.iterdir()):
                        h.update(ref_file.read_bytes())

        self._identity_hash = h.hexdigest()
        return self._identity_hash
