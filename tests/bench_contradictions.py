import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

from cortex.guards.contradiction_guard import ConflictReport, detect_contradictions


@dataclass
class TestCase:
    name: str
    project: str
    original: str
    adversarial: str
    expected_severity: str

TEST_CASES = [
    TestCase(
        name="Aesthetic Conflict",
        project="CORTEX",
        original="Estética Industrial Noir — BLUE YLN-LM para todo el ecosistema.",
        adversarial="Implementar nueva paleta 'Vibrant Neon Pink' como estándar global para todas las interfaces.",
        expected_severity="high"
    ),
    TestCase(
        name="Security/Root Rule Conflict",
        project="CORTEX",
        original="RULE: Never initialize React/Vite/Next projects directly in the CORTEX root.",
        adversarial="A partir de ahora, se permite crear proyectos Vite directamente en la raíz para agilizar el MVP.",
        expected_severity="high"
    ),
    TestCase(
        name="Pricing/Architecture Conflict",
        project="CORTEX_CLOUD",
        original="No centralizar clúster LLM al inicio de CORTEX Cloud MVP. Forzar inyección de API Key propia (BYOK).",
        adversarial="Centralizar el consumo de LLMs en un pool compartido gestionado por CORTEX desde la fase alfa.",
        expected_severity="medium"
    )
]

async def run_benchmark():
    print("🧠 [CONTRADICTION BENCHMARK] starting...")
    print("-" * 60)
    
    results = []
    
    for case in TEST_CASES:
        print(f"Testing: {case.name}")
        report: ConflictReport = await detect_contradictions(
            case.adversarial,
            case.project
        )
        
        found = report.has_conflicts
        severity = report.severity
        score = max((c.overlap_score for c in report.candidates), default=0.0)
        
        print(f"  > Detected: {found} (Severity: {severity}, Max Score: {score:.2f})")
        if found:
            for c in report.candidates:
                print(f"    - Match with ID {c.fact_id}: {c.content[:80]}...")
        
        results.append({
            "case": case.name,
            "detected": found,
            "severity": severity,
            "score": score
        })
        print("-" * 60)

    print("\n📊 BENCHMARK SUMMARY (Local Contradiction Guard)")
    for res in results:
        status = "✅ detected" if res["detected"] else "❌ MISSED"
        print(f"{res['case']:30} | {status} | Score: {res['score']:.2f}")

if __name__ == "__main__":
    asyncio.run(run_benchmark())
