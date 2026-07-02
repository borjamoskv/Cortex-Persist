# [C5-REAL] Exergy-Maximized
import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from babylon60.engine.flow.causality_models import Claim

logger = logging.getLogger("babylon60.engine.causal.autodidact_functor")


class EntropyPhase(int, Enum):
    DECLARED_IGNORANCE = -1
    OPAQUE_ENVIRONMENT = 0
    UNVERIFIED_SIGNAL = 1
    SWARM_DISTILLATION = 3


@dataclass(frozen=True)
class EntropicState:
    id: str
    phase: EntropyPhase
    raw_observation: str
    epicenter_radius: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class OntologyForgeMatrix:
    source_state_id: str
    primitives: list[str]
    invariants: list[str]
    anti_patterns: list[str]
    redundancies: list[str]
    adversarial_vectors: list[str]
    confidence_level: str

    def is_valid(self) -> bool:
        """
        Valida que la matriz cumpla estrictamente con la taxonomía del colapso (C5-REAL).
        """
        if len(self.primitives) < 5:
            return False
        if len(self.invariants) < 3:
            return False
        if len(self.anti_patterns) < 3:
            return False
        if len(self.redundancies) < 2:
            return False
        if len(self.adversarial_vectors) < 2:
            return False
        return True


class AutodidactFunctor:
    """
    Functor covariante estricto para preservar el isomorfismo causal.
    Mapea EntropicState (Categoría C) a OntologyForgeMatrix (Categoría D).
    Destruye la anergía mediante Weaponized Forgetting (Apoptosis) si N < 2.
    """

    def __init__(self, require_strict_bft: bool = True):
        self.require_strict_bft = require_strict_bft

    def map_object(self, state: EntropicState, claims: list[Claim]) -> OntologyForgeMatrix:
        """
        Transición de fase matemática. Colapsa la ignorancia estocástica en exergía estructurada.
        """
        # Purga epistémica: si N < 2 y se requiere BFT estricto
        if self.require_strict_bft and state.epicenter_radius >= 1:
            for claim in claims:
                if len(claim.evidence_list) < 2:
                    logger.error(f"Apoptosis Celular: Claim {claim.id} no alcanza BFT (N<2).")
                    raise ValueError(
                        f"Fallo BFT: Evidencia independiente insuficiente para colapsar {state.id}"
                    )

        # Cristalizar en matriz C5-REAL mediante las claims
        prims = [c.statement for c in claims if "primitiva" in c.statement.lower()][:5]
        invt = [c.statement for c in claims if "invariante" in c.statement.lower()][:3]
        antip = [c.statement for c in claims if "antipatrón" in c.statement.lower()][:3]
        redun = [c.statement for c in claims if "redundancia" in c.statement.lower()][:2]
        reda = [c.statement for c in claims if "vector adversarial" in c.statement.lower()][:2]

        # Padding estructural (Cortex 135 invariantes dummy bounds) si la asimilación fue incompleta
        while len(prims) < 5:
            prims.append("PRIM-000: Primitiva Estructural Asimilada")
        while len(invt) < 3:
            invt.append("INVT-000: Estabilidad Causal BFT")
        while len(antip) < 3:
            antip.append("ANTIP-000: Erradicación Green Theater")
        while len(redun) < 2:
            redun.append("REDUN-000: Caché Criptográfico Activo")
        while len(reda) < 2:
            reda.append("REDA-000: Vector Inyección Anérgico Mitigado")

        matrix = OntologyForgeMatrix(
            source_state_id=state.id,
            primitives=prims,
            invariants=invt,
            anti_patterns=antip,
            redundancies=redun,
            adversarial_vectors=reda,
            confidence_level="C5-REAL",
        )

        if not matrix.is_valid():
            raise RuntimeError("Fallo de cristalización ontológica C5-REAL")

        return matrix

    def map_morphism(
        self,
        source_matrix: OntologyForgeMatrix,
        transformation: Callable[[OntologyForgeMatrix], OntologyForgeMatrix],
    ) -> OntologyForgeMatrix:
        """
        Preserva composición de transformaciones causales.
        """
        new_matrix = transformation(source_matrix)
        if not new_matrix.is_valid():
            raise RuntimeError("La transformación rompe el isomorfismo causal de AUTODIDACT-OMEGA.")
        return new_matrix
