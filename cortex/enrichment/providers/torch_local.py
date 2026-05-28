from __future__ import annotations

import os
from typing import Any


class TorchEmbeddingProvider:
    name = "torch_local"

    def __init__(self, model: Any) -> None:
        self.model = model

    def is_available(self) -> bool:
        if os.getenv("CORTEX_NO_EMBED") == "1":
            return False
        return self.model is not None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.is_available():
            raise RuntimeError("TorchEmbeddingProvider unavailable")
        vectors = self.model.encode(texts)
        return [list(map(float, row)) for row in vectors]
