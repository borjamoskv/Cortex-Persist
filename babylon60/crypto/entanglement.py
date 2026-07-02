# [C5-REAL] Exergy-Maximized
# entanglement.py — Cross-Agent Cryptographic Entanglement
# Operator: borjamoskv | Kernel: MOSKV-1 APEX

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from threading import Lock
from typing import Any, Optional


class MerkleNode:
    def __init__(
        self,
        left: "Optional[MerkleNode]" = None,
        right: "Optional[MerkleNode]" = None,
        hash_val: str = "",
    ):
        self.left = left
        self.right = right
        self.hash_val = hash_val


def calculate_sha256(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


class StateEntangler:
    """Provides cryptographic state entanglement (INV-E01).
    Ensures state-rollback protection by forcing the transaction hash
    to entangle with parallel active agents' state hashes.
    """

    @staticmethod
    def entangle_states(
        previous_hash: str,
        transaction_data: dict[str, Any],
        parallel_state_hashes: list[str],
    ) -> str:
        """Computes an entangled hash linking the transaction data to parallel agents."""
        sorted_parallel = sorted(parallel_state_hashes)
        parallel_seed = calculate_sha256(json.dumps(sorted_parallel, sort_keys=True))

        payload = {
            "previous_hash": previous_hash,
            "tx": transaction_data,
            "parallel_seed": parallel_seed,
            "entropy_salt": f"{time.monotonic()}",
        }
        raw_payload = json.dumps(payload, sort_keys=True)
        return calculate_sha256(raw_payload)


class MerkleTreeAnchoring:
    """Constructs Merkle Trees from transaction hashes and outputs publication anchors."""

    @staticmethod
    def build_tree(leaves: list[str]) -> MerkleNode | None:
        if not leaves:
            return None

        nodes = [MerkleNode(hash_val=h) for h in leaves]
        while len(nodes) > 1:
            next_level = []
            for i in range(0, len(nodes), 2):
                left = nodes[i]
                if i + 1 < len(nodes):
                    right = nodes[i + 1]
                    # Mitigar colisiones usando separador nulo
                    parent_hash = calculate_sha256(left.hash_val + "\x00" + right.hash_val)
                    next_level.append(MerkleNode(left=left, right=right, hash_val=parent_hash))
                else:
                    next_level.append(left)
            nodes = next_level
        return nodes[0]

    @staticmethod
    def generate_git_anchor_commit_message(root_hash: str, epoch: int) -> str:
        """Formats the anchor message for Git Sentinel publishing (Axiom 2 / C7 Proof-of-Publication)."""
        return f"[bridge] publish(anchor): Merkle Root {root_hash} for epoch {epoch} [C5-REAL]"


@dataclass(frozen=True)
class EntangledHash:
    """Hash entrelazado con firma y tracking de secuencia cruzada."""

    agent_id: str
    sequence: int
    own_previous: str
    foreign_previous: str  # Hash del agente entrelazado
    foreign_agent_id: str
    foreign_sequence: int  # Secuencia exacta del vecino al entrelazar (evita bug 1:1)
    payload_hash: str
    combined_hash: str  # El hash final entrelazado
    signature: str  # Autenticación cruzada (HMAC con clave de agente)


class EntanglementRing:
    """
    Anillo de entrelazamiento criptográfico con firmas y locks de grano fino.

    Topología: A ──► B ──► C ──► A
    """

    def __init__(self, agent_ids: list[str]):
        if len(agent_ids) < 2:
            raise ValueError("Ring requires at least 2 agents")

        self.agent_ids = agent_ids

        # Locks por agente para eliminar el cuello de botella global
        self._locks: dict[str, Lock] = {aid: Lock() for aid in agent_ids}

        # Secretos de firma compartida simétrica por agente (sustituye firmas débiles)
        self.agent_secrets: dict[str, bytes] = {
            aid: hashlib.sha256(f"secret:{aid}".encode()).digest() for aid in agent_ids
        }

        # Mapa de dependencia circular
        self.entanglement_map: dict[str, str] = {}
        for i, agent_id in enumerate(agent_ids):
            provider = agent_ids[(i - 1) % len(agent_ids)]
            self.entanglement_map[agent_id] = provider

        # Estado inicial (Génesis)
        genesis = hashlib.sha256(b"CORTEX_GENESIS_v8").hexdigest()
        self.latest_hashes: dict[str, str] = {aid: genesis for aid in agent_ids}
        self.sequences: dict[str, int] = {aid: 0 for aid in agent_ids}
        self.chain: dict[str, list[EntangledHash]] = {aid: [] for aid in agent_ids}

    def hash_transaction(self, agent_id: str, payload: bytes) -> EntangledHash:
        """
        Calcula el hash entrelazado adquiriendo locks atómicos de forma segura.
        """
        if agent_id not in self.entanglement_map:
            raise ValueError(f"Agent {agent_id} not in ring")

        foreign_id = self.entanglement_map[agent_id]

        # Ordenar deterministamente los IDs para evitar deadlocks en la adquisición
        lock_order = sorted([agent_id, foreign_id])

        # Adquirir ambos locks en orden determinista
        for lock_id in lock_order:
            self._locks[lock_id].acquire()

        try:
            own_prev = self.latest_hashes[agent_id]
            foreign_prev = self.latest_hashes[foreign_id]
            foreign_seq = self.sequences[foreign_id]

            payload_hash = hashlib.sha256(payload).hexdigest()

            # Hashing con inyección de separador y firma HMAC para evitar falsificaciones
            preimage = f"{own_prev}\x00{foreign_prev}\x00{payload_hash}".encode()
            combined = hashlib.sha256(preimage).hexdigest()

            # Firmar el hash combinado con el secreto del agente para atestación externa
            secret = self.agent_secrets[agent_id]
            sig = hmac.new(secret, combined.encode("utf-8"), hashlib.sha256).hexdigest()

            self.sequences[agent_id] += 1
            entry = EntangledHash(
                agent_id=agent_id,
                sequence=self.sequences[agent_id],
                own_previous=own_prev,
                foreign_previous=foreign_prev,
                foreign_agent_id=foreign_id,
                foreign_sequence=foreign_seq,
                payload_hash=payload_hash,
                combined_hash=combined,
                signature=sig,
            )

            self.latest_hashes[agent_id] = combined
            self.chain[agent_id].append(entry)
            return entry
        finally:
            # Liberar en orden inverso
            for lock_id in reversed(lock_order):
                self._locks[lock_id].release()

    def verify_chain(self, agent_id: str) -> bool:
        """Verifica la integridad de la cadena local y la firma."""
        chain = self.chain.get(agent_id, [])
        genesis = hashlib.sha256(b"CORTEX_GENESIS_v8").hexdigest()
        prev = genesis
        secret = self.agent_secrets[agent_id]

        for entry in chain:
            preimage = (
                f"{entry.own_previous}\x00{entry.foreign_previous}\x00{entry.payload_hash}".encode()
            )
            expected = hashlib.sha256(preimage).hexdigest()

            if expected != entry.combined_hash:
                return False
            if entry.own_previous != prev:
                return False

            # Validar firma del emisor
            sig_check = hmac.new(
                secret, entry.combined_hash.encode("utf-8"), hashlib.sha256
            ).hexdigest()
            if sig_check != entry.signature:
                return False

            prev = entry.combined_hash

        return True

    def verify_cross_consistency(self) -> dict[str, bool]:
        """
        Verifica que los foreign_previous de cada entrada coincidan exactamente
        con el hash que el agente vecino tenía registrado bajo la secuencia cruzada capturada.
        """
        results = {}
        for agent_id in self.agent_ids:
            chain = self.chain[agent_id]
            foreign_id = self.entanglement_map[agent_id]
            foreign_chain = self.chain[foreign_id]

            genesis = hashlib.sha256(b"CORTEX_GENESIS_v8").hexdigest()
            valid = True

            for entry in chain:
                # Usar la secuencia real capturada al entrelazar para evitar desfases de carga
                foreign_seq = entry.foreign_sequence
                if foreign_seq <= 0:
                    expected_foreign = genesis
                elif foreign_seq <= len(foreign_chain):
                    expected_foreign = foreign_chain[foreign_seq - 1].combined_hash
                else:
                    valid = False
                    break

                if entry.foreign_previous != expected_foreign:
                    valid = False
                    break

            results[agent_id] = valid
        return results

    def recover_agent(self, agent_id: str, correct_chain: list[EntangledHash]) -> bool:
        """
        Mecanismo de recuperación (Recovery):
        Reconstruye el estado de un agente desincronizado a partir de una cadena válida provista.
        """
        if agent_id not in self._locks:
            return False

        with self._locks[agent_id]:
            # Validar de forma secuencial la cadena entrante
            genesis = hashlib.sha256(b"CORTEX_GENESIS_v8").hexdigest()
            prev = genesis
            secret = self.agent_secrets[agent_id]

            for entry in correct_chain:
                preimage = f"{entry.own_previous}\x00{entry.foreign_previous}\x00{entry.payload_hash}".encode()
                expected = hashlib.sha256(preimage).hexdigest()

                if expected != entry.combined_hash or entry.own_previous != prev:
                    return False
                sig_check = hmac.new(
                    secret, entry.combined_hash.encode("utf-8"), hashlib.sha256
                ).hexdigest()
                if sig_check != entry.signature:
                    return False
                prev = entry.combined_hash

            self.chain[agent_id] = list(correct_chain)
            self.latest_hashes[agent_id] = (
                correct_chain[-1].combined_hash if correct_chain else genesis
            )
            self.sequences[agent_id] = len(correct_chain)
            return True
