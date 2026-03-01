"""Cognitive Evolution Rate (CER) — Measure how fast CORTEX evolves.

CER quantifies the intra-decision coherence of stored memory.
Decisions semantically distant from the cluster centroid indicate
evolutionary friction — evidence that Gf (fluid intelligence) has
evolved faster than Gc (crystallized intelligence).

    CER = |frictions| / |decisions|
    Sweet spot: CER ∈ [0.15, 0.35]

    CER ≈ 0 → stagnant (Gc dominates, no evolution)
    CER ≈ 1 → chaotic  (Gf ignores Gc, no memory)
    CER ∈ [0.15, 0.35] → evolving (healthy friction)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger("cortex.evolution.cer")


# ─── Configuration ────────────────────────────────────────────────


@dataclass(frozen=True)
class CERConfig:
    """Hyperparameters for CER computation."""

    sweet_spot_low: float = 0.15
    sweet_spot_high: float = 0.35
    max_decisions: int = 50
    surprise_threshold: float = 0.55
    """Cosine similarity below this → friction."""


# ─── Output Models ────────────────────────────────────────────────


@dataclass
class DecisionFriction:
    """A single decision flagged as evolutionary friction."""

    fact_id: int
    project: str
    content: str
    surprise_score: float
    age_days: float
    fact_type: str = "decision"


@dataclass
class CERResult:
    """Aggregate CER analysis result."""

    cer: float
    total_decisions: int
    discrepancies: int
    frictions: list[DecisionFriction] = field(default_factory=list)
    health: str = "stagnant"
    centroid_norm: float = 0.0

    @property
    def health_icon(self) -> str:
        icons = {"stagnant": "🧊", "evolving": "🌱", "chaotic": "🌋"}
        return icons.get(self.health, "❓")

    @property
    def health_color(self) -> str:
        colors = {"stagnant": "cyan", "evolving": "green", "chaotic": "red"}
        return colors.get(self.health, "white")


# ─── Core Computation ─────────────────────────────────────────────


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine similarity between two vectors."""
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))


def _classify_health(cer: float, config: CERConfig) -> str:
    """Classify CER into health zone."""
    if cer < config.sweet_spot_low:
        return "stagnant"
    if cer <= config.sweet_spot_high:
        return "evolving"
    return "chaotic"


async def compute_cer(
    engine,
    config: CERConfig | None = None,
    project: str | None = None,
) -> CERResult:
    """Compute Cognitive Evolution Rate from stored decisions.

    Strategy: embed all recent decisions, compute centroid, measure
    each decision's cosine distance from centroid. Decisions far from
    the centroid are "frictions" — evidence of cognitive evolution.

    Args:
        engine: CortexEngine instance (must be initialized).
        config: Optional CER configuration overrides.
        project: Optional project scope (None = all projects).

    Returns:
        CERResult with the CER metric and friction details.
    """
    if config is None:
        config = CERConfig()

    # ─── 1. Load decisions ────────────────────────────────────
    conn = await engine.get_conn()

    query = """
        SELECT id, project, content, fact_type, created_at
        FROM facts
        WHERE fact_type = 'decision'
          AND valid_until IS NULL
          AND is_quarantined = 0
    """
    params: list = []
    if project:
        query += " AND project = ?"
        params.append(project)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(config.max_decisions)

    cursor = await conn.execute(query, params)
    rows = await cursor.fetchall()

    if not rows:
        return CERResult(
            cer=0.0,
            total_decisions=0,
            discrepancies=0,
            health="stagnant",
        )

    # ─── 2. Decrypt & Embed decisions ──────────────────────────
    from cortex.crypto.aes import CortexEncrypter, get_default_encrypter
    from cortex.embeddings import LocalEmbedder

    encrypter = get_default_encrypter()
    decrypted_rows: list[tuple] = []
    contents: list[str] = []

    for row in rows:
        raw_content = row[2]
        # Decrypt if encrypted
        if raw_content and raw_content.startswith(CortexEncrypter.PREFIX):
            try:
                plain = encrypter.decrypt_str(raw_content)
                if plain and plain.strip():
                    decrypted_rows.append(row)
                    contents.append(plain)
            except (ValueError, RuntimeError):
                logger.debug("Skipping undecryptable fact #%d", row[0])
        elif raw_content and raw_content.strip():
            decrypted_rows.append(row)
            contents.append(raw_content)

    if not contents:
        return CERResult(
            cer=0.0,
            total_decisions=len(rows),
            discrepancies=0,
            health="stagnant",
        )

    # Replace rows with only the ones we could decrypt
    rows = decrypted_rows

    embedder = LocalEmbedder()
    embeddings = embedder.embed_batch(contents)
    embeddings_np = np.array(embeddings)

    # ─── 3. Compute centroid ──────────────────────────────────
    centroid = np.mean(embeddings_np, axis=0)
    centroid_norm = float(np.linalg.norm(centroid))

    # ─── 4. Score each decision ───────────────────────────────
    frictions: list[DecisionFriction] = []

    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)

    for i, row in enumerate(rows):
        fact_id, proj, content, fact_type, created_at = row
        similarity = _cosine_similarity(embeddings_np[i], centroid)
        surprise_score = 1.0 - similarity  # distance from centroid

        # Compute age in days
        try:
            created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            age_days = (now - created).total_seconds() / 86400
        except (ValueError, AttributeError):
            age_days = 0.0

        if similarity < config.surprise_threshold:
            frictions.append(
                DecisionFriction(
                    fact_id=fact_id,
                    project=proj,
                    content=contents[i][:200],
                    surprise_score=round(surprise_score, 4),
                    age_days=round(age_days, 1),
                    fact_type=fact_type,
                )
            )

    # ─── 5. Compute CER ──────────────────────────────────────
    total = len(rows)
    discrepancies = len(frictions)
    cer = discrepancies / total if total > 0 else 0.0
    health = _classify_health(cer, config)

    # Sort frictions by surprise (highest first)
    frictions.sort(key=lambda f: f.surprise_score, reverse=True)

    logger.info(
        "CER computed: %.3f (%d/%d frictions) — %s",
        cer, discrepancies, total, health,
    )

    return CERResult(
        cer=round(cer, 4),
        total_decisions=total,
        discrepancies=discrepancies,
        frictions=frictions,
        health=health,
        centroid_norm=round(centroid_norm, 4),
    )
