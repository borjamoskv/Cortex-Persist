import os
import time


def main():
    try:
        import cortex_rs
    except ImportError as e:
        print(f"Error importing cortex_rs: {e}")
        return

    print(">>> Inicializando PyWasmSwarm...")
    swarm = cortex_rs.PyWasmSwarm()

    wasm_path = os.path.join(
        os.path.dirname(__file__),
        "../crates/agent-pure/target/wasm32-unknown-unknown/release/agent_pure.wasm",
    )

    if not os.path.exists(wasm_path):
        print(f"ERROR: No se encontró {wasm_path}")
        return

    with open(wasm_path, "rb") as f:
        wasm_bytes = f.read()

    print(f">>> Instanciando Agente WASM (Payload: {len(wasm_bytes)} bytes)")
    agent_id = "agent_zero_01"

    t0 = time.time()
    swarm.spawn_agent(agent_id, wasm_bytes)
    t1 = time.time()
    print(f"    - Agent spawned in: {(t1 - t0) * 1000:.2f} ms")

    print(">>> Ejecutando ciclo de fricción puro C5-REAL")
    t0 = time.time()

    # Send a friction signal of 5.0.
    # Our pure agent has an assimilation_rate of 0.85, so it should return -4.25
    delta = swarm.cycle_friction(agent_id, 5.0)

    t1 = time.time()

    print("    - Fricción inyectada: 5.0")
    print(f"    - Entropía delta calculada por WASM: {delta}")
    print(f"    - Execution latency: {(t1 - t0) * 1000:.4f} ms")

    if abs(delta - (-4.25)) < 0.001:
        print("\n✅ C5-REAL WASM SWARM VERIFICADO. Latencia pura.")
    else:
        print(f"\n❌ ERROR: Esperaba -4.25, obtuve {delta}")


if __name__ == "__main__":
    main()
