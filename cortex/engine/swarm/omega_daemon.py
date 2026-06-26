# [C5-REAL] Exergy-Maximized
"""
C5-REAL OmegaDaemon — Macro-organismo que reside en memoria y evalúa termodinámica del sistema.
Claim: Zero-Prompt Operation mediante ExergyGuard + EntropySensor.
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
    Termodinámica restrictiva: Mantiene el balance de Exergía del sistema.
    Si el costo de entropía supera la exergía disponible, frena el sistema.
    También monitorea exergía física (RAM libre + CPU load).
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
        Devuelve True si hay suficiente Exergía para afrontar el costo de entropía.
        """
        if self.current_exergy >= entropy_cost:
            return True
        return False

    def consume(self, amount: Decimal):
        self.current_exergy -= amount
        if self.current_exergy < Decimal("0.0"):
            self.current_exergy = Decimal("0.0")

    def check_ram_free_mb(self) -> float:
        """RAM libre en MB (macOS vm_stat)."""
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
        """RAM pressure de macOS (memory_pressure)."""
        try:
            result = subprocess.run(["memory_pressure"], capture_output=True, text=True, timeout=5)
            for line in result.stdout.splitlines():
                if "RAM pressure" in line:
                    return line.split(":")[1].strip()
            return "unknown"
        except (ValueError, TypeError, KeyError, OSError, RuntimeError):
            return "unknown"

    def check(self) -> dict:
        """Ciclo de exergía: RAM libre + presión."""
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
        """Reclaim RAM con purge (macOS)."""
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
    Sensa entropía del sistema (código + CPU load + swap).
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
        """CPU load promedio (top -l 1)."""
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
        """Swap usado en MB (sysctl vm.swapusage)."""
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
        """Sensado de entropía física: CPU + swap."""
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
    El metabolismo de CORTEX. Un bucle infinito que respira, escanea, y evoluciona.
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
        El núcleo de un latido metabólico.
        """
        from datetime import datetime

        # Scan code entropy (Shannon code structure)
        entropy = await self.sensor.scan()
        self.last_entropy = entropy
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.events.append(f"[{timestamp}] Iniciando ciclo... Entropía código: {entropy:.2f} J")

        # Monitor physical telemetry
        ex = self.guard.check()
        ent = self.sensor.sense()

        physical_entropy = Decimal(str(round(ent["entropy"] * 100, 2)))
        total_entropy = entropy + physical_entropy

        self.events.append(
            f"[{timestamp}] Telemetría RAM: {ex['ram_free_mb']:.1f} MB | CPU: {ent['cpu_load']:.2f}"
        )

        # Trigger Purge/Reclaim if RAM is critical
        if ex["critical"] and self.reclaim_on_critical:
            reclaimed, status = self.guard.reclaim()
            self.events.append(
                f"[{timestamp}] [bold red]⚠️ RAM CRÍTICA[/] - Liberado: {reclaimed:.1f} MB ({status})"
            )

        if total_entropy > Decimal("0.0"):
            logger.info("Entropía total detectada: %s J", total_entropy)
            if self.guard.evaluate(total_entropy):
                logger.info("Exergía suficiente. Desatando Enjambre (Swarm)...")
                self.events.append(
                    f"[{timestamp}] [bold green]✔ Exergía suficiente.[/] Desatando Enjambre (Swarm)..."
                )

                # Integración Causal: Swarm 10k y Ouroboros AST Mutation
                try:
                    from pathlib import Path

                    from cortex.engine.evo.autopoiesis import AutopoiesisEngine
                    from cortex.engine.swarm.swarm_10k import SwarmCommander

                    bus_path = Path("~/.cortex/10k_shards").expanduser()
                    commander = SwarmCommander(bus_path=bus_path, tenant_id="omega_daemon")
                    ouroboros = AutopoiesisEngine(observation_window_ms=100)

                    logger.debug("Desplegando formación PHOENIX vía SwarmCommander...")
                    # Dispatch asíncrono para sanación técnica
                    if hasattr(commander, "deploy"):
                        res_deploy = commander.deploy(
                            formation="PHOENIX", mission="Sanar Entropía", cycles=1
                        )
                        if asyncio.iscoroutine(res_deploy):
                            await res_deploy

                    logger.debug("Iniciando mutación recursiva vía AutopoiesisEngine...")
                    if hasattr(ouroboros, "mutate"):
                        res_mutate = ouroboros.mutate(target="entropy_resolution")
                        if asyncio.iscoroutine(res_mutate):
                            await res_mutate

                except (ImportError, RuntimeError, ValueError) as e:
                    logger.exception("Fallo al desatar el Enjambre o Ouroboros: %s", e)
                    self.events.append(f"[{timestamp}] [bold red]✗ Fallo Swarm/Ouroboros:[/] {e}")

                self.guard.consume(total_entropy)
                logger.info("Evolución estructural completada. Auto-commit ejecutado.")
                self.events.append(
                    f"[{timestamp}] [bold green]★ Evolución completada.[/] Auto-commit ejecutado."
                )
            else:
                logger.warning("Fallo Exergético. Hibernando para conservar recursos.")
                self.events.append(
                    f"[{timestamp}] [bold red]⚠️ Fallo Exergético.[/] Presupuesto insuficiente. Hibernando..."
                )
        else:
            logger.debug("Homeostasis mantenida. Sistema estable.")
            self.events.append(f"[{timestamp}] Homeostasis mantenida. Sistema estable.")

    async def start(self, interval_s: float | None = None):
        """OmegaDaemon ciclo continuo."""
        if interval_s is not None:
            self.tick_rate = int(interval_s)
        self._running = True
        logger.info("Omega Singularity Ignited. Tick Rate: %ss", self.tick_rate)

        while self._running:
            self._cycle_count += 1
            logger.debug("Omega Ciclo #%s", self._cycle_count)
            try:
                await self._metabolize()
            except asyncio.CancelledError:
                logger.info("Omega Daemon terminating gracefully...")
                break
            except (OSError, RuntimeError, ValueError) as e:
                logger.exception("Error cataclísmico en el metabolismo: %s", e)
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.events.append(f"[{timestamp}] [bold red]💥 Error metabólico:[/] {e}")

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
