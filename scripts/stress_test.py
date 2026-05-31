import time
import random
from authenticity_engine import AuthenticityDynamicsEngine, InterpretationLayer, RawFeatures


def run_stress_test(iterations=100000):
    engine = AuthenticityDynamicsEngine()
    interpreter = InterpretationLayer()

    print(f"Initiating C5-REAL Stress Test: {iterations} Nodes...")

    start_time = time.time()

    results = {
        "Low-Optimization System (Emergent Organic Signal)": 0,
        "Engagement-Industrial System (Algorithmic Subjugation)": 0,
        "Hybrid Drift System (Critical Convergence Zone)": 0,
    }

    anomalies_count = 0

    for _ in range(iterations):
        # Generate random telemetry vectors
        vectors = RawFeatures(
            creator_autonomy=random.random(),
            algorithmic_pressure=random.random(),
            audience_capture=random.random(),
            creative_entropy=random.random(),
            monetization_coupling=random.random(),
        )

        score = engine.system_dynamics(vectors)
        analysis = interpreter.assign_label(score, vectors)

        results[analysis["assigned_label"]] += 1
        if analysis["detected_anomalies"]:
            anomalies_count += 1

    end_time = time.time()
    elapsed = end_time - start_time
    ops_per_sec = iterations / elapsed

    print("\n[STRESS TEST RESULTS]")
    print(f"Total Vectors Processed: {iterations}")
    print(f"Execution Time: {elapsed:.4f} seconds")
    print(f"Throughput: {ops_per_sec:.2f} operations/second")
    print("\n[DISTRIBUTION]")
    for label, count in results.items():
        print(f" - {label}: {count} ({count / iterations * 100:.2f}%)")
    print(f"\nEdge Case Anomalies Detected: {anomalies_count}")


if __name__ == "__main__":
    # Simulate an extreme load of 250,000 synthetic channels
    run_stress_test(250000)
