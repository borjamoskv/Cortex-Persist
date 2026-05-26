import json
from dataclasses import dataclass, field
from typing import Any

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
    if isinstance(raw, list | dict):
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


def _extract_full_layout(row: list, res: dict) -> None:
    res.update(
        {
            "meta_raw": row[5],
            "hash": row[6],
            "valid_from": row[7],
            "valid_until": row[8],
            "source": row[9],
            "confidence": row[10] or "C3",
            "created_at": row[11],
            "updated_at": row[12],
            "is_tombstoned": bool(row[13]),
            "is_quarantined": bool(row[14]),
            "quadrant": row[17] or "ACTIVE",
            "storage_tier": row[18] or "HOT",
            "exergy_score": _to_float(row[19], 1.0),
            "category": row[20] or "general",
            "semantic_status": row[21],
            "semantic_error": row[22],
            "parent_id": row[23],
            "relation_type": row[24],
            "yield_score": _to_float(row[25], 1.0),
            "tags_raw": row[26],
        }
    )


def _extract_rich_layout(row: list, res: dict) -> None:
    res.update(
        {
            "tags_raw": row[5],
            "meta_raw": row[6],
            "hash": row[7],
            "valid_from": row[8],
            "valid_until": row[9],
            "source": row[10],
            "confidence": row[11] or "C3",
            "created_at": row[12],
            "updated_at": row[13],
            "is_tombstoned": bool(row[14]),
            "is_quarantined": bool(row[15]),
            "quadrant": row[16] or "ACTIVE",
            "storage_tier": row[17] or "HOT",
            "exergy_score": _to_float(row[18], 1.0),
            "category": row[19] or "general",
            "parent_id": row[20],
            "relation_type": row[21],
            "yield_score": _to_float(row[22], 1.0),
        }
    )


def _extract_compat_v1(row: list, res: dict, length: int) -> None:
    res.update(
        {
            "tags_raw": row[5] if length > 5 else None,
            "meta_raw": row[6] if length > 6 else (row[5] if length > 5 else None),
            "hash": row[7] if length > 7 else (row[6] if length > 6 else None),
            "valid_from": row[8] if length > 8 else (row[7] if length > 7 else None),
        }
    )


def _extract_compat_v2_core(row: list, res: dict, length: int) -> None:
    res.update(
        {
            "valid_until": row[9] if length > 9 else (row[8] if length > 8 else None),
            "source": row[10] if length > 10 else (row[9] if length > 9 else None),
            "confidence": (row[11] if length > 11 else (row[10] if length > 10 else None)) or "C3",
        }
    )


def _extract_compat_v2_status(row: list, res: dict, length: int) -> None:
    res.update(
        {
            "created_at": row[12] if length > 12 else (row[11] if length > 11 else None),
            "updated_at": row[13] if length > 13 else (row[12] if length > 12 else None),
            "is_tombstoned": bool(row[14])
            if length > 14
            else (bool(row[13]) if length > 13 else False),
            "is_quarantined": bool(row[15])
            if length > 15
            else (bool(row[14]) if length > 14 else False),
        }
    )


def _extract_compat_v2(row: list, res: dict, length: int) -> None:
    _extract_compat_v2_core(row, res, length)
    _extract_compat_v2_status(row, res, length)


def _extract_compat_legacy(row: list, res: dict, length: int) -> None:
    _extract_compat_v1(row, res, length)
    _extract_compat_v2(row, res, length)


def _extract_compat_standard(row: list, res: dict) -> None:
    res.update(
        {
            "tags_raw": row[5],
            "meta_raw": row[6],
            "hash": row[7],
            "valid_from": row[8],
            "valid_until": row[9],
            "source": row[10],
            "confidence": row[11] or "C3",
            "created_at": row[12],
            "updated_at": row[13],
            "is_tombstoned": bool(row[14]),
            "is_quarantined": bool(row[15]),
        }
    )


