from dataclasses import dataclass


@dataclass(frozen=True)
class BlastRadiusReport:
    reverse_import_count: int
    test_reference_count: int
    runtime_entrypoint_count: int
    causal_dependency_count: int
    criticality_score: float


@dataclass(frozen=True)
class DemolitionDecision:
    allowed: bool
    requires_quarantine: bool
    requires_snapshot: bool
    reason: str


def evaluate_demolition(
    report: BlastRadiusReport, has_snapshot: bool, modifies_schema: bool
) -> DemolitionDecision:
    if report.criticality_score > 0.8:
        return DemolitionDecision(
            allowed=False,
            requires_quarantine=True,
            requires_snapshot=True,
            reason="Criticality > 0.8. Direct demolition denied, requires quarantine.",
        )

    if not has_snapshot:
        return DemolitionDecision(
            allowed=False,
            requires_quarantine=True,
            requires_snapshot=True,
            reason="Destructive mutation without snapshot is prohibited.",
        )

    if modifies_schema:
        if not has_snapshot:
            return DemolitionDecision(
                allowed=False,
                requires_quarantine=False,
                requires_snapshot=True,
                reason="Schema mutation requires strict snapshot rollback.",
            )

    return DemolitionDecision(
        allowed=True,
        requires_quarantine=report.criticality_score > 0.4,
        requires_snapshot=True,
        reason="Demolition allowed under quarantine and snapshot conditions.",
    )
