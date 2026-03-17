"""CORTEX Engine — Fact Model and helpers."""

from __future__ import annotations
from typing import Optional

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
    meta: dict
    created_at: str
    updated_at: str
    is_tombstoned: bool = False
    is_quarantined: bool = False
    hash: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    source: Optional[str] = None
    confidence: str = "C3"
    parent_decision_id: Optional[int] = None
    cognitive_layer: Optional[str] = None
    consensus_score: Optional[float] = None

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
            "tags": self.tags,
            "meta": self.meta,
            "active": self.is_active(),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "parent_decision_id": self.parent_decision_id,
            "cognitive_layer": self.cognitive_layer,
            "consensus_score": self.consensus_score,
        }


def row_to_fact(row: tuple) -> Fact:
    from cortex.crypto import get_default_encrypter

    enc = get_default_encrypter()

    # New schema expects 16 columns
    # row[0]=id, row[1]=tenant_id, row[2]=project, row[3]=content, row[4]=fact_type,
    # row[5]=tags, row[6]=meta, row[7]=hash, row[8]=valid_from, row[9]=valid_until,
    # row[10]=source, row[11]=confidence, row[12]=created_at, row[13]=updated_at,
    # row[14]=is_tombstoned, row[15]=is_quarantined
    r = list(row)
    while len(r) < 16:
        r.append(None)

    tenant_id = r[1] or "default"
    try:
        content = enc.decrypt_str(r[3], tenant_id=tenant_id) if r[3] else ""
    except ValueError:
        content = f"[ENCRYPTED — decryption failed] (fact #{r[0]})"

    # Safely handle JSON parsing
    try:
        tags = json.loads(r[5]) if r[5] else []
    except (json.JSONDecodeError, TypeError):
        tags = []

    try:
        meta = enc.decrypt_json(r[6], tenant_id=tenant_id) if r[6] else {}
    except ValueError:
        meta = {"error": "decryption_failed", "fact_id": r[0]}

    return Fact(
        id=r[0],
        tenant_id=tenant_id,
        project=r[2],
        content=content,  # type: ignore[reportArgumentType]
        fact_type=r[4],
        tags=tags,
        meta=meta,  # type: ignore[reportArgumentType]
        hash=r[7],
        valid_from=r[8],
        valid_until=r[9],
        source=r[10],
        confidence=r[11] or "C3",
        created_at=r[12],
        updated_at=r[13],
        is_tombstoned=bool(r[14]),
        is_quarantined=bool(r[15]),
    )