def _extract_compat_layout(row: list, res: dict, length: int) -> None:
    if length >= 16:
        _extract_compat_standard(row, res)
    else:
        _extract_compat_legacy(row, res, length)


def _extract_row_values(row: list) -> dict:
    """Identify layout type and extract raw values."""
    length = len(row)
    res = {
        "id": row[0],
        "tenant_id": row[1] or "default",
        "project": row[2],
        "content_encrypted": row[3],
        "fact_type": row[4],
        "tags_raw": None,
        "meta_raw": None,
        "confidence": "C3",
        "is_tombstoned": False,
        "is_quarantined": False,
        "quadrant": "ACTIVE",
        "storage_tier": "HOT",
        "exergy_score": 1.0,
        "category": "general",
        "yield_score": 1.0,
        "parent_id": None,
        "relation_type": None,
        "semantic_status": None,
        "semantic_error": None,
        "hash": None,
        "valid_from": None,
        "valid_until": None,
        "created_at": None,
        "updated_at": None,
    }

    if length >= 27:
        _extract_full_layout(row, res)
    elif length >= 23:
        _extract_rich_layout(row, res)
    else:
        _extract_compat_layout(row, res, length)
    return res


def _parse_fact_metadata(v: dict, enc: Any, tenant_id: str) -> dict:
    """Decrypt and parse the manifest-level metadata."""
    m_raw = v["meta_raw"]
    if isinstance(m_raw, str) and m_raw and not m_raw.lstrip().startswith("{"):
        try:
            return enc.decrypt_json(m_raw, tenant_id=tenant_id)
        except Exception:
            return {"error": "decryption_failed", "fact_id": v["id"]}
    meta = _parse_json_blob(m_raw, {})
    return meta if isinstance(meta, dict) else {}


def row_to_fact(row: tuple) -> Fact:
    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()
    r = list(row)
    if len(r) < 5:
        raise ValueError(f"Fact row shape error: expected >= 5, got {len(r)}")

    v = _extract_row_values(r)
    tenant_id = v["tenant_id"]

    try:
        content = (
            enc.decrypt_str(v["content_encrypted"], tenant_id=tenant_id)
            if v["content_encrypted"]
            else ""
        )
    except Exception:
        content = f"[ENCRYPTED - decryption failed] (fact #{v['id']})"

    tags = _parse_json_blob(v["tags_raw"], [])
    if not isinstance(tags, list):
        tags = []

    meta = _parse_fact_metadata(v, enc, tenant_id)
    pid = v["parent_id"] or meta.get("parent_id") or meta.get("parent_decision_id")

    return Fact(
        id=v["id"],
        tenant_id=tenant_id,
        project=v["project"],
        content=content if content is not None else "",
        fact_type=v["fact_type"],
        tags=tags,
        meta=meta,
        created_at=v["created_at"],
        updated_at=v["updated_at"],
        is_tombstoned=v["is_tombstoned"],
        is_quarantined=v["is_quarantined"],
        hash=v["hash"],
        valid_from=v["valid_from"],
        valid_until=v["valid_until"],
        source=v.get("source") or meta.get("source"),
        confidence=v["confidence"] or meta.get("confidence", "C3"),
        quadrant=meta.get("quadrant", v["quadrant"]),
        storage_tier=meta.get("storage_tier", v["storage_tier"]),
        exergy_score=_to_float(meta.get("exergy_score"), v["exergy_score"]),
        category=meta.get("category", v["category"]),
        parent_id=pid,
        parent_decision_id=meta.get("parent_decision_id", pid),
        relation_type=v["relation_type"] or meta.get("relation_type"),
        yield_score=_to_float(meta.get("yield_score"), v["yield_score"]),
        consensus_score=_to_float(meta.get("consensus_score"), 1.0),
        tx_id=meta.get("tx_id") if isinstance(meta.get("tx_id"), int) else None,
        semantic_status=meta.get("semantic_status", v["semantic_status"]),
        semantic_error=meta.get("semantic_error", v["semantic_error"]),
    )
