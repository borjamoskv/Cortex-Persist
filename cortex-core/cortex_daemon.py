import os
import time
import sqlite3
import logging
import asyncio
import json
import shlex
import sys
import tempfile

MAX_CENTURIONS = 10000

# Add parent and local dirs to sys.path for high-agency imports
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist")
sys.path.append("/Users/borjafernandezangulo/Cortex-Persist/cortex-core")

from cortex.config import DB_PATH
from cortex.mcp.knowledge_watcher import start_knowledge_daemon
from skill_compiler import run_compiler
from init_vsa import initialize_substrate
from cortex.extensions.signals.bus import SignalBus
from cortex_engine_parallel import ENGINE as PARALLEL_ENGINE  # V6 Parallel Hub

# V9 Security Hardening: Anthropic Assimilation Protocol
from cortex.extensions.security.security_monitor import (
    SecurityMonitorClassifier,
    ParameterProvenance,
)
from cortex.extensions.security.stochastic_sandbox import StochasticSandbox
from cortex.events.loop import sovereign_run

WATCH_DIR = "/Users/borjafernandezangulo/.gemini/antigravity/knowledge"
SWARM_QUEUE_FILE = "/tmp/cortex_swarm_queue.json"
EXECUTION_LEDGER = "/tmp/cortex_execution_ledger.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] CORTEX-DAEMON: %(message)s"
)


