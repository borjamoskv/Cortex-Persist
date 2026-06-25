import json
import time
import uuid
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from babylon60.math.babylon import Babylon60

import cortex_rs


@dataclass
class Source:
    url: str
    fetch_hash: str
    fetched_at_epoch_ms: int

@dataclass
class RealityClaim:
    statement: str
    domain: str
    sources: list[Source]
    claim_id: str = ""
    created_at_epoch_ms: int = 0
    trust_score: 'Babylon60 | None' = None
    status: str = "pending"
    evidence_hashes: list[str] | None = None
    
    def __post_init__(self):
        from babylon60.math.babylon import Babylon60
        if not self.claim_id:
            self.claim_id = uuid.uuid4().hex
        if not self.created_at_epoch_ms:
            self.created_at_epoch_ms = int(time.time() * 1000)
        if self.evidence_hashes is None:
            self.evidence_hashes = []
        if self.trust_score is None:
            self.trust_score = Babylon60(0)

def submit_claim(claim: RealityClaim, ledger_path: str = "cortex/data/reality_ledger.jsonl") -> str:
    """
    Envía una afirmación al oráculo de realidad en Rust.
    Retorna el estado de verificación: 'verified', 'rejected', 'pending'.
    """
    claim_payload = asdict(claim)
    # Rust boundary expects f32 floats
    if claim.trust_score is not None:
        claim_payload["trust_score"] = claim.trust_score.to_float()
    
    claim_json = json.dumps(claim_payload)
    now_ms = int(time.time() * 1000)
    
    # Llama a ingest_reality_claim exportado desde cortex_rs
    try:
        status = cortex_rs.ingest_reality_claim(ledger_path, claim_json, now_ms)
        return status
    except Exception as e:
        return f"rejected_error: {str(e)}"
