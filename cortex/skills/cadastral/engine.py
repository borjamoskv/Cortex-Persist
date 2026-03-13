# SPDX-License-Identifier: Apache-2.0
"""Cadastral Perimeter Check — Sovereign Territorial Engine.

Cross-references zoning law, ownership records, and expropriation status
to compute risk scores, classify zones, and detect legal blind spots
where autonomous infrastructure (Earthship MMX) can be deployed.

Physics-Inspired Design:
  - Risk fields behave like gravitational wells: private/military zones
    have infinite curvature (forbidden), while abandoned/public zones
    have flat spacetime (sovereign).
  - Blind spots are found at Lagrange-like equilibrium points where
    multiple legal jurisdictions cancel each other out.
"""

from __future__ import annotations

import logging
import math
import uuid
from typing import Any

from cortex.skills.cadastral.models import (
    BlindSpot,
    CadastralReport,
    Coordinate,
    ExpropiationStatus,
    OwnershipType,
    Parcel,
    RiskAssessment,
    RiskLevel,
    ZoneClassification,
)

logger = logging.getLogger(__name__)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# RISK FIELD CONSTANTS — Gravitational curvature per zone
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_ZONE_RISK_WEIGHT: dict[ZoneClassification, float] = {
    ZoneClassification.ABANDONED_PUBLIC: 0.05,
    ZoneClassification.INDUSTRIAL_WASTE: 0.25,
    ZoneClassification.RURAL_UNCLAIMED: 0.15,
    ZoneClassification.PROTECTED_NATURAL: 0.55,
    ZoneClassification.PRIVATE_RESIDENTIAL: 0.85,
    ZoneClassification.MILITARY_RESTRICTED: 1.00,
    ZoneClassification.UNKNOWN: 0.50,
}

_OWNERSHIP_RISK_MODIFIER: dict[OwnershipType, float] = {
    OwnershipType.PUBLIC_STATE: 0.0,
    OwnershipType.PUBLIC_MUNICIPAL: 0.05,
    OwnershipType.PRIVATE_INDIVIDUAL: 0.30,
    OwnershipType.PRIVATE_CORPORATE: 0.25,
    OwnershipType.CONTESTED: -0.10,  # Contested = legal fog → blind spot
    OwnershipType.UNKNOWN: 0.10,
}

_EXPROPIATION_MODIFIER: dict[ExpropiationStatus, float] = {
    ExpropiationStatus.NONE: 0.0,
    ExpropiationStatus.PENDING: -0.05,  # Transition state → opportunity
    ExpropiationStatus.ACTIVE: -0.15,   # State is seizing → legal vacuum
    ExpropiationStatus.COMPLETED: 0.05,
    ExpropiationStatus.REVERTED: -0.08,  # Abandoned process → ghost zone
}

_RISK_THRESHOLDS: dict[RiskLevel, tuple[float, float]] = {
    RiskLevel.SOVEREIGN: (0.0, 0.15),
    RiskLevel.LOW: (0.15, 0.35),
    RiskLevel.MEDIUM: (0.35, 0.60),
    RiskLevel.HIGH: (0.60, 0.85),
    RiskLevel.FORBIDDEN: (0.85, 1.01),
}

_BLIND_SPOT_THRESHOLD: float = 0.20  # Below this risk_score = blind spot


