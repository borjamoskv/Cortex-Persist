from __future__ import annotations

from typing import Protocol


class EmbeddingProvider(Protocol):
    name: str

    def is_available(self) -> bool: ...
    def embed(self, texts: list[str]) -> list[list[float]]: ...
