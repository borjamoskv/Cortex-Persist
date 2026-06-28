import pytest
from pydantic import ValidationError

from cortex.extensions.skills.autodidact.epistemology import (
    Derived,
    EvidenceSource,
    Hypothesis,
    InferenceModel,
    Intervention,
    Invariant,
    InvariantLevel,
    Latent,
    Narrative,
    Observable,
    RawEvidence,
    compile_derived,
    compile_hypothesis,
    compile_latent,
    compile_latent_from_narrative,
    compile_narrative_from_narrative,
    compile_observable,
)


def test_epistemological_pipeline_valid():
    """Test the full valid causal pipeline."""
    # 1. Raw Evidence
    raw = RawEvidence(
        source=EvidenceSource.GIT_OBJECTS,
        raw_payload="diff content",
        timestamp_iso="2026-06-27T10:00:00Z",
    )

    # 2. Observable
    def extract_lines(payload: str) -> int:
        return 10

    obs = compile_observable(
        evidence=raw, extractor=extract_lines, extractor_hash="hash123", name="changed_lines"
    )
    assert obs.value == 10

    # 3. Derived
    def calculate_mttr(inputs: list[int]) -> float:
        return sum(inputs) / len(inputs) if inputs else 0.0

    der = compile_derived(inputs=[obs], pure_func=calculate_mttr, name="MTTR")
    assert der.value == 10.0

    # 4. Latent
    def bayesian_infer(inputs: list[float]) -> tuple[float, dict]:
        return 0.85, {"risk_level": "high"}

    lat = compile_latent(inputs=[der], model=InferenceModel.BAYESIAN, infer_func=bayesian_infer)
    assert lat.posterior == 0.85

    # 5. Hypothesis & Intervention
    inter = Intervention(
        action_name="freeze_release",
        parameters={"duration": "24h"},
        predicted_outcomes={"stability": "high"},
        confidence=0.9,
    )
    hyp = compile_hypothesis(lat, inter)

    assert hyp.proposed_intervention.action_name == "freeze_release"
    assert hyp.proposed_intervention.execute() == "do(freeze_release)"

    # 6. Narrative Rendering
    nar = Narrative(content="Release has been frozen due to high risk.", basis=inter)
    assert nar.basis == inter


def test_narrative_derivation_invalid():
    """Narrative -> Narrative is invalid."""
    inter = Intervention(action_name="test", parameters={}, predicted_outcomes={}, confidence=1.0)
    nar1 = Narrative(content="Initial", basis=inter)

    with pytest.raises(ValueError, match="Narrative cannot be derived from Narrative"):
        Narrative(content="Derived", basis=nar1)

    with pytest.raises(TypeError):
        compile_narrative_from_narrative(nar1)


def test_latent_from_narrative_invalid():
    """Narrative -> Latent is invalid."""
    inter = Intervention(action_name="test", parameters={}, predicted_outcomes={}, confidence=1.0)
    nar1 = Narrative(content="Initial", basis=inter)

    with pytest.raises(TypeError):
        compile_latent_from_narrative(nar1, InferenceModel.BAYESIAN, lambda x: (0.0, {}))


def test_invariant_checking():
    """Invariant validation against arbitrary observable/derived values."""
    inv = Invariant(level=InvariantLevel.HARD, target_metric="MTTR", condition=lambda x: x < 50.0)

    assert inv.check(40.0) is True
    assert inv.check(60.0) is False
