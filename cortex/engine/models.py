import json
from dataclasses import dataclass, field

__all__ = ["Fact", "row_to_fact"]


@dataclass
class Fact:
    id: int | str
    tenant_id: str
    project: str
    content: str
    fact_type: str
    tags: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    is_tombstoned: bool = False
    is_quarantined: bool = False
    hash: str | None = None
    valid_from: str | None = None
    valid_until: str | None = None
    source: str | None = None
    confidence: str = "C3"
    quadrant: str = "ACTIVE"
    storage_tier: str = "HOT"
    exergy_score: float = 1.0
    category: str = "general"
    parent_id: int | str | None = None
    parent_decision_id: int | str | None = None
    relation_type: str | None = None
    yield_score: float = 1.0
    consensus_score: float = 1.0
    tx_id: int | None = None
    semantic_status: str | None = None
    semantic_error: str | None = None
    causal_depth: int | str = 0

    def __post_init__(self) -> None:
        if self.parent_id is None and self.parent_decision_id is not None:
            self.parent_id = self.parent_decision_id
        if self.parent_decision_id is None and self.parent_id is not None:
            self.parent_decision_id = self.parent_id

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
            "fact_type": self.fact_type,
            "category": self.category,
            "quadrant": self.quadrant,
            "storage_tier": self.storage_tier,
            "tags": self.tags,
            "meta": self.meta,
            "active": self.is_active(),
            "parent_id": self.parent_id,
            "parent_decision_id": self.parent_decision_id,
            "relation_type": self.relation_type,
            "yield_score": self.yield_score,
            "exergy_score": self.exergy_score,
            "consensus_score": self.consensus_score,
            "tx_id": self.tx_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "confidence": self.confidence,
            "source": self.source,
            "hash": self.hash,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "is_tombstoned": self.is_tombstoned,
            "is_quarantined": self.is_quarantined,
            "semantic_status": self.semantic_status,
            "semantic_error": self.semantic_error,
        }


def _parse_json_blob(raw: object, fallback: object) -> object:
    if raw is None:
        return fallback
    if isinstance(raw, (list, dict)):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return fallback
    return fallback


def _to_float(value: object, default: float) -> float:
    try:
        return float(value) if value is not None else default  # pyright: ignore
    except (TypeError, ValueError):
        return default


def row_to_fact(row: tuple) -> Fact:
    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()
    r = list(row)
    if len(r) < 5:
        raise ValueError(f"Unsupported fact row shape: expected at least 5 columns, got {len(r)}")

    tenant_id = r[1] or "default"
    try:
        content = enc.decrypt_str(r[3], tenant_id=tenant_id) if r[3] else ""
    except Exception:
        content = f"[ENCRYPTED - decryption failed] (fact #{r[0]})"

    full_layout = len(r) >= 27
    rich_projection_layout = len(r) >= 23 and not full_layout
    compat_layout = len(r) >= 16

    if full_layout:
        raw_meta = r[5]
        raw_tags = r[26]
        hash_value = r[6]
        valid_from = r[7]
        valid_until = r[8]
        source = r[9]
        confidence = r[10] or "C3"
        created_at = r[11]
        updated_at = r[12]
        is_tombstoned = bool(r[13])
        is_quarantined = bool(r[14])
        quadrant = r[17] or "ACTIVE"
        storage_tier = r[18] or "HOT"
        exergy_score = _to_float(r[19], 1.0)
        category = r[20] or "general"
        semantic_status = r[21]
        semantic_error = r[22]
        parent_id = r[23]
        relation_type = r[24]
        yield_score = _to_float(r[25], 1.0)
    elif rich_projection_layout:
        raw_tags = r[5]
        raw_meta = r[6]
        hash_value = r[7]
        valid_from = r[8]
        valid_until = r[9]
        source = r[10]
        confidence = r[11] or "C3"
        created_at = r[12]
        updated_at = r[13]
        is_tombstoned = bool(r[14])
        is_quarantined = bool(r[15])
        quadrant = r[16] or "ACTIVE"
        storage_tier = r[17] or "HOT"
        exergy_score = _to_float(r[18], 1.0)
        category = r[19] or "general"
        semantic_status = None
        semantic_error = None
        parent_id = r[20]
        relation_type = r[21]
        yield_score = _to_float(r[22], 1.0)
    else:
        raw_tags = r[5] if compat_layout else None
        raw_meta = r[6] if compat_layout else (r[5] if len(r) > 5 else None)
        hash_value = r[7] if compat_layout else (r[6] if len(r) > 6 else None)
        valid_from = r[8] if compat_layout else (r[7] if len(r) > 7 else None)
        valid_until = r[9] if compat_layout else (r[8] if len(r) > 8 else None)
        source = r[10] if compat_layout else (r[9] if len(r) > 9 else None)
        confidence = (r[11] if compat_layout else (r[10] if len(r) > 10 else None)) or "C3"
        created_at = r[12] if compat_layout else (r[11] if len(r) > 11 else None)
        updated_at = r[13] if compat_layout else (r[12] if len(r) > 12 else None)
        is_tombstoned = bool(r[14]) if compat_layout else (bool(r[13]) if len(r) > 13 else False)
        is_quarantined = bool(r[15]) if compat_layout else (bool(r[14]) if len(r) > 14 else False)
        quadrant = "ACTIVE"
        storage_tier = "HOT"
        exergy_score = 1.0
        category = "general"
        semantic_status = None
        semantic_error = None
        parent_id = None
        relation_type = None
        yield_score = 1.0

    tags = _parse_json_blob(raw_tags, [])
    if not isinstance(tags, list):
        tags = []

    if isinstance(raw_meta, str) and raw_meta and not raw_meta.lstrip().startswith("{"):
        try:
            meta = enc.decrypt_json(raw_meta, tenant_id=tenant_id)
        except Exception:
            meta = {"error": "decryption_failed", "fact_id": r[0]}
    else:
        meta = _parse_json_blob(raw_meta, {})

    if not isinstance(meta, dict):
        meta = {}

    parent_id = parent_id or meta.get("parent_id") or meta.get("parent_decision_id")
    relation_type = relation_type or meta.get("relation_type")
    quadrant = meta.get("quadrant", quadrant)
    storage_tier = meta.get("storage_tier", storage_tier)
    exergy_score = _to_float(meta.get("exergy_score"), exergy_score)
    category = meta.get("category", category)
    yield_score = _to_float(meta.get("yield_score"), yield_score)
    semantic_status = meta.get("semantic_status", semantic_status)
    semantic_error = meta.get("semantic_error", semantic_error)
    consensus_score = _to_float(meta.get("consensus_score"), 1.0)
    tx_id = meta.get("tx_id")

    return Fact(
        id=r[0],
        tenant_id=tenant_id,
        project=r[2],
        content=content if content is not None else "",
        fact_type=r[4],
        tags=tags,
        meta=meta,
        created_at=created_at,
        updated_at=updated_at,
        is_tombstoned=is_tombstoned,
        is_quarantined=is_quarantined,
        hash=hash_value,
        valid_from=valid_from,
        valid_until=valid_until,
        source=source or meta.get("source"),
        confidence=confidence or meta.get("confidence", "C3"),
        quadrant=quadrant,
        storage_tier=storage_tier,
        exergy_score=exergy_score,
        category=category,
        parent_id=parent_id,
        parent_decision_id=meta.get("parent_decision_id", parent_id),
        relation_type=relation_type,
        yield_score=yield_score,
        consensus_score=consensus_score,
        tx_id=tx_id if isinstance(tx_id, int) or tx_id is None else None,
        semantic_status=semantic_status,
        semantic_error=semantic_error,
    )
