import asyncio
import logging
import subprocess
import sys
import time
from pathlib import Path

# Ω₅₀: The Eternal Loop (Supervisor)
# Ω₇₁: Contextual Recall Integration

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("sovereign-loop")

# Build the bridge to CORTEX core for Recall
try:
    project_root = "/Users/borjafernandezangulo/30_CORTEX"
    if project_root not in sys.path:
        sys.path.append(project_root)
    from cortex.agents.memento import MementoAgent
except ImportError:
    MementoAgent = None
    logger.warning("MementoAgent not found. Recall disabled.")

async def perform_recall(target, session_id):
    """Ω₇₁: Query Memento for previous failures in this session/target."""
    if not MementoAgent:
        return
    
    agent = MementoAgent(session_id=session_id)
    await agent.initialize()
    
    logger.info("🔍 Ω₇₁: Recalling previous audit memories...")
    # Search for failures or "Structural" issues
    results = await agent.search(f"failure audit {target}", limit=3)
    
    if results:
        logger.info(f"💾 Found {len(results)} relevant memories:")
        for r in results:
            summary = r.get("summary", "No summary")
            evidence = r.get("evidence", "No evidence")
            logger.info(f"   - {summary} | {evidence[:60]}...")
    else:
        logger.info("🆕 No previous failures recalled. System state is clean or memory is cold.")
    
    await agent.shutdown()

async def run_loop(target_path, interval=300, cycles=None):
    logger.info(f"🌌 SOVEREIGN-LOOP Ω₅₀ START: target={target_path} interval={interval}s")
    
    session_id = f"sovereign_loop_{int(time.time())}"
    count = 0
    
    while True:
        count += 1
        logger.info(f"--- 🌀 Lifecycle Cycle #{count} (Session: {session_id}) ---")
        
        # Ω₇₁: Contextual Recall before audit
        await perform_recall(target_path, session_id)
        
        try:
            # Run the Confluence Gate
            gate_path = Path("/Users/borjafernandezangulo/30_CORTEX/scripts/confluence-gate.py")
            subprocess.run([sys.executable, str(gate_path), target_path, session_id], check=False)
        except Exception as e:
            logger.error(f"Error in cycle #{count}: {e}")
            
        if cycles and count >= cycles:
            logger.info("🌌 Maximum cycles reached. Exiting.")
            break
            
        logger.info(f"Waiting {interval}s for next cycle...")
        await asyncio.sleep(interval)

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    interval = int(sys.argv[2]) if len(sys.argv) > 2 else 300
    cycles = int(sys.argv[3]) if len(sys.argv) > 3 else None
    
    try:
        asyncio.run(run_loop(target, interval, cycles))
    except KeyboardInterrupt:
        logger.info("🌌 Sovereign Loop terminated by user.")
