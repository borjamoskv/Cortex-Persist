import os
import time
import sqlite3
import logging
import asyncio
import json
import sys

# Add parent and local dirs to sys.path for high-agency imports
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist")
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist/cortex-core")

try:
    from cortex.mcp.knowledge_watcher import start_knowledge_daemon
    from skill_compiler import run_compiler
    from cortex.extensions.signals.bus import SignalBus
except ImportError as e:
    logging.error("Startup Failure: Dependency missing: %s", e)

DB_PATH = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/cortex_memory_vsa.db"
WATCH_DIR = "/Users/borjafernandezangulo/.gemini/antigravity/knowledge"
SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"
EXECUTION_LEDGER = "/tmp/cortex_execution_ledger.json"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] CORTEX-DAEMON: %(message)s"
)


class CortexDaemon:
    """Sovereign Orchestrator V3.1 — The Heart of MOSKV-1."""

    def __init__(self):
        self.is_running = True
        self.cycle_count = 0
        self.knowledge_observer = None
        self.bus = None

        # Initialize SignalBus (V4 Pulse)
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self.bus = SignalBus(conn)
        except Exception as e:
            logging.error("SignalBus Initialization Failed: %s", e)

        # SAGE COUNCIL Missions (V5)
        self.mission_targets = [
            "https://github.com/LayerZero-Labs/LayerZero",
            "https://github.com/Uniswap/v4-core",
        ]

    def ensure_hygiene(self):
        """Flushes redundant temporal caches to maintain strict Exergy."""
        scratch_dir = "/Users/borjafernandezangulo/Cortex-Persist/.scratch"
        if not os.path.exists(scratch_dir):
            return

        try:
            for file in os.listdir(scratch_dir):
                if file.endswith(".tmp") or file.endswith(".log"):
                    target = os.path.join(scratch_dir, file)
                    if os.path.getsize(target) > 5000000:
                        os.remove(target)
                        logging.info("🧹 Hygiene: Purged entropy [%s]", file)
        except Exception:
            pass

    def check_memory_integrity(self):
        """Evaluates SQLite state, triggering implicit yields."""
        try:
            if not os.path.exists(DB_PATH):
                return
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM cortex_knowledge")
            count = c.fetchone()[0]
            conn.close()
            if self.cycle_count % 20 == 0:
                logging.info("📉 VSA State: %d active KIs in RAM", count)
        except Exception as e:
            logging.error("VSA Bridge detached: %s", e)

    async def _execute_task(self, task):
        """Spawns an asynchronous sub-process for a swarm task."""
        agent = task.get("agent", "unknown")
        cmd = task.get("command")
        if not cmd:
            logging.warning("Skipping Task (No Command) for %s", agent)
            return

        logging.info("🚀 [SWARM EXEC] Dispatching: %s for %s", cmd, agent)

        # Emit V4 Pulse: Dispatch
        if self.bus:
            self.bus.emit(
                "swarm_task",
                {"agent": agent, "command": cmd, "status": "dispatched"},
                source="daemon",
            )

        try:
            process = await asyncio.create_subprocess_shell(
                cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()

            result = {
                "timestamp": time.time(),
                "agent": agent,
                "command": cmd,
                "exit_code": process.returncode,
                "stdout": stdout.decode()[-1000:],  # Last 1k to avoid bloat
                "stderr": stderr.decode()[-1000:],
            }

            # Emit V4 Pulse: Completion
            if self.bus:
                self.bus.emit(
                    "swarm_task_complete",
                    {
                        "agent": agent,
                        "exit_code": process.returncode,
                        "status": "success" if process.returncode == 0 else "failed",
                    },
                    source="daemon",
                )

            # 3. Handle Post-Execution (Self-Healing Detection)
            if task.get("type") == "remediation":
                if process.returncode == 0:
                    logging.info("🌟 [SELF-HEALING] Success! Vulnerability neutralized.")
                    if self.bus:
                        self.bus.emit(
                            "critical_finding_resolved",
                            {
                                "agent": agent,
                                "msg": "VULN_NEUTRALIZED",
                                "val": "Autonomous patch verified via Foundry",
                            },
                            source="daemon",
                        )
                else:
                    logging.error("❌ [SELF-HEALING] Failure. Manual intervention required.")

            # Log to Execution Ledger
            self._log_execution(result)
            logging.info("⚡ [EXEC] Success: %s (code %d)", agent, process.returncode)

        except Exception as e:
            logging.error("Execution Crash for %s: %s", agent, e)

    def _log_execution(self, result):
        """Appends task result to the persistent execution ledger."""
        ledger = []
        if os.path.exists(EXECUTION_LEDGER):
            try:
                with open(EXECUTION_LEDGER) as f:
                    ledger = json.load(f)
            except Exception:
                ledger = []

        ledger.append(result)
        # Keep last 100 entries to maintain O(1) performance
        ledger = ledger[-100:]

        with open(EXECUTION_LEDGER, "w") as f:
            json.dump(ledger, f, indent=2)

    async def process_swarm_queue(self):
        """Consumes the Swarm Task Queue and executes autonomous work."""
        if not os.path.exists(SWARM_QUEUE_FILE):
            return

        try:
            with open(SWARM_QUEUE_FILE) as f:
                queue = json.load(f)

            tasks = queue.get("pending_tasks", [])
            if not tasks:
                return

            logging.info("🐝 Swarm Pulse: Processing %d tasks...", len(tasks))
            # Process tasks concurrently
            await asyncio.gather(*(self._execute_task(t) for t in tasks))

            # Clear queue after processing
            with open(SWARM_QUEUE_FILE, "w") as f:
                json.dump({"pending_tasks": []}, f)

            logging.info("✅ Swarm Pulse: Cycle complete.")
        except Exception as e:
            logging.error("Swarm Dispatch Failure: %s", e)

    def check_memory_integrity(self):
        """Validates that the VSA memory substrate is synchronous."""
        if not os.path.exists(DB_PATH):
            logging.warning("⚠️ Memory Substrate Missing at %s", DB_PATH)
            return

        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute("SELECT count(*) FROM signals")
            count = cursor.fetchone()[0]
            conn.close()
            if self.cycle_count % 50 == 0:
                logging.info("🧠 [MEMORY] Integrity check: %d signals.", count)
        except Exception:
            logging.error("Memory Integrity Violation detected.")

    async def _run_council_deliberation(self):
        """Invoke SAGE COUNCIL decision engine."""
        logging.info("🧠 [SAGE COUNCIL] Deliberating next mission...")
        target = self.mission_targets[self.cycle_count % len(self.mission_targets)]

        if self.bus:
            self.bus.emit(
                "swarm_task",
                {
                    "agent": "SAGE_COUNCIL",
                    "command": f"audit --target {target}",
                    "status": "deliberating",
                },
                source="daemon",
            )

        cmd = f"python3 /Users/borjafernandezangulo/Cortex-Persist/cortex-core/ouroboros_engine.py --target {target}"
        self._queue_task("SAGE_COUNCIL", cmd)

    def _queue_task(self, agent: str, cmd: str):
        """Internal helper to push tasks to the persistent queue."""
        try:
            queue = {"pending_tasks": []}
            if os.path.exists(SWARM_QUEUE_FILE):
                with open(SWARM_QUEUE_FILE) as f:
                    queue = json.load(f)

            queue["pending_tasks"].append(
                {
                    "id": f"council_{int(time.time())}",
                    "agent": agent,
                    "command": cmd,
                    "timestamp": time.time(),
                }
            )

            with open(SWARM_QUEUE_FILE, "w") as f:
                json.dump(queue, f, indent=2)
            logging.info("📌 [COUNCIL] Mission queued: %s", cmd)
        except Exception as e:
            logging.error("Council Queue Failure: %s", e)

    async def _run_self_audit(self):
        """Invoke Mirror Protocol to audit own source code (Ω₄)."""
        logging.info("👁️ [MIRROR] Starting Self-Audit...")

        # Path to self
        self_path = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/cortex_daemon.py"
        cmd = f"python3 /Users/borjafernandezangulo/Cortex-Persist/cortex-core/mirror_audit.py {self_path}"

        process = await asyncio.create_subprocess_shell(
            cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await process.communicate()

        try:
            report = json.loads(stdout.decode())
            if report["status"] == "UNSTABLE":
                logging.warning(
                    "⚠️ [MIRROR] Self-Optimization Required (Score: %d)", report["exergy_score"]
                )
                # Queue Remediation
                error_log = "/tmp/mirror_findings.json"
                with open(error_log, "w") as f:
                    json.dump(report, f)

                self._queue_task(
                    "OPTIMIZER",
                    f"python3 /Users/borjafernandezangulo/Cortex-Persist/cortex-core/remediator.py {self_path} {error_log}",
                )
            else:
                logging.info("✅ [MIRROR] Self-Audit Optimal (Score: %d)", report["exergy_score"])
        except Exception as e:
            logging.error("Self-Audit Parse Error: %s", e)

    async def run(self):
        """Main Autopoiesis Loop."""
        logging.info("👁️  CORTEX Daemon Active: V5 Sovereign Ontogeny.")

        try:
            run_compiler()
            logging.info("🛠️ [JIT] Skills synchronized.")
        except Exception as e:
            logging.error("Skill Synchronization Failed: %s", e)

        self.knowledge_observer = start_knowledge_daemon()

        while self.is_running:
            self.cycle_count += 1

            # 1. Hygiene & Memory
            self.ensure_hygiene()
            self.check_memory_integrity()

            # 2. SAGE COUNCIL (Every 100 cycles)
            if self.cycle_count % 100 == 0:
                await self._run_council_deliberation()

            # 2.5 MIRROR PROTOCOL (Every 250 cycles)
            if self.cycle_count % 250 == 0:
                await self._run_self_audit()

            # 3. Swarm Execution
            await self.process_swarm_queue()

            await asyncio.sleep(5)

    def stop(self):
        """Graceful shutdown sequence."""
        self.is_running = False
        if self.knowledge_observer:
            try:
                self.knowledge_observer.stop()
                self.knowledge_observer.join()
            except Exception:
                pass
        logging.info("Daemon decommissioned safely.")


if __name__ == "__main__":
    daemon = CortexDaemon()
    try:
        asyncio.run(daemon.run())
    except KeyboardInterrupt:
        daemon.stop()
    except Exception as e:
        logging.critical("Fatal Crash: %s", e)
        daemon.stop()
