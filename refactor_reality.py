import os
from pathlib import Path

def refactor_reality():
    filepath = Path("/Users/borjafernandezangulo/10_PROJECTS/cortex-persist/babylon60/reality/rul.py")
    content = filepath.read_text(encoding="utf-8")
    
    old_claim = """@dataclass
class RealityClaim:
    statement: str
    domain: str
    sources: list[Source]
    claim_id: str = ""
    created_at_epoch_ms: int = 0
    trust_score: float = 0.0
    status: str = "pending"
    evidence_hashes: list[str] = None
    
    def __post_init__(self):
        if not self.claim_id:
            self.claim_id = uuid.uuid4().hex
        if not self.created_at_epoch_ms:
            self.created_at_epoch_ms = int(time.time() * 1000)
        if self.evidence_hashes is None:
            self.evidence_hashes = []"""
            
    new_claim = """@dataclass
class RealityClaim:
    statement: str
    domain: str
    sources: list[Source]
    claim_id: str = ""
    created_at_epoch_ms: int = 0
    trust_score: 'Babylon60 | None' = None
    status: str = "pending"
    evidence_hashes: list[str] = None
    
    def __post_init__(self):
        from babylon60.math.babylon import Babylon60
        if not self.claim_id:
            self.claim_id = uuid.uuid4().hex
        if not self.created_at_epoch_ms:
            self.created_at_epoch_ms = int(time.time() * 1000)
        if self.evidence_hashes is None:
            self.evidence_hashes = []
        if self.trust_score is None:
            self.trust_score = Babylon60(0)"""
            
    content = content.replace(old_claim, new_claim)
    
    old_submit = """def submit_claim(claim: RealityClaim, ledger_path: str = "cortex/data/reality_ledger.jsonl") -> str:
    \"\"\"
    Envía una afirmación al oráculo de realidad en Rust.
    Retorna el estado de verificación: 'verified', 'rejected', 'pending'.
    \"\"\"
    claim_payload = asdict(claim)
    
    claim_json = json.dumps(claim_payload)"""
    
    new_submit = """def submit_claim(claim: RealityClaim, ledger_path: str = "cortex/data/reality_ledger.jsonl") -> str:
    \"\"\"
    Envía una afirmación al oráculo de realidad en Rust.
    Retorna el estado de verificación: 'verified', 'rejected', 'pending'.
    \"\"\"
    claim_payload = asdict(claim)
    # Rust boundary expects f32 floats
    if claim.trust_score is not None:
        claim_payload["trust_score"] = claim.trust_score.to_float()
    
    claim_json = json.dumps(claim_payload)"""
    
    content = content.replace(old_submit, new_submit)
    
    filepath.write_text(content, encoding="utf-8")

if __name__ == "__main__":
    refactor_reality()
