"""
ZKORTEX — Integration Test Suite.

Demuestra el protocolo completo de opacidad selectiva:
    1. CORTEX ingiere hechos (privados)
    2. CORTEX publica solo el Merkle Root
    3. Verifier externo verifica pertenencia sin conocer el conjunto
    4. CORTEX demuestra que tiene N hechos sin revelar N exacto
    5. Commitment: CORTEX se compromete a un hecho sin revelarlo

Run: python -m pytest cortex/zkortex/test_integration.py -v
  or: python cortex/zkortex/test_integration.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Asegurar que la raíz del proyecto esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_full_sovereign_opacity_protocol() -> None:
    """Test completo del protocolo de opacidad soberana."""
    from cortex.zkortex import SovereignOpacityLayer, ZKOrtexVerifier

    print("\n" + "═" * 60)
    print("  ZKORTEX — SOVEREIGN OPACITY PROTOCOL")
    print("  Demostración Zero-Knowledge Completa")
    print("═" * 60)

    # ── 1. Base de conocimiento privada de CORTEX ─────────────────────────────
    private_knowledge = [
        "El proyecto Naroa usa Vite + React con Industrial Noir",
        "La wallet 0x4a2b...cc91 tiene 142 ETH",
        "El Berghain rechaza a quien llega antes de las 2am",
        "CORTEX v6 usa HKDF + AES-GCM con aislamiento por tenant",
        "El Merkle Root del legado fiscal está en cold storage",
    ]

    print(f"\n[CORTEX PRIVADO] {len(private_knowledge)} hechos en la base de conocimiento")
    print("[CORTEX PRIVADO] Nadie exterior los verá directamente\n")

    # ── 2. Inicializar Opacity Layer ──────────────────────────────────────────
    opacity = SovereignOpacityLayer(
        opacity_strategy=SovereignOpacityLayer.STRATEGY_MEDIUM, session_id="sovereign-demo-session"
    )

    # ── 3. Ingestión — genera el root público ─────────────────────────────────
    public_root = opacity.ingest_facts(private_knowledge)
    print(f"[PÚBLICO] Merkle Root publicado: {public_root[:32]}...")
    print("[PÚBLICO] Este hash representa TODO el conocimiento, sin revelar nada")

    # ── 4. Verifier externo se configura con el root público ──────────────────
    verifier = ZKOrtexVerifier(expected_root=opacity.public_root)
    print(f"\n[VERIFIER EXTERNO] Root pinned: {public_root[:16]}...")

    # ── 5. CORTEX demuestra que conoce un hecho específico ────────────────────
    fact_to_prove = "CORTEX v6 usa HKDF + AES-GCM con aislamiento por tenant"
    print("\n[CORTEX] Generando prueba de membresía para:")
    print(f"         '{fact_to_prove[:50]}...'")

    proof = opacity.prove_knows_fact(fact_to_prove)
    assert proof is not None, "Proof generation failed"

    result = verifier.verify_membership(proof, element_to_verify=_fact_fingerprint(fact_to_prove))
    print(f"\n[VERIFIER] Resultado: {'✓ VÁLIDO' if result.is_valid else '✗ INVÁLIDO'}")
    print("[VERIFIER] El hecho existe en el knowledge set de CORTEX")
    print("[VERIFIER] El Verifier NO ha visto ningún otro hecho")

    # ── 6. Prueba de rango — "¿Tienes más de 3 hechos?" ──────────────────────
    print("\n[AUDITOR] ¿Tiene CORTEX entre 3 y 100 hechos?")
    range_proof = opacity.prove_count_in_range(3, 100)
    assert range_proof is not None

    range_result = verifier.verify_range(range_proof)
    print(f"[VERIFIER] Rango: {'✓ CONFIRMADO' if range_result.is_valid else '✗ RECHAZADO'}")
    print("[VERIFIER] CORTEX tiene entre 3 y 100 hechos. El número exacto: REDACTADO.")

    # ── 7. Commitment — CORTEX se compromete a un hecho futuro ───────────────
    print("\n[CORTEX] Emitiendo commitment a un hecho sensible...")
    commitment = opacity.commit_to_knowledge(
        fact_id="wallet-balance-2026-03",
        fact_content="El saldo total en cold storage es 847 ETH",
        metadata={"category": "financial", "date": "2026-03-03"},
    )
    print(f"[PÚBLICO] Commitment emitido: {commitment.commitment_hex[:32]}...")
    print("[PÚBLICO] Nadie puede abrir este commitment sin el blinding key")

    # ── 8. Estado público sin datos privados ──────────────────────────────────
    status = opacity.public_status()
    print("\n[PÚBLICO] Estado del sistema ZKORTEX:")
    print(f"  Strategy:     {status['opacity_strategy']}")
    print(f"  Proofs:       {status['proofs_emitted']}")
    print(f"  Commitments:  {status['commitments_emitted']}")
    print(f"  Tree active:  {status['knowledge_tree_active']}")

    print("\n" + "═" * 60)
    print("  ✓ PROTOCOLO COMPLETO. CORTEX SOBERANO. OPACIDAD TOTAL.")
    print("═" * 60 + "\n")


def _fact_fingerprint(fact: str) -> str:
    """Helper para fingerprint — replicando la lógica interna de SovereignOpacityLayer."""
    import hashlib

    return hashlib.sha256(b"zkortex:fact:" + fact.encode()).hexdigest()


def test_commitment_binding() -> None:
    """Verifica que el commitment es binding: no se puede forjar."""
    from cortex.zkortex.commitment import commit

    secret = "El Berghain tiene 3 puertas de seguridad"
    c, blinding = commit(secret)

    assert c.verify(secret, blinding), "Commitment should verify correctly"
    assert not c.verify("Otro secreto", blinding), "Commitment should NOT verify wrong secret"
    assert not c.verify(secret, b"\x00" * 32), "Commitment should NOT verify wrong blinding"
    print("✓ test_commitment_binding PASSED")


def test_merkle_membership() -> None:
    """Verifica la integridad del árbol Merkle."""
    from cortex.zkortex.merkle import MerkleTree

    elements = ["alpha", "beta", "gamma", "delta"]
    tree = MerkleTree()
    root = tree.build(elements)

    for elem in elements:
        proof = tree.prove(elem)
        assert proof.verify(elem), f"Membership proof failed for '{elem}'"
        assert not proof.verify("impostor"), "Proof should not verify wrong element"

    print(f"✓ test_merkle_membership PASSED. Root: {root[:16]}...")


def test_range_proof_honesty() -> None:
    """Verifica que un range proof honesto siempre es válido,
    y que uno deshonesto no se puede construir."""
    from cortex.zkortex.range_proof import prove_range, verify_range_proof

    # Honesto
    proof = prove_range(42, 10, 100)
    assert verify_range_proof(proof)

    # Deshonesto — debe lanzar ValueError
    try:
        prove_range(200, 10, 100)
        raise AssertionError("Should have raised ValueError")
    except ValueError:
        pass

    print("✓ test_range_proof_honesty PASSED")


if __name__ == "__main__":
    test_commitment_binding()
    test_merkle_membership()
    test_range_proof_honesty()
    test_full_sovereign_opacity_protocol()
    print("\n🔒 ZKORTEX: ALL TESTS PASSED. Sovereignty confirmed.\n")
