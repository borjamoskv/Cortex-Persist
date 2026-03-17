from __future__ import annotations

import json
import urllib.request


class RemoteEmbeddingProvider:
    name = "remote"

    def __init__(self, endpoint: str, timeout: float = 5.0) -> None:
        self.endpoint = endpoint
        self.timeout = timeout

    def is_available(self) -> bool:
        return bool(self.endpoint)

    def embed(self, texts: list[str]) -> list[list[float]]:
        payload = json.dumps({"texts": texts}).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["vectors"]
