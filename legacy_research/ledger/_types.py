# [C5-REAL] Exergy-Maximized
from typing import Any, Protocol


class PublicVerifierProtocol(Protocol):
    errors: list[str]
    warnings: list[str]
    events: list[dict[str, Any]]
    checkpoints: list[dict[str, Any]]
    key_registry: dict[str, Any] | None
    key_index: dict[str, dict[str, Any]]
    manifest: dict[str, Any] | None
    event_hashes: list[str]
    guarantees: dict[str, bool]
    paths: Any
