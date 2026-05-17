"""
CORTEX — Stress Test: Sovereign Exploit Substrate (Ω).

Simulates high-volume adversarial analysis across multiple targets.
"""

import asyncio
import time
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from cortex.guards.mythos_auditor import MythosAuditor
from cortex.forensics.models import MythosClaim, Severity, HazardClass


async def stress_worker(auditor, file_path, file_id):
    start = time.time()
    try:
        with open(file_path) as f:
            code = f.read()

        # Simulate Torpedo finding different issues based on file_id
        async def mocked_claims(*args, **kwargs):
            return [
                MythosClaim(
                    fact_id=f"STRESS-CLAIM-{file_id}",
                    hypothesis=f"Simulated high-exergy exploit in {os.path.basename(file_path)}",
                    exploit_vector="t0 -> t1 -> extraction",
                    severity=Severity.CRITICAL if file_id % 2 == 0 else Severity.HIGH,
                    suggested_hazard=HazardClass.H4 if file_id % 3 == 0 else HazardClass.H2,
                    agent_id="torpedo-stress-unit",
                )
            ]

        auditor._generate_claims = mocked_claims
        artifacts = await auditor.analyze_target(code, "stress-test")

        elapsed = time.time() - start
        return {
            "file": os.path.basename(file_path),
            "artifacts_count": len(artifacts),
            "hazards": [a.get_hazard_class().value for a in artifacts],
            "max_e_score": max([a.exploitability.score for a in artifacts]) if artifacts else 0,
            "time": elapsed,
        }
    except Exception as e:
        return {"file": os.path.basename(file_path), "error": str(e)}


async def main():
    print("--- INICIANDO PRUEBA DE ESTRÉS: SUSTRATO Ω ---")
    auditor = MythosAuditor()

    target_dir = (
        "/Users/borjafernandezangulo/10_PROJECTS/2026-04-k2/contracts/liquidation-engine/src"
    )
    files = [os.path.join(target_dir, f) for f in os.listdir(target_dir) if f.endswith(".rs")]

    print(f"Cargando {len(files)} objetivos de ataque...")

    start_total = time.time()
    tasks = [stress_worker(auditor, f, i) for i, f in enumerate(files)]
    results = await asyncio.gather(*tasks)
    end_total = time.time()

    print("\n--- RESULTADOS DEL ESTRÉS ---")
    total_artifacts = 0
    total_h4 = 0

    for r in results:
        if "error" in r:
            print(f"[-] {r['file']}: ERROR: {r['error']}")
            continue

        h4_count = r["hazards"].count("H4")
        total_h4 += h4_count
        total_artifacts += r["artifacts_count"]

        status_icon = "🔥" if h4_count > 0 else "✅"
        print(
            f"[{status_icon}] {r['file']:<15} | E-Score Max: {r['max_e_score']:.2f} | Time: {r['time']:.4f}s"
        )

    print("\nOntología Final:")
    print(f"- Total Artefactos Forenses: {total_artifacts}")
    print(f"- Protocolos ANATHEMA Activados (H4): {total_h4}")
    print(f"- Tiempo Total de Simulación: {end_total - start_total:.4f}s")
    print(f"- Rendimiento: {len(files) / (end_total - start_total):.2f} targets/sec")


if __name__ == "__main__":
    asyncio.run(main())
