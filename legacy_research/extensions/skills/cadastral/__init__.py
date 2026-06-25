# [C5-REAL] Exergy-Maximized
# SPDX-License-Identifier: Apache-2.0
"""Cadastral Perimeter Check - Sovereign Territorial Radar.

Cross-references zoning, ownership, and expropriation data to identify
legal blind spots where an autonomous swarm (Earthship MMX) can operate
with minimal legal and existential risk.
"""

from __future__ import annotations

from legacy_research.extensions.skills.cadastral.engine import CadastralEngine
from legacy_research.extensions.skills.cadastral.models import (
    BlindSpot,
    CadastralReport,
    Coordinate,
    ZoneClassification,
)

__all__ = [
    "BlindSpot",
    "CadastralEngine",
    "CadastralReport",
    "Coordinate",
    "ZoneClassification",
]
