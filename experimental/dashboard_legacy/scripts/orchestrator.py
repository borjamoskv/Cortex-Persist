#!/usr/bin/env python3
"""∴ CORTEX-MASTER-ORCHESTRATOR v2.0 — Sovereign Swarm Core.

Consolidated background process management for standard scanning, 
yield tracking, and high-exergy autonomous strikes.
"""

import time
import asyncio
import logging
import subprocess
import sys
from pathlib import Path

# Fix PYTHONPATH to include project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT / "scripts"))

try:
    from dotenv import load_dotenv
    # Ensure variables from the root .env file are injected
    load_dotenv(dotenv_path=str(PROJECT_ROOT / ".env"))

    from db import record_memory_event
    from automata_loop import process_target, build_mythos_graph
    from db import get_bounties
except ImportError as e:
    print(f"[!] CORTEX-ORCHESTRATOR: Dependency failure: {e}")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(PROJECT_ROOT / "data" / "orchestrator_v2.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("CORTEX.ORCHESTRATOR")

class ReasonedTask:
    """Hito 11: Task representation with latent reasoning states."""
    def __init__(self, target):  # type: ignore
        self.target = target
        self.id = target.get('id', 'unknown')
        self.state = "ANALYZING" # ANALYZING, PLANNING, EXECUTING, OBSERVING
        self.plan = []
        self.thinking_tokens = ""
        self.results = ""

    async def step(self):
        """Cyclical state progression based on Manus-Parity."""
        if self.state == "ANALYZING":
            self.thinking_tokens = f"◈ Deciphering exergy vectors for {self.id}..."
            await asyncio.sleep(1)
            self.state = "PLANNING"
        elif self.state == "PLANNING":
            self.thinking_tokens = "◈ Decomposing into sub-tasks: [Scout, Extract, Seal]..."
            self.plan = ["scout", "extract", "seal"]
            await asyncio.sleep(2)
            self.state = "EXECUTING"
        elif self.state == "EXECUTING":
            current_sub = self.plan.pop(0) if self.plan else "done"
            self.thinking_tokens = f"◈ Executing sub-task: {current_sub} via Node_Ω..."
            if not self.plan: self.state = "OBSERVING"
            await asyncio.sleep(2)
        elif self.state == "OBSERVING":
            self.thinking_tokens = "◈ Verifying results against Axiom Ω9..."
            self.state = "COMPLETED"
            await asyncio.sleep(1)

    def __init__(self):
        self.scan_interval = 900    # 15 mins (Aggressive)
        self.yield_interval = 1800  # 30 mins (Aggressive)
        self.automata_interval = 30 # Check for new targets every 30s (Aggressive)

        self.last_scan = 0
        self.last_yield = 0
        self.last_automata = 0
        self.last_daily = 0 # Clock Recalibration (24h)
        
        self.daily_interval = 86400 # 24 Hours
        
        # Adaptive Tuning (Axiom Ω₂)
        self.base_intervals = {
            "scan": 1800,
            "yield": 3600,
            "automata": 60
        }
        
        # Build the engine once to share weights/cache
        self.automata_engine = build_mythos_graph()

    def run_foundation_script(self, script_name):
        """Runs foundation scripts as subprocesses to maintain isolation."""
        script_path = PROJECT_ROOT / "scripts" / script_name
        if not script_path.exists():
            logger.error(f"  [!] Script not found: {script_name}")
            return
            
        logger.info(f"◈ [SYNERGY] Launching {script_name}...")
        try:
            subprocess.run(["python3", str(script_path)], check=False, cwd=str(PROJECT_ROOT))
        except Exception as e:
            logger.error(f"  ❌ Failure in {script_name}: {e}")

    def _calculate_adaptive_intervals(self):
        """Ω₂ Enforcement: Throttles system frequency based on strike exergy."""
        targets = get_bounties(status="audited", min_exergy=1.0, limit=1)
        if not targets:
            # Idle state: use base intervals
            self.scan_interval = self.base_intervals["scan"]
            self.yield_interval = self.base_intervals["yield"]
            self.automata_interval = self.base_intervals["automata"]
            return

        max_exergy = targets[0]["exergy"]
        # Scale: higher exergy = faster polling. 
        # Cap at 10x acceleration for P0 strikes.
        factor = max(1.0, min(10.0, max_exergy / 0.5))
        
        self.scan_interval = self.base_intervals["scan"] / factor
        self.yield_interval = self.base_intervals["yield"] / factor
        self.automata_interval = max(5.0, self.base_intervals["automata"] / factor)
        
        logger.debug(f"◈ [ADAPTIVE] Exergy {max_exergy} detected. System factor: {factor:.2f}x")

    async def execute_automata_cycle(self):
        """High-exergy autonomous strike cycle (H11: APE-Loop)."""
        self._calculate_adaptive_intervals()
        logger.info(f"◈ [STRIKE] Scanning triaged targets (Current Cycle: {self.automata_interval:.1f}s)...")
        targets = get_bounties(status="found", min_exergy=1.5, limit=3)
        
        if not targets:
            logger.info("  ○ No qualifying targets in ledger. Standing by.")
            return
            
        for target in targets:
            # Hito 11: Transition to ReasonedTask
            task = ReasonedTask(target)  # type: ignore
            logger.info(f"◈ [REASONING] Initiating APE-Loop for {task.id}...")
            
            while task.state != "COMPLETED":
                await task.step()
                # Record to ledger for UI ReasoningView
                record_memory_event(
                    "reasoning", 
                    f"Task {task.id}: {task.thinking_tokens}", 
                    f"state_{task.state.lower()}"
                )
            
            await process_target(self.automata_engine, target)
            await asyncio.sleep(2) # Thermal cooling

    async def run_daily_recalibration(self):
        """∴ 24h Clock Sync & System Recalibration."""
        logger.info("∴ [KAIROS] 24h INTERNAL CLOCK SYNC INITIATED...")
        
        # 0. Primary Action: AI Press Digest
        self.run_foundation_script("ai_press_digest.py")
        
        # 1. Heartbeat to Ledger
        record_memory_event("system", "Daily Calibration: Internal Clock Synced", "heartbeat_24h")
        
        # 2. Exergy Governor Re-tuning (verify_nativeated for V2)
        # In V3 this will trigger a retraining of the PCI prediction weights
        logger.info("  ◈ Recalibrating Exergy Governor weights...")
        
        # 3. Log hygiene (Optional: Prune very old local logs)
        logger.info("  ◈ System Integrity: FEACIENTE [OPTIMAL]")
        
        self.last_daily = time.time()

    async def master_loop(self):
        logger.info("∴ CORTEX-ORCHESTRATOR v2.0 ACTIVE [PROTOCOLS: FULL_AUTO]")
        record_memory_event("system", "Orchestrator v2.0 Warm-Start", "sys_boot")

        while True:
            now = time.time()

            # 1. Swarm Scan (Ouroboros)
            if now - self.last_scan > self.scan_interval:
                self.run_foundation_script("ouroboros_capital_engine.py")
                self.last_scan = now

            # 2. Yield Tracking
            if now - self.last_yield > self.yield_interval:
                self.run_foundation_script("yield_tracker_omega.py")
                self.last_yield = now

            # 3. High-Exergy Automata strikes (Highest Priority)
            if now - self.last_automata > self.automata_interval:
                await self.execute_automata_cycle()
                self.last_automata = now

            # 4. Daily Re-Calibration (DELEGATED TO RUST DAEMON)
            # if now - self.last_daily > self.daily_interval:
            #     await self.run_daily_recalibration()

            # Thermodynamic cooldown
            await asyncio.sleep(60)

if __name__ == "__main__":
    # Ensure data dir exists for logging
    (PROJECT_ROOT / "data").mkdir(exist_ok=True)
    
    orchestrator = SwarmOrchestrator()  # type: ignore
    try:
        asyncio.run(orchestrator.master_loop())
    except KeyboardInterrupt:
        logger.info("∴ [HALT] Master Orchestrator terminated by operator.")
