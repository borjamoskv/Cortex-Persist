# [C5-REAL] Exergy-Maximized
import asyncio
import logging
import signal
import time
from datetime import datetime, timezone

from babylon60.extensions.daemon.models import DEFAULT_INTERVAL

logger = logging.getLogger("moskv-daemon")


import typing


class EventLoopMixin:
    _shutdown: bool
    _stop_event: asyncio.Event
    scheduler: typing.Any
    hot_state: typing.Any
    watchdog_hub: typing.Any
    callback_api: typing.Any
    _aether_daemon: typing.Any
    fiat_oracle: typing.Any
    ast_oracle: typing.Any
    iot_oracle: typing.Any
    heartbeat_daemon: typing.Any
    entropic_wake_daemon: typing.Any
    frontier_daemon: typing.Any
    zero_prompting_daemon: typing.Any
    epistemic_breaker_daemon: typing.Any
    sentinel_oracle: typing.Any
    agy2_planner_daemon: typing.Any
    sovereignty_runtime: typing.Any
    _threads: list[typing.Any]
    _event_bus: typing.Any

    check: typing.Callable[[], None]
    _run_neural_loop_async: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]
    _run_lifecycle_daemon_async: typing.Callable[
        ..., typing.Coroutine[typing.Any, typing.Any, None]
    ]
    _run_loop_daemon_async: typing.Callable[..., typing.Coroutine[typing.Any, typing.Any, None]]
    _run_health_loop_async: typing.Callable[[], typing.Coroutine[typing.Any, typing.Any, None]]

    def run(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Run the daemon using the sovereign async loop (all subsystems as tasks)."""
        from babylon60.events.loop import sovereign_run

        logger.info("🚀 MOSKV-1 Daemon starting in sovereign async mode (interval=%ds)", interval)
        sovereign_run(self.run_sovereign(interval=interval))

    def _signal_shutdown(self) -> None:
        """Signal handler for async loop."""

        logger.info("Received shutdown signal")

        self._shutdown = True

        self._stop_event.set()

        # Cancel all running tasks

        for task in asyncio.all_tasks():
            if task is not asyncio.current_task():
                task.cancel()

    def _register_default_schedules(self) -> None:
        """Register built-in recurring tasks with the scheduler."""

        if self.scheduler is None:
            return

        # Hot state TTL purge every 10 minutes

        if self.hot_state is not None:
            self.scheduler.add_recurring(
                "purge_expired_state",
                lambda: asyncio.coroutine(lambda: self.hot_state.purge_expired())(),  # type: ignore
                interval_s=600,
                priority=8,
            )

        # CABLE-04a: daily pruning of the Ouroboros graph
        import sys
        from pathlib import Path

        scripts_path = str(Path(__file__).resolve().parents[3] / "scripts")
        if scripts_path not in sys.path:
            sys.path.append(scripts_path)

        async def run_ouroboros_prune():
            from babylon60.core.paths import CORTEX_DB
            from ouroboros_prune import execute_thermal_purge

            await asyncio.to_thread(execute_thermal_purge, db_path=str(CORTEX_DB))

        self.scheduler.add_recurring(
            "ouroboros_prune",
            lambda: run_ouroboros_prune(),
            interval_s=86400,
            priority=6,
        )

        # CABLE-04b: LLM absorption of reflections.md -> SKILL.md every 12h
        async def run_ouroboros_absorb():
            from ouroboros_absorb_runner import main as absorb_main

            await absorb_main()

        self.scheduler.add_recurring(
            "ouroboros_absorb",
            lambda: run_ouroboros_absorb(),
            interval_s=43200,
            priority=5,
        )

    async def run_sovereign(self, interval: int = DEFAULT_INTERVAL) -> None:
        """Sovereign async execution - single event loop, all subsystems as tasks.

        This is the x100 upgrade: replaces N threads with N async tasks on one loop.
        All subsystems share the same DistributedEventBus and HotStateDB.
        """
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            try:
                loop.add_signal_handler(sig, self._signal_shutdown)
            except Exception as exc:
                logger.warning("Suppressed exception: %s", exc)
        logger.info("🚀 MOSKV-1 Sovereign Daemon starting (interval=%ds)", interval)
        if self.hot_state is not None:
            self.hot_state.set("daemon.mode", "sovereign")
            self.hot_state.set(
                "daemon.started_at",
                datetime.fromtimestamp(time.time(), tz=timezone.utc).isoformat(),
            )
        tasks: list[asyncio.Task] = []
        tasks.append(asyncio.create_task(self._sovereign_check_loop(interval), name="CheckLoop"))
        if self.scheduler is not None:
            self._register_default_schedules()
            tasks.append(asyncio.create_task(self.scheduler.run(), name="Scheduler"))
        if self.watchdog_hub is not None:
            tasks.append(asyncio.create_task(self.watchdog_hub.start(), name="WatchdogHub"))
        if self.callback_api is not None:
            tasks.append(asyncio.create_task(self.callback_api.serve(), name="CallbackAPI"))
        if self._aether_daemon is not None:
            tasks.append(
                asyncio.create_task(
                    asyncio.to_thread(self._aether_daemon.start), name="AetherAgent"
                )
            )
        if self.fiat_oracle:
            tasks.append(asyncio.create_task(self.fiat_oracle.run_loop(), name="FiatOracle"))
        tasks.append(asyncio.create_task(self._run_neural_loop_async(), name="NeuralSync"))
        if self.ast_oracle:
            tasks.append(
                asyncio.create_task(
                    self._run_lifecycle_daemon_async(self.ast_oracle, "AST Oracle", "👁️"),
                    name="ASTOracle",
                )
            )
        if getattr(self, "iot_oracle", None):
            tasks.append(
                asyncio.create_task(
                    self._run_lifecycle_daemon_async(self.iot_oracle, "IoT Oracle", "📡"),
                    name="IoTOracle",
                )
            )
        if self.heartbeat_daemon:
            tasks.append(
                asyncio.create_task(
                    self._run_lifecycle_daemon_async(self.heartbeat_daemon, "Heartbeat", "❤️"),
                    name="HeartbeatDaemon",
                )
            )
        if self.entropic_wake_daemon:
            tasks.append(
                asyncio.create_task(
                    self._run_loop_daemon_async(self.entropic_wake_daemon, "Entropic Wake", "🌌"),
                    name="EntropicWakeDaemon",
                )
            )
        if self.frontier_daemon:
            tasks.append(
                asyncio.create_task(
                    self._run_loop_daemon_async(self.frontier_daemon, "Frontier", "🚀"),
                    name="FrontierDaemon",
                )
            )
        if getattr(self, "zero_prompting_daemon", None):
            tasks.append(
                asyncio.create_task(
                    self._run_loop_daemon_async(self.zero_prompting_daemon, "Zero-Prompting", "🧠"),
                    name="ZeroPromptingDaemon",
                )
            )
        if getattr(self, "epistemic_breaker_daemon", None):
            tasks.append(
                asyncio.create_task(
                    self._run_loop_daemon_async(
                        self.epistemic_breaker_daemon, "Epistemic Breaker", "🛡️", run_method="run"
                    ),
                    name="EpistemicBreakerDaemon",
                )
            )
        if getattr(self, "sentinel_oracle", None):
            tasks.append(
                asyncio.create_task(
                    self._run_loop_daemon_async(self.sentinel_oracle, "Sentinel Oracle", "🛡️"),
                    name="SentinelOracle",
                )
            )
        if getattr(self, "agy2_planner_daemon", None):
            tasks.append(
                asyncio.create_task(
                    self._run_loop_daemon_async(self.agy2_planner_daemon, "AGY2 Planner", "🧠"),
                    name="AGY2PlannerDaemon",
                )
            )
        if getattr(self, "sovereignty_runtime", None):
            tasks.append(
                asyncio.create_task(
                    self.sovereignty_runtime.start(), name="EventSovereigntyRuntime"
                )
            )
            # Ensure auth_requests table exists asynchronously at startup
            if (
                hasattr(self.sovereignty_runtime, "auth_gateway")
                and self.sovereignty_runtime.auth_gateway
            ):
                tasks.append(
                    asyncio.create_task(self.sovereignty_runtime.auth_gateway.ensure_table())
                )
        tasks.append(asyncio.create_task(self._run_health_loop_async(), name="HealthMonitor"))
        async_count = len(tasks)
        thread_count = len(self._threads)
        logger.info(
            "Sovereign Daemon started: %d async tasks + %d legacy threads",
            async_count,
            thread_count,
        )
        try:
            await asyncio.gather(*tasks, return_exceptions=True)
        except Exception as exc:
            logger.warning("Suppressed exception: %s", exc)
        finally:
            await self._sovereign_shutdown()

    async def _sovereign_check_loop(self, interval: int) -> None:
        """Async version of the main check loop."""
        while not self._shutdown:
            try:
                # Run check in thread pool to not block the event loop
                await asyncio.to_thread(self.check)

                # Update hot state cycle counter
                if self.hot_state is not None:
                    self.hot_state.increment("cycle_count")

            except Exception as e:  # noqa: BLE001
                logger.error("Check loop error: %s", e)

            # Async sleep instead of threading.Event.wait
            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def _sovereign_shutdown(self) -> None:
        """Graceful shutdown of all sovereign subsystems."""
        logger.info("Sovereign shutdown initiated...")

        if self.watchdog_hub is not None:
            await self.watchdog_hub.stop()
        if self.scheduler is not None:
            await self.scheduler.stop()
        if hasattr(self, "_event_bus") and self._event_bus is not None:
            await self._event_bus.shutdown()
        if self.entropic_wake_daemon:
            self.entropic_wake_daemon.stop()
        if self.frontier_daemon:
            self.frontier_daemon.stop()
        if getattr(self, "zero_prompting_daemon", None):
            self.zero_prompting_daemon.stop()  # type: ignore[union-attr]
        if getattr(self, "epistemic_breaker_daemon", None):
            self.epistemic_breaker_daemon.stop()  # type: ignore[union-attr]
        if getattr(self, "sovereignty_runtime", None):
            await self.sovereignty_runtime.stop()

        # Persist final state
        if self.hot_state is not None:
            self.hot_state.set("daemon.stopped_at", datetime.now(timezone.utc).isoformat())

        logger.info("MOSKV-1 Sovereign Daemon stopped")
