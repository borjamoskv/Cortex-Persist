# SPDX-License-Identifier: Apache-2.0
"""Cadastral Perimeter Check — Data Models.

Defines the type-safe domain objects for territorial risk analysis:
zone classifications, coordinates, risk scores, and blind-spot reports.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ENUMERATIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class ZoneClassification(str, Enum):
    """Legal classification of a cadastral zone.

    Ordered by decreasing operational freedom:
      ABANDONED_PUBLIC  → free to operate (default authorization)
      INDUSTRIAL_WASTE  → requires prior contact (Scrap Negotiator)
      RURAL_UNCLAIMED   → low risk, verify with local registry
      PROTECTED_NATURAL → environmental restrictions, partial block
      PRIVATE_RESIDENTIAL → automatic block, zero tolerance
      MILITARY_RESTRICTED → lethal-risk zone, absolute block
      UNKNOWN            → human review required
    """

    ABANDONED_PUBLIC = "abandoned_public"
    INDUSTRIAL_WASTE = "industrial_waste"
    RURAL_UNCLAIMED = "rural_unclaimed"
    PROTECTED_NATURAL = "protected_natural"
    PRIVATE_RESIDENTIAL = "private_residential"
    MILITARY_RESTRICTED = "military_restricted"
    UNKNOWN = "unknown"


class RiskLevel(str, Enum):
    """Existential risk level for swarm operations in a zone."""

    SOVEREIGN = "sovereign"    # Full autonomy, no legal friction
    LOW = "low"                # Minor bureaucratic risk
    MEDIUM = "medium"          # Requires human review
    HIGH = "high"              # Likely prosecution or seizure
    FORBIDDEN = "forbidden"    # Absolute prohibition


class OwnershipType(str, Enum):
    """Titularidad de la parcela."""

    PUBLIC_STATE = "public_state"
    PUBLIC_MUNICIPAL = "public_municipal"
    PRIVATE_INDIVIDUAL = "private_individual"
    PRIVATE_CORPORATE = "private_corporate"
    CONTESTED = "contested"
    UNKNOWN = "unknown"


class ExpropiationStatus(str, Enum):
    """Estado de expropiación vigente sobre la parcela."""

    NONE = "none"
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    REVERTED = "reverted"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# DATA MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


@dataclass(frozen=True)
class Coordinate:
    """WGS-84 coordinate pair with optional altitude."""

    latitude: float
    longitude: float
    altitude_m: float | None = None

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            msg = f"Latitude {self.latitude} out of range [-90, 90]"
            raise ValueError(msg)
        if not (-180.0 <= self.longitude <= 180.0):
            msg = f"Longitude {self.longitude} out of range [-180, 180]"
            raise ValueError(msg)

    @property
    def as_tuple(self) -> tuple[float, float]:
        return (self.latitude, self.longitude)


@dataclass()
class Parcel:
    """A cadastral parcel with legal metadata."""

    parcel_id: str
    coordinates: list[Coordinate]  # polygon vertices
    zone: ZoneClassification = ZoneClassification.UNKNOWN
    ownership: OwnershipType = OwnershipType.UNKNOWN
    expropriation: ExpropiationStatus = ExpropiationStatus.NONE
    area_m2: float = 0.0
    municipality: str = ""
    region: str = ""
    country_code: str = ""
    last_registry_check: str = ""
    notes: str = ""


@dataclass()
class RiskAssessment:
    """Risk analysis result for a single coordinate or parcel."""

    coordinate: Coordinate
    zone: ZoneClassification
    risk: RiskLevel
    ownership: OwnershipType
    expropriation: ExpropiationStatus
    risk_score: float  # 0.0 (sovereign) → 1.0 (forbidden)
    factors: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass()
class BlindSpot:
    """A legal 'blind spot' — a gap in the system where risk is minimal.

    These are the zones where an autonomous swarm can operate with the
    lowest probability of legal friction or existential threat.
    """

    spot_id: str
    center: Coordinate
    radius_km: float
    zone: ZoneClassification
    risk_score: float  # lower = safer
    legal_gaps: list[str] = field(default_factory=list)
    confidence: float = 0.0  # C1→C5 mapped to 0.2→1.0
    notes: str = ""


@dataclass()
class CadastralReport:
    """Final cryptographic report of a cadastral perimeter check.

    Includes all assessed parcels, identified blind spots, and a
    SHA-256 hash of the entire report for ledger integrity.
    """

    report_id: str
    timestamp: float = field(default_factory=time.time)
    assessments: list[RiskAssessment] = field(default_factory=list)
    blind_spots: list[BlindSpot] = field(default_factory=list)
    total_parcels_scanned: int = 0
    sovereign_zones_found: int = 0
    forbidden_zones_found: int = 0
    entropy_reduced: float = 0.0
    hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA-256 hash of the report for ledger verification."""
        payload = (
            f"{self.report_id}|{self.timestamp}|"
            f"{self.total_parcels_scanned}|{self.sovereign_zones_found}|"
            f"{self.forbidden_zones_found}|{self.entropy_reduced}|"
            f"{len(self.assessments)}|{len(self.blind_spots)}"
        )
        self.hash = hashlib.sha256(payload.encode()).hexdigest()
        return self.hash

    @property
    def summary(self) -> str:
        """Human-readable summary of the report."""
        return (
            f"CadastralReport[{self.report_id[:8]}]: "
            f"{self.total_parcels_scanned} parcels scanned, "
            f"{self.sovereign_zones_found} sovereign, "
            f"{self.forbidden_zones_found} forbidden, "
            f"{len(self.blind_spots)} blind spots detected"
        )
