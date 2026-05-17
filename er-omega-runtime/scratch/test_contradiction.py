from eromega.genome import ExploitGenome
from eromega.contradiction_engine import AutonomousContradictionEngine


def run_test():
    # Creamos un genoma básico
    genome = ExploitGenome(
        id="test_01",
        primitives=["read_primitive", "write_primitive"],
        transitions=[{"from": "vuln", "to": "primitive"}],
        entropy_dependencies={"stack_leak": 0.3},
        mitigation_bypasses=["smap_bypass"],
    )

    engine = AutonomousContradictionEngine()
    print(f"Genoma inicial: {genome.get_metrics()}")

    # Simulamos frente a perfiles generados por el Digital Twin
    results = engine.simulate_mitigation_profiles(genome)

    print("\nResultados de Supervivencia frente a Perfiles del Digital Twin:")
    for profile, score in results.items():
        print(f" - {profile}: {score:.2f} / 1.00")


if __name__ == "__main__":
    run_test()
