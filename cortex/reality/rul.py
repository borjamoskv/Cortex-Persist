import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Literal

from cortex_rs import ingest_reality_claim

LEDGER_PATH = "cortex/data/reality_ledger.jsonl"

ClaimStatus = Literal["pending", "verified", "rejected", "unknown"]
ClaimDomain = Literal["llm", "api", "system", "performance", "pricing"]


@dataclass
class Source:
    url: str
    fetch_hash: str
    fetched_at_epoch_ms: int


@dataclass
class RealityClaim:
    statement: str
    domain: ClaimDomain
    sources: list[Source] = field(default_factory=list)
    claim_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at_epoch_ms: int = field(
        default_factory=lambda: int(time.time() * 1000)
    )
    trust_score: float = 0.0
    status: ClaimStatus = "pending"
    evidence_hashes: list[str] = field(default_factory=list)


def submit_claim(claim: RealityClaim) -> ClaimStatus:
    """
    Único punto de entrada para registrar un claim externo en el sistema.

    El claim es serializado, enviado al validador Rust,
    y el resultado escrito en el ledger append-only.

    No hay override. No hay bypass. No hay "trust me bro".
    """
    payload = json.dumps({
        **asdict(claim),
        # Rust espera sources como lista de objetos
        "sources": [asdict(s) for s in claim.sources],
    })

    now_ms = int(time.time() * 1000)

    status = ingest_reality_claim(LEDGER_PATH, payload, now_ms)
    return status
