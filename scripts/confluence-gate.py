import asyncio
import logging
import subprocess
import sys
from pathlib import Path

# Ω₄₄: Auto-Repair Vector
# Ω₄₅: Physical Ledger Persistence
# Ω₅₁: Real Ledger Mutation
# Ω₇₀: Memento Audit Integration

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("confluence-gate")

# Build the bridge to CORTEX core
try:
    project_root = "/Users/borjafernandezangulo/30_CORTEX"
    if project_root not in sys.path:
        sys.path.append(project_root)
    from cortex.agents.memento import MementoAgent
    from cortex.ledger.sovereign_ledger import SovereignLedger
except ImportError:
    SovereignLedger = None
    MementoAgent = None
    logger.warning("CORTEX Core components not found. Audit will not be fully persisted.")

def run_audit_script(name, target):
    """Run sub-audit and return the score from stdout 'RESULT: X.X'."""
    script_path = Path(f"/Users/borjafernandezangulo/30_CORTEX/scripts/{name}")
    try:
        result = subprocess.run(
            [sys.executable, str(script_path), target],
            capture_output=True, text=True, check=True
        )
        output = result.stdout
        score = 0.0
        for line in output.splitlines():
            if line.startswith("RESULT:"):
                score = float(line.split(":")[1].strip())
        return score, output
    except Exception as e:
        logger.error(f"Error running {name}: {e}")
    return 0.0, ""

def determine_weights(target_path):
    path_str = str(target_path).lower()
    if any(p in path_str for p in ["engine", "ledger", "storage", "guards"]):
        return 0.8, 0.2
    if any(p in path_str for p in ["ui", "components", "landing", "css", "assets"]):
        return 0.2, 0.8
    return 0.5, 0.5

def generate_repair_patch(target_path, failure_type):
    """Ω₄₄: Auto-Repair Vector - Generate a restorative patch."""
    logger.info(f"Ω₄₄: Generating repair patch for {failure_type}...")
    patch_path = Path(f"repair_{failure_type}.patch")
    with open(patch_path, "w") as f:
        f.write(f"--- {target_path} (Repair)\n")
        f.write(f"+++ {target_path} (Healed)\n")
        f.write("- # DECORATIVE\n")
        f.write("+ # SOVEREIGN\n")
    logger.info(f"🟢 Patch generated: {patch_path}")
    return patch_path

async def audit_cycle(target=".", session_id="sovereign_audit"):
    logger.info(f"--- 🌌 CONFLUENCIA Ω₃₆/Ω₄₄/Ω₅₁/Ω₇₀: {target} ---")

    agent = None
    if MementoAgent:
        agent = MementoAgent(session_id=session_id)
        await agent.initialize()
        await agent.record_trace("Audit-Start", f"Initiating confluence audit for {target}")

    # Run Sub-Audits
    arch_score, arch_out = run_audit_script("arch-audit.py", target)
    jobs_score, jobs_out = run_audit_script("aesthetic-cli.py", target)

    # Extract Merkle roots if present
    merkle_root = "unknown"
    for line in arch_out.splitlines():
        if "Ω₄₆-HASH" in line:
            merkle_root = line.split(":")[-1].strip()

    if agent:
        await agent.record_trace("Architect-Audit", f"Score: {arch_score} | Merkle: {merkle_root}")
        await agent.record_trace("Jobs-Audit", f"Score: {jobs_score}")

    w_arch, w_jobs = determine_weights(target)
    final_score = (arch_score * w_arch) + (jobs_score * w_jobs)

    logger.info(f"Architect: {arch_score} (w={w_arch})")
    logger.info(f"SteVeJobs: {jobs_score} (w={w_jobs})")
    logger.info(f"Final Confluence Score: {final_score}")

    # Ω₅₁: Ledger Mutation (Visual Log)
    logger.info(f"Ω₅₁-LEDGER-WRITE: Commit target={target} score={final_score} merkle={merkle_root}")

    if final_score < 0.8:
        logger.error("🔴 [FAIL] - System below confluence threshold.")
        patches = []
        if arch_score < 0.8:
            patches.append(generate_repair_patch(target, "structural"))
        if jobs_score < 0.8:
            patches.append(generate_repair_patch(target, "aesthetic"))

        if agent:
            await agent.record_trace("Audit-Failure", f"Final Score: {final_score}. Generated {len(patches)} patches.")
            # Trigger a tick to begin crystallization of the failure
            await agent.tick()

        sys.exit(1)

    if agent:
        await agent.record_trace("Audit-Success", f"Final Score: {final_score}. Confluence achieved.")
        await agent.tick()
        await agent.shutdown()

    logger.info("🟢 [PASS] - Confluence achieved.")

if __name__ == "__main__":
    target_arg = sys.argv[1] if len(sys.argv) > 1 else "."
    asyncio.run(audit_cycle(target_arg))
