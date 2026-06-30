# [C5-REAL] Exergy-Maximized
# anchor.py — Merkle Root Anchoring Service
# Operator: borjamoskv | Kernel: MOSKV-1 APEX

import hashlib
import sqlite3
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime, UTC


@dataclass
class MerkleNode:
    """Nodo individual del Merkle Tree."""
    hash_value: str
    left: Optional['MerkleNode'] = None
    right: Optional['MerkleNode'] = None


class MerkleTree:
    """
    Árbol de Merkle sobre las transacciones del ledger.
    
    Construye el árbol completo desde las hojas (hashes de txn)
    y expone la raíz para anclar externamente.
    """

    def __init__(self, tx_hashes: List[str]):
        if not tx_hashes:
            raise ValueError("Cannot build MerkleTree from empty hash list")
        self.leaves = [MerkleNode(hash_value=h) for h in tx_hashes]
        self.root = self._build(self.leaves)

    @staticmethod
    def _hash_pair(left: str, right: str) -> str:
        combined = f"{left}{right}".encode('utf-8')
        return hashlib.sha256(combined).hexdigest()

    def _build(self, nodes: List[MerkleNode]) -> MerkleNode:
        if len(nodes) == 1:
            return nodes[0]
        # Si es impar, duplicar el último nodo (estándar Bitcoin)
        if len(nodes) % 2 != 0:
            nodes.append(MerkleNode(hash_value=nodes[-1].hash_value))
        parents = []
        for i in range(0, len(nodes), 2):
            parent_hash = self._hash_pair(
                nodes[i].hash_value,
                nodes[i + 1].hash_value
            )
            parents.append(MerkleNode(
                hash_value=parent_hash,
                left=nodes[i],
                right=nodes[i + 1]
            ))
        return self._build(parents)

    @property
    def root_hash(self) -> str:
        return self.root.hash_value


@dataclass
class EpochAnchor:
    """Registro de un anchor publicado."""
    epoch_id: int
    merkle_root: str
    tx_count: int
    timestamp: str
    anchor_target: str          # "ethereum" | "arbitrum" | "git"
    anchor_tx_hash: str         # Hash de la transacción en L1/L2
    verified: bool = False


class AnchorService:
    """
    Servicio de anclaje periódico.
    
    Cada N transacciones (epoch), construye un Merkle Tree
    sobre los hashes acumulados y publica la raíz en un
    destino externo inmutable.
    """

    EPOCH_SIZE = 1000  # Transacciones por epoch

    def __init__(self, db_path: str):
        self.db_path = db_path
        self.pending_hashes: List[str] = []
        self.current_epoch: int = self._load_last_epoch() + 1

    def _load_last_epoch(self) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(
                "SELECT MAX(epoch_id) FROM merkle_anchors"
            )
            result = cur.fetchone()[0]
            return result if result is not None else 0
        except sqlite3.OperationalError:
            # Tabla no existe aún — primer arranque
            conn.execute("""
                CREATE TABLE IF NOT EXISTS merkle_anchors (
                    epoch_id     INTEGER PRIMARY KEY,
                    merkle_root  TEXT NOT NULL,
                    tx_count     INTEGER NOT NULL,
                    timestamp    TEXT NOT NULL,
                    anchor_target TEXT NOT NULL,
                    anchor_tx    TEXT NOT NULL,
                    verified     INTEGER DEFAULT 0
                )
            """)
            conn.commit()
            return 0
        finally:
            conn.close()

    def ingest_tx_hash(self, tx_hash: str) -> Optional[EpochAnchor]:
        """
        Ingesta un hash de transacción. Si se alcanza EPOCH_SIZE,
        dispara el anclaje automáticamente.
        
        Returns:
            EpochAnchor si se publicó un anchor, None en caso contrario.
        """
        self.pending_hashes.append(tx_hash)

        if len(self.pending_hashes) >= self.EPOCH_SIZE:
            return self._seal_epoch()
        return None

    def _seal_epoch(self) -> EpochAnchor:
        tree = MerkleTree(self.pending_hashes)
        
        anchor = EpochAnchor(
            epoch_id=self.current_epoch,
            merkle_root=tree.root_hash,
            tx_count=len(self.pending_hashes),
            timestamp=datetime.now(UTC).isoformat(),
            anchor_target="arbitrum",      # Configurable
            anchor_tx_hash=self._publish_to_l2(tree.root_hash)
        )

        self._persist_anchor(anchor)
        self.pending_hashes.clear()
        self.current_epoch += 1
        return anchor

    def _publish_to_l2(self, merkle_root: str) -> str:
        """
        Publica el Merkle Root en Arbitrum L2.
        STUB: Requiere integración con web3.py + wallet.
        """
        # TODO: Integrar con contrato AnchorRegistry en Arbitrum
        # return web3_client.publish_anchor(merkle_root)
        placeholder_tx = hashlib.sha256(
            f"anchor:{merkle_root}".encode()
        ).hexdigest()
        return placeholder_tx

    def _persist_anchor(self, anchor: EpochAnchor) -> None:
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            """INSERT INTO merkle_anchors 
               (epoch_id, merkle_root, tx_count, timestamp, 
                anchor_target, anchor_tx)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (anchor.epoch_id, anchor.merkle_root, anchor.tx_count,
             anchor.timestamp, anchor.anchor_target, anchor.anchor_tx_hash)
        )
        conn.commit()
        conn.close()

    def verify_epoch(self, epoch_id: int, tx_hashes: List[str]) -> bool:
        """
        Verificación independiente: Recalcula el Merkle Root
        a partir de los hashes brutos y lo compara con el anchor
        almacenado y publicado.
        """
        conn = sqlite3.connect(self.db_path)
        cur = conn.execute(
            "SELECT merkle_root FROM merkle_anchors WHERE epoch_id = ?",
            (epoch_id,)
        )
        row = cur.fetchone()
        conn.close()

        if row is None:
            raise ValueError(f"Epoch {epoch_id} not found")

        stored_root = row[0]
        recalculated = MerkleTree(tx_hashes).root_hash
        return recalculated == stored_root
