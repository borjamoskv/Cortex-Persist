from __future__ import annotations

from cortex.extensions.skills.autodidact.rotorquant import (
    RotorQuantProfile,
    evaluate_rotorquant,
    select_rotorquant_profile,
)


def _raw_payload() -> str:
    return (
        "CORTEX Persist enforces deterministic guard validation, tenant isolation, contradiction checks, "
        "and hash-chain ledger continuity. The Autodidact synthesis stage distills noisy source documents "
        "into grounded memo artifacts. Version 2.1 of the pipeline keeps evidence traceability and entity "
        "extraction for SQLite, Ledger, and ContradictionGuard."
    )


def test_profile_selection_by_intent() -> None:
    assert select_rotorquant_profile("deep_learn").name == "deep_learn"
    assert select_rotorquant_profile("quick_read").name == "quick_read"
    assert select_rotorquant_profile("search_gap").name == "search_gap"
    assert select_rotorquant_profile("other").name == "default"


def test_rotorquant_accepts_grounded_distillation() -> None:
    raw = _raw_payload()
    distilled = (
        "Autodidact distills source artifacts with deterministic guard validation, contradiction checks, "
        "and hash-chain ledger continuity. Version 2.1 preserves evidence traceability and tenant isolation."
    )
    result = evaluate_rotorquant(
        raw_data=raw,
        distilled_content=distilled,
        entities=["SQLite", "Ledger", "ContradictionGuard"],
        intent="deep_learn",
        source_url="https://example.com/cortex/persist/v2",
    )

    assert result.accepted is True
    assert result.score >= 0.66
    assert result.profile == "deep_learn"
    assert result.metrics["grounding_ratio"] >= 0.60


def test_rotorquant_rejects_numeric_drift() -> None:
    raw = _raw_payload()
    distilled = (
        "Pipeline version 9.9 introduces 300 nodes and 42 shards with no guard validation details."
    )
    result = evaluate_rotorquant(
        raw_data=raw,
        distilled_content=distilled,
        entities=[],
        intent="search_gap",
        source_url="https://example.com/cortex/persist/v2",
    )

    assert result.accepted is False
    assert "NUMERIC_DRIFT" in result.reasons


def test_rotorquant_rejects_high_repetition() -> None:
    raw = _raw_payload()
    repeated = "ledger ledger ledger ledger ledger ledger ledger ledger ledger ledger"
    result = evaluate_rotorquant(
        raw_data=raw,
        distilled_content=repeated,
        entities=[],
        intent="quick_read",
    )

    assert result.accepted is False
    assert "HIGH_REPETITION" in result.reasons


def test_rotorquant_rejects_low_intent_alignment() -> None:
    raw = _raw_payload()
    distilled = "General notes about gardening and cooking without distributed memory content."
    result = evaluate_rotorquant(
        raw_data=raw,
        distilled_content=distilled,
        entities=["Ledger"],
        intent="Focus on contradiction guard and tenant isolation",
    )

    assert result.accepted is False
    assert "LOW_INTENT_ALIGNMENT" in result.reasons


def test_rotorquant_metadata_shape() -> None:
    assessment = evaluate_rotorquant(
        raw_data=_raw_payload(),
        distilled_content=(
            "Autodidact keeps ledger continuity, contradiction checks, and deterministic guard validation."
        ),
        entities=["Ledger"],
        intent="quick_read",
    )
    metadata = assessment.as_metadata()

    assert isinstance(metadata["profile"], str)
    assert isinstance(metadata["score"], float)
    assert isinstance(metadata["accepted"], bool)
    assert isinstance(metadata["reasons"], list)
    assert isinstance(metadata["metrics"], dict)


def test_profile_override_is_supported() -> None:
    custom = RotorQuantProfile(
        name="strict_custom",
        min_score=0.95,
        min_raw_chars=20,
        min_distilled_chars=20,
        min_grounding_ratio=0.90,
        min_bigram_coverage=0.70,
        min_numeric_fidelity=1.0,
        max_repetition_ratio=0.10,
        min_entropy=2.0,
        max_entropy=6.5,
        min_retention_ratio=0.10,
        max_retention_ratio=0.40,
        min_entity_density=0.01,
        target_entity_density=0.08,
        target_retention_low=0.12,
        target_retention_high=0.24,
        weights={
            "grounding": 0.22,
            "bigram": 0.12,
            "compression": 0.12,
            "entropy": 0.10,
            "entity": 0.10,
            "numeric": 0.10,
            "repetition": 0.08,
            "intent": 0.10,
            "source": 0.06,
        },
    )
    result = evaluate_rotorquant(
        raw_data=_raw_payload(),
        distilled_content="short summary with weak signals",
        entities=[],
        intent="quick_read",
        profile=custom,
    )

    assert result.profile == "strict_custom"
    assert result.accepted is False
