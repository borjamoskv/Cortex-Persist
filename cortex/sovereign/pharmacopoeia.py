# cortex/sovereign/pharmacopoeia.py
"""Predefined agonist/antagonist substance library.

Factory functions that return ready-to-inject Substance lists for common
behavioral modulation scenarios. Compound agents (e.g. caffeine) return
multiple Substance instances targeting different hormones.
"""

from __future__ import annotations

from cortex.sovereign.endocrine import Substance


def caffeine(potency: float = 0.3, half_life: float = 6.0) -> list[Substance]:
    """Alertness boost: ↑ cortisol, ↑ dopamine, ↓ melatonin."""
    return [
        Substance("caffeine:cortisol", "cortisol", "agonist", potency * 0.6, half_life),
        Substance("caffeine:dopamine", "dopamine", "agonist", potency * 0.4, half_life),
        Substance("caffeine:melatonin", "melatonin", "antagonist", potency * 0.8, half_life),
    ]


def anxiolytic(potency: float = 0.4, half_life: float = 8.0) -> list[Substance]:
    """Calm under pressure: ↓ cortisol, ↓ adrenaline."""
    return [
        Substance("anxiolytic:cortisol", "cortisol", "antagonist", potency, half_life),
        Substance("anxiolytic:adrenaline", "adrenaline", "antagonist", potency * 0.7, half_life),
    ]


def nootropic(potency: float = 0.35, half_life: float = 10.0) -> list[Substance]:
    """Creative flow state: ↑ dopamine, ↑ serotonin."""
    return [
        Substance("nootropic:dopamine", "dopamine", "agonist", potency, half_life),
        Substance("nootropic:serotonin", "serotonin", "agonist", potency * 0.6, half_life),
    ]


def sedative(potency: float = 0.5, half_life: float = 5.0) -> list[Substance]:
    """Wind-down / sleep prep: ↑ melatonin, ↓ adrenaline."""
    return [
        Substance("sedative:melatonin", "melatonin", "agonist", potency, half_life),
        Substance("sedative:adrenaline", "adrenaline", "antagonist", potency * 0.5, half_life),
    ]


def empathogen(potency: float = 0.4, half_life: float = 7.0) -> list[Substance]:
    """Collaboration mode: ↑ oxytocin, ↓ cortisol."""
    return [
        Substance("empathogen:oxytocin", "oxytocin", "agonist", potency, half_life),
        Substance("empathogen:cortisol", "cortisol", "antagonist", potency * 0.5, half_life),
    ]


def beta_blocker(potency: float = 0.5, half_life: float = 6.0) -> list[Substance]:
    """Risk tolerance: ↓ adrenaline."""
    return [
        Substance("beta_blocker:adrenaline", "adrenaline", "antagonist", potency, half_life),
    ]
