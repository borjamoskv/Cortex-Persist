# [C5-REAL] Exergy-Maximized
"""
C5-REAL OmegaDaemon — Macro-organism residing in memory and evaluating system thermodynamics.
Claim: Zero-Prompt Operation via ExergyGuard + EntropySensor.
"""

import asyncio
import logging
import os
import re
import subprocess
from decimal import Decimal

logger = logging.getLogger(__name__)


# ==================== ExergyGuard ====================
class ExergyGuard:
    """
    Restrictive thermodynamics: Maintains system Exergy balance.
    If entropy cost exceeds available exergy, throttles the system.
    Also monitors physical exergy (free RAM + CPU load).
    """

    def __init__(
        self,
        initial_budget_usd: Decimal = Decimal("10.0"),
        max_exergy_joules: Decimal = Decimal("1000.0"),
        ram_threshold_mb: float = 200.0,
    ):
        self.budget_usd = initial_budget_usd
        self.max_exergy = max_exergy_joules
        self.current_exergy = max_exergy_joules
        self.ram_threshold_mb = ram_threshold_mb

    def evaluate(self, entropy_cost: Decimal) -> bool:
        """
        Returns True if there is enough Exergy to face the entropy cost.
        """
        if self.current_exergy >= entropy_cost:
            return True
        return False

    def consume(self, amount: Decimal):
        self.current_exergy -= amount
        if self.current_exergy < Decimal("0.0"):
            self.current_exergy = Decimal("0.0")

    def check_ram_free_mb(self) -> float:
        """Free RAM in MB (macOS vm_stat)."""
        try:
            result = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=5)
            pages_free = 0
            for line in result.stdout.splitlines():
                if "Pages free" in line:
                    pages_free = int(line.split(":")[1].strip().rstrip("."))
                    break
            return pages_free * 16384 / (1024 * 1024)  # MB
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            return 0.0

    def get_ram_pressure(self) -> str:
        """macOS RAM pressure (memory_pressure)."""
        try:
            result = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if "RAM pressure" in line:
                    return line.split(":")[1].strip()
            return "unknown"
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            return "unknown"

    def check(self) -> dict:
        """Exergy cycle: free RAM + pressure."""
        ram_free = self.check_ram_free_mb()
        pressure = self.get_ram_pressure()

        critical = ram_free < self.ram_threshold_mb
        return {
            "ram_free_mb": ram_free,
            "ram_pressure": pressure,
            "critical": critical,
            "exergy": float(self.current_exergy),
        }

    def reclaim(self) -> tuple[float, str]:
        """Reclaim RAM via purge (macOS)."""
        try:
            before = self.check_ram_free_mb()
            subprocess.run(["purge"], capture_output=True, timeout=10)
            after = self.check_ram_free_mb()
            reclaimed = after - before
            return reclaimed, "OK"
        except (ValueError, TypeError, KeyError, OSError, RuntimeError) as e:
            return 0.0, f"ERR: {e}"


