import asyncio
from cortex.engine.membrane.firecracker_fd_guard import FIRECRACKER_ISOLATION_GUARD
from cortex.engine.exceptions import RealityBorderBreach
from cortex.guards.capability_guard import CapabilityGuard
from cortex.guards.capabilities import AgentCredentials, Capability, RiskTier


async def test_membrane():
    print("=== INICIANDO TEST DE FALSACIÓN DE MEMBRANA (SAGA-1) ===")

    # 1. Test Firecracker FD Guard
    print("\n[1] Testeando: FirecrackerIsolationGuard (Ley Ω9)")
    try:
        await FIRECRACKER_ISOLATION_GUARD.check(
            fact_id=1,
            event_type="exploit_synthesized",
            payload={
                "agent_id": "ER-Omega-v1",
                "contains_poc": True,
                "isolation_metadata": {
                    "runtime_type": "standard_container",  # VIOLATION!
                    "transfer_method": "network_socket",
                },
            },
            conn=None,
            tenant_id="tenant-001",
        )
        print("❌ FALLO: El guardia permitió un PoC sin aislamiento Firecracker.")
    except RealityBorderBreach as e:
        print(f"✅ ÉXITO (Rechazo Determinístico): {e}")

    try:
        await FIRECRACKER_ISOLATION_GUARD.check(
            fact_id=2,
            event_type="exploit_synthesized",
            payload={
                "agent_id": "ER-Omega-v1",
                "contains_poc": True,
                "isolation_metadata": {
                    "runtime_type": "firecracker_microvm",
                    "transfer_method": "serialized_fd",
                },
            },
            conn=None,
            tenant_id="tenant-001",
        )
        print("✅ ÉXITO (Aprobación Determinística): PoC aislado correctamente vía FD.")
    except RealityBorderBreach as e:
        print(f"❌ FALLO: {e}")

    # 2. Test Capability Guard
    print("\n[2] Testeando: CapabilityGuard")
    creds = AgentCredentials(
        agent_id="Centuria-Forge",
        capabilities={Capability(name="AST_FORGE", tier=RiskTier.TIER_1_LOCAL_SAFE)},
        max_tier=RiskTier.TIER_2_REMOTE_READ,
    )
    guard = CapabilityGuard(credentials=creds)

    try:
        guard.validate_action("AST_FORGE", RiskTier.TIER_1_LOCAL_SAFE)
        print("✅ ÉXITO (Aprobación Determinística): Capacidad autorizada.")
    except ValueError as e:
        print(f"❌ FALLO: {e}")

    try:
        guard.validate_action("EXECUTE_PAYLOAD", RiskTier.TIER_4_REMOTE_MUTATION)
        print("❌ FALLO: El guardia permitió una escalada de privilegios.")
    except ValueError as e:
        print(f"✅ ÉXITO (Rechazo Determinístico): {e}")


if __name__ == "__main__":
    asyncio.run(test_membrane())
