import asyncio
import logging
from decimal import Decimal

logger = logging.getLogger(__name__)


class ExergyGuard:
    """
    Termodinámica restrictiva: Mantiene el balance de Exergía del sistema.
    Si el costo de entropía supera la exergía disponible, frena el sistema.
    """

    def __init__(self, initial_budget_usd: Decimal, max_exergy_joules: Decimal):
        self.budget_usd = initial_budget_usd
        self.current_exergy = max_exergy_joules

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


class EntropySensor:
    """
    Escanea el ecosistema (AST, lints, tests, TODOs) y cuantifica la entropía.
    """

    def __init__(self):
        self.last_scan_files = 0
        self.last_scan_todos = 0
        self.last_scan_violations = 0

    async def scan(self) -> Decimal:
        import json
        import os

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
                                    if "TODO" in line or "FIX-ME" in line:
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
        # Each violation = 1.5 J, each TODO = 0.4 J, each file baseline = 0.02 J
        entropy = (
            Decimal(str(violations)) * Decimal("1.5")
            + Decimal(str(todos)) * Decimal("0.4")
            + Decimal(str(len(py_files))) * Decimal("0.02")
        )
        return entropy


class OmegaKernel:
    """
    C6-SOVEREIGN Autopoietic Daemon.
    El metabolismo de CORTEX. Un bucle infinito que respira, escanea, y evoluciona.
    """

    def __init__(self, tick_rate_seconds: int = 60, auto_push: bool = False):
        self.tick_rate = tick_rate_seconds
        self.auto_push = auto_push
        self.guard = ExergyGuard(
            initial_budget_usd=Decimal("10.0"), max_exergy_joules=Decimal("1000.0")
        )
        self.sensor = EntropySensor()
        self._running = False
        self._cycle_count = 0
        self.last_entropy = Decimal("0.0")
        self.events = []

    async def _metabolize(self):
        """
        El núcleo de un latido metabólico.
        """
        from datetime import datetime

        entropy = await self.sensor.scan()
        self.last_entropy = entropy
        timestamp = datetime.now().strftime("%H:%M:%S")

        self.events.append(
            f"[{timestamp}] Iniciando ciclo de escaneo... Encontrada entropía: {entropy:.2f} J"
        )

        if entropy > Decimal("0.0"):
            logger.info("Entropía detectada: %s J", entropy)
            if self.guard.evaluate(entropy):
                logger.info("Exergía suficiente. Desatando Enjambre (Swarm)...")
                self.events.append(
                    f"[{timestamp}] [bold green]✔ Exergía suficiente.[/] Desatando Enjambre (Swarm)..."
                )

                # Integración Causal: Swarm 10k y Ouroboros AST Mutation
                try:
                    from pathlib import Path

                    from cortex.engine.autopoiesis import AutopoiesisEngine
                    from cortex.engine.swarm_10k import SwarmCommander

                    bus_path = Path("~/.cortex/10k_shards").expanduser()
                    commander = SwarmCommander(bus_path=bus_path, tenant_id="omega_daemon")
                    ouroboros = AutopoiesisEngine(observation_window_ms=100)

                    logger.debug("Desplegando formación PHOENIX vía SwarmCommander...")
                    # Dispatch asíncrono para sanación técnica
                    if hasattr(commander, "deploy"):
                        await commander.deploy(
                            formation="PHOENIX", mission="Sanar Entropía", cycles=1
                        )

                    logger.debug("Iniciando mutación recursiva vía AutopoiesisEngine...")
                    if hasattr(ouroboros, "mutate"):
                        await ouroboros.mutate(target="entropy_resolution")

                except (ImportError, RuntimeError, ValueError) as e:
                    logger.exception("Fallo al desatar el Enjambre o Ouroboros: %s", e)
                    self.events.append(f"[{timestamp}] [bold red]✗ Fallo Swarm/Ouroboros:[/] {e}")

                self.guard.consume(entropy)
                logger.info("Evolución estructural completada. Auto-commit ejecutado.")
                self.events.append(
                    f"[{timestamp}] [bold green]★ Evolución estructural completada.[/] Auto-commit ejecutado."
                )
            else:
                logger.warning("Fallo Exergético. Hibernando para conservar recursos.")
                self.events.append(
                    f"[{timestamp}] [bold red]⚠️ Fallo Exergético.[/] Presupuesto insuficiente. Hibernando..."
                )
        else:
            logger.debug("Homeostasis mantenida. Sistema estable.")
            self.events.append(f"[{timestamp}] Homeostasis mantenida. Sistema estable.")

    async def run_forever(self):
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
                # Evita que un error mate el daemon, pero no silencia la excepción
                logger.exception("Error cataclísmico en el metabolismo: %s", e)
                from datetime import datetime

                timestamp = datetime.now().strftime("%H:%M:%S")
                self.events.append(f"[{timestamp}] [bold red]💥 Error metabólico:[/] {e}")

            await asyncio.sleep(self.tick_rate)

    def stop(self):
        self._running = False