def _haversine_km(c1: Coordinate, c2: Coordinate) -> float:
    """Haversine distance between two WGS-84 coordinates in km."""
    r_earth = 6371.0
    lat1, lon1 = math.radians(c1.latitude), math.radians(c1.longitude)
    lat2, lon2 = math.radians(c2.latitude), math.radians(c2.longitude)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return r_earth * 2 * math.asin(math.sqrt(a))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class CadastralEngine:
    """Sovereign Territorial Radar — Risk analysis and blind-spot detection.

    Usage:
        engine = CadastralEngine()
        engine.register_parcel(parcel)
        report = engine.scan_perimeter(center, radius_km=50)
    """

    def __init__(self) -> None:
        self._parcels: dict[str, Parcel] = {}
        self._scan_count: int = 0

    # ── Registration ──────────────────────────────────────────────────────

    def register_parcel(self, parcel: Parcel) -> None:
        """Register a parcel in the engine's spatial index."""
        self._parcels[parcel.parcel_id] = parcel
        logger.debug("[CADASTRAL] Registered parcel %s (%s)", parcel.parcel_id, parcel.zone)

    def register_parcels(self, parcels: list[Parcel]) -> int:
        """Bulk-register parcels. Returns count registered."""
        for p in parcels:
            self.register_parcel(p)
        return len(parcels)

    # ── Risk Scoring ──────────────────────────────────────────────────────

    def assess_risk(self, parcel: Parcel) -> RiskAssessment:
        """Compute a composite risk score for a single parcel.

        Score = clamp(zone_weight + ownership_mod + expropiation_mod, 0, 1)
        """
        factors: list[str] = []
        base = _ZONE_RISK_WEIGHT[parcel.zone]
        factors.append(f"zone:{parcel.zone.value}={base:.2f}")

        own_mod = _OWNERSHIP_RISK_MODIFIER[parcel.ownership]
        factors.append(f"ownership:{parcel.ownership.value}={own_mod:+.2f}")

        exp_mod = _EXPROPIATION_MODIFIER[parcel.expropriation]
        factors.append(f"expropriation:{parcel.expropriation.value}={exp_mod:+.2f}")

        raw_score = base + own_mod + exp_mod
        risk_score = max(0.0, min(1.0, raw_score))

        risk_level = RiskLevel.MEDIUM
        for level, (lo, hi) in _RISK_THRESHOLDS.items():
            if lo <= risk_score < hi:
                risk_level = level
                break

        recommendation = self._generate_recommendation(risk_level, parcel)

        center = parcel.coordinates[0] if parcel.coordinates else Coordinate(0.0, 0.0)
        return RiskAssessment(
            coordinate=center,
            zone=parcel.zone,
            risk=risk_level,
            ownership=parcel.ownership,
            expropriation=parcel.expropriation,
            risk_score=risk_score,
            factors=factors,
            recommendation=recommendation,
        )

    # ── Perimeter Scan ────────────────────────────────────────────────────

    def scan_perimeter(
        self,
        center: Coordinate,
        radius_km: float = 50.0,
    ) -> CadastralReport:
        """Scan all registered parcels within a radius and produce a report.

        Identifies blind spots where the risk_score falls below the
        _BLIND_SPOT_THRESHOLD — the Lagrange points of the legal field.
        """
        report_id = f"cad-{uuid.uuid4().hex[:12]}"
        assessments: list[RiskAssessment] = []
        blind_spots: list[BlindSpot] = []
        sovereign_count = 0
        forbidden_count = 0

        for parcel in self._parcels.values():
            if not parcel.coordinates:
                continue

            parcel_center = parcel.coordinates[0]
            distance = _haversine_km(center, parcel_center)

            if distance > radius_km:
                continue

            assessment = self.assess_risk(parcel)
            assessments.append(assessment)

            if assessment.risk == RiskLevel.SOVEREIGN:
                sovereign_count += 1
            elif assessment.risk == RiskLevel.FORBIDDEN:
                forbidden_count += 1

            # Blind-spot detection
            if assessment.risk_score <= _BLIND_SPOT_THRESHOLD:
                gaps = self._detect_legal_gaps(parcel, assessment)
                if gaps:
                    spot = BlindSpot(
                        spot_id=f"bs-{uuid.uuid4().hex[:8]}",
                        center=parcel_center,
                        radius_km=min(radius_km * 0.1, distance * 0.5) if distance > 0 else 1.0,
                        zone=parcel.zone,
                        risk_score=assessment.risk_score,
                        legal_gaps=gaps,
                        confidence=self._gap_confidence(gaps),
                        notes=f"Parcel {parcel.parcel_id}, {parcel.municipality}",
                    )
                    blind_spots.append(spot)

        # Compute entropy reduction
        total = len(assessments)
        entropy_before = math.log2(max(1, len(self._parcels)))
        entropy_after = math.log2(max(1, total)) if total > 0 else 0.0
        entropy_reduced = max(0.0, entropy_before - entropy_after)

        self._scan_count += 1
        report = CadastralReport(
            report_id=report_id,
            assessments=assessments,
            blind_spots=blind_spots,
            total_parcels_scanned=total,
            sovereign_zones_found=sovereign_count,
            forbidden_zones_found=forbidden_count,
            entropy_reduced=entropy_reduced,
        )
        report.compute_hash()

        logger.info("[CADASTRAL] %s", report.summary)
        return report

    # ── Blind-Spot Analysis ───────────────────────────────────────────────

    def _detect_legal_gaps(
        self, parcel: Parcel, assessment: RiskAssessment
    ) -> list[str]:
        """Identify specific legal gaps that create a blind spot."""
        gaps: list[str] = []

        if parcel.ownership == OwnershipType.CONTESTED:
            gaps.append("ownership_contested: no clear legal claimant")
        if parcel.ownership == OwnershipType.UNKNOWN:
            gaps.append("ownership_unknown: registry data missing")

        if parcel.expropriation == ExpropiationStatus.ACTIVE:
            gaps.append("expropriation_active: state seizure in progress, legal vacuum")
        if parcel.expropriation == ExpropiationStatus.REVERTED:
            gaps.append("expropriation_reverted: abandoned process, ghost jurisdiction")
        if parcel.expropriation == ExpropiationStatus.PENDING:
            gaps.append("expropriation_pending: transition state, uncertainty window")

        if parcel.zone == ZoneClassification.ABANDONED_PUBLIC:
            gaps.append("zone_abandoned: no active governance or enforcement")
        if parcel.zone == ZoneClassification.RURAL_UNCLAIMED:
            gaps.append("zone_unclaimed: rural void, minimal registration")

        if not parcel.last_registry_check:
            gaps.append("registry_stale: no recent verification timestamp")

        return gaps

    def _gap_confidence(self, gaps: list[str]) -> float:
        """Map number of legal gaps to a confidence score (C1→C5)."""
        n = len(gaps)
        if n >= 5:
            return 1.0  # C5
        if n >= 4:
            return 0.8  # C4
        if n >= 3:
            return 0.6  # C3
        if n >= 2:
            return 0.4  # C2
        return 0.2  # C1

    # ── Recommendations ───────────────────────────────────────────────────

    def _generate_recommendation(self, risk: RiskLevel, parcel: Parcel) -> str:
        """Generate a sovereign recommendation based on risk level."""
        recs: dict[RiskLevel, str] = {
            RiskLevel.SOVEREIGN: (
                "DEPLOY: Zone is sovereign-grade. Full autonomous operation authorized."
            ),
            RiskLevel.LOW: (
                f"PROCEED_WITH_CAUTION: Low risk in {parcel.municipality or 'unknown area'}. "
                "Verify local bylaw compliance before deployment."
            ),
            RiskLevel.MEDIUM: (
                "HUMAN_REVIEW_REQUIRED: Medium risk detected. "
                "Submit to legal advisor before any physical deployment."
            ),
            RiskLevel.HIGH: (
                "ABORT_RECOMMENDED: High legal risk. "
                "Prosecution or asset seizure probable. Do NOT deploy."
            ),
            RiskLevel.FORBIDDEN: (
                "ABSOLUTE_BLOCK: This zone is under military/private protection. "
                "Any operation here is existentially dangerous."
            ),
        }
        return recs.get(risk, "UNKNOWN: Classification failed, manual review required.")

    # ── Telemetry ─────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Return engine telemetry."""
        return {
            "registered_parcels": len(self._parcels),
            "total_scans": self._scan_count,
            "zones_distribution": self._zone_distribution(),
        }

    def _zone_distribution(self) -> dict[str, int]:
        """Count parcels per zone classification."""
        dist: dict[str, int] = {}
        for p in self._parcels.values():
            key = p.zone.value
            dist[key] = dist.get(key, 0) + 1
        return dist
