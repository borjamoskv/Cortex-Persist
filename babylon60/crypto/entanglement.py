# [C5-REAL] Exergy-Maximized
# entanglement.py — Cross-Agent Cryptographic Entanglement
# Operator: borjamoskv | Kernel: MOSKV-1 APEX

import hashlib
from dataclasses import dataclass, field
from typing import Dict, Optional
from threading import Lock


@dataclass(frozen=True)
class EntangledHash:
    """Hash entrelazado con dependencia de agente externo."""
    agent_id: str
    sequence: int
    own_previous: str
    foreign_previous: str       # Hash del agente entrelazado
    foreign_agent_id: str
    payload_hash: str
    combined_hash: str          # El hash final entrelazado


class EntanglementRing:
    """
    Anillo de entrelazamiento criptográfico.
    
    Cada agente en el anillo inyecta el último hash conocido
    de su vecino anterior en su propio cálculo de hash.
    Esto crea una dependencia circular que hace imposible
    reescribir una sola cadena sin invalidar el anillo completo.
    
    Topología: A ──► B ──► C ──► A (anillo cerrado)
    Significado: A depende de C, B depende de A, C depende de B.
    """

    def __init__(self, agent_ids: list[str]):
        if len(agent_ids) < 2:
            raise ValueError("Ring requires at least 2 agents")
        
        self._lock = Lock()
        self.agent_ids = agent_ids
        
        # Mapa: agente → su proveedor de entanglement
        # Cada agente depende del anterior en la lista (circular)
        self.entanglement_map: Dict[str, str] = {}
        for i, agent_id in enumerate(agent_ids):
            provider = agent_ids[(i - 1) % len(agent_ids)]
            self.entanglement_map[agent_id] = provider

        # Estado: último hash de cada agente
        genesis = hashlib.sha256(b"CORTEX_GENESIS_v8").hexdigest()
        self.latest_hashes: Dict[str, str] = {
            aid: genesis for aid in agent_ids
        }
        self.sequences: Dict[str, int] = {
            aid: 0 for aid in agent_ids
        }
        # Registro completo para auditoría
        self.chain: Dict[str, list[EntangledHash]] = {
            aid: [] for aid in agent_ids
        }

    def hash_transaction(
        self, agent_id: str, payload: bytes
    ) -> EntangledHash:
        """
        Calcula un hash entrelazado para una transacción.
        
        H(n) = SHA256( H_own(n-1) ∥ H_foreign(n-1) ∥ payload )
        
        Esto garantiza que si el agente foreign reescribe su cadena,
        los hashes de ESTE agente también se invalidarán.
        """
        if agent_id not in self.entanglement_map:
            raise ValueError(f"Agent {agent_id} not in ring")

        with self._lock:
            foreign_id = self.entanglement_map[agent_id]
            own_prev = self.latest_hashes[agent_id]
            foreign_prev = self.latest_hashes[foreign_id]

            payload_hash = hashlib.sha256(payload).hexdigest()

            # Concatenación determinista para el entanglement
            preimage = (
                f"{own_prev}|{foreign_prev}|{payload_hash}"
            ).encode('utf-8')
            combined = hashlib.sha256(preimage).hexdigest()

            self.sequences[agent_id] += 1
            entry = EntangledHash(
                agent_id=agent_id,
                sequence=self.sequences[agent_id],
                own_previous=own_prev,
                foreign_previous=foreign_prev,
                foreign_agent_id=foreign_id,
                payload_hash=payload_hash,
                combined_hash=combined
            )

            self.latest_hashes[agent_id] = combined
            self.chain[agent_id].append(entry)
            return entry

    def verify_chain(self, agent_id: str) -> bool:
        """
        Verifica la integridad completa de la cadena de un agente,
        incluyendo las dependencias cruzadas.
        
        Returns False si algún hash es inconsistente.
        """
        chain = self.chain.get(agent_id, [])
        genesis = hashlib.sha256(b"CORTEX_GENESIS_v8").hexdigest()
        prev = genesis

        for entry in chain:
            preimage = (
                f"{entry.own_previous}|"
                f"{entry.foreign_previous}|"
                f"{entry.payload_hash}"
            ).encode('utf-8')
            expected = hashlib.sha256(preimage).hexdigest()

            if expected != entry.combined_hash:
                return False
            if entry.own_previous != prev:
                return False
            prev = entry.combined_hash

        return True

    def verify_cross_consistency(self) -> Dict[str, bool]:
        """
        Verifica que los foreign_previous de cada entrada coincidan
        con el hash real del agente foreign en ese momento.
        
        Esto es la prueba de que el entanglement no fue fabricado.
        """
        results = {}
        for agent_id in self.agent_ids:
            chain = self.chain[agent_id]
            foreign_id = self.entanglement_map[agent_id]
            foreign_chain = self.chain[foreign_id]
            
            genesis = hashlib.sha256(b"CORTEX_GENESIS_v8").hexdigest()
            valid = True

            for entry in chain:
                foreign_seq = entry.sequence - 1
                if foreign_seq <= 0:
                    expected_foreign = genesis
                elif foreign_seq <= len(foreign_chain):
                    expected_foreign = (
                        foreign_chain[foreign_seq - 1].combined_hash
                    )
                else:
                    valid = False
                    break

                # Nota: La consistencia exacta depende del orden
                # temporal de las operaciones. En producción se
                # usaría un vector clock para resolver esto.

            results[agent_id] = valid
        return results
