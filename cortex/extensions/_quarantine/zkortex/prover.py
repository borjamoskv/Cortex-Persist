"""
ZKORTEX — Sovereign Prover.

El Prover es la entidad soberana: CORTEX mismo.
Tiene acceso a los secretos y genera pruebas sin exponerlos.

Arquitectura:
    ZKOrtexProver mantiene:
      1. Un MerkleTree del conocimiento activo
      2. Un registro de commitments emitidos
      3. La capacidad de generar pruebas verificables externamente

El Prover NUNCA exporta datos en plaintext — solo commitments y proofs.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from cortex.extensions._quarantine.zkortex.commitment import KnowledgeCommitment, commit
from cortex.extensions._quarantine.zkortex.merkle import MerkleTree, ZKMembershipProof
from cortex.extensions._quarantine.zkortex.range_proof import ZKRangeProof, prove_range

logger = logging.getLogger("cortex.extensions._quarantine.zkortex.prover")


@dataclass
class ProverSession:
    """Estado de una sesión de pruebas — el Prover controla su ciclo de vida."""

    session_id: str
    created_at: float = field(default_factory=time.time)
    proofs_issued: int = 0
    commitments_issued: int = 0


class ZKOrtexProver:
    """
    Orchestrador soberano de Zero-Knowledge Proofs para CORTEX.

    Responsabilidades:
      - Mantener el árbol Merkle del conocimiento privado
      - Emitir commitments y proofs sin revelar los hechos subyacentes
      - Registrar todas las pruebas emitidas (audit trail interno)

    Opacidad selectiva:
      - El mundo exterior ve: roots, commitments, proofs
      - El mundo exterior NUNCA ve: los hechos, las memorias, las fuentes
    """

    def __init__(self, session_id: str | None = None) -> None:
        import uuid

        self._session_id = session_id or str(uuid.uuid4())
        self._knowledge_base: list[str] = []
        self._tree: MerkleTree = MerkleTree()
        self._tree_built: bool = False
        self._commitments: dict[str, tuple[KnowledgeCommitment, bytes]] = {}
        self._session = ProverSession(session_id=self._session_id)

        logger.info("ZKOrtexProver initialized. Session: %s", self._session_id)

    # ─── Knowledge Management (Private) ──────────────────────────────────────

    def ingest(self, facts: list[str]) -> str:
        """
        Ingiere un conjunto de hechos en el árbol.
        Retorna el Merkle Root público — el único dato que sale.

        Los hechos originales jamás se exponen fuera del Prover.
        """
        self._knowledge_base = list(facts)
        root = self._tree.build(facts)
        self._tree_built = True
        logger.info(
            "Knowledge tree built. %d facts ingested. Root: %s", len(facts), root[:16] + "..."
        )
        return root

    @property
    def public_root(self) -> str:
        """El único dato del conjunto que puede publicarse libremente."""
        return self._tree.root_hex

    @property
    def knowledge_count(self) -> int:
        """Número de hechos conocidos — solo accesible internamente."""
        return len(self._knowledge_base)

    # ─── Commitment Generation ────────────────────────────────────────────────

    def commit_to_fact(
        self,
        fact_id: str,
        fact_content: str,
        metadata: dict[str, str] | None = None,
    ) -> KnowledgeCommitment:
        """
        Genera un commitment a `fact_content` bajo el identificador `fact_id`.
        Almacena el blinding factor internamente (necesario para abrir el commitment).

        El commitment puede publicarse. El contenido, no.
        """
        c, blinding = commit(fact_content)
        if metadata:
            # Reemplazar con metadata (commitment es frozen, creamos nuevo)
            from cortex.extensions._quarantine.zkortex.commitment import KnowledgeCommitment as KC

            c = KC(commitment_hex=c.commitment_hex, metadata=metadata)

        self._commitments[fact_id] = (c, blinding)
        self._session.commitments_issued += 1
        logger.debug("Commitment issued for fact_id='%s'", fact_id)
        return c

    def open_commitment(self, fact_id: str) -> tuple[str, KnowledgeCommitment] | None:
        """
        Abre un commitment — revela el hecho y el blinding factor.

        ADVERTENCIA: Abrir un commitment destruye su opacidad.
        Solo hacer si la auditoría soberana lo requiere explícitamente.
        """
        if fact_id not in self._commitments:
            return None
        commitment, blinding = self._commitments[fact_id]
        # Solo el Prover sabe el contenido original — aquí lo recuperaríamos
        # de nuestra base de conocimiento interna
        logger.warning(
            "Commitment OPENED for fact_id='%s'. Opacity compromised for this fact.", fact_id
        )
        return blinding.hex(), commitment

    # ─── Membership Proofs ────────────────────────────────────────────────────

    def prove_knows(self, fact: str, commitment_hex: str = "") -> ZKMembershipProof:
        """
        Prueba que CORTEX conoce `fact` (es miembro del conjunto)
        sin revelar ningún otro miembro.

        Raises RuntimeError si el árbol no ha sido construido.
        Raises ValueError si el hecho no está en el conjunto.
        """
        if not self._tree_built:
            raise RuntimeError("Knowledge tree not built. Call ingest() first.")

        proof = self._tree.prove(fact, element_commitment=commitment_hex)
        self._session.proofs_issued += 1
        logger.info(
            "Membership proof issued. Leaf index: %d. Root: %s",
            proof.leaf_index,
            proof.root[:16] + "...",
        )
        return proof

    # ─── Range Proofs ─────────────────────────────────────────────────────────

    def prove_knowledge_count_in_range(self, min_count: int, max_count: int) -> ZKRangeProof:
        """
        Prueba que la cantidad de hechos que CORTEX conoce ∈ [min_count, max_count].
        El número exacto permanece oculto.

        Ejemplo: "CORTEX tiene entre 100 y 10000 memorias sobre proyectos activos"
        sin revelar que son exactamente 4237.
        """
        actual = self.knowledge_count
        proof = prove_range(actual, min_count, max_count)
        self._session.proofs_issued += 1
        logger.info(
            "Range proof issued. Claimed: [%d, %d]. Actual: REDACTED.", min_count, max_count
        )
        return proof

    # ─── Session Stats ────────────────────────────────────────────────────────

    def session_stats(self) -> dict[str, Any]:
        """Estadísticas de la sesión — sin datos privados."""
        return {
            "session_id": self._session_id,
            "created_at": self._session.created_at,
            "proofs_issued": self._session.proofs_issued,
            "commitments_issued": self._session.commitments_issued,
            "tree_built": self._tree_built,
            "public_root": self.public_root if self._tree_built else None,
        }
