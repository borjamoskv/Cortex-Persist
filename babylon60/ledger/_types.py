# [C5-REAL] Exergy-Maximized
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from babylon60.ledger.public_verifier import VerificationInput


class PublicVerifierProtocol(Protocol):
    paths: "VerificationInput"
    errors: list[str]
    warnings: list[str]
    events: list[dict[str, Any]]
    checkpoints: list[dict[str, Any]]
    key_registry: dict[str, Any] | None
    key_index: dict[str, dict[str, Any]]
    manifest: dict[str, Any] | None
    event_hashes: list[str]
    guarantees: dict[str, bool]
