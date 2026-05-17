from eromega.genome import ExploitGenome
from eromega.contradiction_engine import AutonomousContradictionEngine
from eromega.digital_twin import OffensiveDigitalTwin


def run_evolution():
    print("=== Iniciando Autodidact-Ω Evolutionary Engine ===")

    # 1. Configurar Digital Twin en perfil "Hardened"
    hardened_profile = {"KASLR": True, "SMAP": True, "SMEP": True, "KPTI": True}
    twin = OffensiveDigitalTwin("target_hardened", custom_mitigations=hardened_profile)
    env = twin.synthesize_environment()

    # 2. Población inicial: Genomas débiles (entropy_resistance bajo, mitigation_pressure bajo)
    population = []
    for i in range(10):
        population.append(
            ExploitGenome(
                id=f"base_gen_{i}",
                primitives=["read_primitive"],
                transitions=[{"from": "vuln", "to": "primitive"}],
                entropy_dependencies={"stack_leak": 0.1},  # Baja resistencia a KASLR
                mitigation_bypasses=[],  # Sin bypasses adicionales
            )
        )

    engine = AutonomousContradictionEngine()

    # Test inicial
    print("\n--- Generación 0 (Población Base) ---")
    engine.test_genome(population[0], env)
    print(f"Mejor Genoma Base Score: {population[0].state_dominance_score:.2f}")
    print(f"Métricas Iniciales: {population[0].get_metrics()}")

    # 3. Evolucionar durante 30 generaciones
    generations = 30
    print(
        f"\nSometiendo población a {generations} generaciones de Presión Termodinámica Darwiniana..."
    )
    evolved_population = engine.evolve_population(population, env, generations=generations)

    # Resultados post-evolución
    best_genome = evolved_population[0]
    print("\n--- Resultados Post-Evolución ---")
    print(f"Mejor Genoma Score: {best_genome.state_dominance_score:.2f}")
    print(f"Bypasses Adquiridos: {best_genome.mitigation_bypasses}")
    print(f"Dependencias Entrópicas: {best_genome.entropy_dependencies}")
    print(f"Métricas Finales: {best_genome.get_metrics()}")

    if best_genome.state_dominance_score >= 1.0:
        print(
            "\n[SUCCESS] El Motor Autodidact-Ω logró mutar un exploit resistente al perfil Hardened (C5-REAL)."
        )
    else:
        print("\n[INCOMPLETE] El exploit no alcanzó resistencia perfecta bajo la presión actual.")


if __name__ == "__main__":
    run_evolution()
