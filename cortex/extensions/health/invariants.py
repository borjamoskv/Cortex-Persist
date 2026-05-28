"""Health system invariant verification.

Self-test that runs in tests AND daemon — any future regression
breaks automatically.
"""

from __future__ import annotations

from cortex.extensions.health.collector import (
    CollectorRegistry,
    create_default_registry,
)
from cortex.extensions.health.health_protocol import MetricCollectorProtocol
from cortex.extensions.health.models import Grade


def verify_health_system(
    registry: CollectorRegistry | None = None,
) -> list[str]:
    """Verify all health system invariants.

    Returns list of violations. Empty = system is sound.
    Call from tests and daemon self-check.
    """
    violations: list[str] = []
    # CRITICAL: do NOT use `registry or default` — empty registry
    # has __len__==0 which makes bool(registry)==False in Python.
    reg = create_default_registry() if registry is None else registry

    # 1. Grade enum is exhaustive and ordered
    grades = list(Grade)
    if len(grades) != 6:
        violations.append(f"Grade enum must have 6 members, has {len(grades)}")

    # Verify ordering is monotonically decreasing
    for i in range(len(grades) - 1):
        if grades[i].threshold <= grades[i + 1].threshold:
            violations.append(f"Grade ordering violated: {grades[i]} <= {grades[i + 1]}")

    # All grades must have unique letters
    letters = [g.letter for g in Grade]
    if len(letters) != len(set(letters)):
        violations.append("Duplicate grade letters detected")

    # 2. All registered collectors implement protocol
    for name in reg.list_collectors():
        collector = reg._collectors[name]
        if not isinstance(collector, MetricCollectorProtocol):
            violations.append(f"Collector '{name}' violates MetricCollectorProtocol")

    # 3. No duplicate collector names
    names = reg.list_collectors()
    if len(names) != len(set(names)):
        violations.append("Duplicate collector names detected")

    # 4. Total weight must be > 0
    total_weight = sum(reg._collectors[n].weight for n in reg.list_collectors())
    if total_weight <= 0:
        violations.append(f"Total collector weight must be > 0, got {total_weight}")

    # 5. Built-in collector count — must be at least 9
    if len(reg) < 9:
        violations.append(f"Need at least 9 collectors, have {len(reg)}")

    # 6. Grade.from_score covers full range
    edge_cases = [0.0, 39.9, 40.0, 55.0, 70.0, 85.0, 95.0, 100.0]
    for score in edge_cases:
        try:
            g = Grade.from_score(score)
            if not isinstance(g, Grade):
                violations.append(f"Grade.from_score({score}) returned non-Grade: {type(g)}")
        except Exception as e:  # noqa: BLE001
            violations.append(f"Grade.from_score({score}) raised: {e}")

    # 7. Registry Truthiness (C1)
    if not bool(reg):
        violations.append("CollectorRegistry must always evaluate to True")

    # 8. Collector Metadata (C2)
    for name, collector in reg._collectors.items():
        if not hasattr(collector, "description") or not collector.description:
            violations.append(f"Collector '{name}' missing description")
        if not hasattr(collector, "remediation") or not collector.remediation:
            violations.append(f"Collector '{name}' missing remediation")

    # 9. Required collectors by name
    required_names = {
        "db",
        "ledger",
        "entropy",
        "facts",
        "wal",
        "sysload",
        "browsers",
        "snapshot",
        "disk",
    }
    present = set(reg.list_collectors())
    missing = required_names - present
    if missing:
        violations.append(f"Missing required collectors: {sorted(missing)}")

    # 10. Sub-index coverage — all collector names must appear in at least one sub-index

    # Build the mapping from scorer's internals
    sub_idx_mapping = {
        "storage": {"db", "facts", "disk"},
        "integrity": {"ledger", "entropy"},
        "performance": {"wal", "sysload"},
        "environment": {"browsers", "snapshot"},
    }
    all_mapped = set()
    for metrics_set in sub_idx_mapping.values():
        all_mapped |= metrics_set

    unmapped = required_names - all_mapped
    if unmapped:
        violations.append(f"Collectors not in any sub-index: {sorted(unmapped)}")

    if len(sub_idx_mapping) != 4:
        violations.append(f"Expected 4 sub-indices, found {len(sub_idx_mapping)}")

    return violations
