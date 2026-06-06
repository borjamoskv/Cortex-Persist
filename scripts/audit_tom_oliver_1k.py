import asyncio
import time
import shutil
import subprocess
from pathlib import Path

from cortex.engine import CortexEngine
from cortex.audit.frontier import FrontierAuditor
from cortex.engine.swarm_10k import SwarmCommander


async def deep_audit_cortex():
    print("[C5-REAL] AUDIT: CORTEX")

    # 1. Start Engine
    engine = CortexEngine()

    # 2. Orchestrate 1000 agents for deep structural scan
    print("[C5-REAL] TASK: SWARM_INIT | COUNT: 1000 | ACTION: AST_SCAN")
    test_bus_dir = Path("/tmp/cortex_1k_audit_bus")
    if test_bus_dir.exists():
        shutil.rmtree(test_bus_dir)
    test_bus_dir.mkdir(parents=True)

    commander = SwarmCommander(bus_path=test_bus_dir)
    await commander.initialize()

    tasks = [
        {"id": i, "domain": f"audit_shard_{i % 10}", "payload": f"scan_ast_region_{i}"}
        for i in range(1000)
    ]

    start_time = time.perf_counter()
    await commander.execute_global_dispatch(tasks, parallel=True)
    total_time = time.perf_counter() - start_time

    report = await commander.get_density_report()
    print(f"[C5-REAL] TASK: SWARM_COMPLETE | TIME_S: {total_time:.4f} | AGENTS: {report['agents']}")

    print("[C5-REAL] TASK: TELEMETRY_INJECT | DEST: CORTEX-Memory")
    await engine.store(
        tenant_id="default",
        project="CORTEX",
        fact_type="system_health",
        content=f"SWARM_DEPLOY: {report['agents']} AGENTS | TIME_S: {total_time:.4f} | TARGETS: OuroborosGate, Rust ZeroCopyRingBuffer, GIL",
        confidence="C5",
    )
    await engine.store(
        tenant_id="default",
        project="CORTEX",
        fact_type="system_health",
        content="ISSUE: ASYNC_TECH_DEBT | REC: PURGE_STOCHASTIC_DEPS | REASON: EXERGY_LAW_LANDAUER_LIMIT",
        confidence="C5",
    )

    # 3. TOM & OLIVER (y BENJI) Audit
    print("[C5-REAL] TASK: TRIAD_WAKE | TARGETS: TOM, BENJI, OLIVER")
    auditor = FrontierAuditor(engine, model_override="anthropic")

    audit_start = time.perf_counter()
    res = await auditor.run_audit("CORTEX")
    time.perf_counter() - audit_start

    print("---")
    print("Report:")
    print(res["report_markdown"])
    print(f"Metrics: {{ Status: {res['status']}, Provider: {res['provider']}, Latency_ms: {res['latency']:.1f} }}")

    await commander.consolidate_and_annihilate()
    if test_bus_dir.exists():
        shutil.rmtree(test_bus_dir)

    # Git Sentinel (R4)
    subprocess.run(["git", "status"])


if __name__ == "__main__":
    asyncio.run(deep_audit_cortex())
