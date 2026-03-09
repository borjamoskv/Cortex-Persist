"""CORTEX v8.0 — Crystal Thermometer (Knowledge Vital Signs).

Measures the health of each knowledge crystal in L2 using two orthogonal metrics:
    - Temperature: recall frequency / age (usage intensity)
    - Resonance: semantic alignment with sovereign axioms (relevance)

Together these place each crystal in one of 4 quadrants:
    ACTIVE         — Hot + Resonant  → Maintain
    FOUNDATIONAL   — Cold + Resonant → Protect (diamond candidate)
    NOISE          — Hot + Irrelevant → Decay with grace
    DEAD_WEIGHT    — Cold + Irrelevant → Purge

Axiom Derivations:
    Ω₂ (Entropic Asymmetry): Dead weight increases recall noise — must be purged.
    Ω₅ (Antifragile): Each purge refines the system's semantic precision.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Literal

logger = logging.getLogger("cortex.swarm.crystal_thermometer")

# ── Quadrant Classification ───────────────────────────────────────────────

Quadrant = Literal["ACTIVE", "FOUNDATIONAL", "NOISE", "DEAD_WEIGHT"]
Recommendation = Literal["MAINTAIN", "PROTECT", "DECAY", "PURGE", "MERGE", "PROMOTE"]

# ── Thresholds ────────────────────────────────────────────────────────────

TEMPERATURE_HOT = 0.1       # recalls/day — above this is "hot"
TEMPERATURE_COLD = 0.01     # below this is "cold"
RESONANCE_HIGH = 0.5        # cosine sim vs axioms — above is "resonant"
RESONANCE_LOW = 0.2         # below this is "irrelevant"
AXIOMATIC_INERTIA_THRESHOLD = 0.8  # Ω₃: structural knowledge threshold
TEMPERATURE_TIBIA = 0.1     # min "warm" temperature for axiomatic facts
MIN_AGE_DAYS_FOR_PURGE = 14  # Don't purge anything younger than 2 weeks
MIN_AGE_DAYS_FOR_PROMOTE = 7  # Must survive 7 days to earn diamond status


# ── Axiom Reference Texts ────────────────────────────────────────────────
# Pre-computed semantic anchors for resonance measurement.
# These are the Peano Soberano v3 axioms in their essential form.

AXIOM_TEXTS = [
    "Self-reference: if I write it, I execute it. Autonomous systems.",
    "Multi-scale causality: wrong scale, not wrong place. Architecture patterns.",
    "Entropic asymmetry: does it reduce or displace entropy. Information theory.",
    "Byzantine default: verify then trust, never reversed. Security validation.",
    "Aesthetic integrity: ugly equals incomplete. Design systems UI UX.",
    "Antifragile by default: what antibody does this failure forge. Error recovery.",
    "Zenon's razor: did the conclusion mutate? Execute. Decision making.",
]


# ── Data Models ───────────────────────────────────────────────────────────


@dataclass
class CrystalVitals:
    """Health assessment of a single knowledge crystal."""

    fact_id: str
    content_preview: str
    temperature: float
    resonance: float
    quadrant: Quadrant
    recommendation: Recommendation
    age_days: float
    recall_count: int
    is_diamond: bool
    project_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


# ── Temperature Calculation ───────────────────────────────────────────────


def calculate_temperature(recall_count: int, age_days: float) -> float:
    """Calculate crystal temperature as recall rate per day.

    Temperature measures usage intensity:
        temp = recall_count / max(age_days, 1)

    A crystal recalled 10 times in 2 days has temp=5.0 (very hot).
    A crystal recalled 0 times in 30 days has temp=0.0 (frozen).
    """
    if age_days < 0.01:
        # New crystal — give it a warm start
        return float(recall_count) if recall_count > 0 else 0.5
    return recall_count / max(age_days, 1.0)


# ── Resonance Calculation ────────────────────────────────────────────────


async def calculate_resonance(
    content_embedding: list[float],
    axiom_embeddings: list[list[float]],
) -> float:
    """Calculate semantic resonance with sovereign axioms.

    Resonance = max cosine similarity between the crystal and any axiom.
    A crystal that strongly aligns with at least one axiom is "resonant".
    """
    if not content_embedding or not axiom_embeddings:
        return 0.0

    try:
        import numpy as np

        content_vec = np.array(content_embedding, dtype=np.float32)
        content_norm = np.linalg.norm(content_vec)
        if content_norm < 1e-10:
            return 0.0

        max_sim = 0.0
        for axiom_emb in axiom_embeddings:
            axiom_vec = np.array(axiom_emb, dtype=np.float32)
            axiom_norm = np.linalg.norm(axiom_vec)
            if axiom_norm < 1e-10:
                continue
            sim = float(np.dot(content_vec, axiom_vec) / (content_norm * axiom_norm))
            max_sim = max(max_sim, sim)

        return max_sim

    except Exception as e:
        logger.error("Resonance calculation failed: %s", e)
        return 0.0


# ── Quadrant Classification ──────────────────────────────────────────────


def classify_quadrant(temperature: float, resonance: float) -> Quadrant:
    """Place crystal in the 2D temperature×resonance space."""
    is_hot = temperature >= TEMPERATURE_HOT
    is_resonant = resonance >= RESONANCE_HIGH

    if is_hot and is_resonant:
        return "ACTIVE"
    if not is_hot and is_resonant:
        return "FOUNDATIONAL"
    if is_hot and not is_resonant:
        return "NOISE"
    return "DEAD_WEIGHT"


def determine_recommendation(
    quadrant: Quadrant,
    is_diamond: bool,
    age_days: float,
    _temperature: float,
    resonance: float,
) -> Recommendation:
    """Determine what action to take on this crystal."""
    if quadrant == "ACTIVE":
        # Hot + resonant — promote to diamond if old enough
        if not is_diamond and age_days >= MIN_AGE_DAYS_FOR_PROMOTE and resonance > 0.6:
            return "PROMOTE"
        return "MAINTAIN"

    if quadrant == "FOUNDATIONAL":
        # Cold + resonant — protect (make diamond if not already)
        if not is_diamond and age_days >= MIN_AGE_DAYS_FOR_PROMOTE:
            return "PROTECT"
        return "MAINTAIN"

    if quadrant == "NOISE":
        # Hot + irrelevant — let it decay naturally
        return "DECAY"

    # DEAD_WEIGHT: Cold + irrelevant
    if is_diamond:
        return "DECAY"  # Diamonds degrade to decay, never purge
    if age_days >= MIN_AGE_DAYS_FOR_PURGE:
        return "PURGE"
    return "DECAY"


# ── Single Crystal Assessment ────────────────────────────────────────────


def measure_crystal_sync(
    fact_id: str,
    content: str,
    recall_count: int,
    age_days: float,
    is_diamond: bool,
    resonance: float,
    project_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> CrystalVitals:
    """Synchronous crystal health measurement (resonance pre-computed)."""
    temperature = calculate_temperature(recall_count, age_days)
    
    # Ω₃: Axiomatic Inertia (Byzantine Default)
    # Structural knowledge maintains a minimum "warm" (Tibia) temperature 
    # regardless of usage frequency to prevent democratic decay loops.
    if resonance >= AXIOMATIC_INERTIA_THRESHOLD:
        if temperature < TEMPERATURE_TIBIA:
            logger.debug(
                "🛡️ [THERMOMETER] Axiomatic Inertia: keeping %s warm (res=%.3f)", 
                fact_id, resonance
            )
            temperature = TEMPERATURE_TIBIA

    quadrant = classify_quadrant(temperature, resonance)
    recommendation = determine_recommendation(
        quadrant, is_diamond, age_days, temperature, resonance,
    )

    return CrystalVitals(
        fact_id=fact_id,
        content_preview=content[:100],
        temperature=temperature,
        resonance=resonance,
        quadrant=quadrant,
        recommendation=recommendation,
        age_days=age_days,
        recall_count=recall_count,
        is_diamond=is_diamond,
        project_id=project_id,
        metadata=metadata or {},
    )


# ── Full L2 Scan ─────────────────────────────────────────────────────────


async def get_axiom_embeddings(encoder: Any) -> list[list[float]]:
    """Pre-compute axiom embeddings for resonance measurement."""
    embeddings = []
    for text in AXIOM_TEXTS:
        try:
            emb = await encoder.encode(text)
            embeddings.append(emb)
        except Exception as e:
            logger.warning("Failed to encode axiom: %s", e)
    return embeddings


async def scan_all_crystals(
    db_conn: Any,
    encoder: Any | None = None,
    project: str = "autodidact_knowledge",
    tenant_id: str = "sovereign",
) -> list[CrystalVitals]:
    """Scan all crystals in L2 and assess their vital signs.

    Args:
        db_conn: SQLite connection or compatible DB handle.
        encoder: AsyncEncoder for axiom embedding (optional — uses 0.5 default resonance).
        project: Filter by project.
        tenant_id: Filter by tenant.

    Returns:
        List of CrystalVitals sorted by recommendation priority
        (PURGE first, then MERGE, DECAY, PROMOTE, PROTECT, MAINTAIN).
    """
    logger.info("🌡️ [THERMOMETER] Scanning crystals for project=%s", project)

    # Pre-compute axiom embeddings
    axiom_embeddings: list[list[float]] = []
    if encoder is not None:
        axiom_embeddings = await get_axiom_embeddings(encoder)

    now = time.time()
    vitals: list[CrystalVitals] = []

    try:
        # Query all facts for this project
        import sqlite3
        import numpy as np

        if hasattr(db_conn, "cursor"):
            cursor = db_conn.cursor()
        elif hasattr(db_conn, "_get_conn"):
            cursor = db_conn._get_conn().cursor()
        else:
            logger.warning("🌡️ [THERMOMETER] No compatible DB handle")
            return []

        cursor.execute(
            """
            SELECT f.id, f.content, f.timestamp, f.is_diamond,
                   f.project_id, f.metadata, f.success_rate,
                   v.embedding
            FROM facts_meta f
            JOIN vec_facts v ON f.rowid = v.rowid
            WHERE f.tenant_id = ? AND f.project_id = ?
            ORDER BY f.timestamp DESC
            """,
            (tenant_id, project),
        )

        rows = cursor.fetchall()
        logger.info("🌡️ [THERMOMETER] Found %d crystals to assess", len(rows))

        for row in rows:
            fact_id = row[0]
            content = row[1] or ""
            timestamp = row[2] or now
            is_diamond = bool(row[3])
            project_id = row[4] or project
            raw_meta = row[5]
            metadata = json.loads(raw_meta) if raw_meta else {}

            age_days = max(0.0, (now - timestamp) / 86400.0)

            # Extract recall count from metadata (access_stats)
            access_stats = metadata.get("access_stats", {})
            recall_count = access_stats.get("total_access_count", 0)

            # Calculate resonance
            resonance = 0.5  # Default neutral resonance
            if axiom_embeddings:
                try:
                    embedding = np.frombuffer(row[7], dtype=np.float32).tolist()
                    resonance = await calculate_resonance(embedding, axiom_embeddings)
                except Exception:
                    pass

            vital = measure_crystal_sync(
                fact_id=fact_id,
                content=content,
                recall_count=recall_count,
                age_days=age_days,
                is_diamond=is_diamond,
                resonance=resonance,
                project_id=project_id,
                metadata=metadata,
            )
            vitals.append(vital)

    except Exception as e:
        logger.error("🌡️ [THERMOMETER] Scan failed: %s", e)

    # Sort by recommendation priority: PURGE > MERGE > DECAY > PROMOTE > PROTECT > MAINTAIN
    priority_order = {"PURGE": 0, "MERGE": 1, "DECAY": 2, "PROMOTE": 3, "PROTECT": 4, "MAINTAIN": 5}
    vitals.sort(key=lambda v: priority_order.get(v.recommendation, 5))

    # Log summary
    quadrant_counts = {}
    for v in vitals:
        quadrant_counts[v.quadrant] = quadrant_counts.get(v.quadrant, 0) + 1

    logger.info(
        "🌡️ [THERMOMETER] Assessment complete: %s",
        " | ".join(f"{q}={c}" for q, c in sorted(quadrant_counts.items())),
    )

    return vitals
