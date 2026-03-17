"""
ZKORTEX — Sovereign Opacity Layer.

Capa de integración entre ZKORTEX y cortex.crypto.aes.

La Opacidad Selectiva opera en dos niveles:
  L1 (Cryptographic): AES-GCM cifra el contenido en reposo
  L2 (Zero-Knowledge): ZK proofs permiten demostrar conocimiento del contenido
                       sin descifrar

El flujo completo:
    1. CORTEX ingiere un hecho → AES-GCM encrypt → almacena ciphertext (L1)
    2. CORTEX construye Merkle Tree sobre los hashes de los hechos → root (L2)
    3. External query: "¿Sabes X?"
       → CORTEX genera ZKMembershipProof → verifier confirma → L1 nunca se toca

Caso de uso soberano:
    "Auditor quiere confirmar que CORTEX tiene más de 1000 memorias de proyecto"
    → Range proof: "CORTEX tiene entre 1000 y ∞ memorias"
    → Sin revelar: cuántas exactamente, qué proyectos, ni ningún contenido
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any

from cortex.extensions.zkortex.commitment import KnowledgeCommitment
from cortex.extensions.zkortex.merkle import ZKMembershipProof
from cortex.extensions.zkortex.prover import ZKOrtexProver
from cortex.extensions.zkortex.range_proof import ZKRangeProof

logger = logging.getLogger("cortex.extensions.zkortex.opacity")


class SovereignOpacityLayer:
    """
    La membrana semipermeable entre CORTEX y el mundo.

    Administra:
      - El Merkle tree sobre fact-fingerprints (SHA-256 de cada hecho cifrado)
      - La emisión soberana de proofs (control total de qué se demuestra)
      - El registro de pruebas emitidas (accountability interna sin exposición)

    Estrategia de opacidad:
      - HIGH (default): Solo Merkle roots y proofs de membresía.
                        Nunca commitments abiertos.
      - MEDIUM: Permite range proofs. El rango revela magnitud pero no valor.
      - SELECTIVE: El operador soberano decide caso por caso qué abrir.
    """

    STRATEGY_HIGH = "HIGH"
    STRATEGY_MEDIUM = "MEDIUM"
    STRATEGY_SELECTIVE = "SELECTIVE"

    def __init__(
        self,
        opacity_strategy: str = STRATEGY_HIGH,
        session_id: str | None = None,
    ) -> None:
        self._strategy = opacity_strategy
        self._prover = ZKOrtexProver(session_id=session_id)
        self._fingerprint_to_original: dict[str, str] = {}  # solo en memoria, nunca persiste
        self._proof_log: list[dict[str, Any]] = []
        logger.info("SovereignOpacityLayer initialized. Strategy: %s", opacity_strategy)

    # ─── Ingestion ─────────────────────────────────────────────────────────────

    def ingest_facts(self, facts: list[str]) -> str:
        """
        Ingiere hechos en el árbol ZK.

        CRUCIAL: Los hechos originales NUNCA deben ser texto plano en producción.
        En producción, `facts` deben ser fingerprints de los AES-GCM ciphertexts,
        no los textos originales.

        Retorna: El Merkle Root público.
        """
        # Fingerprinting: H("zkortex:fact:" || content)
        fingerprints = []
        for fact in facts:
            fp = hashlib.sha256(b"zkortex:fact:" + fact.encode()).hexdigest()
            self._fingerprint_to_original[fp] = fact  # mapa inverso, solo en memoria
            fingerprints.append(fp)

        root = self._prover.ingest(fingerprints)
        logger.info(
            "SovereignOpacityLayer: %d facts ingested. Root: %s", len(facts), root[:16] + "..."
        )
        return root

    # ─── Proof Emission ────────────────────────────────────────────────────────

    def prove_knows_fact(self, fact_content: str) -> ZKMembershipProof | None:
        """
        Genera una prueba de que CORTEX conoce `fact_content`.

        En HIGH strategy: Solo emite la proof, nunca el contenido.
        Retorna None si el hecho no está en el árbol.
        """
        fp = hashlib.sha256(b"zkortex:fact:" + fact_content.encode()).hexdigest()

        try:
            proof = self._prover.prove_knows(fp)
            self._log_proof("membership", {"leaf_index": proof.leaf_index})
            return proof
        except ValueError:
            logger.warning("prove_knows_fact: fact not in sovereign knowledge set.")
            return None

    def prove_count_in_range(self, min_count: int, max_count: int) -> ZKRangeProof | None:
        """
        Prueba que el número de hechos conocidos ∈ [min_count, max_count].
        Solo disponible en MEDIUM o SELECTIVE strategy.
        """
        if self._strategy == self.STRATEGY_HIGH:
            logger.warning(
                "Range proof blocked by HIGH opacity strategy. "
                "Switch to MEDIUM or SELECTIVE to enable."
            )
            return None

        try:
            proof = self._prover.prove_knowledge_count_in_range(min_count, max_count)
            self._log_proof("range", {"min": min_count, "max": max_count})
            return proof
        except ValueError as e:
            logger.error("Range proof failed: %s", e)
            return None

    def commit_to_knowledge(
        self,
        fact_id: str,
        fact_content: str,
        metadata: dict[str, str] | None = None,
    ) -> KnowledgeCommitment:
        """
        Emite un commitment al hecho (no el hecho en sí).
        El commitment puede compartirse públicamente.
        """
        commitment = self._prover.commit_to_fact(fact_id, fact_content, metadata)
        self._log_proof("commitment", {"fact_id": fact_id})
        return commitment

    # ─── Public Interface ──────────────────────────────────────────────────────

    @property
    def public_root(self) -> str | None:
        """El único identificador público del knowledge set de CORTEX."""
        try:
            return self._prover.public_root
        except RuntimeError:
            return None

    def public_status(self) -> dict[str, Any]:
        """
        Estado público de la capa de opacidad.
        Zero datos privados. Máxima información estructural.
        """
        stats = self._prover.session_stats()
        return {
            "opacity_strategy": self._strategy,
            "public_root": self.public_root,
            "session_id": stats["session_id"],
            "proofs_emitted": stats["proofs_issued"],
            "commitments_emitted": stats["commitments_issued"],
            "knowledge_tree_active": stats["tree_built"],
            "timestamp": time.time(),
        }

    # ─── Internal ──────────────────────────────────────────────────────────────

    def _log_proof(self, proof_type: str, meta: dict[str, Any]) -> None:
        """Registro interno de auditoría — sin datos privados."""
        self._proof_log.append(
            {
                "type": proof_type,
                "timestamp": time.time(),
                **meta,
            }
        )

    def proof_audit_log(self) -> list[dict[str, Any]]:
        """Audit log de proofs emitidas. Solo metadatos, nunca contenido."""
        return list(self._proof_log)
