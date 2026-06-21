import pytest
from pydantic import ValidationError
from legacy_research.types.lexicon_schema import (
    LexiconPrimitive, LexiconLedger, LexiconLayer, ConfidenceLevel
)

@pytest.fixture
def full_ledger():
    ledger = LexiconLedger()
    layers = [
        LexiconLayer.HARDWARE,
        LexiconLayer.MATHEMATICS,
        LexiconLayer.CRYPTOGRAPHY,
        LexiconLayer.ARCHITECTURE,
        LexiconLayer.INFERENCE_OPT,
        LexiconLayer.DATA_PIPELINE,
        LexiconLayer.EPISTEMOLOGY,
        LexiconLayer.SWARM,
    ]
    for i, layer in enumerate(layers):
        p = LexiconPrimitive(
            term=f"Term_{i}",
            definition=f"This is a valid definition for Term_{i} that exceeds 20 chars.",
            layer=layer,
        )
        ledger = ledger.add_primitive(p)
    return ledger

class TestInvariants:
    """AX-041: Todo estado persiste via hash criptográfico."""

    def test_term_hash_is_deterministic(self):
        """El mismo term+definition siempre produce el mismo hash."""
        p1 = LexiconPrimitive(
            term="KAN", 
            definition="Kolmogorov-Arnold Networks con splines en aristas.",
            layer=LexiconLayer.MATHEMATICS,
        )
        p2 = LexiconPrimitive(
            term="KAN", 
            definition="Kolmogorov-Arnold Networks con splines en aristas.",
            layer=LexiconLayer.MATHEMATICS,
        )
        assert p1.term_hash == p2.term_hash

    def test_c4_sim_physically_rejected(self):
        """L3.5: C4-SIM jamás entra al ledger."""
        with pytest.raises(ValidationError, match="C4-SIM"):
            LexiconPrimitive(
                term="Theater",
                definition="Green theater narrative output",
                layer=LexiconLayer.EPISTEMOLOGY,
                confidence=ConfidenceLevel.C4_SIM,
            )

    def test_ledger_is_append_only(self):
        """El ledger no permite mutación, solo extensión."""
        ledger = LexiconLedger()
        p = LexiconPrimitive(
            term="Parquet",
            definition="Almacenamiento columnar binario inmutable.",
            layer=LexiconLayer.DATA_PIPELINE,
        )
        new_ledger = ledger.add_primitive(p)
        
        assert ledger.total_count == 0
        assert new_ledger.total_count == 1

    def test_duplicate_primitive_rejected(self):
        """No puede existir la misma primitiva dos veces."""
        ledger = LexiconLedger()
        p = LexiconPrimitive(
            term="DAG",
            definition="Grafo acíclico dirigido de dependencias causales.",
            layer=LexiconLayer.DATA_PIPELINE,
        )
        ledger = ledger.add_primitive(p)
        
        with pytest.raises(ValueError, match="DUPLICATE PRIMITIVE"):
            ledger.add_primitive(p)

    def test_ledger_hash_changes_on_extension(self):
        """Cada extensión del ledger produce un hash raíz diferente."""
        ledger = LexiconLedger()
        hash_0 = ledger.compute_ledger_hash()
        
        p = LexiconPrimitive(
            term="Memristor",
            definition="Resistencia con memoria que fusiona compute y storage.",
            layer=LexiconLayer.HARDWARE,
        )
        ledger = ledger.add_primitive(p)
        hash_1 = ledger.compute_ledger_hash()
        
        assert hash_0 != hash_1

    def test_definition_minimum_signal(self):
        """R12: Toda definición debe tener mínimo 20 caracteres de señal."""
        with pytest.raises(ValidationError):
            LexiconPrimitive(
                term="Test",
                definition="Short",  # < 20 chars → rechazado
                layer=LexiconLayer.EPISTEMOLOGY,
            )

class TestCoverage:
    """Verifica que todas las capas ontológicas tienen cobertura."""

    REQUIRED_LAYERS = {
        LexiconLayer.HARDWARE,
        LexiconLayer.MATHEMATICS,
        LexiconLayer.CRYPTOGRAPHY,
        LexiconLayer.ARCHITECTURE,
        LexiconLayer.INFERENCE_OPT,
        LexiconLayer.DATA_PIPELINE,
        LexiconLayer.EPISTEMOLOGY,
        LexiconLayer.SWARM,
    }

    def test_all_critical_layers_represented(self, full_ledger):
        """El ledger completo debe cubrir todas las capas críticas."""
        present_layers = {p.layer for p in full_ledger.primitives}
        missing = self.REQUIRED_LAYERS - present_layers
        assert not missing, f"CAPAS SIN COBERTURA: {missing}"
