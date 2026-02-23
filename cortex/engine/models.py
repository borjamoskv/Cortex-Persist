"""CORTEX Engine — Fact Model and helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass

__all__ = ["Fact", "row_to_fact"]


@dataclass
class Fact:
    id: int
    tenant_id: str
    project: str
    content: str
    fact_type: str
    tags: list[str]
    confidence: str
    valid_from: str
    valid_until: str | None
    source: str | None
    meta: dict
    created_at: str
    updated_at: str
    consensus_score: float = 1.0
    tx_id: int | None = None
    hash: str | None = None

    def is_active(self) -> bool:
        return self.valid_until is None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "project": self.project,
            "content": self.content,
            "type": self.fact_type,
            "tags": self.tags,
            "confidence": self.confidence,
            "valid_from": self.valid_from,
            "valid_until": self.valid_until,
            "source": self.source,
            "active": self.is_active(),
            "consensus_score": self.consensus_score,
        }


def row_to_fact(row: tuple) -> Fact:
    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()

    # Handle shorter tuples safely (legacy tests might pass incomplete rows)
    # New schema expects 16 columns (indices 0-15)
    # row[0]=id, row[1]=tenant_id, row[2]=project, row[3]=content, row[4]=fact_type,
    # row[5]=tags, row[6]=confidence, row[7]=valid_from, row[8]=valid_until,
    # row[9]=source, row[10]=meta, row[11]=consensus_score, row[12]=created_at,
    # row[13]=updated_at, row[14]=tx_id, row[15]=hash
    r = list(row)
    while len(r) < 16:
        r.append(None)

    tenant_id = r[1] or "default"
    content = enc.decrypt_str(r[3], tenant_id=tenant_id) if r[3] else ""

    # Safely handle JSON parsing
    try:
        tags = json.loads(r[5]) if r[5] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    try:
        meta = enc.decrypt_json(r[10], tenant_id=tenant_id) if r[10] else {}
    except (json.JSONDecodeError, TypeError):
        meta = {}

    score = r[11] if r[11] is not None else 1.0

    return Fact(
        id=r[0],
        tenant_id=tenant_id,
        project=r[2],
        content=content,
        fact_type=r[4],
        tags=tags,
        confidence=r[6],
        valid_from=r[7],
        valid_until=r[8],
        source=r[9],
        meta=meta,
        consensus_score=score,
        created_at=r[12],
        updated_at=r[13],
        tx_id=r[14],
        hash=r[15],
    )
