import pytest

from babylon60.engine.causal.autodidact_functor import (
    AutodidactFunctor,
    EntropicState,
    EntropyPhase,
    OntologyForgeMatrix,
)
from babylon60.engine.flow.causality_models import Claim, Evidence


def test_functor_successful_collapse():
    functor = AutodidactFunctor(require_strict_bft=True)
    state = EntropicState(
        id="bug-123",
        phase=EntropyPhase.OPAQUE_ENVIRONMENT,
        raw_observation="Segfault in unknown module",
        epicenter_radius=3,
    )

    claims = [
        Claim(
            id="c1",
            statement="Primitiva de fallo de memoria identificada.",
            evidence_list=[Evidence("A", 1.0), Evidence("B", 1.0)],
        ),
        Claim(
            id="c2",
            statement="Primitiva del puntero nulo.",
            evidence_list=[Evidence("C", 1.0), Evidence("D", 1.0)],
        ),
        Claim(
            id="c3",
            statement="Invariante: no se puede acceder a direcciones 0x0.",
            evidence_list=[Evidence("E", 1.0), Evidence("F", 1.0)],
        ),
    ]

    matrix = functor.map_object(state, claims)
    assert matrix.is_valid()
    assert matrix.source_state_id == "bug-123"
    assert matrix.confidence_level == "C5-REAL"
    # Should pad primitives to 5 and invariants to 3
    assert len(matrix.primitives) == 5
    assert len(matrix.invariants) == 3


def test_functor_bft_failure_apoptosis():
    functor = AutodidactFunctor(require_strict_bft=True)
    state = EntropicState(
        id="bounty-001",
        phase=EntropyPhase.UNVERIFIED_SIGNAL,
        raw_observation="Flash loan attack speculation",
        epicenter_radius=4,
    )

    claims = [
        Claim(
            id="c1",
            statement="Primitiva vulnerabilidad detectada.",
            evidence_list=[Evidence("A", 1.0)],
        )  # N=1, fails BFT
    ]

    with pytest.raises(ValueError, match="Fallo BFT: Evidencia independiente insuficiente"):
        functor.map_object(state, claims)


def test_functor_morphism_preservation():
    functor = AutodidactFunctor(require_strict_bft=True)

    matrix = OntologyForgeMatrix(
        source_state_id="init-1",
        primitives=["p1", "p2", "p3", "p4", "p5"],
        invariants=["i1", "i2", "i3"],
        anti_patterns=["a1", "a2", "a3"],
        redundancies=["r1", "r2"],
        adversarial_vectors=["v1", "v2"],
        confidence_level="C5-REAL",
    )

    def valid_transform(m: OntologyForgeMatrix) -> OntologyForgeMatrix:
        return OntologyForgeMatrix(
            source_state_id=m.source_state_id,
            primitives=m.primitives + ["p6"],
            invariants=m.invariants,
            anti_patterns=m.anti_patterns,
            redundancies=m.redundancies,
            adversarial_vectors=m.adversarial_vectors,
            confidence_level="C5-REAL",
        )

    new_matrix = functor.map_morphism(matrix, valid_transform)
    assert "p6" in new_matrix.primitives

    def invalid_transform(m: OntologyForgeMatrix) -> OntologyForgeMatrix:
        return OntologyForgeMatrix(
            source_state_id=m.source_state_id,
            primitives=["p1"],  # invalidates length constraint
            invariants=m.invariants,
            anti_patterns=m.anti_patterns,
            redundancies=m.redundancies,
            adversarial_vectors=m.adversarial_vectors,
            confidence_level="C5-REAL",
        )

    with pytest.raises(RuntimeError, match="La transformación rompe el isomorfismo"):
        functor.map_morphism(matrix, invalid_transform)