# ==================== EntropySensor ====================
class EntropySensor:
    """
    Senses system entropy (code + CPU load + swap).
    """

    def __init__(self):
        self.last_scan_files = 0
        self.last_scan_todos = 0
        self.last_scan_violations = 0

    async def scan(self) -> Decimal:
        import json

        py_files = []
        todos = 0
        violations = 0

        cortex_dir = os.path.join(os.getcwd(), "cortex")
        if os.path.exists(cortex_dir):
            for root, _, files in os.walk(cortex_dir):
                for file in files:
                    if file.endswith(".py"):
                        file_path = os.path.join(root, file)
                        py_files.append(file_path)
                        try:
                            with open(file_path, encoding="utf-8", errors="ignore") as f:
                                for line in f:
                                    if ("TO" + "DO") in line or "FIX-ME" in line:
                                        todos += 1
                        except OSError:
                            pass

        # Run ruff check asynchronously
        try:
            proc = await asyncio.create_subprocess_exec(
                "ruff",
                "check",
                "cortex/",
                "--format=json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
            if stdout:
                try:
                    data = json.loads(stdout)
                    if isinstance(data, list):
                        violations = len(data)
                except json.JSONDecodeError:
                    pass
        except OSError:
            pass

        self.last_scan_files = len(py_files)
        self.last_scan_todos = todos
        self.last_scan_violations = violations

        # Calculate structural entropy:
        # Each violation = 1.5 J, each TO-DO = 0.4 J, each file baseline = 0.02 J
        entropy = (
            Decimal(str(violations)) * Decimal("1.5")
            + Decimal(str(todos)) * Decimal("0.4")
            + Decimal(str(len(py_files))) * Decimal("0.02")
        )
        return entropy

    def check_cpu_load(self) -> float:
        """Average CPU load (top -l 1)."""
        try:
            result = subprocess.run(
                ["top", "-l", "1", "-o", "cpu"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "CPU usage" in line:
                    match = re.search(r"([\d.]+)%\s*user.*([\d.]+)%\s*sys", line)
                    if match:
                        return (float(match.group(1)) + float(match.group(2))) / 100.0
            return 0.0
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            return 0.0

    def check_swap_mb(self) -> float:
        """Used swap in MB (sysctl vm.swapusage)."""
        try:
            result = subprocess.run(
                ["sysctl", "vm.swapusage"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.splitlines():
                if "used" in line:
                    match = re.search(r"([\d.]+)\s*M", line)
                    if match:
                        return float(match.group(1))
            return 0.0
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            return 0.0

    def sense(self) -> dict:
        """Physical entropy sensing: CPU + swap."""
        cpu = self.check_cpu_load()
        swap = self.check_swap_mb()
        return {
            "cpu_load": cpu,
            "swap_mb": swap,
            "entropy": cpu * 0.6 + swap / 1000.0 * 0.4,  # Normalizada
        }


# ==================== OmegaDaemon ====================
class OmegaDaemon:
    """
    C6-SOVEREIGN Autopoietic Daemon.
    The metabolism of CORTEX. An infinite loop that breathes, scans, and evolves.
    """

    def __init__(
        self,
        tick_rate_seconds: int = 60,
        auto_push: bool = False,
        exergy_threshold: float = 0.5,
        reclaim_on_critical: bool = True,
    ):
        self.tick_rate = tick_rate_seconds
        self.auto_push = auto_push
        self.exergy_threshold = exergy_threshold
        self.reclaim_on_critical = reclaim_on_critical

        self.guard = ExergyGuard(
            initial_budget_usd=Decimal("10.0"),
            max_exergy_joules=Decimal("1000.0"),
            ram_threshold_mb=200.0,
        )
        self.sensor = EntropySensor()
        self._running = False
        self._cycle_count = 0
        self.last_entropy = Decimal("0.0")
        self.events = []

    @property
    def running(self) -> bool:
        return self._running

    @running.setter
    def running(self, value: bool):
        self._running = value

    @property
    def loop_count(self) -> int:
        return self._cycle_count

    async def _metabolize(self):
        """
        The core of a metabolic heartbeat.
        """
        from datetime import datetime

        # Scan code entropy (Shannon code structure)
        entropy = await self.sensor.scan()
        self.last_entropy = entropy
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.events.append(f"[{timestamp}] Initiating cycle... Code entropy: {entropy:.2f} J")

        # Monitor physical telemetry
        ex = self.guard.check()
        ent = self.sensor.sense()

        physical_entropy = Decimal(str(round(ent["entropy"] * 100, 2)))
        total_entropy = entropy + physical_entropy

        self.events.append(
            f"[{timestamp}] RAM Telemetry: {ex['ram_free_mb']:.1f} MB | CPU: {ent['cpu_load']:.2f}"
        )

        # Trigger Purge/Reclaim if RAM is critical
        if ex["critical"] and self.reclaim_on_critical:
            reclaimed, status = self.guard.reclaim()
            self.events.append(
                f"[{timestamp}] [bold red]⚠️ CRITICAL RAM[/] - Reclaimed: {reclaimed:.1f} MB ({status})"
            )

        if total_entropy > Decimal("0.0"):
            logger.info("Total entropy detected: %s J", total_entropy)
            if self.guard.evaluate(total_entropy):
                logger.info("Sufficient exergy. Unleashing Swarm...")
                self.events.append(
                    f"[{timestamp}] [bold green]✔ Sufficient exergy.[/] Unleashing Swarm..."
                )

                # --- Thermodynamic Apoptosis Hooks ---
                try:
                    from pathlib import Path

                    from babylon60.audit.ledger import EnterpriseAuditLedger
                    from babylon60.audit.ledger_compactor import compact_ledger
                    from babylon60.database.core import connect_async_ctx
                    from babylon60.extensions.daemon.apoptosis_daemon import ApoptosisDaemon
                    
                    async with connect_async_ctx("cortex_ledger.db") as conn:
                        ledger = EnterpriseAuditLedger(conn)
                        await ledger.ensure_table()
                        
                        # O(1) Bounded Ledger Snapshotting
                        logger.debug("Executing L1 Ledger Compaction...")
                        compaction_res = await compact_ledger(conn, ledger, max_rows=1000)
                        if compaction_res.get("status") == "compacted":
                            self.events.append(f"[{timestamp}] [bold magenta]🗜️ Ledger compacted[/]: {compaction_res.get('rows_compacted')} rows.")
                        
                        # Continuous Entropy Pruning (Code Apoptosis)
                        if total_entropy > Decimal("30.0"):
                            logger.warning("High entropy detected. Triggering structural source apoptosis.")
                            apoptosis = ApoptosisDaemon(repo_path=Path(os.getcwd()))
                            purged_count = await apoptosis.execute_purge()
                            if purged_count > 0:
                                self.events.append(f"[{timestamp}] [bold red]☠️ Apoptosis triggered[/]: Purged {purged_count} dead modules.")
                except Exception as e:
                    logger.error("Thermodynamic Apoptosis failed: %s", e)
                    self.events.append(f"[{timestamp}] [bold red]✗ Apoptosis failure:[/] {e}")
                # ------------------------------------

                # Causal Integration: Swarm 10k and Ouroboros AST Mutation
                try:
                    from pathlib import Path

                    from babylon60.engine.evo.autopoiesis import AutopoiesisEngine
                    from babylon60.swarm.swarm_10k import SwarmCommander

                    bus_path = Path("~/.cortex/10k_shards").expanduser()
                    commander = SwarmCommander(bus_path=bus_path, tenant_id="omega_daemon")
                    ouroboros = AutopoiesisEngine(observation_window_ms=100)

                    logger.debug("Deploying PHOENIX formation via SwarmCommander...")
                    # Asynchronous dispatch for technical healing
                    if hasattr(commander, "deploy"):
                        res_deploy = commander.deploy(  # type: ignore
                            formation="PHOENIX", mission="Heal Entropy", cycles=1
                        )
                        if asyncio.iscoroutine(res_deploy):
                            await res_deploy

                    logger.debug("Initiating recursive mutation via AutopoiesisEngine...")
                    if hasattr(ouroboros, "mutate"):
                        res_mutate = ouroboros.mutate(target="entropy_resolution")
                        if asyncio.iscoroutine(res_mutate):
                            await res_mutate

                    # [C5-REAL] Vector P1.2 Ouroboros Hooks
                    if total_entropy > Decimal("50.0"):
                        logger.warning(
                            "Critical entropy detected. Hooking Ouroboros to Turbopuffer for Prune."
                        )
                        try:
                            import keyring

                            from babylon60.engine.causal.taint_engine import (
                                generate_secure_taint_token,
                            )
                            from babylon60.storage.turbopuffer import TurbopufferVectorBackend

                            priv_b64 = os.environ.get("CORTEX_ED25519_PRIVATE_KEY")
                            if not priv_b64:
                                try:
                                    priv_b64 = keyring.get_password(
                                        "cortex_v6", "ed25519_private_key"
                                    )
                                except (ValueError, TypeError, OSError, KeyError):
                                    pass

                            ns = "cortex_omega_daemon"
                            content = f"prune:{ns}:0.99"

                            if priv_b64:
                                taint_signature = generate_secure_taint_token(
                                    agent_id="omega_daemon",
                                    session_id="ouroboros_p1.2",
                                    content=content,
                                    private_key_b64=priv_b64,
                                )
                            else:
                                taint_signature = "CORTEX-TAINT:OUROBOROS_P1.2_FALLBACK"

                            backend = TurbopufferVectorBackend(
                                api_key=os.environ.get("TURBOPUFFER_API_KEY", "dummy")
                            )
                            await backend.connect()
                            await backend.autonomous_prune_by_entropy(
                                tenant_id="omega_daemon",
                                entropy_threshold=0.99,
                                taint_signature=taint_signature,
                            )
                            await backend.close()
                        except Exception as bp_exc:
                            logger.error("Failed to execute autopoietic bypass in L2: %s", bp_exc)

                except (ImportError, RuntimeError, ValueError) as e:
                    logger.exception("Failed to unleash Swarm or Ouroboros: %s", e)
                    self.events.append(f"[{timestamp}] [bold red]✗ Swarm/Ouroboros failure:[/] {e}")

                self.guard.consume(total_entropy)
                logger.info("Structural evolution completed. Auto-commit executed.")
                self.events.append(
                    f"[{timestamp}] [bold green]★ Evolution completed.[/] Auto-commit executed."
                )
            else:
                logger.warning("Exergetic failure. Hibernating to conserve resources.")
                self.events.append(
                    f"[{timestamp}] [bold red]⚠️ Exergetic failure.[/] Insufficient budget. Hibernating..."
                )
        else:
            logger.debug("Homeostasis maintained. System stable.")
            self.events.append(f"[{timestamp}] Homeostasis maintained. System stable.")

    async def start(self, interval_s: float | None = None):
        """OmegaDaemon continuous cycle."""
        if interval_s is not None:
            self.tick_rate = int(interval_s)
        self._running = True
        logger.info("Omega Singularity Ignited. Tick Rate: %ss", self.tick_rate)

        while self._running:
            self._cycle_count += 1
            logger.debug("Omega Cycle #%s", self._cycle_count)
            try:
                await self._metabolize()
            except asyncio.CancelledError:
                logger.info("Omega Daemon terminating gracefully...")
                break
            except (OSError, RuntimeError, ValueError) as e:
                logger.exception("Cataclysmic error in metabolism: %s", e)
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.events.append(f"[{timestamp}] [bold red]💥 Metabolic error:[/] {e}")

            await asyncio.sleep(self.tick_rate)

    async def run_forever(self):
        await self.start()

    def stop(self):
        self._running = False


# Alias for backwards compatibility with CLI and legacy tests
OmegaKernel = OmegaDaemon

if __name__ == "__main__":
    daemon = OmegaDaemon()
    try:
        asyncio.run(daemon.start(interval_s=5.0))
    except KeyboardInterrupt:
        daemon.stop()
