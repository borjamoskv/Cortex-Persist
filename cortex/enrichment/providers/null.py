from __future__ import annotations


class NullEmbeddingProvider:
    name = "null"

    def is_available(self) -> bool:
        return False

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("NullEmbeddingProvider: embeddings unavailable")