def _atomic_write_text(path: str, content: str) -> None:
    """Persist text via same-directory temp file and atomic replace."""
    target_dir = os.path.dirname(path) or "."
    fd, temp_path = tempfile.mkstemp(prefix="cortex_daemon_", dir=target_dir, text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as tmp_file:
            tmp_file.write(content)
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


class CortexDaemon:
    """Sovereign Orchestrator V3.1 — The Heart of MOSKV-1."""

    def __init__(self):
        self.is_running = True
        self.cycle_count = 0
        self.knowledge_observer = None
        self.bus = None
        self._current_user_request = ""  # Tracks the originating user request
        
        # V6: Zero-Spawn Actor Queue (Max 10k capacity)
        self.task_queue = asyncio.Queue(maxsize=10000)
        self.active_workers = []
        
        # V9: Security Monitor Classifier (7 Intent Axioms)
        self.security_monitor = SecurityMonitorClassifier()
        self.stochastic_sandbox = StochasticSandbox()
        
        # V6: Parallel SQLite Sharding Semaphore
        self.db_semaphore = asyncio.Semaphore(100)
        logging.info("🛡️ [SECURITY] SecurityMonitorClassifier + StochasticSandbox initialized")
        
        # Initialize SignalBus (V4 Pulse)
        try:
            conn = sqlite3.connect(DB_PATH, check_same_thread=False)
            self.bus = SignalBus(conn)
        except Exception as e:
            logging.error("SignalBus Initialization Failed: %s", e)

        # SAGE COUNCIL Missions (V5)
        self.mission_targets = [
            "https://github.com/LayerZero-Labs/LayerZero",
            "https://github.com/Uniswap/v4-core"
        ]

    def ensure_hygiene(self):
        """Flushes redundant temporal caches to maintain strict Exergy."""
        import subprocess
        try:
            subprocess.run(["pkill", "-f", "du -sh /*"], stderr=subprocess.DEVNULL)
            subprocess.run(["pkill", "-f", "python3 -c \"    width: 100%"], stderr=subprocess.DEVNULL)
        except Exception:
            pass

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

    async def _execute_task(self, task):
        """Spawns an asynchronous sub-process for a swarm task."""
        agent = task.get("agent", "unknown")
        cmd = task.get("command")
        if not cmd:
             logging.warning("Skipping Task (No Command) for %s", agent)
             return

        # --- [V9 SECURITY MONITOR: 7 INTENT AXIOMS & TAINT TRACKING (Phase 4)] ---
        verdict = self.security_monitor.classify(
            task=task,
            user_request=self._current_user_request,
            provenance=task.get("provenance", ParameterProvenance.AGENT_INFERRED),
            tool_outputs=task.get("tool_outputs", None)
        )
        
        override_signature = None  # Phase 5 tracking

        if not verdict.allowed:
            import time
            pulse_id = f"pulse_{int(time.time())}"
            logging.critical("🚨 [SECURITY MONITOR] Blocked: %s (Reason: %s)", cmd, verdict.reason)
            if self.bus:
                self.bus.emit("security_block_interactive", {
                    "agent": agent, 
                    "command": cmd, 
                    "reason": verdict.axiom_violated or "SCOPE_CREEP",
                    "pulse_id": pulse_id
                }, source="daemon")

                # Pausa Táctica: Espera al Consentimiento Humano (Interactive Pulse)
                logging.info("⏸️ Esperando autorización humana vía WebSockets (timeout: 300s).")
                approved = False
                backoff_sleep = 0.5
                max_sleep = 5.0
                elapsed_time = 0.0
                timeout_limit = 300.0

                while elapsed_time < timeout_limit:
                    import asyncio
                    await asyncio.sleep(backoff_sleep)
                    elapsed_time += backoff_sleep
                    backoff_sleep = min(backoff_sleep * 1.5, max_sleep)
                    
                    try:
                        override_signals = self.bus.poll(event_type="human_override", consumer=f"daemon_{pulse_id}", limit=10)
                        for sig in override_signals:
                            import json
                            payload = json.loads(sig.payload) if isinstance(sig.payload, str) else sig.payload
                            if payload.get("pulse_id") == pulse_id:
                                if payload.get("action") == "APPROVED":
                                    # Phase 5: Cryptographic Logic
                                    from cortex.extensions.security.signatures import get_default_signer, generate_keypair, configure_signer
                                    client_sig = payload.get("signature")
                                    
                                    signer = get_default_signer()
                                    if not signer:
                                        priv, pub = generate_keypair()
                                        signer = configure_signer(priv)
                                        logging.info("🔑 [CRYPTO] Auto-generated Ed25519 keyring for daemon.")
                                        
                                    if client_sig:
                                        try:
                                            signer.verify(content=cmd, fact_hash=pulse_id, signature_b64=client_sig)
                                            override_signature = client_sig
                                            logging.info("✅ [CRYPTO] Notch Signature VÁLIDA.")
                                        except Exception as sig_err:
                                            logging.critical("💀 [CRYPTO] FIRMA INVÁLIDA (Spoofing Alert): %s", sig_err)
                                            return
                                    else:
                                        override_signature = signer.sign(content=cmd, fact_hash=pulse_id)
                                        logging.info("✍️ [CRYPTO] Daemon Auto-Signed the Override.")
                                        
                                    approved = True
                                    break
                                else:
                                    logging.info("🔒 [SECURITY MONITOR] Humano RECHAZÓ la operación operando en Notch.")
                                    return
                        if approved:
                            break
                    except Exception as e:
                        logging.error("Fallo durante el Polling de Interactive Pulse: %s", e)

                if not approved:
                    logging.info("⏳ [SECURITY MONITOR] Timeout sin respuesta Humana. Foso restaurado. Tarea abortada.")
                    return
                else:
                    logging.warning("🔓 [SECURITY MONITOR] Human Override Engaged. Bypass activado por el Notch. Ejecutando...")
            else:
                return

        # --- [V9 STOCHASTIC SANDBOX] ---
        sandboxed = self.stochastic_sandbox.intercept(cmd, cwd="/Users/borjafernandezangulo/Cortex-Persist")
        execute_cmd = sandboxed.redirected_cmd if sandboxed.is_redirected else sandboxed.original_cmd

        # --- [BASH SANDBOXING + OS-LEVEL PRISON] ---
        # Isolate iterations via Apple sandbox-exec.
        from cortex.extensions.security.security_monitor import SecurityMonitorClassifier
        # Parse Intent for JIT Network
        is_npm_git = execute_cmd.strip().startswith("npm ") or execute_cmd.strip().startswith("git ") or execute_cmd.strip().startswith("forge ")
        
        sb_template_path = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/cortex_prison.sb.template"
        try:
            with open(sb_template_path, "r") as f:
                sb_content = f.read()
        except FileNotFoundError:
            # Fallback if the template hasn't been written yet or missing
            sb_content = "(version 1)\n(allow default)"
            
        if is_npm_git:
            net_rules = "(allow network-outbound)\n"
            logging.info("🌐 [JIT SANDBOX] Network granted (npm/git/forge intent recognized).")
        else:
            net_rules = "(deny network-outbound)\n"
            logging.info("🚫 [JIT SANDBOX] Network ZERO-OUTBOUND enforced.")
            
        sb_content_rendered = sb_content.replace("{{NETWORK_OUTBOUND_RULES}}", net_rules)
        
        # Write ephemeral jail profile
        import uuid
        jit_jail_path = os.path.join(tempfile.gettempdir(), f"jail_{uuid.uuid4().hex[:8]}.sb")
        _atomic_write_text(jit_jail_path, sb_content_rendered)

        # Removed bash 'timeout 180', using Orphan Slayer Python approach
        sandbox_cmd = f"sandbox-exec -f {jit_jail_path} /bin/sh -lc {execute_cmd!r}"

        logging.info("🚀 [SWARM EXEC] Dispatching OS-Sandboxed Task: %s for %s", execute_cmd, agent)
        
        # Emit V4 Pulse: Dispatch
        if self.bus:
            self.bus.emit("swarm_task", {
                "agent": agent, 
                "command": sandbox_cmd, 
                "status": "dispatched"
            }, source="daemon")

        try:
            import time
            import asyncio
            import os
            import signal

            process = await asyncio.create_subprocess_exec(
                "sandbox-exec",
                "-f",
                jit_jail_path,
                "/bin/sh",
                "-lc",
                execute_cmd,
                stdin=asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                preexec_fn=os.setsid,
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=180.0)
            except asyncio.TimeoutError:
                # Orphan Slayer Triggered
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                process.returncode = 124
                stdout, stderr = b"", b"CORTEX KINETIC SHIELD: Timeout Orphan Slayer Triggered. Process group destroyed."
                logging.error("💀 [ORPHAN SLAYER] Timeout exceeded. Process group %d annihilated.", process.pid)
            
            # Clean up JIT profile
            if os.path.exists(jit_jail_path):
                os.remove(jit_jail_path)

            result = {
                "timestamp": time.time(),
                "agent": agent,
                "command": execute_cmd,
                "exit_code": process.returncode if process.returncode is not None else 1,
                "stdout": stdout.decode()[-1000:], # Last 1k to avoid bloat
                "stderr": stderr.decode()[-1000:]
            }
            if override_signature:
                result["override_signature"] = override_signature
                result["provenance"] = "USER_EXPLICIT_SIGNED"

            # Emit V4 Pulse: Completion
            if self.bus:
                self.bus.emit("swarm_task_complete", {
                    "agent": agent,
                    "exit_code": process.returncode,
                    "status": "success" if process.returncode == 0 else "failed"
                }, source="daemon")
            
            # 3. Handle Post-Execution (Self-Healing Detection)
            if task.get("type") == "remediation":
                if process.returncode == 0:
                    logging.info("🌟 [SELF-HEALING] Success! Vulnerability neutralized.")
                    if self.bus:
                        self.bus.emit("critical_finding_resolved", {
                            "agent": agent,
                            "msg": "VULN_NEUTRALIZED",
                            "val": "Autonomous patch verified via Foundry"
                        }, source="daemon")
                else:
                    logging.error("❌ [SELF-HEALING] Failure. Manual intervention required.")

            # 4. Cleanup stochastic sandbox arena
            if sandboxed.is_redirected and sandboxed.arena_path:
                self.stochastic_sandbox.cleanup(sandboxed.arena_path)

            # Log to Execution Ledger
            self._log_execution(result)
            logging.info("⚡ [EXEC] Success: %s (code %d)", agent, process.returncode)

        except Exception as e:
            logging.error("Execution Crash for %s: %s", agent, e)
            # Cleanup stochastic sandbox arena
            if (
                sandboxed.is_redirected
                and sandboxed.arena_path
            ):
                self.stochastic_sandbox.cleanup(
                    sandboxed.arena_path
                )

            self._log_execution(result)
            logging.info(
                "⚡ [EXEC] %s (code %d)",
                agent,
                process.returncode,
            )

        except Exception as e:
            logging.error(
                "Execution Crash for %s: %s", agent, e
            )

    def _log_execution(self, result):
        """Appends task result to the persistent execution ledger."""
        ledger = []
        if os.path.exists(EXECUTION_LEDGER):
             try:
                 with open(EXECUTION_LEDGER, "r") as f:
                     ledger = json.load(f)
             except Exception:
                 ledger = []
        
        ledger.append(result)
        # Keep last 100 entries to maintain O(1) performance
        ledger = ledger[-100:]

        ledger_dir = os.path.dirname(EXECUTION_LEDGER) or "."
        with tempfile.NamedTemporaryFile(
            "w",
            dir=ledger_dir,
            delete=False,
            encoding="utf-8",
        ) as tmp_file:
             json.dump(ledger, tmp_file, indent=2)
             tmp_path = tmp_file.name
        os.replace(tmp_path, EXECUTION_LEDGER)

    async def _centurion_worker_loop(self, worker_id: int):
        """Persistent worker loop pulling from V6 Task Queue (Zero-Spawn Mode)."""
        while self.is_running:
            try:
                task = await self.task_queue.get()
                logging.info(f"🐝 Centurion-{worker_id} acquired task: {task.get('agent')}")
                
                async with self.db_semaphore:
                    # V6 Multiplexing: Qwen para masa operativa, Gemini para Mando Central
                    agent_id = task.get("agent", "unknown")
                    task["llm_boundary"] = "gemini-3.1-pro" if "Commander" in agent_id else "qwen-2.5-coder-7b (OpenCode-Omega)"
                    await self._execute_task(task)
                
                self.task_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Centurion-{worker_id} crashed: {e}")

    async def process_swarm_queue(self):
        """Pushes tasks to the V6 Zero-Spawn Queue instead of spawning OS threads."""
        if not os.path.exists(SWARM_QUEUE_FILE):
             return
             
        try:
            with open(SWARM_QUEUE_FILE, "r") as f:
                 queue = json.load(f)
                 
            tasks = queue.get("pending_tasks", [])
            if not tasks:
                 return

            # Feed persistent queue
            added = 0
            for t in tasks[:MAX_CENTURIONS]:
                 if not self.task_queue.full():
                     await self.task_queue.put(t)
                     added += 1

            remaining = tasks[added:]
            fd, temp_path = tempfile.mkstemp(
                prefix="cortex_swarm_queue_",
                dir=os.path.dirname(SWARM_QUEUE_FILE) or None,
            )
            with os.fdopen(fd, "w") as f:
                 json.dump({"pending_tasks": remaining}, f)
            os.replace(temp_path, SWARM_QUEUE_FILE)

            logging.info("🐝 Swarm Legion Pulse: %d tasks injected into Zero-Spawn Pool.", added)
        except Exception as e:
            logging.error("Swarm Task Injection Failure: %s", e)

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
        """Invoke SAGE COUNCIL decision engine (Parallel Strike Logic V6)."""
        logging.info("🧠 [SAGE COUNCIL] Scaling Legion Strike across all mission targets...")
        
        for target in self.mission_targets[:3]: # Scale to first 3 repos simultaneously
            if self.bus:
                self.bus.emit("swarm_task", {
                    "agent": "SAGE_COUNCIL",
                    "command": f"audit --target {target}",
                    "status": "scaling_legion"
                }, source="daemon")

            cmd = f"python3 /Users/borjafernandezangulo/Cortex-Persist/cortex-core/ouroboros_engine.py --target {target}"
            self._queue_task("SAGE_COUNCIL", cmd)

    def _queue_task(self, agent: str, cmd: str):
        """Internal helper to push tasks to the persistent queue."""
        try:
            queue = {"pending_tasks": []}
            if os.path.exists(SWARM_QUEUE_FILE):
                with open(SWARM_QUEUE_FILE, "r") as f:
                    queue = json.load(f)
            
            queue["pending_tasks"].append({
                "id": f"council_{int(time.time())}",
                "agent": agent,
                "command": cmd,
                "timestamp": time.time()
            })

            queue_dir = os.path.dirname(SWARM_QUEUE_FILE) or "."
            with tempfile.NamedTemporaryFile(
                "w",
                dir=queue_dir,
                delete=False,
                encoding="utf-8",
            ) as tmp_file:
                json.dump(queue, tmp_file, indent=2)
                tmp_path = tmp_file.name
            os.replace(tmp_path, SWARM_QUEUE_FILE)
            logging.info("📌 [COUNCIL] Mission queued: %s", cmd)
        except Exception as e:
            logging.error("Council Queue Failure: %s", e)

    async def _run_self_audit(self):
        """Invoke Mirror Protocol to audit own source code (Ω₄)."""
        logging.info("👁️ [MIRROR] Starting Self-Audit...")
        
        # Path to self
        self_path = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/cortex_daemon.py"
        mirror_audit_path = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/mirror_audit.py"

        process = await asyncio.create_subprocess_exec(
            "python3",
            mirror_audit_path,
            self_path,
            stdin=asyncio.subprocess.DEVNULL,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            logging.error(
                "Self-Audit Execution Failed: %s",
                stderr.decode(errors="replace").strip(),
            )
            return
        
        try:
            report = json.loads(stdout.decode())
            if report["status"] == "UNSTABLE":
                logging.warning("⚠️ [MIRROR] Self-Optimization Required (Score: %d)", report["exergy_score"])
                # Queue Remediation
                error_log = "/tmp/mirror_findings.json"
                _atomic_write_text(error_log, json.dumps(report))
                
                remediator_path = "/Users/borjafernandezangulo/Cortex-Persist/cortex-core/remediator.py"
                self._queue_task(
                    "OPTIMIZER",
                    " ".join(
                        [
                            "python3",
                            shlex.quote(remediator_path),
                            shlex.quote(self_path),
                            shlex.quote(error_log),
                        ]
                    ),
                )
            else:
                logging.info("✅ [MIRROR] Self-Audit Optimal (Score: %d)", report["exergy_score"])
        except Exception as e:
            logging.error("Self-Audit Parse Error: %s", e)

    async def run(self):
        """Main Autopoiesis Loop."""
        logging.info("👁️  CORTEX Daemon Active: V5 Sovereign Ontogeny.")
        
        try:
            initialize_substrate()
            run_compiler()
            logging.info("🛠️ [JIT] Substrate and Skills synchronized.")
        except Exception as e:
            logging.error("Startup Synchronization Failed: %s", e)

        self.knowledge_observer = start_knowledge_daemon()

        # V6: Ignite 100 Persistent Centurion Workers (Zero-Spawn Pool)
        for i in range(100):
             worker_task = asyncio.create_task(self._centurion_worker_loop(i))
             self.active_workers.append(worker_task)
        logging.info("🐝 [LEGION] 100 Persistent Centurion Workers Online.")

        while self.is_running:
            await asyncio.sleep(0.1) # AUTO_THROTTLE_V6
            self.cycle_count += 1
            
            # 1. Hygiene & Memory
            self.ensure_hygiene()
            self.check_memory_integrity()
            
            # 2. SAGE COUNCIL (Every 25 cycles for fast feedback)
            if self.cycle_count % 25 == 0:
                await self._run_council_deliberation()
            
            # 2.5 MIRROR PROTOCOL (Every 50 cycles)
            if self.cycle_count % 50 == 0:
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
        sovereign_run(daemon.run())
    except KeyboardInterrupt:
        daemon.stop()
    except Exception as e:
        logging.critical("Fatal Crash: %s", e)
        daemon.stop()
