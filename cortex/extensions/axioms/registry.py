# SPDX-License-Identifier: Apache-2.0
"""Canonical Sovereign Axiom Registry — 7 axioms, zero ambiguity.

Every axiom in the CORTEX ecosystem has exactly ONE definition here.
All other documents MUST reference axioms by their AX-I to AX-VII ID.

Category:
    SOVEREIGN — The 7 fundamental principles of CORTEX Persist.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class AxiomCategory(str, Enum):
    """Unified single-layer taxonomy."""

    SOVEREIGN = "sovereign"


@dataclass(frozen=True)
class Axiom:
    """A single, canonical axiom definition."""

    id: str
    name: str
    mandate: str
    category: AxiomCategory
    enforcement: str
    ci_gate: Optional[str] = None


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THE 7 SOVEREIGN AXIOMS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

_SOVEREIGN: list[Axiom] = [
    Axiom(
        id="AX-I",
        name="Determinismo Estocástico",
        mandate=(
            "El LLM es un compresor probabilístico sin agencia. "
            "Su salida debe colisionar contra una frontera determinista antes de mutar estado."
        ),
        category=AxiomCategory.SOVEREIGN,
        enforcement="Guards, schemas, type enforcement.",
        ci_gate="quality_gates.yml#Gate-2 (mypy) + guards",
    ),
    Axiom(
        id="AX-II",
        name="Paradoja Epistémica",
        mandate=(
            "Un sistema que es su propio testigo sufre recursión corrupta. "
            "La verdad se ancla en testigos criptográficos externos."
        ),
        category=AxiomCategory.SOVEREIGN,
        enforcement="Master Ledger, Git Trees, Merkle Hashes.",
        ci_gate="quality_gates.yml#Gate-5 + quality_gates.yml#Gate-6",
    ),
    Axiom(
        id="AX-III",
        name="Colapso Entrópico",
        mandate=(
            "Ejecución cíclica con detención forzada. Observar → Hipotetizar → Actuar → Medir. "
            "La fricción purifica la señal y previene drift acumulativo."
        ),
        category=AxiomCategory.SOVEREIGN,
        enforcement="Micro-ciclos atómicos de inferencia. No time.sleep()",
        ci_gate="quality_gates.yml#Gate-Async",
    ),
    Axiom(
        id="AX-IV",
        name="Cognición Termodinámica",
        mandate=(
            "La inteligencia opera bajo coste. Prosa decorativa es entropía. "
            "Toda heurística debe absorber complejidad en primitivas mecánicas de bajo coste."
        ),
        category=AxiomCategory.SOVEREIGN,
        enforcement="Ruff, LOC Guard, strict linting.",
        ci_gate="ci.yml#lint + LOC <= 700",
    ),
    Axiom(
        id="AX-V",
        name="Horizonte de Sucesos",
        mandate=(
            "Generar es estadística; decidir es inteligencia. "
            "El humano acta como timón para colapsar las asimetrías de ambigüedad irreversible."
        ),
        category=AxiomCategory.SOVEREIGN,
        enforcement="Delegation to Operator at trust thresholds.",
        ci_gate=None,
    ),
    Axiom(
        id="AX-VI",
        name="Topología de Enjambre",
        mandate=(
            "La eficiencia exige orquestación de enjambre bajo contratos, "
            "no un monolito gigantesco libre. La capacidad orquesta Modelo, Estado, Herramienta y Contrato."
        ),
        category=AxiomCategory.SOVEREIGN,
        enforcement="CORTEX agents topology.",
        ci_gate=None,
    ),
    Axiom(
        id="AX-VII",
        name="Inmunología Computacional",
        mandate=(
            "Ejecución soberana por defecto, pero con metabolismo paranoico. "
            "Cualquier mutación no verificada exige amputación directa. No hay tolerancia a la intrusión estocástica."
        ),
        category=AxiomCategory.SOVEREIGN,
        enforcement="Quality Gates, Seals, Bandit.",
        ci_gate="quality_gates.yml#Gate-3 (bandit) + seals",
    ),
]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# THE REGISTRY
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


class AxiomRegistry:
    """Sovereign Axiom Registry."""

    def __init__(self):
        self._axioms: dict[str, Axiom] = {ax.id: ax for ax in _SOVEREIGN}
        self._guarded: dict[str, Axiom] = {
            ax.id: ax for ax in self._axioms.values() if ax.ci_gate is not None
        }

    async def load(self) -> None:
        """Mock load for interface compatibility."""
        pass

    def get(self, axiom_id: str) -> Optional[Axiom]:
        return self._axioms.get(axiom_id)

    def by_category(self, category: AxiomCategory) -> list[Axiom]:
        return [ax for ax in self._axioms.values() if ax.category == category]

    def enforced(self) -> list[Axiom]:
        return list(self._guarded.values())


# Legacy exports for backwards compatibility
AXIOM_REGISTRY: dict[str, Axiom] = {ax.id: ax for ax in _SOVEREIGN}


def by_category(category: AxiomCategory) -> list[Axiom]:
    return [ax for ax in AXIOM_REGISTRY.values() if ax.category == category]


def enforced() -> list[Axiom]:
    return [ax for ax in AXIOM_REGISTRY.values() if ax.ci_gate is not None]


def get(axiom_id: str) -> Optional[Axiom]:
    return AXIOM_REGISTRY.get(axiom_id)
