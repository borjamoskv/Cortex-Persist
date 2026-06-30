# [C5-REAL] Exergy-Maximized
"""
Unit tests for MemoryFirewallGuard.
"""

from __future__ import annotations

import pytest
from babylon60.guards.memory_firewall import MemoryFirewallGuard


def test_memory_firewall_guard_empty_fact() -> None:
    guard = MemoryFirewallGuard()
    with pytest.raises(ValueError, match="Cannot persist empty fact"):
        guard.validate_fact("", source="agent-1", confidence="C5")


def test_memory_firewall_guard_confidence_levels() -> None:
    # Default min_confidence is C3
    guard = MemoryFirewallGuard(require_taint=False, min_confidence="C3")

    # 1. Equal or higher confidence passes
    assert guard.validate_fact("Sovereign data fact.", source="agent-1", confidence="C3") is True
    assert (
        guard.validate_fact("Sovereign data fact.", source="agent-1", confidence="C4-SIM") is True
    )
    assert (
        guard.validate_fact("Sovereign data fact.", source="agent-1", confidence="C5-REAL") is True
    )

    # 2. Lower confidence fails
    with pytest.raises(ValueError, match="is below minimum threshold"):
        guard.validate_fact("Low confidence assertion.", source="agent-1", confidence="C2")

    with pytest.raises(ValueError, match="is below minimum threshold"):
        guard.validate_fact("Low confidence assertion.", source="agent-1", confidence="C1")


def test_memory_firewall_guard_invalid_confidence() -> None:
    guard = MemoryFirewallGuard(require_taint=False)
    with pytest.raises(ValueError, match="Invalid confidence level"):
        guard.validate_fact("Some fact.", source="agent-1", confidence="C6")


def test_memory_firewall_guard_require_taint() -> None:
    guard = MemoryFirewallGuard(require_taint=True)

    # Missing taint raises error
    with pytest.raises(ValueError, match="lacks CORTEX-TAINT"):
        guard.validate_fact("Sovereign fact.", source="agent-1", confidence="C5", meta={})
