import pytest
import math

class BeliefState:
    ACTIVE = "Active"
    CONTESTED = "Contested"
    SUBSUMED = "Subsumed"
    DISCARDED = "Discarded"
    ARCHIVED = "Archived"

class BeliefObject:
    def __init__(self, factuality="Asserted", kinetic_mass=1.0):
        self.state = BeliefState.ACTIVE
        self.factuality = factuality
        self.kinetic_mass = kinetic_mass

    def apply_conflicting_evidence(self):
        if self.state == BeliefState.ACTIVE:
            self.state = BeliefState.CONTESTED

    def apply_refutation(self):
        if self.state == BeliefState.ACTIVE or self.state == BeliefState.CONTESTED:
            self.state = BeliefState.DISCARDED

class OuroborosEngine:
    MAX_KINETIC_MULTIPLIER = 2.0
    DECAY_FACTOR = 0.85

    @staticmethod
    def calculate_decay(initial_energy: float, distance: int) -> float:
        return initial_energy * (OuroborosEngine.DECAY_FACTOR ** distance)

class ShannonEngine:
    NCD_THRESHOLD = 0.15

    @staticmethod
    def should_collapse(ncd: float, mass_a: float, mass_b: float) -> bool:
        if ncd > ShannonEngine.NCD_THRESHOLD:
            return False
        max_mass = max(mass_a, mass_b)
        if max_mass == 0:
            return False
        mass_diff_ratio = abs(mass_a - mass_b) / max_mass
        return mass_diff_ratio < 0.15

class TestArchitectureClaims:
    """
    AX-044: Transubstanciación del CORTEX-PERSIST-WHITEPAPER.md a pruebas formales C5-REAL.
    """

    def test_belief_state_transitions(self):
        """Appendix A: Transiciones de estado de BeliefObjects"""
        bo = BeliefObject()
        assert bo.state == BeliefState.ACTIVE
        
        # conflicting evidence -> Contested
        bo.apply_conflicting_evidence()
        assert bo.state == BeliefState.CONTESTED

        # strong refutation -> Discarded
        bo.apply_refutation()
        assert bo.state == BeliefState.DISCARDED

    def test_ouroboros_kinetic_decay(self):
        """13.1 Kinetic Mass Layer (Ouroboros)"""
        e0 = 1.0
        e_1 = OuroborosEngine.calculate_decay(e0, 1)
        assert math.isclose(e_1, 0.85)

        e_10 = OuroborosEngine.calculate_decay(e0, 10)
        assert math.isclose(e_10, 0.19687, rel_tol=1e-3)

        # I3: Estabilidad en límite profundo (d=114, e < 1e-8)
        e_114 = OuroborosEngine.calculate_decay(e0, 114)
        assert e_114 < 1e-8

    def test_shannon_semantic_collapse(self):
        """13.2 Informational Entropy Layer (Shannon)"""
        # Debe colapsar si NCD < 0.15 y diferencia de masa < 15%
        assert ShannonEngine.should_collapse(ncd=0.10, mass_a=1.0, mass_b=1.1) == True
        
        # No debe colapsar si NCD > 0.15 (I6: Protección de Ortogonalidad)
        assert ShannonEngine.should_collapse(ncd=0.20, mass_a=1.0, mass_b=1.1) == False
        
        # No debe colapsar si diferencia de masa >= 15%
        assert ShannonEngine.should_collapse(ncd=0.10, mass_a=1.0, mass_b=1.2) == False
