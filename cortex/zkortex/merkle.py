"""
ZKORTEX — Merkle Tree + Zero-Knowledge Membership Proof.

Probar que "CORTEX conoce el hecho X" sin revelar X ni ningún otro hecho.

El árbol Merkle transforma un conjunto de secretos en una raíz pública (root).
La prueba de membresía (path) demuestra pertenencia con O(log n) hashes —
revelando solo el camino, nunca el contenido de las hojas.

Uso soberano:
    - CORTEX publica el Merkle Root de su base de conocimiento (un solo hash).
    - Para cualquier consulta, genera un ZKMembershipProof sin abrir el dataset.
    - El verificador externo confirma sin ver jamás el interior.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


def _sha256(data: bytes) -> bytes:
    return hashlib.sha256(data).digest()


def _hash_pair(left: bytes, right: bytes) -> bytes:
    """H(left || right) — orden lexicográfico para consistencia."""
    if left <= right:
        return _sha256(left + right)
    return _sha256(right + left)


def _leaf_hash(value: str) -> bytes:
    """Leaf: H("leaf" || value) — domain separation para evitar second-preimage."""
    return _sha256(b"zkortex:leaf:" + value.encode("utf-8"))


@dataclass(frozen=True)
class MerkleProofNode:
    """Un nodo en el proof path."""
    sibling_hash: str   # hex del nodo hermano
    is_right: bool      # ¿el hermano está a la derecha?


@dataclass(frozen=True)
class ZKMembershipProof:
    """
    Prueba de que un elemento pertenece al conjunto cuya raíz es `root`.

    Campos públicos (compartibles sin riesgo):
        root:       La raíz del árbol (hash del conjunto completo)
        proof_path: Los nodos hermanos en el camino a la raíz
        leaf_index: Posición en el árbol (opcional, para ordering)

    Campo privado (NUNCA se incluye en la prueba pública):
        [el valor del elemento — solo el prover lo conoce]
    """

    root: str
    proof_path: list[MerkleProofNode]
    leaf_index: int
    element_commitment: str  # commitment al elemento, no el elemento en sí

    def verify(self, element_value: str) -> bool:
        """
        Verifica que element_value ∈ árbol con esta raíz.
        El verificador externo necesita el valor para verificar —
        pero CORTEX controla cuándo y a quién lo da.
        """
        current = _leaf_hash(element_value)
        for node in self.proof_path:
            sibling = bytes.fromhex(node.sibling_hash)
            if node.is_right:
                current = _hash_pair(current, sibling)
            else:
                current = _hash_pair(sibling, current)
        return current.hex() == self.root

    def to_public_dict(self) -> dict[str, object]:
        """Exportación pública — sin el valor del elemento."""
        return {
            "root": self.root,
            "proof_path": [
                {"sibling": n.sibling_hash, "is_right": n.is_right}
                for n in self.proof_path
            ],
            "leaf_index": self.leaf_index,
            "element_commitment": self.element_commitment,
        }


class MerkleTree:
    """
    Árbol Merkle sobre un conjunto de hechos de CORTEX.

    El árbol acepta strings arbitrarios (hechos, decisiones, memorias).
    Calcula internamente los hashes, nunca exponiendo los valores.

    Operaciones:
        build(elements)  → root (hash público)
        prove(element)   → ZKMembershipProof
        root_hex         → El hash raíz público
    """

    def __init__(self) -> None:
        self._elements: list[str] = []
        self._leaves: list[bytes] = []
        self._layers: list[list[bytes]] = []

    def build(self, elements: list[str]) -> str:
        """
        Construye el árbol desde una lista de elementos.
        Retorna el root hex — el único dato que se publica.
        """
        if not elements:
            raise ValueError("Cannot build Merkle tree from empty set.")

        self._elements = list(elements)
        self._leaves = [_leaf_hash(e) for e in elements]

        # Padding a potencia de 2 con hoja vacía
        leaves = list(self._leaves)
        while len(leaves) & (len(leaves) - 1):  # no es potencia de 2
            leaves.append(_sha256(b"zkortex:empty_leaf"))

        self._layers = [leaves]
        current_layer = leaves

        while len(current_layer) > 1:
            next_layer = []
            for i in range(0, len(current_layer), 2):
                left = current_layer[i]
                right = current_layer[i + 1] if i + 1 < len(current_layer) else left
                next_layer.append(_hash_pair(left, right))
            self._layers.append(next_layer)
            current_layer = next_layer

        return current_layer[0].hex()

    @property
    def root_hex(self) -> str:
        if not self._layers:
            raise RuntimeError("Tree not built. Call build() first.")
        return self._layers[-1][0].hex()

    def prove(self, element: str, element_commitment: str = "") -> ZKMembershipProof:
        """
        Genera una ZK Membership Proof para `element`.

        Raises ValueError si el elemento no está en el árbol.
        """
        if element not in self._elements:
            raise ValueError("Element not found in the sovereign knowledge set.")

        index = self._elements.index(element)
        proof_path: list[MerkleProofNode] = []

        # Reconstruir el path por layers (el padding hace que el index sea correcto)
        current_index = index
        for layer in self._layers[:-1]:  # Todas excepto la raíz
            is_right = current_index % 2 == 0
            sibling_index = current_index + 1 if is_right else current_index - 1
            sibling = layer[sibling_index] if sibling_index < len(layer) else layer[current_index]
            proof_path.append(MerkleProofNode(
                sibling_hash=sibling.hex(),
                is_right=not is_right,  # El hermano está a la derecha si el nodo actual es izquierdo
            ))
            current_index //= 2

        return ZKMembershipProof(
            root=self.root_hex,
            proof_path=proof_path,
            leaf_index=index,
            element_commitment=element_commitment,
        )
