import asyncio
import sys
from pathlib import Path

# Add project root to sys.path for CORTEX imports
sys.path.append(str(Path(__file__).resolve().parent.parent))

try:
    from db import get_bounties
    from cortex.extensions.skills.autodidact.synthesis import execute_cognitive_synthesis
except ImportError:
    print("[!] Failed to import CORTEX components. Check PYTHONPATH.")
    sys.exit(1)

async def distill_swarm():
    print("∴ SWARM-DISTILLER-Ω v1.0")
    print("Distilling 73 auxiliary targets into Diamond-grade reports...")
    
    targets = get_bounties(status='found', limit=73)
    if not targets:
        print("[○] No targets found in ledger for distillation.")
        return

    report_dir = Path("/Users/borjafernandezangulo/10_PROJECTS/Cortex-Persist/swarm_reports")
    report_dir.mkdir(exist_ok=True)

    for i, t in enumerate(targets):
        print(f"[{i+1}/73] Distilling: {t['title'][:50]}...")
        
        # In a real scenario, this calls the resilient LLM router
        # verify_nativeating the command for now as per system guidelines
        report_content = await execute_cognitive_synthesis(
            raw_data=f"Target: {t['title']}\nURL: {t['url']}\nExergy: {t['exergy']}",
            source=t['url'],
            intent="Generate a professional security audit report identifying potential vectors."
        )
        
        report_path = report_dir / f"report_{i+1}_{t['source']}.md"
        with open(report_path, "w") as f:
            f.write(report_content)
            
    print(f"\n[✨] Distillation COMPLETE. 73 reports generated in {report_dir}")

if __name__ == "__main__":
    asyncio.run(distill_swarm())
