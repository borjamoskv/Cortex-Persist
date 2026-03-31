import asyncio
import re
import math
import sys
import logging
from pathlib import Path

# CORTEX-SWARM-10K: El Fin del Software Plano
# 1 Commander -> 100 Legions -> 100 Centurions (10,000 Agents)
# Mission: Absolute Exergy Extraction & Ghost Hunt (API Secret Purging)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("SWARM-10K")

# Regex to detect Google API Keys broadly: AIza[0-9A-Za-z-_]{35}
GOOGLE_API_KEY_PATTERN = re.compile(r"AIza[0-9A-Za-z-_]{35}")

class CenturionAgent:
    """The tactical O(1) executor resolving atomic tasks instantly."""
    def __init__(self, centurion_id: str):
        self.centurion_id = centurion_id

    async def execute_scan(self, chunk: tuple[Path, int, str]) -> list[str]:
        file_path, line_no, content = chunk
        findings = []
        if GOOGLE_API_KEY_PATTERN.search(content):
            findings.append(f"[{self.centurion_id}] ⚠️ Ghost detected in {file_path}:{line_no} -> {content.strip()}")
        # Simulate fractional thermal cooldown
        await asyncio.sleep(0.001)
        return findings

class LegionSupervisor:
    """Manages up to 100 Centurions."""
    def __init__(self, legion_id: int):
        self.legion_id = f"LEGION-{legion_id:03d}"
        self.centurions = [CenturionAgent(f"{self.legion_id}/CEN-{i:03d}") for i in range(100)]

    async def deploy(self, task_chunks: list[tuple[Path, int, str]]) -> list[str]:
        # Sharded distribution
        tasks = []
        for i, chunk in enumerate(task_chunks):
            centurion = self.centurions[i % 100]
            tasks.append(asyncio.create_task(centurion.execute_scan(chunk)))
        
        results = await asyncio.gather(*tasks)
        return [finding for sublist in results for finding in sublist]

class SwarmCommander:
    """Root Node Orchestrator for 10,000 Agents."""
    def __init__(self):
        self.legions = [LegionSupervisor(i) for i in range(100)]
    
    async def orkestrate(self, directory: Path):
        logger.info(f"👑 SWARM COMMANDER: Deploying CORTEX-SWARM-10K across '{directory}'...")
        
        # Load all lines of all text files in repo to distribute as atomic chunks
        atomic_chunks = []
        for path in directory.rglob("*"):
            if path.is_file() and not any(part.startswith(".") for part in path.parts) and "site-packages" not in path.parts:
                try:
                    lines = path.read_text(encoding="utf-8").splitlines()
                    for i, line in enumerate(lines, start=1):
                        if len(line.strip()) > 10:  # Only meaningful lines
                            atomic_chunks.append((path, i, line))
                except UnicodeDecodeError:
                    pass # Ignore binary files
                    
        total_chunks = len(atomic_chunks)
        logger.info(f"⚔️ 10,000 Agents mobilized. Sharding {total_chunks} atomic tasks across 100 Legions...")
        
        # Distribute chunks across Legions
        chunk_size = math.ceil(total_chunks / 100) if total_chunks > 0 else 1
        tasks = []
        for i in range(100):
            legion_chunks = atomic_chunks[i * chunk_size : (i + 1) * chunk_size]
            if legion_chunks:
                tasks.append(asyncio.create_task(self.legions[i].deploy(legion_chunks)))
        
        if tasks:
            results = await asyncio.gather(*tasks)
            all_findings = [f for r in results for f in r]
        else:
            all_findings = []
            
        logger.info(f"◈ Swarm Aniquilation Phase: Found {len(all_findings)} compromised secrets.")
        for f in all_findings:
            logger.warning(f)
            
        return all_findings

if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    asyncio.run(SwarmCommander().orkestrate(target))
