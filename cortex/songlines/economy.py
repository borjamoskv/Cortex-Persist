"""
ThermalEconomy — The Entropy Gatekeeper.
Enforces 'Proof-of-Skin' and field density limits.
"""

import logging
from pathlib import Path
from typing import Any

from cortex.songlines.sensor import TopographicSensor

logger = logging.getLogger("cortex.songlines.economy")


class ThermalEconomy:
    """Musk: Entropy without value = death.

    Prevents the agent from polucioning the codebase with too many ghosts.
    Enforces a 'field density' limit.
    """

    # Maximum active ghosts allowed in a project topography
    MAX_FIELD_DENSITY = 50

    def __init__(self, sensor: TopographicSensor | None = None):
        self.sensor = sensor or TopographicSensor()

    def check_entropy(self, root_dir: Path) -> dict[str, Any]:
        """Measure current ghost density and determine if new ones can be emitted."""
        active_ghosts = self.sensor.scan_field(root_dir)
        count = len(active_ghosts)

        status = {
            "count": count,
            "density": count / self.MAX_FIELD_DENSITY,
            "is_saturated": count >= self.MAX_FIELD_DENSITY,
            "remaining_capacity": max(0, self.MAX_FIELD_DENSITY - count),
        }

        if status["is_saturated"]:
            logger.warning(f"Field saturated! {count}/{self.MAX_FIELD_DENSITY} ghosts active.")

        return status

    def validate_emission(self, root_dir: Path):
        """Raise an error if entropy is too high to plant a new ghost."""
        status = self.check_entropy(root_dir)
        if status["is_saturated"]:
            raise RuntimeError(
                f"Thermal Economy Error: Field density limit reached ({status['count']} ghosts). "
                "Resolve or let existing ghosts decay before planting new ones."
            )
        return True
