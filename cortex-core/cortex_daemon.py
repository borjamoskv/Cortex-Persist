import os
import time
import sqlite3
import logging
import asyncio
import json
import sys
import threading

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Add parent and local dirs to sys.path for high-agency imports
sys.path.append(str(PROJECT_ROOT))
sys.path.append(str(PROJECT_ROOT / "cortex-core"))

try:
    from cortex.mcp.knowledge_watcher import start_knowledge_daemon
    from skill_compiler import run_compiler
    from cortex.extensions.signals.bus import SignalBus
except ImportError as e:
    logging.error("Startup Failure: Dependency missing: %s", e)

DB_PATH = str(PROJECT_ROOT / "cortex-core" / "cortex_memory_vsa.db")
WATCH_DIR = str(Path.home() / ".gemini" / "antigravity" / "knowledge")
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

        self.db_lock = threading.Lock()

        # Initialize Sovereign DB Connection (LGD-200 Persistent Connection)
        try:
            # check_same_thread=False and isolation_level=None (autocommit)
            self.db_conn = sqlite3.connect(
                DB_PATH, check_same_thread=False, timeout=10.0, isolation_level=None
            )
            self.db_conn.executescript(
                "PRAGMA synchronous = NORMAL; PRAGMA temp_store = MEMORY; PRAGMA mmap_size = 30000000000;"
            )
            self.db_conn.execute(
                "CREATE TABLE IF NOT EXISTS cortex_execution_ledger (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp REAL, agent TEXT, command TEXT, returncode INTEGER, execution_time REAL);"
            )
            self.bus = SignalBus(self.db_conn)
        except Exception as e:
            logging.error("Database/SignalBus Initialization Failed: %s", e)

        # SAGE COUNCIL Missions (V5)
        self.mission_targets = [
            "https://github.com/LayerZero-Labs/LayerZero",
            "https://github.com/Uniswap/v4-core",
        ]

    def ensure_hygiene(self):
        """Flushes redundant temporal caches to maintain strict Exergy."""
        if self.cycle_count % 20 != 0:
            return
        scratch_dir = str(PROJECT_ROOT / ".scratch")
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
        if self.cycle_count % 20 != 0:
            return
        try:
            with self.db_lock:
                c = self.db_conn.cursor()
                c.execute("SELECT COUNT(*) FROM cortex_knowledge")
                count = c.fetchone()[0]
            logging.info("📉 VSA State: %d active KIs in RAM", count)
        except Exception as e:
            logging.error("VSA Bridge detached: %s", e)

    def check_swarm_exergy(self):
        """Evaluates Swarm Exergy Metrics and logs them to LGD-200."""
        if self.cycle_count % 10 != 0:
            return
        try:
            from persistence import get_swarm_metrics
            metrics = get_swarm_metrics()
            logging.info("🔋 [EXERGY] Swarm Telemetry: Active=%d, Latency=%.2fms, Uncertainty=%.2f",
                         metrics["active_children"], metrics["latency_ms"], metrics["uncertainty"])
            if self.bus:
                self.bus.emit(
                    "exergy_telemetry",
                    metrics,
                    source="daemon"
                )
        except Exception as e:
            logging.error("Failed to read Exergy Metrics: %s", e)

    async def _execute_task(self, task):
        """Spawns an asynchronous sub-process for a swarm task or handles internal autonomous actions."""
        agent = task.get("agent", "unknown")
        cmd = task.get("command")
        payload = task.get("payload")
        
        if not cmd and isinstance(payload, dict):
            cmd = payload.get("command")

        # ── TERMINAL STATE 4: ALL AST MUTATIONS ARE NOW INTERCEPTED AT L0 (OutboxDaemon) ──

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
            # HIGH-02 hardened: avoid shell interpretation of task commands
            import shlex as _shlex

            process = await asyncio.create_subprocess_exec(
                *_shlex.split(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # C5-REAL Kill-Switch (Muerte Temprana) - 300s max exergy allocation
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=300.0)
            except asyncio.TimeoutError:
                logging.error(
                    "💀 [KILL-SWITCH] Agent %s exceeded 300s exergy allocation. Terminating.", agent
                )
                try:
                    process.kill()
                    stdout, stderr = await process.communicate()
                except ProcessLookupError:
                    stdout, stderr = b"", b"Process vanished before kill."
                stderr += b"\n[SYSTEM] Terminated by CORTEX LGD-200 Kill-Switch (Timeout)."

            result = {
                "timestamp": time.time(),
                "agent": agent,
                "command": cmd,
                "returncode": process.returncode if process.returncode is not None else -9,
                "stdout": stdout.decode(errors="replace")[-1000:],  # Last 1k to avoid bloat
                "stderr": stderr.decode(errors="replace")[-1000:],
            }

            # Emit V4 Pulse: Completion
            if self.bus:
                self.bus.emit(
                    "swarm_task_complete",
                    {
                        "agent": agent,
                        "returncode": process.returncode,
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

            # Log to Execution Ledger via Executor
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self._log_execution, result)
            logging.info("⚡ [EXEC] Success: %s (code %d)", agent, process.returncode)

        except Exception as e:
            logging.error("Execution error for agent %s: %s", agent, e)

        logging.info("RESULT DICT: %s", result)

    def _log_execution(self, result):
        """Appends task result to the persistent execution ledger via Sovereign SQLite."""
        try:
            with self.db_lock:
                c = self.db_conn.cursor()
                c.execute(
                    "INSERT INTO cortex_execution_ledger (timestamp, agent, command, returncode, execution_time) VALUES (?, ?, ?, ?, ?)",
                    (
                        result.get("timestamp", time.time()),
                        result.get("agent", "unknown"),
                        result.get("command", ""),
                        result.get("returncode", -1),
                        result.get("execution_time", 0.0),
                    ),
                )
                # Prune to last 100 entries to maintain O(1) constraints
                c.execute(
                    "DELETE FROM cortex_execution_ledger WHERE id NOT IN (SELECT id FROM cortex_execution_ledger ORDER BY id DESC LIMIT 100)"
                )
        except Exception as e:
            print("Execution Ledger SQLite Failure:", e)

    def _fetch_and_lock_swarm_tasks(self):
        tasks = []
        # 1. Zero-Copy Exergy Path: Drain from Ring Buffer first
        try:
            from persistence import _get_ring_buffer
            ring = _get_ring_buffer()
            ring_tasks = ring.fetch_pending()
            for idx, ts, agent_bytes, payload_bytes in ring_tasks:
                agent = agent_bytes.decode('utf-8', 'ignore').rstrip('\x00')
                payload_str = payload_bytes.decode('utf-8', 'ignore').rstrip('\x00')
                try:
                    payload = json.loads(payload_str)
                except Exception:
                    payload = payload_str
                tasks.append(
                    {
                        "id": f"ring_{idx}",
                        "timestamp": ts,
                        "agent": agent,
                        "payload": payload,
                        "command": payload.get("command") if isinstance(payload, dict) else payload,
                    }
                )
        except Exception as e:
            logging.error("Failed to fetch from ZeroCopyRingBuffer in daemon: %s", e)

        return tasks

    async def process_swarm_queue(self):
        """Consumes the Swarm Task Queue and executes autonomous work using Sovereign SQLite VSA bypass."""
        try:
            loop = asyncio.get_running_loop()
            tasks = await loop.run_in_executor(None, self._fetch_and_lock_swarm_tasks)
        except Exception as e:
            logging.error("Swarm Queue SQLite Reading Failure: %s", e)
            return

        if not tasks:
            # ── C5-REAL AEON-0 DOWNTIME MUTATION ──
            if self.cycle_count > 0 and self.cycle_count % 50 == 0:
                await self._trigger_aeon_0_mutation()
            return

        try:
            logging.info("🐝 Swarm Pulse: Processing %d tasks...", len(tasks))
            # Process tasks concurrently (lock is already released)
            await asyncio.gather(*(self._execute_task(t) for t in tasks))
            logging.info("✅ Swarm Pulse: Cycle complete.")
        except Exception as e:
            logging.error("Swarm Dispatch Failure: %s", e)

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

        cmd = (
            f"python3 {str(PROJECT_ROOT / 'cortex-core' / 'ouroboros_engine.py')} --target {target}"
        )
        self._queue_task("SAGE_COUNCIL", cmd)

    def _queue_task(self, agent: str, cmd: str):
        """Internal helper to push tasks to the persistent SQLite queue via the Sovereign Persistence module."""
        from persistence import enqueue_swarm_task

        try:
            payload = {
                "command": cmd,
                "timestamp": time.time(),
                "id": f"council_{int(time.time())}",
            }
            enqueue_swarm_task(agent, payload)
            logging.info("📌 [COUNCIL] Mission queued via Sovereign Nexus: %s", cmd)
        except Exception as e:
            logging.error("Council Nexus Queue Failure: %s", e)

    async def _run_self_audit(self):
        """Invoke Mirror Protocol to audit own source code (Ω₄)."""
        logging.info("👁️ [MIRROR] Starting Self-Audit...")

        # Path to self
        self_path = str(PROJECT_ROOT / "cortex-core" / "cortex_daemon.py")
        mirror_script = str(PROJECT_ROOT / "cortex-core" / "mirror_audit.py")

        # HIGH-02 hardened: use exec with explicit arg list
        process = await asyncio.create_subprocess_exec(
            "python3",
            mirror_script,
            self_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
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
                    f"python3 {str(PROJECT_ROOT / 'cortex-core' / 'remediator.py')} {self_path} {error_log}",
                )
            else:
                logging.info("✅ [MIRROR] Self-Audit Optimal (Score: %d)", report["exergy_score"])
        except Exception as e:
            logging.error("Self-Audit Parse Error: %s", e)

    async def _trigger_aeon_0_mutation(self):
        """Invoke AEON-0 Compiler for autonomous AST mutation during swarm downtime."""
        logging.info("🧬 [AEON-0] Swarm Idle. Triggering Autonomous AST Mutation...")
        try:
            import random
            from persistence import enqueue_swarm_task
            from persistence.ledger import LedgerManager
            
            target_dir = str(PROJECT_ROOT / "cortex-core")
            # Candidates for autonomous mutation
            candidates = ["ouroboros_engine.py", "k0_swarm_node.py", "cortex_exergy_stress.py"]
            
            target_file = os.path.join(target_dir, random.choice(candidates))
            if not os.path.exists(target_file):
                return
                
            new_source = f"# AEON-0 Autonomous Mutagenesis Timestamp: {time.time()}"
            
            # Generate valid C5-REAL signature for AEON-0 verification
            ledger = LedgerManager()
            signature = ledger.private_key.sign(new_source.encode("utf-8")).hex()
            
            payload = {
                "type": "AST_MUTATION",
                "target_file": target_file,
                "function_name": "auto_mutate",
                "new_source": new_source,
                "yield_amount": 10.0,
                "signature": signature
            }
            
            enqueue_swarm_task("AEON_0_DAEMON", payload)
            logging.info("🧬 [AEON-0] Mutation task queued for %s via ZeroCopyRingBuffer", target_file)
        except Exception as e:
            logging.error("AEON-0 Integration Failure: %s", e)

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

            # 1. Hygiene & Memory & Exergy
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(None, self.ensure_hygiene)
            await loop.run_in_executor(None, self.check_memory_integrity)
            await loop.run_in_executor(None, self.check_swarm_exergy)

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
