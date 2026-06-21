from pydantic import BaseModel, Field, field_validator, model_validator
from enum import Enum
import hashlib

class ConfidenceLevel(str, Enum):
    C5_REAL = "C5-REAL"
    C4_SIM  = "C4-SIM"
    C3_HYP  = "C3-HYP"

class LexiconLayer(str, Enum):
    HARDWARE              = "hardware_thermodynamics"
    MATHEMATICS           = "mathematics_core"
    CRYPTOGRAPHY          = "cryptography"
    ARCHITECTURE          = "architecture"
    ARCHITECTURE_INV      = "architecture_invariant"
    INFERENCE_OPT         = "inference_optimization"
    MEMORY_OPT            = "memory_optimization"
    DISTRIBUTED           = "distributed_systems"
    DISTRIBUTED_TRAINING  = "distributed_training"
    DATA_PIPELINE         = "data_pipeline"
    EPISTEMOLOGY          = "epistemology_engine"
    SWARM                 = "swarm_architecture"
    GOFAI                 = "gofai_symbolic"

class LexiconPrimitive(BaseModel):
    """
    Primitiva C5-REAL del AI GOAT Lexicon.
    Invariante: term_hash debe ser SHA3-256 del (term + definition).
    """
    term:        str            = Field(..., min_length=2)
    definition:  str            = Field(..., min_length=20)
    layer:       LexiconLayer
    confidence:  ConfidenceLevel = ConfidenceLevel.C5_REAL
    term_hash:   str            = Field(default="")

    @model_validator(mode="after")
    def compute_hash(self):
        if self.term and self.definition:
            raw = f"{self.term}::{self.definition}"
            self.term_hash = hashlib.sha3_256(raw.encode()).hexdigest()
        return self

    @field_validator("confidence")
    def reject_c4_sim(cls, v):
        if v == ConfidenceLevel.C4_SIM:
            raise ValueError(
                "P0 VIOLATION: C4-SIM output cannot enter the lexicon. "
                "Transmute to C5-REAL before injection."
            )
        return v


class LexiconLedger(BaseModel):
    """
    Ledger inmutable del lexicon completo.
    Invariante: ledger_hash = SHA3-256(∑ term_hash_i ordenados)
    """
    version:      str                   = "2.0.0"
    total_count:  int                   = Field(default=0)
    primitives:   list[LexiconPrimitive] = Field(default_factory=list)
    ledger_hash:  str                   = Field(default="")

    def compute_ledger_hash(self) -> str:
        """Calcula el hash raíz del ledger (Merkle-flat)."""
        sorted_hashes = sorted(p.term_hash for p in self.primitives)
        combined = "::".join(sorted_hashes)
        return hashlib.sha3_256(combined.encode()).hexdigest()

    def add_primitive(self, primitive: LexiconPrimitive) -> "LexiconLedger":
        """Append-only. Nunca muta. Retorna nuevo ledger."""
        existing_terms = {p.term for p in self.primitives}
        if primitive.term in existing_terms:
            raise ValueError(f"DUPLICATE PRIMITIVE: '{primitive.term}' ya existe en el ledger.")
        
        new_primitives = self.primitives + [primitive]
        new_ledger = LexiconLedger(
            version=self.version,
            total_count=len(new_primitives),
            primitives=new_primitives,
        )
        new_ledger.ledger_hash = new_ledger.compute_ledger_hash()
        return new_ledger
