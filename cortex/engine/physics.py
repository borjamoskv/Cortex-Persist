"""
Sovereign Physics Context & Multi-Planetary Geometry.

Establishes the non-terrestrial constants for CORTEX-Persist
Operation under 'Cuatrida Expansion Omega'.
Erradicates earthly technical debt such as hardcoded gravity,
solar cycles, and zero-latency assumptions.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PhysicsContext:
    """Contexto físico parametrizado para operación multi-planetaria."""

    gravity: float = 9.8  # m/s² — Earth default
    day_seconds: float = 86400  # seconds — Earth default
    year_days: float = 365.25  # days — Earth default
    light_delay_ms: float = 0.0  # one-way light delay to nearest relay
    radiation_flux: float = 1.0  # normalized solar radiation (Earth = 1.0)
    magnetic_shielding: float = 1.0  # magnetosphere factor (Earth = 1.0)
    atm_pressure_kpa: float = 101.3  # atmospheric pressure


# Presets Axiomáticos
EARTH = PhysicsContext()

MARS = PhysicsContext(
    gravity=3.72,
    day_seconds=88775,
    year_days=687,
    light_delay_ms=780_000,  # 3–22 min one-way depending on orbit
    radiation_flux=0.43,
    magnetic_shielding=0.0,
    atm_pressure_kpa=0.636,
)

LUNA = PhysicsContext(
    gravity=1.62,
    day_seconds=2_551_443,
    year_days=354.37,
    light_delay_ms=1_282,  # ~1.28s one-way
    radiation_flux=1.0,
    magnetic_shielding=0.0,
    atm_pressure_kpa=0.0,
)


def get_local_physics() -> PhysicsContext:
    """Retrieves the active PhysicsContext for current operations."""
    # In future: resolved by orbital telemtry or env var.
    return EARTH
