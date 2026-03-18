import json
from dataclasses import dataclass, field
from typing import Optional

# Import removed to break circularity: from cortex.embeddings.provider import EmbeddingProvider

__all__ = ["Fact", "row_to_fact"]


@dataclass
class Fact:
    id: int | str
    tenant_id: str
    project: str
    content: str
    fact_type: str
    # Thermodynamic Plane
    quadrant: str = "ACTIVE"
    storage_tier: str = "HOT"
    exergy_score: float = 1.0
    # Semantic Plane
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    # Causal Lineage
    parent_id: Optional[int | str] = None
    relation_type: Optional[str] = None
    yield_score: float = 1.0
    # Provenance and State
    meta: dict = field(default_factory=dict)
    confidence: str = "C3"
    source: Optional[str] = None
    hash: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    is_tombstoned: bool = False
    is_quarantined: bool = False

    def is_active(self) -> bool:
        """Evaluate logical validity using valid_until and physical state."""
        return not self.is_tombstoned and self.valid_until is None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project": self.project,
            "content": self.content,
            "type": self.fact_type,
            "category": self.category,
            "quadrant": self.quadrant,
            "storage_tier": self.storage_tier,
            "tags": self.tags,
            "meta": self.meta,
            "active": self.is_active(),
            "parent_id": self.parent_id,
            "relation_type": self.relation_type,
            "yield_score": self.yield_score,
            "exergy_score": self.exergy_score,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "confidence": self.confidence,
            "source": self.source,
        }


def row_to_fact(row: tuple) -> Fact:
    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()

    # V2 schema expects 21 columns
    # 0:id, 1:tenant_id, 2:project, 3:content, 4:fact_type, 5:metadata, 6:hash,
    # 7:valid_from, 8:valid_until, 9:source, 10:confidence, 11:created_at,
    # 12:updated_at, 13:is_tombstoned, 14:is_quarantined, 15:signature,
    # 16:signer_pubkey, 17:quadrant, 18:storage_tier, 19:exergy_score,
    # 20:category, 21:parent_id, 22:relation_type, 23:yield_score
    # Wait, let's count:
    # facts (
    #    id, tenant_id, project, content, fact_type, metadata, hash, valid_from, valid_until,
    #    source, confidence, created_at, updated_at, is_tombstoned, is_quarantined,
    #    signature, signer_pubkey,
    #    quadrant, storage_tier, exergy_score, category, parent_id, relation_type, yield_score
    # ) -> 24 columns if we add all these.
    r = list(row)
    # Ensure we have enough columns to avoid IndexError during transition
    while len(r) < 24:
        r.append(None)

    tenant_id = r[1] or "default"
    try:
        # Content is usually encrypted
        content = enc.decrypt_str(r[3], tenant_id=tenant_id) if r[3] else ""
    except Exception:
        content = f"[ENCRYPTED — decryption failed] (fact #{r[0]})"

    try:
        meta = json.loads(r[5]) if r[5] and isinstance(r[5], str) else {}
        # If it was actually encrypted JSON (older versions), handle it:
        if isinstance(meta, str) and meta.startswith("{"):
            pass  # Already dict
        elif r[5] and not r[5].startswith("{"):
            try:
                meta = enc.decrypt_json(r[5], tenant_id=tenant_id)
            except Exception:
                meta = {"error": "decryption_failed"}
    except (json.JSONDecodeError, TypeError):
        meta = {}

    return Fact(
        id=r[0],
        tenant_id=tenant_id,
        project=r[2],
        content=content,
        fact_type=r[4],
        meta=meta,
        hash=r[6],
        valid_from=r[7],
        valid_until=r[8],
        source=r[9],
        confidence=r[10] or "C3",
        created_at=r[11],
        updated_at=r[12],
        is_tombstoned=bool(r[13]),
        is_quarantined=bool(r[14]),
        # Double Plane fields (from index 17 onwards)
        quadrant=r[17] or "ACTIVE",
        storage_tier=r[18] or "HOT",
        exergy_score=float(r[19]) if r[19] is not None else 1.0,
        category=r[20] or "general",
        parent_id=r[21],
        relation_type=r[22],
        yield_score=float(r[23]) if r[23] is not None else 1.0,
        tags=[],  # Tags are loaded separately from fact_tags table
    )
